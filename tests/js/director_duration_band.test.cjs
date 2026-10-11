const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const stateSource = fs.readFileSync(
    path.join(__dirname, '..', '..', 'static', 'js', 'state.js'),
    'utf8',
);
const helperMatch = stateSource.match(/^function directorDurationStatus\(duration\) \{[\s\S]*?^\}/m);

assert.ok(helperMatch, 'state.js must define directorDurationStatus');
assert.ok(
    stateSource.includes(
        "setSqpPill('sqp-duration', `Sure: ${totalSec.toFixed(1)}sn`, directorDurationStatus(totalSec));",
    ),
    'the studio duration pill must use the production contract',
);

const context = {};
vm.runInNewContext(
    `${helperMatch[0]}\nglobalThis.directorDurationStatus = directorDurationStatus;`,
    context,
);

test('duration pill follows hard, target, and style-default thresholds', () => {
    const cases = [
        [37.99, 'fail'],
        [38, 'warn'],
        [44.99, 'warn'],
        [45, 'warn'],
        [49.99, 'warn'],
        [50, 'ok'],
        [60, 'ok'],
        [60.25, 'ok'],
        [60.26, 'warn'],
        [65, 'warn'],
        [65.01, 'fail'],
    ];

    for (const [duration, expected] of cases) {
        assert.equal(context.directorDurationStatus(duration), expected, `${duration}s`);
    }
});
