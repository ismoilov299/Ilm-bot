"""Testlar uchun umumiy sozlamalar.

Mavjud kod import paytida ``data/config.py`` orqali ``BOT_TOKEN`` va ``ADMINS`` ni o'qiydi va
``loader.py`` da ``Bot`` obyektini yaratadi. Testlar haqiqiy token va tarmoqsiz ishlashi uchun
soxta qiymatlar ilova modullari import qilinishidan oldin o'rnatiladi.
"""

import os

os.environ["BOT_TOKEN"] = "123456789:TEST-TOKEN"
os.environ["ADMINS"] = "1"
