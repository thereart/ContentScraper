# Content Scraper v2: scrape and improve

v2 scrapes every page of a website, then uses Claude to turn that content into material for a **new** site:

1. **Brand profile:** the new site's voice, tone, audience and positioning, drafted from the old site plus any notes you give it.
2. **New site plan:** which pages to keep, merge, split, drop or add, plus navigation, page addresses, structured data (schema) suggestions and ways to get more bookings or enquiries.
3. **Every page rewritten** in the brand voice, with an SEO title, a meta description, the new copy, and notes on what changed.

You get two files that open in Google Docs: the **original** content and the **improved** content.

Claude never invents facts. Where better copy needs something the old site didn't say (a price, a number, a detail), it writes `[NEED: ...]` so you can fill it in.

The original v1 (scrape only, no Claude) is still in the folder above and works as before.

## The skills it uses

Claude follows eight marketing skills from [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) (MIT licence), stored in `.claude/skills/`:

| Step | Skills |
|---|---|
| Brand profile | `product-marketing` |
| Site plan | `site-architecture`, `schema`, `cro` |
| Page rewrites | `copy-editing`, `copywriting`, `seo-audit`, `ai-seo` |

You can edit any `SKILL.md` to change how Claude works. When you open this folder in Claude Code, the same skills are available there too.

## What you need

- Everything v1 needs (Python 3.8+; on a Mac, also run **Install Certificates.command**; see the main README).
- An **Anthropic API key** from [console.anthropic.com](https://console.anthropic.com), with some credit on the account.

The launcher installs the one extra Python package v2 needs (`anthropic`) the first time it runs.

## How to use

1. Double-click **`Start Scraper v2.bat`** (Windows) or **`Start Scraper v2.command`** (Mac). The page opens at <http://localhost:8001>.
2. Paste the website address.
3. Optional: under **Notes about the new site**, describe what should change, e.g. a new name, target audience, the tone you want, things to stress or avoid. Your notes win over the old site where they conflict.
4. Paste your API key the first time. It's saved on this computer only (in a file called `.api_key`, never uploaded to GitHub).
5. Click **Start**. Progress shows as it goes. Rewriting takes roughly a minute per 4 pages.
6. Download **improved content** and/or **original content**.

Untick **Improve with Claude** to just scrape, like v1, at no cost.

## Cost

v2 uses Claude Opus 5.5. A site with about 25 pages typically costs well under a few US dollars. The log shows the approximate cost at the end of each run. To keep costs down, lower **Max pages**.

## Good to know

- **Check the output before publishing.** Look for `[NEED: ...]` markers and check that facts are correct.
- **One failed page doesn't stop the run.** It's marked "Not improved" in the document with the original text, and the log says why.
- **If Claude declines a request**, the app automatically retries on another Claude model.
- **Mac with Homebrew Python:** if the launcher can't install `anthropic`, run `python3 -m pip install --user anthropic` or use the python.org installer.
- v1 and v2 can run at the same time (ports 8000 and 8001).

## Files

| File | What it is |
|---|---|
| `Start Scraper v2.bat` / `.command` | Double-click to start (Windows / Mac) |
| `ui.py` | The web page |
| `improve.py` | Sends the content to Claude with the skills |
| `scrape.py` | The scraper (a copy of v1's) |
| `.claude/skills/` | The eight marketing skills |
