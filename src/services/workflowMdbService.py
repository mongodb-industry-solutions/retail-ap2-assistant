import logging
import os

from pymongo import MongoClient

from src.services.workflowService import WorkflowService

logger = logging.getLogger(__name__)


class WorkflowMdbService(WorkflowService):
    """REMOTE provider: loads workflow definitions from a MongoDB collection."""

    def __init__(self):
        self.client = MongoClient(os.getenv("MDB_URI"))
        self.db = self.client[os.getenv("MDB_DATABASE_NAME")]
        self.collection = self.db[os.getenv("MDB_COLLECTION_NAME")]
        logger.info("WorkflowMdbService initialized with MongoDB connection")

    def loadWorkflow(self, workflowId: str) -> dict:
        logger.info("Loading workflow from MongoDB: %s", workflowId)
        workflow = self.collection.find_one({"workflowId": workflowId})
        if workflow is None:
            raise FileNotFoundError(f"Workflow '{workflowId}' not found in MongoDB")
        workflow.pop("_id", None)
        return workflow

    def listWorkflows(self) -> list[dict]:
        logger.info("Listing workflows from MongoDB: %s", self.collection.name)
        cursor = self.collection.find(
            {},
            {"_id": 0, "workflowId": 1, "description": 1},
        ).sort("workflowId", 1)
        return [
            {
                "workflowId": doc.get("workflowId", ""),
                "description": doc.get("description", ""),
            }
            for doc in cursor
        ]
