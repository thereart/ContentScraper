"""v2 web UI: scrape a site, then improve it with Claude. Run:  python ui.py   then open http://localhost:8001"""
import io
import json
import os
import pathlib
import threading
import webbrowser
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

from scrape import crawl, site_sections, to_docx

PORT = 8001  # v1 uses 8000, so both can run at once
KEY_FILE = pathlib.Path(__file__).parent / ".api_key"  # gitignored; only readable on this computer
job = {"running": False, "log": [], "files": {}, "error": None, "summary": None}


def saved_key():
    return os.environ.get("ANTHROPIC_API_KEY") or (KEY_FILE.read_text().strip() if KEY_FILE.exists() else "")


PAGE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Content Scraper v2</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  body { font: 16px/1.5 system-ui, sans-serif; max-width: 760px; margin: 40px auto; padding: 0 16px; color: #222; }
  h1 { font-size: 1.6rem; margin-bottom: 4px; }
  p.hint { color: #666; margin-top: 0; font-size: .9rem; }
  form { display: flex; gap: 12px; flex-wrap: wrap; align-items: end; margin: 24px 0; }
  label { display: flex; flex-direction: column; font-size: .9rem; color: #444; gap: 4px; }
  label.wide { flex: 1 1 100%; }
  label.url { flex: 1; min-width: 260px; }
  label.check { flex-direction: row; align-items: center; gap: 8px; }
  input, textarea { font: inherit; padding: 8px 10px; border: 1px solid #bbb; border-radius: 6px; }
  textarea { min-height: 90px; resize: vertical; }
  input[type=number] { width: 90px; }
  button, a.download { font: inherit; padding: 9px 18px; border: 0; border-radius: 6px; background: #1a73e8; color: #fff; cursor: pointer; text-decoration: none; display: inline-block; }
  button:disabled { background: #9bb8e8; cursor: wait; }
  a.download.secondary { background: #e8eef9; color: #1a4fa0; }
  #status { font-weight: 600; margin: 16px 0 8px; }
  #log { background: #f5f5f5; border-radius: 6px; padding: 12px; height: 280px; overflow-y: auto; font: 13px/1.4 ui-monospace, monospace; white-space: pre-wrap; }
  #log:empty { display: none; }
  [hidden] { display: none !important; }
  #done { margin-top: 16px; display: flex; gap: 8px; flex-wrap: wrap; }
</style></head>
<body>
<h1>Content Scraper v2</h1>
<p class="hint">Scrapes every page of a website, then Claude writes a brand profile, plans the new site, and rewrites each page for tone, brand and SEO. Results open in Google Docs.</p>
<form id="f">
  <label class="url">Website URL<input id="url" type="text" required placeholder="https://example.com"></label>
  <label>Max pages<input id="max" type="number" value="200" min="1" max="5000"></label>
  <label class="wide">Notes about the new site (optional)
    <textarea id="notes" placeholder="e.g. New name, target audience, tone you want (warm, premium, playful…), things to stress or avoid."></textarea></label>
  <label class="wide" id="keyrow">Anthropic API key <span class="hint" id="keyhint">Get one at console.anthropic.com. It's saved on this computer only.</span>
    <input id="key" type="password" autocomplete="off" placeholder="sk-ant-…"></label>
  <label class="check"><input id="improve" type="checkbox" checked> Improve with Claude (uses your API credit)</label>
  <button id="go">Start</button>
</form>
<div id="status" role="status" aria-live="polite"></div>
<div id="log"></div>
<div id="done" hidden>
  <a class="download" id="dl-improved" href="/download/improved" hidden>Download improved content</a>
  <a class="download secondary" id="dl-original" href="/download/original" hidden>Download original content</a>
</div>
<p class="hint" id="gdocs" hidden>To open in Google Docs: upload the file to Google Drive, right-click it, then choose Open with &rarr; Google Docs.</p>
<script>
const $ = id => document.getElementById(id);
$("f").onsubmit = async e => {
  e.preventDefault();
  $("go").disabled = true; $("done").hidden = $("gdocs").hidden = true; $("log").textContent = "";
  $("status").textContent = "Starting…";
  const body = {url: $("url").value, max: +$("max").value, notes: $("notes").value, key: $("key").value, improve: $("improve").checked};
  const r = await fetch("/start", {method: "POST", body: JSON.stringify(body)});
  if (!r.ok && r.status !== 409) { $("status").textContent = await r.text(); $("go").disabled = false; return; }
  $("key").value = "";
  poll();  // on 409 this shows the job that is already running
};
fetch("/status").then(r => r.json()).then(s => {
  if (s.has_key) { $("keyhint").textContent = "A key is saved. Leave blank to keep using it."; $("key").placeholder = "saved"; }
  if (s.running) { $("go").disabled = true; poll(); }  // resume after a page refresh
});
async function poll() {
  const s = await (await fetch("/status")).json();
  const log = $("log"), atBottom = log.scrollHeight - log.scrollTop - log.clientHeight < 20;
  log.textContent = s.log.join("\\n");
  if (atBottom) log.scrollTop = log.scrollHeight;
  if (s.running) { $("status").textContent = "Working… " + (s.log[s.log.length - 1] || "").trim(); return setTimeout(poll, 1500); }
  $("go").disabled = false;
  $("status").textContent = s.error ? "Error: " + s.error : s.summary;
  for (const kind of ["improved", "original"]) $("dl-" + kind).hidden = !s.files.includes(kind);
  $("done").hidden = $("gdocs").hidden = !s.files.length;
}
</script>
</body></html>"""


def docx_bytes(title, sections, intro):
    buf = io.BytesIO()
    to_docx(title, sections, buf, intro)  # zipfile accepts a file object, so nothing is written to disk
    return buf.getvalue()


def run_job(url, max_pages, notes, key, improve):
    log = job["log"].append
    try:
        host, pages = crawl(url, max_pages, 0.5, log=log)
        if not pages:
            job["summary"] = "Done, but no pages could be read from that site."
            return
        sections = site_sections(pages)
        name = host.replace(":", "_")
        job["files"]["original"] = (f"{name}-original.docx", docx_bytes(host, sections, f"{len(pages)} pages, as scraped"))
        job["summary"] = f"Done: {len(pages)} pages scraped."
        if not improve:
            return
        try:
            from improve import Improver
        except ImportError:
            raise RuntimeError("The 'anthropic' package is missing. Run: python -m pip install anthropic")
        imp = Improver(key, log=log)
        try:
            improved = imp.run(sections, notes)
        finally:
            log(f"Approximate Claude cost: ${imp.cost():.2f}")
        job["files"]["improved"] = (f"{name}-improved.docx",
                                    docx_bytes(f"{host}: improved content", improved, f"{len(pages)} pages, rewritten by Claude"))
        failed = sum(1 for _, _, b in improved[2:] if b and b[0].startswith("[Not improved"))
        job["summary"] = f"Done: {len(pages)} pages scraped and improved" + (f" ({failed} failed, see log)." if failed else ".")
    except Exception as e:
        job["error"] = str(e)
    finally:
        job["running"] = False


class Handler(BaseHTTPRequestHandler):
    def send(self, code, body, ctype="text/plain; charset=utf-8", extra=()):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        for k, v in extra:
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body if isinstance(body, bytes) else body.encode())

    def do_GET(self):
        if self.path == "/":
            self.send(200, PAGE, "text/html; charset=utf-8")
        elif self.path == "/status":
            status = {k: job[k] for k in ("running", "log", "error", "summary")}
            status.update(files=list(job["files"]), has_key=bool(saved_key()))
            self.send(200, json.dumps(status), "application/json")
        elif self.path.startswith("/download/") and self.path[10:] in job["files"]:
            name, data = job["files"][self.path[10:]]
            self.send(200, data, "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                      [("Content-Disposition", f'attachment; filename="{name}"')])
        else:
            self.send(404, "Not found")

    def do_POST(self):
        if self.path != "/start":
            return self.send(404, "Not found")
        if job["running"]:
            return self.send(409, "A job is already running. Wait for it to finish.")
        try:
            data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            url, max_pages = data["url"].strip(), max(1, min(int(data.get("max", 200)), 5000))
            notes, key, improve = str(data.get("notes", ""))[:20000], str(data.get("key", "")).strip(), bool(data.get("improve", True))
        except (ValueError, KeyError, TypeError):
            return self.send(400, "Bad request.")
        if "://" not in url:
            url = "https://" + url
        if urlparse(url).scheme not in ("http", "https") or not urlparse(url).netloc:
            return self.send(400, "That doesn't look like a website address.")
        if key:
            KEY_FILE.write_text(key)
        key = key or saved_key()
        if improve and not key:
            return self.send(400, "Add your Anthropic API key, or untick 'Improve with Claude'.")
        job.update(running=True, log=[], files={}, error=None, summary=None)
        threading.Thread(target=run_job, args=(url, max_pages, notes, key, improve), daemon=True).start()
        self.send(200, "started")

    def log_message(self, *args):
        pass  # keep the terminal quiet; progress shows in the browser


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)  # localhost only: not reachable from other machines
    print(f"Content Scraper v2 running at http://localhost:{PORT}  (close this window to stop)")
    webbrowser.open(f"http://localhost:{PORT}")
    server.serve_forever()
