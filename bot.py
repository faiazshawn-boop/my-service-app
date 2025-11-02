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
RENDER_APP_URL = os.environ.get("RENDER_EXTERNAL_URL") 
MINI_APP_URL = "https://faiazshawn-boop.github.io/my-service-app/" # আপনার GitHub লিঙ্ক

# ===== নতুন: ওয়েব সার্ভার অ্যাপ =====
app = Flask(__name__)
bot = telebot.TeleBot(TOKEN, threaded=False) # Webhook-এর জন্য threaded=False

# ===== গুগল শীট কনফিগারেশন =====
try:
    creds_json_string = os.environ.get("GOOGLE_CREDENTIALS_JSON")
    if creds_json_string:
        creds_dict = json.loads(creds_json_string)
        scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        logger.info("JSON স্ট্রিং থেকে Creds লোড হয়েছে।")
    else:
        raise ValueError("GOOGLE_CREDENTIALS_JSON এনভায়রনমেন্ট ভেরিয়েবল সেট করা নেই।")

    client = gspread.authorize(creds)
    SHEET_NAME = "My Bot Sheet"
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


# ===== ইন-মেমোরি ডেটা =====
balances = {}
orders = {}
user_pinned_messages = {}
whatsapp_numbers = {}
products_config = {}
previous_products_config = {}

