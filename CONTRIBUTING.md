# Contributing to Alatar Bot

Thank you for your interest in contributing to Alatar Bot! This document provides guidelines and instructions for contributing.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone <your-fork-url>`
3. Create a feature branch: `git checkout -b feature/my-new-feature`
4. Install dependencies: `pip install -r requirements.txt`
5. Make your changes
6. Test your changes thoroughly
7. Commit your changes: `git commit -am 'Add some feature'`
8. Push to your branch: `git push origin feature/my-new-feature`
9. Submit a pull request

## Code Style

- **PEP 8** compliance — naming, spacing, line length ≤ 120 chars
- **PEP 257** docstrings — triple-quoted, imperative mood
- **PEP 484** type hints — **mandatory** on all functions, methods, and non-trivial variables
- Use Python 3.10+ built-in generics (`list[str]`, `dict[str, int]`) — avoid `typing.List`, `typing.Dict`
- Use **f-strings** for all string formatting
- Use `asyncio.create_task()` for background tasks, not `event_loop.call_later()`
- Use `discord.utils.get()` or `guild.get_channel_named()` instead of manual iteration
- Prefer `asyncio.to_thread()` for blocking I/O operations
- Use modern discord.py 2.x patterns (application commands, intents, etc.)

## Adding Commands

When adding new bot commands:

1. **Prefer slash commands** using `@bot.tree.command()` for public commands
2. Use prefix commands (`@bot.command()`) only for admin-only utilities
3. Include proper type hints for parameters
4. Add comprehensive docstrings explaining the command
5. Implement appropriate permission checks (`@commands.check`)
6. Handle errors gracefully with try/except
7. Log important actions using `logger.info/warning/error`
8. Use `interaction.response.send_message()` for slash commands
9. Use `ephemeral=True` for admin-only responses

## Testing

Before submitting changes:

- Test all new features thoroughly
- Ensure existing functionality still works
- Verify the bot connects and runs without errors
- Check that logging works correctly
- Test slash commands appear in Discord's command menu
- Run `python -m py_compile Alatar_Bot.py` — **must pass with zero errors**
- Verify **all functions have type hints** — no exceptions
- Verify **PEP 8 compliance** — run `ruff check` if available

## Requirements

When reporting issues, please include:

- A clear description of the problem
- Steps to reproduce the issue
- Expected vs. actual behavior
- Python version (must be 3.10+) and discord.py version
- Any relevant error messages or logs

## Code of Conduct

- Be respectful and constructive
- Focus on what is best for the community
- Accept constructive criticism gracefully

## Questions?

If you have questions about contributing, feel free to open an issue or contact the maintainer.
