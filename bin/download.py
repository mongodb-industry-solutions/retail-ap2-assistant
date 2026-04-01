"""Download GGUF models from Hugging Face to the models/ directory.

Usage:
    python bin/download.py                           # download default catalog model
    python bin/download.py --model phi-2             # catalog model (skips if file exists)
    python bin/download.py --list                    # list catalog + on-disk
    python bin/download.py --repo USER/REPO --file model.gguf
    python bin/download.py --force --model phi-2     # re-download even if present
    python bin/download.py --remove phi-2            # remove catalog model file
    python bin/download.py --remove-file custom.gguf # remove file by basename
    python bin/download.py --clean                   # remove all .gguf / .bin in models/
"""

import argparse
import logging
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.services.modelDownloadService import ModelDownloadService

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Download GGUF models from Hugging Face")
    parser.add_argument("--model", type=str, metavar="NAME", help="Model key from cfg/models.json")
    parser.add_argument("--list", action="store_true", help="List catalog + on-disk models")
    parser.add_argument("--repo", type=str, help="Hugging Face repo (e.g. TheBloke/Mistral-7B-Instruct-v0.2-GGUF)")
    parser.add_argument("--file", type=str, help="Model filename (e.g. mistral-7b-instruct-v0.2.Q4_K_M.gguf)")
    parser.add_argument("--force", action="store_true", help="Re-download even if file already exists")
    parser.add_argument("--remove", type=str, metavar="NAME", help="Remove catalog model file from models/")
    parser.add_argument("--remove-file", type=str, dest="remove_file", metavar="FILE", help="Remove models/FILE by basename")
    parser.add_argument("--clean", action="store_true", help="Remove all .gguf and .bin files under models/")
    args = parser.parse_args()

    service = ModelDownloadService()

    if args.list:
        service.listModels()
        return

    if args.clean:
        service.cleanModelsDir()
        return

    if args.remove:
        try:
            service.removeCatalogModel(args.remove)
        except ValueError:
            sys.exit(1)
        return

    if args.remove_file:
        service.removeFile(args.remove_file)
        return

    try:
        if args.repo and args.file:
            service.download(args.repo, args.file, force=args.force)
        elif args.model:
            repo, filename = service.getModelInfo(args.model)
            service.download(repo, filename, force=args.force)
        else:
            defaultModel = service.catalog.get("default")
            if defaultModel:
                logger.info("No model specified, using default: %s", defaultModel)
                repo, filename = service.getModelInfo(defaultModel)
                service.download(repo, filename, force=args.force)
            else:
                parser.print_help()
    except ValueError:
        sys.exit(1)
    except RuntimeError:
        sys.exit(1)


if __name__ == "__main__":
    main()
