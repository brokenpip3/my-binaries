#!/usr/bin/env python3

import os
import sys
import json
import sqlite3
import subprocess
import requests
import hashlib
from typing import Dict, List, Any
import argparse

BROWN = "\033[33m"
RESET = "\033[0m"


def pcolor(text):
    if os.environ.get("NO_COLOR"):
        return text
    return f"{BROWN}{text}{RESET}"


def setup_database(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS scan_results (
        image_hash TEXT PRIMARY KEY,
        image_name TEXT NOT NULL,
        scan_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        findings_count INTEGER NOT NULL,
        findings_data TEXT
    )
    """)
    conn.commit()
    return conn


def get_image_hash(image_name):
    return hashlib.md5(image_name.encode()).hexdigest()


def check_image_scanned(conn, image_hash):
    cursor = conn.cursor()
    cursor.execute(
        "SELECT image_name, findings_count, findings_data FROM scan_results WHERE image_hash = ?",
        (image_hash,),
    )
    return cursor.fetchone()


def save_scan_result(conn, image_hash, image_name, findings):
    cursor = conn.cursor()
    findings_count = len(findings)
    findings_data = json.dumps(findings) if findings else "[]"
    cursor.execute(
        "INSERT OR REPLACE INTO scan_results (image_hash, image_name, findings_count, findings_data) VALUES (?, ?, ?, ?)",
        (image_hash, image_name, findings_count, findings_data),
    )
    conn.commit()


def get_docker_hub_token() -> str:
    pass_binary = os.environ.get("UTIL_SECURITY_TARTUFI_PASS", "pass")
    pass_entry = os.environ.get(
        "UTIL_SECURITY_TARTUFI_DOCKERHUB_TOKEN", "pass docker entry fix me"
    )

    if not pass_entry:
        print(
            "error UTIL_SECURITY_TARTUFI_DOCKERHUB_TOKEN environment variable not set"
        )
        print(
            "please set UTIL_SECURITY_TARTUFI_DOCKERHUB_TOKEN to the pass entry name for your dockerhub token"
        )
        sys.exit(1)

    try:
        result = subprocess.run(
            [pass_binary, "show", pass_entry],
            capture_output=True,
            text=True,
            check=True,
        )
        token = result.stdout.strip().split("\n")[0]
        return token
    except subprocess.CalledProcessError as e:
        print(f"error retrieving dockerhub token from pass {e}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"error {pass_binary} command not found")
        print(f"please make sure {pass_binary} is installed and in your path")
        sys.exit(1)


def get_repositories(
    docker_username: str, docker_hub_token: str
) -> List[Dict[str, Any]]:
    repositories_list = (
        f"https://hub.docker.com/v2/repositories/{docker_username}/?page_size=100"
    )
    repos_headers = {"Authorization": f"JWT {docker_hub_token}"}

    print(pcolor(f"fetching repositories for {docker_username}"))
    try:
        repos_response = requests.get(repositories_list, headers=repos_headers)
        repos_response.raise_for_status()
        return repos_response.json().get("results", [])
    except requests.exceptions.RequestException as e:
        print(f"error fetching repositories {str(e)}")
        sys.exit(1)


def get_tags(
    docker_username: str, repository_name: str, docker_hub_token: str
) -> List[Dict[str, Any]]:
    tags_url = f"https://hub.docker.com/v2/repositories/{docker_username}/{repository_name}/tags/?page_size=100"
    tags_headers = {"Authorization": f"JWT {docker_hub_token}"}

    print(pcolor(f"fetching tags for {docker_username}/{repository_name}"))
    try:
        tags_response = requests.get(tags_url, headers=tags_headers)
        tags_response.raise_for_status()
        return tags_response.json().get("results", [])
    except requests.exceptions.RequestException as e:
        print(f"error fetching tags {str(e)}")
        return []


def scan_docker_image(image_name: str) -> Dict[str, Any]:
    cmd = [
        "docker",
        "run",
        "--rm",
        "--cpus=1",
        "--memory=2g",
        "trufflesecurity/trufflehog:latest",
        "docker",
        "--image",
        image_name,
        "--results=verified,unknown",
        "--json",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        output_lines = result.stdout.strip().split("\n")

        findings = []
        for line in output_lines:
            line = line.strip()
            if not line:
                continue

            try:
                data = json.loads(line)
                if "SourceMetadata" in data:
                    findings.append(data)
            except json.JSONDecodeError:
                pass

        return {"image": image_name, "success": True, "findings": findings}
    except Exception as e:
        print(f"error scanning {image_name} {str(e)}")
        return {"image": image_name, "success": False, "error": str(e), "findings": []}


def extract_secret_details(finding: Dict[str, Any]) -> Dict[str, Any]:
    detector = finding.get("DetectorName", "Unknown")
    redacted = finding.get("Redacted", "")
    verified = finding.get("Verified", False)

    source_metadata = finding.get("SourceMetadata", {})
    source_data = source_metadata.get("Data", {})
    docker_info = source_data.get("Docker", {})
    file_path = docker_info.get("file", "Unknown path")

    return {
        "detector": detector,
        "redacted": redacted,
        "verified": verified,
        "file_path": file_path,
    }


def format_finding_details(findings: List[Dict[str, Any]]) -> str:
    if not findings:
        return ""

    summary_details = []

    for finding in findings:
        details = extract_secret_details(finding)
        detector = details["detector"]
        redacted = details["redacted"]
        verified = details["verified"]

        status = "✓" if verified else "?"
        summary_text = f"{detector}:{redacted} ({status})"
        summary_details.append(summary_text)

    summary = ", ".join(summary_details[:2]) + (
        "..." if len(summary_details) > 2 else ""
    )

    return summary


def display_summary(scan_results: List[Dict[str, Any]]) -> None:
    print("\nscan summary")

    header = f"{'NAME':<50} {'STATUS':<10} {'SECRETS':<10} {'DETAILS':<50}"
    separator = "-" * 120
    print(f"{header}")
    print(separator)

    total_findings = 0

    for result in scan_results:
        image = result["image"]
        status = "Success" if result["success"] else "Failed"
        findings_count = len(result["findings"])
        total_findings += findings_count

        details = (
            format_finding_details(result["findings"]) if findings_count > 0 else ""
        )

        row = f"{image:<50} {status:<10} {findings_count:<10} {details:<50}"
        print(row)

    if total_findings > 0:
        print(f"\ntotal secrets found: {total_findings}")
    else:
        print("\nno secrets found in any scanned images")

    if total_findings > 0:
        display_detailed_findings(scan_results)


def display_detailed_findings(scan_results: List[Dict[str, Any]]) -> None:
    print("\nDETAILED FINDINGS")
    print("=" * 80)

    for result in scan_results:
        image = result["image"]
        findings = result["findings"]

        if not findings:
            continue

        print(f"\nIMAGE: {image}")
        print("-" * 80)

        for i, finding in enumerate(findings, 1):
            details = extract_secret_details(finding)
            verified_status = "✓ VERIFIED" if details["verified"] else "? UNVERIFIED"

            print(f"\n  Finding #{i} - {verified_status}")
            print(f"  Detector: {details['detector']}")
            print(f"  Secret: {details['redacted']}")
            print(f"  Location: {details['file_path']}")
            print("  " + "-" * 60)


def display_repositories(repositories: List[Dict[str, Any]]) -> None:
    if not repositories:
        print("no repositories found for this user")
        return

    print("\nAVAILABLE REPOSITORIES")
    header = f"{'#':<5} {'REPOSITORY':<30} {'PULLS':<15} {'DESCRIPTION':<40}"
    separator = "-" * 90
    print(f"{header}")
    print(separator)

    for i, repo in enumerate(repositories, 1):
        pulls = f"{repo.get('pull_count', 0):,}"
        description = repo.get("description", "") or ""
        if len(description) > 38:
            description = description[:38] + "..."

        print(f"{i:<5} {repo['name']:<30} {pulls:<15} {description:<40}")


def display_tags(tags: List[Dict[str, Any]], repo_name: str) -> None:
    if not tags:
        print(f"no tags found for {repo_name}")
        return

    print(f"\nTAGS FOR {repo_name}")
    header = f"{'#':<5} {'TAG':<30} {'LAST UPDATED':<30} {'SIZE':<15}"
    separator = "-" * 80
    print(f"{header}")
    print(separator)

    for i, tag in enumerate(tags, 1):
        size = tag.get("full_size", 0) / (1024 * 1024)
        print(
            f"{i:<5} {tag['name']:<30} {tag.get('last_updated', 'Unknown'):<30} {size:.2f} MB"
        )


def get_user_selection(options_count: int, prompt: str) -> List[int]:
    while True:
        print(pcolor(f"\n{prompt}"))
        selection = input(pcolor("> ")).strip().lower()

        if selection == "all":
            return list(range(options_count))
        elif selection == "":
            return []

        try:
            indices = []
            for part in selection.split(","):
                part = part.strip()
                if "-" in part:
                    start, end = map(int, part.split("-"))
                    indices.extend(range(start - 1, end))
                else:
                    indices.append(int(part) - 1)

            if any(idx < 0 or idx >= options_count for idx in indices):
                print("invalid selection some numbers are out of range")
                continue

            return indices
        except ValueError:
            print("invalid input please enter comma-separated numbers or ranges")


def select_images_to_scan(
    repositories: List[Dict[str, Any]], docker_username: str, docker_hub_token: str
) -> List[str]:
    if not repositories:
        print("no repositories found for this user")
        return []

    display_repositories(repositories)

    selection_prompt = "select repositories to scan (comma-separated numbers ranges like 1-3 'all' for all enter to skip)"
    repo_indices = get_user_selection(len(repositories), selection_prompt)

    if not repo_indices:
        print("no repositories selected")
        return []

    selected_repos = [repositories[idx] for idx in repo_indices]
    images_to_scan = []

    for repo in selected_repos:
        repo_name = repo["name"]
        tags = get_tags(docker_username, repo_name, docker_hub_token)

        if not tags:
            print(f"no tags found for {docker_username}/{repo_name}")
            continue

        display_tags(tags, f"{docker_username}/{repo_name}")

        tag_prompt = f"select tags to scan for {repo_name} (comma-separated numbers ranges like 1-3 'all' for all enter to skip)"
        tag_indices = get_user_selection(len(tags), tag_prompt)

        if not tag_indices:
            print(f"no tags selected for {repo_name} skipping")
            continue

        selected_tags = [tags[idx]["name"] for idx in tag_indices]

        for tag in selected_tags:
            images_to_scan.append(f"{docker_username}/{repo_name}:{tag}")

    return images_to_scan


def display_selected_images(images: List[str]) -> None:
    if not images:
        print("no images selected for scanning")
        return

    print("\nSELECTED IMAGES FOR SCANNING")
    print("=" * 80)

    repos = {}
    for image in images:
        repo, tag = image.rsplit(":", 1)
        if repo not in repos:
            repos[repo] = []
        repos[repo].append(tag)

    for repo, tags in repos.items():
        print(f"\n{repo}")
        for i, tag in enumerate(sorted(tags), 1):
            print(f"  {i}. {tag}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Scan Docker images for secrets using TruffleHog"
    )
    parser.add_argument("--username", "-u", required=True, help="DockerHub username")
    parser.add_argument(
        "--db-path",
        default=os.environ.get("UTIL_SECURITY_TARTUFI_DB_PATH", "tartufi.db"),
        help="Path to SQLite database (default from UTIL_SECURITY_TARTUFI_DB_PATH env or tartufi_scans.db)",
    )

    args = parser.parse_args()

    banner = """
    ┌─────────────────────┐
    │      TARTUFI        │
    │ oh, just found one! │
    └─────────────────────┘
    """
    print(pcolor(banner))

    print(pcolor(f"using database at {args.db_path}"))
    conn = setup_database(args.db_path)

    docker_hub_token = get_docker_hub_token()
    repositories = get_repositories(args.username, docker_hub_token)
    images_to_scan = select_images_to_scan(
        repositories, args.username, docker_hub_token
    )

    if not images_to_scan:
        print("no images selected for scanning")
        sys.exit(0)

    display_selected_images(images_to_scan)

    scan_results = []
    for i, image in enumerate(images_to_scan, 1):
        image_hash = get_image_hash(image)
        existing_scan = check_image_scanned(conn, image_hash)

        if existing_scan:
            print(
                pcolor(
                    f"skipping {image} (already scanned) ({i}/{len(images_to_scan)})"
                )
            )
            image_name, findings_count, findings_data = existing_scan
            findings = json.loads(findings_data) if findings_data else []
            scan_results.append({"image": image, "success": True, "findings": findings})
            continue

        print(pcolor(f"scanning {image} ({i}/{len(images_to_scan)})"))
        result = scan_docker_image(image)

        save_scan_result(conn, image_hash, image, result["findings"])
        scan_results.append(result)

    display_summary(scan_results)
    conn.close()


if __name__ == "__main__":
    main()
