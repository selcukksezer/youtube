const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const indexHtml = fs.readFileSync(
    path.join(__dirname, '..', '..', 'static', 'index.html'),
    'utf8',
);
const styles = fs.readFileSync(
    path.join(__dirname, '..', '..', 'static', 'style.css'),
    'utf8',
);
const disclosureMatch = indexHtml.match(
    /<details class="series-planner series-tools-disclosure mt-2" id="series-tools-disclosure">([\s\S]*?)<\/details>/,
);

test('optional continuity and series planning are collapsed together without nested disclosures', () => {
    assert.ok(disclosureMatch, 'series tools must be available in one disclosure');
    assert.doesNotMatch(disclosureMatch[0].split('>')[0], /\sopen(?:\s|=|>)/);
    assert.match(disclosureMatch[1], /Seri devamlılığı ve bölüm planı/);
    assert.match(disclosureMatch[1], /İsteğe bağlı/);
    assert.doesNotMatch(disclosureMatch[1], /<details\b/);
});

test('all existing continuity and series planner controls remain available', () => {
    for (const id of [
        'input-series-continuity',
        'btn-use-current-script-continuity',
        'select-series-episode-count',
        'btn-plan-series',
        'series-plan-results',
    ]) {
        assert.ok(disclosureMatch[1].includes(`id="${id}"`), `${id} must remain available`);
    }
});

test('series disclosure retains visible keyboard focus feedback', () => {
    assert.match(
        styles,
        /\.series-tools-summary:focus-visible\s*\{[^}]*outline:\s*2px/s,
    );
});
