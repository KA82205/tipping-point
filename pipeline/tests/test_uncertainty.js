// The engine's error structure must reproduce the paper's published 2024 odds
// (Trump about 73%, Harris about 27%) from the paper's own state forecasts.
const path = require('path');
global.window = {};
require(path.join(__dirname, '..', '..', 'docs', 'data.js'));
const { simulate, COEFS } = require(path.join(__dirname, '..', '..', 'docs', 'engine.js'));
const R = window.RESULTS_2024;
const by = Object.fromEntries(R.map(r => [r.abbr, r]));
// Inputs chosen so the central estimate equals the published forecast for each state.
const states = R.filter(r => r.abbr.length === 2).map(r => ({
  abbr: r.abbr, ev: r.ev, pop: r.dem + r.rep,
  inputs: { lagDev: (r.fc - COEFS.constant.b) / COEFS.lagDev.b },
}));
const districts = R.filter(r => r.abbr.length === 3).map(d => {
  const parent = d.abbr.slice(0, 2);
  return { abbr: d.abbr, parent, ev: d.ev, offset: d.fc - by[parent].fc };
});
const res = simulate({ states, districts, n: 40000, seed: 2024 });
const harris = res.pDemWin;
console.log(`Harris wins ${(100 * harris).toFixed(1)}% of simulations (paper: about 27%); ties ${(100 * res.pTie).toFixed(2)}%`);
if (harris < 0.23 || harris > 0.31) { console.error('FAIL: outside 23-31%'); process.exit(1); }
for (const a of ['PA', 'MI', 'WI', 'NC']) {
  const got = res.states.find(s => s.abbr === a).pDem;
  if (Math.abs(got - by[a].pDem) > 0.04) { console.error(`FAIL: ${a} ${got.toFixed(2)} vs paper ${by[a].pDem}`); process.exit(1); }
}
console.log('ok');
