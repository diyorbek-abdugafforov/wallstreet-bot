import asyncio
import logging
import sys
import subprocess
import re
from typing import Optional
from pathlib import Path
import uvicorn
import config
from config import BOT_TOKEN, ADMINS, WEB_HOST, WEB_PORT, WEBAPP_BASE_URL

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
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

cloudflared_process: Optional[subprocess.Popen] = None

def start_cloudflared_tunnel(port: int = 8000) -> Optional[str]:
    """Cloudflare tunnelini fonda ishga tushirib, avtomatik yangi jonli havola olish"""
    global cloudflared_process
    cf_path = Path(__file__).resolve().parent / "cloudflared.exe"
    if not cf_path.exists():
        logger.warning("cloudflared.exe topilmadi. Faqat lokal server ishlaydi.")
        return None

    try:
        cloudflared_process = subprocess.Popen(
            [str(cf_path), "tunnel", "--url", f"http://localhost:{port}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace"
        )
        for _ in range(80):
            line = cloudflared_process.stderr.readline()
            if not line and cloudflared_process.poll() is not None:
                break
            m = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", line)
            if m:
                live_url = m.group(0).rstrip("/")
                config.ADMIN_TUNNEL_URL = live_url
                return live_url
    except Exception as e:
        logger.warning(f"Cloudflare tunnel ishga tushirishda xatolik: {e}")
    return None

async def run_web_server():
    """FastAPI Web App va CMS serverini fonda ishga tushirish"""
    cfg = uvicorn.Config(
        app=web_app,
        host=WEB_HOST,
        port=WEB_PORT,
        log_level="warning"
    )
    server = uvicorn.Server(cfg)
    logger.info(f"🌐 Web App & Admin CMS ishga tushdi: http://localhost:{WEB_PORT}/admin")
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

    # Fon vazifalarini ishga tushirish (Web Server va Eslatmalar)
    web_server_task = asyncio.create_task(run_web_server())
    reminder_task = asyncio.create_task(check_reminders_task(bot, db))

    # Cloudflare tunnelni ishga tushirish (agar mavjud bo'lsa)
    tunnel_url = start_cloudflared_tunnel(WEB_PORT)
    if tunnel_url:
        logger.info(f"🌐 Cloudflare jonli tunnel ulandi: {tunnel_url}/admin")
    else:
        logger.info(f"🌐 Standart havola ishlatiladi: {config.ADMIN_TUNNEL_URL}/admin")

    print("\n" + "=" * 65)
    print("🚀 WALL STREET EDUBOT & ADMIN PANEL ISHGA TUSHDI!")
    print(f"💻 Kompyuterda:            http://localhost:{WEB_PORT}/admin")
    print(f"📱 Telefonda / Tashqi:     {config.ADMIN_TUNNEL_URL}/admin")
    print("🔑 Kirish:                 Login: admin | Parol: wallstreet2026")
    print("=" * 65 + "\n")

    # Bot ishga tushganida adminlarga xabar berish
    for admin_id in ADMINS:
        if admin_id != 0:
            try:
                await bot.send_message(
                    chat_id=admin_id,
                    text=(
                        "🚀 <b>Wall Street EduBot & Admin Panel muvaffaqiyatli ishga tushdi!</b>\n\n"
                        f"💻 <b>Admin Panel (Kompyuterda):</b> <code>http://localhost:{WEB_PORT}/admin</code>\n"
                        f"📱 <b>Admin Panel (Telefonda):</b> <code>{config.ADMIN_TUNNEL_URL}/admin</code>\n"
                        f"🌐 <b>Foydalanuvchi Web App:</b> <code>{WEBAPP_BASE_URL}</code>\n\n"
                        "🔑 <i>Login: admin | Parol: wallstreet2026</i>"
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
        if cloudflared_process and cloudflared_process.poll() is None:
            try:
                cloudflared_process.terminate()
            except Exception:
                pass
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("EduBot to'xtatildi.")
