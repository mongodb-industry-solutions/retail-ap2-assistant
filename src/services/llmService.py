import json
import logging
import os
from abc import ABC, abstractmethod

from src.services.helpers import (
    WorkflowPromptParts,
    coerceLlmContentToStr,
    parse_workflow_llm_response,
)

logger = logging.getLogger(__name__)


class LlmService(ABC):
    """LLM workflow assistant: shared prompt, parsing, and invoke orchestration.

    Subclasses set ``self.llm`` (LangChain runnable with ``.invoke``) and implement
    :meth:`_invokeLogMessage`. Override :meth:`_wrapPrompt` for instruction
    formats (e.g. Mistral ``[INST]`` … ``[/INST]``).

    Prompt env: ``LLM_PROMPT_FORMAT`` = ``text`` (default) or ``json`` (case-insensitive).
    """

    envPromptFormat = "LLM_PROMPT_FORMAT"
    defaultPromptFormat = "text"

    outputRulesText = (
        "You MUST output exactly one JSON object. Do not add markdown, comments, "
        "or any text before or after the JSON.\n"
        'On success: {"stepId":"<id from workflow steps>","answers":["...", ...]} — '
        "answers must contain exactly maxAnswers strings. Each answer is a short, "
        "natural message that the USER (buyer/customer) would send back to the AGENT "
        "in response to the agent's latest message. They are NOT agent messages. "
        "Write them in first person from the user's point of view.\n"
        'On failure: {"error":"<short user-visible message in the conversation language>"} '
        "(omit or null stepId/answers).\n"
        "Do not output Python, scripts, unit tests, or markdown code fences. "
        "Escape double quotes inside JSON strings."
    )

    exampleSuccessJson = (
        '{"stepId":"merchant-agent-introduction","answers":['
        '"Yes, please proceed with those details."]}'
    )

    def _outputRulesAndExample(self) -> str:
        return (
            self.outputRulesText
            + "\n\nExample success: "
            + self.exampleSuccessJson
        )

    def _instructionForJsonPayload(self, maxAnswers: int) -> str:
        """Full instruction string embedded in the JSON prompt (self-contained for the model)."""
        return (
            "You are a conversational assistant analyzing a workflow-driven dialogue.\n\n"
            "Role clarification:\n"
            "- 'user' is the buyer/customer who wants to make a purchase.\n"
            "- 'agent' is the shopping assistant who guides the user through the process.\n"
            "- The last message in the conversation is always from the agent.\n\n"
            "The workflow object contains description, goals, policies, and steps "
            "(each step has id and description). The conversation array is the message history "
            "(role user or agent, message text). Root-level keys in this prompt JSON use camelCase "
            "(e.g. maxAnswers).\n\n"
            "Tasks:\n"
            "1) Determine the current active step: choose stepId from workflow.steps[].id that "
            "best matches the latest agent message given the full conversation and policies.\n"
            f"2) Generate exactly {maxAnswers} suggested replies that the USER (buyer) would "
            "send back to the agent. These must be written from the user's perspective "
            "(first person), be coherent responses to the agent's latest message, and "
            "advance the workflow toward the next step.\n\n"
            + self._outputRulesAndExample()
        )

    def generateResponse(self, context: dict) -> tuple:
        """Return ``(stepId, answers, error)``; see subclass docstrings."""
        early = self._validateContext(context)
        if early is not None:
            return early

        maxAnswers = context.get("maxAnswers", 2)
        prompt = self._buildPrompt(context)
        logger.info(self._invokeLogMessage())
        response = self.llm.invoke(prompt)
        raw = response.content if hasattr(response, "content") else response
        text = coerceLlmContentToStr(raw)
        return self._parseModelOutput(text, maxAnswers)

    def _validateContext(self, context: dict) -> tuple[str, list[str], str] | None:
        workflow = context.get("workflow")
        conversation = context.get("conversation")
        maxAnswers = context.get("maxAnswers", 2)
        if not isinstance(workflow, dict):
            return "", [], "Invalid assistant context: workflow is missing."
        if not isinstance(conversation, list):
            return "", [], "Invalid assistant context: conversation is missing."
        if not isinstance(maxAnswers, int) or maxAnswers < 1:
            return (
                "",
                [],
                "Invalid assistant context: maxAnswers must be a positive integer.",
            )
        return None

    def _buildPrompt(self, context: dict) -> str:
        core = self._buildPromptCore(context)
        return self._wrapPrompt(core)

    def _wrapPrompt(self, core: str) -> str:
        return core

    def _promptFormat(self) -> str:
        raw = (
            os.getenv(self.envPromptFormat, self.defaultPromptFormat)
            .strip()
            .lower()
        )
        return "json" if raw == "json" else "text"

    def _buildPromptCore(self, context: dict) -> str:
        fmt = self._promptFormat()
        if fmt == "json":
            return self._buildPromptCoreJson(context)
        return self._buildPromptCoreText(context)

    def _workflowPayload(self, workflow: dict) -> dict:
        goals = workflow.get("goals")
        steps = workflow.get("steps")
        return {
            "description": WorkflowPromptParts.description(workflow),
            "goals": goals if isinstance(goals, list) else [],
            "policies": WorkflowPromptParts.policy_items(workflow),
            "steps": self._normalizeSteps(steps),
        }

    def _normalizeSteps(self, steps: object) -> list[dict[str, str]]:
        if not isinstance(steps, list):
            return []
        out: list[dict[str, str]] = []
        for s in steps:
            if not isinstance(s, dict):
                continue
            sid = s.get("id", "")
            desc = s.get("description", "")
            out.append(
                {
                    "id": sid if isinstance(sid, str) else str(sid),
                    "description": desc if isinstance(desc, str) else str(desc),
                }
            )
        return out

    def _conversationPayload(self, conversation: list) -> list[dict]:
        out: list[dict] = []
        for m in conversation:
            if not isinstance(m, dict):
                continue
            item: dict = {
                "role": m.get("role", ""),
                "message": m.get("message", "")
                if isinstance(m.get("message"), str)
                else str(m.get("message", "")),
            }
            if m.get("step") is not None:
                item["step"] = m["step"]
            out.append(item)
        return out

    def _buildPromptCoreJson(self, context: dict) -> str:
        workflow = context["workflow"]
        conversation = context["conversation"]
        maxAnswers = context.get("maxAnswers", 2)
        if not isinstance(maxAnswers, int) or maxAnswers < 1:
            maxAnswers = 2

        payload = {
            "instruction": self._instructionForJsonPayload(maxAnswers),
            "workflow": self._workflowPayload(workflow),
            "conversation": self._conversationPayload(conversation),
            "maxAnswers": maxAnswers,
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    def _buildPromptCoreText(self, context: dict) -> str:
        workflow = context["workflow"]
        conversation = context["conversation"]
        maxAnswers = context.get("maxAnswers", 2)
        if not isinstance(maxAnswers, int) or maxAnswers < 1:
            maxAnswers = 2

        stepsText = "\n".join(WorkflowPromptParts.bullet_lines(workflow, "steps"))
        goalsText = "\n".join(WorkflowPromptParts.bullet_lines(workflow, "goals"))
        policyText = "\n".join(WorkflowPromptParts.bullet_lines(workflow, "policies"))
        conversationText = "\n".join(
            WorkflowPromptParts.conversation_lines(conversation)
        )
        description = WorkflowPromptParts.description(workflow)

        return (
            "You are a conversational assistant analyzing a workflow.\n\n"
            "Role clarification:\n"
            "- 'user' is the buyer/customer who wants to make a purchase.\n"
            "- 'agent' is the shopping assistant who guides the user through the process.\n"
            "- The last message in the conversation is always from the agent.\n\n"
            f"Workflow: {description}\n\n"
            f"Goals:\n{goalsText}\n\n"
            f"Policies:\n{policyText}\n\n"
            f"Steps:\n{stepsText}\n\n"
            f"Conversation so far:\n{conversationText}\n\n"
            "Based on the conversation, determine:\n"
            "1. The current active step ID from the workflow steps.\n"
            f"2. Generate exactly {maxAnswers} suggested replies that the USER (buyer) "
            "would send back to the agent. Write them from the user's perspective "
            "(first person), as coherent responses to the agent's latest message, "
            "advancing the workflow toward the next step.\n\n"
            + self._outputRulesAndExample()
        )

    def _parseModelOutput(
        self, text: str, maxAnswers: int
    ) -> tuple[str, list[str], str | None]:
        return parse_workflow_llm_response(text, maxAnswers)

    def startupInfo(self) -> dict:
        """Non-sensitive configuration summary; subclasses extend with provider details."""
        return {"promptFormat": self._promptFormat()}

    @abstractmethod
    def _invokeLogMessage(self) -> str:
        """Log line when sending a prompt to the provider-specific model."""
