# Tartufi

`tartufi` is a simple [trufflehog](https://github.com/trufflesecurity/trufflehog) companion that will let you scan an entire docker registry organization for secrets.

It will ask the user for each repo which tags to scan and then save the results a sqlite db.

Like other script in this repo, will use `pass` command to retrieve the dockerhub token.

## Usage

`tartufi` needs 1 environment variable to work:

* `UTIL_SECURITY_TARTUFI_DOCKERHUB_TOKEN`: the pass entry that contains the dockerhub token

not mandatory but you can also pass:

* `UTIL_SECURITY_TARTUFI_PASS`: the pass command, default to `pass`
* `UTIL_SECURITY_TARTUFI_DB`: the path to the sqlite db, default to `tartufi.db`
* [`NO_COLOR`](https://no-color.org/): if set to any value, will disable colors

it also need docker to run the trufflehog container (by default is capped to 1cpu and 2GB of memory for reasons)

example output:
```bash
$ nix run .#tartufi -- -u trufflesecurity

    ┌─────────────────────┐
    │      TARTUFI        │
    │ oh, just found one! │
    └─────────────────────┘

using database at tartufi.db
fetching repositories for trufflesecurity

AVAILABLE REPOSITORIES
#     REPOSITORY                     PULLS           DESCRIPTION
------------------------------------------------------------------------------------------
1     driftwood                      407             Private key usage verification
2     trufflehog                     5,355,481       Find credentials all over the place
3     protos                         1,182
4     email-graffiti                 52              Vandalize old emails.
5     of-cors                        76              Suite for identifying and exploiting C...
6     secrets                        17,279
7     lint-robot                     1,704

select repositories to scan (comma-separated numbers ranges like 1-3 'all' for all enter to skip)
> 6
fetching tags for trufflesecurity/secrets

TAGS FOR trufflesecurity/secrets
#     TAG                            LAST UPDATED                   SIZE
--------------------------------------------------------------------------------
1     latest                         2023-06-20T22:20:35.869472Z    0.00 MB

select tags to scan for secrets (comma-separated numbers ranges like 1-3 'all' for all enter to skip)
> 1

SELECTED IMAGES FOR SCANNING
================================================================================

trufflesecurity/secrets
  1. latest

skipping trufflesecurity/secrets:latest (already scanned) (1/1)

scan summary
NAME                                               STATUS     SECRETS    DETAILS
------------------------------------------------------------------------------------------------------------------------
trufflesecurity/secrets:latest                     Success    1          AWS:AKIAXYZDQCEN4B6JSJQI (✓)

total secrets found: 1
```
