import sqlite3

import requests
from loader import db


class NamozVaqti():

    def __init__(self, city):
        self.city = city
        self.url = 'https://islomapi.uz/api/present/day?region=' + \
            self.city
        self.response = requests.get(self.url)
        self.data = self.response.json()

    def get_sana(self):
        return self.data['date']

    def get_kun(self):
        return self.data['weekday']

    def get_namoz_vaqt(self):
        return self.data['times']

    def bomdod(self):
        return self.get_namoz_vaqt()['tong_saharlik']

    def quyosh_chiqishi(self):
        return self.get_namoz_vaqt()['quyosh']

    def peshin(self):
        return self.get_namoz_vaqt()['peshin']

    def asr(self):
        return self.get_namoz_vaqt()['asr']

    def shom(self):
        return self.get_namoz_vaqt()['shom_iftor']

    def xufton(self):
        return self.get_namoz_vaqt()['hufton']

    def day(self):
        return self.get_namoz_vaqt()['tong_saharlik'],['quyosh'],['peshin'],['asr'],['shom_iftor'],['hufton']

li = ['Toshkent', 'Andijon', 'Buxoro', 'Guliston', 'Samarqand', 'Namangan', 'Navoiy', 'Jizzax', 'Nukus', 'Qarshi', "Qo'qon", 'Xiva','Marg\'ilon']
async def api_namaz():
    for i in li:
        b = NamozVaqti(i).get_namoz_vaqt()['tong_saharlik']
        q = NamozVaqti(i).get_namoz_vaqt()['quyosh']
        p = NamozVaqti(i).get_namoz_vaqt()['peshin']
        a = NamozVaqti(i).get_namoz_vaqt()['asr']
        sh = NamozVaqti(i).get_namoz_vaqt()['shom_iftor']
        x = NamozVaqti(i).get_namoz_vaqt()['hufton']
        db.api_update(b, q, p, a, sh, x,  i)




def update_prayer_times():
    conn = sqlite3.connect('backend/ilmbot/db.sqlite3')

    cur = conn.cursor()

    for city in ["Toshkent", "Andijon", "Buxoro", "Guliston", "Samarqand", "Namangan", "Navoiy", "Jizzax", "Nukus", "Qarshi", "Xiva"]:#, "Marg'ilon"
        namoz_vaqti = NamozVaqti(city)
        print(city)

        bomdod = namoz_vaqti.bomdod()
        quyosh = namoz_vaqti.quyosh_chiqishi()
        peshin = namoz_vaqti.peshin()
        asr = namoz_vaqti.asr()
        shom = namoz_vaqti.shom()
        xufton = namoz_vaqti.xufton()

        cur.execute(f"UPDATE category_categoryregion SET bomdod='{bomdod}', quyosh='{quyosh}', peshin='{peshin}', asr='{asr}', shom='{shom}', xufton='{xufton}' WHERE name='{city}'")
        namoz_vaqti2 = NamozVaqti("Qo'qon")
        print(namoz_vaqti2)

        bomdod = namoz_vaqti2.bomdod()
        quyosh = namoz_vaqti2.quyosh_chiqishi()
        peshin = namoz_vaqti2.peshin()
        asr = namoz_vaqti2.asr()
        shom = namoz_vaqti2.shom()
        xufton = namoz_vaqti2.xufton()
        cur.execute(
            "UPDATE category_categoryregion SET bomdod=?, quyosh=?, peshin=?, asr=?, shom=?, xufton=? WHERE name=?",
            (bomdod, quyosh, peshin, asr, shom, xufton, "Qo'qon"))

        cur.execute(
            f"UPDATE category_categoryregion SET bomdod='{bomdod}', quyosh='{quyosh}', peshin='{peshin}', asr='{asr}', shom='{shom}', xufton='{xufton}' WHERE name='{city}'")
        namoz_vaqti3 = NamozVaqti('Marg‘ilon')
        print(namoz_vaqti3)

        bomdod = namoz_vaqti3.bomdod()
        quyosh = namoz_vaqti3.quyosh_chiqishi()
        peshin = namoz_vaqti3.peshin()
        asr = namoz_vaqti3.asr()
        shom = namoz_vaqti3.shom()
        xufton = namoz_vaqti3.xufton()
        cur.execute(
            "UPDATE category_categoryregion SET bomdod=?, quyosh=?, peshin=?, asr=?, shom=?, xufton=? WHERE name=?",
            (bomdod, quyosh, peshin, asr, shom, xufton, 'Marg‘ilon'))

    conn.commit()
    cur.close()
    conn.close()


