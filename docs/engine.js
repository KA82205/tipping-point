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
   */
  const MODEL = {"vars":["constant","lagDev","approval","econ","home","homeLag","vpHome","anderson","perot"],"variants":[{"delta":0.52,"b":[49.699343,0.834587,0.29912,1.457614,2.309662,-3.066821,1.77788,-0.421735,-0.584839],"L":[[0.15725912],[0.00223749,0.0155822],[-0.00097594,-0.0072755,0.01362067],[-0.05527036,0.04352319,-0.04977496,0.23349721],[-0.0062376,-0.04398357,-0.02884825,0.00346093,0.77619152],[-0.01325802,-0.07258401,-0.0221112,-0.01307115,-0.2471225,0.73526824],[-0.0050853,-0.0547104,-0.02461575,-0.00200198,0.03247427,-0.0003142,0.70389262],[-0.0228434,-0.0052832,0.01558334,0.015164,-0.00054799,0.0015361,-0.00117565,0.06248199],[-0.01326314,0.01159213,-0.01768601,-0.00605103,0.00018082,0.00012102,0.00036024,0.0,0.05215684]],"rmse":3.44766},{"delta":0.53,"b":[49.69918,0.834645,0.298929,1.490005,2.31039,-3.067986,1.777618,-0.419861,-0.585532],"L":[[0.15720882],[0.00223809,0.01557938],[-0.00097367,-0.00727764,0.01362179],[-0.05615906,0.04435358,-0.05101153,0.23779731],[-0.00626102,-0.04395379,-0.0288715,0.00353686,0.7760419],[-0.01323646,-0.07259353,-0.02206469,-0.01321554,-0.24707486,0.7351265],[-0.0050822,-0.05470376,-0.02460443,-0.00205178,0.03246801,-0.00031414,0.70375693],[-0.0228924,-0.00523234,0.0155043,0.01544458,-0.00054788,0.00153581,-0.00117542,0.06246995],[-0.01323241,0.01156878,-0.01765053,-0.00618578,0.00018078,0.00012099,0.00036017,-0.0,0.05214679]],"rmse":3.447},{"delta":0.54,"b":[49.699017,0.834702,0.298736,1.523624,2.311144,-3.069207,1.777357,-0.417949,-0.586257],"L":[[0.15715842],[0.00223875,0.0155765],[-0.00097138,-0.00727975,0.01362297],[-0.05708101,0.04521102,-0.0522984,0.24225539],[-0.00628514,-0.04392341,-0.02889565,0.00361512,0.77589111],[-0.01321316,-0.07260429,-0.02201569,-0.01336897,-0.24702685,0.73498366],[-0.0050792,-0.05469702,-0.02459287,-0.00210236,0.0324617,-0.00031408,0.70362019],[-0.02294204,-0.00518085,0.01542341,0.01572919,-0.00054777,0.00153551,-0.0011752,0.06245781],[-0.01320077,0.01154461,-0.01761368,-0.00632498,0.00018075,0.00012097,0.0003601,0.0,0.05213666]],"rmse":3.44633},{"delta":0.55,"b":[49.698851,0.834758,0.298542,1.558526,2.311926,-3.070486,1.777097,-0.416,-0.587017],"L":[[0.157108],[0.00223945,0.01557355],[-0.00096907,-0.00728183,0.0136242],[-0.0580381,0.04609627,-0.05363789,0.24687941],[-0.00630997,-0.04389247,-0.02892069,0.00369569,0.77573934],[-0.01318799,-0.07261637,-0.02196401,-0.01353212,-0.24697853,0.7348399],[-0.00507632,-0.05469016,-0.02458107,-0.00215371,0.03245535,-0.00031402,0.70348256],[-0.02299229,-0.00512882,0.01534071,0.01601759,-0.00054767,0.00153521,-0.00117497,0.06244559],[-0.01316818,0.01151958,-0.01757539,-0.00646886,0.00018071,0.00012094,0.00036003,0.0,0.05212646]],"rmse":3.44565},{"delta":0.56,"b":[49.698684,0.834811,0.298346,1.594767,2.312736,-3.071829,1.776841,-0.414016,-0.587814],"L":[[0.15705764],[0.00224021,0.01557054],[-0.00096674,-0.00728387,0.01362549],[-0.05903229,0.04701003,-0.05503234,0.25167765],[-0.00633551,-0.04386099,-0.02894663,0.00377855,0.77558683],[-0.01316083,-0.07262987,-0.02190949,-0.01370567,-0.24692998,0.73469543],[-0.00507359,-0.05468319,-0.02456904,-0.00220578,0.03244897,-0.00031396,0.70334426],[-0.02304311,-0.00507635,0.01525626,0.01630947,-0.00054756,0.0015349,-0.00117473,0.06243332],[-0.01313457,0.01149366,-0.0175356,-0.00661764,0.00018067,0.00012092,0.00035996,0.0,0.05211621]],"rmse":3.44498},{"delta":0.57,"b":[49.698516,0.834863,0.298149,1.632404,2.313575,-3.073237,1.776589,-0.412,-0.588649],"L":[[0.15700742],[0.00224104,0.01556745],[-0.00096442,-0.00728583,0.01362683],[-0.06006565,0.04795289,-0.05648413,0.25665879],[-0.00636177,-0.04382902,-0.02897347,0.00386366,0.77543385],[-0.01313154,-0.0726449,-0.02185194,-0.01389034,-0.24688127,0.73455051],[-0.00507103,-0.05467612,-0.02455678,-0.00225854,0.03244257,-0.00031389,0.70320553],[-0.02309445,-0.00502354,0.01517015,0.01660449,-0.00054745,0.0015346,-0.0011745,0.062421],[-0.01309988,0.01146681,-0.01749424,-0.00677159,0.00018064,0.0001209,0.00035989,0.0,0.05210593]],"rmse":3.4443},{"delta":0.58,"b":[49.698347,0.834912,0.297952,1.671495,2.314442,-3.074715,1.776342,-0.409953,-0.589526],"L":[[0.15695746],[0.00224194,0.01556428],[-0.00096209,-0.00728772,0.01362822],[-0.06114032,0.04892535,-0.05799562,0.26183191],[-0.00638874,-0.04379662,-0.02900118,0.00395092,0.77528074],[-0.01309998,-0.07266156,-0.02179116,-0.01408689,-0.24683252,0.73440547],[-0.00506867,-0.05466894,-0.02454429,-0.00231197,0.03243617,-0.00031383,0.70306667],[-0.02314626,-0.00497052,0.01508246,0.01690226,-0.00054734,0.0015343,-0.00117427,0.06240868],[-0.01306405,0.01143897,-0.01745124,-0.00693097,0.0001806,0.00012087,0.00035982,-0.0,0.05209564]],"rmse":3.44362}]};
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
   *            weight 1 (the default) is this model alone, with the same random draws.
   * model (optional): the fits to use (default MODEL); one per econVariant.
   *
   * As in the authors' code: coefficients drawn together from their covariance, and a model error with
   * SD = rmse whose correlation across states is drawn once per weighting, between 0.70 and 0.97.
   */
  function simulate({ states, districts = [], n = 10000, seed = 2028, econVariants = null, mix = null, model = MODEL }) {
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
    const w = mix ? mix.weight : 1, other = states.map(s => mix ? mix.point[s.abbr] : 0);
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
          y = w * y + (1 - w) * other[i] + shared + stateSd * normal(rand);
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
    });
    const total = n * variants.length;
    const mid = model.variants[Math.floor(model.variants.length / 2)];
    const point = Object.fromEntries(states.map((s, i) => [s.abbr, w * predict(s.inputs, mid, model) + (1 - w) * other[i]]));
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

  // Coefficient of each variable in the middle fit, for text on the site.
  const coef = v => MODEL.variants[Math.floor(MODEL.variants.length / 2)].b[MODEL.vars.indexOf(v)];
  const api = { COEFS, RMSE, MODEL, CORR, coef, predict, simulate, rate };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.SPASE = api;
})(typeof window !== 'undefined' ? window : globalThis);
