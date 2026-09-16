"""
examples/discord_bot_simple.py — Example Discord AI Bot using MAX AI SDK.

How to Run:
    1. pip install "max-ai[discord]" (or pip install discord.py)
    2. Set DISCORD_BOT_TOKEN and MAXPLUS_API_KEY environment variables
    3. Run: python examples/discord_bot_simple.py
"""

import os
import max_ai
from max_ai.discord import create_max_bot

# Read configuration from environment or set directly
DISCORD_TOKEN = os.environ.get("DISCORD_BOT_TOKEN", "YOUR_DISCORD_BOT_TOKEN_HERE")
MAX_KEY = os.environ.get("MAXPLUS_API_KEY", "")

if __name__ == "__main__":
    print("🚀 Initializing MAX Discord AI Bot...")

    # Create bot instance with multi-turn session memory
    bot = create_max_bot(
        discord_token=DISCORD_TOKEN,
        max_api_key=MAX_KEY,
        model="gemini-2.5-flash",
        command_prefix="!max ",
        system_prompt=(
            "You are MAX, a friendly and super-smart Discord AI assistant. "
            "Help users with coding, answering questions, and creative tasks. "
            "Format your code blocks with syntax highlighting."
        ),
        enable_tools=True,  # Allows autonomous calculations, time checks, and tools
    )

    # Start the bot (Blocking call that runs the Discord event loop)
    # Commands available in Discord:
    #   !max <prompt>        - Ask question or chat with multi-turn memory
    #   @Bot <prompt>        - Mention the bot to chat
    #   !max reset           - Clear chat history for the channel
    #   !max help            - Show bot commands & info
    bot.run()
