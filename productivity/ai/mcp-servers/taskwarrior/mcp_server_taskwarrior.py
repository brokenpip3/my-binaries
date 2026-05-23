#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import subprocess
import argparse
from typing import List, Optional, Dict, Any
from collections import defaultdict
from datetime import datetime, timedelta
import uvicorn
from pydantic import BaseModel
from mcp.server.fastmcp import FastMCP
from mcp.server.auth.provider import TokenVerifier, AccessToken
from mcp.server.auth.settings import AuthSettings
import logging
import os

logging.basicConfig(level=logging.INFO)

BEARER_TOKEN = os.getenv("UTIL_AI_MCP_TASKWARRIOR_TOKEN", "change-me")


class TaskwarriorTokenVerifier(TokenVerifier):
    async def verify_token(self, token: str) -> AccessToken | None:
        if token == BEARER_TOKEN:
            return AccessToken(
                token=token,
                client_id="taskwarrior_client",
                scopes=["taskwarrior:read", "taskwarrior:write"],
            )
        return None


mcp = FastMCP(
    "taskwarrior mcp server",
    instructions="lightweight taskwarrior mcp server for basic task management",
    token_verifier=TaskwarriorTokenVerifier(),
    auth=AuthSettings(
        issuer_url="https://taskwarrior-mcp.local/auth", resource_server_url=None
    ),
)


class Task(BaseModel):
    id: int
    description: str
    status: str
    project: Optional[str] = None
    tags: List[str] = []
    due: Optional[str] = None
    priority: Optional[str] = None
    urgency: Optional[float] = None
    scheduled: Optional[str] = None
    start: Optional[str] = None


