import json
import telebot
from telebot import types
from telebot.apihelper import ApiTelegramException
import time
import threading
import math
import random
import os
import re
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from flask import Flask, request, jsonify, abort # <-- ওয়েব সার্ভার
import logging

# --- লগিং সেটআপ ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ===== কনফিগারেশন (Render.com থেকে লোড হবে) =====
TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID"))
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME")
# Render.com এই URL টি নিজে সেট করবে
RENDER_APP_URL = os.environ.get("RENDER_EXTERNAL_URL") 
# আপনার GitHub লিঙ্ক (মিনি অ্যাপের ঠিকানা)
MINI_APP_URL = "https://faiazshawn-boop.github.io/my-service-app/" 

# ===== নতুন: ওয়েব সার্ভার অ্যাপ =====
app = Flask(__name__)
bot = telebot.TeleBot(TOKEN)

# ===== গুগল শীট কনফিগারেশন =====
try:
    # Render.com-এ এই ফাইলটি আমরা "Secret File" হিসেবে আপলোড করবো
    creds_file_path = os.environ.get("GOOGLE_CREDENTIALS_PATH", "credentials.json")
    
    # Render-এ JSON স্ট্রিং হিসেবে লোড করা ভালো
    if creds_file_path == "credentials.json" and not os.path.exists(creds_file_path):
        # যদি ফাইল না থাকে, Environment Variable থেকে JSON স্ট্রিং লোড করার চেষ্টা
        creds_json_string = os.environ.get("GOOGLE_CREDENTIALS_JSON")
        if creds_json_string:
            creds_dict = json.loads(creds_json_string)
            scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/drive']
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            logger.info("JSON স্ট্রিং থেকে Creds লোড হয়েছে।")
        else:
            raise FileNotFoundError("credentials.json ফাইল পাওয়া যায়নি এবং GOOGLE_CREDENTIALS_JSON সেট করা নেই।")
    else:
        # ফাইল থেকে লোড করা (লোকাল টেস্টিং-এর জন্য)
        scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_file_path, scope)
        logger.info("ফাইল থেকে Creds লোড হয়েছে।")

    client = gspread.authorize(creds)
    
    SHEET_NAME = "My Bot Sheet" # <-- আপনার গুগল শীটের নাম
    sheet = client.open(SHEET_NAME)
    
    users_sheet = sheet.worksheet("users")
    orders_sheet = sheet.worksheet("orders")
    products_config_sheet = sheet.worksheet("products_config")
    previous_products_sheet = sheet.worksheet("previous_products")
    transactions_sheet = sheet.worksheet("transactions")
    pinned_messages_sheet = sheet.worksheet("pinned_messages")
    logger.info("Google Sheet সফলভাবে কানেক্ট হয়েছে।")

except Exception as e:
    logger.error(f"!!! Google Sheet কানেক্ট করতে ব্যর্থ: {e} !!!")


