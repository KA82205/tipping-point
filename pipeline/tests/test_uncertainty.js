// The engine's error structure must reproduce the paper's published 2024 odds
// (Trump about 73%, Harris about 27%) from the paper's own state forecasts.
const path = require('path');
global.window = {};
require(path.join(__dirname, '..', '..', 'docs', 'data.js'));
const { simulate } = require(path.join(__dirname, '..', '..', 'docs', 'engine.js'));
const R = window.RESULTS_2024;
const by = Object.fromEntries(R.map(r => [r.abbr, r]));
// A stand-in model whose forecast for each state is the published one, with the paper's model error
// (SD 3.463, the 1980-2020 fit) and no coefficient uncertainty. The authors' own simulation, rerun from their
// replication files, gives Harris 27.1%; coefficient uncertainty adds little.
const zero = Array.from({ length: 9 }, (_, i) => Array.from({ length: i + 1 }, () => 0));
const model = { vars: ['constant', 'lagDev', 'approval', 'econ', 'home', 'homeLag', 'vpHome', 'anderson', 'perot'],
  variants: [{ b: [0, 1, 0, 0, 0, 0, 0, 0, 0], L: zero, rmse: 3.463 }] };
const states = R.filter(r => r.abbr.length === 2).map(r => ({ abbr: r.abbr, ev: r.ev, pop: r.dem + r.rep, inputs: { lagDev: r.fc } }));
const districts = R.filter(r => r.abbr.length === 3).map(d => {
  const parent = d.abbr.slice(0, 2);
  return { abbr: d.abbr, parent, ev: d.ev, offset: d.fc - by[parent].fc };
});
const res = simulate({ states, districts, n: 40000, seed: 2024, model });
const harris = res.pDemWin;
console.log(`Harris wins ${(100 * harris).toFixed(1)}% of simulations (paper: about 27%); ties ${(100 * res.pTie).toFixed(2)}%`);
if (harris < 0.23 || harris > 0.31) { console.error('FAIL: outside 23-31%'); process.exit(1); }
for (const a of ['PA', 'MI', 'WI', 'NC']) {
  const got = res.states.find(s => s.abbr === a).pDem;
  if (Math.abs(got - by[a].pDem) > 0.04) { console.error(`FAIL: ${a} ${got.toFixed(2)} vs paper ${by[a].pDem}`); process.exit(1); }
}

// The Archive (docs/archive.js). Its back-tests of 2008, 2012 and 2016 must agree with the Method page's track
// record: states called of 50 and the Democrat's chance in 100 for the Nowcast's method. Its 2020 page must show
// the forecasts as published: Enns and Lagodny missed only Georgia with 290 electoral votes, DeSart missed Florida
// and North Carolina with 350.
require(path.join(__dirname, '..', '..', 'docs', 'archive.js'));
const TRACK = { 2008: [47, 91], 2012: [49, 72], 2016: [46, 61] };
const fail = m => { console.error('FAIL: archive ' + m); process.exit(1); };
for (const y of [2008, 2012, 2016, 2020]) {
  const Y = window.ARCHIVE.years[y], all = Object.entries(Y.states), st = all.filter(([a]) => a !== 'DC');
  if (all.length !== 51 || all.reduce((t, [, s]) => t + s.ev, 0) !== 538) fail(`${y}: ${all.length} contests`);
  if (!st.every(([, s]) => Math.abs(s.bt.fc - (s.enns.fc + s.desart.fc) / 2) < 0.011)) fail(`${y}: the Nowcast's method is not the average of the two models`);
  if (TRACK[y]) {
    const got = st.filter(([, s]) => (s.bt.fc > 50) === (s.share > 50)).length, p = Math.round(100 * Y.nat.bt.pDemWin);
    if (got !== TRACK[y][0] || p !== TRACK[y][1]) fail(`${y}: ${got} of 50 called and a chance of ${p}, against ${TRACK[y]} in the track record`);
  }
}
{
  const Y = window.ARCHIVE.years[2020], st = Object.entries(Y.states), miss = k => st.filter(([a, s]) => a !== 'DC' && (s[k].fc > 50) !== (s.share > 50)).map(([a]) => a).join(' ');
  const ev = k => st.filter(([, s]) => s[k].fc > 50).reduce((t, [, s]) => t + s.ev, 0);
  if (miss('enns') !== 'GA' || ev('enns') !== 290 || miss('desart') !== 'FL NC' || ev('desart') !== 350) fail(`2020 as published: missed ${miss('enns')} (${ev('enns')}) and ${miss('desart')} (${ev('desart')})`);
}
console.log('archive agrees with the track record and the published 2020 forecasts');
console.log('ok');
