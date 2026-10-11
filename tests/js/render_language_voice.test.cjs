const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const source = fs.readFileSync(
    path.join(__dirname, '..', '..', 'static', 'js', 'studio.js'),
    'utf8',
);
const helperMatch = source.match(
    /^function ensureTtsVoiceForLanguage\(lang\) \{[\s\S]*?^\}/m,
);
const languageFunctionMatch = source.match(
    /^function setStudioLanguage\(lang, options = \{\}\) \{[\s\S]*?^\}/m,
);

assert.ok(helperMatch, 'studio.js must define ensureTtsVoiceForLanguage');
assert.ok(languageFunctionMatch, 'studio.js must define setStudioLanguage');
assert.match(
    languageFunctionMatch[0],
    /ensureTtsVoiceForLanguage\(targetLang\);/,
    'language changes must reconcile the selected voice with the target language',
);

function reconcileVoice(language, selectedVoice, catalog) {
    const selector = {
        value: selectedVoice,
        options: [
            { value: 'auto' },
            { value: 'tr-TR-AhmetNeural' },
            { value: 'en-US-GuyNeural' },
            { value: 'local:piper-tr' },
            { value: 'en-US-AndrewMultilingualNeural' },
        ],
    };
    const context = {
        selectTtsVoice: selector,
        ttsVoiceCatalog: catalog,
        LOCAL_OFFLINE_VOICES: [{ id: 'local:piper-tr' }],
    };
    vm.runInNewContext(
        `${helperMatch[0]}\nglobalThis.reconcile = ensureTtsVoiceForLanguage;`,
        context,
    );
    context.reconcile(language);
    return selector.value;
}

test('switching back to Turkish replaces an English-only voice with a compatible default', () => {
    assert.equal(
        reconcileVoice('tr', 'en-US-GuyNeural', {
            tr: [{ id: 'tr-TR-AhmetNeural' }],
            en: [{ id: 'en-US-GuyNeural' }],
        }),
        'tr-TR-AhmetNeural',
    );
});

test('language switching preserves multilingual and local voices supported by the API', () => {
    const catalog = {
        tr: [{ id: 'tr-TR-AhmetNeural' }, { id: 'en-US-AndrewMultilingualNeural' }],
        en: [{ id: 'en-US-GuyNeural' }],
    };
    assert.equal(
        reconcileVoice('tr', 'en-US-AndrewMultilingualNeural', catalog),
        'en-US-AndrewMultilingualNeural',
    );
    assert.equal(reconcileVoice('en', 'local:piper-tr', catalog), 'local:piper-tr');
});
