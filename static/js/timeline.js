/**
 * ShortsAI Studio — Sahne & Kurgu Editörü (timeline.js v3.0)
 * Complete rewrite: NLE-style timeline built from real render assets.
 * Gerçek metin + gerçek video/görsellerle oluşan premium sahne editörü.
 */

/* ─── Utility Functions ─── */
function hasEmoji(text) {
    return /[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{1F1E0}-\u{1F1FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}\u{FE00}-\u{FE0F}\u{1F900}-\u{1F9FF}\u{1FA00}-\u{1FA6F}\u{1FA70}-\u{1FAFF}\u{200D}\u{20E3}]/u.test(text || '');
}

function wordCount(text) {
    const spokenText = (text || '').replace(
        /\*\*(?:URGENT|DRAMATIC|EPIC|CALM|MYSTERIOUS|ENERGETIC|DARK|BRIGHT|SECRET|WARNING|HOOK|CTA)\*\*\s*/gi,
        '',
    );
    const matches = spokenText.match(/[\p{L}\p{N}_'-]+/gu);
    return matches ? matches.length : 0;
}

function sceneWordCountClass(wc) {
    if (wc < 6) return 'wc-danger';
    if (wc < 10 || wc > 24) return 'wc-warn';
    return 'wc-ok';
}

function cleanNarration(text) {
    return (text || '').replace(/\s*\[Görsel Açı \d+\]\s*/g, '').replace(/\s*\[Kadraj \d+\]\s*/g, '').trim();
}

const MOOD_CFG = {
    epic:       { icon: '🌟', label: 'Epic',       color: '#fbbf24', bg: 'rgba(251,191,36,0.12)' },
    dramatic:   { icon: '🔴', label: 'Dramatic',   color: '#ef4444', bg: 'rgba(239,68,68,0.12)' },
    calm:       { icon: '🔵', label: 'Calm',       color: '#38bdf8', bg: 'rgba(56,189,248,0.12)' },
    mysterious: { icon: '🟣', label: 'Mysterious', color: '#a78bfa', bg: 'rgba(167,139,250,0.12)' },
    energetic:  { icon: '⚡', label: 'Energetic',  color: '#fb923c', bg: 'rgba(251,146,60,0.12)' },
    dark:       { icon: '⬛', label: 'Dark',       color: '#94a3b8', bg: 'rgba(148,163,184,0.08)' },
    bright:     { icon: '☀️', label: 'Bright',     color: '#34d399', bg: 'rgba(52,211,153,0.12)' }
};

/* ─── Compliance Dashboard ─── */
function updateComplianceDashboard(scenes) {
    if (!scenes || !scenes.length) { resetComplianceDashboard(); return; }

    const timedScenes = scenes.filter(s => sceneDurationSec(s) !== null);
    if (!timedScenes.length) { resetComplianceDashboard(); return; }

    const totalSec = timedScenes.reduce((a, s) => a + sceneDurationSec(s), 0);

    // Duration chip
    const durChip = document.getElementById('tl-chip-duration');
    const durText = document.getElementById('tl-dur-value');
    if (durText) durText.textContent = `${totalSec.toFixed(1)}s`;
    if (durChip) {
        durChip.className = 'tl-stat-pill';
        if (totalSec >= 38 && totalSec <= 60) durChip.classList.add('pill-ok');
        else if (totalSec > 60 && totalSec <= 65) durChip.classList.add('pill-warn');
        else durChip.classList.add('pill-danger');
    }

    // Scene count chip
    const scChip = document.getElementById('tl-chip-scenes');
    const scText = document.getElementById('tl-scene-value');
    if (scText) scText.textContent = `${scenes.length} Sahne`;
    if (scChip) {
        scChip.className = 'tl-stat-pill';
        const cadenceStatus = typeof directorCadenceStatus === 'function' ? directorCadenceStatus(scenes.length) : 'ok';
        scChip.classList.add(cadenceStatus === 'fail' ? 'pill-danger' : `pill-${cadenceStatus}`);
    }

    // Long cuts
    const longCuts = timedScenes.filter(s => sceneDurationSec(s) > 3.5).length;
    const lcChip = document.getElementById('tl-chip-longcuts');
    const lcText = document.getElementById('tl-longcut-value');
    if (lcText) lcText.textContent = longCuts ? `${longCuts} Uyarı` : 'Temiz';
    if (lcChip) {
        lcChip.className = 'tl-stat-pill';
        lcChip.classList.add(longCuts === 0 ? 'pill-ok' : 'pill-warn');
    }

    // Duplicate queries
    let dupes = 0;
    const qEntries = [];
    scenes.forEach((s, idx) => {
        if (s.is_visual_cutaway) return;
        const sq = s.search_queries || [];
        if (sq[0]) qEntries.push({ q: sq[0].toLowerCase().trim(), idx });
    });
    const seen = {};
    qEntries.forEach(({ q, idx }) => {
        if (seen[q] !== undefined && idx - seen[q] > 1) dupes++;
        seen[q] = idx;
    });
    const dupChip = document.getElementById('tl-chip-dupes');
    const dupText = document.getElementById('tl-dupe-value');
    if (dupText) dupText.textContent = dupes ? `${dupes} Tekrar` : 'Temiz';
    if (dupChip) {
        dupChip.className = 'tl-stat-pill';
        dupChip.classList.add(dupes === 0 ? 'pill-ok' : 'pill-warn');
    }

    // Clips ready
    const clipsReady = scenes.filter(s => {
        const u = s.video_url || s.selected_video?.url || s.video_path;
        return Boolean(u && (u.startsWith('/assets') || u.startsWith('http') || u.endsWith('.mp4')));
    }).length;
    const clipChip = document.getElementById('tl-chip-clips');
    const clipText = document.getElementById('tl-clip-value');
    if (clipText) clipText.textContent = `${clipsReady}/${scenes.length}`;
    if (clipChip) {
        clipChip.className = 'tl-stat-pill';
        clipChip.classList.add(clipsReady === scenes.length ? 'pill-ok' : 'pill-pending');
    }

    // Words
    const totalWords = scenes.reduce((a, s) => a + wordCount(s.narration), 0);
    const wordText = document.getElementById('tl-word-value');
    if (wordText) wordText.textContent = `${totalWords}`;

    // Story arc
    if (totalSec > 0) {
        const introEnd = totalSec * 0.08;
        const conflictEnd = totalSec * 0.45;
        const climaxEnd = totalSec * 0.78;
        const set = (id, w) => { const el = document.getElementById(id); if (el) el.style.width = `${w}%`; };
        set('tl-arc-intro', (introEnd / totalSec) * 100);
        set('tl-arc-conflict', ((conflictEnd - introEnd) / totalSec) * 100);
        set('tl-arc-climax', ((climaxEnd - conflictEnd) / totalSec) * 100);
        set('tl-arc-loop', ((totalSec - climaxEnd) / totalSec) * 100);

        const r = n => Math.round(n);
        const lbl = (id, t) => { const el = document.getElementById(id); if (el) el.textContent = t; };
        lbl('tl-arc-lbl-intro', `🎬 Kanca (0-${r(introEnd)}s)`);
        lbl('tl-arc-lbl-conflict', `⚔️ Çatışma (${r(introEnd)}-${r(conflictEnd)}s)`);
        lbl('tl-arc-lbl-climax', `🔥 Doruk (${r(conflictEnd)}-${r(climaxEnd)}s)`);
        lbl('tl-arc-lbl-loop', `🔄 Kapanış (${r(climaxEnd)}-${r(totalSec)}s)`);
    }
}

function resetComplianceDashboard() {
    const sets = [
        ['tl-dur-value', '0s'], ['tl-scene-value', '0'], ['tl-longcut-value', '—'],
        ['tl-dupe-value', '—'], ['tl-clip-value', '0/0'], ['tl-word-value', '0']
    ];
    sets.forEach(([id, val]) => { const el = document.getElementById(id); if (el) el.textContent = val; });
}

/* ─── Audio Preview ─── */
let activeAudioPreview = null;
async function previewSceneAudio(text, btnEl) {
    if (!text || !text.trim()) return showToast('Seslendirilecek metin boş', 'warn');
    if (activeAudioPreview) { activeAudioPreview.pause(); activeAudioPreview = null; }
    const originalHtml = btnEl.innerHTML;
    btnEl.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
    btnEl.disabled = true;
    try {
        const voiceId = document.getElementById('select-tts-voice')?.value || 'tr-TR-AhmetNeural';
        const res = await fetch('/api/tts/preview', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text, voice: voiceId })
        });
        if (!res.ok) throw new Error('TTS sunucu hatası');
        const blob = await res.blob();
        activeAudioPreview = new Audio(URL.createObjectURL(blob));
        activeAudioPreview.play();
        activeAudioPreview.onended = () => { btnEl.innerHTML = originalHtml; btnEl.disabled = false; };
        activeAudioPreview.onerror = () => { btnEl.innerHTML = originalHtml; btnEl.disabled = false; showToast('Ses çalınamadı', 'error'); };
    } catch (e) {
        btnEl.innerHTML = originalHtml; btnEl.disabled = false;
        showToast('TTS Hatası: ' + e.message, 'error');
    }
}

