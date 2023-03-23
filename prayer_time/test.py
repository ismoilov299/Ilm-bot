import requests


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

w = "12:07"
list = [(1, 736342916, 'Zafar', 'Toshkent', 1), (3, 1161180912, 'Исмоилов Младший', 'Toshkent', 1), (157, 5006818392, 'Muhammad Amin', 'Toshkent', 1)]
for i in list:
    q, z, e, r, t = i
    if t == 1:
        obj = NamozVaqti(r)
        # print(e)
        # print(obj.bomdod())
        # print(obj.quyosh_chiqishi())
        # print(obj.peshin())
        # print(obj.asr())
        # print(obj.shom())
        # print(obj.xufton())
        b, p, a, s, h = obj.bomdod(), obj.peshin(), obj.asr(), obj.shom(), obj.xufton()
        if w == b:
            print(b)
        elif w == p:
            print(p)
        elif w == a:
            print(a)
        elif w == s:
            print(s)
        elif w == h:
            print(h)


