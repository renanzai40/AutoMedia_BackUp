"""``AUTOMEDIA_LLM_REASONING_MODEL`` must reach ``llm.text_generation.reasoning_model``.

Nightly 2026-11-17: sandboxed validation runs use a fresh config dir, so the
file-layer ``reasoning_model: true`` disappears and reasoning models keep
thinking enabled — structured completions come back truncated/empty. The env
layer is the only channel that survives the sandbox, but it had no mapping
for this flag.

Reverse evidence (DoD): revert the ``llm_reasoning_model`` remap in
``_env_to_config`` and the first two tests fail — the key lands on the
generic ``llm.llm.reasoning.model`` path instead.
"""

from __future__ import annotations

from automedia.core.config_loader import _env_to_config


def _tg(monkeypatch, value: str) -> object:
    monkeypatch.setenv("AUTOMEDIA_LLM_REASONING_MODEL", value)
    return _env_to_config()["llm"]["text_generation"]["reasoning_model"]


class TestReasoningModelEnvRemap:
    def test_true_string(self, monkeypatch):
        assert _tg(monkeypatch, "true") is True

    def test_false_string(self, monkeypatch):
        assert _tg(monkeypatch, "false") is False

    def test_numeric_variants(self, monkeypatch):
        assert _tg(monkeypatch, "1") is True
        assert _tg(monkeypatch, "0") is False
        assert _tg(monkeypatch, "on") is True
        assert _tg(monkeypatch, "off") is False

    def test_case_insensitive_and_whitespace(self, monkeypatch):
        assert _tg(monkeypatch, "  TRUE ") is True
        assert _tg(monkeypatch, "No") is False
