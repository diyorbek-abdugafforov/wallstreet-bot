import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

# .env faylini yuklash
load_dotenv(BASE_DIR / ".env")

# Bot sozlamalari
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Rahbar va Adminlar ID lari (vergul bilan ajratilgan bo'lishi mumkin)
ADMINS_RAW = os.getenv("ADMIN_ID", "0")
ADMINS = [int(x.strip()) for x in ADMINS_RAW.split(",") if x.strip().isdigit()]

# Reception / Menejerlar guruhi chat ID si (masalan -100...)
MANAGER_GROUP_ID = int(os.getenv("MANAGER_GROUP_ID", "0") or 0)

# Ma'lumotlar bazasi fayli
DB_NAME = os.getenv("DB_NAME", str(BASE_DIR / "edubot.db"))

# Web App va Server sozlamalari
WEB_HOST = os.getenv("WEB_HOST", "0.0.0.0")
WEB_PORT = int(os.getenv("PORT", os.getenv("WEB_PORT", "8000")))
WEBAPP_BASE_URL = os.getenv("WEBAPP_BASE_URL", "http://localhost:8000").rstrip("/")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "wallstreet2026")
ADMIN_TUNNEL_URL = os.getenv("ADMIN_TUNNEL_URL", "https://circle-thesis-teeth-mode.trycloudflare.com").rstrip("/")

# O'quv markazi ma'lumotlari
CENTER_NAME = "Wall Street Education"
CENTER_PHONE = "+998 71 200 77 77"
CENTER_LOCATION = "Toshkent shahri, Chilonzor tumani, Bunyodkor shoh ko'chasi 15-uy"
LOCATION_LATITUDE = 41.2858
LOCATION_LONGITUDE = 69.2045

# Sinov darsi chegirma kuponi
TRIAL_COUPON_CODE = "EDUBOT-FREE"

# Placement Test savollari (Darajani aniqlash testi)
# 5 ta darajaga mos savollar to'plami
PLACEMENT_TEST_QUESTIONS = [
    {
        "id": 1,
        "question": "1. She _______ to the gym every morning before breakfast.",
        "options": ["go", "goes", "is going", "went"],
        "answer": 1, # "goes" (Index 1)
        "level": "A1"
    },
    {
        "id": 2,
        "question": "2. We haven't seen them _______ last summer.",
        "options": ["for", "since", "during", "while"],
        "answer": 1, # "since"
        "level": "A2"
    },
    {
        "id": 3,
        "question": "3. If I _______ you, I would take that opportunity immediately.",
        "options": ["am", "was", "were", "had been"],
        "answer": 2, # "were"
        "level": "B1"
    },
    {
        "id": 4,
        "question": "4. Despite _______ tired, he continued preparing for his IELTS exam.",
        "options": ["being", "be", "was", "to be"],
        "answer": 0, # "being"
        "level": "B1"
    },
    {
        "id": 5,
        "question": "5. By the time the teacher entered, the students _______ their assignment.",
        "options": ["finished", "have finished", "had finished", "finish"],
        "answer": 2, # "had finished"
        "level": "B2"
    },
    {
        "id": 6,
        "question": "6. Hardly _______ entered the room when the phone started ringing.",
        "options": ["he had", "had he", "he did", "did he"],
        "answer": 1, # "had he"
        "level": "B2"
    }
]

# Mavjud kurslar ro'yxati
COURSES = [
    {
        "name": "General English (Starter - Advanced)",
        "duration": "Har bir bosqich 3 oy",
        "price": "600,000 so'm / oy",
        "description": "Grammatika, so'z boyligi va ravon so'zlashuvni oshirish uchun mukammal kurs."
    },
    {
        "name": "IELTS Rocket (7.0+ Kafolati)",
        "duration": "3 - 5 oy intensiv",
        "price": "850,000 so'm / oy",
        "description": "Mock imtihonlar, individual feedback va tajribali IELTS 8.0+ instruktorlari."
    },
    {
        "name": "Kids English (7 - 13 yosh)",
        "duration": "Doimiy qabul",
        "price": "500,000 so'm / oy",
        "description": "Interaktiv o'yinlar, multfilmlar va xalqaro metodika asosida yosh bolalar uchun ingliz tili."
    },
    {
        "name": "IT & Dasturlash (Frontend / Python)",
        "duration": "6 oy",
        "price": "900,000 so'm / oy",
        "description": "Noldan amaliy loyihalargacha, ishga joylashishda amaliy yordam."
    }
]

# Guruh vaqtlari (dars jadvallari)
GROUP_SCHEDULES = [
    "Dushanba - Chorshanba - Juma (09:00 - 10:30)",
    "Dushanba - Chorshanba - Juma (14:30 - 16:00)",
    "Dushanba - Chorshanba - Juma (18:30 - 20:00)",
    "Seshanba - Payshanba - Shanba (10:00 - 11:30)",
    "Seshanba - Payshanba - Shanba (15:00 - 16:30)",
    "Seshanba - Payshanba - Shanba (18:30 - 20:00)"
]
