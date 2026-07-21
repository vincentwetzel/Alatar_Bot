# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Documentation

- Reworked the README to match the current command set, configuration flow, and runtime behavior.
- Updated the contributing guide with current coding and testing expectations.
- Cleaned up the changelog so future entries can track changes in a consistent format.

## [2.1.0] - 2025

### Code Quality and Refactoring

- Encapsulated mutable global state in `BotState`.
- Moved hardcoded strings and numbers into module-level constants.
- Removed legacy migration code for `admin_dicord_id.txt`.
- Standardized timestamps on `datetime.now(UTC)`.
- Tightened type annotations across settings loading and runtime state.
- Added a dedicated constants section and shared UTC helper.
- Removed unused typing imports and redundant guard logic.

## [2.0.0] - 2024

### Major Modernization

- Migrated to `discord.py 2.x`.
- Added slash commands for modern Discord interactions.
- Replaced deprecated member activity access with `member.activities`.
- Replaced manual event-loop scheduling with `asyncio.create_task()`.
- Centralized configuration in `settings.json`.
- Added `pyproject.toml` for packaging and tooling.
- Improved logging, DM handling, and error handling across the bot.

### Removed

- Legacy `activity` attribute usage.
- Manual `get_event_loop()` calls.
- Deprecated enum access patterns.
