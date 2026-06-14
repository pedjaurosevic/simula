"""Backend abstraction for simula.

One interface, two adapters. Local-first (llama.cpp + GBNF) but always able to run against
any OpenAI-compatible endpoint. "Constrained output" is the reliability backbone and is
implemented differently per backend (PLAN.md #5, PRINCIPLES.md #4).

This is a SKELETON: contracts + docstrings. Implement per build phases. stdlib only at the
contract level; concrete adapters may use `requests`/`httpx` and `sentence-transformers`.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, Sequence


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
        # Phase 0: implement.
        # - If contract.gbnf_path and prefer_native_grammar: POST /completion with
        #   {"prompt": render(messages), "grammar": gbnf_text, "temperature": ..., "n_predict": ...}
        #   (Gemma: fold system into the prompt; see PRINCIPLES.md note on system role.)
        # - Else: POST /v1/chat/completions (no hard grammar; rely on repair loop).
        raise NotImplementedError

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
        # Phase 0: implement.
        # - structured_output == "json_schema": pass response_format with contract.json_schema.
        # - "tools": expose a single tool whose params == contract.json_schema; force tool_choice.
        # - "repair": free generation + JSON extraction + one repair retry.
        raise NotImplementedError

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
