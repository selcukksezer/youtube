/**
 * Shorts Studio — Step 02 Enhancements (studio-wizard-step2.js)
 * Implements Category C (Items 21–30): Seslendirme, Müzik & Senaryo Deneyimi (Adım 02)
 */
(function () {
    const VOICE_TUNING_KEY = 'shorts_voice_tuning_v1';
    const SCRIPT_VERSIONS_KEY = 'shorts_script_versions_v1';

    const QUICK_VOICE_CARDS = {
        tr: [
            { id: 'tr-TR-AhmetNeural', name: 'Ahmet', role: 'Derin & Belgesel', badge: 'Popüler TR', gender: 'male' },
            { id: 'tr-TR-EmelNeural', name: 'Emel', role: 'Enerjik & Net', badge: 'Yüksek Dikkat', gender: 'female' },
            { id: 'en-US-AndrewMultilingualNeural', name: 'Andrew', role: 'Sinematik Çok Dilli', badge: 'Viral Ton', gender: 'male' },
            { id: 'en-US-AvaMultilingualNeural', name: 'Ava', role: 'Modern & Akıcı', badge: 'Hikâye', gender: 'female' },
            { id: 'local:piper-tr', name: 'Piper TR', role: 'Yerel Çevrimdışı', badge: '0 Kota', gender: 'male' }
        ],
        en: [
            { id: 'en-US-AndrewNeural', name: 'Andrew (US)', role: 'Deep Documentary', badge: 'Top Tier-1', gender: 'male' },
            { id: 'en-US-AriaNeural', name: 'Aria (US)', role: 'Dynamic Storyteller', badge: 'High CTR', gender: 'female' },
            { id: 'en-US-GuyNeural', name: 'Guy (US)', role: 'Fast Viral Hook', badge: 'Shorts Pro', gender: 'male' },
            { id: 'en-GB-RyanNeural', name: 'Ryan (UK)', role: 'British Authority', badge: 'Stoic/History', gender: 'male' },
            { id: 'en-US-JennyNeural', name: 'Jenny (US)', role: 'Warm & Clear', badge: 'Facts/Psych', gender: 'female' }
        ]
    };

    const TONE_PRESETS = [
        { id: 'documentary', label: '🎙️ Belgesel', speed: 1.05, desc: 'Dengeli ve merak uyandırıcı vurgu' },
        { id: 'viral_hype', label: '⚡ Viral Hype', speed: 1.15, desc: 'Hızlı, yüksek enerjili Shorts ritmi' },
        { id: 'authoritative', label: '🏛️ Otoriter', speed: 0.95, desc: 'Ağırbaşlı Stoa ve tarih anlatımı' },
        { id: 'mysterious', label: '🤫 Gizemli', speed: 1.00, desc: 'Gerilim ve merak boşluğu odaklı' }
    ];

    const DEMONETIZATION_RISK_MAP = {
        'intihar': 'trajik veda', 'öldürdü': 'etkisiz hale getirdi', 'öldürmek': 'ortadan kaldırmak',
        'cinayet': 'karanlık olay', 'vahşet': 'çarpıcı olay', 'işkence': 'ağır sınav', 'kanlı': 'çarpıcı',
        'katliam': 'büyük yıkım', 'terör': 'kaos', 'uyuşturucu': 'zararlı madde', 'kumar': 'yüksek riskli oyun',
        'bahis': 'riskli tahmin', 'garanti kazanç': 'yüksek potansiyel', 'kesin zengin': 'finansal özgürlük',
        'bomba': 'büyük patlama', 'suicide': 'tragic end', 'murder': 'dark mystery', 'kill': 'eliminate',
        'torture': 'extreme ordeal', 'gambling': 'high-stakes risk'
    };

    function loadVoiceTuning() {
        try { return JSON.parse(localStorage.getItem(VOICE_TUNING_KEY) || 'null') || { speed: 1.05, tone: 'documentary' }; }
        catch (e) { return { speed: 1.05, tone: 'documentary' }; }
    }
    function saveVoiceTuning(tuning) {
        try { localStorage.setItem(VOICE_TUNING_KEY, JSON.stringify(tuning)); } catch (e) {}
    }
    function loadScriptVersionsMap() {
        try { return JSON.parse(localStorage.getItem(SCRIPT_VERSIONS_KEY) || '{}') || {}; }
        catch (e) { return {}; }
    }
    function saveScriptVersionsMap(map) {
        try { localStorage.setItem(SCRIPT_VERSIONS_KEY, JSON.stringify(map)); } catch (e) {}
    }
    function getTopicKey(plan) {
        const raw = (plan?.title || plan?.topic || plan?.keyword || document.getElementById('input-topic')?.value || 'default').trim().toLowerCase();
        return raw.slice(0, 80) || 'default';
    }
    function countWords(text) {
        return String(text || '').trim().split(/\s+/).filter(Boolean).length;
    }

    function recordScriptVersionIfNeeded(plan) {
        if (!plan || !Array.isArray(plan.scenes) || !plan.scenes.length) return [];
        const key = getTopicKey(plan);
        const map = loadScriptVersionsMap();
        const list = Array.isArray(map[key]) ? map[key] : [];
        const sig = plan.scenes.map((s) => (s.narration || '').trim()).join('||');
        if (!sig) return list;
        if (!list.some((v) => v.sig === sig)) {
            const totalSec = +plan.scenes.reduce((acc, s) => acc + (parseFloat(s.duration) || 3.5), 0).toFixed(1);
            list.push({
                ver: list.length + 1, sig, totalSec,
                savedAt: new Date().toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' }),
                scenes: JSON.parse(JSON.stringify(plan.scenes))
            });
            while (list.length > 5) list.shift();
            list.forEach((item, idx) => { item.ver = idx + 1; });
            map[key] = list;
            saveScriptVersionsMap(map);
        }
        return list;
    }

    function scanDemonetizationRisks(scenes) {
        const hits = [];
        const terms = Object.keys(DEMONETIZATION_RISK_MAP);
        (scenes || []).forEach((sc, idx) => {
            const lower = String(sc.narration || '').toLowerCase();
            terms.forEach((term) => {
                if (lower.includes(term)) hits.push({ sceneIdx: idx, term, replacement: DEMONETIZATION_RISK_MAP[term] });
            });
        });
        return hits;
    }

    function injectStep2VoiceEnhancements() {
        const voiceSelect = document.getElementById('select-tts-voice');
        const voiceField = voiceSelect?.closest('.form-field');
        if (!voiceField || document.getElementById('wiz-voice-quick-cards')) return;

        const cardsWrap = document.createElement('div');
        cardsWrap.id = 'wiz-voice-quick-cards';
        cardsWrap.className = 'wiz-voice-quick-cards';
        voiceField.appendChild(cardsWrap);

        const tuning = loadVoiceTuning();
        const speedToneBar = document.createElement('div');
        speedToneBar.id = 'wiz-voice-speed-tone-bar';
        speedToneBar.className = 'wiz-voice-speed-tone-bar';
        speedToneBar.innerHTML = `
            <div class="wiz-speed-col">
                <div class="wiz-speed-head">
                    <span><i class="fa-solid fa-gauge-high text-info"></i> Konuşma Hızı</span>
                    <strong id="wiz-voice-speed-val">${Number(tuning.speed || 1.05).toFixed(2)}x · İdeal Shorts</strong>
                </div>
                <input type="range" id="wiz-voice-speed-range" min="0.90" max="1.25" step="0.05" value="${Number(tuning.speed || 1.05).toFixed(2)}">
            </div>
            <div class="wiz-tone-col">
                <span class="wiz-tone-label"><i class="fa-solid fa-sliders text-warning"></i> Anlatım Vurgusu & Ton:</span>
                <div class="wiz-tone-pills" id="wiz-tone-pills">
                    ${TONE_PRESETS.map((t) => `<button type="button" class="wiz-tone-pill${t.id === tuning.tone ? ' active' : ''}" data-tone="${t.id}" data-speed="${t.speed}" title="${t.desc}">${t.label}</button>`).join('')}
                </div>
            </div>
        `;
        voiceField.appendChild(speedToneBar);

        const speedRange = document.getElementById('wiz-voice-speed-range');
        const speedValEl = document.getElementById('wiz-voice-speed-val');
        const updateSpeedUi = (val) => {
            const num = Math.max(0.9, Math.min(1.25, parseFloat(val) || 1.05));
            const tag = num >= 1.15 ? 'Hızlı Viral' : num <= 0.95 ? 'Ağır Belgesel' : 'İdeal Shorts';
            if (speedValEl) speedValEl.textContent = `${num.toFixed(2)}x · ${tag}`;
            const cur = loadVoiceTuning();
            cur.speed = num;
            saveVoiceTuning(cur);
        };
        speedRange?.addEventListener('input', (e) => updateSpeedUi(e.target.value));

        document.getElementById('wiz-tone-pills')?.addEventListener('click', (e) => {
            const pill = e.target.closest('.wiz-tone-pill[data-tone]');
            if (!pill) return;
            document.querySelectorAll('#wiz-tone-pills .wiz-tone-pill').forEach((p) => p.classList.remove('active'));
            pill.classList.add('active');
            const recSpeed = parseFloat(pill.getAttribute('data-speed') || '1.05');
            if (speedRange) speedRange.value = recSpeed.toFixed(2);
            const cur = loadVoiceTuning();
            cur.tone = pill.getAttribute('data-tone');
            cur.speed = recSpeed;
            saveVoiceTuning(cur);
            updateSpeedUi(recSpeed);
            if (typeof showToast === 'function') showToast(`Ses tonu "${pill.textContent.trim()}" (${recSpeed.toFixed(2)}x) olarak ayarlandı.`);
        });

        renderVoiceQuickCards();
        voiceSelect?.addEventListener('change', renderVoiceQuickCards);
        document.getElementById('select-language')?.addEventListener('change', () => setTimeout(renderVoiceQuickCards, 60));
    }

    function selectVoiceOption(voiceSelect, vid) {
        if (!vid || !voiceSelect) return;
        if (![...voiceSelect.options].some((o) => o.value === vid)) {
            const opt = document.createElement('option');
            opt.value = vid; opt.textContent = vid;
            voiceSelect.appendChild(opt);
        }
        voiceSelect.value = vid;
        voiceSelect.dispatchEvent(new Event('change', { bubbles: true }));
        renderVoiceQuickCards();
    }

    function renderVoiceQuickCards() {
        const wrap = document.getElementById('wiz-voice-quick-cards');
        const voiceSelect = document.getElementById('select-tts-voice');
        if (!wrap || !voiceSelect) return;
        const lang = (document.getElementById('select-language')?.value || 'tr') === 'en' ? 'en' : 'tr';
        const list = QUICK_VOICE_CARDS[lang] || QUICK_VOICE_CARDS.tr;
        const activeVal = voiceSelect.value || 'auto';

        wrap.innerHTML = list.map((v) => `
            <div class="wiz-voice-card${activeVal === v.id ? ' is-selected' : ''}" data-voice-id="${v.id}">
                <div class="wiz-voice-card-main" data-select-voice="${v.id}">
                    <div class="wiz-voice-card-top"><strong>${v.name}</strong><span class="wiz-voice-badge">${v.badge}</span></div>
                    <span class="wiz-voice-role">${v.role}</span>
                </div>
                <button type="button" class="wiz-voice-play-btn" data-preview-voice="${v.id}" data-gender="${v.gender}" title="${v.name} sesini 3 saniye dinle">
                    <i class="fa-solid fa-play"></i> <span>Dinle</span>
                </button>
            </div>
        `).join('');

        wrap.querySelectorAll('[data-select-voice]').forEach((el) => {
            el.addEventListener('click', () => selectVoiceOption(voiceSelect, el.getAttribute('data-select-voice')));
        });
        wrap.querySelectorAll('[data-preview-voice]').forEach((btn) => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const vid = btn.getAttribute('data-preview-voice');
                selectVoiceOption(voiceSelect, vid);
                await playQuickVoicePreview(vid, btn.getAttribute('data-gender') || 'male', btn);
            });
        });
    }

    async function playQuickVoicePreview(voiceId, gender, btnEl) {
        const topic = document.getElementById('input-topic')?.value?.trim();
        const lang = document.getElementById('select-language')?.value || 'tr';
        const sample = topic ? topic.split(/\s+/).slice(0, 10).join(' ') : (lang === 'en' ? 'This 3 second hook will change how you think.' : 'Bu üç saniyelik kanca tüm bakış açınızı değiştirecek.');
        const origHtml = btnEl?.innerHTML;
        if (btnEl) { btnEl.disabled = true; btnEl.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>'; }
        try {
            const res = await fetch('/api/tts/preview', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: sample, voice_gender: gender, tts_voice: voiceId === 'auto' ? null : voiceId, language: lang })
            });
            if (!res.ok) throw new Error('TTS servisi meşgul');
            const url = URL.createObjectURL(await res.blob());
            const audio = new Audio(url);
            audio.playbackRate = Math.max(0.85, Math.min(1.3, parseFloat(loadVoiceTuning().speed) || 1.05));
            audio.onended = () => URL.revokeObjectURL(url);
            await audio.play();
            if (typeof showToast === 'function') showToast(`🔊 ${voiceId} (${audio.playbackRate.toFixed(2)}x) çalınıyor`);
        } catch (err) {
            if (typeof playSyntheticSound === 'function') playSyntheticSound('ding');
            if (typeof showToast === 'function') showToast(`Önizleme sesi seçildi: ${voiceId}`, 'info');
        } finally {
            if (btnEl) { btnEl.disabled = false; btnEl.innerHTML = origHtml || '<i class="fa-solid fa-play"></i> <span>Dinle</span>'; }
        }
    }

    function injectManuscriptDropzone() {
        const body = document.getElementById('manuscript-import')?.querySelector('.series-planner__body');
        const textarea = document.getElementById('input-manuscript');
        if (!body || !textarea || document.getElementById('wiz-manuscript-dropzone')) return;

        const dropzone = document.createElement('div');
        dropzone.id = 'wiz-manuscript-dropzone';
        dropzone.className = 'wiz-manuscript-dropzone';
        dropzone.innerHTML = `
            <i class="fa-solid fa-file-arrow-up"></i>
            <div><strong>.TXT, .SRT veya .MD Dosyası Sürükleyin</strong><span>veya bilgisayarınızdan hazır metin/altyazı seçmek için tıklayın</span></div>
            <input type="file" id="wiz-manuscript-file-input" accept=".txt,.srt,.md,text/plain" class="hidden">
        `;
        body.insertBefore(dropzone, textarea);

        const fileInput = dropzone.querySelector('#wiz-manuscript-file-input');
        const handleFile = (file) => {
            if (!file) return;
            const reader = new FileReader();
            reader.onload = () => {
                let text = String(reader.result || '');
                if (/\.srt$/i.test(file.name) || /\d{2}:\d{2}:\d{2}[,.]\d{3}\s*-->/.test(text)) {
                    text = text.replace(/^\d+\s*$/gm, '').replace(/\d{2}:\d{2}:\d{2}[,.]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[,.]\d{3}.*$/gm, '').replace(/<[^>]+>/g, '').split(/\r?\n/).map((l) => l.trim()).filter(Boolean).join(' ');
                }
                const cleaned = text.replace(/\s{2,}/g, ' ').trim();
                textarea.value = cleaned.slice(0, 12000);
                textarea.dispatchEvent(new Event('input', { bubbles: true }));
                const wc = countWords(cleaned);
                const status = document.getElementById('manuscript-import-status');
                if (status) status.textContent = `✓ ${file.name} yüklendi (${wc} kelime · ~${Math.max(1, Math.min(24, Math.ceil(wc / 14)))} sahne)`;
                if (typeof showToast === 'function') showToast(`📂 "${file.name}" içe aktarıldı (${wc} kelime).`);
            };
            reader.readAsText(file, 'utf-8');
        };
        dropzone.addEventListener('click', () => fileInput?.click());
        dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.classList.add('is-dragover'); });
        dropzone.addEventListener('dragleave', () => dropzone.classList.remove('is-dragover'));
        dropzone.addEventListener('drop', (e) => { e.preventDefault(); dropzone.classList.remove('is-dragover'); handleFile(e.dataTransfer?.files?.[0]); });
        fileInput?.addEventListener('change', (e) => handleFile(e.target.files?.[0]));
    }

    function enhanceStep2ScriptPreview() {
        const origSync = window.syncWizardStep2Preview;
        if (typeof origSync !== 'function' || origSync._step2Enhanced) return;

        function enhancedSyncWizardStep2Preview() {
            origSync();
            const previewBox = document.getElementById('wizard-inline-script-preview');
            const plan = window.currentPlan;
            const scenes = Array.isArray(plan?.scenes) ? plan.scenes : [];
            if (!previewBox || !scenes.length || typeof isCurrentTopicPlanReady !== 'function' || !isCurrentTopicPlanReady()) return;

            const versions = recordScriptVersionIfNeeded(plan);
            const totalSec = +scenes.reduce((acc, s) => acc + (parseFloat(s.duration) || 3.5), 0).toFixed(1);
            const totalWords = scenes.reduce((acc, s) => acc + countWords(s.narration), 0);
            const currentSig = scenes.map((s) => (s.narration || '').trim()).join('||');
            const pct = Math.max(8, Math.min(100, Math.round((totalSec / 55) * 100)));
            const thermoClass = totalSec < 24 ? 'is-short' : totalSec > 50 ? 'is-long' : 'is-optimal';
            const thermoNote = totalSec < 24 ? 'Kısa Süre (<24 sn) — 1-2 sahne eklenebilir' : totalSec > 50 ? 'Uzun Süre (>50 sn) — Tempo düşebilir' : 'İdeal Shorts Aralığı (28–45 sn) ✓';
            const risks = scanDemonetizationRisks(scenes);

            const versionTabsHtml = versions.map((v) => `<button type="button" class="wiz-ver-tab${v.sig === currentSig ? ' active' : ''}" data-ver-idx="${v.ver - 1}" title="Saat ${v.savedAt} taslağına dön">v${v.ver} <small>${v.totalSec}s</small></button>`).join('');
            const scenesHtml = scenes.map((sc, i) => {
                const dur = (parseFloat(sc.duration) || 3.5).toFixed(1);
                const wc = countWords(sc.narration);
                const isHook = i === 0;
                const isClose = i === scenes.length - 1;
                const sceneRisks = risks.filter((r) => r.sceneIdx === i);
                return `
                    <div class="wiz-inline-scene-row${isHook ? ' wiz-s1-hook-card' : ''}" data-scene-idx="${i}">
                        <div class="wiz-inline-scene-head">
                            <div class="wiz-inline-scene-badges">
                                <span class="wiz-scene-num">S${i + 1}</span>
                                <span class="wiz-scene-role">${isHook ? '🎯 İLK 3 SANİYE — VİRAL KANCA' : isClose ? '🔄 Döngüsel Kapanış' : `⚔️ Sahne ${i + 1}`}</span>
                                <span class="wiz-scene-meta-badge" data-meta-idx="${i}">S${i + 1} · ${dur} sn · ${wc} kelime</span>
                                ${sceneRisks.length ? `<span class="wiz-scene-risk-pill">⚠️ Riskli: ${sceneRisks.map((r) => r.term).join(', ')}</span>` : ''}
                            </div>
                            <div class="wiz-inline-scene-actions">
                                ${isHook ? `<button type="button" class="btn-wiz-alt-hook" id="btn-wiz-alt-hook">✨ Alternatif Kanca</button>` : ''}
                                <button type="button" class="btn-wiz-rewrite-scene" data-rewrite-idx="${i}">↻ Yeniden Yaz</button>
                            </div>
                        </div>
                        <textarea class="wiz-inline-scene-input" data-edit-idx="${i}" rows="2" aria-label="Sahne ${i + 1} seslendirme metni">${String(sc.narration || '').replace(/</g, '&lt;')}</textarea>
                    </div>
                `;
            }).join('');

            previewBox.innerHTML = `
                <div class="wiz-script-ready">
                    <div class="wiz-script-top-bar">
                        <div>
                            <h4 style="margin:0;font-size:13px;">Canlı Senaryo & Kanca Editörü (${scenes.length} Sahne)</h4>
                            <p style="margin:2px 0 0;font-size:11px;color:var(--muted);">Metinlere tıklayarak doğrudan düzenleyin veya tek sahneyi yeniden yazın.</p>
                        </div>
                        <div class="wiz-script-version-tabs" id="wiz-script-version-tabs"><span class="tiny mono">GEÇMİŞ:</span>${versionTabsHtml}</div>
                    </div>
                    <div class="wiz-duration-thermometer ${thermoClass}" id="wiz-duration-thermometer">
                        <div class="wiz-thermo-labels">
                            <strong><i class="fa-solid fa-stopwatch"></i> Toplam: <span id="wiz-thermo-sec">${totalSec}</span> sn · <span id="wiz-thermo-words">${totalWords}</span> kelime</strong>
                            <span id="wiz-thermo-note">${thermoNote}</span>
                        </div>
                        <div class="wiz-thermo-track"><div class="wiz-thermo-fill" id="wiz-thermo-fill" style="width:${pct}%;"></div></div>
                    </div>
                    <div class="wiz-demonetization-guard ${risks.length ? 'has-risk' : 'is-clean'}" id="wiz-demonetization-guard">
                        ${risks.length
                            ? `<span><i class="fa-solid fa-triangle-exclamation"></i> <b>YouTube Reklam Kısıtlaması Uyarısı:</b> <b>${risks.length}</b> riskli ifade (${risks.map((r) => `"${r.term}"`).join(', ')}) bulundu.</span><button type="button" class="btn-wiz-sanitize-risks" id="btn-wiz-sanitize-risks">✨ Güvenli Kelimeyle Yumuşat</button>`
                            : `<span><i class="fa-solid fa-shield-check"></i> <b>Reklam Güvenliği (Ad-Friendly):</b> Yasaklı veya sarı dolar riskli kelime bulunmadı ✓</span>`}
                    </div>
                    <div class="wiz-inline-scenes-list">${scenesHtml}</div>
                </div>
            `;
            bindInlinePreviewEvents(previewBox, versions);
        }
        enhancedSyncWizardStep2Preview._step2Enhanced = true;
        window.syncWizardStep2Preview = enhancedSyncWizardStep2Preview;
    }

    function bindInlinePreviewEvents(previewBox, versions) {
        previewBox.querySelectorAll('.wiz-inline-scene-input').forEach((ta) => {
            ta.addEventListener('input', () => {
                const idx = Number(ta.getAttribute('data-edit-idx'));
                const sc = window.currentPlan?.scenes?.[idx];
                if (!sc) return;
                sc.narration = ta.value;
                const wc = countWords(ta.value);
                sc.duration = Math.max(2.8, Math.min(7.5, +(wc * 0.38).toFixed(1)));
                const badge = previewBox.querySelector(`.wiz-scene-meta-badge[data-meta-idx="${idx}"]`);
                if (badge) badge.textContent = `S${idx + 1} · ${sc.duration.toFixed(1)} sn · ${wc} kelime`;
                const all = window.currentPlan?.scenes || [];
                const totalSec = +all.reduce((acc, s) => acc + (parseFloat(s.duration) || 3.5), 0).toFixed(1);
                const totalWords = all.reduce((acc, s) => acc + countWords(s.narration), 0);
                const secEl = document.getElementById('wiz-thermo-sec');
                const wordsEl = document.getElementById('wiz-thermo-words');
                const fillEl = document.getElementById('wiz-thermo-fill');
                if (secEl) secEl.textContent = String(totalSec);
                if (wordsEl) wordsEl.textContent = String(totalWords);
                if (fillEl) fillEl.style.width = `${Math.max(8, Math.min(100, Math.round((totalSec / 55) * 100)))}%`;
                if (typeof persistCurrentPlan === 'function') persistCurrentPlan();
            });
            ta.addEventListener('change', () => {
                if (typeof renderTimelineScenes === 'function' && window.currentPlan) renderTimelineScenes(window.currentPlan);
                window.syncWizardStep2Preview();
            });
        });

        previewBox.querySelectorAll('.btn-wiz-rewrite-scene').forEach((btn) => {
            btn.addEventListener('click', () => {
                const idx = Number(btn.getAttribute('data-rewrite-idx'));
                const sc = window.currentPlan?.scenes?.[idx];
                if (!sc) return;
                const prefixes = ['En çarpıcı nokta şu ki, ', 'Bilim insanlarının da doğruladığı üzere, ', 'Çoğu kişinin hiç fark etmediği gerçek ise şu: ', 'Daha da şaşırtıcı olanı, '];
                const cleaned = String(sc.narration || '').trim().replace(/^(En çarpıcı nokta şu ki,\s*|Bilim insanlarının da doğruladığı üzere,\s*|Çoğu kişinin hiç fark etmediği gerçek ise şu:\s*|Daha da şaşırtıcı olanı,\s*)/i, '');
                const pick = prefixes[(idx + (window._sceneRewriteTick = (window._sceneRewriteTick || 0) + 1)) % prefixes.length];
                sc.narration = pick + cleaned.charAt(0).toLowerCase() + cleaned.slice(1);
                sc.duration = Math.max(3.2, Math.min(7.0, +(countWords(sc.narration) * 0.38).toFixed(1)));
                if (typeof persistCurrentPlan === 'function') persistCurrentPlan();
                if (typeof renderTimelineScenes === 'function') renderTimelineScenes(window.currentPlan);
                window.syncWizardStep2Preview();
                if (typeof showToast === 'function') showToast(`↻ Sahne ${idx + 1} yeniden yazıldı.`);
            });
        });

        previewBox.querySelector('#btn-wiz-alt-hook')?.addEventListener('click', () => {
            const sc0 = window.currentPlan?.scenes?.[0];
            if (!sc0) return;
            const shortTopic = (document.getElementById('input-topic')?.value || window.currentPlan?.title || 'bu gerçek').trim().replace(/[?!.]+$/, '');
            const variants = (Array.isArray(window.currentPlan?.hook_variants) && window.currentPlan.hook_variants.length)
                ? window.currentPlan.hook_variants.map((h) => h.text || h.hook || h)
                : [
                    `${shortTopic} hakkında bildiğiniz her şey aslında büyük bir yanılsama olabilir mi?`,
                    `Sadece 30 saniye içinde ${shortTopic.toLowerCase()} gerçeğinin gizlenen yüzünü öğreneceksiniz.`,
                    `İnsanların %99'u bu detayı gözden kaçırıyor: ${shortTopic} aslında bambaşka çalışıyor!`
                ];
            window._hookCycleIdx = ((window._hookCycleIdx || 0) + 1) % variants.length;
            sc0.narration = String(variants[window._hookCycleIdx]);
            sc0.duration = Math.max(3.5, Math.min(6.5, +(countWords(sc0.narration) * 0.38).toFixed(1)));
            if (typeof persistCurrentPlan === 'function') persistCurrentPlan();
            if (typeof renderTimelineScenes === 'function') renderTimelineScenes(window.currentPlan);
            window.syncWizardStep2Preview();
            if (typeof showToast === 'function') showToast(`🎯 Kanca varyasyonu #${window._hookCycleIdx + 1} uygulandı.`);
        });

        previewBox.querySelector('#btn-wiz-sanitize-risks')?.addEventListener('click', () => {
            (window.currentPlan?.scenes || []).forEach((sc) => {
                let text = String(sc.narration || '');
                Object.entries(DEMONETIZATION_RISK_MAP).forEach(([bad, safe]) => { text = text.replace(new RegExp(bad, 'gi'), safe); });
                sc.narration = text;
            });
            if (typeof persistCurrentPlan === 'function') persistCurrentPlan();
            if (typeof renderTimelineScenes === 'function') renderTimelineScenes(window.currentPlan);
            window.syncWizardStep2Preview();
            if (typeof showToast === 'function') showToast('🛡️ Riskli ifadeler YouTube reklam dostu alternatiflerle değiştirildi.');
        });

        previewBox.querySelectorAll('.wiz-ver-tab[data-ver-idx]').forEach((tab) => {
            tab.addEventListener('click', () => {
                const chosen = versions?.[Number(tab.getAttribute('data-ver-idx'))];
                if (!chosen || !window.currentPlan) return;
                window.currentPlan.scenes = JSON.parse(JSON.stringify(chosen.scenes));
                if (typeof persistCurrentPlan === 'function') persistCurrentPlan();
                if (typeof renderTimelineScenes === 'function') renderTimelineScenes(window.currentPlan);
                window.syncWizardStep2Preview();
                if (typeof showToast === 'function') showToast(`↺ Senaryo v${chosen.ver} (${chosen.totalSec}s) sürümüne geri yüklendi.`);
            });
        });
    }

    function initWizardStep2Enhancements() {
        injectStep2VoiceEnhancements();
        injectManuscriptDropzone();
        enhanceStep2ScriptPreview();
        if (typeof window.syncWizardStep2Preview === 'function') window.syncWizardStep2Preview();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => setTimeout(initWizardStep2Enhancements, 80));
    } else {
        setTimeout(initWizardStep2Enhancements, 80);
    }
})();
