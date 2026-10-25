from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo
from config import WEBAPP_BASE_URL

def get_contact_kb() -> ReplyKeyboardMarkup:
    """Telegramdagi raqamni asosiy qilib yuborish tugmasi"""
    kb = [
        [KeyboardButton(text="📲 Shu Telegram raqamimni yuborish", request_contact=True)]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True, one_time_keyboard=True)

def get_main_menu_kb(telegram_id: int = 0, is_admin: bool = False) -> ReplyKeyboardMarkup:
    """
    O'quvchi uchun yagona Web App portali va tezkor boshqaruv:
    Barcha bo'limlar (Test, Kurslar, Jadvallar, Natijalar, Aloqa) bitta tugmada!
    """
    is_https = WEBAPP_BASE_URL.startswith("https://")
    portal_url = f"{WEBAPP_BASE_URL}/?uid={telegram_id}"

    if is_https:
        btn_portal = KeyboardButton(text="📱 Wall Street Web App (Barcha bo'limlar)", web_app=WebAppInfo(url=portal_url))
    else:
        btn_portal = KeyboardButton(text="📱 Wall Street Web App (Barcha bo'limlar)")

    kb = [
        [btn_portal],
        [
            KeyboardButton(text="📞 Reception telefon raqami"),
            KeyboardButton(text="🎁 Promokod")
        ]
    ]

    if is_admin:
        kb.append([KeyboardButton(text="⚙️ Rahbar & Reception Paneli")])

    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_cancel_kb() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="❌ Bekor qilish")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)
