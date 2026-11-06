# Własny Notion na Nextcloudzie (K146)

Zestaw, który zakłada w Nextcloudzie zamiennik Notiona Filipa (wariant A z planu K146: sam Nextcloud, bez nowych usług):

| Plik | Co daje | Zamiast w Notionie |
|---|---|---|
| `bazy.json` | 13 tabel w **Tables** (schematy 11 baz Filipa + minimalne Cele, Epiki, Szablony randek), z opcjami wyborów i relacjami | bazy danych |
| `szablony/collectives/*.md` | 8 szablonów stron w **Collectives** (Raport, Notatka, Decyzja, Projekt, Przegląd tygodnia, Spotkanie, Przepis, Podróż) w kolektywach „Notatki” i „Raporty” | szablony stron, wiki |
| `szablony/pliki/*.md` | szablony plików w menu „Nowy” w Plikach i `Snippety.md` (callouty, toggle, checklisty, tabela decyzji, Mermaid, KaTeX) | bloki i snippety |
| `deck.json` | tablice **Deck** „Zadania” i „Projekty i epiki” z kolumnami i etykietami | board/kanban, timeline (Gantt w Deck) |
| `kit.py` | zakłada brakujące rzeczy przez API (przyrostowo, nic nie usuwa) | — |
| `notion_import.py` | import wierszy Notion → Tables (próba bez `--apply`), nowe opcje wyborów, relacje w drugim przebiegu | — |

Widoki, których Tables nie ma (grupowanie, board z wierszy, „Plan dnia”), pokazuje AetherShell (element `nextcloud`, repo `aethershell`, `docs/nextcloud.md`).

## Uruchomienie

```sh
python3 -m kits.wlasny_notion.kit plan                 # lista kroków, bez sieci
export NC_URL=https://nextcloud-stage-1.tail5c846a.ts.net NC_USER=filip
export NC_APP_PASSWORD_FILE=~/.config/wlasny-notion/nc-app-password   # hasło aplikacji, chmod 600
python3 -m kits.wlasny_notion.kit plan --live          # co brakuje na serwerze
python3 -m kits.wlasny_notion.kit apply                # zakłada brakujące

export NOTION_TOKEN=...                                # integracja Notion tylko do odczytu
python3 -m kits.wlasny_notion.notion_import --notion-db <id> --table "Skrzynka"           # próba
python3 -m kits.wlasny_notion.notion_import --notion-db <id> --table "Skrzynka" --apply
```

Wymaga w Nextcloudzie aplikacji Tables, Collectives, Deck i Text (faza F1 planu K121).
Hasła i treść wierszy nigdy nie trafiają na wyjście.

## Punkty decyzji

Domyślne wybory zrobione bez czekania na Filipa; w kodzie oznaczone `DECYZJA(K146-Dn)`:

| Id | Wybrano | Inna droga |
|---|---|---|
| D1 | sam Nextcloud + ten klej | pilot Teable (AGPL) po K19 dla baz z grupowaniem i boardem |
| D2 | tylko licencje open source (AGPL/MIT/Apache) | AFFiNE, Outline, NocoDB (source-available) |
| D5 | Task List (2023) → tablica Deck | tabela w Tables |
| D6 | relacja Tables wskazuje jeden wiersz; importer bierze pierwszy, resztę liczy w raporcie | Teable (relacje wielokrotne) |
| D7 | dwa kolektywy: „Notatki” i „Raporty” | jeden kolektyw albo kolektyw na temat |
| D8 | folder szablonów `Templates` (`NC_TEMPLATES_DIR` zmienia) | „Szablony” przy polskim interfejsie |
| D9 | import tylko Notion → Nextcloud; piszący zostają przy Notionie | przełączenie Hermesa na Tables przez MCP (K120) |

D3 i D4 dotyczą AetherShell (`docs/nextcloud.md` w repo `aethershell`).
