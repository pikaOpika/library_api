import requests
import os
import logging
from dotenv import load_dotenv


load_dotenv()
logger = logging.getLogger(__name__)

def send_telegram_message(text):
    
    token = os.environ.get("BOT_TOKEN")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": os.environ.get("TELEGRAM_CHAT_ID"),
        "text": text
    }
    try:
        res = requests.post(url, json=payload, timeout=5)
        if res.status_code == 200:
            logger.info("Message sent")
        else:
            logger.error("Telegram error %s: %s", res.status_code, res.text)
    except requests.RequestException as exc:
        logger.error("Telegram request failed %s", exc)