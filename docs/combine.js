/*
 * The 2028 Nowcast: three models, averaged state by state with equal weights and simulated together.
 *
 *   1. Enns, Colner, Kumar & Lagodny (2024): state approval and state economy (engine.js).
 *   2. DeSart (2025), "Long-Range State-Level 2024 Presidential Election Forecast",
 *      PS: Political Science & Politics 58(2), doi:10.1017/S1049096524000805:
 *      previous result, national head-to-head polls, home state, consecutive terms.
 *   3. Five of Lichtman's objective Keys to the White House, counted and turned into a national vote
 *      (pipeline/keys.py), spread to the states by shifting the 2024 results.
 *
 * The site (app.js) and the daily run (pipeline/run_forecast.js) both call run(),
 * so the published numbers and the ones in the browser are the same.
 */
(function (root) {
  const SPASE = root.SPASE || require(require('path').join(__dirname, 'engine.js'));

  // DeSart, Table 2 (1996-2020 estimates, as published). se is the standard error of the estimate.
  const DESART_PAPER = { constant: -27.423, prior: 1.017, polls: 0.524, home: 2.544, terms: -0.988, se: 3.08 };
  // The model the Nowcast runs: the same regression refitted on 1996-2024 from DeSart's replication data
  // (doi:10.7910/DVN/HZGLY9) with 2024 added (October 2023 poll average 49.53%, Harris CA, Trump FL), as he
  // refits before each forecast. Refitting on 1996-2020 reproduces Table 2 exactly.
  const DESART = { constant: -26.91544, prior: 1.00662, polls: 0.52232, home: 1.90685, terms: -0.9966, se: 2.93309 };
  const norm = s => (s || '').toLowerCase().replace(/[^a-z]/g, '');

  function mulberry32(seed) {
    return function () {
      seed |= 0; seed = seed + 0x6D2B79F5 | 0;
      let t = Math.imul(seed ^ seed >>> 15, 1 | seed);
      t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
      return ((t ^ t >>> 14) >>> 0) / 4294967296;
    };
  }
  function normal(rand) {
    let u = 0; while (u === 0) u = rand();
    return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * rand());
  }

  /*
   * prior  Democratic two-party share in the state, previous election
   * polls  average Democratic two-party share in national head-to-head polls
   * home   this election's home states (+ Democrat, - Republican) minus the previous election's
   * terms  consecutive terms the incumbent party has held the White House (+ Democrats, - Republicans)
   */
  function desartPredict(prior, polls, home, terms, c = DESART) {
    return c.constant + c.prior * prior + c.polls * polls + c.home * home + c.terms * terms;
  }

  /*
   * DeSart's own simulation, kept to check this code against his paper; the Nowcast does not use it.
   * Each state's forecast gets its own normal error of 3.08 points, nothing shared between states.
   * Run on the paper's 2024 inputs this reproduces its published results (mean 256 Democratic
   * electoral votes, 95% range 218 to 306, a Democratic win in about 1 simulation in 4).
   */
  function desartSimulate({ states, districts = [], polls, terms, n = 20000, seed = 2028 }) {
    const rand = mulberry32(seed), nS = states.length;
    const point = states.map(s => desartPredict(s.prior, polls, s.home || 0, terms, DESART_PAPER));
    const dIdx = districts.map(d => states.findIndex(s => s.abbr === d.parent));
    const wins = new Float64Array(nS + districts.length), share = new Float64Array(nS);
    const evHist = new Array(539).fill(0);
    const popTotal = states.reduce((a, s) => a + (s.pop || 1), 0);
    let demWins = 0, ties = 0, popSum = 0;
    for (let it = 0; it < n; it++) {
      let ev = 0, pop = 0;
      for (let i = 0; i < nS; i++) {
        const y = point[i] + DESART_PAPER.se * normal(rand);
        share[i] = y;
        pop += y * (states[i].pop || 1);
        if (y > 50) { ev += states[i].ev; wins[i]++; }
      }
      for (let k = 0; k < districts.length; k++) {
        if (share[dIdx[k]] + districts[k].offset > 50) { ev += districts[k].ev; wins[nS + k]++; }
      }
      evHist[ev]++;
      if (ev >= 270) demWins++; if (ev === 269) ties++;
      popSum += pop / popTotal;
    }
    const byState = states.map((s, i) => ({ abbr: s.abbr, ev: s.ev, demShare: point[i], pDem: wins[i] / n }))
      .concat(districts.map((d, k) => ({ abbr: d.abbr, ev: d.ev, demShare: point[dIdx[k]] + d.offset, pDem: wins[nS + k] / n })));
    byState.forEach(s => { s.rating = SPASE.rate(s.pDem); });
    return { simulations: n, pDemWin: demWins / n, pTie: ties / n, demPopular: popSum / n, evHistogram: evHist.map(c => c / n), states: byState };
  }


  // Before the nominees are known, DeSart spreads each party's home-state effect over its possible
  // nominees. For his model the weights are how often each candidate appears in the head-to-head
  // polls, as in the paper. For the approval and economy model they are shares of primary polling.
  function primaryField(cands, party) {
    const list = cands.filter(c => c.party === party && c.primary > 0), tot = list.reduce((a, c) => a + c.primary, 0);
    return list.map(c => ({ name: c.name, state: c.state, w: c.primary / tot }));
  }
  function pollField(polls, cands, key) {
    const count = {};
    polls.forEach(p => { count[p[key]] = (count[p[key]] || 0) + 1; });
    return Object.keys(count).map(name => {
      const c = cands.find(x => x.name === name);
      return { name, state: c ? c.state : null, w: count[name] / polls.length, polls: count[name] };
    }).sort((a, b) => b.w - a.w);
  }
  const fieldAt = (field, st) => field.reduce((a, f) => a + (f.state === st ? f.w : 0), 0);

  // Which head-to-head polls speak to the chosen nominees. Too few polls of a choice falls back to a wider set.
  function pickPolls(h2h, dp, rp) {
    const all = h2h.polls, min = h2h.min_polls || 3, D = dp && dp.name, R = rp && rp.name;
    const use = (polls, basis) => ({ polls, basis, avg: polls.reduce((a, p) => a + p.share, 0) / polls.length });
    if (D && R) {
      const exact = all.filter(p => p.d === D && p.r === R);
      if (exact.length >= min) return use(exact, 'matchup');
      const either = all.filter(p => p.d === D || p.r === R);
      if (either.length >= min) return use(either, 'either');
    } else if (D || R) {
      const one = all.filter(p => D ? p.d === D : p.r === R);
      if (one.length >= min) return use(one, 'one');
    }
    return use(all, 'all');
  }

  /*
   * N      the daily payload (window.NOWCAST)
   * picks  { dp, rp, dv, rv }: nominee and running mate per party as { name, state }, or null if not chosen
   * Returns { combined, enns, desart, keys, info }: the average and each model alone, all simulated the same
   * way. desart is null without head-to-head polls and keys is null when the keys are not scored; the average
   * is then taken over the models that are available. With parts: false only combined is run (faster). keep: how many of the combined
   * simulations to keep draw by draw (see docs/engine.js), returned as combined.draws.
   */
  function run(N, picks = {}, { n = 10000, seed = 2028, forceVpShift = null, parts = true, keep = 0 } = {}) {
    const S = N.scenario, { dp, rp, dv, rv } = picks;
    const lagW = S.homeLagWeight || { dem: 1, rep: 1 };
    const fieldD = primaryField(S.candidates, 'D'), fieldR = primaryField(S.candidates, 'R');
    const isVp = p => !!p && norm(p.name) === norm(N.sitting_vp);
    const gap = N.vp && N.vp.gap != null ? N.vp.gap : 0;
    const vpNom = isVp(dp) || isVp(rp);
    // The vice-president adjustment: in full if he is the chosen nominee, by his share of his
    // party's field while that party's nominee is open, and not at all otherwise.
    const vpIn = [[fieldD, dp], [fieldR, rp]].map(([f, p]) => p ? 0 : f.reduce((a, x) => a + (norm(x.name) === norm(N.sitting_vp) ? x.w : 0), 0));
    const vpWeight = vpNom ? 1 : Math.max(vpIn[0], vpIn[1]);
    const vpShift = forceVpShift != null ? forceVpShift : gap * vpWeight;
    const homeD = st => dp ? (dp.state === st ? 1 : 0) : fieldAt(fieldD, st);
    const homeR = st => rp ? (rp.state === st ? 1 : 0) : fieldAt(fieldR, st);
    const states = S.states.map(s => ({
      abbr: s.abbr, ev: s.ev, pop: s.pop,
      inputs: {
        lagDev: s.lagDev, approval: S.sign * (s.approve + vpShift - S.constant), econ: S.econVariants[Math.floor(S.econVariants.length / 2)][s.abbr],
        home: homeD(s.abbr) - homeR(s.abbr),
        homeLag: (s.abbr === S.homeLag.dem ? lagW.dem : 0) - (s.abbr === S.homeLag.rep ? lagW.rep : 0),
        vpHome: (dv && dv.state === s.abbr ? 1 : 0) - (rv && rv.state === s.abbr ? 1 : 0), anderson: 0, perot: 0,
      },
    }));
    // Every run uses the approval and economy model's simulation: its coefficient draws, its seven economic
    // weightings, and its model error, most of it shared by every state. mix sets how much of each state's
    // forecast comes from the polls model instead.
    const sim = (weight, point, kp = 0) => SPASE.simulate({ states, districts: S.districts, n, seed, econVariants: weight === 0 ? null : S.econVariants,
      mix: point ? { weight, point } : null, keep: kp });
    const info = { vpNom, vpShift, vpWeight, fieldD, fieldR, polls: null, keys: null };
    const h = N.h2h, K = N.keys, priors = !S.states.some(s => s.prior == null);
    let dPoint = null, kPoint = null;
    if (priors && h && h.polls && h.polls.length) {
      const sel = pickPolls(h, dp, rp);
      const pollD = pollField(h.polls, S.candidates, 'd'), pollR = pollField(h.polls, S.candidates, 'r');
      const hD = st => dp ? (dp.state === st ? 1 : 0) : fieldAt(pollD, st);
      const hR = st => rp ? (rp.state === st ? 1 : 0) : fieldAt(pollR, st);
      dPoint = Object.fromEntries(S.states.map(s => [s.abbr, desartPredict(s.prior, sel.avg,
        hD(s.abbr) - hR(s.abbr) - (s.abbr === S.homeLag.dem ? 1 : 0) + (s.abbr === S.homeLag.rep ? 1 : 0), h.terms)]));
      info.polls = { avg: sel.avg, n: sel.polls.length, basis: sel.basis, total: h.polls.length, pollD, pollR };
    }
    // The keys give one national vote; each state moves from its 2024 result by the same amount.
    if (priors && K && K.demNational != null) {
      const shift = K.demNational - K.base;
      kPoint = Object.fromEntries(S.states.map(s => [s.abbr, s.prior + shift]));
      info.keys = { false: K.false, pending: K.pending, demNational: K.demNational };
    }
    const others = [dPoint, kPoint].filter(Boolean);
    if (!others.length) {
      const enns = sim(1, null, keep);
      return { combined: enns, enns, desart: null, keys: null, info };
    }
    // Equal weights: the approval and economy model's share is 1/3 with both others (1/2 with one), and the
    // rest is the average of the others.
    const wE = 1 / (1 + others.length);
    const otherPoint = Object.fromEntries(S.states.map(s => [s.abbr, others.reduce((a, p) => a + p[s.abbr], 0) / others.length]));
    const combined = sim(wE, otherPoint, keep);
    if (!parts) return { combined, enns: null, desart: null, keys: null, info };
    const enns = sim(1), desart = dPoint ? sim(0, dPoint) : null, keys = kPoint ? sim(0, kPoint) : null;
    const by = m => m && Object.fromEntries(m.states.map(x => [x.abbr, x]));
    const eBy = by(enns), dBy = by(desart), kBy = by(keys);
    combined.states.forEach(x => {
      x.enns = eBy[x.abbr].demShare; x.ennsP = eBy[x.abbr].pDem;
      if (dBy) { x.desart = dBy[x.abbr].demShare; x.desartP = dBy[x.abbr].pDem; }
      if (kBy) { x.keys = kBy[x.abbr].demShare; x.keysP = kBy[x.abbr].pDem; }
    });
    return { combined, enns, desart, keys, info };
  }

  const api = { DESART, DESART_PAPER, desartPredict, desartSimulate, pickPolls, pollField, primaryField, run };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.TP = api;
})(typeof window !== 'undefined' ? window : globalThis);
