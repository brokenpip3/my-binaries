# Telegram cleanup

Delete messages older than 30days from a telegram group chat or dm, both attended and unattended.

## Usage

Since the telegram token is super sensitive I use pass to retrieve the secret at runtime.

Necessary env:

```
UTIL_PRIVACY_TELEGRAM_CLEANUP_PASS_CLI = "pass"
UTIL_PRIVACY_TELEGRAM_CLEANUP_PASS_ENTRY = "telegram-api"
```

TDB
