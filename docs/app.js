(function () {
  const R = window.RESULTS_2024;
  const NAT = window.NATIONAL_2024;
  const SHAPES = window.US_STATES;
  const N = window.NOWCAST;
  const byAbbr = Object.fromEntries(R.map(r => [r.abbr, r]));
  const natActual = 100 * NAT.dem / (NAT.dem + NAT.rep);
  const RATING = { SR: 'Solid R', LR: 'Likely R', TR: 'Lean R', TD: 'Lean D', LD: 'Likely D', SD: 'Solid D', TOSS: 'Toss-up' };
  const SMALL = ['VT', 'NH', 'MA', 'RI', 'CT', 'NJ', 'DE', 'MD', 'DC'];
  const DISTRICTS = ['ME1', 'ME2', 'NE1', 'NE2', 'NE3'];
  const LABEL_NUDGE = { FL: [14, 6], MI: [8, 14], LA: [-8, 0], KY: [6, 2], HI: [6, 6], CA: [-8, 0], ID: [0, 14], MN: [-4, 6], TX: [6, 0], NY: [6, 0], VA: [8, 2], WV: [-2, 4] };
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
  function snake(el, readEl, items, label) {
    const { rows, tp } = tippingOf(items);
    const demEV = rows.filter(r => r.share > 50).reduce((a, r) => a + r.ev, 0);
    el.innerHTML = rows.map(r => `<div class="seg${r === tp ? ' tp' : ''}" data-a="${r.abbr}" style="flex:${r.ev} 0 0;background:${shareColor(r.share)}" tabindex="0" aria-label="${esc(byAbbr[r.abbr].name)} ${fmt(r.share)} Democratic">${r.ev >= 9 ? dname(r.abbr) : ''}</div>`).join('') +
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
    let o = bins.map(bn => `<rect x="${x(bn.x) + 0.5}" y="${y(bn.p)}" width="${Math.max(1, x(bn.x + bin) - x(bn.x) - 1)}" height="${H - b - y(bn.p)}" fill="${bn.x + bin / 2 >= 270 ? '#4f8de0' : '#d8665b'}" rx="1.5"></rect>`).join('');
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

  function drawUS(svg, { fill, onPick, onHover, selected }) {
    const W = 1075, H = 610, hex = mapMode === 'hex';
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
    const shape = {}, at = {};
    for (const a of Object.keys(SHAPES)) {
      if (hex) { const [c, r] = HEX[a]; at[a] = [96 + c * 69.3, 76 + r * 60]; shape[a] = hexD(at[a][0], at[a][1], 39); }
      else { const [dx, dy] = LABEL_NUDGE[a] || [0, 0]; at[a] = [SHAPES[a].c[0] + dx, SHAPES[a].c[1] + dy]; shape[a] = SHAPES[a].d; }
    }
    let o = '';
    for (const a of Object.keys(SHAPES)) o += `<path class="st" data-a="${a}" d="${shape[a]}" fill="${fill(a)}" tabindex="0" aria-label="${byAbbr[a].name}"></path>`;
    for (const a of Object.keys(SHAPES)) if (hex || !SMALL.includes(a)) o += `<text class="lbl${hex ? ' big' : ''}" x="${at[a][0]}" y="${at[a][1] + (hex ? 5 : 3)}">${a}</text>`;
    const bx = 1005, bw = 54, bh = 21, dy0 = hex ? 232 : 392;
    if (!hex) SMALL.forEach((a, i) => {
      const y = 118 + i * 27, c = SHAPES[a].c;
      o += `<line class="leader" x1="${c[0]}" y1="${c[1]}" x2="${bx}" y2="${y + bh / 2}"></line>`;
      o += `<g class="box" data-a="${a}" tabindex="0" aria-label="${byAbbr[a].name}"><rect x="${bx}" y="${y}" width="${bw}" height="${bh}" rx="4" fill="${fill(a)}"></rect><text x="${bx + bw / 2}" y="${y + 14.5}">${a}</text></g>`;
    });
    o += `<text class="grp" x="${bx}" y="${dy0 - 8}">Districts</text>`;
    DISTRICTS.forEach((a, i) => {
      const y = dy0 + i * 27;
      o += `<g class="box" data-a="${a}" tabindex="0" aria-label="${byAbbr[a].name}"><rect x="${bx}" y="${y}" width="${bw}" height="${bh}" rx="4" fill="${fill(a)}"></rect><text x="${bx + bw / 2}" y="${y + 14.5}">${dname(a)}</text></g>`;
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
    return { mark, recolor: f => svg.querySelectorAll('[data-a]').forEach(el => { const t = el.tagName === 'g' ? el.querySelector('rect') : el; t.setAttribute('fill', f(el.dataset.a)); }) };
  }

  // ---------- balance beam: tips toward whoever wins more simulations ----------
  const BEAM = ['#4f8de0', '#6083dc', '#717ad7', '#8270d3', '#976bc1', '#af6ba0', '#c66a80', '#de6a5f'];
  function beamSVG() {
    let h = '';
    for (let i = 0; i < 8; i++) h += `<path d="${hexD(62 + i * 68, 96, 32)}" fill="${BEAM[i]}"></path>`;
    for (let i = 0; i < 7; i++) h += `<path d="${hexD(96 + i * 68, 153, 32)}" fill="${mix(BEAM[i], BEAM[i + 1], 0.5)}"></path>`;
    return `<svg viewBox="0 0 600 300" aria-hidden="true"><g class="beam-arm">${h}</g><path d="M300,190 L258,288 L342,288 Z" fill="#f0a35e"></path></svg>`;
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
      const chips = rows.map(s => `<button type="button" data-a="${s.abbr}" style="background:${shareColor(s.demShare)}" title="${esc(byAbbr[s.abbr].name)}: ${fmt(s.demShare)} Democratic, ${s.ev} EV">${dname(s.abbr)}</button>`).join('');
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
    document.getElementById('hero-2024').innerHTML = strip({ f: NAT.fc, a: natActual }, 40, 60);
    document.getElementById('hero-2024-read').innerHTML =
      `Forecast <b class="a-ink">${fmt(NAT.fc)}</b><br>Result <b>${fmt(natActual)}</b><br>Trump won, as the model gave ${Math.round(100 * (1 - NAT.pDemWin))}% odds`;
    const el = document.getElementById('hero-2028'), rd = document.getElementById('hero-2028-read');
    if (N && !N.fixture_run) {
      el.className = 'strip';
      el.innerHTML = strip({ f: N.summary.demPopular }, 40, 60);
      rd.innerHTML = `Nowcast <b class="a-ink">${fmt(N.summary.demPopular)}</b><br>Democrat wins ${pct(N.summary.pDemWin)} of simulations<br><a href="#nowcast">Pick the tickets</a>`;
    } else {
      el.innerHTML = `<div class="pending">Real forecast publishes July 30, 2028</div>`;
      rd.innerHTML = `${daysTo(FORECAST_DATE)} days to go<br><a href="#nowcast">See the 2028 Nowcast</a>`;
    }
    const views = {
      fc: [R.map(r => ({ abbr: r.abbr, ev: r.ev, share: r.fc })), '2024 forecast'],
      actual: [R.map(r => ({ abbr: r.abbr, ev: r.ev, share: r.share })), '2024 result'],
      today: N ? [N.states.map(s => ({ abbr: s.abbr, ev: s.ev, share: s.demShare })), '2028 Nowcast'] : null,
    };
    const tabs = document.querySelectorAll('[data-snake]');
    const show = k => { const v = views[k] || views.fc; tabs.forEach(t => t.setAttribute('aria-selected', t.dataset.snake === k)); snake(document.getElementById('snake-home'), document.getElementById('snake-home-read'), v[0], v[1]); };
    tabs.forEach(t => { if (t.dataset.snake === 'today' && !views.today) t.disabled = true; t.addEventListener('click', () => show(t.dataset.snake)); });
    show('fc');
  }

  // ================= 2024 =================
  let layer24 = 'forecast', pinned24 = null, map24;
  const err = r => r.fc - r.share;

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
          <div><dt>Electoral votes</dt><dd>Trump 312 · actual 312</dd></div>
          <div><dt>Trump win chance</dt><dd>${Math.round(100 * (1 - NAT.pDemWin))}%</dd></div>
        </dl>
        <div class="stack" style="gap:6px"><div class="strip-scale num"><span>30%</span><span>50%</span><span>70%</span></div><div class="strip">${strip({ f: NAT.fc, a: natActual })}</div></div>
        <div class="strip-legend"><span><i class="f"></i>Forecast</span><span><i class="a"></i>Actual</span></div>
        <p class="hint">Hover or click a state for its numbers.</p>`;
      return;
    }
    const r = byAbbr[a], e = err(r), ok = (r.fc > 50) === (r.share > 50);
    el.innerHTML = `<span class="tag">${dname(a)} · ${r.ev} electoral vote${r.ev > 1 ? 's' : ''}</span><h3>${r.name}</h3>
      <dl class="kv">
        <div><dt>Forecast D share</dt><dd class="d-ink">${fmt(r.fc, 2)}</dd></div>
        <div><dt>Actual D share</dt><dd class="d-ink">${fmt(r.share, 2)}</dd></div>
        <div><dt>Forecast R share</dt><dd class="r-ink">${fmt(100 - r.fc, 2)}</dd></div>
        <div><dt>Signed error (pred − actual)</dt><dd class="a-ink">${sgn(e)} pts</dd></div>
        <div><dt>Rating</dt><dd>${RATING[r.rating]}</dd></div>
        <div><dt>Harris win chance</dt><dd>${Math.round(100 * r.pDem)}%</dd></div>
        <div><dt>90% range</dt><dd>${r.lo.toFixed(1)}–${r.hi.toFixed(1)}%</dd></div>
        <div><dt>Call</dt><dd style="color:${ok ? 'var(--ok)' : 'var(--rep-ink)'}">${ok ? 'Correct' : 'Missed'}</dd></div>
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

  function render2024() {
    const st = R.filter(r => r.abbr.length === 2);
    const mae = st.reduce((s, r) => s + Math.abs(err(r)), 0) / st.length;
    const inside = R.filter(r => r.share >= r.lo && r.share <= r.hi).length;
    const correct = R.filter(r => (r.fc > 50) === (r.share > 50)).length;
    document.getElementById('figs-2024').innerHTML = [
      [`${correct}/${R.length}`, 'States and districts called'],
      ['312 = 312', 'Trump electoral votes, forecast and actual'],
      [`${mae.toFixed(1)} pts`, 'Average state miss'],
      [`${inside}/${R.length}`, 'Results inside the 90% range'],
    ].map(([v, l]) => `<div><span class="v">${v}</span><span class="l">${l}</span></div>`).join('');

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

  function buildPick(box) {
    const role = box.dataset.role, [party, label] = ROLES[role], off = official(role);
    box.classList.toggle('locked', !!off);
    if (off) {
      box.innerHTML = `<span class="lab">${label}</span><div class="lockrow"><b>${esc(off.name)}</b>${off.state ? `<span>${off.state}</span>` : ''}<span class="lock">Confirmed</span></div>`;
      return;
    }
    const people = N.scenario.candidates.filter(c => c.party === party).slice().sort((a, b) => (b.primary || 0) - (a.primary || 0) || a.name.localeCompare(b.name));
    const polled = role.endsWith('-p');
    const opts = `<option value="">Not chosen yet</option><optgroup label="Possible candidates">` +
      people.map(c => `<option value="${esc(c.name)}">${esc(c.name)} (${c.state})${polled && c.primary ? `, ${Math.round(c.primary)}% in primary polls` : ''}</option>`).join('') +
      `</optgroup><option value="__custom">Someone else…</option>`;
    box.innerHTML = `<label for="sel-${role}">${label}</label><select id="sel-${role}">${opts}</select>
      <div class="custom" hidden><input id="nm-${role}" type="text" placeholder="Name" aria-label="${label} name"><select id="st-${role}" aria-label="${label} home state">${STATE_LIST.map(([a]) => `<option value="${a}">${a}</option>`).join('')}</select></div>`;
    const sel = box.querySelector('select'), custom = box.querySelector('.custom');
    sel.addEventListener('change', () => { custom.hidden = sel.value !== '__custom'; if (!custom.hidden) box.querySelector('input').focus(); schedule(); });
    box.querySelector('input').addEventListener('input', () => schedule());
    box.querySelector('#st-' + role).addEventListener('change', () => schedule());
  }

  function readPick(role) {
    const off = official(role);
    if (off) return { name: off.name, state: off.state, locked: true };
    const v = document.getElementById('sel-' + role).value;
    if (!v) return null;
    if (v === '__custom') return { name: document.getElementById('nm-' + role).value.trim() || 'Your pick', state: document.getElementById('st-' + role).value };
    const c = N.scenario.candidates.find(x => x.name === v);
    return { name: c.name, state: c.state };
  }

  // Both models and their average, for a set of picks (docs/combine.js). n is draws per economic weighting.
  const pk = o => ({ dp: o['dem-p'] || null, rp: o['rep-p'] || null, dv: o['dem-vp'] || null, rv: o['rep-vp'] || null });
  const runModels = (o, n) => window.TP.run(N, pk(o), { n: n || 10000 });
  const runCombined = (o, n) => window.TP.run(N, pk(o), { n: n || 10000, parts: false }).combined;
  const lastName = n => n.replace(/ (Jr\.|Sr\.|II|III)$/, '').split(' ').pop();

  // The strongest ticket on today's numbers, per party. The nominee is the one who does best in
  // head-to-head polls (the only place the models can tell candidates apart, apart from home state);
  // the running mate is the one whose home state helps most. Each side faces the other party's whole
  // field. Runs once, in small steps, so the page stays responsive.
  let bestStarted = false;
  async function findStrongest() {
    if (bestStarted) return;
    bestStarted = true;
    const h = N.h2h, min = h && h.min_polls || 3;
    const sides = [['dem', 'D', 'Democrat', 'Republican', 'd'], ['rep', 'R', 'Republican', 'Democratic', 'r']].filter(([side]) => !official(side + '-p') && !official(side + '-vp'));
    if (!sides.length || !h || !h.polls || !h.polls.length) return;
    const pause = () => new Promise(r => setTimeout(r, 0));
    const head = `<span class="lab">Strongest ticket on today's numbers</span>`;
    sides.forEach(([side]) => { const el = document.getElementById('best-' + side); el.hidden = false; el.innerHTML = `${head}<p class="hint">Working it out…</p>`; });
    document.getElementById('best-note').hidden = false;
    await pause();
    const base = runCombined({});
    const open = new Set(base.states.filter(s => s.pDem > 0.02 && s.pDem < 0.98).map(s => s.abbr));
    for (const [side, party, own, other, key] of sides) {
      const el = document.getElementById('best-' + side);
      const wins = r => side === 'dem' ? Math.round(100 * r.pDemWin) : 100 - Math.round(100 * r.pDemWin) - Math.round(100 * r.pTie);
      const score = r => side === 'dem' ? r.pDemWin : 1 - r.pDemWin - r.pTie;
      const people = N.scenario.candidates.filter(c => c.party === party);
      const polled = people.map(c => ({ c, polls: h.polls.filter(p => p[key] === c.name) })).filter(x => x.polls.length >= min);
      if (!polled.length) { el.innerHTML = `${head}<p class="hint">No possible ${own === 'Democrat' ? 'Democratic' : own} nominee has ${min} head-to-head polls in the last ${h.days} days yet.</p>`; continue; }
      const ticket = (c, st) => { const o = {}; o[side + '-p'] = { name: c.name, state: c.state }; if (st) o[side + '-vp'] = { name: '', state: st }; return o; };
      let top = null;
      for (const x of polled) { const sc = score(runCombined(ticket(x.c), 2000)); if (!top || sc > top.sc) top = { ...x, sc }; await pause(); }
      // Running mate: one candidate per competitive home state, tested with the nominee in place.
      const mates = [...new Set(people.filter(c => c.name !== top.c.name && c.state !== top.c.state && open.has(c.state)).map(c => c.state))];
      let mate = null;
      for (const st of mates) { const sc = score(runCombined(ticket(top.c, st), 2000)); if (sc > top.sc && (!mate || sc > mate.sc)) mate = { st, sc }; await pause(); }
      const mateNames = mate ? people.filter(c => c.state === mate.st && c.name !== top.c.name).sort((a, b) => (b.primary || 0) - (a.primary || 0)).map(c => c.name) : [];
      const now = wins(runCombined(ticket(top.c, mate && mate.st))), was = wins(base);
      const avg = top.polls.reduce((a, p) => a + p.share, 0) / top.polls.length, ownShare = side === 'dem' ? avg : 100 - avg;
      el.innerHTML = `${head}
        <p class="who"><b>${esc(top.c.name)}</b> (${top.c.state})${mate ? ` with <b>${mateNames.slice(0, 3).map(esc).join('</b> or <b>')}</b> (${mate.st})` : ''}</p>
        <p class="hint">${own} wins ${now} in 100 against the ${other} field, compared with ${was} when both nominees are open. ${esc(lastName(top.c.name))} averages ${fmt(ownShare)} of the two-party vote in ${top.polls.length} head-to-head polls. ${polled.length > 1 ? `Of the ${polled.length} possible nominees with at least ${min} such polls, this one does best in the Nowcast as a whole, which also counts home states and the vice-president adjustment.` : `No other possible nominee has ${min} such polls yet.`}${mate ? ' The running mate is chosen for home state.' : ''}</p>
        <button class="btn" type="button">Use this ticket</button>`;
      el.querySelector('button').addEventListener('click', () => {
        [[side + '-p', top.c.name], [side + '-vp', mateNames[0] || '']].forEach(([role, v]) => { const sel = document.getElementById('sel-' + role); if (!sel) return; sel.value = v; sel.dispatchEvent(new Event('change')); });
      });
      await pause();
    }
  }

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
    timer = setTimeout(() => { runScenario(); out.forEach(el => el.classList.remove('busy')); setTimeout(findStrongest, 300); }, 60);
  }

  function effectsList() {
    const p = cur.picks, out = [], info = cur.info, h = N.h2h;
    const who = r => `${esc(p[r].name)} (${p[r].state})`;
    const has = r => p[r] && p[r].state;
    const pts = v => v.toFixed(1);
    if (!has('dem-p') && !has('rep-p')) out.push(`<b>No nominees chosen.</b> Each party's possible nominees are weighted by their polling, so the home-state effects are spread across the field. Pick candidates to test a ticket; they lock in automatically once confirmed.`);
    const E = window.SPASE.coef, DH = window.TP.DESART.home, homePts = `${pts(E('home'))} points in the approval and economy model and ${pts(DH)} in the polls model`;
    if (has('dem-p')) out.push(`<b>Home state:</b> ${who('dem-p')} adds ${homePts}, for the Democrat in ${byAbbr[p['dem-p'].state].name}.`);
    if (has('rep-p')) out.push(`<b>Home state:</b> ${who('rep-p')} adds ${homePts}, for the Republican in ${byAbbr[p['rep-p'].state].name}.`);
    if (has('dem-vp')) out.push(`<b>Running mate:</b> ${who('dem-vp')} adds about ${pts(E('vpHome'))} points for the Democrat in ${byAbbr[p['dem-vp'].state].name} in the approval and economy model. The polls model has no running-mate effect.`);
    if (has('rep-vp')) out.push(`<b>Running mate:</b> ${who('rep-vp')} adds about ${pts(E('vpHome'))} points for the Republican in ${byAbbr[p['rep-vp'].state].name} in the approval and economy model. The polls model has no running-mate effect.`);
    if (has('dem-p') && has('rep-p') && p['dem-p'].state === p['rep-p'].state) out.push(`Both nominees are from ${byAbbr[p['dem-p'].state].name}, so their home-state bonuses cancel out.`);
    if (info.polls) {
      const q = info.polls, share = fmt(q.avg), d = has('dem-p') && p['dem-p'].name, r = has('rep-p') && p['rep-p'].name;
      const short = (d || r) && q.basis === 'all' ? ` There are fewer than ${h.min_polls} polls of ${d && r ? 'these nominees' : esc(d || r)}, so all of them are used.` : '';
      out.push(`<b>Head-to-head polls:</b> ` + (
        q.basis === 'matchup' ? `the Democrat gets ${share} of the two-party vote on average in ${q.n} polls of ${esc(d)} against ${esc(r)}.`
        : q.basis === 'either' ? `the Democrat gets ${share} of the two-party vote on average in the ${q.n} polls that test ${esc(d)} or ${esc(r)}. Fewer than ${h.min_polls} test them against each other.`
        : q.basis === 'one' ? `the Democrat gets ${share} of the two-party vote on average in the ${q.n} polls that test ${esc(d || r)}.`
        : `the Democrat gets ${share} of the two-party vote on average across all ${q.n} national head-to-head polls from the last ${h.days} days.${short}`) + ` ${SHRINK}`);
    } else out.push(`<b>Head-to-head polls:</b> none are available today, so the Nowcast is the approval and economy model on its own.`);
    const lw = N.scenario.homeLagWeight || { dem: 1, rep: 1 };
    out.push(`<b>2024 home states fade:</b> Harris's California and Trump's Florida give back part of their 2024 boost, whether or not they run again: about ${pts(-E('homeLag') * lw.dem)} points in the approval and economy model${cur.desart ? ` and ${pts(DH)} in the polls model` : ''}.`);
    const net = N.vp.kind === 'favorability' ? 'net favorability' : 'net approval';
    if (N.vp.gap == null) out.push(`<b>Vice-president adjustment:</b> there are no recent polls of ${esc(N.sitting_vp)} to measure it.`);
    else if (cur.vpNom) out.push(`<b>Vice-president adjustment on:</b> ${esc(N.sitting_vp)} is the sitting vice president, so state approval shifts by ${sgn(N.vp.gap, 1)} points, his ${net} minus Trump's (${esc(N.vp.basis)}).`);
    else if (info.vpWeight > 0) out.push(`<b>Vice-president adjustment, in part:</b> ${esc(N.sitting_vp)} has ${Math.round(100 * info.vpWeight)}% of his party's primary polling, so that share of his ${sgn(N.vp.gap, 1)}-point adjustment is applied (${sgn(info.vpShift, 1)} points). It applies in full if he is the nominee and not at all if someone else is.`);
    else out.push(`<b>Vice-president adjustment off:</b> it applies only if the sitting vice president, ${esc(N.sitting_vp)}, is the nominee.`);
    document.getElementById('effects').innerHTML = out.map(x => `<li>${x}</li>`).join('');
  }

  function showResults() {
    const s = cur;
    // Whole numbers out of 100, so the two big figures, the hexagons and the caption always agree.
    const nD = Math.round(100 * s.pDemWin), nT = Math.round(100 * s.pTie), rep = (100 - nD - nT) / 100;
    let cum = 0, median = 0;
    for (let i = 0; i < s.evHistogram.length; i++) { cum += s.evHistogram[i]; if (cum >= 0.5) { median = i; break; } }
    const items = s.states.map(x => ({ abbr: x.abbr, ev: x.ev, share: x.demShare }));
    const tp = tippingOf(items).tp;
    countTo(document.getElementById('bm-dem'), s.pDemWin, pct);
    countTo(document.getElementById('bm-rep'), rep, pct);
    document.querySelector('#beam .beam-arm').style.transform = `rotate(${(-12 * (s.pDemWin - rep)).toFixed(1)}deg)`;
    waffle(document.getElementById('waffle-28'), s.pDemWin, s.pTie);
    document.getElementById('waffle-cap').textContent = `Out of 100 simulated elections held today, the Democrat wins ${nD} and the Republican wins ${100 - nD - nT}${nT ? `, with ${nT} tied` : ''}. A simulation is one possible outcome given how far off the models have been in the past.`;
    const mo = document.getElementById('models-28');
    if (mo) mo.innerHTML = s.desart
      ? `Each state's number is the average of two models, and the map is then simulated as a whole. Each model on its own, simulated the same way: <b>approval and economy</b>, Democrat wins ${Math.round(100 * s.enns.pDemWin)} in 100 with ${fmt(s.enns.demPopular)} of the two-party vote; <b>polls model</b>, ${Math.round(100 * s.desart.pDemWin)} in 100 with ${fmt(s.desart.demPopular)}. ${POLLS_NOTE(s.info)} <a href="#method">How they work</a>`
      : `Today's Nowcast is the approval and economy model on its own, because no head-to-head polls are available. <a href="#method">How it works</a>`;
    document.getElementById('figs-2028').innerHTML = [
      [fmt(s.demPopular), 'Democratic share of the two-party vote'],
      [`${median}`, 'Median Democratic electoral votes, of 538'],
      [esc(byAbbr[tp.abbr].name.replace(' District', '')), `Tipping-point state, ${fmt(tp.share)} Democratic`],
    ].map(([v, l]) => `<div><span class="v">${v}</span><span class="l">${l}</span></div>`).join('');
    snake(document.getElementById('snake-2028'), document.getElementById('snake-2028-read'), items, '2028 Nowcast');
    board(document.getElementById('board-28'), s.states, a => {
      setLayer28('tracker');
      if (pinned28 !== a) pick28(a);
      document.getElementById('map-2028').scrollIntoView({ behavior: 'smooth', block: 'center' });
    });
    histogram(document.getElementById('hist-2028'), s.evHistogram);
    if (map28) map28.recolor(fill28);
    insp28(pinned28);
    effectsList();
  }

  function insp28(a) {
    const el = document.getElementById('insp-2028');
    const natShare = 100 * NAT.dem / (NAT.dem + NAT.rep);
    if (layer28 === 'lean') {
      const r = a ? byAbbr[a] : null;
      el.innerHTML = r ? `<span class="tag">${dname(a)} · ${r.ev} electoral vote${r.ev > 1 ? 's' : ''}</span><h3>${r.name}</h3>
        <dl class="kv"><div><dt>2024 D share</dt><dd class="d-ink">${fmt(r.share, 2)}</dd></div><div><dt>Lean vs. nation</dt><dd>${sgn(r.share - natShare)} pts</dd></div><div><dt>Model weight</dt><dd>0.82 × lean</dd></div></dl>
        <div class="strip">${strip({ a: r.share })}</div>`
        : `<span class="tag">The one input already known</span><h3>2024 lean</h3><p class="small">Each state's Democratic share in 2024 relative to the nation (${fmt(natShare, 2)}). The model carries 82% of this lean into 2028.</p>`;
      return;
    }
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
        <p class="hint">Not the forecast. The Nowcast averages the two models state by state, so its odds are not the average of theirs. Hover a state for its numbers.</p>`;
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
    if (layer28 === 'lean') return shareColor(50 + (byAbbr[a].share - 100 * NAT.dem / (NAT.dem + NAT.rep)));
    const s = cur && cur.byAbbr[a];
    return s ? shareColor(s.demShare) : greyColor();
  }
  function pick28(a) { pinned28 = a === pinned28 ? null : a; map28.mark(pinned28); insp28(pinned28); }
  const draw28 = () => drawUS(document.getElementById('map-2028'), { fill: fill28, selected: pinned28, onPick: pick28, onHover: a => { insp28(a || pinned28); map28.mark(a || pinned28); } });

  // Map layers. "Real forecast" shows a countdown, not a map, until July 30, 2028.
  function setLayer28(l) {
    layer28 = l;
    document.querySelectorAll('[data-layer28]').forEach(x => x.setAttribute('aria-selected', x.dataset.layer28 === l));
    document.getElementById('desk-28').hidden = l === 'official';
    document.getElementById('official-28').hidden = l !== 'official';
    if (l !== 'official') { map28.recolor(fill28); insp28(pinned28); }
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
    document.getElementById('beam').innerHTML = beamSVG();
    map28 = draw28();
    ramp(document.getElementById('ramp-2028'), 'share');
    document.querySelectorAll('[data-layer28]').forEach(b => b.addEventListener('click', () => setLayer28(b.dataset.layer28)));
    document.getElementById('btn-to-nowcast').addEventListener('click', () => setLayer28('tracker'));
    if (!N) {
      ['hero-28', 'builder', 'results-detail', 'tracker-detail'].forEach(id => { document.getElementById(id).hidden = true; });
      document.getElementById('live-pill').textContent = 'Waiting for the first data run';
      setLayer28('official'); return;
    }
    document.getElementById('live-pill').textContent = `Live · updated ${niceDate(N.generated_at)}`;
    document.getElementById('live-inputs').innerHTML = `<b>Live data (automatic):</b> National approval ${fmt(N.approval.approve)} from ${N.approval.pollsters} pollsters through ${niceDate(N.approval.window[1])} · state-by-state differences from Morris's estimates of September 22, 2026 · state economies through ${monthName(N.economy.through)}. Only the tickets can be changed above.`;
    const picks = [...document.querySelectorAll('.pick')];
    picks.forEach(buildPick);
    const locked = Object.keys(ROLES).filter(official).length;
    document.getElementById('builder-h').textContent = locked === 4 ? 'The tickets are set' : 'Pick the tickets';
    document.getElementById('builder-p').textContent = locked === 4
      ? 'Both tickets are confirmed, so the Nowcast uses them and they can no longer be changed.'
      : 'The nominees are not known yet, so each party\'s field is weighted by its polling. Choose who you think will be on each ticket to see what their home states and head-to-head polls do to the map. Each nominee and running mate locks in automatically once confirmed.';
    const reset = document.getElementById('btn-reset');
    reset.hidden = locked === 4;
    reset.addEventListener('click', () => { picks.forEach(buildPick); schedule(); });
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
