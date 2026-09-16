"""max_ai.discord forwarder."""
try:
    from max_ai.discord.bot import create_max_bot, MaxDiscordBot
except (ImportError, ModuleNotFoundError):
    from src.max_ai.discord.bot import create_max_bot, MaxDiscordBot  # type: ignore[no-redef]

__all__ = ["create_max_bot", "MaxDiscordBot"]
