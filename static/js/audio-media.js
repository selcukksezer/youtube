/**
 * ShortsAI Studio — Audio, TTS, SFX & Subtitle Lab (audio-media.js)
 * Covers Subtitle lab presets, SFX synthetic sound effects, BGM library & custom upload, and Edge/ElevenLabs TTS voice catalog.
 */

const TTS_VOICE_STORAGE_KEY = 'shortsTtsVoice';


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


// ══════════════════════════════════════════════════════════════
// 6. ALTYAZI PRESET SEÇİCİ & ANİMASYON TESTİ (Items 42 & 43)
// ══════════════════════════════════════════════════════════════
const SUBTITLE_LAB_KEY = 'subtitleLabSettings';
const SUBTITLE_LAB_COLORS = {
    capcut_yellow: { highlight: '#FFD700', glow: '0 0 15px #FFD700' },
    cyber_green: { highlight: '#00FF66', glow: '0 0 15px #00FF66' },
    red_fire: { highlight: '#FF3333', glow: '0 0 15px #FF3333' },
    clean_white: { highlight: '#00D4FF', glow: '0 0 15px #00D4FF' },
};
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
    const colors = SUBTITLE_LAB_COLORS[preset] || SUBTITLE_LAB_COLORS.capcut_yellow;
    const fontSize = parseInt(subRangeSize?.value || '54', 10);
    const yPct = parseFloat(subRangeY?.value || '0.8');

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
    }
    subStage?.querySelectorAll('.stage-w').forEach(w => {
        if (w.classList.contains('active-word')) {
            w.style.color = colors.highlight;
            w.style.textShadow = colors.glow;
        } else {
            w.style.color = '#FFFFFF';
            w.style.textShadow = 'none';
        }
    });

    const subOverlay = document.getElementById('mockup-sub-overlay');
    if (subOverlay) {
        subOverlay.className = `mockup-subtitle-overlay preset-${preset}`;
    }
}

restoreSubtitleLabSettings();
updateSubtitleSimulator();

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
        selectSubPreset.value = p;
        updateSubtitleSimulator();
        saveSubtitleLabSettings();
        showToast(`🎨 '${card.querySelector('h4').textContent}' altyazı stili seçildi!`);
    });
});

selectSubPreset?.addEventListener('change', () => {
    document.querySelectorAll('.preset-card').forEach(c => {
        c.classList.toggle('active', c.getAttribute('data-preset') === selectSubPreset.value);
    });
    updateSubtitleSimulator();
    saveSubtitleLabSettings();
});

document.getElementById('btn-test-sub-animation')?.addEventListener('click', () => {
    const words = document.querySelectorAll('.stage-w');
    let idx = 0;
    const interval = setInterval(() => {
        words.forEach(w => w.classList.remove('active-word'));
        if (idx < words.length) {
            words[idx].classList.add('active-word');
            updateSubtitleSimulator();
            idx++;
        } else {
            clearInterval(interval);
            words[1].classList.add('active-word');
            updateSubtitleSimulator();
        }
    }, 400);
});



// ══════════════════════════════════════════════════════════════
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

// ══════════════════════════════════════════════════════════════


// 8. BGM MÜZİK LİSTESİ + ÖZEL YÜKLEME (P3-32)
// ══════════════════════════════════════════════════════════════
document.getElementById('btn-bgm-upload')?.addEventListener('click', () => {
    document.getElementById('input-bgm-upload')?.click();
});

document.getElementById('input-bgm-upload')?.addEventListener('change', async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const status = document.getElementById('bgm-upload-status');
    const form = new FormData();
    form.append('file', file);
    try {
        if (status) status.textContent = 'Yükleniyor...';
        const res = await fetch('/api/bgm/upload', { method: 'POST', body: form });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(data.detail || 'Yükleme başarısız');
        if (status) status.textContent = `✓ ${data.filename}`;
        showToast(`BGM yüklendi: ${data.filename}`);
        await loadBgmList();
        const sel = document.getElementById('select-bgm-track');
        const studioSel = document.getElementById('studio-bgm-track');
        if (sel) sel.value = data.filename;
        if (studioSel) studioSel.value = data.filename;
    } catch (err) {
        if (status) status.textContent = `Hata: ${err.message}`;
        showToast(`BGM yükleme hatası: ${err.message}`, 'error');
    }
    e.target.value = '';
});

