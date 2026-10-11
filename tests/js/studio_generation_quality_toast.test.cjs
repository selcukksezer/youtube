const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const studioSource = fs.readFileSync(
    path.join(__dirname, '..', '..', 'static', 'js', 'studio.js'),
    'utf8',
);
const helperMatch = studioSource.match(
    /^function showScriptGenerationToast\(validation, forceRegenerate, qualityRepair\) \{[\s\S]*?^\}/m,
);

assert.ok(helperMatch, 'studio.js must define showScriptGenerationToast');
assert.match(
    studioSource,
    /showScriptGenerationToast\(validation, forceRegenerate, data\.script_quality_repair\);/,
    'script generation must report the quality result',
);

function runToast(validation, forceRegenerate = false, qualityRepair = null) {
    const calls = [];
    const context = {
        showToast: (...args) => calls.push(args),
    };
    vm.runInNewContext(
        `${helperMatch[0]}\nglobalThis.showScriptGenerationToast = showScriptGenerationToast;`,
        context,
    );
    context.showScriptGenerationToast(validation, forceRegenerate, qualityRepair);
    return calls;
}

test('quality hard-fail does not show a successful generation toast', () => {
    assert.deepEqual(
        runToast({ ok: true, hard_fail: true, script_quality: { hard_fail: true } }),
        [['Senaryo üretildi ancak kalite kapısı renderı engelliyor; timeline uyarılarını düzeltin.', 'warn']],
    );
});

test('narration validation failure is also reported as a warning', () => {
    const [toast] = runToast({ ok: false, hard_fail: false });
    assert.equal(toast[1], 'warn');
    assert.match(toast[0], /kalite kapısı/);
});

test('valid generation preserves normal success toasts', () => {
    assert.deepEqual(runToast({ ok: true, hard_fail: false }), [
        ['Senaryo hazır — timeline\'da inceleyin', 'success'],
    ]);
    assert.deepEqual(runToast({ ok: true, hard_fail: false }, true), [
        ['Senaryo başarıyla yeniden yazıldı', 'success'],
    ]);
});

test('automatic quality repair and unresolved repair get explicit feedback', () => {
    assert.deepEqual(
        runToast({ ok: true }, false, { status: 'repaired' }),
        [['Senaryo kalite uyarıları yapay zekâ tarafından otomatik düzeltildi.', 'success']],
    );
    assert.deepEqual(
        runToast({ ok: true }, false, { status: 'provider_unavailable' }),
        [['Senaryo kalite sorunlarının bir kısmı otomatik düzeltilemedi; timeline raporunu inceleyin.', 'warn']],
    );
});
