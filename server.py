# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp>=1.2,<2"]
# ///
"""Gaea MCP server: inspect and edit Gaea 2 .terrain node graphs.

Run:  uv run --script server.py
Edits are written straight into the .terrain file (a .bak is kept next to it).
Gaea does not reload files that are open: close the project in Gaea before
editing, or reopen it afterwards, and do not save from Gaea in between.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from mcp.server.fastmcp import FastMCP  # noqa: E402

import gaea_terrain as gt  # noqa: E402

GAEA_DIR = Path(os.environ.get(
    "GAEA_DIR", Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Gaea 2.0"))

mcp = FastMCP("gaea")


def _edit(file: str, fn):
    t = gt.Terrain(file)
    result = fn(t)
    t.save()
    return result


@mcp.tool()
def gaea_open(file: str) -> dict:
    """Overview of a .terrain file: version, build settings and every node with
    its type, params (only non-default values are stored), inputs and outputs."""
    return gt.Terrain(file).summary()


@mcp.tool()
def gaea_get_node(file: str, node_id: int) -> dict:
    """Full details of one node."""
    return gt.Terrain(file).describe(node_id)


@mcp.tool()
def gaea_copy(src: str, dst: str) -> str:
    """Copy a .terrain file to experiment safely (refuses to overwrite)."""
    if Path(dst).exists():
        raise gt.GaeaError(f"{dst} already exists")
    gt.Terrain(src)  # validate
    shutil.copy2(src, dst)
    return dst


@mcp.tool()
def gaea_set_params(file: str, node_id: int, params: dict) -> dict:
    """Set node parameters, e.g. {"Height": 2.0, "Seed": 42, "Style": "Alpine"}.
    A value of null removes the param so Gaea uses its default.
    Param names are Gaea's internal names (see gaea_open); unknown names are
    written anyway and ignored by Gaea, so check spelling against a saved file."""
    return _edit(file, lambda t: t.set_params(node_id, params))


@mcp.tool()
def gaea_rename_node(file: str, node_id: int, name: str) -> str:
    """Rename a node (display name in the graph)."""
    _edit(file, lambda t: t.rename(node_id, name))
    return f"node {node_id} renamed to {name}"


@mcp.tool()
def gaea_move_node(file: str, node_id: int, x: float, y: float) -> str:
    """Move a node in the graph view (graph coordinates, ~300 units between nodes)."""
    _edit(file, lambda t: t.move(node_id, x, y))
    return f"node {node_id} moved to {x}, {y}"


@mcp.tool()
def gaea_duplicate_node(file: str, node_id: int, name: str | None = None,
                        x: float | None = None, y: float | None = None) -> dict:
    """Copy a node with all its params (unconnected). Returns the new node."""
    def fn(t):
        new_id = t.duplicate(node_id, name, x, y)
        return new_id
    new_id = _edit(file, fn)
    return gt.Terrain(file).describe(new_id)


@mcp.tool()
def gaea_add_node(file: str, node_type: str, name: str | None = None,
                  x: float | None = None, y: float | None = None) -> dict:
    """Add a node of a learned type (see gaea_list_node_types), unconnected.
    Unknown types must first be learned from a file saved by Gaea."""
    new_id = _edit(file, lambda t: t.add_from_template(node_type, name, x, y))
    return gt.Terrain(file).describe(new_id)


@mcp.tool()
def gaea_connect(file: str, from_id: int, to_id: int,
                 from_port: str = "Out", to_port: str = "In") -> str:
    """Connect an output port to an input port (replaces any existing link on
    that input). Common ports: Out/In; Erosion also has Wear, Deposits, Flow
    outputs and AreaMask input; Rivers has Rivers, Depth, Surface, Direction."""
    _edit(file, lambda t: t.connect(from_id, to_id, from_port, to_port))
    return f"{from_id}.{from_port} -> {to_id}.{to_port}"


@mcp.tool()
def gaea_disconnect(file: str, node_id: int, port: str = "In") -> str:
    """Remove the link going into an input port."""
    _edit(file, lambda t: t.disconnect(node_id, port))
    return f"disconnected {node_id}.{port}"


@mcp.tool()
def gaea_remove_node(file: str, node_id: int) -> str:
    """Delete a node and every link coming out of it."""
    _edit(file, lambda t: t.remove(node_id))
    return f"removed node {node_id}"


@mcp.tool()
def gaea_insert_between(file: str, node_id: int, after_id: int, before_id: int,
                        before_port: str = "In") -> str:
    """Rewire after_id -> node_id -> before_id (for putting a node into a chain)."""
    def fn(t):
        t.connect(after_id, node_id, "Out", "In")
        t.connect(node_id, before_id, "Out", before_port)
    _edit(file, fn)
    return f"{after_id} -> {node_id} -> {before_id}"


@mcp.tool()
def gaea_learn_node_types(file: str, keep_params: bool = False) -> dict:
    """Learn every node type in a Gaea-saved .terrain file as a template so
    gaea_add_node can create it. By default new nodes start at Gaea defaults;
    keep_params=true keeps the values set in that file (presets)."""
    return gt.learn_templates(file, keep_params)


@mcp.tool()
def gaea_list_node_types() -> dict:
    """Node types gaea_add_node can create, with their ports and stored params."""
    out = {}
    for k, n in gt.load_templates().items():
        out[k] = {
            "ports": [f"{p['Name']} ({p.get('Type')})" for p in n.get("Ports", {}).get("$values", [])],
            "params": {pk: pv for pk, pv in n.items() if pk not in gt.STRUCT_KEYS},
        }
    return out


@mcp.tool()
def gaea_build(file: str, build_path: str, resolution: int = 1024,
               timeout_s: int = 300) -> dict:
    """Try a headless build with Gaea.Swarm. Only nodes marked for export in
    Gaea produce files. Known issue: on Gaea 2.3 Community the Swarm can hang
    after 'Loading Baked Cache' (probably an edition limit); it is killed after
    timeout_s and the log tail is returned."""
    exe = GAEA_DIR / "Gaea.Swarm.exe"
    if not exe.exists():
        raise gt.GaeaError(f"Gaea.Swarm.exe not found in {GAEA_DIR} (set GAEA_DIR)")
    Path(build_path).mkdir(parents=True, exist_ok=True)
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = 0  # hidden; Swarm needs a real console of its own
    t0 = time.time()
    p = subprocess.Popen(
        [str(exe), "--Filename", file, "--buildpath", build_path,
         "--resolution", str(resolution), "--silent"],
        creationflags=subprocess.CREATE_NEW_CONSOLE, startupinfo=si)
    try:
        code = p.wait(timeout=timeout_s)
        status = "finished"
    except subprocess.TimeoutExpired:
        p.kill()
        code, status = None, "timeout"
    logs = sorted((GAEA_DIR / "Data" / "Logs").glob("*SWARM*.txt"), key=os.path.getmtime)
    tail = logs[-1].read_text(encoding="utf-8", errors="replace").splitlines()[-15:] if logs else []
    files = [str(f) for f in Path(build_path).rglob("*") if f.is_file()]
    return {"status": status, "exit_code": code, "seconds": round(time.time() - t0),
            "files": files, "log_tail": tail}


if __name__ == "__main__":
    mcp.run()