# ===== ইন-মেমোরি ডেটা (বাকি কোড আপনার আগের মতোই) =====
balances = {}
orders = {}
user_pinned_messages = {}
whatsapp_numbers = {}
products_config = {}
previous_products_config = {}
base_products = {
    "SERVER_COPY": {"name": "সার্ভার কপি", "price": 80, "enabled": True, "delivery": "১০ মিনিট", "fields": [{"label": "NID নাম্বার", "type": "text", "example": "10/13/17 সংখ্যা"}, {"label": "জন্ম তারিখ", "type": "text", "example": "DD-MM-YYYY"}]},
    "ID_CARD": {"name": "আইডি কার্ড", "price": 160, "enabled": True, "delivery": "২০ মিনিট", "sub_options": {"nid": {"name": "এনআইডি নাম্বার", "fields": [{"label": "নাম (বাংলায়)", "type": "text"}, {"label": "NID নাম্বার", "type": "text"}, {"label": "জন্ম তারিখ", "type": "text"}]}, "voter_slip": {"name": "ভোটার স্লিপ নাম্বার", "fields": [{"label": "নাম (বাংলায়)", "type": "text"}, {"label": "ভোটার স্লিপ নাম্বার", "type": "text"}, {"label": "জন্ম তারিখ", "type": "text"}]}}},
    "SMART_CARD": {"name": "স্মার্ট কার্ড", "price": 350, "enabled": True, "delivery": "২০ মিনিট", "sub_options": {"nid": {"name": "এনআইডি নাম্বার", "fields": [{"label": "নাম (বাংলায়)", "type": "text"}, {"label": "NID নাম্বার", "type": "text"}, {"label": "জন্ম তারিখ", "type": "text"}]}, "voter_slip": {"name": "ভোটার স্লিপ নাম্বার", "fields": [{"label": "নাম (বাংলায়)", "type": "text"}, {"label": "ভোটার স্লিপ নাম্বার", "type": "text"}, {"label": "জন্ম তারিখ", "type": "text"}]}}},
    "BIOMETRIC": {"name": "বায়োমেট্রিক", "price": 650, "enabled": True, "delivery": "৩০ মিনিট", "sub_options": {"bl": {"name": "বাংলালিংক", "fields": [{"label": "বাংলালিংক নাম্বার", "type": "text"}]}, "gp": {"name": "গ্রামীন", "fields": [{"label": "গ্রামীন নাম্বার", "type": "text"}]}, "robi": {"name": "রবি", "fields": [{"label": "রবি নাম্বার", "type": "text"}]}, "airtel": {"name": "এয়ারটেল", "fields": [{"label": "এয়ারটেল নাম্বার", "type": "text"}]}, "teletalk": {"name": "টেলিটক", "fields": [{"label": "টেলিটক নাম্বার", "type": "text"}]}}},
    "LOCATION": {"name": "লোকেশ", "price": 850, "enabled": True, "delivery": "৩০ মিনিট", "sub_options": {"bl": {"name": "বাংলালিংক", "fields": [{"label": "বাংলালিংক নাম্বার", "type": "text"}]}, "gp": {"name": "গ্রামীন", "fields": [{"label": "গ্রামীন নাম্বার", "type": "text"}]}, "robi": {"name": "রবি", "fields": [{"label": "রবি নাম্বার", "type": "text"}]}, "airtel": {"name": "এয়ারটেল", "fields": [{"label": "এয়ারটেল নাম্বার", "type": "text"}]}, "teletalk": {"name": "টেলিটক", "fields": [{"label": "টেলিটক নাম্বার", "type": "text"}]}}},
    "CALL_LIST": {"name": "কল লিস্ট", "price": 1900, "enabled": True, "delivery": "২৪/৪৮ ঘন্টা", "sub_options": {"bl": {"name": "বাংলালিংক", "fields": [{"label": "বাংলালিংক নাম্বার", "type": "text"}]}, "gp": {"name": "গ্রামীন", "fields": [{"label": "গ্রামীন নাম্বার", "type": "text"}]}, "robi": {"name": "রবি", "fields": [{"label": "রবি নাম্বার", "type": "text"}]}, "airtel": {"name": "এয়ারটেল", "fields": [{"label": "এয়ারটেল নাম্বার", "type": "text"}]}, "teletalk": {"name": "টেলিটক", "fields": [{"label": "টেলিটক নাম্বার", "type": "text"}]}}},
    "ID_TO_NUMBER": {"name": "আইডি টু নাম্বার", "price": 900, "enabled": True, "delivery": "২০ মিনিট", "fields": [{"label": "NID নাম্বার", "type": "text"}, {"label": "জন্ম সাল", "type": "text", "example": "YYYY"}]},
    "TIN_CERTIFICATE": {"name": "টিন সার্টিফিকেট", "price": 200, "enabled": True, "delivery": "১০ মিনিট", "sub_options": {"nid": {"name": "NID NO", "fields": [{"label": "NID NO", "type": "text"}]}, "tin": {"name": "TIN NO", "fields": [{"label": "TIN NO", "type": "text"}]}, "mobile": {"name": "MOBILE NO", "fields": [{"label": "MOBILE NO", "type": "text"}]}, "old_tin": {"name": "OLD TIN NO", "fields": [{"label": "OLD TIN NO", "type": "text"}]}, "passport": {"name": "PASSPORT NO", "fields": [{"label": "PASSPORT NO", "type": "text"}]}}},
    "BKASH_INFO": {"name": "বিকাশ ইনফর্মেশন", "price": 2500, "enabled": True, "delivery": "অফিস টাইম", "fields": [{"label": "বিকাশ নাম্বার", "type": "text"}]},
    "NAGAD_INFO": {"name": "নগদ ইনফর্মেশন", "price": 1500, "enabled": True, "delivery": "অফিস টাইম", "fields": [{"label": "নগদ নাম্বার", "type": "text"}]},
    "LOST_ID_CARD": {"name": "হারানো আইডি কার্ড", "price": 1600, "enabled": True, "delivery": "অফিস টাইম", "fields": [{"label": "নাম", "type": "text"}, {"label": "পিতার নাম", "type": "text"}, {"label": "মাতার নাম", "type": "text"}, {"label": "বিভাগ", "type": "text"}, {"label": "জেলা", "type": "text"}, {"label": "উপজেলা", "type": "text"}, {"label": "ইউনিয়ন", "type": "text"}, {"label": "ওয়ার্ড নাম্বার", "type": "text"}, {"label": "গ্রাম", "type": "text"}, {"label": "জন্ম নিবন্ধন (যদি থাকে)", "type": "text"}, {"label": "ব্যক্তির ছবি", "type": "photo"}]},
    "NEW_BIRTH_CERTIFICATE": {"name": "নতুন জন্ম নিবন্ধন", "price": 2400, "enabled": True, "delivery": "৪৮ ঘন্টা", "fields": [{"label": "নাম (বাংলায়)", "type": "text"}, {"label": "Name (ENGLISH)", "type": "text"}, {"label": "জন্ম তারিখ", "type": "text", "example": "DD-MM-YYYY"}, {"label": "পিতার নাম (বাংলায়)", "type": "text"}, {"label": "Father's Name (ENGLISH)", "type": "text"}, {"label": "মাতার নাম (বাংলায়)", "type": "text"}, {"label": "Mother's Name (ENGLISH)", "type": "text"}, {"label": "কততম সন্তান", "type": "text"}, {"label": "জন্মস্থান", "type": "text"}, {"label": "বিভাগ", "type": "text"}, {"label": "জেলা", "type": "text"}, {"label": "উপজেলা", "type": "text"}, {"label": "ইউনিয়ন", "type": "text"}, {"label": "গ্রাম", "type": "text"}, {"label": "ওয়ার্ড নাম্বার", "type": "text"}, {"label": "পোস্ট অফিস", "type": "text"}, {"label": "পিতার আইডি কার্ডের ছবি", "type": "photo"}, {"label": "পিতার জন্ম নিবন্ধন (যদি থাকে)", "type": "photo"}, {"label": "মাতার আইডি কার্ডের ছবি", "type": "photo"}, {"label": "মাতার জন্ম নিবন্ধন (যদি থাকে)", "type": "photo"}]},
    "MRP_PASSPORT": {"name": "MRP পাসপোর্ট SB", "price": 1400, "enabled": True, "delivery": "অফিস টাইম", "sub_options": {"nid": {"name": "NID NO", "fields": [{"label": "NID NO", "type": "text"}, {"label": "জন্ম তারিখ", "type": "text"}]}, "passport": {"name": "PASSPORT NO", "fields": [{"label": "PASSPORT NO", "type": "text"}, {"label": "জন্ম তারিখ", "type": "text"}]}, "birth": {"name": "BIRTH NO", "fields": [{"label": "BIRTH NO", "type": "text"}, {"label": "জন্ম তারিখ", "type": "text"}]}}},
    "E_PASSPORT": {"name": "ই-পাসপোর্ট SB", "price": 1400, "enabled": True, "delivery": "অফিস টাইম", "sub_options": {"nid": {"name": "NID NO", "fields": [{"label": "NID NO", "type": "text"}, {"label": "জন্ম তারিখ", "type": "text"}]}, "passport": {"name": "PASSPORT NO", "fields": [{"label": "PASSPORT NO", "type": "text"}, {"label": "জন্ম তারিখ", "type": "text"}]}, "birth": {"name": "BIRTH NO", "fields": [{"label": "BIRTH NO", "type": "text"}, {"label": "জন্ম তারিখ", "type": "text"}]}}}
}
products = base_products # ডিফল্ট

