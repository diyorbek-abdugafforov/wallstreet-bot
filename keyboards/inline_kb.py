from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from typing import List, Dict, Any
from config import WEBAPP_BASE_URL

def get_level_selection_kb(telegram_id: int) -> InlineKeyboardMarkup:
    """
    Ro'yxatdan o'tgach darajani tanlash yoki Web App orqali test topshirish
    """
    is_https = WEBAPP_BASE_URL.startswith("https://")
    if "netlify.app" in WEBAPP_BASE_URL:
        test_url = f"{WEBAPP_BASE_URL}/?tab=test&uid={telegram_id}"
    else:
        test_url = f"{WEBAPP_BASE_URL}/webapp/portal?tab=test&uid={telegram_id}"

    if is_https:
        test_btn = InlineKeyboardButton(text="🎯 Darajani aniqlash (Online Test)", web_app=WebAppInfo(url=test_url))
    else:
        test_btn = InlineKeyboardButton(text="🎯 Darajani aniqlash (Online Test)", callback_data="start_bot_quiz")

    buttons = [
        [
            InlineKeyboardButton(text="🌱 Beginner", callback_data="choose_lvl:Beginner"),
            InlineKeyboardButton(text="📘 Elementary", callback_data="choose_lvl:Elementary")
        ],
        [
            InlineKeyboardButton(text="📗 Pre-Intermediate", callback_data="choose_lvl:Pre-Intermediate"),
            InlineKeyboardButton(text="📙 Intermediate", callback_data="choose_lvl:Intermediate")
        ],
        [
            test_btn
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_test_question_kb(question_id: int, options: List[str]) -> InlineKeyboardMarkup:
    """Test savolining javob variantlari"""
    buttons = []
    option_letters = ["A", "B", "C", "D"]
    for idx, opt in enumerate(options):
        letter = option_letters[idx] if idx < len(option_letters) else str(idx + 1)
        buttons.append([
            InlineKeyboardButton(
                text=f"{letter}) {opt}",
                callback_data=f"test_ans:{question_id}:{idx}"
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_schedules_kb(schedules: List[str]) -> InlineKeyboardMarkup:
    """Qulay dars vaqtini tanlash inline tugmalari"""
    buttons = []
    for idx, sch in enumerate(schedules):
        buttons.append([
            InlineKeyboardButton(
                text=f"🕒 {sch}",
                callback_data=f"sel_sched:{idx}"
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_manager_lead_kb(telegram_id: int, phone: str = "") -> InlineKeyboardMarkup:
    """
    Reception va Menejerlar guruhi uchun lidni boshqarish tugmalari.
    PDF qo'llanmasiga muvofiq:
    - Qo'ng'iroq qilish
    - Statusni o'zgartirish (Bog'lanildi, Sinov darsiga yozildi, Guruhga qo'shildi, Rad etildi)
    """
    clean_phone = phone.replace("+", "").replace(" ", "").replace("-", "") if phone else ""
    buttons = []
    
    # Tezkor qo'ng'iroq va profil
    row_top = []
    if clean_phone:
        row_top.append(InlineKeyboardButton(text="📞 Qo'ng'iroq", url=f"tel:+{clean_phone}"))
    row_top.append(InlineKeyboardButton(text="👤 Profil", url=f"tg://user?id={telegram_id}"))
    buttons.append(row_top)

    # Status boshqaruvi
    buttons.append([
        InlineKeyboardButton(text="📞 Bog'lanildi", callback_data=f"mgr_st:{telegram_id}:Bog'lanildi"),
        InlineKeyboardButton(text="📅 Sinov darsiga yozildi", callback_data=f"mgr_st:{telegram_id}:Sinov darsiga yozildi")
    ])
    buttons.append([
        InlineKeyboardButton(text="🎉 Guruhga qo'shildi", callback_data=f"mgr_st:{telegram_id}:Guruhga qo'shildi"),
        InlineKeyboardButton(text="❌ Rad etildi", callback_data=f"mgr_st:{telegram_id}:Rad etildi")
    ])
    buttons.append([
        InlineKeyboardButton(text="✍️ Izoh / Eslatma qo'shish", callback_data=f"mgr_note:{telegram_id}")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

from config import WEBAPP_BASE_URL, ADMIN_TUNNEL_URL

def get_admin_panel_kb(user_id: int = 0) -> InlineKeyboardMarkup:
    """Rahbar va Admin boshqaruv paneli (Web App bilan)"""
    admin_webapp_url = f"{ADMIN_TUNNEL_URL}/admin?uid={user_id}"

    buttons = [
        [
            InlineKeyboardButton(text="💻 Admin Panelga Kirish (Chrome / Sayt)", url=admin_webapp_url)
        ],
        [
            InlineKeyboardButton(text="📊 Statistika", callback_data="adm_stats"),
            InlineKeyboardButton(text="📥 Excel Bazani Yuklash", callback_data="adm_export")
        ],
        [
            InlineKeyboardButton(text="👤 Adminlarni Boshqarish", callback_data="adm_manage_admins"),
            InlineKeyboardButton(text="📢 Ommaviy Xabarnoma", callback_data="adm_broadcast")
        ],
        [
            InlineKeyboardButton(text="🎪 Yangi Tadbir Qo'shish", callback_data="adm_add_event"),
            InlineKeyboardButton(text="🔄 Yangilash", callback_data="adm_refresh")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_users_kb(admins: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Adminlar ro'yxati va o'chirish tugmalari"""
    buttons = [
        [InlineKeyboardButton(text="➕ Yangi Admin Qo'shish", callback_data="adm_add_admin")]
    ]
    for a in admins:
        tid = a["telegram_id"]
        name = a.get("full_name", str(tid))
        buttons.append([
            InlineKeyboardButton(text=f"❌ O'chirish: {name}", callback_data=f"adm_del_admin:{tid}")
        ])
    buttons.append([InlineKeyboardButton(text="🔙 Asosiy Admin Panel", callback_data="adm_refresh")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_broadcast_target_kb() -> InlineKeyboardMarkup:
    """Xabar kimga va qanday yuborilishini tanlash"""
    buttons = [
        [
            InlineKeyboardButton(text="📢 Ommaviy (Barcha foydalanuvchilar va guruhlarga)", callback_data="bc_tgt:all")
        ],
        [
            InlineKeyboardButton(text="👤 Bitta foydalanuvchiga (Telegram ID orqali)", callback_data="bc_tgt:single_user")
        ],
        [
            InlineKeyboardButton(text="🎯 Faqat A1 - A2", callback_data="bc_tgt:beginner"),
            InlineKeyboardButton(text="🎯 Faqat B1 - B2", callback_data="bc_tgt:intermediate")
        ],
        [
            InlineKeyboardButton(text="⏳ Faqat Yangi Lidlar", callback_data="bc_tgt:Yangi")
        ],
        [
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="bc_cancel")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_event_action_kb(event_id: int) -> InlineKeyboardMarkup:
    """Ochiq darsga ro'yxatdan o'tish tugmasi"""
    buttons = [
        [InlineKeyboardButton(text="🎟 Joy band qilish", callback_data=f"reg_ev:{event_id}")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
