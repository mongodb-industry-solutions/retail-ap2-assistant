import logging

from fastapi import APIRouter, HTTPException

from src.models.workflow import (
    ProcessRequest,
    ProcessResponse,
    WorkflowSummary,
)
from src.services.llmService import LlmService
from src.services.serviceFactory import ServiceFactory
from src.services.workflowService import WorkflowService

logger = logging.getLogger(__name__)
router = APIRouter()


class WorkflowController:
    """Handles workflow processing API requests."""

    def __init__(
        self,
        workflowService: WorkflowService = None,
        llmService: LlmService = None,
    ):
        self._workflowService = workflowService
        self._llmService = llmService
        logger.info("WorkflowController initialized")

    @property
    def workflowService(self) -> WorkflowService:
        if self._workflowService is None:
            self._workflowService = ServiceFactory.getWorkflowService()
        return self._workflowService

    @workflowService.setter
    def workflowService(self, value: WorkflowService):
        self._workflowService = value

    @property
    def llmService(self) -> LlmService:
        if self._llmService is None:
            self._llmService = ServiceFactory.getLlmService()
        return self._llmService

    @llmService.setter
    def llmService(self, value: LlmService):
        self._llmService = value

    async def processWorkflow(self, request: ProcessRequest) -> ProcessResponse:
        logger.info(f"Processing workflow: {request.workflowId}")
        try:
            workflowContext = self.workflowService.loadWorkflow(request.workflowId)
            # Transforming objects to dictionaries for LLM processing, excluding None fields
            conversationDicts = [
                msg.model_dump(exclude_none=True) for msg in request.conversation
            ]
            stepId, answers, llmError = self.llmService.generateResponse(
                {
                    "workflow": workflowContext,
                    "conversation": conversationDicts,
                    "maxAnswers": request.maxAnswers,
                }
            )
            return ProcessResponse(
                workflowId=request.workflowId,
                stepId=stepId or "",
                answers=list(answers or []),
                error=llmError,
            )
        except FileNotFoundError:
            raise HTTPException(
                status_code=404, detail=f"Workflow '{request.workflowId}' not found"
            ) from None
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e
        except Exception as e:
            logger.error(f"Error processing workflow: {e}")
            raise HTTPException(status_code=500, detail=str(e)) from e


    async def listWorkflows(self) -> list[WorkflowSummary]:
        try:
            items = self.workflowService.listWorkflows()
            return [WorkflowSummary(**item) for item in items]
        except Exception as e:
            logger.error("Error listing workflows: %s", e)
            raise HTTPException(status_code=500, detail=str(e)) from e


controller = WorkflowController()


@router.get("/api/workflows", response_model=list[WorkflowSummary])
async def listWorkflows():
    return await controller.listWorkflows()


@router.post("/api/process", response_model=ProcessResponse)
async def processWorkflow(request: ProcessRequest):
    return await controller.processWorkflow(request)
