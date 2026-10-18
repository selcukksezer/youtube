/**
 * ShortsAI Studio — Audio, TTS, SFX & Subtitle Lab (audio-media.js)
 * Covers Subtitle lab presets, SFX synthetic sound effects, and Edge/ElevenLabs TTS voice catalog.
 */

const TTS_VOICE_STORAGE_KEY = 'shortsTtsVoice';

const LOCAL_OFFLINE_VOICES = [
    { id: 'local:piper-tr', label: 'Piper Türkçe (çevrimdışı)', gender: 'male', quality: 'Local', native: true },
];

const STATIC_TTS_FALLBACK = {
    tr: [
        { id: 'tr-TR-AhmetNeural', label: 'Ahmet', gender: 'male', quality: 'Neural', native: true },
        { id: 'tr-TR-EmelNeural', label: 'Emel', gender: 'female', quality: 'Neural', native: true },
        { id: 'en-US-AndrewMultilingualNeural', label: 'Andrew (çok dilli)', gender: 'male', quality: 'Multilingual Neural', native: false },
        { id: 'en-US-AvaMultilingualNeural', label: 'Ava (çok dilli)', gender: 'female', quality: 'Multilingual Neural', native: false },
        { id: 'en-US-BrianMultilingualNeural', label: 'Brian (çok dilli)', gender: 'male', quality: 'Multilingual Neural', native: false },
        { id: 'en-US-EmmaMultilingualNeural', label: 'Emma (çok dilli)', gender: 'female', quality: 'Multilingual Neural', native: false },
        { id: 'en-AU-WilliamMultilingualNeural', label: 'William (çok dilli)', gender: 'male', quality: 'Multilingual Neural', native: false },
        { id: 'de-DE-FlorianMultilingualNeural', label: 'Florian (çok dilli)', gender: 'male', quality: 'Multilingual Neural', native: false },
        { id: 'de-DE-SeraphinaMultilingualNeural', label: 'Seraphina (çok dilli)', gender: 'female', quality: 'Multilingual Neural', native: false },
        { id: 'fr-FR-RemyMultilingualNeural', label: 'Remy (çok dilli)', gender: 'male', quality: 'Multilingual Neural', native: false },
        { id: 'fr-FR-VivienneMultilingualNeural', label: 'Vivienne (çok dilli)', gender: 'female', quality: 'Multilingual Neural', native: false },
        { id: 'it-IT-GiuseppeMultilingualNeural', label: 'Giuseppe (çok dilli)', gender: 'male', quality: 'Multilingual Neural', native: false },
        { id: 'ko-KR-HyunsuMultilingualNeural', label: 'Hyunsu (çok dilli)', gender: 'male', quality: 'Multilingual Neural', native: false },
        { id: 'pt-BR-ThalitaMultilingualNeural', label: 'Thalita (çok dilli)', gender: 'female', quality: 'Multilingual Neural', native: false },
    ],
    en: [
        { id: 'en-US-GuyNeural', label: 'Guy (US)', gender: 'male', quality: 'Neural', native: true },
        { id: 'en-US-JennyNeural', label: 'Jenny (US)', gender: 'female', quality: 'Neural', native: true },
        { id: 'en-US-AriaNeural', label: 'Aria (US)', gender: 'female', quality: 'Neural', native: true },
        { id: 'en-US-AndrewNeural', label: 'Andrew (US)', gender: 'male', quality: 'Neural', native: true },
        { id: 'en-US-BrianNeural', label: 'Brian (US)', gender: 'male', quality: 'Neural', native: true },
        { id: 'en-US-EmmaNeural', label: 'Emma (US)', gender: 'female', quality: 'Neural', native: true },
        { id: 'en-US-ChristopherNeural', label: 'Christopher (US)', gender: 'male', quality: 'Neural', native: true },
        { id: 'en-US-EricNeural', label: 'Eric (US)', gender: 'male', quality: 'Neural', native: true },
        { id: 'en-US-MichelleNeural', label: 'Michelle (US)', gender: 'female', quality: 'Neural', native: true },
        { id: 'en-GB-SoniaNeural', label: 'Sonia (UK)', gender: 'female', quality: 'Neural', native: true },
        { id: 'en-GB-RyanNeural', label: 'Ryan (UK)', gender: 'male', quality: 'Neural', native: true },
        { id: 'en-AU-NatashaNeural', label: 'Natasha (AU)', gender: 'female', quality: 'Neural', native: true },
        { id: 'en-CA-ClaraNeural', label: 'Clara (CA)', gender: 'female', quality: 'Neural', native: true },
        { id: 'en-CA-LiamNeural', label: 'Liam (CA)', gender: 'male', quality: 'Neural', native: true },
    ],
};
let ttsVoiceCatalog = {
    tr: STATIC_TTS_FALLBACK.tr.slice(),
    en: STATIC_TTS_FALLBACK.en.slice(),
    elevenlabs: [],
};
let elevenlabsConfigured = false;

