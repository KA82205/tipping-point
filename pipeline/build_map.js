// Builds docs/us-states.js (state outlines) from us-atlas. Run after:
//   npm install --no-save us-atlas@3.0.1 topojson-client@3.1.0
const path = require('path');
const fs = require('fs');
const topo = require('topojson-client');
const us = require('us-atlas/states-albers-10m.json');
const R = require('./results_2024.json');
const byName = {}; for (const [k, v] of Object.entries(R)) if (k.length === 2) byName[v.name] = k;
const r = n => Math.round(n * 10) / 10;
const ring = pts => 'M' + pts.map(p => r(p[0]) + ',' + r(p[1])).join('L') + 'Z';
const out = {};
for (const f of topo.feature(us, us.objects.states).features) {
  const ab = byName[f.properties.name];
  if (!ab) continue;
  const polys = f.geometry.type === 'Polygon' ? [f.geometry.coordinates] : f.geometry.coordinates;
  let d = '', cx = 0, cy = 0, A = 0;
  for (const poly of polys) {
    poly.forEach(rg => { d += ring(rg); });
    const o = poly[0]; let a = 0, x = 0, y = 0;
    for (let i = 0; i < o.length - 1; i++) { const c = o[i][0] * o[i + 1][1] - o[i + 1][0] * o[i][1]; a += c; x += (o[i][0] + o[i + 1][0]) * c; y += (o[i][1] + o[i + 1][1]) * c; }
    if (Math.abs(a) > Math.abs(A)) { A = a; cx = x / (3 * a); cy = y / (3 * a); }
  }
  out[ab] = { d, c: [r(cx), r(cy)] };
}
fs.writeFileSync(path.join(__dirname, '..', 'docs', 'us-states.js'),
  '// US state outlines from us-atlas 3.0.1 (ISC), Census cartographic boundaries, Albers USA.\nwindow.US_STATES = ' + JSON.stringify(out) + ';\n');
console.log('us-states.js:', Object.keys(out).length, 'shapes');
