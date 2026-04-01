import os

from src.services.serviceFactory import ServiceFactory
from src.services.workflowJsonService import WorkflowJsonService
from src.services.workflowService import WorkflowService


class TestServiceFactory:
    """Tests for ServiceFactory DI resolution."""

    def test_getWorkflowServiceDefaultIsJson(self):
        os.environ.pop("WORKFLOW_PROVIDER", None)
        service = ServiceFactory.getWorkflowService()
        assert isinstance(service, WorkflowService)
        assert isinstance(service, WorkflowJsonService)

    def test_getWorkflowServiceJson(self):
        os.environ["WORKFLOW_PROVIDER"] = "JSON"
        service = ServiceFactory.getWorkflowService()
        assert isinstance(service, WorkflowJsonService)
        os.environ.pop("WORKFLOW_PROVIDER", None)
