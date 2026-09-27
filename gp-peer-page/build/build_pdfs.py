#!/usr/bin/env python3
"""Build the Governance Paradox peer document PDFs.

Renders the artifact page (page.html, or ../index.html in the repo) with the
text in pdf-content.json, using headless Chrome or Edge. Writes two 16:9 PDFs,
one frame per page:

    GP_Peer_Document_print.pdf   light palette, for printing
    GP_Peer_Document_screen.pdf  dark palette, as on screen

Python 3.8+ standard library only. Needs Chrome, Edge or Chromium installed.

    python build_pdfs.py                     # writes the PDFs into the folder above this kit
    python build_pdfs.py --out "C:\\path\\to\\folder"
    python build_pdfs.py --chrome "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
"""
import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
EXPECTED_PAGES = 12
PAGE_W_PT, PAGE_H_PT = 960, 540  # 13.333 x 7.5 in

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
]
CHROME_NAMES = ["chrome", "google-chrome", "chromium", "chromium-browser", "msedge"]


def find_file(*names):
    for n in names:
        p = (HERE / n).resolve()
        if p.is_file():
            return p
    sys.exit("Missing file: looked for " + ", ".join(names))


def find_chrome(explicit):
    if explicit:
        if pathlib.Path(explicit).is_file():
            return explicit
        sys.exit("Chrome not found at " + explicit)
    local = os.environ.get("LOCALAPPDATA")
    extra = [os.path.join(local, r"Google\Chrome\Application\chrome.exe")] if local else []
    for c in extra + CHROME_CANDIDATES:
        if os.path.isfile(c):
            return c
    for n in CHROME_NAMES:
        w = shutil.which(n)
        if w:
            return w
    sys.exit("No Chrome, Edge or Chromium found. Pass its path with --chrome.")


FONTS_URL = ("https://fonts.googleapis.com/css2?family=Libre+Caslon+Display"
             "&family=Libre+Caslon+Text:ital,wght@0,400;0,700;1,400&family=Sora:wght@300;400;600&display=swap")


def ensure_fonts():
    """Download the page's fonts into ./fonts once, so Chrome never prints before they load."""
    import re
    import urllib.request
    d = HERE / "fonts"
    if (d / "fonts.css").is_file():
        return
    ua = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}
    try:
        css = urllib.request.urlopen(urllib.request.Request(FONTS_URL, headers=ua), timeout=30).read().decode()
        d.mkdir(exist_ok=True)
        keep = []
        for sub, block in re.findall(r"/\* (\S+) \*/\s*(@font-face \{.*?\})", css, re.S):
            if sub != "latin":
                continue
            url = re.search(r"url\((.*?)\)", block).group(1)
            name = url.rsplit("/", 1)[-1]
            if not (d / name).is_file():
                (d / name).write_bytes(urllib.request.urlopen(url, timeout=30).read())
            keep.append(block.replace(url, name))
        (d / "fonts.css").write_text("\n".join(keep), encoding="utf-8")
        print("fonts:   downloaded to", d)
    except Exception as e:  # the font check after rendering will flag the result
        print("fonts:   download failed (" + str(e) + "); relying on the page's own font link")


def font_css():
    """Local fonts if the kit carries them, else the Google Fonts link the page already has."""
    d = HERE / "fonts"
    css = d / "fonts.css"
    if not css.is_file():
        return ""
    text = css.read_text(encoding="utf-8")
    return "<style>" + text.replace("url(", "url(" + d.as_uri() + "/") + "</style>"


def build_html(page, content, light):
    """Wrap the page the way the artifact host does, and feed it the text directly."""
    body = page.read_text(encoding="utf-8")
    # Chrome's command-line printer lays out at 8.5 in wide before applying the 16:9 @page size,
    # which would trigger the phone layout. Keep the narrow rules on screen only.
    for q in ("@media (max-width:820px){", "@media (max-width:520px){"):
        if q not in body:
            sys.exit("Page layout changed: '" + q + "' not found. Update build_pdfs.py.")
        body = body.replace(q, q.replace("@media (", "@media screen and ("))
    data = json.dumps(content, ensure_ascii=False).replace("</", "<\\/")
    feed = (
        "<script>(function(){var C=" + data + ";var f=window.fetch;"
        "window.fetch=function(u,o){return String(u).indexOf('content.json')>-1"
        "?Promise.resolve(new Response(JSON.stringify(C))):f(u,o)};"
        + ("document.documentElement.classList.add('light');" if light else "")
        + "})();</script>"
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        + font_css()
        + "</head><body>"
        + feed
        + body
        + "</body></html>"
    )