ORDER_DISPLAY_CONFIG = {
    "SERVER_COPY": {"name": "Server_Copy", "time": "10 Minutes"},
    "ID_CARD": {"name": "NID_PDF", "time": "15 Minutes"},
    "SMART_CARD": {"name": "Smart_PDF", "time": "25 Minutes"},
    # ... (বাকিগুলো আপনার পুরানো কোড থেকে কপি করুন) ...
}

# ===== গুগল শীট হেল্পার ফাংশন (আপনার পুরানো কোড থেকে) =====
def gs_load_all_data():
    global balances, orders, user_pinned_messages, whatsapp_numbers, products_config, previous_products_config, products
    logger.info("Google Sheet থেকে ডেটা লোড করা হচ্ছে...")
    try:
        # (এখানে আপনার পুরানো gs_load_all_data ফাংশনের সব কোড থাকবে)
        # 1. users (balances, whatsapp) লোড
        users_data = users_sheet.get_all_records()
        balances.clear()
        whatsapp_numbers.clear()
        for user in users_data:
            uid = str(user.get('user_id', ''))
            if not uid: continue 
            balances[uid] = float(user.get('balance', 0))
            if user.get('whatsapp'):
                whatsapp_numbers[uid] = str(user.get('whatsapp'))
        
        # 2. orders লোড
        orders_data = orders_sheet.get_all_records()
        orders.clear()
        for order in orders_data:
            order_id = str(order.get('order_id', '')) 
            if not order_id: continue
            try:
                order_data_dict = json.loads(order.get('data', '{}'))
            except json.JSONDecodeError:
                order_data_dict = {}
            
            orders[order_id] = {
                "uid": str(order.get('uid')),"status": order.get('status'),"order_id": order_id,"short_id": order.get('short_id'),
                "price": float(order.get('price', 0)),
                "progress_msg_id": int(order.get('progress_msg_id', 0)) if order.get('progress_msg_id') else None,
                "admin_notification_msg_id": int(order.get('admin_notification_msg_id', 0)) if order.get('admin_notification_msg_id') else None,
                "product": order.get('product'),"sub_option": order.get('sub_option') or None,"data": order_data_dict,"message_ids": [] 
            }

        # 3. products_config লোড
        config_data = products_config_sheet.get_all_records()
        products_config.clear()
        for item in config_data:
            key = str(item.get('key', ''))
            if not key: continue
            products_config[key] = {"price": float(item.get('price')),"enabled": bool(item.get('enabled') == 'TRUE' or item.get('enabled') == True)}
        
        # 4. previous_products লোড
        prev_config_data = previous_products_sheet.get_all_records()
        previous_products_config.clear()
        for item in prev_config_data:
            key = str(item.get('key', ''))
            if not key: continue
            previous_products_config[key] = {"price": float(item.get('price')),"enabled": bool(item.get('enabled') == 'TRUE' or item.get('enabled') == True)}

        # 5. pinned_messages লোড
        pinned_data = pinned_messages_sheet.get_all_records()
        user_pinned_messages.clear()
        for item in pinned_data:
            if item.get('user_id'):
                user_pinned_messages[str(item['user_id'])] = int(item.get('msg_id'))
            
        # 6. transactions লোড
        transactions_data = transactions_sheet.get_all_records()
        for tr in transactions_data:
            tr_id = str(tr.get('transaction_id', ''))
            if not tr_id: continue
            orders[tr_id] = {
                "type": tr.get('type'),"uid": str(tr.get('uid')),"amount": float(tr.get('amount', 0)),
                "timestamp": int(tr.get('timestamp', 0)),"product_name": tr.get('product_name'),"short_id": tr.get('short_id')
            }
        logger.info("...ডেটা লোড সম্পন্ন।")
        
        # products ডিকশনারি আপডেট করা
        for key, config in products_config.items():
            if key in base_products:
                base_products[key]['price'] = config.get('price', base_products[key]['price'])
                base_products[key]['enabled'] = config.get('enabled', base_products[key].get('enabled', True))
        products = base_products
        
        if not config_data:
            logger.warning("'products_config' শীটটি খালি। বেস প্রোডাক্ট দিয়ে পূরণ করা হচ্ছে...")
            gs_init_products_config()
        if not prev_config_data:
            logger.warning("'previous_products' শীটটি খালি। বর্তমান প্রোডাক্ট দিয়ে পূরণ করা হচ্ছে...")
            if not products_config:
                 temp_config = {k: {'price': p['price'], 'enabled': p.get('enabled', True)} for k, p in base_products.items()}
                 gs_update_previous_products(temp_config)
            else:
                 gs_update_previous_products(products_config)
    except Exception as e:
        logger.error(f"!!! Google Sheet থেকে ডেটা লোড করতে মারাত্মক ব্যর্থতা: {e} !!!")

