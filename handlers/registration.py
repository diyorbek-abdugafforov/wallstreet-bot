import re
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from database import Database
from config import ADMINS
from keyboards.default_kb import get_contact_kb, get_main_menu_kb
from keyboards.inline_kb import get_test_question_kb
from config import PLACEMENT_TEST_QUESTIONS
from handlers.states import RegistrationStates

router = Router()

# 1-QADAM: Ismni qabul qilish
@router.message(RegistrationStates.waiting_for_first_name)
async def process_first_name(message: types.Message, state: FSMContext):
    first_name = message.text.strip() if message.text else ""
    if len(first_name) < 2 or any(char.isdigit() for char in first_name):
        await message.answer("Iltimos, ismingizni to'g'ri kiriting (faqat harflar bilan):")
        return

    await state.update_data(first_name=first_name)
    await state.set_state(RegistrationStates.waiting_for_last_name)

    await message.answer(
        f"Rahmat, <b>{first_name}</b>! 👍\n\n"
        f"2️⃣ Endi <b>Familiyangizni</b> yozing: 👇",
        parse_mode="HTML"
    )

# 2-QADAM: Familiyani qabul qilish
@router.message(RegistrationStates.waiting_for_last_name)
async def process_last_name(message: types.Message, state: FSMContext):
    last_name = message.text.strip() if message.text else ""
    if len(last_name) < 2 or any(char.isdigit() for char in last_name):
        await message.answer("Iltimos, familiyangizni to'g'ri kiriting (faqat harflar bilan):")
        return

    data = await state.get_data()
    first_name = data.get("first_name", "")
    full_name = f"{first_name} {last_name}".strip()
    await state.update_data(last_name=last_name, full_name=full_name)
    await state.set_state(RegistrationStates.waiting_for_phone)

    await message.answer(
        f"Ajoyib, <b>{full_name}</b>! 👏\n\n"
        f"3️⃣ Endi siz bilan bog'lanishimiz uchun <b>asosiy telefon raqamingizni</b> qoldiring:\n\n"
        f"📲 Agar hozirgi <b>Telegram raqamingiz asosiy bo'lsa</b>, pastdagi tugmani bosing;\n"
        f"✍️ Agar boshqa raqam bo'lsa, uni xabar sifatida yozib yuboring (masalan: <code>+998901234567</code>):",
        reply_markup=get_contact_kb(),
        parse_mode="HTML"
    )

# 3-QADAM: Telefon raqamini tugma orqali qabul qilish
@router.message(RegistrationStates.waiting_for_phone, F.contact)
async def process_phone_contact(message: types.Message, state: FSMContext, db: Database):
    contact = message.contact
    phone = contact.phone_number
    if not phone.startswith("+"):
        phone = "+" + phone

    await save_registration_and_offer_test(message, state, db, phone)

# 3-QADAM: Telefon raqamini matn (qo'lda) orqali qabul qilish
@router.message(RegistrationStates.waiting_for_phone, F.text)
async def process_phone_text(message: types.Message, state: FSMContext, db: Database):
    text = message.text.strip()
    # Telefon raqami formatini tozalash va tekshirish
    cleaned = re.sub(r"[^\d+]", "", text)
    if not (cleaned.startswith("+998") and len(cleaned) == 13) and not (len(cleaned) == 9 or len(cleaned) == 12):
        await message.answer(
            "⚠️ Noto'g'ri raqam formati!\n\n"
            "Iltimos, telefon raqamingizni <b>+998901234567</b> formatida yozing yoki pastdagi <b>'📲 Shu Telegram raqamimni yuborish'</b> tugmasini bosing:",
            reply_markup=get_contact_kb(),
            parse_mode="HTML"
        )
        return

    if not cleaned.startswith("+"):
        cleaned = "+" + cleaned

    await save_registration_and_offer_test(message, state, db, cleaned)

async def save_registration_and_offer_test(message: types.Message, state: FSMContext, db: Database, phone: str):
    user_id = message.from_user.id
    data = await state.get_data()
    full_name = data.get("full_name") or f"{data.get('first_name', '')} {data.get('last_name', '')}".strip() or message.from_user.full_name

    # Bazaga yozish
    await db.set_student_contact(telegram_id=user_id, full_name=full_name, phone=phone)
    await state.clear()

    is_admin = user_id in ADMINS

    # Asosiy menyu klaviaturasini faollashtirish
    await message.answer(
        "Xush kelibsiz! Asosiy boshqaruv menyusi faollashtirildi.",
        reply_markup=get_main_menu_kb(telegram_id=user_id, is_admin=is_admin)
    )

    from keyboards.inline_kb import get_level_selection_kb
    offer_text = (
        f"✅ <b>Ro'yxatdan o'tish muvaffaqiyatli yakunlandi!</b>\n\n"
        f"👤 <b>O'quvchi:</b> {full_name}\n"
        f"📱 <b>Telefon:</b> {phone}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📊 <b>Iltimos, o'z bilim darajangizni belgilang:</b>\n\n"
        f"Agar darajangizni bilsangiz, quyidagi tugmalardan birini tanlang.\n"
        f"Agar darajangizni bilmasangiz yoki aniq tekshirmoqchi bo'lsangiz, <b>'🎯 Darajani aniqlash (Online Test)'</b> tugmasini bosing:"
    )

    await message.answer(
        offer_text,
        reply_markup=get_level_selection_kb(telegram_id=user_id),
        parse_mode="HTML"
    )
