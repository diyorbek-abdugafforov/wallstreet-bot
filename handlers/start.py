from aiogram import Router, types
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from database import Database
from config import ADMINS, CENTER_NAME
from keyboards.default_kb import get_main_menu_kb, get_contact_kb
from handlers.states import RegistrationStates

router = Router()

@router.message(CommandStart())
async def cmd_start(message: types.Message, command: CommandObject, state: FSMContext, db: Database):
    user_id = message.from_user.id
    username = message.from_user.username
    is_admin = await db.is_admin(user_id)

    # Deep link orqali reklama manbasini aniqlash (masalan /start insta_reels)
    utm_source = "organic"
    if command.args:
        utm_source = command.args.strip()

    # O'quvchini bazaga saqlash yoki tekshirish
    await db.add_or_update_student(
        telegram_id=user_id,
        username=username,
        utm_source=utm_source
    )

    student = await db.get_student(user_id)

    # Agar o'quvchining telefon raqami yo'q bo'lsa - ro'yxatdan o'tishni boshlaymiz
    if not student or not student.get("phone"):
        await state.set_state(RegistrationStates.waiting_for_first_name)
        welcome_text = (
            f"Assalomu alaykum, <b>{message.from_user.first_name}</b>! 😊\n\n"
            f"<b>{CENTER_NAME}</b> o'quv markazining qabul bo'limiga (reception) xush kelibsiz!\n"
            f"Men markazning raqamli administratoriman.\n\n"
            f"Sizga to'g'ri kurs va guruh tanlashda yordam beraman. Bot orqali:\n"
            f"🎯 <b>3 daqiqada</b> bilim darajangizni bepul aniqlashingiz;\n"
            f"🎁 <b>1-bepul sinov darsi</b> va maxsus chegirma kuponini yutib olishingiz;\n"
            f"🕒 O'zingizga qulay dars vaqtlarini tanlashingiz mumkin.\n\n"
            f"<i>Tanishib olishimiz uchun, 1-qadam:</i>\n"
            f"Iltimos, <b>Ismingizni</b> yozing: 👇"
        )
        await message.answer(welcome_text, parse_mode="HTML")
    else:
        # Ro'yxatdan o'tgan foydalanuvchi
        text = (
            f"Assalomu alaykum, <b>{student.get('full_name', message.from_user.first_name)}</b>! 👋\n\n"
            f"<b>{CENTER_NAME}</b> botiga xush kelibsiz. O'zingizga kerakli bo'limni tanlang:"
        )
        await message.answer(
            text,
            reply_markup=get_main_menu_kb(is_admin=is_admin),
            parse_mode="HTML"
        )
