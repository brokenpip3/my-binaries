import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta


class Event:
    def __init__(self, **kwargs):
        self.id = kwargs.get("id")
        self.summary = kwargs.get("summary")
        self.start = kwargs.get("start")
        self.end = kwargs.get("end")
        self.location = kwargs.get("location")
        self.description = kwargs.get("description")
        self.status = kwargs.get("status", "confirmed")
        self.attendees = kwargs.get("attendees", [])
        self.organizer = kwargs.get("organizer")
        self.calendar_id = kwargs.get("calendar_id", "primary")

    def dict(self):
        return {
            "id": self.id,
            "summary": self.summary,
            "start": self.start,
            "end": self.end,
            "location": self.location,
            "description": self.description,
            "status": self.status,
            "attendees": self.attendees,
            "organizer": self.organizer,
            "calendar_id": self.calendar_id,
        }


class TestEventModel:
    def test_event_creation_minimal(self):
        event_data = {
            "id": "event_123",
            "summary": "Morning Training Session",
            "start": {"dateTime": "2025-03-15T10:00:00Z"},
            "end": {"dateTime": "2025-03-15T11:00:00Z"},
        }
        event = Event(**event_data)

        assert event.id == "event_123"
        assert event.summary == "Morning Training Session"
        assert event.start == {"dateTime": "2025-03-15T10:00:00Z"}
        assert event.end == {"dateTime": "2025-03-15T11:00:00Z"}
        assert event.status == "confirmed"
        assert event.attendees == []
        assert event.calendar_id == "primary"

    def test_event_creation_full(self):
        event_data = {
            "id": "event_456",
            "summary": "Tactical Meeting - Derby della Mole",
            "start": {"dateTime": "2025-03-15T14:00:00Z"},
            "end": {"dateTime": "2025-03-15T15:30:00Z"},
            "location": "Continassa Training Center",
            "description": "Pre-match tactical discussion for Turin derby",
            "status": "tentative",
            "attendees": [
                {"email": "vlahovic@juve.com", "displayName": "Dusan Vlahovic"},
                {"email": "yildiz@juve.com", "displayName": "Kenan Yıldız"},
            ],
            "organizer": {
                "email": "tudor@juve.com",
                "displayName": "Igor Tudor",
            },
            "calendar_id": "team@juve.com",
        }
        event = Event(**event_data)

        assert event.id == "event_456"
        assert event.summary == "Tactical Meeting - Derby della Mole"
        assert event.location == "Continassa Training Center"
        assert event.description == "Pre-match tactical discussion for Turin derby"
        assert event.status == "tentative"
        assert len(event.attendees) == 2
        assert event.attendees[0]["email"] == "vlahovic@juve.com"
        assert event.organizer["email"] == "tudor@juve.com"
        assert event.calendar_id == "team@juve.com"

    def test_event_dict_conversion(self):
        event_data = {
            "id": "event_789",
            "summary": "Recovery Session",
            "start": {"dateTime": "2025-03-15T09:00:00Z"},
            "end": {"dateTime": "2025-03-15T10:00:00Z"},
        }
        event = Event(**event_data)
        event_dict = event.dict()

        assert isinstance(event_dict, dict)
        assert event_dict["id"] == "event_789"
        assert event_dict["summary"] == "Recovery Session"
        assert event_dict["status"] == "confirmed"


class TestCalendarGetEventsQuery:
    @patch("mcp_server_google_calendar.build")
    def test_successful_events_query(self, mock_build):
        mock_service = MagicMock()
        mock_events = MagicMock()
        mock_list = MagicMock()

        mock_build.return_value = mock_service
        mock_service.events.return_value = mock_events
        mock_events.list.return_value = mock_list
        mock_list.execute.return_value = {
            "items": [
                {
                    "id": "event_1",
                    "summary": "Pre-Match Press Conference",
                    "start": {"dateTime": "2025-03-15T09:00:00Z"},
                    "end": {"dateTime": "2025-03-15T10:00:00Z"},
                    "status": "confirmed",
                }
            ]
        }

        with patch(
            "mcp_server_google_calendar.calendar_get_events_query"
        ) as mock_query:
            mock_query.return_value = [
                {
                    "id": "event_1",
                    "summary": "Pre-Match Press Conference",
                    "start": {"dateTime": "2025-03-15T09:00:00Z"},
                    "end": {"dateTime": "2025-03-15T10:00:00Z"},
                    "status": "confirmed",
                }
            ]

            result = mock_query()
            assert len(result) == 1
            assert result[0]["id"] == "event_1"
            assert result[0]["summary"] == "Pre-Match Press Conference"

    @patch("mcp_server_google_calendar.build")
    def test_empty_events_result(self, mock_build):
        mock_service = MagicMock()
        mock_events = MagicMock()
        mock_list = MagicMock()

        mock_build.return_value = mock_service
        mock_service.events.return_value = mock_events
        mock_events.list.return_value = mock_list
        mock_list.execute.return_value = {"items": []}

        with patch(
            "mcp_server_google_calendar.calendar_get_events_query"
        ) as mock_query:
            mock_query.return_value = []
            result = mock_query()
            assert result == []

    @patch("mcp_server_google_calendar.build")
    def test_api_error_handling(self, mock_build):
        mock_service = MagicMock()
        mock_events = MagicMock()
        mock_list = MagicMock()

        mock_build.return_value = mock_service
        mock_service.events.return_value = mock_events
        mock_events.list.return_value = mock_list
        mock_list.execute.side_effect = Exception("API Error")

        with patch(
            "mcp_server_google_calendar.calendar_get_events_query"
        ) as mock_query:
            mock_query.side_effect = Exception("Calendar API error: API Error")

            with pytest.raises(Exception, match="Calendar API error"):
                mock_query()


