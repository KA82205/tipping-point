/*
 * State Presidential Approval / State Economy Model
 * Enns, Colner, Kumar & Lagodny (2024), PS: Political Science & Politics
 * doi:10.1017/S1049096524000994  (CC BY-NC 4.0)
 *
 * Predicts the Democratic share of the two-party vote in each state and DC,
 * then simulates the Electoral College.
 *
 * Per-state inputs (all measured >= 100 days before Election Day):
 *   lagDev     state Dem two-party share minus national Dem share, previous election (pts)
 *   approval   MRP state approval of the president, minus the fitted constant,
 *              multiplied by -1 when the president is a Republican.
 *              If the incumbent VP is the nominee, add (VP net approval - president net approval).
 *   econ       cumulative weighted avg. monthly % change in the Philadelphia Fed
 *              State Coincident Index through June of the election year
 *              (sign-flipped for a Republican incumbent, like approval)
 *   home       +1 Dem presidential candidate's state, -1 Rep's, 0 otherwise
 *   homeLag    the same coding for the previous election's candidates
 *   vpHome     +1 Dem VP candidate's state, -1 Rep's, 0 otherwise
 *   anderson   John Anderson 1980 share (1984 only), else 0
 *   perot      Ross Perot 1996 share (2000 only), else 0
 */
(function (root) {
  // Table 1, 1980-2020 estimates and standard errors.
  const COEFS = {
    constant: { b: 49.38, se: 0.17 },
    lagDev:   { b: 0.82,  se: 0.02 },
    approval: { b: 0.33,  se: 0.02 },
    econ:     { b: 1.43,  se: 0.27 },
    home:     { b: 2.47,  se: 0.81 },
    homeLag:  { b: -3.49, se: 0.82 },
    vpHome:   { b: 1.87,  se: 0.74 },
    anderson: { b: -0.35, se: 0.07 },
    perot:    { b: -0.60, se: 0.06 },
  };
  const RMSE = 3.46;          // standard error of the estimate
  const VARS = Object.keys(COEFS).filter(k => k !== 'constant');

  // Rating thresholds from Figure 2 (share of simulations won).
  function rate(pDem) {
    const p = Math.max(pDem, 1 - pDem), party = pDem >= 0.5 ? 'D' : 'R';
    if (p > 0.98) return 'S' + party;
    if (p > 0.75) return 'L' + party;
    if (p > 0.55) return 'T' + party;
    return 'TOSS';
  }

  function predict(inputs, coefs = COEFS) {
    let y = coefs.constant.b;
    for (const v of VARS) y += coefs[v].b * (inputs[v] || 0);
    return y;
  }

  // Seeded PRNG so a published forecast is reproducible.
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
   * states:    [{ abbr, ev, pop, inputs: {...} }]  (50 states + DC)
   * districts: [{ abbr, parent, ev, offset }]      offset = district Dem share minus
   *                                                 statewide Dem share, previous election
   * econVariants (optional): array of per-state econ maps, one per weight parameter
   *            (the paper uses the chosen weight plus three above and three below).
   *
   * Parameter draws are independent normals from the Table 1 SEs. The paper's
   * CLARIFY draws use the full covariance matrix, which needs the replication data.
   * One model-error draw per state per simulation, as described in the paper.
   */
  function simulate({ states, districts = [], n = 10000, seed = 2028, econVariants = null }) {
    const rand = mulberry32(seed);
    const variants = econVariants && econVariants.length ? econVariants : [null];
    const all = states.concat(districts);
    const wins = Object.fromEntries(all.map(s => [s.abbr, 0]));
    const evHist = new Array(539).fill(0);
    let demWins = 0, ties = 0, popSum = 0;
    const popTotal = states.reduce((a, s) => a + (s.pop || 1), 0);

    // Inputs as plain arrays (one row per state, columns in VARS order) for speed.
    const ie = VARS.indexOf('econ');
    const base = states.map(s => VARS.map(v => s.inputs[v] || 0));
    const nS = states.length, nV = VARS.length, b = new Float64Array(nV), share = new Float64Array(nS);
    const dIdx = districts.map(d => states.findIndex(s => s.abbr === d.parent));
    for (const variant of variants) {
      const X = variant ? base.map((row, i) => { const r = row.slice(); r[ie] = variant[states[i].abbr]; return r; }) : base;
      for (let it = 0; it < n; it++) {
        const b0 = COEFS.constant.b + COEFS.constant.se * normal(rand);
        for (let j = 0; j < nV; j++) b[j] = COEFS[VARS[j]].b + COEFS[VARS[j]].se * normal(rand);
        let ev = 0, pop = 0;
        for (let i = 0; i < nS; i++) {
          const row = X[i];
          let y = b0;
          for (let j = 0; j < nV; j++) y += b[j] * row[j];
          y += RMSE * normal(rand);
          share[i] = y;
          pop += y * (states[i].pop || 1);
          if (y > 50) { ev += states[i].ev; wins[states[i].abbr]++; }
        }
        for (let k = 0; k < districts.length; k++) {
          const d = districts[k];
          if (share[dIdx[k]] + d.offset > 50) { ev += d.ev; wins[d.abbr]++; }
        }
        evHist[ev]++;
        if (ev >= 270) demWins++; if (ev === 269) ties++;
        popSum += pop / popTotal;
      }
    }
    const total = n * variants.length;
    const point = Object.fromEntries(states.map(s => [s.abbr, predict(s.inputs)]));
    for (const d of districts) point[d.abbr] = point[d.parent] + d.offset;
    const byState = all.map(s => {
      const p = wins[s.abbr] / total;
      return { abbr: s.abbr, ev: s.ev, demShare: point[s.abbr], pDem: p, rating: rate(p) };
    });
    return {
      simulations: total,
      pDemWin: demWins / total,
      pTie: ties / total,
      demPopular: popSum / total,
      evHistogram: evHist.map(c => c / total),
      states: byState,
    };
  }

  const api = { COEFS, RMSE, predict, simulate, rate };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.SPASE = api;
})(typeof window !== 'undefined' ? window : globalThis);
