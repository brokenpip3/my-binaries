#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import logging
import os
import json
import base64
import threading
import itertools
from getpass import getpass
from concurrent.futures import ThreadPoolExecutor, as_completed

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

PASS_CLI = os.environ.get("UTIL_BITSYNC_PASS_CLI", "pass")


def verify_bitwarden_binary() -> None:
    logging.info("Verifying bitwarden cli binary")
    process = subprocess.run(["bw", "--version"], capture_output=True, text=True)
    if process.returncode != 0:
        logging.error("Failed to verify Bitwarden CLI binary: %s", process.stderr)
        raise RuntimeError("Bitwarden cli binary not found")
    logging.info("Bitwarden cli binary verified successfully")


def authenticate_bitwarden() -> str:
    try:
        master_password = getpass("Enter your Bitwarden master password: ")
        process = subprocess.run(
            ["bw", "unlock", "--raw"],
            input=master_password,
            text=True,
            capture_output=True,
        )
        del master_password
        if process.returncode != 0:
            logging.error("Failed to authenticate with bitwarden")
            raise RuntimeError("Bitwarden authentication failed.")
        logging.info("Successfully authenticated with Bitwarden.")
        logging.info("Session token: %s", process.stdout.strip())
        return process.stdout.strip()
    except Exception as e:
        logging.critical("An error occurred during Bitwarden authentication: %s", e)
        raise


def fetch_pass_entries() -> list[str]:
    logging.info("Fetching pass entries.")
    process = subprocess.run(
        [PASS_CLI, "git", "ls-tree", "-r", "--name-only", "HEAD"],
        capture_output=True,
        text=True,
    )
    if process.returncode != 0:
        logging.error("Failed to list pass entries: %s", process.stderr)
        raise RuntimeError("Failed to retrieve pass entries.")
    entries = [
        line.strip()
        for line in process.stdout.splitlines()
        if line.strip().endswith(".gpg")
    ]
    logging.info("Found %d pass entries.", len(entries))
    return entries


def get_pass_details(entry: str) -> tuple[str, str | None]:
    logging.info("Retrieving details for pass entry '%s'.", entry)
    entry_name = os.path.splitext(entry)[0]
    process = subprocess.run(
        [PASS_CLI, "show", entry_name], capture_output=True, text=True
    )
    if process.returncode != 0:
        logging.error("Failed to retrieve pass entry '%s': %s", entry, process.stderr)
        return ("", "")

    lines = process.stdout.splitlines()
    if not lines:
        logging.warning("No details found for entry '%s'.", entry)
        return ("", "")

    password = lines[0]
    username = next(
        (
            line.split(":", 1)[1].strip()
            for line in lines[1:]
            if line.lower().startswith(("user:", "username:"))
        ),
        None,
    )
    logging.info("Retrieved password and username for entry '%s'.", entry)
    return password, username


def insert_or_update_bitwarden(
    entryraw: str, password: str, username: str | None, session: str
) -> None:
    entry = os.path.splitext(entryraw)[0]
    logging.info("Checking if entry '%s' exists in Bitwarden.", entry)
    search_cmd = f"bw list items --search '{entry}' --session {session}"
    search_process = subprocess.run(
        search_cmd, shell=True, capture_output=True, text=True
    )
    if search_process.returncode != 0:
        logging.error(
            "Failed to search for entry '%s': %s", entry, search_process.stderr
        )
        raise RuntimeError(f"Failed to search for entry {entry}")

    existing_items = json.loads(search_process.stdout or "[]")
    if existing_items:
        item_id = existing_items[0]["id"]
        logging.info("Entry '%s' exists. Updating item.", entry)
        action_cmd = f"bw edit item {item_id} --session {session}"
    else:
        logging.info("Entry '%s' does not exist. Creating new item.", entry)
        action_cmd = f"bw create item --session {session}"

    item_data = json.dumps(build_item_data(entry, password, username))
    encoded_item_data = base64.b64encode(item_data.encode()).decode()

    action_process = subprocess.run(
        f"echo {encoded_item_data} | base64 --decode | bw encode | {action_cmd}",
        shell=True,
        capture_output=True,
        text=True,
    )
    if action_process.returncode != 0:
        logging.error("Failed to process entry '%s': %s", entry, action_process.stderr)
        raise RuntimeError(f"Failed to process entry {entry}.")
    logging.info("Entry '%s' successfully processed.", entry)


def build_item_data(entry_name: str, password: str, username: str | None) -> dict:
    login_data = {
        "username": username or "",
        "password": password,
        "uris": [{"match": 0, "uri": f"https://{entry_name}"}],
        "totp": None,
    }
    return {
        "passwordHistory": [],
        "revisionDate": None,
        "creationDate": None,
        "deletedDate": None,
        "organizationId": None,
        "collectionIds": [],
        "folderId": None,
        "type": 1,
        "name": entry_name,
        "notes": None,
        "favorite": False,
        "fields": [],
        "login": login_data,
        "secureNote": None,
        "card": None,
        "identity": None,
        "reprompt": 0,
    }


def sync_pass_to_bitwarden():
    logging.info("Starting synchronization of pass entries to Bitwarden.")
    verify_bitwarden_binary()
    session = authenticate_bitwarden()
    entries = fetch_pass_entries()

    stop_event = threading.Event()
    total_entries = len(entries)
    processed_counter = itertools.count(1)

    def process_entry(entry: str):
        if stop_event.is_set():
            return
        if entry == "bitwarden.gpg":
            return
        current_count = next(processed_counter)
        logging.info("Processing entry %d/%d: %s", current_count, total_entries, entry)
        password, username = get_pass_details(entry)
        if password:
            insert_or_update_bitwarden(entry, password, username, session)
        else:
            logging.warning("Skipping entry '%s' due to missing password.", entry)

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(process_entry, entry) for entry in entries]
        try:
            for future in as_completed(futures):
                if stop_event.is_set():
                    break
                future.result()
        except KeyboardInterrupt:
            logging.warning("Keyboard interrupt received. Stopping sync.")
            stop_event.set()
            executor.shutdown(wait=False)
            raise

    logging.info("Sync process completed successfully.")


if __name__ == "__main__":
    try:
        sync_pass_to_bitwarden()
    except Exception as e:
        logging.critical("Sync failed: %s", str(e))
