const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const source = fs.readFileSync(
    path.join(__dirname, '..', '..', 'static', 'js', 'audio-media.js'),
    'utf8',
);
const appendGroupMatch = source.match(
    /^function appendEdgeVoiceGroup\(selectEl, label, voices\) \{[\s\S]*?^\}/m,
);
const populateMatch = source.match(
    /^function populateTtsVoiceSelect\(lang\) \{[\s\S]*?^\}/m,
);

assert.ok(appendGroupMatch, 'audio-media.js must define appendEdgeVoiceGroup');
assert.ok(populateMatch, 'audio-media.js must define populateTtsVoiceSelect');

function createSelect(selectedVoice) {
    const groups = [];
    const directOptions = [];
    return {
        value: selectedVoice,
        set innerHTML(_value) {
            groups.length = 0;
            directOptions.length = 0;
            directOptions.push({ value: 'auto', textContent: 'Automatic' });
        },
        get options() {
            return [...directOptions, ...groups.flatMap(group => group.children)];
        },
        appendChild(group) {
            groups.push(group);
        },
    };
}

function populate(language, selectedVoice = 'auto', savedVoice = '') {
    const selector = createSelect(selectedVoice);
    const context = {
        selectTtsVoice: selector,
        ttsVoiceCatalog: {
            tr: [
                { id: 'tr-TR-AhmetNeural', label: 'Ahmet', gender: 'male', quality: 'Neural', native: true },
                { id: 'en-US-AndrewMultilingualNeural', label: 'Andrew', gender: 'male', quality: 'Multilingual Neural', native: false },
            ],
            en: [
                { id: 'en-US-GuyNeural', label: 'Guy', gender: 'male', quality: 'Neural', native: true },
            ],
            local: [{ id: 'local:piper-tr', label: 'Piper', gender: 'male', quality: 'Local' }],
            elevenlabs: [{ id: 'elevenlabs:multilingual', label: 'Multilingual', gender: 'female', quality: 'Multilingual' }],
            elevenlabs_meta: {},
        },
        STATIC_TTS_FALLBACK: { tr: [], en: [] },
        LOCAL_OFFLINE_VOICES: [{ id: 'local:piper-tr', label: 'Piper', gender: 'male', quality: 'Local' }],
        document: {
            createElement() {
                return {
                    children: [],
                    appendChild(child) { this.children.push(child); },
                };
            },
        },
        savedTtsVoicePreference: () => '',
        restoreStudioSettings: () => ({ ttsVoice: savedVoice }),
        genderLabel: gender => gender,
    };

    vm.runInNewContext(
        `${appendGroupMatch[0]}\n${populateMatch[0]}\nglobalThis.populate = populateTtsVoiceSelect;`,
        context,
    );
    context.populate(language);
    return {
        selected: selector.value,
        options: selector.options.map(option => option.value),
    };
}

test('voice selector exposes only Edge voices accepted for the selected language', () => {
    const turkish = populate('tr');
    const english = populate('en');

    assert.ok(turkish.options.includes('tr-TR-AhmetNeural'));
    assert.ok(turkish.options.includes('en-US-AndrewMultilingualNeural'));
    assert.ok(!turkish.options.includes('en-US-GuyNeural'));
    assert.ok(english.options.includes('en-US-GuyNeural'));
    assert.ok(!english.options.includes('tr-TR-AhmetNeural'));
});

test('unsupported current voice falls back to a compatible saved choice or auto', () => {
    assert.equal(populate('tr', 'en-US-GuyNeural', 'tr-TR-AhmetNeural').selected, 'tr-TR-AhmetNeural');
    assert.equal(populate('tr', 'en-US-GuyNeural').selected, 'auto');
});

test('shared local and multilingual provider voices remain selectable', () => {
    const { options } = populate('tr');
    assert.ok(options.includes('local:piper-tr'));
    assert.ok(options.includes('elevenlabs:multilingual'));
});