// 6. ALTYAZI PRESET SEÇİCİ & ANİMASYON TESTİ (Items 42 & 43)
// ══════════════════════════════════════════════════════════════
const SUBTITLE_LAB_KEY = 'subtitleLabSettings';
let SUBTITLE_STYLE_TOKENS = null;

function applySubtitleCardTokens() {
    if (!SUBTITLE_STYLE_TOKENS) return;
    document.querySelectorAll('.preset-card').forEach(card => {
        const token = SUBTITLE_STYLE_TOKENS[card.getAttribute('data-preset')];
        if (!token) return;
        const preview = card.querySelector('.preset-preview');
        if (!preview) return;
        preview.style.color = token.color;
        preview.style.background = token.preview_background || token.stroke_color;
        preview.style.fontWeight = token.bold === false ? '400' : '800';
        const glow = token.glow ? `0 0 10px ${token.highlight_color}` : 'none';
        if (token.box) {
            const box = preview.querySelector('span');
            if (!box) return;
            box.style.background = token.box_color || '#000000';
            box.style.color = token.color;
            box.style.padding = '2px 6px';
            const inner = box.querySelector('span');
            if (inner) {
                inner.style.color = token.highlight_color;
                inner.style.textShadow = glow;
            }
            return;
        }
        const hi = preview.querySelector('span');
        if (hi) {
            hi.style.color = token.highlight_color;
            hi.style.textShadow = glow;
        }
    });
}

function loadSubtitleStyleTokens() {
    return fetch('/static/js/subtitle-style-tokens.json?v=p5')
        .then(response => response.json())
        .then(data => {
            SUBTITLE_STYLE_TOKENS = data;
            applySubtitleCardTokens();
            updateSubtitleSimulator();
        })
        .catch(() => {});
}
const subRangeSize = document.getElementById('sub-range-size');
const subRangeY = document.getElementById('sub-range-y');
const valSubSize = document.getElementById('val-sub-size');
const valSubY = document.getElementById('val-sub-y');
const subStage = document.getElementById('sub-stage');

function getSubtitleLabSettings() {
    return {
        preset: selectSubPreset?.value || 'capcut_yellow',
        fontSize: parseInt(subRangeSize?.value || '54', 10),
        yPosition: parseFloat(subRangeY?.value || '0.8'),
    };
}

function saveSubtitleLabSettings() {
    try {
        localStorage.setItem(SUBTITLE_LAB_KEY, JSON.stringify(getSubtitleLabSettings()));
    } catch (_) {}
}

function restoreSubtitleLabSettings() {
    try {
        const raw = localStorage.getItem(SUBTITLE_LAB_KEY);
        if (!raw) return;
        const s = JSON.parse(raw);
        if (s.preset && selectSubPreset) selectSubPreset.value = s.preset;
        if (s.fontSize && subRangeSize) subRangeSize.value = s.fontSize;
        if (s.yPosition && subRangeY) subRangeY.value = s.yPosition;
        document.querySelectorAll('.preset-card').forEach(c => {
            c.classList.toggle('active', c.getAttribute('data-preset') === s.preset);
        });
    } catch (_) {}
}

