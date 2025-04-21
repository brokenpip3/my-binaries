#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
from datetime import datetime, timedelta, timezone
from telethon import TelegramClient
from telethon.sessions import MemorySession
import os
import subprocess
import argparse


UTIL_PRIVACY_TELEGRAM_CLEANUP_PASS_CLI = os.getenv(
    "UTIL_PRIVACY_TELEGRAM_CLEANUP_PASS_CLI", "pass"
)
UTIL_PRIVACY_TELEGRAM_CLEANUP_PASS_ENTRY = os.getenv(
    "UTIL_PRIVACY_TELEGRAM_CLEANUP_PASS_ENTRY", "telegram/cleanup"
)


def get_api_credentials():
    result = subprocess.run(
        [
            UTIL_PRIVACY_TELEGRAM_CLEANUP_PASS_CLI,
            "show",
            UTIL_PRIVACY_TELEGRAM_CLEANUP_PASS_ENTRY,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError("Failed to fetch API credentials from pass")
    lines = result.stdout.splitlines()
    api_id = int(
        [line.split(":", 1)[1].strip() for line in lines if line.startswith("appid:")][
            0
        ]
    )
    api_hash = [
        line.split(":", 1)[1].strip() for line in lines if line.startswith("hash:")
    ][0]
    return api_id, api_hash


async def delete_old_messages(
    chat_ids: list, interactive: bool, days: int, api_id: int, api_hash: str
):
    session = MemorySession()
    async with TelegramClient(session, api_id, api_hash) as client:
        chats = await client.get_dialogs()

        if chat_ids:
            chats = [chat for chat in chats if chat.id in chat_ids]

        if interactive:
            chat_type = input(
                "Do you want to filter Group Chats or DMs? (group/dm): "
            ).lower()
            if chat_type == "group":
                chats = [chat for chat in chats if chat.is_group]
                print("Counting messages in group chats...")
            elif chat_type == "dm":
                chats = [chat for chat in chats if chat.is_user]
                print("Counting messages in DMs...")
            else:
                print("Invalid choice. Exiting.")
                return

        chat_message_counts = []
        for i, chat in enumerate(chats, 1):
            print(f"Counting {i}/{len(chats)}: {chat.name or chat.title}")
            messages = await client.get_messages(chat, from_user="me", limit=3001)
            count = len(messages) if len(messages) <= 3000 else "+3000"
            if count != 0:
                chat_message_counts.append((chat, count))

        sorted_chats = sorted(
            chat_message_counts,
            key=lambda x: (x[1] if isinstance(x[1], int) else 3001),
            reverse=True,
        )
        print("\nChats sorted by your message count:")
        for i, (chat, count) in enumerate(sorted_chats, 1):
            print(f"{i}. {chat.name or chat.title} (ID: {chat.id}) - {count} messages")

        if not interactive:
            # Non-interactive mode: delete messages from all chats without prompting
            for selected_chat, message_count in sorted_chats:
                if message_count == "+3000":
                    print(
                        f"Skipping {selected_chat.name or selected_chat.title} because it has over 3000 messages."
                    )
                    continue

                print(
                    f"Selected chat: {selected_chat.name or selected_chat.title} (ID: {selected_chat.id}) with {message_count} messages"
                )
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
                messages = await client.get_messages(
                    selected_chat, from_user="me", limit=None
                )
                to_delete = [msg for msg in messages if msg.date < cutoff_date]
                print(f"Deleting {len(to_delete)} messages...")

                for msg in to_delete:
                    print(f"Deleting message from {msg.date}: {msg.text}")
                    try:
                        await client.delete_messages(selected_chat, msg.id)
                    except Exception as e:
                        print(f"Failed to delete message {msg.id}: {e}")

                print("Deletion complete!")
            return

        # Interactive mode: prompt for user input
        while True:
            chat_index = int(input("\nSelect a chat by number: ")) - 1
            selected_chat, message_count = sorted_chats[chat_index]

            if message_count == "+3000":
                print(
                    f"Skipping {selected_chat.name or selected_chat.title} because it has over 3000 messages."
                )
                continue

            print(
                f"Selected chat: {selected_chat.name or selected_chat.title} (ID: {selected_chat.id}) with {message_count} messages"
            )

            confirm = input(
                f"Do you want to delete all messages older than {days} days? (yes/no): "
            ).lower()
            if confirm != "yes":
                print("Operation cancelled.")
                break

            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            messages = await client.get_messages(
                selected_chat, from_user="me", limit=None
            )
            to_delete = [msg for msg in messages if msg.date < cutoff_date]
            print(f"Deleting {len(to_delete)} messages...")

            for msg in to_delete:
                print(f"Deleting message from {msg.date}: {msg.text}")
                try:
                    await client.delete_messages(selected_chat, msg.id)
                except Exception as e:
                    print(f"Failed to delete message {msg.id}: {e}")

            print("Deletion complete!")

            another = input(
                "Do you want to delete messages from another chat in this list? (yes/no): "
            ).lower()
            if another != "yes":
                print("Exiting.")
                break


def parse_args():
    parser = argparse.ArgumentParser(description="Telegram Cleanup Script")
    parser.add_argument(
        "--ids", type=str, help="Comma-separated list of chat IDs", default=""
    )
    parser.add_argument(
        "--no-interactive", action="store_true", help="Run in non-interactive mode"
    )
    parser.add_argument(
        "--days",
        type=int,
        help="Number of days to retain messages (default: 30)",
        default=30,
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.ids:
        chat_ids = [int(id.strip()) for id in args.ids.split(",")]
    else:
        chat_ids = []
    interactive = not args.no_interactive
    api_id, api_hash = get_api_credentials()
    asyncio.run(delete_old_messages(chat_ids, interactive, args.days, api_id, api_hash))
