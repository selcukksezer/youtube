const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const source = fs.readFileSync(
    path.join(__dirname, '..', '..', 'static', 'js', 'render-monitor.js'),
    'utf8',
);
const formatterMatch = source.match(
    /^function formatRenderErrorDetail\(detail\) \{[\s\S]*?^\}/m,
);

assert.ok(formatterMatch, 'render-monitor.js must define formatRenderErrorDetail');

function formatRenderErrorDetail(detail) {
    const context = {};
    vm.runInNewContext(
        `${formatterMatch[0]}\nglobalThis.formatRenderErrorDetail = formatRenderErrorDetail;`,
        context,
    );
    return context.formatRenderErrorDetail(detail);
}

test('formats FastAPI validation errors with field paths and messages', () => {
    const formatted = formatRenderErrorDetail([
        { loc: ['body', 'tts_voice'], msg: 'voice is not available', type: 'value_error' },
        { loc: ['body', 'subtitle_font_size'], msg: 'Input should be less than or equal to 72', type: 'less_than_equal' },
    ]);

    assert.equal(
        formatted,
        'tts_voice: voice is not available\nsubtitle_font_size: Input should be less than or equal to 72',
    );
    assert.doesNotMatch(formatted, /\[object Object\]/);
});

test('preserves plain-text render errors', () => {
    assert.equal(formatRenderErrorDetail('Render could not start'), 'Render could not start');
});

test('formats structured render gate errors without object coercion', () => {
    const formatted = formatRenderErrorDetail({
        message: 'Script failed quality gate',
        script_quality: {
            duration: 22,
            word_count: 48,
            scene_count: 3,
            limits: { min_words: 85, max_words: 195, hard_min_scenes: 4, hard_max_scenes: 24 },
            issues: ['word_count_out_of_band:48', 'scene_count_out_of_band:3'],
        },
    });

    assert.match(formatted, /Script failed quality gate/);
    assert.match(formatted, /mevcut: 48/);
    assert.doesNotMatch(formatted, /\[object Object\]/);
});
