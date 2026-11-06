"""
Offline tests for ``kits/wlasny_notion`` (K146): the schema file, the column
mapping for Nextcloud Tables, the plan/apply runner against a fake Nextcloud,
and the Notion → Tables value conversion.
"""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urlparse

import pytest

from kits.wlasny_notion import kit, notion_import
from kits.wlasny_notion.kit import (
    Column,
    Kit,
    KitError,
    Nextcloud,
    column_payload,
    load_tables,
    parse_column,
)

pytestmark = pytest.mark.unit


class FakeResponse:
    def __init__(self, status: int, payload: Any = None, text: str = "") -> None:
        self.status_code = status
        self._payload = payload
        self.content = b"" if payload is None else json.dumps(payload).encode()
        self.headers = {"Content-Type": "application/json"} if payload is not None else {}
        self.text = text

    def json(self) -> Any:
        return self._payload


class FakeNextcloud:
    """Just enough of Tables, Collectives, WebDAV and Deck for the kit."""

    def __init__(self) -> None:
        self.auth: Any = None
        self.headers: dict[str, str] = {}
        self.calls: list[tuple[str, str, Any]] = []
        self.tables: dict[int, dict[str, Any]] = {}
        self.columns: dict[int, list[dict[str, Any]]] = {}
        self.collectives: dict[int, dict[str, Any]] = {}
        self.templates: dict[int, list[dict[str, Any]]] = {}
        self.files: dict[str, bytes] = {}
        self.boards: list[dict[str, Any]] = []
        self.next_id = 1

    def _id(self) -> int:
        self.next_id += 1
        return self.next_id

    def request(self, method: str, url: str, **kw: Any) -> FakeResponse:
        path = urlparse(url).path
        body: dict[str, Any] = kw.get("json") or {}
        self.calls.append((method, path, body))

        def ocs(data: Any) -> FakeResponse:
            return FakeResponse(200, {"ocs": {"meta": {"status": "ok"}, "data": data}})

        if path == "/index.php/apps/tables/api/1/tables" and method == "GET":
            return FakeResponse(200, list(self.tables.values()))
        if path == "/ocs/v2.php/apps/tables/api/2/tables" and method == "POST":
            t = {"id": self._id(), "title": body["title"]}
            self.tables[t["id"]] = t
            self.columns[t["id"]] = []
            return ocs(t)
        m = re.fullmatch(r"/index.php/apps/tables/api/1/tables/(\d+)/columns", path)
        if m:
            cols = self.columns[int(m.group(1))]
            if method == "GET":
                return FakeResponse(200, cols)
            c = {"id": self._id(), **body}
            cols.append(c)
            return FakeResponse(200, c)
        if path == "/ocs/v2.php/apps/collectives/api/v1.0/collectives":
            if method == "GET":
                return ocs(list(self.collectives.values()))
            c = {"id": self._id(), "name": body["name"]}
            self.collectives[c["id"]] = c
            self.templates[c["id"]] = [{"id": self._id(), "title": "Template", "parentId": 0}]
            return ocs({"collective": c})
        m = re.fullmatch(r"/ocs/v2.php/apps/collectives/api/v1.0/collectives/(\d+)/pages/templates(?:/(\d+))?", path)
        if m:
            cid = int(m.group(1))
            if method == "GET":
                return ocs({"templates": self.templates[cid]})
            name = self.collectives[cid]["name"]
            page = {"id": self._id(), "title": body["title"], "parentId": body["parentId"],
                    "collectivePath": f"Collectives/{name}", "filePath": ".templates", "fileName": f"{body['title']}.md"}
            self.templates[cid].append(page)
            return ocs({"template": page})
        if path.startswith("/remote.php/dav/files/"):
            if method == "PROPFIND":
                folder = path.rstrip("/")
                if not any(k.startswith(folder) for k in self.files) and folder not in self.files:
                    return FakeResponse(404)
                listing = "".join(f"<d:href>{k}</d:href>" for k in self.files)
                return FakeResponse(207, None, listing)
            self.files[path] = kw.get("data") or b""
            return FakeResponse(201)
        if path == "/index.php/apps/deck/api/v1.0/boards":
            if method == "GET":
                return FakeResponse(200, self.boards)
            b = {"id": self._id(), "title": body["title"], "stacks": [], "labels": []}
            self.boards.append(b)
            return FakeResponse(200, b)
        m = re.fullmatch(r"/index.php/apps/deck/api/v1.0/boards/(\d+)/(stacks|labels)", path)
        if m:
            board = next(b for b in self.boards if b["id"] == int(m.group(1)))
            board[m.group(2)].append(body)
            return FakeResponse(200, {"id": self._id(), **body})
        return FakeResponse(404)


