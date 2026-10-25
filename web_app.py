import asyncio
import hashlib
import logging
import time
import uuid
import re
from typing import Optional, List, Dict, Any
from pathlib import Path
from fastapi import FastAPI, Request, Form, Body, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from services.export_excel import create_students_excel
from services.test_template import (
    generate_test_template_excel,
    parse_test_excel,
    sync_questions_to_html,
    sync_courses_to_html,
    sync_results_to_html,
    sync_schedules_to_html
)

from config import BOT_TOKEN, MANAGER_GROUP_ID, ADMINS, CENTER_NAME, ADMIN_USERNAME, ADMIN_PASSWORD, WEBAPP_BASE_URL
from database import Database
from data_manager import (
    get_placement_test,
    get_bonus_test,
    get_courses,
    get_schedules,
    get_results,
    get_settings,
    read_json,
    write_json
)
from keyboards.inline_kb import get_manager_lead_kb

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "web" / "templates"))

# Rasmlar va statik fayllar papkasi
UPLOADS_DIR = BASE_DIR / "web" / "static" / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Wall Street WebApp & CMS")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "web" / "static")), name="static")
app.mount("/uploads", StaticFiles(directory=str(BASE_DIR / "web" / "static" / "uploads")), name="uploads")

db = Database()
bot_instance: Optional[Bot] = None

def set_bot_instance(bot: Bot):
    global bot_instance
    bot_instance = bot

@app.on_event("startup")
async def startup_event():
    await db.init()

@app.middleware("http")
async def add_ngrok_skip_header(request: Request, call_next):
    response = await call_next(request)
    response.headers["ngrok-skip-browser-warning"] = "true"
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response

# --- ADMIN AUTENTIFIKATSIYA ---
def get_auth_token() -> str:
    return hashlib.sha256(f"{ADMIN_USERNAME}:{ADMIN_PASSWORD}:ws_secret_key_2026".encode()).hexdigest()

def is_authenticated(request: Request) -> bool:
    # Barcha xodimlar va adminlar uchun to'liq ochiq kirish
    return True

# --- WEB APP YO'NALISHLARI (O'quvchilar uchun) ---

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return RedirectResponse(url="/admin")

@app.get("/webapp/portal", response_class=HTMLResponse)
async def webapp_portal(request: Request, uid: Optional[int] = None):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={}
    )

@app.get("/webapp/test", response_class=HTMLResponse)
async def webapp_placement_test(request: Request, uid: Optional[int] = None):
    student_name = "O'quvchi"
    student_id = uid or 0
    if uid:
        st = await db.get_student(uid)
        if st and st.get("full_name"):
            student_name = st["full_name"]

    questions = get_placement_test()
    return templates.TemplateResponse(
        request=request,
        name="test.html",
        context={
            "student_name": student_name,
            "student_id": student_id,
            "questions": questions,
            "total_questions": len(questions)
        }
    )

@app.get("/webapp/schedule", response_class=HTMLResponse)
async def webapp_schedule(request: Request):
    schedules = get_schedules()
    return templates.TemplateResponse(
        request=request,
        name="schedule.html",
        context={"schedules": schedules}
    )

@app.get("/webapp/courses", response_class=HTMLResponse)
async def webapp_courses(request: Request):
    courses = get_courses()
    return templates.TemplateResponse(
        request=request,
        name="courses.html",
        context={"courses": courses}
    )

@app.get("/webapp/results", response_class=HTMLResponse)
async def webapp_results(request: Request):
    results = get_results()
    return templates.TemplateResponse(
        request=request,
        name="results.html",
        context={"results": results}
    )

@app.get("/webapp/bonus-test", response_class=HTMLResponse)
async def webapp_bonus_test(request: Request, uid: Optional[int] = None):
    bonus_q = get_bonus_test()
    return templates.TemplateResponse(
        request=request,
        name="bonus_test.html",
        context={"bonus_questions": bonus_q}
    )

# --- TEST NATIJASINI QABUL QILISH ---

class SubmitTestPayload(BaseModel):
    telegram_id: int
    level: str
    score: int
    total: int
    full_name: Optional[str] = None
    phone: Optional[str] = None

