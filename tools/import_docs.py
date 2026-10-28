#!/usr/bin/env python3
"""把 _raw/ 下 GitBook 导出的 Markdown 转换成 Rspress 站点内容。

职责：
1. 按 llms.txt 的顺序和标题重建目录树（它记录了原站的真实导航顺序）
2. GitBook 专有语法 -> Rspress 等价物
3. 下载外链图片到 docs/public/images 并改写为站内路径
4. 生成 docs/_meta.json 全局侧边栏

用法：python3 tools/import_docs.py
"""
import hashlib
import os
import re
import ssl
import sys
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "_raw")
DOCS = os.path.join(ROOT, "docs")
PUBLIC = os.path.join(DOCS, "public")
IMGDIR = os.path.join(PUBLIC, "images")
BASE = "https://madoka315.gitbook.io/ayahelp"

HINT_STYLE = {"success": "tip", "info": "info", "warning": "warning", "danger": "danger"}

VOID_TAGS = ("img", "br", "hr", "input", "source", "meta", "link", "col", "area")

KNOWN_TAG = (
    r"(?:details|summary|br|hr|img|p|div|span|figure|figcaption|table|thead|tbody|"
    r"tfoot|tr|td|th|a|b|i|u|em|strong|mark|code|pre|kbd|ul|ol|li|blockquote|"
    r"h[1-6]|source|center|font|video|iframe|small|sub|sup|del|hgourp|wbr)"
)

CTX = ssl.create_default_context()
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


# ---------- 读取 llms.txt 拿到目录顺序 ----------

def load_toc() -> list[dict]:
    txt = open(os.path.join(ROOT, "llms.txt"), encoding="utf-8").read()
    entries = []
    for m in re.finditer(r"^- \[([^\]]+)\]\(([^)]+)\)(?::\s*(.*))?$", txt, re.M):
        title, url, desc = m.group(1), m.group(2), (m.group(3) or "").strip()
        if not url.startswith(BASE):
            continue
        slug = url[len(BASE):].lstrip("/").removesuffix(".md")
        if not slug:
            continue
        entries.append({"title": title, "slug": slug, "desc": desc})
    return entries


# ---------- 图片处理 ----------

def find_md_images(text: str) -> list[tuple[int, int, str, str]]:
    """返回 [(start, end, alt, url)]，容忍 URL 内转义过的括号。"""
    out = []
    i = 0
    while True:
        i = text.find("![", i)
        if i < 0:
            break
        j = text.find("](", i + 2)
        if j < 0:
            break
        alt = text[i + 2:j]
        k = j + 2
        depth = 0
        while k < len(text):
            ch = text[k]
            if ch == "\\":
                k += 2
                continue
            if ch == "(":
                depth += 1
            elif ch == ")":
                if depth == 0:
                    break
                depth -= 1
            k += 1
        out.append((i, k + 1, alt, text[j + 2:k]))
        i = k + 1
    return out


def find_html_images(text: str) -> list[tuple[int, int, str]]:
    out = []
    for m in re.finditer(r"<img\s[^>]*?src=[\"']([^\"']+)[\"']", text):
        out.append((m.start(1), m.end(1), m.group(1)))
    return out


def decode_camo(url: str) -> str:
    """camo.githubusercontent.com/<hmac>/<hex> 里用 hex 编码了真实图片地址。"""
    parts = url.split("/")
    if len(parts) < 2:
        return url
    try:
        return bytes.fromhex(parts[-1]).decode("utf-8")
    except Exception:  # noqa: BLE001
        return url


def unescape_url(u: str) -> str:
    u = u.replace("\\(", "(").replace("\\)", ")").replace("\\_", "_").replace("\\-", "-")
    if "camo.githubusercontent.com" in u:
        return decode_camo(u)
    return u


def safe_name(url: str, idx: int) -> str:
    path = urllib.parse.urlparse(url).path
    base = os.path.basename(path)
    base = urllib.parse.unquote(base)
    base = re.sub(r"[^A-Za-z0-9._-]", "_", base).strip("_")
    if len(base) > 60:
        h = hashlib.md5(url.encode()).hexdigest()[:8]
        ext = os.path.splitext(base)[1][:8]
        base = base[:40] + "_" + h + ext
    return f"{idx:02d}_{base or 'image.png'}"