def task_execute_query(args: List[str]) -> List[dict]:
    cmd = ["task"] + args + ["export"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logging.error(f"task command failed: {result.stderr}")
        raise Exception(f"task command failed: {result.stderr}")
    return json.loads(result.stdout) if result.stdout.strip() else []


def task_count_filtered(filter_args: List[str]) -> int:
    cmd = ["task"] + filter_args + ["count"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return (
        int(result.stdout.strip())
        if result.returncode == 0 and result.stdout.strip().isdigit()
        else 0
    )


def task_create_new(
    description: str,
    project: Optional[str] = None,
    priority: Optional[str] = None,
    due: Optional[str] = None,
    scheduled: Optional[str] = None,
    tags: List[str] = None,
    estimate: Optional[str] = None,
) -> Dict[str, Any]:
    cmd = ["task", "add", description]

    if project:
        cmd.extend([f"project:{project}"])
    if priority and priority.upper() in ["H", "M", "L"]:
        cmd.extend([f"priority:{priority.upper()}"])
    if due:
        cmd.extend([f"due:{due}"])
    if scheduled:
        cmd.extend([f"scheduled:{scheduled}"])
    if estimate:
        cmd.extend([f"estimate:{estimate}"])
    if tags:
        cmd.extend([f"+{tag}" for tag in tags])

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logging.error(f"failed to add task: {result.stderr}")
        raise Exception(f"failed to add task: {result.stderr}")

    task_id = None
    if "Created task" in result.stdout:
        try:
            task_id = int(result.stdout.split("Created task ")[1].split(".")[0])
        except (ValueError, IndexError) as e:
            logging.warning(f"could not parse task id from output: {e}")

    return {"success": True, "message": result.stdout.strip(), "task_id": task_id}


def task_run_command(task_id: int, command: str) -> Dict[str, Any]:
    cmd = ["task", str(task_id), command]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        logging.error(f"task {command} failed for {task_id}: {result.stderr}")
        raise Exception(f"task {command} failed: {result.stderr}")
    return {"success": True, "message": result.stdout.strip()}


@mcp.resource("tasks://")
async def task_list_pending() -> str:
    tasks = task_execute_query(["status:pending"])
    return json.dumps([Task(**task).dict() for task in tasks], indent=2)


@mcp.resource("tasks://today")
async def task_list_today() -> str:
    tasks = task_execute_query(["status:pending", "due:today"])
    return json.dumps([Task(**task).dict() for task in tasks], indent=2)


@mcp.resource("tasks://tomorrow")
async def task_list_tomorrow() -> str:
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    tasks = task_execute_query(["status:pending", f"due:{tomorrow}"])
    return json.dumps([Task(**task).dict() for task in tasks], indent=2)


@mcp.resource("tasks://overdue")
async def task_list_overdue() -> str:
    tasks = task_execute_query(["status:pending", "due.before:now"])
    return json.dumps([Task(**task).dict() for task in tasks], indent=2)


@mcp.resource("tasks://urgent")
async def task_list_urgent() -> str:
    tasks = task_execute_query(["status:pending", "priority:H"])
    return json.dumps([Task(**task).dict() for task in tasks], indent=2)


@mcp.resource("tasks://active")
async def task_list_active() -> str:
    tasks = task_execute_query(["status:pending", "+ACTIVE"])
    return json.dumps([Task(**task).dict() for task in tasks], indent=2)


@mcp.resource("tasks://scheduled/today")
async def task_list_scheduled_today() -> str:
    tasks = task_execute_query(["status:pending", "scheduled:today"])
    return json.dumps([Task(**task).dict() for task in tasks], indent=2)


@mcp.resource("tasks://scheduled/tomorrow")
async def task_list_scheduled_tomorrow() -> str:
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    tasks = task_execute_query(["status:pending", f"scheduled:{tomorrow}"])
    return json.dumps([Task(**task).dict() for task in tasks], indent=2)


@mcp.resource("tasks://scheduled/week")
async def task_list_scheduled_week() -> str:
    today = datetime.now()
    week_end = today + timedelta(days=7)
    week_filter = f"scheduled.after:{today.strftime('%Y-%m-%d')} scheduled.before:{week_end.strftime('%Y-%m-%d')}"
    tasks = task_execute_query(["status:pending"] + week_filter.split())
    return json.dumps([Task(**task).dict() for task in tasks], indent=2)


@mcp.resource("tasks://planned/{date}")
async def task_list_planned_date(date: str) -> str:
    tasks = task_execute_query(["status:pending", f"scheduled:{date}"])
    due_tasks = task_execute_query(["status:pending", f"due:{date}"])
    all_tasks = tasks + [t for t in due_tasks if t not in tasks]
    return json.dumps([Task(**task).dict() for task in all_tasks], indent=2)


@mcp.resource("tasks://project/{project_name}")
async def tasks_by_project(project_name: str) -> str:
    tasks = task_execute_query(["status:pending", f"project:{project_name}"])
    return json.dumps([Task(**task).dict() for task in tasks], indent=2)


@mcp.resource("task://{id}")
async def task_get_details(id: int) -> str:
    tasks = task_execute_query([f"id:{id}"])
    if not tasks:
        raise Exception(f"task {id} not found")
    return json.dumps(Task(**tasks[0]).dict(), indent=2)


@mcp.resource("tasks://summary")
async def tasks_summary() -> str:
    pending = task_count_filtered(["status:pending"])
    completed_today = task_count_filtered(["status:completed", "end:today"])
    overdue = task_count_filtered(["status:pending", "due.before:now"])
    active = task_count_filtered(["status:pending", "+ACTIVE"])
    scheduled_today = task_count_filtered(["status:pending", "scheduled:today"])

    all_tasks = task_execute_query(["status:pending"])
    projects = list(
        set(task.get("project", "") for task in all_tasks if task.get("project"))
    )

    summary = {
        "pending_tasks": pending,
        "active_tasks": active,
        "completed_today": completed_today,
        "overdue_tasks": overdue,
        "scheduled_today": scheduled_today,
        "projects": sorted(projects),
    }
    return json.dumps(summary, indent=2)


@mcp.resource("tasks://projects")
async def list_projects() -> str:
    tasks = task_execute_query(["status:pending"])
    project_counts = defaultdict(int)

    for task in tasks:
        project = task.get("project", "no project")
        project_counts[project] += 1

    projects = [
        {"name": project, "task_count": count}
        for project, count in project_counts.items()
    ]
    return json.dumps(
        sorted(projects, key=lambda x: x["task_count"], reverse=True), indent=2
    )


@mcp.tool()
async def task_add_new(
    description: str,
    project: str = None,
    priority: str = None,
    due: str = None,
    scheduled: str = None,
    tags: List[str] = None,
    estimate: str = None,
) -> str:
    try:
        result = task_create_new(
            description, project, priority, due, scheduled, tags or [], estimate
        )

        response = f"task created: {description}"
        if result.get("task_id"):
            response += f" (id: {result['task_id']})"
        if project:
            response += f" in project {project}"
        if priority:
            response += f" with priority {priority}"
        if due:
            response += f" due {due}"
        if scheduled:
            response += f" scheduled {scheduled}"
        if tags:
            response += f" tagged: {', '.join(tags)}"

        return response

    except Exception as e:
        logging.error(f"error creating task: {e}")
        return f"error creating task: {str(e)}"


@mcp.tool()
async def task_mark_done(task_id: int) -> str:
    try:
        task_run_command(task_id, "done")
        return f"task {task_id} completed"
    except Exception as e:
        logging.error(f"error completing task: {e}")
        return f"error completing task: {str(e)}"


@mcp.tool()
async def task_remove_entry(task_id: int) -> str:
    try:
        result = subprocess.run(
            ["task", str(task_id), "delete"],
            capture_output=True,
            text=True,
            input="yes\n",
        )
        if result.returncode != 0:
            logging.error(f"failed to delete task {task_id}: {result.stderr}")
            raise Exception(f"failed to delete task: {result.stderr}")

        return f"task {task_id} deleted"
    except Exception as e:
        logging.error(f"error deleting task: {e}")
        return f"error deleting task: {str(e)}"


@mcp.tool()
async def task_set_active(task_id: int) -> str:
    try:
        task_run_command(task_id, "start")
        subprocess.run(
            ["task", str(task_id), "modify", "+ACTIVE"], capture_output=True, text=True
        )
        return f"task {task_id} set as active"
    except Exception as e:
        logging.error(f"error setting task active: {e}")
        return f"error setting task active: {str(e)}"


@mcp.tool()
async def task_clear_active(task_id: int) -> str:
    try:
        task_run_command(task_id, "stop")
        subprocess.run(
            ["task", str(task_id), "modify", "-ACTIVE"], capture_output=True, text=True
        )
        return f"task {task_id} no longer active"
    except Exception as e:
        logging.error(f"error clearing active task: {e}")
        return f"error clearing active task: {str(e)}"


@mcp.tool()
async def task_schedule_item(task_id: int, scheduled_date: str) -> str:
    try:
        result = subprocess.run(
            ["task", str(task_id), "modify", f"scheduled:{scheduled_date}"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            logging.error(f"failed to schedule task {task_id}: {result.stderr}")
            raise Exception(f"failed to schedule task: {result.stderr}")

        return f"task {task_id} scheduled for {scheduled_date}"
    except Exception as e:
        logging.error(f"error scheduling task: {e}")
        return f"error scheduling task: {str(e)}"


@mcp.tool()
async def task_plan_daily(date: str = None) -> str:
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    try:
        scheduled = task_execute_query(["status:pending", f"scheduled:{date}"])
        due = task_execute_query(["status:pending", f"due:{date}"])
        active = task_execute_query(["status:pending", "+ACTIVE"])

        plan = {
            "date": date,
            "scheduled_tasks": [Task(**task).dict() for task in scheduled],
            "due_tasks": [Task(**task).dict() for task in due],
            "active_tasks": [Task(**task).dict() for task in active],
            "total_planned": len(scheduled) + len(due),
        }

        return json.dumps(plan, indent=2)
    except Exception as e:
        logging.error(f"error creating daily plan: {e}")
        return f"error creating daily plan: {str(e)}"


@mcp.tool()
async def task_plan_tomorrow() -> str:
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    return await task_plan_daily(tomorrow)


@mcp.tool()
async def task_plan_weekly(week_offset: int = 0) -> str:
    try:
        today = datetime.now() + timedelta(weeks=week_offset)
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)

        week_filter = f"scheduled.after:{week_start.strftime('%Y-%m-%d')} scheduled.before:{week_end.strftime('%Y-%m-%d')}"
        scheduled = task_execute_query(["status:pending"] + week_filter.split())

        due_filter = f"due.after:{week_start.strftime('%Y-%m-%d')} due.before:{week_end.strftime('%Y-%m-%d')}"
        due = task_execute_query(["status:pending"] + due_filter.split())

        plan = {
            "week_start": week_start.strftime("%Y-%m-%d"),
            "week_end": week_end.strftime("%Y-%m-%d"),
            "scheduled_tasks": [Task(**task).dict() for task in scheduled],
            "due_tasks": [Task(**task).dict() for task in due],
            "total_planned": len(scheduled) + len(due),
        }

        return json.dumps(plan, indent=2)
    except Exception as e:
        logging.error(f"error creating weekly plan: {e}")
        return f"error creating weekly plan: {str(e)}"


if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser(description="minimal taskwarrior mcp server")
        parser.add_argument("--port", type=int, default=8125, help="server port")
        args = parser.parse_args()
        uvicorn.run(
            mcp.streamable_http_app, host="0.0.0.0", port=args.port, factory=True
        )
    except Exception as e:
        logging.error(f"server startup failed: {e}")
        raise
