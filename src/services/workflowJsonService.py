import json
import logging
import os
from pathlib import Path

from src.services.workflowService import WorkflowService

logger = logging.getLogger(__name__)


class WorkflowJsonService(WorkflowService):
    """LOCAL provider: loads workflow definitions from JSON files in cfg/workflows/."""

    def __init__(self):
        self.workflowDir = os.getenv("WORKFLOW_DIR", "cfg/workflows")
        logger.info(
            "WorkflowJsonService initialized with directory: %s", self.workflowDir
        )

    def loadWorkflow(self, workflowId: str) -> dict:
        filePath = os.path.join(self.workflowDir, f"{workflowId}.json")
        logger.info("Loading workflow from: %s", filePath)
        try:
            with open(filePath, encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Workflow '{workflowId}' not found"
            ) from None

    def listWorkflows(self) -> list[dict]:
        logger.info("Listing workflows from directory: %s", self.workflowDir)
        dirPath = Path(self.workflowDir)
        if not dirPath.is_dir():
            return []
        summaries: list[dict] = []
        for fp in sorted(dirPath.glob("*.json")):
            try:
                with open(fp, encoding="utf-8") as f:
                    data = json.load(f)
                summaries.append({
                    "workflowId": data.get("workflowId", fp.stem),
                    "description": data.get("description", ""),
                })
            except Exception:
                logger.warning("Skipping unreadable workflow file: %s", fp.name)
        return summaries
