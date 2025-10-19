[![built with nix](https://builtwithnix.org/badge.svg)](https://builtwithnix.org)

# My binaries

This repo contains a collection of binaries, scripts, amenities that I use on a daily basis and created over time.

The binaries are written mostly in python/bash and also most of them have tests with a good coverage.

The repo is heavily under development and I will add more binaries that I built over time when I have time to clean them up and make them public.

## Installation

Each of them can be installed easily with nix (with the dependencies managed) or copied them (without the dependencies managed).

## Naming convention

Based on my personal preference, I use a simple naming convention for the binaries:

```
util-<category>-<name>-<eventual-subname>
```

Some (not all) of them start with `util` so it is easy to find them in the terminal

## Categories

Some of the binaries are:

### System

- [system](./system/): various linux related utilities

### Security

- [pass-bitwarden-sync](./security/pass-bitwarden-sync): sync your pass passwords into a bitwarden vault
- [tartufi](./security/tartufi): simple [trufflehog](https://github.com/trufflesecurity/trufflehog) companion that will let you scan an entire docker registry organization for secrets

### Privacy

- [util_privacy_telegram-cleanup](./privacy/telegram-cleanup): cleanup your telegram account: delete all messages older than x days from groups and dms

### Productivity

- [task-sync-lib](./productivity/task-sync-lib): a library to sync your tasks with different systems (logseq and youtrack atm)
- [nix](./productivity/nix-specific/): nix specific productivity tools
- [ai](./productivity/ai/) mcp servers that I use with AI tools
