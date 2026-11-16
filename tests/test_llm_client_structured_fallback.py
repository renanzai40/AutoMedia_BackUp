"""Structured chain must fall back to the manual path on length truncation.

Nightly 2026-11-17: on a reasoning model with thinking enabled, the beta
``parse()`` attempt can truncate at ``max_tokens`` (reasoning spends the
budget; bigmodel glm-4.7-flash: reasoning_tokens=1777 / completion_tokens=2048)
and openai's SDK raises ``LengthFinishReasonError`` — a plain ``Exception``,
NOT an ``APIError``. The chain used to abort instead of falling back to the
manual ``json_object`` path, hard-failing quality gates and journeys.

Reverse evidence (DoD): revert ``_get_fallback_structured_errors`` to the
pre-fix tuple and ``test_length_truncation_falls_back_to_manual_path`` fails
with the raw LengthFinishReasonError escaping the chain.
"""

from __future__ import annotations

from types import SimpleNamespace

import openai
import pytest
from pydantic import BaseModel

import automedia.core.llm_client as llm_client


class TinyOutput(BaseModel):
    ok: bool


def _stub_response(content: str) -> SimpleNamespace:
    message = SimpleNamespace(content=content, parsed=None, reasoning_content=None)
    choice = SimpleNamespace(message=message, finish_reason="stop")
    return SimpleNamespace(choices=[choice])


class TestFallbackTuple:
    def test_length_error_included(self):
        assert openai.LengthFinishReasonError in llm_client._FALLBACK_STRUCTURED_ERRORS


class TestChainBehavior:
    def test_length_truncation_falls_back_to_manual_path(self, monkeypatch: pytest.MonkeyPatch):
        stub_completion = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=None, reasoning_content="thinking..."),
                    finish_reason="length",
                )
            ],
            usage=SimpleNamespace(completion_tokens=2048, total_tokens=3000),
        )

        def _raise_length(*a, **k):
            raise openai.LengthFinishReasonError(completion=stub_completion)

        monkeypatch.setattr(llm_client, "_llm_structured_completion_with_retry", _raise_length)

        captured: dict[str, object] = {}

        def fake_chat(client, **kwargs):
            captured["response_format"] = kwargs.get("response_format")
            return _stub_response('{"ok": true}')

        monkeypatch.setattr(llm_client, "_llm_chat_completion_with_retry", fake_chat)

        out = llm_client.llm_complete_structured_safe(
            "Return JSON.", response_format=TinyOutput, max_tokens=64
        )
        assert out.ok is True
        assert captured["response_format"] == {"type": "json_object"}
