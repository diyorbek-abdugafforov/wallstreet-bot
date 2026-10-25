from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from database import Database
from config import (
    PLACEMENT_TEST_QUESTIONS,
    GROUP_SCHEDULES,
    TRIAL_COUPON_CODE,
    MANAGER_GROUP_ID,
    ADMINS,
    CENTER_NAME
)
from keyboards.inline_kb import (
    get_test_question_kb,
    get_schedules_kb,
    get_manager_lead_kb
)

router = Router()

@router.message(F.text == "📝 Darajani aniqlash testi (Placement Test)")
async def start_quiz_menu(message: types.Message, state: FSMContext, db: Database):
    """Menyudan testni qayta boshlash"""
    student = await db.get_student(message.from_user.id)
    if not student or not student.get("phone"):
        await message.answer("Avval ro'yxatdan o'tishingiz kerak. /start buyrug'ini bosing.")
        return

    # Savollarni boshlash
    await state.update_data(score=0, current_idx=0)
    first_q = PLACEMENT_TEST_QUESTIONS[0]
    await message.answer(
        f"🎯 <b>Bilim darajangizni aniqlash testi!</b>\n\n"
        f"Test {len(PLACEMENT_TEST_QUESTIONS)} ta savoldan iborat.\n\n"
        f"👉 <b>1-savol:</b>\n"
        f"<b>{first_q['question']}</b>",
        reply_markup=get_test_question_kb(first_q["id"], first_q["options"]),
        parse_mode="HTML"
    )

@router.callback_query(F.data == "start_bot_quiz")
async def start_quiz_callback(call: types.CallbackQuery, state: FSMContext, db: Database):
    await state.update_data(score=0, current_idx=0)
    first_q = PLACEMENT_TEST_QUESTIONS[0]
    await call.message.edit_text(
        f"🎯 <b>Bilim darajangizni aniqlash testi!</b>\n\n"
        f"Test {len(PLACEMENT_TEST_QUESTIONS)} ta savoldan iborat.\n\n"
        f"👉 <b>1-savol:</b>\n"
        f"<b>{first_q['question']}</b>",
        reply_markup=get_test_question_kb(first_q["id"], first_q["options"]),
        parse_mode="HTML"
    )
    await call.answer()

@router.callback_query(F.data.startswith("test_ans:"))
async def handle_test_answer(call: types.CallbackQuery, state: FSMContext, db: Database, bot: Bot):
    _, q_id_str, opt_idx_str = call.data.split(":")
    q_id = int(q_id_str)
    chosen_opt = int(opt_idx_str)

    data = await state.get_data()
    score = data.get("score", 0)

    # Savolni topish
    curr_q = next((q for q in PLACEMENT_TEST_QUESTIONS if q["id"] == q_id), None)
    if curr_q:
        if chosen_opt == curr_q["answer"]:
            score += 1

    await state.update_data(score=score)

    # Keyingi savolni aniqlash
    next_q = next((q for q in PLACEMENT_TEST_QUESTIONS if q["id"] > q_id), None)

    if next_q:
        await call.message.edit_text(
            f"👉 <b>{next_q['id']}-savol:</b>\n"
            f"<b>{next_q['question']}</b>",
            reply_markup=get_test_question_kb(next_q["id"], next_q["options"]),
            parse_mode="HTML"
        )
    else:
        # Barcha savollar tugadi - Test Yakunlandi
        total_questions = len(PLACEMENT_TEST_QUESTIONS)
        
        # Darajani belgilash
        if score <= 2:
            level = "A1 (Beginner)"
        elif score <= 4:
            level = "A2 (Elementary / Pre-Int)"
        elif score == 5:
            level = "B1 (Intermediate)"
        else:
            level = "B2 (Upper-Intermediate)"

        coupon = TRIAL_COUPON_CODE
        # Natijani bazaga yozish
        await db.set_test_result(
            telegram_id=call.from_user.id,
            score=score,
            level=level,
            coupon=coupon
        )

        result_text = (
            f"🎊 <b>Test yakunlandi! Natijangiz:</b>\n\n"
            f"📊 <b>To'plagan balingiz:</b> {score} / {total_questions}\n"
            f"🎯 <b>Aniqlangan darajangiz:</b> <b>{level}</b>\n\n"
            f"🎁 <b>Maxsus sovg'angiz:</b>\n"
            f"Sizga <b>1-bepul sinov darsi</b> va 10% chegirma kuponi taqdim etildi!\n"
            f"🏷 Kupon kodi: <code>{coupon}</code>\n\n"
            f"👇 <i>Darsga qatnashish uchun o'zingizga qulay vaqtni tanlang:</i>"
        )

        await call.message.edit_text(
            result_text,
            reply_markup=get_schedules_kb(GROUP_SCHEDULES),
            parse_mode="HTML"
        )