@app.post("/api/submit-test")
async def submit_test_result(payload: SubmitTestPayload):
    user_id = payload.telegram_id
    level = payload.level
    score = payload.score
    total = payload.total

    coupon = "WALLSTREET10"

    # 1. Bazada yangilash va urinishni sarflash
    if user_id != 0:
        if payload.full_name and payload.phone:
            await db.set_student_contact(telegram_id=user_id, full_name=payload.full_name, phone=payload.phone)
        await db.set_test_result(telegram_id=user_id, score=score, level=level, coupon=coupon)
        await db.increment_student_attempt(user_id)
        await db.set_application_submitted(user_id)
        student = await db.get_student(user_id)
    else:
        student = None

    full_name = payload.full_name or (student.get("full_name") if student else "O'quvchi")
    phone = payload.phone or (student.get("phone") if student else "")
    username = f"@{student.get('username')}" if (student and student.get("username")) else "Mavjud emas"
    utm = student.get("utm_source", "organic") if student else "organic"

    # 2. Telegram Bot orqali o'quvchiga darhol tasdiq xabari yuborish
    if bot_instance and user_id != 0:
        student_msg = (
            f"✅ <b>Arizangiz muvaffaqiyatli qoldirildi!</b>\n\n"
            f"👤 <b>O'quvchi:</b> {full_name}\n"
            f"🎯 <b>Aniqlangan bilim darajangiz:</b> <b>{level}</b>\n"
            f"📊 <b>Natijangiz:</b> {score} / {total} ball\n"
            f"🎁 <b>Kuponingiz:</b> <code>{coupon}</code> (1-sinov darsi bepul!)\n\n"
            f"⚡ <i>Tez orada reception adminlari siz bilan bog'lanadi va mos dars vaqtlari haqida xabar berishadi.</i>\n\n"
            f"O'zingizga qiziq bo'limlarni quyidagi panellardan ko'rishingiz mumkin: 👇"
        )
        try:
            await bot_instance.send_message(chat_id=user_id, text=student_msg, parse_mode="HTML")
        except Exception as e:
            logger.warning(f"O'quvchiga xabar yetkazilmadi: {e}")

    # 3. Reception / Menejerlar guruhiga yoki adminga tayyor lid xabarini tashlash
    if bot_instance:
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
                await bot_instance.send_message(chat_id=MANAGER_GROUP_ID, text=lead_msg, reply_markup=kb, parse_mode="HTML")
                sent = True
            except Exception as e:
                logger.warning(f"Menejer guruhiga yuborilmadi: {e}")

        if not sent:
            for aid in ADMINS:
                if aid != 0:
                    try:
                        await bot_instance.send_message(chat_id=aid, text=lead_msg, reply_markup=kb, parse_mode="HTML")
                    except Exception:
                        pass

    return JSONResponse({"status": "success", "level": level})

# --- ADMIN LOGIN VA CMS PANEL ---

@app.get("/admin/login", response_class=HTMLResponse)
async def login_page(request: Request, error: Optional[str] = None):
    if is_authenticated(request):
        return RedirectResponse(url="/admin")
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"error": error}
    )

@app.post("/admin/login")
async def login_submit(username: str = Form(...), password: str = Form(...)):
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        response = RedirectResponse(url="/admin", status_code=303)
        response.set_cookie(
            key="admin_session",
            value=get_auth_token(),
            httponly=True,
            max_age=86400 * 7 # 7 kun eslab qoladi
        )
        return response
    return RedirectResponse(url="/admin/login?error=Login+yoki+parol+noto'g'ri!", status_code=303)

@app.get("/admin/logout")
async def logout():
    response = RedirectResponse(url="/admin/login", status_code=303)
    response.delete_cookie(key="admin_session")
    return response

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request, uid: Optional[int] = None):
    # Hamma xodimlar va adminlar uchun to'g'ridan-to'g'ri ochiq
    students = await db.get_all_students()
    admins = await db.get_admins()
    placement_test = get_placement_test()
    bonus_test = get_bonus_test()
    courses = get_courses()
    results = get_results()
    schedules = get_schedules()
    events = await db.get_active_events()
    settings = get_settings()

    response = templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={
            "students": students,
            "admins": admins,
            "placement_test": placement_test,
            "bonus_test": bonus_test,
            "courses": courses,
            "results": results,
            "schedules": schedules,
            "events": events,
            "settings": settings
        }
    )
    # Avtomatik avtorizatsiya sessiyasini saqlash
    response.set_cookie(key="admin_session", value=get_auth_token(), httponly=True, max_age=86400 * 30)
    return response

