from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from src.controllers.workflowController import controller
from src.main import app


class TestWorkflowController:
    """Tests for WorkflowController with mocked services."""

    def setup_method(self):
        self.mockWorkflowService = MagicMock()
        self.mockLlmService = MagicMock()
        self.originalWorkflowService = controller._workflowService
        self.originalLlmService = controller._llmService
        controller.workflowService = self.mockWorkflowService
        controller.llmService = self.mockLlmService
        self.client = TestClient(app)

    def teardown_method(self):
        controller._workflowService = self.originalWorkflowService
        controller._llmService = self.originalLlmService

    def test_processWorkflowSuccess(self):
        self.mockWorkflowService.loadWorkflow.return_value = {
            "description": "Test workflow.",
            "goals": ["Goal 1"],
            "policy": ["Policy 1"],
            "steps": [
                {"id": "step1", "description": "First step."},
                {"id": "step2", "description": "Second step."},
            ],
        }
        self.mockLlmService.generateResponse.return_value = (
            "step1",
            ["Answer 1", "Answer 2"],
            None,
        )

        response = self.client.post(
            "/api/process",
            json={
                "workflowId": "test_workflow",
                "conversation": [
                    {"role": "user", "message": "Hello"},
                ],
                "maxAnswers": 2,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["workflowId"] == "test_workflow"
        assert data["stepId"] == "step1"
        assert len(data["answers"]) == 2
        assert data.get("error") is None

    def test_processWorkflowLlmUserVisibleErrorReturns200(self):
        self.mockWorkflowService.loadWorkflow.return_value = {
            "description": "Test workflow.",
            "goals": ["Goal 1"],
            "policy": ["Policy 1"],
            "steps": [
                {"id": "step1", "description": "First step."},
            ],
        }
        self.mockLlmService.generateResponse.return_value = (
            "",
            [],
            "No pude entender el último mensaje. Reformula tu pregunta.",
        )
        response = self.client.post(
            "/api/process",
            json={
                "workflowId": "test_workflow",
                "conversation": [{"role": "agent", "message": "Hello."}],
                "maxAnswers": 1,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["stepId"] == ""
        assert data["answers"] == []
        assert (
            data["error"]
            == "No pude entender el último mensaje. Reformula tu pregunta."
        )

    def test_processWorkflowNotFound(self):
        self.mockWorkflowService.loadWorkflow.side_effect = FileNotFoundError(
            "Workflow 'missing' not found"
        )

        response = self.client.post(
            "/api/process",
            json={
                "workflowId": "missing",
                "conversation": [
                    {"role": "user", "message": "Hello"},
                ],
            },
        )

        assert response.status_code == 404

    def test_processWorkflowInvalidRequest(self):
        response = self.client.post(
            "/api/process",
            json={
                "conversation": [
                    {"role": "user", "message": "Hello"},
                ],
            },
        )

        assert response.status_code == 422

    def test_healthEndpoint(self):
        response = self.client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_listWorkflowsReturnsArray(self):
        self.mockWorkflowService.listWorkflows.return_value = [
            {"workflowId": "wf-a", "description": "First."},
            {"workflowId": "wf-b", "description": "Second."},
        ]
        response = self.client.get("/api/workflows")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["workflowId"] == "wf-a"
        assert data[1]["description"] == "Second."

    def test_listWorkflowsEmptyCollection(self):
        self.mockWorkflowService.listWorkflows.return_value = []
        response = self.client.get("/api/workflows")
        assert response.status_code == 200
        assert response.json() == []

    def test_rootRedirectsToDocs(self):
        response = self.client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers.get("location") == "/docs"
