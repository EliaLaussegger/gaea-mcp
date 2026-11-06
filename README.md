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
- Export markieren: `gaea_set_params` mit `{"SaveDefinition": {"Node": <id>, "Filename": "Name", "Format": "PNG16", "IsEnabled": true, "DisabledInProfiles": {"$values": []}}}`. `Format` muss ein Gaea-Enum sein (z. B. `PNG8`, `PNG16`, `PNG64`, `TIFF8`, `TIFF16`, `TIFF32`, `EXR`) - `PNG` allein macht die Datei unlesbar ("File is corrupt").
- Fehler beim Öffnen: Gaea schreibt sie gzip+base64 ins Log (`Data/Logs`), erste 4 Bytes überspringen und entpacken.
- Bekannte Parameter (aus `Gaea.Nodes.dll` gelesen): **Combine** `Mode` (Blend, Add, Subtract, Multiply, Max, Min, ...), `Ratio`, `Clamp` - nicht `Method`, sonst bleibt Blend und bei Ratio 1 kommt nur Input2 raus. **Island** `Size`, `Chaos`, `Seed`. **Sea** `Level`, `ShoreSize`, `ShoreHeight`, `CoastalErosion`, `Variation`. **Mountain** `Scale`, `Height`, `Style`, `Bulk`, `Seed`, `X`, `Y`.
- **Slope** `Range` als Objekt `{"X": min, "Y": max}`, `Falloff`, `Type`. **Adjust** `Multiply`, `Shaper`, `Clamp`, `Clip`, `Drop`, `Autolevel`, `Equalize`, `Strong`, `Invert`. **Rivers** `Water`, `Width`, `Depth`, `Downcutting`, `RiverValleyWidth`, `Headwaters`, `Seed`. Beispiele mit echten Werten: `Gaea 2.0/Examples/*.terrain`.