# (gs_update_user_data, gs_add_order, gs_update_order, gs_add_transaction, ইত্যাদি সব হেল্পার ফাংশন এখানে পেস্ট করুন)
def gs_update_user_data(user_id_str, balance=None, whatsapp=None, pinned_msg_id=None):
    try:
        cell = None
        try:
            cell = users_sheet.find(user_id_str, in_column=1) # user_id কলাম (1)
        except gspread.exceptions.CellNotFound: pass
        if cell:
            row_index = cell.row
            if balance is not None: users_sheet.update_cell(row_index, 2, balance) 
            if whatsapp is not None: users_sheet.update_cell(row_index, 3, whatsapp)
        else:
            new_row = [user_id_str, 0, None]
            if balance is not None: new_row[1] = balance
            if whatsapp is not None: new_row[2] = whatsapp
            users_sheet.append_row(new_row)
    except Exception as e:
        logger.error(f"GS আপডেট (ইউজার) সমস্যা: {e}"); client.login()

    if pinned_msg_id is not None:
        try:
            cell = None
            try: cell = pinned_messages_sheet.find(user_id_str, in_column=1)
            except gspread.exceptions.CellNotFound: pass
            if cell: pinned_messages_sheet.update_cell(cell.row, 2, pinned_msg_id)
            else: pinned_messages_sheet.append_row([user_id_str, pinned_msg_id])
        except Exception as e: logger.error(f"GS আপডেট (পিন) সমস্যা: {e}")
