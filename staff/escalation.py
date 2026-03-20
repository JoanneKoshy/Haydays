import asyncio
from telegram import Bot
from config import TELEGRAM_BOT_TOKEN, MANAGER_TELEGRAM_ID, ANALYST_TELEGRAM_ID

bot = Bot(token=TELEGRAM_BOT_TOKEN)

# Global flag to track manager acknowledgement
manager_acknowledged = {}

async def notify_manager(staff_name: str, role: str, question: str, escalation_id: str):
    message = (
        f"⚠️ *Escalation Alert!*\n\n"
        f"*{staff_name}* ({role}) has not responded to:\n"
        f"_{question}_\n\n"
        f"Please reply *anything* to this bot to acknowledge.\n"
        f"If you don't respond in 1 min, the analyst will be notified."
    )
    await bot.send_message(
        chat_id=MANAGER_TELEGRAM_ID,
        text=message,
        parse_mode="Markdown"
    )

async def notify_analyst(staff_name: str, role: str, question: str):
    message = (
        f"🚨 *Second Level Escalation!*\n\n"
        f"Manager *Ashwin* has not responded to the pending query.\n\n"
        f"*Staff:* {staff_name} ({role})\n"
        f"*Unanswered Question:* _{question}_\n\n"
        f"Immediate attention required."
    )
    await bot.send_message(
        chat_id=ANALYST_TELEGRAM_ID,
        text=message,
        parse_mode="Markdown"
    )

async def notify_manager_staff_responded(staff_name: str, role: str, question: str, answer: str):
    message = (
        f"✅ *Late Response Received*\n\n"
        f"*{staff_name}* ({role}) has now responded.\n\n"
        f"*Question:* _{question}_\n"
        f"*Answer:* *{answer}*"
    )
    await bot.send_message(
        chat_id=MANAGER_TELEGRAM_ID,
        text=message,
        parse_mode="Markdown"
    )

async def escalation_watch(
    context,
    chat_id: int,
    staff_name: str,
    role: str,
    question: str
):
    # Unique ID for this escalation instance
    escalation_id = f"{chat_id}_{question}"
    manager_acknowledged[escalation_id] = False

    # Wait 1 min for staff reply
    await asyncio.sleep(60)

    # Check if staff already answered
    if context.user_data.get("answered"):
        manager_acknowledged.pop(escalation_id, None)
        return

    # Mark escalated
    context.user_data["escalated"] = True

    # Alert manager
    await notify_manager(staff_name, role, question, escalation_id)

    # Store escalation_id so manager handler can set the flag
    context.user_data["escalation_id"] = escalation_id

    # Wait 1 min for manager acknowledgement
    await asyncio.sleep(60)

    # Check if manager acknowledged
    if manager_acknowledged.get(escalation_id):
        manager_acknowledged.pop(escalation_id, None)
        return

    # Check if staff answered during manager window
    if context.user_data.get("answered"):
        manager_acknowledged.pop(escalation_id, None)
        return

    # Alert analyst
    await notify_analyst(staff_name, role, question)
    manager_acknowledged.pop(escalation_id, None)