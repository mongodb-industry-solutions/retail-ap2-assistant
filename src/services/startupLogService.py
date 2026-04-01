import logging
import os

from src.services.serviceFactory import ServiceFactory

logger = logging.getLogger(__name__)


class StartupLogService:
    """Logs a non-sensitive configuration summary and eagerly initialises services."""

    def logStartupConfig(self, controller) -> None:
        """Build the banner, create services, and emit context-window advisory."""
        workflowProvider = os.getenv("WORKFLOW_PROVIDER", "JSON")
        llmProvider = os.getenv("LLM_PROVIDER", "LOCAL")

        lines = ["", "========== Startup Configuration =========="]

        lines.append(f"  Workflow provider : {workflowProvider}")
        if workflowProvider.upper() == "MDB":
            lines.append(
                f"  Database          : {os.getenv('MDB_DATABASE_NAME', 'n/a')}"
            )
            lines.append(
                f"  Collection        : {os.getenv('MDB_COLLECTION_NAME', 'n/a')}"
            )
        else:
            lines.append(
                f"  Workflow directory: {os.getenv('WORKFLOW_DIR', 'cfg/workflows')}"
            )

        lines.append(f"  LLM provider      : {llmProvider}")

        llmInfo = self._initLlmService(controller)
        self._initWorkflowService(controller)

        promptFormat = llmInfo.get(
            "promptFormat", os.getenv("LLM_PROMPT_FORMAT", "text")
        )
        lines.append(f"  Prompt format     : {promptFormat}")

        if llmProvider.upper() == "LOCAL":
            self._appendLocalInfo(lines, llmInfo)
        else:
            self._appendRemoteInfo(lines, llmInfo, llmProvider)

        lines.append("============================================")
        logger.info("\n".join(lines))

        self._logContextWindowAdvisory(llmProvider, llmInfo)

    def _initLlmService(self, controller) -> dict:
        try:
            llmService = ServiceFactory.getLlmService()
            controller.llmService = llmService
            return llmService.startupInfo()
        except Exception as exc:
            logger.warning("Could not initialise LLM service at startup: %s", exc)
            return {}

    def _initWorkflowService(self, controller) -> None:
        try:
            wfService = ServiceFactory.getWorkflowService()
            controller.workflowService = wfService
        except Exception as exc:
            logger.warning(
                "Could not initialise workflow service at startup: %s", exc
            )

    def _appendLocalInfo(self, lines: list[str], llmInfo: dict) -> None:
        modelPath = llmInfo.get(
            "modelPath", os.getenv("LLM_LOCAL_MODEL_PATH", "n/a")
        )
        lines.append(f"  Model             : {modelPath}")

        nCtx = llmInfo.get("nCtx")
        nCtxTrain = llmInfo.get("nCtxTrain")
        if nCtx and nCtxTrain:
            lines.append(
                f"  Context window    : {nCtx} tokens (training: {nCtxTrain})"
            )
        elif nCtx:
            lines.append(f"  Context window    : {nCtx} tokens")
        else:
            envCtx = os.getenv("LLM_LOCAL_MODEL_N_CTX")
            if envCtx:
                lines.append(f"  Context window    : {envCtx} tokens")

        nThreads = llmInfo.get(
            "nThreads", os.getenv("LLM_LOCAL_MODEL_N_THREADS", "n/a")
        )
        temperature = llmInfo.get(
            "temperature", os.getenv("LLM_LOCAL_MODEL_TEMPERATURE", "n/a")
        )
        lines.append(f"  Threads           : {nThreads}")
        lines.append(f"  Temperature       : {temperature}")

    def _appendRemoteInfo(
        self, lines: list[str], llmInfo: dict, llmProvider: str = ""
    ) -> None:
        modelId = llmInfo.get("modelId", os.getenv("GOOGLE_MODEL_ID", "n/a"))
        lines.append(f"  Model             : {modelId}")
        sdk = llmInfo.get("sdk")
        if sdk:
            lines.append(f"  SDK               : {sdk}")
        authMode = llmInfo.get("authMode", "n/a")
        lines.append(f"  Auth mode         : {authMode}")
        if llmInfo.get("jsonEnforced"):
            lines.append("  JSON enforced     : yes (response_mime_type)")
        project = llmInfo.get("project", os.getenv("GOOGLE_CLOUD_PROJECT"))
        if project:
            lines.append(f"  GCP project       : {project}")
        location = llmInfo.get(
            "location", os.getenv("GOOGLE_CLOUD_LOCATION", "n/a")
        )
        lines.append(f"  GCP location      : {location}")

    def _logContextWindowAdvisory(self, llmProvider: str, llmInfo: dict) -> None:
        if llmProvider.upper() != "LOCAL":
            return
        nCtx = llmInfo.get("nCtx")
        nCtxTrain = llmInfo.get("nCtxTrain")
        if not nCtx or not nCtxTrain:
            return
        if nCtx > nCtxTrain:
            logger.warning(
                "Context window n_ctx (%d) exceeds model training context (%d). "
                "Prompts near the limit may produce degraded output.",
                nCtx,
                nCtxTrain,
            )
        else:
            logger.info(
                "Context window n_ctx (%d) within model training context (%d).",
                nCtx,
                nCtxTrain,
            )
