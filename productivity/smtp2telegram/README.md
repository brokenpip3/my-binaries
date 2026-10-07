# smtp2telegram

SMTP server that receives emails and forwards them to telegram users

## Usage

```bash
SMTP2TG_BOT_TOKEN=123456:ABC-DEF1234gh \
SMTP2TG_DEFAULT_CHAT_ID=987654321 \
smtp2telegram

smtp2telegram --config ~/.config/smtp2telegram/config.toml
```

## Config

Config file is optional — use env vars, a TOML file, or both (env vars override).

### Env vars

| Variable | Description |
|---|---|
| `SMTP2TG_BOT_TOKEN` | Telegram bot token from [@BotFather](https://t.me/BotFather) |
| `SMTP2TG_DEFAULT_CHAT_ID` | Telegram chat ID for emails without a specific route |

### TOML config

```toml
[telegram]
bot_token = "123456:ABC-DEF1234gh"

[routing]
"alerts@my-domain.com" = "111111"
"invoices@my-domain.com" = "222222"
default = "987654321"
```
