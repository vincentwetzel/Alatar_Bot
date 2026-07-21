# Contributing to Alatar Bot

Thanks for helping improve Alatar Bot.

## Getting Started

1. Fork the repository.
2. Clone your fork.
3. Create a feature branch.
4. Install dependencies with `pip install -r requirements.txt`.
5. Make your changes.
6. Test your changes.
7. Commit your work.
8. Push the branch and open a pull request.

## Code Style

- Follow PEP 8, including line length at or below 120 characters.
- Use PEP 257 docstrings in imperative mood.
- Add explicit type hints to every function signature and non-trivial variable.
- Prefer Python 3.10 built-in generics such as `list[str]` and `dict[str, int]`.
- Use f-strings for all string formatting.
- Use `asyncio.create_task()` for background tasks.
- Use `asyncio.to_thread()` for blocking I/O.
- Use `discord.utils.get()` for lookups instead of manual iteration.
- Follow discord.py 2.x patterns, especially slash commands and `Interaction`.
- Keep all mutable runtime state on `bot_state` instead of module-level globals.
- Store configuration in `settings.json` and persist updates with `save_settings(bot_state.settings)`.

## Adding Commands

When adding or changing commands:

1. Prefer slash commands with `@bot.tree.command()`.
2. Add type hints for all parameters and return values.
3. Include clear docstrings.
4. Apply permission checks where needed.
5. Handle errors with specific `try/except` blocks.
6. Log important actions with `logger.info`, `logger.warning`, or `logger.error`.
7. Use `interaction.response.send_message()` for slash command responses.
8. Use `ephemeral=True` for admin-only responses.
9. Update the README command table if the user-facing surface changes.

## Testing

Before submitting changes, run:

```bash
python -m py_compile Alatar_Bot.py
```

Also verify:

- The bot starts without errors.
- Slash commands sync successfully.
- Type hints remain complete and accurate.
- Logging still works as expected.
- Settings changes round-trip through `settings.json`.

If `ruff` is available, run it as well.

## Reporting Issues

When filing a bug report, include:

- What you expected to happen
- What actually happened
- Steps to reproduce
- Your Python version
- Your `discord.py` version
- Any relevant log output

## Code of Conduct

- Be respectful and constructive.
- Focus on what helps the project and its users.
- Accept feedback with openness.
