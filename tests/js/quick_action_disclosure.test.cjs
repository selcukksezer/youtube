const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const indexHtml = fs.readFileSync(
    path.join(__dirname, '..', '..', 'static', 'index.html'),
    'utf8',
);
const drawerMatch = indexHtml.match(
    /<details class="quick-action-drawer mb-4" id="quick-action-drawer">([\s\S]*?)<\/details>/,
);

test('secondary quick actions are collapsed behind a summary that names their categories', () => {
    assert.ok(drawerMatch, 'quick actions must remain available in a native disclosure');
    assert.doesNotMatch(drawerMatch[0].split('>')[0], /\sopen(?:\s|=|>)/);
    assert.match(drawerMatch[1], /<summary class="quick-action-summary">/);
    assert.match(drawerMatch[1], /Hızlı başlangıçlar/);
    assert.match(drawerMatch[1], /Rastgele konu · haber · oyun · İngilizce · ürün/);
});

test('all existing quick action button IDs remain available inside the disclosure', () => {
    for (const id of [
        'qa-random-niche',
        'qa-latest-news',
        'qa-split-mode',
        'qa-tier1-en',
        'btn-open-afm-modal',
    ]) {
        assert.ok(drawerMatch[1].includes(`id="${id}"`), `${id} must remain available`);
    }
});
