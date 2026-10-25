import asyncio
import logging
import sys
import uvicorn

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN, ADMINS, WEB_HOST, WEB_PORT, WEBAPP_BASE_URL
from database import Database
from services.scheduler import check_reminders_task

# Web App va CMS
from web_app import app as web_app, set_bot_instance

# Handlerlar
from handlers.start import router as start_router
from handlers.registration import router as reg_router
from handlers.level_choice import router as level_choice_router
from handlers.test_quiz import router as quiz_router
from handlers.admin_group import router as admin_group_router
from handlers.admin_panel import router as admin_panel_router
from handlers.student_menu import router as student_menu_router
from handlers.web_app_handler import router as web_app_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

async def run_web_server():
    """FastAPI Web App va CMS serverini fonda ishga tushirish"""
    config = uvicorn.Config(
        app=web_app,
        host=WEB_HOST,
        port=WEB_PORT,
        log_level="warning"
    )
    server = uvicorn.Server(config)
    logger.info(f"🌐 Web App & Admin CMS ishga tushdi: http://localhost:{WEB_PORT}/admin (Tashqi URL: {WEBAPP_BASE_URL})")
    await server.serve()

async def main():
    if not BOT_TOKEN:
        logger.error("BOT_TOKEN aniqlanmadi! Iltimos, .env faylida BOT_TOKEN ni to'ldiring.")
        print("\n[DIQQAT] .env faylida BOT_TOKEN ko'rsatilmagan! Bot ishga tushishi uchun BotFather bergan tokenni .env fayliga kiriting.\n")
        return

    # Bot va Dispatcher
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Web App serveriga Bot obyektini ulash (natijalarni bot va guruhga yuborish uchun)
    set_bot_instance(bot)

    # Ma'lumotlar bazasi
    db = Database()
    await db.init()
    logger.info("Ma'lumotlar bazasi muvaffaqiyatli ishga tushirildi.")

    # Dependency Injection
    dp["db"] = db

    # Routerlarni ulash
    dp.include_router(start_router)
    dp.include_router(reg_router)
    dp.include_router(level_choice_router)
    dp.include_router(quiz_router)
    dp.include_router(admin_group_router)
    dp.include_router(admin_panel_router)
    dp.include_router(student_menu_router)
    dp.include_router(web_app_router)

    # Fon vazifalarini ishga tushirish (Eslatmalar va Web Server)
    web_server_task = asyncio.create_task(run_web_server())
    reminder_task = asyncio.create_task(check_reminders_task(bot, db))

    # Bot ishga tushganida adminlarga xabar berish
    for admin_id in ADMINS:
        if admin_id != 0:
            try:
                await bot.send_message(
                    chat_id=admin_id,
                    text=(
                        "🚀 <b>Wall Street EduBot & Web App muvaffaqiyatli ishga tushdi!</b>\n\n"
                        f"🌐 <b>Admin CMS Paneli:</b> <code>http://localhost:{WEB_PORT}/admin</code>\n"
                        f"📱 <b>Web App manzili:</b> <code>{WEBAPP_BASE_URL}</code>"
                    ),
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.warning(f"Adminga {admin_id} xabar yetkazilmadi: {e}")

    logger.info("Wall Street EduBot xabarlarni qabul qilishga tayyor!")

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        reminder_task.cancel()
        web_server_task.cancel()
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("EduBot to'xtatildi.")
