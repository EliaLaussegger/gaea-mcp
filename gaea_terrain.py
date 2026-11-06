"""Read and edit Gaea 2 .terrain files (Json.NET JSON with $id/$ref).

No third-party dependencies. Used by server.py, but works on its own too.
"""
from __future__ import annotations

import copy
import json
import os
import shutil
import uuid
from pathlib import Path

TEMPLATE_FILE = Path(__file__).with_name("node_templates.json")

# keys of a node that are structure, not user parameters
STRUCT_KEYS = {"$id", "$type", "Id", "Name", "Position", "Ports", "Modifiers"}


def short_type(full: str) -> str:
    """'QuadSpinner.Gaea.Nodes.Mountain, Gaea.Nodes' -> 'Mountain'"""
    return full.split(",")[0].rsplit(".", 1)[-1]


class GaeaError(Exception):
    pass


def _is_in(port: dict) -> bool:
    """Port Type looks like 'PrimaryIn, Required', 'In', 'Out', 'PrimaryOut'."""
    return port.get("Type", "").split(",")[0].strip() in ("In", "PrimaryIn")


class Terrain:
    def __init__(self, path: str | os.PathLike):
        self.path = Path(path)
        if not self.path.is_file():
            raise GaeaError(f"File not found: {self.path}")
        with open(self.path, encoding="utf-8-sig") as f:
            self.doc = json.load(f)
        try:
            self.terrain = self.doc["Assets"]["$values"][0]["Terrain"]
        except (KeyError, IndexError) as e:
            raise GaeaError("Not a Gaea 2 .terrain file (no Assets/Terrain)") from e

    # ---------- reading ----------
    @property
    def nodes(self) -> dict:
        return self.terrain["Nodes"]

    def node_ids(self) -> list[int]:
        return [int(k) for k in self.nodes if k != "$id"]

    def node(self, node_id: int) -> dict:
        n = self.nodes.get(str(node_id))
        if n is None:
            raise GaeaError(f"No node with id {node_id}. Existing: {self.node_ids()}")
        return n

    def find_by_name(self, name: str) -> list[int]:
        return [i for i in self.node_ids() if self.node(i).get("Name", "").lower() == name.lower()]

    @staticmethod
    def ports(n: dict) -> list[dict]:
        return n.get("Ports", {}).get("$values", [])

    def port(self, n: dict, name: str) -> dict:
        for p in self.ports(n):
            if p["Name"].lower() == name.lower():
                return p
        raise GaeaError(
            f"Node {n['Id']} ({n.get('Name')}) has no port '{name}'. "
            f"Ports: {[p['Name'] for p in self.ports(n)]}"
        )

    def describe(self, node_id: int) -> dict:
        n = self.node(node_id)
        inputs, outputs = [], []
        for p in self.ports(n):
            entry = {"port": p["Name"], "type": p.get("Type", "")}
            if _is_in(p):
                rec = p.get("Record")
                if rec:
                    entry["from"] = rec["From"]
                    entry["from_port"] = rec["FromPort"]
                inputs.append(entry)
            else:
                outputs.append(p["Name"])
        return {
            "id": n["Id"],
            "name": n.get("Name"),
            "type": short_type(n["$type"]),
            "params": {k: v for k, v in n.items() if k not in STRUCT_KEYS},
            "position": {"x": n["Position"]["X"], "y": n["Position"]["Y"]},
            "inputs": inputs,
            "outputs": outputs,
            "modifiers": len(n.get("Modifiers", {}).get("$values", [])),
        }

    def summary(self) -> dict:
        meta = self.doc.get("Metadata", {})
        build = self.doc["Assets"]["$values"][0].get("BuildDefinition", {})
        return {
            "file": str(self.path),
            "gaea_version": meta.get("Version"),
            "edition": meta.get("Edition"),
            "terrain_size": {"width": self.terrain.get("Width"), "height": self.terrain.get("Height")},
            "build": {k: build.get(k) for k in ("Destination", "Resolution", "NumberOfTiles")},
            "nodes": [self.describe(i) for i in self.node_ids()],
        }

    # ---------- editing ----------
    def set_params(self, node_id: int, params: dict) -> dict:
        n = self.node(node_id)
        for k, v in params.items():
            if k in STRUCT_KEYS:
                raise GaeaError(f"'{k}' is structural; use the dedicated tool (move/rename/connect).")
            if v is None:
                n.pop(k, None)  # back to Gaea default
            else:
                n[k] = v
        return self.describe(node_id)

    def rename(self, node_id: int, name: str):
        self.node(node_id)["Name"] = name

    def move(self, node_id: int, x: float, y: float):
        pos = self.node(node_id)["Position"]
        pos["X"], pos["Y"] = float(x), float(y)

    def _new_id(self) -> int:
        ids = self.node_ids()
        return (max(ids) + 1) if ids else 100

    def _insert(self, n: dict, x: float | None, y: float | None, name: str | None) -> int:
        new_id = self._new_id()
        n["Id"] = new_id
        if name:
            n["Name"] = name
        if x is None or y is None:
            # default: right of the right-most node
            xs = [self.node(i)["Position"]["X"] for i in self.node_ids()] or [26000.0]
            ys = [self.node(i)["Position"]["Y"] for i in self.node_ids()] or [26000.0]
            x = max(xs) + 300 if x is None else x
            y = ys[0] if y is None else y
        n.setdefault("Position", {"$id": _tmp_id(), "X": 0.0, "Y": 0.0})
        n["Position"]["X"], n["Position"]["Y"] = float(x), float(y)
        for p in self.ports(n):
            p.pop("Record", None)
        self.nodes[str(new_id)] = n
        return new_id

    def duplicate(self, node_id: int, name: str | None = None,
                  x: float | None = None, y: float | None = None) -> int:
        src = self.node(node_id)
        n = copy.deepcopy(src)
        if x is None:
            x = src["Position"]["X"] + 300
        if y is None:
            y = src["Position"]["Y"] + 150
        return self._insert(n, x, y, name or f"{src.get('Name', 'Node')} Copy")

    def add_from_template(self, type_name: str, name: str | None = None,
                          x: float | None = None, y: float | None = None) -> int:
        templates = load_templates()
        key = next((k for k in templates if k.lower() == type_name.lower()), None)
        if key is None:
            raise GaeaError(
                f"Unknown node type '{type_name}'. Known: {sorted(templates)}. "
                "Create it once in Gaea, save, then run learn_node_types on that file."
            )
        n = copy.deepcopy(templates[key])
        return self._insert(n, x, y, name or key)

    def connect(self, from_id: int, to_id: int, from_port: str = "Out", to_port: str = "In"):
        if from_id == to_id:
            raise GaeaError("Cannot connect a node to itself.")
        src, dst = self.node(from_id), self.node(to_id)
        sp = self.port(src, from_port)
        dp = self.port(dst, to_port)
        if _is_in(sp):
            raise GaeaError(f"'{from_port}' on node {from_id} is not an output.")
        if not _is_in(dp):
            raise GaeaError(f"'{to_port}' on node {to_id} is not an input.")
        if self._reaches(to_id, from_id):
            raise GaeaError("Connection would create a cycle.")
        record = {"$id": _tmp_id(), "From": from_id, "To": to_id,
                  "FromPort": sp["Name"], "ToPort": dp["Name"], "IsValid": True}
        # keep Json.NET-friendly key order: $id, Name, Type, Record, rest
        rebuilt = {}
        for k in ("$id", "Name", "Type"):
            if k in dp:
                rebuilt[k] = dp[k]
        rebuilt["Record"] = record
        for k, v in dp.items():
            if k not in rebuilt:
                rebuilt[k] = v
        dp.clear()
        dp.update(rebuilt)

    def disconnect(self, node_id: int, port: str = "In"):
        self.port(self.node(node_id), port).pop("Record", None)

    def remove(self, node_id: int):
        self.node(node_id)
        del self.nodes[str(node_id)]
        for i in self.node_ids():
            for p in self.ports(self.node(i)):
                if p.get("Record", {}).get("From") == node_id:
                    p.pop("Record")

    def _reaches(self, start: int, target: int) -> bool:
        """True if data flows from start downstream to target."""
        children: dict[int, list[int]] = {}
        for i in self.node_ids():
            for p in self.ports(self.node(i)):
                r = p.get("Record")
                if r:
                    children.setdefault(r["From"], []).append(i)
        stack, seen = [start], set()
        while stack:
            cur = stack.pop()
            if cur == target:
                return True
            if cur in seen:
                continue
            seen.add(cur)
            stack.extend(children.get(cur, []))
        return False

    # ---------- saving ----------
    def save(self, path: str | os.PathLike | None = None, backup: bool = True) -> Path:
        out = Path(path) if path else self.path
        if backup and out.exists():
            shutil.copy2(out, out.with_suffix(out.suffix + ".bak"))
        renumber(self.doc)
        validate(self.doc)
        tmp = out.with_suffix(out.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8", newline="\r\n") as f:
            json.dump(self.doc, f, indent=2, ensure_ascii=False)
        os.replace(tmp, out)
        self.path = out
        return out


# ---------- Json.NET reference handling ----------
def _tmp_id() -> str:
    return "tmp-" + uuid.uuid4().hex


def renumber(doc) -> None:
    """Give every $id a fresh sequential number and rewrite $ref accordingly.

    Duplicated subtrees carry the same old ids, so refs are resolved against the
    nearest enclosing definition first (Gaea's refs point to ancestors), then
    against the last global definition.
    """
    counter = [0]
    global_map: dict[str, str] = {}

    def walk(obj, scope: dict):
        if isinstance(obj, dict):
            local = scope
            if "$id" in obj:
                counter[0] += 1
                new = str(counter[0])
                local = {**scope, obj["$id"]: new}
                global_map[obj["$id"]] = new
                obj["$id"] = new
            for k, v in obj.items():
                if k != "$ref":
                    walk(v, local)
            if "$ref" in obj:
                old = obj["$ref"]
                if old in local:
                    obj["$ref"] = local[old]
                elif old in global_map:
                    obj["$ref"] = global_map[old]
                else:
                    raise GaeaError(f"Dangling $ref {old}")
        elif isinstance(obj, list):
            for v in obj:
                walk(v, scope)

    walk(doc, {})


def validate(doc) -> None:
    ids, refs = [], []

    def walk(o):
        if isinstance(o, dict):
            if "$id" in o:
                ids.append(o["$id"])
            if "$ref" in o:
                refs.append(o["$ref"])
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(doc)
    if len(ids) != len(set(ids)):
        raise GaeaError("Duplicate $id after renumbering")
    missing = set(refs) - set(ids)
    if missing:
        raise GaeaError(f"Dangling $ref: {sorted(missing)}")


# ---------- node type templates ----------
def load_templates() -> dict:
    if TEMPLATE_FILE.exists():
        with open(TEMPLATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def learn_templates(path: str | os.PathLike, keep_params: bool = False) -> dict:
    """Store every node type found in a .terrain file as a template.

    By default params are stripped, so new nodes start at Gaea's defaults
    (Gaea only stores non-default values). Connections are always removed.
    """
    t = Terrain(path)
    templates = load_templates()
    learned = []
    for i in t.node_ids():
        n = copy.deepcopy(t.node(i))
        for p in t.ports(n):
            p.pop("Record", None)
        if not keep_params:
            for k in [k for k in n if k not in STRUCT_KEYS]:
                del n[k]
        n.get("Modifiers", {}).get("$values", []).clear()
        key = short_type(n["$type"])
        templates[key] = n
        learned.append(key)
    with open(TEMPLATE_FILE, "w", encoding="utf-8") as f:
        json.dump(templates, f, indent=2, ensure_ascii=False)
    return {"learned": sorted(set(learned)), "all_known": sorted(templates)}
