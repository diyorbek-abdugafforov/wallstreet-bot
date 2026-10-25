import asyncio
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from database import Database
import config
from config import ADMINS, MANAGER_GROUP_ID
from keyboards.inline_kb import (
    get_admin_panel_kb,
    get_admin_users_kb,
    get_broadcast_target_kb
)
from handlers.states import AdminBroadcastStates, AdminEventStates, AdminManagementStates
from services.export_excel import create_students_excel

router = Router()

async def check_admin(db: Database, user_id: int) -> bool:
    return await db.is_admin(user_id)

@router.message(F.text == "⚙️ Rahbar & Reception Paneli")
async def show_admin_panel(message: types.Message, db: Database):
    """Rahbar va administrator boshqaruv paneli"""
    if not await check_admin(db, message.from_user.id):
        return

    text = (
        "💼 <b>Rahbar & Reception Boshqaruv Markazi (CMS)</b>\n\n"
        "Ushbu panel orqali barcha arizalar oqimi, yangi lidlar, o'quvchilar darajasi, "
        "statistika va xabarnomalarni real vaqtda boshqarishingiz mumkin.\n\n"
        "🌐 <b>Brauzerda kirish havolalari:</b>\n"
        "• Kompyuterda: <code>http://localhost:8000/admin</code>\n"
        f"• Telefonda / Tashqi: <code>{config.ADMIN_TUNNEL_URL}/admin</code>\n\n"
        "🔑 <b>Kirish ma'lumotlari:</b>\n"
        "• Login: <code>admin</code>\n"
        "• Parol: <code>wallstreet2026</code>\n\n"
        "<i>Quyidagi tugma orqali panelni to'g'ridan-to'g'ri ochishingiz mumkin 👇</i>"
    )
    await message.answer(text, reply_markup=get_admin_panel_kb(user_id=message.from_user.id), parse_mode="HTML")

@router.callback_query(F.data == "adm_refresh")
async def refresh_admin_panel(call: types.CallbackQuery, db: Database):
    if not await check_admin(db, call.from_user.id):
        await call.answer("Ruxsat yo'q!", show_alert=True)
        return
    text = (
        "💼 <b>Rahbar & Reception Boshqaruv Markazi (Yangilandi)</b>\n\n"
        "🌐 <b>Brauzerda kirish havolalari:</b>\n"
        "• Kompyuterda: <code>http://localhost:8000/admin</code>\n"
        f"• Telefonda / Tashqi: <code>{config.ADMIN_TUNNEL_URL}/admin</code>\n\n"
        "🔑 <b>Kirish ma'lumotlari:</b>\n"
        "• Login: <code>admin</code> | Parol: <code>wallstreet2026</code>"
    )
    await call.message.edit_text(
        text,
        reply_markup=get_admin_panel_kb(user_id=call.from_user.id),
        parse_mode="HTML"
    )
    await call.answer("Yangilandi!")

# --- ADMINLARNI BOSHQARISH (QO'SHISH / O'CHIRISH) ---
@router.callback_query(F.data == "adm_manage_admins")
async def manage_admins_menu(call: types.CallbackQuery, db: Database):
    if not await check_admin(db, call.from_user.id):
        await call.answer("Ruxsat yo'q!", show_alert=True)
        return

    admins = await db.get_admins()
    
    text = "👤 <b>Barcha Administratorlar va Reception Xodimlari:</b>\n━━━━━━━━━━━━━━━━━━\n\n"
    # Dastlabki superadminlar
    for sa in ADMINS:
        if sa != 0:
            text += f"👑 <b>Bosh Rahbar:</b> ID <code>{sa}</code>\n"

    for a in admins:
        text += f"🔹 <b>{a.get('full_name', 'Admin')}</b>: ID <code>{a['telegram_id']}</code> ({a.get('role', 'admin')})\n"

    text += "\n<i>Yangi admin qo'shish yoki o'chirish uchun pastdagi tugmalardan foydalaning:</i>"

    await call.message.edit_text(text, reply_markup=get_admin_users_kb(admins), parse_mode="HTML")
    await call.answer()

@router.callback_query(F.data == "adm_add_admin")
async def start_add_admin(call: types.CallbackQuery, state: FSMContext, db: Database):
    if not await check_admin(db, call.from_user.id):
        await call.answer("Ruxsat yo'q!", show_alert=True)
        return

    await state.set_state(AdminManagementStates.waiting_for_admin_id)
    await call.message.reply(
        "👤 <b>Yangi adminning Telegram ID raqamini kiriting:</b>\n"
        "(ID raqamni bilish uchun @userinfobot dan foydalanish mumkin)",
        parse_mode="HTML"
    )
    await call.answer()

