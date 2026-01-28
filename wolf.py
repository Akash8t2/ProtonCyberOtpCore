#!/usr/bin/env python3
import requests
import time
import re
import logging
import json
import os
from datetime import datetime
from urllib.parse import urlencode
import html

# ================= CONFIG =================

AJAX_URL = "http://213.32.24.208/ints/client/res/data_smscdr.php"

# Bot Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN") or "YOUR_BOT_TOKEN"
CHAT_IDS = ["-1003559187782", "-1003316982194"]  # Dual chat support

# Cookies - Update with current session
COOKIES = {
    "PHPSESSID": os.getenv("PHPSESSID") or "PUT_SESSION_HERE"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "http://213.32.24.208/ints/client/smscdr.php",
    "Connection": "keep-alive"
}

CHECK_INTERVAL = 10  # seconds
STATE_FILE = "state.json"

# Button URLs (from environment variables with defaults)
DEVELOPER_URL = "https://t.me/botcasx"  # Fixed - Dev button
NUMBERS_URL_1 = os.getenv("NUMBERS_URL_1", "https://t.me/CyberOTPCore")  # Button 1
NUMBERS_URL_2 = os.getenv("NUMBERS_URL_2", "https://t.me/example2")      # Button 2
SUPPORT_URL_1 = os.getenv("SUPPORT_URL_1", "https://t.me/example3")      # Button 4
SUPPORT_URL_2 = os.getenv("SUPPORT_URL_2", "https://t.me/example4")      # Button 5

# =========================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.StreamHandler()]
)

session = requests.Session()
session.headers.update(HEADERS)
session.cookies.update(COOKIES)

# ================= STATE =================

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error loading state: {e}")
    return {"last_uid": None, "processed_ids": []}

def save_state(state):
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logging.error(f"Error saving state: {e}")

STATE = load_state()

# ================= HELPERS =================

