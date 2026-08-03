import os
import logging
import json
import requests
import time
from collections import defaultdict
from datetime import datetime
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import secrets
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# --- CONFIGURATION ---
load_dotenv()

# --- LOGGING SETUP ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- ENVIRONMENT VARIABLES ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
OWNER_IDS = [int(id.strip()) for id in os.getenv("OWNER_ID", "").split(",") if id.strip()]
SECRETARY_IDS = [int(id.strip()) for id in os.getenv("SECRETARY_ID", "").split(",") if id.strip()]
NOTIFICATION_IDS = [int(id.strip()) for id in os.getenv("NOTIFICATION_IDS", "").split(",") if id.strip()]
ALLOWED_IDS = OWNER_IDS + SECRETARY_IDS
API_URL = f"htfrom flask import Flask, request, jsonify, render_template, redirect, url_for, session
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
DATABASE_URL = os.getenv("DATABASE_URL")

# --- RATE LIMITING ---
rate_limit_store = defaultdict(list)
RATE_LIMIT_WINDOW = 60
RATE_LIMIT_MAX = 30

def check_rate_limit(chat_id):
    now = time.time()
    rate_limit_store[chat_id] = [t for t in rate_limit_store[chat_id] if now - t < RATE_LIMIT_WINDOW]
    if len(rate_limit_store[chat_id]) >= RATE_LIMIT_MAX:
        return False
    rate_limit_store[chat_id].append(now)
    return True