@router.callback_query(F.data.startswith("sel_sched:"))
async def handle_schedule_choice(call: types.CallbackQuery, db: Database, bot: Bot):
    _, idx_str = call.data.split(":")
    sched_idx = int(idx_str)
    selected_time = GROUP_SCHEDULES[sched_idx]

    user_id = call.from_user.id
    await db.set_preferred_schedule(telegram_id=user_id, schedule=selected_time)

    # O'quvchiga xushxabar
    await call.message.edit_text(
        f"✅ <b>Arizangiz qabul qilindi!</b>\n\n"
        f"🕒 <b>Tanlangan guruh vaqti:</b> {selected_time}\n"
        f"🏢 <b>O'quv markaz:</b> {CENTER_NAME}\n\n"
        f"⚡ <i>Menejerimiz 15 daqiqa ichida siz bilan bog'lanib, bepul sinov darsi kunini tasdiqlaydi!</i>",
        parse_mode="HTML"
    )

    # RECEPTION / MENEJERLAR GURUHIGA BILDIRISHTOMA YUBORISH
    student = await db.get_student(user_id)
    if student:
        full_name = student.get("full_name") or call.from_user.full_name
        phone = student.get("phone") or "Ko'rsatilmagan"
        username = f"@{call.from_user.username}" if call.from_user.username else "Mavjud emas"
        utm_source = student.get("utm_source", "organic")
        level = student.get("level", "Aniqlanmagan")
        score = student.get("test_score", 0)
        coupon = student.get("coupon_code", TRIAL_COUPON_CODE)

        lead_message = (
            f"🔥 <b>YANGI LID (Murojaat & Sinov darsi so'rovi)</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>O'quvchi:</b> {full_name}\n"
            f"📱 <b>Telefon:</b> {phone}\n"
            f"💬 <b>Telegram:</b> {username} (ID: <code>{user_id}</code>)\n"
            f"🎯 <b>Darajasi:</b> {level} ({score}/{len(PLACEMENT_TEST_QUESTIONS)} ball)\n"
            f"🕒 <b>Qulay vaqt:</b> {selected_time}\n"
            f"🏷 <b>Kupon:</b> <code>{coupon}</code>\n"
            f"⚡ <b>Reklama manbasi:</b> <code>{utm_source}</code>\n"
            f"📌 <b>Status:</b> ⏳ Yangi\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<i>Reglament: Menejer 15 daqiqa ichida qo'ng'iroq qilishi lozim!</i>"
        )

        kb = get_manager_lead_kb(telegram_id=user_id, phone=phone)

        # 1. Menejerlar guruhiga yuborish
        sent_to_group = False
        if MANAGER_GROUP_ID != 0:
            try:
                await bot.send_message(
                    chat_id=MANAGER_GROUP_ID,
                    text=lead_message,
                    reply_markup=kb,
                    parse_mode="HTML"
                )
                sent_to_group = True
            except Exception as e:
                print(f"Menejer guruhiga yuborib bo'lmadi: {e}")

        # 2. Agar guruh sozlanmagan bo'lsa yoki xatolik bo'lsa, barcha adminlarga yuborish
        if not sent_to_group:
            for admin_id in ADMINS:
                if admin_id != 0:
                    try:
                        await bot.send_message(
                            chat_id=admin_id,
                            text=lead_message,
                            reply_markup=kb,
                            parse_mode="HTML"
                        )
                    except Exception as e:
                        print(f"Adminga yuborib bo'lmadi: {e}")
