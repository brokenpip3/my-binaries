#!/usr/bin/env python3

import json
import argparse
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
import uvicorn
from pydantic import BaseModel, ConfigDict
from mcp.server.fastmcp import FastMCP
from mcp.server.auth.provider import TokenVerifier, AccessToken
from mcp.server.auth.settings import AuthSettings
import logging
import os
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

logging.basicConfig(level=logging.INFO)

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
BEARER_TOKEN = os.getenv("UTIL_AI_MCP_GOOGLECALENDAR_TOKEN")
SERVICE_ACCOUNT_FILE = os.getenv("UTIL_AI_MCP_GOOGLECALENDAR_ACCOUNT_FILE")
MAX_RESULTS_DEFAULT = int(os.getenv("UTIL_AI_MCP_GOOGLECALENDAR_MAX_RESULTS", "250"))
CALENDAR_ID = os.getenv("UTIL_AI_MCP_GOOGLECALENDAR_CALENDAR_ID", "primary")


class GoogleCalendarTokenVerifier(TokenVerifier):
    async def verify_token(self, token: str) -> AccessToken | None:
        if not BEARER_TOKEN:
            raise ValueError("missing bearer token")
        if token == BEARER_TOKEN:
            return AccessToken(
                token=token,
                client_id="google_calendar_client",
                scopes=["calendar:read"],
            )
        return None


mcp = FastMCP(
    "google calendar mcp server",
    instructions="lightweight google calendar mcp server for read-only calendar access",
    token_verifier=GoogleCalendarTokenVerifier(),
    auth=AuthSettings(
        issuer_url="https://google-calendar-mcp.local/auth", resource_server_url=None
    ),
)


