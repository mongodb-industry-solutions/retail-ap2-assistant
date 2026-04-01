import logging
import os

from langchain_google_genai import ChatGoogleGenerativeAI

from src.services.llmService import LlmService

logger = logging.getLogger(__name__)


class LlmRemoteService(LlmService):
    """REMOTE provider: Gemini via LangChain ``ChatGoogleGenerativeAI``.

    Two mutually exclusive auth modes (auto-detected from env vars):

    * **API key** — ``GOOGLE_API_KEY`` is set and
      ``GOOGLE_GENAI_USE_VERTEXAI`` is NOT explicitly ``true``.
    * **Vertex AI** — ``GOOGLE_GENAI_USE_VERTEXAI=true`` +
      ``GOOGLE_CLOUD_PROJECT``.  Requires Application Default Credentials
      (``gcloud auth application-default login``).

    The service explicitly sets ``GOOGLE_GENAI_USE_VERTEXAI`` in the process
    environment to match the detected mode so the underlying ``google-genai``
    SDK does not contradict the intended configuration.
    """

    defaultModel = "gemini-2.5-flash"

    def __init__(self):
        self.modelId = os.getenv("GOOGLE_MODEL_ID", self.defaultModel)

        vertexAiExplicit = (
            os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").strip().lower()
            in ("true", "1", "yes")
        )
        apiKey = os.getenv("GOOGLE_API_KEY", "").strip() or None
        project = os.getenv("GOOGLE_CLOUD_PROJECT", "").strip() or None
        location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")

        if vertexAiExplicit and apiKey:
            logger.warning(
                "Both GOOGLE_GENAI_USE_VERTEXAI=true and GOOGLE_API_KEY are set. "
                "Vertex AI takes precedence; API key is ignored."
            )

        if vertexAiExplicit:
            self._initVertexAi(project, location)
        elif apiKey:
            self._initApiKey(apiKey, location)
        else:
            self._initFallback(project, location)

    def _initVertexAi(self, project: str | None, location: str) -> None:
        self.authMode = "vertexAi"
        self.project = project
        self.location = location
        if not project:
            logger.warning(
                "GOOGLE_GENAI_USE_VERTEXAI=true but GOOGLE_CLOUD_PROJECT is "
                "not set. Vertex AI requires a project ID."
            )
        os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "true"
        self.llm = ChatGoogleGenerativeAI(
            model=self.modelId,
            project=project,
            location=location,
        )
        logger.info(
            "LlmRemoteService initialized (Vertex AI, model=%s, "
            "project=%s, location=%s)",
            self.modelId,
            project,
            location,
        )

    def _initApiKey(self, apiKey: str, location: str) -> None:
        self.authMode = "apiKey"
        self.project = None
        self.location = location
        os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "false"
        self.llm = ChatGoogleGenerativeAI(
            model=self.modelId,
            google_api_key=apiKey,
        )
        logger.info(
            "LlmRemoteService initialized (API key, model=%s)",
            self.modelId,
        )

    def _initFallback(self, project: str | None, location: str) -> None:
        self.authMode = "adc"
        self.project = project
        self.location = location
        self.llm = ChatGoogleGenerativeAI(model=self.modelId)
        logger.warning(
            "LlmRemoteService initialized without explicit credentials "
            "(model=%s). Falling back to Application Default Credentials.",
            self.modelId,
        )

    def startupInfo(self) -> dict:
        info = super().startupInfo()
        info["provider"] = "REMOTE"
        info["modelId"] = self.modelId
        info["authMode"] = self.authMode
        info["location"] = self.location
        if self.project:
            info["project"] = self.project
        return info

    def _invokeLogMessage(self) -> str:
        return "Sending request to Google Generative AI (Gemini)"
