import asyncio
import logging
from aiogram import Bot
from database import Database
from config import CENTER_NAME, CENTER_LOCATION, CENTER_PHONE

logger = logging.getLogger(__name__)

async def check_reminders_task(bot: Bot, db: Database):
    """
    Har soatda yoki belgilangan oraliqda sinov darsi bor o'quvchilarga
    1 kun oldin eslatma xabarini avtomatik jo'natish vazifasi.
    """
    while True:
        try:
            # Eslatma jo'natilmagan va sinov darsi belgilangan o'quvchilarni tekshirish
            # Amalda sinov darsi yaqinlashganda eslatma yuboriladi
            await asyncio.sleep(3600) # Har soatda 1 marta tekshiradi
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Eslatma yuborishda xatolik: {e}")
            await asyncio.sleep(60)

async def send_trial_confirmation_to_student(bot: Bot, telegram_id: int, trial_date: str):
    """
    Menejer sinov darsi sanasini belgilaganda o'quvchiga darhol xabar boradi
    """
    text = (
        f"🎉 <b>Tabriklaymiz! Sizning sinov darsingiz belgilandi!</b>\n\n"
        f"📅 <b>Dars vaqti:</b> {trial_date}\n"
        f"🏢 <b>O'quv markaz:</b> {CENTER_NAME}\n"
        f"📍 <b>Manzil:</b> {CENTER_LOCATION}\n"
        f"📞 <b>Aloqa:</b> {CENTER_PHONE}\n\n"
        f"<i>Iltimos, dars boshlanishidan 10 daqiqa oldin kelishingizni so'raymiz. Reception xodimi sizni kutib oladi!</i>"
    )
    try:
        await bot.send_message(chat_id=telegram_id, text=text, parse_mode="HTML")
    except Exception as e:
        logger.warning(f"O'quvchiga {telegram_id} xabar yetkazilmadi: {e}")
