import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta, timezone
from telethon.tl.types import PeerChannel
from util_privacy_telegram_cleanup import get_api_credentials, delete_old_messages, parse_args

MOCK_API_ID = 5489987
MOCK_CHAT_ID = 1001
MOCK_CHAT_NAME = "Fantasy Football"
MOCK_MESSAGE_TEXT = "I hope you did 65,5"
MOCK_MESSAGE_DATE = datetime.now(timezone.utc) - timedelta(days=31)
mashupmyfakehash = "mashupmyfakehash"


class MockChat:
    def __init__(self, id, is_group=False, is_user=False):
        self.id = id
        self.name = f"Chat {id}"
        self.title = f"Chat {id}"
        self.is_group = is_group
        self.is_user = is_user
        self.entity = PeerChannel(id)


class MockMessage:
    def __init__(self, id, date, text):
        self.id = id
        self.date = date
        self.text = text


def mock_subprocess_run(*args, **kwargs):
    class MockResult:
        def __init__(self, stdout, returncode):
            self.stdout = stdout
            self.returncode = returncode

    if args[0] == ["pass", "show", "telegram-api"]:
        return MockResult("appid: 5489987\nhash: mashupmyfakehash\n", 0)
    return MockResult("", 1)


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.get_dialogs = AsyncMock(
        return_value=[MockChat(1001, is_group=True), MockChat(1002, is_user=True)]
    )
    client.get_messages = AsyncMock(
        return_value=[
            MockMessage(1, MOCK_MESSAGE_DATE, "Old message"),
            MockMessage(2, datetime.now(timezone.utc), "Recent message"),
        ]
    )
    client.delete_messages = AsyncMock()
    return client


def test_get_api_credentials():
    with patch("subprocess.run", side_effect=mock_subprocess_run):
        api_id, api_hash = get_api_credentials()
        assert api_id == MOCK_API_ID
        assert api_hash == mashupmyfakehash


@pytest.mark.asyncio
async def test_delete_old_messages_interactive(mock_client):
    with patch("util_privacy_telegram_cleanup.TelegramClient", return_value=mock_client), patch(
        "builtins.input", side_effect=["group", "1", "yes", "no"]
    ):
        await delete_old_messages(
            chat_ids=[],
            interactive=True,
            days=30,
            api_id=MOCK_API_ID,
            api_hash=mashupmyfakehash,
        )

        mock_client.get_dialogs.assert_awaited_once()
        mock_client.delete_messages.assert_called()


def test_parse_args():
    with patch("sys.argv", ["script.py"]):
        args = parse_args()
        assert args.ids == ""
        assert args.no_interactive is False
        assert args.days == 30

    with patch(
        "sys.argv",
        [
            "util_privacy_telegram_cleanup.py",
            "--ids",
            "434343431,104779902",
            "--no-interactive",
            "--days",
            "60",
        ],
    ):
        args = parse_args()
        assert args.ids == "434343431,104779902"
        assert args.no_interactive is True
        assert args.days == 60
