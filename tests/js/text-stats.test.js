// Run with: npm run test:js
// Checks the browser counting rules against the same cases as the Python tests.
const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");
const TextStats = require("../../static/js/text-stats.js");
const cases = require(path.join(__dirname, "../../analyzer/tests/fixtures/text_stats_cases.json"));

for (const c of cases) {
  test(c.name, () => {
    const { name, text, ...expected } = c;
    assert.deepEqual(TextStats.compute(text), expected);
  });
}

test("reading speed matches the Python constant", () => {
  assert.equal(TextStats.READING_WPM, 238);
});
