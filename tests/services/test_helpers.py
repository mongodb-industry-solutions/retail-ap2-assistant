import pytest

from src.services.helpers import (
    DEFAULT_LLM_PARSE_ERROR,
    ResponseParser,
    WorkflowPromptParts,
    coerceLlmContentToStr,
    parse_workflow_llm_response,
)


class TestResponseParser:
    """Tests for ResponseParser utility."""

    def test_parseJsonValid(self):
        content = '{"stepId": "step1", "answers": ["Answer 1", "Answer 2"]}'
        stepId, answers = ResponseParser.parseJson(content, 2)
        assert stepId == "step1"
        assert answers == ["Answer 1", "Answer 2"]

    def test_parseJsonWithCodeBlock(self):
        content = '```json\n{"stepId": "step1", "answers": ["Answer 1"]}\n```'
        stepId, answers = ResponseParser.parseJson(content, 2)
        assert stepId == "step1"
        assert answers == ["Answer 1"]

    def test_parseJsonTruncatesAnswers(self):
        content = '{"stepId": "step1", "answers": ["A1", "A2", "A3"]}'
        stepId, answers = ResponseParser.parseJson(content, 2)
        assert len(answers) == 2

    def test_parseJsonInvalidJson(self):
        with pytest.raises(ValueError):
            ResponseParser.parseJson("not json", 2)

    def test_parseJsonMissingKey(self):
        with pytest.raises(ValueError):
            ResponseParser.parseJson('{"wrong": "format"}', 2)


class TestParseWorkflowLlmResponse:
    def test_success(self):
        sid, ans, err = parse_workflow_llm_response(
            '{"stepId": "a", "answers": ["x", "y"]}', 2
        )
        assert sid == "a"
        assert ans == ["x", "y"]
        assert err is None

    def test_error_shape(self):
        sid, ans, err = parse_workflow_llm_response(
            '{"error": "Tell the user this"}', 2
        )
        assert sid == ""
        assert ans == []
        assert err == "Tell the user this"

    def test_json_embedded_in_noise(self):
        raw = 'Here you go: {"stepId": "s1", "answers": ["one"]} thanks'
        sid, ans, err = parse_workflow_llm_response(raw, 1)
        assert sid == "s1"
        assert ans == ["one"]
        assert err is None

    def test_empty_yields_default_error(self):
        sid, ans, err = parse_workflow_llm_response("   ", 2)
        assert sid == ""
        assert ans == []
        assert err == DEFAULT_LLM_PARSE_ERROR

    def test_invalid_json_yields_default_error(self):
        sid, ans, err = parse_workflow_llm_response("not json {", 2)
        assert err == DEFAULT_LLM_PARSE_ERROR

    def test_too_few_answers_yields_default_error(self):
        sid, ans, err = parse_workflow_llm_response(
            '{"stepId": "a", "answers": ["only"]}', 2
        )
        assert err == DEFAULT_LLM_PARSE_ERROR

    def test_code_like_answers_rejected(self):
        payload = (
            '{"stepId": "shopping-agent-introduction", "answers": ['
            '"import json\\n", "def foo(): pass"]}'
        )
        sid, ans, err = parse_workflow_llm_response(payload, 2)
        assert sid == ""
        assert ans == []
        assert err == DEFAULT_LLM_PARSE_ERROR

    def test_oversized_answer_rejected(self):
        long = "x" * 600
        sid, ans, err = parse_workflow_llm_response(
            f'{{"stepId": "step1", "answers": ["{long}", "{long}"]}}', 2
        )
        assert err == DEFAULT_LLM_PARSE_ERROR


class TestWorkflowPromptParts:
    def test_policy_items_prefers_policies_key(self):
        assert WorkflowPromptParts.policy_items(
            {"policies": ["a"], "policy": ["b"]}
        ) == ["a"]

    def test_policy_items_falls_back_to_policy(self):
        assert WorkflowPromptParts.policy_items({"policy": ["x"]}) == ["x"]

    def test_policy_items_empty_when_missing(self):
        assert WorkflowPromptParts.policy_items({}) == []

    def test_policy_items_non_list_policies_falls_back(self):
        assert WorkflowPromptParts.policy_items(
            {"policies": "bad", "policy": ["ok"]}
        ) == ["ok"]

    def test_bullet_lines_goals(self):
        wf = {"goals": ["a", None, "b"]}
        assert WorkflowPromptParts.bullet_lines(wf, "goals") == [
            "  - a",
            "  - b",
        ]

    def test_bullet_lines_steps_skips_non_dict(self):
        wf = {"steps": [{"id": "s1", "description": "d"}, "skip", {"id": "s2"}]}
        lines = WorkflowPromptParts.bullet_lines(wf, "steps")
        assert lines[0] == "  - s1: d"
        assert lines[1] == "  - s2: "


class TestCoerceLlmContentToStr:
    def test_strUnchanged(self):
        assert coerceLlmContentToStr("hello") == "hello"

    def test_noneBecomesEmpty(self):
        assert coerceLlmContentToStr(None) == ""

    def test_listOfTextDicts(self):
        parts = [{"type": "text", "text": '{"stepId": "a", "answers": []}'}]
        assert "stepId" in coerceLlmContentToStr(parts)