@router.message(AdminManagementStates.waiting_for_admin_id)
async def process_admin_id(message: types.Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit():
        await message.reply("⚠️ Iltimos, faqat raqamlardan iborat Telegram ID kiriting:")
        return

    await state.update_data(new_admin_id=int(text))
    await state.set_state(AdminManagementStates.waiting_for_admin_name)
    await message.reply("📝 Endi ushbu adminning <b>Ism va Familiyasini</b> (yoki lavozimini) kiriting:", parse_mode="HTML")

@router.message(AdminManagementStates.waiting_for_admin_name)
async def process_admin_name(message: types.Message, state: FSMContext, db: Database, bot: Bot):
    full_name = message.text.strip()
    data = await state.get_data()
    new_admin_id = data["new_admin_id"]
    await state.clear()

    success = await db.add_admin(telegram_id=new_admin_id, full_name=full_name, role="admin", added_by=message.from_user.id)
    if success:
        await message.reply(
            f"✅ <b>Yangi admin muvaffaqiyatli qo'shildi!</b>\n\n"
            f"👤 <b>F.I.O:</b> {full_name}\n"
            f"🆔 <b>Telegram ID:</b> <code>{new_admin_id}</code>\n"
            f"U endi botdagi admin paneldan va Web App dan to'liq foydalana oladi.",
            parse_mode="HTML"
        )
        # Yangi adminga bildirishnoma yuborish
        try:
            await bot.send_message(
                chat_id=new_admin_id,
                text="🎉 <b>Siz Wall Street Education tizimiga Administrator etib tayinlandingiz!</b>\nBoshqaruv menyusini ko'rish uchun /start buyrug'ini bosing.",
                parse_mode="HTML"
            )
        except Exception:
            pass
    else:
        await message.reply("Xatolik: admin qo'shilmadi.")

@router.callback_query(F.data.startswith("adm_del_admin:"))
async def delete_admin_callback(call: types.CallbackQuery, db: Database):
    if not await check_admin(db, call.from_user.id):
        await call.answer("Ruxsat yo'q!", show_alert=True)
        return

    del_id = int(call.data.split(":")[1])
    await db.remove_admin(del_id)
    await call.answer("Admin muvaffaqiyatli o'chirildi!", show_alert=True)

    # Ro'yxatni yangilash
    admins = await db.get_admins()
    await call.message.edit_reply_markup(reply_markup=get_admin_users_kb(admins))

# --- STATISTIKA ---
@router.callback_query(F.data == "adm_stats")
async def show_full_stats(call: types.CallbackQuery, db: Database):
    """To'liq tahliliy statistika"""
    if not await check_admin(db, call.from_user.id):
        await call.answer("Ruxsat yo'q!", show_alert=True)
        return

    stats = await db.get_stats()
    total = stats["total"]
    today = stats["today"]
    status_counts = stats["status_counts"]
    level_counts = stats["level_counts"]
    utm_counts = stats["utm_counts"]

    status_text = "".join([f"  • {st}: <b>{cnt} ta</b>\n" for st, cnt in status_counts.items()]) or "  <i>Hozircha yo'q</i>\n"
    level_text = "".join([f"  • {lvl}: <b>{cnt} ta</b>\n" for lvl, cnt in level_counts.items()]) or "  <i>Test topshirganlar yo'q</i>\n"
    utm_text = "".join([f"  • <code>{utm}</code>: <b>{cnt} ta</b>\n" for utm, cnt in utm_counts.items()]) or "  <i>Ma'lumot yo'q</i>\n"

    report = (
        "📊 <b>WALL STREET STRATEGIK STATISTIKA VA TAHLIL</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 <b>Jami yig'ilgan lidlar:</b> {total} nafar\n"
        f"⚡ <b>Bugungi yangi arizalar:</b> {today} nafar\n\n"
        f"📌 <b>Menejerlar holati (Statuslar):</b>\n{status_text}\n"
        f"🎯 <b>O'quvchilar bilimi (Darajalar):</b>\n{level_text}\n"
        f"📈 <b>Reklama Samaradorligi (UTM):</b>\n{utm_text}"
        "━━━━━━━━━━━━━━━━━━━━━━━━"
    )

    await call.message.edit_text(report, reply_markup=get_admin_panel_kb(user_id=call.from_user.id), parse_mode="HTML")
    await call.answer()

# --- EXCEL BAZANI YUKLASH ---
@router.callback_query(F.data == "adm_export")
async def export_excel_database(call: types.CallbackQuery, db: Database):
    if not await check_admin(db, call.from_user.id):
        await call.answer("Ruxsat yo'q!", show_alert=True)
        return

    await call.answer("Excel hisobot tayyorlanmoqda...")
    students = await db.get_all_students()

    if not students:
        await call.message.reply("Bazada hozircha o'quvchilar mavjud emas.")
        return

    excel_file = create_students_excel(students)
    input_file = BufferedInputFile(excel_file.getvalue(), filename="WallStreet_Lidlar_Bazasi.xlsx")

    await call.message.reply_document(
        document=input_file,
        caption=f"📁 <b>Mijozlar Bazasi (Oltin Fond)</b>\nJami yozuvlar soni: {len(students)} ta.",
        parse_mode="HTML"
    )

# --- BROADCAST ---
@router.callback_query(F.data == "adm_broadcast")
async def start_broadcast(call: types.CallbackQuery, state: FSMContext, db: Database):
    if not await check_admin(db, call.from_user.id):
        await call.answer("Ruxsat yo'q!", show_alert=True)
        return

    await state.set_state(AdminBroadcastStates.waiting_for_target)
    await call.message.edit_text(
        "📢 <b>Xabarnoma yuborish bo'limi:</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        "Quyidagi variantlardan birini tanlang:\n"
        "• <b>1. Ommaviy</b> — bazadagi barcha foydalanuvchilar va ulangan guruhlarga birvarakay yuborish.\n"
        "• <b>2. Bitta foydalanuvchiga</b> — faqat bitta tanlangan shaxsga Telegram ID raqami orqali yuborish.\n\n"
        "<i>⚡ Eslatma: Xabar qanday yuborilsa (oddiy matn, formatlangan matn, rasm, video, Premium stiker, ovozli xabar) aynan o'z asl holatida yetkaziladi!</i>",
        reply_markup=get_broadcast_target_kb(),
        parse_mode="HTML"
    )
    await call.answer()

@router.callback_query(F.data.startswith("bc_tgt:"))
async def choose_broadcast_target(call: types.CallbackQuery, state: FSMContext):
    target = call.data.split(":")[1]

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="bc_cancel")]
    ])

    if target == "single_user":
        await state.update_data(broadcast_target="single_user")
        await state.set_state(AdminBroadcastStates.waiting_for_user_id)
        await call.message.edit_text(
            "👤 <b>Bitta foydalanuvchiga xabar yuborish:</b>\n━━━━━━━━━━━━━━━━━━\n\n"
            "Xabar yubormoqchi bo'lgan foydalanuvchining <b>Telegram ID</b> raqamini kiriting:\n"
            "<i>(Masalan: <code>6262775861</code>. ID raqamini o'quvchilar ro'yxatidan yoki guruhdagi arizalardan olishingiz mumkin)</i>",
            reply_markup=kb,
            parse_mode="HTML"
        )
        await call.answer()
        return

    await state.update_data(broadcast_target=target)
    await state.set_state(AdminBroadcastStates.waiting_for_message)

    target_names = {
        "all": "Barcha o'quvchilar va ulangan guruhlar",
        "beginner": "A1 - A2 (Beginner / Elementary)",
        "intermediate": "B1 - B2 (Pre-Intermediate / Intermediate)",
        "Yangi": "Yangi Lidlar"
    }
    t_name = target_names.get(target, target)

    await call.message.edit_text(
        f"🎯 <b>Maqsadli auditoriya:</b> <b>{t_name}</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        f"Endi tarqatmoqchi bo'lgan xabaringizni yuboring:\n"
        f"<i>(Matn, rasm, video, Premium stiker, ovozli xabar, dumaloq video yoki fayl — <b>qanday bo'lsa aynan shunday boradi</b>)</i>",
        reply_markup=kb,
        parse_mode="HTML"
    )
    await call.answer()