def extract_otp(text):
    """Extract OTP from SMS text"""
    if not text:
        return "N/A"
    
    # Telegram codes
    telegram_match = re.search(r'Telegram code\s+(\d{4,8})', text)
    if telegram_match:
        return telegram_match.group(1)
    
    # General patterns
    patterns = [
        r'\b(\d{4,8})\b',
        r'code[\s:]+(\d{4,8})',
        r'OTP[\s:]+(\d{4,8})',
        r'verification[\s:]+(\d{4,8})',
        r'密码[\s:]+(\d{4,8})',
        r'코드[\s:]+(\d{4,8})',
        r'код[\s:]+(\d{4,8})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return "N/A"

def clean_phone_number(number):
    """Clean and format phone number"""
    if not number:
        return "N/A"
    
    cleaned = re.sub(r'\D', '', number)
    if len(cleaned) >= 10:
        return f"+{cleaned}"
    return number

def build_payload():
    """Build AJAX payload"""
    today = datetime.now().strftime("%Y-%m-%d")
    timestamp = int(time.time() * 1000)
    
    params = {
        "fdate1": f"{today} 00:00:00",
        "fdate2": f"{today} 23:59:59",
        "frange": "",
        "fnum": "",
        "fcli": "",
        "fgdate": "",
        "fgmonth": "",
        "fgrange": "",
        "fgnumber": "",
        "fgcli": "",
        "fg": 0,
        "sEcho": 1,
        "iColumns": 7,
        "sColumns": ",,,,,,",
        "iDisplayStart": 0,
        "iDisplayLength": 25,
        "mDataProp_0": 0,
        "sSearch_0": "",
        "bRegex_0": "false",
        "bSearchable_0": "true",
        "bSortable_0": "true",
        "mDataProp_1": 1,
        "sSearch_1": "",
        "bRegex_1": "false",
        "bSearchable_1": "true",
        "bSortable_1": "true",
        "mDataProp_2": 2,
        "sSearch_2": "",
        "bRegex_2": "false",
        "bSearchable_2": "true",
        "bSortable_2": "true",
        "mDataProp_3": 3,
        "sSearch_3": "",
        "bRegex_3": "false",
        "bSearchable_3": "true",
        "bSortable_3": "true",
        "mDataProp_4": 4,
        "sSearch_4": "",
        "bRegex_4": "false",
        "bSearchable_4": "true",
        "bSortable_4": "true",
        "mDataProp_5": 5,
        "sSearch_5": "",
        "bRegex_5": "false",
        "bSearchable_5": "true",
        "bSortable_5": "true",
        "mDataProp_6": 6,
        "sSearch_6": "",
        "bRegex_6": "false",
        "bSearchable_6": "true",
        "bSortable_6": "true",
        "sSearch": "",
        "bRegex": "false",
        "iSortCol_0": 0,
        "sSortDir_0": "desc",
        "iSortingCols": 1,
        "_": timestamp
    }
    
    return params

def format_message(row):
    """Format SMS data into HTML Telegram message"""
    try:
        date = row[0] if len(row) > 0 else "N/A"
        route = row[1] if len(row) > 1 else "Unknown"
        number = clean_phone_number(row[2]) if len(row) > 2 else "N/A"
        service = row[3] if len(row) > 3 else "Unknown"
        message = row[4] if len(row) > 4 else ""
        
        # Extract country
        country = "Unknown"
        if route and isinstance(route, str):
            country = route.split()[0] if route.split() else "Unknown"
        
        # Extract OTP
        otp = extract_otp(message)
        
        # Escape HTML special characters
        safe_number = html.escape(str(number))
        safe_otp = html.escape(str(otp))
        safe_service = html.escape(str(service))
        safe_country = html.escape(str(country))
        safe_date = html.escape(str(date))
        safe_message = html.escape(str(message))
        
        # Replace newlines with HTML line breaks for message
        safe_message = safe_message.replace('\n', '<br>')
        
        # Format message as HTML
        formatted = (
            "💎 <b>PREMIUM OTP ALERT</b> 💎\n"
            "<i>Instant • Secure • Verified</i>\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            f"📞 <b>Number</b> <code>{safe_number}</code>\n"
            f"🔐 <b>OTP CODE</b> 🔥 <code>{safe_otp}</code> 🔥\n"
            f"🏷 <b>Service</b> <b>{safe_service}</b>\n"
            f"🌍 <b>Country</b> <b>{safe_country}</b>\n"
            f"🕒 <b>Received At</b> <code>{safe_date}</code>\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            f"💬 <b>Message Content</b>\n"
            f"<i>{safe_message}</i>\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "⚡ <b>POWERED BY @Rasel424282</b>"
        )
        
        return formatted
    except Exception as e:
        logging.error(f"Error formatting message: {e}")
        return None

def send_telegram(text, chat_id):
    """Send message to specific Telegram chat"""
    if not text:
        return
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    # Create inline keyboard with 5 buttons
    reply_markup = {
        "inline_keyboard": [
            # First row: 3 buttons
            [
                {"text": "🧑‍💻 Dev", "url": DEVELOPER_URL},
                {"text": "📱 Numbers 1", "url": NUMBERS_URL_1},
                {"text": "📱 Numbers 2", "url": NUMBERS_URL_2}
            ],
            # Second row: 2 buttons
            [
                {"text": "🆘 Support 1", "url": SUPPORT_URL_1},
                {"text": "🆘 Support 2", "url": SUPPORT_URL_2}
            ]
        ]
    }
    
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",  # Using HTML formatting
        "disable_web_page_preview": True,
        "reply_markup": reply_markup
    }
    
    try:
        response = requests.post(url, json=payload, timeout=15)
        if response.status_code == 200:
            logging.info(f"Message sent to chat {chat_id}")
            return True
        else:
            logging.error(f"Telegram API error for chat {chat_id}: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logging.error(f"Error sending to Telegram (chat {chat_id}): {e}")
        return False

# ================= CORE LOGIC =================

def fetch_latest_sms():
    """Fetch latest SMS from website"""
    global STATE
    
    try:
        params = build_payload()
        
        logging.debug(f"Fetching data with params: {params}")
        response = session.get(AJAX_URL, params=params, timeout=30)
        
        if response.status_code != 200:
            logging.error(f"HTTP Error: {response.status_code}")
            return
        
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            logging.error(f"JSON decode error: {e}")
            logging.debug(f"Raw response: {response.text[:500]}")
            return
        
        rows = data.get("aaData", [])
        if not rows:
            logging.debug("No data found in response")
            return
        
        # Filter valid rows
        valid_rows = []
        for row in rows:
            if not isinstance(row, list) or len(row) < 5:
                continue
            
            # Skip summary rows
            if isinstance(row[0], str) and row[0].startswith("0,0,0,"):
                continue
            
            # Check for valid date format
            if not row[0] or not re.match(r'\d{4}-\d{2}-\d{2}', str(row[0])):
                continue
            
            valid_rows.append(row)
        
        if not valid_rows:
            logging.debug("No valid SMS rows found")
            return
        
        # Sort by date (newest first)
        valid_rows.sort(
            key=lambda x: datetime.strptime(x[0], "%Y-%m-%d %H:%M:%S"),
            reverse=True
        )
        
        # Process newest row
        newest = valid_rows[0]
        
        # Create unique ID
        sms_id = f"{newest[0]}_{newest[2]}_{hash(newest[4][:100])}" if len(newest) > 4 else f"{newest[0]}_{newest[2]}"
        
        # Check if already processed
        if STATE["last_uid"] == sms_id or sms_id in STATE.get("processed_ids", []):
            return
        
        # Format message
        formatted_msg = format_message(newest)
        if not formatted_msg:
            return
        
        # Send to all chat IDs
        success_count = 0
        for chat_id in CHAT_IDS:
            if send_telegram(formatted_msg, chat_id):
                success_count += 1
        
        if success_count > 0:
            logging.info(f"New OTP sent to {success_count} chats for number: {newest[2]}")
            
            # Update state
            STATE["last_uid"] = sms_id
            
            # Keep track of processed IDs
            processed_ids = STATE.get("processed_ids", [])
            processed_ids.append(sms_id)
            if len(processed_ids) > 200:  # Increased limit
                processed_ids = processed_ids[-200:]
            STATE["processed_ids"] = processed_ids
            
            save_state(STATE)
        
    except requests.RequestException as e:
        logging.error(f"Network error: {e}")
    except Exception as e:
        logging.error(f"Unexpected error in fetch: {e}")
        import traceback
        traceback.print_exc()

# ================= MAIN =================

def main():
    """Main function"""
    logging.info("=" * 50)
    logging.info("🚀 PREMIUM OTP BOT STARTED")
    logging.info("=" * 50)
    logging.info(f"Website: {AJAX_URL}")
    logging.info(f"Chat IDs: {', '.join(CHAT_IDS)}")
    logging.info(f"Check interval: {CHECK_INTERVAL} seconds")
    logging.info(f"Developer: {DEVELOPER_URL}")
    logging.info(f"Numbers 1: {NUMBERS_URL_1}")
    logging.info(f"Numbers 2: {NUMBERS_URL_2}")
    logging.info(f"Support 1: {SUPPORT_URL_1}")
    logging.info(f"Support 2: {SUPPORT_URL_2}")
    logging.info("=" * 50)
    
    # Test environment variables
    env_vars = ["NUMBERS_URL_2", "SUPPORT_URL_1", "SUPPORT_URL_2"]
    for var in env_vars:
        value = os.getenv(var)
        if value:
            logging.info(f"{var}: {value}")
        else:
            logging.warning(f"{var} not set, using default")
    
    # Main loop
    while True:
        try:
            fetch_latest_sms()
        except KeyboardInterrupt:
            logging.info("Bot stopped by user")
            break
        except Exception as e:
            logging.error(f"Critical error in main loop: {e}")
            time.sleep(30)  # Longer sleep on critical error
        
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
