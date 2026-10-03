# Refaktoring rejasi (Clean Code + SOLID)

Bu hujjat kodni to'liq o'qib chiqib tuzildi. Maqsad: xatti-harakatni o'zgartirmasdan, xavfsizlik va tuzilishni
bosqichma-bosqich yaxshilash. Har bosqich alohida commit bo'ladi.

## 1. Joriy holat

- Bot: aiogram 2.21 (polling), `MemoryStorage`.
- Admin panel: Django 4.1 (`backend/ilmbot`), kontent va foydalanuvchilar shu yerda boshqariladi.
- DB: bitta SQLite fayl (`backend/ilmbot/db.sqlite3`, `.gitignore` da, repoda yo'q). Bot va Django bir xil faylni ishlatadi.
- Jadvallar Django migratsiyalaridan keladi: `category_categorybutton`, `category_categoryregion`, `bot_post`,
  `bot_namazuser` va boshqalar. `namaz` jadvali hech qaysi modelda yo'q, lekin `DataBase.get_times/get_bugun` unga murojaat qiladi.

## 2. Topilgan muammolar

### 2.1 Xavfsizlik (eng yuqori ustuvorlik)
| Joyi | Muammo |
|---|---|
| `keyboards/inline/regions.py` | f-string bilan SQL (`WHERE id={region_id}`, `user_id={user_id}`). `region_id` callback ma'lumotidan keladi, ya'ni foydalanuvchi boshqaradi. |
| `prayer_time/vaqt.py` | `UPDATE ... SET bomdod='{bomdod}' ... WHERE name='{city}'`, tashqi API javobi to'g'ridan-to'g'ri SQL ga tushadi. |
| `backend/ilmbot/ilmbot/settings.py` | `SECRET_KEY` repoda, `DEBUG=True`, `ALLOWED_HOSTS=['*']`. |
| `backend/ilmbot/ilmbot/urls.py` | Admin panel `""` (ildiz) yo'lida. |
| `handlers/users/admins.py` | Broadcast holati (`broadcast_text`) handleri `user_id=ADMINS` filtrisiz; xatolar `except: pass` bilan yutiladi. |

### 2.2 Haqiqiy xatolar
1. **Handlerlar ro'yxatdan o'tish tartibiga bog'liq.** `keyboards/inline/callback.py` da
   `@dp.callback_query_handler(lambda c: True)`: bu hamma callbackni ushlaydi. U `region:`/`subscribe:` handlerlaridan
   keyin ro'yxatdan o'tgani uchun hozir ishlayapti, lekin import tartibi o'zgarsa namoz vaqti tugmalari jim ishlamay qoladi.
   Handlerlar `keyboards/` papkasida turibdi va `__init__.py` orqali import qilinadi (yashirin yon ta'sir).
2. **`scheduler()` (`app.py`)**
   - `get_prayer_times` `None` qaytarsa `enumerate(times)` yiqiladi (tekshiruv faqat `print` uchun).
   - `aioschedule.every().day.at(...).do(update_prayer_times)` har siklda qo'shiladi, lekin `run_pending()` chaqirilmaydi,
     shuning uchun kunlik yangilanish umuman ishlamaydi.
   - Vaqt `datetime.now()` bilan, vaqt zonasi ko'rsatilmagan. Server UTC bo'lsa eslatmalar 5 soat kechikadi.
   - Barcha foydalanuvchilar uchun har daqiqada DB so'rovi (N+1), region vaqtlari har foydalanuvchi uchun alohida olinadi.
   - Bir daqiqadan oshsa yoki sikl kechiksa eslatma o'tib ketadi yoki ikki marta yuboriladi.
3. **`update_prayer_times`**: Qo'qon va Marg'ilon `for city` sikli ichida har iteratsiyada qayta so'raladi (11 marta), ichida
   `WHERE name='{city}'` ga noto'g'ri qiymat yoziladi. Sinxron `requests` event loop ni bloklaydi.
4. **`DataBase` klassi**: `select_one`, `count_obuna` mavjud bo'lmagan `name` ustunini so'raydi (to'g'risi `user_name`);
   `get_times`/`get_bugun` mavjud bo'lmagan `namaz` jadvaliga; `vaqt.api_namaz` mavjud bo'lmagan `db.api_update` ga murojaat qiladi.
5. **`start.py`**: foydalanuvchi bazada bo'lmasa ham "sizni yana ko'rganimizdan xursandmiz" yoziladi.
6. **`regions.py`**: `prayer_times_callback_handler` oxiridagi `if callback_query.data.startswith('subscribe:')` bloki
   hech qachon bajarilmaydi (handler faqat `region:` uchun). Foydalanuvchi regioni hech qachon `region:` bosilganda saqlanmaydi;
   `subscribe:0` bosilganda `region_id=0` bilan ishlanadi, ya'ni eslatma regioni noto'g'ri qoladi.
7. `get_prayer_times` / `get_subscribed_users` ulanishni yopmaydi (`get_prayer_times`), `print` bilan to'la.
8. Django: `Ramadan.__str__` `ForeignKey` obyektini qaytaradi (`TypeError`); `CategoryRegion.__str__` da `return` dan keyin
   o'lik kod; `NamazUser.user_id` `IntegerField` (Telegram ID 32-bitdan katta bo'lishi mumkin, boshqa DB da yiqiladi).
9. `requirements.txt` to'liq emas (`aioschedule`, `environs`, `requests` yo'q), `Pipfile` bilan mos emas. CI faqat `pip install` qiladi.

