import json
import logging
import re
from collections.abc import Callable
from typing import Any, Literal

logger = logging.getLogger(__name__)

DEFAULT_LLM_PARSE_ERROR = (
    "The assistant could not produce a valid structured response. Please try again."
)

# Reject model output that looks like code / tests instead of short user replies (common with small LLMs).
_MAX_STEP_ID_LEN = 96
_MAX_ANSWER_LINE_LEN = 520
_MAX_ANSWERS_COMBINED_LEN = 4000
_STEP_ID_PATTERN = re.compile(r"^[a-zA-Z][a-zA-Z0-9_-]*$")
_GARBAGE_MARKERS = (
    "import json",
    "import sys",
    "__main__",
    "pathlib",
    "sys.path",
    "unit test",
    "workflow.json",
    "extract_steps",
    "get_active_step",
    "logic_functions",
    "```",
    "\ndef ",
    "\nclass ",
)


def _llm_json_payload_sanity_fail(step_id: str, answers: list[str]) -> bool:
    """True if ``step_id`` / ``answers`` are implausible for this API (e.g. Python dump)."""
    if len(step_id) > _MAX_STEP_ID_LEN or not _STEP_ID_PATTERN.fullmatch(step_id):
        return True
    combined = 0
    for a in answers:
        if len(a) > _MAX_ANSWER_LINE_LEN:
            return True
        combined += len(a)
        lower = a.lower()
        for needle in _GARBAGE_MARKERS:
            if needle in lower or needle in a:
                return True
    if combined > _MAX_ANSWERS_COMBINED_LEN:
        return True
    return False


class WorkflowPromptParts:
    """Validated excerpts from workflow / conversation JSON for LLM system prompts."""

    _BULLET = "  - "

    @classmethod
    def policy_items(cls, workflow: dict) -> list:
        """``policies`` list if present and a list, else ``policy``; otherwise []."""
        for key in ("policies", "policy"):
            v = workflow.get(key)
            if isinstance(v, list):
                return v
        return []

    @classmethod
    def description(cls, workflow: dict) -> str:
        d = workflow.get("description")
        if isinstance(d, str) and d.strip():
            return d.strip()
        return "(no workflow description)"

    @classmethod
    def bullet_lines(
        cls,
        workflow: dict,
        part: Literal["goals", "steps", "policies"],
    ) -> list[str]:
        """One workflow list field → bullet lines; ``part`` selects key(s) and row shape."""
        if part == "goals":
            return cls._to_bullets(workflow.get("goals"), "(none)", cls._fmt_scalar)
        if part == "steps":
            return cls._to_bullets(
                workflow.get("steps"), "(no steps defined)", cls._fmt_step
            )
        return cls._to_bullets(cls.policy_items(workflow), "(none)", cls._fmt_scalar)

    @classmethod
    def conversation_lines(cls, conversation: Any) -> list[str]:
        if not isinstance(conversation, list):
            return ["  (invalid conversation format)"]
        if not conversation:
            return ["  (empty)"]
        lines: list[str] = []
        for m in conversation:
            if not isinstance(m, dict):
                lines.append(f"  ?: {m!r}")
                continue
            role = m.get("role", "?")
            msg = m.get("message", "")
            if not isinstance(msg, str):
                msg = str(msg)
            lines.append(f"  {role}: {msg}")
        return lines

    @staticmethod
    def _fmt_scalar(item: Any) -> str | None:
        if item is None:
            return None
        return str(item)

    @staticmethod
    def _fmt_step(item: Any) -> str | None:
        if not isinstance(item, dict):
            return None
        return f"{item.get('id', '?')}: {item.get('description', '')}"

    @classmethod
    def _to_bullets(
        cls,
        items: Any,
        empty_suffix: str,
        fmt: Callable[[Any], str | None],
    ) -> list[str]:
        empty_line = f"{cls._BULLET}{empty_suffix}"
        if not isinstance(items, list):
            return [empty_line]
        lines: list[str] = []
        for item in items:
            text = fmt(item)
            if text is not None:
                lines.append(f"{cls._BULLET}{text}")
        return lines if lines else [empty_line]


