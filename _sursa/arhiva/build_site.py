#!/usr/bin/env python3
"""Generează site-ul static Linux for Education din posts.json (export al fluxului Blogger).
Utilizare: python3 build_site.py posts.json <folder_iesire>"""
import json, re, sys, os, html, unicodedata, collections
from html.parser import HTMLParser
from datetime import datetime, timezone, timedelta

SRC, OUT = sys.argv[1], sys.argv[2]
BLOG = 'https://linuxforeducation.blogspot.com/'
data = json.load(open(SRC, encoding='utf-8'))
POSTS = data['posts']
SITE = data.get('title', 'Linux for Education')
ROOT = '\x00ROOT\x00'
LUNI = ['ianuarie', 'februarie', 'martie', 'aprilie', 'mai', 'iunie', 'iulie', 'august',
        'septembrie', 'octombrie', 'noiembrie', 'decembrie']
try:
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo('Europe/Bucharest')
except Exception:
    TZ = timezone(timedelta(hours=2))


def slugify(s):
    s = s.replace('ș', 's').replace('ț', 't').replace('Ș', 'S').replace('Ț', 'T')
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')


def esc(s):
    return html.escape(s, quote=True)


# ---------- pregătire articole ----------
used = set()
for p in POSTS:
    p['title'] = re.sub(r'\s+', ' ', p['title']).strip()
    dt = datetime.fromisoformat(p['published']).astimezone(TZ)
    p['dt'] = dt
    p['iso'] = dt.date().isoformat()
    p['date'] = '%d %s %d' % (dt.day, LUNI[dt.month - 1], dt.year)
    base = os.path.basename(p['url'] or '').replace('.html', '') or slugify(p['title'])[:60]
    slug = '%d-%02d-%s' % (dt.year, dt.month, base)
    while slug in used:
        slug += '-2'
    used.add(slug)
    p['slug'] = slug
    p['path'] = 'articole/%s.html' % slug

URLMAP = {}
for p in POSTS:
    if p['url']:
        URLMAP[p['url'].split('://', 1)[1]] = p
HOME_RE = re.compile(r'https?://(linuxforeducation\.blogspot\.com/[^?#]*)')


def local_link(href):
    m = HOME_RE.match(href)
    if not m:
        return None
    u = m.group(1)
    if u in URLMAP:
        return ROOT + URLMAP[u]['path']
    if u.rstrip('/') == 'linuxforeducation.blogspot.com':
        return ROOT + 'index.html'
    return None


# ---------- curățare HTML ----------
VOID = {'br', 'hr', 'img', 'input', 'meta', 'link', 'source', 'wbr', 'col', 'area', 'base', 'embed', 'param', 'track'}
DROP = {'script', 'style', 'button', 'svg', 'mat-icon', 'gem-icon', 'gem-icon-button', 'sources-carousel-inline',
        'source-inline-chip', 'source-footnote', 'elicitations', 'follow-up', 'sider-code-explain', 'iframe',
        'noscript', 'form', 'object', 'textarea', 'select'}
KEEP = {'p', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'li', 'b', 'strong', 'i', 'em', 'u', 'table', 'thead',
        'tbody', 'tr', 'td', 'th', 'pre', 'code', 'blockquote', 'sup', 'sub', 'figure', 'figcaption', 'div', 'a'}
MAPTAG = {'h1': 'h2'}


