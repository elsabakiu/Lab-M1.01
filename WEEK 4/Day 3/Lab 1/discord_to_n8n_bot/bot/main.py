from __future__ import annotations

import logging
from typing import Any

import discord

try:
    from bot.config import Settings, load_settings
    from bot.logger import configure_logging
    from bot.webhook_client import WebhookClient
except ModuleNotFoundError:
    # Support direct execution: python bot/main.py
    from config import Settings, load_settings
    from logger import configure_logging
    from webhook_client import WebhookClient


class DiscordRelayBot(discord.Client):
    def __init__(self, settings: Settings, webhook_client: WebhookClient, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.settings = settings
        self.webhook_client = webhook_client
        self.logger = logging.getLogger(self.__class__.__name__)

    async def setup_hook(self) -> None:
        await self.webhook_client.start()

    async def on_ready(self) -> None:
        user = self.user
        self.logger.info("Bot is online as %s (id=%s)", user, getattr(user, "id", "unknown"))
        self.logger.info(
            "Listening in guild_id=%s channel_id=%s",
            self.settings.discord_guild_id,
            self.settings.discord_channel_id,
        )

    async def on_message(self, message: discord.Message) -> None:
        if message.guild is None:
            return

        if message.guild.id != self.settings.discord_guild_id:
            return

        if message.channel.id != self.settings.discord_channel_id:
            return

        if self.settings.ignore_bots and message.author.bot:
            self.logger.debug("Ignored bot message: message_id=%s", message.id)
            return

        content = (message.content or "").strip()
        if not content:
            self.logger.debug("Ignored empty message: message_id=%s", message.id)
            return

        payload: dict[str, Any] = {
            "content": content,
            "username": message.author.name,
            "user_id": str(message.author.id),
            "message_id": str(message.id),
            "channel_id": str(message.channel.id),
            "guild_id": str(message.guild.id),
            "timestamp": message.created_at.isoformat(),
            "jump_url": message.jump_url,
            "attachments": [attachment.url for attachment in message.attachments],
        }

        sent = await self.webhook_client.send_with_retries(payload)
        if sent:
            self.logger.info(
                "Forwarded message_id=%s from user=%s",
                message.id,
                message.author.name,
            )
        else:
            self.logger.error("Failed to forward message_id=%s", message.id)

    async def close(self) -> None:
        await self.webhook_client.close()
        await super().close()


def build_intents() -> discord.Intents:
    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True
    intents.messages = True
    return intents


def main() -> None:
    settings = load_settings()
    configure_logging(settings.log_level)

    webhook_client = WebhookClient(settings.n8n_webhook_url)
    bot = DiscordRelayBot(settings=settings, webhook_client=webhook_client, intents=build_intents())
    bot.run(settings.discord_bot_token)


if __name__ == "__main__":
    main()
