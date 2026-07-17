#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import email as _email
import logging
import os
import re
import signal
import sys
import tomllib
from email.message import Message
from email.policy import default as _email_policy
from html import unescape
from html.parser import HTMLParser
from pathlib import Path

from aiosmtpd.controller import Controller
from telegram import Bot

logger = logging.getLogger(__name__)

def load_config(path: Path) -> dict:
    with open(path, "rb") as f:
        return tomllib.load(f)


def resolve_recipient(routing: dict, to_address: str) -> str | None:
    cleaned = to_address.lower().strip()
    if cleaned in routing:
        return routing[cleaned]
    return routing.get("default")

class _HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.result: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in ("br", "p", "div", "li", "td", "tr", "h1", "h2", "h3", "h4", "h5", "h6"):
            self.result.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("p", "div", "li", "td", "tr", "h1", "h2", "h3", "h4", "h5", "h6"):
            self.result.append("\n")

    def handle_data(self, data: str) -> None:
        self.result.append(data)


def strip_html(text: str) -> str:
    stripper = _HTMLStripper()
    stripper.feed(text)
    raw = "".join(stripper.result)
    cleaned = re.sub(r"\n{3,}", "\n\n", raw)
    return unescape(cleaned).strip()

_MD_V2_ESCAPE_RE = re.compile(r"([_*\[\]()~`>#+\-=|{}.!])")


def escape_markdown_v2(text: str) -> str:
    return _MD_V2_ESCAPE_RE.sub(r"\\\1", text)


_BODY_MAX_LEN = 3500


def format_message(
    *,
    mail_from: str,
    to: str,
    subject: str,
    date: str,
    body: str,
) -> str:
    esc = escape_markdown_v2
    truncated_body = body[:_BODY_MAX_LEN]
    return (
        f"📧 *{esc(subject)}*\n"
        f"From: {esc(mail_from)}\n"
        f"To: {esc(to)}\n"
        f"Date: {esc(date)}\n"
        f"─────────────────\n"
        f"{esc(truncated_body)}"
    )

def _decode_part(part: Message) -> str:
    payload = part.get_payload(decode=True)
    if payload is None:
        return ""
    charset = part.get_content_charset() or "utf-8"
    try:
        return payload.decode(charset)
    except (UnicodeDecodeError, LookupError):
        return payload.decode("utf-8", errors="replace")


def _extract_body_and_type(msg: Message) -> tuple[str, bool]:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_maintype() != "text":
                continue
            if part.get_content_type() == "text/plain":
                return _decode_part(part), False
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                return _decode_part(part), True
        for part in msg.walk():
            if part.get_content_maintype() == "text":
                return _decode_part(part), False
        return "", False
    else:
        ct = msg.get_content_type()
        body = _decode_part(msg)
        return body, ct == "text/html"

class TelegramSender:
    def __init__(self, bot_token: str) -> None:
        self._token = bot_token

    async def send(self, chat_id: str, text: str) -> None:
        async with Bot(self._token) as bot:
            await bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode="MarkdownV2",
                disable_web_page_preview=True,
            )

class SmtpHandler:
    def __init__(self, config: dict, sender: TelegramSender) -> None:
        self._routing = config["routing"]
        self._sender = sender

    async def handle_DATA(self, server, session, envelope) -> str:
        try:
            msg = _email.message_from_bytes(envelope.content, policy=_email_policy)
        except Exception:
            logger.exception("failed to parse email")
            return "250 OK"

        mail_from = envelope.mail_from or msg.get("From", "")
        subject = msg.get("Subject", "(no subject)")
        date = msg.get("Date", "")

        body, is_html = _extract_body_and_type(msg)
        if is_html:
            try:
                body = strip_html(body)
            except Exception:
                logger.exception("html stripping failed, using raw body")

        for to_addr in envelope.rcpt_tos:
            chat_id = resolve_recipient(self._routing, to_addr)
            if chat_id is None:
                logger.warning("no route for recipient %s", to_addr)
                continue

            try:
                text = format_message(
                    mail_from=mail_from,
                    to=to_addr,
                    subject=subject,
                    date=date,
                    body=body,
                )
                await self._sender.send(chat_id, text)
            except Exception:
                logger.exception(
                    "telegram send failed (subject=%r, chat_id=%s)", subject, chat_id
                )

        return "250 OK"

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="SMTP server that forwards emails to Telegram",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8025,
        help="SMTP server port (default: 8025)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="SMTP server bind address (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=str(Path.home() / ".config" / "smtp2telegram" / "config.toml"),
        help="Path to TOML config file",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()

    config: dict = {}
    config_path = Path(args.config)
    if config_path.exists():
        try:
            config = load_config(config_path)
        except Exception as e:
            print(f"error: failed to parse config: {e}", file=sys.stderr)
            sys.exit(1)

    env_token = os.environ.get("SMTP2TG_BOT_TOKEN", "")
    if env_token:
        config.setdefault("telegram", {})["bot_token"] = env_token

    env_default = os.environ.get("SMTP2TG_DEFAULT_CHAT_ID", "")
    if env_default:
        config.setdefault("routing", {})["default"] = env_default

    if "telegram" not in config or "bot_token" not in config["telegram"]:
        print(
            "error: bot_token must be set via config [telegram].bot_token "
            "or SMTP2TG_BOT_TOKEN env var",
            file=sys.stderr,
        )
        sys.exit(1)

    if "routing" not in config:
        print(
            "error: routing must be set via config [routing] "
            "or SMTP2TG_DEFAULT_CHAT_ID env var",
            file=sys.stderr,
        )
        sys.exit(1)

    sender = TelegramSender(config["telegram"]["bot_token"])
    handler = SmtpHandler(config=config, sender=sender)
    controller = Controller(handler, hostname=args.host, port=args.port)

    controller.start()
    print(f"smtp2telegram listening on {args.host}:{args.port}", file=sys.stderr)

    try:
        signal.pause()
    except AttributeError:
        import time

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
    except KeyboardInterrupt:
        pass

    controller.stop()


if __name__ == "__main__":
    main()
