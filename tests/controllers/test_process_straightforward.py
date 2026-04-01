"""
/api/process tests grounded in cfg/conversations/straightforward.json.

Supervised agent turns carry ``step`` (ground-truth step id). Each checkpoint is a
conversation prefix ending with that agent message, matching the workflow policy
that the latest message is from the agent. The LLM is mocked so responses return
the expected step id and sample answers; this validates the HTTP contract and
that the controller passes workflow + conversation through correctly. Error cases
cover 404, 422 (validation + LLM parse), and 500.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.controllers.workflowController import controller
from src.main import app

_ROOT = Path(__file__).resolve().parents[2]
_STRAIGHTFORWARD_CONV_PATH = _ROOT / "cfg" / "conversations" / "straightforward.json"
_STRAIGHTFORWARD_WF_PATH = _ROOT / "cfg" / "workflows" / "straightforward.json"


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _strip_steps(messages: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Client-style payload without supervised ``step`` hints."""
    return [{"role": m["role"], "message": m["message"]} for m in messages]


def _agent_step_checkpoints(
    conversation: list[dict[str, Any]],
) -> list[tuple[str, list[dict[str, Any]]]]:
    """
    (expected_step_id, prefix) for each agent message that defines ``step``.
    Prefix includes that agent turn (last message = agent), per workflow policy.
    """
    out: list[tuple[str, list[dict[str, Any]]]] = []
    for i, msg in enumerate(conversation):
        if msg.get("role") == "agent" and msg.get("step"):
            out.append((msg["step"], conversation[: i + 1]))
    return out


def _pytest_checkpoint_params() -> list[pytest.ParameterSet]:
    data = _load_json(_STRAIGHTFORWARD_CONV_PATH)
    conv = data["conversation"]
    params: list[pytest.ParameterSet] = []
    for step_id, prefix in _agent_step_checkpoints(conv):
        label = step_id
        params.append(pytest.param(step_id, prefix, id=label))
    return params


class TestProcessStraightforwardSupervisedSteps:
    """Step ids from supervised conversation vs /api/process (mocked LLM)."""

    def setup_method(self):
        self.mockWorkflowService = MagicMock()
        self.mockLlmService = MagicMock()
        self.originalWorkflowService = controller._workflowService
        self.originalLlmService = controller._llmService
        controller.workflowService = self.mockWorkflowService
        controller.llmService = self.mockLlmService
        self.client = TestClient(app)
        self.workflow_payload = _load_json(_STRAIGHTFORWARD_WF_PATH)

    def teardown_method(self):
        controller._workflowService = self.originalWorkflowService
        controller._llmService = self.originalLlmService

    @pytest.mark.parametrize(
        ("expected_step_id", "prefix"), _pytest_checkpoint_params()
    )
    def test_process_returns_supervised_step_id(
        self, expected_step_id: str, prefix: list[dict[str, Any]]
    ):
        self.mockWorkflowService.loadWorkflow.return_value = self.workflow_payload
        answers = ["Suggested reply A", "Suggested reply B"]
        self.mockLlmService.generateResponse.return_value = (
            expected_step_id,
            answers,
            None,
        )

        payload = {
            "workflowId": "straightforward",
            "conversation": _strip_steps(prefix),
            "maxAnswers": 2,
        }
        response = self.client.post("/api/process", json=payload)

        assert response.status_code == 200
        body = response.json()
        assert body["workflowId"] == "straightforward"
        assert body["stepId"] == expected_step_id
        assert body["answers"] == answers
        self.mockWorkflowService.loadWorkflow.assert_called_once_with("straightforward")
        call_kw = self.mockLlmService.generateResponse.call_args[0][0]
        assert call_kw["maxAnswers"] == 2
        assert call_kw["workflow"] == self.workflow_payload
        assert call_kw["conversation"] == _strip_steps(prefix)

    def test_supervised_step_ids_are_declared_in_workflow(self):
        wf = _load_json(_STRAIGHTFORWARD_WF_PATH)
        declared = {s["id"] for s in wf["steps"]}
        data = _load_json(_STRAIGHTFORWARD_CONV_PATH)
        for step_id, _ in _agent_step_checkpoints(data["conversation"]):
            assert step_id in declared, (
                f"Supervised step {step_id!r} missing from workflow steps"
            )


