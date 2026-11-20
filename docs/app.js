(function () {
  const R = window.RESULTS_2024;
  const NAT = window.NATIONAL_2024;
  const SHAPES = window.US_STATES;
  const N = window.NOWCAST;
  // The final forecast shows from 9 AM Eastern on August 6, 2028. That morning's run may save it a little
  // earlier or later; until 9 AM the page keeps showing the countdown.
  const FORECAST_DATE = new Date('2028-08-06T09:00:00-04:00');
  if (window.FORECAST && new Date() < FORECAST_DATE) window.FORECAST = null;
  const byAbbr = Object.fromEntries(R.map(r => [r.abbr, r]));
  const natActual = 100 * NAT.dem / (NAT.dem + NAT.rep);
  // The forecasts the authors published for 2024: the approval and fundamentals model's (docs/data.js) and, in
  // docs/backtest2024.js, DeSart's long-range forecast and the average of the two, which nobody published.
  const BT = window.BACKTEST_2024 || null, DS = BT && BT.desartPub ? BT.desartPub : null;
  R.forEach(r => { r.pub = { fc: r.fc, lo: r.lo, hi: r.hi, pDem: r.pDem, rating: r.rating }; });
  NAT.pub = { fc: NAT.fc, pDemWin: NAT.pDemWin };
  const TOSS = '#d9b23f';   // toss-ups in the Nowcast are gold, not the color of whoever is a hair ahead
  const isToss = p => Math.max(p, 1 - p) <= 0.55;
  // The 2028 map is colored by rating: darker means safer, and the light shades and gold mark the close states.
  const RATE_COLOR = { SD: '#2e64b0', LD: '#4f8de0', TD: '#a9c8f0', TOSS: TOSS, TR: '#f2aaa1', LR: '#d8665b', SR: '#a63f37' };
  // Any fill light enough to need dark text: '#rrggbb' or 'rgb(r,g,b)', by relative luminance.
  const lumOf = c => {
    const v = c[0] === '#' ? [1, 3, 5].map(i => parseInt(c.slice(i, i + 2), 16)) : (c.match(/\d+/g) || []).slice(0, 3).map(Number);
    const L = v.map(x => { x /= 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); });
    return 0.2126 * L[0] + 0.7152 * L[1] + 0.0722 * L[2];
  };
  const isLight = c => !!c && lumOf(c) > 0.4;
  // On the state line-ups a label is black wherever black reads better than white on that fill. The two cross
  // at a luminance of 0.179, where both still clear 4.5 to 1.
  const darkInk = c => !!c && lumOf(c) > 0.179;
  // The race in plain words, by the same thresholds as the state ratings.
  const VERDICT = { SD: 'solidly Democratic', LD: 'likely Democratic', TD: 'leaning Democratic', TOSS: 'a toss-up', TR: 'leaning Republican', LR: 'likely Republican', SR: 'solidly Republican' };
  const rateOf = p => window.SPASE.rate(p);
  // The leader's win chance, shown on every state that is not Solid.
  const chance = p => { const r = rateOf(p); return r[0] === 'S' ? '' : `${p >= 0.5 ? 'D' : 'R'} ${Math.round(100 * Math.max(p, 1 - p))}%`; };
  const RATING = { SR: 'Solid R', LR: 'Likely R', TR: 'Lean R', TD: 'Lean D', LD: 'Likely D', SD: 'Solid D', TOSS: 'Toss-up' };
  const SMALL = ['VT', 'NH', 'MA', 'RI', 'CT', 'NJ', 'DE', 'MD', 'DC'];
  const DISTRICTS = ['ME1', 'ME2', 'NE1', 'NE2', 'NE3'];
  const LABEL_NUDGE = { FL: [14, 6], MI: [8, 14], LA: [-8, 0], KY: [6, 2], CA: [-8, 0], ID: [0, 14], MN: [-4, 6], TX: [6, 0], NY: [6, 0], VA: [8, 2], WV: [-2, 4] };
  const OFFSHORE = { HI: [343, 589] };   // Hawaii's islands are too small to hold a label, so it sits just beside the Big Island
  const STATE_LIST = R.filter(r => r.abbr.length === 2).map(r => [r.abbr, r.name]).sort((a, b) => a[1].localeCompare(b[1]));
  const dname = a => a.length === 3 ? `${a.slice(0, 2)}-${a[2]}` : a;
  const fmt = (x, d = 1) => x.toFixed(d) + '%';
  const sgn = (x, d = 2) => (x > 0 ? '+' : x < 0 ? '−' : '') + Math.abs(x).toFixed(d);
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

  // ---------- color ----------
  const hex = h => [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16));
  const mix = (a, b, t) => { const A = hex(a), B = hex(b); return `rgb(${A.map((v, i) => Math.round(v + (B[i] - v) * t)).join(',')})`; };
  function shareColor(s) {
    const m = s - 50, t = Math.pow(Math.min(Math.abs(m) / 15, 1), 0.6);   // light near 50%, full colour by a 15-point margin
    return m >= 0 ? mix('#c9d9f1', '#2e64b0', t) : mix('#f4cbc5', '#a63f37', t);
  }
  const errColor = e => mix('#172131', '#f0a35e', Math.pow(Math.min(Math.abs(e) / 5, 1), 0.85));
  const greyColor = () => '#1a2333';
  function ramp(el, kind) {
    if (kind === 'error') el.innerHTML = `<span>0</span><i style="background:linear-gradient(90deg,${errColor(0)},${errColor(2.5)},${errColor(5)})"></i><span>5+ pts</span>`;
    else if (kind === 'none') el.innerHTML = '';
    else if (kind === 'nowcast') el.innerHTML = `<span class="rate-keys">${['SD', 'LD', 'TD', 'TOSS', 'TR', 'LR', 'SR'].map(k => `<span class="rk"><i style="background:${RATE_COLOR[k]}"></i>${RATING[k]}</span>`).join('')}</span><span class="rate-note">Percent: the leader's chance of winning the state</span>`;
    else el.innerHTML = `<span class="r-ink">R</span><i style="background:linear-gradient(90deg,${shareColor(28)},${shareColor(44)},${shareColor(50)},${shareColor(56)},${shareColor(72)})"></i><span class="d-ink">D</span><span style="margin-left:4px">Democratic share</span>`;
  }

  // ---------- strip ----------
  function strip(o, lo = 30, hi = 70) {
    const p = v => Math.max(0, Math.min(100, (v - lo) / (hi - lo) * 100));
    const clip = v => v < lo || v > hi;
    let h = '<div class="track"></div><div class="mid"></div>';
    if (o.lo != null) h += `<div class="band" style="left:${p(o.lo)}%;width:${Math.max(1, p(o.hi) - p(o.lo))}%"></div>`;
    if (o.f != null && o.a != null) h += `<div class="link" style="left:${Math.min(p(o.f), p(o.a))}%;width:${Math.abs(p(o.f) - p(o.a))}%"></div>`;
    if (o.f != null) h += `<div class="dot f${clip(o.f) ? ' clip' : ''}" style="left:${p(o.f)}%" title="Forecast ${fmt(o.f, 2)}"></div>`;
    if (o.a != null) h += `<div class="dot a${clip(o.a) ? ' clip' : ''}" style="left:${p(o.a)}%" title="Result ${fmt(o.a, 2)}"></div>`;
    return h;
  }

  // ---------- tipping-point chart ----------
  // items: [{abbr, ev, share}] for every state and district. Sorted most Democratic first.
  function tippingOf(items) {
    const rows = items.filter(i => i.ev > 0).slice().sort((a, b) => b.share - a.share);
    let cum = 0, tp = null;
    rows.forEach(r => { r.before = cum; cum += r.ev; r.after = cum; if (!tp && cum >= 270) tp = r; });
    return { rows, tp };
  }
  // What the colors of a line-up mean, how to read a state, and where to go next.
  const snakeKey = kind => `<span class="ramp">${kind === 'rate'
    ? `<span class="rate-keys">${[['Solid', 'SD', 'SR'], ['Likely', 'LD', 'LR'], ['Lean', 'TD', 'TR']].map(([n, d, r]) => `<span class="rk"><i style="background:${RATE_COLOR[d]}"></i><i style="background:${RATE_COLOR[r]}"></i>${n}</span>`).join('')}<span class="rk"><i style="background:${TOSS}"></i>Toss-up</span></span>`
    : `<span class="d-ink">D</span><i style="background:linear-gradient(90deg,${shareColor(72)},${shareColor(56)},${shareColor(50)},${shareColor(44)},${shareColor(28)})"></i><span class="r-ink">R</span><span>Shaded by share of the vote</span>`}</span>
    <span class="hint"><span class="h-hover">Point at a state for its numbers.</span><span class="h-touch">Slide along the bar to read each state.</span><span class="h-tap">Tap a state for its numbers.</span></span>`;
  // ---------- naming every state ----------
  // A state wide enough carries its own name. One too narrow gets its name above the bar, joined to it by a thin
  // line. The names sit in up to three rows, and a line that climbs past a row is given a gap in that row, so no
  // line crosses a name. Where the bar is too short for that (a phone), every state is listed under the bar
  // instead, in the same order and colors.
  const NAME = { h: 13, gap: 3, lead: 16, stub: 2, fit: 4, pad: 4, pass: 5, rows: 3, fan: 20, far: 40, wide: '(min-width: 1000px)' };
  let inkW = {}, inkCtx = null;
  const inkFont = () => `600 11px ${getComputedStyle(document.documentElement).getPropertyValue('--font-num')}`;
  const textW = t => {
    if (inkW[t] === undefined) {
      inkCtx = inkCtx || document.createElement('canvas').getContext('2d');
      inkCtx.font = inkFont();
      inkW[t] = inkCtx.measureText(t).width;
    }
    return inkW[t];
  };
  // Things in a row that each want to sit at t[i] and each need f[i] of room: the nearest places where none
  // overlap, kept between lo and hi. (Isotonic regression on the places, less the room taken up before them.)
  function spread(t, f, lo, hi) {
    const n = t.length, off = [0], pool = [], z = [];
    if (!n) return z;
    for (let i = 1; i < n; i++) off[i] = off[i - 1] + (f[i - 1] + f[i]) / 2;
    for (let i = 0; i < n; i++) {
      let b = { sum: t[i] - off[i], n: 1 };
      while (pool.length && pool[pool.length - 1].sum / pool[pool.length - 1].n > b.sum / b.n) { const p = pool.pop(); b = { sum: p.sum + b.sum, n: p.n + b.n }; }
      pool.push(b);
    }
    pool.forEach(b => { for (let k = 0; k < b.n; k++) z.push(b.sum / b.n); });
    const zlo = lo + f[0] / 2, zhi = Math.max(zlo, hi - f[n - 1] / 2 - off[n - 1]);
    return z.map((v, i) => Math.max(zlo, Math.min(zhi, v)) + off[i]);
  }
  function nameStates(el) {
    const W = el.clientWidth, rail = el.querySelector('.rail');
    if (!W || !rail) return;   // not drawn yet, or not on screen
    const out = [];
    const mark = el.querySelector('.mark270'), x270 = mark && mark.offsetParent ? W * 270 / 538 : null;   // the 270 mark, where one is drawn
    el.querySelectorAll('.seg').forEach(s => {
      const w = textW(s.dataset.n);
      let room = s.clientWidth;
      s.style.padding = '';
      if (x270 !== null && x270 > s.offsetLeft && x270 < s.offsetLeft + s.clientWidth) {
        // The 270 mark runs through this state: its name sits on the wider side of the mark, not under it.
        const before = x270 - 2 - s.offsetLeft, after = s.offsetLeft + s.clientWidth - x270 - 2;
        room = Math.max(before, after);
        s.style.padding = before > after ? `0 ${Math.round(s.clientWidth - before)}px 0 0` : `0 0 0 ${Math.round(s.clientWidth - after)}px`;
      }
      const fits = w + NAME.fit <= room;
      s.classList.toggle('nl', !fits);
      if (!fits) out.push({ a: s.dataset.a, n: s.dataset.n, w, c: s.offsetLeft + s.offsetWidth / 2, row: 0, xs: [] });
    });
    let ok = out.length > 0 && matchMedia(NAME.wide).matches, H = 0, R = 1;
    if (ok) {
      // Row by row from the bar up: the names in that row, and the lines on their way to a higher one, each get room.
      const place = ([side, lo, hi]) => {
        side.forEach(o => { o.xs = []; });
        for (let q = 0; q <= Math.max(0, ...side.map(o => o.row)); q++) {
          const live = side.filter(o => o.row >= q);
          spread(live.map(o => o.xs.length ? o.xs[o.xs.length - 1] : o.c), live.map(o => o.row === q ? o.w + NAME.pad : NAME.pass), lo, hi).forEach((x, k) => live[k].xs.push(x));
        }
      };
      // Where the 270 mark is drawn, the names keep clear of it on either side.
      const sides = x270 === null ? [[out, -10, W + 10]] : [[out.filter(o => o.c < x270), -10, x270 - 17], [out.filter(o => o.c >= x270), x270 + 17, W + 10]];
      sides.forEach(side => {
        // Names whose places would overlap form a cluster. A cluster stays in one row if that keeps every name
        // within reach of its state; otherwise it is dealt out over two rows, or three, starting with whichever
        // name keeps them closest.
        const [all, lo, hi] = side, clusters = [];
        all.forEach((o, i) => { if (i && o.c - all[i - 1].c < (o.w + all[i - 1].w) / 2 + NAME.pad) clusters[clusters.length - 1].push(o); else clusters.push([o]); });
        clusters.forEach(g => {
          let best = null;
          for (let rows = 1; rows <= NAME.rows && !(best && best.d <= NAME.fan); rows++) {
            for (let first = 0; first < rows; first++) {
              g.forEach((o, k) => { o.row = (k + first) % rows; });
              place([g, lo, hi]);
              const d = Math.max(...g.map(o => Math.abs(o.xs[o.row] - o.c)));
              if (!best || d < best.d - 0.5) best = { d, rows: g.map(o => o.row) };
            }
          }
          g.forEach((o, k) => { o.row = best.rows[k]; });
        });
        place(side);
        // Clusters can crowd each other once they are side by side. One still out of reach gets another row.
        const reach = g => Math.max(...g.map(o => Math.abs(o.xs[o.row] - o.c)));
        for (let pass = 0; pass < 2; pass++) {
          clusters.filter(g => reach(g) > NAME.fan && Math.max(...g.map(o => o.row)) < Math.min(NAME.rows, g.length) - 1).forEach(g => {
            const rows = 2 + Math.max(...g.map(o => o.row)), was = { d: reach(g), rows: g.map(o => o.row) };
            let best = was;
            for (let first = 0; first < rows; first++) {
              g.forEach((o, k) => { o.row = (k + first) % rows; });
              place(side);
              if (reach(g) < best.d - 0.5) best = { d: reach(g), rows: g.map(o => o.row) };
            }
            g.forEach((o, k) => { o.row = best.rows[k]; });
            place(side);
          });
        }
      });
      R = 1 + Math.max(...out.map(o => o.row));
      ok = out.every(o => Math.abs(o.xs[o.row] - o.c) <= NAME.far && o.xs[o.row] - o.w / 2 >= -12 && o.xs[o.row] + o.w / 2 <= W + 12);
    }
    if (ok) {
      H = NAME.lead + R * (NAME.h + NAME.gap);
      const f = v => Math.round(v * 10) / 10, y = q => NAME.lead + q * (NAME.h + NAME.gap);   // the bottom of row q, up from the bar
      // A line leaves straight up, steps across on a diagonal, and arrives straight up.
      const step = (x0, y0, x1, y1, stub) => {
        const dx = Math.abs(x1 - x0), room = y0 - y1 - 2 * stub;
        return dx < 0.6 || room < 1 ? `L${f(x1)} ${f(y1)}` : `L${f(x0)} ${f(y0 - stub)}L${f(x1)} ${f(y0 - stub - Math.min(dx, room))}L${f(x1)} ${f(y1)}`;
      };
      const line = o => {
        let p = `M${f(o.c)} ${H}` + step(o.c, H, o.xs[0], H - y(0) + 1, NAME.stub);
        for (let q = 0; q < o.row; q++) p += `L${f(o.xs[q])} ${H - y(q) - NAME.h + 3}` + step(o.xs[q], H - y(q) - NAME.h + 3, o.xs[q + 1], H - y(q + 1) + 1, 1);
        return p;
      };
      rail.innerHTML = `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">${out.map(o => `<path data-a="${o.a}" d="${line(o)}"/>`).join('')}</svg>${out.map(o => `<span class="rl" data-a="${o.a}" style="left:${f(o.xs[o.row])}px;bottom:${y(o.row)}px">${o.n}</span>`).join('')}`;
    } else rail.innerHTML = '';
    el._list.hidden = ok || !out.length;
    el._railH = ok ? Math.max(el._railH || 0, H) : 0;   // does not shrink from one line-up to the next, so the card keeps its height
    el.style.setProperty('--rail-h', `${el._railH}px`);
    const stage = el.closest('.bal-stage');
    if (stage) {   // the beam needs room above it for the names, and more at the end that tips up
      const tilt = parseFloat(el.closest('.bal-arm').dataset.tilt) || 0;
      stage.style.setProperty('--rail-h', `${el._railH}px`);
      stage.style.setProperty('--rise', `${el._railH ? (Math.abs(Math.tan(tilt * Math.PI / 180)) * W / 2).toFixed(1) : 0}px`);
    }
  }
  let fitTimer = 0;
  const refit = () => document.querySelectorAll('.snake').forEach(el => { el._railH = 0; nameStates(el); });
  window.addEventListener('resize', () => { clearTimeout(fitTimer); fitTimer = setTimeout(refit, 150); });
  // Names are measured again once the web font arrives. The face is asked for by name, in case nothing else has yet.
  const remeasure = () => { inkW = {}; refit(); };
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(remeasure);
  if (document.fonts && document.fonts.load) document.fonts.load(inkFont(), 'NE-3').then(remeasure, () => {});
  const votes = n => `${n} electoral vote${n === 1 ? '' : 's'}`;
  function snake(el, readEl, items, label, onPick, lead, touchPick) {
    const { rows, tp } = tippingOf(items);
    const demEV = rows.filter(r => r.share > 50).reduce((a, r) => a + r.ev, 0);
    const paint = r => { const fill = r.col || (r.toss ? TOSS : shareColor(r.share)); return [fill, `${r === tp ? ' tp' : ''}${r.toss || isLight(fill) ? ' toss' : ''}${darkInk(fill) ? ' dk' : ''}`]; };
    el.innerHTML = rows.map(r => {
      const [fill, cls] = paint(r);
      return `<div class="seg${cls}" data-a="${r.abbr}" data-n="${dname(r.abbr)}" style="flex:${r.ev} 0 0;background:${fill}" tabindex="${r === tp ? 0 : -1}" role="${onPick ? 'button' : 'img'}" aria-label="${esc(byAbbr[r.abbr].name)}, ${votes(r.ev)}, ${fmt(r.share)} Democratic">${dname(r.abbr)}</div>`;
    }).join('') + `<div class="mark270" style="left:${270 / 538 * 100}%"></div><div class="rail" aria-hidden="true"></div>`;
    // The same line-up as a list, shown where the bar is too short to name its states.
    if (!el._list) {
      el._list = document.createElement('div');
      el._list.className = 'snake-list'; el._list.hidden = true; el._list.setAttribute('aria-hidden', 'true');
      (el.closest('.bal-stage') || el).insertAdjacentElement('afterend', el._list);
    }
    el._list.innerHTML = rows.map(r => { const [fill, cls] = paint(r); return `<span class="${cls.trim()}" data-a="${r.abbr}" style="background:${fill}">${dname(r.abbr)}</span>`; }).join('');
    el.setAttribute('role', 'group');
    el.setAttribute('aria-label', `${label}: every state from most Democratic to most Republican. The arrow keys move between states.`);
    const tpName = byAbbr[tp.abbr].name.replace(' District', '');
    const winner = tp.share > 50 ? 'Democrats' : 'Republicans';
    const base = `${label}: ${lead ? lead + '. The' : 'the'} tipping point is <b>${esc(tpName)}</b> at ${fmt(tp.share)} Democratic, so <b>${winner}</b> reach 270 (${demEV} Democratic electoral votes).`;
    readEl.innerHTML = base;
    const segs = [...el.querySelectorAll('.seg')];
    // The state being read is also picked out among the names above the bar and in the list.
    const hot = a => [el.querySelector('.rail'), el._list].forEach(box => box.querySelectorAll('[data-a]').forEach(x => x.classList.toggle('hot', x.dataset.a === a)));
    const rest = () => { readEl.innerHTML = base; hot(null); };
    const show = r => { readEl.innerHTML = `<b>${esc(byAbbr[r.abbr].name)}</b>: ${votes(r.ev)}, ${fmt(r.share)} Democratic. Democrats reach ${votes(r.after)} if they win every state up to here.`; hot(r.abbr); };
    segs.forEach((s, i) => {
      const r = rows[i];
      s.addEventListener('mouseenter', () => { if (!el._touch) show(r); });
      s.addEventListener('mouseleave', () => { if (!el._touch) rest(); });
      // One stop for the Tab key: the state that has focus is the one Tab comes back to. A touch also moves
      // focus, to whichever state the browser snaps the finger to; the line keeps the state under the finger.
      s.addEventListener('focus', () => {
        segs.forEach(x => { x.tabIndex = x === s ? 0 : -1; });
        if (performance.now() - (el._touchAt || 0) < 500) return;
        el._touch = false; segs.forEach(g => g.classList.remove('on')); show(r);
      });
      s.addEventListener('blur', () => { if (!el._touch) rest(); });
      if (onPick) {
        // A touch reads the state. It also picks it only where the page says so (touchPick); elsewhere a link under the bar does.
        s.addEventListener('click', () => {
          if (!el._touch) return onPick(r.abbr);
          const on = el.querySelector('.seg.on');   // the state the line is reading, not the one the browser snapped the tap to
          if (touchPick) onPick(on ? on.dataset.a : r.abbr);
        });
        s.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onPick(r.abbr); } });
      }
    });
    // By touch: put a finger on the bar or slide along it, and the line below reads the state under it.
    const readSeg = s => { segs.forEach(g => g.classList.toggle('on', g === s)); show(rows[segs.indexOf(s)]); };
    el._read = x => {
      // The state under the finger, taken along the middle of the bar so a finger that drifts off it still reads.
      const box = el.getBoundingClientRect(), under = document.elementFromPoint(Math.max(box.left + 1, Math.min(box.right - 1, x)), box.top + box.height / 2);
      readSeg(segs.includes(under) ? under : x < box.left + box.width / 2 ? segs[0] : segs[segs.length - 1]);
    };
    // A name above the bar, or in the list, stands in for its state: point at it, tap it or click it.
    el._readA = a => readSeg(segs.find(g => g.dataset.a === a));
    el._lift = a => { segs.forEach(g => { g.classList.toggle('hov', g.dataset.a === a); g.classList.remove('on'); }); if (a) show(rows[segs.findIndex(g => g.dataset.a === a)]); else rest(); };
    el._pick = onPick; el._touchPick = touchPick;
    if (!el._wired) {
      el._wired = true;
      const named = e => { const t = e.target.closest && e.target.closest('.rl, .snake-list span'); return t ? t.dataset.a : null; };
      const touch = e => {
        el._touch = e.pointerType !== 'mouse';
        if (!el._touch) return;
        el._touchAt = performance.now();
        const a = named(e);
        if (a) el._readA(a); else el._read(e.clientX);
      };
      el.addEventListener('pointerdown', touch);
      el._list.addEventListener('pointerdown', e => { if (named(e)) touch(e); });
      el.addEventListener('pointermove', e => { if (e.pointerType !== 'mouse' && (e.pressure > 0 || e.buttons) && !named(e)) { el._touchAt = performance.now(); el._read(e.clientX); } });
      // A mouse arriving after a touch (a laptop with both) goes back to pointing.
      el.addEventListener('pointerover', e => { if (e.pointerType === 'mouse' && el._touch) { el._touch = false; el.querySelectorAll('.seg.on').forEach(g => g.classList.remove('on')); } });
      [el, el._list].forEach(box => {
        box.addEventListener('pointerover', e => { const a = named(e); if (a && e.pointerType === 'mouse') { el._touch = false; el._lift(a); } });
        box.addEventListener('pointerout', e => { if (named(e) && e.pointerType === 'mouse') el._lift(null); });
        box.addEventListener('click', e => { const a = named(e); if (a && el._pick && (!el._touch || el._touchPick)) el._pick(a); });
      });
      el.addEventListener('keydown', e => {
        const all = [...el.querySelectorAll('.seg')], i = all.indexOf(document.activeElement);
        const to = { ArrowRight: i + 1, ArrowDown: i + 1, ArrowLeft: i - 1, ArrowUp: i - 1, Home: 0, End: all.length - 1 }[e.key];
        if (i < 0 || to === undefined) return;
        e.preventDefault();
        all[Math.max(0, Math.min(all.length - 1, to))].focus();
      });
    }
    nameStates(el);
  }

  // ---------- electoral-vote histogram ----------
  function histogram(el, hist) {
    const W = 600, H = 220, l = 10, r = 10, t = 14, b = 30, bin = 10;
    const bins = [];
    for (let i = 0; i <= 538; i += bin) bins.push({ x: i, p: hist.slice(i, i + bin).reduce((a, v) => a + v, 0) });
    const max = Math.max(...bins.map(b => b.p)) || 1;
    const x = v => l + v / 538 * (W - l - r), y = p => t + (1 - p / max) * (H - t - b);
        let o = bins.map(bn => `<rect x="${x(bn.x) + 0.5}" y="${y(bn.p)}" width="${Math.max(1, x(bn.x + bin) - x(bn.x) - 1)}" height="${H - b - y(bn.p)}" fill="${bn.x + bin / 2 >= 270 ? '#4f8de0' : '#d8665b'}" rx="1.5"><title>${bn.x} to ${Math.min(538, bn.x + bin - 1)} Democratic electoral votes: ${bn.p < 0.0005 ? 'almost none' : (100 * bn.p).toFixed(1) + '%'} of simulations</title></rect>`).join('');
    o += `<line x1="${x(270)}" x2="${x(270)}" y1="${t - 6}" y2="${H - b}" stroke="#e9eef5" stroke-dasharray="3 3"></line><text x="${x(270) + 5}" y="${t + 2}">270</text>`;
    [0, 100, 200, 300, 400, 538].forEach(v => { o += `<text x="${x(v)}" y="${H - 10}" text-anchor="${v === 0 ? 'start' : v === 538 ? 'end' : 'middle'}">${v}</text>`; });
    el.innerHTML = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Distribution of Democratic electoral votes across all simulations">${o}</svg><p class="small" style="margin-top:6px">Democratic electoral votes. Blue bars are Democratic wins, red are Republican wins.</p>`;
  }

  // ---------- map: state outlines or a hexagon grid ----------
  let mapMode = window.matchMedia && matchMedia('(max-width: 600px)').matches ? 'hex' : 'geo';   // hexagons read better on phones
  const HEX = {
    AK: [0.5, 0], ME: [11.5, 0], VT: [10, 1], NH: [11, 1],
    WA: [1.5, 2], MT: [2.5, 2], ND: [3.5, 2], MN: [4.5, 2], WI: [5.5, 2], MI: [7.5, 2], NY: [9.5, 2], MA: [10.5, 2], RI: [11.5, 2],
    ID: [2, 3], WY: [3, 3], SD: [4, 3], IA: [5, 3], IL: [6, 3], IN: [7, 3], OH: [8, 3], PA: [9, 3], NJ: [10, 3], CT: [11, 3],
    OR: [1.5, 4], NV: [2.5, 4], CO: [3.5, 4], NE: [4.5, 4], MO: [5.5, 4], KY: [6.5, 4], WV: [7.5, 4], VA: [8.5, 4], MD: [9.5, 4], DE: [10.5, 4],
    CA: [2, 5], UT: [3, 5], NM: [4, 5], KS: [5, 5], AR: [6, 5], TN: [7, 5], NC: [8, 5], SC: [9, 5], DC: [10, 5],
    AZ: [3.5, 6], OK: [4.5, 6], LA: [5.5, 6], MS: [6.5, 6], AL: [7.5, 6], GA: [8.5, 6],
    HI: [1, 7], TX: [5, 7], FL: [9, 7],
  };
  const hexD = (cx, cy, r) => 'M' + [0, 1, 2, 3, 4, 5].map(k => { const t = Math.PI / 180 * (60 * k - 90); return (cx + r * Math.cos(t)).toFixed(1) + ',' + (cy + r * Math.sin(t)).toFixed(1); }).join('L') + 'Z';

  function drawUS(svg, { fill, sub, onPick, onHover, selected, districts = true }) {
    const W = 1075, H = 610, hex = mapMode === 'hex';
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
    const shape = {}, at = {};
    for (const a of Object.keys(SHAPES)) {
      if (hex) { const [c, r] = HEX[a]; at[a] = [96 + c * 69.3, 76 + r * 60]; shape[a] = hexD(at[a][0], at[a][1], 39); }
      else { const [dx, dy] = LABEL_NUDGE[a] || [0, 0]; at[a] = OFFSHORE[a] || [SHAPES[a].c[0] + dx, SHAPES[a].c[1] + dy]; shape[a] = SHAPES[a].d; }
    }
    let o = '';
    for (const a of Object.keys(SHAPES)) o += `<path class="st" data-a="${a}" d="${shape[a]}" fill="${fill(a)}" tabindex="0" aria-label="${byAbbr[a].name}"></path>`;
    for (const a of Object.keys(SHAPES)) if (hex || !SMALL.includes(a)) o += `<text class="lbl${hex ? ' big' : !hex && OFFSHORE[a] ? ' off' : ''}" data-l="${a}" x="${at[a][0]}" y="${at[a][1] + (hex ? 5 : 3)}">${a}</text>` +
      (sub ? `<text class="lbl pc${hex ? ' big' : OFFSHORE[a] ? ' off' : ''}" data-l="${a}" data-p="${a}" x="${at[a][0]}" y="${at[a][1] + (hex ? 21 : 14)}"></text>` : '');
    const bx = 1005, bw = 54, bh = 21, dy0 = hex ? 232 : 392;
    if (!hex) SMALL.forEach((a, i) => {
      const y = 118 + i * 27, c = SHAPES[a].c;
      o += `<line class="leader" x1="${c[0]}" y1="${c[1]}" x2="${bx}" y2="${y + bh / 2}"></line>`;
      o += `<g class="box" data-a="${a}" tabindex="0" aria-label="${byAbbr[a].name}"><rect x="${bx}" y="${y}" width="${bw}" height="${bh}" rx="4" fill="${fill(a)}"></rect><text x="${bx + bw / 2}" y="${y + 14.5}">${a}<tspan class="bp" data-bp="${a}"></tspan></text></g>`;
    });
    if (districts) o += `<text class="grp" x="${bx}" y="${dy0 - 8}">Districts</text>`;
    (districts ? DISTRICTS : []).forEach((a, i) => {
      const y = dy0 + i * 27;
      o += `<g class="box" data-a="${a}" tabindex="0" aria-label="${byAbbr[a].name}"><rect x="${bx}" y="${y}" width="${bw}" height="${bh}" rx="4" fill="${fill(a)}"></rect><text x="${bx + bw / 2}" y="${y + 14.5}">${dname(a)}<tspan class="bp" data-bp="${a}"></tspan></text></g>`;
    });
    o += '<path class="sel" d=""></path>';
    svg.innerHTML = o;
    const sel = svg.querySelector('.sel');
    const mark = a => {
      svg.querySelectorAll('g.box').forEach(g => g.classList.toggle('on', g.dataset.a === a));
      sel.setAttribute('d', shape[a] || '');
    };
    svg.querySelectorAll('[data-a]').forEach(el => {
      const a = el.dataset.a;
      el.addEventListener('mouseenter', () => onHover(a));
      el.addEventListener('mouseleave', () => onHover(null));
      el.addEventListener('click', () => onPick(a));
      el.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onPick(a); } });
      el.addEventListener('focus', () => onHover(a));
    });
    mark(selected);
    // Labels turn dark on light fills (gold toss-ups and the Lean shades) so they stay readable.
    const dark = c => c === TOSS || isLight(c);
    const ink = () => {
      svg.querySelectorAll('text[data-l]').forEach(t => t.classList.toggle('dark', dark(fillOf[t.dataset.l]) && !t.classList.contains('off')));
      svg.querySelectorAll('g.box').forEach(g => g.classList.toggle('dark', dark(fillOf[g.dataset.a])));
    };
    // Win chances under the labels (and inside the side boxes), when the map has them.
    const relabel = f => {
      if (!f) return;
      svg.querySelectorAll('text[data-p]').forEach(t => { t.textContent = f(t.dataset.p); });
      svg.querySelectorAll('tspan[data-bp]').forEach(t => { const v = f(t.dataset.bp); t.textContent = v ? ' ' + v.split(' ')[1] : ''; });
    };
    const fillOf = Object.fromEntries(Object.keys(SHAPES).concat(DISTRICTS).map(a => [a, fill(a)]));
    ink(); relabel(sub);
    return { mark, recolor: (f, sb) => { relabel(sb); svg.querySelectorAll('[data-a]').forEach(el => { const t = el.tagName === 'g' ? el.querySelector('rect') : el; fillOf[el.dataset.a] = f(el.dataset.a); t.setAttribute('fill', fillOf[el.dataset.a]); }); ink(); } };
  }

  // ---------- the balance: the path to 270 as a beam on a fulcrum ----------
  // The beam tips toward whoever wins more simulations: level at 50-50, five degrees at a certainty.
  const BALANCE = `<div class="bal-top"><div class="side d"><span class="big" data-k="dem"></span> <span class="l">in 100 <b>Democrat wins</b></span></div>
    <div class="side r"><span class="l">in 100 <b>Republican wins</b></span> <span class="big" data-k="rep"></span></div></div>
    <div class="bal-stage"><div class="bal-arm"><div class="snake"></div></div><div class="bal-fulcrum" aria-hidden="true"><span>270</span></div></div>
    <div class="snake-key"></div>
    <p class="snake-read"></p>
    <div class="snake-more"></div>`;
  const tiltOf = d => -Math.sign(d) * 5 * Math.pow(Math.min(1, Math.abs(d)), 0.6);
  function balance(el, items, label, pDem, pRep, onPick, more, touchPick) {
    if (!el.firstChild) el.innerHTML = BALANCE;
    const whole = v => String(Math.round(100 * v));
    countTo(el.querySelector('[data-k="dem"]'), pDem, whole);
    countTo(el.querySelector('[data-k="rep"]'), pRep, whole);
    const arm = el.querySelector('.bal-arm'), tilt = tiltOf(pDem - pRep).toFixed(2);
    arm.dataset.tilt = tilt;   // the names above the beam need to know how far its ends rise
    snake(el.querySelector('.snake'), el.querySelector('.snake-read'), items, label, onPick, VERDICT[rateOf(pDem)], touchPick);
    el.querySelector('.snake-key').innerHTML = snakeKey(items.some(i => i.col) ? 'rate' : 'share');
    el.querySelector('.snake-more').innerHTML = more || '';
    // Read aloud as one sentence, not as loose numbers and labels.
    const top = el.querySelector('.bal-top');
    top.setAttribute('role', 'img');
    top.setAttribute('aria-label', `${whole(pDem)} in 100 Democrat wins, ${whole(pRep)} in 100 Republican wins`);
    setTimeout(() => { arm.style.transform = `rotate(${tilt}deg)`; }, 80);
  }
  // The models and their average, side by side. m: { enns, desart, now }, each { pDemWin, demPopular } or null.
  const MODELS = [['enns', 'State-level approval and fundamentals model', 'Enns, Colner, Kumar and Lagodny'], ['desart', 'Long-range model', 'DeSart']];
  function ensemble(el, m) {
    const card = (cls, name, by, x) => `<div class="ens ${cls}"><span class="nm">${name}</span><span class="by">${by}</span>
      <span class="k">Chance of winning the election</span>
      <span class="odds"><b>${Math.round(100 * x.pDemWin)}</b> in 100 for the Democrat</span><span class="split" aria-hidden="true"><i style="width:${(100 * x.pDemWin).toFixed(1)}%"></i></span>
      <span class="vote">Expected vote: ${fmt(x.demPopular)} Democratic, ${fmt(100 - x.demPopular)} Republican</span></div>`;
    const have = MODELS.filter(([k]) => m[k]);
    el.style.setProperty('--cols', have.length > 1 ? Array(have.length + 1).fill('minmax(0, 1fr)').join(' auto ') : 'minmax(0, 1fr)');
    el.innerHTML = have.length > 1
      ? have.map(([k, name, by]) => card('m-' + k, name, by, m[k])).join('<span class="op" aria-hidden="true">+</span>') + '<span class="op" aria-hidden="true">=</span>' +
        card('now', 'The Nowcast', 'Their average, state by state', m.now)
      : card('now', 'The Nowcast', 'The state-level approval and fundamentals model alone today', m.now);
  }
  // The light at the top of the page leans toward whoever is ahead.
  function setGlow(pDem, pRep) {
    const d = Math.max(-0.5, Math.min(0.5, pDem - pRep)), st = document.documentElement.style;
    st.setProperty('--glow-d', (0.10 + 0.16 * d).toFixed(3));
    st.setProperty('--glow-r', (0.10 - 0.16 * d).toFixed(3));
  }

  // ---------- 100 simulated elections as hexagons ----------
  function waffle(el, pDem, pTie) {
    const nD = Math.round(100 * pDem), nT = Math.round(100 * pTie);
    let o = '';
    for (let i = 0; i < 100; i++) {
      const c = Math.floor(i / 5), r = i % 5;
      o += `<path d="${hexD(12 + c * 16.2 + (r % 2 ? 8.1 : 0), 12 + r * 14, 8.6)}" fill="${i < nD ? '#4f8de0' : i < nD + nT ? '#8b6bd1' : '#d8665b'}"></path>`;
    }
    el.innerHTML = `<svg viewBox="0 0 344 80" role="img" aria-label="${nD} of 100 simulated elections go to the Democrat">${o}</svg>`;
  }

  // ---------- head-to-head matchups at a glance ----------
  // One row per pairing: each poll as a small dot and the pairing's plain average as a large one, on the
  // Democrat's share of the two-party vote. The top row is every poll together, the figure the long-range model uses.
  function matchups(el, noteEl, polls, fixed) {
    if (!el) return;
    if (!polls.length) { el.innerHTML = ''; noteEl.textContent = ''; return; }
    const lo = 38, hi = 62, x = v => (Math.min(hi, Math.max(lo, v)) - lo) / (hi - lo) * 100;
    const groups = {};
    polls.forEach(p => { const k = p.d + '|' + p.r; (groups[k] = groups[k] || { d: p.d, r: p.r, polls: [] }).polls.push(p); });
    const avg = ps => ps.reduce((a, p) => a + p.share, 0) / ps.length;
    const rows = Object.values(groups).map(g => ({ ...g, avg: avg(g.polls) }))
      .sort((a, b) => b.polls.length - a.polls.length || Math.abs(b.avg - 50) - Math.abs(a.avg - 50));
    const margin = v => { const m = 2 * (v - 50); return Math.abs(m) < 0.05 ? 'Even' : (m > 0 ? 'D+' : 'R+') + Math.abs(m).toFixed(1); };
    const row = (name, sub, ps, a, all) => {
      const side = a > 50 ? 'D' : 'R', single = ps.length === 1;
      const dots = single ? '' : ps.map(p => `<i class="pt ${p.share > 50 ? 'D' : 'R'}" style="left:${x(p.share).toFixed(2)}%" title="${esc(p.pollster)}, ${p.date}: ${fmt(p.share)}"></i>`).join('');
      return `<div class="mx-row${all ? ' all' : ''}"><div class="mx-name"><b>${name}</b><span>${sub}</span></div>
        <div class="mx-track"><span class="mid"></span><span class="lean ${side}" style="left:${Math.min(x(a), 50).toFixed(2)}%;width:${Math.abs(x(a) - 50).toFixed(2)}%"></span>${dots}<i class="avg ${side}${single ? ' one' : ''}" style="left:${x(a).toFixed(2)}%" title="${fmt(a)} Democratic"></i></div>
        <div class="mx-m ${side === 'D' ? 'd-ink' : 'r-ink'}">${margin(a)}</div></div>`;
    };
    const total = avg(polls);
    el.innerHTML = `<div class="mx-scale" aria-hidden="true"><span></span><div>${[40, 45, 50, 55, 60].map(v => `<em style="left:${x(v)}%">${v}%</em>`).join('')}</div><span></span></div>` +
      row('All matchups', `Average of ${polls.length} polls`, polls, total, true) +
      rows.map(g => row(`${esc(pollName(g.d))} vs. ${esc(pollName(g.r))}`, g.polls.length === 1 ? `1 poll, ${g.polls[0].date}` : `Average of ${g.polls.length} polls`, g.polls, g.avg)).join('');
    el.setAttribute('aria-label', `Head-to-head matchups: all ${polls.length} polls together are ${margin(total)}; ` + rows.map(g => `${pollName(g.d)} vs. ${pollName(g.r)} ${margin(g.avg)}`).join(', '));
    noteEl.textContent = `The Democrat's share of the two-party vote in each pairing: small dots are single polls, the large dot is their plain average, and the margin is the gap between the two candidates. The top row puts every poll together, as DeSart does; it is the poll figure the long-range model uses${fixed ? '' : ' until the nominees are known'}.`;
  }

  // ---------- the Nowcast day by day, on a timeline running to the forecast ----------
  // The x axis runs from the first day to the publish day, so the line fills in over time, with the days the
  // inputs change marked ahead of time: when they happen the Nowcast can jump.
  const EVENTS = [
    ['2027-11-07', 'Long-range model locks', 'The long-range model switches to polls from October 2027 and stops changing. Once DeSart publishes his own forecast from those polls, his state forecasts replace the site\'s run of his model.'],
    ['2028-06-01', 'Approval window', 'The approval model starts moving to polls conducted June 1 to July 30, as the paper does; it switches once ten pollsters have one.'],
    ['2028-08-06', 'Final', 'The final forecast is posted: DeSart\'s published forecast averaged with the one Enns and colleagues publish. If theirs is not out yet, the site\'s own run of their model stands in until it is.'],
  ];
  function trendChart(el, noteEl, H) {
    if (!el) return;
    const day = d => Date.parse(d + 'T12:00:00Z') / 864e5;
    const start = H.length ? H[0].date : todayIso(), end = EVENTS[EVENTS.length - 1][0];
    const W = 600, Ht = 236, l = 40, r = 14, tp = 30, b = 26;
    const x = d => l + (day(d) - day(start)) / (day(end) - day(start)) * (W - l - r), y = v => tp + (1 - v) * (Ht - tp - b);
    let o = '';
    [0, .25, .5, .75, 1].forEach(v => { o += `<line x1="${l}" x2="${W - r}" y1="${y(v)}" y2="${y(v)}" stroke="${v === .5 ? '#5d6a7e' : '#1f2b3e'}" ${v === .5 ? 'stroke-dasharray="3 3"' : ''}></line><text x="${l - 8}" y="${y(v) + 4}" text-anchor="end">${v * 100}%</text>`; });
    o += `<text x="${l}" y="${Ht - 6}">${niceDate(start)}</text>`;
    ['2027-01-01', '2028-01-01'].forEach(d => { if (x(d) - l > 90) o += `<text x="${x(d)}" y="${Ht - 6}" text-anchor="middle">${d.slice(0, 4)}</text>`; });
    const today = todayIso();
    EVENTS.forEach(([d, short], k) => {
      const done = today >= d, xx = x(d);
      o += `<line x1="${xx}" x2="${xx}" y1="${tp - 2}" y2="${y(0)}" stroke="${done ? '#5d6a7e' : '#f0a35e'}" stroke-dasharray="4 4" opacity="${done ? .6 : .8}"></line>
        <g class="ev${done ? ' done' : ''}"><circle cx="${xx}" cy="${tp - 12}" r="9"></circle><text x="${xx}" y="${tp - 8}" text-anchor="middle">${k + 1}</text><title>${short}, ${niceDate(d)}</title></g>`;
    });
    if (H.length) {
      const pts = H.map(h => `${x(h.date).toFixed(1)},${y(h.pDemWin).toFixed(1)}`).join(' ');
      if (H.length > 1) o += `<polygon points="${x(H[0].date)},${y(0)} ${pts} ${x(H[H.length - 1].date)},${y(0)}" fill="rgba(240,163,94,.1)"></polygon><polyline points="${pts}" fill="none" stroke="#f0a35e" stroke-width="2"></polyline>`;
      const last = H[H.length - 1];
      o += `<circle cx="${x(last.date)}" cy="${y(last.pDemWin)}" r="4" fill="#f0a35e"><title>${niceDate(last.date)}: ${Math.round(100 * last.pDemWin)} in 100 for the Democrat</title></circle>`;
    }
    el.innerHTML = `<svg viewBox="0 0 ${W} ${Ht}" role="img" aria-label="Share of simulations the Democrat wins, day by day, on a timeline to the forecast on August 6, 2028">${o}</svg>`;
    if (noteEl) noteEl.innerHTML = '<ol class="ev-list">' + EVENTS.map(([d, , long], k) =>
      `<li class="${today >= d ? 'done' : ''}"><b>${k + 1}. ${niceDate(d)}</b> ${long}</li>`).join('') + '</ol>';
  }

  // ---------- ratings board ----------
  const BOARD = [['SD', 'Solid D'], ['LD', 'Likely D'], ['TD', 'Lean D'], ['TOSS', 'Toss-up'], ['TR', 'Lean R'], ['LR', 'Likely R'], ['SR', 'Solid R']];
  function board(el, states, onPick) {
    el.innerHTML = BOARD.map(([k, label]) => {
      const rows = states.filter(s => s.rating === k).sort((a, b) => b.demShare - a.demShare);
      const chips = rows.map(s => `<button type="button" data-a="${s.abbr}"${darkInk(RATE_COLOR[k]) ? ' class="toss"' : ''} style="background:${RATE_COLOR[k]}" title="${esc(byAbbr[s.abbr].name)}: ${fmt(s.demShare)} Democratic, ${s.ev} EV">${dname(s.abbr)}</button>`).join('');
      return `<div class="col ${k}"><div class="hd"><b>${label}</b><span class="num">${rows.reduce((a, s) => a + s.ev, 0)} EV</span></div><div class="chips">${chips || '<span class="none">None</span>'}</div></div>`;
    }).join('');
    el.querySelectorAll('button').forEach(b => b.addEventListener('click', () => onPick(b.dataset.a)));
  }

  // ---------- numbers that count up ----------
  const still = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  function countTo(el, to, show) {
    const from = el.dataset.v === undefined ? 0.5 : +el.dataset.v;
    el.dataset.v = to;
    if (still || from === to) { el.textContent = show(to); return; }
    const t0 = performance.now();
    const step = t => { const k = Math.max(0, Math.min(1, (t - t0) / 700)), e = 1 - Math.pow(1 - k, 3); el.textContent = show(from + (to - from) * e); if (k < 1) requestAnimationFrame(step); };
    el.textContent = show(from);
    requestAnimationFrame(step);
  }

  // ---------- dates ----------
  const ELECTION_DATE = new Date('2028-11-07T00:00:00-05:00');
  const daysTo = d => Math.max(0, Math.floor((d - new Date()) / 86400000));
  const monthName = ym => new Date(ym + '-15').toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
  const niceDate = iso => new Date(iso.length === 10 ? iso + 'T12:00:00' : iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  // How much of a state's gap in the state approval source counts: '' in full, 'half' at 0.5, otherwise a percentage.
  // What the state approval figure in a state's panel is made of.
  const approvalNote = () => { const g = gapSize(N.approval.state_data); return `The national average, moved by ${g === 'half' ? 'half ' : g ? g + ' of ' : ''}this state's gap in ${(N.approval.state_data && N.approval.state_data.name) || 'the state source'}${N.approval.state_data && N.approval.state_data.name ? "'s tracker" : ''}${cur && cur.vpShift ? ' and by the vice-president adjustment' : ''}.`; };
  const gapSize = sd => { const k = sd && sd.gap_scale; return k == null || k === 1 ? '' : k === 0.5 ? 'half' : `${Math.round(100 * k)}%`; };

  // ================= HOME =================
  function renderHome() {
    const views = {
      fc: [R.map(r => ({ abbr: r.abbr, ev: r.ev, share: r.pub.fc })), '2024 forecast'],
      actual: [R.map(r => ({ abbr: r.abbr, ev: r.ev, share: r.share })), '2024 result'],
      today: N ? [N.states.map(s => ({ abbr: s.abbr, ev: s.ev, share: s.demShare, toss: s.rating === 'TOSS', col: RATE_COLOR[s.rating] })), window.FORECAST ? '2028 forecast' : '2028 Nowcast'] : null,
    };
    const hb = document.getElementById('bal-home');
    if (N && !N.fixture_run) {
      const s = N.summary, M = N.models || {}, nD = Math.round(100 * s.pDemWin), nT = Math.round(100 * s.pTie), rep = (100 - nD - nT) / 100;
      balance(hb, views.today[0], views.today[1], s.pDemWin, rep, () => { location.hash = 'nowcast'; }, '<a href="#nowcast">See every state</a>');
      ensemble(document.getElementById('ens-home'), { enns: M.enns || s, desart: M.desart || null, now: s });
      MODELS.forEach(([k]) => { const el = document.getElementById('odds-' + k); if (el && M[k]) el.textContent = Math.round(100 * M[k].pDemWin); });
      document.getElementById('hero-date').textContent = window.FORECAST ? `Published ${niceDate(window.FORECAST.published)}. Final: it does not change.` : `Updated ${niceDate(N.generated_at)}. Not the forecast, which is due August 6, 2028.`;
      if (window.FORECAST) document.getElementById('hero-live').textContent = 'Final 2028 forecast';
      setGlow(s.pDemWin, rep);
    } else {
      balance(hb, views.fc[0], '2024 forecast', NAT.pub.pDemWin, 1 - NAT.pub.pDemWin);
      document.getElementById('hero-live').textContent = 'The 2024 forecast, as published in July 2024';
      document.getElementById('hero-date').textContent = 'The 2028 Nowcast starts with its first daily data run.';
      document.getElementById('ens-home').hidden = true;
    }
    const tabs = document.querySelectorAll('[data-snake]');
    const show = k => { const v = views[k] || views.fc; tabs.forEach(t => t.setAttribute('aria-selected', t.dataset.snake === k)); snake(document.getElementById('snake-home'), document.getElementById('snake-home-read'), v[0], v[1]); document.getElementById('snake-home-key').innerHTML = snakeKey(v[0].some(i => i.col) ? 'rate' : 'share'); };
    tabs.forEach(t => { if (t.dataset.snake === 'today' && !views.today) t.disabled = true; t.addEventListener('click', () => show(t.dataset.snake)); });
    show('fc');   // the 2028 line-up is the balance at the top of the page
  }

  // ================= Archive: 2008 to 2024 =================
  // One election at a time, in the same form for every year: the 50 states and the District of Columbia, Maine
  // and Nebraska counted whole, and three views of it (the Nowcast's method and each model on its own).
  // 2008 to 2020 come from docs/archive.js (pipeline/make_archive.py). 2024 is put in that form here, from the
  // two forecasts the authors published for it.
  const ARCH = window.ARCHIVE && window.ARCHIVE.years ? window.ARCHIVE.years : {};
  if (BT && DS) {
    const WHOLE = { ME: 4, NE: 5 };
    ARCH['2024'] = {
      dem: 'Harris', rep: 'Trump', wholeEV: { dem: 226, rep: 312 }, natActual, pub: '',
      evNote: 'The real count was also 312 to 226: Maine\'s 2nd district went to Trump and Nebraska\'s 2nd to Harris.',
      src: {
        bt: { kind: 'backtest', tab: 'Nowcast method, back-tested',
          lede: 'What the Nowcast\'s method would have said in 2024. State by state it averages two forecasts published before the election: the state-level approval and fundamentals forecast from July 2024 and Jay DeSart\'s long-range model forecast from November 2023. Nobody published this average at the time, so it is a back-test.',
          note: `A back-test, not a forecast anyone published. State by state it averages two forecasts that were published, whose national votes were ${fmt(BT.national.enns)} and ${fmt(BT.national.desart)}.` },
        enns: { kind: 'published', tab: 'State-level approval and fundamentals, as published',
          lede: 'The state-level approval and fundamentals forecast as Enns, Colner, Kumar and Lagodny published it in July 2024, with data from 100 days before the election.', note: '' },
        desart: { kind: 'published', tab: 'Long-range model, as published',
          lede: 'The long-range model\'s forecast as Jay DeSart published it in November 2023, a year before the election, from head-to-head polls taken the month before.',
          note: 'The odds are reproduced from DeSart\'s own simulation script, which draws every state independently around its forecast. His national vote adds the states by his own turnout weights.' },
      },
      nat: { bt: { fc: BT.national.fc, pDemWin: BT.national.pDemWin }, enns: NAT.pub, desart: { fc: DS.national.fc, pDemWin: DS.national.pDemWin } },
      states: Object.fromEntries(R.filter(r => r.abbr.length === 2).map(r => [r.abbr, { ev: WHOLE[r.abbr] || r.ev, share: r.share, bt: BT.states[r.abbr], enns: r.pub, desart: DS.states[r.abbr] }])),
    };
  }
  const SRC = { bt: 'bt', pub: 'enns', ds: 'desart' };   // the three tabs, and the forecast each one shows
  const YEARS24 = ['2024', '2020', '2016', '2012', '2008'].filter(y => ARCH[y]);
  let year24 = YEARS24[0], src24 = 'bt', Y24 = null, Rv = [], byV = {}, NATv = null;
  function useSrc24(k) {
    Y24 = ARCH[year24]; src24 = SRC[k] ? k : 'bt';
    const s = SRC[src24];
    Rv = Object.keys(Y24.states).map(x => { const c = Y24.states[x]; return { name: byAbbr[x].name, abbr: x, ev: c.ev, share: c.share, ...c[s], hi: Math.min(100, c[s].hi), all: c }; });
    byV = Object.fromEntries(Rv.map(r => [r.abbr, r]));
    NATv = Y24.nat[s];
  }
  let layer24 = 'forecast', pinned24 = null, map24;
  const err = r => r.fc - r.share;
  // A view is either a forecast its authors published or a back-test: the page says which, wherever it names it.
  const word24 = () => Y24.src[SRC[src24]].kind === 'published' ? 'forecast' : 'back-test';
  const demEV24 = () => Rv.filter(r => r.fc > 50).reduce((a, r) => a + r.ev, 0);
  // The candidate who won that year: the forecast is read against their electoral votes and their chance.
  const won24 = () => {
    const dem = Y24.wholeEV.dem >= 270, ev = dem ? demEV24() : 538 - demEV24(), p = NATv.pDemWin;
    return { name: dem ? Y24.dem : Y24.rep, ev, act: dem ? Y24.wholeEV.dem : Y24.wholeEV.rep, p: p == null ? null : dem ? p : 1 - p, called: ev >= 270 };
  };

  function insp24(a) {
    const el = document.getElementById('insp-2024');
    if (!a || !byV[a]) {
      const e = NATv.fc - Y24.natActual, w = won24(), note = Y24.src[SRC[src24]].note;
      // A chance its authors published keeps their own decimals where the page would otherwise say only ">99%" or "<1%".
      const exact = word24() === 'forecast' && w.p != null && (w.p > 0.995 || w.p < 0.005);
      el.innerHTML = `<span class="tag">United States · 538 electoral votes</span><h2>National vote</h2>
        <dl class="kv">
          <div><dt>Forecast D share</dt><dd class="d-ink">${fmt(NATv.fc, 2)}</dd></div>
          <div><dt>Actual D share</dt><dd class="d-ink">${fmt(Y24.natActual, 2)}</dd></div>
          <div><dt>Forecast R share</dt><dd class="r-ink">${fmt(100 - NATv.fc, 2)}</dd></div>
          <div><dt>Signed error (pred − actual)</dt><dd class="a-ink">${sgn(e)} pts</dd></div>
          <div><dt>Electoral votes</dt><dd>${w.name} ${w.ev} · actual ${w.act}</dd></div>
          <div><dt>${w.name} win chance</dt><dd>${w.p == null ? 'Not on record' : exact ? (100 * w.p).toFixed(2) + '%' : pct(w.p)}</dd></div>
          <div><dt>Winner</dt><dd style="color:${w.called ? 'var(--ok)' : 'var(--rep-ink)'}">${w.called ? 'Called' : 'Missed'}</dd></div>
        </dl>
        <div class="stack" style="gap:6px"><div class="strip-scale num"><span>30%</span><span>50%</span><span>70%</span></div><div class="strip">${strip({ f: NATv.fc, a: Y24.natActual })}</div></div>
        <div class="strip-legend"><span><i class="f"></i>Forecast</span><span><i class="a"></i>Actual</span></div>
        ${note ? `<p class="hint">${esc(note)}</p>` : ''}
        <p class="hint">Electoral votes count each state as a whole. ${esc(Y24.evNote)}</p>
        <p class="hint">Hover or click a state for its numbers.</p>`;
      return;
    }
    const r = byV[a], e = err(r), ok = (r.fc > 50) === (r.share > 50), c = r.all;
    const part = (k, label) => `<div><dt>${label}, ${Y24.src[k].kind === 'published' ? 'published' : 'back-test'}</dt><dd>${fmt(c[k].fc, 2)}</dd></div>`;
    el.innerHTML = `<span class="tag">${a} · ${r.ev} electoral vote${r.ev > 1 ? 's' : ''}</span><h2>${r.name}</h2>
      <dl class="kv">
        <div><dt>Forecast D share</dt><dd class="d-ink">${fmt(r.fc, 2)}</dd></div>
        <div><dt>Actual D share</dt><dd class="d-ink">${fmt(r.share, 2)}</dd></div>
        ${src24 === 'bt' && !c.same ? part('enns', 'Approval and fundamentals') + part('desart', 'Long-range model') : `<div><dt>Forecast R share</dt><dd class="r-ink">${fmt(100 - r.fc, 2)}</dd></div>`}
        <div><dt>Signed error (pred − actual)</dt><dd class="a-ink">${sgn(e)} pts</dd></div>
        <div><dt>Rating</dt><dd>${RATING[r.rating]}</dd></div>
        <div><dt>${Y24.dem} win chance</dt><dd>${Math.round(100 * r.pDem)}%</dd></div>
        <div><dt>90% range</dt><dd>${r.lo.toFixed(1)}–${r.hi.toFixed(1)}%</dd></div>
        <div><dt>Call</dt><dd style="color:${ok ? 'var(--ok)' : 'var(--rep-ink)'}">${ok ? 'Correct' : 'Missed'}</dd></div>
        ${c.note ? `<p class="hint" style="grid-column:1/-1">${esc(c.note)}</p>` : ''}
      </dl>
      <div class="stack" style="gap:6px"><div class="strip-scale num"><span>30%</span><span>50%</span><span>70%</span></div><div class="strip">${strip({ f: r.fc, a: r.share, lo: r.lo, hi: r.hi })}</div></div>
      <div class="strip-legend"><span><i class="f"></i>Forecast</span><span><i class="a"></i>Actual</span><span><i class="b"></i>90% range</span></div>
      ${pinned24 ? '<button class="btn" id="unpin24" style="justify-self:start">Show national</button>' : ''}`;
    const u = document.getElementById('unpin24');
    if (u) u.onclick = () => pick24(null);
  }
  const fill24 = a => { const r = byV[a]; if (!r) return '#1f2b3e'; return layer24 === 'forecast' ? shareColor(r.fc) : layer24 === 'actual' ? shareColor(r.share) : errColor(err(r)); };
  function pick24(a) {
    pinned24 = a === pinned24 ? null : a;
    map24.mark(pinned24); insp24(pinned24);
    document.querySelectorAll('#rows-2024 .st-row').forEach(x => x.classList.toggle('on', x.dataset.a === pinned24));
  }
  function snake24() {
    const actual = layer24 === 'actual';
    snake(document.getElementById('snake-2024'), document.getElementById('snake-2024-read'),
      Rv.map(r => ({ abbr: r.abbr, ev: r.ev, share: actual ? r.share : r.fc })), `${year24} ${actual ? 'result' : word24()}`);
  }

  let filter24 = 'all', sort24 = { k: 'fc', dir: -1 };
  function rows24() {
    let rows = Rv.slice();
    if (filter24 === 'comp') rows = rows.filter(r => !r.rating.startsWith('S'));
    const key = r => sort24.k === 'name' ? r.name : sort24.k === 'err' ? Math.abs(err(r)) : r[sort24.k];
    rows.sort((x, y) => (key(x) > key(y) ? 1 : key(x) < key(y) ? -1 : 0) * sort24.dir);
    const line = (a, name, ev, o, f, s, e, cls = '') =>
      `<div class="st-row ${cls}" data-a="${a}" tabindex="0" role="button" aria-label="${name}"><div class="nm">${name}${a ? `<small>${a}</small>` : ''}</div><div class="n">${ev}</div>` +
      `<div class="strip">${strip(o)}</div><div class="n a-ink">${f.toFixed(1)}</div><div class="n">${s.toFixed(1)}</div><div class="n">${sgn(e, 1)}</div></div>`;
    let h = line('', 'National vote', 538, { f: NATv.fc, a: Y24.natActual }, NATv.fc, Y24.natActual, NATv.fc - Y24.natActual, 'nat');
    h += rows.map(r => line(r.abbr, r.name, r.ev, { f: r.fc, a: r.share, lo: r.lo, hi: r.hi }, r.fc, r.share, err(r), r.abbr === pinned24 ? 'on' : '')).join('');
    const box = document.getElementById('rows-2024');
    box.innerHTML = h;
    box.querySelectorAll('.st-row').forEach(el => {
      const go = () => { pick24(el.dataset.a || null); document.getElementById('map-2024').scrollIntoView({ behavior: 'smooth', block: 'center' }); };
      el.addEventListener('click', go);
      el.addEventListener('keydown', e => { if (e.key === 'Enter') go(); });
    });
  }

  const draw24 = () => drawUS(document.getElementById('map-2024'), { fill: fill24, selected: pinned24, onPick: pick24, onHover: a => { insp24(a || pinned24); map24.mark(a || pinned24); }, districts: false });
  const nw24 = t => t.replace('back-tested', '<span class="nw">back-tested</span>');
  function figs24() {
    // Every year is scored on the 50 states.
    const st = Rv.filter(r => r.abbr !== 'DC'), S = Y24.src[SRC[src24]], w = word24();
    const mae = st.reduce((s, r) => s + Math.abs(err(r)), 0) / st.length;
    const inside = st.filter(r => r.share >= r.lo && r.share <= r.hi).length;
    const correct = st.filter(r => (r.fc > 50) === (r.share > 50)).length;
    const { name: who, ev, act, called } = won24();
    document.getElementById('figs-2024').innerHTML = [
      [`${correct}/${st.length}`, 'States called'],
      [ev === act ? `${ev} = ${act}` : `${ev} vs ${act}`, `${who} electoral votes, ${w} and actual. <b>Winner ${called ? 'called' : 'missed'}.</b>`],
      [`${mae.toFixed(1)} pts`, 'Average state miss'],
      [`${inside}/${st.length}`, 'States inside the 90% range'],
    ].map(([v, l]) => `<div><span class="v">${v}</span><span class="l">${l}</span></div>`).join('');
    document.getElementById('h-2024').innerHTML = `${year24}: the <span class="nw">${w}</span> against the result`;
    document.getElementById('lede-2024').textContent = S.lede + ' Pick a state on the map or in the list to compare its forecast and result.';
    const pub = document.getElementById('pub-2024');
    pub.innerHTML = Y24.pub ? `<b>Published at the time.</b> ${esc(Y24.pub)}` : ''; pub.hidden = !Y24.pub;
    document.querySelector('[data-layer="forecast"]').textContent = w === 'forecast' ? 'Published forecast' : 'Back-test';
    document.querySelectorAll('[data-src24]').forEach(x => { x.setAttribute('aria-selected', x.dataset.src24 === src24); x.innerHTML = nw24(esc(Y24.src[SRC[x.dataset.src24]].tab)); });
    document.querySelectorAll('[data-year24]').forEach(x => x.setAttribute('aria-selected', x.dataset.year24 === year24));
    document.getElementById('flt-all').textContent = `All ${Rv.length}`;
    document.getElementById('map-2024').setAttribute('aria-label', `Map of the ${year24} ${w} and results by state`);
  }
  // Another election: its own rows, map and figures, starting from the Nowcast's method.
  function setYear24(y) {
    year24 = ARCH[y] ? y : YEARS24[0];
    pinned24 = null;
    useSrc24('bt'); figs24();
    map24 = draw24(); insp24(null); snake24(); rows24();
  }
  function render2024() {
    if (!YEARS24.length) { document.getElementById('lede-2024').textContent = 'The archive could not be loaded. Reload the page to try again.'; return; }
    useSrc24('bt');
    figs24();
    document.querySelectorAll('[data-src24]').forEach(b => b.addEventListener('click', () => {
      useSrc24(b.dataset.src24); figs24();
      map24.recolor(fill24); insp24(pinned24); snake24(); rows24();
    }));
    document.querySelectorAll('[data-year24]').forEach(b => {
      if (!ARCH[b.dataset.year24]) { b.hidden = true; b.disabled = true; return; }
      b.addEventListener('click', () => setYear24(b.dataset.year24));
    });

    map24 = draw24();
    ramp(document.getElementById('ramp-2024'), 'share');
    insp24(null);
    snake24();
    document.querySelectorAll('[data-layer]').forEach(b => b.addEventListener('click', () => {
      layer24 = b.dataset.layer;
      document.querySelectorAll('[data-layer]').forEach(x => x.setAttribute('aria-selected', x === b));
      map24.recolor(fill24);
      ramp(document.getElementById('ramp-2024'), layer24 === 'error' ? 'error' : 'share');
      snake24();
    }));
    const setF = f => { filter24 = f; ['all', 'comp'].forEach(k => { const b = document.getElementById('flt-' + k); b.setAttribute('aria-pressed', k === f); b.setAttribute('aria-selected', k === f); }); rows24(); };
    document.getElementById('flt-all').onclick = () => setF('all');
    document.getElementById('flt-comp').onclick = () => setF('comp');
    document.querySelectorAll('.st-head [data-sort]').forEach(b => b.addEventListener('click', () => {
      const k = b.dataset.sort;
      sort24 = { k, dir: sort24.k === k ? -sort24.dir : (k === 'name' ? 1 : -1) };
      document.querySelectorAll('.st-head [data-sort]').forEach(x => x === b ? x.setAttribute('aria-sort', sort24.dir > 0 ? 'ascending' : 'descending') : x.removeAttribute('aria-sort'));
      rows24();
    }));
    rows24();
  }

  // ================= 2028 Nowcast =================
  let layer28 = 'tracker', pinned28 = null, map28, cur = null;   // cur = current simulation result
  // The long-range model's vote is not the polls' average: DeSart's equation starts from the last result and moves it by
  // about half of the polls' margin (coefficient 0.52), so the two are shown side by side to avoid misreading.
  const SHRINK = 'The long-range model starts from the 2024 result and moves it by about half of the polls\' margin, because polls this far out are only partly predictive (DeSart\'s estimate).';
  const POLLS_NOTE = info => info && info.polls
    ? `The polls themselves: the Democrat gets ${(Math.round(info.polls.avg * 10) / 10).toFixed(1)}% of the two-party vote on average in ${info.polls.n} head-to-head poll${info.polls.n === 1 ? '' : 's'}. ${SHRINK}`
    : '';
  const ROLES = { 'dem-p': ['D', 'Democratic nominee'], 'dem-vp': ['D', 'Running mate'], 'rep-p': ['R', 'Republican nominee'], 'rep-vp': ['R', 'Running mate'] };
  const TICKET_KEY = { 'dem-p': ['dem', 'president'], 'dem-vp': ['dem', 'vp'], 'rep-p': ['rep', 'president'], 'rep-vp': ['rep', 'vp'] };
  const norm = s => (s || '').toLowerCase().replace(/[^a-z]/g, '');
  const pct = p => p > 0.995 ? '>99%' : p < 0.005 ? '<1%' : Math.round(100 * p) + '%';
  // Each model on its own next to the Nowcast: vote share and how often the Democrat wins.
  const modelTable = (rows, what) => `<table class="mt"><caption>Each model on its own</caption>
    <thead><tr><th scope="col"></th><th scope="col">D vote</th><th scope="col">D wins</th></tr></thead><tbody>
    ${rows.map(([name, v, p, cls]) => `<tr${cls ? ` class="${cls}"` : ''}><th scope="row">${name}</th><td>${fmt(v)}</td><td>${pct(p)}</td></tr>`).join('')}</tbody></table>`;

  // A confirmed nominee or running mate, read from Wikipedia by the daily run. Confirmed names are locked.
  function official(role) { const [side, k] = TICKET_KEY[role]; const o = (N.tickets[side] || {})[k]; return o && o.name ? o : null; }

  function nomineesNote() {
    const d = official('dem-p'), r = official('rep-p');
    if (d && r) return `The nominees are confirmed: ${esc(d.name)} and ${esc(r.name)}.`;
    return `Until the nominees are confirmed, each party's possible nominees are averaged by their standing in the polls${d || r ? `; ${esc((d || r).name)} is confirmed` : ''}.`;
  }
  // Until a nominee or running mate is confirmed, each party's possible nominees are averaged by their polling.
  function readPick(role) {
    const off = official(role);
    return off ? { name: off.name, state: off.state, locked: true } : null;
  }

  // Both models and their average, for a set of picks (docs/combine.js). n is draws per economic weighting.
  const pk = o => ({ dp: o['dem-p'] || null, rp: o['rep-p'] || null, dv: o['dem-vp'] || null, rv: o['rep-vp'] || null });
  const runModels = (o, n) => window.TP.run(N, pk(o), { n: n || 10000 });
  const lastName = n => n.replace(/ (Jr\.|Sr\.|II|III)$/, '').split(' ').pop();
  // Names in poll listings: last name, keeping "Jr." (Trump Jr.), and the full name for anyone polled who is
  // not on the candidate list (Hunter Biden, Mark Cuban), so no one is mistaken for a better-known namesake.
  // Long pollster names, shortened for tables; the full name shows on hover.
  const SHORT_POLLSTER = {
    'University of Massachusetts Lowell Center for Public Opinion/YouGov': 'UMass Lowell/YouGov',
    'Hart Research Associates/Public Opinion Strategies': 'Hart/Public Opinion Strategies',
    'Impact Research/National Research Inc.': 'Impact/National Research',
  };
  const shortPollster = n => SHORT_POLLSTER[n] || n.replace(/University of /, 'U. of ').replace(/ Center for Public Opinion/, '');
  const pollsterCell = n => { const sh = shortPollster(n); return sh === n ? esc(n) : `<span title="${esc(n)}">${esc(sh)}</span>`; };
  const pollName = n => {
    if (N && ((N.h2h && N.h2h.people) || []).concat((N.desart_final && N.desart_final.people) || []).some(p => p.name === n)) return n;
    const m = n.match(/ (Jr\.|Sr\.)$/);
    return m ? `${lastName(n)} ${m[1]}` : lastName(n);
  };

  // The Nowcast: today's polls and state economies, with the chosen (or confirmed) tickets.
  function runScenario() {
    const picks = Object.fromEntries(Object.keys(ROLES).map(r => [r, readPick(r)]));
    const out = runModels(picks);
    cur = out.combined;
    cur.enns = out.enns; cur.desart = out.desart; cur.info = out.info;
    cur.picks = picks; cur.vpNom = out.info.vpNom; cur.vpShift = out.info.vpShift;
    cur.byAbbr = Object.fromEntries(cur.states.map(s => [s.abbr, s]));
    showResults();
  }

  let timer = null;
  function schedule() {
    const out = ['hero-28', 'results-2028'].map(id => document.getElementById(id));
    out.forEach(el => el.classList.add('busy'));
    clearTimeout(timer);
    timer = setTimeout(() => { runScenario(); out.forEach(el => el.classList.remove('busy')); }, 60);
  }

  function showResults() {
    const s = cur;
    // Whole numbers out of 100, so the two big figures, the hexagons and the caption always agree.
    const nD = Math.round(100 * s.pDemWin), nT = Math.round(100 * s.pTie), rep = (100 - nD - nT) / 100;
    // Electoral votes with each state going to whoever is ahead in it: the map as drawn.
    const evPoint = s.states.filter(x => x.demShare > 50).reduce((a, x) => a + x.ev, 0);
    const items = s.states.map(x => ({ abbr: x.abbr, ev: x.ev, share: x.demShare, toss: x.rating === 'TOSS', col: RATE_COLOR[x.rating] }));
    const tp = tippingOf(items).tp;
    const toMap = a => {
      setLayer28('tracker');
      if (pinned28 !== a) pick28(a, true);
      document.getElementById('map-2028').scrollIntoView({ behavior: still ? 'auto' : 'smooth', block: 'center' });
    };
    balance(document.getElementById('bal-28'), items, window.FORECAST ? '2028 forecast' : '2028 Nowcast', s.pDemWin, rep, toMap, '', true);
    ensemble(document.getElementById('ens-28'), { enns: s.enns || s, desart: s.desart, now: s });
    setGlow(s.pDemWin, rep);
    waffle(document.getElementById('waffle-28'), s.pDemWin, s.pTie);
    document.getElementById('waffle-cap').textContent = `Out of 100 simulated elections${window.FORECAST ? '' : ' held today'}, the Democrat wins ${nD} and the Republican wins ${100 - nD - nT}${nT ? `, with ${nT} tied` : ''}. A simulation is one possible outcome given how far off the models have been in the past.`;
    const mo = document.getElementById('models-28');
    if (mo) mo.innerHTML = s.desart
      ? `Each state's number is the average of the state-level approval and fundamentals model and the long-range model, half each. The whole map is then simulated together, so the Nowcast's odds are not simply the average of the two models' odds. ${nomineesNote()} ${s.desart ? POLLS_NOTE(s.info) : ''} <a href="#method">How they work</a>`
      : `Today's Nowcast is the state-level approval and fundamentals model on its own, because no head-to-head polls are available. <a href="#method">How it works</a> · <a href="#models">Each model on its own</a>`;
    document.getElementById('figs-2028').innerHTML = [
      [fmt(s.demPopular), 'Democratic share of the two-party vote'],
      [`${evPoint}`, 'Democratic electoral votes, each state to the candidate ahead in it'],
      [esc(byAbbr[tp.abbr].name.replace(' District', '')), `Tipping-point state, ${fmt(tp.share)} Democratic`],
    ].map(([v, l]) => `<div><span class="v">${v}</span><span class="l">${l}</span></div>`).join('');
    board(document.getElementById('board-28'), s.states, toMap);
    histogram(document.getElementById('hist-2028'), s.evHistogram);
    renderModels();
    if (map28 && layer28 !== 'official') map28.recolor(fill28, sub28);
    insp28(pinned28);
  }

  // ---------- each model on its own (a secondary page) ----------
  // The two inputs to the Nowcast, each simulated alone, with its own map. Clearly marked as background:
  // the Nowcast (their average, simulated together) is the site's prediction.
  const MODEL_PAGE = [
    ['enns', 'State-level approval and fundamentals model', 'Enns, Colner, Kumar and Lagodny',
      'Reads how voters rate the president in each state, how each state\'s economy has grown, and home states. Built to forecast about 100 days before the election.'],
    ['desart', 'Long-range model', 'DeSart',
      'Reads national head-to-head polls and each state\'s last result. Built to forecast a year out, before the nominees are known.'],
  ];
  let modelMaps = [];
  function renderModels() {
    const el = document.getElementById('models-each');
    if (!el || !cur) return;
    const label = window.FORECAST ? 'the 2028 forecast' : 'the Nowcast';
    document.getElementById('models-back').textContent = window.FORECAST ? 'Go to the 2028 forecast' : 'Go to the 2028 Nowcast';
    const now = Object.fromEntries(cur.states.map(s => [s.abbr, s]));
    modelMaps = [];
    el.innerHTML = MODEL_PAGE.map(([k, name, by, reads]) => {
      const m = cur[k];
      if (!m) return `<section class="model-alone"><div class="ma-head"><div><h2>${name}</h2><span class="by">${by}</span></div></div><p class="small">Not available today: no head-to-head polls could be read, so ${label} uses the other model alone.</p></section>`;
      const nD = Math.round(100 * m.pDemWin), nT = Math.round(100 * (m.pTie || 0));
      const ev = m.states.filter(x => x.demShare > 50).reduce((a, x) => a + x.ev, 0);
      const close = [...m.states].filter(x => byAbbr[x.abbr] && !x.abbr.includes('-')).sort((a, b) => Math.abs(a.pDem - .5) - Math.abs(b.pDem - .5)).slice(0, 6);
      const diff = [...m.states].filter(x => now[x.abbr] && !x.abbr.includes('-')).sort((a, b) => Math.abs(b.demShare - now[b.abbr].demShare) - Math.abs(a.demShare - now[a.abbr].demShare)).slice(0, 4);
      const row = x => `<li><span>${esc(byAbbr[x.abbr].name)}</span><b class="${x.demShare > 50 ? 'd-ink' : 'r-ink'}">${chance(x.pDem) || (x.pDem > .5 ? 'D >98%' : 'R >98%')}</b></li>`;
      const drow = x => { const d = x.demShare - now[x.abbr].demShare; return `<li><span>${esc(byAbbr[x.abbr].name)}</span><b class="${d > 0 ? 'd-ink' : 'r-ink'}">${d > 0 ? 'D' : 'R'} +${Math.abs(d).toFixed(1)}</b></li>`; };
      return `<section class="model-alone" aria-label="${name}, on its own">
        <div class="ma-head"><div><h2>${name}</h2><span class="by">${by}</span></div><span class="ma-tag">One half of ${label}</span></div>
        <p class="ma-reads">${reads}</p>
        <div class="ma-figs">
          <div><span class="v d-ink">${nD}</span><span class="l">in 100 for the Democrat</span></div>
          <div><span class="v r-ink">${100 - nD - nT}</span><span class="l">in 100 for the Republican</span></div>
          <div><span class="v">${fmt(m.demPopular)}</span><span class="l">Expected Democratic vote</span></div>
          <div><span class="v">${ev}</span><span class="l">Democratic electoral votes, each state to whoever is ahead</span></div>
        </div>
        <div class="ma-grid">
          <div><p class="ma-read" id="read-${k}" aria-live="polite">Hover or tap a state for this model's numbers.</p><svg class="usmap" id="map-m-${k}" role="img" aria-label="${name}: each state by rating"></svg><div class="ramp" id="ramp-m-${k}"></div></div>
          <div class="ma-side">
            <h3>Closest states</h3><ul class="ma-list">${close.map(row).join('')}</ul>
            <h3>Furthest from ${label}</h3><p class="small">Its vote share minus ${label}'s.</p><ul class="ma-list">${diff.map(drow).join('')}</ul>
          </div>
        </div>
      </section>`;
    }).join('');
    MODEL_PAGE.forEach(([k, name]) => {
      const m = cur[k]; if (!m) return;
      const by = Object.fromEntries(m.states.map(s => [s.abbr, s])), read = document.getElementById('read-' + k);
      const show = a => { const s = a && by[a]; read.textContent = s ? `${byAbbr[a] ? byAbbr[a].name : a}: ${fmt(s.demShare)} Democratic, ${Math.round(100 * s.pDem)} in 100 for the Democrat (${RATING[s.rating]}). ${label[0].toUpperCase() + label.slice(1)}: ${fmt(now[a].demShare)}.` : 'Hover or tap a state for this model\'s numbers.'; };
      const draw = () => drawUS(document.getElementById('map-m-' + k), { fill: a => by[a] ? RATE_COLOR[rateOf(by[a].pDem)] : greyColor(), sub: a => by[a] ? chance(by[a].pDem) : '', selected: null, onPick: show, onHover: show });
      draw(); modelMaps.push(draw); ramp(document.getElementById('ramp-m-' + k), 'nowcast');
    });
  }

  // ================= LATEST DATA =================
  // What the morning run read: the newest polls, approval, state economies and primary polling, and what changed
  // since the run before. Reads the payload and the daily history only; it runs no simulation of its own.
  const etTime = iso => new Date(iso).toLocaleString('en-US', { timeZone: 'America/New_York', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }) + ' ET';
  const shortDay = iso => new Date(iso + 'T12:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  const dayDiff = (a, b) => Math.round((Date.parse(a + 'T12:00:00Z') - Date.parse(b + 'T12:00:00Z')) / 864e5);
  const marginOf = share => { const m = 2 * (share - 50); return Math.abs(m) < 0.05 ? 'Even' : (m > 0 ? 'D+' : 'R+') + Math.abs(m).toFixed(1); };
  const linkOr = (url, html) => url && /^https?:\/\//.test(url) ? `<a href="${esc(url)}" target="_blank" rel="noopener">${html}</a>` : html;

  // A line chart with a hover readout. series: [{key, color, label}], rows: [{d, ...}], text(row) for the readout.
  function lineChart(el, readEl, rows, series, opts) {
    const narrow = el.clientWidth < 480, W = narrow ? 380 : 600, Ht = narrow ? 230 : 210, l = 36, r = narrow ? 104 : 118, tp = 12, b = 24;
    const day = d => Date.parse(d + 'T12:00:00Z');
    const vals = rows.flatMap(row => series.map(s => row[s.key]));
    const lo = Math.floor(Math.min(...vals) / 5) * 5, hi = Math.ceil(Math.max(...vals) / 5) * 5;
    const x = d => l + (day(d) - day(rows[0].d)) / Math.max(1, day(rows[rows.length - 1].d) - day(rows[0].d)) * (W - l - r);
    const y = v => tp + (1 - (v - lo) / (hi - lo)) * (Ht - tp - b);
    let o = '';
    for (let v = lo; v <= hi; v += 5) o += `<line x1="${l}" x2="${W - r}" y1="${y(v)}" y2="${y(v)}" stroke="#1f2b3e"></line><text x="${l - 6}" y="${y(v) + 4}" text-anchor="end">${v}%</text>`;
    const y0 = +rows[0].d.slice(0, 4), y1 = +rows[rows.length - 1].d.slice(0, 4);
    for (let yr = y0 + 1; yr <= y1; yr++) { const xx = x(yr + '-01-01'); o += `<line x1="${xx}" x2="${xx}" y1="${tp}" y2="${Ht - b}" stroke="#1f2b3e"></line><text x="${xx}" y="${Ht - 6}" text-anchor="middle">${yr}</text>`; }
    o += `<text x="${l}" y="${Ht - 6}">${new Date(rows[0].d + 'T12:00:00').toLocaleDateString('en-US', { month: 'short', year: 'numeric' })}</text>`;
    const last = rows[rows.length - 1];
    series.forEach(s => {
      o += `<polyline points="${rows.map(row => `${x(row.d).toFixed(1)},${y(row[s.key]).toFixed(1)}`).join(' ')}" fill="none" stroke="${s.color}" stroke-width="2" stroke-linejoin="round"></polyline>
        <circle cx="${x(last.d)}" cy="${y(last[s.key])}" r="3.5" fill="${s.color}"></circle>
        <text class="end" x="${x(last.d) + 8}" y="${y(last[s.key]) + 4}" fill="${s.color}">${s.label} ${last[s.key].toFixed(1)}%</text>`;
    });
    o += `<line class="guide" x1="0" x2="0" y1="${tp}" y2="${Ht - b}" stroke="#5d6a7e" visibility="hidden"></line><rect class="hit" x="${l}" y="${tp}" width="${W - l - r}" height="${Ht - tp - b}" fill="transparent"></rect>`;
    el.innerHTML = `<svg viewBox="0 0 ${W} ${Ht}" role="img" aria-label="${esc(opts.label)}">${o}</svg>`;
    const svg = el.querySelector('svg'), guide = svg.querySelector('.guide'), hit = svg.querySelector('.hit');
    const pick = (row, isLast) => { readEl.textContent = opts.text(row, isLast); if (opts.onPick) opts.onPick(row, isLast); };
    const idle = () => { guide.setAttribute('visibility', 'hidden'); pick(last, true); };
    const at = ev => {
      const pt = svg.createSVGPoint(); pt.x = ev.clientX; pt.y = ev.clientY;
      const px = pt.matrixTransform(svg.getScreenCTM().inverse()).x;
      let best = rows[0]; rows.forEach(row => { if (Math.abs(x(row.d) - px) < Math.abs(x(best.d) - px)) best = row; });
      guide.setAttribute('x1', x(best.d)); guide.setAttribute('x2', x(best.d)); guide.setAttribute('visibility', 'visible');
      pick(best, best === last);
    };
    hit.addEventListener('pointermove', at); hit.addEventListener('pointerdown', at); hit.addEventListener('pointerleave', idle);
    idle();
  }

  function renderData() {
    const H = (window.NOWCAST_HISTORY || []).filter(h => h.v === 5);
    const box = id => document.getElementById(id);
    if (!N) { box('data-status').textContent = 'This fills in after the first daily data run.'; return; }
    const S = N.summary, A = N.approval, E = N.economy, h2h = N.h2h || { polls: [] };
    const today = H.find(h => h.date === N.as_of), prev = [...H].reverse().find(h => h.date < N.as_of);
    const fixed = !!(N.desart_final && N.desart_final.frozen);

    // Status line: when the data were read, and from where.
    box('data-status').innerHTML = (window.FORECAST ? `The final forecast was published ${niceDate(window.FORECAST.published)}. The data stopped updating then; this page shows them as they stood.`
      : `Last update <b>${etTime(N.generated_at)}</b>. Updates every morning, Eastern time.`) +
      (h2h.stale ? ' <span class="warn">PollResults.org could not be read this morning, so the head-to-head polls are the last good copy.</span>' : '');

    // What moved since the run before.
    const since = prev ? `since ${shortDay(prev.date)}` : '';
    const change = (now, then, unit, digits, partisan) => {
      if (!prev) return '';   // nothing earlier to compare with yet, so the figure stands alone
      if (then === undefined || then === null) return '<span class="chg">First day tracked</span>';
      const d = now - then, r = +d.toFixed(digits);
      if (r === 0) return `<span class="chg">No change ${since}</span>`;
      const cls = partisan ? (d > 0 ? 'd-ink' : 'r-ink') : '';
      return `<span class="chg ${cls}">${d > 0 ? '▲' : '▼'} ${Math.abs(r).toFixed(digits)}${unit} ${since}</span>`;
    };
    const pollAvg = N.models && N.models.polls ? N.models.polls.avg : null;
    const nD = Math.round(100 * S.pDemWin);
    const econNew = prev && prev.econThrough && prev.econThrough !== E.through;
    box('data-changes').innerHTML = [
      [`${nD} in 100`, `The Democrat's chance in ${window.FORECAST ? 'the forecast' : 'the Nowcast'}`, change(100 * S.pDemWin, prev && 100 * prev.pDemWin, '', 0, true)],
      [fmt(S.demPopular), 'Expected Democratic vote', change(S.demPopular, prev && prev.demPopular, ' pts', 1, true)],
      [fmt(A.approve), 'Trump\'s approval', change(A.approve, prev && prev.approve, ' pts', 1)],
      [pollAvg === null ? '—' : fmt(pollAvg), 'Democrat\'s share in head-to-head polls', change(pollAvg, prev && prev.pollAvg, ' pts', 1, true)],
      [monthName(E.through).replace(' ', '<br>'), 'Newest month of state economic data', prev ? `<span class="chg">${econNew ? 'New month added ' : 'No new month '}${since}</span>` : ''],
    ].map(([v, l, c]) => `<div><span class="v">${v}</span><span class="l">${l}</span>${c}</div>`).join('');

    // ---- head-to-head polls ----
    const hp = [...(h2h.polls || [])].sort((a, b) => (b.added || '').localeCompare(a.added || '') || b.date.localeCompare(a.date));
    const recent = p => p.added && dayDiff(N.as_of, p.added) <= 7;
    const nRecent = hp.filter(recent).length;
    const hRow = p => `<tr${recent(p) ? ' class="new"' : ''}><td class="num c-a">${p.added ? shortDay(p.added) : '—'}${recent(p) ? '<i class="dot" title="Added in the last 7 days"></i>' : ''}</td>
      <td class="c-p">${linkOr(p.url, pollsterCell(p.pollster))}</td><td class="c-m">${esc(pollName(p.d))} vs. ${esc(pollName(p.r))}</td>
      <td class="num c-g ${p.share > 50 ? 'd-ink' : p.share < 50 ? 'r-ink' : ''}">${marginOf(p.share)}</td><td class="num muted c-c"><span class="lbl">Conducted to </span>${shortDay(p.date)}</td></tr>`;
    const SHOW = 8;
    box('dc-h2h').innerHTML = `<div class="dc-head"><div><h2 id="dc-h2h-h">Head-to-head polls</h2>
        <p class="small">${fixed ? `The long-range model is fixed on ${N.desart_final.polls.length} polls conducted in October 2027${pollAvg !== null ? `, where the Democrat averages ${fmt(pollAvg)} of the two-party vote` : ''}. Below are the ${hp.length} polls conducted since ${shortDay(h2h.window[0])}.`
          : `${hp.length} poll${hp.length === 1 ? '' : 's'} conducted ${shortDay(h2h.window[0])} to ${shortDay(h2h.window[1])} count toward the long-range model${pollAvg !== null ? `; the Democrat averages ${fmt(pollAvg)} of the two-party vote` : ''}.`} ${nRecent ? `${nRecent} added in the last week.` : 'None added in the last week.'}</p></div>
        <a class="dc-link" href="#nowcast" data-goto="mx-anchor">Matchups chart</a></div>
      ${fixed ? `<p class="note">Since November 7, 2027 the long-range model uses only polls conducted in October 2027, as DeSart does. Newer polls are listed here but no longer move ${window.FORECAST ? 'the forecast' : 'the Nowcast'}.</p>` : ''}
      ${hp.length ? `<div class="dt-wrap"><table class="dt cards"><thead><tr><th>Added</th><th>Pollster</th><th>Matchup</th><th class="num">Margin</th><th class="num">Conducted</th></tr></thead>
        <tbody>${hp.slice(0, SHOW).map(hRow).join('')}</tbody><tbody class="more" hidden>${hp.slice(SHOW).map(hRow).join('')}</tbody></table></div>
        ${hp.length > SHOW ? `<button class="btn ghost dc-more" type="button" aria-expanded="false">Show all ${hp.length} polls</button>` : ''}` : '<p class="small">No head-to-head polls in the window yet.</p>'}
      <p class="foot">Margin is the gap between the two candidates' share of the two-party vote. Added is the day PollResults.org listed the poll; conducted is the last day it was in the field. ${h2h.skipped ? `${h2h.skipped} other pairing${h2h.skipped === 1 ? ' was' : 's were'} left out: generic party labels, three-way questions, or a president who cannot run again.` : ''}</p>`;
    const more = box('dc-h2h').querySelector('.dc-more');
    if (more) more.addEventListener('click', () => {
      const tb = box('dc-h2h').querySelector('tbody.more'), open = tb.hidden;
      tb.hidden = !open; more.setAttribute('aria-expanded', open); more.textContent = open ? 'Show fewer' : `Show all ${hp.length} polls`;
    });

    // ---- approval ----
    const ap = [...(A.polls || [])].sort((a, b) => (b.added || '').localeCompare(a.added || '') || b.date.localeCompare(a.date)).slice(0, 6);
    const trend = (A.trend || []).filter(t => t.a && t.dis);
    box('dc-appr').innerHTML = `<div class="dc-head"><div><h2 id="dc-appr-h">Trump's approval</h2>
        <p class="small">The approval model's national figure: ${A.pooled ? `every poll of all adults conducted ${shortDay(A.window[0])} to ${shortDay(A.window[1])}, from ${A.pollsters} pollsters, each counted by its sample size, as the paper pools them.` : `the latest poll of all adults from each of ${A.pollsters} pollsters, finished ${shortDay(A.window[0])} to ${shortDay(A.window[1])}, newer and larger polls counting more.`}</p></div></div>
      <div class="dc-big"><span><b id="appr-big-a">${fmt(A.approve)}</b> approve</span><span><b id="appr-big-d">${fmt(A.disapprove)}</b> disapprove</span></div>
      ${trend.length > 2 ? `<p class="dc-read" id="appr-read" aria-live="polite"></p><div class="dc-chart" id="appr-chart"></div>` : ''}
      <h3>Newest approval polls</h3>
      <ul class="dc-list">${ap.map(p => `<li><span>${linkOr(p.url, pollsterCell(p.pollster))}<small>Conducted to ${shortDay(p.date)}${p.added ? `, added ${shortDay(p.added)}` : ''}</small></span><b class="num">${Math.round(p.approve)}–${Math.round(p.disapprove)}</b></li>`).join('')}</ul>
      <p class="foot">This is the national figure.${A.all_polls ? ` Polls of registered or likely voters only are left out, because the paper measures approval among all adults; with them the average would be ${fmt(A.all_polls.approve)} approve.` : ''} Each state sits above or below it by ${gapSize(A.state_data) === 'half' ? 'half ' : gapSize(A.state_data) ? gapSize(A.state_data) + ' of ' : ''}its gap in ${A.state_data && A.state_data.name ? esc(A.state_data.name) + "'s" : 'a'} state-by-state tracker${A.state_data && A.state_data.as_of ? ' on ' + niceDate(A.state_data.as_of) : ''}${gapSize(A.state_data) ? ' (the model was built on state figures that sit closer together)' : ''}; the gaps are refreshed by hand, not daily. ${A.official_wait ? `The model moves to polls finished June 1 to July 30, 2028, the paper's window, once ${A.official_wait.needed} pollsters have one in it (${A.official_wait.pollsters} so far).` : N.mode === 'official' ? 'The model now uses polls finished June 1 to July 30, 2028, as the paper does.' : 'From June 2028 the model uses polls finished June 1 to July 30, 2028, as the paper does, once ten pollsters have one in that window.'}</p>`;
    if (trend.length > 2) lineChart(box('appr-chart'), box('appr-read'), trend,
      [{ key: 'dis', color: '#94a1b5', label: 'Disapprove' }, { key: 'a', color: '#f2a65e', label: 'Approve' }],
      { label: `Trump's approval, a 30-day average each week since ${trend[0].d}: now ${fmt(A.approve)} approve, ${fmt(A.disapprove)} disapprove`,
        text: (t, isLast) => isLast ? 'Today (30-day average). Move over the chart to see any week.' : `Week of ${niceDate(t.d)} (30-day average)`,
        // The large figures follow the pointer, and return to today's when it leaves the chart.
        onPick: t => { box('appr-big-a').textContent = fmt(t.a); box('appr-big-d').textContent = fmt(t.dis); } });

    // ---- state economies ----
    const M = E.monthly || [], lat = E.latest || {};
    const ranked = Object.entries(lat).sort((a, b) => b[1] - a[1]);
    const st = ([a, v]) => `<li><span>${esc(byAbbr[a] ? byAbbr[a].name : a)}</span><b class="num">${v > 0 ? '+' : ''}${v.toFixed(2)}%</b></li>`;
    const lastM = M[M.length - 1];
    box('dc-econ').innerHTML = `<div class="dc-head"><div><h2 id="dc-econ-h">State economies</h2>
        <p class="small">Each state's monthly economic index from the Philadelphia Fed (jobs, unemployment, hours and wages), via FRED. The approval model averages each state's growth over the term, recent quarters counting most.</p></div></div>
      ${lastM ? `<div class="dc-big"><span><b>${lastM.up} of ${lastM.n}</b> states grew in ${monthName(lastM.m)}</span></div>
        <p class="dc-read" id="econ-read" aria-live="polite"></p><div class="dc-chart bars" id="econ-chart"></div>` : ''}
      ${ranked.length ? `<div class="dc-two"><div><h3>Grew most</h3><ul class="dc-list">${ranked.slice(0, 3).map(st).join('')}</ul></div>
        <div><h3>${ranked[ranked.length - 1][1] < 0 ? 'Shrank most' : 'Grew least'}</h3><ul class="dc-list">${ranked.slice(-3).reverse().map(st).join('')}</ul></div></div>` : ''}
      <p class="foot">Change in ${lastM ? monthName(lastM.m) : 'the newest month'} from the month before. The Philadelphia Fed publishes each month about four weeks after it ends; the model uses months through June 2028.</p>`;
    if (M.length) {
      const el = box('econ-chart'), read = box('econ-read');
      const W = el.clientWidth < 480 ? 380 : 600, Ht = 150, l = 30, r = 8, tp = 8, b = 22, bw = (W - l - r) / M.length;
      const y = v => tp + (1 - v / 50) * (Ht - tp - b);
      let o = '';
      [0, 25, 50].forEach(v => { o += `<line x1="${l}" x2="${W - r}" y1="${y(v)}" y2="${y(v)}" stroke="${v === 25 ? '#2a3953' : '#1f2b3e'}"${v === 25 ? ' stroke-dasharray="3 3"' : ''}></line><text x="${l - 6}" y="${y(v) + 4}" text-anchor="end">${v}</text>`; });
      M.forEach((m, i) => {
        const h = y(0) - y(m.up * 50 / m.n);
        o += `<rect data-i="${i}" x="${(l + i * bw + 1.5).toFixed(1)}" y="${(y(0) - h).toFixed(1)}" width="${(bw - 3).toFixed(1)}" height="${h.toFixed(1)}" rx="2" fill="${i === M.length - 1 ? '#f2a65e' : '#3c4f6e'}"></rect>`;
        if (m.m.endsWith('-01')) o += `<text x="${(l + i * bw + bw / 2).toFixed(1)}" y="${Ht - 6}" text-anchor="middle">${m.m.slice(0, 4)}</text>`;
      });
      el.innerHTML = `<svg viewBox="0 0 ${W} ${Ht}" role="img" aria-label="States whose economy grew each month, ${monthName(M[0].m)} to ${monthName(lastM.m)}">${o}</svg>`;
      const say = m => { read.textContent = `${monthName(m.m)}: ${m.up} of ${m.n} states grew; the typical state ${m.median >= 0 ? 'grew' : 'shrank'} ${Math.abs(m.median).toFixed(2)}%`; };
      el.querySelectorAll('rect').forEach(rc => { const m = M[+rc.dataset.i]; rc.addEventListener('pointerenter', () => say(m)); rc.addEventListener('pointerdown', () => say(m)); });
      el.querySelector('svg').addEventListener('pointerleave', () => say(lastM));
      say(lastM);
    }

    // ---- primary polling ----
    const cands = (N.scenario && N.scenario.candidates) || [];
    const side = party => {
      const list = cands.filter(c => c.party === party && c.primary > 0).sort((a, b) => b.primary - a.primary).slice(0, 6);
      const top = list.length ? list[0].primary : 1;
      return `<div><h3 class="${party === 'D' ? 'd-ink' : 'r-ink'}">${party === 'D' ? 'Democrats' : 'Republicans'}</h3>
        <ul class="dc-bars">${list.map(c => `<li><span class="nm">${esc(c.name)}</span><span class="bar"><i class="${party}" style="width:${(100 * c.primary / top).toFixed(1)}%"></i></span><b class="num">${c.primary.toFixed(1)}%</b></li>`).join('')}</ul></div>`;
    };
    box('dc-primary').innerHTML = `<div class="dc-head"><div><h2 id="dc-primary-h">Primary polling</h2>
        <p class="small">${nomineesNote()} The approval model counts each possible nominee's home state by this share.</p></div></div>
      <div class="dc-two">${side('D')}${side('R')}</div>
      <p class="foot">Average share in national primary polls from PollResults.org. Top six in each party.</p>`;

    // ---- what changes next ----
    const nowIso = todayIso();
    const next = window.FORECAST ? [] : EVENTS.map(([d, short, long]) => ({ d, short, long, left: dayDiff(d, nowIso) })).filter(e => e.left >= 0);
    const wait = !window.FORECAST && A.official_wait;
    box('dc-next').innerHTML = `<div class="dc-head"><div><h2 id="dc-next-h">What changes next</h2>
        <p class="small">${window.FORECAST ? 'The days when the inputs switched.' : 'Days when the inputs switch, so the Nowcast can move more than usual.'}</p></div></div>
      ${next.length ? '' : '<p class="small">Nothing more changes: the final forecast is published.</p>'}
      ${wait ? `<p class="note">The approval model moves to polls conducted June 1 to July 30, 2028 once ${wait.needed} pollsters have a poll in that window. So far ${wait.pollsters} ${wait.pollsters === 1 ? 'has' : 'have'}, so it still uses the last 30 days.</p>` : ''}
      <ul class="dc-next">${next.map(e => `<li><span class="days"><b class="num">${e.left}</b>${e.left === 1 ? 'day' : 'days'}</span><span><b>${esc(e.short)}, ${niceDate(e.d)}</b>${esc(e.long)}</span></li>`).join('')}</ul>`;

    // ---- daily log ----
    const pct = v => v === undefined || v === null ? '—' : Math.round(100 * v);
    const logRow = h => `<tr${h.date === N.as_of ? ' class="new"' : ''}><td>${niceDate(h.date)}</td><td class="num">${pct(h.pDemWin)}</td><td class="num">${fmt(h.demPopular)}</td>
      <td class="num">${h.ev ?? '—'}</td><td class="num">${pct(h.enns)}</td><td class="num">${pct(h.desart)}</td>
      <td class="num">${h.approve !== undefined ? fmt(h.approve) : '—'}</td><td class="num">${h.pollAvg ? fmt(h.pollAvg) : '—'}${h.h2hN ? ` <small>(${h.h2hN})</small>` : ''}</td><td class="num">${h.econThrough ? new Date(h.econThrough + '-15').toLocaleDateString('en-US', { month: 'short', year: 'numeric' }) : '—'}</td></tr>`;
    const L = [...H].reverse(), LS = 10;
    box('dc-log').innerHTML = `<div class="dc-head"><div><h2 id="dc-log-h">Daily log</h2>
        <p class="small">The Nowcast and its inputs after each morning's run. Chances are in 100 for the Democrat.</p></div></div>
      <div class="dt-wrap"><table class="dt"><thead><tr><th>Date</th><th class="num">Nowcast</th><th class="num">Vote</th><th class="num">Electoral votes</th><th class="num">Approval model</th><th class="num">Long-range model</th><th class="num">Approval</th><th class="num">Poll average</th><th class="num">Economy through</th></tr></thead>
      <tbody>${L.slice(0, LS).map(logRow).join('')}</tbody><tbody class="more" hidden>${L.slice(LS).map(logRow).join('')}</tbody></table></div>
      ${L.length > LS ? `<button class="btn ghost dc-more" type="button" aria-expanded="false">Show all ${L.length} days</button>` : ''}
      <p class="foot">Columns added in November 2026 are blank for earlier days. Poll average: the Democrat's share of the two-party vote across head-to-head polls, with the number of polls in brackets.</p>`;
    const lm = box('dc-log').querySelector('.dc-more');
    if (lm) lm.addEventListener('click', () => {
      const tb = box('dc-log').querySelector('tbody.more'), open = tb.hidden;
      tb.hidden = !open; lm.setAttribute('aria-expanded', open); lm.textContent = open ? 'Show fewer' : `Show all ${L.length} days`;
    });
  }

  function insp28(a) {
    const el = document.getElementById('insp-2028');
    if (!cur) { el.innerHTML = `<span class="tag">2028 Nowcast</span><h2>Waiting for data</h2><p class="small">This fills in after the first daily data run.</p>`; return; }
    const s = a ? cur.byAbbr[a] : null;
    if (!s) {
      el.innerHTML = `<span class="tag">2028 Nowcast${N.fixture_run ? '<span class="test-flag">TEST DATA</span>' : ''}</span><h2>National picture</h2>
        <dl class="kv">
          <div><dt>Democratic two-party vote</dt><dd class="d-ink">${fmt(cur.demPopular)}</dd></div>
          <div><dt>Democrat wins</dt><dd>${pct(cur.pDemWin)} of simulations</dd></div>
          <div><dt>Trump approval (national avg)</dt><dd>${fmt(N.approval.approve)}</dd></div>
          <div><dt>Economy data through</dt><dd>${monthName(N.economy.through)}</dd></div>
        </dl>
        <div class="strip">${strip({ f: cur.demPopular })}</div>
        ${cur.desart ? modelTable([['State-level approval and fundamentals', cur.enns.demPopular, cur.enns.pDemWin], ['Long-range model', cur.desart.demPopular, cur.desart.pDemWin], ['Nowcast', cur.demPopular, cur.pDemWin, 'avg']], 'the election') : ''}
        <p class="hint">Hover or tap a state for its numbers.</p>`;
      return;
    }
    const r = byAbbr[a], base = N.scenario.states.find(x => x.abbr === a);
    el.innerHTML = `<span class="tag">${dname(a)} · ${r.ev} electoral vote${r.ev > 1 ? 's' : ''}</span><h2>${r.name}</h2>
      <dl class="kv">
        <div><dt>Nowcast D share</dt><dd class="d-ink">${fmt(s.demShare)}</dd></div>
        <div><dt>2024 D share</dt><dd>${fmt(r.share, 2)}</dd></div>
        <div><dt>Democrat wins</dt><dd>${pct(s.pDem)} of simulations</dd></div>
        <div><dt>Rating</dt><dd>${RATING[s.rating] || s.rating}</dd></div>
        ${base ? `<div title="${esc(approvalNote())}"><dt>Trump approval the model uses</dt><dd>${fmt(base.approve + cur.vpShift)}</dd></div>` : ''}
      </dl>
      <div class="strip">${strip({ f: s.demShare, a: r.share })}</div>
      <div class="strip-legend"><span><i class="f"></i>Nowcast</span><span><i class="a"></i>2024 result</span></div>
      ${s.desart != null ? modelTable([['State-level approval and fundamentals', s.enns, s.ennsP], ['Long-range model', s.desart, s.desartP], ['Nowcast', s.demShare, s.pDem, 'avg']], 'the state') : ''}
      ${a === N.scenario.homeLag.rep || a === N.scenario.homeLag.dem ? `<p class="hint">Both models take back part of the 2024 ${a === N.scenario.homeLag.rep ? 'Republican' : 'Democratic'} nominee's home-state boost here, which moves this state toward the ${a === N.scenario.homeLag.rep ? 'Democrat' : 'Republican'}: ${(-window.SPASE.coef('homeLag') * (N.scenario.homeLagWeight || { dem: 1, rep: 1 })[a === N.scenario.homeLag.rep ? 'rep' : 'dem']).toFixed(1)} points in the state-level approval and fundamentals model${s.desart != null ? `, ${window.TP.DESART.home.toFixed(1)} in the long-range model` : ''}.</p>` : ''}`;
  }
  function fill28(a) {
    const s = cur && cur.byAbbr[a];
    if (!s) return greyColor();
    return RATE_COLOR[rateOf(s.pDem)];
  }
  const sub28 = a => { const s = cur && cur.byAbbr[a]; return s ? chance(s.pDem) : ''; };
  function pick28(a) {
    pinned28 = a === pinned28 ? null : a; map28.mark(pinned28); insp28(pinned28);
  }

  const draw28 = () => drawUS(document.getElementById('map-2028'), { fill: fill28, sub: sub28, selected: pinned28, onPick: pick28, onHover: a => { insp28(a || pinned28); map28.mark(a || pinned28); } });

  // Map layers. "Forecast" shows a countdown, not a map, until August 6, 2028.
  function setLayer28(l) {
    layer28 = l;
    document.querySelectorAll('[data-layer28]').forEach(x => x.setAttribute('aria-selected', x.dataset.layer28 === l));
    document.getElementById('desk-28').hidden = l === 'official';
    document.getElementById('official-28').hidden = l !== 'official';
  }
  let counting = FORECAST_DATE > new Date();
  function tickCountdown() {
    const ms = Math.max(0, FORECAST_DATE - new Date());
    // When the countdown runs out with the page open, load the page again once to pick up the forecast.
    if (counting && ms === 0) { counting = false; location.reload(); return; }
    const parts = [[Math.floor(ms / 864e5), 'days'], [Math.floor(ms % 864e5 / 36e5), 'hours'], [Math.floor(ms % 36e5 / 6e4), 'minutes'], [Math.floor(ms % 6e4 / 1e3), 'seconds']];
    document.getElementById('cd-28').innerHTML = parts.map(([v, l], i) => `<div><span class="v num">${i ? String(v).padStart(2, '0') : v}</span><span class="l">${l}</span></div>`).join('');
  }

  // ---------- the 2028 forecast, built up as its data arrives ----------
  // Each paper's own cutoff, by the date polls were conducted: DeSart's polls from October 2027 (fixed Nov 7,
  // 2027), Enns et al.'s approval polls from June 1 to July 30, 2028 and the economy through June. Until it
  // publishes on Aug 6, 2028 the tab shows only the countdown and how far each input has got, with no forecast
  // numbers. The published forecast (docs/forecast.js) is shown as it was and never changes.
  const PUBLISH = '2028-08-06', DS_WIN = ['2027-10-01', '2027-10-31'], DS_FREEZE = '2027-11-07', AP_WIN = ['2028-06-01', '2028-07-30'];
  // Today's date in US Eastern time, the clock the site's cutoffs run on.
  const todayIso = () => new Date().toLocaleDateString('en-CA', { timeZone: 'America/New_York' });
  let mapFc = null;
  function forecastTab() {
    const F = window.FORECAST || null, df = N && N.desart_final, t = todayIso();
    const steps = [];
    const step = (name, what, state, note) => steps.push(`<li class="${state}"><span class="st">${{ wait: 'Not started', open: 'Collecting', done: 'Done' }[state]}</span><div><b>${name}</b><span>${what}</span>${note ? `<em>${note}</em>` : ''}</div></li>`);
    // 1. Long-range model: October 2027 head-to-head polls
    if (F || (df && df.frozen)) {
      const n = F ? F.desart_polls.n : df.polls.length, avg = F ? F.desart_polls.avg : df.polls.reduce((a, p) => a + p.share, 0) / df.polls.length;
      step('Long-range model (DeSart)', 'Head-to-head polls conducted in October 2027', 'done', `Fixed November 7, 2027: ${n} polls averaging ${fmt(avg)} Democratic. The Nowcast uses them from then on.`);
    } else if (df) {
      const n = df.polls.length;
      step('Long-range model (DeSart)', 'Head-to-head polls conducted in October 2027', 'open', `${n ? `${n} poll${n === 1 ? '' : 's'} so far` : 'No polls from the window yet'}. Fixed November 7, 2027.`);
    } else step('Long-range model (DeSart)', 'Head-to-head polls conducted in October 2027', 'wait', 'Starts October 1, 2027.');
    // 2. Approval polls: June 1 - July 30, 2028
    const apState = F ? 'done' : t < AP_WIN[0] ? 'wait' : 'open';
    step('State-level approval and fundamentals (Enns et al.)', 'Trump approval polls conducted June 1 to July 30, 2028', apState,
      F ? `${fmt(F.approval.approve)} approve, from ${F.approval.pollsters} pollsters.` : apState === 'wait' ? 'Starts June 1, 2028.' : N ? `${fmt(N.approval.approve)} approve so far, from ${N.approval.pollsters} pollsters.` : '');
    // 3. State economies through June 2028
    const ec = F ? F.economy.through : N && N.economy.through;
    step('State economies', 'Philadelphia Fed state indexes through June 2028', F || (ec && ec >= '2028-06') ? 'done' : 'open',
      ec ? (F ? `Used data through ${monthName(ec)}.` : `Through ${monthName(ec)}${ec >= '2028-06' ? '' : ' so far'}.`) : '');
    // 4. Tickets
    const tk = F ? F.tickets : N && N.tickets, named = tk ? ['dem', 'rep'].flatMap(s => ['president', 'vp'].map(k => (tk[s] || {})[k]).filter(x => x && x.name)) : [];
    step('Nominees and running mates', 'Read from Wikipedia once confirmed', named.length === 4 || F ? 'done' : named.length ? 'open' : 'wait',
      named.length ? named.map(x => esc(x.name)).join(', ') + (F && named.length < 4 ? '. The rest were not known by the publish date.' : '')
        : F ? 'None were confirmed by the publish date, so each party\'s possible nominees were averaged by their polling.' : 'None confirmed yet.');
    step('Publish', 'August 6, 2028, a week after the last cutoff', F ? 'done' : 'wait', F ? `Published ${niceDate(F.published)}. Final: it does not change.` : 'Polls published a few days late are included. After that, nothing changes.');
    document.getElementById('fc-steps').innerHTML = steps.join('');

    // The forecast itself is shown only once published (docs/forecast.js); until then, only the countdown.
    const R = F ? { ...F.summary, states: F.states, evHistogram: F.evHistogram, models: F.models } : null, label = 'final';
    const body = document.getElementById('fc-body');
    const due = !F && new Date() >= FORECAST_DATE;   // the hour has come but this morning's run has not saved it yet
    document.getElementById('fc-head').innerHTML = F ? 'The 2028 forecast' : due ? 'The official prediction is being published. Check back in a little while.'
      : `The official prediction will be made in <span id="cd-days">${daysTo(FORECAST_DATE)}</span> days`;
    document.getElementById('cd-28').hidden = !!F || due;
    if (!R) { body.hidden = true; return; }
    body.hidden = false;
    const med = R.states.filter(x => x.demShare > 50).reduce((a, x) => a + x.ev, 0);   // each state to whoever is ahead
    const nD = Math.round(100 * R.pDemWin), nT = Math.round(100 * (R.pTie || 0));
    const m = R.models || {};
    body.innerHTML = `<p class="fc-tag ${label}">Final forecast, published ${niceDate(F.published)}</p>
      <div class="fc-figs">
        <div><span class="v d-ink">${nD}</span><span class="l">in 100 for the Democrat</span></div>
        <div><span class="v r-ink">${100 - nD - nT}</span><span class="l">in 100 for the Republican</span></div>
        <div><span class="v">${fmt(R.demPopular)}</span><span class="l">Democratic two-party vote</span></div>
        <div><span class="v">${med}</span><span class="l">Democratic electoral votes</span></div>
      </div>
      <p class="small">Half the state-level approval and fundamentals model (${m.enns ? `${Math.round(100 * m.enns.pDemWin)} in 100, ${fmt(m.enns.demPopular)}` : '—'}), half the long-range model from October 2027 (${m.desart ? `${Math.round(100 * m.desart.pDemWin)} in 100, ${fmt(m.desart.demPopular)}` : '—'}), simulated together.</p>
      <svg class="usmap" id="map-fc" role="img" aria-label="Forecast map by rating"></svg>`;
    const by = Object.fromEntries(R.states.map(s => [s.abbr, s]));
    mapFc = () => drawUS(document.getElementById('map-fc'), { fill: a => by[a] ? RATE_COLOR[rateOf(by[a].pDem)] : greyColor(), sub: a => by[a] ? chance(by[a].pDem) : '',
      selected: null, onPick: () => {}, onHover: () => {} });
    mapFc();
  }

  // After the final forecast publishes, the Nowcast is frozen with it (the daily run stops), so the Nowcast
  // views become the final forecast: relabelled, with the Forecast tab and countdown no longer needed.
  function finalLabels() {
    const F = window.FORECAST;
    if (!F) return;
    const when = niceDate(F.published);
    const set = (sel, txt) => document.querySelectorAll(sel).forEach(el => { el.textContent = txt; });
    document.querySelectorAll('a[data-view="nowcast"]').forEach(a => { a.innerHTML = '<span class="nl">2028 forecast</span><span class="ns">Forecast</span>'; a.setAttribute('aria-label', '2028 forecast'); });
    set('#title-28', '2028 forecast');
    set('[data-layer28="tracker"]', '2028 forecast');
    set('[data-snake="today"]', '2028 forecast');
    set('#hero-live', 'Final 2028 forecast');
    const lede = document.getElementById('lede-28');
    if (lede) lede.innerHTML = `The final forecast, published ${when}: two published models, averaged state by state, each on its own paper's data. Approval polls conducted June 1 to July 30, 2028 and the economy through June (Enns et al.); head-to-head polls conducted in October 2027 (DeSart). <strong>It does not change.</strong>`;
    const tab = document.querySelector('[data-layer28="official"]');
    if (tab) tab.hidden = true;
  }

  function render2028() {
    const days = daysTo(FORECAST_DATE);
    const dEl = document.getElementById('d-forecast');
    if (dEl && days < 1) { const p = dEl.parentNode; p.innerHTML = p.innerHTML.replace(/, in <span id="d-forecast"><\/span> days\./, ' today.'); } else if (dEl) dEl.textContent = days;
    document.getElementById('cd-days').textContent = days;
    tickCountdown(); setInterval(tickCountdown, 1000);
    map28 = draw28();
    ramp(document.getElementById('ramp-2028'), 'nowcast');
    document.querySelectorAll('[data-layer28]').forEach(b => b.addEventListener('click', () => setLayer28(b.dataset.layer28)));
    document.getElementById('btn-to-nowcast').addEventListener('click', () => setLayer28('tracker'));
    try { forecastTab(); } catch (e) { console.error('forecast tab', e); }
    if (!N) {
      ['hero-28', 'jump-28', 'results-detail', 'tracker-detail'].forEach(id => { document.getElementById(id).hidden = true; });
      document.getElementById('live-pill').textContent = 'Waiting for the first data run';
      setLayer28('official'); return;
    }
    document.getElementById('live-pill').textContent = window.FORECAST ? `Final · published ${niceDate(window.FORECAST.published)}` : `Live · updated ${niceDate(N.generated_at)}`;
    finalLabels();
    document.getElementById('live-inputs').innerHTML = `<b>Live data (automatic):</b> National approval ${fmt(N.approval.approve)} from ${N.approval.pollsters} pollsters' polls of all adults through ${niceDate(N.approval.window[1])} · state-by-state differences from ${N.approval.state_data && N.approval.state_data.as_of ? `<a href="${N.approval.state_data.url}">Civiqs</a> through ${niceDate(N.approval.state_data.as_of)}` : 'Civiqs'}${gapSize(N.approval.state_data) ? `, counted at ${gapSize(N.approval.state_data)}` : ''} · state economies through ${monthName(N.economy.through)}.`;
    // Jump links, with the section on screen marked.
    const jump = [...document.querySelectorAll('#jump-28 button')];
    jump.forEach(b => b.addEventListener('click', () => document.getElementById(b.dataset.to).scrollIntoView({ behavior: still ? 'auto' : 'smooth', block: 'start' })));
    if ('IntersectionObserver' in window) {
      const seen = {};
      const io = new IntersectionObserver(es => {
        es.forEach(e => { seen[e.target.id] = e.isIntersecting; });
        const on = jump.filter(b => seen[b.dataset.to]).pop();
        jump.forEach(b => b.setAttribute('aria-current', b === on));
      }, { rootMargin: '-130px 0px -55% 0px' });
      jump.forEach(b => io.observe(document.getElementById(b.dataset.to)));
    }
    // From Nov 7, 2027 the long-range model runs on DeSart's fixed October 2027 polls; until then the latest 180 days.
    const DF = N.desart_final && N.desart_final.frozen && N.desart_final.polls.length ? N.desart_final : null;
    const hp = DF ? DF.polls : (N.h2h && N.h2h.polls) || [];
    matchups(document.getElementById('mx-2028'), document.getElementById('mx-note'), hp, !!DF);
    const tb = document.getElementById('h2h-2028'), more = document.getElementById('h2h-more');
    const showPolls = all => {
      tb.innerHTML = (all ? hp : hp.slice(0, 10)).map(q => `<tr><td class="num">${q.date}</td><td>${pollsterCell(q.pollster)}</td><td class="mu">${esc(pollName(q.d))} vs. ${esc(pollName(q.r))}</td><td class="n"><span class="bar" aria-hidden="true"><i class="${q.share > 50 ? 'D' : 'R'}" style="width:${Math.min(50, Math.abs(q.share - 50) * 8).toFixed(1)}%"></i></span>${fmt(q.share)}</td></tr>`).join('');
      more.hidden = all || hp.length <= 10;
      more.textContent = `Show all ${hp.length} polls`;
    };
    more.addEventListener('click', () => showPolls(true));
    showPolls(false);
    document.getElementById('h2h-note').innerHTML = DF
      ? `The Democrat's share of the two-party vote in each poll. These are the polls DeSart's model uses: national polls between one named Democrat and one named Republican conducted in October 2027, fixed on November 7, 2027, from <a href="https://pollresults.org/races/president-2028/">PollResults.org</a> (New York Times poll data, CC BY 4.0). ${DF.skipped} other questions were left out: generic party ballots, questions that name a third candidate, and pairings with a two-term president.`
      : hp.length
      ? `The Democrat's share of the two-party vote in each poll. National polls between one named Democrat and one named Republican from the last ${N.h2h.days} days, from <a href="https://pollresults.org/races/president-2028/">PollResults.org</a> (New York Times poll data, CC BY 4.0). ${N.h2h.skipped ? `${N.h2h.skipped} other questions are left out: generic party ballots, questions that name a third candidate, and pairings with a two-term president, who cannot run again.` : ''}`
      : 'No head-to-head polls are available today, so the Nowcast is the state-level approval and fundamentals model on its own.';
    const t = N.tickets, set = ['dem', 'rep'].filter(s => t[s] && t[s].president).length;
    document.getElementById('need-tickets').textContent = set ? `Confirmed: ${set === 2 ? 'both nominees' : 'one nominee'}` : 'Watching, none yet';
    document.getElementById('need-vp').textContent = N.vp.applied ? `On, ${sgn(N.vp.gap, 1)} pts` : N.vp.gap != null ? `Standing by, ${sgn(N.vp.gap, 1)} pts` : 'No recent polls of the vice president';
    const nh = document.getElementById('need-h2h');
    if (nh) nh.textContent = DF ? `Fixed November 7, 2027: ${DF.polls.length} October polls` : N.h2h && N.h2h.polls.length ? (N.h2h.stale ? `Today's read failed; using the last good copy, ${N.h2h.polls.length} polls` : `Daily, ${N.h2h.polls.length} polls in the window`) : 'No polls available today';
    document.getElementById('need-econ').textContent = `Daily, through ${monthName(N.economy.through)}`;
    document.getElementById('need-cands').textContent = `Daily, ${N.scenario.candidates.filter(c => c.primary).length} names in primary polls`;
    document.getElementById('polls-2028').innerHTML = N.approval.polls.map(p =>
      `<tr><td>${p.url ? `<a href="${esc(p.url)}">${pollsterCell(p.pollster)}</a>` : pollsterCell(p.pollster)}</td><td class="num">${p.date}</td><td class="n">${Number(p.approve).toFixed(1)}</td><td class="n">${Number(p.disapprove).toFixed(1)}</td></tr>`).join('');
    const H = window.NOWCAST_HISTORY || [];
    trendChart(document.getElementById('trend-2028'), document.getElementById('trend-note'), H);
    schedule();
  }

  // Map style switch (state outlines or hexagons), shared by both maps.
  document.querySelectorAll('[data-mapmode]').forEach(x => x.setAttribute('aria-pressed', x.dataset.mapmode === mapMode));
  document.querySelectorAll('[data-mapmode]').forEach(b => b.addEventListener('click', () => {
    mapMode = b.dataset.mapmode;
    document.querySelectorAll('[data-mapmode]').forEach(x => x.setAttribute('aria-pressed', x.dataset.mapmode === mapMode));
    if (map24) map24 = draw24();
    if (map28) map28 = draw28();
    if (mapFc) mapFc();
    modelMaps.forEach(f => f());
  }));

  // Method page: a contents list built from its section headings.
  (function methodContents() {
    const view = document.getElementById('view-method');
    if (!view) return;
    const heads = [...view.querySelectorAll('h2')];
    const slug = t => 'm-' + t.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
    heads.forEach(h => { if (!h.id) h.id = slug(h.textContent); });
    const nav = document.createElement('div');
    nav.className = 'toc'; nav.setAttribute('role', 'navigation'); nav.setAttribute('aria-label', 'On this page');
    nav.innerHTML = '<b>On this page</b><ol>' + heads.map(h => `<li><a href="#method" data-to="${h.id}">${esc(h.textContent)}</a></li>`).join('') + '</ol>';
    const lede = view.querySelector('.lede');
    (lede ? lede.parentNode : view).appendChild(nav);
    nav.addEventListener('click', e => {
      const a = e.target.closest('a[data-to]');
      if (!a) return;
      e.preventDefault();
      document.getElementById(a.dataset.to).scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  })();

  // Contact card: the header button opens it; Esc, the close button or a click outside closes it.
  (function contact() {
    const dlg = document.getElementById('contact'), open = document.getElementById('contact-open');
    if (!dlg || !open || typeof dlg.showModal !== 'function') return;
    open.addEventListener('click', () => dlg.showModal());
    document.getElementById('contact-close').addEventListener('click', () => dlg.close());
    dlg.addEventListener('click', e => { if (e.target === dlg) dlg.close(); });
  })();

  // ================= routing =================
  const VIEWS = ['home', 'nowcast', 'models', 'data', 'archive', 'method'];
  const done = {};
  function route() {
    let h = location.hash.replace('#', '');
    if (h === 'forecast-2028') h = 'nowcast';   // old address
    if (h === 'results-2024') h = 'archive';    // old address: the 2024 scorecard is the Archive's first page
    const v = VIEWS.includes(h) ? h : 'home';
    VIEWS.forEach(n => document.getElementById('view-' + n).hidden = n !== v);
    document.querySelectorAll('nav a').forEach(a => a.dataset.view === v ? a.setAttribute('aria-current', 'page') : a.removeAttribute('aria-current'));
    const here = document.querySelector(`nav a[data-view="${v}"]`), name = here && v !== 'home' ? (here.querySelector('.nl') || here).textContent.trim() : '';
    document.title = name ? `${name} | Tipping Point` : 'Tipping Point';
    if (!done[v]) {
      if (v === 'home') renderHome();
      if (v === 'archive') render2024();
      if (v === 'data') renderData();
      // The models page reads the same simulation as the Nowcast, so it starts that run too.
      if ((v === 'nowcast' || v === 'models') && !done.nowcast) { render2028(); done.nowcast = true; }
      if (v === 'models' && !N) document.getElementById('models-each').innerHTML = '<p class="small">This fills in after the first daily data run.</p>';
      done[v] = true;
    }
    refit();   // a page that was hidden while the window changed size lays out its names now
    window.scrollTo(0, 0);
    if (goTo) { const id = goTo; goTo = null; scrollToWhenReady(id); }
  }
  // A link can ask to land on one part of a page (data-goto). The page may still be drawing, so keep
  // scrolling to that part until its position settles, and stop if the reader scrolls themselves.
  // Skip link: the address bar belongs to the pages, so move focus to the content without touching it.
  const skip = document.querySelector('.skip');
  if (skip) skip.addEventListener('click', e => { e.preventDefault(); const m = document.getElementById('main'); m.focus({ preventScroll: true }); m.scrollIntoView(); });
  // Left and right arrows move between tabs, on every set of tabs.
  document.addEventListener('keydown', e => {
    const t = e.target.closest && e.target.closest('[role="tab"]');
    if (!t || (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft')) return;
    const all = [...t.closest('[role="tablist"]').querySelectorAll('[role="tab"]:not(:disabled)')];
    const next = all[(all.indexOf(t) + (e.key === 'ArrowRight' ? 1 : all.length - 1)) % all.length];
    e.preventDefault(); next.focus(); next.click();
  });
  let goTo = null;
  document.addEventListener('click', ev => { const a = ev.target.closest && ev.target.closest('a[data-goto]'); if (a) goTo = a.dataset.goto; });
  function scrollToWhenReady(id) {
    let tries = 0, lastTop = null, steady = 0, stop = false;
    const quit = () => { stop = true; };
    ['wheel', 'touchstart', 'keydown'].forEach(e => window.addEventListener(e, quit, { once: true, passive: true }));
    const step = () => {
      const el = document.getElementById(id);
      if (stop || !el || tries++ > 60) return;
      const top = Math.round(el.getBoundingClientRect().top + window.scrollY);
      el.scrollIntoView({ block: 'start' });
      steady = top === lastTop ? steady + 1 : 0; lastTop = top;
      if (steady < 10) setTimeout(step, 150);
    };
    step();
  }
  // The day the copy of Civiqs's state figures was taken, wherever the text gives it.
  const civiqsDay = N && N.approval && N.approval.state_data && N.approval.state_data.as_of;
  if (civiqsDay) {
    const long = new Date(civiqsDay + 'T12:00:00').toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
    document.querySelectorAll('[data-civiqs-date]').forEach(e => { e.textContent = long; });
  }
  window.addEventListener('hashchange', route);
  finalLabels();
  route();
})();
