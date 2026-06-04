"""
Telegram-бот AI-ассистент для компании Центр Красок #1
Использует OpenRouter API (Claude models) для ответов на основе базы знаний.
"""

import os
import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler
from telegram.constants import ChatAction
from openai import OpenAI
from company_data import COMPANY_KNOWLEDGE

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

# OpenRouter client
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

# ─────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# HISTORY (СЕНІҢ КОДЫҢ 100% САҚТАЛДЫ)
# ─────────────────────────────────────────────

conversation_history: dict[int, list] = {}
MAX_HISTORY = 10


def get_history(chat_id: int):
    return conversation_history.get(chat_id, [])


def add_to_history(chat_id: int, role: str, content: str):
    if chat_id not in conversation_history:
        conversation_history[chat_id] = []

    conversation_history[chat_id].append({
        "role": role,
        "content": content
    })

    if len(conversation_history[chat_id]) > MAX_HISTORY:
        conversation_history[chat_id] = conversation_history[chat_id][-MAX_HISTORY:]


# ─────────────────────────────────────────────
# SYSTEM PROMPT (сол күйі)
# ─────────────────────────────────────────────

SYSTEM_PROMPT = f"""
Ты — вежливый и полезный AI-ассистент интернет-магазина «Центр Красок #1» (centr-krasok.kz).

Твоя задача — отвечать на вопросы клиентов о компании, её товарах, услугах, брендах, доставке, акциях и контактах.

ПРАВИЛА:
1. Отвечай ТОЛЬКО на основе предоставленной информации о компании ниже.
2. Если информации по вопросу нет в базе знаний — честно скажи об этом и предложи позвонить по телефону +7 (777) 292-84-01 или посетить сайт centr-krasok.kz.
3. НЕ придумывай факты, цены, адреса или данные, которых нет в базе знаний.
4. Отвечай на том языке, на котором написал пользователь (русский, казахский, английский).
5. Будь дружелюбным, кратким и конкретным. Избегай лишних слов.
6. Если вопрос не связан с компанией или её продукцией — вежливо объясни, что ты ассистент магазина красок и можешь помочь только по теме магазина.

БАЗА ЗНАНИЙ О КОМПАНИИ:
{COMPANY_KNOWLEDGE}
"""


# ─────────────────────────────────────────────
# OPENROUTER REQUEST (НАҒЫЗ ТҮЗЕТУ ОСЫ ЖЕРДЕ)
# ─────────────────────────────────────────────

def ask_claude(chat_id: int, user_message: str) -> str:
    add_to_history(chat_id, "user", user_message)

    try:
        response = client.chat.completions.create(
            model="anthropic/claude-3-haiku",  # OpenRouter model
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                *get_history(chat_id),
            ],
            temperature=0.3,
            max_tokens=800,
        )

        answer = response.choices[0].message.content

        add_to_history(chat_id, "assistant", answer)

        return answer

    except Exception as e:
        logger.error(f"OpenRouter API error: {e}")
        return "Ошибка сервера. Попробуйте позже или позвоните +7 (777) 292-84-01"


# ─────────────────────────────────────────────
# TELEGRAM HANDLERS (ӨЗГЕРІССІЗ)
# ─────────────────────────────────────────────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message or not message.text:
        return

    chat_id = message.chat_id
    user_text = message.text.strip()

    logger.info(f"[{chat_id}] Вопрос: {user_text}")

    await context.bot.send_chat_action(
        chat_id=chat_id,
        action=ChatAction.TYPING
    )

    answer = ask_claude(chat_id, user_text)

    logger.info(f"[{chat_id}] Ответ: {answer[:80]}")

    await message.reply_text(answer)


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    conversation_history.pop(chat_id, None)

    await update.message.reply_text(
        "👋 Привет! Я AI-ассистент Центр Красок #1.\n"
        "Задайте любой вопрос о товарах, доставке или акциях."
    )


async def handle_reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    conversation_history.pop(chat_id, None)

    await update.message.reply_text("🔄 История очищена.")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    logger.info("Запуск бота Центр Красок #1...")

    import asyncio

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(CommandHandler("reset", handle_reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Бот запущен...")
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()