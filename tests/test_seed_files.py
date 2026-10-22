"""`seeds/*.json` fayllarining yaxlitligi (bazasiz)."""

from collections import Counter

import pytest

from ilmbot.db.models import ButtonAction, ButtonKind
from ilmbot.seed import load_seed


@pytest.fixture(scope="module")
def nodes():
    return load_seed("menu_seed.json")["nodes"]


def test_menu_keys_are_unique_and_parents_exist(nodes):
    keys = [node["key"] for node in nodes]
    assert len(keys) == len(set(keys))
    assert all(node["parent"] is None or node["parent"] in set(keys) for node in nodes)


def test_menu_has_no_cycles(nodes):
    parent = {node["key"]: node["parent"] for node in nodes}
    for key in parent:
        seen = set()
        while key is not None:
            assert key not in seen, f"aylana: {key}"
            seen.add(key)
            key = parent[key]


def test_menu_kinds_and_actions_are_valid(nodes):
    kinds = {kind.value for kind in ButtonKind}
    actions = {action.value for action in ButtonAction}
    assert all(node["kind"] in kinds for node in nodes)
    assert all(node["action"] is None or node["action"] in actions for node in nodes)
    assert all((node["kind"] == "action") == (node["action"] is not None) for node in nodes)


def test_menu_positions_are_unique_per_parent(nodes):
    counts = Counter((node["parent"], node["position"]) for node in nodes)
    assert max(counts.values()) == 1


def test_post_nodes_without_posts_are_marked_for_review(nodes):
    empty = [node for node in nodes if node["kind"] == "post" and not node["message_ids"]]
    assert all(node.get("review") for node in empty), [node["key"] for node in empty if not node.get("review")]


def test_menu_message_ids_are_positive_integers(nodes):
    ids = [mid for node in nodes for mid in node["message_ids"]]
    assert ids and all(isinstance(mid, int) and mid > 0 for mid in ids)


def test_menu_top_level_and_known_counts(nodes):
    roots = [node for node in nodes if node["parent"] is None]
    assert len(roots) == 10
    assert len(nodes) == 801
    assert {action for node in nodes if (action := node["action"])} == {"prayer_times", "nearest_mosques"}


def test_mosques_are_in_tashkent():
    mosques = load_seed("mosques.json")
    assert len(mosques) == 115
    assert all(41.1 < m["lat"] < 41.5 and 69.0 < m["lon"] < 69.5 for m in mosques)
    assert all(m["name"] and m["district"] for m in mosques)
    assert sum("review" in m for m in mosques) == 5


def test_regions_have_coordinates_inside_uzbekistan():
    regions = load_seed("regions.json")
    assert len(regions) == 13
    assert len({r["name"] for r in regions}) == 13
    assert all(37 < r["lat"] < 46 and 55 < r["lon"] < 74 for r in regions)
