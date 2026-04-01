"""Service: catalog-backed Hugging Face GGUF downloads into models/."""

import json
import logging
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlretrieve

logger = logging.getLogger(__name__)

HF_BASE_URL = "https://huggingface.co"
MODEL_EXTENSIONS = frozenset({".gguf", ".bin"})


class ModelDownloadService:
    """Download, list, and remove local LLM model files (GGUF / bin) from Hugging Face."""

    def __init__(self, projectRoot: Path | None = None):
        self.projectRoot = projectRoot or Path(__file__).resolve().parent.parent.parent
        self.modelsDir = self.projectRoot / "models"
        self.catalogPath = self.projectRoot / "cfg" / "models.json"
        self.catalog = self._loadCatalog()

    def _loadCatalog(self) -> dict:
        if self.catalogPath.exists():
            with open(self.catalogPath, encoding="utf-8") as f:
                return json.load(f)
        return {"models": {}, "default": None}

    def _downloadedModelFilenames(self) -> set[str]:
        if not self.modelsDir.exists():
            return set()
        return {
            p.name
            for p in self.modelsDir.iterdir()
            if p.is_file() and p.suffix.lower() in MODEL_EXTENSIONS
        }

    def _formatFileSizeMb(self, path: Path) -> str:
        mb = path.stat().st_size / (1024 * 1024)
        return f"{mb:.0f} MB"

    def listModels(self) -> None:
        """Print catalog models and files already present in models/."""
        onDisk = self._downloadedModelFilenames()
        defaultName = self.catalog.get("default", "")

        print("\nCatalog (available to download):\n")
        if not self.catalog.get("models"):
            print("  (no entries in cfg/models.json)\n")
        else:
            for name, info in self.catalog["models"].items():
                marker = " (default)" if name == defaultName else ""
                fname = info["file"]
                status = "downloaded" if fname in onDisk else "not on disk"
                print(f"  {name}{marker}  [{status}]")
                print(f"    {info['description']}")
                print(f"    repo: {info['repo']}")
                print(f"    file: {fname}")
                if fname in onDisk:
                    path = self.modelsDir / fname
                    print(f"    local: models/{fname} ({self._formatFileSizeMb(path)})")
                print()

        print("On disk (models/):\n")
        if not onDisk:
            print("  (no .gguf or .bin files in models/)\n")
        else:
            catalogByFile = {
                info["file"]: n for n, info in self.catalog.get("models", {}).items()
            }
            for fname in sorted(onDisk):
                path = self.modelsDir / fname
                catNote = (
                    f"  (catalog: {catalogByFile[fname]})"
                    if fname in catalogByFile
                    else "  (custom / not in catalog)"
                )
                print(f"  {fname}  ({self._formatFileSizeMb(path)}){catNote}")
            print()

    def getModelInfo(self, modelName: str) -> tuple[str, str]:
        """Return (repo, filename) for a catalog model name. Raises ValueError if unknown."""
        if modelName not in self.catalog["models"]:
            available = ", ".join(self.catalog["models"].keys())
            logger.error("Model '%s' not found. Available: %s", modelName, available)
            raise ValueError(f"Unknown catalog model: {modelName}")
        info = self.catalog["models"][modelName]
        return info["repo"], info["file"]

    def buildUrl(self, repo: str, filename: str) -> str:
        return f"{HF_BASE_URL}/{repo}/resolve/main/{filename}"

    def download(self, repo: str, filename: str, force: bool = False) -> None:
        """Download a model file. Skips network if file exists unless force. Raises RuntimeError on fetch failure."""
        self.modelsDir.mkdir(parents=True, exist_ok=True)
        destPath = self.modelsDir / filename

        if destPath.exists() and not force:
            size = destPath.stat().st_size / (1024 * 1024)
            logger.info(
                "Model already present, skipping download: %s (%s MB)",
                destPath,
                int(size),
            )
            self._updateEnv(filename)
            return

        url = self.buildUrl(repo, filename)
        logger.info("Downloading: %s", filename)
        logger.info("From: %s", url)
        logger.info("To: %s", destPath)
        print()

        try:
            urlretrieve(url, str(destPath), reporthook=self._progressHook)
            print()
            size = destPath.stat().st_size / (1024 * 1024)
            logger.info("Download complete: %s MB", int(size))
            self._updateEnv(filename)
        except URLError as e:
            logger.error("Download failed: %s", e)
            if destPath.exists():
                destPath.unlink()
            raise RuntimeError(str(e)) from e
        except KeyboardInterrupt:
            print()
            logger.info("Download cancelled.")
            if destPath.exists():
                destPath.unlink()
            raise

    def removeCatalogModel(self, modelName: str) -> None:
        _, filename = self.getModelInfo(modelName)
        self._removeFileIfExists(filename, label=f"catalog '{modelName}'")

    def removeFile(self, filename: str) -> None:
        base = Path(filename).name
        if base != filename:
            logger.warning("Using basename only: %s", base)
        self._removeFileIfExists(base, label=f"file '{base}'")

    def _removeFileIfExists(self, filename: str, label: str) -> None:
        path = self.modelsDir / filename
        if not self.modelsDir.exists():
            logger.info("models/ does not exist, nothing to remove for %s", label)
            return
        if not path.is_file():
            logger.info("Not found (skipped): %s", path)
            return
        path.unlink()
        logger.info("Removed %s -> %s", label, path)

    def cleanModelsDir(self) -> None:
        if not self.modelsDir.exists():
            logger.info("models/ does not exist, nothing to clean.")
            return
        removed = 0
        for p in list(self.modelsDir.iterdir()):
            if p.is_file() and p.suffix.lower() in MODEL_EXTENSIONS:
                p.unlink()
                removed += 1
                logger.info("Removed: %s", p.name)
        if removed == 0:
            logger.info("No .gguf / .bin files found in models/.")
        else:
            logger.info("Cleaned %s model file(s) from models/.", removed)

    def _progressHook(self, blockNum: int, blockSize: int, totalSize: int):
        downloaded = blockNum * blockSize
        if totalSize > 0:
            percent = min(100, downloaded * 100 / totalSize)
            downloadedMb = downloaded / (1024 * 1024)
            totalMb = totalSize / (1024 * 1024)
            bar = "=" * int(percent // 2) + ">" + " " * (50 - int(percent // 2))
            sys.stdout.write(
                f"\r  [{bar}] {percent:5.1f}% ({downloadedMb:.0f}/{totalMb:.0f} MB)"
            )
            sys.stdout.flush()

    def _updateEnv(self, filename: str) -> None:
        envPath = self.projectRoot / "cfg" / ".env"
        if not envPath.exists():
            return
        newPath = f"models/{filename}"
        lines = envPath.read_text(encoding="utf-8").splitlines()
        updated = False
        for i, line in enumerate(lines):
            if line.startswith("LLM_LOCAL_MODEL_PATH="):
                lines[i] = f"LLM_LOCAL_MODEL_PATH={newPath}"
                updated = True
                break
        if updated:
            envPath.write_text("\n".join(lines) + "\n", encoding="utf-8")
            logger.info("Updated cfg/.env: LLM_LOCAL_MODEL_PATH=%s", newPath)
