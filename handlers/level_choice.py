from aiogram import Router, types, F, Bot
from database import Database
from config import MANAGER_GROUP_ID, ADMINS, CENTER_NAME
from keyboards.inline_kb import get_manager_lead_kb

router = Router()

@router.callback_query(F.data.startswith("choose_lvl:"))
async def handle_direct_level_choice(call: types.CallbackQuery, db: Database, bot: Bot):
    lvl = call.data.split(":")[1]
    user_id = call.from_user.id

    # Bazada yangilash
    await db.set_test_result(telegram_id=user_id, score=0, level=lvl, coupon="WALLSTREET10")
    student = await db.get_student(user_id)

    full_name = student.get("full_name") if student else call.from_user.full_name
    phone = student.get("phone") if student else ""
    username = f"@{call.from_user.username}" if call.from_user.username else "Mavjud emas"
    utm_source = student.get("utm_source", "organic") if student else "organic"

    # O'quvchiga javob
    await call.message.edit_text(
        f"✅ <b>Arizangiz muvaffaqiyatli qabul qilindi!</b>\n\n"
        f"👤 <b>O'quvchi:</b> {full_name}\n"
        f"🎯 <b>Tanlangan daraja:</b> <b>{lvl}</b>\n"
        f"🏢 <b>Markaz:</b> {CENTER_NAME}\n\n"
        f"⚡ <i>Tez orada reception adminlari siz bilan bog'lanib, bepul sinov darsi va dars jadvallari haqida ma'lumot berishadi.</i>\n\n"
        f"Quyidagi menyu orqali dars vaqtlari, narxlar va natijalar bilan tanishishingiz mumkin! 👇",
        parse_mode="HTML"
    )

    # Reception / Menejer guruhiga bildirishnoma yuborish
    lead_text = (
        f"🔥 <b>YANGI ARIZA (O'quvchi daraja tanladi)</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>O'quvchi:</b> {full_name}\n"
        f"📱 <b>Telefon:</b> {phone}\n"
        f"💬 <b>Telegram:</b> {username} (ID: <code>{user_id}</code>)\n"
        f"🎯 <b>Tanlagan darajasi:</b> <b>{lvl}</b>\n"
        f"⚡ <b>Reklama manbasi:</b> <code>{utm_source}</code>\n"
        f"📌 <b>Status:</b> ⏳ Yangi\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<i>Reglament: Menejer 15 daqiqa ichida qo'ng'iroq qilishi lozim!</i>"
    )

    kb = get_manager_lead_kb(telegram_id=user_id, phone=phone)

    # Guruhga yoki adminga jo'natish
    sent = False
    if MANAGER_GROUP_ID != 0:
        try:
            await bot.send_message(chat_id=MANAGER_GROUP_ID, text=lead_text, reply_markup=kb, parse_mode="HTML")
            sent = True
        except Exception as e:
            print(f"Guruhga xabar yuborishda xato: {e}")

    if not sent:
        for admin_id in ADMINS:
            if admin_id != 0:
                try:
                    await bot.send_message(chat_id=admin_id, text=lead_text, reply_markup=kb, parse_mode="HTML")
                except Exception:
                    pass

    await call.answer("Darajangiz qabul qilindi!")