def gs_add_order(order_id, order_data):
    try:
        data_json = json.dumps(order_data.get('data', {}))
        new_row = [order_data.get('order_id'),order_data.get('uid'),order_data.get('status'),order_data.get('short_id'),order_data.get('price'),
            order_data.get('progress_msg_id'),order_data.get('admin_notification_msg_id'),order_data.get('product'),order_data.get('sub_option'),data_json]
        orders_sheet.append_row(new_row)
    except Exception as e: logger.error(f"GS অ্যাড (অর্ডার) সমস্যা: {e}"); client.login()
def gs_update_order(order_id, status=None, progress_msg_id=None, admin_msg_id=None):
    try:
        cell = orders_sheet.find(order_id, in_column=1)
        row_index = cell.row
        if status: orders_sheet.update_cell(row_index, 3, status)
        if progress_msg_id: orders_sheet.update_cell(row_index, 6, progress_msg_id)
        if admin_msg_id: orders_sheet.update_cell(row_index, 7, admin_msg_id)
    except Exception as e: logger.error(f"GS আপডেট (অর্ডার) সমস্যা: {e}"); client.login()
def gs_add_transaction(tr_id, tr_data):
    try:
        new_row = [tr_id,tr_data.get('type'),tr_data.get('uid'),tr_data.get('amount'),tr_data.get('timestamp'),tr_data.get('product_name'),tr_data.get('short_id')]
        transactions_sheet.append_row(new_row)
    except Exception as e: logger.error(f"GS অ্যাড (ট্রানজেকশন) সমস্যা: {e}"); client.login()
def gs_update_product_config(product_key, price=None, enabled=None):
    try:
        cell = products_config_sheet.find(product_key, in_column=1)
        row_index = cell.row
        if price is not None: products_config_sheet.update_cell(row_index, 2, price)
        if enabled is not None: products_config_sheet.update_cell(row_index, 3, enabled)
    except Exception as e: logger.error(f"GS আপডেট (প্রোডাক্ট) সমস্যা: {e}"); client.login()
def gs_init_products_config():
    try:
        rows = [["key", "price", "enabled"]]
        for k, p in base_products.items(): rows.append([k, p['price'], p.get('enabled', True)])
        if len(rows) > 1: products_config_sheet.append_rows(rows)
    except Exception as e: logger.error(f"GS init (প্রোডাক্ট) সমস্যা: {e}"); client.login()
def gs_update_previous_products(current_config_dict):
    try:
        previous_products_sheet.clear()
        rows = [["key", "price", "enabled"]]
        for key, config in current_config_dict.items(): rows.append([key, config['price'], config.get('enabled', True)])
        if len(rows) > 1: previous_products_sheet.append_rows(rows)
    except Exception as e: logger.error(f"GS আপডেট (Previous Products) সমস্যা: {e}"); client.login()
def escape_markdown_v1(text):
    escape_chars = r'_*`['
    return re.sub(r'([%s])' % re.escape(escape_chars), r'\\\1', text)
def update_pinned_balance(user_id):
    user_id_str = str(user_id)
    if user_id_str in user_pinned_messages:
        try:
            msg_id = user_pinned_messages[user_id_str]; balance = balances.get(user_id_str, 0)
            text = f"💳 *আপনার বর্তমান ব্যালেন্স:* {balance} টাকা"
            bot.edit_message_text(text, user_id_str, msg_id, parse_mode="Markdown")
        except ApiTelegramException: pass
