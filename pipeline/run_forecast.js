// Runs the model engine (docs/engine.js) on pipeline-built inputs.
// Usage: node pipeline/run_forecast.js inputs.json > result.json
const fs = require('fs');
const path = require('path');
const E = require(path.join(__dirname, '..', 'docs', 'engine.js'));

const inp = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const res = E.simulate({
  states: inp.states,
  districts: inp.districts,
  n: inp.n_per_delta,
  seed: inp.seed,
  econVariants: inp.econ_variants,
});
process.stdout.write(JSON.stringify(res));
