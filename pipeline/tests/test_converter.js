// The converter page (docs/civiqs.html): its reading functions are run here exactly as they are in the page, on a
// made-up tracker page in both forms a browser saves, and what they write is checked against the Python reader, figure
// for figure. Also checked: nothing but the figures gets into the data file, and the page cannot make a request.
//
//   node pipeline/tests/test_converter.js
const fs = require('fs'), path = require('path'), vm = require('vm'), os = require('os'), { execFileSync } = require('child_process');
const assert = require('assert');
const root = path.join(__dirname, '..', '..'), page = fs.readFileSync(path.join(root, 'docs', 'civiqs.html'), 'utf8');

const a = page.indexOf('/* ---- the reading'), b = page.indexOf('/* ---- end of the reading ---- */');
assert(a > 0 && b > a, 'the reading functions are marked in the page');
const box = {}; vm.createContext(box);
vm.runInContext(page.slice(a, b) + '\nthis.extract = extract; this.toCsv = toCsv; this.STATES = STATES; this.SOURCE = SOURCE;', box);

// the page may not send anything: its policy forbids every request, and its script never asks for one
const csp = /<meta http-equiv="Content-Security-Policy" content="([^"]+)"/.exec(page)[1];
assert(/default-src 'none'/.test(csp) && /connect-src 'none'/.test(csp) && /form-action 'none'/.test(csp), 'the page forbids every request');
assert(!/fetch\(|XMLHttpRequest|sendBeacon|WebSocket|EventSource|import\(|<script[^>]+src=|<link|<img|<iframe|<form/i.test(page), 'the page asks for nothing');

// a made-up tracker page, shaped as the real one: the data block among settings and keys that must not come through
const fx = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures', 'civiqs_state_approval.json'), 'utf8')).states;
const name = Object.fromEntries(Object.entries(box.STATES).map(([n, c]) => [c, n]));
const map = {}; for (const [c, v] of Object.entries(fx)) map[name[c]] = { demographic: name[c], Approve: v.approve / 100, Disapprove: v.disapprove / 100, net: (v.approve - v.disapprove) / 100 };
const ENV = { SOME_SERVICE_API_KEY: 'made-up-key-that-must-not-come-through', TRACKING_TOKEN: 'made-up-token' };
const make = (m, extra) => {
  const ctx = { basename: '/', state: { loaderData: { root: { ENV }, 'routes/_app.results_.$question': Object.assign({ question_body: 'Do you approve or disapprove of the way Donald Trump is handling his job as president?', end_date: '2026-11-10', crosstabs: { map: m } }, extra || {}) } } };
  return '<!DOCTYPE html><html><head><link rel="canonical" href="https://civiqs.com/results/approve_president_trump_2025"><script>window.ENV = ' + JSON.stringify(ENV) + '</script></head><body><p>a "quoted" } brace { in the page</p><script>window.__remixContext = ' + JSON.stringify(ctx) + ';</script><script>var after = {"x": [1, 2]};</script></body></html>';
};
const source = make(map);
const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
// a "view source" tab saved as a page: every line in a table cell, the markup escaped, tags wrapped in spans
const viewSource = '<!-- saved from url=(0058)https://civiqs.com/results/approve_president_trump_2025 -->\n<html><body><table><tbody>' + source.split('<script>').map((l, i) => '<tr><td class="line-number" value="' + (i + 1) + '"></td><td class="line-content">' + (i ? '<span class="html-tag">&lt;script&gt;</span>' : '') + esc(l) + '</td></tr>').join('') + '</tbody></table></body></html>';
// the worst case: the saved copy's own markup falls inside the data block
const broken = viewSource.replace('"crosstabs"', '"cross</td></tr><tr><td class="line-content">tabs"');

const want = box.extract(source), csv = box.toCsv(want);
assert.strictEqual(want.as_of, '2026-11-10'); assert.strictEqual(Object.keys(want.states).length, 50);
assert.strictEqual(want.states.GA, '33.11');
for (const [what, text] of [['a saved view-source tab', viewSource], ['markup inside the data block', broken]])
  assert.deepStrictEqual(JSON.parse(JSON.stringify(box.extract(text))), JSON.parse(JSON.stringify(want)), what);

// the data file: a heading, fifty lines, and only codes, figures, the date and the tracker's address
const lines = csv.trim().split('\n');
assert.strictEqual(lines[0], 'state,approve,as_of,source'); assert.strictEqual(lines.length, 51);
for (const l of lines.slice(1)) assert(/^[A-Z]{2},\d{2}\.\d{2},2026-11-10,https:\/\/civiqs\.com\/results\/approve_president_trump_2025$/.test(l), l);
assert(!/key|token|ENV|script|made-up/i.test(csv), 'nothing else from the page is in the file');
assert(csv.length < 4000);

// the same figures as the Python reader takes from the same page, and the Python inbox reader accepts the file
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'conv-')); fs.writeFileSync(path.join(tmp, 'page.html'), source); fs.writeFileSync(path.join(tmp, 'civiqs.csv'), csv);
const py = JSON.parse(execFileSync('python3', ['-c', 'import sys, json; sys.path.insert(0, sys.argv[1]); import civiqs; p = civiqs.parse(open(sys.argv[2], encoding="utf-8").read()); c = civiqs.read_clean(sys.argv[3]); print(json.dumps({"page": {k: v["approve"] for k, v in p["states"].items()}, "file": {k: v["approve"] for k, v in c["states"].items()}, "as_of": [p["as_of"], c["as_of"]]}))', path.join(root, 'pipeline'), path.join(tmp, 'page.html'), path.join(tmp, 'civiqs.csv')], { encoding: 'utf8' }));
assert.deepStrictEqual(py.as_of, ['2026-11-10', '2026-11-10']);
for (const c of Object.keys(want.states)) { assert.strictEqual(py.page[c], py.file[c], c); assert.strictEqual(py.page[c], +want.states[c], c); assert.strictEqual(py.page[c], fx[c].approve, c); }

// what it refuses, and that it says why in plain words
const refuses = (text, re, what) => assert.throws(() => box.extract(text), e => re.test(e.message), what);
refuses('<html>404</html>', /not found in this file/, 'not the page');
refuses('<div><span>Approve</span><span class="float-right">41%</span></div>', /whole percentages/, 'the page as shown');
refuses(make(Object.fromEntries(Object.entries(map).filter(([n]) => n !== 'Ohio'))), /No figures for Ohio/, 'a state missing');
refuses(make(Object.assign({}, map, { Ohio: { Approve: 0.99, Disapprove: 0.005 } })), /Ohio are not believable/, 'a figure out of range');
refuses(make(map, { question_body: 'Do you have a favorable or unfavorable opinion of Donald Trump?' }), /not the tracker/, 'another question');
refuses(make(map, { end_date: 'sometime' }), /day the figures run through/, 'no date');
refuses(source.replace('window.__remixContext = {', 'window.__remixContext = {"unclosed": "'), /not found|shape/, 'a block that does not close');
console.log('ok (the converter: both saved forms, the data file and nothing else, the same figures as the Python reader, refusals)');