# ===== পণ্যের তালিকা (আপনার কোড থেকে) =====
base_products = {
    "SERVER_COPY": {
        "name": "সার্ভার কপি", "price": 80, "enabled": True, "delivery": "১০ মিনিট",
        "fields": [
            {"label": "NID নাম্বার", "type": "text", "example": "10/13/17 সংখ্যা"},
            {"label": "জন্ম তারিখ", "type": "text", "example": "DD-MM-YYYY"}
        ]
    },
    "ID_CARD": {
        "name": "আইডি কার্ড", "price": 160, "enabled": True, "delivery": "২০ মিনিট",
        "sub_options": {
            "nid": {"name": "এনআইডি নাম্বার", "fields": [
                {"label": "নাম (বাংলায়)", "type": "text"},
                {"label": "NID নাম্বার", "type": "text"},
                {"label": "জন্ম তারিখ", "type": "text"}
            ]},
            "voter_slip": {"name": "ভোটার স্লিপ নাম্বার", "fields": [
                {"label": "নাম (বাংলায়)", "type": "text"},
                {"label": "ভোটার স্লিপ নাম্বার", "type": "text"},
                {"label": "জন্ম তারিখ", "type": "text"}
            ]}
        }
    },
    "SMART_CARD": {
        "name": "স্মার্ট কার্ড", "price": 350, "enabled": True, "delivery": "২০ মিনিট",
        "sub_options": {
             "nid": {"name": "এনআইডি নাম্বার", "fields": [
                {"label": "নাম (বাংলায়)", "type": "text"},
                {"label": "NID নাম্বার", "type": "text"},
                {"label": "জন্ম তারিখ", "type": "text"}
            ]},
            "voter_slip": {"name": "ভোটার স্লিপ নাম্বার", "fields": [
                {"label": "নাম (বাংলায়)", "type": "text"},
                {"label": "ভোটার স্লিপ নাম্বার", "type": "text"},
                {"label": "জন্ম তারিখ", "type": "text"}
            ]}
        }
    },
     "BIOMETRIC": {
        "name": "বায়োমেট্রিক", "price": 650, "enabled": True, "delivery": "৩০ মিনিট",
        "sub_options": {
            "bl": {"name": "বাংলালিংক", "fields": [{"label": "বাংলালিংক নাম্বার", "type": "text"}]},
            "gp": {"name": "গ্রামীন", "fields": [{"label": "গ্রামীন নাম্বার", "type": "text"}]},
            "robi": {"name": "রবি", "fields": [{"label": "রবি নাম্বার", "type": "text"}]},
            "airtel": {"name": "এয়ারটেল", "fields": [{"label": "এয়ারটেল নাম্বার", "type": "text"}]},
            "teletalk": {"name": "টেলিটক", "fields": [{"label": "টেলিটক নাম্বার", "type": "text"}]}
        }
    },
    "LOCATION": {
        "name": "লোকেশ", "price": 850, "enabled": True, "delivery": "৩০ মিনিট",
        "sub_options": {
             "bl": {"name": "বাংলালিংক", "fields": [{"label": "বাংলালিংক নাম্বার", "type": "text"}]},
            "gp": {"name": "গ্রামীন", "fields": [{"label": "গ্রামীন নাম্বার", "type": "text"}]},
            "robi": {"name": "রবি", "fields": [{"label": "রবি নাম্বার", "type": "text"}]},
            "airtel": {"name": "এয়ারটেল", "fields": [{"label": "এয়ারটেল নাম্বার", "type": "text"}]},
            "teletalk": {"name": "টেলিটক", "fields": [{"label": "টেলিটক নাম্বার", "type": "text"}]}
        }
    },
    "CALL_LIST": {
        "name": "কল লিস্ট", "price": 1900, "enabled": True, "delivery": "২৪/৪৮ ঘন্টা",
        "sub_options": {
             "bl": {"name": "বাংলালিংক", "fields": [{"label": "বাংলালিংক নাম্বার", "type": "text"}]},
            "gp": {"name": "গ্রামীন", "fields": [{"label": "গ্রামীন নাম্বার", "type": "text"}]},
            "robi": {"name": "রবি", "fields": [{"label": "রবি নাম্বার", "type": "text"}]},
            "airtel": {"name": "এয়ারটেল", "fields": [{"label": "এয়ারটেল নাম্বার", "type": "text"}]},
            "teletalk": {"name": "টেলিটক", "fields": [{"label": "টেলিটক নাম্বার", "type": "text"}]}
        }
    },
    "ID_TO_NUMBER": {
        "name": "আইডি টু নাম্বার", "price": 900, "enabled": True, "delivery": "২০ মিনিট",
        "fields": [
             {"label": "NID নাম্বার", "type": "text"},
             {"label": "জন্ম সাল", "type": "text", "example": "YYYY"}
        ]
    },
    "TIN_CERTIFICATE": {
        "name": "টিন সার্টিফিকেট", "price": 200, "enabled": True, "delivery": "১০ মিনিট",
        "sub_options": {
            "nid": {"name": "NID NO", "fields": [{"label": "NID NO", "type": "text"}]},
            "tin": {"name": "TIN NO", "fields": [{"label": "TIN NO", "type": "text"}]},
            "mobile": {"name": "MOBILE NO", "fields": [{"label": "MOBILE NO", "type": "text"}]},
            "old_tin": {"name": "OLD TIN NO", "fields": [{"label": "OLD TIN NO", "type": "text"}]},
            "passport": {"name": "PASSPORT NO", "fields": [{"label": "PASSPORT NO", "type": "text"}]}
        }
    },
    "BKASH_INFO": { "name": "বিকাশ ইনফর্মেশন", "price": 2500, "enabled": True, "delivery": "অফিস টাইম", "fields": [{"label": "বিকাশ নাম্বার", "type": "text"}]},
    "NAGAD_INFO": { "name": "নগদ ইনফর্মেশন", "price": 1500, "enabled": True, "delivery": "অফিস টাইম", "fields": [{"label": "নগদ নাম্বার", "type": "text"}]},
    "LOST_ID_CARD": {
        "name": "হারানো আইডি কার্ড", "price": 1600, "enabled": True, "delivery": "অফিস টাইম", 
        "fields": [ 
            {"label": "নাম", "type": "text"}, {"label": "পিতার নাম", "type": "text"}, {"label": "মাতার নাম", "type": "text"}, 
            {"label": "বিভাগ", "type": "text"}, {"label": "জেলা", "type": "text"}, {"label": "উপজেলা", "type": "text"}, 
            {"label": "ইউনিয়ন", "type": "text"}, {"label": "ওয়ার্ড নাম্বার", "type": "text"}, {"label": "গ্রাম", "type": "text"}, 
            {"label": "জন্ম নিবন্ধন (যদি থাকে)", "type": "text"}, {"label": "ব্যক্তির ছবি", "type": "photo"} 
        ]
    },
    "NEW_BIRTH_CERTIFICATE": {
        "name": "নতুন জন্ম নিবন্ধন", "price": 2400, "enabled": True, "delivery": "৪৮ ঘন্টা", 
        "fields": [ 
            {"label": "নাম (বাংলায়)", "type": "text"}, {"label": "Name (ENGLISH)", "type": "text"}, {"label": "জন্ম তারিখ", "type": "text", "example": "DD-MM-YYYY"}, 
            {"label": "পিতার নাম (বাংলায়)", "type": "text"}, {"label": "Father's Name (ENGLISH)", "type": "text"}, {"label": "মাতার নাম (বাংলায়)", "type": "text"}, 
            {"label": "Mother's Name (ENGLISH)", "type": "text"}, {"label": "কততম সন্তান", "type": "text"}, {"label": "জন্মস্থান", "type": "text"}, 
            {"label": "বিভাগ", "type": "text"}, {"label": "জেলা", "type": "text"}, {"label": "উপজেলা", "type": "text"}, 
            {"label": "ইউনিয়ন", "type": "text"}, {"label": "গ্রাম", "type": "text"}, {"label": "ওয়ার্ড নাম্বার", "type": "text"}, 
            {"label": "পোস্ট অফিস", "type": "text"}, {"label": "পিতার আইডি কার্ডের ছবি", "type": "photo"}, {"label": "পিতার জন্ম নিবন্ধন (যদি থাকে)", "type": "photo"}, 
            {"label": "মাতার আইডি কার্ডের ছবি", "type": "photo"}, {"label": "মাতার জন্ম নিবন্ধন (যদি থাকে)", "type": "photo"} 
        ]
    },
     "MRP_PASSPORT": {
        "name": "MRP পাসপোর্ট SB", "price": 1400, "enabled": True, "delivery": "অফিস টাইম", 
        "sub_options": { 
            "nid": {"name": "NID NO", "fields": [{"label": "NID NO", "type": "text"}, {"label": "জন্ম তারিখ", "type": "text"}]}, 
            "passport": {"name": "PASSPORT NO", "fields": [{"label": "PASSPORT NO", "type": "text"}, {"label": "জন্ম তারিখ", "type": "text"}]}, 
            "birth": {"name": "BIRTH NO", "fields": [{"label": "BIRTH NO", "type": "text"}, {"label": "জন্ম তারিখ", "type": "text"}]} 
        }
    },
    "E_PASSPORT": {
        "name": "ই-পাসপোর্ট SB", "price": 1400, "enabled": True, "delivery": "অফিস টাইম", 
        "sub_options": { 
            "nid": {"name": "NID NO", "fields": [{"label": "NID NO", "type": "text"}, {"label": "জন্ম তারিখ", "type": "text"}]}, 
            "passport": {"name": "PASSPORT NO", "fields": [{"label": "PASSPORT NO", "type": "text"}, {"label": "জন্ম তারিখ", "type": "text"}]}, 
            "birth": {"name": "BIRTH NO", "fields": [{"label": "BIRTH NO", "type": "text"}, {"label": "জন্ম তারিখ", "type": "text"}]} 
        }
    }
}
products = base_products # ডিফল্ট

ORDER_DISPLAY_CONFIG = {
    "SERVER_COPY": {"name": "Server_Copy", "time": "10 Minutes"},
    "ID_CARD": {"name": "NID_PDF", "time": "15 Minutes"},
    "SMART_CARD": {"name": "Smart_PDF", "time": "25 Minutes"},
    "BIOMETRIC": {"name": "Biometric", "time": "30 Minutes"},
    "LOCATION": {"name": "Location", "time": "30 Minutes"},
    "CALL_LIST": {"name": "Call_List", "time": "24 Hours"},
    "ID_TO_NUMBER": {"name": "I'd_To_Number", "time": "25 Minutes"},
    "TIN_CERTIFICATE": {"name": "Tin_Certificate", "time": "10 Minutes"},
    "BKASH_INFO": {"name": "bKash_Info", "time": "4 Hours"},
    "NAGAD_INFO": {"name": "Nagad_Info", "time": "4 Hours"},
    "LOST_ID_CARD": {"name": "Lost_ID_Card", "time": "3Hours"},
    "NEW_BIRTH_CERTIFICATE": {"name": "Birth_Certificate", "time": "48 Hours"},
    "MRP_PASSPORT": {"name": "Passport_SB", "time": "Office Time"},
    "E_PASSPORT": {"name": "Passport_SB", "time": "Office Time"}
}