class TestProcessStraightforwardSlices:
    """A few named slices of the same conversation (readability + regression)."""

    def setup_method(self):
        self.mockWorkflowService = MagicMock()
        self.mockLlmService = MagicMock()
        self.originalWorkflowService = controller._workflowService
        self.originalLlmService = controller._llmService
        controller.workflowService = self.mockWorkflowService
        controller.llmService = self.mockLlmService
        self.client = TestClient(app)
        self.workflow_payload = _load_json(_STRAIGHTFORWARD_WF_PATH)
        self.full_conv = _load_json(_STRAIGHTFORWARD_CONV_PATH)["conversation"]

    def teardown_method(self):
        controller._workflowService = self.originalWorkflowService
        controller._llmService = self.originalLlmService

    def test_slice_after_shopping_agent_introduction(self):
        """First labeled agent turn: shopping-agent-introduction."""
        prefix = self.full_conv[:2]
        assert prefix[-1].get("step") == "shopping-agent-introduction"
        self.mockWorkflowService.loadWorkflow.return_value = self.workflow_payload
        self.mockLlmService.generateResponse.return_value = (
            "shopping-agent-introduction",
            ["I'm looking for running shoes."],
            None,
        )
        r = self.client.post(
            "/api/process",
            json={
                "workflowId": "straightforward",
                "conversation": _strip_steps(prefix),
                "maxAnswers": 1,
            },
        )
        assert r.status_code == 200
        assert r.json()["stepId"] == "shopping-agent-introduction"
        assert len(r.json()["answers"]) == 1

    def test_slice_after_mandates_created(self):
        """Product options presented: mandates-created."""
        idx = next(
            i
            for i, m in enumerate(self.full_conv)
            if m.get("role") == "agent" and m.get("step") == "mandates-created"
        )
        prefix = self.full_conv[: idx + 1]
        self.mockWorkflowService.loadWorkflow.return_value = self.workflow_payload
        self.mockLlmService.generateResponse.return_value = (
            "mandates-created",
            ["I'll take option 2.", "Option 2 please."],
            None,
        )
        r = self.client.post(
            "/api/process",
            json={
                "workflowId": "straightforward",
                "conversation": _strip_steps(prefix),
                "maxAnswers": 2,
            },
        )
        assert r.status_code == 200
        assert r.json()["stepId"] == "mandates-created"

    def test_slice_after_payment_completed(self):
        """Final receipt: payment-completed."""
        idx = next(
            i
            for i, m in enumerate(self.full_conv)
            if m.get("role") == "agent" and m.get("step") == "payment-completed"
        )
        prefix = self.full_conv[: idx + 1]
        self.mockWorkflowService.loadWorkflow.return_value = self.workflow_payload
        self.mockLlmService.generateResponse.return_value = (
            "payment-completed",
            ["Thank you very much."],
            None,
        )
        r = self.client.post(
            "/api/process",
            json={
                "workflowId": "straightforward",
                "conversation": _strip_steps(prefix),
                "maxAnswers": 1,
            },
        )
        assert r.status_code == 200
        assert r.json()["stepId"] == "payment-completed"


class TestProcessWorkflowErrors:
    """HTTP errors and message bodies for /api/process."""

    def setup_method(self):
        self.mockWorkflowService = MagicMock()
        self.mockLlmService = MagicMock()
        self.originalWorkflowService = controller._workflowService
        self.originalLlmService = controller._llmService
        controller.workflowService = self.mockWorkflowService
        controller.llmService = self.mockLlmService
        self.client = TestClient(app)
        self.workflow_payload = _load_json(_STRAIGHTFORWARD_WF_PATH)

    def teardown_method(self):
        controller._workflowService = self.originalWorkflowService
        controller._llmService = self.originalLlmService

    def _minimal_valid_body(self) -> dict[str, Any]:
        return {
            "workflowId": "straightforward",
            "conversation": [{"role": "agent", "message": "Hello."}],
            "maxAnswers": 1,
        }

    def test_workflow_not_found_404(self):
        self.mockWorkflowService.loadWorkflow.side_effect = FileNotFoundError("missing")
        r = self.client.post("/api/process", json=self._minimal_valid_body())
        assert r.status_code == 404
        assert r.json()["detail"] == "Workflow 'straightforward' not found"

    def test_llm_value_error_422(self):
        self.mockWorkflowService.loadWorkflow.return_value = self.workflow_payload
        self.mockLlmService.generateResponse.side_effect = ValueError(
            "Invalid LLM response format: unexpected token"
        )
        r = self.client.post("/api/process", json=self._minimal_valid_body())
        assert r.status_code == 422
        assert "Invalid LLM response format" in r.json()["detail"]

    def test_unexpected_exception_500(self):
        self.mockWorkflowService.loadWorkflow.return_value = self.workflow_payload
        self.mockLlmService.generateResponse.side_effect = RuntimeError("model offline")
        r = self.client.post("/api/process", json=self._minimal_valid_body())
        assert r.status_code == 500
        assert r.json()["detail"] == "model offline"

    def test_missing_workflow_id_validation_422(self):
        r = self.client.post(
            "/api/process",
            json={"conversation": [{"role": "user", "message": "Hi"}]},
        )
        assert r.status_code == 422

    def test_max_answers_below_one_validation_422(self):
        r = self.client.post(
            "/api/process",
            json={
                "workflowId": "straightforward",
                "conversation": [{"role": "agent", "message": "Hi."}],
                "maxAnswers": 0,
            },
        )
        assert r.status_code == 422
