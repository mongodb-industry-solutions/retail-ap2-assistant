from abc import ABC, abstractmethod


class WorkflowService(ABC):
    """Abstract interface for workflow loading and listing."""

    @abstractmethod
    def loadWorkflow(self, workflowId: str) -> dict:
        """Load and return a workflow definition by its ID."""

    @abstractmethod
    def listWorkflows(self) -> list[dict]:
        """Return lightweight summaries of all available workflows.

        Each item: ``{"workflowId": str, "description": str}``.
        """
