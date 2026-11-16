"""Make the print shop page: shop/index.html.

Lists the prints in data/prints.json (Steven's selection, made from his
full-resolution files). Names and captions come from PHOTOS in index.html
for photos on the site, or from prints.json for new ones. "max" is the
biggest size the original file allows ("m" = 30x40, "l" = 50x70).

Checkout: every print is a Gelato product in the Shopify store. Buy links
are in shop/checkout.json as
  {"<slug>|<size id>|<frame id>": "https://...", "*|a4|none": "..."}
and "Order this print" goes straight to Shopify checkout. No Instagram
ordering (Steven, 16 Nov): a combination without a link shows as
"Not available online" and can't be clicked.

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
SHOP_OPEN = False

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
        print("shop/index.html: offline page (SHOP_OPEN = False)")
        return

    src = open(os.path.join(ROOT, "index.html"), encoding="utf-8").read()
    photos = {p[0]: p for p in js_array(src, "PHOTOS")}
    closed = js_array(src, "CLOSED", single_quotes=True)
    a = src.index('<symbol id="fa-logo"')
    logo = src[a:src.index("</symbol>", a) + len("</symbol>")]
    prints = json.load(open(os.path.join(ROOT, "data", "prints.json"), encoding="utf-8"))

    items = []
    for e in prints:
        p = photos.get(e["id"])
        it = {"id": e["id"], "land": e["w"] > e["h"], "closed": e["id"] in closed or bool(e.get("closed")), "max": e.get("max", "l"),
              "img": e.get("img") or "img/%s.jpg" % e["id"]}
        it["name"] = e.get("name") or (p[2] if p else e["id"])
        it["cap"] = e.get("cap") or (p[3] if p else "")
        it["alt"] = e.get("alt") or (p[4] if p else "")
        items.append(it)

    cards = []
    for it in items:
        stamp = ('<span class="stamp"><span lang="el">Έκλεισε</span> · Closed</span>' if it["closed"] else "")
        sizes = "up to 50 × 70 cm" if it["max"] == "l" else "up to 30 × 40 cm"
        cards.append(
            '<li class="card"><button type="button" class="card-btn" data-id="{id}">'
            '<span class="thumb"><img src="../{img}" alt="{alt}" loading="lazy">{stamp}</span>'
            '<span class="c-name">{name}</span><span class="c-meta">From €{low} · {sizes}</span></button></li>'.format(
                id=it["id"], img=it["img"], alt=html.escape(it["alt"]), stamp=stamp,
                name=html.escape(it["name"]), low=SIZES[0][2], sizes=sizes))

    data = json.dumps({"items": items, "sizes": SIZES, "frames": FRAMES}, ensure_ascii=False)
    page = PAGE.replace("{LOGO}", logo).replace("{CARDS}", "\n".join(cards)).replace("{DATA}", data).replace(
        "{COUNT}", str(len(items))).replace("{LOW}", str(SIZES[0][2]))
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
:root{color-scheme:light dark;--plaster:#fbfaf6;--plaster-2:#f2efe6;--line:#e4ded0;--ink:#1f1d1a;--muted:#5f5a52;--red:#c8321f;--yellow:#efb51c;--on-yellow:#1c1a14;--green:#1f5c40;--on-green:#f6f1e3;--f:"Commissioner",system-ui,sans-serif}
@media (prefers-color-scheme:dark){:root{--plaster:#141513;--plaster-2:#1d1e1b;--line:#33342f;--ink:#efe9dc;--muted:#a8a294;--red:#ff6b57;--yellow:#f2bf3a;--green:#123826;--on-green:#f1ecdf}}
*{box-sizing:border-box}
body{margin:0;background:var(--plaster);color:var(--ink);font:400 16px/1.5 var(--f)}
img{max-width:100%;display:block}
a{color:inherit}
.wrap{max-width:1240px;margin:0 auto;padding:0 max(24px,env(safe-area-inset-left,0px))}
nav.top{border-bottom:1px solid var(--line)}
nav.top .wrap{display:flex;align-items:center;justify-content:space-between;gap:16px;padding-block:14px}
.logo svg{height:46px;width:auto;fill:currentColor;display:block;aspect-ratio:1197/1628}
.logo{color:var(--ink)}
.back{font-size:13px;letter-spacing:.12em;text-transform:uppercase;text-decoration:none;font-weight:500}
.back:hover{color:var(--red)}
header.intro{padding:48px 0 28px}
.kicker{margin:0;font-size:13px;letter-spacing:.3em;text-transform:uppercase;color:var(--green)}
@media (prefers-color-scheme:dark){.kicker{color:#5fb388}}
h1{margin:8px 0 12px;font-weight:800;font-size:clamp(34px,5vw,58px);line-height:.95;letter-spacing:-.02em;color:var(--red);font-variation-settings:"FLAR" 100,"VOLM" 100}
.intro p.lede{max-width:40em;margin:0;color:var(--muted)}
.facts{display:flex;flex-wrap:wrap;gap:8px;margin:18px 0 0;padding:0;list-style:none}
.facts li{border:1px solid var(--line);padding:5px 10px;font-size:13px}
.chips{display:flex;gap:8px;overflow-x:auto;scrollbar-width:none;padding:4px 0 18px;position:sticky;top:0;background:var(--plaster);z-index:5}
.chips::-webkit-scrollbar{display:none}
.chips button{flex:none;font:500 13px var(--f);letter-spacing:.06em;color:var(--ink);background:none;border:1.5px solid var(--line);padding:7px 12px;cursor:pointer}
.chips button[aria-pressed="true"]{background:var(--ink);color:var(--plaster);border-color:var(--ink)}
.grid{list-style:none;margin:0 0 64px;padding:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:28px 22px}
.card[hidden]{display:none}
.card-btn{all:unset;cursor:pointer;display:flex;flex-direction:column;gap:6px;width:100%}
.thumb{position:relative;display:flex;align-items:center;justify-content:center;aspect-ratio:4/5;min-height:0;overflow:hidden;background:var(--plaster-2);padding:16px;transition:background .2s}
.thumb img{max-height:100%;width:auto;height:auto;max-width:100%;object-fit:contain;box-shadow:0 1px 2px rgba(0,0,0,.12),0 10px 20px -10px rgba(0,0,0,.4);background:#fff;padding:5px}
.card-btn:hover .thumb,.card-btn:focus-visible .thumb{background:var(--line)}
.card-btn:focus-visible{outline:2px solid var(--red);outline-offset:3px}
.stamp{position:absolute;top:10px;right:10px;transform:rotate(6deg);border:2px solid var(--red);color:var(--red);background:#f6f1e3;font:800 10px/1 var(--f);letter-spacing:.12em;text-transform:uppercase;padding:4px 6px}
.c-name{font-weight:700;font-size:15px;line-height:1.25}
.c-meta{font-size:13px;color:var(--muted)}
.how{border-top:1px solid var(--line);padding:36px 0 56px;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:28px}
.how h2{margin:0 0 6px;font-size:17px;font-weight:800}
.how p{margin:0;color:var(--muted);font-size:15px}
@media (max-width:760px){.how{grid-template-columns:1fr;gap:18px}.grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:22px 14px}.thumb{padding:10px}header.intro{padding:32px 0 20px}}
footer.foot{border-top:1px solid var(--line);padding:22px 0 40px;font-size:13px;color:var(--muted)}
/* product panel */
.panel{position:fixed;inset:0;z-index:50;background:rgba(15,14,12,.6);display:flex;align-items:center;justify-content:center;padding:20px}
.panel[hidden]{display:none}
.sheet{background:var(--plaster);color:var(--ink);width:min(1000px,100%);max-height:calc(100vh - 40px);overflow:auto;display:grid;grid-template-columns:minmax(0,1.15fr) minmax(0,1fr);position:relative}
.sheet .pic{background:var(--plaster-2);display:grid;place-items:center;padding:28px;min-height:320px}
.sheet .pic img{max-height:min(70vh,640px);width:auto;background:#fff;padding:8px;box-shadow:0 2px 4px rgba(0,0,0,.15),0 18px 34px -16px rgba(0,0,0,.5)}
.sheet .pic.framed-wood img{border:14px solid #b98a5a;padding:14px}
.sheet .pic.framed-black img{border:10px solid #1a1a1a;padding:14px}
.info{padding:28px 28px 24px;display:flex;flex-direction:column;gap:14px}
.info .p-series{margin:0;font-size:12.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted)}
.info h2{margin:0;font-size:clamp(24px,2.6vw,32px);line-height:1.05;font-weight:800;color:var(--red);font-variation-settings:"FLAR" 100,"VOLM" 100}
.info .p-cap{margin:0;font-size:15px;color:var(--muted)}
.info .p-closed{margin:0;font-size:13px;font-weight:700;color:var(--red)}
fieldset{border:0;margin:0;padding:0}
legend{font-size:12.5px;letter-spacing:.14em;text-transform:uppercase;margin-bottom:8px;font-weight:600}
.opts{display:grid;gap:6px}
.opts label{display:flex;justify-content:space-between;gap:10px;border:1.5px solid var(--line);padding:9px 12px;cursor:pointer;font-size:15px}
.opts input{position:absolute;opacity:0}
.opts label:has(input:checked){border-color:var(--ink);background:var(--plaster-2)}
.opts label:has(input:focus-visible){outline:2px solid var(--red)}
.opts .pr{color:var(--muted)}
.total{display:flex;align-items:baseline;justify-content:space-between;border-top:1px solid var(--line);padding-top:12px;font-size:15px}
.total b{font-size:26px;font-weight:800}
.buy{font:600 14px var(--f);letter-spacing:.14em;text-transform:uppercase;background:var(--yellow);color:var(--on-yellow);border:0;padding:15px 18px;cursor:pointer;text-align:center;text-decoration:none}
.buy:hover{filter:brightness(1.05)}
.small{margin:0;font-size:13px;color:var(--muted)}
.buy.off{opacity:.45;cursor:default;pointer-events:none}
.x{position:absolute;top:8px;right:10px;font:400 30px/1 var(--f);background:none;border:0;color:var(--ink);cursor:pointer;width:40px;height:40px;z-index:2}
@media (max-width:760px){.panel{padding:0;align-items:flex-end}.sheet{grid-template-columns:1fr;max-height:100vh}.sheet .pic{min-height:0;padding:18px}.sheet .pic img{max-height:42vh}.info{padding:20px 18px 28px}}
</style>
</head>
<body>
<svg width="0" height="0" style="position:absolute" aria-hidden="true">{LOGO}</svg>
<nav class="top"><div class="wrap">
  <a class="logo" href="../" aria-label="Fading Athens home"><svg viewBox="0 0 1197 1628" aria-hidden="true"><use href="#fa-logo"/></svg></a>
  <a class="back" href="../">← Back to Fading Athens</a>
</div></nav>
<main class="wrap">
  <header class="intro">
    <p class="kicker" lang="el">Τυπώματα</p>
    <h1>Prints</h1>
    <p class="lede">A first selection of Fading Athens photographs, available as fine art prints: shopfronts, cafés, hotels and corners of an Athens that is disappearing. Printed to order with a white border, so nothing of the photo is cropped. More prints will follow.</p>
    <ul class="facts"><li>{COUNT} photographs</li><li>3 sizes, from €{LOW}</li><li>Unframed fine art prints</li><li>Printed in Europe, shipped across the EU</li></ul>
  </header>
  <ul class="grid" id="grid">
{CARDS}
  </ul>
  <section class="how" aria-label="About the prints">
    <div><h2>Fine art paper</h2><p>Unframed prints are 12-colour giclée on 200 gsm matte fine art paper.</p></div>
    <div><h2>Places that are gone</h2><p>Prints marked <span lang="el">Έκλεισε</span> · Closed show places that no longer exist. The photograph is all that is left.</p></div>
    <div><h2>Printed for you</h2><p>Each print is made when you order it, at a print lab in Europe, and posted straight to your door. Pay by card at checkout; shipping is shown before you pay.</p></div>
  </section>
</main>
<footer class="foot"><div class="wrap">© Steven A.J. Beijer · Fading Athens · <a href="../">fadingathens.com</a></div></footer>

<div class="panel" id="panel" hidden role="dialog" aria-modal="true" aria-labelledby="pName">
  <div class="sheet">
    <button type="button" class="x" id="pClose" aria-label="Close">×</button>
    <div class="pic" id="pPic"><img id="pImg" alt=""></div>
    <div class="info">
      <p class="p-series" id="pSeries"></p>
      <h2 id="pName"></h2>
      <p class="p-cap" id="pCap"></p>
      <p class="p-closed" id="pClosed" hidden><span lang="el">Έκλεισε</span> · This place has closed</p>
      <fieldset><legend>Size</legend><div class="opts" id="pSizes"></div></fieldset>
      <fieldset hidden><legend>Frame</legend><div class="opts" id="pFrames"></div></fieldset>
      <div class="total"><span>Price</span><b id="pTotal"></b></div>
      <a class="buy" id="pBuy" href="#" role="button">Order this print</a>
      <p class="small" id="pShip">Shipping is added at checkout.</p>
    </div>
  </div>
</div>

<script>
var D={DATA},CHECKOUT={};
try{fetch('checkout.json',{cache:'no-store'}).then(function(r){return r.ok?r.json():{}}).then(function(j){CHECKOUT=j||{};if(typeof P!=='undefined'&&!P.hidden)update()}).catch(function(){})}catch(e){}
var byId={};D.items.forEach(function(it){byId[it.id]=it});
var P=document.getElementById('panel'),cur=null,last=null;
function opt(name,list,land){return list.filter(function(o){return name!=='size'||cur.max==='l'||o[0]!=='l'}).map(function(o,i){var lab=o[1];if(land&&name==='size')lab=lab.replace(/(\d+) × (\d+)/,'$2 × $1');
  return '<label><span><input type="radio" name="'+name+'" value="'+o[0]+'"'+(i===0?' checked':'')+'> '+lab+'</span><span class="pr">'+(name==='frame'?(o[2]?'+ €'+o[2]:'included'):'€'+o[2])+'</span></label>'}).join('')}
function sel(n){return document.querySelector('input[name="'+n+'"]:checked').value}
function find(list,id){for(var i=0;i<list.length;i++)if(list[i][0]===id)return list[i]}
function update(){var s=find(D.sizes,sel('size')),f=find(D.frames,sel('frame')),tot=s[2]+f[2];
  document.getElementById('pTotal').textContent='€'+tot;
  var pic=document.getElementById('pPic');pic.className='pic'+(f[0]==='none'?'':' framed-'+f[0]);
  var url=CHECKOUT[cur.id+'|'+s[0]+'|'+f[0]]||CHECKOUT['*|'+s[0]+'|'+f[0]],b=document.getElementById('pBuy');
  b.dataset.url=url||'';b.href=url||'#';if(url){b.target='_blank';b.rel='noopener'}else{b.removeAttribute('target')}
  var size=s[1];if(cur.land)size=size.replace(/(\d+) × (\d+)/,'$2 × $1');
  b.textContent=url?'Order this print':'Not available online';b.classList.toggle('off',!url);if(url)b.removeAttribute('aria-disabled');else b.setAttribute('aria-disabled','true')}
function openP(id,push){cur=byId[id];if(!cur)return;last=document.activeElement;
  document.getElementById('pImg').src='../'+cur.img;document.getElementById('pImg').alt=cur.alt;
  document.getElementById('pSeries').textContent='Fine art print'+(cur.max==='l'?'':' · up to 30 × 40 cm');document.getElementById('pName').textContent=cur.name;
  document.getElementById('pCap').textContent=cur.cap;document.getElementById('pClosed').hidden=!cur.closed;
  document.getElementById('pSizes').innerHTML=opt('size',D.sizes,cur.land);document.getElementById('pFrames').innerHTML=opt('frame',D.frames);
  update();P.hidden=false;document.body.style.overflow='hidden';document.getElementById('pClose').focus();
  if(push!==false)try{history.replaceState(null,'','#'+id)}catch(e){}}
function closeP(){P.hidden=true;document.body.style.overflow='';try{history.replaceState(null,'',location.pathname)}catch(e){}if(last)last.focus()}
document.getElementById('grid').addEventListener('click',function(e){var b=e.target.closest('.card-btn');if(b)openP(b.dataset.id)});
P.addEventListener('change',update);
P.addEventListener('click',function(e){if(e.target===P)closeP()});
document.getElementById('pClose').addEventListener('click',closeP);
document.addEventListener('keydown',function(e){if(!P.hidden&&e.key==='Escape')closeP()});
document.getElementById('pBuy').addEventListener('click',function(e){if(!this.dataset.url)e.preventDefault()});
if(location.hash.length>1)openP(decodeURIComponent(location.hash.slice(1)),false);
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
