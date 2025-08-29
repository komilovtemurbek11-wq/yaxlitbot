# -*- coding: utf-8 -*-
# Nitro Movies Bot — Temur uchun to‘liq ishlaydigan va barqaror versiya

import os
import sqlite3
import telebot
from telebot import types
from flask import Flask
import threading

# ===================== MUHIM SOZLAMALAR =====================
TOKEN = os.getenv("BOT_TOKEN", "8374881360:AAG4awRqTVHRJCptoLY1ItLss6r6oLl0DRE")
ADMIN_IDS = {5051898362}
ADMIN_USERNAME = "temur_2080"  # @temur_2080
DB_PATH = "media.db"
# ============================================================

bot = telebot.TeleBot(TOKEN, parse_mode="HTML", threaded=True)

# ====== SQLite ======
def db_init():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS media (
        code TEXT PRIMARY KEY,
        category TEXT,
        name TEXT,
        file_id TEXT,
        media_type TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    try:
        c.execute("ALTER TABLE media ADD COLUMN name TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

def db_add(code, category, name, file_id, media_type):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("REPLACE INTO media (code, category, name, file_id, media_type) VALUES (?, ?, ?, ?, ?)",
              (code, category, name, file_id, media_type))
    conn.commit()
    conn.close()

def db_get(code):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT code, category, name, file_id, media_type FROM media WHERE code = ?", (code,))
    row = c.fetchone()
    conn.close()
    return row

def db_get_category(category):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT code, name, file_id, media_type FROM media WHERE category = ?", (category,))
    rows = c.fetchall()
    conn.close()
    return rows

def db_delete(code):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM media WHERE code = ?", (code,))
    cnt = c.rowcount
    conn.commit()
    conn.close()
    return cnt

db_init()

# ====== Kategoriya normalize ======
def normalize_category(cat_raw: str):
    if not cat_raw:
        return None
    cat = cat_raw.strip().lower()
    aliases = {
        "kino": "kino", "kinolar": "kino", "film": "kino", "filmlar": "kino",
        "serial": "serial", "seriallar": "serial",
        "mult": "multfilm", "multfilm": "multfilm", "multfilmlar": "multfilm",
        "cartoon": "multfilm", "animation": "multfilm", "anime": "multfilm",
    }
    return aliases.get(cat)

# ====== Menyular ======
def main_menu(is_admin: bool = False):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🎥 Kinolar", "📺 Seriallar")
    kb.row("🎞 Multfilmlar")
    kb.row("⭐ Xizmatlar", "📩 Admin bilan bog‘lanish")
    if is_admin:
        kb.row("🛠 Admin panel")
    return kb

def services_keyboard():
    ikb = types.InlineKeyboardMarkup()
    ikb.add(
        types.InlineKeyboardButton("Telegram Premium", url=f"https://t.me/{ADMIN_USERNAME}"),
        types.InlineKeyboardButton("Telegram Stars", url=f"https://t.me/{ADMIN_USERNAME}")
    )
    ikb.add(types.InlineKeyboardButton("Admin bilan bog‘lanish", url=f"https://t.me/{ADMIN_USERNAME}"))
    return ikb

def admin_help_text():
    return (
        "🛠 <b>Admin panel</b>\n"
        "➕ Qo‘shish: media yuboring → kategoriya → kod → nom\n"
        "🗑 O‘chirish: <code>del &lt;kod&gt;</code>\n"
        "📂 Kategoriyalar: <code>kino</code> | <code>serial</code> | <code>multfilm</code>\n"
        "📎 Media turlari: video, document, animation (gif), sticker\n"
    )

# ====== /start ======
@bot.message_handler(commands=['start'])
def cmd_start(message: telebot.types.Message):
    is_admin = message.from_user.id in ADMIN_IDS
    text_user = (
        "🎬 <b>Nitro Movies</b> botiga xush kelibsiz!\n\n"
        "Kod yuboring va to‘liq kino/serial/multfilmlarni oling.\n"
        "Masalan: <code>7</code>\n"
    )
    if is_admin:
        text_user += "\n\n" + admin_help_text()
    bot.send_message(message.chat.id, text_user, reply_markup=main_menu(is_admin), disable_web_page_preview=True)

# ====== /id ======
@bot.message_handler(commands=['id'])
def cmd_id(message: telebot.types.Message):
    bot.reply_to(message, f"Sizning ID: <code>{message.from_user.id}</code>")

# ====== Kategoriya va sub-menu ======
@bot.message_handler(func=lambda m: m.text in ["🎥 Kinolar", "📺 Seriallar", "🎞 Multfilmlar"])
def menu_categories(message: telebot.types.Message):
    mapping = {
        "🎥 Kinolar": "kino",
        "📺 Seriallar": "serial",
        "🎞 Multfilmlar": "multfilm",
    }
    category = mapping[message.text]
    rows = db_get_category(category)
    if not rows:
        bot.send_message(message.chat.id, "❌ Bu kategoriyada hali media yo‘q.")
        return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for code, name, _, _ in rows:
        kb.add(f"{code} - {name}")
    kb.row("⬅️ Orqaga")
    bot.send_message(message.chat.id, f"📂 <b>{category}</b> kategoriyasidagi media ro‘yxati:", reply_markup=kb, parse_mode="HTML")

# ====== Xizmatlar ======
@bot.message_handler(func=lambda m: m.text == "⭐ Xizmatlar")
def menu_services(message: telebot.types.Message):
    bot.send_message(
        message.chat.id,
        "⭐ <b>Xizmatlar</b>\n\nTelegram Premium / Telegram Stars / Admin bilan bog‘lanish:",
        reply_markup=services_keyboard(),
        disable_web_page_preview=True
    )

# ====== Admin bilan bog‘lanish ======
@bot.message_handler(func=lambda m: m.text == "📩 Admin bilan bog‘lanish")
def menu_admin_contact(message: telebot.types.Message):
    bot.send_message(
        message.chat.id,
        f"👉 <b>Admin:</b> @{ADMIN_USERNAME}",
        reply_markup=main_menu(message.from_user.id in ADMIN_IDS),
        disable_web_page_preview=True
    )

# ====== ADMIN PANEL ======
@bot.message_handler(func=lambda m: m.text == "🛠 Admin panel")
def menu_admin_panel(message: telebot.types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("📤 Kino/Serial/Multfilm qo‘shish")
    kb.row("🗑 O‘chirish", "📂 Kategoriyalar")
    kb.row("⬅️ Orqaga")
    bot.send_message(message.chat.id, "🛠 Admin panel:", reply_markup=kb)

# ====== ADMIN MEDIA QO'SHISH ======
@bot.message_handler(func=lambda m: m.text == "📤 Kino/Serial/Multfilm qo‘shish")
def start_add_media(message: telebot.types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    msg = bot.send_message(message.chat.id, "🔹 Iltimos, media yuboring (video/document/animation/sticker):")
    bot.register_next_step_handler(msg, get_media_file)

def get_media_file(message: telebot.types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    file_id = None
    media_type = None
    if message.video:
        file_id = message.video.file_id
        media_type = "video"
    elif message.document:
        file_id = message.document.file_id
        media_type = "document"
    elif message.animation:
        file_id = message.animation.file_id
        media_type = "animation"
    elif message.sticker:
        file_id = message.sticker.file_id
        media_type = "sticker"
    else:
        msg = bot.send_message(message.chat.id, "❗ Faqat video/document/animation/sticker yuboring. Qaytadan yuboring:")
        bot.register_next_step_handler(msg, get_media_file)
        return

    msg = bot.send_message(message.chat.id, "🔹 Kategoriya kiriting (kino / serial / multfilm):")
    bot.register_next_step_handler(msg, lambda m: get_category(m, file_id, media_type))

def get_category(message, file_id, media_type):
    if message.from_user.id not in ADMIN_IDS:
        return
    category = normalize_category(message.text)
    if not category:
        msg = bot.send_message(message.chat.id, "❗ Noto‘g‘ri kategoriya. Qaytadan kiriting (kino/serial/multfilm):")
        bot.register_next_step_handler(msg, lambda m: get_category(m, file_id, media_type))
        return
    msg = bot.send_message(message.chat.id, "🔹 Kod kiriting (masalan: 7):")
    bot.register_next_step_handler(msg, lambda m: get_code(m, file_id, media_type, category))

def get_code(message, file_id, media_type, category):
    if message.from_user.id not in ADMIN_IDS:
        return
    code = message.text.strip()
    msg = bot.send_message(message.chat.id, "🔹 Nom kiriting (masalan: Wednesday 1-qism):")
    bot.register_next_step_handler(msg, lambda m: save_media(m, file_id, media_type, category, code))

def save_media(message, file_id, media_type, category, code):
    if message.from_user.id not in ADMIN_IDS:
        return
    name = message.text.strip()
    try:
        db_add(code, category, name, file_id, media_type)
        bot.send_message(message.chat.id, f"✅ Qo‘shildi:\n• Kategoriya: <b>{category}</b>\n• Kod: <code>{code}</code>\n• Nom: <b>{name}</b>\n• Media: <i>{media_type}</i>")
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠️ Saqlashda xato: {e}")

# ====== DELETE ======
@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith("del"))
def handle_del(message):
    if message.from_user.id not in ADMIN_IDS:
        return bot.reply_to(message, "⛔ Ruxsat yo‘q.")
    parts = message.text.split()
    if len(parts) < 2:
        return bot.reply_to(message, "❗ Format: <code>del &lt;kod&gt;</code>")
    code = " ".join(parts[1:]).strip()
    deleted = db_delete(code)
    if deleted:
        bot.reply_to(message, f"🗑 O‘chirildi: <code>{code}</code>")
    else:
        bot.reply_to(message, f"❌ Topilmadi: <code>{code}</code>")

# ====== FOYDALANUVCHI KOD YUBORGANIDA ======
@bot.message_handler(func=lambda m: m.text and not m.text.startswith("/"))
def by_code(message):
    text = message.text.strip()

    # ========== ORQAGA TUGMASI ==========
    if text == "⬅️ Orqaga":
        is_admin = message.from_user.id in ADMIN_IDS
        bot.send_message(message.chat.id, "🔹 Asosiy menyu:", reply_markup=main_menu(is_admin))
        return

    # ========== KODNI TEKSHIRISH ==========
    if " - " in text:
        code = text.split(" - ")[0]
        row = db_get(code)
        if row:
            send_media_from_row(message.chat.id, row)
        else:
            bot.send_message(message.chat.id, "❌ Kod topilmadi. Kategoriyani tekshiring yoki to‘g‘ri kod kiriting.")
    else:
        # Kod topilmasa kategoriya bo‘lishi mumkin
        category = normalize_category(text)
        if category:
            rows = db_get_category(category)
            if not rows:
                bot.send_message(message.chat.id, "❌ Bu kategoriyada media topilmadi.")
                return
            kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
            for code, name, _, _ in rows:
                kb.add(f"{code} - {name}")
            kb.row("⬅️ Orqaga")
            bot.send_message(message.chat.id, f"📂 <b>{category}</b> kategoriyasidagi media ro‘yxati:", reply_markup=kb, parse_mode="HTML")
        else:
            bot.send_message(message.chat.id, "❌ Kod yoki kategoriya topilmadi.")

def send_media_from_row(chat_id, row):
    _, category, name, file_id, media_type = row
    caption = f"📦 Kod: <code>{row[0]}</code>\n📂 Kategoriya: <b>{category}</b>\n🎬 Nom: <b>{name}</b>"
    try:
        if media_type == "video":
            bot.send_video(chat_id, file_id, caption=caption)
        elif media_type == "document":
            bot.send_document(chat_id, file_id, caption=caption)
        elif media_type == "animation":
            bot.send_animation(chat_id, file_id, caption=caption)
        elif media_type == "sticker":
            bot.send_sticker(chat_id, file_id)
            bot.send_message(chat_id, caption)
        else:
            bot.send_document(chat_id, file_id, caption=caption)
    except Exception as e:
        bot.send_message(chat_id, f"⚠️ Yuborishda xato: {e}")

# ============================ FLASK WEB SERVER ============================
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running!"

port = int(os.environ.get("PORT", 10000))
def run_flask():
    app.run(host="0.0.0.0", port=port)

threading.Thread(target=run_flask).start()

# ============================ BOTNI ISHGA TUSHURISH ============================
if __name__ == "__main__":
    print("Bot ishga tushdi...")
    bot.skip_pending = True
    bot.infinity_polling(timeout=30, long_polling_timeout=30)


