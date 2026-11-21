#!/usr/bin/env python3
"""Local helper for Image Hash Lab: serves index.html, saves scan results into
the csv/ folder (as .csv and .xlsx) and opens the CSV automatically."""
import csv, datetime, json, os, subprocess, sys, threading, webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BASE = Path(__file__).resolve().parent
CSV_DIR = BASE / "csv"
FIELDS = ["image_a", "image_b", "distance", "similarity_pct", "status"]


def open_file(path):
    if os.environ.get("NO_OPEN"):
        return
    if sys.platform.startswith("win"):
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


def save_results(rows, algo, threshold):
    CSV_DIR.mkdir(exist_ok=True)
    name = f"scan_{algo}_th{threshold}_{datetime.datetime.now():%Y%m%d_%H%M%S}"
    csv_path = CSV_DIR / f"{name}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    xlsx_path = None
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font
        wb = Workbook()
        ws = wb.active
        ws.title = "Duplicates"
        ws.append(FIELDS)
        for c in ws[1]:
            c.font = Font(bold=True)
        for r in rows:
            ws.append([r[k] for k in FIELDS])
        for col, width in zip("ABCDE", (34, 34, 10, 16, 12)):
            ws.column_dimensions[col].width = width
        xlsx_path = CSV_DIR / f"{name}.xlsx"
        wb.save(xlsx_path)
    except ImportError:
        pass
    open_file(csv_path)
    return csv_path, xlsx_path


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, (BASE / "web" / "index.html").read_bytes(), "text/html; charset=utf-8")
        else:
            self._send(404, b"{}")

    def do_POST(self):
        if self.path != "/save":
            return self._send(404, b"{}")
        try:
            data = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            c, x = save_results(data["rows"], data["algo"], data["threshold"])
            out = {"csv": str(c), "xlsx": str(x) if x else None}
            self._send(200, json.dumps(out).encode())
        except Exception as e:
            self._send(500, json.dumps({"error": str(e)}).encode())

    def log_message(self, *a):
        pass


def main():
    for port in range(8000, 8011):
        try:
            srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
            break
        except OSError:
            continue
    else:
        sys.exit("No free port between 8000 and 8010.")
    url = f"http://127.0.0.1:{port}/"
    print(f"Image Hash Lab running at {url}\nResults are saved in: {CSV_DIR}\nPress Ctrl+C to stop.")
    if not os.environ.get("NO_OPEN"):
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
