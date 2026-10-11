const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const root = path.join(__dirname, '..', '..');
const stateSource = fs.readFileSync(path.join(root, 'static', 'js', 'state.js'), 'utf8');
const helperMatch = stateSource.match(/^function directorWordCountStatus\(wordCount\) \{[\s\S]*?^\}/m);

assert.ok(helperMatch, 'state.js must define directorWordCountStatus');
assert.match(
    stateSource,
    /setSqpPill\('sqp-words', `Kelime: \$\{totalWords\}`, directorWordCountStatus\(totalWords\)\)/,
    'the studio word-count pill must use the production contract',
);

const context = {};
vm.runInNewContext(
    `${helperMatch[0]}\nglobalThis.directorWordCountStatus = directorWordCountStatus;`,
    context,
);

test('word-count pill follows hard and target production limits', () => {
    const cases = [
        [84, 'fail'],
        [85, 'ok'],
        [110, 'ok'],
        [111, 'warn'],
        [195, 'warn'],
        [196, 'fail'],
    ];

    for (const [wordCount, expected] of cases) {
        assert.equal(context.directorWordCountStatus(wordCount), expected, `${wordCount} words`);
    }
});
