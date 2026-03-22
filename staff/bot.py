import asyncio
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
from sheets import log_responses, log_late_response
from escalation import (
    escalation_watch,
    notify_manager_staff_responded,
    active_escalations
)
from config import TELEGRAM_BOT_TOKEN, MANAGER_TELEGRAM_ID

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
    context.user_data["answered"] = False
    context.user_data["escalated"] = False

    await update.message.reply_text(
        f"Got it! You are logged in as *{role_data['role_name']}* ✅\n\nLet's start your daily check-in!",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="Markdown"
    )

    first_question = role_data["questions"][0]
    await ask_question(update, context, first_question)
    return ASK_QUESTIONS

# ── Ask question + start escalation timer ────────────────
async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE, question: str):
    index = context.user_data["current_index"]
    name = context.user_data["name"]
    role = context.user_data["role"]

    context.user_data["answered"] = False
    context.user_data["escalated"] = False

    await update.message.reply_text(f"Q{index + 1}: {question}")

    asyncio.create_task(
        escalation_watch(
            context=context,
            chat_id=update.effective_chat.id,
            staff_name=name,
            role=role,
            question=question
        )
    )

# ── Handle answer ────────────────────────────────────────
async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reply = update.message.text.strip()
    index = context.user_data["current_index"]
    questions = context.user_data["questions"]
    current_question = questions[index]
    name = context.user_data["name"]
    role = context.user_data["role"]
    was_escalated = context.user_data.get("escalated", False)

    context.user_data["answered"] = True

    answer = analyze_sentiment(current_question, reply)
    context.user_data["answers"].append(answer)

    if was_escalated:
        await notify_manager_staff_responded(name, role, current_question, answer)
        log_late_response(name, role, current_question, answer)

    index += 1
    context.user_data["current_index"] = index

    if index < len(questions):
        next_question = questions[index]
        await ask_question(update, context, next_question)
        return ASK_QUESTIONS

    answers = context.user_data["answers"]
    log_responses(name, role, questions, answers)

    summary = f"✅ *Check-in Complete!*\n\nHere's your summary, {name}:\n\n"
    for i, (q, a) in enumerate(zip(questions, answers)):
        emoji = "✅" if a == "YES" else "❌"
        summary += f"{emoji} {q}\n   → *{a}*\n\n"
    summary += "Thank you! Have a great day 🌿"

    await update.message.reply_text(summary, parse_mode="Markdown")
    return ConversationHandler.END

# ── Manager acknowledgement handler ─────────────────────
async def manager_ack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    if user_id != MANAGER_TELEGRAM_ID:
        return

    text = update.message.text.strip()

    # Find escalation matching the number Ashwin replied with
    for escalation_id, data in list(active_escalations.items()):
        if str(data["number"]) == text and not data["acknowledged"]:
            active_escalations[escalation_id]["acknowledged"] = True
            await update.message.reply_text(
                f"✅ Escalation #{data['number']} for *{data['staff']}* ({data['role']}) acknowledged!\n"
                f"Second level escalation stopped.",
                parse_mode="Markdown"
            )
            return

    await update.message.reply_text(
        "⚠️ No active escalation found for that number. "
        "Check the escalation alerts and reply with the correct number."
    )

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

    # Manager ack handler — group 1 runs alongside conversation
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.User(int(MANAGER_TELEGRAM_ID)),
        manager_ack
    ), group=1)

    print("🌿 Haydays bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
    