@router.callback_query(F.data == "bc_cancel")
async def cancel_broadcast(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("❌ Xabarnoma yuborish bekor qilindi.", reply_markup=get_admin_panel_kb(user_id=call.from_user.id))
    await call.answer()

@router.message(AdminBroadcastStates.waiting_for_user_id)
async def process_broadcast_user_id(message: types.Message, state: FSMContext, db: Database):
    if not await check_admin(db, message.from_user.id):
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="bc_cancel")]
    ])

    user_input = message.text.strip() if message.text else ""
    if not user_input.isdigit():
        await message.reply(
            "⚠️ <b>Noto'g'ri ID format!</b>\nIltimos, faqat raqamlardan iborat Telegram ID kiriting (masalan: <code>6262775861</code>):",
            reply_markup=kb,
            parse_mode="HTML"
        )
        return

    target_id = int(user_input)
    student = await db.get_student(target_id)
    if student:
        user_info = (
            f"👤 <b>O'quvchi:</b> {student.get('full_name', 'Mavjud')}\n"
            f"📱 <b>Telefon:</b> {student.get('phone', 'Kiritilmagan')}\n"
            f"🎯 <b>Daraja:</b> {student.get('level', 'Nomaʼlum')}\n"
            f"🆔 <b>Telegram ID:</b> <code>{target_id}</code>"
        )
    else:
        user_info = f"🆔 <b>Telegram ID:</b> <code>{target_id}</code> <i>(Bazada to'liq ma'lumot topilmadi)</i>"

    await state.update_data(target_user_id=target_id)
    await state.set_state(AdminBroadcastStates.waiting_for_message)

    await message.reply(
        f"✅ <b>Qabul qiluvchi tanlandi:</b>\n{user_info}\n\n"
        f"Endi ushbu foydalanuvchiga yubormoqchi bo'lgan xabaringizni yuboring:\n"
        f"<i>(Matn, rasm, video, Premium stiker, audio, ovozli xabar — <b>qanday bo'lsa aynan shunday boradi</b>)</i>",
        reply_markup=kb,
        parse_mode="HTML"
    )

