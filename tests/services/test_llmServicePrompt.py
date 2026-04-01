"""Prompt shape for LlmService (text vs JSON) without invoking an LLM."""

import json

import pytest

from src.services.llmService import LlmService


class _StubLlm(LlmService):
    def _invokeLogMessage(self) -> str:
        return "stub"


@pytest.fixture
def sample_context():
    return {
        "workflow": {
            "description": "Test workflow.",
            "goals": ["G1"],
            "policies": ["P1"],
            "steps": [{"id": "step-a", "description": "First."}],
        },
        "conversation": [
            {"role": "user", "message": "Hi"},
            {"role": "agent", "message": "Hello."},
        ],
        "maxAnswers": 2,
    }


def test_build_prompt_json_shape(sample_context, monkeypatch):
    monkeypatch.setenv("LLM_PROMPT_FORMAT", "json")
    svc = _StubLlm()
    raw = svc._buildPromptCore(sample_context)
    data = json.loads(raw)
    assert "instruction" in data
    assert data["maxAnswers"] == 2
    assert data["workflow"]["description"] == "Test workflow."
    assert data["workflow"]["goals"] == ["G1"]
    assert data["workflow"]["policies"] == ["P1"]
    assert data["workflow"]["steps"] == [{"id": "step-a", "description": "First."}]
    assert len(data["conversation"]) == 2
    assert "stepId" in data["instruction"]
    assert "buyer" in data["instruction"].lower()


def test_build_prompt_text_contains_sections(sample_context, monkeypatch):
    monkeypatch.setenv("LLM_PROMPT_FORMAT", "text")
    svc = _StubLlm()
    raw = svc._buildPromptCore(sample_context)
    assert "Workflow: Test workflow." in raw
    assert "Goals:" in raw
    assert "Policies:" in raw
    assert "Steps:" in raw
    assert "user: Hi" in raw
    assert "Example success:" in raw
    assert "buyer" in raw.lower()


def test_default_format_is_text(sample_context, monkeypatch):
    monkeypatch.delenv("LLM_PROMPT_FORMAT", raising=False)
    assert _StubLlm()._promptFormat() == "text"


def test_prompt_format_json_case_insensitive(monkeypatch):
    monkeypatch.setenv("LLM_PROMPT_FORMAT", "JSON")
    assert _StubLlm()._promptFormat() == "json"
