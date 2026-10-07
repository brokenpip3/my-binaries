#!/usr/bin/env python3
import email as _email
import os
import sys
import tempfile
import tomllib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import smtp2telegram as s2t


def test_import():
    assert s2t is not None


class TestLoadConfig:
    def test_valid_config(self):
        data = b"""
[telegram]
bot_token = "1897001:AAGDelPiero-Buffon-Nedved-Trezeguet-01"

[routing]
"delpiero@juventus.com" = "1897010"
default = "1897000"
"""
        with tempfile.NamedTemporaryFile(suffix=".toml", delete=False) as f:
            f.write(data)
            f.flush()
            config = s2t.load_config(Path(f.name))
        Path(f.name).unlink()
        assert config["telegram"]["bot_token"] == "1897001:AAGDelPiero-Buffon-Nedved-Trezeguet-01"
        assert config["routing"]["delpiero@juventus.com"] == "1897010"
        assert config["routing"]["default"] == "1897000"

    def test_missing_file(self):
        with pytest.raises(FileNotFoundError):
            s2t.load_config(Path("/nonexistent/config.toml"))

    def test_invalid_toml(self):
        data = b"this is not toml {{{"
        with tempfile.NamedTemporaryFile(suffix=".toml", delete=False) as f:
            f.write(data)
            f.flush()
            with pytest.raises(tomllib.TOMLDecodeError):
                s2t.load_config(Path(f.name))
        Path(f.name).unlink()


class TestResolveRecipient:
    def test_exact_match(self):
        routing = {"delpiero@juventus.com": "1897010", "default": "1897000"}
        assert s2t.resolve_recipient(routing, "delpiero@juventus.com") == "1897010"

    def test_default_fallback(self):
        routing = {"delpiero@juventus.com": "1897010", "default": "1897000"}
        assert s2t.resolve_recipient(routing, "nedved@juventus.com") == "1897000"

    def test_no_match_no_default(self):
        routing = {"delpiero@juventus.com": "1897010"}
        assert s2t.resolve_recipient(routing, "nedved@juventus.com") is None

    def test_case_insensitive_match(self):
        routing = {"delpiero@juventus.com": "1897010", "default": "1897000"}
        assert s2t.resolve_recipient(routing, "DELPIERO@JUVENTUS.COM") == "1897010"

    def test_whitespace_handling(self):
        routing = {"delpiero@juventus.com": "1897010"}
        assert s2t.resolve_recipient(routing, " delpiero@juventus.com ") == "1897010"


class TestStripHtml:
    def test_simple_tags(self):
        assert s2t.strip_html("<p>Forza Juve</p>") == "Forza Juve"

    def test_br_becomes_newline(self):
        assert s2t.strip_html("Del Piero<br>Nedved") == "Del Piero\nNedved"

    def test_nested_tags(self):
        result = s2t.strip_html("<div><p>Forza <b>Juve</b></p></div>")
        assert "Forza Juve" in result

    def test_html_entities(self):
        result = s2t.strip_html("Juve &amp; Torino")
        assert "&" in result
        result2 = s2t.strip_html("Milan &lt; Juve")
        assert "<" in result2

    def test_plain_text_passthrough(self):
        assert s2t.strip_html("cronaca partita") == "cronaca partita"

    def test_empty_string(self):
        assert s2t.strip_html("") == ""

    def test_multiple_block_elements(self):
        result = s2t.strip_html("<p>primo tempo</p><p>secondo tempo</p>")
        assert "primo tempo" in result
        assert "secondo tempo" in result


class TestEscapeMarkdownV2:
    def test_escapes_special_chars(self):
        result = s2t.escape_markdown_v2("forza_juve *campioni*")
        assert result == r"forza\_juve \*campioni\*"

    def test_plain_text_unchanged(self):
        assert s2t.escape_markdown_v2("forza juve") == "forza juve"

    def test_escapes_backslash(self):
        assert s2t.escape_markdown_v2(r"mail\box") == r"mail\\box"

    def test_all_special_chars(self):
        result = s2t.escape_markdown_v2("_*[]()~`>#+-=|{}.!")
        for ch in "_*[]()~`>#+-=|{}.!":
            assert f"\\{ch}" in result

    def test_empty_string(self):
        assert s2t.escape_markdown_v2("") == ""


