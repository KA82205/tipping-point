// Runs both Nowcast models (docs/combine.js) on the payload built by update.py.
// Usage: node pipeline/run_forecast.js inputs.json > result.json
const fs = require('fs');
const path = require('path');
const TP = require(path.join(__dirname, '..', 'docs', 'combine.js'));

const inp = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const out = TP.run(inp.N, inp.picks || {}, { n: inp.n, seed: inp.seed, forceVpShift: inp.force_vp_shift, asPublished: !!inp.as_published });
process.stdout.write(JSON.stringify(out));
