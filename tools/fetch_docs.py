#!/usr/bin/env python3
"""从 GitBook 拉取原生 Markdown 源文件。

GitBook 公开空间支持在页面 URL 后追加 .md 得到该页 Markdown（带 frontmatter 之外的正文）。
本脚本读取 sitemap-pages.xml 的 URL 列表，逐个抓取并落到 _raw/ 下，保留层级。
"""
import os
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE = "https://madoka315.gitbook.io/ayahelp"
SITEMAP = f"{BASE}/sitemap-pages.xml"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_raw")
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

# GitBook 在 .md 输出开头注入的推广首行，需要剥掉
BOILER = re.compile(r"^>\s*For the complete documentation index.*?\n+", re.S)


def http_get(url: str) -> tuple[int, bytes]:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=45, context=ctx) as r:
        return r.status, r.read()


def get_urls() -> list[str]:
    _, body = http_get(SITEMAP)
    return re.findall(r"<loc>([^<]+)</loc>", body.decode("utf-8"))


def to_md_url(page_url: str) -> str:
    return page_url.rstrip("/") + ".md"


def to_slug(page_url: str) -> str:
    rel = page_url[len(BASE):].strip("/")
    return rel if rel else "index"


def fetch(page_url: str) -> tuple[str, str]:
    slug = to_slug(page_url)
    dest = os.path.join(OUT, slug + ".md")
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return slug, "cached"
    status, body = http_get(to_md_url(page_url))
    if status != 200:
        return slug, f"HTTP {status}"
    text = body.decode("utf-8")
    if not text.lstrip().startswith(">"):
        # 不是 GitBook 的 md 输出，多半是 404 页
        return slug, "unexpected-format"
    text = BOILER.sub("", text, count=1).lstrip("\n")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w", encoding="utf-8") as f:
        f.write(text)
    return slug, "ok"


def main() -> int:
    os.makedirs(OUT, exist_ok=True)
    urls = get_urls()
    print(f"sitemap 共 {len(urls)} 个页面", flush=True)
    results: dict[str, str] = {}
    workers = 6
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(fetch, u): u for u in urls}
        for i, fut in enumerate(as_completed(futs), 1):
            slug, status = fut.result()
            results[slug] = status
            if i % 10 == 0 or i == len(urls):
                print(f"  {i}/{len(urls)}", flush=True)
    bad = {s: v for s, v in results.items() if v not in ("ok", "cached")}
    total = 0
    count = 0
    for root, _, files in os.walk(OUT):
        for name in files:
            total += os.path.getsize(os.path.join(root, name))
            count += 1
    print(f"\n完成: {count} 个文件  未成功 {len(bad)}/{len(urls)}  总字节: {total}")
    if bad:
        print("异常页:")
        for s, v in sorted(bad.items()):
            print(f"  {s}: {v}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
