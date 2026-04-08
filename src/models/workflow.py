from pydantic import BaseModel, Field
from typing import Dict, Any


class ConversationMessage(BaseModel):
    role: str
    message: str
    step: str | None = None


class ProcessRequest(BaseModel):
    workflowId: str
    conversation: list[ConversationMessage]
    maxAnswers: int = Field(default=2, ge=1)
    paymentDocument: Dict[str, Any] | None = None


class ProcessResponse(BaseModel):
    workflowId: str
    stepId: str = ""
    answers: list[str] = Field(default_factory=list)
    error: str | None = None


class WorkflowSummary(BaseModel):
    workflowId: str
    description: str = ""