class San(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.stack = []
        self.dropping = 0
        self.pre = 0

    def handle_starttag(self, tag, attrs):
        a = {k: (v or '') for k, v in attrs}
        cls = a.get('class', '').split()
        if tag in VOID:
            if self.dropping:
                return
            if tag == 'br':
                self.out.append('<br>')
            elif tag == 'hr':
                self.out.append('<hr>')
            elif tag == 'img':
                src = a.get('src', '')
                if re.match(r'https?://', src):
                    self.out.append('<img src="%s" alt="%s" loading="lazy" decoding="async">'
                                    % (esc(src), esc(a.get('alt', ''))))
            return
        tag2 = MAPTAG.get(tag, tag)
        if tag in DROP or (tag == 'div' and 'toolbar' in cls) or (tag == 'a' and 'td-heading-self-link' in cls):
            self.stack.append((tag, None, True))
            self.dropping += 1
            return
        close = None
        if not self.dropping and tag2 in KEEP:
            if tag2 == 'a':
                href = a.get('href', '').strip()
                loc = local_link(href)
                if loc:
                    self.out.append('<a href="%s">' % esc(loc))
                    close = '</a>'
                elif re.match(r'(https?://|mailto:)', href):
                    self.out.append('<a href="%s" target="_blank" rel="noopener noreferrer">' % esc(href))
                    close = '</a>'
            elif tag2 == 'table':
                self.out.append('<div class="tw"><table>')
                close = '</table></div>'
            elif tag2 in ('td', 'th'):
                ex = ''.join(' %s="%d"' % (k, int(a[k])) for k in ('colspan', 'rowspan') if a.get(k, '').isdigit())
                self.out.append('<%s%s>' % (tag2, ex))
                close = '</%s>' % tag2
            else:
                self.out.append('<%s>' % tag2)
                close = '</%s>' % tag2
        if tag == 'pre':
            self.pre += 1
        self.stack.append((tag, close, False))

    def _pop(self):
        t, close, drop = self.stack.pop()
        if drop:
            self.dropping -= 1
        if t == 'pre':
            self.pre -= 1
        if close and not self.dropping:
            self.out.append(close)

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        idx = None
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                idx = i
                break
        if idx is None:
            return
        while len(self.stack) > idx:
            self._pop()

    def handle_data(self, d):
        if self.dropping:
            return
        if not self.pre:
            d = d.replace('\xa0', ' ')
        self.out.append(html.escape(d, quote=False))

    def result(self):
        while self.stack:
            self._pop()
        return ''.join(self.out)


EMPTY = re.compile(r'<(p|div|b|strong|i|em|u|a|h[2-6]|li|ul|ol|blockquote|code|sup|sub|figure|figcaption)'
                   r'(?: [^>]*)?>\s*</\1>')


def sanitize(raw):
    s = San()
    s.feed(raw)
    s.close()
    h = s.result()
    for _ in range(10):
        n = EMPTY.sub('', h)
        if n == h:
            break
        h = n
    h = re.sub(r'(?:<br>\s*){3,}', '<br><br>', h)
    h = re.sub(r'^(?:\s|<br>)+', '', h)
    return h.strip()


def text_of(h):
    t = re.sub(r'<pre>.*?</pre>', ' ', h, flags=re.S)
    t = html.unescape(re.sub(r'<[^>]+>', ' ', t))
    return re.sub(r'\s+', ' ', t).strip()


def excerpt(t, n=210):
    if len(t) <= n:
        return t
    return t[:n].rsplit(' ', 1)[0].rstrip(',.;:—- ') + '…'


def thumb(src):
    if 'googleusercontent.com' in src:
        return re.sub(r'/(?:s\d+|w\d+-h\d+)(?:-[a-z0-9-]+)?/(?=[^/]+$)', '/w480/', src)
    return src


POSTS.sort(key=lambda p: p['dt'], reverse=True)
counts = collections.Counter(l for p in POSTS for l in p['labels'])
first_seen = {}
for p in POSTS:
    for l in p['labels']:
        first_seen.setdefault(l, len(first_seen))
LABELS = sorted(counts, key=lambda l: (-counts[l], first_seen[l]))
LSLUG = {l: slugify(l) for l in LABELS}
ABOUT = [p for p in POSTS if not p['labels']]
about = ABOUT[0] if ABOUT else None
if about:
    about['path'] = 'despre.html'

for p in POSTS:
    p['html'] = sanitize(p['content'])
    p['text'] = text_of(p['html'])
    p['excerpt'] = excerpt(p['text'])
    m = re.search(r'<img src="([^"]+)"', p['html'])
    p['thumb'] = thumb(html.unescape(m.group(1))) if m else ''

if len(sys.argv) > 3:
    # export pentru panoul de administrare (admin/index.html)
    dump = {'title': SITE, 'blog': BLOG, 'deleted': [], 'posts': []}
    for p in POSTS:
        rec = {'id': p['slug'], 'slug': p['slug'], 'bid': p['id'], 'title': p['title'], 'published': p['published'],
               'updated': p['updated'], 'labels': p['labels'], 'url': p['url'] or '',
               'html': p['html'].replace(ROOT, '%%ROOT%%')}
        if p is about:
            rec['page'] = 'despre'
        dump['posts'].append(rec)
    with open(sys.argv[3], 'w', encoding='utf-8') as f:
        json.dump(dump, f, ensure_ascii=False)
    print('export admin:', sys.argv[3], len(dump['posts']))
    sys.exit(0)

today = datetime.now(TZ)
STAMP = '%d %s %d' % (today.day, LUNI[today.month - 1], today.year)

# ---------- șabloane ----------
FAV = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' "
       "height='32' rx='7' fill='%230f6b4f'/%3E%3Cpath d='M8 10l6 6-6 6M16 22h8' stroke='%23fff' stroke-width='3' "
       "fill='none' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E")
