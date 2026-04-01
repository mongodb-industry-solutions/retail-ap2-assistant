from pathlib import Path

import pytest

from src.services.modelDownloadService import ModelDownloadService

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class TestModelDownloadService:
    def test_getModelInfoKnownCatalogKey(self):
        service = ModelDownloadService(projectRoot=PROJECT_ROOT)
        repo, fname = service.getModelInfo("phi-2")
        assert repo
        assert fname.endswith(".gguf")

    def test_getModelInfoUnknownRaises(self):
        service = ModelDownloadService(projectRoot=PROJECT_ROOT)
        with pytest.raises(ValueError, match="Unknown catalog model"):
            service.getModelInfo("nonexistentCatalogKeyXyz")
