# Alatar Bot

Alatar Bot is a Discord bot for server management, activity monitoring, and automated voice channel organization.
It is built with `discord.py 2.x` and targets Python 3.10+.

## Features

- Slash commands for moderation and fun interactions
- User activity tracking for presence, voice state, and channel events
- Automated voice channel organization based on selected games or activities
- Welcome and role automation for new members
- Ignore list management for activity logging
- DM notifications to the configured admin
- Rotating log files for bot output and per-user activity history

## Requirements

- Python 3.10 or newer
- A Discord bot token
- The Discord user ID of the admin account that should receive notifications

## Installation

1. Clone or download this repository.
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

   You can also install the project as a package:

   ```bash
   pip install .
   ```

3. Run the bot:

   ```bash
   python Alatar_Bot.py
   ```

## Configuration

Runtime configuration lives in `settings.json`.

The file is created automatically on first run if it does not already exist.

### Settings

```json
{
    "discord_token": "your-bot-token-here",
    "admin_discord_id": "123456789012345678",
    "log_max_bytes": 5242880,
    "log_backup_count": 5,
    "ignored_members": []
}
```

### Field Reference

| Field | Description | Required |
| --- | --- | --- |
| `discord_token` | Discord bot token from the Developer Portal | Yes |
| `admin_discord_id` | Discord user ID that receives admin notifications | Yes |
| `log_max_bytes` | Maximum size of `discord.log` before rotation | No |
| `log_backup_count` | Number of rotated log files to keep | No |
| `ignored_members` | Member display names excluded from activity logging | No |

### Environment Variables

These optional environment variables override values in `settings.json`:

- `DISCORD_TOKEN`
- `DISCORD_BOT_TOKEN`
- `ADMIN_DISCORD_ID`

## Usage

On startup, the bot loads settings, syncs slash commands, and connects to Discord.
If the bot is missing a token or admin ID, it prompts for them when run interactively.

## Commands

### Slash Commands

| Command | Description |
| --- | --- |
| `/ignore <target_member_name>` | Add a member display name to the ignore list |
| `/unignore <target_member_name>` | Remove a member display name from the ignore list |
| `/unignoreall` | Clear the ignore list |
| `/invite <invite_target>` | Invite a user to your current voice channel |
| `/printignored` | Show the current ignore list |
| `/printnotignored` | Show members not on the ignore list |
| `/printseeking` | Show members currently seeking playmates |
| `/insult <insult_target>` | Send a random insult to a user |
| `/serverinfo` | Display information about the current server |

### Prefix Commands

The bot still uses `!` as its command prefix for legacy command handling and error routing, but the primary user-facing commands are slash commands.

## Logging

- `discord.log` stores bot-level logs and rotates automatically.
- `logs/<display-name>.txt` stores per-member activity history.

## Project Structure

```text
Alatar_Bot.py      Main bot source
pyproject.toml     Packaging and tooling configuration
requirements.txt   Dependency list
settings.json      Runtime configuration
README.md          Project overview and setup
CHANGELOG.md       Version history
CONTRIBUTING.md    Contribution guide
AGENTS.md          Agent-specific coding instructions
discord.log        Rotating bot log
logs/              Per-user activity logs
```

## Dependencies

- `discord.py>=2.3.0`
- `requests>=2.31.0`

## Troubleshooting

- If slash commands do not appear, make sure the bot has been invited with the correct scopes and has permission to read the guild.
- If the bot cannot DM the admin, confirm the admin account accepts direct messages from the server.
- If voice organization is not working, verify the bot has `Manage Channels` and `Move Members` permissions.
- If the bot asks for configuration repeatedly, confirm `settings.json` is writable and contains valid JSON.

## License

This project is provided as-is for personal Discord server management use.

## Acknowledgments

- Evil Insult API for the insult command
- The Discord.py community for documentation and examples