class ImageStore:
    def __init__(self) -> None:
        self.mapping: dict[str, str] = {}
        self.failed: list[tuple[str, str]] = []
        self.idx = 0

    def local_for(self, url: str) -> str:
        url = unescape_url(url)
        if not url.lower().startswith(("http://", "https://")):
            return url
        if url in self.mapping:
            return self.mapping[url]
        self.idx += 1
        name = safe_name(url, self.idx)
        dest = os.path.join(IMGDIR, name)
        if os.path.exists(dest) and os.path.getsize(dest) >= 512:
            rel = "/images/" + name
            self.mapping[url] = rel
            return rel
        last = ""
        for attempt in range(3):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=45, context=CTX) as r:
                    data = r.read()
                if len(data) < 512:
                    raise ValueError(f"响应过小 {len(data)}B")
                os.makedirs(IMGDIR, exist_ok=True)
                with open(dest, "wb") as f:
                    f.write(data)
                rel = "/images/" + name
                self.mapping[url] = rel
                return rel
            except Exception as e:  # noqa: BLE001
                last = str(e)
        self.failed.append((url, last))
        return url


# ---------- 正文转换 ----------

def close_void_tags(text: str) -> str:
    def repl(m: re.Match) -> str:
        attrs = m.group(2).rstrip()
        return f"<{m.group(1)}{attrs} />" if attrs else f"<{m.group(1)} />"

    return re.sub(rf"<({'|'.join(VOID_TAGS)})\b([^>]*?)/?>", repl, text, flags=re.I)


def convert_autolinks(text: str) -> str:
    # 跳过已经是 markdown 目标地址的 (<url>) 形式
    return re.sub(r"(?<!\()<((?:https?|mailto):[^<>\s]+)>", r"[\1](\1)", text)


def repair_broken_links(text: str) -> str:
    """原文档里有些链接文本被换行截断，这里把换行接回去。"""
    prev = None
    while prev != text:
        prev = text
        text = re.sub(
            r"\[([^\[\]\(\)]*)\n+([^\[\]\(\)]*)\]\(",
            lambda m: "[" + m.group(1) + m.group(2) + "](",
            text,
        )
    return text


def escape_angle_brackets(text: str) -> str:
    """把非标签用途的字面 < 转成实体，避免 MDX 当成 JSX 解析。"""
    return re.sub(rf"<(?![/!]?{KNOWN_TAG}\b|https?:|!)" , "&lt;", text)


def escape_braces(text: str) -> str:
    return text.replace("{", "&#123;").replace("}", "&#125;")


def protect_inline_code(text: str) -> tuple[str, list[str]]:
    spans: list[str] = []

    def repl(m: re.Match) -> str:
        spans.append(m.group(0))
        return f"\x00SPAN{len(spans) - 1}\x00"

    return re.sub(r"`[^`\n]+`", repl, text), spans


def restore_inline_code(text: str, spans: list[str]) -> str:
    for i, s in enumerate(spans):
        text = text.replace(f"\x00SPAN{i}\x00", s)
    return text


def protect_code_blocks(text: str) -> tuple[str, list[str]]:
    blocks: list[str] = []

    def repl(m: re.Match) -> str:
        blocks.append(m.group(0))
        return f"\x00CODE{len(blocks) - 1}\x00"

    return re.sub(r"```.*?```", repl, text, flags=re.S), blocks


def restore_code_blocks(text: str, blocks: list[str]) -> str:
    for i, b in enumerate(blocks):
        text = text.replace(f"\x00CODE{i}\x00", b)
    return text


def convert_hints(text: str) -> str:
    def repl(m: re.Match) -> str:
        style = m.group(1)
        return f':::{HINT_STYLE.get(style, "info")}\n'

    text = re.sub(r"{%\s*hint\s+style=\"([^\"]+)\"\s*%}\n?", repl, text)
    text = re.sub(r"{%\s*endhint\s*%}\n?", ":::\n\n", text)
    return text


