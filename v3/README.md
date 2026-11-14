# Content Scraper v3: plan, scrape and fill

v3 joins the **[Sitemap Generator](../sitemap/)** and the **v2 scraper** into one tool:

1. **Plan** the new site in the Sitemap Generator: its pages, and the sections of its home page.
2. **Scrape** the old site.
3. **Claude sorts the old content into your plan.** Each new page is written from only the old content that belongs on it. The home page follows your section layout, top to bottom.

You get two files that open in Google Docs: the **original** content, and the **new site content**. The new site content contains:

- **Brand profile:** the new site's voice, tone, audience and positioning.
- **Content map:** which old pages feed each new page, which new pages have nothing from the old site, and which old pages were **left out**. This is the filtering: old content that has no place in the new plan doesn't make it into the new pages.
- **One section per new page**, in sitemap order, with an SEO title, meta description, the copy, and notes. Home page copy comes under a heading for each section.

Claude never invents facts. Where a page or section needs something the old site didn't say, it writes `[NEED: ...]` so you can fill it in. A new page with no old content at all gets a `[NEED]` note and no Claude call, so you aren't charged for it.

Without a plan, v3 works exactly like v2: Claude plans the new site itself.

## What you need

The same as v2: Python 3.8+ (on a Mac, also run **Install Certificates.command**) and an **Anthropic API key** with some credit. See the [v2 README](../v2/README.md).

Keep the `sitemap` folder next to the `v3` folder: v3 uses the Sitemap Generator from there. Downloading the whole project, as the main README describes, does this for you.

## How to use

1. Double-click **`Start Scraper v3.bat`** (Windows) or **`Start Scraper v3.command`** (Mac). The page opens at <http://localhost:8002>.
2. Under **New site plan**, click **Open the Sitemap Generator**. It opens in a new tab.
3. Build the plan there (see the [Sitemap Generator README](../sitemap/README.md)). There's no need to save: switch back to the scraper tab and it picks up the plan automatically, showing the page count.
4. Paste the old website's address, add any notes about the new site, and your API key the first time.
5. Click **Start**. Progress shows as it goes.
6. Download **improved content** (the new site content) and/or **original content**.

### Other ways to give it a plan

- **Follow a saved plan file:** choose a `.json` file made with **Save plan** in the Sitemap Generator, e.g. one a colleague emailed you, or one made by opening the Sitemap Generator file directly.
- **No plan:** Claude plans the new site itself, like v2.

Untick **Improve with Claude** to just scrape, at no cost. The plan isn't used then.

## Good to know

- **The Sitemap Generator in v3 keeps its own plan.** Plans you made by double-clicking `Sitemap Generator.html` aren't visible at <http://localhost:8002/sitemap>, and the other way round, because the browser keeps them separately. Use **Save plan** and **Open plan…** to move a plan between them.
- **Check the content map first.** If old content went to the wrong page, or was left out when you need it, you can still find it in the original content file.
- **Cost:** about the same as v2. Pages with no old content cost nothing. The log shows the approximate cost at the end of each run.
- **One failed page doesn't stop the run.** It's marked "Not improved" with the old content that was meant for it.
- v1, v2 and v3 can run at the same time (ports 8000, 8001 and 8002).

## Files

| File | What it is |
|---|---|
| `Start Scraper v3.bat` / `.command` | Double-click to start (Windows / Mac) |
| `ui.py` | The web page; also serves the Sitemap Generator at `/sitemap` |
| `improve.py` | Sends the content and the plan to Claude with the skills |
| `scrape.py` | The scraper (a copy of v1's) |
| `.claude/skills/` | The eight marketing skills (same as v2) |
