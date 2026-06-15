"""Unit tests for backend helpers that don't need a live server."""
from __future__ import annotations

import simula.backends as backends
from simula.backends import Contract, Message, OpenAICompatBackend, _render_gemma_prompt, from_config


def test_render_folds_system_into_first_user_turn():
    messages = [
        Message(role="system", content="SYS"),
        Message(role="user", content="hello"),
        Message(role="assistant", content="hi"),
        Message(role="user", content="again"),
    ]
    prompt = _render_gemma_prompt(messages)

    assert prompt.endswith("<start_of_turn>model\n")
    # System is folded into the first user turn only.
    assert "<start_of_turn>user\nSYS\n\nhello<end_of_turn>" in prompt
    assert "<start_of_turn>model\nhi<end_of_turn>" in prompt
    assert prompt.count("SYS") == 1


def test_openai_compat_json_schema_and_auth(monkeypatch):
    captured = {}

    def fake_post(url, payload, *, headers=None, timeout=120):
        captured["url"] = url
        captured["payload"] = payload
        captured["headers"] = headers
        return {"choices": [{"message": {"content": '{"narration":"ok","deltas":[]}'}}]}

    monkeypatch.setattr(backends, "_post_json", fake_post)
    be = OpenAICompatBackend("https://api.example.com/v1", "sk-test", "gpt-x")
    out = be.complete([Message("user", "hi")], contract=Contract(json_schema={"type": "object"}))

    assert out == '{"narration":"ok","deltas":[]}'
    assert captured["url"] == "https://api.example.com/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer sk-test"
    assert captured["payload"]["response_format"]["type"] == "json_schema"


def test_openai_compat_tools_mode_reads_arguments(monkeypatch):
    def fake_post(url, payload, *, headers=None, timeout=120):
        assert payload["tool_choice"]["function"]["name"] == "turn_output"
        return {"choices": [{"message": {"tool_calls": [
            {"function": {"name": "turn_output", "arguments": '{"narration":"x","deltas":[]}'}}
        ]}}]}

    monkeypatch.setattr(backends, "_post_json", fake_post)
    be = OpenAICompatBackend("https://api.example.com/v1", "k", "m", structured_output="tools")
    out = be.complete([Message("user", "hi")], contract=Contract(json_schema={"type": "object"}))

    assert out == '{"narration":"x","deltas":[]}'


def test_from_config_builds_llamacpp_backend():
    cfg = {
        "backend": {
            "kind": "llamacpp",
            "llamacpp": {"endpoint": "http://127.0.0.1:18083", "model": "gemma-4-12b-it"},
        }
    }
    backend = from_config(cfg)
    assert backend.endpoint == "http://127.0.0.1:18083"
    assert backend.prefer_native_grammar is True
