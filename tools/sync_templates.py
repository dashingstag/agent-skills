#!/usr/bin/env python3
"""Regenerate skills/graph-rag/templates/graph/ from the live graphrag app.

Copies the app files (site/ + tools/, minus generated artifacts) from a dev
checkout and applies the template substitutions (REPO-NAME placeholders, a
generic sources.js). Keeps the skill's templates in sync with the real app
instead of hand-maintaining two copies.

Usage:
    python tools/sync_templates.py [--src <path-to-graphrag-repo>]
"""

import argparse
import io
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEST = os.path.join(REPO, "skills", "graph-rag", "templates", "graph")

COPY_FILES = [
    "site/index.html",
    "site/sources.js",
    "site/assets/app.js",
    "site/assets/chat.js",
    "site/assets/data.js",
    "site/assets/detail.js",
    "site/assets/graph.js",
    "site/assets/search.js",
    "site/assets/style.css",
    "site/vendor/force-graph.min.js",
    "tools/serve.py",
    "tools/smoke.js",
    "tools/ingest.py",
    "launch.bat",
]

# sources.js is rewritten, not copied — the template default assumes the app
# sits at <repo>/graph/ and documents the explicit-URL escape hatches.
SOURCES_JS = '''// Repos to load — paths are relative to this site/ directory. The default
// assumes this folder lives at <repo>/graph/ and the manual's generated
// bundles are at <repo>/site/. Add siblings the same way, or point map: (and
// optionally notation:/lore:) at ANY url that sets window.CONCEPT_MAP /
// NOTATION / LORE — the source doesn't have to be an understanding-* manual.
window.GRAPH_SOURCES = [
  { "id": "main", "label": "REPO-NAME", "path": "../.." },
  // { "id": "other", "label": "Another manual", "path": "../../other-repo" },
  // { "id": "x", "label": "Custom", "map": "../x/site/map.js", "notation": null, "lore": null },
];
'''

SUBS = [
    ("graphrag — concept map explorer", "REPO-NAME — concept map explorer"),
    ("<h1>graphrag</h1>", "<h1>REPO-NAME</h1>"),
]

TEXT_EXT = (".html", ".js", ".css", ".py", ".bat", ".md", ".json")


def read_text(p):
    with io.open(p, encoding="utf-8") as f:
        return f.read()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src", default=os.path.join(os.path.dirname(REPO), "graphrag"),
                    help="dev checkout of the graphrag app (default: sibling dir)")
    args = ap.parse_args()
    src = os.path.abspath(args.src)
    if not os.path.isfile(os.path.join(src, "site", "index.html")):
        sys.exit(f"source app not found at {src} (expected site/index.html)")

    copied, skipped = 0, []
    for rel in COPY_FILES:
        sp = os.path.join(src, rel)
        dp = os.path.join(DEST, rel)
        if not os.path.isfile(sp):
            skipped.append(rel)
            continue
        os.makedirs(os.path.dirname(dp), exist_ok=True)
        if rel == "site/sources.js":
            content = SOURCES_JS
        elif rel.endswith(TEXT_EXT):
            content = read_text(sp)
            for a, b in SUBS:
                content = content.replace(a, b)
        else:
            with open(sp, "rb") as f:
                content = f.read()
        if isinstance(content, str):
            with io.open(dp, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
        else:
            with open(dp, "wb") as f:
                f.write(content)
        copied += 1

    print(f"synced {copied} file(s) -> {os.path.relpath(DEST, REPO)}")
    for s in skipped:
        print(f"skip (missing): {s}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
