"""Backend abstraction for simula.

One interface, two adapters. Local-first (llama.cpp + GBNF) but always able to run against
any OpenAI-compatible endpoint. "Constrained output" is the reliability backbone and is
implemented differently per backend (PLAN.md #5, PRINCIPLES.md #4).

This is a SKELETON: contracts + docstrings. Implement per build phases. stdlib only at the
contract level; concrete adapters may use `requests`/`httpx` and `sentence-transformers`.
"""
from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence

_HTTP_TIMEOUT = 120


def _post_json(url: str, payload: dict, *, headers: dict | None = None, timeout: int = _HTTP_TIMEOUT) -> dict:
    """Minimal stdlib JSON POST. Keeps the default (local) backend dependency-free."""
    data = json.dumps(payload).encode("utf-8")
    all_headers = {"Content-Type": "application/json", **(headers or {})}
    req = urllib.request.Request(url, data=data, headers=all_headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _render_gemma_prompt(messages: Sequence["Message"]) -> str:
    """Render messages into a Gemma-style chat prompt for llama.cpp's native /completion.

    Gemma has no separate system role, so system content is folded into the first user turn
    (PLAN.md #5). This targets Gemma; other models loaded on llama.cpp may need a different
    template, but the OpenAI-compatible path (chat completions) handles templating server-side.
    """
    system = "\n\n".join(m.content for m in messages if m.role == "system")
    turns: list[str] = []
    first_user = True
    for m in messages:
        if m.role == "system":
            continue
        content = m.content
        if m.role == "user" and first_user and system:
            content = f"{system}\n\n{content}"
            first_user = False
        role = "model" if m.role == "assistant" else "user"
        turns.append(f"<start_of_turn>{role}\n{content}<end_of_turn>")
    turns.append("<start_of_turn>model\n")
    return "\n".join(turns)


@dataclass(frozen=True)
class Message:
    role: str          # "system" | "user" | "assistant"
    content: str


@dataclass(frozen=True)
class Contract:
    """How to constrain structured output. Backend chooses how to honor it.

    Exactly one of `gbnf_path` / `json_schema` is the primary mechanism; backends fall back
    to a parse-and-repair loop if neither is supported.
    """
    gbnf_path: Path | None = None        # used by llama.cpp native /completion
    json_schema: dict | None = None      # used by OpenAI-compat (response_format/tools)


class Backend(Protocol):
    """Text + embedding generation. Implementations MUST guarantee that, when a Contract is
    given, the returned string parses against it (raising on irrecoverable failure)."""

    def complete(
        self,
        messages: Sequence[Message],
        *,
        contract: Contract | None = None,
        temperature: float = 0.2,
        max_tokens: int = 800,
    ) -> str:
        ...

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        ...


class LlamaCppBackend:
    """Default, local. Talks to a llama.cpp server (e.g. :18083).

    Constrained output: prefer the native /completion endpoint with a `grammar` (GBNF) field,
    which guarantees valid structure at decode time. Embeddings stay local (e5-small).
    """

    def __init__(self, endpoint: str, model: str, *, prefer_native_grammar: bool = True) -> None:
        self.endpoint = endpoint
        self.model = model
        self.prefer_native_grammar = prefer_native_grammar

    def complete(self, messages, *, contract=None, temperature=0.2, max_tokens=800) -> str:
        json_schema = contract.json_schema if contract is not None else None
        gbnf_path = contract.gbnf_path if contract is not None else None

        # Preferred: the OpenAI-compatible chat endpoint with response_format json_schema. The server
        # applies the model's own chat template (so reasoning models behave) and enforces structure.
        if json_schema is not None:
            payload = {
                "model": self.model,
                "messages": [{"role": m.role, "content": m.content} for m in messages],
                "temperature": temperature,
                "max_tokens": max_tokens,
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {"name": "turn_output", "schema": json_schema, "strict": True},
                },
            }
            resp = _post_json(f"{self.endpoint.rstrip('/')}/v1/chat/completions", payload)
            return resp["choices"][0]["message"]["content"]

        # No schema but a GBNF grammar: use the native /completion endpoint with a raw prompt.
        if self.prefer_native_grammar and gbnf_path is not None:
            payload = {
                "prompt": _render_gemma_prompt(messages),
                "grammar": Path(gbnf_path).read_text(encoding="utf-8"),
                "temperature": temperature,
                "n_predict": max_tokens,
                "cache_prompt": True,
            }
            resp = _post_json(f"{self.endpoint.rstrip('/')}/completion", payload)
            return resp["content"]

        # Unconstrained: plain chat completion.
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        resp = _post_json(f"{self.endpoint.rstrip('/')}/v1/chat/completions", payload)
        return resp["choices"][0]["message"]["content"]

    def embed(self, texts) -> list[list[float]]:
        # Phase 1: local e5-small (sentence-transformers) or llama.cpp /embedding.
        raise NotImplementedError


class OpenAICompatBackend:
    """Any OpenAI-compatible endpoint + key + model. Never store the key in config; read env."""

    def __init__(self, base_url: str, api_key: str, model: str, *, structured_output: str = "json_schema") -> None:
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.structured_output = structured_output  # "json_schema" | "tools" | "repair"

    def complete(self, messages, *, contract=None, temperature=0.2, max_tokens=800) -> str:
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        schema = contract.json_schema if contract is not None else None
        mode = self.structured_output

        if schema is not None and mode == "tools":
            payload["tools"] = [{
                "type": "function",
                "function": {"name": "turn_output", "parameters": schema},
            }]
            payload["tool_choice"] = {"type": "function", "function": {"name": "turn_output"}}
        elif schema is not None and mode == "json_schema":
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "turn_output", "schema": schema, "strict": True},
            }
        # mode == "repair" (or no schema): free generation; the caller parses/repairs.

        resp = _post_json(
            f"{self.base_url.rstrip('/')}/chat/completions",
            payload,
            headers={"Authorization": f"Bearer {self.api_key}"},
        )
        message = resp["choices"][0]["message"]
        if message.get("tool_calls"):
            return message["tool_calls"][0]["function"]["arguments"]
        return message["content"]

    def embed(self, texts) -> list[list[float]]:
        # Default to local e5 even here (decoupling); only use remote embeddings if configured.
        raise NotImplementedError


def from_config(cfg: dict) -> Backend:
    """Construct the backend from a parsed simula.toml dict. See simula.toml.example."""
    kind = cfg["backend"]["kind"]
    if kind == "llamacpp":
        c = cfg["backend"]["llamacpp"]
        return LlamaCppBackend(c["endpoint"], c["model"], prefer_native_grammar=c.get("prefer_native_grammar", True))
    if kind == "openai_compat":
        import os
        c = cfg["backend"]["openai_compat"]
        return OpenAICompatBackend(c["base_url"], os.environ[c["api_key_env"]], c["model"],
                                   structured_output=c.get("structured_output", "json_schema"))
    raise ValueError(f"unknown backend.kind: {kind}")