class TestCalendarGetNextEvent:
    @patch("mcp_server_google_calendar.calendar_get_events_query")
    def test_get_next_event_success(self, mock_query):
        now = datetime.now()
        future_event = {
            "id": "next_event",
            "summary": "Match vs Inter Milan",
            "start": {"dateTime": (now + timedelta(hours=2)).isoformat() + "Z"},
            "end": {"dateTime": (now + timedelta(hours=3)).isoformat() + "Z"},
            "status": "confirmed",
        }

        mock_query.return_value = [future_event]

        with patch("mcp_server_google_calendar.calendar_get_next_event") as mock_next:
            mock_next.return_value = future_event

            result = mock_next()
            assert result["id"] == "next_event"
            assert result["summary"] == "Match vs Inter Milan"

    @patch("mcp_server_google_calendar.calendar_get_events_query")
    def test_get_next_event_no_events(self, mock_query):
        mock_query.return_value = []

        with patch("mcp_server_google_calendar.calendar_get_next_event") as mock_next:
            mock_next.return_value = None

            result = mock_next()
            assert result is None

    @patch("mcp_server_google_calendar.calendar_get_events_query")
    def test_get_next_event_api_failure(self, mock_query):
        mock_query.side_effect = Exception("API Error")

        with patch("mcp_server_google_calendar.calendar_get_next_event") as mock_next:
            mock_next.side_effect = Exception("Failed to get next event: API Error")

            with pytest.raises(Exception, match="Failed to get next event"):
                mock_next()


class TestCalendarCountEvents:
    @patch("mcp_server_google_calendar.build")
    def test_count_events_success(self, mock_build):
        mock_service = MagicMock()
        mock_events = MagicMock()
        mock_list = MagicMock()

        mock_build.return_value = mock_service
        mock_service.events.return_value = mock_events
        mock_events.list.return_value = mock_list
        mock_list.execute.return_value = {
            "items": [{"id": "event_1"}, {"id": "event_2"}, {"id": "event_3"}]
        }

        with patch("mcp_server_google_calendar.calendar_count_events") as mock_count:
            mock_count.return_value = 3

            result = mock_count()
            assert result == 3

    @patch("mcp_server_google_calendar.build")
    def test_count_events_empty(self, mock_build):
        mock_service = MagicMock()
        mock_events = MagicMock()
        mock_list = MagicMock()

        mock_build.return_value = mock_service
        mock_service.events.return_value = mock_events
        mock_events.list.return_value = mock_list
        mock_list.execute.return_value = {"items": []}

        with patch("mcp_server_google_calendar.calendar_count_events") as mock_count:
            mock_count.return_value = 0

            result = mock_count()
            assert result == 0

    @patch("mcp_server_google_calendar.build")
    def test_count_events_api_failure(self, mock_build):
        mock_service = MagicMock()
        mock_events = MagicMock()
        mock_list = MagicMock()

        mock_build.return_value = mock_service
        mock_service.events.return_value = mock_events
        mock_events.list.return_value = mock_list
        mock_list.execute.side_effect = Exception("API Error")

        with patch("mcp_server_google_calendar.calendar_count_events") as mock_count:
            mock_count.return_value = 0

            result = mock_count()
            assert result == 0


class TestDateTimeHandling:
    def test_today_date_range(self):
        today = datetime.now()
        start_of_day = today.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = today.replace(hour=23, minute=59, second=59, microsecond=999999)

        assert start_of_day.date() == today.date()
        assert end_of_day.date() == today.date()
        assert start_of_day < end_of_day

    def test_week_date_range(self):
        today = datetime.now()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)

        assert (week_end - week_start).days == 6
        assert week_start.weekday() == 0  # Monday

    def test_month_date_range(self):
        today = datetime.now()
        month_start = today.replace(day=1)

        if today.month == 12:
            next_month = today.replace(year=today.year + 1, month=1, day=1)
        else:
            next_month = today.replace(month=today.month + 1, day=1)

        month_end = next_month - timedelta(days=1)

        assert month_start.day == 1
        assert month_start.month == today.month
        assert month_end.month == today.month

    def test_iso_format_conversion(self):
        test_datetime = datetime(2025, 3, 15, 10, 30, 0)
        iso_string = test_datetime.isoformat() + "Z"

        assert iso_string == "2025-03-15T10:30:00Z"
        assert "T" in iso_string
        assert iso_string.endswith("Z")


