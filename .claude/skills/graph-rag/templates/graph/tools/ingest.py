#!/usr/bin/env python3
"""Bake the sibling learning-journal repos into site/graph-data.js.

Reads the repo list from site/sources.js (window.GRAPH_SOURCES — the same
contract the app loads; paths are relative to site/), then for each repo loads
map.json, notation.json and lore.json, scans concepts/ for pages, and greps
every page for data-* links so satellite nodes (symbols, formulas, people,
theorems) and concept-mention edges can be drawn.

Output: site/graph-data.js  ->  window.GRAPH_DATA = {generated, sources, levels,
nodes, links}.  All node ids are prefixed "<src>:<id>" to avoid collisions.

Usage:
    python tools/ingest.py                 # bake
    python tools/ingest.py --embed-articles  # also inline each index.md body
"""

import argparse
import io
import json
import os
import re
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

RE_DATA_TAG = re.compile(r'data-(concept-link|notation|formula|person|theorem)="([^"]+)"')
RE_BACKTICK = re.compile(r'`([a-z0-9][a-z0-9\-]*)`')
RE_SOURCES = re.compile(r'GRAPH_SOURCES\s*=\s*(\[.*?\])\s*;', re.S)

SAT_PREFIX = {"symbol": "sym", "formula": "frm", "person": "per", "theorem": "thm"}


def load_sources():
    """The single contract: parse window.GRAPH_SOURCES from site/sources.js.
    Each 'path' is relative to site/ — resolve it there."""
    src_js = os.path.join(ROOT, "site", "sources.js")
    m = RE_SOURCES.search(read_text(src_js))
    if not m:
        sys.exit(f"could not parse GRAPH_SOURCES in {src_js}")
    # the literal is JSON-superset JS — tolerate trailing commas
    return json.loads(re.sub(r",\s*([}\]])", r"\1", m.group(1)))


def load_json(path):
    with io.open(path, encoding="utf-8") as f:
        return json.load(f)


def read_text(path):
    try:
        with io.open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def scan_concept_dirs(repo_dir):
    """Walk concepts/ -> {concept-id: {dir, article, playback, page_files}}."""
    cdir = os.path.join(repo_dir, "concepts")
    found = {}
    if not os.path.isdir(cdir):
        return found
    for root, dirs, files in os.walk(cdir):
        dirs[:] = [d for d in dirs if d != "assets"]
        if os.path.normpath(root) == os.path.normpath(cdir):
            continue
        cid = os.path.basename(root)
        rel = os.path.relpath(root, repo_dir).replace(os.sep, "/")
        found[cid] = {
            "dir": rel,
            "root": root,
            "article": "index.md" in files,
            "playback": "playback.html" in files,
            "md_path": os.path.join(root, "index.md"),
            "page_files": [
                os.path.join(root, f)
                for f in files
                if f.endswith((".html", ".md"))
            ],
        }
    return found


