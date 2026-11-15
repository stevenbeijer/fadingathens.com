#!/usr/bin/env python3
"""Refresh the "On Instagram" section on fadingathens.com.

Fetches @fadingathens from the Behold JSON feed and rewrites, in index.html:
  - the post grid           (IG:START / IG:END)        images in img/ig/
    Behold's free plan gives 6 posts; earlier posts are remembered in
    data/instagram-posts.json so the grid fills up to 9.
  - the profile picture     (IG-AVATAR:START / END)    img/ig-avatar.jpg
  - follower counts         (IG-STATS:START / END)
  - the bio and website     (IG-BIO:START / END)
Old post images are removed.

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
ARCHIVE = os.path.join(ROOT, "data", "instagram-posts.json")  # posts remembered between runs
GRID_SIZE = 9
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


def replace_between(page, tag, content):
    a, b = page.find(f"<!-- {tag}:START -->"), page.find(f"<!-- {tag}:END -->")
    if a < 0 or b < 0:
        print(f"{tag} markers not found; skipped", file=sys.stderr)
        return page
    return page[: a + len(f"<!-- {tag}:START -->")] + content + page[b:]


def linkify_bio(text):
    out = []
    for part in re.split(r"(https?://\S+|@[A-Za-z0-9._]+|#\w+)", text):
        if not part:
            continue
        if part.startswith("http"):
            out.append(f'<a href="{html.escape(part, quote=True)}" target="_blank" rel="noopener">{html.escape(part)}</a>')
        elif part.startswith("@"):
            h = part[1:].rstrip(".")
            out.append(f'<a href="https://www.instagram.com/{html.escape(h, quote=True)}/" target="_blank" rel="noopener">@{html.escape(h)}</a>' + part[1 + len(h):])
        elif part.startswith("#"):
            out.append(f'<a href="https://www.instagram.com/explore/tags/{html.escape(part[1:], quote=True)}/" target="_blank" rel="noopener">{html.escape(part)}</a>')
        else:
            out.append(html.escape(part))
    return "".join(out).replace("\n", "<br>")


def short_url(url):
    s = re.sub(r"^https?://(www\.)?", "", url).rstrip("/")
    return s if len(s) <= 34 else s[:33] + "…"


def save_avatar(url):
    """Download the profile picture as a small square JPEG. Returns True if it changed."""
    path = os.path.join(ROOT, "img", "ig-avatar.jpg")
    data, _ = get(url)
    try:
        from PIL import Image
        im = Image.open(BytesIO(data)).convert("RGB")
        side = min(im.size)
        im = im.crop(((im.width - side) // 2, (im.height - side) // 2, (im.width + side) // 2, (im.height + side) // 2)).resize((168, 168), Image.LANCZOS)
        out = BytesIO()
        im.save(out, "JPEG", quality=88)
        data = out.getvalue()
    except Exception:
        pass
    if os.path.exists(path) and open(path, "rb").read() == data:
        return False
    with open(path, "wb") as f:
        f.write(data)
    return True


def update_profile(page, feed):
    user = feed.get("username") or "fadingathens"
    if feed.get("profilePictureUrl"):
        try:
            save_avatar(feed["profilePictureUrl"])
            page = replace_between(page, "IG-AVATAR", f'<img src="img/ig-avatar.jpg" alt="" width="168" height="168">')
        except Exception as e:
            print(f"avatar skipped: {e}", file=sys.stderr)
    fo, fg = feed.get("followersCount"), feed.get("followsCount")
    if fo is not None:
        stats = f"<strong>{fo:,}</strong> followers"
        if fg is not None:
            stats += f" · <strong>{fg:,}</strong> following"
        page = replace_between(page, "IG-STATS", stats)
    bio = (feed.get("biography") or "").strip()
    if bio:
        block = f"<p>{linkify_bio(bio)}</p>"
        web = (feed.get("website") or "").strip()
        if web:
            block += f'<p class="ig-web"><a href="{html.escape(web, quote=True)}" target="_blank" rel="noopener">{html.escape(short_url(web))}</a></p>'
        page = replace_between(page, "IG-BIO", block)
    return page


def main():
    raw, _ = get(FEED_URL)
    feed = json.loads(raw)
    posts = [p for p in feed.get("posts", []) if p.get("visibility", "visible") == "visible"]
    if not posts:
        print("Feed returned no posts; leaving the page as it is.")
        return 0

    os.makedirs(IG_DIR, exist_ok=True)

    # 1. turn the feed's posts into grid entries (downloading new images)
    fresh = {}
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
        w, h = size.get("width", 561), size.get("height", 700)
        try:
            from PIL import Image
            with Image.open(os.path.join(IG_DIR, name)) as im:
                w, h = im.width, im.height
        except Exception:
            pass
        fresh[p["id"]] = {
            "id": p["id"],
            "permalink": p.get("permalink") or "https://www.instagram.com/fadingathens/",
            "timestamp": p.get("timestamp", ""),
            "alt": alt_text(p),
            "image": name,
            "width": w,
            "height": h,
        }
    if not fresh:
        print("No usable images in feed; leaving the page as it is.")
        return 0

    # 2. merge with posts remembered from earlier runs, so the grid can show more
    #    than the feed's limit. Remembered posts newer than the oldest feed post but
    #    missing from the feed were deleted or archived on Instagram: drop them.
    try:
        archive = json.load(open(ARCHIVE, encoding="utf-8"))
    except Exception:
        archive = []
    oldest = min(e["timestamp"] for e in fresh.values())
    merged = dict(fresh)
    for e in archive:
        if e["id"] in merged:
            continue
        if e["timestamp"] >= oldest:
            continue  # inside the feed's window but not in it: gone from Instagram
        if not os.path.exists(os.path.join(IG_DIR, e["image"])):
            continue
        merged[e["id"]] = e
    shown = sorted(merged.values(), key=lambda e: e["timestamp"], reverse=True)[:GRID_SIZE]

    # show whole rows of three only (6 or 9), so the grid never has a gap
    rows = len(shown) // 3 * 3 or len(shown)
    tiles = []
    for e in shown[:rows]:
        alt = html.escape(e["alt"], quote=True)
        link = html.escape(e["permalink"], quote=True)
        tiles.append(
            f'      <a href="{link}" target="_blank" rel="noopener" aria-label="{alt}, on Instagram">'
            f'<img src="img/ig/{e["image"]}" alt="{alt}" width="{e["width"]}" height="{e["height"]}" loading="lazy"></a>'
        )

    page = open(INDEX, encoding="utf-8").read()
    a, b = page.find(START), page.find(END)
    if a < 0 or b < 0:
        print("IG markers not found in index.html", file=sys.stderr)
        return 1
    new = page[: a + len(START)] + "\n" + "\n".join(tiles) + "\n      " + page[b:]
    new = update_profile(new, feed)
    if new != page:
        open(INDEX, "w", encoding="utf-8").write(new)

    os.makedirs(os.path.dirname(ARCHIVE), exist_ok=True)
    with open(ARCHIVE, "w", encoding="utf-8") as f:
        json.dump(shown, f, ensure_ascii=False, indent=1)
        f.write("\n")

    keep = {e["image"] for e in shown}
    for f in os.listdir(IG_DIR):
        if f not in keep:
            os.remove(os.path.join(IG_DIR, f))
    print(f"Grid now shows {len(tiles)} posts ({len(fresh)} from the feed).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
