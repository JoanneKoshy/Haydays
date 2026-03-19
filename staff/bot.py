from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes
)
from questions import ROLE_QUESTIONS
from sentiment import analyze_sentiment
from sheets import log_responses
from config import TELEGRAM_BOT_TOKEN

# States
ASK_NAME, ASK_ROLE, ASK_QUESTIONS = range(3)

# ── /start ──────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "👋 Welcome to *Haydays Daily Check-in!*\n\nWhat is your name?",
        parse_mode="Markdown"
    )
    return ASK_NAME

# ── Name received ────────────────────────────────────────
async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    context.user_data["name"] = name

    role_keyboard = [
        ["1. Manager"],
        ["2. Accountant"],
        ["3. Chef"],
        ["4. Guest Service Staff"],
        ["5. Housekeeping"]
    ]
    markup = ReplyKeyboardMarkup(role_keyboard, one_time_keyboard=True, resize_keyboard=True)

    await update.message.reply_text(
        f"Nice to meet you, *{name}!* 👋\n\nPlease select your role:",
        reply_markup=markup,
        parse_mode="Markdown"
    )
    return ASK_ROLE

# ── Role received ────────────────────────────────────────
async def get_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    role_number = text.split(".")[0].strip()

    if role_number not in ROLE_QUESTIONS:
        await update.message.reply_text("Please choose a valid role from the options.")
        return ASK_ROLE

    role_data = ROLE_QUESTIONS[role_number]
    context.user_data["role"] = role_data["role_name"]
    context.user_data["questions"] = role_data["questions"]
    context.user_data["answers"] = []
    context.user_data["current_index"] = 0

    await update.message.reply_text(
        f"Got it! You are logged in as *{role_data['role_name']}* ✅\n\nLet's start your daily check-in!",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="Markdown"
    )

    # Ask first question
    first_question = role_data["questions"][0]
    await update.message.reply_text(f"Q1: {first_question}")
    return ASK_QUESTIONS

# ── Questions loop ───────────────────────────────────────
async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply = update.message.text.strip()
    index = context.user_data["current_index"]
    questions = context.user_data["questions"]
    current_question = questions[index]

    # Sentiment analysis
    answer = analyze_sentiment(current_question, reply)
    context.user_data["answers"].append(answer)

    index += 1
    context.user_data["current_index"] = index

    # More questions remaining
    if index < len(questions):
        next_question = questions[index]
        await update.message.reply_text(f"Q{index + 1}: {next_question}")
        return ASK_QUESTIONS

    # All questions done
    name = context.user_data["name"]
    role = context.user_data["role"]
    answers = context.user_data["answers"]

    # Log to Google Sheets
    log_responses(name, role, questions, answers)

    # Build summary
    summary = f"✅ *Check-in Complete!*\n\nHere's your summary, {name}:\n\n"
    for i, (q, a) in enumerate(zip(questions, answers)):
        emoji = "✅" if a == "YES" else "❌"
        summary += f"{emoji} {q}\n   → *{a}*\n\n"
    summary += "Thank you! Have a great day 🌿"

    await update.message.reply_text(summary, parse_mode="Markdown")
    return ConversationHandler.END

# ── Cancel ───────────────────────────────────────────────
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Check-in cancelled. Type /start to begin again.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

# ── Main ─────────────────────────────────────────────────
def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            ASK_ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_role)],
            ASK_QUESTIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(conv_handler)
    print("🌿 Haydays bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
