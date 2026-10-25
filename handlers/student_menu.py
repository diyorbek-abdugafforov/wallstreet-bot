from aiogram import Router, types, F, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.fsm.context import FSMContext
from database import Database
from config import (
    CENTER_NAME,
    WEBAPP_BASE_URL,
    MANAGER_GROUP_ID,
    ADMINS
)
from data_manager import get_settings, get_courses, get_schedules, get_results
from keyboards.inline_kb import get_event_action_kb
from keyboards.default_kb import get_cancel_kb, get_main_menu_kb
from handlers.states import PromocodeStates

router = Router()

@router.message(F.text == "📞 Reception telefon raqami")
async def show_reception_contact(message: types.Message):
    """Reception telefon raqami va manzili"""
    settings = get_settings()
    phone1 = settings.get("reception_phone", "+998 71 200 77 77")
    phone2 = settings.get("reception_additional_phone", "+998 90 123 45 67")
    address = settings.get("location_address", "Toshkent shahri, Bunyodkor ko'chasi")
    work_hours = settings.get("work_hours", "08:30 - 20:30")

    clean_phone = phone1.replace("+", "").replace(" ", "").replace("-", "")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📞 Receptionga qo'ng'iroq", url=f"tel:+{clean_phone}")],
        [InlineKeyboardButton(text="💬 Administratorga yozish", url="https://t.me/edubot_admin")]
    ])

    text = (
        f"🏢 <b>{settings.get('center_name', CENTER_NAME)} Reception</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📞 <b>Asosiy telefon:</b> {phone1}\n"
        f"📱 <b>Qo'shimcha raqam:</b> {phone2}\n"
        f"⏰ <b>Ish vaqti:</b> {work_hours}\n"
        f"📍 <b>Manzil:</b> {address}\n\n"
        f"<i>Savollaringiz bo'lsa, xodimlarimiz doim yordam berishga tayyor!</i>"
    )
    await message.answer(text, reply_markup=kb, parse_mode="HTML")

@router.message(F.text == "🎁 Promokod")
async def ask_promocode(message: types.Message, state: FSMContext):
    """Foydalanuvchidan maxsus promokodni so'rash (barcha promokodlar ommaga oshkor qilinmaydi)"""
    await state.set_state(PromocodeStates.waiting_for_code)
    text = (
        f"🎁 <b>{CENTER_NAME} Maxsus Chegirma Promokodi</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"Agar sizda markazimiz tomonidan berilgan maxsus <b>promokod</b> bo'lsa, uni yozib yuboring:\n\n"
        f"<i>(Masalan: flayer, do'stingiz taklifi yoki aksiya orqali olingan kod)</i>"
    )
    await message.answer(text, reply_markup=get_cancel_kb(), parse_mode="HTML")

@router.message(PromocodeStates.waiting_for_code, F.text == "❌ Bekor qilish")
async def cancel_promocode_input(message: types.Message, state: FSMContext, is_admin: bool = False):
    await state.clear()
    await message.answer("Bosh menyuga qaytildi:", reply_markup=get_main_menu_kb(message.from_user.id, is_admin))

@router.message(PromocodeStates.waiting_for_code)
async def process_promocode_input(message: types.Message, state: FSMContext, db: Database, is_admin: bool = False):
    input_code = message.text.strip().upper()
    settings = get_settings()
    promos = settings.get("promocodes", [])

    matched = None
    for p in promos:
        if p.get("code", "").upper() == input_code and p.get("is_active", True):
            matched = p
            break

    await state.clear()

    if matched:
        text = (
            f"🎉 <b>Tabriklaymiz! Promokod muvaffaqiyatli faollashtirildi!</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🏷 <b>Kupon:</b> <code>{matched['code']}</code>\n"
            f"✨ <b>Chegirma:</b> {matched.get('discount', 'Chegirma')}\n"
            f"ℹ️ {matched.get('description', '')}\n\n"
            f"✅ <i>Ushbu chegirma profilingizga biriktirildi. Markazimizga kelganingizda yoki reception bilan bog'langanda ushbu kodni eslatib o'tishingiz mumkin!</i>"
        )
        await message.answer(text, reply_markup=get_main_menu_kb(message.from_user.id, is_admin), parse_mode="HTML")
    else:
        text = (
            f"❌ <b>Bunday promokod topilmadi yoki muddati o'tgan!</b>\n\n"
            f"Iltimos, promokodni to'g'ri yozganingizni tekshirib ko'ring yoki ma'lumot olish uchun reception xodimiga murojaat qiling."
        )
        await message.answer(text, reply_markup=get_main_menu_kb(message.from_user.id, is_admin), parse_mode="HTML")

def get_page_url(page_name: str, uid: int = 0) -> str:
    if "netlify.app" in WEBAPP_BASE_URL:
        if page_name == "bonus-test":
            return f"{WEBAPP_BASE_URL}/bonus_test.html?uid={uid}"
        elif page_name in ["courses", "schedule", "results", "reception", "test"]:
            return f"{WEBAPP_BASE_URL}/?tab={page_name}&uid={uid}"
        else:
            return f"{WEBAPP_BASE_URL}/?uid={uid}"
    else:
        if page_name in ["courses", "schedule", "results", "reception", "test"]:
            return f"{WEBAPP_BASE_URL}/webapp/portal?tab={page_name}&uid={uid}"
        elif page_name == "bonus-test":
            return f"{WEBAPP_BASE_URL}/webapp/bonus-test?uid={uid}"
        else:
            return f"{WEBAPP_BASE_URL}/webapp/portal?uid={uid}"

