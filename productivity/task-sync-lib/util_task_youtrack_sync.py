#!/usr/bin/env python3

from _tasklib import setup_logging, fetch_existing_tasks
import logging
import subprocess
from _youtrack import get_youtrack_issues, get_custom_field_data


def sync_task_with_youtrack():
    query = "for:me #Unresolved"
    issues = get_youtrack_issues(query)

    if issues:
        for issue in issues:
            state_id, state = get_custom_field_data(issue.get("customFields"), "State")
            _existing = {
                task["youtrack"]
                for task in fetch_existing_tasks()
                if "youtrack" in task
            }
            if issue["idReadable"] in _existing:
                logging.debug(
                    f"task {issue['summary']} already exist: {issue['idReadable']}, state: {state}, rawid: {state_id}:{issue['id']}"
                )
                continue
            else:
                task_command = [
                    "task",
                    "add",
                    f"youtrack:{issue.get('idReadable')}",
                    f"youtrack_rawid:{state_id}:{issue.get('id')}",
                    "project:work.prima",
                    f"{issue.get('summary')}",
                ]

                if state == "In Progress":
                    task_command.append("start:now")

                subprocess.run(task_command, check=True)
                logging.info(
                    f"task added {issue.get('summary')} youtrack:{issue.get('idReadable')} project:work.prima"
                )
                if state:
                    logging.info(f"State of task: {state}")

    else:
        logging.warning("no card assigned, you are basically fired!")


if __name__ == "__main__":
    setup_logging()
    sync_task_with_youtrack()