async function loadBgmList() {
    const select = document.getElementById('select-bgm-track');
    const studioSelect = document.getElementById('studio-bgm-track');
    const audioStatus = document.getElementById('audio-pipeline-status');
    const mediaStatus = document.getElementById('media-compliance-status');
    if (!select && !studioSelect) return;
    try {
        const res = await fetch('/api/bgm/list?include_catalog=true');
        const data = await res.json();
        const detailed = data.tracks_detailed || (data.tracks || []).map(f => ({ filename: f, display: f }));
        const fill = (el) => {
            if (!el) return;
            const prev = el.value;
            el.innerHTML = '<option value="">Otomatik / yok</option>';
            detailed.forEach(t => {
                const fn = t.filename || t;
                const opt = document.createElement('option');
                opt.value = fn;
                const label = t.display || fn;
                opt.textContent = t.downloaded === false ? `${label} (indirilecek)` : label;
                el.appendChild(opt);
            });
            const savedBgm = restoreStudioSettings()?.bgmTrack;
            const candidate = prev || savedBgm;
            if (candidate && [...el.options].some(o => o.value === candidate)) el.value = candidate;
            else if (detailed.some(t => (t.filename || t) === 'royalty_free_ambient.wav')) el.value = 'royalty_free_ambient.wav';
        };
        fill(select);
        fill(studioSelect);
        if (select && studioSelect && !select._bgmSyncBound) {
            select._bgmSyncBound = true;
            select.addEventListener('change', () => { studioSelect.value = select.value; });
            studioSelect.addEventListener('change', () => { select.value = studioSelect.value; });
        }
        const duckAudio = document.getElementById('range-ducking-vol');
        const duckStudio = document.getElementById('studio-ducking-vol');
        if (duckAudio && duckStudio && !duckAudio._duckSyncBound) {
            duckAudio._duckSyncBound = true;
            duckAudio.addEventListener('input', () => { duckStudio.value = duckAudio.value; });
            duckStudio.addEventListener('input', () => { duckAudio.value = duckStudio.value; });
        }
        if (audioStatus) {
            const catalogCount = detailed.length || 0;
            audioStatus.innerHTML = `
                <div class="stat-pill"><span>135 Telifsiz BGM:</span><strong class="text-success">${catalogCount ? catalogCount + ' parça' : 'Sentezleniyor'}</strong></div>
                <div class="stat-pill mt-2"><span>141 Nefes Katmanı:</span><strong class="text-success">8 sn aralıklı</strong></div>
                <div class="stat-pill mt-2"><span>144 Voice Ducking:</span><strong class="text-primary">80 ms iniş / 200 ms dönüş</strong></div>
                <div class="stat-pill mt-2"><span>145 Oda Ambiyansı:</span><strong class="text-primary">Hafif, -34 dB</strong></div>
            `;
        }
        if (mediaStatus) {
            mediaStatus.innerHTML = `
                <div class="stat-pill"><span>136 Matematiksel SFX:</span><strong class="text-success">Sinüs / Kare Dalga</strong></div>
                <div class="stat-pill mt-2"><span>137 Döngü Bağlaçları:</span><strong class="text-success">12 varyasyon</strong></div>
                <div class="stat-pill mt-2"><span>138 Neon İlerleme:</span><strong class="text-success">Renderda aktif</strong></div>
                <div class="stat-pill mt-2"><span>139 Arka Plan Dilimleme:</span><strong class="text-success">Rastgele başlangıç</strong></div>
                <div class="stat-pill mt-2"><span>140 Yasal Bildirim:</span><strong class="text-success">SEO açıklamasına eklenir</strong></div>
                <div class="stat-pill mt-2"><span>142 Konuşma Prosodisi:</span><strong class="text-primary">Kanca / soru ritmi</strong></div>
                <div class="stat-pill mt-2"><span>143 Diyalog Sesleri:</span><strong class="text-primary">Konuşmacı bazlı</strong></div>
            `;
        }
    } catch (e) {
        console.error(e);
    }
}



function genderLabel(g) {
    return g === 'female' ? 'Kadın' : 'Erkek';
}

function findVoiceMeta(voiceId) {
    if (!voiceId || voiceId === 'auto') return null;
    const pools = [
        ...(ttsVoiceCatalog.tr || []),
        ...(ttsVoiceCatalog.en || []),
        ...(ttsVoiceCatalog.elevenlabs || []),
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

function populateTtsVoiceSelect(_lang) {
    if (!selectTtsVoice) return;
    const prev = selectTtsVoice.value !== 'auto' ? selectTtsVoice.value : savedTtsVoicePreference();
    const trVoices = (ttsVoiceCatalog.tr && ttsVoiceCatalog.tr.length) ? ttsVoiceCatalog.tr : STATIC_TTS_FALLBACK.tr;
    const enVoices = (ttsVoiceCatalog.en && ttsVoiceCatalog.en.length) ? ttsVoiceCatalog.en : STATIC_TTS_FALLBACK.en;
    const elevenVoices = ttsVoiceCatalog.elevenlabs || [];
    const elevenMeta = ttsVoiceCatalog.elevenlabs_meta || {};

    selectTtsVoice.innerHTML = '<option value="auto">Otomatik (konu / nişe göre)</option>';
    appendEdgeVoiceGroup(selectTtsVoice, 'Türkçe Edge', trVoices);
    appendEdgeVoiceGroup(selectTtsVoice, 'English Edge', enVoices);

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
    const preferredVoice = prev || savedSettings?.ttsVoice;
    if (preferredVoice && [...selectTtsVoice.options].some(o => o.value === preferredVoice)) {
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


