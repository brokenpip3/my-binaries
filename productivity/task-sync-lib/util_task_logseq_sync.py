#!/usr/bin/env python
# -*- coding: utf-8 -*-
from logseq import (
    setup_logging,
    fetch_existing_tasks,
    grab_todos_from_logseq,
    translate_todo,
    from_logseq_to_taskwarrior,
)
import subprocess
import logging


def main():
    setup_logging()
    _existing = {
        task["logseq_uuid"] for task in fetch_existing_tasks() if "logseq_uuid" in task
    }
    added = 0
    for todo in grab_todos_from_logseq():
        _todo = translate_todo(todo)
        if todo["uuid"] in _existing:
            logging.debug(f"task {todo['content']} already exist: {todo['uuid']}")
            continue
        cmd = from_logseq_to_taskwarrior(_todo)
        try:
            logging.debug(f"running command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                logging.error(f"failed to add task: {result.stderr}")
            else:
                logging.info(f"task added: {_todo}")
                added += 1
        except subprocess.TimeoutExpired:
            logging.error(f"command timed out: {' '.join(cmd)}")
        except Exception as e:
            logging.error(f"error: {e}")
    logging.info(f"added {added} new tasks")


if __name__ == "__main__":
    main()