@app.post("/admin/api/add-admin")
async def add_admin_endpoint(
    request: Request,
    telegram_id: int = Form(...),
    full_name: str = Form(...),
    role: str = Form("admin")
):
    if not is_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    await db.add_admin(telegram_id=telegram_id, full_name=full_name, role=role)
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/admin/api/delete-admin")
async def delete_admin_endpoint(request: Request, telegram_id: int = Form(...)):
    if not is_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    await db.remove_admin(telegram_id=telegram_id)
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/admin/api/add-placement-q")
async def add_placement_question(
    request: Request,
    question: str = Form(...),
    opt0: str = Form(...),
    opt1: str = Form(...),
    opt2: str = Form(...),
    opt3: str = Form(...),
    answer: int = Form(...),
    level: str = Form(...)
):
    if not is_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    questions = get_placement_test()
    new_id = (max([q.get("id", 0) for q in questions]) + 1) if questions else 1
    questions.append({
        "id": new_id,
        "question": question,
        "options": [opt0, opt1, opt2, opt3],
        "answer": int(answer),
        "level": level
    })
    write_json("placement_test.json", questions)
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/admin/api/delete-placement-q")
async def delete_placement_question(request: Request, id: int = Form(...)):
    if not is_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    questions = get_placement_test()
    questions = [q for q in questions if q.get("id") != id]
    write_json("placement_test.json", questions)
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/admin/api/add-bonus-q")
async def add_bonus_question(
    request: Request,
    question: str = Form(...),
    opt0: str = Form(...),
    opt1: str = Form(...),
    opt2: str = Form(...),
    opt3: str = Form(...),
    answer: int = Form(...),
    explanation: str = Form("")
):
    if not is_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    questions = get_bonus_test()
    new_id = (max([q.get("id", 0) for q in questions]) + 1) if questions else 1
    questions.append({
        "id": new_id,
        "question": question,
        "options": [opt0, opt1, opt2, opt3],
        "answer": int(answer),
        "explanation": explanation
    })
    write_json("bonus_test.json", questions)
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/admin/api/delete-bonus-q")
async def delete_bonus_question(request: Request, id: int = Form(...)):
    if not is_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    questions = get_bonus_test()
    questions = [q for q in questions if q.get("id") != id]
    write_json("bonus_test.json", questions)
    return RedirectResponse(url="/admin", status_code=303)

def format_course_price(raw_price: str) -> str:
    """
    Admin faqat miqdorni (masalan: 850000 yoki 850 000 yoki 850,000) kiritganda
    avtomatik 'so'm / oy' qo'shib, toza formatlash.
    """
    if not raw_price:
        return ""
    p = raw_price.strip()
    # Har qanday mavjud so'm, som, / oy, /oy larni tozalaymiz
    clean = re.sub(r"(?i)so'?m\s*(/\s*oy)?", "", p).strip()
    clean = re.sub(r"(?i)/\s*oy", "", clean).strip()

    digits_only = re.sub(r"[^\d]", "", clean)
    if digits_only:
        try:
            num = int(digits_only)
            formatted_num = f"{num:,}"
            return f"{formatted_num} so'm / oy"
        except ValueError:
            pass
        return f"{clean} so'm / oy"
    return clean

