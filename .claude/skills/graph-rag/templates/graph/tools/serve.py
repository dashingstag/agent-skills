#!/usr/bin/env python3
"""Dev server for the graph explorer (and the source repos) with caching disabled.

Serves the parent of the folder containing tools/ so the loader's relative
source paths resolve wherever this is invoked from:

    python graph/tools/serve.py [port]            # default 8519
"""

import http.server
import os
import sys


class NoStoreHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def log_message(self, fmt, *args):
        pass  # quiet


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8519
    # serve the parent of the app folder so a source's relative path (e.g.
    # "../.." -> the repo root, "../../sibling" -> a sibling repo) resolves
    app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    root = os.path.dirname(app_dir)
    os.chdir(root)
    site_rel = os.path.relpath(os.path.join(app_dir, "site"), root).replace(os.sep, "/")
    http.server.ThreadingHTTPServer.allow_reuse_address = True
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", port), NoStoreHandler)
    print(f"serving {os.getcwd()} on http://localhost:{port}/{site_rel}/")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
