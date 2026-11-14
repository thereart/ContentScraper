# Content Scraper

Give it a website address and it reads the text from every page on that site, then saves it all into one organised Word document (`.docx`) that you can open in Google Docs.

The document has a contents list, then one section per page with the page title, its web address, and its text. Headings and bullet points are kept. Menus, headers and footers are left out so they don't repeat on every page.

> **New: [v2](v2/)** also uses Claude to write a brand profile, plan a new site, and rewrite every page for tone, brand and SEO. See the [v2 README](v2/README.md).
>
> **New: [Sitemap Generator](sitemap/)** plans a new site's pages from a Pebble package, customised to what the client wants. See the [Sitemap Generator README](sitemap/README.md).
>
> **New: [v3](v3/)** joins the two: plan the new site in the Sitemap Generator, and Claude sorts the old site's content into that plan, page by page and home page section by section. See the [v3 README](v3/README.md).

## What you need

- A Windows PC or a Mac
- [Python](https://www.python.org/downloads/) 3.8 or newer
  - **Windows:** when installing, tick **"Add Python to PATH"**.
  - **Mac:** after installing, open **Applications → Python 3.x** and double-click **Install Certificates.command**. Without this, every website fails with a `CERTIFICATE_VERIFY_FAILED` error.

Nothing else needs installing.

## Download

Click the green **Code** button on this page → **Download ZIP**, then unzip it somewhere, for example your Documents folder.

Or, if you use git:

```bash
git clone https://github.com/thereart/ContentScraper.git
```

## How to use

1. Start the scraper. A small window opens, and the scraper page opens in your web browser.
   - **Windows:** double-click **`Start Scraper.bat`**.
   - **Mac:** double-click **`Start Scraper.command`**. See [First launch on a Mac](#first-launch-on-a-mac) if it's blocked.
2. Paste a website address, e.g. `https://example.com`.
3. Optionally change **Max pages** (default 200).
4. Click **Scrape**. Each page appears in the list as it's read.
5. When it says **Done**, click the **Download** button to save the `.docx` file.
6. To stop the scraper, close the small window.

If the browser doesn't open by itself, go to <http://localhost:8000>.

### First launch on a Mac

The first time you open `Start Scraper.command`, macOS may block it because it was downloaded from the internet and isn't from a registered Apple developer. To allow it once:

1. Right-click (or Control-click) **`Start Scraper.command`** → **Open** → **Open**.
2. On newer versions of macOS, that may not show an **Open** button. Instead, go to **System Settings → Privacy & Security**, scroll down, and click **Open Anyway** next to the message about `Start Scraper.command`.

After that, double-clicking works normally.

If Mac says the file "could not be executed because you do not have appropriate access privileges", open Terminal, type `chmod +x ` (with a space after it), drag the file into the Terminal window, and press Return.

### Opening the file in Google Docs

1. Go to [Google Drive](https://drive.google.com) and upload the `.docx` file.
2. Right-click it → **Open with** → **Google Docs**.
3. Optional: **Insert → Table of contents** gives you a clickable contents list built from the page headings.

## Using it from the command line (optional)

```bash
python scrape.py https://example.com
```

On a Mac, type `python3` instead of `python`.

This saves `example.com.docx` in the current folder.

- `--max-pages 500` changes the page limit (default 200)
- `--delay 1` waits longer between pages (in seconds, default 0.5)

## Good to know

- **It's polite to websites.** It follows each site's `robots.txt` rules and waits between pages.
- **It only follows links on the same site.** Links to other websites are ignored.
- **Sites built with JavaScript may come out mostly empty.** It reads a page's HTML without running its JavaScript, and some modern web apps only fill in their text with JavaScript.
- **Addresses ending in `?...` count as one page.** On a site that splits content across `?page=2`, `?page=3` and so on, only the first page is saved.
- **Google Docs has a size limit** of about 1 million characters, so a very large site may be too big to open there as one document. Lower **Max pages** if that happens.
- **The web page only works on your own computer.** Other people on your network can't reach it.
- **It runs one scrape at a time.** The result is only kept until you download it or start another scrape.
- **`CERTIFICATE_VERIFY_FAILED` error (Mac):** run **Install Certificates.command** as described in [What you need](#what-you-need).
- **"Port 8000 already in use" error:** the scraper is probably already running in another window. Close that window and try again.

## Files

| File | What it is |
|------|------------|
| `Start Scraper.bat` | Double-click to start (Windows) |
| `Start Scraper.command` | Double-click to start (Mac) |
| `ui.py` | The web page |
| `scrape.py` | The scraper itself, which also works on its own from the command line |
