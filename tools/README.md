# tools/

Bir martalik tahlil skriptlari. Ular yangi tizimning bir qismi emas: natijalar (`seeds/*.json`) allaqachon repoda.
Skriptlar kelib chiqishni ko'rsatish va kerak bo'lsa seed'ni qayta yaratish uchun saqlangan. Barchasi **faqat o'qiydi**
va tashqi kodni ishga tushirmaydi (`ast` bilan tahlil qiladi). Python: `python -I -X utf8 ...` (Windows konsolida UTF-8 uchun `-X utf8` kerak).

## prayer_fit/: namoz vaqtini hisoblash

- `pt.py`: PrayTimes algoritmi (quyosh holati). `compute(date, lat, lng, tz=5.0, fajr=15.0, isha=15.0, rise=0.833, asr_f=2)`
  kasr soatlarda `[bomdod, quyosh, peshin, asr, shom, xufton]` qaytaradi. **Yakuniy qoidalar** (`docs/ARCHITECTURE.md`, 6.2.1):
  `fajr=15`, `isha=15`, `asr_f=2`, hamda natijaga ofsetlar: bomdod **−5 daqiqa**, shom **+5 daqiqa**, qolganlari 0.
  Bosqich 3 da bu fayl `ilmbot/integrations/prayer_calc.py` ga o'tkaziladi.
- `fit.py`: parametrlarni moslash va tekshirish. Diniy idora jadvali kerak: v1 repodagi `data/dataNamaz.sqlite`
  (`https://github.com/davlatovv/ilm_yo-lida.telegramBot`, 13 shahar × 245 kun, 2022). Ishlatish:
  `python -I -X utf8 fit.py <pt.py papkasi> <dataNamaz.sqlite yo'li> fit` (yoki oxirgi argument `bad`, jadvaldagi buzilgan qatorlarni ko'rsatadi).

## seed_build/: menyu seed'ini tiklash

Manbalar: v1 repo (yuqoridagi havola) va Telegram Desktop'dan kanal eksporti (`result.json`, **gitga qo'yilmaydi**).

```
python -I -X utf8 extract_v1.py    <v1repo>  > v1_posts.json      # callback -> post ID
python -I -X utf8 extract_lists.py <v1repo>  > v1_lists.json      # raqamli ro'yxatlar (sura, kitob...)
python -I -X utf8 map_pages.py     <v1repo>  > v1_pagenames.json  # duo/zikr/salovat nomlari
python -I -X utf8 build_seed.py    <json'lar papkasi> <repo>/seeds/menu_seed.json   # v1 daraxti
python -I -X utf8 build_seed2.py   <repo>                          # result.json bilan boyitadi, inventarni yozadi
```
`extract_labels.py` yordamchi (tugma matnlari). `build_seed2.py` `result.json` va `seeds/menu_seed.json` ni o'qiydi, ikkala seed faylni qayta yozadi.
