#!/usr/bin/env python
# -*- coding: utf-8 -*-
from logseq import translate_taskwarrior, update_logseq_todo
from _tasklib import setup_logging
import sys
import json
import logging


def main():
    setup_logging()
    task_input = sys.stdin.read()
    logging.debug(f"Received input: {task_input}")

    try:
        # Taskwarrior sends two json (original and modified task)
        # separated by newline
        task_states = task_input.strip().split("\n")
        if len(task_states) != 2:
            raise ValueError("expected 2 json objects original and modified task")

        _, modified_task_json = task_states
        modified_task = json.loads(modified_task_json)
    except (ValueError, json.JSONDecodeError) as e:
        logging.error(f"invalid json input: {e}")
        sys.exit(1)

    if "logseq_uuid" not in modified_task:
        logging.debug("logseq uuid not found skipping logseq update")
        print(json.dumps(modified_task))
        sys.exit(0)

    uuid = modified_task["logseq_uuid"]
    page = modified_task.get("logseq_page", "")
    project = modified_task.get("project", "")
    logseq_content = None

    marker = "TODO"
    if "start" in modified_task:
        if modified_task.get("status") == "completed":
            marker = "DONE"
        else:
            marker = "DOING"
    elif modified_task.get("status") == "completed":
        marker = "DONE"

    logseq_content = translate_taskwarrior(modified_task, marker)
    if logseq_content:
        # add project if it's not in a project page
        if not page.startswith("projects") and project:
            logseq_content = (
                f"{logseq_content} [[projects/{project.replace('.', '/')}]]"
            )
        try:
            logging.debug(
                f"updating task {uuid} in logseq with content: {logseq_content}"
            )
            update_logseq_todo(uuid, logseq_content)
            print(json.dumps(modified_task))
            sys.exit(0)
        except Exception as e:
            logging.error(f"failed to update task {uuid} in logseq {e}")
            sys.exit(1)
    else:
        print(json.dumps(modified_task))
        sys.exit(0)


if __name__ == "__main__":
    main()