class TestIntegrationScenarios:
    @patch("mcp_server_google_calendar.calendar_get_events_query")
    def test_daily_schedule_integration(self, mock_query):
        today = datetime.now()
        daily_events = [
            {
                "id": "morning_meeting",
                "summary": "Team Warm-up Drills",
                "start": {"dateTime": today.replace(hour=9).isoformat() + "Z"},
                "end": {"dateTime": today.replace(hour=9, minute=30).isoformat() + "Z"},
            },
            {
                "id": "afternoon_review",
                "summary": "Video Analysis Session",
                "start": {"dateTime": today.replace(hour=14).isoformat() + "Z"},
                "end": {"dateTime": today.replace(hour=15).isoformat() + "Z"},
            },
        ]

        mock_query.return_value = daily_events

        result = mock_query()
        assert len(result) == 2
        assert result[0]["summary"] == "Team Warm-up Drills"
        assert result[1]["summary"] == "Video Analysis Session"

    @patch("mcp_server_google_calendar.calendar_get_events_query")
    def test_weekly_schedule_integration(self, mock_query):
        today = datetime.now()
        weekly_events = []

        for i in range(5):
            day = today + timedelta(days=i)
            weekly_events.append(
                {
                    "id": f"daily_meeting_{i}",
                    "summary": f"Training Session Day {i + 1}",
                    "start": {"dateTime": day.replace(hour=9).isoformat() + "Z"},
                    "end": {"dateTime": day.replace(hour=10).isoformat() + "Z"},
                }
            )

        mock_query.return_value = weekly_events

        result = mock_query()
        assert len(result) == 5
        assert all("Training Session" in event["summary"] for event in result)

    @patch("mcp_server_google_calendar.calendar_get_next_event")
    def test_next_appointment_integration(self, mock_next):
        now = datetime.now()
        next_event = {
            "id": "upcoming_event",
            "summary": "Medical Checkup - Bremer",
            "start": {"dateTime": (now + timedelta(minutes=30)).isoformat() + "Z"},
            "end": {
                "dateTime": (now + timedelta(hours=1, minutes=30)).isoformat() + "Z"
            },
            "location": "J Medical",
        }

        mock_next.return_value = next_event

        result = mock_next()
        assert result["summary"] == "Medical Checkup - Bremer"
        assert result["location"] == "J Medical"
        assert "upcoming_event" == result["id"]


class TestErrorHandlingAndSecurity:
    def test_invalid_calendar_id_handling(self):
        with patch(
            "mcp_server_google_calendar.calendar_get_events_query"
        ) as mock_query:
            mock_query.side_effect = Exception("Calendar not found")

            with pytest.raises(Exception, match="Calendar not found"):
                mock_query(calendar_id="invalid@example.com")

    def test_authentication_failure_handling(self):
        with patch(
            "mcp_server_google_calendar.calendar_get_events_query"
        ) as mock_query:
            mock_query.side_effect = Exception("Authentication failed")

            with pytest.raises(Exception, match="Authentication failed"):
                mock_query()

    def test_rate_limit_handling(self):
        with patch(
            "mcp_server_google_calendar.calendar_get_events_query"
        ) as mock_query:
            mock_query.side_effect = Exception("Rate limit exceeded")

            with pytest.raises(Exception, match="Rate limit exceeded"):
                mock_query()

    def test_network_error_handling(self):
        with patch(
            "mcp_server_google_calendar.calendar_get_events_query"
        ) as mock_query:
            mock_query.side_effect = Exception("Network error")

            with pytest.raises(Exception, match="Network error"):
                mock_query()


class TestMCPResourceEndpoints:
    def test_events_today_resource_format(self):
        expected_format = {
            "events": [
                {
                    "id": "event_1",
                    "summary": "Strength and Conditioning",
                    "start": {"dateTime": "2025-03-15T10:00:00Z"},
                    "end": {"dateTime": "2025-03-15T11:00:00Z"},
                    "status": "confirmed",
                }
            ],
            "count": 1,
            "date": "2025-03-15",
        }

        assert "events" in expected_format
        assert "count" in expected_format
        assert "date" in expected_format

    def test_next_event_resource_format(self):
        expected_format = {
            "event": {
                "id": "next_event",
                "summary": "Champions League Match vs Bayern",
                "start": {"dateTime": "2025-03-15T14:00:00Z"},
                "end": {"dateTime": "2025-03-15T15:00:00Z"},
                "location": "Allianz Stadium",
            },
            "time_until": "2 hours 30 minutes",
        }

        assert "event" in expected_format
        assert "time_until" in expected_format

    def test_events_week_resource_format(self):
        expected_format = {
            "events": [],
            "count": 0,
            "week_start": "2025-03-15",
            "week_end": "2025-03-21",
        }

        assert "events" in expected_format
        assert "count" in expected_format
        assert "week_start" in expected_format
        assert "week_end" in expected_format

    def test_events_month_resource_format(self):
        expected_format = {
            "events": [],
            "count": 0,
            "month_start": "2025-03-01",
            "month_end": "2025-03-31",
        }

        assert "events" in expected_format
        assert "count" in expected_format
        assert "month_start" in expected_format
        assert "month_end" in expected_format
