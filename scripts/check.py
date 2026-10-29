from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, unquote
import json
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://bellussi1.github.io/read-ecosystem/"

class Check(HTMLParser):
    def __init__(self, filename):
        super().__init__(convert_charrefs=True)
        self.filename = filename
        self.ids = set()
        self.refs = []
        self.headings = []
        self.language = None
        self.meta = set()
        self.canonical = None
        self.alternates = set()
        self.in_json = False
        self.json_text = ""
        self.has_main = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html": self.language = a.get("lang")
        if tag == "main": self.has_main = True
        if a.get("id"): self.ids.add(a["id"])
        if tag == "h1": self.headings.append(tag)
        if tag == "img":
            assert "alt" in a, f"{self.filename}: image missing alt"
            assert a.get("width") and a.get("height"), f"{self.filename}: image missing dimensions"
        if tag == "meta": self.meta.add(a.get("name") or a.get("property"))
        if tag == "link" and a.get("rel") == "canonical": self.canonical = a.get("href")
        if tag == "link" and a.get("rel") == "alternate" and a.get("hreflang"): self.alternates.add(a["hreflang"])
        if tag == "script" and a.get("type") == "application/ld+json": self.in_json = True
        if tag in ("a", "link"): self.refs.append(a.get("href", ""))
        if tag == "img": self.refs.append(a.get("src", ""))
    def handle_endtag(self, tag):
        if tag == "script": self.in_json = False
    def handle_data(self, data):
        if self.in_json: self.json_text += data

for rel, lang, url in [("index.html", "pt-BR", BASE), ("en/index.html", "en", BASE + "en/")]:
    f = ROOT / rel
    parser = Check(rel)
    parser.feed(f.read_text(encoding="utf-8-sig"))
    assert parser.language == lang and parser.headings == ["h1"] and parser.has_main, rel
    assert parser.canonical == url and {"pt-BR", "en", "x-default"} <= parser.alternates, rel
    assert {"description", "og:title", "og:description", "og:image", "viewport"} <= parser.meta, rel
    assert json.loads(parser.json_text)["url"] == url, rel
    for ref in parser.refs:
        target = urlsplit(ref)
        if target.scheme or target.netloc: continue
        if not target.path:
            if target.fragment: assert target.fragment in parser.ids, f"{rel}: missing anchor {ref}"
            continue
        candidate = (f.parent / unquote(target.path)).resolve()
        assert candidate.is_relative_to(ROOT), f"{rel}: path escapes site {ref}"
        if candidate.is_dir(): candidate = candidate / "index.html"
        assert candidate.is_file(), f"{rel}: missing {ref}"

sitemap = ET.parse(ROOT / "sitemap.xml")
urls = {e.text for e in sitemap.findall("{http://www.sitemaps.org/schemas/sitemap/0.9}url/{http://www.sitemaps.org/schemas/sitemap/0.9}loc")}
assert urls == {BASE, BASE + "en/"}, urls
print("Static checks passed for both languages.")
