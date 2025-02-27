import logging
import os
import subprocess
import json
from typing import Dict, List


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.DEBUG if os.getenv("LOGW_DEBUG") else logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )


def fetch_existing_tasks() -> List[Dict]:
    try:
        result = subprocess.run(
            ["task", "rc.hooks=0", "rc.context=0", "export"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        tasks = json.loads(result.stdout) if result.stdout.strip() else []
        logging.debug(f"grabbed {len(tasks)} task from taskwarrior")
        return tasks
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        logging.error(f"error grabbing existing tasks: {e}")
        return []