# ===== গুগল শীট হেল্পার ফাংশন (আপনার পুরানো কোড থেকে) =====
def gs_load_all_data():
    global balances, orders, user_pinned_messages, whatsapp_numbers, products_config, previous_products_config, products
    logger.info("Google Sheet থেকে ডেটা লোড করা হচ্ছে...")
    try:
        # 1. users (balances, whatsapp) লোড
        users_data = users_sheet.get_all_records()
        balances.clear()
        whatsapp_numbers.clear()
        for user in users_data:
            uid = str(user.get('user_id', '')) # .get() ব্যবহার
            if not uid: continue # খালি সারি উপেক্ষা করুন
            balances[uid] = float(user.get('balance', 0))
            if user.get('whatsapp'):
                whatsapp_numbers[uid] = str(user.get('whatsapp'))
        
        # 2. orders লোড
        orders_data = orders_sheet.get_all_records()
        orders.clear()
        for order in orders_data:
            order_id = str(order.get('order_id', '')) # .get() ব্যবহার
            if not order_id: continue # খালি সারি উপেক্ষা করুন
            
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
            key = str(item.get('key', '')) # .get() ব্যবহার
            if not key: continue # খালি সারি উপেক্ষা করুন
            products_config[key] = {"price": float(item.get('price')),"enabled": bool(item.get('enabled') == 'TRUE' or item.get('enabled') == True)}
        
        # 4. previous_products লোড
        prev_config_data = previous_products_sheet.get_all_records()
        previous_products_config.clear()
        for item in prev_config_data:
            key = str(item.get('key', '')) # .get() ব্যবহার
            if not key: continue # খালি সারি উপেক্ষা করুন
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
            tr_id = str(tr.get('transaction_id', '')) # .get() ব্যবহার
            if not tr_id: continue # খালি সারি উপেক্ষা করুন
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
    if not isinstance(text, str): return text
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

# ===== টেবিল জেনারেটর ফাংশন (সঠিক করা) =====
def get_short_data_for_table(order_data):
    nid = order_data.get("NID নাম্বার", order_data.get("NID NO", "")).strip()
    dob = order_data.get("জন্ম তারিখ", order_data.get("জন্ম সাল", "")).strip()
    if not nid and not dob:
        # ৮টি get() এবং ৮টি বন্ধনী
        nid = order_data.get("বাংলালিংক নাম্বার", 
              order_data.get("গ্রামীন নাম্বার", 
              order_data.get("রবি নাম্বার", 
              order_data.get("এয়ারটেল নাম্বার", 
              order_data.get("টেলিটক নাম্বার", 
              order_data.get("MOBILE NO", 
              order_data.get("বিকাশ নাম্বার", 
              order_data.get("নগদ নাম্বার", "")))))))).strip()
        dob = ""
    if len(nid) > 11: nid = nid[:11] + ".."
    if len(dob) > 10: dob = dob[:10]
    return nid if nid else "N/A", dob if dob else "N/A"

def generate_table_status_text(order, product_key, status_key):
    short_id = order.get('short_id', order['order_id'])
    product_data = products.get(product_key)
    if not product_data: product_data = {}
    display_config = ORDER_DISPLAY_CONFIG.get(product_key, {"name": product_data.get("name", "N/A"), "time": product_data.get("delivery", "N/A")})
    service_name = display_config["name"]
    delivery_time = display_config["time"]
    order_data = order.get('data', {})
    nid, dob = get_short_data_for_table(order_data)
    
    status_text = ""
    if status_key == "processing": status_text = "🔵 Processing"
    elif status_key == "pending": status_text = "🟡 Pending"
    elif status_key == "Success": status_text = "🟢 Success"
    elif status_key == "Cancelled": status_text = "🚫 Cancel"
    elif status_key == "Not Found": status_text = "🚯 Not Found"
    elif status_key == "Completed": status_text = "✅ Completed"
    else: status_text = f"{status_key}"
    
    header =   f"NID         DOB        Time      Status"
    line =     f"----------------------------------------------"
    data_row = f"{nid:<11} {dob:<10} {delivery_time:<9} {status_text:<12}"
    message_text = f"""
📦 *অর্ডার:* `#{short_id}`
🏷️ *সার্ভিস:* {service_name}

`{header}`
`{line}`
`{data_row}`
"""
    return message_text
    
# ===== ব্যবহারকারীর অবস্থা ট্র্যাক করার জন্য ডিকশনারি =====
pending_replies = {}
admin_states = {}


# ===== নতুন: ওয়েব সার্ভার রুট (API) =====