class TestFormatMessage:
    def test_formats_basic_message(self):
        result = s2t.format_message(
            mail_from="delpiero@juventus.com",
            to="tifoso@juveclub.it",
            subject="Report partita Juventus Inter",
            date="2015-06-06 20:45 CEST",
            body="La Vecchia Signora vince allo Stadium.",
        )
        assert "📧" in result
        assert "Report partita Juventus Inter" in result
        assert "delpiero@juventus" in result
        assert "tifoso@juveclub" in result
        assert "Stadium\\." in result

    def test_subject_escaped_for_markdown(self):
        result = s2t.format_message(
            mail_from="buffon@juventus.com",
            to="tifoso@juveclub.it",
            subject="Biglietti curva: 5$ settore #3",
            date="oggi",
            body="ok",
        )
        assert "5$" in result
        assert "\\#" in result

    def test_body_truncated(self):
        long_body = "x" * 4000
        result = s2t.format_message(
            mail_from="buffon@juventus.com",
            to="tifoso@juveclub.it",
            subject="Cronaca lunga della partita",
            date="now",
            body=long_body,
        )
        body_start = result.find("x" * 10)
        body_section = result[body_start:]
        assert len(body_section) <= 3500 + 50

    def test_empty_body(self):
        result = s2t.format_message(
            mail_from="buffon@juventus.com",
            to="tifoso@juveclub.it",
            subject="Convocazione allenamento",
            date="now",
            body="",
        )
        assert "📧" in result


class TestExtractBodyAndType:
    def test_plain_text_email(self):
        msg = MIMEText("Forza Juventus", "plain")
        body, is_html = s2t._extract_body_and_type(msg)
        assert body.strip() == "Forza Juventus"
        assert is_html is False

    def test_html_email(self):
        msg = MIMEText("<p>Forza <b>Juve</b></p>", "html")
        body, is_html = s2t._extract_body_and_type(msg)
        assert "<p>" in body
        assert is_html is True

    def test_multipart_prefers_plain(self):
        msg = MIMEMultipart("alternative")
        msg.attach(MIMEText("<p>versione html</p>", "html"))
        msg.attach(MIMEText("versione testo semplice", "plain"))
        body, is_html = s2t._extract_body_and_type(msg)
        assert body.strip() == "versione testo semplice"
        assert is_html is False

    def test_multipart_html_only(self):
        msg = MIMEMultipart("alternative")
        msg.attach(MIMEText("<p>solo html</p>", "html"))
        body, is_html = s2t._extract_body_and_type(msg)
        assert "<p>solo html</p>" in body
        assert is_html is True

    def test_multipart_with_attachment(self):
        msg = MIMEMultipart("mixed")
        msg.attach(MIMEText("cronaca partita", "plain"))
        attachment = MIMEText("allegato formazione", "plain")
        attachment.add_header("Content-Disposition", "attachment", filename="formazione.txt")
        msg.attach(attachment)
        body, is_html = s2t._extract_body_and_type(msg)
        assert "cronaca partita" in body
        assert is_html is False

    def test_encoded_charset(self):
        msg = MIMEText("Nedvěd", "plain", "utf-8")
        body, _ = s2t._extract_body_and_type(msg)
        assert "Nedvěd" in body

    def test_empty_message(self):
        msg = _email.message_from_string("")
        body, is_html = s2t._extract_body_and_type(msg)
        assert body == ""
        assert is_html is False


class TestTelegramSender:
    @pytest.fixture
    def sender(self):
        return s2t.TelegramSender(bot_token="1996005:AAGLippi-ChampionsLeague-Roma-Ajax-Final")

    def test_send_calls_bot(self, sender):
        import asyncio

        async def _run():
            with patch("smtp2telegram.Bot") as MockBot:
                mock_bot = MockBot.return_value
                mock_bot.__aenter__ = AsyncMock(return_value=mock_bot)
                mock_bot.__aexit__ = AsyncMock(return_value=None)
                mock_bot.send_message = AsyncMock()

                await sender.send("1897010", "Forza Juve")

                mock_bot.send_message.assert_awaited_once_with(
                    chat_id="1897010",
                    text="Forza Juve",
                    parse_mode="MarkdownV2",
                    disable_web_page_preview=True,
                )

        asyncio.run(_run())

    def test_send_to_different_chat(self, sender):
        import asyncio

        async def _run():
            with patch("smtp2telegram.Bot") as MockBot:
                mock_bot = MockBot.return_value
                mock_bot.__aenter__ = AsyncMock(return_value=mock_bot)
                mock_bot.__aexit__ = AsyncMock(return_value=None)
                mock_bot.send_message = AsyncMock()

                await sender.send("1897001", "Fino alla fine")

                mock_bot.send_message.assert_awaited_once_with(
                    chat_id="1897001",
                    text="Fino alla fine",
                    parse_mode="MarkdownV2",
                    disable_web_page_preview=True,
                )

        asyncio.run(_run())