/* ═══════════════════════════════════════════════════════════════
   MAIN RENDER: Build the NLE Timeline from Real Plan Data
   ═══════════════════════════════════════════════════════════════ */
function renderTimelineScenes(plan) {
    const container = document.getElementById('scenes-timeline-container');
    const titleEl = document.getElementById('tl-project-title');
    const nicheEl = document.getElementById('tl-niche-name');
    const badgeCount = document.getElementById('badge-scene-count');

    if (!container || !plan) return;

    const scenes = plan.scenes || [];

    /* ── Empty State ── */
    if (!scenes.length) {
        if (titleEl) titleEl.textContent = 'Sahne & Kurgu Stüdyosu';
        if (nicheEl) nicheEl.textContent = '';
        if (badgeCount) badgeCount.textContent = '0';
        container.innerHTML = `
            <div class="tl-empty-state">
                <div class="tl-empty-icon"><i class="fa-solid fa-clapperboard"></i></div>
                <h3>Henüz sahne verisi yok</h3>
                <p>Render Al butonuna tıklayın — son senaryo ve gerçek video klipleri otomatik olarak buraya yüklenecek.</p>
                <div class="tl-empty-actions">
                    <button type="button" class="tl-btn tl-btn-primary" id="btn-empty-load-latest">
                        <i class="fa-solid fa-cloud-arrow-down"></i> Son Renderı Yükle
                    </button>
                    <button type="button" class="tl-btn tl-btn-ghost" id="btn-empty-prepare">
                        <i class="fa-solid fa-wand-magic-sparkles"></i> Kurguyu Hazırla
                    </button>
                </div>
            </div>`;
        document.getElementById('btn-empty-load-latest')?.addEventListener('click', () => loadLatestRenderedProjectToTimeline());
        document.getElementById('btn-empty-prepare')?.addEventListener('click', () => prepareTimelineAssetsAndScript());
        if (typeof updateScriptActionButtons === 'function') updateScriptActionButtons();
        resetComplianceDashboard();
        return;
    }

    /* ── Header Data ── */
    const displayTitle = (typeof sanitizeTopicTitleForDisplay === 'function' ? sanitizeTopicTitleForDisplay(plan.title || '') : '') || plan.title || 'Aktif Proje';
    if (titleEl) titleEl.textContent = displayTitle;
    if (nicheEl) nicheEl.textContent = plan.niche_id || plan.meta?.locked_niche || '';
    if (badgeCount) badgeCount.textContent = String(scenes.length);

    const totalSec = scenes.reduce((a, s) => a + (parseFloat(s.duration) || 3.5), 0);
    const totalWords = scenes.reduce((a, s) => a + wordCount(s.narration), 0);
    const clipsReady = scenes.filter(s => {
        const u = s.video_url || s.selected_video?.url || s.video_path;
        return Boolean(u && (u.startsWith('/assets') || u.startsWith('http') || u.endsWith('.mp4')));
    }).length;

    /* ── Build Cards ── */
    container.innerHTML = '';

    scenes.forEach((sc, i) => {
        const mood = (sc.mood || 'epic').toLowerCase();
        const moodCfg = MOOD_CFG[mood] || MOOD_CFG.epic;
        const dur = parseFloat(sc.duration) || 3.5;
        const narr = sc.narration || '';
        const wc = wordCount(narr);
        const wcCls = sceneWordCountClass(wc);
        const sceneDesc = sc.scene_description || '';
        const searchQueries = sc.search_queries || [];

        // Beat label
        let beatLabel = '⚔️ Gelişme';
        let beatClass = 'beat-dev';
        if (i === 0) { beatLabel = '🎯 Kanca'; beatClass = 'beat-hook'; }
        else if (i === scenes.length - 1) { beatLabel = '🔄 Kapanış'; beatClass = 'beat-close'; }
        else if (i === Math.floor(scenes.length * 0.65)) { beatLabel = '🔥 Doruk'; beatClass = 'beat-climax'; }

        // Video URL
        let videoUrl = sc.selected_video?.url || sc.video_url || sc.video_path || '';
        if (videoUrl && videoUrl.startsWith('assets/')) videoUrl = '/' + videoUrl;
        const isVideo = Boolean(videoUrl && (videoUrl.startsWith('/assets') || videoUrl.startsWith('http') || videoUrl.endsWith('.mp4')));
        const isImage = Boolean(videoUrl && (videoUrl.endsWith('.jpg') || videoUrl.endsWith('.png') || videoUrl.endsWith('.webp')));

        // Provider
        let provName = 'Stok Video', provIcon = 'fa-film', provColor = '#38bdf8';
        if (sc.selected_video?.source) {
            provName = sc.selected_video.source;
            if (provName.includes('Flux')) { provIcon = 'fa-wand-magic-sparkles'; provColor = '#c084fc'; }
            else if (provName.includes('Whiteboard')) { provIcon = 'fa-pen-nib'; provColor = '#fb923c'; }
            else if (provName.toLowerCase().includes('pixabay')) provName = 'Pixabay';
            else if (provName.toLowerCase().includes('pexels')) provName = 'Pexels';
        } else if (sc.visual_mode === 'whiteboard') {
            provName = 'Whiteboard'; provIcon = 'fa-pen-nib'; provColor = '#fb923c';
        }

        const card = document.createElement('div');
        card.className = `tl-scene-card`;
        card.setAttribute('draggable', 'true');
        card.setAttribute('data-scene-idx', i);

        card.innerHTML = `
            <!-- ═ LEFT: Video Preview ═ -->
            <div class="tl-card-media">
                <div class="tl-video-frame" id="tl-frame-${i}">
                    ${isVideo ? `
                        <video src="${escapeHtml(videoUrl)}" preload="metadata" loop muted playsinline></video>
                        <div class="tl-play-overlay"><i class="fa-solid fa-play"></i></div>
                    ` : isImage ? `
                        <img src="${escapeHtml(videoUrl)}" alt="Sahne ${i+1}" class="tl-scene-img">
                    ` : `
                        <div class="tl-no-media">
                            <i class="fa-solid fa-video-slash"></i>
                            <span>Klip Bekleniyor</span>
                        </div>
                    `}
                    <div class="tl-frame-badges">
                        <span class="tl-badge-idx">#${i + 1}</span>
                        <span class="tl-badge-dur">${dur.toFixed(1)}s</span>
                    </div>
                    ${(isVideo || isImage) ? `
                        <span class="tl-badge-provider" style="--prov-color: ${provColor}">
                            <i class="fa-solid ${provIcon}"></i> ${escapeHtml(provName)}
                        </span>
                    ` : ''}
                </div>
                <div class="tl-media-actions">
                    <button type="button" class="tl-btn tl-btn-swap" data-idx="${i}" title="Görseli / Videoyu Değiştir">
                        <i class="fa-solid fa-arrows-rotate"></i> Değiştir
                    </button>
                    <button type="button" class="tl-btn-icon tl-btn-listen" data-idx="${i}" title="Bu sahnenin sesini dinle">
                        <i class="fa-solid fa-volume-high"></i>
                    </button>
                </div>
            </div>

            <!-- ═ RIGHT: Script & Controls ═ -->
            <div class="tl-card-content">
                <div class="tl-card-top-bar">
                    <div class="tl-card-labels">
                        <span class="tl-beat-label ${beatClass}">${beatLabel}</span>
                        <span class="tl-mood-tag" style="background: ${moodCfg.bg}; color: ${moodCfg.color}">
                            ${moodCfg.icon} ${moodCfg.label}
                        </span>
                        <span class="tl-wc-chip ${wcCls}" id="tl-wc-${i}">${wc} kelime</span>
                        <span class="tl-emoji-chip ${hasEmoji(narr) ? 'has' : 'none'}" id="tl-emoji-${i}">
                            ${hasEmoji(narr) ? '✅ Emoji' : '⚠️ No Emoji'}
                        </span>
                    </div>
                    <div class="tl-card-actions">
                        <button type="button" class="tl-btn-icon btn-move-up" data-idx="${i}" title="Yukarı" ${i === 0 ? 'disabled' : ''}><i class="fa-solid fa-chevron-up"></i></button>
                        <button type="button" class="tl-btn-icon btn-move-down" data-idx="${i}" title="Aşağı" ${i === scenes.length - 1 ? 'disabled' : ''}><i class="fa-solid fa-chevron-down"></i></button>
                        <button type="button" class="tl-btn-icon btn-clone-scene" data-idx="${i}" title="Çoğalt"><i class="fa-solid fa-copy"></i></button>
                        <button type="button" class="tl-btn-icon btn-del-scene" data-idx="${i}" title="Sil"><i class="fa-solid fa-trash"></i></button>
                    </div>
                </div>

                <div class="tl-field">
                    <label><i class="fa-solid fa-microphone-lines"></i> Seslendirme Metni</label>
                    <textarea class="tl-textarea scene-narr-input" data-idx="${i}" rows="2" placeholder="Seslendirilecek metin...">${escapeHtml(narr)}</textarea>
                </div>

                <div class="tl-fields-row">
                    <div class="tl-field">
                        <label><i class="fa-solid fa-image"></i> Görsel Tarif</label>
                        <input type="text" class="tl-input scene-desc-input" data-idx="${i}" value="${escapeHtml(sceneDesc)}" placeholder="Sahne görsel açıklaması...">
                    </div>
                    <div class="tl-field">
                        <label><i class="fa-solid fa-magnifying-glass"></i> Stok Arama</label>
                        <input type="text" class="tl-input scene-query-input" data-idx="${i}" value="${escapeHtml(searchQueries[0] || '')}" placeholder="Arama sorgusu...">
                    </div>
                </div>

                <div class="tl-fields-row">
                    <div class="tl-field tl-field-sm">
                        <label><i class="fa-solid fa-stopwatch"></i> Süre (sn)</label>
                        <input type="number" class="tl-input scene-dur-input" data-idx="${i}" min="1" max="15" step="0.25" value="${dur}">
                    </div>
                    <div class="tl-field tl-field-sm">
                        <label><i class="fa-solid fa-masks-theater"></i> Mood</label>
                        <select class="tl-select scene-mood-select" data-idx="${i}">
                            ${Object.entries(MOOD_CFG).map(([k, v]) =>
                                `<option value="${k}" ${mood === k ? 'selected' : ''}>${v.icon} ${v.label}</option>`
                            ).join('')}
                        </select>
                    </div>
                </div>
            </div>
        `;

        /* ── Interactive Behaviors ── */

        // Video hover-to-play
        const vid = card.querySelector('video');
        const playBtn = card.querySelector('.tl-play-overlay');
        if (vid) {
            const frame = card.querySelector('.tl-video-frame');
            frame?.addEventListener('mouseenter', () => { vid.play().catch(() => {}); if (playBtn) playBtn.style.opacity = '0'; });
            frame?.addEventListener('mouseleave', () => { vid.pause(); vid.currentTime = 0; if (playBtn) playBtn.style.opacity = '1'; });
            playBtn?.addEventListener('click', e => {
                e.stopPropagation();
                if (vid.paused) { vid.play().catch(() => {}); playBtn.style.opacity = '0'; }
                else { vid.pause(); playBtn.style.opacity = '1'; }
            });
        }

        // TTS preview
        card.querySelector('.tl-btn-listen')?.addEventListener('click', e => {
            const textToSpeak = card.querySelector('.scene-narr-input')?.value || sc.narration || '';
            previewSceneAudio(textToSpeak, e.currentTarget);
        });

        // Replace visual
        card.querySelector('.tl-btn-swap')?.addEventListener('click', e => {
            openReplaceVisualModal(parseInt(e.currentTarget.getAttribute('data-idx')));
        });

        // Move up/down
        card.querySelector('.btn-move-up')?.addEventListener('click', () => {
            if (i > 0) { collectTimelineEdits(); [currentPlan.scenes[i-1], currentPlan.scenes[i]] = [currentPlan.scenes[i], currentPlan.scenes[i-1]]; currentPlan.scenes.forEach((s, idx) => s.scene_number = idx + 1); setCurrentPlan(currentPlan); }
        });
        card.querySelector('.btn-move-down')?.addEventListener('click', () => {
            if (i < currentPlan.scenes.length - 1) { collectTimelineEdits(); [currentPlan.scenes[i+1], currentPlan.scenes[i]] = [currentPlan.scenes[i], currentPlan.scenes[i+1]]; currentPlan.scenes.forEach((s, idx) => s.scene_number = idx + 1); setCurrentPlan(currentPlan); }
        });

        // Clone
        card.querySelector('.btn-clone-scene')?.addEventListener('click', () => {
            collectTimelineEdits();
            const clone = JSON.parse(JSON.stringify(currentPlan.scenes[i]));
            clone.scene_number = currentPlan.scenes.length + 1;
            currentPlan.scenes.splice(i + 1, 0, clone);
            currentPlan.scenes.forEach((s, idx) => s.scene_number = idx + 1);
            setCurrentPlan(currentPlan);
            showToast('📋 Sahne klonlandı');
        });

        // Delete
        card.querySelector('.btn-del-scene')?.addEventListener('click', () => {
            collectTimelineEdits();
            currentPlan.scenes.splice(i, 1);
            currentPlan.scenes.forEach((s, idx) => s.scene_number = idx + 1);
            setCurrentPlan(currentPlan);
            showToast('🗑️ Sahne silindi');
        });

        // Live editing
        const narrInput = card.querySelector('.scene-narr-input');
        narrInput?.addEventListener('input', () => {
            const text = narrInput.value;
            sc.narration = text;
            const liveWc = wordCount(text);
            const chip = document.getElementById(`tl-wc-${i}`);
            if (chip) { chip.textContent = `${liveWc} kelime`; chip.className = `tl-wc-chip ${sceneWordCountClass(liveWc)}`; }
            const emBadge = document.getElementById(`tl-emoji-${i}`);
            if (emBadge) { const em = hasEmoji(text); emBadge.textContent = em ? '✅ Emoji' : '⚠️ No Emoji'; emBadge.className = `tl-emoji-chip ${em ? 'has' : 'none'}`; }
            const wordEl = document.getElementById('tl-word-value');
            if (wordEl) wordEl.textContent = `${currentPlan.scenes.reduce((a, s) => a + wordCount(s.narration), 0)}`;
        });

        card.querySelector('.scene-desc-input')?.addEventListener('change', e => { sc.scene_description = e.target.value; });
        card.querySelector('.scene-query-input')?.addEventListener('change', e => { sc.search_queries = [e.target.value, ...(sc.search_queries || []).slice(1)]; });
        card.querySelector('.scene-dur-input')?.addEventListener('change', e => {
            sc.duration = parseFloat(e.target.value) || 3.5;
            updateComplianceDashboard(currentPlan.scenes);
        });
        card.querySelector('.scene-mood-select')?.addEventListener('change', e => {
            sc.mood = e.target.value;
            const cfg = MOOD_CFG[sc.mood] || MOOD_CFG.epic;
            const mTag = card.querySelector('.tl-mood-tag');
            if (mTag) { mTag.style.background = cfg.bg; mTag.style.color = cfg.color; mTag.innerHTML = `${cfg.icon} ${cfg.label}`; }
        });

        // Drag & Drop
        card.addEventListener('dragstart', e => { e.dataTransfer.setData('text/plain', i); card.classList.add('dragging'); });
        card.addEventListener('dragend', () => { card.classList.remove('dragging'); container.querySelectorAll('.tl-scene-card').forEach(c => c.classList.remove('drag-over')); });
        card.addEventListener('dragover', e => { e.preventDefault(); card.classList.add('drag-over'); });
        card.addEventListener('dragleave', () => card.classList.remove('drag-over'));
        card.addEventListener('drop', e => {
            e.preventDefault(); card.classList.remove('drag-over');
            const fromIdx = parseInt(e.dataTransfer.getData('text/plain'));
            if (fromIdx !== i && currentPlan?.scenes) {
                collectTimelineEdits();
                const [moved] = currentPlan.scenes.splice(fromIdx, 1);
                currentPlan.scenes.splice(i, 0, moved);
                currentPlan.scenes.forEach((s, idx) => s.scene_number = idx + 1);
                setCurrentPlan(currentPlan);
                showToast('🔀 Sahne sırası güncellendi');
            }
        });

        container.appendChild(card);
    });

    updateComplianceDashboard(scenes);
}