def get_user_order_count(user_id):
     return len([o for o in orders.values() if o.get("uid") == str(user_id) and o.get("status") and not o.get("order_id", "").endswith("_deduct") and o.get("type") != "balance_add"])
def get_user_status_emoji(user_id):
    count = get_user_order_count(user_id);
    if count >= 25: return "🤝"
    elif count >= 10: return "⭐"
    elif count >= 3: return "🥉"
    else: return ""

# ===== নতুন: ওয়েব সার্ভার রুট (API) =====

# রুট ১: মিনি অ্যাপের জন্য ডেটা পাঠানো (ব্যালেন্স, অর্ডার)
@app.route('/get_init_data', methods=['POST'])
def get_init_data():
    try:
        # (এখানে একটি জটিল টেলিগ্রাম ভেরিফিকেশন কোড থাকা উচিত)
        # আপাতত সহজ রাখছি
        user_data = request.json.get('user', {})
        user_id = user_data.get('id')
        if not user_id:
            logger.warning("Auth check failed for get_init_data")
            abort(401) # Unauthorized
        
        user_id_str = str(user_id)
        logger.info(f"/get_init_data called by user: {user_id_str}")

        # গুগল শীট থেকে রিয়েল ডেটা লোড (বা মেমোরি থেকে)
        balance = balances.get(user_id_str, 0)
        
        # ইউজারের অর্ডারগুলো ফিল্টার করা
        user_orders_list = []
        for order_id, order in orders.items():
            if order.get('uid') == user_id_str and order.get('type') is None: # শুধু আসল অর্ডার
                product_key = order.get('product')
                product = products.get(product_key)
                if not product: continue
                display_config = ORDER_DISPLAY_CONFIG.get(product_key, {"name": product.get("name", "N/A"), "time": product.get("delivery", "N/A")})
                
                delivery_type = "text" # ডিফল্ট
                if product_key in ["ID_CARD", "SMART_CARD", "NEW_BIRTH_CERTIFICATE"]:
                    delivery_type = "pdf"

                user_orders_list.append({
                    "id": order.get('short_id', order_id),
                    "type": product.get('name'),
                    "info_data": order.get('data', {}),
                    "delivery_type": delivery_type,
                    "status": order.get('status', 'N/A'),
                    "rate": f"{order.get('price', 0)}tk",
                    "time": display_config.get('time', 'N/A')
                })
        
        user_orders_list.reverse() 
        notifications = [{"id": 1, "text": "আপনার মিনি অ্যাপে স্বাগতম!", "time": "এখন"}]

        return jsonify({
            "balance": f"৳ {balance:.2f}",
            "orders": user_orders_list,
            "notifications": notifications,
            "products": base_products
        })
    except Exception as e:
        logger.error(f"get_init_data error: {e}")
        return jsonify({"error": str(e)}), 500

