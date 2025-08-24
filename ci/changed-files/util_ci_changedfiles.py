#!/usr/bin/env python3

import os
import fnmatch
import logging
import argparse
import git

logging.basicConfig(level=logging.INFO, format="%(message)s")


def diff_finder(
    include: list[str] | None = None,
    exclude: list[str] | None = None,
    untracked: bool = False,
) -> list[str]:
    repo = git.Repo(".")

    if untracked:
        files = repo.untracked_files
    elif os.getenv("CI"):
        base_ref = os.getenv("GITHUB_BASE_REF")
        head_ref = os.getenv("GITHUB_HEAD_REF") or os.getenv("GITHUB_REF_NAME")
        if "origin" in [r.name for r in repo.remotes]:
            try:
                repo.remotes.origin.fetch([base_ref, head_ref])
            except Exception as e:
                logging.debug(f"skip fetch: {e}")
        base_sha = repo.git.rev_parse(f"origin/{base_ref}")
        head_sha = repo.git.rev_parse(f"origin/{head_ref}")
        files = repo.git.diff("--name-only", f"{base_sha}...{head_sha}").splitlines()
    else:
        files = [d.a_path for d in repo.index.diff(None)]  # unstaged
        files += [d.a_path for d in repo.index.diff("HEAD")]  # staged

    files = sorted(set(files))
    if include:
        files = [f for f in files if any(fnmatch.fnmatch(f, pat) for pat in include)]
    if exclude:
        files = [
            f for f in files if not any(fnmatch.fnmatch(f, pat) for pat in exclude)
        ]
    return files


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--include", nargs="*", default=None)
    parser.add_argument("--exclude", nargs="*", default=None)
    parser.add_argument("--untracked", action="store_true")
    args = parser.parse_args()

    for f in diff_finder(args.include, args.exclude, args.untracked):
        logging.info(f)