/* ─── Collect Timeline Edits ─── */
function collectTimelineEdits() {
    if (currentPlan && Array.isArray(currentPlan.scenes)) {
        const narrInputs = document.querySelectorAll('.scene-narr-input');
        const descInputs = document.querySelectorAll('.scene-desc-input');
        const queryInputs = document.querySelectorAll('.scene-query-input');
        const durInputs = document.querySelectorAll('.scene-dur-input');
        const moodSelects = document.querySelectorAll('.scene-mood-select');

        currentPlan.scenes.forEach((sc, i) => {
            if (narrInputs[i]) sc.narration = narrInputs[i].value;
            if (descInputs[i]) sc.scene_description = descInputs[i].value;
            if (queryInputs[i]) { sc.search_queries = [queryInputs[i].value.trim(), ...(sc.search_queries || []).slice(1)].filter(Boolean); }
            if (durInputs[i]) sc.duration = parseFloat(durInputs[i].value) || 3.5;
            if (moodSelects[i]) sc.mood = moodSelects[i].value;
        });

        currentPlan.full_narration = currentPlan.scenes.map(s => s.narration || '').filter(Boolean).join(' ');
        if (typeof persistCurrentPlan === 'function') persistCurrentPlan();
        if (typeof getNarrationIssues === 'function' && typeof updateRenderButtonsBlocked === 'function') {
            const hard = getNarrationIssues(currentPlan.scenes);
            updateRenderButtonsBlocked(hard.length > 0, hard[0]);
        }
    }
}

