const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const indexHtml = fs.readFileSync(
    path.join(__dirname, '..', '..', 'static', 'index.html'),
    'utf8',
);
const stateSource = fs.readFileSync(
    path.join(__dirname, '..', '..', 'static', 'js', 'state.js'),
    'utf8',
);
const sectionMatch = indexHtml.match(
    /<details class="fx-switches-card mt-3" id="render-enhancement-options">([\s\S]*?)<\/details>/,
);

test('advanced render controls stay collapsed without removing existing options', () => {
    assert.ok(sectionMatch, 'advanced render controls must use a native details disclosure');
    assert.doesNotMatch(sectionMatch[0].split('>')[0], /\sopen(?:\s|=|>)/);
    assert.match(sectionMatch[1], /<summary class="fx-header">/);

    const existingControlIds = [
        'chk-hook-card',
        'chk-split-screen',
        'chk-reddit-card',
        'select-gameplay-category',
        'chk-anti-duplicate',
        'chk-ken-burns',
        'chk-zoompan',
        'chk-broll-insert',
        'chk-center-face',
        'chk-emphasis-card',
        'chk-audio-visualizer',
        'chk-news-ticker',
        'chk-allow-similar-script',
        'chk-resume-render',
        'chk-whisper-align',
    ];
    for (const id of existingControlIds) {
        assert.ok(sectionMatch[1].includes(`id="${id}"`), `${id} must remain in the disclosure`);
    }
});

test('the disclosure summarizes active options and updates when they change', () => {
    assert.match(sectionMatch[1], /id="fx-enabled-count" aria-live="polite"/);
    assert.match(
        stateSource,
        /fxOptionToggles\.forEach\(toggle => toggle\.addEventListener\('change', updateFxEnabledCount\)\)/,
    );
    assert.match(stateSource, /chkEmphasisCardLab\?\.addEventListener\('change', updateFxEnabledCount\)/);
    assert.match(stateSource, /fxEnabledCount\.textContent = `\$\{enabledCount\} açık`;/);
});
