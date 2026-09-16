"""
max_ai.discord.bot — Ready-to-use Discord AI Bot builder.
Handles channel isolation, message chunking (<2000 chars), typing indicators, and session resetting.
"""

from __future__ import annotations

import asyncio
from typing import Any, Optional, Union
try:
    from ..agent import MaxAgent
except (ImportError, ModuleNotFoundError):
    from max_ai.agent import MaxAgent  # type: ignore[no-redef]


def split_discord_message(text: str, limit: int = 1900) -> list[str]:
    """Split long text response into Discord-safe chunks (<2000 chars) preserving newlines."""
    if len(text) <= limit:
        return [text]
    chunks = []
    lines = text.split("\n")
    current_chunk = ""
    for line in lines:
        if len(current_chunk) + len(line) + 1 > limit:
            if current_chunk:
                chunks.append(current_chunk.strip())
                current_chunk = ""
            # If a single line exceeds the limit, hard-slice it
            if len(line) > limit:
                for i in range(0, len(line), limit):
                    chunks.append(line[i : i + limit])
                continue
        current_chunk += line + "\n"
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    return chunks


class MaxDiscordBot:
    """
    Wrapper for launching and managing a Discord AI Bot with MAX AI.
    """

    def __init__(
        self,
        discord_token: str,
        agent: Optional[MaxAgent] = None,
        model: str = "gemini-2.5-flash",
        api_key: Optional[str] = None,
        command_prefix: str = "!max ",
        system_prompt: str = "You are MAX, an intelligent and helpful AI assistant in Discord.",
        respond_to_mentions: bool = True,
        respond_to_dms: bool = True,
        enable_tools: bool = False,
    ):
        self.discord_token = discord_token
        self.command_prefix = command_prefix
        self.respond_to_mentions = respond_to_mentions
        self.respond_to_dms = respond_to_dms

        self.agent = agent or MaxAgent(
            model=model,
            api_key=api_key,
            system_prompt=system_prompt,
            enable_tools=enable_tools,
        )

    def run(self) -> None:
        """Start the Discord bot event loop."""
        try:
            import discord  # type: ignore[import-untyped]
            from discord.ext import commands  # type: ignore[import-untyped]
        except ImportError:
            raise RuntimeError(
                "Discord.py is required to run the Discord Bot. Install it with: pip install discord.py"
            )

        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True

        bot = commands.Bot(command_prefix=self.command_prefix, intents=intents)

        @bot.event
        async def on_ready():
            print(f"🤖 MAX Discord Bot is online as {bot.user} (ID: {bot.user.id})")
            print(f"⚡ Model: {self.agent.model} | Prefix: {self.command_prefix}")

        @bot.event
        async def on_message(message: discord.Message):
            # Do not reply to self or other bots
            if message.author.bot:
                return

            content = message.content.strip()
            is_dm = isinstance(message.channel, discord.DMChannel)
            is_mention = bot.user in message.mentions if self.respond_to_mentions and bot.user else False
            starts_with_prefix = content.startswith(self.command_prefix)

            # Determine prompt
            prompt = ""
            if starts_with_prefix:
                prompt = content[len(self.command_prefix) :].strip()
            elif is_mention:
                # Remove mention tag
                prompt = content.replace(f"<@{bot.user.id}>", "").replace(f"<@!{bot.user.id}>", "").strip()
            elif is_dm and self.respond_to_dms:
                prompt = content

            if not prompt:
                await bot.process_commands(message)
                return

            # Commands handling
            channel_id = str(message.channel.id)
            if prompt.lower() in ("reset", "clear", "!reset", "/reset"):
                session = self.agent.get_session(channel_id, create_if_missing=False)
                if session:
                    session.clear()
                await message.reply("🧹 ล้างประวัติการสนทนาในห้องนี้เรียบร้อยแล้วครับ! (Conversation context reset)")
                return

            if prompt.lower() in ("help", "!help"):
                help_text = (
                    "**🤖 MAX AI Discord Bot**\n"
                    f"• โมเดลปัจจุบัน: `{self.agent.model}`\n"
                    f"• คำสั่งถาม: `{self.command_prefix}<คำถาม>` หรือ Mention @{bot.user.name}\n"
                    f"• ล้างประวัติ: `{self.command_prefix}reset`\n"
                )
                await message.reply(help_text)
                return

            # Multi-turn interaction
            session = self.agent.get_session(channel_id)
            async with message.channel.typing():
                try:
                    response = await session.send_async(prompt)
                    chunks = split_discord_message(response.text)
                    for chunk in chunks:
                        await message.reply(chunk)
                except Exception as ex:
                    await message.reply(f"⚠️ เกิดข้อผิดพลาดในการประมวลผล: `{ex}`")

        bot.run(self.discord_token)


def create_max_bot(
    discord_token: str,
    max_api_key: Optional[str] = None,
    model: str = "gemini-2.5-flash",
    command_prefix: str = "!max ",
    system_prompt: str = "You are MAX, an intelligent AI assistant in Discord.",
    enable_tools: bool = False,
) -> MaxDiscordBot:
    """Convenience factory function to create a MaxDiscordBot instance."""
    return MaxDiscordBot(
        discord_token=discord_token,
        api_key=max_api_key,
        model=model,
        command_prefix=command_prefix,
        system_prompt=system_prompt,
        enable_tools=enable_tools,
    )