# --- DARS VAQTLARI ---
@router.message(F.text == "🕒 Dars vaqtlari")
async def open_schedule_webapp(message: types.Message):
    is_https = WEBAPP_BASE_URL.startswith("https://")
    if is_https:
        url = get_page_url("schedule")
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🕒 Dars jadvalini ochish (Web App)", web_app=WebAppInfo(url=url))]
        ])
        await message.answer("Quyidagi tugma orqali dars vaqtlari va jadvallarini ko'rishingiz mumkin:", reply_markup=kb)
    else:
        schedules = get_schedules()
        text = f"🕒 <b>{CENTER_NAME} Dars Jadvallari:</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        for s in schedules:
            text += (
                f"📌 <b>{s['type']} ({s['level']})</b>\n"
                f"📅 {s['days']}\n"
                f"⏰ {s['time']}\n\n"
            )
        await message.answer(text, parse_mode="HTML")

# --- KURS NARXLARI ---
@router.message(F.text == "📚 Kurs narxlari")
async def open_courses_webapp(message: types.Message):
    is_https = WEBAPP_BASE_URL.startswith("https://")
    if is_https:
        url = get_page_url("courses")
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📚 Kurslar va narxlar (Web App)", web_app=WebAppInfo(url=url))]
        ])
        await message.answer("Barcha kurslar va ularning oylik narxlari:", reply_markup=kb)
    else:
        courses = get_courses()
        text = f"📚 <b>{CENTER_NAME} Kurslar va Narxlar:</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        for c in courses:
            text += (
                f"<b>{c['name']}</b> ({c.get('badge', '')})\n"
                f"⏳ Davomiyligi: {c['duration']}\n"
                f"💰 Narxi: <b>{c['price']}</b>\n"
                f"ℹ️ {c['description']}\n\n"
            )
        text += "<i>1-sinov darsi barcha kurslar uchun mutlaqo bepul!</i>"
        await message.answer(text, parse_mode="HTML")

# --- WALL STREET NATIJALARI ---
@router.message(F.text == "🏆 Wall Street natijalari")
async def open_results_webapp(message: types.Message):
    is_https = WEBAPP_BASE_URL.startswith("https://")
    if is_https:
        url = get_page_url("results")
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🏆 Natijalar va sertifikatlar (Web App)", web_app=WebAppInfo(url=url))]
        ])
        await message.answer("Wall Street o'quvchilarining eng yuqori IELTS va CEFR natijalari:", reply_markup=kb)
    else:
        results = get_results()
        text = f"🏆 <b>Wall Street O'quvchilar Natijalari:</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        for r in results:
            text += (
                f"🎓 <b>{r['student_name']}</b> — <b>{r['score']}</b>\n"
                f"📊 {r['details']}\n"
                f"💬 {r['description']}\n\n"
            )
        await message.answer(text, parse_mode="HTML")

# --- BONUS TEST ---
@router.message(F.text == "🎯 Bonus test")
async def open_bonus_test_webapp(message: types.Message):
    is_https = WEBAPP_BASE_URL.startswith("https://")
    if is_https:
        url = get_page_url("bonus-test", uid=message.from_user.id)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎯 Bonus testni boshlash (Web App)", web_app=WebAppInfo(url=url))]
        ])
        await message.answer("Bilimingizni sinab ko'rish uchun bonus test:", reply_markup=kb)
    else:
        from config import PLACEMENT_TEST_QUESTIONS
        from keyboards.inline_kb import get_test_question_kb
        first_q = PLACEMENT_TEST_QUESTIONS[0]
        await message.answer(
            f"🎯 <b>Bonus mashg'ulot savoli:</b>\n\n<b>{first_q['question']}</b>",
            reply_markup=get_test_question_kb(first_q["id"], first_q["options"]),
            parse_mode="HTML"
        )

# --- YAGONA WEB APP PORTALI (BARCHA BO'LIMLAR BIR JOYDA) ---
@router.message(F.text == "📱 Wall Street Web App (Barcha bo'limlar)")
async def open_main_portal(message: types.Message):
    is_https = WEBAPP_BASE_URL.startswith("https://")
    portal_url = f"{WEBAPP_BASE_URL}/?uid={message.from_user.id}"

    if is_https:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📱 Web App Portalini Ochish", web_app=WebAppInfo(url=portal_url))]
        ])
        await message.answer(
            "🌟 <b>Wall Street Education Barcha Bo'limlari</b>\n\n"
            "Ushbu yagona Web App orqali:\n"
            "• 🎯 Darajani aniqlash testi\n"
            "• 📚 Kurslar va narxlar (batafsil syllabus bilan)\n"
            "• 🕒 Dars jadvallari va guruhlar\n"
            "• 🏆 O'quvchilar natijalari va video isbotlar\n"
            "• 📞 Reception va aloqa markazi\n\n"
            "Quyidagi tugma orqali portalni oching: 👇",
            reply_markup=kb,
            parse_mode="HTML"
        )
    else:
        await message.answer("Web App manzili: " + portal_url)
