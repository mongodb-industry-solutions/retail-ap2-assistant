import logging
import os

from google import genai
from google.genai import types

from src.services.llmService import LlmService

logger = logging.getLogger(__name__)


class LlmVertexAiService(LlmService):
    """VERTEXAI provider: direct ``google-genai`` SDK (no LangChain wrapper).

    Uses ``genai.Client`` and ``client.models.generate_content()`` with
    ``response_mime_type="application/json"`` so the model is forced to
    return valid JSON — no markdown fences, no extra text.

    Auth modes (auto-detected, same env vars as REMOTE):

    * **API key** — ``GOOGLE_API_KEY`` is set.
    * **Vertex AI** — ``GOOGLE_CLOUD_PROJECT`` is set (uses ADC).
    """

    defaultModel = "gemini-2.5-flash"

    def __init__(self):
        self.modelId = os.getenv("GOOGLE_MODEL_ID", self.defaultModel)
        apiKey = os.getenv("GOOGLE_API_KEY", "").strip() or None
        project = os.getenv("GOOGLE_CLOUD_PROJECT", "").strip() or None
        self.location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

        if apiKey:
            self.authMode = "apiKey"
            self.project = None
            self.client = genai.Client(api_key=apiKey)
            logger.info(
                "LlmVertexAiService initialized (API key, model=%s)",
                self.modelId,
            )
        elif project:
            self.authMode = "vertexAi"
            self.project = project
            self.client = genai.Client(
                vertexai=True,
                project=project,
                location=self.location,
            )
            logger.info(
                "LlmVertexAiService initialized (Vertex AI, model=%s, "
                "project=%s, location=%s)",
                self.modelId,
                project,
                self.location,
            )
        else:
            raise ValueError(
                "VERTEXAI provider requires GOOGLE_API_KEY or "
                "GOOGLE_CLOUD_PROJECT. Set one in cfg/.env."
            )

        self.llm = None

    def generateResponse(self, context: dict) -> tuple:
        """Call google-genai SDK directly with JSON-enforced output."""
        early = self._validateContext(context)
        if early is not None:
            return early

        maxAnswers = context.get("maxAnswers", 2)
        prompt = self._buildPrompt(context)
        logger.info(self._invokeLogMessage())

        try:
            response = self.client.models.generate_content(
                model=self.modelId,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )
            text = response.text or ""
        except Exception as exc:
            logger.error("google-genai SDK error: %s", exc)
            return "", [], f"LLM request failed: {exc}"

        return self._parseModelOutput(text, maxAnswers)

    def startupInfo(self) -> dict:
        info = super().startupInfo()
        info["provider"] = "VERTEXAI"
        info["modelId"] = self.modelId
        info["authMode"] = self.authMode
        info["sdk"] = "google-genai (direct)"
        info["jsonEnforced"] = True
        info["location"] = self.location
        if self.project:
            info["project"] = self.project
        return info

    def _invokeLogMessage(self) -> str:
        return "Sending request via google-genai SDK (Gemini)"