def convert_tabs(text: str) -> str:
    # 1) 先删掉被 GitBook 误转成表格单元格的结束标记行
    text = re.sub(r"^\|(?:\s*{%\s*(?:endtab|endtabs)\s*%}\s*\|.*)$\n?", "", text, flags=re.M)
    # 2) 其余标签清理
    text = re.sub(r"{%\s*tabs\s*%}\n?", "", text)
    text = re.sub(r"{%\s*(?:endtab|endtabs)\s*%}\n?", "", text)
    # tab 标题 -> 小节标题
    def repl(m: re.Match) -> str:
        return f'\n#### {m.group(1)}\n\n'

    return re.sub(r"{%\s*tab\s+title=\"([^\"]+)\"\s*%}\n?", repl, text)


def convert_content_ref(text: str) -> str:
    # {% content-ref %}...[](url)...{% endcontent-ref %}
    text = re.sub(r"{%\s*content-ref[^%]*%}\n?", "", text)
    return re.sub(r"{%\s*endcontent-ref\s*%}\n?", "", text)


def convert_file_block(text: str) -> str:
    """GitBook 附件块无法迁移（源文件里没有可解析的地址），改为提示。"""
    def repl(m: re.Match) -> str:
        return "> 原始附件（GitBook 托管）未迁移，如有需要请手动补充。\n"

    return re.sub(r"{%\s*file\s+src=\"[^\"]+\"\s*%}\n?", repl, text)


MARK_TAG = re.compile(r"<mark\b[^>]*>.*?</mark>", re.S)


def _bold_core(s: str) -> str:
    core = s.strip()
    if not core or (core.startswith("**") and core.endswith("**")):
        return s
    lead = s[: len(s) - len(s.lstrip())]
    trail = s[len(s.rstrip()):]
    return f"{lead}**{core}**{trail}"


def demote_state_headings(text: str) -> str:
    """「该服务默认启用/禁用」在 GitBook 源里是 #### 标题，会混进页面大纲，降为加粗段落。"""
    def repl(m: re.Match) -> str:
        line = m.group(2)
        parts = []
        pos = 0
        for t in MARK_TAG.finditer(line):
            parts.append(_bold_core(line[pos:t.start()]))
            tag = t.group(0)
            open_end = tag.index(">") + 1
            close_start = tag.rindex("</mark>")
            parts.append(
                tag[:open_end] + _bold_core(tag[open_end:close_start]) + tag[close_start:]
            )
            pos = t.end()
        parts.append(_bold_core(line[pos:]))
        return "".join(parts)

    return re.sub(r"(?m)^(#{1,6} )(该服务默认.*)$", repl, text)


def rewrite_internal_links(text: str) -> str:
    """把 /ayahelp/<slug>.md[#anchor] 这类站内链接改成新站的路由。"""
    def repl(m: re.Match) -> str:
        target = "/" + m.group(1)
        if m.group(2):
            target += m.group(2)
        return f"]({target})"

    text = re.sub(r"\]\(<?/ayahelp/([^)#]+?)\.md(#[^)>]*)?>?\)", repl, text)
    return re.sub(r"\]\(<?/ayahelp/?>?\)", "](/", text)


def strip_leading_h1(text: str) -> str:
    lines = text.lstrip("\n").split("\n")
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    return "\n".join(lines).lstrip("\n")


def first_paragraph(text: str) -> str:
    for line in text.split("\n"):
        s = line.strip()
        if not s or s.startswith(("#", "|", "<", ">", ":", "-", "*", "[")):
            continue
        if "http" in s:
            continue
        s = re.sub(r"[*`\[\]\\]", "", s).strip()
        if len(s) < 8:
            continue
        return s[:80]
    return ""


