# Gaea MCP

Liest und bearbeitet Gaea-2-Projekte (`.terrain`) direkt in der Datei. Getestet mit Gaea 2.3.1 Community.

## Einrichten

Voraussetzung: [uv](https://docs.astral.sh/uv/) (installiert die MCP-Bibliothek beim ersten Start selbst).

```bash
claude mcp add gaea --scope user -- uv run --script "<PFAD>/gaea-mcp/server.py"
```

Optional `GAEA_DIR` setzen, falls Gaea nicht unter `%LOCALAPPDATA%\Programs\Gaea 2.0` liegt.

## Tools

| Tool | Zweck |
|---|---|
| `gaea_open` | Übersicht: Version, Build-Einstellungen, alle Nodes mit Parametern und Verbindungen |
| `gaea_get_node` | Ein Node im Detail |
| `gaea_copy` | Projekt kopieren zum gefahrlosen Ausprobieren |
| `gaea_set_params` | Parameter setzen; `null` = zurück auf Gaea-Standard |
| `gaea_rename_node`, `gaea_move_node` | Name / Position im Graphen |
| `gaea_add_node` | Node eines gelernten Typs anlegen |
| `gaea_duplicate_node` | Node mit allen Parametern kopieren |
| `gaea_connect`, `gaea_disconnect` | Ports verbinden / trennen (prüft Richtung und Zyklen) |
| `gaea_insert_between` | Node in eine bestehende Kette einhängen |
| `gaea_remove_node` | Node samt ausgehender Verbindungen löschen |
| `gaea_learn_node_types` | Node-Typen aus einer in Gaea gespeicherten Datei lernen |
| `gaea_list_node_types` | Bekannte Typen mit Ports |
| `gaea_build` | Build über `Gaea.Swarm.exe` versuchen (hängt in der Community Edition, Abbruch nach Timeout) |

## Wichtig

- **Projekt in Gaea vorher schließen** (oder danach neu öffnen). Gaea lädt Dateien nicht neu, und Speichern in Gaea überschreibt die Änderungen.
- Vor jeder Änderung wird `<datei>.terrain.bak` angelegt (nur die letzte Version).
- Neue Node-Typen: einmal in Gaea anlegen, speichern, dann `gaea_learn_node_types` auf die Datei. Bekannt sind bisher: Adjust, Combine, Erosion, Height, Island, Mountain, RGBMerge, Rivers, Sea, Shape, Slope (`node_templates.json`).
- Parameternamen sind Gaeas interne Namen. Unbekannte Namen werden geschrieben, aber von Gaea ignoriert.
