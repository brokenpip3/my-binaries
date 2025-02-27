#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import json
import logging
from _tasklib import setup_logging
from _youtrack import update_youtrack_issue


def main():
    setup_logging()
    task_input = sys.stdin.read().strip()
    logging.debug(f"received input: {task_input}")
    try:
        _, modified_task_json = task_input.split("\n")
        modified_task = json.loads(modified_task_json)
    except (ValueError, json.JSONDecodeError) as e:
        logging.error(f"invalid json input: {e}")
        sys.exit(1)

    issue = modified_task.get("youtrack_rawid")
    # split the state_id and issue_id by colon
    if not issue:
        logging.debug("no youtrack_rawid found, skipping update")
        print(json.dumps(modified_task))
        sys.exit(0)
    state_id, issue_id = issue.split(":")

    new_state = "To Do"
    if "start" in modified_task:
        new_state = "In Progress"
    elif modified_task.get("status") == "completed":
        new_state = "Done"
    else:
        logging.debug("no state change detected, setting to todo")

    update_youtrack_issue(issue_id, state_id, new_state)
    logging.info(f"updated issue {issue_id} to state {new_state}")
    print(json.dumps(modified_task))
    sys.exit(0)


if __name__ == "__main__":
    main()
