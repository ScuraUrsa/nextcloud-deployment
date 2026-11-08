"""Zakłada w Nextcloudzie wszystko, co zastępuje Notiona (K146).

* tabele w Tables według ``bazy.json`` (kolumny, opcje wyborów, relacje),
* kolektywy w Collectives z szablonami stron z ``szablony/collectives``,
* szablony plików i snippety w folderze szablonów użytkownika (menu „Nowy” w Plikach),
* tablice Deck według ``deck.json``.

Działa przyrostowo: czego już jest (po tytule), nie dotyka, więc można uruchamiać wielokrotnie.
Nic nie usuwa.

Użycie (z katalogu repozytorium)::

    python3 -m kits.wlasny_notion.kit plan            # co by zrobił, bez logowania
    python3 -m kits.wlasny_notion.kit plan --live     # porównanie z Nextcloudem
    python3 -m kits.wlasny_notion.kit apply           # zakłada brakujące

Zmienne: ``NC_URL``, ``NC_USER`` i ``NC_APP_PASSWORD`` albo ``NC_APP_PASSWORD_FILE``
(hasło aplikacji z Ustawienia → Bezpieczeństwo). Hasło nigdy nie trafia na wyjście.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests

HERE = Path(__file__).resolve().parent

# DECYZJA(K146-D1): wariant A, czyli sam Nextcloud (Tables, Collectives, Deck, Text) i ten
# klej, bez nowych usług. Alternatywa po K19: pilot Teable (AGPL, OIDC przez Nextcloud) dla
# baz, które potrzebują grupowania i boardu. Wtedy tabele z bazy.json zakłada się w Teable.

# DECYZJA(K146-D7): dwa kolektywy. „Notatki” na notatki Filipa (wiki, przepisy, podróże),
# „Raporty” na strony pisane przez Hermesa i Claude'a. Oba mają te same szablony.
COLLECTIVES = {"Notatki": "📝", "Raporty": "📋"}

# DECYZJA(K146-D8): folder szablonów plików. Nextcloud po polsku zakłada go jako „Szablony”,
# po angielsku „Templates”; ścieżkę bierzemy z NC_TEMPLATES_DIR, domyślnie „Templates”.
DEFAULT_TEMPLATES_DIR = "Templates"

TIMEOUT = 30


class KitError(Exception):
    """Błąd, który da się pokazać użytkownikowi (bez sekretów)."""


# --- Schematy --------------------------------------------------------------------------

TYPES = {"title", "t", "long", "url", "email", "phone", "n", "d", "dt", "cb", "s", "ms"}


@dataclass(frozen=True)
class Column:
    title: str
    kind: str
    options: tuple[str, ...] = ()
    target: str | None = None


@dataclass
class TableSpec:
    title: str
    emoji: str
    description: str
    columns: list[Column] = field(default_factory=list)


def parse_column(spec: str) -> Column:
    """``"Status:s=new|done"`` → Column. Tytuł może zawierać dwukropek tylko przed typem."""
    title, sep, rest = spec.rpartition(":")
    if not sep or not title.strip():
        raise KitError(f"kolumna bez typu: {spec!r}")
    title = title.strip()
    if rest.startswith("rel>"):
        target = rest[4:].strip()
        if not target:
            raise KitError(f"relacja bez tabeli: {spec!r}")
        return Column(title, "rel", target=target)
    kind, _, opts = rest.partition("=")
    if kind not in TYPES:
        raise KitError(f"nieznany typ {kind!r} w {spec!r}")
    options = tuple(o.strip() for o in opts.split("|") if o.strip()) if opts else ()
    if options and kind not in {"s", "ms"}:
        raise KitError(f"opcje tylko dla s/ms: {spec!r}")
    return Column(title, kind, options)


def load_tables(path: Path = HERE / "bazy.json") -> list[TableSpec]:
    data = json.loads(path.read_text(encoding="utf-8"))
    tables = [
        TableSpec(t["tytul"], t.get("emoji", ""), t.get("opis", ""), [parse_column(c) for c in t["kolumny"]])
        for t in data["tabele"]
    ]
    titles = [t.title for t in tables]
    if len(set(titles)) != len(titles):
        raise KitError("powtórzony tytuł tabeli w bazy.json")
    for t in tables:
        if not t.columns or t.columns[0].kind != "title":
            raise KitError(f"tabela {t.title!r}: pierwsza kolumna musi być typu title")
        for c in t.columns:
            if c.target is not None and c.target not in titles:
                raise KitError(f"tabela {t.title!r}: relacja do nieznanej tabeli {c.target!r}")
    return tables


def column_payload(col: Column, table_ids: dict[str, int], label_columns: dict[str, int]) -> dict[str, Any]:
    """Treść ``POST /index.php/apps/tables/api/1/tables/{id}/columns`` dla kolumny."""
    body: dict[str, Any] = {"title": col.title, "mandatory": col.kind == "title"}
    if col.kind in {"title", "t", "email", "phone"}:
        body |= {"type": "text", "subtype": "line"}
    elif col.kind == "long":
        body |= {"type": "text", "subtype": "rich"}
    elif col.kind == "url":
        body |= {"type": "text", "subtype": "link"}
    elif col.kind == "n":
        body |= {"type": "number"}
    elif col.kind == "d":
        body |= {"type": "datetime", "subtype": "date"}
    elif col.kind == "dt":
        body |= {"type": "datetime"}
    elif col.kind == "cb":
        body |= {"type": "selection", "subtype": "check", "selectionDefault": "false"}
    elif col.kind in {"s", "ms"}:
        body |= {
            "type": "selection",
            "subtype": "multi" if col.kind == "ms" else "",
            "selectionOptions": json.dumps(
                [{"id": i, "label": o} for i, o in enumerate(col.options)], ensure_ascii=False
            ),
        }
    elif col.kind == "rel":
        assert col.target is not None
        target_id = table_ids.get(col.target)
        label_id = label_columns.get(col.target)
        if target_id is None or label_id is None:
            # Tabela docelowa jeszcze nie istnieje (tryb plan): kolumna tekstowa z opisem.
            return {"title": col.title, "type": "text", "subtype": "line", "mandatory": False,
                    "description": f"relacja do „{col.target}” (tabela docelowa niedostępna)"}
        # Ustawienia relacji jak w Tables (RelationService): relationType, targetId, labelColumn.
        body |= {"type": "relation", "customSettings": {
            "relationType": "table", "targetId": target_id, "labelColumn": label_id}}
    return body


# --- Nextcloud -------------------------------------------------------------------------


class Nextcloud:
    """Minimalny klient: hasło aplikacji przez Basic, nagłówki OCS, odpowiedzi jako JSON."""

    def __init__(self, url: str, user: str, password: str, session: requests.Session | None = None) -> None:
        self.url = url.rstrip("/")
        self.user = user
        self.http = session or requests.Session()
        self.http.auth = (user, password)
        self.http.headers.update({"OCS-APIRequest": "true", "Accept": "application/json"})

    @classmethod
    def from_env(cls) -> Nextcloud:
        url, user = os.environ.get("NC_URL"), os.environ.get("NC_USER")
        password = os.environ.get("NC_APP_PASSWORD")
        if not password and os.environ.get("NC_APP_PASSWORD_FILE"):
            password = Path(os.environ["NC_APP_PASSWORD_FILE"]).read_text(encoding="utf-8").strip()
        if not (url and user and password):
            raise KitError("ustaw NC_URL, NC_USER i NC_APP_PASSWORD (albo NC_APP_PASSWORD_FILE)")
        return cls(url, user, password)

    def request(self, method: str, path: str, **kw: Any) -> Any:
        try:
            resp = self.http.request(method, self.url + path, timeout=TIMEOUT, **kw)
        except requests.RequestException as e:
            raise KitError(f"{method} {path}: Nextcloud nieosiągalny ({type(e).__name__})") from None
        if resp.status_code >= 400:
            raise KitError(f"{method} {path}: HTTP {resp.status_code}")
        if not resp.content or not resp.headers.get("Content-Type", "").startswith("application/json"):
            return None
        data = resp.json()
        if isinstance(data, dict) and "ocs" in data:
            return data["ocs"].get("data")
        return data

    def dav_path(self, *parts: str) -> str:
        segs = [quote(p, safe="") for part in parts for p in part.split("/") if p]
        return f"/remote.php/dav/files/{quote(self.user, safe='')}/" + "/".join(segs)


# --- Plan i wykonanie ------------------------------------------------------------------


@dataclass
class Step:
    what: str
    name: str
    detail: str = ""

    def __str__(self) -> str:
        return f"{self.what}: {self.name}" + (f" ({self.detail})" if self.detail else "")


def templates_dir() -> str:
    return os.environ.get("NC_TEMPLATES_DIR", DEFAULT_TEMPLATES_DIR)


def page_templates() -> dict[str, str]:
    return {p.stem: p.read_text(encoding="utf-8") for p in sorted((HERE / "szablony/collectives").glob("*.md"))}


def file_templates() -> dict[str, str]:
    return {p.name: p.read_text(encoding="utf-8") for p in sorted((HERE / "szablony/pliki").glob("*.md"))}


def load_boards(path: Path = HERE / "deck.json") -> list[dict[str, Any]]:
    boards: list[dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))["tablice"]
    return boards


class Kit:
    def __init__(self, nc: Nextcloud | None, apply: bool = False) -> None:
        self.nc = nc
        self.apply = apply
        self.steps: list[Step] = []
        self.warnings: list[str] = []

    def do(self, step: Step) -> bool:
        """Zapisuje krok; zwraca True, gdy trzeba go naprawdę wykonać."""
        self.steps.append(step)
        return self.apply and self.nc is not None

    def run(self) -> list[Step]:
        self.tables()
        self.collectives()
        self.file_templates()
        self.boards()
        return self.steps

    # Tables
    def tables(self) -> None:
        specs = load_tables()
        existing: dict[str, int] = {}
        if self.nc:
            for t in self.nc.request("GET", "/index.php/apps/tables/api/1/tables") or []:
                existing[t["title"]] = t["id"]
        ids = dict(existing)
        for spec in specs:
            if spec.title in ids:
                continue
            if self.do(Step("tabela", f"{spec.emoji} {spec.title}", f"{len(spec.columns)} kolumn")):
                assert self.nc
                t = self.nc.request("POST", "/ocs/v2.php/apps/tables/api/2/tables", json={
                    "title": spec.title, "emoji": spec.emoji, "description": spec.description, "template": "custom"})
                ids[spec.title] = t["id"]
        # Kolumny w drugim przebiegu: relacje potrzebują id tabel docelowych i ich kolumn tytułu.
        columns: dict[str, dict[str, int]] = {}
        for spec in specs:
            columns[spec.title] = {}
            if self.nc and spec.title in ids and (self.apply or spec.title in existing):
                path = f"/index.php/apps/tables/api/1/tables/{ids[spec.title]}/columns"
                columns[spec.title] = {c["title"]: c["id"] for c in self.nc.request("GET", path) or []}
        for ordered in (False, True):  # najpierw zwykłe kolumny, potem relacje
            for spec in specs:
                for col in spec.columns:
                    if (col.kind == "rel") != ordered or col.title in columns[spec.title]:
                        continue
                    labels = {s.title: columns[s.title].get(s.columns[0].title, 0) for s in specs}
                    label_ids = {k: v for k, v in labels.items() if v}
                    body = column_payload(col, ids, label_ids)
                    detail = f"relation → {col.target}" if col.target else body["type"]
                    if self.do(Step("kolumna", f"{spec.title} / {col.title}", detail)):
                        assert self.nc
                        path = f"/index.php/apps/tables/api/1/tables/{ids[spec.title]}/columns"
                        try:
                            made = self.nc.request("POST", path, json=body)
                        except KitError as e:
                            if col.kind != "rel":
                                raise
                            # Starsze Tables bez relacji: zostaje tekst, import wpisze tytuły.
                            self.warnings.append(f"{spec.title} / {col.title}: relacja nie przeszła ({e}), zakładam tekst")
                            made = self.nc.request("POST", path, json=column_payload(col, {}, {}))
                        columns[spec.title][col.title] = made["id"]

    # Collectives
    def collectives(self) -> None:
        templates = page_templates()
        existing: dict[str, int] = {}
        if self.nc:
            for c in self.nc.request("GET", "/ocs/v2.php/apps/collectives/api/v1.0/collectives") or []:
                existing[c["name"]] = c["id"]
        for name, emoji in COLLECTIVES.items():
            cid = existing.get(name)
            if cid is None and self.do(Step("kolektyw", f"{emoji} {name}")):
                assert self.nc
                made = self.nc.request("POST", "/ocs/v2.php/apps/collectives/api/v1.0/collectives",
                                       json={"name": name, "emoji": emoji})
                cid = (made.get("collective") or made)["id"]
            have: dict[str, Any] = {}
            root: dict[str, Any] | None = None
            if self.nc and cid is not None:
                listed = self.nc.request("GET", f"/ocs/v2.php/apps/collectives/api/v1.0/collectives/{cid}/pages/templates")
                pages = (listed or {}).get("templates", listed) if isinstance(listed, dict) else listed or []
                for p in pages:
                    if p.get("parentId") == 0:
                        root = p
                    have[p["title"]] = p
            for title, content in templates.items():
                if title in have:
                    continue
                if not self.do(Step("szablon strony", f"{name} / {title}")):
                    continue
                assert self.nc and cid is not None
                if root is None:
                    self.warnings.append(f"{name}: brak strony głównej szablonów; szablony do dodania ręcznie")
                    break
                base = f"/ocs/v2.php/apps/collectives/api/v1.0/collectives/{cid}/pages/templates/{root['id']}"
                made = self.nc.request("POST", base, json={"title": title, "parentId": root["id"]})
                page = made.get("template") or made.get("page") or made
                self.nc.request("PUT", self.nc.dav_path(page["collectivePath"], page["filePath"], page["fileName"]),
                                data=content.encode("utf-8"), headers={"Content-Type": "text/markdown"})

    # Szablony plików i snippety
    def file_templates(self) -> None:
        folder = templates_dir()
        have: set[str] = set()
        if self.nc:
            try:
                resp = self.nc.http.request("PROPFIND", self.nc.url + self.nc.dav_path(folder),
                                            headers={"Depth": "1"}, timeout=TIMEOUT)
            except requests.RequestException:
                raise KitError("PROPFIND szablonów: Nextcloud nieosiągalny") from None
            if resp.status_code == 404:
                if self.do(Step("folder", folder)):
                    self.nc.request("MKCOL", self.nc.dav_path(folder))
            elif resp.status_code < 400:
                have = {name for name in file_templates() if f"/{quote(name, safe='')}<" in resp.text}
        for name, content in file_templates().items():
            if name in have:
                continue
            if self.do(Step("szablon pliku", f"{folder}/{name}")):
                assert self.nc
                self.nc.request("PUT", self.nc.dav_path(folder, name), data=content.encode("utf-8"),
                                headers={"Content-Type": "text/markdown"})

    # Deck
    def boards(self) -> None:
        existing: set[str] = set()
        if self.nc:
            existing = {b["title"] for b in self.nc.request("GET", "/index.php/apps/deck/api/v1.0/boards") or []
                        if not b.get("deletedAt")}
        for board in load_boards():
            if board["tytul"] in existing:
                continue
            detail = f"{len(board['kolumny'])} kolumn, {len(board['etykiety'])} etykiet"
            if not self.do(Step("tablica Deck", board["tytul"], detail)):
                continue
            assert self.nc
            made = self.nc.request("POST", "/index.php/apps/deck/api/v1.0/boards",
                                   json={"title": board["tytul"], "color": board["kolor"]})
            base = f"/index.php/apps/deck/api/v1.0/boards/{made['id']}"
            for order, title in enumerate(board["kolumny"]):
                self.nc.request("POST", f"{base}/stacks", json={"title": title, "order": order})
            for title, color in board["etykiety"].items():
                self.nc.request("POST", f"{base}/labels", json={"title": title, "color": color})


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0] if __doc__ else None)
    ap.add_argument("command", choices=["plan", "apply"])
    ap.add_argument("--live", action="store_true", help="plan: porównaj z Nextcloudem")
    args = ap.parse_args(argv)
    try:
        nc = Nextcloud.from_env() if args.command == "apply" or args.live else None
        kit = Kit(nc, apply=args.command == "apply")
        steps = kit.run()
    except KitError as e:
        print(f"Błąd: {e}", file=sys.stderr)
        return 1
    verb = "Zrobione" if args.command == "apply" else "Do zrobienia"
    print(f"{verb}: {len(steps)} kroków")
    for s in steps:
        print(f"  {s}")
    for w in kit.warnings:
        print(f"Uwaga: {w}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