class TestSmtpHandler:
    @pytest.fixture
    def config(self):
        return {
            "telegram": {"bot_token": "1897001:AAGDelPiero-Buffon-Nedved-Trezeguet-01"},
            "routing": {"delpiero@juventus.com": "1897010", "default": "1897000"},
        }

    @pytest.fixture
    def mock_sender(self):
        sender = MagicMock()
        sender.send = AsyncMock()
        return sender

    @pytest.fixture
    def handler(self, config, mock_sender):
        return s2t.SmtpHandler(config=config, sender=mock_sender)

    def _make_envelope(self, mail_from="segreteria@juventus.com", rcpt_tos=None, content=None):
        envelope = MagicMock()
        envelope.mail_from = mail_from
        envelope.rcpt_tos = rcpt_tos or ["delpiero@juventus.com"]
        envelope.content = content or self._make_email_bytes(
            "Report partita", "cronaca della partita", mail_from="segreteria@juventus.com"
        )
        return envelope

    def _make_email_bytes(self, subject, body, mail_from="segreteria@juventus.com", content_type="plain"):
        msg = MIMEText(body, content_type)
        msg["Subject"] = subject
        msg["From"] = mail_from
        msg["To"] = "delpiero@juventus.com"
        msg["Date"] = "Sun, 26 May 2015 20:45:00 +0200"
        return msg.as_bytes()

    def test_handle_data_routes_and_sends(self, handler, mock_sender):
        import asyncio

        async def _run():
            envelope = self._make_envelope(rcpt_tos=["delpiero@juventus.com"])
            result = await handler.handle_DATA(None, None, envelope)
            assert mock_sender.send.awaited
            call_args = mock_sender.send.await_args
            assert call_args[0][0] == "1897010"

        asyncio.run(_run())

    def test_handle_data_default_routing(self, handler, mock_sender):
        import asyncio

        async def _run():
            envelope = self._make_envelope(rcpt_tos=["sconosciuto@juveclub.it"])
            result = await handler.handle_DATA(None, None, envelope)
            assert mock_sender.send.awaited
            call_args = mock_sender.send.await_args
            assert call_args[0][0] == "1897000"

        asyncio.run(_run())

    def test_handle_data_no_route_no_default(self, handler, mock_sender, config):
        import asyncio

        async def _run():
            del config["routing"]["default"]
            handler2 = s2t.SmtpHandler(config=config, sender=mock_sender)
            envelope = self._make_envelope(rcpt_tos=["sconosciuto@juveclub.it"])
            result = await handler2.handle_DATA(None, None, envelope)
            assert mock_sender.send.await_count == 0
            assert "250" in result

        asyncio.run(_run())

    def test_handle_data_telegram_error(self, handler, mock_sender):
        import asyncio

        async def _run():
            mock_sender.send.side_effect = Exception("Telegram API error")
            envelope = self._make_envelope(rcpt_tos=["delpiero@juventus.com"])
            result = await handler.handle_DATA(None, None, envelope)
            assert result == "451 4.3.0 Temporary Telegram delivery failure"

        asyncio.run(_run())

    def test_handle_data_parse_error(self, handler):
        import asyncio

        async def _run():
            envelope = self._make_envelope()
            with patch("smtp2telegram._email.message_from_bytes", side_effect=ValueError):
                result = await handler.handle_DATA(None, None, envelope)
            assert result == "550 5.6.0 Could not parse message"

        asyncio.run(_run())

    def test_handle_data_html_email_stripped(self, handler, mock_sender):
        import asyncio

        async def _run():
            envelope = self._make_envelope(
                rcpt_tos=["delpiero@juventus.com"],
                content=self._make_email_bytes(
                    "Newsletter Juventus", "<p>Forza <b>Juve</b></p>", content_type="html"
                ),
            )
            result = await handler.handle_DATA(None, None, envelope)
            assert mock_sender.send.awaited
            sent_text = mock_sender.send.await_args[0][1]
            assert "Forza Juve" in sent_text
            assert "<b>" not in sent_text

        asyncio.run(_run())

    def test_handle_data_multiple_recipients(self, handler, mock_sender, config):
        import asyncio

        async def _run():
            config["routing"]["chiellini@juventus.com"] = "1897003"
            handler2 = s2t.SmtpHandler(config=config, sender=mock_sender)
            envelope = self._make_envelope(
                rcpt_tos=["delpiero@juventus.com", "chiellini@juventus.com", "sconosciuto@juveclub.it"]
            )
            result = await handler2.handle_DATA(None, None, envelope)
            assert mock_sender.send.await_count == 3

        asyncio.run(_run())


