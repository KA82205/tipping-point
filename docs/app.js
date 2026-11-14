(function () {
  const R = window.RESULTS_2024;
  const NAT = window.NATIONAL_2024;
  const SHAPES = window.US_STATES;
  const N = window.NOWCAST;
  const byAbbr = Object.fromEntries(R.map(r => [r.abbr, r]));
  const natActual = 100 * NAT.dem / (NAT.dem + NAT.rep);
  // The 2024 scorecard has two forecasts to score: 'pub', the state-level approval and fundamentals model's forecast as its
  // authors published it, and 'bt', the Nowcast's method applied to 2024 (docs/backtest2024.js).
  const BT = window.BACKTEST_2024 || null, F24 = ['fc', 'lo', 'hi', 'pDem', 'rating'];
  // 'ds': DeSart's long-range model as he published it (November 2023), also from docs/backtest2024.js.
  const DS = BT && BT.desartPub ? BT.desartPub : null;
  R.forEach(r => { r.pub = Object.fromEntries(F24.map(k => [k, r[k]])); r.bt = BT && BT.states[r.abbr] ? BT.states[r.abbr] : null; r.ds = DS && DS.states[r.abbr] ? DS.states[r.abbr] : null; });
  NAT.pub = { fc: NAT.fc, pDemWin: NAT.pDemWin }; NAT.bt = BT ? BT.national : null; NAT.ds = DS ? DS.national : null;
  let src24 = 'pub';
  function useSrc24(k) {
    src24 = k === 'bt' && BT ? 'bt' : k === 'ds' && DS ? 'ds' : 'pub';
    R.forEach(r => F24.forEach(f => { r[f] = (r[src24] || r.pub)[f]; }));
    NAT.fc = NAT[src24].fc; NAT.pDemWin = NAT[src24].pDemWin;
  }
  const TOSS = '#d9b23f';   // toss-ups in the Nowcast are gold, not the color of whoever is a hair ahead
  const isToss = p => Math.max(p, 1 - p) <= 0.55;
  // The 2028 map is colored by rating: darker means safer, and the light shades and gold mark the close states.
  const RATE_COLOR = { SD: '#2e64b0', LD: '#4f8de0', TD: '#a9c8f0', TOSS: TOSS, TR: '#f2aaa1', LR: '#d8665b', SR: '#a63f37' };
  const LIGHT = new Set([RATE_COLOR.TD, TOSS, RATE_COLOR.TR]);   // fills that need dark text
  // Any fill light enough to need dark text: '#rrggbb' or 'rgb(r,g,b)', by relative luminance.
  const isLight = c => {
    if (!c) return false;
    const v = c[0] === '#' ? [1, 3, 5].map(i => parseInt(c.slice(i, i + 2), 16)) : (c.match(/\d+/g) || []).slice(0, 3).map(Number);
    const L = v.map(x => { x /= 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); });
    return 0.2126 * L[0] + 0.7152 * L[1] + 0.0722 * L[2] > 0.4;
  };
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
  function snake(el, readEl, items, label, onPick) {
    const { rows, tp } = tippingOf(items);
    const demEV = rows.filter(r => r.share > 50).reduce((a, r) => a + r.ev, 0);
    el.innerHTML = rows.map(r => `<div class="seg${r === tp ? ' tp' : ''}${r.ev < 19 ? ' sm' : ''}${r.toss || isLight(r.col || shareColor(r.share)) ? ' toss' : ''}" data-a="${r.abbr}" style="flex:${r.ev} 0 0;background:${r.col || (r.toss ? TOSS : shareColor(r.share))}" tabindex="0" aria-label="${esc(byAbbr[r.abbr].name)} ${fmt(r.share)} Democratic">${r.ev >= 9 ? dname(r.abbr) : ''}</div>`).join('') +
      `<div class="mark270" style="left:${270 / 538 * 100}%"></div>`;
    const tpName = byAbbr[tp.abbr].name.replace(' District', '');
    const winner = tp.share > 50 ? 'Democrats' : 'Republicans';
    const base = `${label}: the tipping point is <b>${esc(tpName)}</b> at ${fmt(tp.share)} Democratic, so <b>${winner}</b> reach 270 (${demEV} Democratic electoral votes).`;
    readEl.innerHTML = base;
    el.querySelectorAll('.seg').forEach(s => {
      const r = rows.find(x => x.abbr === s.dataset.a);
      const show = () => { readEl.innerHTML = `<b>${esc(byAbbr[r.abbr].name)}</b> · ${r.ev} EV · ${fmt(r.share)} Democratic · Democrats reach ${r.after} electoral votes if they win every state up to here`; };
      s.addEventListener('mouseenter', show); s.addEventListener('focus', show);
      s.addEventListener('mouseleave', () => { readEl.innerHTML = base; }); s.addEventListener('blur', () => { readEl.innerHTML = base; });
      if (onPick) { s.addEventListener('click', () => onPick(r.abbr)); s.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onPick(r.abbr); } }); }
    });
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

  function drawUS(svg, { fill, sub, onPick, onHover, selected }) {
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
    o += `<text class="grp" x="${bx}" y="${dy0 - 8}">Districts</text>`;
    DISTRICTS.forEach((a, i) => {
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
  const BALANCE = `<div class="bal-top"><div class="side d"><span class="big" data-k="dem"></span><span class="l">in 100<b>Democrat wins</b></span></div>
    <div class="side r"><span class="l">in 100<b>Republican wins</b></span><span class="big" data-k="rep"></span></div></div>
    <div class="bal-stage"><div class="bal-arm"><div class="snake"></div></div><div class="bal-fulcrum" aria-hidden="true"><span>270</span></div></div>
    <p class="snake-read"></p>`;
  const tiltOf = d => -Math.sign(d) * 5 * Math.pow(Math.min(1, Math.abs(d)), 0.6);
  function balance(el, items, label, pDem, pRep, onPick) {
    if (!el.firstChild) el.innerHTML = BALANCE;
    const whole = v => String(Math.round(100 * v));
    countTo(el.querySelector('[data-k="dem"]'), pDem, whole);
    countTo(el.querySelector('[data-k="rep"]'), pRep, whole);
    snake(el.querySelector('.snake'), el.querySelector('.snake-read'), items, label, onPick);
    const arm = el.querySelector('.bal-arm');
    setTimeout(() => { arm.style.transform = `rotate(${tiltOf(pDem - pRep).toFixed(2)}deg)`; }, 80);
  }
  // The models and their average, side by side. m: { enns, desart, now }, each { pDemWin, demPopular } or null.
  const MODELS = [['enns', 'State-level approval and fundamentals model', 'Enns, Colner, Kumar and Lagodny'], ['desart', 'Long-range model', 'DeSart']];
  function ensemble(el, m) {
    const card = (cls, name, by, x) => `<div class="ens ${cls}"><span class="nm">${name}</span><span class="by">${by}</span>
      <span class="odds"><b>${Math.round(100 * x.pDemWin)}</b> in 100 for the Democrat</span><span class="split" aria-hidden="true"><i style="width:${(100 * x.pDemWin).toFixed(1)}%"></i></span>
      <span class="vote">${fmt(x.demPopular)} of the two-party vote</span></div>`;
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
    ['2027-11-07', 'Long-range model locks', 'The long-range model switches to DeSart\'s October 2027 polls and stops changing.'],
    ['2028-06-01', 'Approval window', 'The approval model switches to polls conducted June 1 to July 30, as the paper does.'],
    ['2028-08-06', 'Final', 'The final forecast publishes and stops changing.'],
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
      const chips = rows.map(s => `<button type="button" data-a="${s.abbr}"${LIGHT.has(RATE_COLOR[k]) ? ' class="toss"' : ''} style="background:${RATE_COLOR[k]}" title="${esc(byAbbr[s.abbr].name)}: ${fmt(s.demShare)} Democratic, ${s.ev} EV">${dname(s.abbr)}</button>`).join('');
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
  const FORECAST_DATE = new Date('2028-08-06T09:00:00-04:00');   // 9 AM ET Aug 6, 2028: by then that morning's run has published it
  const ELECTION_DATE = new Date('2028-11-07T00:00:00-05:00');
  const daysTo = d => Math.max(0, Math.floor((d - new Date()) / 86400000));
  const monthName = ym => new Date(ym + '-15').toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
  const niceDate = iso => new Date(iso.length === 10 ? iso + 'T12:00:00' : iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });

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
      balance(hb, views.today[0], views.today[1], s.pDemWin, rep, () => { location.hash = 'nowcast'; });
      ensemble(document.getElementById('ens-home'), { enns: M.enns || s, desart: M.desart || null, now: s });
      MODELS.forEach(([k]) => { const el = document.getElementById('odds-' + k); if (el && M[k]) el.textContent = Math.round(100 * M[k].pDemWin); });
      document.getElementById('hero-date').textContent = window.FORECAST ? `Published ${niceDate(window.FORECAST.published)}. Final: it does not change.` : `Updated ${niceDate(N.generated_at)}. Not the forecast, which publishes August 6, 2028.`;
      if (window.FORECAST) document.getElementById('hero-live').textContent = 'Final 2028 forecast';
      setGlow(s.pDemWin, rep);
    } else {
      balance(hb, views.fc[0], '2024 forecast', NAT.pub.pDemWin, 1 - NAT.pub.pDemWin);
      document.getElementById('hero-live').textContent = 'The 2024 forecast, as published in July 2024';
      document.getElementById('hero-date').textContent = 'The 2028 Nowcast starts with its first daily data run.';
      document.getElementById('ens-home').hidden = true;
    }
    const tabs = document.querySelectorAll('[data-snake]');
    const show = k => { const v = views[k] || views.fc; tabs.forEach(t => t.setAttribute('aria-selected', t.dataset.snake === k)); snake(document.getElementById('snake-home'), document.getElementById('snake-home-read'), v[0], v[1]); };
    tabs.forEach(t => { if (t.dataset.snake === 'today' && !views.today) t.disabled = true; t.addEventListener('click', () => show(t.dataset.snake)); });
    show('fc');   // the 2028 line-up is the balance at the top of the page
  }

  // ================= 2024 =================
  let layer24 = 'forecast', pinned24 = null, map24;
  const err = r => r.fc - r.share;
  const repEV24 = () => 538 - R.filter(r => r.fc > 50).reduce((a, r) => a + r.ev, 0);

  function insp24(a) {
    const el = document.getElementById('insp-2024');
    if (!a) {
      const e = NAT.fc - natActual;
      el.innerHTML = `<span class="tag">United States · 538 electoral votes</span><h3>National vote</h3>
        <dl class="kv">
          <div><dt>Forecast D share</dt><dd class="d-ink">${fmt(NAT.fc, 2)}</dd></div>
          <div><dt>Actual D share</dt><dd class="d-ink">${fmt(natActual, 2)}</dd></div>
          <div><dt>Forecast R share</dt><dd class="r-ink">${fmt(100 - NAT.fc, 2)}</dd></div>
          <div><dt>Signed error (pred − actual)</dt><dd class="a-ink">${sgn(e)} pts</dd></div>
          <div><dt>Electoral votes</dt><dd>Trump ${repEV24()} · actual 312</dd></div>
          <div><dt>Trump win chance</dt><dd>${Math.round(100 * (1 - NAT.pDemWin))}%</dd></div>
        </dl>
        <div class="stack" style="gap:6px"><div class="strip-scale num"><span>30%</span><span>50%</span><span>70%</span></div><div class="strip">${strip({ f: NAT.fc, a: natActual })}</div></div>
        <div class="strip-legend"><span><i class="f"></i>Forecast</span><span><i class="a"></i>Actual</span></div>
        ${src24 === 'ds' ? `<p class="hint">The odds are reproduced from DeSart's own simulation script, which draws every state independently around its forecast. His national vote adds the states by his own turnout weights.</p>` : ''}
        ${src24 === 'bt' ? `<p class="hint">A back-test, not a forecast anyone published. State by state it averages two forecasts that were published: the state-level approval and fundamentals model (July 2024) and DeSart's long-range model (November 2023). Their national votes were ${fmt(NAT.bt.enns)} and ${fmt(NAT.bt.desart)}.</p>` : ''}
        <p class="hint">Hover or click a state for its numbers.</p>`;
      return;
    }
    const r = byAbbr[a], e = err(r), ok = (r.fc > 50) === (r.share > 50);
    el.innerHTML = `<span class="tag">${dname(a)} · ${r.ev} electoral vote${r.ev > 1 ? 's' : ''}</span><h3>${r.name}</h3>
      <dl class="kv">
        <div><dt>Forecast D share</dt><dd class="d-ink">${fmt(r.fc, 2)}</dd></div>
        <div><dt>Actual D share</dt><dd class="d-ink">${fmt(r.share, 2)}</dd></div>
        ${src24 === 'bt' ? `<div><dt>State-level approval and fundamentals, published</dt><dd>${fmt(r.pub.fc, 2)}</dd></div>${r.bt.desart != null ? `<div><dt>DeSart long-range model, published</dt><dd>${fmt(r.bt.desart, 2)}</dd></div>` : ''}` : `<div><dt>Forecast R share</dt><dd class="r-ink">${fmt(100 - r.fc, 2)}</dd></div>`}
        <div><dt>Signed error (pred − actual)</dt><dd class="a-ink">${sgn(e)} pts</dd></div>
        <div><dt>Rating</dt><dd>${RATING[r.rating]}</dd></div>
        <div><dt>Harris win chance</dt><dd>${Math.round(100 * r.pDem)}%</dd></div>
        <div><dt>90% range</dt><dd>${r.lo.toFixed(1)}–${r.hi.toFixed(1)}%</dd></div>
        <div><dt>Call</dt><dd style="color:${ok ? 'var(--ok)' : 'var(--rep-ink)'}">${ok ? 'Correct' : 'Missed'}</dd></div>
        ${src24 === 'ds' && r.ds && r.ds.district ? `<p class="hint" style="grid-column:1/-1">DeSart forecasts states only. This district is his ${byAbbr[a.slice(0, 2)].name} forecast moved by the district's gap from the state in the state-level approval and fundamentals forecast.</p>` : ''}
      </dl>
      <div class="stack" style="gap:6px"><div class="strip-scale num"><span>30%</span><span>50%</span><span>70%</span></div><div class="strip">${strip({ f: r.fc, a: r.share, lo: r.lo, hi: r.hi })}</div></div>
      <div class="strip-legend"><span><i class="f"></i>Forecast</span><span><i class="a"></i>Actual</span><span><i class="b"></i>90% range</span></div>
      ${pinned24 ? '<button class="btn" id="unpin24" style="justify-self:start">Show national</button>' : ''}`;
    const u = document.getElementById('unpin24');
    if (u) u.onclick = () => pick24(null);
  }
  const fill24 = a => { const r = byAbbr[a]; return layer24 === 'forecast' ? shareColor(r.fc) : layer24 === 'actual' ? shareColor(r.share) : errColor(err(r)); };
  function pick24(a) {
    pinned24 = a === pinned24 ? null : a;
    map24.mark(pinned24); insp24(pinned24);
    document.querySelectorAll('#rows-2024 .st-row').forEach(x => x.classList.toggle('on', x.dataset.a === pinned24));
  }
  function snake24() {
    const actual = layer24 === 'actual';
    snake(document.getElementById('snake-2024'), document.getElementById('snake-2024-read'),
      R.map(r => ({ abbr: r.abbr, ev: r.ev, share: actual ? r.share : r.fc })), actual ? '2024 result' : '2024 forecast');
  }

  let filter24 = 'all', sort24 = { k: 'fc', dir: -1 };
  function rows24() {
    let rows = R.slice();
    if (filter24 === 'comp') rows = rows.filter(r => !r.rating.startsWith('S'));
    const key = r => sort24.k === 'name' ? r.name : sort24.k === 'err' ? Math.abs(err(r)) : r[sort24.k];
    rows.sort((x, y) => (key(x) > key(y) ? 1 : key(x) < key(y) ? -1 : 0) * sort24.dir);
    const line = (a, name, ev, o, f, s, e, cls = '') =>
      `<div class="st-row ${cls}" data-a="${a}" tabindex="0" role="button" aria-label="${name}"><div class="nm">${name}${a && a.length === 2 ? `<small>${a}</small>` : ''}</div><div class="n">${ev}</div>` +
      `<div class="strip">${strip(o)}</div><div class="n a-ink">${f.toFixed(1)}</div><div class="n">${s.toFixed(1)}</div><div class="n">${sgn(e, 1)}</div></div>`;
    let h = line('', 'National vote', 538, { f: NAT.fc, a: natActual }, NAT.fc, natActual, NAT.fc - natActual, 'nat');
    h += rows.map(r => line(r.abbr, r.name.replace(' District', ''), r.ev, { f: r.fc, a: r.share, lo: r.lo, hi: r.hi }, r.fc, r.share, err(r), r.abbr === pinned24 ? 'on' : '')).join('');
    const box = document.getElementById('rows-2024');
    box.innerHTML = h;
    box.querySelectorAll('.st-row').forEach(el => {
      const go = () => { pick24(el.dataset.a || null); document.getElementById('map-2024').scrollIntoView({ behavior: 'smooth', block: 'center' }); };
      el.addEventListener('click', go);
      el.addEventListener('keydown', e => { if (e.key === 'Enter') go(); });
    });
  }

  const draw24 = () => drawUS(document.getElementById('map-2024'), { fill: fill24, selected: pinned24, onPick: pick24, onHover: a => { insp24(a || pinned24); map24.mark(a || pinned24); } });

  const LEDE24 = {
    bt: 'What the Nowcast\'s method would have said in 2024. State by state it averages two forecasts published before the election: the state-level approval and fundamentals forecast from July 2024 and Jay DeSart\'s long-range model forecast from November 2023. Nobody published this average at the time, so it is a back-test.',
    pub: 'The state-level approval and fundamentals forecast as Enns, Colner, Kumar and Lagodny published it in July 2024, with data from 100 days before the election.',
    ds: 'The long-range model\'s forecast as Jay DeSart published it in November 2023, a year before the election, from head-to-head polls taken the month before. It forecasts the 50 states and DC; the five districts in Maine and Nebraska are filled in from the state-level approval and fundamentals forecast.',
  };
  function figs24() {
    const st = R.filter(r => r.abbr.length === 2);
    const mae = st.reduce((s, r) => s + Math.abs(err(r)), 0) / st.length;
    const inside = R.filter(r => r.share >= r.lo && r.share <= r.hi).length;
    const correct = R.filter(r => (r.fc > 50) === (r.share > 50)).length, ev = repEV24();
    document.getElementById('figs-2024').innerHTML = [
      [`${correct}/${R.length}`, 'States and districts called'],
      [ev === 312 ? '312 = 312' : `${ev} vs 312`, 'Trump electoral votes, forecast and actual'],
      [`${mae.toFixed(1)} pts`, 'Average state miss'],
      [`${inside}/${R.length}`, 'Results inside the 90% range'],
    ].map(([v, l]) => `<div><span class="v">${v}</span><span class="l">${l}</span></div>`).join('');
    document.getElementById('lede-2024').textContent = LEDE24[src24] + ' Pick a state on the map or in the list to compare its forecast and result.';
    document.querySelector('[data-layer="forecast"]').textContent = src24 === 'bt' ? 'Back-test forecast' : 'Published forecast';
    document.getElementById('lede-2024').dataset.src = src24;
    document.querySelectorAll('[data-src24]').forEach(x => x.setAttribute('aria-selected', x.dataset.src24 === src24));
  }

  function render2024() {
    useSrc24('bt');
    figs24();
    const srcTabs = document.querySelectorAll('[data-src24]');
    if (!BT) srcTabs.forEach(x => { x.parentElement.hidden = true; });
    if (!DS) srcTabs.forEach(x => { if (x.dataset.src24 === 'ds') x.hidden = true; });
    srcTabs.forEach(b => b.addEventListener('click', () => {
      useSrc24(b.dataset.src24); figs24();
      map24.recolor(fill24); insp24(pinned24); snake24(); rows24();
    }));

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
    balance(document.getElementById('bal-28'), items, window.FORECAST ? '2028 forecast' : '2028 Nowcast', s.pDemWin, rep, toMap);
    ensemble(document.getElementById('ens-28'), { enns: s.enns || s, desart: s.desart, now: s });
    setGlow(s.pDemWin, rep);
    waffle(document.getElementById('waffle-28'), s.pDemWin, s.pTie);
    document.getElementById('waffle-cap').textContent = `Out of 100 simulated elections held today, the Democrat wins ${nD} and the Republican wins ${100 - nD - nT}${nT ? `, with ${nT} tied` : ''}. A simulation is one possible outcome given how far off the models have been in the past.`;
    const mo = document.getElementById('models-28');
    if (mo) mo.innerHTML = s.desart
      ? `Each state's number is the average of the state-level approval and fundamentals model and the long-range model, half each. The whole map is then simulated together, so the Nowcast's odds are not simply the average of the two models' odds. ${nomineesNote()} ${s.desart ? POLLS_NOTE(s.info) : ''} <a href="#method">How they work</a>`
      : `Today's Nowcast is the state-level approval and fundamentals model on its own, because no head-to-head polls are available. <a href="#method">How it works</a>`;
    document.getElementById('figs-2028').innerHTML = [
      [fmt(s.demPopular), 'Democratic share of the two-party vote'],
      [`${evPoint}`, 'Democratic electoral votes, each state to the candidate ahead in it'],
      [esc(byAbbr[tp.abbr].name.replace(' District', '')), `Tipping-point state, ${fmt(tp.share)} Democratic`],
    ].map(([v, l]) => `<div><span class="v">${v}</span><span class="l">${l}</span></div>`).join('');
    board(document.getElementById('board-28'), s.states, toMap);
    histogram(document.getElementById('hist-2028'), s.evHistogram);
    if (map28 && layer28 !== 'official') map28.recolor(fill28, sub28);
    insp28(pinned28);
  }

  function insp28(a) {
    const el = document.getElementById('insp-2028');
    if (!cur) { el.innerHTML = `<span class="tag">2028 Nowcast</span><h3>Waiting for data</h3><p class="small">This fills in after the first daily data run.</p>`; return; }
    const s = a ? cur.byAbbr[a] : null;
    if (!s) {
      el.innerHTML = `<span class="tag">2028 Nowcast${N.fixture_run ? '<span class="test-flag">TEST DATA</span>' : ''}</span><h3>National picture</h3>
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
    el.innerHTML = `<span class="tag">${dname(a)} · ${r.ev} electoral vote${r.ev > 1 ? 's' : ''}</span><h3>${r.name}</h3>
      <dl class="kv">
        <div><dt>Nowcast D share</dt><dd class="d-ink">${fmt(s.demShare)}</dd></div>
        <div><dt>2024 D share</dt><dd>${fmt(r.share, 2)}</dd></div>
        <div><dt>Democrat wins</dt><dd>${pct(s.pDem)} of simulations</dd></div>
        <div><dt>Rating</dt><dd>${RATING[s.rating] || s.rating}</dd></div>
        ${base ? `<div><dt>Trump approval in state</dt><dd>${fmt(base.approve + cur.vpShift)}</dd></div>` : ''}
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
  function tickCountdown() {
    const ms = Math.max(0, FORECAST_DATE - new Date());
    const parts = [[Math.floor(ms / 864e5), 'days'], [Math.floor(ms % 864e5 / 36e5), 'hours'], [Math.floor(ms % 36e5 / 6e4), 'minutes'], [Math.floor(ms % 6e4 / 1e3), 'seconds']];
    document.getElementById('cd-28').innerHTML = parts.map(([v, l], i) => `<div><span class="v num">${i ? String(v).padStart(2, '0') : v}</span><span class="l">${l}</span></div>`).join('');
  }

  // ---------- the 2028 forecast, built up as its data arrives ----------
  // Each paper's own cutoff, by the date polls were conducted: DeSart's polls from October 2027 (fixed Nov 7,
  // 2027), Enns et al.'s approval polls from June 1 to July 30, 2028 and the economy through June. Until it
  // publishes on Aug 6, 2028 the tab shows only the countdown and how far each input has got, with no forecast
  // numbers. The published forecast (docs/forecast.js) is shown as it was and never changes.
  const PUBLISH = '2028-08-06', DS_WIN = ['2027-10-01', '2027-10-31'], DS_FREEZE = '2027-11-07', AP_WIN = ['2028-06-01', '2028-07-30'];
  const todayIso = () => new Date().toISOString().slice(0, 10);
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
    document.getElementById('fc-head').innerHTML = F ? 'The 2028 forecast' : `The official prediction will be made in <span id="cd-days">${daysTo(FORECAST_DATE)}</span> days`;
    document.getElementById('cd-28').hidden = !!F;
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
    set('a[data-view="nowcast"]', '2028 forecast');
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
    document.getElementById('d-forecast').textContent = days;
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
    document.getElementById('live-inputs').innerHTML = `<b>Live data (automatic):</b> National approval ${fmt(N.approval.approve)} from ${N.approval.pollsters} pollsters through ${niceDate(N.approval.window[1])} · state-by-state differences from ${N.approval.state_data && N.approval.state_data.as_of ? `<a href="${N.approval.state_data.url}">Civiqs</a> through ${niceDate(N.approval.state_data.as_of)}` : 'Civiqs'} · state economies through ${monthName(N.economy.through)}.`;
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

  // ================= routing =================
  const VIEWS = ['home', 'nowcast', 'results-2024', 'method'];
  const done = {};
  function route() {
    let h = location.hash.replace('#', '');
    if (h === 'forecast-2028') h = 'nowcast';   // old address
    const v = VIEWS.includes(h) ? h : 'home';
    VIEWS.forEach(n => document.getElementById('view-' + n).hidden = n !== v);
    document.querySelectorAll('nav a').forEach(a => a.dataset.view === v ? a.setAttribute('aria-current', 'page') : a.removeAttribute('aria-current'));
    if (!done[v]) {
      if (v === 'home') renderHome();
      if (v === 'results-2024') render2024();
      if (v === 'nowcast') render2028();
      done[v] = true;
    }
    window.scrollTo(0, 0);
  }
  window.addEventListener('hashchange', route);
  route();
})();