def _strip_code_fence(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        rest = cleaned.split("\n", 1)
        cleaned = rest[1] if len(rest) > 1 else cleaned[3:]
        cleaned = cleaned.rsplit("```", 1)[0]
    return cleaned.strip()


def _extract_json_object_dict(text: str) -> dict | None:
    cleaned = _strip_code_fence(text)
    if not cleaned:
        return None
    try:
        val = json.loads(cleaned)
        return val if isinstance(val, dict) else None
    except json.JSONDecodeError:
        pass
    start = cleaned.find("{")
    if start < 0:
        return None
    decoder = json.JSONDecoder()
    try:
        val, _ = decoder.raw_decode(cleaned, start)
        return val if isinstance(val, dict) else None
    except json.JSONDecodeError:
        return None


def parse_workflow_llm_response(
    content: str, max_answers: int
) -> tuple[str, list[str], str | None]:
    """
    Parse LLM output into ``(step_id, answers, error)``.

    Success: ``error`` is ``None``. The model may report a user-visible problem
    with ``{"error": "..."}``. If JSON is missing or invalid, returns a generic
    ``error`` string instead of raising.
    """
    raw = content if isinstance(content, str) else str(content)
    cleaned = _strip_code_fence(raw)
    if not cleaned:
        logger.warning("LLM output empty after strip")
        return "", [], DEFAULT_LLM_PARSE_ERROR

    data = _extract_json_object_dict(raw)
    if data is None:
        snippet = cleaned[:120].replace("\n", " ")
        logger.warning("LLM output not parseable as JSON object: %s...", snippet)
        return "", [], DEFAULT_LLM_PARSE_ERROR

    err_val = data.get("error")
    if err_val is not None:
        err_str = str(err_val).strip()
        if err_str:
            return "", [], err_str

    step_id = data.get("stepId")
    answers = data.get("answers")
    if not isinstance(step_id, str) or not step_id.strip():
        logger.warning("LLM JSON missing non-empty stepId")
        return "", [], DEFAULT_LLM_PARSE_ERROR
    if not isinstance(answers, list):
        logger.warning("LLM JSON answers is not a list")
        return "", [], DEFAULT_LLM_PARSE_ERROR

    str_answers: list[str] = []
    for a in answers:
        if a is None:
            continue
        str_answers.append(str(a).strip() if isinstance(a, str) else str(a))
    str_answers = str_answers[:max_answers]
    if len(str_answers) < max_answers:
        logger.warning(
            "LLM returned %d answers, expected at least %d",
            len(str_answers),
            max_answers,
        )
        return "", [], DEFAULT_LLM_PARSE_ERROR

    sid = step_id.strip()
    if _llm_json_payload_sanity_fail(sid, str_answers):
        logger.warning(
            "LLM JSON failed sanity check (likely code or noise, not user replies)"
        )
        return "", [], DEFAULT_LLM_PARSE_ERROR

    return sid, str_answers, None


def coerceLlmContentToStr(content: Any) -> str:
    """Turn chat-model output content into a single string (LC 1.x / Gemini may use list parts)."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if text is not None:
                    parts.append(str(text))
                else:
                    parts.append(str(item))
            else:
                parts.append(str(item))
        return "".join(parts)
    return str(content)


class ResponseParser:
    """Utility class for parsing LLM JSON responses."""

    @staticmethod
    def parseJson(content: str, maxAnswers: int) -> tuple:
        """Parse a JSON string from LLM output and return (stepId, answers)."""
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
            cleaned = cleaned.rsplit("```", 1)[0]
        try:
            data = json.loads(cleaned)
            stepId = data["stepId"]
            answers = data["answers"][:maxAnswers]
            return stepId, answers
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse LLM response: {e}")
            raise ValueError(f"Invalid LLM response format: {e}") from e