@app.post("/admin/api/add-course")
async def add_course(
    request: Request,
    name: str = Form(...),
    price: str = Form(...),
    duration: str = Form(...),
    badge: str = Form("Yangi"),
    description: str = Form("")
):
    if not is_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    courses = get_courses()
    new_id = (max([c.get("id", 0) for c in courses]) + 1) if courses else 1
    courses.append({
        "id": new_id,
        "name": name,
        "price": format_course_price(price),
        "duration": duration,
        "badge": badge,
        "description": description
    })
    write_json("courses.json", courses)
    sync_courses_to_html(courses)
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/admin/api/add-result")
async def add_result(
    request: Request,
    student_name: str = Form(...),
    score: str = Form(...),
    image_file: Optional[UploadFile] = File(None),
    image_url: Optional[str] = Form(None),
    details: str = Form(""),
    description: str = Form(""),
    telegram_post_url: str = Form(""),
    video_url: str = Form("")
):
    final_image_url = ""

    # Kompyuterdan yoki telefondan fayl yuklangan bo'lsa
    if image_file and image_file.filename:
        ext = Path(image_file.filename).suffix.lower()
        if not ext or ext not in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
            ext = ".jpg"
        filename = f"result_{int(time.time())}_{uuid.uuid4().hex[:6]}{ext}"
        save_path = UPLOADS_DIR / filename
        content = await image_file.read()
        with open(save_path, "wb") as f:
            f.write(content)

        # Netlify uploads papkasiga ham nusxa olish
        try:
            netlify_uploads = BASE_DIR / "netlify_app" / "uploads"
            netlify_uploads.mkdir(parents=True, exist_ok=True)
            with open(netlify_uploads / filename, "wb") as nf:
                nf.write(content)
        except Exception:
            pass

        final_image_url = f"/static/uploads/{filename}"
    elif image_url and image_url.strip():
        final_image_url = image_url.strip()
    else:
        final_image_url = "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=500&auto=format&fit=crop&q=60"

    results = get_results()
    new_id = (max([r.get("id", 0) for r in results]) + 1) if results else 1
    results.append({
        "id": new_id,
        "student_name": student_name,
        "score": score,
        "image_url": final_image_url,
        "details": details,
        "description": description,
        "telegram_post_url": telegram_post_url.strip() if telegram_post_url else "",
        "video_url": video_url.strip() if video_url else ""
    })
    write_json("results.json", results)
    sync_results_to_html(results)
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/admin/api/update-settings")
async def update_settings_endpoint(
    request: Request,
    reception_phone: str = Form(...),
    reception_additional_phone: str = Form(""),
    location_address: str = Form("")
):
    if not is_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    settings = get_settings()
    settings["reception_phone"] = reception_phone
    settings["reception_additional_phone"] = reception_additional_phone
    settings["location_address"] = location_address
    write_json("settings.json", settings)
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/admin/api/add-promocode")
async def add_promocode(
    request: Request,
    code: str = Form(...),
    discount: str = Form(...),
    description: str = Form("")
):
    if not is_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    settings = get_settings()
    promos = settings.get("promocodes", [])
    promos.append({
        "code": code.upper().strip(),
        "discount": discount,
        "description": description,
        "is_active": True
    })
    settings["promocodes"] = promos
    write_json("settings.json", settings)
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/admin/api/delete-course")
async def delete_course_endpoint(request: Request, id: int = Form(...)):
    if not is_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    courses = get_courses()
    courses = [c for c in courses if c.get("id") != id]
    write_json("courses.json", courses)
    sync_courses_to_html(courses)
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/admin/api/delete-result")
async def delete_result_endpoint(request: Request, id: int = Form(...)):
    if not is_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    results = get_results()
    results = [r for r in results if r.get("id") != id]
    write_json("results.json", results)
    sync_results_to_html(results)
    return RedirectResponse(url="/admin", status_code=303)

class UpdateLeadStatusPayload(BaseModel):
    telegram_id: int
    status: str

@app.post("/admin/api/update-lead-status")
async def update_lead_status_endpoint(request: Request, payload: UpdateLeadStatusPayload):
    if not is_authenticated(request):
        return JSONResponse({"status": "error", "message": "Unauthorized"}, status_code=401)
    await db.update_student_status(telegram_id=payload.telegram_id, status=payload.status)
    return JSONResponse({"status": "success", "new_status": payload.status})

class UpdateLeadNotePayload(BaseModel):
    telegram_id: int
    note: str

@app.post("/admin/api/update-lead-note")
async def update_lead_note_endpoint(request: Request, payload: UpdateLeadNotePayload):
    if not is_authenticated(request):
        return JSONResponse({"status": "error", "message": "Unauthorized"}, status_code=401)
    await db.update_manager_note(telegram_id=payload.telegram_id, note=payload.note)
    return JSONResponse({"status": "success"})

