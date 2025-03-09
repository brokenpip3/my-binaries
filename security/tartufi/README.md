# Tartufi

`tartufi` is a simple trufflehog companion that will let you scan an entire docker registry organization for secrets.

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
