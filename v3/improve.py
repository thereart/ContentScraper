"""Improve scraped website content with Claude, guided by the marketing skills in .claude/skills."""
import json
import pathlib
from concurrent.futures import ThreadPoolExecutor

import anthropic

SKILLS_DIR = pathlib.Path(__file__).parent / ".claude" / "skills"
MODEL = "claude-opus-5-5"

PIPELINE_NOTE = """You are running inside an automated content pipeline, not an interactive chat.
You cannot read files, browse, or ask the user questions. Where a skill says to check a file, ask the user,
or gather data, work from the material given here instead. Never invent facts (prices, amenities, numbers,
awards, reviews, contact details): when copy needs a fact that isn't in the source, write [NEED: what is missing].
Write plain text with Markdown headings (##, ###) and "- " bullets only: no bold, italics, links, tables or code blocks."""


def skills(*names):
    text = "\n\n".join(
        f'<skill name="{n}">\n{(SKILLS_DIR / n / "SKILL.md").read_text(encoding="utf-8")}\n</skill>' for n in names)
    return {"type": "text", "text": text + "\n\n" + PIPELINE_NOTE, "cache_control": {"type": "ephemeral"}}


def to_blocks(md):
    """Claude's Markdown -> the block format scrape.to_docx expects."""
    out = []
    for line in md.splitlines():
        line = line.strip().replace("**", "")
        if not line:
            continue
        if line.startswith("#"):
            line = "#" + line  # "## X" -> "### X" -> Heading 2, under the page heading
        elif line[:2] in ("* ", "• "):
            line = "- " + line[2:]
        out.append(line)
    return out


def page_text(title, url, blocks):
    return f"<page title=\"{title}\" url=\"{url}\">\n" + "\n".join(blocks) + "\n</page>"


MAP_SCHEMA = {
    "type": "object",
    "properties": {"pages": {"type": "array", "items": {
        "type": "object",
        "properties": {"path": {"type": "string"}, "sources": {"type": "array", "items": {"type": "string"}}},
        "required": ["path", "sources"], "additionalProperties": False}}},
    "required": ["pages"], "additionalProperties": False,
}


def sitemap_outline(sitemap):
    """The Sitemap Generator plan as text Claude can read: indented page list, then the home page layout."""
    lines = [f"{'  ' * p['level']}{p['path']}  {p['title']}" for p in sitemap["pages"]]
    if sitemap["homeSections"]:
        lines += ["", "Home page (/) sections, top to bottom:"]
        lines += [f"{i}. {s['label']}: {s['notes']}" for i, s in enumerate(sitemap["homeSections"], 1)]
    return "\n".join(lines)


