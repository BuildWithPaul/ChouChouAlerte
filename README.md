# ChouChouAlerte

Train disruption alert system. Get notified on Telegram when your daily SNCF routes have disruptions.

## Features

- **Journey monitoring**: Add routes with departure/arrival stations, time windows, and day selection
- **Day toggles**: Enable/disable notification per day of the week
- **Telegram alerts**: Receive disruption notifications via your own Telegram bot
- **Multiple auth**: Sign in with Google, GitHub, or continue as guest
- **Persistent data**: SQLite database stored outside Docker container
- **SNCF API**: Backend-only integration, API key never exposed to frontend

## Quick Start

```bash
# 1. Clone and configure
cp .env.example .env
# Edit .env with your SNCF API token and OAuth credentials

# 2. Build and run
docker compose up -d

# 3. Access at http://localhost:5000/
```

## Deployment with Caddy

For production with subpath `/chouchoularte/`, add to your Caddyfile:

```caddyfile
handle_path /chouchoularte/* {
    reverse_proxy chouchoularte:5000 {
        header_up X-Forwarded-Prefix /chouchoularte
    }
}
redir /chouchoularte /chouchoularte/ permanent
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SNCF_API_TOKEN` | Yes | SNCF API token (never exposed to frontend) |
| `SECRET_KEY` | Yes | Flask session secret key |
| `APPLICATION_ROOT` | No | Subpath for deployment (default: `/chouchoularte`) |
| `GOOGLE_CLIENT_ID` | No | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | No | Google OAuth client secret |
| `GITHUB_CLIENT_ID` | No | GitHub OAuth client ID |
| `GITHUB_CLIENT_SECRET` | No | GitHub OAuth client secret |
| `DISRUPTION_CHECK_INTERVAL` | No | Check interval in seconds (default: 300) |

## Telegram Bot Setup

1. Open Telegram, find **@BotFather**
2. Send `/newbot`, choose a name and username
3. Copy the HTTP API token
4. Start a conversation with your new bot (send it any message)
5. Enter the token in ChouChouAlerte's Telegram setup page

## Data Persistence

The SQLite database and all user data are stored in `./data/chouchou.db`, which is mounted as a Docker volume. This survives container restarts and rebuilds.