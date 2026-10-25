# 🎓 EduBot — O'quv Markazi Qabul va Reception Tizimi

Ushbu tizim **"Markaz Rahbari Uchun EduBot Strategik Qo'llanmasi"** konsepsiyasi va reglamenti asosida ishlab chiqilgan.
EduBot markazning 24/7 ishlaydigan "raqamli sotuv menejeri" bo'lib, o'quvchini jalb qiladi, bilim darajasini aniqlaydi va arizani reception/menejerlar guruhiga tayyor holda yetkazadi.

---

## 📌 Asosiy Imkoniyatlar va Voronka (Marketing Funnel)

1. **Jalb Qilish & UTM Treking:**
   - Reklama manbalarini aniqlash (masalan: `t.me/bot?start=insta_reels`, `t.me/bot?start=tg_ads`, `t.me/bot?start=banner_chilonzor`).
   - O'quvchi birgina tugma bilan ism va telefon raqamini tasdiqlaydi.
2. **Saralash Testi (Placement Test):**
   - Til/fan bo'yicha interaktiv savollar (A1, A2, B1, B2).
   - Real vaqtda ball va bilim darajasini hisoblash.
3. **Sovg'a & Kupon (Incentive):**
   - Natijaga qarab 1-bepul sinov darsi va maxsus chegirma kuponi taqdim etiladi.
   - O'quvchiga mos guruh vaqtlari taklif qilinadi.
4. **Menejerlar va Reception Guruhiga Integratsiya:**
   - Yangi o'quvchi ro'yxatdan o'tishi bilan xodimlar guruhiga to'liq lid kartasi boradi:
     - F.I.O, telefon raqami, Telegram profili, aniqlangan darajasi, tanlangan dars vaqti, reklama manbasi va kupon kodi.
   - **Reglament (15 daqiqa ichida):** Menejer uchun 1 tugma bilan to'g'ridan-to'g'ri qo'ng'iroq qilish (`tel:`) imkoniyati.
   - Inline status boshqaruvi: `Bog'lanildi`, `Sinov darsiga yozildi`, `Guruhga qo'shildi`, `Rad etildi`.
   - Sinov darsi sanasi belgilanganda o'quvchiga avtomatik tasdiqlash va lokatsiya xabari boradi.
5. **Yangiliklar, Tadbirlar va Ochiq Darslar (Events):**
   - Speaking club, mahorat darslari, Mock imtihonlarni e'lon qilish.
   - O'quvchilar 1 tugma orqali joy band qiladi (`Joy band qilish 🎟`).
6. **Rahbar Paneli & Tahlil:**
   - 📊 **Statistika:** Jami lidlar, bugungi arizalar, menejerlar ishlash holati, darajalar statistikasi va reklama manbalari tahlili.
   - 📁 **Mijozlar Bazasi (Oltin Fond):** Barcha o'quvchilar ro'yxatini to'liq tartiblangan zamonaviy **Excel (.xlsx)** formatida yuklab olish.
   - 📢 **Ommaviy Xabarnoma (Broadcast):** Barchaga yoki filtrlangan guruhlarga (masalan: faqat A1-A2 yoki faqat yangi lidlar) xabar tarqatish.

---

## 📂 Loyiha Tuzilishi

```text
d:\Wall Stree uchun bot\
├── bot.py                # Asosiy ishga tushirish fayli
├── config.py             # Konfiguratsiya, test savollari, kurslar va sozlamalar
├── database.py           # SQLite asinxron ma'lumotlar bazasi (aiosqlite)
├── handlers/
│   ├── states.py         # FSM (Finite State Machine) holatlari
│   ├── start.py          # /start komandasi va UTM manba aniqlash
│   ├── registration.py   # Ism va telefon qabul qilish
│   ├── test_quiz.py      # Placement test va saralash voronkasi
│   ├── admin_group.py    # Reception/Menejerlar guruhidagi lidlar bilan ishlash
│   ├── admin_panel.py    # Rahbar paneli: statistika, Excel eksport, xabarnoma
│   └── student_menu.py   # Kurslar, narxlar, lokatsiya, kupon va tadbirlar
├── keyboards/
│   ├── default_kb.py     # Kontakt yuborish va asosiy menyu klaviaturalari
│   └── inline_kb.py      # Test savollari, menejer statuslari va boshqaruv
├── services/
│   ├── export_excel.py   # Chiroyli Excel (.xlsx) hisobot generatori
│   └── scheduler.py      # Sinov darsi eslatmalari va tasdiqlash xizmati
├── .env.example          # Sozlamalar namunasi
└── README.md             # Ushbu qo'llanma
```

---

## 🚀 Ishga Tushirish Bo'yicha Qo'llanma

### 1. Sozlamalarni kiritish (.env)

Loyiha papkasidagi `.env.example` faylidan nusxa olib, `.env` faylini yarating:

```bash
cp .env.example .env
```

`.env` faylini ochib, o'z parametrlaringizni kiriting:

```env
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
ADMIN_ID=123456789
MANAGER_GROUP_ID=-1001234567890
DB_NAME=edubot.db
```

> **Izoh:**
> - `BOT_TOKEN`: [@BotFather](https://t.me/BotFather) dan olingan bot tokeni.
> - `ADMIN_ID`: Rahbarning Telegram ID si (bir nechta bo'lsa vergul bilan: `123456,789101`).
> - `MANAGER_GROUP_ID`: Reception xodimlari va menejerlar jamlangan guruh/superguruh ID si (masalan: `-100192837465`).

### 2. Botni ishga tushirish

Terminalda quyidagi buyruqni bering:

```powershell
python bot.py
```

Bot ishga tushganda adminlarga "EduBot ishga tushdi!" xabarini yuboradi.

---

## 🎯 Reklama Kampaniyalarida Havolalar (UTM Tracking)

PDF strategiyasiga muvofiq, reklama byudjetini o'lchash uchun turli manbalarga maxsus havolalar bering:

- **Instagram Reels:** `https://t.me/botingiz_username?start=insta_reels`
- **Instagram Bio:** `https://t.me/botingiz_username?start=insta_bio`
- **Telegram Kanal:** `https://t.me/botingiz_username?start=tg_post`
- **Chilonzor Filial Banneri:** `https://t.me/botingiz_username?start=chilonzor_banner`

Rahbar bot ichidagi **"📊 To'liq Statistika"** bo'limida qaysi reklama qancha real o'quvchi olib kelganini aniq ko'rib turadi.