@app.route('/get_init_data', methods=['POST'])
def get_init_data_route():
    try:
        data = request.json
        # (এখানে একটি জটিল টেলিগ্রাম ভেরিফিকেশন কোড থাকা উচিত)
        user_data = data.get('user', {})
        user_id = user_data.get('id')
        if not user_id:
            logger.warning("Auth check failed for get_init_data")
            abort(401)
        
        user_id_str = str(user_id)
        logger.info(f"/get_init_data called by user: {user_id_str}")

        balance = balances.get(user_id_str, 0)
        user_orders_list = []
        for order_id, order in orders.items():
            if order.get('uid') == user_id_str and order.get('type') is None:
                product_key = order.get('product')
                product = products.get(product_key)
                if not product: continue
                display_config = ORDER_DISPLAY_CONFIG.get(product_key, {"name": product.get("name", "N/A"), "time": product.get("delivery", "N/A")})
                delivery_type = "text"
                if product_key in ["ID_CARD", "SMART_CARD", "NEW_BIRTH_CERTIFICATE", "TIN_CERTIFICATE"]:
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
        notifications = [{"id": 1, "text": f"স্বাগতম, {user_data.get('first_name', '')}!", "time": "এখন"}]

        return jsonify({
            "balance": f"৳ {balance:.2f}",
            "orders": user_orders_list,
            "notifications": notifications,
            "products": base_products
        })
    except Exception as e:
        logger.error(f"get_init_data error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/submit_order', methods=['POST'])
def submit_order_route():
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
        
        price = product.get('price', 0)
        product_name = product.get('name')
        if sub_option_key and "sub_options" in product:
            sub_option_data = product["sub_options"].get(sub_option_key)
            if sub_option_data:
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
            
            photo_labels = [f.get('label') for f in product.get('fields', []) if f.get('type') == 'photo']
            if "sub_options" in product and sub_option_key:
                photo_labels.extend([f.get('label') for f in product["sub_options"][sub_option_key].get('fields', []) if f.get('type') == 'photo'])

            for label, value in form_data.items():
                if label in photo_labels:
                    order_text += f"{label}: (ফাইল আসছে...)\n"
                    try:
                        bot.send_photo(ADMIN_ID, value, caption=f"ফাইল: {label} (অর্ডার #{short_order_id})")
                    except:
                        bot.send_message(ADMIN_ID, f"ফাইল পাঠাতে ব্যর্থ: {label} (অর্ডার #{short_order_id})")
                else:
                    order_text += f"{label}: `{escape_markdown_v1(value)}`\n"
                
            markup = types.InlineKeyboardMarkup(row_width=3)
            markup.add(types.InlineKeyboardButton("🔵 Processing", callback_data=f"update_progress:processing:{full_order_id}"))
            markup.row(types.InlineKeyboardButton("✍️ রিপ্লাই (ফাইল)", callback_data=f"reply_{full_order_id}"), types.InlineKeyboardButton("✅ Success (স্ট্যাটাস)", callback_data=f"success_{full_order_id}"))
            markup.row(types.InlineKeyboardButton("🚫 ক্যানসেল", callback_data=f"cancel_{full_order_id}"), types.InlineKeyboardButton("🚯 নট ফাউন্ড", callback_data=f"notfound_{full_order_id}"))

            admin_msg = bot.send_message(ADMIN_ID, order_text, reply_markup=markup, parse_mode="Markdown")
            
            orders[full_order_id]['admin_notification_msg_id'] = admin_msg.message_id
            gs_update_order(full_order_id, admin_msg_id=admin_msg.message_id)

        except Exception as e:
            logger.error(f"অ্যাডমিনকে নোটিফিকেশন পাঠাতে ব্যর্থ: {e}")

        # ইউজারকে চ্যাটে কনফার্মেশন পাঠানো
        try:
            order_data['progress_msg_id'] = -1 # একটি প্লেসহোল্ডার
            status_text = generate_table_status_text(order_data, service_key, "pending")
            
            sent_msg = bot.send_message(user_id_str, status_text, parse_mode="Markdown")
            
            orders[full_order_id]['progress_msg_id'] = sent_msg.message_id
            gs_update_order(full_order_id, progress_msg_id=sent_msg.message_id)

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
        try:
            json_string = request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
            return "!", 200
        except Exception as e:
            logger.error(f"Webhook error: {e}")
            return "!", 200
    else:
        abort(403)

# রুট ৪: ওয়েব অ্যাপের URL সেট করা (শুধু প্রথমবার চালানোর জন্য)
@app.route('/')
def set_webhook():
    try:
        bot.remove_webhook()
        time.sleep(0.1)
        webhook_url = RENDER_APP_URL + '/' + TOKEN
        bot.set_webhook(url=webhook_url)
        logger.info(f"Webhook set to {webhook_url}")
        return f"Webhook set to {webhook_url}", 200
    except Exception as e:
        logger.error(f"Webhook সেট করতে ব্যর্থ: {e}")
        return f"Webhook সেট করতে ব্যর্থ: {e}", 500

@bot.message_handler(commands=["start"])
def start(message):
    uid = str(message.chat.id)
    
    menu_button = types.WebAppInfo(MINI_APP_URL)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add(types.KeyboardButton("🛒 সার্ভিস মেনু 🚀", web_app=menu_button))
    
    if message.chat.id == ADMIN_ID:
        markup.add(types.KeyboardButton("/admin"))

    bot.send_message(uid, "স্বাগতম! সার্ভিস অর্ডার করতে নিচের 'সার্ভিস মেনু' বাটনটি চাপুন:", reply_markup=markup)

    if uid not in balances:
        balances[uid] = 0
        whatsapp_numbers[uid] = "N/A"
        gs_update_user_data(uid, balance=0, whatsapp="N/A")

# ===== অ্যাডমিন প্যানেল এবং কলব্যাক হ্যান্ডলার (আপনার পুরানো কোড থেকে) =====
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

@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_"))
def handle_admin_panel_callback(call):
    bot.answer_callback_query(call.id)
    action = call.data.split('_', 1)[-1]
    
    if action == "add_balance":
        msg = bot.send_message(ADMIN_ID, "👤 ইউজার আইডি পাঠান:", parse_mode="Markdown")
        bot.register_next_step_handler(msg, admin_ask_for_amount)
    elif action == "broadcast":
        msg = bot.send_message(ADMIN_ID, "📢 মেসেজটি পাঠান (টেক্সট/ফটো/ভিডিও):", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_broadcast_message)
    elif action == "find_user":
        msg = bot.send_message(ADMIN_ID, "🔍 ইউজার আইডি পাঠান:", parse_mode="Markdown")
        bot.register_next_step_handler(msg, admin_process_user_find)
    elif action == "pending_orders":
        show_pending_orders()
    elif action == "show_all_users":
        show_all_users()
    # (প্রোডাক্ট ম্যানেজমেন্ট কলব্যাকগুলো নিচে আলাদাভাবে আছে)

def admin_ask_for_amount(message):
    try:
        user_id = message.text.strip()
        int(user_id)
        admin_states[ADMIN_ID] = {"action": "add_balance", "user_id": user_id}
        msg = bot.send_message(ADMIN_ID, f"💰 `{user_id}` এর জন্য টাকার *পরিমাণ* লিখুন:", parse_mode="Markdown")
        bot.register_next_step_handler(msg, admin_process_balance_add)
    except ValueError:
        bot.send_message(ADMIN_ID, "❌ ভুল ইউজার আইডি।"); admin_panel(message)
    except Exception as e: logger.error(e)

def admin_process_balance_add(message):
    try:
        amount = int(message.text.strip())
        if ADMIN_ID not in admin_states or admin_states[ADMIN_ID]['action'] != 'add_balance':
             bot.send_message(ADMIN_ID, "❌ একটি সমস্যা হয়েছে।"); return
        
        user_id = admin_states[ADMIN_ID]["user_id"]
        current_balance = float(balances.get(user_id, 0))
        new_balance = current_balance + amount
        
        balances[user_id] = new_balance
        gs_update_user_data(user_id, balance=new_balance)
        
        transaction_id = f"add_{user_id}_{int(time.time())}"
        tr_data = {"type": "balance_add", "uid": user_id, "amount": amount, "timestamp": int(time.time())}
        orders[transaction_id] = tr_data
        gs_add_transaction(transaction_id, tr_data)

        bot.send_message(ADMIN_ID, f"✅ সফল! `{user_id}` ব্যালেন্সে *{amount}* টাকা যোগ।\nবর্তমান ব্যালেন্স: {new_balance} টাকা", parse_mode="Markdown")
        try:
            bot.send_message(int(user_id), f"💰 *অভিনন্দন!* এডমিন আপনার ব্যালেন্সে *{amount}* টাকা যোগ করেছেন।\nআপনার বর্তমান ব্যালেন্স: {new_balance} টাকা", parse_mode="Markdown")
            update_pinned_balance(user_id)
        except Exception as e:
            logger.error(f"ইউজারকে ব্যালেন্স মেসেজ পাঠাতে সমস্যা: {e}")
        del admin_states[ADMIN_ID]
    except Exception as e:
        logger.error(e)
        bot.send_message(ADMIN_ID, "❌ ভুল ইনপুট। টাকার পরিমাণ সংখ্যা হতে হবে।")
        if ADMIN_ID in admin_states: del admin_states[ADMIN_ID]
        admin_panel(message)

def admin_process_user_find(message):
    try:
        user_id = message.text.strip()
        user_balance = balances.get(user_id, "N/A")
        total_orders = get_user_order_count(user_id)
        user_wa = whatsapp_numbers.get(user_id, "N/A")
        info_text = (f"🔍 *ব্যবহারকারীর তথ্য*\n\n🆔 *ইউজার:* `{user_id}`\n📱 *WhatsApp:* `{user_wa}`\n"
                     f"💳 *ব্যালেন্স:* *{user_balance}* টাকা\n🛒 *মোট অর্ডার:* *{total_orders}* টি")
        bot.send_message(ADMIN_ID, info_text, parse_mode="Markdown")
    except Exception as e: bot.send_message(ADMIN_ID, f"❌ খুঁজতে সমস্যা: {e}")

def show_pending_orders():
    try:
        pending_list = [f"`#{o.get('short_id', o['order_id'])}`" for oid, o in orders.items() if o.get("status") == "Pending" and o.get("type") is None]
        if not pending_list:
            bot.send_message(ADMIN_ID, "✅ _কোনো পেন্ডিং অর্ডার নেই।_", parse_mode="Markdown"); return
        text = "⏳ *পেন্ডিং অর্ডার তালিকা:*\n\n" + ", ".join(pending_list)
        bot.send_message(ADMIN_ID, text, parse_mode="Markdown")
    except Exception as e: logger.error(e)

def show_all_users():
    try:
        user_list = list(balances.keys())
        if not user_list:
            bot.send_message(ADMIN_ID, "ℹ️ কোনো ব্যবহারকারী নেই।"); return
        bot.send_message(ADMIN_ID, f"⏳ *{len(user_list)}* জন ব্যবহারকারীর তথ্য লোড হচ্ছে...", parse_mode="Markdown")
        full_text = "👥 *সকল ব্যবহারকারীর তালিকা*\n\n";
        for user_id in user_list:
            balance = balances.get(user_id, 0); name = "N/A"
            user_wa = whatsapp_numbers.get(user_id, "N/A")
            try:
                user_info = bot.get_chat(user_id); name = user_info.first_name
            except Exception: pass
            full_text += (f"👤 *নাম:* {name}\n🆔 *আইডি:* `{user_id}`\n📱 *WA:* `{user_wa}`\n"
                          f"💳 *ব্যালেন্স:* {balance} টাকা\n" + "-"*20 + "\n")
        if len(full_text) > 4096:
            for x in range(0, len(full_text), 4096): bot.send_message(ADMIN_ID, full_text[x:x+4096], parse_mode="Markdown")
        else: bot.send_message(ADMIN_ID, full_text, parse_mode="Markdown")
    except Exception as e: logger.error(e)

def process_broadcast_message(message):
    try:
        user_ids = list(balances.keys())
        if not user_ids: bot.send_message(ADMIN_ID, "❌ কোনো ইউজার পাওয়া যায়নি।"); return
        bot.send_message(ADMIN_ID, f"⏳ ব্রডকাস্ট শুরু... মোট *{len(user_ids)}* জন।", parse_mode="Markdown")
        success, fail = 0, 0
        for user_id in user_ids:
            try:
                bot.copy_message(int(user_id), ADMIN_ID, message.message_id); success += 1; time.sleep(0.1)
            except Exception as e:
                fail += 1; logger.warning(f"Broadcast failed for {user_id}: {e}")
        bot.send_message(ADMIN_ID, f"✅ *ব্রডকাস্ট সম্পন্ন!*\n*সফল:* {success} | *ব্যর্থ:* {fail}", parse_mode="Markdown")
    except Exception as e: bot.send_message(ADMIN_ID, f"⚠️ ব্রডকাস্টে সমস্যা: {e}")

@bot.callback_query_handler(func=lambda call: call.data == "admin_manage_products")
def handle_manage_products_callback(call): show_product_management_options(call.message)
@bot.callback_query_handler(func=lambda call: call.data == "admin_update_price_select")
def handle_update_price_select(call): ask_which_product_to_update_price(call.message)
@bot.callback_query_handler(func=lambda call: call.data == "admin_toggle_service_select")
def handle_toggle_service_select(call): ask_which_service_to_toggle(call.message)
@bot.callback_query_handler(func=lambda call: call.data == "admin_back_to_main")
def handle_back_to_main_admin(call):
     try: bot.delete_message(call.message.chat.id, call.message.message_id)
     except Exception: pass
     admin_panel(call.message)
@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_price_update:"))
def handle_price_update_selection(call):
    product_key = call.data.split(":", 1)[1]
    if product_key in products:
        product_price = products[product_key]['price']
        admin_states[ADMIN_ID] = {"action": "update_price", "product_key": product_key, "last_msg_id": call.message.message_id}
        msg = bot.send_message(ADMIN_ID, f"`{base_products[product_key]['name']}`-এর নতুন মূল্য লিখুন (বর্তমান: {product_price}):", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_new_price)
    else: bot.answer_callback_query(call.id, "❌ সার্ভিস নেই।")
@bot.callback_query_handler(func=lambda call: call.data.startswith("admin_toggle_service:"))
def handle_toggle_service(call):
    global products
    product_key = call.data.split(":", 1)[1]
    if product_key in base_products:
        current_status = products[product_key].get('enabled', True)
        new_status = not current_status
        gs_update_product_config(product_key, enabled=new_status)
        products[product_key]['enabled'] = new_status
        if product_key not in products_config: products_config[product_key] = {}
        products_config[product_key]['enabled'] = new_status
        new_status_text = "চালু" if new_status else "বন্ধ"
        bot.answer_callback_query(call.id, f"✅ {base_products[product_key]['name']} {new_status_text} করা হয়েছে। (লাইভ)")
        ask_which_service_to_toggle(call.message)
    else: bot.answer_callback_query(call.id, "❌ সার্ভিস নেই।")
def show_product_management_options(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add( types.InlineKeyboardButton("💰 মূল্য আপডেট", callback_data="admin_update_price_select"),
                types.InlineKeyboardButton("🟢/🔴 সার্ভিস চালু/বন্ধ", callback_data="admin_toggle_service_select"),
                types.InlineKeyboardButton("⬅️ ফিরে যান", callback_data="admin_back_to_main") )
    bot.edit_message_text("⚙️ *প্রোডাক্ট ম্যানেজমেন্ট*", message.chat.id, message.message_id, reply_markup=markup, parse_mode="Markdown")
def ask_which_product_to_update_price(message):
    temp_products = {}
    for key, base_p in base_products.items():
         temp_products[key] = base_p.copy()
         temp_products[key]['price'] = products[key]['price']
    markup = types.InlineKeyboardMarkup(row_width=1)
    for key, product in temp_products.items():
         markup.add(types.InlineKeyboardButton(f"{product['name']} (৳{product['price']})", callback_data=f"admin_price_update:{key}"))
    markup.add(types.InlineKeyboardButton("⬅️ ফিরে যান", callback_data="admin_manage_products"))
    bot.edit_message_text("💰 কোন সার্ভিসের মূল্য পরিবর্তন করতে চান?", message.chat.id, message.message_id, reply_markup=markup)
def process_new_price(message):
    class MockMessage:
         def __init__(self, chat_id, message_id): self.chat = MockChat(chat_id); self.message_id = message_id
    class MockChat:
         def __init__(self, id): self.id = id
    try:
        new_price = int(message.text.strip())
        if ADMIN_ID in admin_states and admin_states[ADMIN_ID]['action'] == 'update_price':
            product_key = admin_states[ADMIN_ID]['product_key']
            last_msg_id = admin_states[ADMIN_ID]['last_msg_id']
            gs_update_product_config(product_key, price=new_price)
            global products
            products[product_key]['price'] = new_price
            if product_key not in products_config: products_config[product_key] = {}
            products_config[product_key]['price'] = new_price
            bot.send_message(ADMIN_ID, f"✅ `{base_products[product_key]['name']}`-এর মূল্য ৳{new_price}-তে আপডেট করা হয়েছে। (লাইভ)")
            del admin_states[ADMIN_ID]
            try: bot.delete_message(ADMIN_ID, message.message_id)
            except Exception: pass
            original_list_message = MockMessage(ADMIN_ID, last_msg_id)
            ask_which_product_to_update_price(original_list_message) 
        else: bot.send_message(ADMIN_ID, "❌ সমস্যা হয়েছে।")
    except Exception as e:
        logger.error(e)
        bot.send_message(ADMIN_ID, "❌ ভুল ইনপুট। সংখ্যা লিখুন।")
        if ADMIN_ID in admin_states: del admin_states[ADMIN_ID]
        admin_panel(message)
def ask_which_service_to_toggle(message):
    temp_products = {}
    for key, base_p in base_products.items():
         temp_products[key] = base_p.copy()
         temp_products[key]['enabled'] = products[key].get('enabled', True)
    markup = types.InlineKeyboardMarkup(row_width=1)
    for key, product in temp_products.items():
        status_icon = "🟢" if product.get("enabled", True) else "🔴"
        markup.add(types.InlineKeyboardButton(f"{product['name']} ({status_icon})", callback_data=f"admin_toggle_service:{key}"))
    markup.add(types.InlineKeyboardButton("⬅️ ফিরে যান", callback_data="admin_manage_products"))
    bot.edit_message_text("🟢/🔴 কোন সার্ভিসের অবস্থা পরিবর্তন করতে চান?", message.chat.id, message.message_id, reply_markup=markup)
@bot.callback_query_handler(func=lambda call: call.data.startswith("update_progress:"))
def handle_admin_progress_update(call):
    try:
        _, _, order_id = call.data.split(":") 
        if order_id in orders:
            order = orders[order_id]; product = products[order["product"]]; uid = order['uid']
            progress_msg_id = order.get('progress_msg_id')
            if progress_msg_id:
                try:
                    product_key = order["product"]
                    processing_text = generate_table_status_text(order, product_key, "processing")
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton("👁️ অর্ডারের তথ্য দেখুন", callback_data=f"view_info:{order_id}"))
                    bot.edit_message_text(processing_text, uid, progress_msg_id, reply_markup=markup, parse_mode="Markdown") 
                    bot.answer_callback_query(call.id, f"✅ 'Processing' আপডেট।")
                except ApiTelegramException as e:
                    if "message is not modified" in str(e): bot.answer_callback_query(call.id, "⚠️ ইতিমধ্যে আপডেট।")
                    else: logger.error(f"ERROR editing message: {e}"); bot.answer_callback_query(call.id, "❌ মেসেজ আপডেটে সমস্যা!")
        else: bot.answer_callback_query(call.id, "❌ অর্ডার নেই।")
    except Exception as e: logger.error(e); bot.answer_callback_query(call.id, "❌ ভুল কমান্ড।")
@bot.callback_query_handler(func=lambda call: call.data.startswith("quick_reply:"))
def handle_quick_reply(call):
    try:
        _, reply_key, order_id = call.data.split(":")
        if order_id in orders and reply_key in quick_replies:
             order = orders[order_id]; uid = order['uid']; reply_text = quick_replies[reply_key]
             bot.send_message(uid, f"💬 *এডমিনের বার্তা:*\n{reply_text}", parse_mode="Markdown")
             bot.answer_callback_query(call.id, f"✅ '{reply_text[:15]}...' পাঠানো হয়েছে।")
             show_main_order_actions(call.message, order_id)
        else: bot.answer_callback_query(call.id, "❌ অর্ডার বা রিপ্লাই খুঁজে পাওয়া যায়নি।")
    except Exception as e: logger.error(e); bot.answer_callback_query(call.id, "❌ একটি সমস্যা হয়েছে।")
def show_main_order_actions(message, order_id):
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(types.InlineKeyboardButton("🔵 Processing", callback_data=f"update_progress:processing:{order_id}"))
    markup.row(types.InlineKeyboardButton("✍️ রিপ্লাই (ফাইল)", callback_data=f"reply_{order_id}"), types.InlineKeyboardButton("✅ Success (স্ট্যাটাস)", callback_data=f"success_{order_id}"))
    markup.row(types.InlineKeyboardButton("💬 দ্রুত উত্তর", callback_data=f"quick_{order_id}"))
    markup.row( types.InlineKeyboardButton("🚫 ক্যানসেল", callback_data=f"cancel_{order_id}"), types.InlineKeyboardButton("🚯 নট ফাউন্ড", callback_data=f"notfound_{order_id}"))
    try:
        bot.edit_message_reply_markup(ADMIN_ID, message.message_id, reply_markup=markup)
    except ApiTelegramException as e:
        if "message is not modified" not in str(e): logger.error(f"Error showing main actions: {e}")
@bot.callback_query_handler(func=lambda call: call.data.startswith(("reply_", "cancel_", "notfound_", "quick_", "success_")))
def handle_admin_final_actions(call):
    try:
        parts = call.data.split("_", 1); action_type = parts[0]; order_id = parts[1]
        if order_id not in orders: bot.answer_callback_query(call.id, "❌ অর্ডার খুঁজে পাওয়া যাচ্ছে না।"); return
        order = orders[order_id]; uid = order["uid"]; product = products.get(order["product"])
        if not product: bot.answer_callback_query(call.id, "❌ প্রোডাক্টটি আর নেই।"); return
        
        if action_type == "reply":
            pending_replies[str(ADMIN_ID)] = order_id
            bot.send_message(ADMIN_ID, f"✍️ অর্ডার `#{order.get('short_id', order_id)}` এর রিপ্লাই পাঠান।", parse_mode="Markdown")
            bot.answer_callback_query(call.id, "✅ এখন রিপ্লাই পাঠান।")
        
        elif action_type == "quick":
             markup = types.InlineKeyboardMarkup(row_width=1).add( types.InlineKeyboardButton("⏳ অপেক্ষা করুন", callback_data=f"quick_reply:wait:{order_id}"),
                                                                 types.InlineKeyboardButton("🤔 তথ্য সঠিক নয়", callback_data=f"quick_reply:wrong:{order_id}"),
                                                                 types.InlineKeyboardButton("👍 কাজ শুরু", callback_data=f"quick_reply:started:{order_id}"),
                                                                 types.InlineKeyboardButton("⬅️ ফিরে যান", callback_data=f"back_to_order_actions:{order_id}") )
             bot.edit_message_reply_markup(ADMIN_ID, call.message.message_id, reply_markup=markup); bot.answer_callback_query(call.id)
        
        elif action_type == "success":
            new_status_key = "Success"
            order["status"] = new_status_key
            gs_update_order(order_id, status=new_status_key)
            progress_msg_id = order.get('progress_msg_id')
            if progress_msg_id:
                try: 
                    product_key = order["product"]
                    final_text = generate_table_status_text(order, product_key, new_status_key)
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton("👁️ অর্ডারের তথ্য দেখুন", callback_data=f"view_info:{order_id}"))
                    bot.edit_message_text(final_text, uid, progress_msg_id, reply_markup=markup, parse_mode="Markdown")
                except ApiTelegramException as e: logger.error(f"ERROR editing message: {e}")
            bot.edit_message_text(f"✅ অর্ডার `#{order.get('short_id', order_id)}` {new_status_key}।", call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=None)
            bot.answer_callback_query(call.id, f"✅ অর্ডার {new_status_key}।")

        elif action_type in ["cancel", "notfound"]:
            new_status_key = "Cancelled" if action_type == "cancel" else "Not Found" 
            order["status"] = new_status_key
            gs_update_order(order_id, status=new_status_key)
            price = order.get("price", product['price'])
            current_balance = float(balances.get(uid, 0)); new_balance = current_balance + price
            balances[uid] = new_balance
            gs_update_user_data(uid, balance=new_balance)
            progress_msg_id = order.get('progress_msg_id')
            if progress_msg_id:
                try: 
                    product_key = order["product"]
                    final_text = generate_table_status_text(order, product_key, new_status_key)
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton("👁️ অর্ডারের তথ্য দেখুন", callback_data=f"view_info:{order_id}"))
                    bot.edit_message_text(final_text, uid, progress_msg_id, reply_markup=markup, parse_mode="Markdown")
                except ApiTelegramException as e: 
                     logger.error(f"ERROR editing message: {e}")
                     try: bot.send_message(uid, f"❌ অর্ডার {new_status_key}, কিন্তু স্ট্যাটাস মেসেজ আপডেট করা যায়নি।") 
                     except: pass
            try:
                bot.send_message(int(uid), f"❌ '{product['name']}' অর্ডার ({new_status_key}) করা হয়েছে। *{price}* টাকা ফেরত।", parse_mode="Markdown")
                update_pinned_balance(uid)
            except Exception as e: logger.error(f"ইউজারকে রিফান্ড মেসেজ পাঠাতে সমস্যা: {e}")
            bot.edit_message_text(f"❌ অর্ডার `#{order.get('short_id', order_id)}` {new_status_key}।", call.message.chat.id, call.message.message_id, parse_mode="Markdown", reply_markup=None)
            bot.answer_callback_query(call.id, f"❌ অর্ডার {new_status_key}।")
    except Exception as e: logger.error(f"ফাইনাল অ্যাকশন এরর: {e}")
