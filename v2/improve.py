"""Improve scraped website content with Claude, guided by the marketing skills in .claude/skills."""
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


class Improver:
    def __init__(self, api_key=None, log=print):
        self.client = anthropic.Anthropic(api_key=api_key or None)  # None: SDK reads ANTHROPIC_API_KEY
        self.log, self.usage = log, []

    def ask(self, system, prompt):
        with self.client.beta.messages.stream(
            model=MODEL, max_tokens=64000,
            betas=["server-side-fallback-2026-07-01"], fallbacks="default",  # retry on another model if declined
            output_config={"effort": "high"},
            system=system, messages=[{"role": "user", "content": prompt}],
        ) as stream:
            msg = stream.get_final_message()
        self.usage.append(msg.usage)
        if msg.stop_reason == "refusal":
            raise RuntimeError("Claude declined this request")
        if msg.stop_reason == "max_tokens":
            raise RuntimeError("Claude's answer was cut off (too long)")
        return "".join(b.text for b in msg.content if b.type == "text").strip()

    def run(self, pages, notes=""):
        """pages: list of (title, url, blocks). Returns docx sections: brand profile, site plan, improved pages."""
        site = "\n\n".join(page_text(*p) for p in pages)
        owner = f"\n\nThe site owner's notes for the new site (these win over the old site where they conflict):\n{notes}" if notes.strip() else ""

        self.log("Writing brand profile (product-marketing skill)…")
        brand = self.ask([skills("product-marketing")],
                         "Draft the product marketing context document for the NEW website, based on the old site's "
                         f"content below.{owner}\nInclude a detailed brand voice and tone section. Output only the document.\n\n{site}")
        brand_block = {"type": "text", "text": f"<brand_profile>\n{brand}\n</brand_profile>", "cache_control": {"type": "ephemeral"}}

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

    def cost(self):
        """Approximate USD at Claude Opus 5.5 list prices ($4 in, $20 out, cache write 1.25x, cache read $0.20 per M)."""
        t = lambda f: sum(getattr(u, f, 0) or 0 for u in self.usage)
        return (t("input_tokens") * 4 + t("cache_creation_input_tokens") * 5
                + t("cache_read_input_tokens") * 0.2 + t("output_tokens") * 20) / 1e6


assert to_blocks("## A\n**b** text\n* c\n\n") == ["### A", "b text", "- c"]