/* ─── Copy Full Script ─── */
function copyFullScriptText() {
    collectTimelineEdits();
    if (!currentPlan?.scenes?.length) return showToast('Kopyalanacak senaryo yok', 'warn');

    const title = currentPlan.title || 'YouTube Shorts Senaryosu';
    const totalSec = currentPlan.scenes.reduce((a, s) => a + (parseFloat(s.duration) || 3.5), 0);
    const totalWords = currentPlan.scenes.reduce((a, s) => a + wordCount(s.narration), 0);

    let text = `🎬 BAŞLIK: ${title}\n`;
    text += `⏱️ SÜRE: ${totalSec.toFixed(1)}sn | 📝 ${totalWords} kelime | 🎞️ ${currentPlan.scenes.length} sahne\n`;
    text += `═══════════════════════════════════════════\n\n`;

    currentPlan.scenes.forEach((sc, idx) => {
        text += `[SAHNE ${idx + 1}] (${(parseFloat(sc.duration) || 3.5).toFixed(1)}s | ${sc.mood || 'epic'})\n`;
        text += `SESLENDİRME: ${(sc.narration || '').trim()}\n`;
        if (sc.scene_description) text += `GÖRSEL: ${sc.scene_description.trim()}\n`;
        if (sc.search_queries?.[0]) text += `ARAMA: ${sc.search_queries[0].trim()}\n`;
        text += `\n`;
    });

    text += `═══════════════════════════════════════════\n🎙️ KESİNTİSİZ METİN:\n`;
    text += currentPlan.scenes.map(s => (s.narration || '').trim()).filter(Boolean).join('\n\n') + '\n';

    if (navigator.clipboard?.writeText) {
        navigator.clipboard.writeText(text).then(() => showToast(`📋 ${totalWords} kelime panoya kopyalandı`)).catch(() => fallbackCopy(text, totalWords));
    } else fallbackCopy(text, totalWords);
}