function updateSubtitleSimulator() {
    const preset = selectSubPreset?.value || 'capcut_yellow';
    const token = (SUBTITLE_STYLE_TOKENS && SUBTITLE_STYLE_TOKENS[preset]) || null;
    const fontSize = parseInt(subRangeSize?.value || '54', 10);
    const yPct = parseFloat(subRangeY?.value || '0.8');
    const highlight = token?.highlight_color || '#FFD700';
    const baseColor = token?.color || '#FFFFFF';
    const glow = token?.glow ? `0 0 15px ${highlight}` : 'none';

    if (valSubSize) valSubSize.textContent = `${fontSize} px`;
    if (valSubY) valSubY.textContent = `%${Math.round(yPct * 100)} (Alt Kısım)`;

    if (subStage) {
        subStage.className = `subtitle-stage preset-${preset}`;
        subStage.style.alignItems = yPct <= 0.65 ? 'flex-start' : (yPct >= 0.75 ? 'flex-end' : 'center');
        subStage.style.paddingBottom = yPct >= 0.75 ? '14px' : '0';
        subStage.style.paddingTop = yPct <= 0.65 ? '14px' : '0';
    }
    const stageText = subStage?.querySelector('.stage-text');
    if (stageText) {
        stageText.style.fontSize = `${Math.round(fontSize * 0.44)}px`;
        stageText.style.fontFamily = token?.font_name || 'Anton';
        stageText.style.fontWeight = token?.bold === false ? '400' : '800';
        stageText.style.color = baseColor;
        if (token?.box) {
            stageText.style.background = token.box_color || '#000000';
            stageText.style.padding = '2px 8px';
        } else {
            stageText.style.background = 'transparent';
            stageText.style.padding = '0';
        }
    }
    subStage?.querySelectorAll('.stage-w').forEach(w => {
        if (w.classList.contains('active-word')) {
            w.style.color = highlight;
            w.style.textShadow = glow;
        } else {
            w.style.color = baseColor;
            w.style.textShadow = 'none';
        }
    });

    const subOverlay = document.getElementById('mockup-sub-overlay');
    if (subOverlay) {
        const posClass = Array.from(subOverlay.classList).find(c => c.startsWith('sub-pos-')) || 'sub-pos-middle';
        subOverlay.className = `mockup-subtitle-overlay preset-${preset} ${posClass}`;
        subOverlay.style.color = baseColor;
        const hi = subOverlay.querySelector('.sub-word-highlight');
        if (hi) {
            hi.style.color = highlight;
            hi.style.textShadow = token?.glow ? `0 0 12px ${highlight}` : 'none';
            hi.style.background = token?.box ? (token.box_color || '#000000') : 'transparent';
            hi.style.padding = token?.box ? '2px 6px' : '0';
        }
    }
}

restoreSubtitleLabSettings();
updateSubtitleSimulator();
loadSubtitleStyleTokens();

subRangeSize?.addEventListener('input', () => {
    updateSubtitleSimulator();
    saveSubtitleLabSettings();
});
subRangeY?.addEventListener('input', () => {
    updateSubtitleSimulator();
    saveSubtitleLabSettings();
});

document.querySelectorAll('.preset-card').forEach(card => {
    card.addEventListener('click', () => {
        document.querySelectorAll('.preset-card').forEach(c => c.classList.remove('active'));
        card.classList.add('active');
        const p = card.getAttribute('data-preset');
        if (selectSubPreset) selectSubPreset.value = p;
        updateSubtitleSimulator();
        saveSubtitleLabSettings();
        showToast(`🎨 '${card.querySelector('h4')?.textContent || p}' altyazı stili seçildi!`);
    });
});

