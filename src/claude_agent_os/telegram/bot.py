"""Telegram bot listener with allowlist and file handling."""

import asyncio
import logging
from pathlib import Path

from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

logger = logging.getLogger(__name__)


class TelegramBot:
    """Async Telegram bot that routes messages to Claude agents."""

    def __init__(
        self,
        bot_token: str,
        allowed_users: list[str],
        agent_pool,
        soul_path: Path,
        memory_manager,
    ):
        self.bot_token = bot_token
        self.allowed_users = set(allowed_users)
        self.agent_pool = agent_pool
        self.soul_path = soul_path
        self.memory_manager = memory_manager
        self.app: Application | None = None

    async def start(self):
        """Start the Telegram bot (non-blocking)."""
        self.app = Application.builder().token(self.bot_token).build()
        self.app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message)
        )
        self.app.add_handler(
            MessageHandler(filters.PHOTO | filters.Document.ALL, self._handle_file)
        )
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()
        logger.info("Telegram bot started")

    async def stop(self):
        """Stop the Telegram bot gracefully."""
        if self.app:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()

    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming text messages — check allowlist, spawn agent."""
        user_id = str(update.effective_user.id)
        if user_id not in self.allowed_users:
            await update.message.reply_text("Access denied.")
            return

        prompt = update.message.text
        try:
            result = await self.agent_pool.spawn(
                task_id=f"telegram-{update.message.message_id}",
                prompt=prompt,
                workspace=str(Path.home()),
            )
            response = result.output or "(no response)"
            for i in range(0, len(response), 4096):
                await update.message.reply_text(response[i : i + 4096])
        except Exception as e:
            logger.error(f"Agent error: {e}")
            await update.message.reply_text(f"Error: {e}")

    async def _handle_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming photos/documents — save to inbox, spawn agent."""
        user_id = str(update.effective_user.id)
        if user_id not in self.allowed_users:
            return

        # Save file to inbox
        inbox = Path.home() / ".claude-agent-os" / "inbox"
        inbox.mkdir(parents=True, exist_ok=True)

        if update.message.photo:
            file = await update.message.photo[-1].get_file()
            file_path = inbox / f"{update.message.message_id}.jpg"
            await file.download_to_drive(str(file_path))
            caption = update.message.caption or "Analyze this image"
            prompt = f"{caption}\n\nImage saved at: {file_path}"
        elif update.message.document:
            file = await update.message.document.get_file()
            file_path = inbox / update.message.document.file_name
            await file.download_to_drive(str(file_path))
            caption = update.message.caption or f"Process this file: {file_path}"
            prompt = caption
        else:
            return

        try:
            result = await self.agent_pool.spawn(
                task_id=f"telegram-{update.message.message_id}",
                prompt=prompt,
                workspace=str(Path.home()),
            )
            response = result.output or "(no response)"
            for i in range(0, len(response), 4096):
                await update.message.reply_text(response[i : i + 4096])
        except Exception as e:
            await update.message.reply_text(f"Error: {e}")

    async def send_message(self, chat_id: str, text: str):
        """Send a message to a specific chat (for notifications)."""
        if self.app and self.app.bot:
            for i in range(0, len(text), 4096):
                await self.app.bot.send_message(chat_id=chat_id, text=text[i : i + 4096])