@pytest.fixture
def fake() -> FakeNextcloud:
    return FakeNextcloud()


@pytest.fixture
def nc(fake: FakeNextcloud) -> Nextcloud:
    return Nextcloud("https://cloud.test", "filip", "secret-app-pass", session=fake)  # type: ignore[arg-type]


def test_schema_file_is_consistent() -> None:
    tables = load_tables()
    titles = {t.title for t in tables}
    assert {"Plan dnia", "Skrzynka", "CRM Contacts", "Baza wiedzy Hermesa"} <= titles
    for t in tables:
        assert t.columns[0].kind == "title"
        assert len({c.title for c in t.columns}) == len(t.columns), t.title
        for c in t.columns:
            assert c.target is None or c.target in titles


@pytest.mark.parametrize("bad", ["NoType", "X:zz", "X:t=a|b", "X:rel>", ":t"])
def test_bad_column_specs_are_rejected(bad: str) -> None:
    with pytest.raises(KitError):
        parse_column(bad)


def test_column_spec_keeps_colons_and_options() -> None:
    assert parse_column("Status:s=new|done") == Column("Status", "s", ("new", "done"))
    assert parse_column("A: b:t") == Column("A: b", "t")
    assert parse_column("Cel:rel>Cele") == Column("Cel", "rel", target="Cele")


def test_column_payloads_follow_tables_types() -> None:
    p = column_payload(parse_column("Status:s=new|done"), {}, {})
    assert p["type"] == "selection" and p["subtype"] == ""
    assert json.loads(p["selectionOptions"]) == [{"id": 0, "label": "new"}, {"id": 1, "label": "done"}]
    assert column_payload(parse_column("Tagi:ms"), {}, {})["subtype"] == "multi"
    assert column_payload(parse_column("Done:cb"), {}, {})["subtype"] == "check"
    assert column_payload(parse_column("Kiedy:d"), {}, {})["subtype"] == "date"
    assert column_payload(parse_column("Link:url"), {}, {})["subtype"] == "link"
    assert column_payload(parse_column("Name:title"), {}, {})["mandatory"] is True
    rel = column_payload(parse_column("Cel:rel>Cele"), {"Cele": 5}, {"Cele": 50})
    assert rel["type"] == "relation"
    assert rel["customSettings"] == {"relationType": "table", "targetId": 5, "labelColumn": 50}
    assert column_payload(parse_column("Cel:rel>Cele"), {}, {})["type"] == "text"


def test_offline_plan_lists_everything() -> None:
    steps = Kit(None).run()
    kinds = [s.what for s in steps]
    tables = load_tables()
    assert kinds.count("tabela") == len(tables)
    assert kinds.count("kolumna") == sum(len(t.columns) for t in tables)
    assert kinds.count("kolektyw") == len(kit.COLLECTIVES)
    assert kinds.count("szablon strony") == len(kit.COLLECTIVES) * len(kit.page_templates())
    assert kinds.count("szablon pliku") == len(kit.file_templates())
    assert kinds.count("tablica Deck") == len(kit.load_boards())