# রুট ২: মিনি অ্যাপ থেকে নতুন অর্ডার রিসিভ করা
@app.route('/submit_order', methods=['POST'])
def submit_order():
    try:
        data = request.json
        user_data = data.get('user', {})
        user_id = user_data.get('id')
        if not user_id:
            logger.warning("Auth check failed for submit_order")
            abort(401)

        user_id_str = str(user_id)
        service_key = data.get('service_key')
        sub_option_key = data.get('sub_option_key')
        form_data = data.get('form_data') 
        
        logger.info(f"নতুন অর্ডার রিসিভড: {user_id_str} | {service_key}")

        product = products.get(service_key)
        if not product:
            return jsonify({"status": "error", "message": "সার্ভিসটি পাওয়া যায়নি।"}), 400
        
        # সাব অপশন থাকলে দাম পরিবর্তন
        price = product.get('price', 0)
        product_name = product.get('name')
        if sub_option_key and "sub_options" in product:
            sub_option_data = product["sub_options"].get(sub_option_key)
            if sub_option_data:
                # যদি সাব-অপশনের আলাদা দাম থাকে (ভবিষ্যতের জন্য)
                # price = sub_option_data.get('price', price) 
                product_name += f" ({sub_option_data.get('name')})"

        current_balance = float(balances.get(user_id_str, 0))
        if current_balance < price:
            return jsonify({"status": "error", "message": "দুঃখিত, আপনার পর্যাপ্ত ব্যালেন্স নেই।"}), 400
            
        new_balance = current_balance - price
        balances[user_id_str] = new_balance
        gs_update_user_data(user_id_str, balance=new_balance)
        
        full_order_id = f"{user_id_str}_{int(time.time())}"
        short_order_id = str(random.randint(1000, 9999))
        
        order_data = {
            "uid": user_id_str, "status": "Pending", "order_id": full_order_id, "short_id": short_order_id, "price": price,
            "product": service_key, "sub_option": sub_option_key, "data": form_data,
            "progress_msg_id": None, "admin_notification_msg_id": None
        }
        
        orders[full_order_id] = order_data
        gs_add_order(full_order_id, order_data)
        
        transaction_id = f"deduct_{full_order_id}"
        tr_data = {"type": "order_deduct", "uid": user_id_str, "amount": price, "product_name": product_name, "short_id": short_order_id, "timestamp": int(time.time())}
        orders[transaction_id] = tr_data
        gs_add_transaction(transaction_id, tr_data)
        
        try:
            user_name = user_data.get('first_name', 'N/A')
            user_wa_number = whatsapp_numbers.get(user_id_str, "N/A")
            
            order_text = f"✅ *নতুন মিনি অ্যাপ অর্ডার!* `#{short_order_id}`\n\n"
            order_text += f"👤 *ইউজার:* {user_name} (`{user_id_str}`)\n"
            order_text += f"📱 *WhatsApp:* `{user_wa_number}`\n"
            order_text += f"🛒 *প্রোডাক্ট:* {product_name}\n"
            order_text += f"💰 *দাম:* {price} টাকা\n\n📋 *তথ্য:*\n"
            
            for label, value in form_data.items():
                if isinstance(value, str) and value.startswith("FILE_ID:"):
                    order_text += f"{label}: (ফাইল আপলোড হয়েছে)\n"
                    # বটকে দিয়ে ফাইল পাঠানো
                    bot.send_document(ADMIN_ID, value.split("FILE_ID:")[1], caption=f"ফাইল: {label}")
                else:
                    order_text += f"{label}: `{value}`\n"
                
            markup = types.InlineKeyboardMarkup(row_width=3)
            markup.add(types.InlineKeyboardButton("🔵 Processing", callback_data=f"update_progress:processing:{full_order_id}"))
            markup.row(types.InlineKeyboardButton("✍️ রিপ্লাই (ফাইল)", callback_data=f"reply_{full_order_id}"), types.InlineKeyboardButton("✅ Success (স্ট্যাটাস)", callback_data=f"success_{full_order_id}"))
            markup.row(types.InlineKeyboardButton("🚫 ক্যানসেল", callback_data=f"cancel_{full_order_id}"), types.InlineKeyboardButton("🚯 নট ফাউন্ড", callback_data=f"notfound_{full_order_id}"))

            admin_msg = bot.send_message(ADMIN_ID, order_text, reply_markup=markup, parse_mode="Markdown")
            
            orders[full_order_id]['admin_notification_msg_id'] = admin_msg.message_id
            gs_update_order(full_order_id, admin_msg_id=admin_msg.message_id)

        except Exception as e:
            logger.error(f"অ্যাডমিনকে নোটিফিকেশন পাঠাতে ব্যর্থ: {e}")

        # ইউজারকে চ্যাটে কনফার্মেশন পাঠানো (আপনার টেবিল ডিজাইন এখানে আসবে)
        try:
            # (এখানে আপনার টেবিল স্ট্যাটাস মেসেজটি পাঠানো হবে)
            bot.send_message(user_id_str, f"✅ আপনার '{product_name}' অর্ডারটি সফলভাবে রিসিভ হয়েছে।\nস্ট্যাটাস: 🟡 Pending\nঅর্ডার আইডি: `#{short_order_id}`", parse_mode="Markdown")
        except Exception as e:
            logger.error(f"ইউজারকে মেসেজ পাঠাতে সমস্যা: {e}")

        return jsonify({"status": "success", "message": "অর্ডার সফল হয়েছে!"})
    except Exception as e:
        logger.error(f"submit_order error: {e}")
        return jsonify({"error": str(e)}), 500

# ===== টেলিগ্রাম বট হ্যান্ডলার (পরিবর্তিত) =====

# রুট ৩: বটকে সেট করা (Render.com এটি ব্যবহার করবে)
@app.route('/' + TOKEN, methods=['POST'])
def get_message():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "!", 200
    else:
        abort(403)

