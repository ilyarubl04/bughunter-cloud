import os
import json
import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import openai
from random import choice

TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY

with open("bughunter_100_cases.json", encoding="utf-8") as f:
    bug_cases = json.load(f)

user_states = {}
user_scores = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Привет! Я тренажёр Bug Hunter 🐞\nНапиши /next, чтобы получить задание.")

async def next_case(update: Update, context: ContextTypes.DEFAULT_TYPE):
    case = choice(bug_cases)
    uid = update.effective_chat.id
    user_states[uid] = case
    reply_markup = ReplyKeyboardMarkup([['🧩 Подсказка', '📊 Мой счёт']], one_time_keyboard=False, resize_keyboard=True)
    await update.message.reply_text(f"🎯 Сцена: {case['scene']}\n🧩 {case['description']}\n\n📝 Напиши, в чём баг:", reply_markup=reply_markup)

async def check_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_chat.id
    answer = update.message.text.strip()

    if uid not in user_states:
        await update.message.reply_text("Напиши /next, чтобы получить задание.")
        return

    case = user_states[uid]
    keywords = case['keywords']
    matches = [k for k in keywords if k.lower() in answer.lower()]

    user_scores[uid] = user_scores.get(uid, 0)

    if matches:
        user_scores[uid] += 1
        await update.message.reply_text(f"✅ Отлично! Ты уловил баг: {', '.join(matches)}")
    else:
        await update.message.reply_text("❗Почти! Попробуй подумать про валидацию или логику интерфейса.")

    feedback = generate_feedback(answer, keywords)
    await update.message.reply_text(f"🤖 Комментарий:\n{feedback}")

async def hint(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_chat.id
    if uid not in user_states:
        await update.message.reply_text("Сначала вызови /next!")
        return
    case = user_states[uid]
    hint_text = "💡 Подумай об этих аспектах: " + ", ".join(case["keywords"])
    await update.message.reply_text(hint_text)

async def score(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_chat.id
    score = user_scores.get(uid, 0)
    await update.message.reply_text(f"📊 Твой счёт: {score} правильных ответов.")

def generate_feedback(user_input, keywords):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Ты опытный тестировщик и тренер по баг-репортам."},
                {"role": "user", "content": f"Студент описал баг так: '{user_input}'. Оцени кратко и конструктивно, какие аспекты он упустил. Подсказки: {', '.join(keywords)}"}
            ]
        )
        return response["choices"][0]["message"]["content"]
    except Exception as e:
        return f"⚠️ Не удалось получить AI-комментарий: {str(e)}"

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("next", next_case))
    app.add_handler(CommandHandler("hint", hint))
    app.add_handler(CommandHandler("score", score))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_answer))
    print("🤖 Бот запущен! Жди команд /start и /next в Telegram.")
    app.run_polling()