@app.post("/admin/api/edit-course")
async def edit_course_endpoint(
    request: Request,
    id: int = Form(...),
    name: str = Form(...),
    price: str = Form(...),
    duration: str = Form(...),
    badge: str = Form("Yangi"),
    description: str = Form("")
):
    courses = get_courses()
    for c in courses:
        if c.get("id") == id:
            c["name"] = name
            c["price"] = format_course_price(price)
            c["duration"] = duration
            c["badge"] = badge
            c["description"] = description
            break
    write_json("courses.json", courses)
    sync_courses_to_html(courses)
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/admin/api/edit-result")
async def edit_result_endpoint(
    request: Request,
    id: int = Form(...),
    student_name: str = Form(...),
    score: str = Form(...),
    image_file: Optional[UploadFile] = File(None),
    image_url: Optional[str] = Form(None),
    details: str = Form(""),
    description: str = Form(""),
    telegram_post_url: str = Form(""),
    video_url: str = Form("")
):
    results = get_results()
    for r in results:
        if r.get("id") == id:
            r["student_name"] = student_name
            r["score"] = score
            r["details"] = details
            r["description"] = description
            r["telegram_post_url"] = telegram_post_url.strip() if telegram_post_url else ""
            r["video_url"] = video_url.strip() if video_url else ""

            # Yangi rasm yuklansa almashtirish
            if image_file and image_file.filename:
                ext = Path(image_file.filename).suffix.lower()
                if not ext or ext not in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
                    ext = ".jpg"
                filename = f"result_{int(time.time())}_{uuid.uuid4().hex[:6]}{ext}"
                save_path = UPLOADS_DIR / filename
                content = await image_file.read()
                with open(save_path, "wb") as f:
                    f.write(content)
                try:
                    netlify_uploads = BASE_DIR / "netlify_app" / "uploads"
                    netlify_uploads.mkdir(parents=True, exist_ok=True)
                    with open(netlify_uploads / filename, "wb") as nf:
                        nf.write(content)
                except Exception:
                    pass
                r["image_url"] = f"/static/uploads/{filename}"
            elif image_url and image_url.strip():
                r["image_url"] = image_url.strip()
            break
    write_json("results.json", results)
    sync_results_to_html(results)
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/admin/api/edit-placement-q")
async def edit_placement_question(
    request: Request,
    id: int = Form(...),
    question: str = Form(...),
    opt0: str = Form(...),
    opt1: str = Form(...),
    opt2: str = Form(...),
    opt3: str = Form(...),
    answer: int = Form(...)
):
    questions = get_placement_test()
    for q in questions:
        if q.get("id") == id:
            q["question"] = question
            q["options"] = [opt0, opt1, opt2, opt3]
            q["answer"] = int(answer)
            break
    write_json("placement_test.json", questions)
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/admin/api/edit-bonus-q")
async def edit_bonus_question(
    request: Request,
    id: int = Form(...),
    question: str = Form(...),
    opt0: str = Form(...),
    opt1: str = Form(...),
    opt2: str = Form(...),
    opt3: str = Form(...),
    answer: int = Form(...),
    explanation: str = Form("")
):
    questions = get_bonus_test()
    for q in questions:
        if q.get("id") == id:
            q["question"] = question
            q["options"] = [opt0, opt1, opt2, opt3]
            q["answer"] = int(answer)
            q["explanation"] = explanation
            break
    write_json("bonus_test.json", questions)
    return RedirectResponse(url="/admin", status_code=303)

@app.post("/admin/api/delete-promocode")
async def delete_promocode_endpoint(request: Request, code: str = Form(...)):
    settings = get_settings()
    promos = settings.get("promocodes", [])
    promos = [p for p in promos if p.get("code") != code]
    settings["promocodes"] = promos
    write_json("settings.json", settings)
    return RedirectResponse(url="/admin", status_code=303)