@bot.callback_query_handler(func=lambda call: call.data.startswith("back_to_order_actions:"))
def handle_back_to_order_actions(call):
     order_id = call.data.split(":", 1)[1]
     if order_id in orders: show_main_order_actions(call.message, order_id)
     bot.answer_callback_query(call.id)
quick_replies = {"wait": "⏳ একটু অপেক্ষা করুন...","wrong": "🤔 তথ্যে গরমিল আছে...","started": "👍 কাজ শুরু হয়েছে।"}
@bot.callback_query_handler(func=lambda call: call.data.startswith('view_info:'))
def handle_view_info(call):
    try:
        order_id = call.data.split(":", 1)[1]
        if order_id in orders:
            order = orders[order_id]; order_data = order.get('data', {})
            hidden_info = "অর্ডারের জন্য দেওয়া তথ্য:\n\n" 
            if not order_data: hidden_info += "কোনো তথ্য সেভ করা নেই।"
            else:
                for label, value in order_data.items():
                    clean_label = label.replace("ঃ", "").strip() 
                    if isinstance(value, str) and value.startswith(("AgAC", "BAAC", "FILE_ID:")): display_value = "(ফাইল 🖼️)"
                    else: display_value = value
                    hidden_info += f"{clean_label}: {display_value}\n" 
            bot.answer_callback_query(call.id, text=hidden_info, show_alert=True, cache_time=1)
        else: bot.answer_callback_query(call.id, "❌ দুঃখিত, অর্ডারের তথ্য খুঁজে পাওয়া যায়নি।", show_alert=True)
    except Exception as e: logger.error(e); bot.answer_callback_query(call.id, "❌ তথ্য দেখাতে সমস্যা হচ্ছে।", show_alert=True)