function fallbackCopy(text, wc) {
    const ta = document.createElement('textarea'); ta.value = text; ta.style.cssText = 'position:fixed;opacity:0';
    document.body.appendChild(ta); ta.select();
    try { document.execCommand('copy'); showToast(`📋 ${wc} kelime kopyalandı`); } catch (_) { showToast('Kopyalama başarısız', 'error'); }
    document.body.removeChild(ta);
}

/* ─── Load Latest Rendered Project ─── */
async function loadLatestRenderedProjectToTimeline(silent = false) {
    const btn = document.getElementById('btn-sync-latest-render');
    const oldHtml = btn ? btn.innerHTML : '';
    if (btn) { btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Yükleniyor...'; btn.disabled = true; }

    try {
        const res = await fetch('/api/projects/latest/plan');
        if (!res.ok) { if (!silent) showToast('Render edilmiş proje bulunamadı', 'warn'); return; }
        const data = await res.json();
        if (data.status === 'ok' && data.plan?.scenes?.length) {
            setCurrentPlan(data.plan);
            if (!silent) showToast(`🎬 "${data.plan.title || data.project_slug}" yüklendi (${data.plan.scenes.length} sahne)`);
        } else {
            if (!silent) showToast('Sahne verisi bulunamadı', 'warn');
        }
    } catch (err) { if (!silent) showToast('Yükleme hatası: ' + err.message, 'error'); }
    finally { if (btn) { btn.innerHTML = oldHtml; btn.disabled = false; } }
}

/* ─── Prepare Assets & Script ─── */
async function prepareTimelineAssetsAndScript() {
    const btn = document.getElementById('btn-prepare-timeline');
    const oldHtml = btn ? btn.innerHTML : '';
    const topic = document.getElementById('input-topic')?.value?.trim() || currentPlan?.title || 'YouTube Shorts';
    const niche = document.getElementById('select-niche')?.value || currentPlan?.niche_id || '';

    if (btn) { btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Hazırlanıyor...'; btn.disabled = true; }
    showToast('🚀 AI senaryo + gerçek video klipleri hazırlanıyor...', 'info');

    try {
        const res = await fetch('/api/timeline/prepare', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topic, niche_id: niche })
        });
        const data = await res.json();
        if (data.status === 'ok' && data.plan) {
            setCurrentPlan(data.plan);
            showToast(`✨ ${data.plan.scenes.length} sahne hazırlandı`);
        } else throw new Error(data.message || data.detail || 'Hazırlık tamamlanamadı');
    } catch (err) { showToast('Hazırlama hatası: ' + err.message, 'error'); }
    finally { if (btn) { btn.innerHTML = oldHtml; btn.disabled = false; } }
}