# --- DATABASE FUNCTIONS ---
def get_db():
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS stock (
        id SERIAL PRIMARY KEY,
        item_name TEXT NOT NULL,
        color TEXT DEFAULT '',
        quantity INTEGER DEFAULT 0,
        cost_price REAL DEFAULT 0.0,
        selling_price REAL DEFAULT 0.0,
        category TEXT NOT NULL,
        low_stock_threshold INTEGER DEFAULT 5,
        UNIQUE(item_name, color)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS sales (
        id SERIAL PRIMARY KEY,
        item_name TEXT NOT NULL,
        color TEXT DEFAULT '',
        quantity INTEGER NOT NULL,
        profit REAL NOT NULL,
        sold_by INTEGER NOT NULL,
        customer_info TEXT DEFAULT 'Walk-in',
        payment_status TEXT DEFAULT 'paid',
        sold_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS user_state (
        chat_id BIGINT PRIMARY KEY,
        state TEXT,
        data TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    conn.commit()
    
    # --- SEED DATA ---
    colors = ["Black", "White", "Silver", "Grey", "Blue", "Red"]
    items = []

    # 1. LAPTOPS
    laptops = [
        "HP 250 G9 (i5 / 8GB / 256GB SSD)",
        "HP 250 G9 (i7 / 16GB / 512GB SSD)",
        "HP ProBook 450 G10 (i5 / 8GB / 512GB SSD)",
        "HP EliteBook 840 G9 (i7 / 16GB / 512GB SSD)",
        "HP Pavilion 15 (Ryzen 5 / 8GB / 512GB SSD)",
        "Dell Inspiron 15 (i5 / 8GB / 256GB SSD)",
        "Dell Inspiron 15 (i7 / 16GB / 512GB SSD)",
        "Dell Latitude 5420 (i5 / 8GB / 256GB SSD)",
        "Dell XPS 13 (i7 / 16GB / 512GB SSD)",
        "Dell Vostro 3520 (i3 / 4GB / 256GB SSD)",
        "Lenovo IdeaPad 3 (Ryzen 3 / 8GB / 256GB SSD)",
        "Lenovo ThinkPad E14 (i5 / 8GB / 512GB SSD)",
        "Lenovo ThinkPad T14 (i7 / 16GB / 512GB SSD)",
        "Lenovo IdeaPad Slim 3 (Ryzen 5 / 8GB / 512GB SSD)",
        "Acer Aspire 3 (i3 / 4GB / 256GB SSD)",
        "Acer Aspire 5 (i5 / 8GB / 512GB SSD)",
        "Acer Swift 3 (Ryzen 5 / 8GB / 512GB SSD)",
        "ASUS VivoBook 15 (i5 / 8GB / 512GB SSD)",
        "ASUS ROG Strix G15 (Ryzen 7 / 16GB / 512GB SSD)",
        "ASUS TUF Gaming A15 (Ryzen 5 / 8GB / 512GB SSD)",
        "MacBook Air M1 (8GB / 256GB SSD / 2020)",
        "MacBook Air M2 (8GB / 256GB SSD / 2022)",
        "MacBook Pro 14 M3 (16GB / 512GB SSD / 2023)",
        "HP Chromebook 14 (4GB / 64GB eMMC)",
        "Lenovo Chromebook 3 (4GB / 64GB eMMC)",
    ]
    for laptop in laptops:
        items.append((laptop, "", 0, 0.0, 0.0, "Laptops", 2))

    # 2. DESKTOP COMPUTERS
    desktops = [
        "HP ProDesk Desktop Tower (i5 / 8GB / 512GB SSD)",
        "HP ProDesk Desktop Tower (i7 / 16GB / 1TB SSD)",
        "Dell OptiPlex Desktop Tower (i5 / 8GB / 256GB SSD)",
        "Dell OptiPlex Desktop Tower (i7 / 16GB / 512GB SSD)",
        "Lenovo ThinkCentre Desktop Tower (i5 / 8GB / 512GB SSD)",
        "HP All-in-One 24\" (i5 / 8GB / 512GB SSD)",
        "Dell All-in-One 24\" (i7 / 16GB / 1TB SSD)",
        "Lenovo IdeaCentre AIO 24\" (Ryzen 5 / 8GB / 512GB SSD)",
        "Intel NUC Mini PC (i5 / 8GB / 256GB SSD)",
        "HP ProDesk Mini PC (i5 / 8GB / 256GB SSD)",
    ]
    for desktop in desktops:
        items.append((desktop, "", 0, 0.0, 0.0, "Desktops", 2))

    # 3. MONITORS
    monitors = [
        "HP 21.5\" FHD Monitor (1920x1080)",
        "HP 24\" FHD Monitor (1920x1080)",
        "Dell 22\" HD Monitor (1366x768)",
        "Dell 24\" FHD Monitor (1920x1080)",
        "Samsung 24\" FHD Monitor (1920x1080)",
        "LG 24\" FHD IPS Monitor (1920x1080)",
        "LG 27\" QHD Monitor (2560x1440)",
        "Acer Nitro 24\" Gaming (144Hz / 1ms)",
        "ASUS TUF 27\" Gaming (165Hz / 1ms)",
        "Samsung Odyssey 27\" Gaming (165Hz / QHD)",
    ]
    for monitor in monitors:
        items.append((monitor, "", 0, 0.0, 0.0, "Monitors", 3))

    # 4. KEYBOARDS
    keyboards = [
        "HP Wired USB Keyboard",
        "Dell Wired USB Keyboard",
        "Lenovo Wired USB Keyboard",
        "Logitech Wireless Keyboard (USB)",
        "Logitech Bluetooth Keyboard",
        "Logitech Keyboard + Mouse Combo",
        "Redragon Mechanical Gaming Keyboard (RGB)",
        "Razer Mechanical Gaming Keyboard (RGB)",
        "Corsair Mechanical Gaming Keyboard (RGB)",
    ]
    for kb in keyboards:
        items.append((kb, "", 0, 0.0, 0.0, "Keyboards", 5))

    # 5. MICE
    mice = [
        "HP Wired USB Mouse",
        "Dell Wired USB Mouse",
        "Lenovo Wired USB Mouse",
        "Logitech Wireless Mouse (USB)",
        "Logitech Bluetooth Silent Mouse",
        "Logitech MX Master 3 (Bluetooth)",
        "Redragon Gaming Mouse (RGB)",
        "Razer DeathAdder Gaming Mouse",
    ]
    for mouse in mice:
        items.append((mouse, "", 0, 0.0, 0.0, "Mice", 5))

    # 6. STORAGE
    storage = [
        "Seagate External HDD 1TB (USB 3.0)",
        "Seagate External HDD 2TB (USB 3.0)",
        "WD External HDD 1TB (USB 3.0)",
        "WD External HDD 2TB (USB 3.0)",
        "Kingston A400 SSD 240GB (SATA)",
        "Kingston A400 SSD 480GB (SATA)",
        "Samsung 870 EVO SSD 500GB (SATA)",
        "Samsung 970 EVO NVMe SSD 500GB",
        "Samsung 980 NVMe SSD 1TB",
        "WD Blue NVMe SSD 500GB",
        "Kingston NV2 NVMe SSD 1TB",
        "SanDisk USB Flash Drive 16GB",
        "SanDisk USB Flash Drive 32GB",
        "SanDisk USB Flash Drive 64GB",
        "SanDisk USB Flash Drive 128GB",
        "SanDisk MicroSD Card 32GB",
        "SanDisk MicroSD Card 64GB",
        "SanDisk MicroSD Card 128GB",
    ]
    for item in storage:
        items.append((item, "", 0, 0.0, 0.0, "Storage", 5))

    # 7. ACCESSORIES & PARTS
    accessories_no_color = [
        "HP Laptop Charger (45W)",
        "HP Laptop Charger (65W)",
        "Dell Laptop Charger (65W)",
        "Lenovo Laptop Charger (65W)",
        "Universal Laptop Charger (90W)",
        "USB-C Laptop Charger (65W PD)",
        "HP Laptop Battery (Original)",
        "Dell Laptop Battery (Original)",
        "Lenovo Laptop Battery (Original)",
        "HP Laptop Screen 15.6\" (FHD)",
        "Dell Laptop Screen 15.6\" (FHD)",
        "Lenovo Laptop Screen 14\" (FHD)",
        "Laptop Keyboard Replacement (HP)",
        "Laptop Keyboard Replacement (Dell)",
        "Laptop Keyboard Replacement (Lenovo)",
        "Webcam 1080p USB",
        "USB 3.0 Hub (4-Port)",
        "USB-C Hub (7-in-1)",
        "HDMI Cable 1.5m",
        "HDMI Cable 3m",
        "VGA Cable 1.5m",
        "DisplayPort Cable 1.5m",
        "USB-C to HDMI Adapter",
        "HDMI to VGA Converter",
        "Screen Protector (Laptop 15.6\")",
        "Laptop Cleaning Kit",
        "Thermal Paste (Arctic MX-4)",
        "Laptop Cooling Pad",
        "External DVD Writer (USB)",
        "Laptop Docking Station (USB-C)",
    ]
    for item in accessories_no_color:
        items.append((item, "", 0, 0.0, 0.0, "Accessories", 5))

    for color in colors:
        items.append(("Laptop Bag 15.6\"", color, 0, 0.0, 0.0, "Accessories", 3))
        items.append(("Laptop Sleeve 14\"", color, 0, 0.0, 0.0, "Accessories", 3))
        items.append(("Mouse Pad (Standard)", color, 0, 0.0, 0.0, "Accessories", 5))
        items.append(("Gaming Mouse Pad (XL)", color, 0, 0.0, 0.0, "Accessories", 3))

    # 8. NETWORKING
    networking = [
        "TP-Link WiFi Router (N300)",
        "TP-Link WiFi Router (AC1200)",
        "TP-Link WiFi Router (AX1500 WiFi 6)",
        "D-Link WiFi Router (N300)",
        "Mercusys WiFi Router (AC1200)",
        "Ethernet Cable Cat6 (1.5m)",
        "Ethernet Cable Cat6 (3m)",
        "Ethernet Cable Cat6 (5m)",
        "Ethernet Cable Cat6 (10m)",
        "USB WiFi Adapter (300Mbps)",
        "USB WiFi Adapter (Dual Band AC)",
        "TP-Link 5-Port Network Switch",
        "TP-Link 8-Port Network Switch",
        "TP-Link 16-Port Network Switch",
        "RJ45 Connector (Pack of 50)",
        "Network Cable Tester",
    ]
    for item in networking:
        items.append((item, "", 0, 0.0, 0.0, "Networking", 5))

    # 9. AUDIO
    audio = [
        "HP Wired Headphones (3.5mm)",
        "Logitech Wired Headset with Mic",
        "JBL Wired Earphones",
        "Sony Wired Earphones",
        "JBL Tune Wireless Bluetooth Headphones",
        "Sony WH-CH520 Wireless Headphones",
        "Apple AirPods (2nd Gen)",
        "Samsung Galaxy Buds",
        "Oraimo FreePods (True Wireless)",
        "Edifier R1280T Bookshelf Speakers",
        "Logitech Stereo Speakers (USB)",
        "HP USB Condenser Microphone",
        "Boya BY-M1 Lavalier Microphone",
    ]
    for item in audio:
        items.append((item, "", 0, 0.0, 0.0, "Audio", 3))

    # 10. PRINTERS & SCANNERS
    printers = [
        "HP DeskJet 2700 Inkjet Printer",
        "HP DeskJet 4100 All-in-One Inkjet",
        "Canon PIXMA MG2570S Inkjet",
        "HP LaserJet Pro M15w Mono Laser",
        "HP LaserJet Pro M404dn Mono Laser",
        "Canon imageCLASS LBP6030 Mono Laser",
        "HP ScanJet 200 s1 Flatbed Scanner",
        "Canon CanoScan LiDE 300 Scanner",
        "HP 680 Black Ink Cartridge",
        "HP 680 Tri-Color Ink Cartridge",
        "HP 12A Laser Toner (Black)",
        "Canon PG-47 Black Ink Cartridge",
        "Canon CL-57 Tri-Color Ink Cartridge",
        "A4 Printer Paper (500 Sheets)",
        "A4 Printer Paper (Box of 5 Reams)",
    ]
    for item in printers:
        items.append((item, "", 0, 0.0, 0.0, "Printers", 3))

    # 11. SOFTWARE
    software = [
        "Windows 10 Home License (OEM)",
        "Windows 10 Pro License (OEM)",
        "Windows 11 Home License (OEM)",
        "Windows 11 Pro License (OEM)",
        "Microsoft Office 2021 Home & Business",
        "Microsoft Office 2021 Professional Plus",
        "Microsoft 365 Personal (1 Year)",
        "Kaspersky Antivirus (1 Year / 1 PC)",
        "ESET NOD32 Antivirus (1 Year)",
        "Norton 360 Antivirus (1 Year)",
    ]
    for item in software:
        items.append((item, "", 0, 0.0, 0.0, "Software", 5))

    # 12. POWER PROTECTION
    power = [
        "UPS 650VA (APC / Mercury)",
        "UPS 1000VA (APC / Mercury)",
        "UPS 1500VA (APC)",
        "Surge Protector 4-Way",
        "Surge Protector 6-Way with USB",
        "Extension Box 4-Way (3m Cable)",
        "Extension Box 6-Way (5m Cable)",
        "Voltage Stabilizer 1000VA",
        "Voltage Stabilizer 2000VA",
    ]
    for item in power:
        items.append((item, "", 0, 0.0, 0.0, "Power Protection", 3))

    # 13. GAMING
    gaming = [
        "Xbox Wireless Controller",
        "PlayStation DualSense Controller",
        "Logitech F310 Gamepad (USB)",
        "Razer Gaming Headset",
        "HyperX Cloud Stinger Headset",
        "Gaming Chair (Standard)",
        "RGB LED Strip (2m USB)",
    ]
    for item in gaming:
        items.append((item, "", 0, 0.0, 0.0, "Gaming", 3))

    # 14. REPAIR TOOLS
    tools = [
        "Precision Screwdriver Set (25-in-1)",
        "Anti-Static Wrist Strap",
        "Tweezers Set (ESD Safe)",
        "Soldering Iron Kit (60W)",
        "Multimeter Digital",
        "Hot Air Gun Station",
        "USB Bootable Flash Drive (with tools)",
    ]
    for item in tools:
        items.append((item, "", 0, 0.0, 0.0, "Repair Tools", 3))

    # Insert all items
    for item in items:
        try:
            c.execute("""
                INSERT INTO stock (item_name, color, quantity, cost_price, selling_price, category, low_stock_threshold)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (item_name, color) DO NOTHING
            """, item)
        except Exception as e:
            logger.error(f"Seed error: {e}")
    # ADD THIS AT THE END OF init_db() BEFORE conn.commit()
    from werkzeug.security import generate_password_hash
    # Default credentials: admin / Victory2024!
    default_hash = generate_password_hash("Victory2024!")
    try:
        c.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s) ON CONFLICT (username) DO NOTHING", 
                  ("admin", default_hash))
    except Exception as e:
        logger.error(f"User seed error: {e}")
    
    conn.commit()
    c.close()
    conn.close()
    logger.info(f"Database initialized with {len(items)} seed items")

# --- TELEGRAM API FUNCTIONS ---
def send_message(chat_id, text, reply_markup=None):
    url = f"{API_URL}/sendMessage"
    data = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if reply_markup:
        data["reply_markup"] = reply_markup
    try:
        response = requests.post(url, json=data, timeout=10)
        if response.status_code != 200:
            logger.error(f"Telegram API error: {response.text}")
    except Exception as e:
        logger.error(f"Send Error: {e}")

def send_force_reply(chat_id, text, placeholder="Type here..."):
    url = f"{API_URL}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "reply_markup": {"force_reply": True, "input_field_placeholder": placeholder}
    }
    try:
        requests.post(url, json=data, timeout=10)
    except Exception as e:
        logger.error(f"Send Error: {e}")

def answer_callback(query_id, text=""):
    url = f"{API_URL}/answerCallbackQuery"
    data = {"callback_query_id": query_id, "text": text}
    try:
        requests.post(url, json=data, timeout=10)
    except Exception as e:
        logger.error(f"Answer Callback Error: {e}")

