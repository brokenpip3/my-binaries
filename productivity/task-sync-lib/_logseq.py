import logging
import os
import re
import subprocess
import requests
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from _tasklib import fetch_existing_tasks, setup_logging

LOGSEQ_HOST = os.getenv("LOGW_LOGSEQ_HOST", "127.0.0.1")
LOGSEQ_PORT = os.getenv("LOGW_LOGSEQ_PORT", "12315")
LOGSEQ_TOKEN = os.getenv("LOGW_LOGSEQ_TOKEN", "<replace with your token>")
LOGSEQ_TLS = os.getenv("LOGW_LOGSEQ_TLS")
LOGSEQ_QUERY = os.getenv(
    "LOGW_LOGSEQ_QUERY",
    "(and (task TODO DOING) (not [[resources/it/logseq/template-collection]] ))",
)
LOGSEQ_API_URL = (
    f"{'http' if not LOGSEQ_TLS else 'https'}://{LOGSEQ_HOST}:{LOGSEQ_PORT}/api"
)
PRIORITY_MAP = {"A": "H", "B": "M", "C": "L"}


def grab_todos_from_logseq() -> List[Dict]:
    payload = {"method": "logseq.DB.q", "args": [LOGSEQ_QUERY]}
    headers = {
        "Authorization": f"Bearer {LOGSEQ_TOKEN}",
        "Content-Type": "application/json",
    }
    try:
        response = requests.post(
            LOGSEQ_API_URL, json=payload, headers=headers, timeout=10
        )
        response.raise_for_status()
        todos = response.json()
        logging.debug(f"grabbed {len(todos)} TODO from logseq")
        return todos
    except requests.RequestException as e:
        logging.error(f"error grabbing TODO {e}")
        return []


def extract_marker(content: str) -> Tuple[str, Optional[str]]:
    match = re.match(r"\s*(TODO|DOING)\s*(.*)", content)
    if match:
        return match.group(2).strip(), match.group(1)
    return content, None


def extract_priority(content: str) -> Tuple[str, Optional[str]]:
    match = re.match(r"\[#([ABC])\]\s*(.*)", content)
    if match:
        return match.group(2).strip(), PRIORITY_MAP.get(match.group(1))
    return content, None


def extract_project_from_content(content: str) -> Tuple[str, Optional[str]]:
    match = re.search(r"\[\[projects/([^]]+)\]\]", content)
    if match:
        return content.replace(match.group(0), "").strip(), match.group(1)
    return content, None


def extract_project_from_page(page: str) -> Optional[str]:
    if page.startswith("projects/"):
        return page.split("/", maxsplit=1)[1]


def extract_schedule(content: str) -> Tuple[str, Optional[str]]:
    match = re.match(r"(.*)\nSCHEDULED:\s*<(.*)>", content)
    if match:
        return match.group(1).strip(), match.group(2)
    return content, None


def extract_tags_from_content(content: str) -> Tuple[str, List[str]]:
    match = re.findall(r"#\w+", content)
    _content = re.sub(r"#\w+", "", content).strip()
    if match:
        _match = [match.replace("#", "") for match in match]
        return _content, _match
    return content, []


def remove_unwanted(content: str) -> str:
    """remove logbook, I'm not interested in misure the time spent on a task"""
    return re.sub(r":LOGBOOK:.*?:END:", "", content).strip()


def translate_todo(todo: Dict) -> List[str]:
    logseq_id = todo.get("id")
    logseq_uuid = todo.get("uuid")
    logseq_page_dict = todo.get("page", {})
    logseq_page = logseq_page_dict.get("name")
    t = todo.get("content", "")
    t = remove_unwanted(t)
    t, schedule = extract_schedule(t)
    t, marker = extract_marker(t)
    t, priority = extract_priority(t)
    t, project_c = extract_project_from_content(t)
    if project_c:
        project = project_c
    else:
        project = extract_project_from_page(logseq_page)
    t, tags = extract_tags_from_content(t)
    return [
        t,
        f"project:{project.replace('/', '.')}" if project else "",
        f"priority:{priority}" if priority else "",
        f"tags:{','.join(tags)}" if tags else "",
        f"schedule:{schedule}" if schedule else "",
        f"logseq_id:{logseq_id}",
        f"logseq_uuid:{logseq_uuid}",
        f"logseq_page:{logseq_page}",
        "start:now" if marker == "DOING" else "",
    ]


def translate_taskwarrior(task: Dict, marker: Optional[str] = "TODO") -> str:
    marker = "TODO" if not marker else marker
    c = task.get("description")
    reversed_priority_map = {v: k for k, v in PRIORITY_MAP.items()}
    if task.get("priority"):
        c = f"[#{reversed_priority_map.get(task.get('priority'))}] {c}"
    if task.get("tags"):
        c = f"{c} {' '.join([f'#{tag}' for tag in task.get('tags')])}"
    sched = task.get("scheduled", None)
    due = task.get("due", None)
    # taskwarrior date format: 20240101T000000Z
    if sched or due:
        dt = datetime.strptime((sched or due), "%Y%m%dT%H%M%SZ").strftime("%Y-%m-%d %a")
        c = f"{c}\nSCHEDULED: <{dt}>"
    c = f"{marker} {c}"
    return c


def from_logseq_to_taskwarrior(todo: List[str]) -> List[str]:
    cmd = ["task", "rc.hooks=0", "add"] + [f"{t}" for t in todo if t]
    return cmd


def create_logseq_todo(todo: str, page: str) -> Optional[Dict]:
    page = page or "taskwarrior"
    payload = {
        "method": "logseq.Editor.insertBlock",
        "args": [page, todo, {"isPageBlock": True}],
    }
    headers = {
        "Authorization": f"Bearer {LOGSEQ_TOKEN}",
        "Content-Type": "application/json",
    }
    try:
        response = requests.post(
            LOGSEQ_API_URL, json=payload, headers=headers, timeout=10
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logging.error(f"error while creating task in logseq: {e}")
        return None


def update_logseq_todo(uuid: str, task: str) -> bool:
    payload = {"method": "logseq.editor.updateBlock", "args": [uuid, task]}
    headers = {
        "Authorization": f"Bearer {LOGSEQ_TOKEN}",
        "Content-Type": "application/json",
    }
    try:
        response = requests.post(
            LOGSEQ_API_URL, headers=headers, json=payload, timeout=5
        )
        response.raise_for_status()
        logging.debug(f"logseq todo {uuid} updated")
        return True
    except requests.RequestException as e:
        logging.error(f"failed to update logseq todo {uuid}: {e}")
        return False


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
                logging.debug(f"task added successfully: {result.stdout}")
                added += 1
        except subprocess.TimeoutExpired:
            logging.error(f"command timed out: {' '.join(cmd)}")
        except Exception as e:
            logging.error(f"error: {e}")
    logging.info(f"added {added} new tasks")


if __name__ == "__main__":
    main()