def render(chrome, html, out_pdf, tmp):
    src = pathlib.Path(tmp) / ("render_" + out_pdf.stem + ".html")
    src.write_text(html, encoding="utf-8")
    cmd = [
        chrome,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--hide-scrollbars",
        "--no-pdf-header-footer",
        "--run-all-compositor-stages-before-draw",
        "--virtual-time-budget=20000",
        "--window-size=1280,720",
        "--user-data-dir=" + str(pathlib.Path(tmp) / "profile"),
        "--print-to-pdf=" + str(out_pdf),
        src.as_uri(),
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if not out_pdf.is_file() or out_pdf.stat().st_size == 0:
        sys.exit("Chrome did not write " + out_pdf.name + "\n" + r.stderr[-2000:])


def fonts_ok(pdf):
    """The design fonts must be embedded. If Chrome printed before they loaded, it used fallback fonts."""
    raw = pdf.read_bytes()
    missing = [f for f in ("LibreCaslonDisplay", "LibreCaslonText") if f.encode() not in raw]
    return "" if not missing else "fonts not embedded: " + ", ".join(missing)


def check(pdf, content):
    """Fonts, page count, page size and two text probes. Page and text checks need pypdf or PyMuPDF."""
    f = fonts_ok(pdf)
    if f:
        return "CHECK: " + f
    try:
        import pymupdf as fitz  # noqa
    except ImportError:
        try:
            import fitz  # noqa
        except ImportError:
            fitz = None
    if fitz is not None:
        d = fitz.open(str(pdf))
        pages = len(d)
        size = (round(d[0].rect.width), round(d[0].rect.height))
        text = " ".join(" ".join(p.get_text().split()) for p in d)
    else:
        try:
            from pypdf import PdfReader
        except ImportError:
            return "fonts OK; pages and text not checked (pip install pypdf to check them)"
        rd = PdfReader(str(pdf))
        pages = len(rd.pages)
        box = rd.pages[0].mediabox
        size = (round(float(box.width)), round(float(box.height)))
        text = " ".join(" ".join((p.extract_text() or "").split()) for p in rd.pages)
    problems = []
    if pages != EXPECTED_PAGES:
        problems.append(f"{pages} pages, expected {EXPECTED_PAGES}")
    if abs(size[0] - PAGE_W_PT) > 2 or abs(size[1] - PAGE_H_PT) > 2:
        problems.append(f"page size {size[0]}x{size[1]} pt, expected {PAGE_W_PT}x{PAGE_H_PT}")
    for probe in (content.get("phone", ""), content["problemQuote"][-1][:40]):
        if probe and " ".join(probe.split()) not in text:
            problems.append("text missing: " + probe)
    return "OK" if not problems else "CHECK: " + "; ".join(problems)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--content", help="text file (default: pdf-content.json in this folder)")
    ap.add_argument("--page", help="page file (default: page.html here, else ../index.html)")
    ap.add_argument("--out", help="output folder (default: the folder above this kit)")
    ap.add_argument("--chrome", help="path to chrome.exe or msedge.exe")
    a = ap.parse_args()

    content_path = pathlib.Path(a.content) if a.content else find_file("pdf-content.json")
    page_path = pathlib.Path(a.page) if a.page else find_file("page.html", "../index.html")
    out = pathlib.Path(a.out) if a.out else HERE.parent
    out.mkdir(parents=True, exist_ok=True)
    content = json.loads(content_path.read_text(encoding="utf-8"))
    chrome = find_chrome(a.chrome)
    ensure_fonts()

    print("page:   ", page_path)
    print("text:   ", content_path)
    print("browser:", chrome)
    with tempfile.TemporaryDirectory() as tmp:
        for light, name in ((True, "GP_Peer_Document_print.pdf"), (False, "GP_Peer_Document_screen.pdf")):
            pdf = out / name
            render(chrome, build_html(page_path, content, light), pdf, tmp)
            print(f"{name}: {pdf.stat().st_size // 1024} KB, {check(pdf, content)}")
    print("written to", out)


if __name__ == "__main__":
    main()