def test_apply_builds_everything_once(fake: FakeNextcloud, nc: Nextcloud) -> None:
    first = Kit(nc, apply=True)
    first.run()
    assert not first.warnings
    tables = load_tables()
    assert len(fake.tables) == len(tables)
    by_title = {t["title"]: tid for tid, t in fake.tables.items()}
    plan_cols = fake.columns[by_title["Plan dnia"]]
    rel = next(c for c in plan_cols if c["title"] == "Cel")
    cele_title_col = fake.columns[by_title["Cele"]][0]
    assert rel["type"] == "relation"
    assert rel["customSettings"] == {"relationType": "table", "targetId": by_title["Cele"],
                                     "labelColumn": cele_title_col["id"]}
    # Relations are created after every plain column.
    posts = [b for m, p, b in fake.calls if m == "POST" and p.endswith("/columns")]
    first_rel = next(i for i, b in enumerate(posts) if b["type"] == "relation")
    assert all(b["type"] == "relation" for b in posts[first_rel:])
    assert len(fake.collectives) == len(kit.COLLECTIVES)
    assert all(len(t) == 1 + len(kit.page_templates()) for t in fake.templates.values())
    assert any(k.endswith("/Templates/Snippety.md") for k in fake.files)
    assert any(k.endswith("/.templates/Decyzja.md") for k in fake.files)
    assert [b["title"] for b in fake.boards] == [b["tytul"] for b in kit.load_boards()]
    assert [s["title"] for s in fake.boards[0]["stacks"]] == kit.load_boards()[0]["kolumny"]
    # Second run finds everything and does nothing.
    calls = len(fake.calls)
    again = Kit(nc, apply=True).run()
    assert again == []
    assert all(m in {"GET", "PROPFIND"} for m, _, _ in fake.calls[calls:])


def test_errors_never_show_the_password(fake: FakeNextcloud, nc: Nextcloud) -> None:
    with pytest.raises(KitError) as err:
        nc.request("GET", "/nope")
    assert "secret-app-pass" not in str(err.value)
    assert "404" in str(err.value)


def prop(kind: str, value: Any) -> dict[str, Any]:
    return {"type": kind, kind: value}


def test_notion_values_are_flattened() -> None:
    assert notion_import.notion_value(prop("title", [{"plain_text": "Ab"}, {"plain_text": "c"}])) == "Abc"
    assert notion_import.notion_value(prop("select", {"name": "p1"})) == "p1"
    assert notion_import.notion_value(prop("status", None)) is None
    assert notion_import.notion_value(prop("multi_select", [{"name": "a"}, {"name": "b"}])) == ["a", "b"]
    assert notion_import.notion_value(prop("date", {"start": "2026-11-06T10:30:00.000+01:00"})) == "2026-11-06T10:30:00.000+01:00"
    assert notion_import.notion_value(prop("relation", [{"id": "x"}])) == ["x"]
    assert notion_import.notion_value(prop("checkbox", False)) is False


def test_tables_values_match_column_types() -> None:
    tv = notion_import.tables_value
    opts = {"new": 0, "done": 1}
    assert tv(parse_column("S:s"), "done", opts, {}) == 1
    assert tv(parse_column("S:s"), "unknown", opts, {}) is None
    assert tv(parse_column("M:ms"), ["new", "x", "done"], opts, {}) == [0, 1]
    assert tv(parse_column("C:cb"), True, {}, {}) == "true"
    assert tv(parse_column("D:d"), "2026-11-06T10:30:00.000+01:00", {}, {}) == "2026-11-06"
    assert tv(parse_column("D:dt"), "2026-11-06T10:30:00.000+01:00", {}, {}) == "2026-11-06 10:30"
    assert tv(parse_column("D:dt"), "2026-11-06", {}, {}) == "2026-11-06 00:00"
    assert tv(parse_column("N:n"), True, {}, {}) is None
    assert tv(parse_column("R:rel>X"), ["a", "b"], {}, {"b": 7}) == 7
    assert tv(parse_column("T:t"), "", {}, {}) is None


def test_missing_select_options_are_found() -> None:
    spec = next(t for t in load_tables() if t.title == "Skrzynka")
    pages = [{"properties": {"Kind": prop("select", {"name": "podcast"}), "Nastroje": prop("multi_select", [{"name": "😊"}])}},
             {"properties": {"Kind": prop("select", {"name": "news"})}}]
    columns: dict[str, dict[str, Any]] = {
        "Kind": {"selectionOptions": [{"id": 0, "label": "news"}]},
        "Nastroje": {"selectionOptions": []},
    }
    assert notion_import.missing_options(spec, pages, columns) == {"Kind": ["podcast"], "Nastroje": ["😊"]}


def test_templates_are_markdown_pages() -> None:
    for name, text in {**kit.page_templates(), **kit.file_templates()}.items():
        assert text.startswith("# "), name
