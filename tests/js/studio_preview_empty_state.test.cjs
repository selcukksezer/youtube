const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const indexHtml = fs.readFileSync(
    path.join(__dirname, '..', '..', 'static', 'index.html'),
    'utf8',
);
const styleCss = fs.readFileSync(
    path.join(__dirname, '..', '..', 'static', 'style.css'),
    'utf8',
);

const previewMatch = indexHtml.match(
    /<div class="glass-box preview-mockup-card">([\s\S]*?)<\/div>\s*<\/div>\s*<\/section>/,
);

test('empty phone preview is identified as an example and explains what appears after rendering', () => {
    assert.ok(previewMatch, 'Studio must keep the Shorts preview');
    assert.match(previewMatch[1], /<h3>9:16 Shorts Önizlemesi<\/h3>/);
    assert.match(previewMatch[1], /<span class="preview-example-label">ÖRNEK GÖRÜNÜM<\/span>/);
    assert.match(
        previewMatch[1],
        /id="mockup-status-text">Render tamamlandığında videonuz burada oynatılır\./,
    );
    assert.match(previewMatch[1], /Kanca örneği · ilk 3 sn:/);
    assert.match(previewMatch[1], /Kapanış örneği:/);
});

test('decorative Shorts actions no longer imply fake engagement counts', () => {
    const actionMarkup = previewMatch[1].match(
        /<div class="phone-side-actions" aria-hidden="true">([\s\S]*?)<\/div>\s*<\/div>/,
    );
    assert.ok(actionMarkup, 'mock feed actions must be hidden from assistive technology');
    assert.match(actionMarkup[1], /<span>Beğen<\/span>/);
    assert.match(actionMarkup[1], /<span>Yorum<\/span>/);
    assert.doesNotMatch(actionMarkup[1], /148K|5\.2K/);
});

test('example subtitles reserve clear space for the Shorts action rail', () => {
    const overlayRule = styleCss.match(/\.mockup-subtitle-overlay\s*\{([^}]+)\}/);
    assert.ok(overlayRule, 'the subtitle overlay must keep an explicit layout rule');

    const rightInset = Number(overlayRule[1].match(/right:\s*(\d+)px/)?.[1]);
    assert.ok(rightInset >= 44, 'subtitle text must stay left of the 30px action rail and its gap');
});

test('hook and closing examples stack into readable blocks on narrow screens', () => {
    assert.match(
        styleCss,
        /@media \(max-width: 480px\) \{\s*\.loop-bridge-card \{\s*align-items: stretch;\s*flex-direction: column;/,
    );
});