@router.message(AdminBroadcastStates.waiting_for_message)
async def process_broadcast_send(message: types.Message, state: FSMContext, db: Database, bot: Bot):
    if not await check_admin(db, message.from_user.id):
        return

    data = await state.get_data()
    target = data.get("broadcast_target", "all")
    target_user_id = data.get("target_user_id")
    await state.clear()

    # 1. Bitta tanlangan foydalanuvchiga yuborish (ID orqali)
    if target == "single_user" and target_user_id:
        try:
            # Qanday bo'lsa aynan shundayligicha (premium stiker, media, formatlar) yuboradi
            await message.copy_to(chat_id=target_user_id)
            await message.reply(
                f"✅ <b>Xabar muvaffaqiyatli yetkazildi!</b>\n\n"
                f"👤 Qabul qiluvchi ID: <code>{target_user_id}</code>\n"
                f"⚡ Xabar o'z asl holatida (stiker/media/matn) foydalanuvchiga yetkazildi.",
                reply_markup=get_admin_panel_kb(user_id=message.from_user.id),
                parse_mode="HTML"
            )
        except Exception as e:
            await message.reply(
                f"❌ <b>Xabar yetkazilmadi!</b>\n\n"
                f"👤 ID: <code>{target_user_id}</code>\n"
                f"Sabab: Foydalanuvchi botni to'xtatgan (bloklagan) yoki bu ID botdan foydalanmagan.\n"
                f"<i>Texnik xato: {e}</i>",
                reply_markup=get_admin_panel_kb(user_id=message.from_user.id),
                parse_mode="HTML"
            )
        return

    # 2. Ommaviy xabarnoma (Barcha odamlar va ulangan guruhlar)
    students = await db.get_all_students()
    recipients = set()

    for s in students:
        lvl = s.get("level") or ""
        st = s.get("status") or ""
        tid = s.get("telegram_id")
        if not tid:
            continue

        if target == "all":
            recipients.add(tid)
        elif target == "beginner" and ("A1" in lvl or "A2" in lvl or "Beginner" in lvl or "Elementary" in lvl):
            recipients.add(tid)
        elif target == "intermediate" and ("B1" in lvl or "B2" in lvl or "Pre-Int" in lvl or "Intermediate" in lvl):
            recipients.add(tid)
        elif target == "Yangi" and st == "Yangi":
            recipients.add(tid)

    # Ulangan guruhga ham yuborish
    if target == "all" and MANAGER_GROUP_ID != 0:
        recipients.add(MANAGER_GROUP_ID)

    if not recipients:
        await message.reply(
            "⚠️ Tanlangan mezon bo'yicha bazada qabul qiluvchilar topilmadi.",
            reply_markup=get_admin_panel_kb(user_id=message.from_user.id)
        )
        return

    status_msg = await message.answer(f"⏳ Xabar tarqatilmoqda (0/{len(recipients)})...")
    success_count = 0
    fail_count = 0

    for tid in recipients:
        try:
            # Qanday bo'lsa aynan shundayligicha (premium stiker, media, ovoz, matn) nusxalab yuboradi
            await message.copy_to(chat_id=tid)
            success_count += 1
            await asyncio.sleep(0.04) # Telegram Flood limitdan himoya
        except Exception:
            fail_count += 1

    await status_msg.edit_text(
        f"✅ <b>Ommaviy xabarnoma muvaffaqiyatli yakunlandi!</b>\n━━━━━━━━━━━━━━━━━━\n\n"
        f"📨 Yuborildi (odamlar + guruh): <b>{success_count}</b> ta\n"
        f"❌ Yetib bormadi (botni bloklaganlar): <b>{fail_count}</b> ta\n\n"
        f"<i>Barcha xabarlar (matn, media, premium stikerlar) o'zining asl holatida yetkazildi.</i>",
        reply_markup=get_admin_panel_kb(user_id=message.from_user.id),
        parse_mode="HTML"
    )