def edit_message(chat_id, message_id, text, reply_markup=None):
    url = f"{API_URL}/editMessageText"
    data = {"chat_id": chat_id, "message_id": message_id, "text": text, "parse_mode": "Markdown"}
    if reply_markup:
        data["reply_markup"] = reply_markup
    try:
        response = requests.post(url, json=data, timeout=10)
        if response.status_code != 200:
            logger.warning(f"Edit message failed: {response.text}")
    except Exception as e:
        logger.error(f"Edit Message Error: {e}")

# --- UI BUILDERS ---
def build_main_menu(chat_id):
    is_owner = chat_id in OWNER_IDS
    if is_owner:
        buttons = [
            [{"text": "📋 View Stock", "callback_data": "m_view"}, {"text": "💰 Record Sale", "callback_data": "m_sale"}],
            [{"text": "📜 Recent Sales", "callback_data": "m_recent"}, {"text": "📊 Daily Summary", "callback_data": "m_summary"}],
            [{"text": "➕ Add Stock", "callback_data": "m_add"}, {"text": "✏️ Edit Item", "callback_data": "m_edit"}],
            [{"text": "🗑️ Remove Item", "callback_data": "m_remove"}, {"text": "⚠️ Low Stock", "callback_data": "m_low"}],
            [{"text": "⏳ Pending Payments", "callback_data": "m_pending"}]
        ]
        text = "📊 *VICTORY VENTURE — MAIN MENU*\n\nWelcome, Boss. What would you like to do?"
    else:
        buttons = [
            [{"text": "📋 View Stock", "callback_data": "m_view"}, {"text": "💰 Record Sale", "callback_data": "m_sale"}],
            [{"text": "📜 Recent Sales", "callback_data": "m_recent"}, {"text": "📊 Daily Summary", "callback_data": "m_summary"}]
        ]
        text = "📊 *VICTORY VENTURE — MAIN MENU*\n\nWelcome. What would you like to do?"
    return text, {"inline_keyboard": buttons}

def get_color_buttons():
    return [
        [{"text": "⚫ Black", "callback_data": "c_Black"}, {"text": "⚪ White", "callback_data": "c_White"}],
        [{"text": "⚪ Silver", "callback_data": "c_Silver"}, {"text": "⚙️ Grey", "callback_data": "c_Grey"}],
        [{"text": "🔵 Blue", "callback_data": "c_Blue"}, {"text": "🔴 Red", "callback_data": "c_Red"}],
        [{"text": "📝 Custom", "callback_data": "c_Custom"}]
    ]

