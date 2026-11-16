"""Make one small share page per photo: p/<slug>/index.html.

Shared on WhatsApp, Instagram, Facebook etc., the link
https://fadingathens.com/p/<slug>/ shows that photo with its sign name and
caption as the preview. Opened in a browser, the page goes straight to the
photo on the main site (index.html#photo/<slug>).

Reads the PHOTOS and CLOSED arrays from index.html, so it stays in sync
automatically. Also rewrites sitemap.xml with the home page plus every
photo page. Run from the repo root: python3 scripts/make_photo_pages.py
(the photo-pages workflow runs it on every push that changes index.html).
"""
import datetime
import html
import json
import os
import re
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://fadingathens.com"


def js_array(src, name, single_quotes=False):
    a = src.index("var %s=" % name) + len("var %s=" % name)
    b = src.index("];", a) + 1
    text = src[a:b]
    return json.loads(text.replace("'", '"') if single_quotes else text)


def image_size(p):
    w = p[1]
    if p[0] == "hotel-erechthion":
        return w, 1324
    if p[0] == "arcade-descent":
        return w, 1800
    return (w, round(w * 1346 / 2400)) if w > 1400 else (w, 1400)


PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{desc}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="Fading Athens">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{img}">
<meta property="og:image:width" content="{w}">
<meta property="og:image:height" content="{h}">
<meta property="og:image:alt" content="{alt}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{title}">
<meta name="twitter:description" content="{desc}">
<meta name="twitter:image" content="{img}">
<meta http-equiv="refresh" content="0; url={target}">
<link rel="icon" href="/img/apple-touch-icon.png">
<style>body{{margin:0;background:#f3ead2;color:#1c1a14;font:16px/1.5 Georgia,serif;text-align:center;padding:24px}}img{{max-width:100%;max-height:80vh;height:auto}}a{{color:#a8341f}}</style>
<script>location.replace({target_js});</script>
</head>
<body>
<p><a href="{target}">Fading Athens</a></p>
<img src="/img/{slug}.jpg" width="{w}" height="{h}" alt="{alt}">
<p>{label}{desc}</p>
<p><a href="{target}">See it on fadingathens.com →</a></p>
</body>
</html>
"""


def main():
    src = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    photos = js_array(src, "PHOTOS")
    closed = set(js_array(src, "CLOSED", single_quotes=True)) if "var CLOSED=" in src else set()
    out_dir = os.path.join(ROOT, "p")
    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)
    for p in photos:
        slug, sign, cap, alt = p[0], p[2], p[3], p[4]
        place = p[6] if len(p) > 6 else ""
        name = sign or (place and "Athens · " + place) or "Fading Athens"
        title = "%s · Fading Athens" % name
        desc = cap + (" Now closed." if slug in closed else "")
        w, h = image_size(p)
        target = "/#photo/" + slug
        page = PAGE.format(
            title=html.escape(title), desc=html.escape(desc), alt=html.escape(alt),
            url="%s/p/%s/" % (SITE, slug), img="%s/img/%s.jpg" % (SITE, slug),
            w=w, h=h, target=target, target_js=json.dumps(target), slug=slug,
            label=("<strong>%s</strong> · " % html.escape(sign)) if sign else "")
        os.makedirs(os.path.join(out_dir, slug), exist_ok=True)
        open(os.path.join(out_dir, slug, "index.html"), "w", encoding="utf-8").write(page)
    # sitemap: keep the home page's lastmod, add every photo page
    sm = os.path.join(ROOT, "sitemap.xml")
    m = re.search(r"<lastmod>([\d-]+)</lastmod>", open(sm).read()) if os.path.exists(sm) else None
    home = m.group(1) if m else datetime.date.today().isoformat()
    urls = ["  <url>\n    <loc>%s/</loc>\n    <lastmod>%s</lastmod>\n  </url>" % (SITE, home)]
    urls += ["  <url>\n    <loc>%s/p/%s/</loc>\n  </url>" % (SITE, p[0]) for p in photos]
    open(sm, "w").write('<?xml version="1.0" encoding="UTF-8"?>\n'
                        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                        + "\n".join(urls) + "\n</urlset>\n")
    print("Made %d photo pages." % len(photos))


if __name__ == "__main__":
    main()