selectSubPreset?.addEventListener('change', () => {
    document.querySelectorAll('.preset-card').forEach(c => {
        c.classList.toggle('active', c.getAttribute('data-preset') === selectSubPreset.value);
    });
    updateSubtitleSimulator();
    saveSubtitleLabSettings();
});

let subtitleAnimationInterval = null;
document.getElementById('btn-test-sub-animation')?.addEventListener('click', () => {
    const words = subStage?.querySelectorAll('.stage-w');
    if (!words?.length) return;
    clearInterval(subtitleAnimationInterval);
    let idx = 0;
    const advance = () => {
        words.forEach(w => w.classList.remove('active-word'));
        if (idx < words.length) {
            words[idx].classList.add('active-word');
            updateSubtitleSimulator();
            idx++;
        } else {
            clearInterval(subtitleAnimationInterval);
            subtitleAnimationInterval = null;
            words[Math.min(1, words.length - 1)].classList.add('active-word');
            updateSubtitleSimulator();
        }
    };
    advance();
    subtitleAnimationInterval = setInterval(advance, 400);
});

// 7. SES EFEKTLERİ (SFX) SENTEZLEYİCİ & DİNLEME (Item 48)
// ══════════════════════════════════════════════════════════════
function playSyntheticSound(type) {
    try {
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain);
        gain.connect(ctx.destination);

        if (type === 'whoosh') {
            osc.type = 'sine';
            osc.frequency.setValueAtTime(200, ctx.currentTime);
            osc.frequency.exponentialRampToValueAtTime(800, ctx.currentTime + 0.15);
            gain.gain.setValueAtTime(0.3, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.25);
            osc.start();
            osc.stop(ctx.currentTime + 0.25);
        } else if (type === 'pop') {
            osc.type = 'triangle';
            osc.frequency.setValueAtTime(800, ctx.currentTime);
            osc.frequency.exponentialRampToValueAtTime(120, ctx.currentTime + 0.08);
            gain.gain.setValueAtTime(0.4, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.1);
            osc.start();
            osc.stop(ctx.currentTime + 0.1);
        } else if (type === 'ding') {
            osc.type = 'sine';
            osc.frequency.setValueAtTime(1800, ctx.currentTime);
            gain.gain.setValueAtTime(0.4, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.4);
            osc.start();
            osc.stop(ctx.currentTime + 0.4);
        }
    } catch (e) {
        console.error("Audio error:", e);
    }
}

document.getElementById('btn-play-whoosh')?.addEventListener('click', () => playSyntheticSound('whoosh'));
document.getElementById('btn-play-pop')?.addEventListener('click', () => playSyntheticSound('pop'));
document.getElementById('btn-play-ding')?.addEventListener('click', () => playSyntheticSound('ding'));

// TTS SES KATALOĞU VE KONTROLLER
// ══════════════════════════════════════════════════════════════
function genderLabel(g) {
    return g === 'female' ? 'Kadın' : 'Erkek';
}

function findVoiceMeta(voiceId) {
    if (!voiceId || voiceId === 'auto') return null;
    const pools = [
        ...(ttsVoiceCatalog.tr || []),
        ...(ttsVoiceCatalog.en || []),
        ...(ttsVoiceCatalog.elevenlabs || []),
        ...(ttsVoiceCatalog.local || []),
        ...LOCAL_OFFLINE_VOICES,
    ];
    return pools.find(v => v.id === voiceId) || null;
}

function appendEdgeVoiceGroup(selectEl, label, voices) {
    if (!voices.length) return;
    const group = document.createElement('optgroup');
    group.label = label;
    voices.forEach(v => {
        const opt = document.createElement('option');
        opt.value = v.id;
        const nativeTag = v.native ? '' : ' · çok dilli';
        opt.textContent = `${v.label} (${genderLabel(v.gender)}, ${v.quality}${nativeTag})`;
        group.appendChild(opt);
    });
    selectEl.appendChild(group);
}

function savedTtsVoicePreference() {
    try { return localStorage.getItem(TTS_VOICE_STORAGE_KEY) || ''; } catch (e) { return ''; }
}

