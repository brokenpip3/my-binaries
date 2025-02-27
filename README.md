# My binaries

## Introduction

This repo contains a collection of binaries, scripts, amenities that I use on a daily basis and created over time.

Each of them can be installed easily with nix (with the dependencies managed) or copied them (without the dependencies managed).

The binaries are written mostly in python/bash and also most of them have tests with a good coverage.

The repo is heavily under development and I will add more binaries over time.

## Naming convention

Based on my personal preference, I use a simple naming convention for the binaries:

```
util-<category>-<name>-<eventual-subname>
```

Each of them start with `util` so it is easy to find them in the terminal

## Categories

### Security

- [pass-bitwarden-sync](./security/pass-bitwarden-sync): sync your pass passwords into a bitwarden vault

### Privacy

- [telegram-cleaup](./privacy/telegram-cleanup): cleanup your telegram account: delete all messages older than x days from groups and dms

### Productivity

- [task-sync-lib](./productivity/task-sync-lib): a library to sync your tasks with different systems (logseq and youtrack atm)
