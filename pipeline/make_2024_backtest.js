// The 2024 back-test of the Nowcast's method, for the 2024 scorecard. Writes docs/backtest2024.js.
//
// Each state is the average of two forecasts published before the election: Enns, Colner, Kumar and
// Lagodny (July 2024; docs/data.js) and DeSart (November 2023; pipeline/backtest_2024.json), half each, as
// in docs/combine.js. Districts keep their published offset from their state. The odds come from the approval and
// economy model's error (SD 3.463 points, the 1980-2020 fit), as in pipeline/tests/test_uncertainty.js.
// Nobody published this combination in 2024: it is what today's method gives on what was known then.
const fs = require('fs'), path = require('path');
global.window = {};
require(path.join(__dirname, '..', 'docs', 'data.js'));
const { simulate } = require(path.join(__dirname, '..', 'docs', 'engine.js'));
const B = JSON.parse(fs.readFileSync(path.join(__dirname, 'backtest_2024.json'), 'utf8'));
const R = window.RESULTS_2024, by = Object.fromEntries(R.map(r => [r.abbr, r]));
const S = R.filter(r => r.abbr.length === 2), D = R.filter(r => r.abbr.length === 3);
const w = Object.fromEntries(S.map(r => [r.abbr, r.dem + r.rep])), wTot = S.reduce((a, r) => a + w[r.abbr], 0);
const national = f => S.reduce((a, r) => a + f(r) * w[r.abbr], 0) / wTot;
const natE = national(r => r.fc), natD = national(r => B.desart[r.abbr]);
const point = Object.fromEntries(S.map(r => [r.abbr, (r.fc + B.desart[r.abbr]) / 2]));
const zero = Array.from({ length: 9 }, (_, i) => Array.from({ length: i + 1 }, () => 0));
const RMSE = 3.463, HALF = 1.645 * RMSE;
const model = { vars: ['constant', 'lagDev', 'approval', 'econ', 'home', 'homeLag', 'vpHome', 'anderson', 'perot'],
  variants: [{ b: [0, 1, 0, 0, 0, 0, 0, 0, 0], L: zero, rmse: RMSE }] };
const states = S.map(r => ({ abbr: r.abbr, ev: r.ev, pop: w[r.abbr], inputs: { lagDev: point[r.abbr] } }));
const districts = D.map(d => { const parent = d.abbr.slice(0, 2); return { abbr: d.abbr, parent, ev: d.ev, offset: d.fc - by[parent].fc }; });
const res = simulate({ states, districts, n: 40000, seed: 2024, model });
const r1 = x => Math.round(x * 10) / 10, r2 = x => Math.round(x * 100) / 100;
const out = {
  national: { fc: r2(national(r => point[r.abbr])), pDemWin: Math.round(res.pDemWin * 1000) / 1000, enns: r2(natE), desart: r2(natD),
    demEV: res.states.filter(s => s.demShare > 50).reduce((a, s) => a + s.ev, 0) },
  states: Object.fromEntries(res.states.map(s => [s.abbr, { fc: r2(s.demShare), lo: r1(s.demShare - HALF), hi: r1(s.demShare + HALF),
    pDem: Math.round(s.pDem * 1000) / 1000, rating: s.rating, desart: B.desart[s.abbr] != null ? r2(B.desart[s.abbr]) : null }])),
};
// DeSart's own 2024 forecast, scored as he published it: his state forecasts, his national vote (states added
// by his turnout weights), and his odds from his own simulation script ("DeSart PS 2024 Monte Carlo NPV and
// ECV.sps"): every state drawn independently around its forecast with a 3.08-point error, 100,000 runs. He
// forecasts states only, so the five districts here are his state forecast moved by the gap between district
// and state in the approval and economy forecast; that part is ours, and is marked on the site.
{
  let seed = 42616 >>> 0;
  const rand = () => { seed = (seed + 0x6D2B79F5) >>> 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
  const normal = () => { let u = 0; while (!u) u = rand(); return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * rand()); };
  const SE = B.desart_se, N = 100000, units = S.concat(D);
  const dsFc = r => r.abbr.length === 2 ? B.desart[r.abbr] : B.desart[r.abbr.slice(0, 2)] + (r.fc - by[r.abbr.slice(0, 2)].fc);
  const wins = Object.fromEntries(units.map(r => [r.abbr, 0])); let demWins = 0, ties = 0;
  const dcEV = 3, dcFc = B.desart.DC;
  for (let it = 0; it < N; it++) {
    const draw = {}; let ev = 0;
    for (const r of S) { draw[r.abbr] = B.desart[r.abbr] + SE * normal(); if (draw[r.abbr] > 50) { ev += r.ev; wins[r.abbr]++; } }
    for (const d of D) { if (draw[d.abbr.slice(0, 2)] + (d.fc - by[d.abbr.slice(0, 2)].fc) > 50) { ev += d.ev; wins[d.abbr]++; } }
    if (!R.some(r => r.abbr === 'DC') && dcFc + SE * normal() > 50) ev += dcEV;
    if (ev >= 270) demWins++; else if (ev === 269) ties++;
  }
  const tw = Object.entries(B.turnout).reduce((a, [k, v]) => a + v, 0);
  const natDs = Object.entries(B.turnout).reduce((a, [k, v]) => a + v * B.desart[k], 0) / tw;
  const pDem = Object.fromEntries(units.map(r => [r.abbr, wins[r.abbr] / N]));
  const rate = p => { const SP = require(path.join(__dirname, '..', 'docs', 'engine.js')); return SP.rate(p); };
  out.desartPub = {
    national: { fc: r2(natDs), pDemWin: Math.round(demWins / N * 1000) / 1000, pTie: Math.round(ties / N * 1000) / 1000, demEV: units.filter(r => dsFc(r) > 50).reduce((a, r) => a + r.ev, 0) },
    states: Object.fromEntries(units.map(r => { const fc = dsFc(r); return [r.abbr, { fc: r2(fc), lo: r1(fc - 1.645 * SE), hi: r1(fc + 1.645 * SE), pDem: Math.round(pDem[r.abbr] * 1000) / 1000, rating: rate(pDem[r.abbr]), district: r.abbr.length === 3 }]; })),
  };
  console.log('DeSart as published:', JSON.stringify(out.desartPub.national), 'missed', units.filter(r => (dsFc(r) > 50) !== (by[r.abbr].share > 50)).map(r => r.abbr));
}
fs.writeFileSync(path.join(__dirname, '..', 'docs', 'backtest2024.js'),
  '// Generated by pipeline/make_2024_backtest.js: the Nowcast\'s method applied to 2024 (see that file).\nwindow.BACKTEST_2024 = ' + JSON.stringify(out) + ';\n');
const miss = res.states.filter(s => (s.demShare > 50) !== (by[s.abbr].share > 50)).map(s => s.abbr);
console.log(JSON.stringify(out.national), 'missed', miss, 'toss-ups', res.states.filter(s => s.rating === 'TOSS').map(s => s.abbr).join(' '));
