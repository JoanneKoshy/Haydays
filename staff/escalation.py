import asyncio
from telegram import Bot
from config import TELEGRAM_BOT_TOKEN, MANAGER_TELEGRAM_ID, ANALYST_TELEGRAM_ID

bot = Bot(token=TELEGRAM_BOT_TOKEN)

# Global escalation tracker
# { escalation_id: { "acknowledged": False, "number": 1, "staff": ..., "role": ..., "question": ... } }
active_escalations = {}
escalation_counter = [0]  # using list so it's mutable inside async functions

async def notify_manager(escalation_id: str, staff_name: str, role: str, question: str, number: int):
    message = (
        f"⚠️ *Escalation Alert #{number}*\n\n"
        f"*{staff_name}* ({role}) has not responded to:\n"
        f"_{question}_\n\n"
        f"Reply *{number}* to acknowledge this.\n"
        f"If you don't respond in 1 min, the analyst will be notified."
    )
    await bot.send_message(
        chat_id=MANAGER_TELEGRAM_ID,
        text=message,
        parse_mode="Markdown"
    )

async def notify_analyst(number: int, staff_name: str, role: str, question: str):
    message = (
        f"🚨 *Second Level Escalation #{number}*\n\n"
        f"Manager *Ashwin* has not responded to escalation #{number}.\n\n"
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
    # ── STEP 1: Wait 1 min for staff reply ──
    await asyncio.sleep(60)

    # Staff replied in time — stop
    if context.user_data.get("answered"):
        return

    # ── STEP 2: Assign escalation number and register ──
    escalation_counter[0] += 1
    number = escalation_counter[0]
    escalation_id = f"{chat_id}_{question}"

    active_escalations[escalation_id] = {
        "acknowledged": False,
        "number": number,
        "staff": staff_name,
        "role": role,
        "question": question
    }

    context.user_data["escalated"] = True
    context.user_data["escalation_id"] = escalation_id

    # Alert manager
    await notify_manager(escalation_id, staff_name, role, question, number)

    # ── STEP 3: Wait 1 min for manager acknowledgement ──
    await asyncio.sleep(60)

    # Manager acknowledged — stop
    if active_escalations.get(escalation_id, {}).get("acknowledged"):
        active_escalations.pop(escalation_id, None)
        return

    # Staff replied during manager window — stop
    if context.user_data.get("answered"):
        active_escalations.pop(escalation_id, None)
        return

    # ── STEP 4: Alert analyst ──
    await notify_analyst(number, staff_name, role, question)
    active_escalations.pop(escalation_id, None)