class Event(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    summary: str
    start: Dict[str, Any]
    end: Dict[str, Any]
    location: Optional[str] = None
    description: Optional[str] = None
    status: str = "confirmed"
    attendees: List[Dict[str, Any]] = []
    organizer: Optional[Dict[str, Any]] = None
    calendar_id: str = "primary"


def get_calendar_service():
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build("calendar", "v3", credentials=creds)


def calendar_get_events_query(
    time_min=None, time_max=None, max_results=None, calendar_id=None
):
    if max_results is None:
        max_results = MAX_RESULTS_DEFAULT
    if calendar_id is None:
        calendar_id = CALENDAR_ID

    service = get_calendar_service()

    if not time_min:
        time_min = datetime.now(timezone.utc).isoformat()
    if not time_max:
        time_max = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()

    events_result = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    return events_result.get("items", [])


def calendar_get_next_event(calendar_id=None):
    now = datetime.now(timezone.utc)
    events = calendar_get_events_query(
        time_min=now.isoformat(),
        time_max=(now + timedelta(days=30)).isoformat(),
        max_results=1,
        calendar_id=calendar_id,
    )
    return events[0] if events else None


def calendar_count_events(time_min=None, time_max=None, calendar_id=None):
    events = calendar_get_events_query(
        time_min=time_min, time_max=time_max, calendar_id=calendar_id
    )
    return len(events)


def get_time_until_event(event_start):
    if "dateTime" in event_start:
        start_time = datetime.fromisoformat(
            event_start["dateTime"].replace("Z", "+00:00")
        )
    else:
        start_time = datetime.strptime(event_start["date"], "%Y-%m-%d").replace(
            tzinfo=timezone.utc
        )

    now = datetime.now(timezone.utc)
    delta = start_time - now

    if delta.total_seconds() < 0:
        return "past event"

    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, _ = divmod(remainder, 60)

    if days > 0:
        return f"{days} days, {hours} hours"
    elif hours > 0:
        return f"{hours} hours, {minutes} minutes"
    else:
        return f"{minutes} minutes"


@mcp.resource("events://next")
async def get_next_event() -> str:
    event = calendar_get_next_event()
    if not event:
        return json.dumps({"event": None, "message": "no events"}, indent=2)

    result = {
        "event": Event(**event, calendar_id=CALENDAR_ID).dict(),
        "time_until": get_time_until_event(event["start"]),
    }
    return json.dumps(result, indent=2)


@mcp.resource("events://today")
async def get_events_today() -> str:
    today = datetime.now(timezone.utc)
    start_of_day = today.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = today.replace(hour=23, minute=59, second=59, microsecond=999999)

    events = calendar_get_events_query(
        time_min=start_of_day.isoformat(), time_max=end_of_day.isoformat()
    )

    result = {
        "events": [Event(**event, calendar_id=CALENDAR_ID).dict() for event in events],
        "count": len(events),
        "date": today.strftime("%Y-%m-%d"),
    }
    return json.dumps(result, indent=2)


@mcp.resource("events://tomorrow")
async def get_events_tomorrow() -> str:
    tomorrow = datetime.now(timezone.utc) + timedelta(days=1)
    start_of_day = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = tomorrow.replace(hour=23, minute=59, second=59, microsecond=999999)

    events = calendar_get_events_query(
        time_min=start_of_day.isoformat(), time_max=end_of_day.isoformat()
    )

    result = {
        "events": [Event(**event, calendar_id=CALENDAR_ID).dict() for event in events],
        "count": len(events),
        "date": tomorrow.strftime("%Y-%m-%d"),
    }
    return json.dumps(result, indent=2)


@mcp.resource("events://week")
async def get_events_week() -> str:
    today = datetime.now(timezone.utc)
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    start_of_week = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_week = week_end.replace(hour=23, minute=59, second=59, microsecond=999999)

    events = calendar_get_events_query(
        time_min=start_of_week.isoformat(), time_max=end_of_week.isoformat()
    )

    result = {
        "events": [Event(**event, calendar_id=CALENDAR_ID).dict() for event in events],
        "count": len(events),
        "week_start": week_start.strftime("%Y-%m-%d"),
        "week_end": week_end.strftime("%Y-%m-%d"),
    }
    return json.dumps(result, indent=2)


@mcp.resource("events://month")
async def get_events_month() -> str:
    today = datetime.now(timezone.utc)
    month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    if today.month == 12:
        next_month = today.replace(year=today.year + 1, month=1, day=1)
    else:
        next_month = today.replace(month=today.month + 1, day=1)

    month_end = next_month - timedelta(days=1)
    month_end = month_end.replace(hour=23, minute=59, second=59, microsecond=999999)

    events = calendar_get_events_query(
        time_min=month_start.isoformat(), time_max=month_end.isoformat()
    )

    result = {
        "events": [Event(**event, calendar_id=CALENDAR_ID).dict() for event in events],
        "count": len(events),
        "month_start": month_start.strftime("%Y-%m-%d"),
        "month_end": month_end.strftime("%Y-%m-%d"),
    }
    return json.dumps(result, indent=2)


@mcp.resource("events://date/{date}")
async def get_events_by_date(date: str) -> str:
    target_date = datetime.strptime(date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)

    events = calendar_get_events_query(
        time_min=start_of_day.isoformat(), time_max=end_of_day.isoformat()
    )

    result = {
        "events": [Event(**event, calendar_id=CALENDAR_ID).dict() for event in events],
        "count": len(events),
        "date": date,
    }
    return json.dumps(result, indent=2)


@mcp.resource("events://calendar/{calendar_id}")
async def get_events_by_calendar(calendar_id: str) -> str:
    now = datetime.now(timezone.utc)
    week_end = now + timedelta(days=7)

    events = calendar_get_events_query(
        time_min=now.isoformat(), time_max=week_end.isoformat(), calendar_id=calendar_id
    )

    result = {
        "events": [Event(**event, calendar_id=calendar_id).dict() for event in events],
        "count": len(events),
        "calendar_id": calendar_id,
        "time_range": f"{now.strftime('%Y-%m-%d')} to {week_end.strftime('%Y-%m-%d')}",
    }
    return json.dumps(result, indent=2)


@mcp.resource("events://summary")
async def get_events_summary() -> str:
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    week_end = now + timedelta(days=7)

    today_count = calendar_count_events(
        time_min=today_start.isoformat(), time_max=today_end.isoformat()
    )

    week_count = calendar_count_events(
        time_min=now.isoformat(), time_max=week_end.isoformat()
    )

    next_event = calendar_get_next_event()

    summary = {
        "events_today": today_count,
        "events_next_7_days": week_count,
        "next_event": Event(**next_event, calendar_id=CALENDAR_ID).dict()
        if next_event
        else None,
        "time_until_next": get_time_until_event(next_event["start"])
        if next_event
        else None,
        "summary_date": now.strftime("%Y-%m-%d %H:%M:%S"),
    }

    return json.dumps(summary, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8126)
    args = parser.parse_args()

    uvicorn.run(mcp.streamable_http_app(), host="0.0.0.0", port=args.port)