@app.get("/admin/api/export-excel")
async def export_excel_web(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    students = await db.get_all_students()
    excel_stream = create_students_excel(students)
    return Response(
        content=excel_stream.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=WallStreet_Lidlar_Bazasi.xlsx"}
    )

@app.get("/admin/api/download-test-template")
async def download_test_template_endpoint(request: Request):
    """Adminlar uchun Excel test shablonini yuklab berish"""
    stream = generate_test_template_excel()
    return Response(
        content=stream.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=WallStreet_Placement_Test_Shablon.xlsx"}
    )

@app.post("/admin/api/upload-test-excel")
async def upload_test_excel_endpoint(request: Request, excel_file: UploadFile = File(...)):
    """Admin to'ldirgan Excel faylni qabul qilib, saytdagi testni yangilash"""
    if not excel_file.filename:
        return RedirectResponse(url="/admin?error=Fayl+tanlanmadi", status_code=303)

    content = await excel_file.read()
    try:
        new_questions, errors = parse_test_excel(content)
        if not new_questions:
            return RedirectResponse(url="/admin?error=Excel+faylda+savollar+topilmadi", status_code=303)

        # 1. placement_test.json ga yozish
        write_json("placement_test.json", new_questions)

        # 2. Sayt va Web App fayllariga (index.html) avtomatik sinxronlash
        sync_questions_to_html(new_questions)

        return RedirectResponse(url="/admin?tab=placement&success=Test+savollari+muvaffaqiyatli+yangilandi", status_code=303)
    except Exception as e:
        logger.error(f"Error parsing test excel: {e}")
        return RedirectResponse(url="/admin?error=Excel+faylni+o'qishda+xatolik", status_code=303)

@app.get("/api/placement-test")
async def get_placement_test_api():
    """Web App uchun doimiy yangi test savollari API si"""
    return JSONResponse(get_placement_test())

@app.get("/api/check-promocode")
async def check_promocode_api(code: str = ""):
    """Foydalanuvchi kiritgan promokodni maxfiy tekshirish (ommaga barcha promokodlarni bermaydi)"""
    code = code.strip().upper()
    if not code:
        return JSONResponse({"valid": False, "message": "Iltimos, promokodni kiriting."})

    settings = get_settings()
    promos = settings.get("promocodes", [])
    for p in promos:
        if p.get("code", "").upper() == code and p.get("is_active", True):
            return JSONResponse({
                "valid": True,
                "code": p.get("code"),
                "discount": p.get("discount", "Chegirma"),
                "description": p.get("description", "")
            })
    return JSONResponse({"valid": False, "message": "Bunday promokod topilmadi yoki muddati o'tgan."})

@app.get("/api/courses")
async def get_courses_api():
    """Web App uchun kurslar ro'yxati API si"""
    return JSONResponse(get_courses())

@app.get("/api/results")
async def get_results_api():
    """Web App uchun natijalar ro'yxati API si"""
    return JSONResponse(get_results())

@app.get("/api/user-status")
async def get_user_status_api(uid: int = 0):
    """Foydalanuvchining ariza holati va test urinishlari sonini qaytarish"""
    status = await db.get_student_attempts(uid)
    return JSONResponse(status)

@app.post("/admin/api/grant-attempt")
async def grant_attempt_endpoint(request: Request, telegram_id: int = Form(...), count: int = Form(1)):
    """Admindan foydalanuvchiga qo'shimcha test topshirish imkoniyati qo'shish"""
    if not is_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    await db.grant_student_attempts(telegram_id, int(count))
    return RedirectResponse(url="/admin?tab=leads&success=Test+imkoniyati+muvaffaqiyatli+qoshildi", status_code=303)

@app.post("/admin/api/reset-attempts")
async def reset_attempts_endpoint(request: Request, telegram_id: int = Form(...), total_allowed: int = Form(1)):
    if not is_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    await db.set_student_attempts(telegram_id, int(total_allowed))
    return RedirectResponse(url="/admin?tab=leads&success=Urinishlar+yangilandi", status_code=303)

@app.get("/api/schedules")
async def get_schedules_api():
    """Web App uchun guruh jadvallari va o'rinlar soni API si"""
    return JSONResponse(get_schedules())

@app.post("/admin/api/add-schedule")
async def add_schedule_endpoint(
    request: Request,
    type: str = Form(...),
    level: str = Form(...),
    days: str = Form(...),
    time: str = Form(...),
    current_students: int = Form(0),
    max_students: int = Form(12)
):
    if not is_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    schedules = get_schedules()
    new_id = (max([s.get("id", 0) for s in schedules]) + 1) if schedules else 1
    schedules.append({
        "id": new_id,
        "type": type,
        "level": level,
        "days": days,
        "time": time,
        "current_students": int(current_students),
        "max_students": int(max_students)
    })
    write_json("schedules.json", schedules)
    sync_schedules_to_html(schedules)
    return RedirectResponse(url="/admin?tab=schedule&success=Guruh+jadvali+qoshildi", status_code=303)

@app.post("/admin/api/edit-schedule")
async def edit_schedule_endpoint(
    request: Request,
    id: int = Form(...),
    type: str = Form(...),
    level: str = Form(...),
    days: str = Form(...),
    time: str = Form(...),
    current_students: int = Form(...),
    max_students: int = Form(...)
):
    if not is_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    schedules = get_schedules()
    for s in schedules:
        if s.get("id") == id:
            s["type"] = type
            s["level"] = level
            s["days"] = days
            s["time"] = time
            s["current_students"] = int(current_students)
            s["max_students"] = int(max_students)
            break
    write_json("schedules.json", schedules)
    sync_schedules_to_html(schedules)
    return RedirectResponse(url="/admin?tab=schedule&success=Guruh+jadvali+yangilandi", status_code=303)

@app.post("/admin/api/delete-schedule")
async def delete_schedule_endpoint(request: Request, id: int = Form(...)):
    if not is_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    schedules = get_schedules()
    schedules = [s for s in schedules if s.get("id") != id]
    write_json("schedules.json", schedules)
    sync_schedules_to_html(schedules)
    return RedirectResponse(url="/admin?tab=schedule&success=Guruh+ochirildi", status_code=303)

class ScheduleEnrollPayload(BaseModel):
    schedule_id: int
    telegram_id: int = 0
    full_name: str
    phone: str
    group_info: str = ""

@app.post("/api/enroll-schedule")
async def enroll_schedule_api(payload: ScheduleEnrollPayload):
    """Guruhga qo'shilish arizasini qabul qilish"""
    schedules = get_schedules()
    target_group = None
    for s in schedules:
        if s.get("id") == payload.schedule_id:
            curr = s.get("current_students", 0)
            max_s = s.get("max_students", 12)
            if curr < max_s:
                s["current_students"] = curr + 1
                target_group = s
            break

    if target_group:
        write_json("schedules.json", schedules)
        sync_schedules_to_html(schedules)

    # Receptionga xabar
    if bot_instance:
        msg = (
            f"🔥 <b>YANGI ARIZA (Guruhga qo'shilish)</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>O'quvchi:</b> {payload.full_name}\n"
            f"📱 <b>Telefon:</b> {payload.phone}\n"
            f"💬 <b>Telegram ID:</b> <code>{payload.telegram_id}</code>\n"
            f"👥 <b>Tanlangan guruh:</b> {target_group.get('type') if target_group else payload.group_info} ({target_group.get('level') if target_group else ''})\n"
            f"⏰ <b>Vaqti:</b> {target_group.get('days', '')} {target_group.get('time', '')}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"<i>Menejer 15 daqiqa ichida qo'ng'iroq qilishi lozim!</i>"
        )
        kb = get_manager_lead_kb(telegram_id=payload.telegram_id, phone=payload.phone)
        if MANAGER_GROUP_ID != 0:
            try:
                await bot_instance.send_message(chat_id=MANAGER_GROUP_ID, text=msg, reply_markup=kb, parse_mode="HTML")
            except Exception as e:
                logger.warning(f"Guruhga xabar yuborilmadi: {e}")
        for aid in ADMINS:
            if aid != 0:
                try:
                    await bot_instance.send_message(chat_id=aid, text=msg, reply_markup=kb, parse_mode="HTML")
                except Exception:
                    pass

    return JSONResponse({"status": "success", "message": "Guruhga arizangiz qabul qilindi!"})

@app.get("/api/events")
async def get_events_api():
    """Web App uchun faol tadbirlar va qatnashchilar soni"""
    events = await db.get_active_events()
    return JSONResponse(events)

@app.post("/admin/api/broadcast-event")
async def broadcast_event_endpoint(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    date_time: str = Form(...),
    seats_limit: int = Form(30)
):
    """Admin panel orqali tadbir yaratish va barcha foydalanuvchilarga hamda guruhlarga e'lon qilish"""
    if not is_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=303)

    event_id = await db.add_event(
        title=title,
        description=description,
        date_time=date_time,
        seats_limit=seats_limit
    )

    if bot_instance:
        text = (
            f"🎉 <b>YANGI TADBIR / MASTER-KLASS!</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📌 <b>{title}</b>\n\n"
            f"📅 <b>Vaqti:</b> {date_time}\n"
            f"👥 <b>Mavjud joylar:</b> {seats_limit} ta\n\n"
            f"ℹ️ {description}\n\n"
            f"<i>Qatnashish mutlaqo bepul! Joylar soni cheklangan, ulgurib qoling! 👇</i>"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎟 Ro'yxatdan o'tish (Qo'shilish)", callback_data=f"join_event:{event_id}")],
            [InlineKeyboardButton(text="📱 Web Appda ko'rish", web_app=WebAppInfo(url=f"{WEBAPP_BASE_URL}/?tab=schedule"))]
        ])

        user_ids = await db.get_all_students_telegram_ids()
        for uid in user_ids:
            try:
                await bot_instance.send_message(chat_id=uid, text=text, reply_markup=kb, parse_mode="HTML")
                await asyncio.sleep(0.04)
            except Exception:
                pass

        if MANAGER_GROUP_ID != 0:
            try:
                await bot_instance.send_message(chat_id=MANAGER_GROUP_ID, text=f"📢 <b>Yangi tadbir e'loni berildi:</b>\n\n" + text, reply_markup=kb, parse_mode="HTML")
            except Exception:
                pass

    return RedirectResponse(url="/admin?tab=events&success=Tadbir+yaratildi+va+barchaga+tarqatildi", status_code=303)