def ingest_source(src, embed_articles, nodes, links, warnings):
    sid, label, path = src["id"], src["label"], src["path"]
    repo_dir = os.path.normpath(os.path.join(ROOT, "site", path))
    if not os.path.isdir(repo_dir):
        warnings.append(f"source {sid}: {repo_dir} not found")
        return None

    cmap = load_json(os.path.join(repo_dir, "map.json"))
    notation = load_json(os.path.join(repo_dir, "notation.json"))
    lore = load_json(os.path.join(repo_dir, "lore.json"))
    progress_path = os.path.join(repo_dir, "progress", "levels.json")
    progress = load_json(progress_path) if os.path.isfile(progress_path) else {}
    concept_ids = {n["id"] for n in cmap.get("nodes", [])}
    folders = scan_concept_dirs(repo_dir)
    base = os.path.relpath(repo_dir, os.path.join(ROOT, "site")).replace(os.sep, "/")

    def nid(raw):
        return f"{sid}:{raw}"

    def sat_id(kind, raw):
        return f"{sid}:{SAT_PREFIX[kind]}:{raw}"

    # --- concept nodes + dependency edges ---
    for n in cmap.get("nodes", []):
        cid = n["id"]
        info = folders.get(cid, {})
        rel = info.get("dir")
        node = {
            "id": nid(cid),
            "cid": cid,
            "repo": sid,
            "repoLabel": label,
            "type": "concept",
            "title": n.get("title", cid),
            "summary": n.get("summary", ""),
            "level": n.get("level", 0),
            "ownerLevel": progress.get(cid),
            "video": n.get("video"),
            "assess": n.get("assess"),
            "playback": f"{base}/{rel}/playback.html" if info.get("playback") else None,
            "article": f"{base}/{rel}/index.html" if info.get("article") else None,
        }
        if embed_articles and info.get("article"):
            node["articleText"] = read_text(info["md_path"])
        nodes.append(node)
        for p in n.get("parents", []):
            if p not in concept_ids:
                warnings.append(f"{sid}:{cid}: unknown parent '{p}'")
                continue
            links.append({
                "source": nid(cid),
                "target": nid(p),
                "kind": "deps",
                "why": (n.get("why") or {}).get(p, ""),
            })

    # --- page tag scan: mentions + satellite usage ---
    sat_used = set()
    for cid, info in folders.items():
        seen_concept = set()
        for fp in info["page_files"]:
            text = read_text(fp)
            for kind, raw in RE_DATA_TAG.findall(text):
                if kind == "concept-link":
                    if raw != cid and raw in concept_ids and raw not in seen_concept:
                        seen_concept.add(raw)
                        links.append({"source": nid(cid), "target": nid(raw), "kind": "mentions"})
                elif kind in SAT_PREFIX:
                    sat_used.add((kind, raw))
                    links.append({"source": nid(cid), "target": sat_id(kind, raw), "kind": "uses"})
            if fp.endswith(".md"):
                for raw in RE_BACKTICK.findall(text):
                    if raw != cid and raw in concept_ids and raw not in seen_concept:
                        seen_concept.add(raw)
                        links.append({"source": nid(cid), "target": nid(raw), "kind": "mentions"})

    # --- satellite nodes ---
    for s in notation.get("symbols", []):
        nodes.append({
            "id": sat_id("symbol", s["id"]), "sid": s["id"], "repo": sid,
            "repoLabel": label, "type": "symbol", "title": s.get("name", s["id"]),
            "summary": s.get("meaning", ""), "tex": s.get("tex", ""),
            "concept": nid(s["concept"]) if s.get("concept") in concept_ids else None,
        })
        if s.get("concept") in concept_ids:
            sat_used.add(("symbol", s["id"]))
            links.append({"source": nid(s["concept"]), "target": sat_id("symbol", s["id"]), "kind": "uses"})
    for f in notation.get("formulas", []):
        nodes.append({
            "id": sat_id("formula", f["id"]), "sid": f["id"], "repo": sid,
            "repoLabel": label, "type": "formula", "title": f.get("name", f["id"]),
            "summary": f.get("meaning", ""), "tex": f.get("tex", ""),
            "concept": nid(f["concept"]) if f.get("concept") in concept_ids else None,
        })
        if f.get("concept") in concept_ids:
            sat_used.add(("formula", f["id"]))
            links.append({"source": nid(f["concept"]), "target": sat_id("formula", f["id"]), "kind": "uses"})
    for p in lore.get("people", []):
        nodes.append({
            "id": sat_id("person", p["id"]), "sid": p["id"], "repo": sid,
            "repoLabel": label, "type": "person", "title": p.get("name", p["id"]),
            "summary": f"{p.get('dates', '')} — {p.get('famous_for', '')}".strip(" —"),
            "wiki": p.get("wiki"),
        })
    for t in lore.get("theorems", []):
        nodes.append({
            "id": sat_id("theorem", t["id"]), "sid": t["id"], "repo": sid,
            "repoLabel": label, "type": "theorem", "title": t.get("name", t["id"]),
            "summary": t.get("text", ""), "status": t.get("status"),
        })

    return {"id": sid, "label": label, "path": path, "base": base,
            "root": nid(cmap["root"]) if cmap.get("root") else None,
            "levels": cmap.get("levels", [])}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--embed-articles", action="store_true",
                    help="inline each concept's index.md text for chat context")
    args = ap.parse_args()

    nodes, links, warnings, sources, levels = [], [], [], [], []
    for src in load_sources():
        info = ingest_source(src, args.embed_articles, nodes, links, warnings)
        if info:
            sources.append(info)
            if not levels and info["levels"]:
                levels = info["levels"]

    # drop links pointing at nodes that were never emitted
    ids = {n["id"] for n in nodes}
    links = [l for l in links if l["source"] in ids and l["target"] in ids]

    data = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sources": sources,
        "levels": levels,
        "nodes": nodes,
        "links": links,
    }

    site_dir = os.path.join(ROOT, "site")
    os.makedirs(site_dir, exist_ok=True)
    payload = json.dumps(data, ensure_ascii=False)
    with io.open(os.path.join(site_dir, "graph-data.js"), "w", encoding="utf-8") as f:
        f.write("// Generated by tools/ingest.py — do not edit.\n")
        f.write("window.GRAPH_DATA = " + payload + ";\n")
    with io.open(os.path.join(site_dir, "graph-data.json"), "w", encoding="utf-8") as f:
        f.write(payload)

    n_concepts = sum(1 for n in nodes if n["type"] == "concept")
    print(f"nodes: {len(nodes)} ({n_concepts} concepts), links: {len(links)}")
    for w in warnings:
        print("warning:", w, file=sys.stderr)


if __name__ == "__main__":
    main()
