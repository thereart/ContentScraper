"""Web UI for scrape.py. Run:  python ui.py   then open http://localhost:8000"""
import io
import json
import threading
import webbrowser
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

from scrape import crawl, to_docx

job = {"running": False, "log": [], "file": None, "name": None, "error": None}

PAGE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Content Scraper</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  body { font: 16px/1.5 system-ui, sans-serif; max-width: 720px; margin: 40px auto; padding: 0 16px; color: #222; }
  h1 { font-size: 1.6rem; margin-bottom: 4px; }
  p.hint { color: #666; margin-top: 0; }
  form { display: flex; gap: 8px; flex-wrap: wrap; align-items: end; margin: 24px 0; }
  label { display: flex; flex-direction: column; font-size: .9rem; color: #444; gap: 4px; }
  label.url { flex: 1; min-width: 260px; }
  input { font: inherit; padding: 8px 10px; border: 1px solid #bbb; border-radius: 6px; }
  input[type=number] { width: 90px; }
  button, a.download { font: inherit; padding: 9px 18px; border: 0; border-radius: 6px; background: #1a73e8; color: #fff; cursor: pointer; text-decoration: none; display: inline-block; }
  button:disabled { background: #9bb8e8; cursor: wait; }
  #status { font-weight: 600; margin: 16px 0 8px; }
  #log { background: #f5f5f5; border-radius: 6px; padding: 12px; height: 280px; overflow-y: auto; font: 13px/1.4 ui-monospace, monospace; white-space: pre-wrap; }
  #log:empty { display: none; }
  #done[hidden] { display: none; }
  #done { margin-top: 16px; }
</style></head>
<body>
<h1>Content Scraper</h1>
<p class="hint">Paste a website address. Every page's text is saved into one document you can open in Google Docs.</p>
<form id="f">
  <label class="url">Website URL<input id="url" type="text" required placeholder="https://example.com"></label>
  <label>Max pages<input id="max" type="number" value="200" min="1" max="5000"></label>
  <button id="go">Scrape</button>
</form>
<div id="status" role="status" aria-live="polite"></div>
<div id="log"></div>
<div id="done" hidden>
  <a class="download" id="dl" href="/download">Download .docx</a>
  <p class="hint">To open in Google Docs: upload it to Google Drive, right-click it, then choose Open with &rarr; Google Docs.</p>
</div>
<script>
const $ = id => document.getElementById(id);
$("f").onsubmit = async e => {
  e.preventDefault();
  $("go").disabled = true; $("done").hidden = true; $("log").textContent = "";
  $("status").textContent = "Starting…";
  const r = await fetch("/start", {method: "POST", body: JSON.stringify({url: $("url").value, max: +$("max").value})});
  if (!r.ok && r.status !== 409) { $("status").textContent = await r.text(); $("go").disabled = false; return; }
  poll();  // on 409 this shows the scrape that is already running
};
fetch("/status").then(r => r.json()).then(s => { if (s.running) { $("go").disabled = true; poll(); } });  // resume after a page refresh
async function poll() {
  const s = await (await fetch("/status")).json();
  const log = $("log"), atBottom = log.scrollHeight - log.scrollTop - log.clientHeight < 20;
  log.textContent = s.log.join("\\n");
  if (atBottom) log.scrollTop = log.scrollHeight;
  if (s.running) { $("status").textContent = `Scraping… ${s.log.filter(l => l.startsWith("[")).length} pages so far`; return setTimeout(poll, 1000); }
  $("go").disabled = false;
  if (s.error) { $("status").textContent = "Error: " + s.error; return; }
  $("status").textContent = s.summary;
  if (s.name) { $("dl").textContent = "Download " + s.name; $("done").hidden = false; }
}
</script>
</body></html>"""


def run_job(url, max_pages):
    try:
        host, pages = crawl(url, max_pages, 0.5, log=job["log"].append)
        if pages:
            buf = io.BytesIO()
            to_docx(host, pages, buf)  # zipfile accepts a file object, so nothing is written to disk
            job["file"], job["name"] = buf.getvalue(), host.replace(":", "_") + ".docx"
        job["summary"] = f"Done: {len(pages)} pages saved." if pages else "Done, but no pages could be read from that site."
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
            self.send(200, json.dumps({k: job.get(k) for k in ("running", "log", "error", "summary", "name")}), "application/json")
        elif self.path == "/download" and job["file"]:
            self.send(200, job["file"], "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                      [("Content-Disposition", f'attachment; filename="{job["name"]}"')])
        else:
            self.send(404, "Not found")

    def do_POST(self):
        if self.path != "/start":
            return self.send(404, "Not found")
        if job["running"]:
            return self.send(409, "A scrape is already running — wait for it to finish.")
        try:
            data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            url, max_pages = data["url"].strip(), max(1, min(int(data.get("max", 200)), 5000))
        except (ValueError, KeyError, TypeError):
            return self.send(400, "Bad request.")
        if "://" not in url:
            url = "https://" + url
        if urlparse(url).scheme not in ("http", "https") or not urlparse(url).netloc:
            return self.send(400, "That doesn't look like a website address.")
        job.update(running=True, log=[], file=None, name=None, error=None, summary=None)
        threading.Thread(target=run_job, args=(url, max_pages), daemon=True).start()
        self.send(200, "started")

    def log_message(self, *args):
        pass  # keep the terminal quiet; progress shows in the browser


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8000), Handler)  # localhost only: not reachable from other machines
    print("Content Scraper running at http://localhost:8000  (Ctrl+C to stop)")
    webbrowser.open("http://localhost:8000")
    server.serve_forever()
