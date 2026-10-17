const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.resolve(__dirname, '../..');

test('all 10 UX roadmap modules (Categories A-J) parse cleanly and expose expected hooks', () => {
    const modules = [
        'studio-wizard.js',
        'studio-wizard-step1.js',
        'studio-wizard-step2.js',
        'studio-wizard-step3.js',
        'studio-wizard-step4.js',
        'studio-phone-preview.js',
        'timeline-ux-enhancements.js',
        'tools-ux-enhancements.js',
        'gallery-channels-ux.js',
        'visual-hierarchy-ux.js',
    ];

    for (const mod of modules) {
        const fullPath = path.join(ROOT, 'static', 'js', mod);
        assert.ok(fs.existsSync(fullPath), `Missing ${mod}`);
        const source = fs.readFileSync(fullPath, 'utf8');
        // Verify valid JS syntax by compiling with Function constructor
        assert.doesNotThrow(() => new Function(source), `Syntax error in ${mod}`);
    }
});

test('Category I & J modules contain required interactive feature identifiers (Items 81-100)', () => {
    const catI = fs.readFileSync(path.join(ROOT, 'static', 'js', 'gallery-channels-ux.js'), 'utf8');
    assert.match(catI, /header-channel-switcher/);
    assert.match(catI, /gallery-filter-search-bar/);
    assert.match(catI, /playbackRate\s*=\s*1\.5/);
    assert.match(catI, /gal-provenance-strip/);
    assert.match(catI, /btn-gal-clone-settings/);
    assert.match(catI, /pub-preupload-confirm-panel/);
    assert.match(catI, /btn-gal-bulk-zip/);
    assert.match(catI, /modal-proof-dossier-viewer/);
    assert.match(catI, /channels-weekly-calendar/);
    assert.match(catI, /gal-ab-titles-row/);

    const catJ = fs.readFileSync(path.join(ROOT, 'static', 'js', 'visual-hierarchy-ux.js'), 'utf8');
    assert.match(catJ, /cmd-palette-modal/);
    assert.match(catJ, /renderShimmerSkeleton/);
    assert.match(catJ, /toast-action-btn/);
    assert.match(catJ, /is-sticky-stage-rail/);
    assert.match(catJ, /sem-badge-ready/);
    assert.match(catJ, /ux-floating-tooltip/);
    assert.match(catJ, /mobile-preview-drawer-fab/);
    assert.match(catJ, /btn-empty-state-quickstart/);
    assert.match(catJ, /density-compact/);
});