### 2.3 Clean Code buzilishlari
- Bir xil `sqlite3.connect('backend/ilmbot/db.sqlite3')` kamida 15 joyda takrorlanadi, nisbiy yo'l (faqat repo ildizidan ishlaydi).
- `get_main_keyboard`, `main()` (start.py), `get_keyboard`: tugmalarni 2 tadan qatorga bo'lish kodi 3 marta nusxalangan (DRY).
- Qattiq yozilgan "sehrli raqamlar": kategoriya ID lari (1, 2, 3, 4, 5, 6, 7, 9, 10, 12, 15, 17, 18, 19-23, 44, 80, 307, 426, 430),
  kanal `message_id` lari (564, 655, 1362, 1532, 1537-1539). Admin paneldan ID o'zgarsa bot buziladi.
- Bir nechta funksiya bir xil nom bilan (`send_menu`, `send_tahorat`, `book_send`, `duo`, `send_zam_suralar`, `send_bilol`) qayta e'lon qilingan.
- Nom va til aralashmasi (`choose_shortes`, `loacation.py`, `masofa`, `idishka`), izohlangan eski kod, ko'p `print`.
- `app.py` da ishlatilmagan importlar (`sqlite3`, `keyboards`, `api_namaz`, `get_regions`), `prayer_time/test.py` skript sifatida repoda.
- Callback ma'lumoti formati (`"123"`, `next_ID_PAGE`, `region:NAME:ID`) tartibsiz, parse qilish `split` bilan, validatsiyasiz.
- `if __name__ == "middlewares":` kabi hiyla bilan sozlash.

### 2.4 SOLID bo'yicha
- **S**: `regions.py` bir faylda UI (klaviatura), DB, xabar matni, obuna biznes mantiqi va scheduler yordamchilarini aralashtirgan.
  `app.py` scheduler ham vaqt tekshiradi, ham bildirishnoma yuboradi.
- **O**: yangi namoz turi yoki yangi bo'lim qo'shish uchun `if/elif` zanjirini (`send_prayer_time_message`, `scheduler`) tahrirlash kerak.
- **L**: aytarli meros yo'q, buzilish yo'q.
- **I**: `DataBase` hamma narsani biladigan bitta "xudo" klass; handlerlar faqat bittasini kerak qilganda ham butun DB ga bog'lanadi.
- **D**: handlerlar to'g'ridan-to'g'ri `sqlite3` va `requests` ga bog'liq (abstraksiya yo'q), shuning uchun test yozib bo'lmaydi.

## 3–5. Maqsadli tuzilma, bajarish tartibi va ochiq savollar

Bu bo'limlar `docs/MIGRATION_2026.md` bilan almashtirildi (2026-10-03). Asosiy farqlar:

- Ma'lumotlar qatlami alohida sqlite repozitoriylari emas, **Django ORM (async)**. Sxemaning yagona manbai Django modellari bo'ladi.
- Bot aiogram 3.31 ga, Python 3.14 ga va Django 6.1 ga o'tadi. Bosqichlar tartibi va sabablari o'sha hujjatda.
- Yuqoridagi 2-bo'limdagi muammolar amalda qoladi va migratsiya davomida yopiladi (`MIGRATION_2026.md`, 10-bo'lim).
