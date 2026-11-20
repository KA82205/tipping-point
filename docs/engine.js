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
  // Table 1, 1980-2020 estimates and standard errors, as published. Shown on the Method page.
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
  const RMSE = 3.46;          // published standard error of the estimate

  /*
   * The model the Nowcast runs: the same regression refitted on 1980-2024 from the authors' replication data
   * (Harvard Dataverse, doi:10.7910/DVN/PBGFOF) with the 2024 results added, as the authors refit before each
   * forecast. One fit per economic weighting parameter (0.52 to 0.58), as in their simulation code
   * (Figures1andA2_2024.do). b: coefficients in `vars` order; L: lower Cholesky factor of their covariance,
   * so coefficients are drawn together, as CLARIFY does; rmse: the fit's root mean square error.
   * Refitting on 1980-2020 reproduces Table 1 exactly.
   * The approval baseline is re-chosen the way the authors choose it before each forecast: the whole number that
   * fits the earlier elections best. Their file uses 44 for 2024 (45 for 2000-2020); with 2024 added the rule
   * gives 43, and these fits use 43 (config.json: approval.constant).
   */
  const MODEL = {"vars":["constant","lagDev","approval","econ","home","homeLag","vpHome","anderson","perot"],"variants":[{"delta":0.52,"b":[49.698341,0.833211,0.301345,1.468239,2.30507,-3.053309,1.769118,-0.383173,-0.61982],"L":[[0.15712561],[0.00224116,0.01559708],[-0.00098472,-0.00735938,0.01366598],[-0.05524717,0.04336084,-0.04903981,0.23329542],[-0.00621644,-0.04373752,-0.02917651,0.00345794,0.77552069],[-0.01329289,-0.0727642,-0.02174691,-0.01305985,-0.24690892,0.73463277],[-0.00505287,-0.05436194,-0.02518352,-0.00200025,0.0324462,-0.00031393,0.70328427],[-0.02295202,-0.00625895,0.01727428,0.01515089,-0.00054751,0.00153477,-0.00117463,0.06242799],[-0.01313407,0.01248452,-0.01919591,-0.0060458,0.00018066,0.00012091,0.00035993,-0.0,0.05211177]],"rmse":3.44468},{"delta":0.53,"b":[49.698743,0.833271,0.301139,1.497346,2.305783,-3.054297,1.768921,-0.381622,-0.620445],"L":[[0.15709623],[0.00224093,0.0155975],[-0.00098011,-0.00736563,0.01367084],[-0.05614239,0.04428836,-0.05042567,0.23762596],[-0.0062415,-0.0437101,-0.02920976,0.00353431,0.77548266],[-0.01327137,-0.07278924,-0.02169846,-0.01320601,-0.24689681,0.73459675],[-0.0050502,-0.05436242,-0.025178,-0.0020503,0.03244461,-0.00031391,0.70324979],[-0.02300021,-0.00620778,0.01719127,0.01543345,-0.00054749,0.0015347,-0.00117458,0.06242493],[-0.01310924,0.01246557,-0.01916233,-0.00618133,0.00018065,0.0001209,0.00035991,0.0,0.05210921]],"rmse":3.44451},{"delta":0.54,"b":[49.699162,0.833329,0.30093,1.527429,2.306519,-3.055329,1.768728,-0.380053,-0.621095],"L":[[0.15706765],[0.00224071,0.01559799],[-0.00097541,-0.00737205,0.01367594],[-0.05707155,0.04525089,-0.05187426,0.2421171],[-0.00626732,-0.04368207,-0.02924448,0.00361305,0.77544814],[-0.01324813,-0.07281625,-0.02164729,-0.01336134,-0.24688582,0.73456405],[-0.00504765,-0.0543631,-0.02517246,-0.00210116,0.03244317,-0.0003139,0.70321848],[-0.02304907,-0.00615573,0.01710588,0.01572021,-0.00054746,0.00153463,-0.00117452,0.06242215],[-0.01308369,0.01244588,-0.01912731,-0.00632137,0.00018064,0.0001209,0.00035989,-0.0,0.05210689]],"rmse":3.44436},{"delta":0.55,"b":[49.699598,0.833386,0.30072,1.558521,2.307279,-3.05641,1.76854,-0.378467,-0.621774],"L":[[0.15704],[0.00224052,0.01559856],[-0.0009706,-0.00737863,0.01368129],[-0.0580366,0.04624988,-0.05338901,0.24677701],[-0.00629392,-0.04365347,-0.02928072,0.00369416,0.77541755],[-0.01322303,-0.07284538,-0.02159319,-0.01352651,-0.24687608,0.73453507],[-0.00504523,-0.05436401,-0.02516692,-0.00215281,0.03244189,-0.00031389,0.70319074],[-0.02309858,-0.00610286,0.0170181,0.01601095,-0.00054744,0.00153457,-0.00117448,0.06241969],[-0.01305739,0.01242542,-0.01909077,-0.00646617,0.00018064,0.00012089,0.00035988,0.0,0.05210483]],"rmse":3.44423},{"delta":0.56,"b":[49.700052,0.833442,0.300508,1.590657,2.308062,-3.057541,1.768358,-0.376868,-0.622482],"L":[[0.15701339],[0.00224036,0.01559921],[-0.0009657,-0.00738537,0.0136869],[-0.05903956,0.04728678,-0.05497347,0.25161422],[-0.00632131,-0.04362432,-0.02931853,0.0037776,0.77539136],[-0.01319593,-0.07287679,-0.02153594,-0.01370221,-0.24686774,0.73451026],[-0.00504298,-0.05436516,-0.02516138,-0.00220522,0.03244079,-0.00031388,0.70316699],[-0.0231487,-0.00604926,0.01692794,0.01630536,-0.00054742,0.00153452,-0.00117444,0.06241758],[-0.0130303,0.01240412,-0.01905262,-0.00661597,0.00018063,0.00012089,0.00035987,0.0,0.05210307]],"rmse":3.44411},{"delta":0.57,"b":[49.700526,0.833495,0.300294,1.623867,2.308868,-3.058724,1.768184,-0.375259,-0.623222],"L":[[0.15698797],[0.00224024,0.01559994],[-0.0009607,-0.00739228,0.01369279],[-0.06008258,0.04836302,-0.05663133,0.25663769],[-0.0063495,-0.04359465,-0.02935795,0.00386334,0.77537011],[-0.01316669,-0.07291065,-0.02147531,-0.01388919,-0.24686098,0.73449013],[-0.00504092,-0.05436656,-0.02515586,-0.00225836,0.0324399,-0.00031387,0.70314772],[-0.02319937,-0.00599499,0.01683545,0.01660313,-0.00054741,0.00153448,-0.00117441,0.06241587],[-0.01300235,0.01238196,-0.01901277,-0.00677104,0.00018062,0.00012089,0.00035986,0.0,0.05210165]],"rmse":3.44401},{"delta":0.58,"b":[49.701021,0.833547,0.30008,1.658181,2.309698,-3.059962,1.768018,-0.373644,-0.623995],"L":[[0.15696389],[0.00224016,0.01560077],[-0.0009556,-0.00739933,0.01369896],[-0.06116791,0.04947999,-0.0583664,0.26185679],[-0.0063785,-0.04356453,-0.02939901,0.0039513,0.7753544],[-0.01313519,-0.07294711,-0.02141107,-0.01408822,-0.24685597,0.73447525],[-0.00503907,-0.05436825,-0.0251504,-0.00231219,0.03243925,-0.00031386,0.70313347],[-0.02325057,-0.00594017,0.01674066,0.01690387,-0.0005474,0.00153444,-0.00117438,0.06241461],[-0.0129735,0.01235887,-0.01897114,-0.00693163,0.00018062,0.00012088,0.00035985,0.0,0.05210059]],"rmse":3.44394}]};
  // Model error, as in the authors' code: each state's error has SD = rmse, and the errors of different states
  // are correlated, with the correlation drawn once per weighting parameter from 0.70 to 0.97.
  const CORR = [0.70, 0.97];
  // Rating thresholds from Figure 2 (share of simulations won).
  function rate(pDem) {
    const p = Math.max(pDem, 1 - pDem), party = pDem >= 0.5 ? 'D' : 'R';
    if (p > 0.98) return 'S' + party;
    if (p > 0.75) return 'L' + party;
    if (p > 0.55) return 'T' + party;
    return 'TOSS';
  }

  // Point forecast with one variant's coefficients (default: the middle weighting, 0.55).
  function predict(inputs, variant = MODEL.variants[Math.floor(MODEL.variants.length / 2)], model = MODEL) {
    return model.vars.reduce((y, v, j) => y + variant.b[j] * (v === 'constant' ? 1 : (inputs[v] || 0)), 0);
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
   * mix (optional, not in the paper): { weight, point: {abbr: share} }. Each state's share becomes
   *            weight x this model + (1 - weight) x another model's forecast, before the model error
   *            is added. Used to average in the head-to-head polls model (docs/combine.js).
   *            weight 1 (the default) is this model alone, with the same random draws. point may be left
   *            out when weight is 1. shift (optional) is added to every state, in points: used to move the
   *            whole map to a national level set partly by a model that gives no state forecasts.
   * model (optional): the fits to use (default MODEL); one per econVariant.
   * keep (optional): keep about this many of the simulated elections, evenly spaced, so the site can replay
   *            one or count only those where chosen states go a chosen way. Returned as draws:
   *            { n, units, shares, ev }; shares holds each unit's Democratic share x 100, draw by draw.
   *            Keeping draws uses no random numbers, so every other result is unchanged.
   *
   * As in the authors' code: coefficients drawn together from their covariance, and a model error with
   * SD = rmse whose correlation across states is drawn once per weighting, between 0.70 and 0.97.
   */
  function simulate({ states, districts = [], n = 10000, seed = 2028, econVariants = null, mix = null, model = MODEL, keep = 0 }) {
    const rand = mulberry32(seed);
    const variants = econVariants && econVariants.length ? econVariants : [null];
    if (variants.length > 1 && variants.length !== model.variants.length) throw new Error('one economic variant per model fit is needed');
    const fitFor = k => model.variants[variants.length > 1 ? k : Math.floor(model.variants.length / 2)];
    const vars = model.vars.filter(v => v !== 'constant'), ic = model.vars.indexOf('constant');
    const all = states.concat(districts);
    const wins = Object.fromEntries(all.map(s => [s.abbr, 0]));
    const evHist = new Array(539).fill(0);
    let demWins = 0, ties = 0, popSum = 0;
    const popTotal = states.reduce((a, s) => a + (s.pop || 1), 0);

    // Inputs as plain arrays (one row per state, columns in VARS order) for speed.
    const ie = vars.indexOf('econ');
    const base = states.map(s => vars.map(v => s.inputs[v] || 0));
    const nS = states.length, nV = vars.length, nB = model.vars.length;
    const z = new Float64Array(nB), bAll = new Float64Array(nB), b = new Float64Array(nV), share = new Float64Array(nS);
    const col = vars.map(v => model.vars.indexOf(v));
    const dIdx = districts.map(d => states.findIndex(s => s.abbr === d.parent));
    const w = mix ? mix.weight : 1, other = states.map(s => mix && mix.point ? mix.point[s.abbr] : 0), shift = mix && mix.shift || 0;
    const every = keep > 0 ? Math.max(1, Math.floor(n * variants.length / keep)) : 0, nU = all.length;
    const kept = every ? { n: 0, units: all.map(s => s.abbr), shares: new Int16Array(variants.length * Math.ceil(n / every) * nU), ev: new Uint16Array(variants.length * Math.ceil(n / every)) } : null;
    // A share is stored in hundredths of a point; a rounded value never lands on the other side of 50.
    const q = y => { const v = Math.round(y * 100); return y > 50 ? Math.max(v, 5001) : Math.min(v, 5000); };
    variants.forEach((variant, k) => {
      const X = variant ? base.map((row, i) => { const r = row.slice(); r[ie] = variant[states[i].abbr]; return r; }) : base;
      const fit = fitFor(k), L = fit.L;
      // Correlation of state errors for this weighting, drawn once, as in the authors' code.
      const u = CORR[0] + (CORR[1] - CORR[0]) * rand();
      const sharedSd = Math.sqrt(u) * fit.rmse, stateSd = Math.sqrt(1 - u) * fit.rmse;
      for (let it = 0; it < n; it++) {
        // Coefficients drawn together from their covariance: b = mean + L z.
        for (let j = 0; j < nB; j++) z[j] = normal(rand);
        for (let j = 0; j < nB; j++) { let s = fit.b[j]; const Lj = L[j]; for (let m = 0; m <= j; m++) s += Lj[m] * z[m]; bAll[j] = s; }
        const b0 = bAll[ic];
        for (let j = 0; j < nV; j++) b[j] = bAll[col[j]];
        const shared = sharedSd * normal(rand);
        let ev = 0, pop = 0;
        for (let i = 0; i < nS; i++) {
          const row = X[i];
          let y = b0;
          for (let j = 0; j < nV; j++) y += b[j] * row[j];
          y = w * y + (1 - w) * other[i] + shift + shared + stateSd * normal(rand);
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
        if (every && it % every === 0) {
          const o = kept.n * nU;
          for (let i = 0; i < nS; i++) kept.shares[o + i] = q(share[i]);
          for (let k = 0; k < districts.length; k++) kept.shares[o + nS + k] = q(share[dIdx[k]] + districts[k].offset);
          kept.ev[kept.n++] = ev;
        }
        popSum += pop / popTotal;
      }
    });
    const total = n * variants.length;
    const mid = model.variants[Math.floor(model.variants.length / 2)];
    const point = Object.fromEntries(states.map((s, i) => [s.abbr, w * predict(s.inputs, mid, model) + (1 - w) * other[i] + shift]));
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
      draws: kept,
    };
  }

  // Coefficient of each variable in the middle fit, for text on the site.
  const coef = v => MODEL.variants[Math.floor(MODEL.variants.length / 2)].b[MODEL.vars.indexOf(v)];
  const api = { COEFS, RMSE, MODEL, CORR, coef, predict, simulate, rate };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.SPASE = api;
})(typeof window !== 'undefined' ? window : globalThis);