@app.post("/admin/api/delete-event")
async def delete_event_endpoint(request: Request, event_id: int = Form(...)):
    if not is_authenticated(request):
        return RedirectResponse(url="/admin/login", status_code=303)
    await db.delete_event(event_id)
    return RedirectResponse(url="/admin?tab=events&success=Tadbir+ochirildi", status_code=303)

@app.get("/admin/api/event-participants")
async def event_participants_endpoint(request: Request, event_id: int):
    if not is_authenticated(request):
        return JSONResponse({"status": "error", "message": "Unauthorized"}, status_code=401)
    participants = await db.get_event_participants(event_id)
    return JSONResponse(participants)

class JoinEventPayload(BaseModel):
    event_id: int
    user_id: int = 0
    full_name: str
    phone: str

@app.post("/api/join-event")
async def join_event_api(payload: JoinEventPayload):
    """Web App orqali tadbirga ro'yxatdan o'tish"""
    success = await db.register_event(
        event_id=payload.event_id,
        telegram_id=payload.user_id,
        full_name=payload.full_name,
        phone=payload.phone
    )
    if not success:
        return JSONResponse({"status": "error", "message": "Tadbirda bo'sh joy qolmagan yoki siz allaqachon ro'yxatdan o'tgansiz."})

    if bot_instance:
        alert = (
            f"🎟 <b>YANGI TADBIR QATNASHCHISI (Web App orqali)</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>O'quvchi:</b> {payload.full_name}\n"
            f"📱 <b>Telefon:</b> {payload.phone}\n"
            f"🆔 <b>Telegram ID:</b> <code>{payload.user_id}</code>\n"
            f"📌 <b>Tadbir ID:</b> #{payload.event_id}\n"
            f"━━━━━━━━━━━━━━━━━━"
        )
        if MANAGER_GROUP_ID != 0:
            try:
                await bot_instance.send_message(chat_id=MANAGER_GROUP_ID, text=alert, parse_mode="HTML")
            except Exception:
                pass
        for aid in ADMINS:
            if aid != 0:
                try:
                    await bot_instance.send_message(chat_id=aid, text=alert, parse_mode="HTML")
                except Exception:
                    pass

    return JSONResponse({"status": "success", "message": "Tadbirga muvaffaqiyatli ro'yxatdan o'tdingiz!"})