# --- TADBIROTLAR ---
@router.callback_query(F.data == "adm_add_event")
async def start_add_event(call: types.CallbackQuery, state: FSMContext, db: Database):
    if not await check_admin(db, call.from_user.id):
        await call.answer("Ruxsat yo'q!", show_alert=True)
        return

    await state.set_state(AdminEventStates.waiting_for_title)
    await call.message.reply("🎪 <b>Tadbir nomini kiriting:</b>\n(Masalan: <i>Speaking Club with Native Speaker</i>)")
    await call.answer()

@router.message(AdminEventStates.waiting_for_title)
async def process_event_title(message: types.Message, state: FSMContext):
    await state.update_data(ev_title=message.text.strip())
    await state.set_state(AdminEventStates.waiting_for_desc)
    await message.reply("📝 <b>Tadbir tavsifi va spiker haqida ma'lumot yozing:</b>")

@router.message(AdminEventStates.waiting_for_desc)
async def process_event_desc(message: types.Message, state: FSMContext):
    await state.update_data(ev_desc=message.text.strip())
    await state.set_state(AdminEventStates.waiting_for_datetime)
    await message.reply("📅 <b>Tadbir o'tkazilish sanasi va vaqtini yozing:</b>\n(Masalan: <i>Shanba, 28-oktyabr 16:00</i>)")

@router.message(AdminEventStates.waiting_for_datetime)
async def process_event_datetime(message: types.Message, state: FSMContext, db: Database):
    data = await state.get_data()
    title = data["ev_title"]
    desc = data["ev_desc"]
    date_time = message.text.strip()
    await state.clear()

    ev_id = await db.add_event(title=title, description=desc, date_time=date_time, seats_limit=30)
    await message.reply(
        f"✅ <b>Yangi tadbir muvaffaqiyatli e'lon qilindi!</b>\n\n"
        f"📌 #{ev_id}: <b>{title}</b>\n"
        f"📅 {date_time}\n"
        f"O'quvchilar '🎪 Ochiq darslar va tadbirlar' bo'limida joy band qilishlari mumkin.",
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("join_event:"))
async def join_event_callback_handler(call: types.CallbackQuery, db: Database):
    """Foydalanuvchi tadbirga ro'yxatdan o'tish tugmasini bosganda"""
    try:
        event_id = int(call.data.split(":")[1])
    except (IndexError, ValueError):
        await call.answer("Xatolik yuz berdi.", show_alert=True)
        return

    user_id = call.from_user.id
    student = await db.get_student(user_id)
    full_name = student.get("full_name") if (student and student.get("full_name")) else call.from_user.full_name
    phone = student.get("phone") if (student and student.get("phone")) else "Kiritilmagan"

    registered = await db.register_event(event_id=event_id, telegram_id=user_id, full_name=full_name, phone=phone)
    if registered:
        await call.answer("✅ Siz tadbirga muvaffaqiyatli ro'yxatdan o'tdingiz!", show_alert=True)
        await call.message.reply(
            f"🎉 <b>Tabriklaymiz, siz tadbirga qabul qilindingiz!</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>Qatnashchi:</b> {full_name}\n"
            f"📱 <b>Telefon:</b> {phone}\n\n"
            f"<i>Belgilangan sanada markazimizga kelishingiz mumkin. Kuting, reception xodimi siz bilan bog'lanadi!</i>",
            parse_mode="HTML"
        )
    else:
        await call.answer("⚠️ Joy qolmagan yoki siz allaqachon ushbu tadbirga ro'yxatdan o'tgansiz!", show_alert=True)