def yaml_str(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def normalize_line_endings(text: str) -> str:
    """原文档里混入了裸 CR 和 CR/LF 实体，会把链接结构撑坏。"""
    text = text.replace("\r\n", "\n").replace("\r", "")
    return text.replace("&#xD;", "").replace("&#xA;", "")


def convert(text: str, store: ImageStore) -> str:
    text = normalize_line_endings(text)
    text = repair_broken_links(text)
    text, blocks = protect_code_blocks(text)
    text, spans = protect_inline_code(text)
    text = convert_tabs(text)
    text = convert_hints(text)
    text = convert_content_ref(text)
    text = convert_file_block(text)
    text = demote_state_headings(text)
    text = close_void_tags(text)
    imgs = []
    for start, end, alt, url in find_md_images(text):
        imgs.append(("md", start, end, alt, url))
    for start, end, url in find_html_images(text):
        imgs.append(("html", start, end, "", url))
    for kind, start, end, alt, url in sorted(imgs, key=lambda x: x[1], reverse=True):
        local = store.local_for(url)
        if kind == "md":
            repl = f"![{alt}]({local})"
        else:
            repl = local
        text = text[:start] + repl + text[end:]
    text = text.replace("\\<", "&lt;")
    text = convert_autolinks(text)
    text = escape_angle_brackets(text)
    text = escape_braces(text)
    text = rewrite_internal_links(text)
    text = restore_inline_code(text, spans)
    text = restore_code_blocks(text, blocks)
    return text.rstrip() + "\n"


# ---------- 落盘 ----------

def target_path(slug: str, has_children: set[str]) -> str:
    parts = slug.split("/")
    if len(parts) == 1 and slug in has_children:
        return os.path.join(DOCS, slug, "index.md")
    return os.path.join(DOCS, *parts) + ".md"


def main() -> int:
    toc = load_toc()
    if not toc:
        print("llms.txt 未解析出条目", file=sys.stderr)
        return 1
    has_children = {s["slug"].split("/")[0] for s in toc if "/" in s["slug"]}
    store = ImageStore()
    os.makedirs(DOCS, exist_ok=True)
    dir_metas = {}

    written = []
    for e in toc:
        src = os.path.join(RAW, e["slug"] + ".md")
        if not os.path.exists(src):
            print(f"缺少源文件: {e['slug']}", file=sys.stderr)
            continue
        body = convert(open(src, encoding="utf-8").read(), store)
        desc = e["desc"] or first_paragraph(body)
        fm = "---\n"
        fm += f"title: {yaml_str(e['title'])}\n"
        if desc:
            fm += f"description: {yaml_str(desc)}\n"
        fm += "---\n\n"
        dest = target_path(e["slug"], has_children)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w", encoding="utf-8") as f:
            f.write(fm + body)
        written.append((e, dest))
        d = os.path.dirname(dest)
        name = os.path.basename(dest)[:-3]
        if d != DOCS and name != "index":
            dir_metas.setdefault(d, []).append({"type": "file", "name": name, "label": e["title"]})

    # 生成全局侧边栏（根节点 _meta.json）
    meta = []
    seen_dirs = set()
    # 有子页面的父级章节自身是 index.md，由 dir 项承载，不能再生成同名的 file 项
    parent_to_skip = set(has_children)
    for e, _dest in written:
        slug = e["slug"]
        if "/" in slug:
            head = slug.split("/")[0]
            if head in seen_dirs:
                continue
            seen_dirs.add(head)
            parent_to_skip.add(head)
            title = next(x["title"] for x in toc if x["slug"] == head)
            meta.append({
                "type": "dir",
                "name": head,
                "label": title,
                "collapsible": True,
                "collapsed": False,
            })
        else:
            if slug in parent_to_skip:
                continue
            meta.append({"type": "file", "name": slug, "label": e["title"]})
    # 开发者专区（密码门保护，见 theme/DevMode.tsx）不来自 GitBook 源，固定追加在末尾
    meta.append({
        "type": "dir",
        "name": "kai-fa-zhe-gong-neng",
        "label": "开发者功能",
        "collapsible": True,
        "collapsed": True,
    })
    import json
    with open(os.path.join(DOCS, "_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
        f.write("\n")
    for d, items in dir_metas.items():
        with open(os.path.join(d, "_meta.json"), "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
            f.write("\n")

    print(f"生成页面 {len(written)} 个，图片 {len(store.mapping)} 张")
    print(f"侧边栏目录项 {len(meta)} 条")
    if store.failed:
        print(f"\n图片下载失败 {len(store.failed)} 个（已保留原链接）:")
        for u, err in store.failed:
            print(f"   {u[:90]} -> {err}")

    leftover = []
    for root, _dirs, files in os.walk(DOCS):
        for name in files:
            if not name.endswith(".md"):
                continue
            p = os.path.join(root, name)
            t = open(p, encoding="utf-8").read()
            if "{%" in t or "&#123;" in t and re.search(r"&#123;[^&]*%", t):
                leftover.append(os.path.relpath(p, DOCS))
    if leftover:
        print("\n仍含未处理 GitBook 标签的页面:")
        for p in leftover:
            print(f"   {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
