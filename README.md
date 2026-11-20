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
- Fehler beim Öffnen: Gaea schreibt sie gzip+base64 ins Log (`%APPDATA%\QuadSpinner\Gaea\2.0\Logs`, ältere Installationen `Data/Logs`), erste 4 Bytes überspringen und entpacken. `gaea_build` mit `exit_code` 1 nach wenigen Sekunden heißt meist: Datei nicht ladbar ("File is corrupt"), nicht Edition-Limit.
- Gaeas 3D-Vorschau zeigt jeden ausgewählten Node als Höhenfeld, auch Masken und Splatmaps (RGBMerge). Eine Splatmap sieht dort wie ein hoher Block aus; die exportierte Datei ist trotzdem nur ein Farbbild. Die Inselhöhe kommt vom Terrain-Node (z. B. Sea).
- Bekannte Parameter (aus `Gaea.Nodes.dll` gelesen): **Combine** `Mode` (Blend, Add, Subtract, Multiply, Max, Min, ...), `Ratio`, `Clamp` - nicht `Method`, sonst bleibt Blend und bei Ratio 1 kommt nur Input2 raus. **Island** `Size`, `Chaos`, `Seed`. **Sea** `Level`, `ShoreSize`, `ShoreHeight`, `CoastalErosion`, `Variation`. **Mountain** `Scale`, `Height`, `Style`, `Bulk`, `Seed`, `X`, `Y`.
- **Slope** `Range` als Objekt `{"X": min, "Y": max}` (Steigung, nicht 0-1: Y=1.0 schneidet steile Hänge ab, Beispiele nutzen >1), `Falloff`, `Type`. Achtung bei übernommenen Graphen: `Range` wählt den Bereich *aus*. 0–28° markiert flaches Gelände; als Fels-Maske braucht es steile Hänge, z. B. `{"X": 30, "Y": 90}`. **Adjust** `Multiply`, `Shaper`, `Clamp`, `Clip`, `Drop`, `Autolevel`, `Equalize`, `Strong`, `Invert`. **Rivers** `Water`, `Width`, `Depth`, `Downcutting`, `RiverValleyWidth`, `Headwaters`, `Seed`. Beispiele mit echten Werten: `Gaea 2.0/Examples/*.terrain`.
- **Height** `Range` ist nicht auf 0–1 normiert. Ein Height-Node mit Range 0–1 ist deshalb *keine* weiße Fläche (er wählt nur das Meer aus). Für "1 minus Maske" `Adjust` mit `Invert: true` nehmen.

## Workflow: RGB-Splatmap mit 3 Layern

Erprobt für Insel → Unity (z. B. Rock / Soil / Sand+River). Die drei Kanäle ergeben überall zusammen 1, dadurch gibt es weder Lücken noch Überlappungen.

| Kanal | Layer | Aufbau |
|---|---|---|
| B | Sand, River | `Combine` Max(`Sea.Water`, `Sea.Shore`) → `Combine` Max(…, `Rivers.Rivers`) |
| R | Rock | `Slope` (`Range` `{"X": 30, "Y": 90}`) → `Combine` Subtract B (kein Fels am Strand / im Fluss) |
| – | NotSoil | `Combine` Max(R, B) |
| G | Soil | `Adjust` `Invert: true` auf NotSoil (= alles, was weder Rock noch B ist) |

- Alle `Combine`: `Mode` setzen, `Ratio: 1`.
- `RGBMerge`: `In` = R, `In2` = G, `In3` = B. Export `{"Format": "PNG8"}` als `SplatMap`.
- Heightmap: der Terrain-Node (z. B. `Sea`) mit `{"Format": "PNG16"}`.
- Kontrolle: In der 2D-Ansicht von `SplatMap` darf an Land nichts schwarz sein. Schwarz bedeutet, dass ein Kanal fehlt.

## Lizenz

MIT, siehe [LICENSE](LICENSE). Kein offizielles Projekt von QuadSpinner; Gaea ist deren Produkt.
