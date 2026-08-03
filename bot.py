import os
import logging
import json
import requests
import time
import secrets
from contextlib import contextmanager
from collections import defaultdict
from datetime import datetime
from functools import wraps

from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor
from werkzeug.security import generate_password_hash, check_password_hash

# --- CONFIGURATION & LOGGING ---
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler('bot.log'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# --- ENVIRONMENT VARIABLES ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
OWNER_IDS = [int(id.strip()) for id in os.getenv("OWNER_ID", "").split(",") if id.strip()]
SECRETARY_IDS = [int(id.strip()) for id in os.getenv("SECRETARY_ID", "").split(",") if id.strip()]
NOTIFICATION_IDS = [int(id.strip()) for id in os.getenv("NOTIFICATION_IDS", "").split(",") if id.strip()]
ALLOWED_IDS = OWNER_IDS + SECRETARY_IDS
API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
DATABASE_URL = os.getenv("DATABASE_URL")

# --- RATE LIMITING ---
rate_limit_store = defaultdict(list)
def check_rate_limit(chat_id):
    now = time.time()
    rate_limit_store[chat_id] = [t for t in rate_limit_store[chat_id] if now - t < 60]
    if len(rate_limit_store[chat_id]) >= 30: return False
    rate_limit_store[chat_id].append(now)
    return True

# --- DATABASE CONTEXT MANAGER ---
@contextmanager
def get_db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    try:
        yield conn
    finally:
        conn.close()

# --- DATABASE INITIALIZATION ---
def init_db():
    with get_db() as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS stock (
            id SERIAL PRIMARY KEY, item_name TEXT NOT NULL, color TEXT DEFAULT '',
            quantity INTEGER DEFAULT 0, cost_price REAL DEFAULT 0.0, selling_price REAL DEFAULT 0.0,
            category TEXT NOT NULL, low_stock_threshold INTEGER DEFAULT 5, UNIQUE(item_name, color))''')
        c.execute('''CREATE TABLE IF NOT EXISTS sales (
            id SERIAL PRIMARY KEY, item_name TEXT NOT NULL, color TEXT DEFAULT '',
            quantity INTEGER NOT NULL, profit REAL NOT NULL, sold_by INTEGER NOT NULL,
            customer_info TEXT DEFAULT 'Walk-in', payment_status TEXT DEFAULT 'paid',
            sold_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        c.execute('''CREATE TABLE IF NOT EXISTS user_state (
            chat_id BIGINT PRIMARY KEY, state TEXT, data TEXT, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'admin', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        conn.commit()

        # Seed Admin User
        default_hash = generate_password_hash("Victory2024!")
        c.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s) ON CONFLICT (username) DO NOTHING", ("admin", default_hash))
        conn.commit()

        # Seed Inventory
        items = []
        laptops = ["HP 250 G9 (i5/8GB/256GB)", "HP EliteBook 840 (i7/16GB/512GB)", "Dell Inspiron 15 (i5/8GB/512GB)", 
                   "Dell XPS 13 (i7/16GB/1TB)", "Lenovo ThinkPad T14 (i7/16GB/512GB)", "MacBook Air M1 (8GB/256GB)", 
                   "MacBook Pro M3 (16GB/512GB)", "Acer Aspire 5 (Ryzen 5/8GB/512GB)", "ASUS ROG Strix (Ryzen 7/16GB/1TB)"]
        for l in laptops: items.append((l, "", 0, 0.0, 0.0, "Laptops", 2))
        
        accessories = ["Laptop Charger (65W Type-C)", "Laptop Charger (Barrel 45W)", "Wireless Mouse", "Mechanical Keyboard", 
                       "USB-C Hub 7-in-1", "HDMI Cable 2m", "Laptop Bag 15.6\"", "Webcam 1080p", "Laptop Cooling Pad"]
        for a in accessories: items.append((a, "", 0, 0.0, 0.0, "Accessories", 5))
        
        storage = ["Samsung 970 NVMe SSD 500GB", "Kingston A400 SATA SSD 240GB", "Seagate External HDD 1TB", "SanDisk USB 64GB"]
        for s in storage: items.append((s, "", 0, 0.0, 0.0, "Storage", 5))

        for item in items:
            c.execute("INSERT INTO stock (item_name, color, quantity, cost_price, selling_price, category, low_stock_threshold) VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT (item_name, color) DO NOTHING", item)
        conn.commit()
        logger.info(f"Database initialized with {len(items)} seed items and admin user.")

# --- TELEGRAM API HELPERS ---
def send_message(chat_id, text, reply_markup=None):
    data = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if reply_markup: data["reply_markup"] = reply_markup
    try: requests.post(f"{API_URL}/sendMessage", json=data, timeout=10)
    except Exception as e: logger.error(f"Send Error: {e}")

def edit_message(chat_id, message_id, text, reply_markup=None):
    data = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": "Markdown"}
    if reply_markup: data["reply_markup"] = reply_markup
    try: requests.post(f"{API_URL}/editMessageText", json=data, timeout=10)
    except Exception as e: logger.error(f"Edit Error: {e}")

def answer_callback(query_id):
    try: requests.post(f"{API_URL}/answerCallbackQuery", json={"callback_query_id": query_id}, timeout=5)
    except Exception as e: logger.error(f"Callback Error: {e}")

# --- STATE MANAGEMENT ---
def save_state(chat_id, state, data_dict=None):
    with get_db() as conn:
        conn.cursor().execute("INSERT INTO user_state (chat_id, state, data) VALUES (%s, %s, %s) ON CONFLICT (chat_id) DO UPDATE SET state=%s, data=%s",
                              (chat_id, state, json.dumps(data_dict or {}), state, json.dumps(data_dict or {})))
        conn.commit()

def get_state(chat_id):
    with get_db() as conn:
        row = conn.cursor().execute("SELECT state, data FROM user_state WHERE chat_id=%s", (chat_id,)).fetchone()
        if row: return row['state'], json.loads(row['data'])
    return None, {}

def clear_state(chat_id):
    with get_db() as conn:
        conn.cursor().execute("DELETE FROM user_state WHERE chat_id=%s", (chat_id,))
        conn.commit()

# --- FLASK APP ---
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", secrets.token_hex(32))
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = True

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal Server Error: {error}", exc_info=True)
    return "Something went wrong. The admin has been notified.", 500

# --- DEBUG TEST ROUTE ---
@app.route('/test')
def test():
    logger.info("✅ TEST ROUTE ACCESSED - Flask is working!")
    try:
        with get_db() as conn:
            count = conn.cursor().execute("SELECT COUNT(*) FROM users").fetchone()[0]
            logger.info(f"✅ Database connection successful! Users in DB: {count}")
        return f"✅ Flask is working! Database connected. Users in DB: {count}"
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}", exc_info=True)
        return f"❌ Database error: {e}", 500

# --- WEB DASHBOARD ROUTES ---
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session: return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

@app.route('/login', methods=['GET', 'POST'])
def login():
    logger.info(f"🔐 LOGIN ROUTE ACCESSED - Method: {request.method}")
    
    if request.method == 'POST':
        logger.info("📝 Processing POST login request")
        username = request.form.get('username')
        password = request.form.get('password')
        logger.info(f"👤 Login attempt for username: {username}")
        
        try:
            with get_db() as conn:
                user = conn.cursor().execute("SELECT id, password_hash FROM users WHERE username=%s", (username,)).fetchone()
                logger.info(f"🔍 Database query completed. User found: {user is not None}")
            
            if user and check_password_hash(user['password_hash'], password):
                logger.info("✅ Password verified successfully")
                session['user_id'] = user['id']
                session['username'] = username
                return redirect(url_for('dashboard'))
            else:
                logger.info("❌ Invalid credentials")
                return render_template('login.html', error="Invalid credentials")
        except Exception as e:
            logger.error(f"💥 Login error: {e}", exc_info=True)
            return f"Database error during login: {e}", 500
    
    logger.info("📄 Rendering login page (GET request)")
    return render_template('login.html', error=None)

@app.route('/dashboard')
@login_required
def dashboard():
    logger.info(f"📊 Dashboard accessed by user: {session.get('username')}")
    with get_db() as conn:
        c = conn.cursor()
        stock_stats = c.execute("SELECT COUNT(*) as total_items, COALESCE(SUM(quantity),0) as total_stock FROM stock").fetchone()
        sales_stats = c.execute("SELECT COUNT(*) as total_sales, COALESCE(SUM(profit),0) as total_profit FROM sales").fetchone()
        recent_sales = c.execute("SELECT item_name, quantity, profit, customer_info, sold_at FROM sales ORDER BY sold_at DESC LIMIT 5").fetchall()
    return render_template('dashboard.html', stock_stats=stock_stats, sales_stats=sales_stats, recent_sales=recent_sales, username=session.get('username'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- TELEGRAM WEBHOOK ---
@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    if WEBHOOK_SECRET and request.headers.get('X-Telegram-Bot-Api-Secret-Token') != WEBHOOK_SECRET:
        return jsonify({"error": "Unauthorized"}), 403
    
    update = request.get_json()
    try:
        if 'message' in update:
            msg = update['message']
            chat_id = msg['chat']['id']
            if chat_id not in ALLOWED_IDS:
                if msg.get('text') == "/start": send_message(chat_id, "⛔ Access Denied.")
                return jsonify({"ok": True})
            if 'text' in msg: handle_text_message(chat_id, msg['text'])
        elif 'callback_query' in update:
            cb = update['callback_query']
            chat_id = cb['message']['chat']['id']
            if chat_id not in ALLOWED_IDS: return jsonify({"ok": True})
            if not check_rate_limit(chat_id): return jsonify({"ok": True})
            button_handler(cb)
    except Exception as e:
        logger.error(f"Webhook Processing Error: {e}", exc_info=True)
    return jsonify({"ok": True})

@app.route('/setup', methods=['GET'])
def setup_webhook():
    if not WEBHOOK_URL: return "Error: WEBHOOK_URL not set."
    data = {"url": WEBHOOK_URL}
    if WEBHOOK_SECRET: data["secret_token"] = WEBHOOK_SECRET
    return requests.post(f"{API_URL}/setWebhook", json=data).text

@app.route('/')
def index():
    return "LapyPlug Backend API is live and secure."

# --- TELEGRAM BUTTON HANDLER ---
def button_handler(query):
    chat_id = query['message']['chat']['id']
    msg_id = query['message']['message_id']
    data = query['data']
    answer_callback(query['id'])

    if data == "m_menu":
        text, markup = build_main_menu(chat_id)
        clear_state(chat_id)
        edit_message(chat_id, msg_id, text, markup)
    elif data == "m_view":
        with get_db() as conn:
            cats = conn.cursor().execute("SELECT DISTINCT category FROM stock ORDER BY category").fetchall()
        btns = [[{"text": c['category'], "callback_data": f"vc_{c['category'][:30]}"}] for c in cats]
        btns.append([{"text": "🏠 Main Menu", "callback_data": "m_menu"}])
        edit_message(chat_id, msg_id, "📋 *VIEW STOCK*\n\nSelect a category:", {"inline_keyboard": btns})
    elif data.startswith("vc_"):
        cat = data[3:]
        with get_db() as conn:
            items = conn.cursor().execute("SELECT * FROM stock WHERE category=%s ORDER BY item_name", (cat,)).fetchall()
        text = f"📋 *{cat}*\n\n" + "".join([f"• *{i['item_name']}* ({i['color'] or 'N/A'})\n  Qty: {i['quantity']} | GHS {i['selling_price']:.0f}\n\n" for i in items])
        edit_message(chat_id, msg_id, text, {"inline_keyboard": [[{"text": "⬅️ Back", "callback_data": "m_view"}]]})
    elif data == "m_sale":
        with get_db() as conn:
            cats = conn.cursor().execute("SELECT DISTINCT category FROM stock WHERE quantity > 0").fetchall()
        btns = [[{"text": c['category'], "callback_data": f"sc_{c['category'][:30]}"}] for c in cats]
        btns.append([{"text": "🏠 Main Menu", "callback_data": "m_menu"}])
        edit_message(chat_id, msg_id, "💰 *RECORD SALE*\n\nSelect category:", {"inline_keyboard": btns})
    elif data.startswith("sc_"):
        cat = data[3:]
        with get_db() as conn:
            items = conn.cursor().execute("SELECT * FROM stock WHERE category=%s AND quantity > 0", (cat,)).fetchall()
        btns = [[{"text": f"{i['item_name']} ({i['quantity']})", "callback_data": f"si_{i['id']}"}] for i in items]
        btns.append([{"text": "⬅️ Back", "callback_data": "m_sale"}])
        edit_message(chat_id, msg_id, "💰 Select item to sell:", {"inline_keyboard": btns})
    elif data.startswith("si_"):
        item_id = int(data[3:])
        with get_db() as conn:
            item = conn.cursor().execute("SELECT * FROM stock WHERE id=%s", (item_id,)).fetchone()
        save_state(chat_id, f"sq_{item_id}")
        edit_message(chat_id, msg_id, f"💰 *{item['item_name']}*\nAvailable: {item['quantity']}\n\n*Type quantity:*", {"inline_keyboard": [[{"text": "❌ Cancel", "callback_data": "m_menu"}]]})
    elif data.startswith("sw_"):
        parts = data.split("_")
        process_sale(chat_id, int(parts[1]), int(parts[2]), "Walk-in", 'paid', msg_id)
    elif data.startswith("sp_") or data.startswith("scred_"):
        status = 'paid' if data.startswith("sp_") else 'pending'
        parts = data.split("_")
        state, d = get_state(chat_id)
        process_sale(chat_id, int(parts[1]), int(parts[2]), d.get('cust', "Walk-in"), status, msg_id)
        clear_state(chat_id)
    elif data.startswith("st_"):
        parts = data.split("_")
        save_state(chat_id, f"st_{parts[1]}_{parts[2]}")
        edit_message(chat_id, msg_id, "✍️ *Type Customer Name & Number:*", {"inline_keyboard": [[{"text": "❌ Cancel", "callback_data": "m_menu"}]]})
    elif data == "m_summary":
        with get_db() as conn:
            c = conn.cursor()
            res = c.execute("SELECT COUNT(*) as c, COALESCE(SUM(profit),0) as t FROM sales WHERE DATE(sold_at)=CURRENT_DATE").fetchone()
            pend = c.execute("SELECT COUNT(*) as c, COALESCE(SUM(profit),0) as t FROM sales WHERE DATE(sold_at)=CURRENT_DATE AND payment_status='pending'").fetchone()
        text = f"📊 *DAILY SUMMARY*\n\n🛒 Sales: {res['c']}\n💰 Profit: GHS {res['t']:.2f}\n⏳ Pending: GHS {pend['t']:.2f}"
        edit_message(chat_id, msg_id, text, {"inline_keyboard": [[{"text": "🏠 Main Menu", "callback_data": "m_menu"}]]})
    elif data == "m_recent":
        with get_db() as conn:
            sales = conn.cursor().execute("SELECT * FROM sales ORDER BY sold_at DESC LIMIT 5").fetchall()
        text = "📜 *RECENT SALES*\n\n" + "".join([f"• {s['item_name']} x{s['quantity']}\n  👤 {s['customer_info']} | 💰 GHS {s['profit']:.2f}\n\n" for s in sales])
        edit_message(chat_id, msg_id, text, {"inline_keyboard": [[{"text": "🏠 Main Menu", "callback_data": "m_menu"}]]})
    elif data == "m_add":
        if chat_id not in OWNER_IDS: return edit_message(chat_id, msg_id, "❌ Owners only.", {"inline_keyboard": [[{"text": "🏠 Menu", "callback_data": "m_menu"}]]})
        save_state(chat_id, "an_name")
        edit_message(chat_id, msg_id, "➕ *ADD STOCK*\n\n*Type item name:*", {"inline_keyboard": [[{"text": "❌ Cancel", "callback_data": "m_menu"}]]})
    elif data == "an_ok":
        state, d = get_state(chat_id)
        with get_db() as conn:
            conn.cursor().execute("INSERT INTO stock (item_name, color, quantity, cost_price, selling_price, category) VALUES (%s,%s,%s,%s,%s,%s)",
                                  (d['name'], d.get('color',''), d['qty'], d['cost'], d['sell'], d['cat']))
            conn.commit()
        clear_state(chat_id)
        edit_message(chat_id, msg_id, f"✅ *Added {d['name']}!*", {"inline_keyboard": [[{"text": "🏠 Menu", "callback_data": "m_menu"}]]})
    else:
        edit_message(chat_id, msg_id, "❓ Unknown action.", {"inline_keyboard": [[{"text": "🏠 Menu", "callback_data": "m_menu"}]]})

def build_main_menu(chat_id):
    is_owner = chat_id in OWNER_IDS
    buttons = [
        [{"text": "📋 View Stock", "callback_data": "m_view"}, {"text": "💰 Record Sale", "callback_data": "m_sale"}],
        [{"text": "📜 Recent Sales", "callback_data": "m_recent"}, {"text": "📊 Daily Summary", "callback_data": "m_summary"}]
    ]
    if is_owner:
        buttons.extend([
            [{"text": "➕ Add Stock", "callback_data": "m_add"}, {"text": "✏️ Edit Item", "callback_data": "m_edit"}],
            [{"text": "🗑️ Remove Item", "callback_data": "m_remove"}, {"text": "⚠️ Low Stock", "callback_data": "m_low"}],
            [{"text": "⏳ Pending Payments", "callback_data": "m_pending"}]
        ])
    text = "📊 *LAPYPLUG — MAIN MENU*\n\nWelcome. What would you like to do?"
    return text, {"inline_keyboard": buttons}

def process_sale(chat_id, item_id, qty, cust, status, msg_id):
    with get_db() as conn:
        c = conn.cursor()
        item = c.execute("SELECT * FROM stock WHERE id=%s", (item_id,)).fetchone()
        if not item or item['quantity'] < qty:
            return edit_message(chat_id, msg_id, "❌ Not enough stock.", {"inline_keyboard": [[{"text": "🏠 Menu", "callback_data": "m_menu"}]]})
        
        new_qty = item['quantity'] - qty
        profit = (item['selling_price'] - item['cost_price']) * qty
        c.execute("UPDATE stock SET quantity=%s WHERE id=%s", (new_qty, item_id))
        c.execute("INSERT INTO sales (item_name, color, quantity, profit, sold_by, customer_info, payment_status) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                  (item['item_name'], item['color'], qty, profit, chat_id, cust, status))
        conn.commit()
    
    text = f"✅ *Sale Recorded!*\n\n📦 {item['item_name']} x{qty}\n👤 {cust}\n💰 Profit: GHS {profit:.2f}\n📉 Remaining: {new_qty}"
    edit_message(chat_id, msg_id, text, {"inline_keyboard": [[{"text": "💰 Sell More", "callback_data": "m_sale"}, {"text": "🏠 Menu", "callback_data": "m_menu"}]]})
    
    for target in (NOTIFICATION_IDS or OWNER_IDS):
        send_message(target, f"🔔 Sale: {item['item_name']} x{qty} — GHS {profit:.2f} ({status})")

# --- TELEGRAM TEXT HANDLER ---
def handle_text_message(chat_id, text):
    text = text.strip()
    if text == "/start":
        text_msg, markup = build_main_menu(chat_id)
        send_message(chat_id, text_msg, markup)
        clear_state(chat_id)
        return

    state, d = get_state(chat_id)
    if not state: return

    if state.startswith("sq_"):
        item_id = int(state.split("_")[1])
        try:
            qty = int(text)
            if qty <= 0: raise ValueError
        except ValueError:
            return send_message(chat_id, "❌ Enter a valid number.")
        markup = {"inline_keyboard": [
            [{"text": "🚶 Walk-in", "callback_data": f"sw_{item_id}_{qty}"}],
            [{"text": "✍️ Enter Customer", "callback_data": f"st_{item_id}_{qty}"}],
            [{"text": "❌ Cancel", "callback_data": "m_menu"}]
        ]}
        send_message(chat_id, f"✅ Qty: *{qty}*\n\nWho is buying?", markup)
    elif state.startswith("st_"):
        parts = state.split("_")
        d = {'cust': text}
        save_state(chat_id, f"spay_{parts[1]}_{parts[2]}", d)
        markup = {"inline_keyboard": [
            [{"text": "💵 Paid Now", "callback_data": f"sp_{parts[1]}_{parts[2]}"}],
            [{"text": "⏳ Pay Later", "callback_data": f"scred_{parts[1]}_{parts[2]}"}]
        ]}
        send_message(chat_id, f"✅ Customer: *{text}*\n\nPayment status?", markup)
    elif state == "an_name":
        d = {'name': text}
        save_state(chat_id, "an_qty", d)
        send_message(chat_id, f"✅ Item: *{text}*\n\n*Quantity?*")
    elif state == "an_qty":
        try: d['qty'] = int(text)
        except ValueError: return send_message(chat_id, "❌ Valid number.")
        save_state(chat_id, "an_cost", d)
        send_message(chat_id, f"✅ Qty: *{text}*\n\n*Cost Price?*")
    elif state == "an_cost":
        try: d['cost'] = float(text)
        except ValueError: return send_message(chat_id, "❌ Valid number.")
        save_state(chat_id, "an_sell", d)
        send_message(chat_id, f"✅ Cost: *GHS {text}*\n\n*Selling Price?*")
    elif state == "an_sell":
        try: d['sell'] = float(text)
        except ValueError: return send_message(chat_id, "❌ Valid number.")
        save_state(chat_id, "an_cat", d)
        send_message(chat_id, f"✅ Sell: *GHS {text}*\n\n*Category? (e.g., Laptops)*")
    elif state == "an_cat":
        d['cat'] = text
        save_state(chat_id, "an_confirm", d)
        markup = {"inline_keyboard": [[{"text": "✅ Confirm", "callback_data": "an_ok"}, {"text": "❌ Cancel", "callback_data": "m_menu"}]]}
        send_message(chat_id, f"➕ *CONFIRM*\n\nName: {d['name']}\nQty: {d['qty']}\nCost: {d['cost']}\nSell: {d['sell']}\nCat: {text}", markup)
    else:
        send_message(chat_id, "🤔 I didn't catch that.", {"inline_keyboard": [[{"text": "🏠 Menu", "callback_data": "m_menu"}]]})
        clear_state(chat_id)

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
