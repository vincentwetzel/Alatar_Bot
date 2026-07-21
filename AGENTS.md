# Agent Guidelines for Alatar Bot

## Project Overview

Alatar Bot is a Discord bot built with **discord.py 2.x** for server management, activity monitoring, and automated voice channel organization. It runs on **Python 3.10+**.

## Core Rules

### 1. PEP Compliance

All code **MUST** adhere to PEP standards:

- **PEP 8** — Style guide (naming, spacing, line length ≤ 120 chars)
- **PEP 257** — Docstring conventions (triple-quoted, imperative mood)
- **PEP 484** — Type hints on **all** function signatures and non-trivial variables
- **PEP 517/518** — Build system configuration via `pyproject.toml`
- **PEP 621** — Project metadata in `pyproject.toml`

### 2. Type Hints — Mandatory

- **Every** function, method, and variable must have explicit type hints.
- Use Python 3.10+ built-in generics (`list[str]`, `dict[str, int]`).
- Use `typing` module only for special types (`Any`, `Optional`, `Union`, `Protocol`).
- Return types must be explicit, including `None`.

```python
# ✅ Correct
async def get_channel(guild: discord.Guild, name: str) -> discord.TextChannel | None:
    ...

# ❌ Incorrect — missing type hints
async def get_channel(guild, name):
    ...
```

### 3. String Formatting

- Use **f-strings** exclusively. No `.format()`, `%` formatting, or `+` concatenation.

### 4. Async Patterns

- Use `asyncio.create_task()` for background tasks. **Never** `event_loop.call_later()`.
- Use `asyncio.to_thread()` for blocking I/O (e.g., `requests.get()`).

### 5. Discord.py Best Practices

- Use `discord.utils.get()` for lookups, **never** manual iteration.
- Use `member.activities` (list), **not** `member.activity` (deprecated).
- Slash commands use `@bot.tree.command()` with `Interaction`.
- Handle `discord.Forbidden` and `discord.HTTPException` on all DM/send operations.

### 6. Error Handling

- Use explicit `try/except` with specific exception types.
- Log errors with `logger.error/warning/info`.
- Never `raise error` silently — handle or log.

### 7. Settings

- **All** configuration lives in `settings.json` — no standalone config files.
- Use the `bot_state` instance (populated at startup via `load_settings()`).
- Persist changes with `save_settings(bot_state.settings)`.
- Never hardcode tokens, IDs, or paths.

### 8. Global State Management

- **Use `BotState` class** — All mutable state lives in `bot_state` instance.
- Access via `bot_state.admin_discord_id`, `bot_state.notifications_enabled`, etc.
- Avoid bare `global` declarations — use `bot_state` instead.

### 9. Constants

- Extract all magic strings/numbers to module-level `UPPER_SNAKE_CASE` constants.
- Group constants in dedicated `# Constants` section at top of file.
- Examples: `CHANNEL_NAME_WELCOME`, `VOICE_CHANNEL_BITRATE`, `PLAYMATE_CLEANUP_DELAY`.

### 10. Timezone Awareness

- Use `datetime.now(UTC)` for all timestamps.
- Use `_get_utc_now()` helper function for consistency.

## File Structure

```
Alatar_Bot.py        # Main bot source (single-file architecture)
pyproject.toml       # Build config and tool settings
requirements.txt     # Pip dependencies
settings.json        # Runtime config (git-ignored)
logs/                # Per-user activity logs (git-ignored)
discord.log          # Rotating bot log (git-ignored)
```

## Dependencies

- `discord.py>=2.3.0`
- `requests>=2.31.0`

## Testing Before Completion

Before marking a task as done:
1. Run `python -m py_compile Alatar_Bot.py` — **must pass**
2. Verify no IDE warnings/errors remain
3. Confirm type hints are present and correct
