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
  function snake(el, readEl, items, label) {
    const rows = items.filter(i => i.ev > 0).slice().sort((a, b) => b.share - a.share);
    let cum = 0, tp = null;
    rows.forEach(r => { r.before = cum; cum += r.ev; r.after = cum; if (!tp && cum >= 270) tp = r; });
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

  // ---------- geographic map ----------
  function drawUS(svg, { fill, onPick, onHover, selected }) {
    const W = 1075, H = 610;
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
    let o = '';
    for (const [a, s] of Object.entries(SHAPES)) o += `<path class="st" data-a="${a}" d="${s.d}" fill="${fill(a)}" tabindex="0" aria-label="${byAbbr[a].name}"></path>`;
    for (const [a, s] of Object.entries(SHAPES)) {
      if (SMALL.includes(a)) continue;
      const [dx, dy] = LABEL_NUDGE[a] || [0, 0];
      o += `<text class="lbl" x="${s.c[0] + dx}" y="${s.c[1] + dy + 3}">${a}</text>`;
    }
    const bx = 1005, bw = 54, bh = 21;
    SMALL.forEach((a, i) => {
      const y = 118 + i * 27, c = SHAPES[a].c;
      o += `<line class="leader" x1="${c[0]}" y1="${c[1]}" x2="${bx}" y2="${y + bh / 2}"></line>`;
      o += `<g class="box" data-a="${a}" tabindex="0" aria-label="${byAbbr[a].name}"><rect x="${bx}" y="${y}" width="${bw}" height="${bh}" rx="4" fill="${fill(a)}"></rect><text x="${bx + bw / 2}" y="${y + 14.5}">${a}</text></g>`;
    });
    o += `<text class="grp" x="${bx}" y="384">Districts</text>`;
    DISTRICTS.forEach((a, i) => {
      const y = 392 + i * 27;
      o += `<g class="box" data-a="${a}" tabindex="0" aria-label="${byAbbr[a].name}"><rect x="${bx}" y="${y}" width="${bw}" height="${bh}" rx="4" fill="${fill(a)}"></rect><text x="${bx + bw / 2}" y="${y + 14.5}">${dname(a)}</text></g>`;
    });
    o += '<path class="sel" d=""></path>';
    svg.innerHTML = o;
    const sel = svg.querySelector('.sel');
    const mark = a => {
      svg.querySelectorAll('g.box').forEach(g => g.classList.toggle('on', g.dataset.a === a));
      sel.setAttribute('d', SHAPES[a] ? SHAPES[a].d : '');
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

  // ---------- dates ----------
  const FORECAST_DATE = new Date('2028-07-30T00:00:00-04:00');
  const ELECTION_DATE = new Date('2028-11-07T00:00:00-05:00');
  const daysTo = d => Math.max(0, Math.ceil((d - new Date()) / 86400000));
  const monthName = ym => new Date(ym + '-15').toLocaleDateString('en-US', { month: 'long', year: 'numeric' });
  const niceDate = iso => new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });

  // ================= HOME =================
  function renderHome() {
    document.getElementById('hero-2024').innerHTML = strip({ f: NAT.fc, a: natActual }, 40, 60);
    document.getElementById('hero-2024-read').innerHTML =
      `Forecast <b class="a-ink">${fmt(NAT.fc)}</b><br>Result <b>${fmt(natActual)}</b><br>Trump won, as the model gave ${Math.round(100 * (1 - NAT.pDemWin))}% odds`;
    const el = document.getElementById('hero-2028'), rd = document.getElementById('hero-2028-read');
    if (N && !N.fixture_run) {
      el.className = 'strip';
      el.innerHTML = strip({ f: N.summary.demPopular }, 40, 60);
      rd.innerHTML = `If held today <b class="a-ink">${fmt(N.summary.demPopular)}</b><br>Democrat wins ${Math.round(100 * N.summary.pDemWin)}% of simulations<br><a href="#forecast-2028">Try any matchup</a>`;
    } else {
      el.innerHTML = `<div class="pending">Real forecast publishes July 30, 2028</div>`;
      rd.innerHTML = `${daysTo(FORECAST_DATE)} days to go<br><a href="#forecast-2028">See 2028 today</a>`;
    }
    const views = {
      fc: [R.map(r => ({ abbr: r.abbr, ev: r.ev, share: r.fc })), '2024 forecast'],
      actual: [R.map(r => ({ abbr: r.abbr, ev: r.ev, share: r.share })), '2024 result'],
      today: N ? [N.states.map(s => ({ abbr: s.abbr, ev: s.ev, share: s.demShare })), '2028 if held today'] : null,
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

    map24 = drawUS(document.getElementById('map-2024'), { fill: fill24, selected: null, onPick: pick24, onHover: a => { insp24(a || pinned24); map24.mark(a || pinned24); } });
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

  // ================= 2028: if held today + matchup builder =================
  let layer28 = 'tracker', pinned28 = null, map28, cur = null;   // cur = current simulation result
  const ROLES = { 'dem-p': ['D', 'Democratic nominee'], 'dem-vp': ['D', 'Running mate'], 'rep-p': ['R', 'Republican nominee'], 'rep-vp': ['R', 'Running mate'] };
  const TICKET_KEY = { 'dem-p': ['dem', 'president'], 'dem-vp': ['dem', 'vp'], 'rep-p': ['rep', 'president'], 'rep-vp': ['rep', 'vp'] };
  const norm = s => (s || '').toLowerCase().replace(/[^a-z]/g, '');

  function official(role) { const [side, k] = TICKET_KEY[role]; return (N.tickets[side] || {})[k] || null; }

  function buildPick(box) {
    const role = box.dataset.role, [party, label] = ROLES[role];
    const off = official(role);
    const people = N.scenario.candidates.filter(c => c.party === party).slice().sort((a, b) => a.name.localeCompare(b.name));
    let opts = `<option value="">No one yet</option>`;
    if (off && off.name) opts += `<option value="__official">${esc(off.name)}${off.state ? ' (' + off.state + ')' : ''}, official</option>`;
    opts += `<optgroup label="Possible candidates">` + people.map(c => `<option value="${esc(c.name)}">${esc(c.name)} (${c.state})</option>`).join('') + `</optgroup>`;
    opts += `<option value="__custom">Someone else…</option>`;
    box.innerHTML = `<label for="sel-${role}">${label}</label><select id="sel-${role}">${opts}</select>
      <div class="custom" hidden><input id="nm-${role}" type="text" placeholder="Name" aria-label="${label} name"><select id="st-${role}" aria-label="${label} home state">${STATE_LIST.map(([a, n]) => `<option value="${a}">${a}</option>`).join('')}</select></div>`;
    const sel = box.querySelector('select'), custom = box.querySelector('.custom');
    sel.value = off && off.name ? '__official' : '';
    sel.addEventListener('change', () => { custom.hidden = sel.value !== '__custom'; if (!custom.hidden) box.querySelector('input').focus(); schedule(); });
    box.querySelector('input').addEventListener('input', () => schedule());
    box.querySelector('#st-' + role).addEventListener('change', () => schedule());
  }

  function readPick(role) {
    const v = document.getElementById('sel-' + role).value;
    if (!v) return null;
    if (v === '__official') { const o = official(role); return { name: o.name, state: o.state }; }
    if (v === '__custom') return { name: document.getElementById('nm-' + role).value.trim() || 'Custom candidate', state: document.getElementById('st-' + role).value };
    const c = N.scenario.candidates.find(x => x.name === v);
    return { name: c.name, state: c.state };
  }

  function runScenario(n = 10000) {
    const S = N.scenario, sign = S.sign, C = S.constant;
    const picks = Object.fromEntries(Object.keys(ROLES).map(r => [r, readPick(r)]));
    const dA = +document.getElementById('sl-appr').value, dE = +document.getElementById('sl-econ').value;
    const vpNom = ['dem-p', 'rep-p'].find(r => picks[r] && norm(picks[r].name) === norm(N.sitting_vp));
    const vpShift = vpNom && N.vp.gap != null ? N.vp.gap : 0;
    const code = (st, d, r) => (st && st === d ? 1 : 0) - (st && st === r ? 1 : 0);
    const st = r => picks[r] && picks[r].state;
    const states = S.states.map(s => ({
      abbr: s.abbr, ev: s.ev, pop: s.pop,
      inputs: {
        lagDev: s.lagDev, approval: sign * (s.approve + dA + vpShift - C), econ: 0,
        home: code(s.abbr, st('dem-p'), st('rep-p')), homeLag: code(s.abbr, S.homeLag.dem, S.homeLag.rep),
        vpHome: code(s.abbr, st('dem-vp'), st('rep-vp')), anderson: 0, perot: 0,
      },
    }));
    const econVariants = S.econVariants.map(v => Object.fromEntries(Object.entries(v).map(([k, x]) => [k, x + sign * dE])));
    states.forEach(s => { s.inputs.econ = econVariants[Math.floor(econVariants.length / 2)][s.abbr]; });
    cur = window.SPASE.simulate({ states, districts: S.districts, n, seed: 2028, econVariants });
    cur.picks = picks; cur.vpNom = vpNom; cur.vpShift = vpShift; cur.dA = dA; cur.dE = dE;
    cur.byAbbr = Object.fromEntries(cur.states.map(s => [s.abbr, s]));
    showResults();
  }

  let timer = null;
  function schedule(quick) {
    quick = quick === true;
    document.getElementById('out-appr').textContent = fmt(N.approval.approve + +document.getElementById('sl-appr').value);
    const e = +document.getElementById('sl-econ').value;
    document.getElementById('out-econ').textContent = e === 0 ? 'as measured' : `${e > 0 ? '+' : '−'}${Math.abs(e).toFixed(2)} pts/month`;
    document.getElementById('results-2028').classList.add('busy');
    clearTimeout(timer);
    timer = setTimeout(() => { runScenario(quick ? 1500 : 10000); document.getElementById('results-2028').classList.remove('busy'); }, quick ? 30 : 120);
  }

  function effectsList() {
    const p = cur.picks, out = [];
    const who = r => p[r] ? `${esc(p[r].name)} (${p[r].state})` : null;
    if (!p['dem-p'] && !p['rep-p'] && !p['dem-vp'] && !p['rep-vp']) out.push(`<b>No tickets chosen.</b> Home-state bonuses switch on once you pick candidates, or automatically when the conventions choose them.`);
    if (p['dem-p']) out.push(`<b>Home state:</b> ${who('dem-p')} adds about 2.5 points for the Democrat in ${byAbbr[p['dem-p'].state].name}.`);
    if (p['rep-p']) out.push(`<b>Home state:</b> ${who('rep-p')} adds about 2.5 points for the Republican in ${byAbbr[p['rep-p'].state].name}.`);
    if (p['dem-vp']) out.push(`<b>Running mate:</b> ${who('dem-vp')} adds about 1.9 points for the Democrat in ${byAbbr[p['dem-vp'].state].name}.`);
    if (p['rep-vp']) out.push(`<b>Running mate:</b> ${who('rep-vp')} adds about 1.9 points for the Republican in ${byAbbr[p['rep-vp'].state].name}.`);
    if (p['dem-p'] && p['rep-p'] && p['dem-p'].state === p['rep-p'].state) out.push(`Both nominees are from ${byAbbr[p['dem-p'].state].name}, so their home-state bonuses cancel out.`);
    out.push(`<b>2024 home states fade:</b> Harris's California and Trump's Florida each give back about 3.5 points of their 2024 boost.`);
    if (cur.vpNom) out.push(N.vp.gap != null
      ? `<b>Vice-president adjustment on:</b> ${esc(N.sitting_vp)} is the sitting vice president, so state approval shifts by ${sgn(N.vp.gap, 1)} points, his net favorability minus Trump's (${esc(N.vp.basis)}).`
      : `<b>Vice-president adjustment:</b> ${esc(N.sitting_vp)} is the sitting vice president, but there are no recent favorability polls to measure the gap.`);
    else out.push(`<b>Vice-president adjustment off:</b> it applies only if the sitting vice president, ${esc(N.sitting_vp)}, is a nominee${N.vp.gap != null ? ` (it would shift approval by ${sgn(N.vp.gap, 1)} points today)` : ''}.`);
    if (cur.dA) out.push(`<b>What if:</b> Trump approval set to ${fmt(N.approval.approve + cur.dA)} instead of today's ${fmt(N.approval.approve)}.`);
    if (cur.dE) out.push(`<b>What if:</b> every state's economy grows ${cur.dE > 0 ? 'faster' : 'slower'} by ${Math.abs(cur.dE).toFixed(2)} points a month.`);
    document.getElementById('effects').innerHTML = out.map(x => `<li>${x}</li>`).join('');
  }

  function showResults() {
    const s = cur, rep = 1 - s.pDemWin - s.pTie;
    let cum = 0, median = 0;
    for (let i = 0; i < s.evHistogram.length; i++) { cum += s.evHistogram[i]; if (cum >= 0.5) { median = i; break; } }
    const lead = s.pDemWin >= rep ? 'd-ink' : 'r-ink';
    document.getElementById('figs-2028').innerHTML = [
      [`${Math.round(100 * s.pDemWin)}%`, 'Democrat wins', 'd-ink'],
      [`${Math.round(100 * rep)}%`, 'Republican wins', 'r-ink'],
      [fmt(s.demPopular), 'Democratic two-party vote', lead],
      [`${median}`, 'Median Democratic electoral votes', lead],
    ].map(([v, l, c]) => `<div><span class="v ${c}">${v}</span><span class="l">${l}</span></div>`).join('');
    snake(document.getElementById('snake-2028'), document.getElementById('snake-2028-read'),
      s.states.map(x => ({ abbr: x.abbr, ev: x.ev, share: x.demShare })), 'If held today');
    histogram(document.getElementById('hist-2028'), s.evHistogram);
    if (map28) map28.recolor(fill28);
    insp28(pinned28);
    effectsList();
  }

  function insp28(a) {
    const el = document.getElementById('insp-2028');
    const natShare = 100 * NAT.dem / (NAT.dem + NAT.rep);
    if (layer28 === 'official') {
      el.innerHTML = `<span class="tag">Real forecast</span><h3>Not yet published</h3><p class="small">The real 2028 forecast uses the nominees, approval surveys from June and July 2028 and economic data through June 2028. It publishes July 30, 2028, ${daysTo(FORECAST_DATE)} days from now. Everything on this page until then is "if the election were held today."</p>`;
      return;
    }
    if (layer28 === 'lean') {
      const r = a ? byAbbr[a] : null;
      el.innerHTML = r ? `<span class="tag">${dname(a)} · ${r.ev} electoral vote${r.ev > 1 ? 's' : ''}</span><h3>${r.name}</h3>
        <dl class="kv"><div><dt>2024 D share</dt><dd class="d-ink">${fmt(r.share, 2)}</dd></div><div><dt>Lean vs. nation</dt><dd>${sgn(r.share - natShare)} pts</dd></div><div><dt>Model weight</dt><dd>0.82 × lean</dd></div></dl>
        <div class="strip">${strip({ a: r.share })}</div>`
        : `<span class="tag">The one input already known</span><h3>2024 lean</h3><p class="small">Each state's Democratic share in 2024 relative to the nation (${fmt(natShare, 2)}). The model carries 82% of this lean into 2028.</p>`;
      return;
    }
    if (!cur) { el.innerHTML = `<span class="tag">If held today</span><h3>Waiting for data</h3><p class="small">This fills in after the first daily data run.</p>`; return; }
    const s = a ? cur.byAbbr[a] : null;
    if (!s) {
      el.innerHTML = `<span class="tag">If held today${N.fixture_run ? '<span class="test-flag">TEST DATA</span>' : ''}</span><h3>National picture</h3>
        <dl class="kv">
          <div><dt>Democratic two-party vote</dt><dd class="d-ink">${fmt(cur.demPopular, 2)}</dd></div>
          <div><dt>Democratic win chance</dt><dd>${Math.round(100 * cur.pDemWin)}%</dd></div>
          <div><dt>Trump approval</dt><dd>${fmt(N.approval.approve + cur.dA)}</dd></div>
          <div><dt>Economy data through</dt><dd>${monthName(N.economy.through)}</dd></div>
        </dl>
        <div class="strip">${strip({ f: cur.demPopular })}</div>
        <p class="hint">Not the forecast. Hover a state for its numbers.</p>`;
      return;
    }
    const r = byAbbr[a], base = N.scenario.states.find(x => x.abbr === a);
    el.innerHTML = `<span class="tag">${dname(a)} · ${r.ev} electoral vote${r.ev > 1 ? 's' : ''}</span><h3>${r.name}</h3>
      <dl class="kv">
        <div><dt>D share if held today</dt><dd class="d-ink">${fmt(s.demShare, 2)}</dd></div>
        <div><dt>2024 D share</dt><dd>${fmt(r.share, 2)}</dd></div>
        <div><dt>Democratic win chance</dt><dd>${Math.round(100 * s.pDem)}%</dd></div>
        <div><dt>Rating</dt><dd>${RATING[s.rating] || s.rating}</dd></div>
        ${base ? `<div><dt>Trump approval (est.)</dt><dd>${fmt(base.approve + cur.dA)}</dd></div>` : ''}
      </dl>
      <div class="strip">${strip({ f: s.demShare, a: r.share })}</div>
      <div class="strip-legend"><span><i class="f"></i>If held today</span><span><i class="a"></i>2024 result</span></div>`;
  }
  function fill28(a) {
    const natShare = 100 * NAT.dem / (NAT.dem + NAT.rep);
    if (layer28 === 'official') return greyColor();
    if (layer28 === 'lean') return shareColor(50 + (byAbbr[a].share - natShare));
    const s = cur && cur.byAbbr[a];
    return s ? shareColor(s.demShare) : greyColor();
  }
  function pick28(a) { pinned28 = a === pinned28 ? null : a; map28.mark(pinned28); insp28(pinned28); }

  function render2028() {
    document.getElementById('d-forecast').textContent = daysTo(FORECAST_DATE);
    document.getElementById('d-election').textContent = daysTo(ELECTION_DATE);
    map28 = drawUS(document.getElementById('map-2028'), { fill: fill28, selected: null, onPick: pick28, onHover: a => { insp28(a || pinned28); map28.mark(a || pinned28); } });
    const setRamp = () => ramp(document.getElementById('ramp-2028'), layer28 === 'official' ? 'none' : 'share');
    setRamp();
    document.querySelectorAll('[data-layer28]').forEach(b => b.addEventListener('click', () => {
      layer28 = b.dataset.layer28;
      document.querySelectorAll('[data-layer28]').forEach(x => x.setAttribute('aria-selected', x === b));
      map28.recolor(fill28); setRamp(); insp28(pinned28);
    }));
    if (!N) {
      ['builder', 'tracker-detail'].forEach(id => { document.getElementById(id).hidden = true; });
      document.getElementById('live-pill').textContent = 'Waiting for the first data run';
      layer28 = 'official'; map28.recolor(fill28); insp28(null); return;
    }
    document.getElementById('live-pill').textContent = `Live · updated ${niceDate(N.generated_at)}`;
    document.getElementById('stamp-2028').textContent = `Polls through ${niceDate(N.approval.window[1])} · economy through ${monthName(N.economy.through)}`;
    document.querySelectorAll('.pick').forEach(buildPick);
    ['sl-appr', 'sl-econ'].forEach(id => {
      const el = document.getElementById(id);
      el.addEventListener('input', () => schedule(true));   // quick pass while dragging
      el.addEventListener('change', () => schedule());      // full 70,000 on release
    });
    document.getElementById('btn-reset').addEventListener('click', () => {
      document.getElementById('sl-appr').value = 0; document.getElementById('sl-econ').value = 0;
      document.querySelectorAll('.pick').forEach(buildPick); schedule();
    });
    const t = N.tickets, set = ['dem', 'rep'].filter(s => t[s] && t[s].president).length;
    document.getElementById('need-tickets').textContent = set ? `Detected ${set === 2 ? 'both tickets' : 'one ticket'}` : 'Watching, none yet';
    document.getElementById('need-vp').textContent = N.vp.applied ? `On, ${sgn(N.vp.gap, 1)} pts` : 'Off until a VP is nominated';
    document.getElementById('need-econ').textContent = `Daily, through ${monthName(N.economy.through)}`;
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
      document.getElementById('trend-2028').innerHTML = `<svg viewBox="0 0 ${W} ${Ht}" role="img" aria-label="Democratic win chance over time">${o}</svg>`;
    }
    schedule();
  }

  // ================= routing =================
  const VIEWS = ['home', 'results-2024', 'forecast-2028', 'method'];
  const done = {};
  function route() {
    const h = location.hash.replace('#', '');
    const v = VIEWS.includes(h) ? h : 'home';
    VIEWS.forEach(n => document.getElementById('view-' + n).hidden = n !== v);
    document.querySelectorAll('nav a').forEach(a => a.dataset.view === v ? a.setAttribute('aria-current', 'page') : a.removeAttribute('aria-current'));
    if (!done[v]) {
      if (v === 'home') renderHome();
      if (v === 'results-2024') render2024();
      if (v === 'forecast-2028') render2028();
      done[v] = true;
    }
    window.scrollTo(0, 0);
  }
  window.addEventListener('hashchange', route);
  route();
})();
