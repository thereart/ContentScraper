"""Crawl every page of a website and save its text as one organised Word file (opens in Google Docs).

Usage:  python scrape.py https://example.com [--max-pages 200] [--delay 0.5]
Output: <domain>.docx  (table of contents, then one section per page, sorted by URL)
"""
import argparse
import re
import time
import urllib.request
import urllib.robotparser
import zipfile
from collections import deque
from html.parser import HTMLParser
from xml.sax.saxutils import escape
from urllib.parse import urljoin, urldefrag, urlparse

SKIP = {"script", "style", "noscript", "svg", "template", "nav", "footer", "header", "head", "form"}
VOID = {"br", "img", "hr", "input", "meta", "link", "area", "base", "col", "embed", "source", "track", "wbr"}
BLOCK = {"p", "div", "section", "article", "main", "li", "td", "th", "tr", "blockquote", "pre",
         "h1", "h2", "h3", "h4", "h5", "h6", "dd", "dt", "figcaption", "br"}
UA = "ContentScraper/1.0"


class PageParser(HTMLParser):
    """Collects the title, links, and readable text blocks (headings become Markdown #)."""

    def __init__(self):
        super().__init__()
        self.title, self.links, self.blocks = "", [], []
        self.skip_depth, self.in_title, self.buf, self.prefix = 0, False, [], ""

    def flush(self):
        text = " ".join("".join(self.buf).split())
        if text:
            self.blocks.append(self.prefix + text)
        self.buf, self.prefix = [], ""

    def handle_starttag(self, tag, attrs):
        if tag == "a" and (href := dict(attrs).get("href")):
            self.links.append(href)
        if tag == "title":
            self.in_title = True
        if tag in SKIP:
            self.skip_depth += 1
        if self.skip_depth or tag in VOID and tag != "br":
            return
        if tag in BLOCK:
            self.flush()
            if tag[0] == "h" and tag[1:].isdigit():
                self.prefix = "#" * (int(tag[1]) + 2) + " "  # page sections are ##, so h1 -> ###
            elif tag == "li":
                self.prefix = "- "

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
        if tag in SKIP and self.skip_depth:
            self.skip_depth -= 1
        elif tag in BLOCK and not self.skip_depth:
            self.flush()

    def handle_data(self, data):
        if self.in_title:
            self.title += data
        elif not self.skip_depth:
            self.buf.append(data)


def parse(html):
    p = PageParser()
    p.feed(html)
    p.flush()
    # Drop consecutive duplicate blocks (common with nested divs).
    blocks = [b for i, b in enumerate(p.blocks) if i == 0 or b != p.blocks[i - 1]]
    return " ".join(p.title.split()), p.links, blocks


def normalise(url):
    # shortcut: query strings are dropped to avoid endless calendar/filter URLs; keep them if a site pages via ?page=
    u = urlparse(urldefrag(url)[0])
    scheme = "https" if u.scheme in ("http", "https") else u.scheme  # http/https of one page are the same page
    return u._replace(scheme=scheme, query="", path=u.path or "/").geturl()


def crawl(start, max_pages, delay, log=print):
    start = normalise(start)
    host = urlparse(start).netloc
    # Fetch robots.txt ourselves: RobotFileParser.read() sends Python's default user agent,
    # which many sites block with 403 — and the parser then treats the whole site as forbidden.
    robots = urllib.robotparser.RobotFileParser()
    try:
        req = urllib.request.Request(urljoin(start, "/robots.txt"), headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=15) as resp:
            robots.parse(resp.read().decode("utf-8", "replace").splitlines())
    except Exception:
        robots.allow_all = True  # no readable robots.txt means no rules

    queue, seen, pages = deque([start]), {start}, {}
    while queue and len(pages) < max_pages:
        url = queue.popleft()
        if not robots.can_fetch(UA, url):
            continue
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=15) as resp:
                if "text/html" not in resp.headers.get("Content-Type", ""):
                    continue
                final = normalise(resp.geturl())
                html = resp.read().decode(resp.headers.get_content_charset() or "utf-8", "replace")
        except Exception as e:
            log(f"  skip {url}: {e}")
            continue
        if urlparse(final).netloc != host or final in pages:
            continue  # redirected off-site, or to a page we already have
        title, links, blocks = parse(html)
        pages[final] = (title or final, blocks)
        log(f"[{len(pages)}] {final}  ({len(blocks)} blocks)")
        for link in links:
            nxt = normalise(urljoin(final, link))
            if urlparse(nxt).scheme in ("http", "https") and urlparse(nxt).netloc == host and nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
        time.sleep(delay)
    return host, pages


