#!/usr/bin/env python3
"""本地预览 dist/，把 /foo 重写到 /foo.html 或 /foo/index.html。

构建阶段已经用 tools/clean-urls.mjs 生成了 /foo/index.html，静态托管无需额外重写规则；
这里保留兜底逻辑，兼容只访问 foo.html 的情况。
用法：python3 tools/preview.py [端口]
"""
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dist")


class CleanUrlHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def translate_path(self, path):
        resolved = super().translate_path(path)
        if os.path.exists(resolved) and not os.path.isdir(resolved):
            return resolved
        if os.path.isdir(resolved):
            index = os.path.join(resolved, "index.html")
            if os.path.exists(index):
                return index
            return resolved
        for cand in (resolved + ".html", os.path.join(resolved, "index.html")):
            if os.path.exists(cand):
                return cand
        return resolved

    def log_message(self, fmt, *args):
        pass


def main() -> int:
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 3930
    if not os.path.isdir(ROOT):
        print(f"找不到 {ROOT}，请先执行 npm run build", file=sys.stderr)
        return 1
    with ThreadingHTTPServer(("127.0.0.1", port), CleanUrlHandler) as srv:
        print(f"预览： http://127.0.0.1:{port}/", flush=True)
        srv.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
