(function () {
  const R = window.RESULTS_2024;
  const NAT = window.NATIONAL_2024;
  const SHAPES = window.US_STATES;
  const N = window.NOWCAST;
  const byAbbr = Object.fromEntries(R.map(r => [r.abbr, r]));
  const natActual = 100 * NAT.dem / (NAT.dem + NAT.rep);
  // The 2024 scorecard has two forecasts to score: 'pub', the approval and economy model's forecast as its
  // authors published it, and 'bt', the Nowcast's method applied to 2024 (docs/backtest2024.js).
  const BT = window.BACKTEST_2024 || null, F24 = ['fc', 'lo', 'hi', 'pDem', 'rating'];
  // 'ds': DeSart's polls model as he published it (November 2023), also from docs/backtest2024.js.
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
    const m = s - 50, t = Math.pow(Math.min(Math.abs(m) / 22, 1), 0.75);
    return m >= 0 ? mix('#1d2a40', '#4f8de0', t) : mix('#3a2830', '#d8665b', t);
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
    el.innerHTML = rows.map(r => `<div class="seg${r === tp ? ' tp' : ''}${r.ev < 19 ? ' sm' : ''}${r.toss || LIGHT.has(r.col) ? ' toss' : ''}" data-a="${r.abbr}" style="flex:${r.ev} 0 0;background:${r.col || (r.toss ? TOSS : shareColor(r.share))}" tabindex="0" aria-label="${esc(byAbbr[r.abbr].name)} ${fmt(r.share)} Democratic">${r.ev >= 9 ? dname(r.abbr) : ''}</div>`).join('') +
      `<div class="mark270" style="left:${270 / 538 * 100}%"></div>`;
    const tpName = byAbbr[tp.abbr].name.replace(' District', '');
    const winner = tp.share > 50 ? 'Democrats' : 'Republicans';
    const base = `${label}: the tipping point is <b>${esc(tpName)}</b> at ${fmt(tp.share)} Democratic, so <b>${winner}</b> reach 270 (${demEV} Democratic electoral votes at the central estimate).`;
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
    let cum = 0, median = 0;
    for (let i = 0; i < hist.length; i++) { cum += hist[i]; if (cum >= 0.5) { median = i; break; } }
    let o = bins.map(bn => `<rect x="${x(bn.x) + 0.5}" y="${y(bn.p)}" width="${Math.max(1, x(bn.x + bin) - x(bn.x) - 1)}" height="${H - b - y(bn.p)}" fill="${bn.x + bin / 2 >= 270 ? '#4f8de0' : '#d8665b'}" rx="1.5"><title>${bn.x} to ${Math.min(538, bn.x + bin - 1)} Democratic electoral votes: ${bn.p < 0.0005 ? 'almost none' : (100 * bn.p).toFixed(1) + '%'} of simulations</title></rect>`).join('');
    o += `<line x1="${x(270)}" x2="${x(270)}" y1="${t - 6}" y2="${H - b}" stroke="#e9eef5" stroke-dasharray="3 3"></line><text x="${x(270) + 5}" y="${t + 2}">270</text>`;
    [0, 100, 200, 300, 400, 538].forEach(v => { o += `<text x="${x(v)}" y="${H - 10}" text-anchor="${v === 0 ? 'start' : v === 538 ? 'end' : 'middle'}">${v}</text>`; });
    o += `<text x="${W - r}" y="${t + 2}" text-anchor="end">Median: ${median} Democratic EV</text>`;
    el.innerHTML = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Distribution of Democratic electoral votes; median ${median}">${o}</svg><p class="small" style="margin-top:6px">Democratic electoral votes. Blue bars are Democratic wins, red are Republican wins.</p>`;
  }

  // ---------- map: state outlines or a hexagon grid ----------
  let mapMode = 'geo';
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
    const dark = c => c === TOSS || LIGHT.has(c);
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
  const MODELS = [['enns', 'Approval and economy', 'Enns, Colner, Kumar and Lagodny'], ['desart', 'Long-range polls', 'DeSart']];
  function ensemble(el, m) {
    const card = (cls, name, by, x) => `<div class="ens ${cls}"><span class="nm">${name}</span><span class="by">${by}</span>
      <span class="odds"><b>${Math.round(100 * x.pDemWin)}</b> in 100 for the Democrat</span><span class="split" aria-hidden="true"><i style="width:${(100 * x.pDemWin).toFixed(1)}%"></i></span>
      <span class="vote">${fmt(x.demPopular)} of the two-party vote</span></div>`;
    const have = MODELS.filter(([k]) => m[k]);
    el.style.setProperty('--cols', have.length > 1 ? Array(have.length + 1).fill('minmax(0, 1fr)').join(' auto ') : 'minmax(0, 1fr)');
    el.innerHTML = have.length > 1
      ? have.map(([k, name, by]) => card('m-' + k, name, by, m[k])).join('<span class="op" aria-hidden="true">+</span>') + '<span class="op" aria-hidden="true">=</span>' +
        card('now', 'The Nowcast', 'Their average, state by state', m.now)
      : card('now', 'The Nowcast', 'The approval and economy model alone today', m.now);
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
  const FORECAST_DATE = new Date('2028-07-30T00:00:00-04:00');
  const ELECTION_DATE = new Date('2028-11-07T00:00:00-05:00');
  const daysTo = d => Math.max(0, Math.floor((d - new Date()) / 86400000));
  const monthName = ym => new Date(ym + '-15').toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
  const niceDate = iso => new Date(iso.length === 10 ? iso + 'T12:00:00' : iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });

  // ================= HOME =================
  function renderHome() {
    const views = {
      fc: [R.map(r => ({ abbr: r.abbr, ev: r.ev, share: r.pub.fc })), '2024 forecast'],
      actual: [R.map(r => ({ abbr: r.abbr, ev: r.ev, share: r.share })), '2024 result'],
      today: N ? [N.states.map(s => ({ abbr: s.abbr, ev: s.ev, share: s.demShare, toss: s.rating === 'TOSS', col: RATE_COLOR[s.rating] })), '2028 Nowcast'] : null,
    };
    const hb = document.getElementById('bal-home');
    if (N && !N.fixture_run) {
      const s = N.summary, M = N.models || {}, nD = Math.round(100 * s.pDemWin), nT = Math.round(100 * s.pTie), rep = (100 - nD - nT) / 100;
      balance(hb, views.today[0], '2028 Nowcast', s.pDemWin, rep, () => { location.hash = 'nowcast'; });
      ensemble(document.getElementById('ens-home'), { enns: M.enns || s, desart: M.desart || null, now: s });
      MODELS.forEach(([k]) => { const el = document.getElementById('odds-' + k); if (el && M[k]) el.textContent = Math.round(100 * M[k].pDemWin); });
      document.getElementById('hero-date').textContent = `Updated ${niceDate(N.generated_at)}. Not the forecast, which publishes July 30, 2028.`;
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
    show(views.today ? 'today' : 'fc');
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
        ${src24 === 'bt' ? `<p class="hint">A back-test, not a forecast anyone published. State by state it averages two forecasts that were published: approval and economy (July 2024) and DeSart's polls model (November 2023). Their national votes were ${fmt(NAT.bt.enns)} and ${fmt(NAT.bt.desart)}.</p>` : ''}
        <p class="hint">Hover or click a state for its numbers.</p>`;
      return;
    }
    const r = byAbbr[a], e = err(r), ok = (r.fc > 50) === (r.share > 50);
    el.innerHTML = `<span class="tag">${dname(a)} · ${r.ev} electoral vote${r.ev > 1 ? 's' : ''}</span><h3>${r.name}</h3>
      <dl class="kv">
        <div><dt>Forecast D share</dt><dd class="d-ink">${fmt(r.fc, 2)}</dd></div>
        <div><dt>Actual D share</dt><dd class="d-ink">${fmt(r.share, 2)}</dd></div>
        ${src24 === 'bt' ? `<div><dt>Approval and economy, published</dt><dd>${fmt(r.pub.fc, 2)}</dd></div>${r.bt.desart != null ? `<div><dt>DeSart polls model, published</dt><dd>${fmt(r.bt.desart, 2)}</dd></div>` : ''}` : `<div><dt>Forecast R share</dt><dd class="r-ink">${fmt(100 - r.fc, 2)}</dd></div>`}
        <div><dt>Signed error (pred − actual)</dt><dd class="a-ink">${sgn(e)} pts</dd></div>
        <div><dt>Rating</dt><dd>${RATING[r.rating]}</dd></div>
        <div><dt>Harris win chance</dt><dd>${Math.round(100 * r.pDem)}%</dd></div>
        <div><dt>90% range</dt><dd>${r.lo.toFixed(1)}–${r.hi.toFixed(1)}%</dd></div>
        <div><dt>Call</dt><dd style="color:${ok ? 'var(--ok)' : 'var(--rep-ink)'}">${ok ? 'Correct' : 'Missed'}</dd></div>
        ${src24 === 'ds' && r.ds && r.ds.district ? `<p class="hint" style="grid-column:1/-1">DeSart forecasts states only. This district is his ${byAbbr[a.slice(0, 2)].name} forecast moved by the district's gap from the state in the approval and economy forecast.</p>` : ''}
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
    bt: 'What the Nowcast\'s method would have said in 2024. State by state it averages two forecasts published before the election: the approval and economy forecast from July 2024 and Jay DeSart\'s polls forecast from November 2023. Nobody published this average at the time, so it is a back-test.',
    pub: 'The approval and economy forecast as Enns, Colner, Kumar and Lagodny published it in July 2024, with data from 100 days before the election.',
    ds: 'The polls forecast as Jay DeSart published it in November 2023, a year before the election, from head-to-head polls taken the month before. It forecasts the 50 states and DC; the five districts in Maine and Nebraska are filled in from the approval and economy forecast.',
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
  // The polls model's vote is not the polls' average: DeSart's equation starts from the last result and moves it by
  // about half of the polls' margin (coefficient 0.52), so the two are shown side by side to avoid misreading.
  const SHRINK = 'The polls model starts from the 2024 result and moves it by about half of the polls\' margin, because polls this far out are only partly predictive (DeSart\'s estimate).';
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
    let cum = 0, median = 0;
    for (let i = 0; i < s.evHistogram.length; i++) { cum += s.evHistogram[i]; if (cum >= 0.5) { median = i; break; } }
    const items = s.states.map(x => ({ abbr: x.abbr, ev: x.ev, share: x.demShare, toss: x.rating === 'TOSS', col: RATE_COLOR[x.rating] }));
    const tp = tippingOf(items).tp;
    const toMap = a => {
      setLayer28('tracker');
      if (pinned28 !== a) pick28(a, true);
      document.getElementById('map-2028').scrollIntoView({ behavior: still ? 'auto' : 'smooth', block: 'center' });
    };
    balance(document.getElementById('bal-28'), items, '2028 Nowcast', s.pDemWin, rep, toMap);
    ensemble(document.getElementById('ens-28'), { enns: s.enns || s, desart: s.desart, now: s });
    setGlow(s.pDemWin, rep);
    waffle(document.getElementById('waffle-28'), s.pDemWin, s.pTie);
    document.getElementById('waffle-cap').textContent = `Out of 100 simulated elections held today, the Democrat wins ${nD} and the Republican wins ${100 - nD - nT}${nT ? `, with ${nT} tied` : ''}. A simulation is one possible outcome given how far off the models have been in the past.`;
    const mo = document.getElementById('models-28');
    if (mo) mo.innerHTML = s.desart
      ? `Each state's number is the average of the approval and economy model and the polls model, half each. The whole map is then simulated together, so the Nowcast's odds are not simply the average of the two models' odds. ${nomineesNote()} ${s.desart ? POLLS_NOTE(s.info) : ''} <a href="#method">How they work</a>`
      : `Today's Nowcast is the approval and economy model on its own, because no head-to-head polls are available. <a href="#method">How it works</a>`;
    document.getElementById('figs-2028').innerHTML = [
      [fmt(s.demPopular), 'Democratic share of the two-party vote'],
      [`${median}`, 'Median Democratic electoral votes, of 538'],
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
        ${cur.desart ? modelTable([['Approval and economy', cur.enns.demPopular, cur.enns.pDemWin], ['Polls model', cur.desart.demPopular, cur.desart.pDemWin], ['Nowcast', cur.demPopular, cur.pDemWin, 'avg']], 'the election') : ''}
        ${cur.info && cur.info.polls ? `<p class="hint">${POLLS_NOTE(cur.info)}</p>` : ''}
        <p class="hint">Not the forecast. The Nowcast simulates the models together, so its odds are not the average of theirs. Hover a state for its numbers.</p>`;
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
      ${s.desart != null ? modelTable([['Approval and economy', s.enns, s.ennsP], ['Polls model', s.desart, s.desartP], ['Nowcast', s.demShare, s.pDem, 'avg']], 'the state') : ''}
      ${a === N.scenario.homeLag.rep || a === N.scenario.homeLag.dem ? `<p class="hint">Both models take back part of the 2024 ${a === N.scenario.homeLag.rep ? 'Republican' : 'Democratic'} nominee's home-state boost here, which moves this state toward the ${a === N.scenario.homeLag.rep ? 'Democrat' : 'Republican'}: ${(-window.SPASE.coef('homeLag') * (N.scenario.homeLagWeight || { dem: 1, rep: 1 })[a === N.scenario.homeLag.rep ? 'rep' : 'dem']).toFixed(1)} points in the approval and economy model${s.desart != null ? `, ${window.TP.DESART.home.toFixed(1)} in the polls model` : ''}.</p>` : ''}`;
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

  // Map layers. "Forecast" shows a countdown, not a map, until July 30, 2028.
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

  function render2028() {
    const days = daysTo(FORECAST_DATE);
    document.getElementById('d-forecast').textContent = days;
    document.getElementById('cd-days').textContent = days;
    tickCountdown(); setInterval(tickCountdown, 1000);
    map28 = draw28();
    ramp(document.getElementById('ramp-2028'), 'nowcast');
    document.querySelectorAll('[data-layer28]').forEach(b => b.addEventListener('click', () => setLayer28(b.dataset.layer28)));
    document.getElementById('btn-to-nowcast').addEventListener('click', () => setLayer28('tracker'));
    if (!N) {
      ['hero-28', 'jump-28', 'results-detail', 'tracker-detail'].forEach(id => { document.getElementById(id).hidden = true; });
      document.getElementById('live-pill').textContent = 'Waiting for the first data run';
      setLayer28('official'); return;
    }
    document.getElementById('live-pill').textContent = `Live · updated ${niceDate(N.generated_at)}`;
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
    const hp = (N.h2h && N.h2h.polls) || [];
    const tb = document.getElementById('h2h-2028'), more = document.getElementById('h2h-more');
    const showPolls = all => {
      tb.innerHTML = (all ? hp : hp.slice(0, 10)).map(q => `<tr><td class="num">${q.date}</td><td>${esc(q.pollster)}</td><td class="mu">${esc(lastName(q.d))} vs. ${esc(lastName(q.r))}</td><td class="n"><span class="bar" aria-hidden="true"><i class="${q.share > 50 ? 'D' : 'R'}" style="width:${Math.min(50, Math.abs(q.share - 50) * 8).toFixed(1)}%"></i></span>${fmt(q.share)}</td></tr>`).join('');
      more.hidden = all || hp.length <= 10;
      more.textContent = `Show all ${hp.length} polls`;
    };
    more.addEventListener('click', () => showPolls(true));
    showPolls(false);
    document.getElementById('h2h-note').innerHTML = hp.length
      ? `The Democrat's share of the two-party vote in each poll. National polls between one named Democrat and one named Republican from the last ${N.h2h.days} days, from <a href="https://pollresults.org/races/president-2028/">PollResults.org</a> (New York Times poll data, CC BY 4.0). ${N.h2h.skipped ? `${N.h2h.skipped} other questions are left out: generic party ballots, and questions that name a third candidate.` : ''}`
      : 'No head-to-head polls are available today, so the Nowcast is the approval and economy model on its own.';
    const t = N.tickets, set = ['dem', 'rep'].filter(s => t[s] && t[s].president).length;
    document.getElementById('need-tickets').textContent = set ? `Confirmed: ${set === 2 ? 'both nominees' : 'one nominee'}` : 'Watching, none yet';
    document.getElementById('need-vp').textContent = N.vp.applied ? `On, ${sgn(N.vp.gap, 1)} pts` : N.vp.gap != null ? `Standing by, ${sgn(N.vp.gap, 1)} pts` : 'No recent polls of the vice president';
    const nh = document.getElementById('need-h2h');
    if (nh) nh.textContent = N.h2h && N.h2h.polls.length ? `Daily, ${N.h2h.polls.length} polls in the window` : 'No polls available today';
    document.getElementById('need-econ').textContent = `Daily, through ${monthName(N.economy.through)}`;
    document.getElementById('need-cands').textContent = `Daily, ${N.scenario.candidates.filter(c => c.primary).length} names in primary polls`;
    document.getElementById('polls-2028').innerHTML = N.approval.polls.map(p =>
      `<tr><td>${p.url ? `<a href="${esc(p.url)}">${esc(p.pollster)}</a>` : esc(p.pollster)}</td><td class="num">${p.date}</td><td class="n">${p.approve}</td><td class="n">${p.disapprove}</td></tr>`).join('');
    const H = window.NOWCAST_HISTORY || [];
    if (H.length >= 2) {
      const W = 600, Ht = 220, l = 40, r = 12, tp = 10, b = 26;
      const x = i => l + i / (H.length - 1) * (W - l - r), y = v => tp + (1 - v) * (Ht - tp - b);
      let o = '';
      [0, .25, .5, .75, 1].forEach(v => { o += `<line x1="${l}" x2="${W - r}" y1="${y(v)}" y2="${y(v)}" stroke="${v === .5 ? '#5d6a7e' : '#1f2b3e'}" ${v === .5 ? 'stroke-dasharray="3 3"' : ''}></line><text x="${l - 8}" y="${y(v) + 4}" text-anchor="end">${v * 100}%</text>`; });
      const pts = H.map((h, i) => `${x(i)},${y(h.pDemWin)}`).join(' ');
      o += `<polygon points="${x(0)},${y(0)} ${pts} ${x(H.length - 1)},${y(0)}" fill="rgba(240,163,94,.1)"></polygon><polyline points="${pts}" fill="none" stroke="#f0a35e" stroke-width="2"></polyline>`;
      o += `<circle cx="${x(H.length - 1)}" cy="${y(H[H.length - 1].pDemWin)}" r="4" fill="#f0a35e"></circle><text x="${l}" y="${Ht - 6}">${H[0].date}</text><text x="${W - r}" y="${Ht - 6}" text-anchor="end">${H[H.length - 1].date}</text>`;
      document.getElementById('trend-2028').innerHTML = `<svg viewBox="0 0 ${W} ${Ht}" role="img" aria-label="Share of simulations the Democrat wins, over time">${o}</svg>`;
    }
    schedule();
  }

  // Map style switch (state outlines or hexagons), shared by both maps.
  document.querySelectorAll('[data-mapmode]').forEach(b => b.addEventListener('click', () => {
    mapMode = b.dataset.mapmode;
    document.querySelectorAll('[data-mapmode]').forEach(x => x.setAttribute('aria-pressed', x.dataset.mapmode === mapMode));
    if (map24) map24 = draw24();
    if (map28) map28 = draw28();
  }));

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
