# Sitemap Generator

Plans the pages of a **new** hotel website before it's built, starting from one of the Pebble packages (Website Packages 2026) and changing it to suit what the client wants.

No install needed: double-click **`Sitemap Generator.html`** and it opens in your web browser. It works offline and nothing is uploaded anywhere.

## How to use

1. Type the **property name**, and the **live domain** if you know it.
2. Pick the **package** the client is looking at. This ticks that package's pages:
   - **Getting Started:** Accommodation (single page), Experiences
   - **Revenue Booster:** Rooms, Experiences, Packages, Gallery
   - **Deluxe Functionality:** adds Dining, Spa, Events
   - **Boutique Custom:** starts like Deluxe; change anything
3. Change it to suit the client:
   - Tick or untick pages: package pages, add-ons (Compendium, Gift Vouchers, Event Tickets, Upcoming Events, Blog) and standard pages (About, Location, Contact, FAQs, Privacy, Terms).
   - Rename a page, change its address, or choose whether it shows in the main menu, the footer, or neither.
   - For **list** pages (Rooms, Dining, Spa, Experiences, Packages, Events, Blog, Compendium), type one item per line. Each item gets its own page, e.g. `/rooms/ocean-king/`.
   - Use ↑ ↓ to set the menu order.
   - **Use short menu names** renames to the Stay / Eat / Play / Offers style.
   - **Add a page** for anything the packages don't cover.
4. Set up the **home page layout**: the sections of the home page, top to bottom (hero, booking bar, welcome intro, teasers, reviews, map, subscribe and so on). Each section has a **Content needed** note saying what has to be supplied, which you can edit. Tick, untick, reorder, rename, or add the client's own sections.
   - Teasers (Rooms, Dining, Spa…) only appear when their page is ticked. Untick Dining and the Dining teaser goes too.
   - Instagram feed and Promotional pop-up are add-ons, so they're listed as extras to quote.
5. The right-hand side shows the finished sitemap, and which package it fits. Anything outside the package (add-ons, custom pages) is listed as an extra to quote.

## Export

| Button | What you get |
|---|---|
| **Save plan (.json)** | Every setting, the page list and the home page sections. Use **Open plan…** to carry on later. |
| **Copy outline** | The indented page list with the home page layout under Home, ready to paste into an email or Google Doc. |
| **Download page list (.csv)** | One row per page: title, address, parent, module, menu. Opens in Google Sheets or Excel. |
| **Download sitemap.xml** | A standard sitemap for search engines. Needs the live domain filled in. |

Your work is also kept in the browser between visits. **Start over** clears it.

## Using it with the scraper

[Content Scraper v3](../v3/) has this tool built in. Its plan picks which pages the old site's content goes to. See the [v3 README](../v3/README.md).
