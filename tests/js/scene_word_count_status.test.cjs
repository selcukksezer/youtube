const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const timelineSource = fs.readFileSync(
    path.join(__dirname, '..', '..', 'static', 'js', 'timeline.js'),
    'utf8',
);
const wordCountMatch = timelineSource.match(/^function wordCount\(text\) \{[\s\S]*?^\}/m);
const helperMatch = timelineSource.match(/^function sceneWordCountClass\(wordCount\) \{[\s\S]*?^\}/m);

assert.ok(wordCountMatch, 'timeline.js must define wordCount');
assert.ok(helperMatch, 'timeline.js must define sceneWordCountClass');
assert.match(
    timelineSource,
    /const wcClass = sceneWordCountClass\(wc\);/,
    'scene cards must use the production scene-word contract',
);

const context = {};
vm.runInNewContext(
    `${wordCountMatch[0]}\n${helperMatch[0]}\n` +
        'globalThis.wordCount = wordCount;\n' +
        'globalThis.sceneWordCountClass = sceneWordCountClass;',
    context,
);

test('scene word-count chip distinguishes hard failures and advisories', () => {
    const cases = [
        [6, 'count-danger'],
        [7, 'count-warn'],
        [11, 'count-warn'],
        [12, 'count-ok'],
        [20, 'count-ok'],
        [21, 'count-warn'],
    ];

    for (const [wordCount, expected] of cases) {
        assert.equal(context.sceneWordCountClass(wordCount), expected, `${wordCount} words`);
    }
});

test('UI word count matches production tokens when narration includes emoji', () => {
    const narration = '**URGENT** Careful observers notice subtle shifts today. 🚨';
    const count = context.wordCount(narration);

    assert.equal(count, 6);
    assert.equal(context.sceneWordCountClass(count), 'count-danger');
});