def para(text, style=None, page_break=False):
    text = re.sub("[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)  # control chars are illegal in XML
    ppr = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    br = '<w:r><w:br w:type="page"/></w:r>' if page_break else ""
    return f'<w:p>{ppr}{br}<w:r><w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>'


def to_docx(host, pages, path):
    order = sorted(pages, key=lambda u: urlparse(u).path)  # groups pages by site section
    body = [para(host, "Title"), para(f"{len(pages)} pages"), para("Contents", "Heading1")]
    body += [para(f"{i}. {pages[u][0]} — {urlparse(u).path}") for i, u in enumerate(order, 1)]
    for u in order:
        title, blocks = pages[u]
        body += [para(title, "Heading1", page_break=True), para(f"Source: {u}")]
        for b in blocks:
            if b.startswith("#"):
                level = min(len(b) - len(b.lstrip("#")) - 1, 6)  # "###" (an h1) -> Heading 2
                body.append(para(b.lstrip("# "), f"Heading{level}"))
            else:
                body.append(para("• " + b[2:] if b.startswith("- ") else b))
    W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
    sizes = {"Title": 48, "Heading1": 36, "Heading2": 30, "Heading3": 26, "Heading4": 24, "Heading5": 22, "Heading6": 22}
    styles = "".join(
        f'<w:style w:type="paragraph" w:styleId="{sid}"><w:name w:val="{sid if sid == "Title" else "heading " + sid[-1]}"/>'
        f'<w:pPr><w:keepNext/><w:spacing w:before="240" w:after="120"/></w:pPr><w:rPr><w:b/><w:sz w:val="{sz}"/></w:rPr></w:style>'
        for sid, sz in sizes.items())
    files = {
        "[Content_Types].xml": '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/></Types>',
        "_rels/.rels": '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>',
        "word/_rels/document.xml.rels": '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>',
        "word/styles.xml": f'<?xml version="1.0" encoding="UTF-8"?><w:styles {W}>{styles}</w:styles>',
        "word/document.xml": f'<?xml version="1.0" encoding="UTF-8"?><w:document {W}><w:body>{"".join(body)}</w:body></w:document>',
    }
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, xml in files.items():
            z.writestr(name, xml)


def _selftest():
    title, links, blocks = parse(
        "<html><head><title> Hi </title><script>x=1</script></head><body><nav><a href='/n'>Nav</a></nav>"
        "<h1>Head</h1><p>One <b>two</b></p><ul><li>a</li></ul><a href='/x#y'>link</a></body></html>")
    assert title == "Hi", title
    assert blocks == ["### Head", "One two", "- a", "link"], blocks
    assert "/n" in links and "/x#y" in links
    assert normalise("https://a.com/x?q=1#f") == "https://a.com/x"
    assert normalise("http://a.com") == "https://a.com/"


if __name__ == "__main__":
    _selftest()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url")
    ap.add_argument("--max-pages", type=int, default=200)
    ap.add_argument("--delay", type=float, default=0.5, help="seconds between requests")
    a = ap.parse_args()
    if "://" not in a.url:
        a.url = "https://" + a.url
    host, pages = crawl(a.url, a.max_pages, a.delay)
    path = host.replace(":", "_") + ".docx"
    to_docx(host, pages, path)
    print(f"\nSaved {len(pages)} pages to {path}")
