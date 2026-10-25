from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from database import Database
from keyboards.inline_kb import get_manager_lead_kb
from handlers.states import ManagerActionStates
from services.scheduler import send_trial_confirmation_to_student
from datetime import datetime

router = Router()

@router.callback_query(F.data.startswith("mgr_st:"))
async def handle_manager_status_change(call: types.CallbackQuery, state: FSMContext, db: Database, bot: Bot):
    """
    Reception/Menejer lid statusini o'zgartiradi
    """
    parts = call.data.split(":")
    student_id = int(parts[1])
    new_status = parts[2]
    manager_name = call.from_user.full_name or call.from_user.username or f"ID:{call.from_user.id}"

    if new_status == "Sinov darsiga yozildi":
        # Sinov darsi sanasini so'rash
        await state.update_data(target_student_id=student_id, message_id=call.message.message_id, chat_id=call.message.chat.id)
        await state.set_state(ManagerActionStates.waiting_for_trial_date)
        await call.message.reply(
            f"📅 <b>Sinov darsi sanasi va vaqtini kiriting</b> (masalan: <i>Ertaga soat 15:00 da</i> yoki <i>26-oktyabr 18:30</i>):",
            parse_mode="HTML"
        )
        await call.answer()
        return

    # Bazada statusni yangilash
    await db.update_status(telegram_id=student_id, status=new_status, manager_id=call.from_user.id)
    
    # Lid kartasi matnini yangilash
    current_text = call.message.html_text
    now_str = datetime.now().strftime("%H:%M, %d.%m")
    
    # Eski status satrini almashtirish
    lines = current_text.split("\n")
    new_lines = []
    for line in lines:
        if "📌 <b>Status:</b>" in line or "📌 Status:" in line:
            new_lines.append(f"📌 <b>Status:</b> {new_status} (✅ {manager_name} tomonidan, {now_str})")
        else:
            new_lines.append(line)
            
    updated_text = "\n".join(new_lines)
    
    student = await db.get_student(student_id)
    phone = student.get("phone", "") if student else ""

    try:
        await call.message.edit_text(
            updated_text,
            reply_markup=get_manager_lead_kb(telegram_id=student_id, phone=phone),
            parse_mode="HTML"
        )
    except Exception:
        pass

    await call.answer(f"Status '{new_status}' ga o'zgartirildi!")

@router.message(ManagerActionStates.waiting_for_trial_date)
async def process_trial_date_input(message: types.Message, state: FSMContext, db: Database, bot: Bot):
    """Menejer kiritgan sinov darsi sanasini qabul qilish"""
    trial_date = message.text.strip()
    data = await state.get_data()
    student_id = data.get("target_student_id")
    msg_id = data.get("message_id")
    chat_id = data.get("chat_id")
    manager_name = message.from_user.full_name or message.from_user.username

    await db.set_trial_date(telegram_id=student_id, trial_date=trial_date)
    await state.clear()

    # O'quvchiga avtomatik tasdiqlash va eslatma xabarini jo'natish
    await send_trial_confirmation_to_student(bot=bot, telegram_id=student_id, trial_date=trial_date)

    await message.reply(
        f"✅ Sinov darsi belgilandi: <b>{trial_date}</b>\nO'quvchiga tasdiqlash xabari yuborildi!",
        parse_mode="HTML"
    )

    # Lid kartasini yangilash
    if chat_id and msg_id:
        try:
            student = await db.get_student(student_id)
            phone = student.get("phone", "") if student else ""
            status_text = f"Sinov darsiga yozildi: {trial_date} (👤 {manager_name})"
            
            # Yangi xabar yuborish yoki mavjudini yangilash
            now_str = datetime.now().strftime("%H:%M, %d.%m")
            info_update = (
                f"✅ <b>Sinov darsi muvaffaqiyatli belgilandi!</b>\n"
                f"👤 O'quvchi ID: <code>{student_id}</code>\n"
                f"📅 Belgilangan sana: <b>{trial_date}</b>\n"
                f"👨‍💼 Mas'ul menejer: {manager_name} ({now_str})"
            )
            await bot.send_message(chat_id=chat_id, text=info_update, parse_mode="HTML")
        except Exception as e:
            print(f"Lid kartasini yangilashda xato: {e}")

@router.callback_query(F.data.startswith("mgr_note:"))
async def handle_manager_note_request(call: types.CallbackQuery, state: FSMContext):
    """Menejerdan izoh so'rash"""
    student_id = int(call.data.split(":")[1])
    await state.update_data(target_student_id=student_id)
    await state.set_state(ManagerActionStates.waiting_for_note)
    await call.message.reply(
        f"✍️ <b>Ushbu o'quvchi bo'yicha izoh yoki eslatma yozing:</b>\n"
        f"(Masalan: <i>Telefon ko'tarmadi, soat 17:00 da qayta terish kerak</i>)",
        parse_mode="HTML"
    )
    await call.answer()

@router.message(ManagerActionStates.waiting_for_note)
async def process_note_input(message: types.Message, state: FSMContext, db: Database):
    note = message.text.strip()
    data = await state.get_data()
    student_id = data.get("target_student_id")
    await state.clear()

    await db.update_status(telegram_id=student_id, status="Izoh qoldirildi", note=note, manager_id=message.from_user.id)
    await message.reply(f"✅ Izoh saqlandi: <i>{note}</i>", parse_mode="HTML")