# রুট ৪: ওয়েব অ্যাপের URL সেট করা (শুধু প্রথমবার চালানোর জন্য)
@app.route('/')
def set_webhook():
    bot.remove_webhook()
    time.sleep(0.1)
    # RENDER_APP_URL এনভায়রনমেন্ট ভেরিয়েবল থেকে নেওয়া
    webhook_url = RENDER_APP_URL + '/' + TOKEN
    bot.set_webhook(url=webhook_url)
    logger.info(f"Webhook set to {webhook_url}")
    return f"Webhook set to {webhook_url}", 200

@bot.message_handler(commands=["start"])
def start(message):
    uid = str(message.chat.id)
    
    # মিনি অ্যাপের মেনু বাটন সেট করা
    menu_button = types.WebAppInfo(MINI_APP_URL) # <-- আপনার GitHub লিঙ্ক
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add(types.KeyboardButton("🛒 সার্ভিস মেনু 🚀", web_app=menu_button))
    
    if message.chat.id == ADMIN_ID:
        markup.add(types.KeyboardButton("/admin"))

    bot.send_message(uid, "স্বাগতম! সার্ভিস অর্ডার করতে নিচের 'সার্ভিস মেনু' বাটনটি চাপুন:", reply_markup=markup)

    if uid not in balances:
        balances[uid] = 0
        whatsapp_numbers[uid] = "N/A"
        gs_update_user_data(uid, balance=0, whatsapp="N/A")

# (আপনার পুরানো /admin এবং সব কলব্যাক হ্যান্ডলার (order success/cancel) 
# এখানে হুবহু পেস্ট করতে হবে, কারণ অ্যাডমিন বটটি আগের মতোই চালাবে)
# ... (admin_panel, handle_admin_final_actions, ইত্যাদি) ...
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.chat.id != ADMIN_ID: return
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ ব্যালেন্স যোগ", callback_data="admin_add_balance"),
        types.InlineKeyboardButton("📢 ব্রডকাস্ট", callback_data="admin_broadcast"),
        types.InlineKeyboardButton("🔍 ইউজার খুঁজুন", callback_data="admin_find_user"),
        types.InlineKeyboardButton("⏳ পেন্ডিং অর্ডার", callback_data="admin_pending_orders"),
        types.InlineKeyboardButton("👥 সকল ইউজার", callback_data="admin_show_all_users"),
        types.InlineKeyboardButton("⚙️ প্রোডাক্ট ম্যানেজমেন্ট", callback_data="admin_manage_products")
    )
    bot.send_message(ADMIN_ID, "👑 *অ্যাডমিন ড্যাশবোর্ড*", reply_markup=markup, parse_mode="Markdown")

# (বাকি সব অ্যাডমিন ফাংশন এখানে পেস্ট করুন...)
# ... (handle_admin_panel_callback, admin_ask_for_amount, admin_process_balance_add, ইত্যাদি) ...
# ... (handle_admin_final_actions, admin_send_reply, ইত্যাদি) ...


# ===== বট এবং সার্ভার চালু করা =====
# Render.com এই ফাইলটি চালালে, Gunicorn `app` ভেরিয়েবলটি খুঁজবে।
# আমাদের বট পোলিং-ও চালু করতে হবে।
def run_bot_polling():
    logger.info("বট ডেটা লোড করা হচ্ছে...")
    try:
        gs_load_all_data() # প্রথমে ডেটা লোড
        # check_product_updates_and_broadcast() # ব্রডকাস্ট (ঐচ্ছিক)
    except Exception as e:
        logger.error(f"gs_load_all_data চালু করতে ব্যর্থ: {e}")
        
    logger.info("বট পোলিং থ্রেড চালু হচ্ছে...")
    bot.remove_webhook()
    bot.infinity_polling(skip_pending=True)

if __name__ != "__main__":
    # এই অংশটি Gunicorn (Render.com) দ্বারা চালিত হবে
    logger.info("Gunicorn সার্ভার হিসেবে চালু হচ্ছে...")
    # Render.com থেকে webhook সেট করার জন্য / URL-এ হিট করতে হবে
    # বট পোলিং আলাদা থ্রেডে চালু করা
    threading.Thread(target=run_bot_polling, daemon=True).start()
    
# যদি লোকালভাবে চালানো হয় (if __name__ == "__main__"):
# (Render.com এটি ব্যবহার করবে না, কিন্তু লোকাল টেস্টিং-এর জন্য রাখা যেতে পারে)
if __name__ == "__main__":
    logger.info("লোকাল মেশিনে Flask + Polling দিয়ে চলছে...")
    threading.Thread(target=run_bot_polling, daemon=True).start()
    app.run(debug=True, port=int(os.environ.get('PORT', 5001)))
