"""Import workflow JSON files from cfg/workflows/ into MongoDB.

Reads MDB_URI, MDB_DATABASE_NAME, and MDB_COLLECTION_NAME from cfg/.env.
Each file is upserted by workflowId so re-runs are safe.

Usage:
    python bin/import_workflows.py                     # import all *.json
    python bin/import_workflows.py --dir other/path    # custom source directory
    python bin/import_workflows.py --dry-run            # show what would be imported
"""

import argparse
import json
import logging
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv

load_dotenv(dotenv_path=str(_ROOT / "cfg" / ".env"))

import os

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def _loadFiles(directory: Path) -> list[dict]:
    """Read and parse every *.json file in *directory*."""
    if not directory.is_dir():
        logger.error("Directory does not exist: %s", directory)
        sys.exit(1)
    files = sorted(directory.glob("*.json"))
    if not files:
        logger.warning("No .json files found in %s", directory)
        return []
    workflows: list[dict] = []
    for fp in files:
        with open(fp, encoding="utf-8") as f:
            data = json.load(f)
        wid = data.get("workflowId", fp.stem)
        data.setdefault("workflowId", wid)
        workflows.append(data)
        logger.info("Loaded  %s  (workflowId=%s)", fp.name, wid)
    return workflows


def _import(workflows: list[dict]) -> None:
    """Upsert each workflow into MongoDB by workflowId."""
    from pymongo import MongoClient

    uri = os.getenv("MDB_URI")
    dbName = os.getenv("MDB_DATABASE_NAME")
    collName = os.getenv("MDB_COLLECTION_NAME")
    if not uri or not dbName or not collName:
        logger.error(
            "MDB_URI, MDB_DATABASE_NAME, and MDB_COLLECTION_NAME must be set in cfg/.env"
        )
        sys.exit(1)

    client = MongoClient(uri)
    collection = client[dbName][collName]

    for wf in workflows:
        wid = wf["workflowId"]
        result = collection.replace_one({"workflowId": wid}, wf, upsert=True)
        action = "inserted" if result.upserted_id else "updated"
        logger.info("  %s  workflowId=%s", action, wid)

    logger.info(
        "Done — %d workflow(s) imported into %s.%s", len(workflows), dbName, collName
    )
    client.close()


def main():
    parser = argparse.ArgumentParser(
        description="Import workflow JSON files into MongoDB"
    )
    parser.add_argument(
        "--dir",
        default=str(_ROOT / "cfg" / "workflows"),
        help="Source directory (default: cfg/workflows)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List files that would be imported without writing to MongoDB",
    )
    args = parser.parse_args()

    srcDir = Path(args.dir)
    workflows = _loadFiles(srcDir)
    if not workflows:
        return

    if args.dry_run:
        logger.info(
            "Dry run — %d workflow(s) would be imported:", len(workflows)
        )
        for wf in workflows:
            logger.info("  workflowId=%s", wf["workflowId"])
        return

    _import(workflows)


if __name__ == "__main__":
    main()
