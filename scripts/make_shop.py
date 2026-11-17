"""Make the print shop page: shop/index.html.

Lists the prints in data/prints.json (Steven's selection, made from his
full-resolution files). Names and captions come from PHOTOS in index.html
for photos on the site, or from prints.json for new ones. "max" is the
biggest size the original file allows ("m" = 30x40, "l" = 50x70).

Checkout (16 Nov, evening): prints are sold through the Etsy shop FadingAthens.
Only prints with an "etsy" listing URL in data/prints.json appear in the shop,
and "Order on Etsy" opens that listing (the buyer picks the size on Etsy).
Gelato prints and ships Etsy orders automatically. shop/checkout.json holds the
old Shopify cart links and is no longer used. No Instagram ordering.

Run from the repo root: python3 scripts/make_shop.py
(the photo-pages workflow runs it on every push that changes index.html).
"""
import html
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://fadingathens.com"

# id, label (portrait orientation, cm), price in euros
SIZES = [("a4", "21 × 30 cm (A4)", 35), ("m", "30 × 40 cm", 55), ("l", "50 × 70 cm", 95)]
FRAMES = [("none", "Unframed", 0)]


def js_array(src, name, single_quotes=False):
    a = src.index("var %s=" % name) + len("var %s=" % name)
    b = src.index("];", a) + 1
    text = src[a:b]
    if single_quotes:
        text = re.sub(r"([{,])\s*(\w+):", r'\1"\2":', text.replace("'", '"'))
    return json.loads(text)


# Shop offline (Steven, 16 Nov) until the Etsy listings are live. While False,
# shop/index.html is a short "coming soon" page that sends visitors home.
SHOP_OPEN = True

