const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const source = fs.readFileSync(
    path.join(__dirname, '..', '..', 'static', 'js', 'render-monitor.js'),
    'utf8',
);
const payloadMatch = source.match(/^    const payload = \{([\s\S]*?)^    \};/m);

assert.ok(payloadMatch, 'render-monitor.js must define a render request payload');

test('render request defines gameplay_category once from the current control value', () => {
    const categoryProperties = payloadMatch[1].match(/^\s*gameplay_category\s*:/gm) || [];

    assert.equal(categoryProperties.length, 1);
    assert.match(
        payloadMatch[1],
        /gameplay_category:\s*document\.getElementById\('select-gameplay-category'\)\?\.value \|\| 'auto'/,
    );
});

test('render language is taken from the language selector and voice is synchronized before sending', () => {
    assert.match(
        source,
        /const renderLanguage = selectLanguage\?\.value === 'en' \? 'en' : 'tr';/,
    );
    assert.match(source, /ensureTtsVoiceForLanguage\(renderLanguage\);/);
    assert.match(payloadMatch[1], /language:\s*renderLanguage/);
});