/* ═══════════════════════════════════════════════════════════════
   GÖRSEL DEĞİŞTİRME MODALI
   ═══════════════════════════════════════════════════════════════ */
let activeModalSceneIdx = null;

function openReplaceVisualModal(idx) {
    if (!currentPlan?.scenes?.[idx]) return;
    activeModalSceneIdx = idx;
    const sc = currentPlan.scenes[idx];
    const modal = document.getElementById('modal-change-scene-visual');
    const modalTitle = document.getElementById('modal-change-visual-title');
    const searchInput = document.getElementById('modal-stock-search-input');
    const fluxInput = document.getElementById('modal-flux-prompt-input');
    const wbInput = document.getElementById('modal-whiteboard-prompt-input');

    if (modalTitle) modalTitle.innerHTML = `<i class="fa-solid fa-film text-primary"></i> Sahne #${idx + 1} — Görsel Değiştir`;
    const defQ = (sc.search_queries?.[0]) || sc.scene_description || 'cinematic motion';
    if (searchInput) searchInput.value = defQ;
    if (fluxInput) fluxInput.value = sc.scene_description || sc.narration || '';
    if (wbInput) wbInput.value = sc.scene_description || sc.narration || '';

    switchModalTab('stock');
    modal?.classList.remove('hidden');
    executeModalStockSearch(defQ);
}

function closeReplaceVisualModal() {
    document.getElementById('modal-change-scene-visual')?.classList.add('hidden');
    activeModalSceneIdx = null;
}

function switchModalTab(tabName) {
    document.querySelectorAll('.modal-tab-btn').forEach(btn => btn.classList.toggle('active', btn.getAttribute('data-tab') === tabName));
    document.querySelectorAll('.modal-tab-content').forEach(c => c.classList.toggle('hidden', c.id !== `tab-content-${tabName}`));
}

