"""Import wierszy z bazy Notiona do tabeli Nextcloud Tables (K146).

Jednokierunkowy: Notion zostaje źródłem, dopóki Filip nie zdecyduje o przełączeniu
piszących (Hermes ``tp``, ``curator.py``, ``promo-watch``…) na Tables.

Użycie::

    python3 -m kits.wlasny_notion.notion_import --notion-db <id> --table "Skrzynka"          # próba
    python3 -m kits.wlasny_notion.notion_import --notion-db <id> --table "Skrzynka" --apply  # zapis

Zmienne: ``NOTION_TOKEN`` (integracja z dostępem tylko do odczytu) i te same ``NC_*`` co w ``kit``.
Na wyjście idą tylko liczby i nazwy kolumn, nigdy treść wierszy (dane prywatne).
Mapa ``id strony Notion → id wiersza`` trafia do ``--state`` (domyślnie ``~/.local/state/wlasny-notion``),
więc ponowny import aktualizuje zamiast dublować, a relacje dopisuje drugi przebieg.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import requests

from .kit import Column, KitError, Nextcloud, TableSpec, load_tables

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"

# DECYZJA(K146-D9): import tylko w jedną stronę (Notion → Nextcloud), a piszący dalej piszą do
# Notiona. Przełączenie zapisu na Tables (przez MCP z K120) to osobny krok po decyzji Filipa.


def notion_value(prop: dict[str, Any]) -> Any:
    """Wartość właściwości strony Notiona jako prosty typ Pythona."""
    kind = prop.get("type")
    v = prop.get(kind) if isinstance(kind, str) else None
    if kind in {"title", "rich_text"}:
        return "".join(part.get("plain_text", "") for part in v or [])
    if kind in {"number", "checkbox", "url", "email", "phone_number", "created_time", "last_edited_time"}:
        return v
    if kind in {"select", "status"}:
        return v.get("name") if v else None
    if kind == "multi_select":
        return [o["name"] for o in v or []]
    if kind == "date":
        return v.get("start") if v else None
    if kind == "relation":
        return [r["id"] for r in v or []]
    if kind == "people":
        return [p.get("name", "") for p in v or []]
    if kind == "formula" and isinstance(v, dict):
        return v.get(v.get("type", ""))
    return None


def tables_value(col: Column, value: Any, options: dict[str, int], rows: dict[str, int]) -> Any:
    """Wartość komórki Tables (API v2) dla kolumny ``col``; ``None`` = pomiń komórkę.

    ``options``: etykieta → id opcji wyboru; ``rows``: id strony Notion → id wiersza.
    """
    if value is None or value == "" or value == []:
        return None
    if col.kind in {"title", "t", "long", "url", "email", "phone"}:
        return str(value)
    if col.kind == "n":
        return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None
    if col.kind == "cb":
        return "true" if value is True else "false"
    if col.kind == "d":
        return str(value)[:10]
    if col.kind == "dt":
        # Tables zapisuje datę i czas jako "RRRR-MM-DD GG:MM"; same daty dostają 00:00.
        text = str(value)
        return text[:10] + " " + (text[11:16] if len(text) >= 16 else "00:00")
    if col.kind == "s":
        return options.get(str(value))
    if col.kind == "ms":
        ids = [options[v] for v in value if v in options]
        return ids or None
    if col.kind == "rel":
        # DECYZJA(K146-D6): relacja w Tables to jeden wiersz; bierzemy pierwszy znany.
        known = [rows[p] for p in value if p in rows]
        return known[0] if known else None
    return None


def missing_options(spec: TableSpec, pages: list[dict[str, Any]], columns: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    """Etykiety wyborów z Notiona, których brakuje w kolumnach Tables (tytuł kolumny → etykiety)."""
    out: dict[str, list[str]] = {}
    for col in spec.columns:
        if col.kind not in {"s", "ms"} or col.title not in columns:
            continue
        known = {o["label"] for o in columns[col.title].get("selectionOptions") or []}
        seen: list[str] = []
        for page in pages:
            v = notion_value(page.get("properties", {}).get(col.title, {}))
            for label in v if isinstance(v, list) else [v]:
                if isinstance(label, str) and label and label not in known and label not in seen:
                    seen.append(label)
        if seen:
            out[col.title] = seen
    return out


def query_notion(db: str, token: str) -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []
    body: dict[str, Any] = {"page_size": 100}
    headers = {"Authorization": f"Bearer {token}", "Notion-Version": NOTION_VERSION}
    while True:
        try:
            resp = requests.post(f"{NOTION_API}/databases/{db}/query", json=body, headers=headers, timeout=60)
        except requests.RequestException as e:
            raise KitError(f"Notion nieosiągalny ({type(e).__name__})") from None
        if resp.status_code >= 400:
            raise KitError(f"Notion: HTTP {resp.status_code}")
        data = resp.json()
        pages.extend(data.get("results", []))
        if not data.get("has_more"):
            return pages
        body["start_cursor"] = data["next_cursor"]


def run(args: argparse.Namespace) -> int:
    spec = next((t for t in load_tables() if t.title == args.table), None)
    if spec is None:
        raise KitError(f"nie ma tabeli {args.table!r} w bazy.json")
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        raise KitError("ustaw NOTION_TOKEN")
    pages = query_notion(args.notion_db, token)
    nc = Nextcloud.from_env()
    tables = {t["title"]: t["id"] for t in nc.request("GET", "/index.php/apps/tables/api/1/tables") or []}
    if spec.title not in tables:
        raise KitError(f"tabeli {spec.title!r} nie ma w Nextcloudzie; najpierw `kit apply`")
    table_id = tables[spec.title]
    cols = {c["title"]: c for c in nc.request("GET", f"/index.php/apps/tables/api/1/tables/{table_id}/columns") or []}
    missing = missing_options(spec, pages, cols)
    state_file = Path(args.state).expanduser() / f"{spec.title}.json"
    rows: dict[str, int] = json.loads(state_file.read_text()) if state_file.exists() else {}
    print(f"{spec.title}: {len(pages)} stron w Notionie, {len(rows)} już zaimportowanych")
    for title, labels in missing.items():
        print(f"  nowe opcje w „{title}”: {len(labels)}")
    if not args.apply:
        print("Próba: nic nie zapisano (dodaj --apply).")
        return 0
    for title, labels in missing.items():
        col = cols[title]
        opts = list(col.get("selectionOptions") or [])
        next_id = max((o["id"] for o in opts), default=-1) + 1
        opts += [{"id": next_id + i, "label": label} for i, label in enumerate(labels)]
        nc.request("PUT", f"/index.php/apps/tables/api/1/columns/{col['id']}",
                   json={"selectionOptions": json.dumps(opts, ensure_ascii=False)})
        col["selectionOptions"] = opts
    # Dwa przebiegi: najpierw wiersze bez relacji, potem relacje (znamy już id wierszy).
    skipped_rel = 0
    for with_relations in (False, True):
        for page in pages:
            data: dict[str, Any] = {}
            for col in spec.columns:
                if (col.kind == "rel") != with_relations or col.title not in cols:
                    continue
                options = {o["label"]: o["id"] for o in cols[col.title].get("selectionOptions") or []}
                raw = notion_value(page.get("properties", {}).get(col.title, {}))
                value = tables_value(col, raw, options, rows)
                if col.kind == "rel" and isinstance(raw, list) and len(raw) > 1:
                    skipped_rel += len(raw) - 1
                if value is not None:
                    data[str(cols[col.title]["id"])] = value
            if not data:
                continue
            row_id = rows.get(page["id"])
            if row_id is None:
                made = nc.request("POST", f"/ocs/v2.php/apps/tables/api/2/tables/{table_id}/rows", json={"data": data})
                rows[page["id"]] = made["id"]
            else:
                nc.request("PUT", f"/ocs/v2.php/apps/tables/api/2/tables/{table_id}/rows/{row_id}", json={"data": data})
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(json.dumps(rows))
        state_file.chmod(0o600)
    print(f"Zapisano {len(rows)} wierszy; pominięte dodatkowe relacje: {skipped_rel} (K146-D6)")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Import bazy Notiona do Nextcloud Tables")
    ap.add_argument("--notion-db", required=True, help="id bazy Notiona")
    ap.add_argument("--table", required=True, help="tytuł tabeli z bazy.json")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--state", default="~/.local/state/wlasny-notion")
    try:
        return run(ap.parse_args(argv))
    except KitError as e:
        print(f"Błąd: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
