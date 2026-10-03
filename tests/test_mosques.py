"""Yaqin masjidni topish (``masjid_aniqlash``) uchun xarakterlovchi testlar."""

from types import SimpleNamespace

import pytest

from data.location import Masjid
from masjid_aniqlash.masofa import show
from masjid_aniqlash.masofa_aniqlash import calc_distance, choose_shortes


def test_one_degree_of_longitude_on_equator():
    # Yer radiusi 6371 km bo'lsa, ekvatorda 1 gradus = 6371 * pi / 180 km
    assert calc_distance(0, 0, 0, 1) == pytest.approx(111.19492664455873)


def test_distance_between_cities():
    tashkent, samarkand = (41.2995, 69.2401), (39.6542, 66.9597)

    assert calc_distance(*tashkent, *samarkand) == pytest.approx(266, abs=1)
    assert calc_distance(*samarkand, *tashkent) == pytest.approx(calc_distance(*tashkent, *samarkand))
    assert calc_distance(*tashkent, *tashkent) == 0


def test_show_builds_google_maps_link_with_quoted_name():
    assert show(41.1, 69.2, "Ko'zi ojizlar") == "http://maps.google.com/maps?q=41.1,69.2&q=Ko%27zi%20ojizlar"


def test_choose_shortes_returns_two_nearest_mosques():
    first = Masjid[0]

    result = choose_shortes(SimpleNamespace(latitude=first["lat"], longitude=first["lon"]))

    assert len(result) == 2
    (distance, name, url, mosque), (second_distance, *_) = result
    assert (distance, name, mosque) == (0, first["name"], first)
    assert url == show(lat=first["lat"], lon=first["lon"], name=first["name"])
    others = [calc_distance(first["lat"], first["lon"], m["lat"], m["lon"]) for m in Masjid[1:]]
    assert second_distance == pytest.approx(min(others))


def test_mosque_coordinates_are_inside_tashkent():
    # Kenglik va uzunlik almashib qolsa (lat ~69), shu yerda ushlanadi.
    outside = [m["name"] for m in Masjid if not (41.0 < m["lat"] < 41.6 and 69.0 < m["lon"] < 69.6)]

    assert outside == []