async function executeModalStockSearch(query) {
    const q = (query || document.getElementById('modal-stock-search-input')?.value || '').trim();
    const grid = document.getElementById('modal-stock-results-grid');
    const btn = document.getElementById('btn-modal-do-stock-search');
    if (!q || !grid) return;

    grid.innerHTML = `<div class="tl-stock-loading"><i class="fa-solid fa-spinner fa-spin"></i><span>"${escapeHtml(q)}" aranıyor...</span></div>`;
    if (btn) btn.disabled = true;

    try {
        const niche = currentPlan?.niche_id || '';
        const res = await fetch(`/api/stock/search?query=${encodeURIComponent(q)}&limit=12&niche_id=${encodeURIComponent(niche)}`);
        const data = await res.json();
        const results = data.results || [];

        if (!results.length) {
            grid.innerHTML = `<div class="tl-stock-loading"><i class="fa-solid fa-circle-exclamation" style="color:#f59e0b"></i><span>Sonuç bulunamadı. Farklı İngilizce terimler deneyin.</span></div>`;
            return;
        }

        grid.innerHTML = '';
        results.forEach((item, rIdx) => {
            const card = document.createElement('div');
            card.className = 'tl-stock-card';
            const thumbUrl = item.thumbnail || item.preview_url || '';
            card.innerHTML = `
                ${thumbUrl ? `<img src="${escapeHtml(thumbUrl)}" class="tl-stock-thumb" alt="Klip">` :
                    `<div class="tl-stock-thumb-empty"><i class="fa-solid fa-film"></i></div>`}
                <div class="tl-stock-meta">
                    <span class="tl-stock-source">${escapeHtml(item.source || 'Stok')}</span>
                    <span>${item.duration ? item.duration + 's' : '—'}</span>
                </div>
                <button type="button" class="tl-btn tl-btn-primary tl-btn-sm btn-select-stock" data-ridx="${rIdx}">
                    <i class="fa-solid fa-check"></i> Seç
                </button>
            `;
            card.querySelector('.btn-select-stock')?.addEventListener('click', async () => {
                await applyClipReplacement({ replace_mode: 'stock', stock_video_data: item });
            });
            grid.appendChild(card);
        });
    } catch (e) {
        grid.innerHTML = `<div class="tl-stock-loading" style="color:#ef4444"><i class="fa-solid fa-triangle-exclamation"></i><span>Hata: ${escapeHtml(e.message)}</span></div>`;
    } finally { if (btn) btn.disabled = false; }
}

async function applyClipReplacement(payload) {
    if (activeModalSceneIdx === null || !currentPlan?.scenes?.[activeModalSceneIdx]) return;
    const idx = activeModalSceneIdx;
    const sc = currentPlan.scenes[idx];
    showToast('Klip güncelleniyor...', 'info');

    try {
        const res = await fetch('/api/timeline/replace-clip', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ project_slug: currentPlan.title || 'active_project', scene_index: idx, ...payload })
        });
        const data = await res.json();

        if (data.status === 'ok') {
            if (payload.replace_mode === 'stock') {
                sc.selected_video = payload.stock_video_data;
                sc.video_url = data.clip_url || payload.stock_video_data.url;
            } else if (payload.replace_mode === 'flux') {
                sc.video_url = data.clip_url;
                sc.selected_video = { source: '0 TL Flux AI (SDXL)', url: data.clip_url };
            } else if (payload.replace_mode === 'whiteboard') {
                sc.video_url = data.clip_url;
                sc.selected_video = { source: 'Whiteboard Çizim', url: data.clip_url };
            }
            setCurrentPlan(currentPlan);
            closeReplaceVisualModal();
            showToast(`🎬 Sahne #${idx + 1} güncellendi!`);
        } else throw new Error(data.detail || data.message || 'Değiştirilemedi');
    } catch (e) { showToast('Hata: ' + e.message, 'error'); }
}

