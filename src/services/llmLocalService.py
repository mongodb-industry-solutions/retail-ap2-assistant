import logging
import os

from src.services.llmService import LlmService

logger = logging.getLogger(__name__)


class LlmLocalService(LlmService):
    """LOCAL provider: GGUF model loaded via llama-cpp-python + LangChain."""

    def __init__(self):
        from langchain_community.llms import LlamaCpp

        self.modelPath = os.getenv(
            "LLM_LOCAL_MODEL_PATH", "models/mistral-7b-instruct-v0.2.Q4_K_M.gguf"
        )
        self.nCtx = int(os.getenv("LLM_LOCAL_MODEL_N_CTX", "4096"))
        self.nThreads = int(os.getenv("LLM_LOCAL_MODEL_N_THREADS", "4"))
        self.temperature = float(os.getenv("LLM_LOCAL_MODEL_TEMPERATURE", "0.25"))

        self.llm = LlamaCpp(
            model_path=self.modelPath,
            n_ctx=self.nCtx,
            n_threads=self.nThreads,
            temperature=self.temperature,
            verbose=False,
        )
        logger.info("LlmLocalService initialized with model: %s", self.modelPath)

    def startupInfo(self) -> dict:
        info = super().startupInfo()
        info["provider"] = "LOCAL"
        info["modelPath"] = self.modelPath
        info["nCtx"] = self.nCtx
        info["nThreads"] = self.nThreads
        info["temperature"] = self.temperature

        try:
            nCtxTrain = self.llm.client.n_ctx_train()
            info["nCtxTrain"] = nCtxTrain
        except Exception:
            pass

        return info

    def _invokeLogMessage(self) -> str:
        return "Sending request to local LLM"

    def _wrapPrompt(self, core: str) -> str:
        return f"[INST]{core}[/INST]"
