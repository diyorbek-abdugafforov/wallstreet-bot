import aiosqlite
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from config import DB_NAME

class Database:
    def __init__(self, db_path: str = DB_NAME):
        self.db_path = db_path

    async def init(self):
        """Barcha jadvallarni yaratish"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS students (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE,
                    username TEXT,
                    full_name TEXT,
                    phone TEXT,
                    utm_source TEXT DEFAULT 'organic',
                    level TEXT,
                    test_score INTEGER DEFAULT 0,
                    preferred_schedule TEXT,
                    coupon_code TEXT,
                    status TEXT DEFAULT 'Yangi',
                    trial_date TEXT,
                    manager_note TEXT,
                    manager_id INTEGER,
                    reminder_sent INTEGER DEFAULT 0,
                    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    date_time TEXT,
                    seats_limit INTEGER DEFAULT 30,
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS event_registrations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id INTEGER,
                    telegram_id INTEGER,
                    full_name TEXT,
                    phone TEXT,
                    UNIQUE(event_id, telegram_id)
                );
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS admins (
                    telegram_id INTEGER PRIMARY KEY,
                    full_name TEXT,
                    role TEXT DEFAULT 'admin',
                    added_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Migratsiyalar (yangi ustunlar xatosiz qo'shiladi)
            for col, col_type in [
                ("test_attempts_allowed", "INTEGER DEFAULT 1"),
                ("test_attempts_used", "INTEGER DEFAULT 0"),
                ("application_submitted", "INTEGER DEFAULT 0")
            ]:
                try:
                    await db.execute(f"ALTER TABLE students ADD COLUMN {col} {col_type};")
                except Exception:
                    pass

            await db.commit()

    async def add_or_update_student(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        utm_source: str = "organic"
    ) -> bool:
        """Yangi o'quvchini qo'shish yoki mavjud bo'lsa yangilash"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT id FROM students WHERE telegram_id = ?", (telegram_id,)
            )
            existing = await cursor.fetchone()
            if existing:
                await db.execute(
                    "UPDATE students SET username = ? WHERE telegram_id = ?",
                    (username, telegram_id)
                )
                await db.commit()
                return False
            else:
                await db.execute(
                    """
                    INSERT INTO students (telegram_id, username, utm_source)
                    VALUES (?, ?, ?)
                    """,
                    (telegram_id, username, utm_source)
                )
                await db.commit()
                return True

    async def set_student_contact(self, telegram_id: int, full_name: str, phone: str):
        """Ism va telefon raqamni saqlash"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE students 
                SET full_name = ?, phone = ? 
                WHERE telegram_id = ?
                """,
                (full_name, phone, telegram_id)
            )
            await db.commit()

    async def set_test_result(self, telegram_id: int, score: int, level: str, coupon: str):
        """Test natijasi va darajani saqlash"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE students 
                SET test_score = ?, level = ?, coupon_code = ? 
                WHERE telegram_id = ?
                """,
                (score, level, coupon, telegram_id)
            )
            await db.commit()

    async def set_preferred_schedule(self, telegram_id: int, schedule: str):
        """Tanlangan guruh vaqtini saqlash"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE students 
                SET preferred_schedule = ? 
                WHERE telegram_id = ?
                """,
                (schedule, telegram_id)
            )
            await db.commit()

    async def update_status(self, telegram_id: int, status: str, manager_id: Optional[int] = None, note: Optional[str] = None):
        """Lid statusini o'zgartirish (Reception/Menejer amali)"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE students 
                SET status = ?, manager_id = COALESCE(?, manager_id), manager_note = COALESCE(?, manager_note)
                WHERE telegram_id = ?
                """,
                (status, manager_id, note, telegram_id)
            )
            await db.commit()

    async def set_trial_date(self, telegram_id: int, trial_date: str):
        """Sinov darsi sanasini belgilash"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE students 
                SET trial_date = ?, status = 'Sinov darsiga yozildi'
                WHERE telegram_id = ?
                """,
                (trial_date, telegram_id)
            )
            await db.commit()

    async def get_student(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """O'quvchi ma'lumotlarini olish"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM students WHERE telegram_id = ?", (telegram_id,)
            )
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return None

    async def get_all_students(self, filter_level: Optional[str] = None, filter_status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Barcha yoki filtr bo'yicha o'quvchilarni olish"""
        query = "SELECT * FROM students WHERE 1=1"
        params = []
        if filter_level:
            query += " AND level = ?"
            params.append(filter_level)
        if filter_status:
            query += " AND status = ?"
            params.append(filter_status)
        query += " ORDER BY id DESC"

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query, tuple(params))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_stats(self) -> Dict[str, Any]:
        """Rahbar uchun to'liq statistika"""
        today = date.today().strftime("%Y-%m-%d")
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            # Jami va bugungi lidlar
            cursor = await db.execute("SELECT COUNT(*) as total FROM students")
            total = (await cursor.fetchone())["total"]

            cursor = await db.execute("SELECT COUNT(*) as today_count FROM students WHERE registered_at LIKE ?", (f"{today}%",))
            today_count = (await cursor.fetchone())["today_count"]

            # Statuslar bo'yicha
            cursor = await db.execute("SELECT status, COUNT(*) as count FROM students GROUP BY status")
            status_rows = await cursor.fetchall()
            status_counts = {r["status"]: r["count"] for r in status_rows}

            # Darajalar bo'yicha
            cursor = await db.execute("SELECT level, COUNT(*) as count FROM students WHERE level IS NOT NULL GROUP BY level")
            level_rows = await cursor.fetchall()
            level_counts = {r["level"]: r["count"] for r in level_rows}

            # Reklama manbalari (UTM)
            cursor = await db.execute("SELECT utm_source, COUNT(*) as count FROM students GROUP BY utm_source")
            utm_rows = await cursor.fetchall()
            utm_counts = {r["utm_source"]: r["count"] for r in utm_rows}

            return {
                "total": total,
                "today": today_count,
                "status_counts": status_counts,
                "level_counts": level_counts,
                "utm_counts": utm_counts
            }

    # Tadbirlar (Events)
    async def add_event(self, title: str, description: str, date_time: str, seats_limit: int = 30) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                INSERT INTO events (title, description, date_time, seats_limit)
                VALUES (?, ?, ?, ?)
                """,
                (title, description, date_time, seats_limit)
            )
            await db.commit()
            return cursor.lastrowid

    async def get_active_events(self) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT e.*, 
                       (SELECT COUNT(*) FROM event_registrations r WHERE r.event_id = e.id) as registered_count
                FROM events e
                WHERE e.is_active = 1
                ORDER BY e.id DESC
                """
            )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def register_event(self, event_id: int, telegram_id: int, full_name: str, phone: str) -> bool:
        """Tadbirga ro'yxatdan o'tish"""
        async with aiosqlite.connect(self.db_path) as db:
            # Joy qolganini tekshirish
            cursor = await db.execute("SELECT seats_limit FROM events WHERE id = ?", (event_id,))
            event = await cursor.fetchone()
            if not event:
                return False

            cursor = await db.execute("SELECT COUNT(*) FROM event_registrations WHERE event_id = ?", (event_id,))
            count = (await cursor.fetchone())[0]
            if count >= event[0]:
                return False # Joy qolmagan

            try:
                await db.execute(
                    """
                    INSERT INTO event_registrations (event_id, telegram_id, full_name, phone)
                    VALUES (?, ?, ?, ?)
                    """,
                    (event_id, telegram_id, full_name, phone)
                )
                await db.commit()
                return True
            except Exception:
                return False # Allaqachon ro'yxatdan o'tgan bo'lishi mumkin

    # --- ADMINLAR BOSHQARUVI ---
    async def add_admin(self, telegram_id: int, full_name: str, role: str = 'admin', added_by: int = 0) -> bool:
        """Yangi admin qo'shish"""
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute(
                    """
                    INSERT OR REPLACE INTO admins (telegram_id, full_name, role, added_by)
                    VALUES (?, ?, ?, ?)
                    """,
                    (telegram_id, full_name, role, added_by)
                )
                await db.commit()
                return True
            except Exception as e:
                print(f"Admin qo'shishda xato: {e}")
                return False

    async def remove_admin(self, telegram_id: int) -> bool:
        """Adminni o'chirish / chiqarib tashlash"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("DELETE FROM admins WHERE telegram_id = ?", (telegram_id,))
            await db.commit()
            return cursor.rowcount > 0

    async def get_admins(self) -> List[Dict[str, Any]]:
        """Barcha adminlar ro'yxatini olish"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM admins ORDER BY created_at DESC")
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def is_admin(self, telegram_id: int) -> bool:
        """Telegram ID admin ekanligini tekshirish"""
        from config import ADMINS
        if telegram_id in ADMINS:
            return True
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT telegram_id FROM admins WHERE telegram_id = ?", (telegram_id,))
            row = await cursor.fetchone()
            return row is not None

    # --- TEST URINISHLARI & ARIZALAR ---
    async def get_student_attempts(self, telegram_id: int) -> Dict[str, Any]:
        """Foydalanuvchining test topshirish imkoniyati va ariza holatini olish"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT test_attempts_allowed, test_attempts_used, application_submitted, full_name, phone, level FROM students WHERE telegram_id = ?",
                (telegram_id,)
            )
            row = await cursor.fetchone()
            if row:
                allowed = row[0] if row[0] is not None else 1
                used = row[1] if row[1] is not None else 0
                submitted = row[2] if row[2] is not None else 0
                return {
                    "allowed": allowed,
                    "used": used,
                    "left": max(0, allowed - used),
                    "application_submitted": bool(submitted),
                    "full_name": row[3] or "",
                    "phone": row[4] or "",
                    "level": row[5] or ""
                }
            return {
                "allowed": 1,
                "used": 0,
                "left": 1,
                "application_submitted": False,
                "full_name": "",
                "phone": "",
                "level": ""
            }

    async def increment_student_attempt(self, telegram_id: int):
        """Test topshirilganda urinishni sarflash va arizani topshirildi deb belgilash"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE students SET test_attempts_used = COALESCE(test_attempts_used, 0) + 1, application_submitted = 1 WHERE telegram_id = ?",
                (telegram_id,)
            )
            await db.commit()

    async def grant_student_attempts(self, telegram_id: int, count: int = 1) -> bool:
        """Admindan qo'shimcha test topshirish imkoniyati berish"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "UPDATE students SET test_attempts_allowed = COALESCE(test_attempts_allowed, 1) + ? WHERE telegram_id = ?",
                (count, telegram_id)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def set_student_attempts(self, telegram_id: int, total_allowed: int) -> bool:
        """Test topshirish imkoniyati sonini aniq o'rnatish"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "UPDATE students SET test_attempts_allowed = ? WHERE telegram_id = ?",
                (total_allowed, telegram_id)
            )
            await db.commit()
            return cursor.rowcount > 0

    async def set_application_submitted(self, telegram_id: int, status: int = 1):
        """Ariza topshirilganlik holatini o'rnatish"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE students SET application_submitted = ? WHERE telegram_id = ?",
                (status, telegram_id)
            )
            await db.commit()

    async def get_all_students_telegram_ids(self) -> List[int]:
        """Tadbir e'lonlarini hamma foydalanuvchilarga yuborish uchun ID lar"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT DISTINCT telegram_id FROM students WHERE telegram_id IS NOT NULL AND telegram_id != 0")
            rows = await cursor.fetchall()
            return [r[0] for r in rows if r[0]]

    async def get_event_participants(self, event_id: int) -> List[Dict[str, Any]]:
        """Tadbirga ro'yxatdan o'tganlar ro'yxati"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM event_registrations WHERE event_id = ? ORDER BY id DESC",
                (event_id,)
            )
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def delete_event(self, event_id: int) -> bool:
        """Tadbirni o'chirish"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM event_registrations WHERE event_id = ?", (event_id,))
            cursor = await db.execute("DELETE FROM events WHERE id = ?", (event_id,))
            await db.commit()
            return cursor.rowcount > 0

