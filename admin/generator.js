/* Generatorul site-ului Linux for Education.
   Primește datele (_sursa/site-data.json) și întoarce toate paginile HTML ca text.
   Rulează atât în browser (panoul de administrare), cât și în Node. */
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.LFE = factory();
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';
  var TOKEN = '%%ROOT%%';
  var LUNI = ['ianuarie', 'februarie', 'martie', 'aprilie', 'mai', 'iunie', 'iulie', 'august',
    'septembrie', 'octombrie', 'noiembrie', 'decembrie'];
  var RESERVED = { index: 1, despre: 1, admin: 1, articole: 1, assets: 1, imagini: 1 };
  var DEF_DESC = 'Știri, tutoriale și resurse despre Linux și software open source, în limba română.';
  var FAV = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' " +
    "height='32' rx='7' fill='%230f6b4f'/%3E%3Cpath d='M8 10l6 6-6 6M16 22h8' stroke='%23fff' stroke-width='3' " +
    "fill='none' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E";
  var fmt = new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Bucharest', year: 'numeric', month: '2-digit', day: '2-digit' });

  function slugify(s) {
    s = String(s).replace(/[șş]/g, 's').replace(/[țţ]/g, 't').replace(/[ȘŞ]/g, 'S').replace(/[ȚŢ]/g, 'T');
    return s.normalize('NFKD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
  }
  function esc(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#x27;');
  }
  function unesc(s) {
    return s.replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').replace(/&#x27;/g, "'").replace(/&amp;/g, '&');
  }
  function dateParts(iso) {
    var o = {};
    fmt.formatToParts(new Date(iso)).forEach(function (p) { o[p.type] = p.value; });
    return { y: +o.year, m: +o.month, d: +o.day, iso: o.year + '-' + o.month + '-' + o.day };
  }
  function textOf(h) {
    return unesc(h.replace(/<pre>[\s\S]*?<\/pre>/g, ' ').replace(/<[^>]+>/g, ' ')).replace(/\s+/g, ' ').trim();
  }
  function excerpt(t, n) {
    n = n || 210;
    if (t.length <= n) return t;
    var cut = t.slice(0, n), i = cut.lastIndexOf(' ');
    if (i >= 0) cut = cut.slice(0, i);
    return cut.replace(/[,.;:—\- ]+$/, '') + '…';
  }
  function thumb(src) {
    if (src.indexOf('googleusercontent.com') > -1) return src.replace(/\/(?:s\d+|w\d+-h\d+)(?:-[a-z0-9-]+)?\/(?=[^\/]+$)/, '/w480/');
    return src;
  }
  function nr(n) { return n + ' ' + (n === 1 ? 'articol' : 'articole'); }

  function build(data) {
    var SITE = data.title || 'Linux for Education', BLOG = data.blog || '';
    var posts = data.posts.map(function (p) {
      var d = dateParts(p.published), html = p.html || '';
      // rândul „Sursa articolului: …” nu se afișează pe site (rămâne în date)
      html = html.replace(/<p><b>Sursa articolului:<\/b>[\s\S]*?<\/p>/g, '');
      // la fel titlul „📌 Surse și detalii:” și rândul „Articol original: …” din lista de sub el
      html = html.replace(/<h3>📌\s*Surse și detalii:<\/h3>/g, '')
        .replace(/<li><strong>Articol original<\/strong>:[\s\S]*?<\/li>/g, '').replace(/<ul>\s*<\/ul>/g, '');
      var text = textOf(html), m = /<img src="([^"]+)"/.exec(html);
      return {
        // titluri în aceeași formă: fără emoji la început și fără „!” la final
        src: p, title: (String(p.title).replace(/^[^\p{L}\p{N}„"(]+/u, '').replace(/\s*!+$/, '').trim() || p.title), labels: p.page ? [] : (p.labels || []), url: p.url || '', slug: p.slug, html: html, page: p.page || '',
        ts: Date.parse(p.published), iso: d.iso, date: d.d + ' ' + LUNI[d.m - 1] + ' ' + d.y,
        path: p.page === 'despre' ? 'despre.html' : 'articole/' + p.slug + '.html',
        text: text, excerpt: excerpt(text), thumb: m ? thumb(unesc(m[1])) : ''
      };
    });
    posts.sort(function (a, b) { return b.ts - a.ts; });
    var about = posts.filter(function (p) { return p.page === 'despre'; })[0] || null;
    var labeled = posts.filter(function (p) { return !p.page && p.labels.length; });
    var counts = {}, first = {}, k = 0;
    labeled.forEach(function (p) { p.labels.forEach(function (l) { counts[l] = (counts[l] || 0) + 1; if (!(l in first)) first[l] = k++; }); });
    // grupuri de meniu (submeniuri): etichetele lor apar mereu, chiar și fără articole
    var GROUPS = (data.groups || []).map(function (g) { return { name: g.name, labels: (g.labels || []).slice() }; });
    var inGroup = {};
    GROUPS.forEach(function (g) { g.labels.forEach(function (l) { inGroup[l] = g; if (!(l in counts)) counts[l] = 0; }); });
    var TOP = Object.keys(counts).filter(function (l) { return !inGroup[l]; })
      .sort(function (a, b) { return counts[b] - counts[a] || first[a] - first[b]; });
    var LABELS = TOP.slice();
    GROUPS.forEach(function (g) { LABELS = LABELS.concat(g.labels); });
    var LSLUG = {}, usedSlugs = {};
    function uniq(s) {
      s = s || 'eticheta';
      if (RESERVED[s]) s = 'eticheta-' + s;
      while (usedSlugs[s]) s += '-2';
      usedSlugs[s] = 1; return s;
    }
    LABELS.forEach(function (l) { LSLUG[l] = uniq(slugify(l)); });
    GROUPS.forEach(function (g) {
      g.slug = uniq(slugify(g.name));
      g.count = g.labels.reduce(function (n, l) { return n + counts[l]; }, 0);
    });
    var files = {};
    var SOCIAL = (data.social || []).map(function (s) {
      return '<a href="' + esc(s.url) + '" target="_blank" rel="me noopener">' + esc(s.name) + '</a>';
    });

    function page(title, body, root, active, desc) {
      var cur = ' aria-current="page"';
      var nav = '<a href="' + root + 'index.html"' + (active === '@home' ? cur : '') + '>Acasă</a>';
      TOP.forEach(function (l) { nav += '<a href="' + root + LSLUG[l] + '.html"' + (active === l ? cur : '') + '>' + esc(l) + '</a>'; });
      GROUPS.forEach(function (g) {
        var here = active === '@group:' + g.name, inside = g.labels.indexOf(active) > -1;
        nav += '<div class="dd"><a class="dd-top' + (inside ? ' on' : '') + '" href="' + root + g.slug + '.html"' + (here ? cur : '') + '>' +
          esc(g.name) + ' <span aria-hidden="true">▾</span></a><div class="dd-menu">' +
          g.labels.map(function (l) { return '<a href="' + root + LSLUG[l] + '.html"' + (active === l ? cur : '') + '>' + esc(l) + '</a>'; }).join('') +
          '</div></div>';
      });
      var full = title === SITE ? SITE : title + ' · ' + SITE;
      var out = '<!doctype html>\n<html lang="ro">\n<head>\n<meta charset="utf-8">\n' +
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n' +
        '<title>' + esc(full) + '</title>\n' +
        '<meta name="description" content="' + esc(desc || DEF_DESC) + '">\n' +
        '<link rel="icon" href="' + FAV + '">\n' +
        '<link rel="stylesheet" href="' + root + 'assets/style.css">\n</head>\n<body>\n' +
        '<a class="skip" href="#continut">Sari la conținut</a>\n<header class="site-header">\n  <div class="wrap bar">\n' +
        '    <a class="brand" href="' + root + 'index.html"><span class="logo" aria-hidden="true">&gt;_</span><span>' + esc(SITE) + '</span></a>\n' +
        (SOCIAL.length ? '    <div class="social">' + SOCIAL.join('') + '</div>\n' : '') +
        '    <button class="menu-btn" type="button" aria-expanded="false" aria-controls="meniu">Meniu</button>\n  </div>\n' +
        '  <nav id="meniu" class="site-nav" aria-label="Etichete"><div class="wrap nav-in">' + nav + '</div></nav>\n</header>\n' +
        '<main id="continut" class="wrap">\n' + body + '\n</main>\n' +
        '<footer class="site-footer"><div class="wrap">\n' +
        '  <p><strong>' + esc(SITE) + '</strong> — Învățăm Linux. Dezvoltăm competențe digitale. Construim încredere.</p>\n' +
        (SOCIAL.length ? '  <p>Urmărește-ne: ' + SOCIAL.join(' · ') + '</p>\n' : '') +
        '</div></footer>\n<script src="' + root + 'assets/site.js" defer></script>\n</body>\n</html>\n';
      return out.split(TOKEN).join(root);
    }
    function chips(p, root) {
      return p.labels.map(function (l) { return '<a class="chip" href="' + root + LSLUG[l] + '.html">' + esc(l) + '</a>'; }).join('');
    }
    function time(p) { return '<time datetime="' + p.iso + '">' + p.date + '</time>'; }
    function card(p, root) {
      var img = p.thumb ? '<img src="' + esc(p.thumb) + '" alt="" loading="lazy" decoding="async">' : '<span class="ph" aria-hidden="true">&gt;_</span>';
      return '<article class="card">\n  <a class="card-img" href="' + root + p.path + '" tabindex="-1" aria-hidden="true">' + img + '</a>\n' +
        '  <div class="card-body">\n    <div class="meta">' + time(p) + chips(p, root) + '</div>\n' +
        '    <h3><a href="' + root + p.path + '">' + esc(p.title) + '</a></h3>\n    <p>' + esc(p.excerpt) + '</p>\n  </div>\n</article>';
    }
    function orig(p) { return ''; }

    // acasă
    function cat(href, name, note) {
      return '<a class="cat" href="' + href + '.html"><span class="cat-name">' + esc(name) + '</span><span class="cat-n">' + note + '</span></a>';
    }
    var cats = TOP.map(function (l) { return cat(LSLUG[l], l, nr(counts[l])); }).join('') +
      GROUPS.map(function (g) { return cat(g.slug, g.name, g.labels.length + ' categorii'); }).join('');

    // pagini de grup (de ex. Tutoriale)
    GROUPS.forEach(function (g) {
      files[g.slug + '.html'] = page(g.name,
        '<header class="page-head">\n  <p class="eyebrow">Secțiune</p>\n  <h1>' + esc(g.name) + '</h1>\n' +
        '  <p class="lead">Alege o categorie.</p>\n</header>\n<div class="cats">' +
        g.labels.map(function (l) { return cat(LSLUG[l], l, counts[l] ? nr(counts[l]) : 'Niciun articol încă'); }).join('') + '</div>',
        '', '@group:' + g.name, g.name + ' Linux for Education.');
    });
    files['index.html'] = page(SITE,
      '<section class="hero">\n  <p class="eyebrow">Platformă educațională · Linux și open source</p>\n  <h1>' + esc(SITE) + '</h1>\n' +
      '  <p class="lead">' + (about ? esc(excerpt(about.text, 400)) : DEF_DESC) + '</p>\n' +
      (about ? '  <p><a class="btn" href="despre.html">Despre proiect</a></p>\n' : '') + '</section>\n' +
      '<section>\n  <h2 class="sec">Etichete</h2>\n  <div class="cats">' + cats + '</div>\n</section>\n' +
      '<section>\n  <h2 class="sec">Cele mai noi articole</h2>\n  <div class="grid">' +
      labeled.slice(0, 3).map(function (p) { return card(p, ''); }).join('') + '</div>\n</section>', '', '@home');

    // pagini de etichetă
    LABELS.forEach(function (l) {
      var ps = labeled.filter(function (p) { return p.labels.indexOf(l) > -1; });
      var items = ps.map(function (p) {
        var img = p.thumb ? '<img class="pt" src="' + esc(p.thumb) + '" alt="" loading="lazy" decoding="async">' : '<span class="pt ph" aria-hidden="true">&gt;_</span>';
        return '<article class="post" id="' + p.slug + '">\n<details>\n<summary>\n  ' + img + '\n  <span class="ps">\n' +
          '    <span class="meta">' + time(p) + '</span>\n' +
          '    <span class="pt-title" role="heading" aria-level="2">' + esc(p.title) + '</span>\n' +
          '    <span class="excerpt">' + esc(p.excerpt) + '</span>\n    <span class="more">Citește articolul</span>\n  </span>\n</summary>\n' +
          '<div class="prose">\n' + p.html + '\n</div>\n' +
          '<p class="post-foot">' + chips(p, '') + '<a href="' + p.path + '">Pagina articolului</a>' + orig(p) + '</p>\n</details>\n</article>';
      }).join('\n');
      var g = inGroup[l], eyebrow = g ? '<a href="' + g.slug + '.html">' + esc(g.name) + '</a>' : 'Etichetă';
      if (!ps.length) {
        files[LSLUG[l] + '.html'] = page(l,
          '<header class="page-head">\n  <p class="eyebrow">' + eyebrow + '</p>\n  <h1>' + esc(l) + '</h1>\n' +
          '  <p class="lead">Niciun articol încă. Revino în curând.</p>\n</header>', '', l, 'Articole Linux for Education cu eticheta ' + l + '.');
        return;
      }
      files[LSLUG[l] + '.html'] = page(l,
        '<header class="page-head">\n  <p class="eyebrow">' + eyebrow + '</p>\n  <h1>' + esc(l) + '</h1>\n' +
        '  <p class="lead">' + nr(ps.length) + ', de la cel mai nou la cel mai vechi. Apasă pe un titlu pentru a citi articolul complet.</p>\n' +
        '  <label class="filter"><span>Caută în ' + esc(l) + '</span><input type="search" id="filtru" placeholder="Filtrează după titlu sau text…" autocomplete="off"></label>\n' +
        '</header>\n<div class="posts" id="lista">\n' + items + '\n</div>\n' +
        '<p class="none" id="nimic" hidden>Niciun articol nu se potrivește căutării.</p>\n' +
        '<p class="more-wrap"><button class="btn" id="mai-multe" type="button" hidden>Arată mai multe</button></p>',
        '', l, 'Articole Linux for Education cu eticheta ' + l + '.');
    });

    // pagini de articol
    labeled.forEach(function (p, i) {
      var newer = labeled[i - 1], older = labeled[i + 1];
      var pn = '<nav class="pn" aria-label="Alte articole">' +
        (newer ? '<a href="../' + newer.path + '"><small>← Mai nou</small>' + esc(newer.title) + '</a>' : '<span></span>') +
        (older ? '<a class="r" href="../' + older.path + '"><small>Mai vechi →</small>' + esc(older.title) + '</a>' : '<span></span>') + '</nav>';
      var o = orig(p);
      files[p.path] = page(p.title,
        '<article class="single">\n<header class="page-head">\n  <div class="meta">' + time(p) + chips(p, '../') + '</div>\n' +
        '  <h1>' + esc(p.title) + '</h1>\n</header>\n<div class="prose">\n' + p.html + '\n</div>\n' +
        (o ? '<p class="post-foot">' + o + '</p>\n' : '') + '</article>\n' + pn, '../', p.labels[0], p.excerpt);
    });

    if (about) {
      files['despre.html'] = page('Despre',
        '<article class="single">\n<header class="page-head"><h1>' + esc(about.title) + '</h1></header>\n<div class="prose">\n' +
        about.html + '\n</div>\n</article>', '', null, about.excerpt);
    }
    return { files: files, labels: LABELS.map(function (l) { return { name: l, slug: LSLUG[l], count: counts[l] }; }) };
  }

  return { build: build, slugify: slugify, esc: esc, dateParts: dateParts, TOKEN: TOKEN };
});