CLOSED_PAGE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex">
<title>Prints · Fading Athens</title>
<meta http-equiv="refresh" content="4;url=../">
<style>body{margin:0;min-height:100vh;display:grid;place-items:center;background:#fbfaf6;color:#1f1d1a;font:17px/1.5 system-ui,sans-serif;text-align:center;padding:24px}a{color:#c8321f;font-weight:700}h1{font-size:28px;margin:0 0 8px}</style>
</head><body><div><h1>Prints are coming soon</h1><p>The Fading Athens print shop is being set up.<br><a href="../">Back to Fading Athens</a></p></div></body></html>
"""


def main():
    if not SHOP_OPEN:
        open(os.path.join(ROOT, "shop", "index.html"), "w", encoding="utf-8").write(CLOSED_PAGE)
        print("shop/index.html: offline page (SHOP_OPEN = True)")
        return

    src = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    photos = {p[0]: p for p in js_array(src, "PHOTOS")}
    closed = js_array(src, "CLOSED", single_quotes=True)
    a = src.index('<symbol id="fa-logo"')
    logo = src[a:src.index("</symbol>", a) + len("</symbol>")]
    prints = json.load(open(os.path.join(ROOT, "data", "prints.json"), encoding="utf-8"))

    items = []
    for e in prints:
        if not e.get("etsy"):
            continue  # only prints that are live on Etsy
        p = photos.get(e["id"])
        it = {"id": e["id"], "land": e["w"] > e["h"], "closed": e["id"] in closed or bool(e.get("closed")), "max": e.get("max", "l"),
              "img": e.get("img") or "img/%s.jpg" % e["id"], "etsy": e["etsy"]}
        it["name"] = e.get("name") or (p[2] if p else e["id"])
        it["cap"] = e.get("cap") or (p[3] if p else "")
        it["alt"] = e.get("alt") or (p[4] if p else "")
        items.append(it)

    SECTIONS = ["Shops and cafés", "Hotels and stations", "Around the city"]
    live = [e for e in prints if e.get("etsy")]
    for it, e in zip(items, live):
        it["sec"] = e.get("section") or "Around the city"
        if it["sec"] not in SECTIONS:
            SECTIONS.append(it["sec"])
    cards = []
    for i, it in enumerate(items):
        stamp = ""  # no Closed stamps in the shop: buyers could read them as "unavailable" (Steven, 16 Nov)
        sizes = "A4 to 50 × 70 cm" if it["max"] == "l" else "A4 to 30 × 40 cm"
        cards.append(
            '<li class="card" data-sec="{sec}" data-i="{i}" data-name="{name}"><button type="button" class="card-btn" data-id="{id}">'
            '<span class="thumb"><img src="../{img}" alt="{alt}" loading="lazy">{stamp}</span>'
            '<span class="c-name">{name}</span>'
            '<span class="c-price">From €{low}</span>'
            '<span class="c-meta">{sizes}</span><span class="c-etsy">Order on Etsy</span></button></li>'.format(
                id=it["id"], img=it["img"], alt=html.escape(it["alt"]), stamp=stamp, i=i, sec=html.escape(it["sec"]),
                name=html.escape(it["name"]), low=SIZES[0][2], sizes=sizes))
    secs = ['<li><button type="button" class="sec" data-sec="" aria-pressed="true">All prints <span>%d</span></button></li>' % len(items)]
    for sname in SECTIONS:
        n = sum(1 for it in items if it["sec"] == sname)
        if n:
            secs.append('<li><button type="button" class="sec" data-sec="%s" aria-pressed="false">%s <span>%d</span></button></li>' % (
                html.escape(sname), html.escape(sname), n))

    data = json.dumps({"items": items, "sizes": SIZES, "frames": FRAMES}, ensure_ascii=False)
    page = PAGE.replace("{LOGO}", logo).replace("{CARDS}", "\n".join(cards)).replace("{DATA}", data).replace(
        "{SECS}", "\n".join(secs)).replace("{COUNT}", str(len(items))).replace("{LOW}", str(SIZES[0][2]))
    os.makedirs(os.path.join(ROOT, "shop"), exist_ok=True)
    open(os.path.join(ROOT, "shop", "index.html"), "w", encoding="utf-8").write(page)
    print("shop/index.html:", len(items), "prints")


PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>Prints · Fading Athens</title>
<meta name="description" content="Fine art prints of Fading Athens: old shop signs, cinemas, hotels and cafés of Athens, photographed by Steven A.J. Beijer before they disappear.">
<link rel="canonical" href="https://fadingathens.com/shop/">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Fading Athens">
<meta property="og:title" content="Prints · Fading Athens">
<meta property="og:description" content="Fine art prints of an Athens that is disappearing. Photographs by Steven A.J. Beijer.">
<meta property="og:url" content="https://fadingathens.com/shop/">
<meta property="og:image" content="https://fadingathens.com/img/zitsa.jpg">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" type="image/png" href="../img/favicon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Commissioner:slnt,wght,FLAR,VOLM@-12..0,100..900,0..100,0..100&display=swap">
<style>
:root{color-scheme:light dark;--plaster:#fbfaf6;--plaster-2:#f2efe6;--line:#e4ded0;--ink:#1f1d1a;--muted:#5f5a52;--red:#c8321f;--yellow:#efb51c;--on-yellow:#1c1a14;--green:#1f5c40;--green-2:#2b7a55;--on-green:#f6f1e3;--card:#fff;--f:"Commissioner",system-ui,sans-serif}
@media (prefers-color-scheme:dark){:root{--plaster:#141513;--plaster-2:#1d1e1b;--line:#33342f;--ink:#efe9dc;--muted:#a8a294;--red:#ff6b57;--yellow:#f2bf3a;--green:#123826;--green-2:#5fb388;--on-green:#f1ecdf;--card:#1d1e1b}}
*{box-sizing:border-box}
body{margin:0;background:var(--plaster);color:var(--ink);font:400 16px/1.5 var(--f)}
img{max-width:100%;display:block}
a{color:inherit}
.wrap{max-width:1240px;margin:0 auto;padding:0 max(24px,env(safe-area-inset-left,0px))}
nav.top{border-bottom:1px solid var(--line);position:sticky;top:0;z-index:20;background:var(--plaster)}
nav.top .wrap{display:flex;align-items:center;justify-content:space-between;gap:16px;padding-block:12px}
.logo svg{height:40px;width:auto;fill:currentColor;display:block;aspect-ratio:1197/1628}
.logo{color:var(--ink)}
.back{font-size:13px;letter-spacing:.12em;text-transform:uppercase;text-decoration:none;font-weight:500}
.back:hover{color:var(--red)}
.pill{display:inline-flex;align-items:center;gap:8px;border-radius:999px;font:600 15px/1 var(--f);padding:12px 20px;text-decoration:none;cursor:pointer;border:2px solid var(--ink);color:var(--ink);background:none;transition:background .15s,transform .15s}
.pill:hover{background:var(--plaster-2);transform:scale(1.02)}
.pill.solid{background:var(--ink);color:var(--plaster)}
.pill.solid:hover{background:var(--ink);filter:brightness(1.15)}
/* shop header */
.shop-head{display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:22px 26px;align-items:center;padding:40px 0 30px;border-bottom:1px solid var(--line)}
.avatar{width:104px;height:104px;border-radius:14px;background:var(--card);border:1px solid var(--line);display:grid;place-items:center;color:var(--ink)}
.avatar svg{height:70px;width:auto;fill:currentColor;aspect-ratio:1197/1628}
.shop-head h1{margin:0;font-weight:800;font-size:clamp(28px,3.6vw,40px);line-height:1.05;letter-spacing:-.01em;font-variation-settings:"FLAR" 100,"VOLM" 100}
.shop-head .tag{margin:4px 0 8px;font-size:16px}
.shop-head .meta{margin:0;display:flex;flex-wrap:wrap;gap:4px 16px;font-size:14px;color:var(--muted);padding:0;list-style:none}
.shop-head .meta b{color:var(--ink);font-weight:600}
.shop-head .meta .ok{color:var(--green-2);font-weight:600}
.head-cta{display:flex;flex-direction:column;align-items:flex-end;gap:8px}
.head-cta small{font-size:12.5px;color:var(--muted)}
.announce{margin:22px 0 0;padding:14px 18px;border-radius:12px;background:var(--plaster-2);font-size:15px;color:var(--muted);grid-column:1/-1;display:flex;gap:14px;align-items:center}
.etsy-dot{flex:none;width:34px;height:34px;border-radius:50%;background:var(--ink);color:var(--plaster);display:grid;place-items:center;font:700 17px/1 var(--f)}
.announce b{color:var(--ink)}
/* layout */
.shop-body{display:grid;grid-template-columns:220px minmax(0,1fr);gap:40px;padding:30px 0 72px}
.shop-body>*{min-width:0}
.side h2{margin:0 0 10px;font-size:15px;font-weight:700}
.secs{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:2px}
.sec{all:unset;box-sizing:border-box;cursor:pointer;display:flex;justify-content:space-between;gap:10px;width:100%;padding:9px 12px;border-radius:8px;font-size:15px}
.sec span{color:var(--muted);font-size:14px}
.sec:hover{background:var(--plaster-2)}
.sec[aria-pressed="true"]{background:var(--plaster-2);font-weight:700;box-shadow:inset 3px 0 0 var(--ink)}
.sec:focus-visible{outline:2px solid var(--red)}
.side-note{margin:24px 0 0;padding-top:18px;border-top:1px solid var(--line);font-size:13.5px;color:var(--muted)}
.side-note a{font-weight:600;color:var(--ink)}
.list-head{display:flex;align-items:center;justify-content:space-between;gap:14px;margin-bottom:18px}
.list-head h2{margin:0;font-size:20px;font-weight:700}
.list-head h2 #secCount{color:var(--muted);font-weight:400;font-size:15px;margin-left:6px}
.sort{display:flex;align-items:center;gap:8px;font-size:14px}
.sort select{font:600 14px var(--f);color:var(--ink);background:var(--plaster);border:1.5px solid var(--line);border-radius:999px;padding:8px 32px 8px 14px;appearance:none;cursor:pointer;background-image:linear-gradient(45deg,transparent 50%,currentColor 50%),linear-gradient(135deg,currentColor 50%,transparent 50%);background-position:calc(100% - 17px) 55%,calc(100% - 12px) 55%;background-size:5px 5px;background-repeat:no-repeat}
.grid{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:30px 18px}
.card[hidden]{display:none}
.card-btn{all:unset;box-sizing:border-box;cursor:pointer;display:flex;flex-direction:column;width:100%;border-radius:12px}
.card-btn:focus-visible{outline:2px solid var(--red);outline-offset:4px}
.thumb{position:relative;display:flex;align-items:center;justify-content:center;aspect-ratio:1/1;overflow:hidden;background:var(--plaster-2);border-radius:12px;padding:12px;margin-bottom:10px;transition:box-shadow .2s}
.thumb img{max-height:100%;width:auto;height:auto;max-width:100%;object-fit:contain;background:#fff;padding:4px;box-shadow:0 1px 2px rgba(0,0,0,.12),0 8px 16px -8px rgba(0,0,0,.35);transition:transform .3s ease}
.card-btn:hover .thumb{box-shadow:0 6px 22px -6px rgba(0,0,0,.28)}
.card-btn:hover .thumb img{transform:scale(1.035)}
.c-name{font-size:14.5px;line-height:1.35;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.card-btn:hover .c-name{text-decoration:underline;text-underline-offset:2px}
.c-price{margin-top:4px;font-size:17px;font-weight:700}
.c-meta{font-size:13px;color:var(--muted)}
.c-tag{align-self:flex-start;margin-top:7px;font-size:12px;font-weight:600;padding:3px 9px;border-radius:999px;background:color-mix(in srgb,var(--green-2) 16%,transparent);color:var(--green-2)}
.c-etsy{margin-top:3px;font-size:12.5px;font-weight:600;color:var(--muted)}
.empty{color:var(--muted)}
/* ordering */
.order{padding-bottom:56px}
.order-box{background:var(--plaster-2);border-radius:18px;padding:34px 34px 36px}
.order h2{margin:0 0 22px;font-size:22px;font-weight:800}
.steps{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:30px}
.steps .n{display:grid;place-items:center;width:38px;height:38px;border-radius:50%;background:var(--red);color:#fff;font-weight:800;font-size:17px;margin-bottom:12px}
.order h3{margin:0 0 6px;font-size:17px;font-weight:700}
.order p{margin:0;color:var(--muted);font-size:15px}
.order p a{color:var(--ink);font-weight:600}
.about{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:30px;padding:30px 34px 0}
footer.foot{border-top:1px solid var(--line);padding:22px 0 40px;font-size:13px;color:var(--muted)}
/* listing panel */
.panel{position:fixed;inset:0;z-index:50;background:rgba(15,14,12,.6);display:flex;align-items:center;justify-content:center;padding:20px}
.panel[hidden]{display:none}
.sheet{background:var(--plaster);color:var(--ink);width:min(1040px,100%);max-height:calc(100vh - 40px);overflow:auto;display:grid;grid-template-columns:minmax(0,1.25fr) minmax(0,1fr);position:relative;border-radius:18px}
.sheet .pic{background:var(--plaster-2);display:grid;place-items:center;padding:30px;min-height:320px}
.sheet .pic img{max-height:min(72vh,660px);width:auto;background:#fff;padding:8px;box-shadow:0 2px 4px rgba(0,0,0,.15),0 18px 34px -16px rgba(0,0,0,.5)}
.info{padding:30px 28px 26px;display:flex;flex-direction:column;gap:14px}
.info .p-price{margin:0;font-size:30px;font-weight:800;line-height:1}
.info .p-price small{font-size:14px;font-weight:400;color:var(--muted);margin-left:6px}
.info h2{margin:0;font-size:19px;line-height:1.35;font-weight:500}
.info .p-cap{margin:0;font-size:15px;color:var(--muted)}
.info .p-closed{margin:0;font-size:13px;font-weight:700;color:var(--red)}
.field .lab{margin:0 0 6px;font-size:14px;font-weight:600}
.field .lab span{font-weight:400;color:var(--muted)}
.sizes{list-style:none;margin:0;padding:0;border:1.5px solid var(--line);border-radius:10px}
.sizes li{display:flex;justify-content:space-between;padding:10px 14px;font-size:15px}
.sizes li+li{border-top:1px solid var(--line)}
.sizes b{font-weight:700}
.via{margin:-4px 0 0;font-size:13px;color:var(--muted);text-align:center}
.field select{width:100%;font:500 16px var(--f);color:var(--ink);background:var(--plaster);border:1.5px solid var(--ink);border-radius:10px;padding:12px 40px 12px 14px;appearance:none;cursor:pointer;background-image:linear-gradient(45deg,transparent 50%,currentColor 50%),linear-gradient(135deg,currentColor 50%,transparent 50%);background-position:calc(100% - 22px) 52%,calc(100% - 16px) 52%;background-size:6px 6px;background-repeat:no-repeat}
fieldset{border:0;margin:0;padding:0}
.buy{justify-content:center;width:100%;padding:16px 20px;font-size:16px}
.buy.off{opacity:.45;cursor:default;pointer-events:none}
.ticks{list-style:none;margin:4px 0 0;padding:14px 0 0;border-top:1px solid var(--line);display:grid;gap:8px;font-size:14px}
.ticks li{display:flex;gap:10px}
.ticks li::before{content:"✓";color:var(--green-2);font-weight:800}
.x{position:absolute;top:12px;right:12px;font:400 26px/1 var(--f);background:var(--plaster);border:0;border-radius:50%;color:var(--ink);cursor:pointer;width:42px;height:42px;z-index:2;box-shadow:0 1px 4px rgba(0,0,0,.2)}
@media (max-width:1000px){.grid{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media (max-width:820px){
 .logo svg{height:34px}.back{font-size:12px;letter-spacing:.1em}nav.top .wrap{padding-block:9px}
 .shop-head{grid-template-columns:auto minmax(0,1fr);padding:24px 0 22px;gap:14px 16px;align-items:start}
 .avatar{width:72px;height:72px;border-radius:12px}.avatar svg{height:48px}
 .shop-head .tag{font-size:15px;margin:2px 0 6px}
 .head-cta{grid-column:1/-1;align-items:stretch}.head-cta .pill{justify-content:center}.head-cta small{text-align:center}
 .announce{margin:4px 0 0}
 .shop-body{grid-template-columns:1fr;gap:16px;padding-top:18px}
 .side h2,.side-note{display:none}
 .secs{flex-direction:row;overflow-x:auto;scrollbar-width:none;gap:8px;margin:0 -24px;padding:0 24px}
 .secs::-webkit-scrollbar{display:none}
 .sec{flex:none;width:auto;white-space:nowrap;border:1.5px solid var(--line);border-radius:999px;padding:8px 14px;font-size:14px}
 .sec[aria-pressed="true"]{background:var(--ink);color:var(--plaster);border-color:var(--ink);box-shadow:none}
 .sec[aria-pressed="true"] span{color:inherit;opacity:.7}
 .grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:24px 12px}
 .thumb{padding:10px}
 .list-head h2{font-size:17px}
 .order-box{padding:24px 20px 26px}.steps,.about{grid-template-columns:1fr;gap:20px}.about{padding:24px 4px 0}
 .panel{padding:0;align-items:flex-end}.sheet{grid-template-columns:1fr;max-height:94vh;border-radius:18px 18px 0 0}.sheet .pic{min-height:0;padding:18px}.sheet .pic img{max-height:40vh}.info{padding:20px 18px 30px}
}
</style>
</head>
<body>
<svg width="0" height="0" style="position:absolute" aria-hidden="true">{LOGO}</svg>
<nav class="top"><div class="wrap">
  <a class="logo" href="../" aria-label="Fading Athens home"><svg viewBox="0 0 1197 1628" aria-hidden="true"><use href="#fa-logo"/></svg></a>
  <a class="back" href="../">← Back to Fading Athens</a>
</div></nav>
<main class="wrap">
  <header class="shop-head">
    <div class="avatar" aria-hidden="true"><svg viewBox="0 0 1197 1628"><use href="#fa-logo"/></svg></div>
    <div>
      <h1>Fading Athens prints</h1>
      <p class="tag">Fine art prints of an Athens that is disappearing</p>
      <ul class="meta"><li>Photographs by <b>Steven A.J. Beijer</b></li><li>Athens, Greece</li><li>{COUNT} prints</li><li class="ok">Printed to order in Europe</li><li><b>Sold through Etsy</b></li></ul>
    </div>
    <div class="head-cta">
      <a class="pill" href="https://www.etsy.com/shop/FadingAthens" target="_blank" rel="noopener">Visit the shop on Etsy ↗</a>
    </div>
    <p class="announce"><span class="etsy-dot" aria-hidden="true">↗</span><span><b>Every order goes through Etsy.</b> Browse the prints here, then click “Order on Etsy” to choose the size, see the shipping cost and pay in the Fading Athens shop on Etsy.</span></p>
  </header>
  <div class="shop-body">
    <aside class="side">
      <h2>Sections</h2>
      <ul class="secs" id="secs">
{SECS}
      </ul>
      <p class="side-note">A first selection; more prints will follow. All prints are unframed. Orders, payment and shipping are handled by Etsy. <a href="https://www.etsy.com/shop/FadingAthens" target="_blank" rel="noopener">Etsy shop ↗</a></p>
    </aside>
    <section aria-labelledby="listTitle">
      <div class="list-head">
        <h2 id="listTitle"><span id="secName">All prints</span><span id="secCount">{COUNT}</span></h2>
        <label class="sort">Sort <select id="sort"><option value="i">Featured</option><option value="name">Name</option></select></label>
      </div>
      <ul class="grid" id="grid">
{CARDS}
      </ul>
    </section>
  </div>
</main>
<section class="wrap order" aria-labelledby="orderT">
  <div class="order-box">
    <h2 id="orderT">How ordering works</h2>
    <ol class="steps">
      <li><span class="n">1</span><h3>Pick a print here</h3><p>Click any print to see it larger, with its sizes and prices.</p></li>
      <li><span class="n">2</span><h3>Order on Etsy</h3><p>“Order on Etsy” opens the print in the <a href="https://www.etsy.com/shop/FadingAthens" target="_blank" rel="noopener">Fading Athens shop on Etsy</a>. Choose the size, see the shipping cost and pay there.</p></li>
      <li><span class="n">3</span><h3>Printed and posted</h3><p>The print is made to order at a print lab in Europe and sent to your door. Etsy keeps you updated on your order.</p></li>
    </ol>
  </div>
  <div class="about">
    <div><h3>Fine art paper</h3><p>Unframed prints, 12-colour giclée on 200 gsm matte fine art paper, with a white border so nothing of the photo is cropped.</p></div>
    <div><h3>Places that are gone</h3><p>Several of the shops, hotels and stations in these prints have since closed for good. The photograph is what is left of them.</p></div>
  </div>
</section>
<footer class="foot"><div class="wrap">© Steven A.J. Beijer · Fading Athens · <a href="../">fadingathens.com</a></div></footer>

<div class="panel" id="panel" hidden role="dialog" aria-modal="true" aria-labelledby="pName">
  <div class="sheet">
    <button type="button" class="x" id="pClose" aria-label="Close">×</button>
    <div class="pic" id="pPic"><img id="pImg" alt=""></div>
    <div class="info">
      <p class="p-price" id="pTotal"></p>
      <h2 id="pName"></h2>
      <p class="p-cap" id="pCap"></p>
      <p class="p-closed" id="pClosed" hidden><span lang="el">Έκλεισε</span> · This place has closed</p>
      <div class="field"><p class="lab">Sizes and prices <span>· choose on Etsy</span></p><ul class="sizes" id="pSizes"></ul></div>
      <fieldset hidden><div id="pFrames"></div></fieldset>
      <a class="pill solid buy" id="pBuy" href="#" role="button">Order on Etsy</a>
      <p class="via">Opens this print in the Fading Athens shop on Etsy, where you choose the size, see shipping and pay.</p>
      <ul class="ticks"><li>Fine art giclée on 200 gsm matte paper</li><li>White border, nothing of the photo cropped</li><li>Printed to order in Europe and posted to you</li><li id="pShip">Payment, shipping and order updates by Etsy</li></ul>
    </div>
  </div>
</div>

<script>
var D={DATA},CHECKOUT={};
var byId={};D.items.forEach(function(it){byId[it.id]=it});
var P=document.getElementById('panel'),cur=null,last=null;
function sizeLab(o,land){var lab=o[1];return land?lab.replace(/(\d+) × (\d+)/,'$2 × $1'):lab}
function sizeList(){return D.sizes.filter(function(o){return cur.max==='l'||o[0]!=='l'}).map(function(o){return '<li><span>'+sizeLab(o,cur.land)+'</span><b>€'+o[2]+'</b></li>'}).join('')}
function find(list,id){for(var i=0;i<list.length;i++)if(list[i][0]===id)return list[i]}
function update(){var s=D.sizes[0];
  document.getElementById('pTotal').innerHTML='<small style="margin:0 6px 0 0">From</small>€'+s[2]+'<small>plus shipping</small>';
  var url=cur.etsy||CHECKOUT[cur.id+'|'+s[0]+'|none'],b=document.getElementById('pBuy');
  b.dataset.url=url||'';b.href=url||'#';if(url){b.target='_blank';b.rel='noopener'}else{b.removeAttribute('target')}
  b.textContent=url?(cur.etsy?'Order on Etsy ↗':'Order this print'):'Not available online';b.classList.toggle('off',!url);if(url)b.removeAttribute('aria-disabled');else b.setAttribute('aria-disabled','true')}
function openP(id,push){cur=byId[id];if(!cur)return;last=document.activeElement;
  document.getElementById('pImg').src='../'+cur.img;document.getElementById('pImg').alt=cur.alt;
  document.getElementById('pName').textContent=cur.name+' · Fine art print'+(cur.max==='l'?'':', up to 30 × 40 cm');
  document.getElementById('pCap').textContent=cur.cap;document.getElementById('pClosed').hidden=true;
  document.getElementById('pSizes').innerHTML=sizeList();
  update();P.hidden=false;document.body.style.overflow='hidden';document.getElementById('pClose').focus();
  if(push!==false)try{history.replaceState(null,'','#'+id)}catch(e){}}
function closeP(){P.hidden=true;document.body.style.overflow='';try{history.replaceState(null,'',location.pathname)}catch(e){}if(last)last.focus()}
document.getElementById('grid').addEventListener('click',function(e){var b=e.target.closest('.card-btn');if(b)openP(b.dataset.id)});
P.addEventListener('click',function(e){if(e.target===P)closeP()});
document.getElementById('pClose').addEventListener('click',closeP);
document.addEventListener('keydown',function(e){if(!P.hidden&&e.key==='Escape')closeP()});
document.getElementById('pBuy').addEventListener('click',function(e){if(!this.dataset.url)e.preventDefault()});
/* sections and sort */
var grid=document.getElementById('grid'),cards=[].slice.call(grid.children);
document.getElementById('secs').addEventListener('click',function(e){var b=e.target.closest('.sec');if(!b)return;
  [].forEach.call(document.querySelectorAll('.sec'),function(x){x.setAttribute('aria-pressed',x===b?'true':'false')});
  var s=b.dataset.sec,n=0;cards.forEach(function(c){var show=!s||c.dataset.sec===s;c.hidden=!show;if(show)n++});
  document.getElementById('secName').textContent=s||'All prints';document.getElementById('secCount').textContent=n});
document.getElementById('sort').addEventListener('change',function(){var k=this.value;
  cards.slice().sort(function(a,b){return k==='name'?a.dataset.name.localeCompare(b.dataset.name,'el'):a.dataset.i-b.dataset.i}).forEach(function(c){grid.appendChild(c)})});
if(location.hash.length>1)openP(decodeURIComponent(location.hash.slice(1)),false);
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
