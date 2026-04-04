# Alatar Bot

A Discord bot for server management, user activity monitoring, and automated voice channel organization.

## 📋 Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Bot Commands](#bot-commands)
- [Project Structure](#project-structure)
- [Logging](#logging)
- [Dependencies](#dependencies)
- [Trouleshooting](#troubleshooting)
- [License](#license)

## ✨ Features

- **Slash Commands**: Modern Discord application commands (`/insult`, `/serverinfo`)
- **User Activity Monitoring**: Tracks and logs member status changes, activities, and voice channel movements
- **Automated Voice Channel Management**: Automatically invites or moves members to appropriate voice channels based on their current game/activity
- **Role Management**: Automatically assigns roles to new members (e.g., "Plebs" role)
- **Welcome System**: Welcomes new members and handles join/leave events
- **Ignore System**: Allows administrators to ignore specific users from activity logging
- **Insult Command**: Fetches random insults from an external API for fun interactions
- **Admin Notifications**: Sends detailed logs and notifications to the server owner via DM
- **Channel Management**: Monitors and logs channel creation/deletion events
- **Log Rotation**: Automatic log file cycling to prevent disk space issues

## 📦 Prerequisites

- Python 3.10 or higher
- A Discord Bot Token
- Administrator access to your Discord server

## 🚀 Installation

1. **Clone or download the repository**

2. **Install required dependencies**

   ```bash
   pip install -r requirements.txt
   ```

   Or use the modern Python installer:

   ```bash
   pip install .
   ```

3. **Configure the bot** (see [Configuration](#configuration) section)

4. **Run the bot**

   ```bash
   python Alatar_Bot.py
   ```

## ⚙️ Configuration

The bot uses a centralized `settings.json` file for configuration. This file is automatically created on first run if it doesn't exist.

### Settings File Structure

**`settings.json`**:
```json
{
    "discord_token": "your-bot-token-here",
    "admin_discord_id": "123456789012345678",
    "log_max_bytes": 5242880,
    "log_backup_count": 5,
    "ignored_members": []
}
```

### Configuration Fields

| Field | Description | Default | Required |
|-------|-------------|---------|----------|
| `discord_token` | Your Discord bot token from the Developer Portal | - | Yes |
| `admin_discord_id` | Discord user ID of the bot administrator (18-digit number) | - | Yes |
| `log_max_bytes` | Maximum size of discord.log before rotation (in bytes) | 5242880 (5 MB) | No |
| `log_backup_count` | Number of rotated log files to keep | 5 | No |
| `ignored_members` | List of usernames excluded from activity logging | `[]` | No |

### Getting Your Credentials

**Discord Bot Token:**
1. Go to the [Discord Developer Portal](https://discord.com/developers/applications)
2. Create an application → Add Bot → Copy Token

**Admin Discord ID:**
1. Enable Developer Mode in Discord settings
2. Right-click your username → Copy ID

## 🎮 Usage

### Starting the Bot

```bash
python Alatar_Bot.py
```

On first run, the bot will prompt you for:
- Discord Bot Token (if not set in `settings.json`)
- Admin Discord ID (if not set in `settings.json`)

### Bot Behavior

Once running, the bot will:
1. Monitor all member activity in connected servers
2. Automatically organize voice channels based on games being played
3. Log all activity to the `logs/` directory (one file per user)
4. Send notifications to the admin via DM
5. Assign the "Plebs" role to new members automatically

## 🤖 Bot Commands

### Slash Commands (Application Commands)

Modern Discord commands accessible via the `/` menu.

| Command | Description | Example |
|---------|-------------|---------|
| `/insult <user>` | Sends a random insult to a target user | `/insult @JohnDoe` |
| `/serverinfo` | Displays server information | `/serverinfo` |

### Legacy Prefix Commands (Admin)

These commands use the `!` prefix and are restricted to the bot owner.

| Command | Description | Example |
|---------|-------------|---------|
| `!on` | Turn on admin notifications | `!on` |
| `!off [seconds]` | Turn off admin notifications (optional delay) | `!off` or `!off 300` |
| `!ignore <username>` | Add a user to the ignore list | `!ignore SpamUser` |
| `!unignore <username>` | Remove a user from the ignore list | `!unignore SpamUser` |
| `!unignoreall` | Clear the entire ignore list | `!unignoreall` |
| `!printignored` | Display currently ignored users | `!printignored` |
| `!printnotignored` | Display users not being ignored | `!printnotignored` |
| `!printseeking` | Show members seeking playmates | `!printseeking` |
| `!invite <@user>` | Invites a user to your current voice channel | `!invite @Friend` |

## 📁 Project Structure

```
Alatar_Bot.py        # Main bot script
pyproject.toml       # Modern Python project configuration
requirements.txt     # Python dependencies
settings.json        # Centralized bot config (git-ignored)
.gitignore           # Git ignore rules
README.md            # This file
CHANGELOG.md         # Version history
CONTRIBUTING.md      # Contribution guidelines
AGENTS.md            # Agent/LLM coding guidelines
discord.log          # Rotating bot log (git-ignored)
logs/
    └── {username}.txt  # Per-user activity logs (git-ignored)
```

## 📝 Logging

The bot implements comprehensive logging:

### Log Files

- **`discord.log`**: General bot logs (created automatically)
- **`logs/{username}.txt`**: Individual user activity logs (one file per user)

### Log Information

Each log entry includes:
- Date (MM-DD-YY format)
- Time (12-hour format with AM/PM)
- Activity description

### Notification Suppression

Use `!off` to temporarily suppress DM notifications. Notifications will be queued and sent when you use `!on`.

## 📦 Dependencies

- **discord.py** - Discord API wrapper
- **requests** - HTTP library for API calls
- Standard library modules:
  - `asyncio` - Asynchronous I/O
  - `logging` - Logging framework
  - `json` - JSON processing
  - `os` - Operating system interface
  - `datetime` - Date/time handling
  - `typing` - Type hints
  - `collections` - Data structures

## 🔧 Troubleshooting

### Common Issues

**Bot doesn't respond to commands:**
- Ensure the bot has proper permissions in your Discord server
- Check that you're using the correct command prefix (`!`)
- Verify the bot is online and connected

**Token or Admin ID errors:**
- Check `settings.json` for proper formatting
- Ensure `discord_token` contains a valid token
- Ensure `admin_discord_id` contains only an 18-digit number
- Regenerate token from Discord Developer Portal if needed

**Voice channel features not working:**
- Ensure bot has "Manage Channels" and "Move Members" permissions
- Check that members have activities/games enabled in their status

**File not found errors:**
- The bot will create missing settings files automatically
- Check file permissions if running on restricted systems

## 📄 License

This project is provided as-is for personal Discord server management use.

## 📏 Code Standards

This project enforces strict code quality standards:

- **PEP 8** — Style guide compliance (naming, formatting, line length ≤ 120)
- **PEP 257** — Docstring conventions (triple-quoted, descriptive)
- **PEP 484** — **Type hints are mandatory** on all functions and variables
- **Python 3.10+** syntax — modern type hints (`list[str]` not `List[str]`)

All contributions must adhere to these standards. See [CONTRIBUTING.md](CONTRIBUTING.md) and [AGENTS.md](AGENTS.md) for details.

## 👤 Author

Created by Vincent

## 🙏 Acknowledgments

- [Evil Insult API](https://evilinsult.com/) for the insult command
- Discord.py community for documentation and examples
