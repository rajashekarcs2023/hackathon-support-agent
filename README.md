# Discord Webhook Notifier

Sends an alert message to a Discord channel and pings a role when something goes wrong. Uses Discord webhooks — no bot account or gateway connection required.

## Setup

### 1. Create a Discord Webhook

1. Open your Discord server and go to **Server Settings > Integrations > Webhooks**
2. Click **New Webhook**
3. Choose the channel you want alerts sent to
4. Click **Copy Webhook URL**

### 2. Get the Role ID

1. Enable **Developer Mode** in Discord: User Settings > Advanced > Developer Mode
2. Right-click the role you want to ping in **Server Settings > Roles**
3. Click **Copy Role ID**

### 3. Fill in `.env`

Open `.env` and set the two new keys:

```
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
DISCORD_ROLE_ID=123456789012345678
```

## Usage

```python
from discord_client import DiscordWebhookClient

client = DiscordWebhookClient()
client.send("Something went wrong!")
```

## Running the Tests

```bash
python -m pytest tests/
```

Both tests run without needing real credentials — the send test mocks the webhook call.
