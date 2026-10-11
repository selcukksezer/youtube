const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const clipperScript = fs.readFileSync(
    path.join(__dirname, '..', '..', 'static', 'js', 'clipper.js'),
    'utf8',
);
const studioHtml = fs.readFileSync(
    path.join(__dirname, '..', '..', 'static', 'index.html'),
    'utf8',
);

test('multimodal provider is selected only by the explicit clipper checkbox', () => {
    assert.match(
        clipperScript,
        /const multimodal = document\.getElementById\('clipper-multimodal'\)\?\.checked === true;/,
    );
    assert.match(clipperScript, /analysis_mode', multimodal \? 'multimodal' : 'transcript'/);
    assert.match(
        clipperScript,
        /external_analysis_consent', multimodal \? 'true' : 'false'/,
    );
    assert.match(
        clipperScript,
        /let highlights = render \? window\.__clipperHighlights \|\| null : null;/,
    );
});

test('the UI discloses that opt-in analysis sends the video to TwelveLabs', () => {
    assert.match(studioHtml, /id="clipper-multimodal"/);
    assert.match(studioHtml, /video URL'si TwelveLabs'a gönderilir/);
    assert.match(studioHtml, /yalnızca paylaşma yetkiniz olan/i);
});

test('suggesting after a prior result reruns the selected provider instead of resending cached clips', async () => {
    const handlers = {};
    const values = {
        'clipper-url': { value: 'https://example.test/video.mp4' },
        'clipper-count': { value: '3' },
        'clipper-start-ost': { value: '0' },
        'clipper-end-ost': { value: '0' },
        'clipper-deleted': { value: '' },
        'clipper-multimodal': { checked: true },
        'clipper-manual-start': { value: '' },
        'clipper-manual-end': { value: '' },
        'clipper-result': { textContent: '' },
        'clipper-suggest': {
            addEventListener: (event, handler) => { handlers.suggest = handler; },
        },
        'clipper-cut': { addEventListener: () => {} },
    };
    let requestBody;

    class MockFormData {
        constructor() {
            this.values = {};
        }

        append(key, value) {
            this.values[key] = value;
        }
    }

    const context = {
        document: { getElementById: (id) => values[id] || null },
        window: {
            __clipperHighlights: [
                { start_time: 5, end_time: 40, title: 'Cached suggestion' },
            ],
        },
        FormData: MockFormData,
        fetch: async (_url, options) => {
            requestBody = options.body.values;
            return { ok: true, json: async () => ({ highlights: [] }) };
        },
    };
    vm.runInNewContext(clipperScript, context);
    await handlers.suggest();

    assert.equal(requestBody.analysis_mode, 'multimodal');
    assert.equal(requestBody.external_analysis_consent, 'true');
    assert.equal(requestBody.highlights, undefined);
});