DEF_DESC = 'Știri, tutoriale și resurse despre Linux și software open source, în limba română.'


def nr(n):
    return '%d %s' % (n, 'articol' if n == 1 else 'articole')


def page(title, body, root, active=None, desc=''):
    cur = ' aria-current="page"'
    nav = ['<a href="%sindex.html"%s>Acasă</a>' % (root, cur if active == '@home' else '')]
    for l in LABELS:
        nav.append('<a href="%s%s.html"%s>%s</a>' % (root, LSLUG[l], cur if active == l else '', esc(l)))
    full = SITE if title == SITE else '%s · %s' % (title, SITE)
    about_link = '<a href="%sdespre.html">Despre</a> · ' % root if about else ''
    out = '''<!doctype html>
<html lang="ro">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{desc}">
<link rel="icon" href="{fav}">
<link rel="stylesheet" href="{root}assets/style.css">
</head>
<body>
<a class="skip" href="#continut">Sari la conținut</a>
<header class="site-header">
  <div class="wrap bar">
    <a class="brand" href="{root}index.html"><span class="logo" aria-hidden="true">&gt;_</span><span>{site}</span></a>
    <button class="menu-btn" type="button" aria-expanded="false" aria-controls="meniu">Meniu</button>
  </div>
  <nav id="meniu" class="site-nav" aria-label="Etichete"><div class="wrap nav-in">{nav}</div></nav>
</header>
<main id="continut" class="wrap">
{body}
</main>
<footer class="site-footer"><div class="wrap">
  <p><strong>{site}</strong> — Învățăm Linux. Dezvoltăm competențe digitale. Construim încredere.</p>
  <p>{about_link}Conținut preluat de pe <a href="{blog}" target="_blank" rel="noopener">linuxforeducation.blogspot.com</a> · copie generată la {stamp} · {n} articole</p>
</div></footer>
<script src="{root}assets/site.js" defer></script>
</body>
</html>
'''.format(title=esc(full), desc=esc(desc or DEF_DESC), fav=FAV, root=root, site=esc(SITE), nav=''.join(nav),
           body=body, about_link=about_link, blog=BLOG, stamp=STAMP, n=len(POSTS))
    return out.replace(ROOT, root)


def chips(p, root):
    return ''.join('<a class="chip" href="%s%s.html">%s</a>' % (root, LSLUG[l], esc(l)) for l in p['labels'])


def card(p, root):
    if p['thumb']:
        img = '<img src="%s" alt="" loading="lazy" decoding="async">' % esc(p['thumb'])
    else:
        img = '<span class="ph" aria-hidden="true">&gt;_</span>'
    return '''<article class="card">
  <a class="card-img" href="{root}{path}" tabindex="-1" aria-hidden="true">{img}</a>
  <div class="card-body">
    <div class="meta"><time datetime="{iso}">{date}</time>{chips}</div>
    <h3><a href="{root}{path}">{title}</a></h3>
    <p>{ex}</p>
  </div>
</article>'''.format(root=root, path=p['path'], img=img, iso=p['iso'], date=p['date'], chips=chips(p, root),
                     title=esc(p['title']), ex=esc(p['excerpt']))


