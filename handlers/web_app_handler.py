import json
import logging
from aiogram import Router, types, F, Bot
from database import Database
from config import MANAGER_GROUP_ID, ADMINS, CENTER_NAME
from keyboards.inline_kb import get_manager_lead_kb
from data_manager import get_schedules, write_json
from services.test_template import sync_schedules_to_html

router = Router()
logger = logging.getLogger(__name__)

@router.message(F.web_app_data)
async def handle_web_app_submission(message: types.Message, db: Database, bot: Bot):
    """
    Telegram Web App orqali yuborilgan ma'lumotni qabul qilish
    (Netlify yoki istalgan HTTPS WebApp dan keladi)
    """
    try:
        raw_data = message.web_app_data.data
        data = json.loads(raw_data)
    except Exception as e:
        logger.error(f"Web App ma'lumotini o'qishda xato: {e}")
        return

    user_id = message.from_user.id
    action = data.get("action", "submit_level_test")
    coupon = "WALLSTREET10"

    # Agar o'quvchi ism va telefonini kiritgan/tahrirlagan bo'lsa
    if data.get("full_name") and data.get("phone"):
        await db.set_student_contact(user_id, data["full_name"], data["phone"])

    if action == "enroll_schedule":
        schedule_id = data.get("schedule_id", 0)
        group_info = data.get("group_info", "Guruh")
        schedules = get_schedules()
        for s in schedules:
            if s.get("id") == schedule_id:
                if s.get("current_students", 0) < s.get("max_students", 12):
                    s["current_students"] = s.get("current_students", 0) + 1
                break
        write_json("schedules.json", schedules)
        sync_schedules_to_html(schedules)

        student = await db.get_student(user_id)
        full_name = data.get("full_name") or (student.get("full_name") if student else message.from_user.full_name)
        phone = data.get("phone") or (student.get("phone") if student else "Kiritilmagan")
        username = f"@{message.from_user.username}" if message.from_user.username else "Mavjud emas"

        await message.answer(
            f"✅ <b>Guruhga yozilish bo'yicha arizangiz qabul qilindi!</b>\n\n"
            f"👤 <b>O'quvchi:</b> {full_name}\n"
            f"👥 <b>Guruh:</b> {group_info}\n\n"
            f"⚡ <i>Menejerlarimiz 15 daqiqa ichida siz bilan bog'lanib, o'rningizni tasdiqlashadi.</i>",
            parse_mode="HTML"
        )
        lead_msg = (
            f"🔥 <b>YANGI ARIZA (Guruhga qo'shilish)</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>O'quvchi:</b> {full_name}\n"
            f"📱 <b>Telefon:</b> {phone}\n"
            f"💬 <b>Telegram:</b> {username} (ID: <code>{user_id}</code>)\n"
            f"👥 <b>Guruh:</b> {group_info}\n"
            f"━━━━━━━━━━━━━━━━━━"
        )
        kb = get_manager_lead_kb(telegram_id=user_id, phone=phone)
        if MANAGER_GROUP_ID != 0:
            try:
                await bot.send_message(chat_id=MANAGER_GROUP_ID, text=lead_msg, reply_markup=kb, parse_mode="HTML")
            except Exception:
                pass
        return

    if action == "choose_level_or_course":
        course_name = data.get("course_name", "Kurs")
        await db.update_student_status(user_id, status="Yangi", level=course_name)
        student = await db.get_student(user_id)
        full_name = data.get("full_name") or (student.get("full_name") if student else message.from_user.full_name)
        phone = data.get("phone") or (student.get("phone") if student else "Kiritilmagan")
        username = f"@{message.from_user.username}" if message.from_user.username else "Mavjud emas"
        utm = student.get("utm_source", "organic") if student else "organic"

        reply_text = (
            f"✅ <b>Arizangiz qabul qilindi!</b>\n\n"
            f"👤 <b>O'quvchi:</b> {full_name}\n"
            f"📚 <b>Tanlangan yo'nalish:</b> <b>{course_name}</b>\n"
            f"🎁 <b>Kuponingiz:</b> <code>{coupon}</code> (1-sinov darsi bepul!)\n\n"
            f"⚡ <i>Reception xodimlarimiz siz bilan tez orada bog'lanishadi va guruh dars vaqtlarini tasdiqlashadi.</i>"
        )
        await message.answer(reply_text, parse_mode="HTML")

        lead_msg = (
            f"🔥 <b>YANGI LID (Web App Kurs Tanlash orqali)</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>O'quvchi:</b> {full_name}\n"
            f"📱 <b>Telefon:</b> {phone}\n"
            f"💬 <b>Telegram:</b> {username} (ID: <code>{user_id}</code>)\n"
            f"📚 <b>Tanlangan kurs:</b> <b>{course_name}</b>\n"
            f"🏷 <b>Kupon:</b> <code>{coupon}</code>\n"
            f"⚡ <b>Reklama manbasi:</b> <code>{utm}</code>\n"
            f"📌 <b>Status:</b> ⏳ Yangi\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<i>Reglament: Menejer 15 daqiqa ichida qo'ng'iroq qilishi lozim!</i>"
        )
        kb = get_manager_lead_kb(telegram_id=user_id, phone=phone)
        sent = False
        if MANAGER_GROUP_ID != 0:
            try:
                await bot.send_message(chat_id=MANAGER_GROUP_ID, text=lead_msg, reply_markup=kb, parse_mode="HTML")
                sent = True
            except Exception as e:
                logger.warning(f"Menejer guruhiga yuborilmadi: {e}")
        if not sent:
            for aid in ADMINS:
                if aid != 0:
                    try:
                        await bot.send_message(chat_id=aid, text=lead_msg, reply_markup=kb, parse_mode="HTML")
                    except Exception:
                        pass
        return

    level = data.get("level", "Aniqlanmagan")
    score = data.get("score", 0)
    total = data.get("total", 6)

    # 1. Bazada yangilash va urinishni sarflash
    await db.set_test_result(telegram_id=user_id, score=score, level=level, coupon=coupon)
    await db.increment_student_attempt(user_id)
    await db.set_application_submitted(user_id)
    student = await db.get_student(user_id)

    full_name = data.get("full_name") or (student.get("full_name") if student else message.from_user.full_name)
    phone = data.get("phone") or (student.get("phone") if student else "Kiritilmagan")
    username = f"@{message.from_user.username}" if message.from_user.username else "Mavjud emas"
    utm = student.get("utm_source", "organic") if student else "organic"

    # 2. O'quvchiga tasdiq xabari
    reply_text = (
        f"✅ <b>Arizangiz muvaffaqiyatli qoldirildi!</b>\n\n"
        f"👤 <b>O'quvchi:</b> {full_name}\n"
        f"🎯 <b>Aniqlangan darajangiz:</b> <b>{level}</b>\n"
        f"📊 <b>Natijangiz:</b> {score} / {total} ball\n"
        f"🎁 <b>Kuponingiz:</b> <code>{coupon}</code> (1-sinov darsi bepul!)\n\n"
        f"⚡ <i>Tez orada reception adminlari siz bilan bog'lanadi va mos dars vaqtlari haqida xabar berishadi.</i>"
    )
    await message.answer(reply_text, parse_mode="HTML")

    # 3. Reception / Menejerlar guruhiga tayyor lid xabarini tashlash
    lead_msg = (
        f"🔥 <b>YANGI LID (Web App Online Test orqali)</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>O'quvchi:</b> {full_name}\n"
        f"📱 <b>Telefon:</b> {phone}\n"
        f"💬 <b>Telegram:</b> {username} (ID: <code>{user_id}</code>)\n"
        f"🎯 <b>Aniqlangan daraja:</b> <b>{level}</b> ({score}/{total} ball)\n"
        f"🏷 <b>Kupon:</b> <code>{coupon}</code>\n"
        f"⚡ <b>Reklama manbasi:</b> <code>{utm}</code>\n"
        f"📌 <b>Status:</b> ⏳ Yangi\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"<i>Reglament: Menejer 15 daqiqa ichida qo'ng'iroq qilishi lozim!</i>"
    )
    kb = get_manager_lead_kb(telegram_id=user_id, phone=phone)

    sent = False
    if MANAGER_GROUP_ID != 0:
        try:
            await bot.send_message(chat_id=MANAGER_GROUP_ID, text=lead_msg, reply_markup=kb, parse_mode="HTML")
            sent = True
        except Exception as e:
            logger.warning(f"Menejer guruhiga yuborilmadi: {e}")

    if not sent:
        for aid in ADMINS:
            if aid != 0:
                try:
                    await bot.send_message(chat_id=aid, text=lead_msg, reply_markup=kb, parse_mode="HTML")
                except Exception:
                    pass