# --- BUTTON HANDLER ---
def button_handler(query):
    chat_id = query['message']['chat']['id']
    message_id = query['message']['message_id']
    callback_data = query['data']
    answer_callback(query['id'])

    if not check_rate_limit(chat_id):
        edit_message(chat_id, message_id, "⚠️ Too many requests. Please wait a moment.", 
                    {"inline_keyboard": [[{"text": "🏠 Main Menu", "callback_data": "m_menu"}]]})
        return

    if callback_data == "m_menu":
        text, markup = build_main_menu(chat_id)
        clear_state(chat_id)
        edit_message(chat_id, message_id, text, reply_markup=markup)
        return

    elif callback_data == "m_view":
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT DISTINCT category FROM stock ORDER BY category")
        categories = c.fetchall()
        conn.close()
        if not categories:
            text = "📋 No items in stock yet."
            markup = {"inline_keyboard": [[{"text": "🏠 Main Menu", "callback_data": "m_menu"}]]}
        else:
            buttons = [[{"text": cat['category'], "callback_data": f"vc_{cat['category'][:30]}"}] for cat in categories]
            buttons.append([{"text": "🏠 Main Menu", "callback_data": "m_menu"}])
            text = "📋 *VIEW STOCK*\n\nSelect a category:"
            markup = {"inline_keyboard": buttons}
        edit_message(chat_id, message_id, text, reply_markup=markup)
        return

    elif callback_data.startswith("vc_"):
        category = callback_data[3:]
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM stock WHERE category=%s ORDER BY item_name", (category,))
        items = c.fetchall()
        conn.close()
        if not items:
            text = f"📋 No items in *{category}*."
        else:
            text = f"📋 *{category}*\n\n"
            for item in items:
                color_str = f" ({item['color']})" if item['color'] else ""
                text += f"• *{item['item_name']}*{color_str}\n  Qty: {item['quantity']} | Price: GHS {item['selling_price']:.0f}\n\n"
        markup = {"inline_keyboard": [[{"text": "📋 View Stock", "callback_data": "m_view"}, {"text": "🏠 Main Menu", "callback_data": "m_menu"}]]}
        edit_message(chat_id, message_id, text, reply_markup=markup)
        return

    elif callback_data == "m_sale":
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT DISTINCT category FROM stock WHERE quantity > 0 ORDER BY category")
        categories = c.fetchall()
        conn.close()
        if not categories:
            text = "📋 No items in stock to sell."
            markup = {"inline_keyboard": [[{"text": "🏠 Main Menu", "callback_data": "m_menu"}]]}
        else:
            buttons = [[{"text": cat['category'], "callback_data": f"sc_{cat['category'][:30]}"}] for cat in categories]
            buttons.append([{"text": "🏠 Main Menu", "callback_data": "m_menu"}])
            text = "💰 *RECORD SALE*\n\nSelect the item category:"
            markup = {"inline_keyboard": buttons}
        edit_message(chat_id, message_id, text, reply_markup=markup)
        return

    elif callback_data.startswith("sc_"):
        category = callback_data[3:]
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM stock WHERE category=%s AND quantity > 0 ORDER BY item_name", (category,))
        items = c.fetchall()
        conn.close()
        if not items:
            text = f"No items in stock for *{category}*."
            markup = {"inline_keyboard": [[{"text": "🏠 Main Menu", "callback_data": "m_menu"}]]}
        else:
            buttons = []
            for item in items:
                color_str = f" ({item['color']})" if item['color'] else ""
                title = f"{item['item_name']}{color_str} ({item['quantity']})"
                buttons.append([{"text": title, "callback_data": f"si_{item['id']}"}])
            buttons.append([{"text": "🏠 Main Menu", "callback_data": "m_menu"}])
            text = "💰 *RECORD SALE*\n\nSelect the item sold:"
            markup = {"inline_keyboard": buttons}
        edit_message(chat_id, message_id, text, reply_markup=markup)
        return

    elif callback_data.startswith("si_"):
        item_id = int(callback_data[3:])
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM stock WHERE id=%s", (item_id,))
        item = c.fetchone()
        conn.close()
        if not item:
            text = "Item not found."
            markup = {"inline_keyboard": [[{"text": "🏠 Main Menu", "callback_data": "m_menu"}]]}
        else:
            color_str = f" ({item['color']})" if item['color'] else ""
            text = f"💰 *RECORD SALE*\n\nItem: *{item['item_name']}*{color_str}\nAvailable: {item['quantity']} pcs\n\n*How many are you selling?*\n\n_Tap below to type the amount._"
            save_state(chat_id, f"sq_{item_id}")
            markup = {"inline_keyboard": [[{"text": "❌ Cancel", "callback_data": "m_menu"}]]}
            edit_message(chat_id, message_id, text, reply_markup=markup)
            send_force_reply(chat_id, "👇 *Type the quantity now:*", "e.g. 5")
        return

    elif callback_data.startswith("sw_"):
        parts = callback_data.split("_")
        item_id = int(parts[1])
        qty = int(parts[2])
        process_sale_confirmation(chat_id, item_id, qty, "Walk-in Customer", payment_status='paid', message_id=message_id)
        return

    elif callback_data.startswith("sp_") or callback_data.startswith("scred_"):
        payment_status = 'paid' if callback_data.startswith("sp_") else 'pending'
        parts = callback_data.split("_")
        item_id = int(parts[1])
        qty = int(parts[2])
        
        state, data_dict = get_state(chat_id)
        customer_info = data_dict.get('customer_info', 'Walk-in Customer')
        
        process_sale_confirmation(chat_id, item_id, qty, customer_info, payment_status=payment_status, message_id=message_id)
        clear_state(chat_id)
        return

    elif callback_data.startswith("st_"):
        parts = callback_data.split("_")
        item_id = int(parts[1])
        qty = int(parts[2])
        save_state(chat_id, f"st_{item_id}_{qty}")
        send_force_reply(chat_id, "💰 *RECORD SALE*\n\nPlease type the Customer's Name & Phone Number:\n\n_The keyboard is open. Type and send._", "e.g. John 0241234567")
        return

    elif callback_data == "m_recent":
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM sales ORDER BY sold_at DESC LIMIT 10")
        sales = c.fetchall()
        conn.close()
        if not sales:
            text = "📜 No recent sales recorded."
        else:
            text = "📜 *RECENT SALES (Last 10)*\n\n"
            for sale in sales:
                color_str = f" ({sale['color']})" if sale['color'] else ""
                dt = sale['sold_at']
                if dt:
                    try:
                        dt_obj = datetime.strptime(str(dt), "%Y-%m-%d %H:%M:%S")
                        dt_str = dt_obj.strftime("%d/%m/%Y %I:%M %p")
                    except:
                        dt_str = str(dt)
                else:
                    dt_str = "Unknown"
                text += f"• {sale['item_name']}{color_str} x{sale['quantity']}\n  🕒 {dt_str}\n  👤 {sale['customer_info']}\n  💰 Profit: GHS {sale['profit']:.2f}\n\n"
        markup = {"inline_keyboard": [[{"text": "🏠 Main Menu", "callback_data": "m_menu"}]]}
        edit_message(chat_id, message_id, text, reply_markup=markup)
        return

    elif callback_data == "m_add":
        if chat_id not in OWNER_IDS:
            text = "❌ Only the owner can add stock."
            markup = {"inline_keyboard": [[{"text": "🏠 Main Menu", "callback_data": "m_menu"}]]}
            edit_message(chat_id, message_id, text, reply_markup=markup)
            return
        save_state(chat_id, "an_name")
        send_force_reply(chat_id, "➕ *ADD STOCK*\n\nStep 1/5: What is the item name?\n\n_The keyboard is open. Type the name and send._", "e.g. Dell XPS 15")
        return

    elif callback_data.startswith("c_"):
        color = callback_data[2:]
        state, data_dict = get_state(chat_id)
        if color == "Custom":
            save_state(chat_id, "an_color_text", data_dict)
            send_force_reply(chat_id, "➕ *ADD STOCK*\n\nPlease type the custom color name:", "e.g. Rose Gold")
            return
        else:
            data_dict['color'] = color if color != "none" else ""
            conn = get_db()
            c = conn.cursor()
            c.execute("SELECT * FROM stock WHERE item_name=%s AND color=%s", (data_dict['name'], data_dict['color']))
            item = c.fetchone()
            conn.close()
            if item:
                data_dict['existing_id'] = item['id']
                data_dict['existing_qty'] = item['quantity']
                data_dict['existing_cost'] = item['cost_price']
                data_dict['existing_sell'] = item['selling_price']
                save_state(chat_id, "an_existing", data_dict)
                color_str = f" ({color})" if color != "none" else ""
                text = f"Found: *{data_dict['name']}*{color_str}\n\nQty: {item['quantity']}\nCost: GHS {item['cost_price']:.2f}\nSell: GHS {item['selling_price']:.2f}\n\nAre you topping up stock or changing prices?"
                markup = {"inline_keyboard": [
                    [{"text": "📦 Top Up Stock", "callback_data": "at_up"}, {"text": "💰 Update Prices", "callback_data": "at_price"}],
                    [{"text": "❌ Cancel", "callback_data": "m_menu"}]
                ]}
                edit_message(chat_id, message_id, text, reply_markup=markup)
            else:
                save_state(chat_id, "an_qty", data_dict)
                text = f"✅ Color: *{color}*\n\nHow many units are you adding?\n\n_Tap below to type the amount._"
                markup = {"inline_keyboard": [[{"text": "❌ Cancel", "callback_data": "m_menu"}]]}
                edit_message(chat_id, message_id, text, reply_markup=markup)
                send_force_reply(chat_id, "👇 *Type the quantity now:*", "e.g. 15")
        return

    elif callback_data == "at_up":
        state, data_dict = get_state(chat_id)
        if state != "an_existing":
            edit_message(chat_id, message_id, "❌ Session expired. Please start over.", {"inline_keyboard": [[{"text": "🏠 Main Menu", "callback_data": "m_menu"}]]})
            return
        save_state(chat_id, "at_qty", data_dict)
        send_force_reply(chat_id, "📦 *TOP UP STOCK*\n\nHow many are you adding?\n\n_The keyboard is open. Type the number and send._", "e.g. 20")
        return

    elif callback_data == "at_price":
        state, data_dict = get_state(chat_id)
        if state != "an_existing":
            edit_message(chat_id, message_id, "❌ Session expired. Please start over.", {"inline_keyboard": [[{"text": "🏠 Main Menu", "callback_data": "m_menu"}]]})
            return
        save_state(chat_id, "at_cost", data_dict)
        send_force_reply(chat_id, "💰 *UPDATE PRICES*\n\nNew cost price per unit?\n\n_The keyboard is open. Type and send._", "e.g. 15.50")
        return

    elif callback_data.startswith("ac_"):
        state, data_dict = get_state(chat_id)
        if callback_data == "ac_custom":
            text = f"✅ Sell: *GHS {data_dict.get('sell', 0):.2f}*\n\nPlease type the custom category name:"
            markup = {"inline_keyboard": [[{"text": "❌ Cancel", "callback_data": "m_menu"}]]}
            save_state(chat_id, "an_cat_text", data_dict)
            send_force_reply(chat_id, text, "e.g. Tools")
            return
        else:
            category = callback_data[3:]
            data_dict['category'] = category
            save_state(chat_id, "an_confirm", data_dict)
            color_str = f" ({data_dict['color']})" if data_dict['color'] else ""
            text_msg = f"➕ *CONFIRM NEW ITEM*\n\nName: *{data_dict['name']}*{color_str}\nQuantity: {data_dict['qty']}\nCost: GHS {data_dict['cost']:.2f}\nSell: GHS {data_dict['sell']:.2f}\nCategory: {category}\n\nAdd this item?"
            markup = {"inline_keyboard": [[{"text": "✅ Confirm", "callback_data": "an_ok"}, {"text": "❌ Cancel", "callback_data": "m_menu"}]]}
            edit_message(chat_id, message_id, text_msg, reply_markup=markup)
            return

    elif callback_data == "an_ok":
        state, data_dict = get_state(chat_id)
        required_keys = ['name', 'color', 'qty', 'cost', 'sell', 'category']
        if not all(k in data_dict for k in required_keys):
            text = "❌ Incomplete data."
            markup = {"inline_keyboard": [[{"text": "🏠 Main Menu", "callback_data": "m_menu"}]]}
            clear_state(chat_id)
            edit_message(chat_id, message_id, text, reply_markup=markup)
            return
        conn = get_db()
        c = conn.cursor()
        try:
            c.execute("""INSERT INTO stock (item_name, color, quantity, cost_price, selling_price, category)
                         VALUES (%s, %s, %s, %s, %s, %s)""",
                         (data_dict['name'], data_dict['color'], data_dict['qty'],
                          data_dict['cost'], data_dict['sell'], data_dict['category']))
            conn.commit()
            color_str = f" ({data_dict['color']})" if data_dict['color'] else ""
            text = f"✅ *Added!*\n\n{data_dict['name']}{color_str} x{data_dict['qty']}\nCost: GHS {data_dict['cost']:.2f}\nSell: GHS {data_dict['sell']:.2f}\nCategory: {data_dict['category']}\n\n*What next?*"
            markup = {"inline_keyboard": [[{"text": "➕ Add More Stock", "callback_data": "m_add"}, {"text": "🏠 Main Menu", "callback_data": "m_menu"}]]}
        except psycopg2.IntegrityError:
            text = "❌ Item with same name and color already exists."
            markup = {"inline_keyboard": [[{"text": "➕ Add More Stock", "callback_data": "m_add"}, {"text": "🏠 Main Menu", "callback_data": "m_menu"}]]}
        finally:
            conn.close()
        clear_state(chat_id)
        edit_message(chat_id, message_id, text, reply_markup=markup)
        return

    elif callback_data == "m_edit":
        if chat_id not in OWNER_IDS:
            text = "❌ Only the owner can edit items."
            markup = {"inline_keyboard": [[{"text": "🏠 Main Menu", "callback_data": "m_menu"}]]}
            edit_message(chat_id, message_id, text, reply_markup=markup)
            return
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT DISTINCT category FROM stock ORDER BY category")
        categories = c.fetchall()
        conn.close()
        buttons = [[{"text": cat['category'], "callback_data": f"ec_{cat['category'][:30]}"}] for cat in categories]
        buttons.append([{"text": "🏠 Main Menu", "callback_data": "m_menu"}])
        text = "✏️ *EDIT ITEM*\n\nSelect a category:"
        markup = {"inline_keyboard": buttons}
        edit_message(chat_id, message_id, text, reply_markup=markup)
        return

    elif callback_data.startswith("ec_"):
        category = callback_data[3:]
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM stock WHERE category=%s ORDER BY item_name", (category,))
        items = c.fetchall()
        conn.close()
        if not items:
            text = f"No items in *{category}*."
            markup = {"inline_keyboard": [[{"text": "⬅️ Back", "callback_data": "m_edit"}]]}
        else:
            buttons = []
            for item in items:
                color_str = f" ({item['color']})" if item['color'] else ""
                title = f"{item['item_name']}{color_str} [Qty: {item['quantity']}]"
                buttons.append([{"text": title, "callback_data": f"ei_{item['id']}"}])
            buttons.append([{"text": "⬅️ Back to Categories", "callback_data": "m_edit"}])
            text = f"✏️ *EDIT: {category}*\n\nSelect the item to edit:"
            markup = {"inline_keyboard": buttons}
        edit_message(chat_id, message_id, text, reply_markup=markup)
        return

    elif callback_data.startswith("ei_"):
        item_id = int(callback_data[3:])
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM stock WHERE id=%s", (item_id,))
        item = c.fetchone()
        conn.close()
        if not item:
            text = "Item not found."
            markup = {"inline_keyboard": [[{"text": "⬅️ Back", "callback_data": "m_edit"}]]}
        else:
            color_str = f" ({item['color']})" if item['color'] else ""
            text = f"✏️ *EDIT ITEM*\n\n*{item['item_name']}*{color_str}\nCategory: {item['category']}\nQty: {item['quantity']}\nCost: GHS {item['cost_price']:.2f}\nSell: GHS {item['selling_price']:.2f}\n\n*What would you like to change?*"
            markup = {"inline_keyboard": [
                [{"text": "📦 Update Qty", "callback_data": f"eq_{item_id}"}, {"text": "💰 Update Cost", "callback_data": f"ecost_{item_id}"}],
                [{"text": "💵 Update Sell Price", "callback_data": f"esell_{item_id}"}, {"text": "🏷️ Update Category", "callback_data": f"ecat_{item_id}"}],
                [{"text": "⬅️ Back", "callback_data": f"ec_{item['category'][:30]}"}]
            ]}
        edit_message(chat_id, message_id, text, reply_markup=markup)
        return

    elif callback_data.startswith("eq_"):
        item_id = int(callback_data[3:])
        save_state(chat_id, f"eq_{item_id}")
        send_force_reply(chat_id, "✏️ *UPDATE QUANTITY*\n\nType the NEW total quantity for this item:", "e.g. 50")
        return

    elif callback_data.startswith("ecost_"):
        item_id = int(callback_data[6:])
        save_state(chat_id, f"ecost_{item_id}")
        send_force_reply(chat_id, "✏️ *UPDATE COST PRICE*\n\nType the NEW cost price per unit:", "e.g. 15.50")
        return

    elif callback_data.startswith("esell_"):
        item_id = int(callback_data[6:])
        save_state(chat_id, f"esell_{item_id}")
        send_force_reply(chat_id, "✏️ *UPDATE SELLING PRICE*\n\nType the NEW selling price per unit:", "e.g. 25.00")
        return

    elif callback_data.startswith("ecat_"):
        item_id = int(callback_data[5:])
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT DISTINCT category FROM stock ORDER BY category")
        categories = c.fetchall()
        conn.close()
        buttons = [[{"text": cat['category'], "callback_data": f"ecs_{item_id}_{cat['category'][:20]}"}] for cat in categories[:6]]
        buttons.append([{"text": "📝 Type Custom", "callback_data": f"ecc_{item_id}"}])
        buttons.append([{"text": "⬅️ Back", "callback_data": f"ei_{item_id}"}])
        text = "✏️ *UPDATE CATEGORY*\n\nSelect a category:"
        edit_message(chat_id, message_id, text, {"inline_keyboard": buttons})
        return

    elif callback_data.startswith("ecs_"):
        parts = callback_data.split("_", 2)
        item_id = int(parts[1])
        category = parts[2]
        conn = get_db()
        c = conn.cursor()
        c.execute("UPDATE stock SET category=%s WHERE id=%s", (category, item_id))
        conn.commit()
        conn.close()
        text = f"✅ *Category Updated!*\n\nNow in: *{category}*"
        markup = {"inline_keyboard": [[{"text": "✏️ Edit Another", "callback_data": "m_edit"}, {"text": "🏠 Main Menu", "callback_data": "m_menu"}]]}
        edit_message(chat_id, message_id, text, reply_markup=markup)
        return

    elif callback_data.startswith("ecc_"):
        item_id = int(callback_data[4:])
        save_state(chat_id, f"ecat_{item_id}")
        send_force_reply(chat_id, "✏️ *UPDATE CATEGORY*\n\nType the new category name:", "e.g. Accessories")
        return

    elif callback_data == "m_remove":
        if chat_id not in OWNER_IDS:
            text = "❌ Only the owner can remove items."
            markup = {"inline_keyboard": [[{"text": "🏠 Main Menu", "callback_data": "m_menu"}]]}
            edit_message(chat_id, message_id, text, reply_markup=markup)
            return
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT DISTINCT category FROM stock ORDER BY category")
        categories = c.fetchall()
        conn.close()
        buttons = [[{"text": cat['category'], "callback_data": f"rc_{cat['category'][:30]}"}] for cat in categories]
        buttons.append([{"text": "🏠 Main Menu", "callback_data": "m_menu"}])
        text = "🗑️ *REMOVE ITEM*\n\nSelect a category:"
        markup = {"inline_keyboard": buttons}
        edit_message(chat_id, message_id, text, reply_markup=markup)
        return

    elif callback_data.startswith("rc_"):
        category = callback_data[3:]
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM stock WHERE category=%s ORDER BY item_name", (category,))
        items = c.fetchall()
        conn.close()
        if not items:
            text = f"No items in *{category}*."
            markup = {"inline_keyboard": [[{"text": "⬅️ Back", "callback_data": "m_remove"}]]}
        else:
            buttons = []
            for item in items:
                color_str = f" ({item['color']})" if item['color'] else ""
                title = f"{item['item_name']}{color_str} [Qty: {item['quantity']}]"
                buttons.append([{"text": title, "callback_data": f"ri_{item['id']}"}])
            buttons.append([{"text": "⬅️ Back to Categories", "callback_data": "m_remove"}])
            text = f"🗑️ *REMOVE: {category}*\n\nSelect the item to remove:"
            markup = {"inline_keyboard": buttons}
        edit_message(chat_id, message_id, text, reply_markup=markup)
        return

    elif callback_data.startswith("ri_"):
        item_id = int(callback_data[3:])
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM stock WHERE id=%s", (item_id,))
        item = c.fetchone()
        conn.close()
        if not item:
            text = "Item not found."
            markup = {"inline_keyboard": [[{"text": "⬅️ Back", "callback_data": "m_remove"}]]}
        else:
            color_str = f" ({item['color']})" if item['color'] else ""
            text = f"🗑️ *{item['item_name']}*{color_str}\n\nQty: {item['quantity']}\n\nRemove entire item or reduce quantity?"
            markup = {"inline_keyboard": [
                [{"text": "🗑️ Remove All", "callback_data": f"ra_{item_id}"}, {"text": "📉 Reduce Qty", "callback_data": f"rr_{item_id}"}],
                [{"text": "⬅️ Back", "callback_data": f"rc_{item['category'][:30]}"}]
            ]}
        edit_message(chat_id, message_id, text, reply_markup=markup)
        return

    elif callback_data.startswith("ra_"):
        item_id = int(callback_data[3:])
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM stock WHERE id=%s", (item_id,))
        item = c.fetchone()
        conn.close()
        if item:
            color_str = f" ({item['color']})" if item['color'] else ""
            text = f"⚠️ *CONFIRM DELETION*\n\nAre you sure you want to permanently delete:\n*{item['item_name']}*{color_str}?\n\n_This cannot be undone._"
            markup = {"inline_keyboard": [
                [{"text": "✅ Yes, Delete", "callback_data": f"rd_{item_id}"}, {"text": "❌ No, Cancel", "callback_data": f"ri_{item_id}"}]
            ]}
            edit_message(chat_id, message_id, text, reply_markup=markup)
        return

    elif callback_data.startswith("rr_"):
        item_id = int(callback_data[3:])
        save_state(chat_id, f"rr_{item_id}")
        send_force_reply(chat_id, "📉 *REDUCE QUANTITY*\n\nHow many units to remove?", "e.g. 5")
        return

    elif callback_data.startswith("rd_"):
        item_id = int(callback_data[3:])
        conn = get_db()
        c = conn.cursor()
        c.execute("DELETE FROM stock WHERE id=%s", (item_id,))
        conn.commit()
        conn.close()
        text = "🗑️ *Item Deleted Successfully!*\n\n*What next?*"
        markup = {"inline_keyboard": [[{"text": "🗑️ Remove Another", "callback_data": "m_remove"}, {"text": "🏠 Main Menu", "callback_data": "m_menu"}]]}
        clear_state(chat_id)
        edit_message(chat_id, message_id, text, reply_markup=markup)
        return

    elif callback_data == "m_summary":
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) as count, SUM(profit) as total FROM sales WHERE DATE(sold_at)=CURRENT_DATE")
        result = c.fetchone()
        c.execute("SELECT COUNT(*) as count, SUM(profit) as total FROM sales WHERE DATE(sold_at)=CURRENT_DATE AND payment_status='pending'")
        pending_result = c.fetchone()
        conn.close()
        
        count = result['count'] or 0
        total = result['total'] or 0
        pend_count = pending_result['count'] or 0
        pend_total = pending_result['total'] or 0
        
        today = datetime.now().strftime("%d/%m/%Y")
        text = f"📊 *DAILY SUMMARY ({today})*\n\n🛒 Sales Today: {count}\n💰 Total Profit: GHS {total:.2f}\n⏳ Pending: GHS {pend_total:.2f} ({pend_count} customers)\n\n*What next?*"
        markup = {"inline_keyboard": [[{"text": "🏠 Main Menu", "callback_data": "m_menu"}]]}
        edit_message(chat_id, message_id, text, reply_markup=markup)
        return

    elif callback_data == "m_low":
        if chat_id not in OWNER_IDS:
            text = "❌ Only the owner can view low stock."
            markup = {"inline_keyboard": [[{"text": "🏠 Main Menu", "callback_data": "m_menu"}]]}
            edit_message(chat_id, message_id, text, reply_markup=markup)
            return
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM stock WHERE quantity <= low_stock_threshold ORDER BY quantity ASC")
        items = c.fetchall()
        conn.close()
        if items:
            text = "⚠️ *LOW STOCK ALERT*\n\n"
            for item in items:
                color_str = f" ({item['color']})" if item['color'] else ""
                text += f"• *{item['item_name']}*{color_str} — {item['quantity']} left\n"
        else:
            text = "✅ All items have sufficient stock."
        markup = {"inline_keyboard": [[{"text": "🏠 Main Menu", "callback_data": "m_menu"}]]}
        edit_message(chat_id, message_id, text, reply_markup=markup)
        return

    elif callback_data == "m_pending":
        if chat_id not in OWNER_IDS:
            text = "❌ Only the owner can view pending payments."
            markup = {"inline_keyboard": [[{"text": "🏠 Main Menu", "callback_data": "m_menu"}]]}
            edit_message(chat_id, message_id, text, reply_markup=markup)
            return
        
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM sales WHERE payment_status='pending' ORDER BY sold_at ASC")
        sales = c.fetchall()
        conn.close()
        
        if not sales:
            text = "✅ No pending payments."
            markup = {"inline_keyboard": [[{"text": "🏠 Main Menu", "callback_data": "m_menu"}]]}
        else:
            text = "⏳ *PENDING PAYMENTS*\n\n"
            buttons = []
            for sale in sales:
                color_str = f" ({sale['color']})" if sale['color'] else ""
                dt = sale['sold_at']
                hours = 0
                if dt:
                    try:
                        dt_obj = datetime.strptime(str(dt), "%Y-%m-%d %H:%M:%S")
                        diff = datetime.now() - dt_obj
                        hours = int(diff.total_seconds() // 3600)
                    except:
                        pass
                
                text += f"• *{sale['item_name']}*{color_str} x{sale['quantity']}\n  👤 {sale['customer_info']}\n  💰 GHS {sale['profit']:.2f} | 🕒 {hours}h ago\n"
                buttons.append([{"text": f"✅ Mark Paid: {sale['customer_info'][:20]}", "callback_data": f"mp_{sale['id']}"}])
            markup = {"inline_keyboard": buttons + [[{"text": "🏠 Main Menu", "callback_data": "m_menu"}]]}
            
        edit_message(chat_id, message_id, text, reply_markup=markup)
        return

    elif callback_data.startswith("mp_"):
        sale_id = int(callback_data[3:])
        conn = get_db()
        c = conn.cursor()
        c.execute("UPDATE sales SET payment_status='paid' WHERE id=%s", (sale_id,))
        conn.commit()
        
        c.execute("SELECT * FROM sales WHERE payment_status='pending' ORDER BY sold_at ASC")
        sales = c.fetchall()
        conn.close()
        
        if not sales:
            text = "✅ *Marked as Paid!*\n\nNo more pending payments."
            markup = {"inline_keyboard": [[{"text": "🏠 Main Menu", "callback_data": "m_menu"}]]}
        else:
            text = "✅ *Marked as Paid!*\n\n⏳ *PENDING PAYMENTS*\n\n"
            buttons = []
            for sale in sales:
                color_str = f" ({sale['color']})" if sale['color'] else ""
                dt = sale['sold_at']
                hours = 0
                if dt:
                    try:
                        dt_obj = datetime.strptime(str(dt), "%Y-%m-%d %H:%M:%S")
                        diff = datetime.now() - dt_obj
                        hours = int(diff.total_seconds() // 3600)
                    except:
                        pass
                
                text += f"• *{sale['item_name']}*{color_str} x{sale['quantity']}\n  👤 {sale['customer_info']}\n  💰 GHS {sale['profit']:.2f} | 🕒 {hours}h ago\n"
                buttons.append([{"text": f"✅ Mark Paid: {sale['customer_info'][:20]}", "callback_data": f"mp_{sale['id']}"}])
            markup = {"inline_keyboard": buttons + [[{"text": "🏠 Main Menu", "callback_data": "m_menu"}]]}
            
        edit_message(chat_id, message_id, text, reply_markup=markup)
        return

    else:
        text, markup = build_main_menu(chat_id)
        clear_state(chat_id)
        edit_message(chat_id, message_id, text, reply_markup=markup)

def process_sale_confirmation(chat_id, item_id, qty, customer_info, payment_status='paid', message_id=None):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM stock WHERE id=%s", (item_id,))
    item = c.fetchone()
    
    if not item or item['quantity'] < qty:
        text = "❌ Not enough stock."
        markup = {"inline_keyboard": [[{"text": "🏠 Main Menu", "callback_data": "m_menu"}]]}
        if message_id:
            edit_message(chat_id, message_id, text, reply_markup=markup)
        else:
            send_message(chat_id, text, reply_markup=markup)
        clear_state(chat_id)
        conn.close()
        return

    new_qty = item['quantity'] - qty
    profit = (item['selling_price'] - item['cost_price']) * qty
    
    c.execute("UPDATE stock SET quantity=%s WHERE id=%s", (new_qty, item_id))
    c.execute("INSERT INTO sales (item_name, color, quantity, profit, sold_by, customer_info, payment_status) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                 (item['item_name'], item['color'], qty, profit, chat_id, customer_info, payment_status))
    conn.commit()
    conn.close()

    color_str = f" ({item['color']})" if item['color'] else ""
    now = datetime.now().strftime("%d/%m/%Y %I:%M %p")
    
    status_str = "(Paid)" if payment_status == 'paid' else "(Credit — Pending)"
    text = f"✅ *Sale Recorded! {status_str}*\n\n🕒 {now}\n📦 Sold {qty}x *{item['item_name']}*{color_str}\n👤 Customer: *{customer_info}*\n📉 Remaining: {new_qty}\n💰 Profit: GHS {profit:.2f}\n\n*What next?*"
    
    markup = {"inline_keyboard": [[{"text": "💰 Record Another Sale", "callback_data": "m_sale"}, {"text": "🏠 Main Menu", "callback_data": "m_menu"}]]}
    
    if message_id:
        edit_message(chat_id, message_id, text, reply_markup=markup)
    else:
        send_message(chat_id, text, reply_markup=markup)

    status_text = "Paid" if payment_status == 'paid' else "Credit"
    notify_targets = NOTIFICATION_IDS if NOTIFICATION_IDS else OWNER_IDS
    for target_id in notify_targets:
        send_message(target_id, f"🔔 Sale: {item['item_name']}{color_str} x{qty} — GHS {profit:.2f} ({status_text} — {customer_info})")

    clear_state(chat_id)

# --- STATE MANAGEMENT ---
def save_state(chat_id, state, data_dict=None):
    conn = get_db()
    c = conn.cursor()
    data_json = json.dumps(data_dict) if data_dict else "{}"
    c.execute("INSERT INTO user_state (chat_id, state, data, updated_at) VALUES (%s, %s, %s, CURRENT_TIMESTAMP) ON CONFLICT (chat_id) DO UPDATE SET state=%s, data=%s, updated_at=CURRENT_TIMESTAMP",
              (chat_id, state, data_json, state, data_json))
    conn.commit()
    c.close()
    conn.close()

def get_state(chat_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT state, data FROM user_state WHERE chat_id=%s", (chat_id,))
    row = c.fetchone()
    conn.close()
    if row:
        try:
            return row['state'], json.loads(row['data'])
        except json.JSONDecodeError:
            return row['state'], {}
    return None, {}

def clear_state(chat_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("DELETE FROM user_state WHERE chat_id=%s", (chat_id,))
    conn.commit()
    c.close()
    conn.close()

# --- TEXT MESSAGE HANDLER ---
def handle_text_message(chat_id, text):
    text = text.strip()
    if text == "/start":
        if chat_id not in ALLOWED_IDS:
            send_message(chat_id, "⛔ Access Denied.")
            return
        text_msg, markup = build_main_menu(chat_id)
        send_message(chat_id, text_msg, reply_markup=markup)
        clear_state(chat_id)
        return

    state, data_dict = get_state(chat_id)
    if chat_id not in OWNER_IDS and not state:
        return

    if state and state.startswith("sq_"):
        item_id = int(state.split("_")[1])
        try:
            qty = int(text)
            if qty <= 0: raise ValueError
        except ValueError:
            send_message(chat_id, "❌ Please enter a valid positive number.")
            return
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM stock WHERE id=%s", (item_id,))
        item = c.fetchone()
        conn.close()
        if item and qty > item['quantity']:
            send_message(chat_id, f"❌ Not enough stock! Only {item['quantity']} available.")
            return
        markup = {"inline_keyboard": [
            [{"text": "🚶 Walk-in Customer", "callback_data": f"sw_{item_id}_{qty}"}],
            [{"text": "✍️ Enter Name & Number", "callback_data": f"st_{item_id}_{qty}"}],
            [{"text": "❌ Cancel", "callback_data": "m_menu"}]
        ]}
        send_message(chat_id, f"✅ Quantity: *{qty}*\n\nWho is buying this?\n\n_Tap an option below._", reply_markup=markup)
        return

    elif state and state.startswith("st_"):
        parts = state.split("_")
        item_id = int(parts[1])
        qty = int(parts[2])
        customer_info = text if text.lower() != "walk-in" else "Walk-in Customer"
        
        data_dict = {'customer_info': customer_info}
        save_state(chat_id, f"spay_{item_id}_{qty}", data_dict)
        
        markup = {"inline_keyboard": [
            [{"text": "💵 Paid Now", "callback_data": f"sp_{item_id}_{qty}"}],
            [{"text": "⏳ Pay Later", "callback_data": f"scred_{item_id}_{qty}"}],
            [{"text": "❌ Cancel", "callback_data": "m_menu"}]
        ]}
        send_message(chat_id, f"✅ Customer: *{customer_info}*\n\nHow will they pay?", reply_markup=markup)
        return

    elif state == "at_qty":
        try:
            qty = int(text)
            if qty <= 0: raise ValueError
        except ValueError:
            send_message(chat_id, "❌ Please enter a valid positive number.")
            return
        new_qty = data_dict['existing_qty'] + qty
        conn = get_db()
        c = conn.cursor()
        c.execute("UPDATE stock SET quantity=%s WHERE id=%s", (new_qty, data_dict['existing_id']))
        conn.commit()
        conn.close()
        color_str = f" ({data_dict['color']})" if data_dict['color'] else ""
        text_msg = f"✅ *Updated!*\n\n{data_dict['name']}{color_str} now {new_qty} pcs.\nPrices unchanged.\n\n*What next?*"
        markup = {"inline_keyboard": [[{"text": "➕ Add More Stock", "callback_data": "m_add"}, {"text": "🏠 Main Menu", "callback_data": "m_menu"}]]}
        clear_state(chat_id)
        send_message(chat_id, text_msg, reply_markup=markup)
        return

    elif state == "at_cost":
        try:
            cost = float(text)
            if cost < 0: raise ValueError
        except ValueError:
            send_message(chat_id, "❌ Please enter a valid number.")
            return
        data_dict['new_cost'] = cost
        save_state(chat_id, "at_sell", data_dict)
        send_message(chat_id, f"✅ Cost: *GHS {cost:.2f}*\n\nNew selling price per unit?",
                    reply_markup={"inline_keyboard": [[{"text": "❌ Cancel", "callback_data": "m_menu"}]]})
        return

    elif state == "at_sell":
        try:
            sell = float(text)
            if sell < 0: raise ValueError
        except ValueError:
            send_message(chat_id, "❌ Please enter a valid number.")
            return
        data_dict['new_sell'] = sell
        save_state(chat_id, "at_qty2", data_dict)
        send_message(chat_id, f"✅ Sell: *GHS {sell:.2f}*\n\nQuantity to add?",
                    reply_markup={"inline_keyboard": [[{"text": "❌ Cancel", "callback_data": "m_menu"}]]})
        return

    elif state == "at_qty2":
        try:
            qty = int(text)
            if qty <= 0: raise ValueError
        except ValueError:
            send_message(chat_id, "❌ Please enter a valid positive number.")
            return
        new_qty = data_dict['existing_qty'] + qty
        conn = get_db()
        c = conn.cursor()
        c.execute("UPDATE stock SET quantity=%s, cost_price=%s, selling_price=%s WHERE id=%s",
                    (new_qty, data_dict['new_cost'], data_dict['new_sell'], data_dict['existing_id']))
        conn.commit()
        conn.close()
        color_str = f" ({data_dict['color']})" if data_dict['color'] else ""
        text_msg = f"✅ *Updated!*\n\n{data_dict['name']}{color_str}\n{new_qty} pcs\nCost: GHS {data_dict['new_cost']:.2f}\nSell: GHS {data_dict['new_sell']:.2f}\n\n*What next?*"
        markup = {"inline_keyboard": [[{"text": "➕ Add More Stock", "callback_data": "m_add"}, {"text": "🏠 Main Menu", "callback_data": "m_menu"}]]}
        clear_state(chat_id)
        send_message(chat_id, text_msg, reply_markup=markup)
        return

    elif state == "an_name":
        data_dict['name'] = text
        save_state(chat_id, "an_color_btn", data_dict)
        markup = {"inline_keyboard": get_color_buttons() + [[{"text": "⚪ None", "callback_data": "c_none"}, {"text": "❌ Cancel", "callback_data": "m_menu"}]]}
        send_message(chat_id, f"✅ Item: *{text}*\n\nSelect color (or tap 'None' if no color):", reply_markup=markup)
        return

    elif state == "an_color_text":
        data_dict['color'] = text
        save_state(chat_id, "an_qty", data_dict)
        text = f"✅ Color: *{text}*\n\nHow many units are you adding?\n\n_Tap below to type the amount._"
        markup = {"inline_keyboard": [[{"text": "❌ Cancel", "callback_data": "m_menu"}]]}
        send_message(chat_id, text, reply_markup=markup)
        send_force_reply(chat_id, "👇 *Type the quantity now:*", "e.g. 15")
        return

    elif state == "an_qty":
        try:
            qty = int(text)
            if qty <= 0: raise ValueError
        except ValueError:
            send_message(chat_id, "❌ Please enter a positive number.")
            return
        data_dict['qty'] = qty
        save_state(chat_id, "an_cost", data_dict)
        send_message(chat_id, f"✅ Quantity: *{qty}*\n\nWhat is the cost price per unit?",
                    reply_markup={"inline_keyboard": [[{"text": "❌ Cancel", "callback_data": "m_menu"}]]})
        return

    elif state == "an_cost":
        try:
            cost = float(text)
            if cost < 0: raise ValueError
        except ValueError:
            send_message(chat_id, "❌ Please enter a valid number.")
            return
        data_dict['cost'] = cost
        save_state(chat_id, "an_sell", data_dict)
        send_message(chat_id, f"✅ Cost: *GHS {cost:.2f}*\n\nWhat is the selling price per unit?",
                    reply_markup={"inline_keyboard": [[{"text": "❌ Cancel", "callback_data": "m_menu"}]]})
        return

    elif state == "an_sell":
        try:
            sell = float(text)
            if sell < 0: raise ValueError
        except ValueError:
            send_message(chat_id, "❌ Please enter a valid number.")
            return
        data_dict['sell'] = sell
        save_state(chat_id, "an_cat", data_dict)
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT DISTINCT category FROM stock ORDER BY category")
        categories = c.fetchall()
        conn.close()
        buttons = []
        for cat in categories[:5]:
            buttons.append([{"text": cat['category'], "callback_data": f"ac_{cat['category'][:30]}"}])
        buttons.append([{"text": "📝 Type Custom Category", "callback_data": "ac_custom"}])
        buttons.append([{"text": "❌ Cancel", "callback_data": "m_menu"}])
        send_message(chat_id, f"✅ Sell: *GHS {sell:.2f}*\n\nSelect a category:", reply_markup={"inline_keyboard": buttons})
        return

    elif state == "an_cat_text":
        data_dict['category'] = text
        save_state(chat_id, "an_confirm", data_dict)
        color_str = f" ({data_dict['color']})" if data_dict['color'] else ""
        text_msg = f"➕ *CONFIRM NEW ITEM*\n\nName: *{data_dict['name']}*{color_str}\nQuantity: {data_dict['qty']}\nCost: GHS {data_dict['cost']:.2f}\nSell: GHS {data_dict['sell']:.2f}\nCategory: {text}\n\nAdd this item?"
        markup = {"inline_keyboard": [[{"text": "✅ Confirm", "callback_data": "an_ok"}, {"text": "❌ Cancel", "callback_data": "m_menu"}]]}
        send_message(chat_id, text_msg, reply_markup=markup)
        return

    elif state and state.startswith("eq_"):
        item_id = int(state.split("_")[1])
        try:
            qty = int(text)
            if qty < 0: raise ValueError
        except ValueError:
            send_message(chat_id, "❌ Please enter a valid positive number.")
            return
        conn = get_db()
        c = conn.cursor()
        c.execute("UPDATE stock SET quantity=%s WHERE id=%s", (qty, item_id))
        conn.commit()
        c.execute("SELECT * FROM stock WHERE id=%s", (item_id,))
        item = c.fetchone()
        conn.close()
        color_str = f" ({item['color']})" if item['color'] else ""
        text_msg = f"✅ *Quantity Updated!*\n\n*{item['item_name']}*{color_str} is now {qty}.\n\n*What next?*"
        markup = {"inline_keyboard": [[{"text": "✏️ Edit Another", "callback_data": "m_edit"}, {"text": "🏠 Main Menu", "callback_data": "m_menu"}]]}
        clear_state(chat_id)
        send_message(chat_id, text_msg, reply_markup=markup)
        return

    elif state and state.startswith("ecost_"):
        item_id = int(state.split("_")[1])
        try:
            cost = float(text)
            if cost < 0: raise ValueError
        except ValueError:
            send_message(chat_id, "❌ Please enter a valid number.")
            return
        conn = get_db()
        c = conn.cursor()
        c.execute("UPDATE stock SET cost_price=%s WHERE id=%s", (cost, item_id))
        conn.commit()
        c.execute("SELECT * FROM stock WHERE id=%s", (item_id,))
        item = c.fetchone()
        conn.close()
        color_str = f" ({item['color']})" if item['color'] else ""
        text_msg = f"✅ *Cost Price Updated!*\n\n*{item['item_name']}*{color_str} cost is now GHS {cost:.2f}.\n\n*What next?*"
        markup = {"inline_keyboard": [[{"text": "✏️ Edit Another", "callback_data": "m_edit"}, {"text": "🏠 Main Menu", "callback_data": "m_menu"}]]}
        clear_state(chat_id)
        send_message(chat_id, text_msg, reply_markup=markup)
        return

    elif state and state.startswith("esell_"):
        item_id = int(state.split("_")[1])
        try:
            sell = float(text)
            if sell < 0: raise ValueError
        except ValueError:
            send_message(chat_id, "❌ Please enter a valid number.")
            return
        conn = get_db()
        c = conn.cursor()
        c.execute("UPDATE stock SET selling_price=%s WHERE id=%s", (sell, item_id))
        conn.commit()
        c.execute("SELECT * FROM stock WHERE id=%s", (item_id,))
        item = c.fetchone()
        conn.close()
        color_str = f" ({item['color']})" if item['color'] else ""
        text_msg = f"✅ *Selling Price Updated!*\n\n*{item['item_name']}*{color_str} sell price is now GHS {sell:.2f}.\n\n*What next?*"
        markup = {"inline_keyboard": [[{"text": "✏️ Edit Another", "callback_data": "m_edit"}, {"text": "🏠 Main Menu", "callback_data": "m_menu"}]]}
        clear_state(chat_id)
        send_message(chat_id, text_msg, reply_markup=markup)
        return

    elif state and state.startswith("ecat_"):
        item_id = int(state.split("_")[1])
        conn = get_db()
        c = conn.cursor()
        c.execute("UPDATE stock SET category=%s WHERE id=%s", (text, item_id))
        conn.commit()
        conn.close()
        text_msg = f"✅ *Category Updated!*\n\nNow in: *{text}*\n\n*What next?*"
        markup = {"inline_keyboard": [[{"text": "✏️ Edit Another", "callback_data": "m_edit"}, {"text": "🏠 Main Menu", "callback_data": "m_menu"}]]}
        clear_state(chat_id)
        send_message(chat_id, text_msg, reply_markup=markup)
        return

    elif state and state.startswith("rr_"):
        item_id = int(state.split("_")[1])
        try:
            qty = int(text)
            if qty <= 0: raise ValueError
        except ValueError:
            send_message(chat_id, "❌ Please enter a valid positive number.")
            return
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT * FROM stock WHERE id=%s", (item_id,))
        item = c.fetchone()
        if item:
            new_qty = item['quantity'] - qty
            if new_qty < 0:
                send_message(chat_id, f"❌ Cannot remove {qty}. Only {item['quantity']} in stock.")
                clear_state(chat_id)
                conn.close()
                return
            if new_qty == 0:
                c.execute("DELETE FROM stock WHERE id=%s", (item_id,))
                conn.commit()
                conn.close()
                color_str = f" ({item['color']})" if item['color'] else ""
                text_msg = f"🗑️ *Removed!*\n\n*{item['item_name']}*{color_str} deleted completely.\n\n*What next?*"
            else:
                c.execute("UPDATE stock SET quantity=%s WHERE id=%s", (new_qty, item_id))
                conn.commit()
                conn.close()
                color_str = f" ({item['color']})" if item['color'] else ""
                text_msg = f"✅ *Quantity Reduced!*\n\n*{item['item_name']}*{color_str}: {item['quantity']} → {new_qty}\n\n*What next?*"
        else:
            text_msg = "❌ Item not found."
            conn.close()
        markup = {"inline_keyboard": [[{"text": "🗑️ Remove Another", "callback_data": "m_remove"}, {"text": "🏠 Main Menu", "callback_data": "m_menu"}]]}
        clear_state(chat_id)
        send_message(chat_id, text_msg, reply_markup=markup)
        return

    if chat_id in ALLOWED_IDS:
        text_msg, markup = build_main_menu(chat_id)
        send_message(chat_id, "🤔 I didn't catch that. Here is the main menu:", reply_markup=markup)
        clear_state(chat_id)
    else:
        send_message(chat_id, "⛔ Access Denied.")

# --- FLASK APP ---
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", secrets.token_hex(32))

@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    if WEBHOOK_SECRET:
        secret_header = request.headers.get('X-Telegram-Bot-Api-Secret-Token')
        if secret_header != WEBHOOK_SECRET:
            logger.warning(f"Unauthorized webhook attempt from {request.remote_addr}")
            return jsonify({"error": "Unauthorized"}), 403
    
    update = request.get_json()
    try:
        if 'message' in update:
            message = update['message']
            chat_id = message['chat']['id']
            if chat_id not in ALLOWED_IDS:
                if 'text' in message and message['text'].strip() == "/start":
                    send_message(chat_id, "⛔ Access Denied.")
                    return jsonify({"ok": True})
            if 'text' in message:
                handle_text_message(chat_id, message['text'])
        elif 'callback_query' in update:
            callback = update['callback_query']
            chat_id = callback['message']['chat']['id']
            if chat_id not in ALLOWED_IDS:
                return jsonify({"ok": True})
            button_handler(callback)
    except Exception as e:
        logger.error(f"Processing Error: {e}", exc_info=True)
    return jsonify({"ok": True})

@app.route('/setup', methods=['GET'])
def setup_webhook():
    if not WEBHOOK_URL:
        return "Error: WEBHOOK_URL environment variable not set."
    url = f"{API_URL}/setWebhook"
    data = {"url": WEBHOOK_URL, "secret_token": WEBHOOK_SECRET} if WEBHOOK_SECRET else {"url": WEBHOOK_URL}
    response = requests.post(url, json=data)
    return response.text

@app.route('/', methods=['GET'])
def index():
    return "Victory Venture StockMind Bot is running!"

# --- WEB DASHBOARD ROUTES ---

def login_required(f):
    """Decorator to protect routes. If no session, kick to login."""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id, password_hash FROM users WHERE username=%s", (username,))
        user = c.fetchone()
        conn.close()
        
        # Security: check_password_hash prevents timing attacks and verifies the hash
        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = username
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="Invalid username or password")
            
    return render_template('login.html', error=None)

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    c = conn.cursor()
    
    # Fetch summary stats
    c.execute("SELECT COUNT(*) as total_items, SUM(quantity) as total_stock FROM stock")
    stock_stats = c.fetchone()
    
    c.execute("SELECT COUNT(*) as total_sales, COALESCE(SUM(profit), 0) as total_profit FROM sales")
    sales_stats = c.fetchone()
    
    # Fetch recent sales
    c.execute("SELECT item_name, quantity, profit, customer_info, sold_at FROM sales ORDER BY sold_at DESC LIMIT 5")
    recent_sales = c.fetchall()
    
    conn.close()
    
    return render_template('dashboard.html', 
                           stock_stats=stock_stats, 
                           sales_stats=sales_stats, 
                           recent_sales=recent_sales,
                           username=session.get('username'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))
if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