def write(rel, s):
    path = os.path.join(OUT, rel)
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(s)


# ---------- acasă ----------
labeled = [p for p in POSTS if p['labels']]
intro = esc(excerpt(about['text'], 400)) if about else DEF_DESC
cats = ''.join('<a class="cat" href="%s.html"><span class="cat-name">%s</span><span class="cat-n">%s</span></a>'
               % (LSLUG[l], esc(l), nr(counts[l])) for l in LABELS)
body = '''<section class="hero">
  <p class="eyebrow">Platformă educațională · Linux și open source</p>
  <h1>{site}</h1>
  <p class="lead">{intro}</p>
  {about}
</section>
<section>
  <h2 class="sec">Etichete</h2>
  <div class="cats">{cats}</div>
</section>
<section>
  <h2 class="sec">Cele mai noi articole</h2>
  <div class="grid">{cards}</div>
</section>'''.format(site=esc(SITE), intro=intro, cats=cats,
                     about='<p><a class="btn" href="despre.html">Despre proiect</a></p>' if about else '',
                     cards=''.join(card(p, '') for p in labeled[:12]))
write('index.html', page(SITE, body, '', '@home'))

# ---------- pagini de etichetă ----------
for l in LABELS:
    ps = [p for p in POSTS if l in p['labels']]
    items = []
    for p in ps:
        if p['thumb']:
            img = '<img class="pt" src="%s" alt="" loading="lazy" decoding="async">' % esc(p['thumb'])
        else:
            img = '<span class="pt ph" aria-hidden="true">&gt;_</span>'
        items.append('''<article class="post" id="{slug}">
<details>
<summary>
  {img}
  <span class="ps">
    <span class="meta"><time datetime="{iso}">{date}</time></span>
    <span class="pt-title" role="heading" aria-level="2">{title}</span>
    <span class="excerpt">{ex}</span>
    <span class="more">Citește articolul</span>
  </span>
</summary>
<div class="prose">
{html}
</div>
<p class="post-foot">{chips}<a href="{path}">Pagina articolului</a><a href="{url}" target="_blank" rel="noopener">Originalul pe blog</a></p>
</details>
</article>'''.format(slug=p['slug'], img=img, iso=p['iso'], date=p['date'], title=esc(p['title']),
                     ex=esc(p['excerpt']), html=p['html'], chips=chips(p, ''), path=p['path'], url=esc(p['url'])))
    body = '''<header class="page-head">
  <p class="eyebrow">Etichetă</p>
  <h1>{l}</h1>
  <p class="lead">{n}, de la cel mai nou la cel mai vechi. Apasă pe un titlu pentru a citi articolul complet.</p>
  <label class="filter"><span>Caută în {l}</span><input type="search" id="filtru" placeholder="Filtrează după titlu sau text…" autocomplete="off"></label>
</header>
<div class="posts" id="lista">
{items}
</div>
<p class="none" id="nimic" hidden>Niciun articol nu se potrivește căutării.</p>
<p class="more-wrap"><button class="btn" id="mai-multe" type="button" hidden>Arată mai multe</button></p>'''.format(
        l=esc(l), n=nr(len(ps)), items='\n'.join(items))
    write('%s.html' % LSLUG[l], page(l, body, '', l, 'Articole Linux for Education cu eticheta %s.' % l))

# ---------- pagini de articol ----------
for i, p in enumerate(labeled):
    newer = labeled[i - 1] if i > 0 else None
    older = labeled[i + 1] if i + 1 < len(labeled) else None
    pn = '<nav class="pn" aria-label="Alte articole">'
    pn += ('<a href="../%s"><small>← Mai nou</small>%s</a>' % (newer['path'], esc(newer['title']))) if newer else '<span></span>'
    pn += ('<a class="r" href="../%s"><small>Mai vechi →</small>%s</a>' % (older['path'], esc(older['title']))) if older else '<span></span>'
    pn += '</nav>'
    body = '''<article class="single">
<header class="page-head">
  <div class="meta"><time datetime="{iso}">{date}</time>{chips}</div>
  <h1>{title}</h1>
</header>
<div class="prose">
{html}
</div>
<p class="post-foot"><a href="{url}" target="_blank" rel="noopener">Originalul pe blog</a></p>
</article>
{pn}'''.format(iso=p['iso'], date=p['date'], chips=chips(p, '../'), title=esc(p['title']), html=p['html'],
               url=esc(p['url']), pn=pn)
    write(p['path'], page(p['title'], body, '../', p['labels'][0], p['excerpt']))

