const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const indexHtml = fs.readFileSync(
    path.join(__dirname, '..', '..', 'static', 'index.html'),
    'utf8',
);
const styles = fs.readFileSync(
    path.join(__dirname, '..', '..', 'static', 'style.css'),
    'utf8',
);
const disclosureMatch = indexHtml.match(
    /<details class="studio-render-settings" id="studio-render-settings">([\s\S]*?)<\/details>/,
);

test('optional render settings are collapsed while language and voice stay in the primary flow', () => {
    assert.ok(disclosureMatch, 'render settings must remain available in the Studio');
    assert.doesNotMatch(disclosureMatch[0].split('>')[0], /\sopen(?:\s|=|>)/);
    assert.match(disclosureMatch[1], /Ses, görsel ve render ayarları/);
    assert.ok(indexHtml.indexOf('id="select-language"') < indexHtml.indexOf(disclosureMatch[0]));
    assert.ok(indexHtml.indexOf('id="select-tts-voice"') < indexHtml.indexOf(disclosureMatch[0]));
});

test('optional topic research is collapsed and preserves its actions and saved content', () => {
    const researchMatch = indexHtml.match(
        /<details class="series-tools-disclosure mt-2" id="topic-research-tools"\s+data-niche-family="news stoic">([\s\S]*?)<\/details>/,
    );
    assert.ok(researchMatch, 'topic research must remain available in the Studio');
    assert.doesNotMatch(researchMatch[0].split('>')[0], /\sopen(?:\s|=|>)/);
    assert.match(researchMatch[1], /Trendler ve içerik boşlukları/);
    assert.match(researchMatch[1], /series-tools-optional">İsteğe bağlı/);
    for (const id of [
        'btn-load-niche-trends',
        'niche-trends-results',
        'content-gap-topics',
        'btn-analyze-content-gaps',
        'content-gap-results',
    ]) {
        assert.ok(researchMatch[1].includes(`id="${id}"`), `${id} must stay in the optional research panel`);
    }

    const stateJs = fs.readFileSync(
        path.join(__dirname, '..', '..', 'static', 'js', 'state.js'),
        'utf8',
    );
    assert.match(
        stateJs,
        /if \(s\.contentGaps\) \{\s*const el = document\.getElementById\('content-gap-topics'\);\s*if \(el\) el\.value = s\.contentGaps;\s*const researchTools = document\.getElementById\('topic-research-tools'\);\s*if \(researchTools\) researchTools\.open = true;\s*\}/,
    );
});

test('voice helper explains the free default and offline fallback clearly', () => {
    const voiceControl = indexHtml.match(
        /<select id="select-tts-voice"[\s\S]*?<small[^>]*>([\s\S]*?)<\/small>/,
    );
    assert.ok(voiceControl, 'voice selector must explain its default and fallback');
    assert.equal(
        voiceControl[1].replace(/\s+/g, ' ').trim(),
        'Edge Neural ücretsiz varsayılandır. Kota dolarsa ve çevrimiçi ses çalışmazsa Türkçe Piper çevrimdışı denenir.',
    );
});

test('production language uses one accessible selector and retains its state value', () => {
    assert.match(
        indexHtml,
        /id="studio-lang-selector-strip"[\s\S]*?role="group" aria-label="Üretim dili"[\s\S]*?id="btn-quick-lang-tr"[\s\S]*?aria-pressed="true"[\s\S]*?id="btn-quick-lang-en"[\s\S]*?aria-pressed="false"[\s\S]*?<select id="select-language" class="hidden" aria-hidden="true" tabindex="-1">/,
    );
    assert.doesNotMatch(indexHtml, /<label[^>]*for="select-language"/);

    const studioJs = fs.readFileSync(
        path.join(__dirname, '..', '..', 'static', 'js', 'studio.js'),
        'utf8',
    );
    const stateJs = fs.readFileSync(
        path.join(__dirname, '..', '..', 'static', 'js', 'state.js'),
        'utf8',
    );
    assert.match(studioJs, /btnTr\.setAttribute\('aria-pressed', String\(!isEn\)\)/);
    assert.match(studioJs, /btnEn\.setAttribute\('aria-pressed', String\(isEn\)\)/);
    assert.match(stateJs, /const restoredLanguage = s\.language === 'en' \? 'en' : 'tr'/);
    assert.match(stateJs, /btnTr\.setAttribute\('aria-pressed', String\(restoredLanguage === 'tr'\)\)/);
    assert.match(stateJs, /btnEn\.setAttribute\('aria-pressed', String\(restoredLanguage === 'en'\)\)/);

    const setLanguageMatch = studioJs.match(
        /^function setStudioLanguage\(lang, options = \{\}\) \{[\s\S]*?^\}/m,
    );
    assert.ok(setLanguageMatch);
    assert.ok(setLanguageMatch[0].indexOf('saveStudioSettings();') < setLanguageMatch[0].indexOf('populateTtsVoiceSelect(targetLang)'));
});

test('script actions follow script setup while render stays behind the quality check', () => {
    const position = id => indexHtml.indexOf(`id="${id}"`);
    const renderSettingsPosition = position('studio-render-settings');
    const qualityPanelPosition = position('studio-quality-panel');

    assert.ok(position('select-tts-voice') < position('studio-script-actions'));
    assert.ok(position('studio-script-actions') < renderSettingsPosition);
    for (const id of ['btn-create-script', 'btn-regenerate-script-studio', 'btn-translate-script']) {
        assert.ok(position('studio-script-actions') < position(id), `${id} must stay in the script action group`);
        assert.ok(position(id) < renderSettingsPosition, `${id} must precede optional render settings`);
    }
    assert.ok(renderSettingsPosition < qualityPanelPosition);
    assert.ok(qualityPanelPosition < position('studio-render-actions'));
    assert.ok(position('studio-render-actions') < position('btn-quick-render'));
});

test('primary script action reflects topic readiness and stays locked during generation', () => {
    const stateJs = fs.readFileSync(
        path.join(__dirname, '..', '..', 'static', 'js', 'state.js'),
        'utf8',
    );
    const actionMatch = stateJs.match(
        /^function updateScriptActionButtons\(\) \{[\s\S]*?^\}/m,
    );
    assert.ok(actionMatch, 'state.js must define the Studio action state');

    const button = { className: '', disabled: false, innerHTML: '', dataset: {} };
    const context = {
        document: { getElementById: id => id === 'btn-create-script' ? button : null },
        window: { APP_STATE: { language: 'tr' } },
        currentPlan: null,
        inputTopic: { value: '' },
        selectLanguage: { value: 'tr' },
        hasExistingPlan: () => Boolean(context.currentPlan),
    };
    vm.runInNewContext(`${actionMatch[0]}\nglobalThis.refreshActions = updateScriptActionButtons;`, context);

    context.refreshActions();
    assert.equal(button.disabled, true);
    assert.match(button.innerHTML, /Konu girin/);

    context.inputTopic.value = 'Stoacılıkta öfke kontrolü';
    context.refreshActions();
    assert.equal(button.disabled, false);
    assert.equal(button.className, 'btn btn-primary btn-lg');
    assert.match(button.innerHTML, /Senaryo Yaz/);

    button.dataset.generating = 'true';
    button.innerHTML = 'AI Senaryosu Yazılıyor...';
    context.refreshActions();
    assert.equal(button.disabled, true);
    assert.equal(button.innerHTML, 'AI Senaryosu Yazılıyor...');

    delete button.dataset.generating;
    context.currentPlan = { title: context.inputTopic.value, language: 'tr' };
    context.refreshActions();
    assert.equal(button.disabled, false);
    assert.match(button.innerHTML, /Senaryoyu İncele & Düzenle/);

    const studioJs = fs.readFileSync(
        path.join(__dirname, '..', '..', 'static', 'js', 'studio.js'),
        'utf8',
    );
    assert.match(studioJs, /btnCreateScript\.dataset\.generating = 'true'/);
    assert.match(studioJs, /delete btnCreateScript\.dataset\.generating/);
});

test('topic editor wraps long titles without accepting accidental line breaks', () => {
    assert.match(indexHtml, /<textarea id="input-topic" class="textarea-styled topic-title-input" rows="2" wrap="soft"/);
    assert.match(styles, /\.topic-title-input\s*\{[^}]*min-height:\s*60px;[^}]*resize:\s*vertical;/);

    const studioJs = fs.readFileSync(
        path.join(__dirname, '..', '..', 'static', 'js', 'studio.js'),
        'utf8',
    );
    assert.match(
        studioJs,
        /inputTopic\?\.addEventListener\('keydown', \(event\) => \{\s*if \(event\.key === 'Enter' && !event\.isComposing\) event\.preventDefault\(\);/,
    );
});

test('render setting controls keep their existing IDs and default values', () => {
    for (const id of [
        'studio-bgm-track',
        'chk-intro-whoosh',
        'chk-enable-bgm',
        'chk-enable-sonilo-sfx',
        'chk-enable-outro',
        'select-visual-engine',
        'public-apis-fallback',
        'select-render-resolution',
        'select-studio-safe-mode',
    ]) {
        assert.ok(disclosureMatch[1].includes(`id="${id}"`), `${id} must remain available`);
    }
    assert.match(disclosureMatch[1], /id="chk-enable-bgm" checked/);
    assert.match(disclosureMatch[1], /id="chk-enable-sonilo-sfx"/);
    assert.match(disclosureMatch[1], /id="select-render-resolution"[\s\S]*?value="1080p" selected/);
});

test('render settings disclosure has keyboard focus and responsive option layout styles', () => {
    const styles = fs.readFileSync(
        path.join(__dirname, '..', '..', 'static', 'style.css'),
        'utf8',
    );
    assert.match(
        styles,
        /\.studio-render-settings__summary:focus-visible\s*\{[^}]*outline:\s*2px/s,
    );
    assert.match(
        styles,
        /\.studio-render-settings__body > \.form-row-2\s*\{\s*grid-template-columns:\s*repeat\(auto-fit/s,
    );
});

test('empty niche profile stays hidden until its profile content is loaded', () => {
    assert.match(indexHtml, /<div class="mt-3 hidden" id="niche-production-profile"/);
    const studioJs = fs.readFileSync(
        path.join(__dirname, '..', '..', 'static', 'js', 'studio.js'),
        'utf8',
    );
    assert.match(studioJs, /profileBox\.classList\.add\('hidden'\)/);
    assert.match(studioJs, /profileBox\.classList\.remove\('hidden'\)/);
    assert.match(studioJs, /if \(!profile\) throw new Error/);
});
