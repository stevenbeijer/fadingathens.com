"""Copy new photos from Steven's iCloud Shared Album into inbox/.

The album must have "Public Website" turned on. Its link
(https://www.icloud.com/sharedalbum/#B0xxxxxxxxxxxxx) is read from the
ALBUM_URL environment variable (a GitHub Actions secret, so the link
stays private).

Each new photo is saved as inbox/<guid>.jpg with all metadata (including
GPS) removed, plus inbox/<guid>.json with the caption typed in the album,
if any. Photos already fetched are remembered in data/album-seen.json, so
a photo is only fetched once even after it leaves the inbox.

Claude's daily scheduled task then checks the inbox, picks a series,
writes the caption and moves each photo onto the website.
"""
import io
import json
import os
import sys
import urllib.error
import urllib.request

from PIL import Image, ImageOps

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INBOX = os.path.join(ROOT, "inbox")
SEEN = os.path.join(ROOT, "data", "album-seen.json")
B62 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"


def token_from(url):
    t = url.strip().split("#")[-1].split(";")[0].strip("/")
    return t


def partition(token):
    def b62(s):
        n = 0
        for c in s:
            n = n * 62 + B62.index(c)
        return n
    return b62(token[1]) if token[0] == "A" else b62(token[1:3])


def post(host, token, path, body):
    url = "https://%s/%s/sharedstreams/%s" % (host, token, path)
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type": "text/plain", "Origin": "https://www.icloud.com",
                 "User-Agent": "Mozilla/5.0 (fadingathens.com album sync)"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return host, json.load(r)
    except urllib.error.HTTPError as e:
        if e.code == 330:  # album lives on another server; Apple says which
            data = json.load(e)
            new = data.get("X-Apple-MMe-Host") or e.headers.get("X-Apple-MMe-Host")
            if new and new != host:
                return post(new, token, path, body)
        raise


def main():
    url = os.environ.get("ALBUM_URL", "").strip()
    if not url:
        print("ALBUM_URL is not set; nothing to do.")
        return 0
    token = token_from(url)
    host = "p%02d-sharedstreams.icloud.com" % partition(token)
    host, stream = post(host, token, "webstream", {"streamCtag": None})
    photos = [p for p in stream.get("photos", [])
              if p.get("mediaAssetType", "").lower() != "video"]
    seen = json.load(open(SEEN)) if os.path.exists(SEEN) else []
    new = [p for p in photos if p["photoGuid"] not in seen]
    print("Album %r: %d photos, %d new." % (stream.get("streamName"), len(photos), len(new)))
    if not new:
        return 0
    # biggest version of each new photo
    best = {}
    for p in new:
        ders = list(p.get("derivatives", {}).values())
        if not ders:
            continue
        d = max(ders, key=lambda d: int(d.get("width", 0)) * int(d.get("height", 0)))
        best[p["photoGuid"]] = (p, d["checksum"])
    host, urls = post(host, token, "webasseturls", {"photoGuids": list(best)})
    items = urls.get("items", {})
    os.makedirs(INBOX, exist_ok=True)
    for guid, (p, checksum) in best.items():
        it = items.get(checksum)
        if not it:
            print("No download link for", guid)
            continue
        src = "https://%s%s" % (it["url_location"], it["url_path"])
        raw = urllib.request.urlopen(src, timeout=120).read()
        im = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGB")
        im.save(os.path.join(INBOX, guid + ".jpg"), quality=92)  # saved without EXIF/GPS
        meta = {"guid": guid, "caption": (p.get("caption") or "").strip(),
                "dateCreated": p.get("dateCreated"), "album": stream.get("streamName"),
                "size": list(im.size)}
        json.dump(meta, open(os.path.join(INBOX, guid + ".json"), "w"), ensure_ascii=False, indent=1)
        seen.append(guid)
        print("Saved", guid, im.size, meta["caption"])
    json.dump(seen, open(SEEN, "w"), indent=0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