function persistTtsVoicePreference(voiceId) {
    try {
        if (voiceId && voiceId !== 'auto') localStorage.setItem(TTS_VOICE_STORAGE_KEY, voiceId);
        else localStorage.removeItem(TTS_VOICE_STORAGE_KEY);
    } catch (e) {}
}

function populateTtsVoiceSelect(lang) {
    if (!selectTtsVoice) return;
    const targetLang = lang === 'en' ? 'en' : 'tr';
    const prev = selectTtsVoice.value !== 'auto' ? selectTtsVoice.value : savedTtsVoicePreference();
    const trVoices = (ttsVoiceCatalog.tr && ttsVoiceCatalog.tr.length) ? ttsVoiceCatalog.tr : STATIC_TTS_FALLBACK.tr;
    const enVoices = (ttsVoiceCatalog.en && ttsVoiceCatalog.en.length) ? ttsVoiceCatalog.en : STATIC_TTS_FALLBACK.en;
    const elevenVoices = ttsVoiceCatalog.elevenlabs || [];
    const elevenMeta = ttsVoiceCatalog.elevenlabs_meta || {};

    selectTtsVoice.innerHTML = '<option value="auto">Otomatik (konu / nişe göre)</option>';
    const localVoices = LOCAL_OFFLINE_VOICES.slice();
    (ttsVoiceCatalog.local || []).forEach((voice) => {
        if (!localVoices.some((row) => row.id === voice.id)) localVoices.push(voice);
    });
    appendEdgeVoiceGroup(selectTtsVoice, 'Yerel (çevrimdışı)', localVoices);
    appendEdgeVoiceGroup(
        selectTtsVoice,
        targetLang === 'en' ? 'English Edge' : 'Türkçe Edge',
        targetLang === 'en' ? enVoices : trVoices,
    );

    if (elevenVoices.length) {
        const group = document.createElement('optgroup');
        group.label = 'ElevenLabs';
        elevenVoices.forEach(v => {
            const opt = document.createElement('option');
            opt.value = v.id;
            opt.textContent = `${v.label} (${genderLabel(v.gender)}, ${v.quality})`;
            group.appendChild(opt);
        });
        selectTtsVoice.appendChild(group);
    } else if (elevenMeta.configured && elevenMeta.error) {
        const group = document.createElement('optgroup');
        group.label = 'ElevenLabs';
        group.disabled = true;
        const opt = document.createElement('option');
        opt.disabled = true;
        opt.value = '';
        opt.textContent = `${elevenMeta.error} — Ayarlar'dan düzeltin`;
        group.appendChild(opt);
        selectTtsVoice.appendChild(group);
    }

    const savedSettings = restoreStudioSettings();
    const options = [...selectTtsVoice.options];
    const preferredVoice = [prev, savedSettings?.ttsVoice].find(
        voice => voice && options.some(option => option.value === voice),
    );
    if (preferredVoice) {
        selectTtsVoice.value = preferredVoice;
    } else {
        selectTtsVoice.value = 'auto';
    }
}

selectTtsVoice?.addEventListener('change', () => {
    persistTtsVoicePreference(selectTtsVoice.value);
    saveStudioSettings();
});

function renderElevenlabsQuota(info) {
    const strip = document.getElementById('elevenlabs-quota-strip');
    if (!strip) return;
    if (!info?.configured) {
        strip.style.display = 'none';
        return;
    }
    strip.style.display = 'block';
    const q = info.quota || {};
    if (q.character_remaining != null) {
        strip.innerHTML = `<i class="fa-solid fa-chart-simple text-info"></i> ElevenLabs: <strong>${q.character_remaining}</strong> / ${q.character_limit || '?'} karakter kaldı (${q.tier || 'free'})`;
    } else if (q.error) {
        strip.textContent = 'ElevenLabs kota bilgisi alınamadı.';
    } else {
        strip.textContent = 'ElevenLabs bağlı — kota yükleniyor…';
    }
}

