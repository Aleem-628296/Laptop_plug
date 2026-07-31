import os
import time
import logging
import sqlite3
import requests
from datetime import datetime, timezone
import pytz
from dotenv import load_dotenv

load_dotenv()

# --- LOGGING SETUP ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('reminders.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SECRETARY_IDS = [int(id.strip()) for id in os.getenv("SECRETARY_ID", "").split(",") if id.strip()]
NOTIFICATION_IDS = [int(id.strip()) for id in os.getenv("NOTIFICATION_IDS", "").split(",") if id.strip()]
API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# Ghana timezone
GHANA_TZ = pytz.timezone('Africa/Accra')

def send_message(chat_id, text):
    url = f"{API_URL}/sendMessage"
    data = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, json=data, timeout=10)
        if response.status_code != 200:
            logger.error(f"Telegram API error: {response.text}")
    except Exception as e:
        logger.error(f"Reminder Send Error: {e}")

def get_pending_sales():
    conn = sqlite3.connect('stock.db', timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL;')
    sales = conn.execute("SELECT * FROM sales WHERE payment_status='pending'").fetchall()
    conn.close()
    return sales

def run_reminders():
    sales = get_pending_sales()
    now = datetime.now(GHANA_TZ)
    current_hour = now.hour
    current_date = now.strftime("%Y-%m-%d")
    
    notify_targets = NOTIFICATION_IDS if NOTIFICATION_IDS else SECRETARY_IDS
    
    for sale in sales:
        dt = sale['sold_at']
        if not dt:
            continue
            
        try:
            # Parse as UTC then convert to Ghana time
            dt_obj = datetime.strptime(dt, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            dt_ghana = dt_obj.astimezone(GHANA_TZ)
        except Exception as e:
            logger.error(f"Date parse error for sale {sale['id']}: {e}")
            continue
            
        diff = now - dt_ghana
        hours_passed = int(diff.total_seconds() // 3600)
        
        color_str = f" ({sale['color']})" if sale['color'] else ""
        item_name = f"{sale['item_name']}{color_str}"
        customer = sale['customer_info']
        amount = sale['profit']
        
        # Hourly reminders (1h to 6h)
        if 1 <= hours_passed <= 6:
            msg = f"⏳ *REMINDER ({hours_passed}h)*\n\n{customer} owes GHS {amount:.2f} for {item_name}."
            for target_id in notify_targets:
                send_message(target_id, msg)
            logger.info(f"Sent {hours_passed}h reminder for sale {sale['id']} to {len(notify_targets)} targets")
                
        # End of day reminder at 19:00
        if current_hour == 19:
            msg = f"🔔 *END OF DAY*\n\n{customer} owes GHS {amount:.2f} for {item_name}. Collect before closing."
            for target_id in notify_targets:
                send_message(target_id, msg)
            logger.info(f"Sent EOD reminder for sale {sale['id']}")

if __name__ == "__main__":
    logger.info("Reminder system started... Running every 15 minutes.")
    while True:
        try:
            run_reminders()
        except Exception as e:
            logger.error(f"Error in reminder loop: {e}", exc_info=True)
        time.sleep(900)  # 15 minutes