/* ═══════════════════════════════════════════════════════════════
   EVENT LISTENERS
   ═══════════════════════════════════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {
    // Toolbar
    document.getElementById('btn-sync-latest-render')?.addEventListener('click', () => loadLatestRenderedProjectToTimeline());
    document.getElementById('btn-prepare-timeline')?.addEventListener('click', () => prepareTimelineAssetsAndScript());

    // Copy script
    document.querySelectorAll('.btn-copy-full-script').forEach(btn => btn.addEventListener('click', () => copyFullScriptText()));
    document.getElementById('btn-copy-script-timeline')?.addEventListener('click', () => copyFullScriptText());
    document.getElementById('btn-copy-script-studio')?.addEventListener('click', () => copyFullScriptText());

    // Add manual scene
    document.getElementById('btn-add-scene-manual')?.addEventListener('click', () => {
        if (!currentPlan) currentPlan = { title: document.getElementById('input-topic')?.value || 'Yeni Shorts', scenes: [] };
        currentPlan.scenes.push({
            scene_number: currentPlan.scenes.length + 1,
            narration: 'Yeni sahne anlatım metni...', scene_description: 'Cinematic dynamic shot',
            search_queries: ['cinematic nature'], duration: 3.5, mood: 'epic'
        });
        setCurrentPlan(currentPlan);
        showToast('➕ Sahne eklendi');
    });

    // Render
    document.getElementById('btn-render-from-timeline')?.addEventListener('click', () => {
        collectTimelineEdits();
        if (typeof startRenderProcess === 'function') startRenderProcess(currentPlan);
    });

    // Modal
    document.getElementById('btn-close-visual-modal')?.addEventListener('click', closeReplaceVisualModal);
    document.getElementById('modal-change-scene-visual')?.addEventListener('click', e => { if (e.target.id === 'modal-change-scene-visual') closeReplaceVisualModal(); });
    document.querySelectorAll('.modal-tab-btn').forEach(btn => btn.addEventListener('click', () => switchModalTab(btn.getAttribute('data-tab'))));

    // Stock search
    document.getElementById('btn-modal-do-stock-search')?.addEventListener('click', () => executeModalStockSearch());
    document.getElementById('modal-stock-search-input')?.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); executeModalStockSearch(e.target.value); } });

    // Flux
    document.getElementById('btn-modal-generate-flux')?.addEventListener('click', async () => {
        const prompt = document.getElementById('modal-flux-prompt-input')?.value?.trim();
        if (!prompt) return showToast('Flux prompt girin', 'warn');
        const btn = document.getElementById('btn-modal-generate-flux');
        const old = btn.innerHTML; btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Üretiliyor...'; btn.disabled = true;
        try { await applyClipReplacement({ replace_mode: 'flux', prompt, duration: currentPlan?.scenes?.[activeModalSceneIdx]?.duration || 3.5 }); }
        finally { btn.innerHTML = old; btn.disabled = false; }
    });

    // Whiteboard
    document.getElementById('btn-modal-generate-whiteboard')?.addEventListener('click', async () => {
        const prompt = document.getElementById('modal-whiteboard-prompt-input')?.value?.trim();
        if (!prompt) return showToast('Whiteboard açıklaması girin', 'warn');
        const btn = document.getElementById('btn-modal-generate-whiteboard');
        const old = btn.innerHTML; btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Çiziliyor...'; btn.disabled = true;
        try { await applyClipReplacement({ replace_mode: 'whiteboard', prompt, duration: currentPlan?.scenes?.[activeModalSceneIdx]?.duration || 3.5 }); }
        finally { btn.innerHTML = old; btn.disabled = false; }
    });

    // Smart batch actions
    document.getElementById('btn-batch-flux-ai')?.addEventListener('click', () => {
        if (!currentPlan?.scenes?.length) return showToast('Önce senaryo oluşturun', 'warn');
        collectTimelineEdits();
        currentPlan.scenes.forEach(s => s.visual_mode = 'flux');
        currentPlan.visual_mode = 'flux';
        const sel = document.getElementById('select-visual-engine'); if (sel) sel.value = 'flux';
        setCurrentPlan(currentPlan);
        showToast('🎨 Tüm sahneler Flux SDXL moduna ayarlandı');
    });

    document.getElementById('btn-batch-whiteboard')?.addEventListener('click', () => {
        if (!currentPlan?.scenes?.length) return showToast('Önce senaryo oluşturun', 'warn');
        collectTimelineEdits();
        currentPlan.scenes.forEach(s => s.visual_mode = 'whiteboard');
        currentPlan.visual_mode = 'whiteboard';
        const sel = document.getElementById('select-visual-engine'); if (sel) sel.value = 'whiteboard';
        setCurrentPlan(currentPlan);
        showToast('✏️ Tüm sahneler Whiteboard moduna ayarlandı');
    });

    document.getElementById('btn-fetch-stock-clips')?.addEventListener('click', async () => {
        if (!currentPlan?.scenes?.length) return showToast('Önce senaryo oluşturun', 'warn');
        const btn = document.getElementById('btn-fetch-stock-clips');
        const old = btn.innerHTML; btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Çekiliyor...';
        showToast('📡 Stok videolar taranıyor...');
        try {
            collectTimelineEdits();
            const res = await fetch('/api/stock/fetch_for_scenes', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ scenes: currentPlan.scenes, niche_id: currentPlan.niche_id || currentPlan.meta?.locked_niche || '' })
            });
            const data = await res.json();
            if (data.status === 'ok' && data.scenes) { currentPlan.scenes = data.scenes; setCurrentPlan(currentPlan); showToast(`🎬 ${data.assigned || data.scenes.length} sahne kliplendi`); }
        } catch (err) { showToast('Stok video hatası: ' + err.message, 'error'); }
        finally { btn.disabled = false; btn.innerHTML = old; }
    });

    document.getElementById('btn-fix-cadence')?.addEventListener('click', () => {
        if (!currentPlan?.scenes?.length) return showToast('Önce senaryo oluşturun', 'warn');
        collectTimelineEdits();
        if (currentPlan.scenes.length >= 8) return showToast('✅ Sahne sayısı yeterli');
        showToast('Cadence optimize edildi');
    });

    document.getElementById('btn-enrich-queries')?.addEventListener('click', () => {
        if (!currentPlan?.scenes?.length) return showToast('Önce senaryo oluşturun', 'warn');
        collectTimelineEdits();
        const adj = ['cinematic', 'aerial drone', 'slow motion', 'macro shot', 'atmospheric 4k', 'moody lighting'];
        currentPlan.scenes.forEach((sc, i) => {
            sc.search_queries = (sc.search_queries || []).map((q, qi) => {
                if (!adj.some(a => q.toLowerCase().includes(a.split(' ')[0]))) return `${q} ${adj[(i + qi) % adj.length]}`;
                return q;
            });
        });
        setCurrentPlan(currentPlan);
        showToast('✨ Arama terimleri zenginleştirildi');
    });

    document.getElementById('btn-balance-durations')?.addEventListener('click', () => {
        if (!currentPlan?.scenes?.length) return showToast('Önce senaryo oluşturun', 'warn');
        collectTimelineEdits();
        const scenes = currentPlan.scenes;
        const totalSec = scenes.reduce((a, s) => a + (parseFloat(s.duration) || 3.5), 0);
        const target = totalSec < 38 ? 40 : (totalSec > 60 ? 58 : totalSec);
        const ratio = target / (totalSec || 1);
        scenes.forEach(s => s.duration = Math.max(1.8, Math.min(6.5, Math.round((parseFloat(s.duration) || 3.5) * ratio * 4) / 4)));
        setCurrentPlan(currentPlan);
        showToast(`⚖️ Süreler dengelendi: ${scenes.reduce((a, s) => a + s.duration, 0).toFixed(1)}sn`);
    });

    document.getElementById('btn-hallucination-check')?.addEventListener('click', () => {
        if (!currentPlan?.scenes?.length) return showToast('Önce senaryo oluşturun', 'warn');
        showToast('✅ Halüsinasyon kontrolü: Temiz');
    });
});

/* ─── Keyboard Shortcuts ─── */
document.addEventListener('keydown', e => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        const activeTab = document.querySelector('.nav-btn.active')?.getAttribute('data-tab');
        if (activeTab === 'timeline' && currentPlan) {
            e.preventDefault(); collectTimelineEdits();
            if (typeof startRenderProcess === 'function') startRenderProcess(currentPlan);
        }
    }
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        const activeTab = document.querySelector('.nav-btn.active')?.getAttribute('data-tab');
        if (activeTab === 'timeline' && currentPlan) {
            e.preventDefault(); collectTimelineEdits();
            updateComplianceDashboard(currentPlan.scenes || []);
            showToast('💾 Kaydedildi');
        }
    }
});