class TestBuildParser:
    def test_default_values(self):
        parser = s2t.build_parser()
        args = parser.parse_args([])
        assert args.port == 8025
        assert args.host == "0.0.0.0"
        assert args.config == str(Path.home() / ".config" / "smtp2telegram" / "config.toml")

    def test_custom_values(self):
        parser = s2t.build_parser()
        args = parser.parse_args([
            "--port", "2525",
            "--host", "127.0.0.1",
            "--config", "/etc/smtp2telegram.toml",
        ])
        assert args.port == 2525
        assert args.host == "127.0.0.1"
        assert args.config == "/etc/smtp2telegram.toml"


class TestMain:
    def test_main_no_config_no_env(self):
        with patch.object(sys, "argv", ["smtp2telegram", "--config", "/nonexistent/config.toml"]), \
             patch.dict(os.environ, {}, clear=True):
            with pytest.raises(SystemExit) as e:
                s2t.main()
            assert e.value.code != 0

    def test_main_env_only_no_config_file(self):
        env = {
            "SMTP2TG_BOT_TOKEN": "2011010:AAGConte-Allegri-FinoAllaFine-Scudetto09",
            "SMTP2TG_DEFAULT_CHAT_ID": "1897011",
        }
        with patch.object(sys, "argv", ["smtp2telegram", "--config", "/nonexistent/config.toml"]), \
             patch.dict(os.environ, env), \
             patch("smtp2telegram.Controller") as MockController, \
             patch("smtp2telegram.signal"):
            s2t.main()
            MockController.assert_called_once()

    def test_main_env_overrides_config(self, tmp_path):
        config_path = tmp_path / "config.toml"
        config_path.write_text("""
[telegram]
bot_token = "1897001:AAGDelPiero-Buffon-Nedved-Trezeguet-01"

[routing]
default = "1897000"
"delpiero@juventus.com" = "1897010"
""")
        env = {"SMTP2TG_BOT_TOKEN": "2011010:AAGConte-Allegri-FinoAllaFine-Scudetto09"}
        with patch.object(sys, "argv", ["smtp2telegram", "--config", str(config_path)]), \
             patch.dict(os.environ, env), \
             patch("smtp2telegram.Controller") as MockController, \
             patch("smtp2telegram.signal"):
            s2t.main()
            call_args = MockController.call_args
            handler = call_args[0][0]
            assert handler._sender._token == "2011010:AAGConte-Allegri-FinoAllaFine-Scudetto09"

    def test_main_missing_bot_token(self, tmp_path):
        config_path = tmp_path / "config.toml"
        config_path.write_text('[routing]\ndefault = "1897000"\n')
        with patch.object(sys, "argv", ["smtp2telegram", "--config", str(config_path)]), \
             patch.dict(os.environ, {}, clear=True):
            with pytest.raises(SystemExit) as e:
                s2t.main()
            assert e.value.code != 0

    def test_main_missing_routing_section(self, tmp_path):
        config_path = tmp_path / "config.toml"
        config_path.write_text('[telegram]\nbot_token = "1897001:AAGDelPiero-Buffon-Nedved-Trezeguet-01"\n')
        with patch.object(sys, "argv", ["smtp2telegram", "--config", str(config_path)]), \
             patch.dict(os.environ, {}, clear=True):
            with pytest.raises(SystemExit) as e:
                s2t.main()
            assert e.value.code != 0

    def test_main_starts_controller(self, tmp_path):
        config_path = tmp_path / "config.toml"
        config_path.write_text("""
[telegram]
bot_token = "1897001:AAGDelPiero-Buffon-Nedved-Trezeguet-01"

[routing]
default = "1897000"
""")
        with patch.object(sys, "argv", ["smtp2telegram", "--config", str(config_path)]), \
             patch.dict(os.environ, {}, clear=True), \
             patch("smtp2telegram.Controller") as MockController, \
             patch("smtp2telegram.signal"):
            mock_controller = MockController.return_value

            s2t.main()

            MockController.assert_called_once()
            mock_controller.start.assert_called_once()
            mock_controller.stop.assert_called_once()