class Improver:
    def __init__(self, api_key=None, log=print):
        self.client = anthropic.Anthropic(api_key=api_key or None)  # None: SDK reads ANTHROPIC_API_KEY
        self.log, self.usage = log, []

    def ask(self, system, prompt, schema=None):
        """schema: optional JSON schema; the answer is then guaranteed to be JSON matching it."""
        output = {"effort": "high"} | ({"format": {"type": "json_schema", "schema": schema}} if schema else {})
        with self.client.beta.messages.stream(
            model=MODEL, max_tokens=64000,
            betas=["server-side-fallback-2026-07-01"], fallbacks="default",  # retry on another model if declined
            output_config=output,
            system=system, messages=[{"role": "user", "content": prompt}],
        ) as stream:
            msg = stream.get_final_message()
        self.usage.append(msg.usage)
        if msg.stop_reason == "refusal":
            raise RuntimeError("Claude declined this request")
        if msg.stop_reason == "max_tokens":
            raise RuntimeError("Claude's answer was cut off (too long)")
        return "".join(b.text for b in msg.content if b.type == "text").strip()

    def run(self, pages, notes="", sitemap=None):
        """pages: list of (title, url, blocks). sitemap: a plan from the Sitemap Generator, or None to let Claude plan the site.
        Returns docx sections: brand profile, then the site plan (or content map) and one section per page."""
        site = "\n\n".join(page_text(*p) for p in pages)
        owner = f"\n\nThe site owner's notes for the new site (these win over the old site where they conflict):\n{notes}" if notes.strip() else ""

        self.log("Writing brand profile (product-marketing skill)…")
        brand = self.ask([skills("product-marketing")],
                         "Draft the product marketing context document for the NEW website, based on the old site's "
                         f"content below.{owner}\nInclude a detailed brand voice and tone section. Output only the document.\n\n{site}")
        brand_block = {"type": "text", "text": f"<brand_profile>\n{brand}\n</brand_profile>", "cache_control": {"type": "ephemeral"}}
        if sitemap:
            return [("Brand profile", "", to_blocks(brand))] + self.follow_sitemap(pages, sitemap, brand_block, site)

        self.log("Planning the new site (site-architecture, schema, cro skills)…")
        plan = self.ask([skills("site-architecture", "schema", "cro"), brand_block],
                        "Plan the new website from the old site's pages below: the page list and hierarchy (which old pages "
                        "to keep, merge, split, drop or add), navigation, URL structure, recommended schema types per page, "
                        f"and the top conversion improvements. Output only the plan.\n\n{site}")

        page_system = [skills("copy-editing", "copywriting", "seo-audit", "ai-seo"), brand_block]

        def improve(p):
            title, url, blocks = p
            try:
                text = self.ask(page_system,
                                "Rewrite this page for the new website in the brand voice. Edit the existing copy with the "
                                "copy-editing skill (use copywriting where the copy is too weak to edit), and apply on-page "
                                "SEO and AI-search guidance. Keep every fact; add none. Output exactly:\n"
                                "SEO title: ...\nMeta description: ...\nthen the page copy, starting with a ## heading,\n"
                                "then a ## Notes section with '- ' bullets on what changed and any [NEED] items.\n\n"
                                + page_text(title, url, blocks))
                self.log(f"  improved: {url}")
                return title, url, to_blocks(text)
            except Exception as e:  # keep going: one failed page shouldn't lose the rest
                self.log(f"  FAILED {url}: {e}")
                return title, url, [f"[Not improved: {e}]"] + blocks

        self.log(f"Rewriting {len(pages)} pages (copy-editing, copywriting, seo-audit, ai-seo skills)…")
        with ThreadPoolExecutor(4) as pool:
            improved = list(pool.map(improve, pages))
        return [("Brand profile", "", to_blocks(brand)), ("New site plan", "", to_blocks(plan))] + improved

    def follow_sitemap(self, pages, sitemap, brand_block, site):
        """Sort the old content into the planned pages, then write each planned page from only its share."""
        old = {url: (title, url, blocks) for title, url, blocks in pages}
        outline = sitemap_outline(sitemap)
        self.log("Matching old content to the new sitemap (site-architecture skill)…")
        answer = json.loads(self.ask(
            [skills("site-architecture"), brand_block],
            "Below are the NEW website's sitemap and the OLD website's pages. For every page in the new sitemap, list the "
            "URLs of the old pages whose content belongs on it. An old page can feed several new pages (e.g. one old rooms "
            "page feeding each new room page); a new page can have none. Leave out old pages with nothing worth keeping "
            f"on the new site.\n\n<new_sitemap>\n{outline}\n</new_sitemap>\n\n{site}",
            schema=MAP_SCHEMA))
        sources = {m["path"]: [u for u in dict.fromkeys(m["sources"]) if u in old] for m in answer["pages"]}  # drop unknown URLs
        used = {u for urls in sources.values() for u in urls}
        unused = [u for u in old if u not in used]

        content_map = []
        for p in sitemap["pages"]:
            urls = sources.get(p["path"], [])
            content_map.append(f"- {p['path']} {p['title']}: " + (", ".join(urls) if urls else "nothing from the old site"))
        content_map += ["### Old pages not used on the new site"] + [f"- {u} ({old[u][0]})" for u in unused]
        if not unused:
            content_map.append("Every old page was used.")

        page_system = [skills("copy-editing", "copywriting", "seo-audit", "ai-seo"), brand_block,
                       {"type": "text", "text": f"<new_sitemap>\n{outline}\n</new_sitemap>", "cache_control": {"type": "ephemeral"}}]
        home_layout = "\n".join(f"{i}. {s['label']}: {s['notes']}" for i, s in enumerate(sitemap["homeSections"], 1))

        def write(p):
            urls = sources.get(p["path"], [])
            source = p["path"] + (" · from " + ", ".join(urls) if urls else "")
            home = p["path"] == "/" and home_layout
            if not urls and not home:
                return p["title"], source, ["[NEED: the old site has no content for this page. Supply copy, or write it fresh.]"]
            layout = ("Lay the page out as these sections, in this order, each under a ## heading named after the section. "
                      "Follow each section's content note. Where the old content has nothing for a section, put a "
                      f"[NEED: ...] line under its heading:\n{home_layout}\n") if home else ""
            old_content = "\n\n".join(page_text(*old[u]) for u in urls) or "(No old content was matched to this page.)"
            try:
                text = self.ask(page_system,
                                f'Write the "{p["title"]}" page ({p["path"]}) of the new website, as planned in the new sitemap, '
                                "in the brand voice. Build it from the old site content below: edit the existing copy with the "
                                "copy-editing skill (use copywriting where it is too weak to edit), and apply on-page SEO and "
                                "AI-search guidance. Use only what belongs on this page; other pages in the sitemap cover the rest. "
                                f"Keep every fact you use; add none.\n{layout}Output exactly:\n"
                                "SEO title: ...\nMeta description: ...\nthen the page copy" + ("" if home else ", starting with a ## heading")
                                + ",\nthen a ## Notes section with '- ' bullets on what changed, which old pages were used, "
                                f"and any [NEED] items.\n\n{old_content}")
                self.log(f"  written: {p['path']}")
                return p["title"], source, to_blocks(text)
            except Exception as e:  # keep going: one failed page shouldn't lose the rest
                self.log(f"  FAILED {p['path']}: {e}")
                return p["title"], source, [f"[Not improved: {e}]"] + [b for u in urls for b in old[u][2]]

        self.log(f"Writing {len(sitemap['pages'])} new pages (copy-editing, copywriting, seo-audit, ai-seo skills)…")
        with ThreadPoolExecutor(4) as pool:
            written = list(pool.map(write, sitemap["pages"]))
        return [("Content map: old pages → new pages", "", content_map)] + written

    def cost(self):
        """Approximate USD at Claude Opus 5.5 list prices ($4 in, $20 out, cache write 1.25x, cache read $0.20 per M)."""
        t = lambda f: sum(getattr(u, f, 0) or 0 for u in self.usage)
        return (t("input_tokens") * 4 + t("cache_creation_input_tokens") * 5
                + t("cache_read_input_tokens") * 0.2 + t("output_tokens") * 20) / 1e6


assert to_blocks("## A\n**b** text\n* c\n\n") == ["### A", "b text", "- c"]
