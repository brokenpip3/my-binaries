#!/usr/bin/env python3
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional, Dict

def get_taskrc_path() -> Path:
    taskrc = os.environ.get("TASKRC")
    if taskrc:
        return Path(taskrc)
    return Path.home() / ".config" / "task" / "taskrc"

def read_taskrc_config() -> Dict[str, str]:
    taskrc = get_taskrc_path()
    config = {}

    if not taskrc.exists():
        return config

    with open(taskrc) as f:
        for line in f:
            line = line.strip()
            if line.startswith("taskopen."):
                key, _, value = line.partition("=")
                config[key.strip()] = value.strip()

    return config

def fzf_select_task() -> Optional[str]:
    result = subprocess.run(
        ["task", "status:pending", "export"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0 or not result.stdout.strip():
        print("no pending tasks found", file=sys.stderr)
        return None

    tasks = json.loads(result.stdout)

    max_project_len = max((len(task.get("project", "")) for task in tasks), default=0)
    max_project_len = max(max_project_len, 10)

    term_width = os.get_terminal_size().columns
    id_width = 4
    separator_width = 6
    available_desc_width = term_width - id_width - max_project_len - separator_width

    fzf_input = []

    for task in tasks:
        task_id = task.get("id")
        description = task.get("description", "")
        project = task.get("project", "")
        tags = task.get("tags", [])

        if tags:
            description += f" +{' +'.join(tags)}"

        if len(description) > available_desc_width:
            description = description[:available_desc_width - 3] + "..."

        project_padded = project.ljust(max_project_len)

        line = f"{task_id:4d} | {project_padded} | {description}"
        fzf_input.append(line)

    fzf_process = subprocess.run(
        ["fzf", "--height=40%", "--reverse", "--header=task to open"],
        input="\n".join(fzf_input),
        capture_output=True,
        text=True
    )

    if fzf_process.returncode != 0 or not fzf_process.stdout.strip():
        return None

    selected = fzf_process.stdout.strip()
    task_id = selected.split("|")[0].strip()

    return task_id

def get_task_data(task_id: str) -> dict:
    result = subprocess.run(
        ["task", task_id, "export"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print(f"error: task not found: {task_id}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(result.stdout)
    if not data:
        print(f"error: task not found: {task_id}", file=sys.stderr)
        sys.exit(1)

    return data[0]

def handle_neovim(task_data: dict, config: dict) -> bool:
    file = task_data.get("neovim_file")
    line = task_data.get("neovim_line")
    repo = task_data.get("neovim_repo")
    task_id = task_data.get("id")

    if not all([file, line, repo]):
        return False

    session_name = f"task {task_id}"

    in_tmux = os.environ.get("TMUX") is not None

    if in_tmux:
        current_session = subprocess.run(
            ["tmux", "display-message", "-p", "#S"],
            capture_output=True,
            text=True
        ).stdout.strip()

        subprocess.run([
            "tmux", "new-window",
            "-t", current_session,
            "-c", repo,
            "-n", session_name,
            f"nvim +{line} {file}"
        ])
        print(f"opened in new window: {file}:{line}")
    else:
        has_session = subprocess.run(
            ["tmux", "has-session", "-t", session_name],
            capture_output=True
        ).returncode == 0

        if has_session:
            subprocess.run([
                "tmux", "new-window",
                "-t", session_name,
                "-c", repo,
                f"nvim +{line} {file}"
            ])
            subprocess.run(["tmux", "attach", "-t", session_name])
        else:
            subprocess.run([
                "tmux", "new-session",
                "-s", session_name,
                "-c", repo,
                f"nvim +{line} {file}"
            ])

    return True

def handle_url(task_data: dict, config: dict) -> bool:
    annotations = task_data.get("annotations", [])
    browser = config.get("taskopen.browser", "xdg-open")

    for annotation in annotations:
        desc = annotation.get("description", "")
        if re.match(r"^https?://", desc):
            subprocess.run([browser, desc])
            print(f"opening url: {desc}")
            return True

    return False

def show_task_info(task_id: str) -> None:
    print("no actionable data found")
    subprocess.run(["task", task_id, "info"])

def main() -> None:
    config = read_taskrc_config()

    if len(sys.argv) == 1:
        task_id = fzf_select_task()
        if not task_id:
            sys.exit(1)
    elif len(sys.argv) == 2:
        task_id = sys.argv[1]
    else:
        print("usage: util_task_open [task-id] or just util_task_open for fzf selection", file=sys.stderr)
        sys.exit(1)

    task_data = get_task_data(task_id)

    handlers = [
        handle_neovim,
        handle_url,
    ]

    for handler in handlers:
        if handler(task_data, config):
            return

    show_task_info(task_id)

if __name__ == "__main__":
    main()
