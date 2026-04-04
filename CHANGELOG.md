# Changelog

All notable changes to this project will be documented in this file.

## [2.1.0] - 2025

### Code Quality & Refactoring

#### Architecture Improvements
- **Encapsulated global state** — Replaced 6 scattered globals with `BotState` class (`bot_state`) for centralized state management
- **Extracted magic strings** — All hardcoded strings now live as constants (`CHANNEL_NAME_WELCOME`, `PLEB_ROLE_NAME`, `VOICE_CHANNEL_BITRATE`, etc.)
- **Removed legacy migration code** — Deleted `admin_dicord_id.txt` migration dead code
- **Timezone-aware datetimes** — All timestamps now use `datetime.now(UTC)` instead of naive `datetime.now()`

#### Type System
- **Removed `Any` type** — Narrowed `load_settings()` return type to explicit `dict[str, str | int | list[str]]`
- **Comprehensive type hints** — Every variable, parameter, and return type now explicitly typed
- **Consistent naming conventions** — All globals use `UPPER_SNAKE_CASE`, parameters use descriptive `snake_case`

#### Code Organization
- **Constants section** — Added dedicated `# Constants` section at top of file
- **Helper functions** — Extracted `_get_utc_now()` for UTC datetime consistency
- **Simplified guards** — Removed redundant `if bot_owner:` check in `send_admin_notification()`
- **Consolidated imports** — Removed unused `typing.Any` import

## [2.0.0] - 2024

### Major Modernization

#### API Updates
- Migrated to **discord.py 2.x** with full support for application commands
- Added **slash commands** (`/insult`, `/serverinfo`) using `discord.app_commands`
- Replaced deprecated `member.activity` with `member.activities` (list-based)
- Updated enum access to modern patterns (`Status.online` instead of `discord.enums.Status.online`)
- Replaced `event_loop.call_later()` with `asyncio.create_task()` + `asyncio.sleep()`
- Used `guild.get_channel_named()` instead of manual channel iteration
- Added `intents.message_content` for modern Discord intent requirements

#### Code Quality
- Replaced all string concatenation with **f-strings** throughout
- Added comprehensive type hints (`list[str]`, `defaultdict`, etc.)
- Added proper error handling with `try/except` blocks
- Implemented global command error handler (`on_command_error`)
- Added `@commands.check` decorators for permission checks
- Used `os.makedirs(exist_ok=True)` instead of manual directory checks
- Replaced blocking API calls with `asyncio.to_thread()` for non-blocking HTTP requests

#### Architecture
- Centralized configuration in `settings.json`
- Added `pyproject.toml` for modern Python packaging
- Removed global mutation patterns where possible
- Added proper logging throughout with `logger.info/warning/error`
- Separated utility functions from event handlers
- Improved DM error handling (catches `discord.Forbidden`)

#### Commands
- Converted `!insult` to slash command `/insult`
- Added `/serverinfo` command with embed display
- Kept admin commands as prefix commands for simplicity
- Added proper ephemeral responses for admin commands

### Removed
- Legacy `activity` attribute usage (now uses `activities` list)
- Manual `get_event_loop()` calls
- Deprecated enum access patterns