async function loadTtsVoiceCatalog(forceRefresh = false) {
    populateTtsVoiceSelect(selectLanguage?.value || 'tr');
    try {
        const voicesRes = await fetch(forceRefresh ? '/api/tts/voices?refresh=true' : '/api/tts/voices');
        if (voicesRes.ok) {
            const catalog = await voicesRes.json();
            if (catalog.tr || catalog.en || catalog.elevenlabs || catalog.elevenlabs_meta) {
                ttsVoiceCatalog = {
                    tr: catalog.tr || STATIC_TTS_FALLBACK.tr,
                    en: catalog.en || STATIC_TTS_FALLBACK.en,
                    elevenlabs: catalog.elevenlabs || [],
                    elevenlabs_meta: catalog.elevenlabs_meta || {},
                    local: catalog.local || LOCAL_OFFLINE_VOICES,
                };
            }
            elevenlabsConfigured = !!(catalog.elevenlabs_meta?.configured || (catalog.elevenlabs || []).length);
        } else {
            showToast('TTS ses listesi sunucudan alınamadı — yerel Edge listesi kullanılıyor.', 'warning');
        }
        populateTtsVoiceSelect(selectLanguage?.value || 'tr');
        if (!forceRefresh) {
            const cfgRes = await fetch('/api/config');
            if (cfgRes.ok) {
                const data = await cfgRes.json();
                elevenlabsConfigured = !!(data.keys?.elevenlabs || data.elevenlabs?.configured);
                if (data.elevenlabs) renderElevenlabsQuota(data.elevenlabs);
                if (data.gameplay_categories && selectGameplayCategory) {
                    selectGameplayCategory.innerHTML = (data.gameplay_categories || []).map(c =>
                        `<option value="${c.id}">${c.label}</option>`
                    ).join('');
                    const savedGc = restoreStudioSettings()?.gameplayCategory;
                    if (savedGc && [...selectGameplayCategory.options].some(o => o.value === savedGc)) {
                        selectGameplayCategory.value = savedGc;
                    }
                }
            }
        }
    } catch (e) {
        console.warn('TTS voice catalog load failed', e);
        populateTtsVoiceSelect(selectLanguage?.value || 'tr');
        showToast('TTS ses kataloğu yüklenemedi — yerel Edge listesi aktif.', 'warning');
    }
}

selectLanguage?.addEventListener('change', () => populateTtsVoiceSelect(selectLanguage.value));

function bindTwinCheckbox(primaryId, twinId) {
    const primary = document.getElementById(primaryId);
    const twin = document.getElementById(twinId);
    if (!primary || !twin || primary.dataset.twinBound === '1') return;
    primary.dataset.twinBound = '1';
    const push = (source, dest) => {
        dest.checked = source.checked;
        if (typeof saveStudioSettings === 'function') saveStudioSettings();
    };
    primary.addEventListener('change', () => push(primary, twin));
    twin.addEventListener('change', () => push(twin, primary));
}

bindTwinCheckbox('chk-enable-bgm', 'audio-chk-enable-bgm');
bindTwinCheckbox('chk-enable-outro', 'audio-chk-enable-outro');
bindTwinCheckbox('chk-intro-whoosh', 'audio-chk-intro-whoosh');

chkSplitScreen?.addEventListener('change', (ev) => {
    if (ev && ev.isTrusted) {
        splitTouched = true;
        if (!chkSplitScreen.checked && selectGameplayCategory) {
            selectGameplayCategory.value = 'auto';
        }
    }
    if (gameplayCategoryWrap) {
        gameplayCategoryWrap.style.display = chkSplitScreen.checked ? 'block' : 'none';
    }
    if (btnSplitMode) {
        btnSplitMode.classList.toggle('active', chkSplitScreen.checked);
        const span = btnSplitMode.querySelector('span');
        if (span) span.textContent = chkSplitScreen.checked ? 'Split-Screen: AÇIK' : 'Split-Screen Modunu Aç';
    }
});
