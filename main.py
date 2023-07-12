import logging
import asyncio
import os
from time import time
from functools import wraps
from dotenv import load_dotenv
from base_prompt import TIMEOUT_MSG, TIMEOUT_MSG2
from pythgpt import pyth_gpt
from telegram import Update
from telegram.ext import ContextTypes, ApplicationHandlerStop, Application, CommandHandler
from telegram.constants import ChatAction

load_dotenv()
TELEGRAM_API_KEY = os.getenv('TELEGRAM_API_KEY')
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
MAX_USAGE = 1


def send_action(action):
    """Sends `action` while processing func command."""
    def decorator(func):
        @wraps(func)
        async def command_func(update, context, *args, **kwargs):
            await context.bot.send_chat_action(chat_id=update.effective_message.chat_id, action=action)
            return await func(update, context, *args, **kwargs)
        return command_func
    return decorator


@send_action(ChatAction.TYPING)
async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    placeholder_message = await context.bot.send_message(chat_id=update.effective_chat.id, text="...")

    user_message = update.message.text[6:]
    answer = await asyncio.to_thread(pyth_gpt, message=user_message)
    await context.bot.edit_message_text(chat_id=placeholder_message.chat_id, message_id=placeholder_message.message_id, parse_mode="Markdown", text=answer)


async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    count = context.user_data.get("usageCount", 0)
    restrict_since = context.user_data.get("restrictSince", 0)

    if restrict_since:
        if (time() - restrict_since) >= 30 * 60:  # 30 minutes
            del context.user_data["restrictSince"]
            del context.user_data["usageCount"]
        else:
            await update.effective_message.reply_text(parse_mode="Markdown", text=TIMEOUT_MSG2)
            raise ApplicationHandlerStop
    else:
        if count >= MAX_USAGE:
            context.user_data["restrictSince"] = time()
            await update.effective_message.reply_text(parse_mode="Markdown", text=TIMEOUT_MSG)
            raise ApplicationHandlerStop
    context.user_data["usageCount"] = count + 1


if __name__ == '__main__':
    app = Application.builder().token(TELEGRAM_API_KEY).build()

    handler = CommandHandler('chat', callback)
    app.add_handler(handler, -1)

    start_handler = CommandHandler('chat', chat)
    app.add_handler(start_handler, 0)

    app.run_polling()
