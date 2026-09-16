"""max_ai.discord.bot forwarder."""
try:
    from max_ai.discord.bot import split_discord_message, MaxDiscordBot, create_max_bot
except (ImportError, ModuleNotFoundError):
    from src.max_ai.discord.bot import split_discord_message, MaxDiscordBot, create_max_bot  # type: ignore[no-redef]

__all__ = ["split_discord_message", "MaxDiscordBot", "create_max_bot"]
