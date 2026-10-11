const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const studioSource = fs.readFileSync(
    path.join(__dirname, '..', '..', 'static', 'js', 'studio.js'),
    'utf8',
);
const stateSource = fs.readFileSync(
    path.join(__dirname, '..', '..', 'static', 'js', 'state.js'),
    'utf8',
);
const rendererMatch = studioSource.match(
    /^function renderTopicSuggestCards\(suggestions, nicheName\) \{[\s\S]*?^\}/m,
);

assert.ok(rendererMatch, 'studio.js must define renderTopicSuggestCards');

test('topic cards show the external source and safely render its signal detail', () => {
    const nodes = {
        'topic-suggest-panel': { classList: { remove() {} } },
        'topic-suggest-body': { innerHTML: '', querySelectorAll: () => [] },
        'topic-suggest-title': { innerHTML: '' },
    };
    const context = {
        document: { getElementById: (id) => nodes[id] || null },
        selectLanguage: { value: 'tr' },
        TOPIC_SOURCE_LABELS: {
            google_trends: {
                label: 'Google Trends',
                icon: 'fa-solid fa-arrow-trend-up',
                cls: 'trend',
            },
            ai: { label: 'AI', icon: 'fa-solid fa-wand-magic-sparkles', cls: 'ai' },
        },
        escapeHtml: (value) => String(value || '')
            .replaceAll('&', '&amp;')
            .replaceAll('<', '&lt;')
            .replaceAll('>', '&gt;')
            .replaceAll('"', '&quot;')
            .replaceAll("'", '&#39;'),
    };

    vm.runInNewContext(
        `let lastTopicSuggestions = [];\n${rendererMatch[0]}\nglobalThis.render = renderTopicSuggestCards;`,
        context,
    );
    context.render([{
        title: 'Stoacılıkta disiplin',
        source: 'google_trends',
        source_detail: 'Google Trends · trafik <20K>',
        confidence: 87,
    }], 'Stoacılık');

    assert.match(nodes['topic-suggest-body'].innerHTML, /Google Trends/);
    assert.match(nodes['topic-suggest-body'].innerHTML, /Google Trends · trafik &lt;20K&gt;/);
    assert.doesNotMatch(nodes['topic-suggest-body'].innerHTML, /trafik <20K>/);
});

test('source labels include Google Trends and RSS', () => {
    assert.match(stateSource, /google_trends:\s*\{\s*label:\s*'Google Trends'/);
    assert.match(stateSource, /rss:\s*\{\s*label:\s*'RSS'/);
});
