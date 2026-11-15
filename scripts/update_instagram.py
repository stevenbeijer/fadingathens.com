#!/usr/bin/env python3
"""Refresh the "On Instagram" grid on fadingathens.com.

Fetches the latest @fadingathens posts from the Behold JSON feed,
saves the images into img/ig/, and rewrites the grid in index.html
between the IG:START / IG:END markers. Old images are removed.

Run by .github/workflows/instagram.yml once a day. Can also be run by hand:
    python3 scripts/update_instagram.py
"""
import html
import json
import os
import re
import sys
import urllib.request
from io import BytesIO
from datetime import datetime

FEED_URL = os.environ.get("BEHOLD_FEED_URL", "https://feeds.behold.so/CmqoCA1Y8TwNuQvf8MLW")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, "index.html")
IG_DIR = os.path.join(ROOT, "img", "ig")
START, END = "<!-- IG:START -->", "<!-- IG:END -->"
UA = {"User-Agent": "fadingathens.com instagram updater"}
EXT = {"image/webp": "webp", "image/jpeg": "jpg", "image/png": "png", "image/avif": "avif"}


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read(), r.headers.get_content_type()


def trim_white_frame(data):
    """Many posts have a white frame baked in; crop it off so tiles fill edge to edge."""
    try:
        from PIL import Image, ImageChops
    except ImportError:
        return data, None
    im = Image.open(BytesIO(data)).convert("RGB")
    bg = Image.new("RGB", im.size, (255, 255, 255))
    # pixels that differ clearly from white
    diff = ImageChops.difference(im, bg).convert("L").point(lambda v: 255 if v > 22 else 0)
    box = diff.getbbox()
    if box:
        w, h = im.size
        l, t, r, b = box
        # only crop a real frame (at least 2% on some side), keep a hair of margin inside
        if max(l, t, w - r, h - b) > 0.02 * min(w, h):
            pad = 2
            im = im.crop((min(l + pad, w), min(t + pad, h), max(r - pad, 0), max(b - pad, 0)))
    out = BytesIO()
    im.save(out, "JPEG", quality=86, optimize=True, progressive=True)
    return out.getvalue(), im.size


def alt_text(post):
    cap = (post.get("prunedCaption") or post.get("caption") or "").strip()
    cap = re.sub(r"\s+", " ", cap)
    # keep it short: first sentence, max ~110 characters
    cap = re.split(r"(?<=[.!?])\s", cap)[0]
    if len(cap) > 110:
        cap = cap[:107].rsplit(" ", 1)[0] + "…"
    if len(re.sub(r"[\W_]", "", cap)) < 4:  # only emoji / nothing useful
        cap = ""
    if cap:
        return cap
    try:
        d = datetime.strptime(post["timestamp"][:10], "%Y-%m-%d")
        return f"Fading Athens Instagram post from {d.day} {d:%B %Y}"
    except Exception:
        return "Fading Athens Instagram post"


def main():
    raw, _ = get(FEED_URL)
    feed = json.loads(raw)
    posts = [p for p in feed.get("posts", []) if p.get("visibility", "visible") == "visible"][:9]
    if not posts:
        print("Feed returned no posts; leaving the page as it is.")
        return 0

    os.makedirs(IG_DIR, exist_ok=True)
    keep, tiles = set(), []
    for p in posts:
        sizes = p.get("sizes") or {}
        size = sizes.get("medium") or sizes.get("large") or sizes.get("small") or {}
        url = size.get("mediaUrl") or p.get("thumbnailUrl") or p.get("mediaUrl")
        if not url:
            continue
        existing = [f for f in os.listdir(IG_DIR) if f.startswith(p["id"] + ".")]
        if existing:
            name = existing[0]
        else:
            data, ctype = get(url)
            data, dims = trim_white_frame(data)
            name = f'{p["id"]}.{"jpg" if dims else EXT.get(ctype, "jpg")}'
            with open(os.path.join(IG_DIR, name), "wb") as f:
                f.write(data)
        keep.add(name)
        try:
            from PIL import Image
            with Image.open(os.path.join(IG_DIR, name)) as im:
                size = {"width": im.width, "height": im.height}
        except Exception:
            pass
        alt = html.escape(alt_text(p), quote=True)
        link = html.escape(p.get("permalink") or "https://www.instagram.com/fadingathens/", quote=True)
        tiles.append(
            f'      <a href="{link}" target="_blank" rel="noopener" aria-label="{alt}, on Instagram">'
            f'<img src="img/ig/{name}" alt="{alt}" width="{size.get("width", 561)}" height="{size.get("height", 700)}" loading="lazy"></a>'
        )

    if not tiles:
        print("No usable images in feed; leaving the page as it is.")
        return 0

    page = open(INDEX, encoding="utf-8").read()
    a, b = page.find(START), page.find(END)
    if a < 0 or b < 0:
        print("IG markers not found in index.html", file=sys.stderr)
        return 1
    new = page[: a + len(START)] + "\n" + "\n".join(tiles) + "\n      " + page[b:]
    if new != page:
        open(INDEX, "w", encoding="utf-8").write(new)

    for f in os.listdir(IG_DIR):
        if f not in keep:
            os.remove(os.path.join(IG_DIR, f))
    print(f"Grid now shows {len(tiles)} posts.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