@bot.message_handler(func=lambda m: str(m.chat.id) == str(ADMIN_ID) and str(m.chat.id) in pending_replies, content_types=["text", "photo", "document", "video"])
def admin_send_reply(message):
    try:
        admin_id_str = str(message.chat.id); order_id = pending_replies.pop(admin_id_str)
        if order_id not in orders: bot.send_message(message.chat.id, "❌ অর্ডার নেই।"); return
        
        order = orders[order_id]; uid = int(order["uid"]); product_key = order["product"]
        product = products.get(product_key)
        if not product: bot.send_message(message.chat.id, "❌ প্রোডাক্টটি আর নেই।"); return
        
        display_config = ORDER_DISPLAY_CONFIG.get(product_key, {"name": product_key,"time": product.get("delivery", "N/A")})
        display_name = display_config["name"]; display_time = display_config["time"]
        order_price = order.get("price", product["price"]); short_id = order.get('short_id', order_id)

        progress_msg_id = order.get('progress_msg_id')
        if progress_msg_id:
            try: 
                final_text = generate_table_status_text(order, product_key, "Completed")
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("👁️ অর্ডারের তথ্য দেখুন", callback_data=f"view_info:{order_id}"))
                bot.edit_message_text(final_text, uid, progress_msg_id, reply_markup=markup, parse_mode="Markdown") 
            except ApiTelegramException as e: 
                 logger.error(f"ERROR editing message in admin_send_reply: {e}")
                 try: bot.send_message(uid, f"✅ অর্ডার সম্পন্ন, কিন্তু স্ট্যাটাস মেসেজ আপডেট করা যায়নি।") 
                 except: pass

        delivery_caption = "" 
        bot.copy_message(uid, message.chat.id, message.message_id, caption=delivery_caption, reply_to_message_id=progress_msg_id, parse_mode=None)
        
        order["status"] = "Completed"; gs_update_order(order_id, status="Completed") 
        bot.send_message(message.chat.id, f"✅ `#{short_id}` রিপ্লাই পাঠানো হয়েছে।", parse_mode="Markdown")
        
        original_admin_msg_id = order.get('admin_notification_msg_id')
        if original_admin_msg_id:
            try:
                bot.edit_message_text(f"✅ `#{short_id}` রিপ্লাই (ফাইল) পাঠানো হয়েছে।", ADMIN_ID, original_admin_msg_id, parse_mode="Markdown", reply_markup=None)
            except Exception: pass
    except Exception as e: 
        logger.error(f"ডেলিভারি পাঠাতে সমস্যা: {e}")
        bot.send_message(message.chat.id, f"⚠️ ডেলিভারি পাঠাতে সমস্যা: {e}"); 
        pending_replies[admin_id_str] = order_id

# ===== পুরানো অর্ডার ফ্লো ফাংশনগুলো ডিজেবল করা =====
@bot.message_handler(func=lambda m: str(m.chat.id) in user_orders)
def handle_legacy_order(message):
    bot.send_message(message.chat.id, "অনুগ্রহ করে '🛒 সার্ভিস মেনু' বাটনটি ব্যবহার করে অর্ডার করুন।")
@bot.message_handler(content_types=['text'])
def handle_all_text(message):
    if message.chat.id == ADMIN_ID and message.text == "/admin":
        admin_panel(message)
    else:
        # ইউজারকে মেনু বাটন ব্যবহার করতে বলা
        start(message)

# ===== বট এবং সার্ভার চালু করা =====
# (এই অংশটি Gunicorn দ্বারা চালিত হবে)
if __name__ != "__main__":
    logger.info("Gunicorn সার্ভার হিসেবে চালু হচ্ছে...")
    try:
        logger.info("বট ডেটা লোড করা হচ্ছে...")
        gs_load_all_data()
        
        # Webhook সেটআপটি / রুট থেকে করা হবে, এখানে নয়
        
    except Exception as e:
        logger.error(f"Gunicorn চালু করার সময় এরর: {e}")
