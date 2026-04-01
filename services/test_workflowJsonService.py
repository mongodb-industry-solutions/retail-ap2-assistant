import json
import os
import tempfile

import pytest

from src.services.workflowJsonService import WorkflowJsonService


class TestWorkflowJsonService:
    """Tests for WorkflowJsonService (LOCAL provider)."""

    def setup_method(self):
        self.tempDir = tempfile.mkdtemp()
        self.sampleWorkflow = {
            "workflowId": "test_workflow",
            "description": "Test workflow.",
            "goals": ["Goal 1"],
            "policy": ["Policy 1"],
            "steps": [
                {"id": "step1", "description": "First step."},
                {"id": "step2", "description": "Second step."},
            ],
        }
        filePath = os.path.join(self.tempDir, "test_workflow.json")
        with open(filePath, "w", encoding="utf-8") as f:
            json.dump(self.sampleWorkflow, f)
        os.environ["WORKFLOW_DIR"] = self.tempDir

    def teardown_method(self):
        os.environ.pop("WORKFLOW_DIR", None)

    def test_loadWorkflowSuccess(self):
        service = WorkflowJsonService()
        result = service.loadWorkflow("test_workflow")
        assert result == self.sampleWorkflow

    def test_loadWorkflowNotFound(self):
        service = WorkflowJsonService()
        with pytest.raises(FileNotFoundError):
            service.loadWorkflow("nonexistent")

    def test_loadWorkflowHasCorrectStructure(self):
        service = WorkflowJsonService()
        result = service.loadWorkflow("test_workflow")
        assert "description" in result
        assert "goals" in result
        assert "policy" in result
        assert "steps" in result
        assert len(result["steps"]) == 2
        assert result["steps"][0]["id"] == "step1"

    def test_listWorkflowsReturnsSummaries(self):
        second = {"workflowId": "alpha", "description": "Alpha flow."}
        with open(
            os.path.join(self.tempDir, "alpha.json"), "w", encoding="utf-8"
        ) as f:
            json.dump(second, f)

        service = WorkflowJsonService()
        result = service.listWorkflows()
        assert len(result) == 2
        ids = [r["workflowId"] for r in result]
        assert "alpha" in ids
        assert "test_workflow" in ids
        for item in result:
            assert "description" in item

    def test_listWorkflowsEmptyDir(self):
        emptyDir = tempfile.mkdtemp()
        os.environ["WORKFLOW_DIR"] = emptyDir
        service = WorkflowJsonService()
        assert service.listWorkflows() == []

    def test_listWorkflowsMissingDir(self):
        os.environ["WORKFLOW_DIR"] = "/nonexistent/path"
        service = WorkflowJsonService()
        assert service.listWorkflows() == []
