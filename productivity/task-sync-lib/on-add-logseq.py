#!/usr/bin/env python
# -*- coding: utf-8 -*-

from _logseq import create_logseq_todo, translate_taskwarrior, setup_logging

import sys
import json
import logging


def main():
    setup_logging()
    try:
        task = json.loads(sys.stdin.read())
        if not task or "description" not in task:
            logging.info("no task description")
            sys.exit(1)
        project = task.get("project")
        if project:
            project = f"projects/{project.replace(".", "/")}"
        else:
            project = "taskwarrior"
        logseq_response = create_logseq_todo(translate_taskwarrior(task), project)
        if not logseq_response:
            logging.error("failed to create task in logseq, original task:")
            print(json.dumps(task))
            sys.exit(1)
        logging.debug(f"created task in logseq: {logseq_response}")
        logseq_uuid = logseq_response.get("uuid")
        if logseq_uuid:
            task["logseq_uuid"] = logseq_uuid
            task["logseq_page"] = project
            print(json.dumps(task))
            sys.exit(0)
        else:
            logging.error("missing logseq uuid")
            sys.exit(1)
    except json.JSONDecodeError as e:
        logging.error(f"invalid json input: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
