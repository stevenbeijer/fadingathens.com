"""Copy new photos from Steven's iCloud Shared Album into inbox/.

The album must be shared with a public link. Both kinds of link work:
- current albums: https://photos.icloud.com/shared/album/<key>/ (CloudKit)
- older albums:   https://www.icloud.com/sharedalbum/#<token> (sharedstreams)
The link is read from the ALBUM_URL environment variable (a GitHub
Actions secret, so the link stays private).

Each new photo is saved as inbox/<guid>.jpg with all metadata (including
GPS) removed, plus inbox/<guid>.json with the caption typed in the album,
if any. Photos already fetched are remembered in data/album-seen.json, so
a photo is only fetched once even after it leaves the inbox.

Claude's daily scheduled task then checks the inbox, picks a series,
writes the caption and moves each photo onto the website.
"""
import base64
import io
import json
import os
import sys
import urllib.error
import urllib.parse
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
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST", headers=HEADERS)
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


HEADERS = {"Content-Type": "text/plain", "Origin": "https://www.icloud.com",
           "User-Agent": "Mozilla/5.0 (fadingathens.com album sync)"}

# ---------- current albums: CloudKit (photos.icloud.com/shared/album/<key>) ----------
CK_RESOLVE = ("https://p01-ckdatabasews.icloud.com/database/1/"
              "com.apple.photos.cloud/production/public/records/resolve")
CK_DB = "/database/1/com.apple.photos.cloud/production/shared/"


def ck_post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST", headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def ck_val(rec, field):
    e = ((rec or {}).get("fields") or {}).get(field)
    return e.get("value") if isinstance(e, dict) else None


def ck_caption(asset):
    """Caption Steven typed on the photo, if Apple exposes it."""
    for f in ("captionEnc", "caption", "titleEnc", "title"):
        v = ck_val(asset, f)
        if not v:
            continue
        if f.endswith("Enc"):
            try:
                raw = base64.b64decode(v)
                if raw.startswith(b"bplist"):
                    import plistlib
                    obj = plistlib.loads(raw)
                    v = obj if isinstance(obj, str) else str(obj)
                else:
                    v = raw.decode("utf-8", "replace")
            except Exception:
                continue
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def cloudkit_photos(key):
    res = ck_post(CK_RESOLVE, {"shortGUIDs": [{"value": key, "shouldFetchRootRecord": True}]})
    item = (res.get("results") or [{}])[0]
    if item.get("serverErrorCode"):
        raise SystemExit("iCloud refused the album link: %s" % item["serverErrorCode"])
    acc = item.get("anonymousPublicAccess") or {}
    if not acc.get("token"):
        raise SystemExit("The album isn't public. Turn on its public link in Photos.")
    part = str(acc.get("databasePartition") or "https://p01-ckdatabasews.icloud.com:443").rstrip("/")
    title = (((item.get("share") or {}).get("fields") or {}).get("cloudkit.title") or {}).get("value") or ""
    q = urllib.parse.urlencode({"publicAccessAuthToken": acc["token"], "sharing_url_key": key})
    body = {"query": {"recordType": "CPLAssetAndMasterByAssetDateWithoutHiddenOrDeleted",
                      "filterBy": [{"fieldName": "direction", "comparator": "EQUALS",
                                    "fieldValue": {"value": "ASCENDING", "type": "STRING"}}]},
            "resultsLimit": 200, "zoneID": item["zoneID"]}
    records = []
    for _ in range(50):
        page = ck_post("%s%srecords/query?%s" % (part, CK_DB, q), body)
        records += page.get("records") or []
        if not page.get("continuationMarker"):
            break
        body["continuationMarker"] = page["continuationMarker"]
    masters = {r.get("recordName"): r for r in records if r.get("recordType") == "CPLMaster"}
    assets = [r for r in records if r.get("recordType") == "CPLAsset"]
    if assets:  # field names only, to help debugging captions; no values
        print("CPLAsset fields:", sorted((assets[0].get("fields") or {}).keys()))
    out = []
    for a in assets:
        m = masters.get((ck_val(a, "masterRef") or {}).get("recordName"))
        if not m:
            continue
        kind = str(ck_val(m, "itemType") or "").lower()
        if "movie" in kind or "video" in kind or "mpeg" in kind:
            continue
        url = None
        best = 0
        for rec in (a, m):
            for pre in ("resJPEGFull", "resJPEGMed"):
                r = ck_val(rec, pre + "Res")
                ft = ck_val(rec, pre + "FileType")
                if not isinstance(r, dict) or not r.get("downloadURL"):
                    continue
                if ft not in (None, "public.jpeg", "public.png"):
                    continue
                size = int(ck_val(rec, pre + "Width") or 0) * int(ck_val(rec, pre + "Height") or 0)
                if size > best:
                    best, url = size, r["downloadURL"].replace("${f}", "photo.jpg")
        if url:
            date = ck_val(a, "assetDate")
            out.append({"guid": a["recordName"], "url": url, "caption": ck_caption(a),
                        "dateCreated": date})
    return title, out


# ---------- older albums: sharedstreams (www.icloud.com/sharedalbum/#<token>) ----------
def legacy_photos(token):
    host = "p%02d-sharedstreams.icloud.com" % partition(token)
    host, stream = post(host, token, "webstream", {"streamCtag": None})
    photos = [p for p in stream.get("photos", [])
              if p.get("mediaAssetType", "").lower() != "video"]
    best = {}
    for p in photos:
        ders = list(p.get("derivatives", {}).values())
        if ders:
            d = max(ders, key=lambda d: int(d.get("width", 0)) * int(d.get("height", 0)))
            best[p["photoGuid"]] = (p, d["checksum"])
    out = []
    if best:
        host, urls = post(host, token, "webasseturls", {"photoGuids": list(best)})
        items = urls.get("items", {})
        for guid, (p, ck) in best.items():
            it = items.get(ck)
            if it:
                out.append({"guid": guid, "url": "https://%s%s" % (it["url_location"], it["url_path"]),
                            "caption": (p.get("caption") or "").strip(), "dateCreated": p.get("dateCreated")})
    return stream.get("streamName"), out


def main():
    url = os.environ.get("ALBUM_URL", "").strip()
    if not url:
        print("ALBUM_URL is not set; nothing to do.")
        return 0
    if "photos.icloud.com/shared/album/" in url or "share.icloud.com/photos/" in url:
        key = url.split("?")[0].rstrip("/").split("/")[-1]
        name, photos = cloudkit_photos(key)
    else:
        name, photos = legacy_photos(token_from(url))
    seen = json.load(open(SEEN)) if os.path.exists(SEEN) else []
    new = [p for p in photos if p["guid"] not in seen]
    print("Album %r: %d photos, %d new." % (name, len(photos), len(new)))
    if not new:
        return 0
    os.makedirs(INBOX, exist_ok=True)
    for p in new:
        raw = urllib.request.urlopen(p["url"], timeout=120).read()
        im = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))).convert("RGB")
        im.save(os.path.join(INBOX, p["guid"] + ".jpg"), quality=92)  # saved without EXIF/GPS
        meta = {"guid": p["guid"], "caption": p["caption"], "dateCreated": p["dateCreated"],
                "album": name, "size": list(im.size)}
        json.dump(meta, open(os.path.join(INBOX, p["guid"] + ".json"), "w"), ensure_ascii=False, indent=1)
        seen.append(p["guid"])
        print("Saved", p["guid"], im.size, "caption:", bool(p["caption"]))
    json.dump(seen, open(SEEN, "w"), indent=0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