if about:
    body = '''<article class="single">
<header class="page-head"><h1>{title}</h1></header>
<div class="prose">
{html}
</div>
</article>'''.format(title=esc(about['title']), html=about['html'])
    write('despre.html', page('Despre', body, '', None, about['excerpt']))

# ---------- resurse ----------
write('assets/style.css', r''':root{--bg:#f6f4ee;--surface:#fffdf8;--ink:#1c2420;--muted:#5d6861;--line:#dedacd;--accent:#0f6b4f;--accent-ink:#fff;--accent-soft:#e2efe8;--code:#efece2;--radius:10px;--w:1120px}
@media (prefers-color-scheme:dark){:root{--bg:#121614;--surface:#1a201d;--ink:#e8ece9;--muted:#9aa69f;--line:#2c3530;--accent:#5fd0a4;--accent-ink:#0b1f17;--accent-soft:#1d3229;--code:#222a26}}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:17px/1.65 system-ui,-apple-system,"Segoe UI",Roboto,"Noto Sans",sans-serif}
a{color:var(--accent);text-underline-offset:.18em}
a:hover{text-decoration-thickness:2px}
:focus-visible{outline:3px solid var(--accent);outline-offset:2px;border-radius:4px}
[hidden]{display:none!important}
.wrap{max-width:var(--w);margin:0 auto;padding:0 20px}
.skip{position:absolute;left:-999px}.skip:focus{left:12px;top:12px;background:var(--surface);padding:8px 12px;z-index:9}
.site-header{background:var(--surface);border-bottom:1px solid var(--line);position:sticky;top:0;z-index:5}
.bar{display:flex;align-items:center;justify-content:space-between;padding-top:12px;padding-bottom:12px}
.brand{display:flex;align-items:center;gap:10px;font-weight:700;font-size:1.15rem;color:var(--ink);text-decoration:none;letter-spacing:-.01em}
.logo{display:grid;place-items:center;width:34px;height:34px;border-radius:8px;background:var(--accent);color:var(--accent-ink);font:700 14px/1 ui-monospace,Consolas,monospace}
.menu-btn{display:none;font:inherit;font-size:.95rem;background:none;border:1px solid var(--line);color:var(--ink);border-radius:8px;padding:6px 14px;cursor:pointer}
.site-nav{border-top:1px solid var(--line)}
.nav-in{display:flex;flex-wrap:wrap;gap:2px 4px;padding-top:6px;padding-bottom:6px}
.site-nav a{padding:6px 12px;border-radius:999px;color:var(--muted);text-decoration:none;font-size:.95rem;font-weight:500;white-space:nowrap}
.site-nav a:hover{color:var(--ink);background:var(--accent-soft)}
.site-nav a[aria-current]{background:var(--accent);color:var(--accent-ink)}
main{padding-top:36px;padding-bottom:64px;min-height:60vh}
h1,h2,h3,h4{line-height:1.2;letter-spacing:-.015em;text-wrap:balance}
h1{font-size:clamp(1.9rem,4.2vw,2.8rem);margin:.2em 0 .4em}
.eyebrow{margin:0;color:var(--accent);font-size:.8rem;font-weight:700;letter-spacing:.09em;text-transform:uppercase}
.lead{font-size:1.1rem;color:var(--muted);max-width:68ch;margin:.4em 0 1em}
.hero{padding:24px 0 12px}
.sec{font-size:1.35rem;margin:44px 0 16px;padding-top:20px;border-top:1px solid var(--line)}
.btn{display:inline-block;font:inherit;font-weight:600;font-size:.95rem;background:var(--accent);color:var(--accent-ink);border:0;border-radius:999px;padding:9px 20px;text-decoration:none;cursor:pointer}
.cats{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:12px}
.cat{display:flex;flex-direction:column;gap:2px;padding:14px 16px;background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);text-decoration:none;color:var(--ink)}
.cat:hover{border-color:var(--accent)}
.cat-name{font-weight:700}.cat-n{color:var(--muted);font-size:.88rem}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:20px}
.card{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);overflow:hidden;display:flex;flex-direction:column}
.card-img{display:block;aspect-ratio:16/9;background:var(--accent-soft)}
.card-img img{width:100%;height:100%;object-fit:cover;display:block}
.ph{display:grid;place-items:center;width:100%;height:100%;color:var(--accent);font:700 1.4rem ui-monospace,Consolas,monospace;background:var(--accent-soft)}
.card-body{padding:14px 16px 16px}
.card h3{font-size:1.05rem;margin:6px 0}
.card h3 a{color:var(--ink);text-decoration:none}.card h3 a:hover{color:var(--accent)}
.card p{margin:0;color:var(--muted);font-size:.92rem;line-height:1.5}
.meta{display:flex;flex-wrap:wrap;align-items:center;gap:6px 10px;color:var(--muted);font-size:.84rem}
.chip{display:inline-block;padding:1px 10px;border-radius:999px;background:var(--accent-soft);color:var(--accent);font-size:.8rem;font-weight:600;text-decoration:none}
.page-head{margin-bottom:24px}
.filter{display:block;max-width:460px;margin-top:18px}
.filter span{display:block;font-size:.85rem;font-weight:600;margin-bottom:4px}
.filter input{width:100%;font:inherit;padding:10px 14px;border:1px solid var(--line);border-radius:8px;background:var(--surface);color:var(--ink)}
.posts{display:flex;flex-direction:column;gap:12px}
.post{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);scroll-margin-top:130px}
.post summary{display:flex;gap:16px;padding:14px;cursor:pointer;list-style:none;border-radius:var(--radius)}
.post summary::-webkit-details-marker{display:none}
.pt{flex:none;width:168px;aspect-ratio:16/9;height:auto;align-self:flex-start;object-fit:cover;border-radius:6px;background:var(--accent-soft)}
.ps{display:flex;flex-direction:column;gap:4px;min-width:0}
.pt-title{font-weight:700;font-size:1.12rem;line-height:1.3;letter-spacing:-.01em}
.post summary:hover .pt-title{color:var(--accent)}
.excerpt{color:var(--muted);font-size:.93rem;line-height:1.5}
.more{color:var(--accent);font-size:.88rem;font-weight:600}
.more::after{content:" ↓"}
details[open] .excerpt{display:none}
details[open] .more{font-size:0}
details[open] .more::after{content:"Închide ↑";font-size:.88rem}
details[open] summary{border-bottom:1px solid var(--line);border-radius:var(--radius) var(--radius) 0 0}
.post .prose{padding:18px 22px 0;max-width:820px}
.post-foot{display:flex;flex-wrap:wrap;gap:8px 16px;align-items:center;font-size:.9rem;margin:28px 0 0;padding:14px 0;border-top:1px solid var(--line)}
.post .post-foot{margin:20px 22px 0}
.none{color:var(--muted)}
.more-wrap{text-align:center;margin-top:24px}
.single{max-width:780px;margin:0 auto}
.prose{font-size:1.04rem;overflow-wrap:break-word}
.prose h2{font-size:1.5rem;margin:1.6em 0 .5em}
.prose h3{font-size:1.25rem;margin:1.5em 0 .4em}
.prose h4{font-size:1.08rem;margin:1.3em 0 .3em}
.prose p{margin:0 0 1em}
.prose img{max-width:100%;height:auto;border-radius:8px;display:block;margin:10px auto}
.prose ul,.prose ol{padding-left:1.4em;margin:0 0 1em}
.prose li{margin:.3em 0}
.prose li>p{margin:0 0 .4em}
.prose pre{background:var(--code);border:1px solid var(--line);border-radius:8px;padding:14px 16px;overflow-x:auto;font:.9rem/1.55 ui-monospace,"Cascadia Code",Consolas,monospace;margin:0 0 1em}
.prose code{background:var(--code);border-radius:4px;padding:.1em .35em;font:.92em ui-monospace,"Cascadia Code",Consolas,monospace}
.prose pre code{background:none;padding:0;font-size:inherit}
.prose blockquote{margin:0 0 1em;padding:4px 0 4px 16px;border-left:3px solid var(--accent);color:var(--muted)}
.prose hr{border:0;border-top:1px solid var(--line);margin:1.8em 0}
.tw{overflow-x:auto;margin:0 0 1em}
.prose table{border-collapse:collapse;width:100%;font-size:.94rem}
.prose th,.prose td{border:1px solid var(--line);padding:8px 10px;text-align:left;vertical-align:top}
.prose thead td,.prose th{background:var(--accent-soft);font-weight:700}
.prose figure{margin:0 0 1em}.prose figcaption{color:var(--muted);font-size:.86rem;text-align:center}
.pn{max-width:780px;margin:28px auto 0;display:grid;grid-template-columns:1fr 1fr;gap:14px}
.pn a{display:block;padding:12px 14px;background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);text-decoration:none;color:var(--ink);font-size:.93rem;font-weight:600;line-height:1.35}
.pn a:hover{border-color:var(--accent)}
.pn small{display:block;color:var(--muted);font-weight:500;margin-bottom:3px}
.pn .r{text-align:right}
.site-footer{border-top:1px solid var(--line);background:var(--surface);padding:24px 0;color:var(--muted);font-size:.9rem}
.site-footer p{margin:.3em 0}
@media (max-width:760px){
 body{font-size:16px}
 .wrap{padding:0 16px}
 .menu-btn{display:block}
 .site-nav{display:none}
 .site-nav.open{display:block}
 .nav-in{flex-direction:column;gap:2px;padding-bottom:12px}
 .site-nav a{border-radius:8px;padding:9px 12px}
 .post summary{flex-direction:column;gap:10px}
 .pt{width:100%}
 .post .prose{padding:14px 14px 0}.post .post-foot{margin:16px 14px 0}
 .pn{grid-template-columns:1fr}.pn .r{text-align:left}
 .post{scroll-margin-top:70px}
}
''')
write('assets/site.js', r'''(function(){
  var b=document.querySelector('.menu-btn'),n=document.getElementById('meniu');
  if(b&&n)b.addEventListener('click',function(){var o=n.classList.toggle('open');b.setAttribute('aria-expanded',o)});
  var list=document.getElementById('lista');if(!list)return;
  var posts=[].slice.call(list.querySelectorAll('.post')),btn=document.getElementById('mai-multe'),
      inp=document.getElementById('filtru'),none=document.getElementById('nimic'),STEP=20,limit=STEP;
  function fold(s){return s.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g,'')}
  var idx=posts.map(function(p){return fold(p.querySelector('summary').textContent)});
  function render(){
    var q=fold(inp.value.trim()),shown=0,match=0;
    posts.forEach(function(p,i){
      var ok=!q||idx[i].indexOf(q)>-1; if(ok)match++;
      var vis=ok&&(q||match<=limit); p.hidden=!vis; if(vis)shown++;
    });
    none.hidden=match>0;
    var left=match-shown; btn.hidden=left<=0;
    btn.textContent='Arată mai multe ('+left+' rămase)';
  }
  btn.addEventListener('click',function(){limit+=STEP;render()});
  inp.addEventListener('input',render);
  function openHash(){
    var id=decodeURIComponent(location.hash.slice(1));if(!id)return;
    var el=document.getElementById(id);if(!el||!el.classList.contains('post'))return;
    limit=Math.max(limit,posts.indexOf(el)+1);render();
    el.querySelector('details').open=true;el.scrollIntoView();
  }
  render();openHash();window.addEventListener('hashchange',openHash);
})();
''')
print('etichete:', [(l, LSLUG[l], counts[l]) for l in LABELS])
print('articole cu etichetă:', len(labeled), '| despre:', bool(about), '| total:', len(POSTS))
