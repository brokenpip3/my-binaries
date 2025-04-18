import requests
import os
import logging

YOUTRACK_URL = os.getenv("TASKSYNC_YOUTRACK_URL", "http://localhost:8080")
YOUTRACK_TOKEN = os.getenv("TASKSYNC_YOUTRACK_TOKEN", "changeme")


def get_youtrack_issues(query=""):
    url = f"{YOUTRACK_URL}/api/issues"
    headers = {
        "Authorization": f"Bearer {YOUTRACK_TOKEN}",
        "Accept": "application/json",
        "Cache-Control": "no-cache",
        "Content-Type": "application/json",
    }
    params = {
        "fields": "idReadable,id,summary,description,customFields(id,projectCustomField(field(name)),value(name))",
        "query": query,
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        issues = response.json()
        return issues

    except requests.exceptions.RequestException as e:
        logging.error(f"error {e}")
        return None


def get_custom_field_data(custom_fields, field_name):
    if custom_fields:
        for cf in custom_fields:
            field = cf.get("projectCustomField", {}).get("field", {})
            if field.get("name") == field_name:
                return cf.get("id"), cf.get("value", {}).get("name") if isinstance(
                    cf.get("value"), dict
                ) else cf.get("value")
    return None, None


def update_youtrack_issue(issue_id: str, state_id: str, new_state: str) -> bool:
    url = f"{YOUTRACK_URL}/api/issues/{issue_id}/customFields/{state_id}?fields=id,name,value(id,name)"
    headers = {
        "Authorization": f"Bearer {YOUTRACK_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {"value": {"name": new_state}}
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        logging.error(f"failed to update youtrack issue {issue_id}: {e}")
        return False


def get_states_from_env(var_name: str, default: list[str]) -> list[str]:
    return os.getenv(var_name, ",".join(default)).split(",")


def update_with_retry(issue_id: str, state_id: str, states: list[str]) -> None:
    for state in states:
        if update_youtrack_issue(issue_id, state_id, state):
            logging.info(f"updated issue {issue_id} to state {state}")
            return
        logging.warning(
            f"failed to update issue {issue_id} to state {state}, trying next"
        )
