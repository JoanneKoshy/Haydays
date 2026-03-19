import os
import base64
import logging
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

load_dotenv()

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
NVIDIA_API_KEY = os.environ["NVIDIA_API_KEY"]

INVOKE_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

# ── Try models in order until one works ──────────────────────────────────────
MODELS_TO_TRY = [

    #"microsoft/phi-3.5-vision-instruct",
    #"google/paligemma-3b-pt-896",
    "microsoft/phi-4-multimodal-instruct",
]

# ── Prompt ────────────────────────────────────────────────────────────────────
PROMPT = """You are a highly specialized plant pathologist and agronomist with 20+ years of field experience diagnosing crop diseases worldwide.

IMPORTANT INSTRUCTIONS:
- Study every visual detail in the image extremely carefully before responding
- Pay close attention to: pustule color (orange/brown/black/white), lesion shape, affected plant part, texture (powdery/watery/dry/crusty)
- Common diseases to watch for:
  * Orange/brown powdery pustules on leaves = RUST (Puccinia species)
  * White powdery coating = POWDERY MILDEW
  * Brown/black water-soaked lesions = BLIGHT (Early or Late)
  * Yellow spots with brown center = LEAF SPOT
  * Yellowing + wilting = WILT disease
  * Black sooty coating = SOOTY MOLD
  * Curling + discoloration = VIRAL infection
- Do NOT confuse rust with leaf spot — rust has raised powdery pustules
- Do NOT confuse crops — wheat and corn look very different
- If you see orange/brown powdery raised spots on wheat = it is WHEAT LEAF RUST (Puccinia triticina)
- Be very specific about the CROP TYPE first, then the disease

Respond ONLY in this exact format, nothing before or after:

🌿 *Plant Identified:* <exact crop/plant name>

🦠 *Disease Detected:* <exact disease common name> (<Scientific name>)

📋 *About the Disease:*
<2-3 precise sentences about this specific disease, how it spreads and what conditions favor it>

🔬 *Symptoms Visible in This Image:*
- <specific symptom you can SEE in this image>
- <specific symptom you can SEE in this image>
- <specific symptom you can SEE in this image>

💊 *Treatment Steps:*
1. <immediate action with specific fungicide/treatment name>
2. <follow-up action>
3. <long term action>

🛡️ *Prevention:*
- <specific prevention tip>
- <specific prevention tip>

⚠️ *Severity:* <Low / Medium / High> — <one line reason why>

🎯 *Confidence:* <High / Medium / Low> — <one line reason>

If the plant looks completely healthy respond with:
✅ *Plant looks HEALTHY — No disease detected*

If the image is not a plant politely ask for a clear plant photo."""
# ── NVIDIA API Call ───────────────────────────────────────────────────────────
def analyze_plant(image_bytes: bytes) -> str:
    image_b64 = base64.b64encode(image_bytes).decode("utf-8")

    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Accept": "application/json"
    }

    last_error = None
    for model in MODELS_TO_TRY:
        try:
            logger.info(f"Trying model: {model}")
            payload = {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_b64}"
                                }
                            },
                            {
                                "type": "text",
                                "text": PROMPT
                            }
                        ]
                    }
                ],
                "max_tokens": 1024,
                "temperature": 0.10,
                "top_p": 0.70,
                "stream": False
            }

            response = requests.post(
                INVOKE_URL,
                headers=headers,
                json=payload,
                timeout=60
            )

            if response.status_code == 200:
                logger.info(f"✅ Success with model: {model}")
                return response.json()["choices"][0]["message"]["content"]
            else:
                logger.warning(f"❌ {model} failed: {response.status_code} - {response.text[:100]}")
                last_error = f"{response.status_code}"
                continue

        except Exception as e:
            logger.warning(f"❌ {model} exception: {e}")
            last_error = str(e)
            continue

    raise Exception(f"All models failed. Last error: {last_error}")


# ── Download Helper ───────────────────────────────────────────────────────────
async def download_image(update: Update, context) -> bytes:
    if update.message.photo:
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
    elif update.message.document:
        file = await context.bot.get_file(update.message.document.file_id)
    else:
        raise Exception("No image found")
    return bytes(await file.download_as_bytearray())


# ── Handlers ──────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌱 *Welcome to Plant Disease Detector!*\n\n"
        "Send me a photo of your plant and I'll identify any diseases instantly.\n\n"
        "📸 *For best accuracy:*\n"
        "Send your image as a *File* (tap 📎 → File) instead of a regular photo!",
        parse_mode="Markdown"
    )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    waiting_msg = await update.message.reply_text("🔍 Analyzing your plant...")

    try:
        image_bytes = await download_image(update, context)

        await waiting_msg.edit_text("🧠 Diagnosing with AI...")

        result = analyze_plant(image_bytes)

        await waiting_msg.delete()
        await update.message.reply_text(result, parse_mode="Markdown")

    except Exception as e:
        logger.error(f"Error: {e}")
        try:
            await waiting_msg.delete()
        except:
            pass
        await update.message.reply_text(
            "❌ Something went wrong. Please try again with a clearer image."
        )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📸 Please send a plant photo for analysis!\n\n"
        "💡 Tip: Send as a *File* (📎 → File) for best accuracy!",
        parse_mode="Markdown"
    )


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.Document.IMAGE, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Bot running with NVIDIA Vision Models! 🌿")
    app.run_polling()


if __name__ == "__main__":
    main()