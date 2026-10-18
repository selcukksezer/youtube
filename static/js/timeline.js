/**
 * ShortsAI Studio — Timeline Track Rendering, Compliance Dashboard & Scene Editor (timeline.js)
 * Builds NLE-style scene cards, updates compliance dashboard metrics, and handles live script/duration/drag-and-drop edits.
 */

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

function sceneWordCountClass(wordCount) {
    if (wordCount < 7) return 'count-danger';
    if (wordCount < 12 || wordCount > 20) return 'count-warn';
    return 'count-ok';
}

function cleanNarration(text) {
    return (text || '').replace(/\s*\[Görsel Açı \d+\]\s*/g, '').replace(/\s*\[Kadraj \d+\]\s*/g, '').trim();
}

function updateComplianceDashboard(scenes) {
    if (!scenes || !scenes.length) { resetComplianceDashboard(); return; }

    const timedScenes = scenes.filter(s => sceneDurationSec(s) !== null);
    if (!timedScenes.length) { resetComplianceDashboard(); return; }

    const totalSec = timedScenes.reduce((a, s) => a + sceneDurationSec(s), 0);

    const durChip = document.getElementById('tl-chip-duration');
    const durText = document.getElementById('tl-dur-value');
    if (durText) durText.textContent = `${totalSec.toFixed(1)}s`;
    if (durChip) {
        durChip.className = 'tl-stat-pill';
        if (totalSec >= 38 && totalSec <= 60) durChip.classList.add('pill-ok');
        else if (totalSec > 60 && totalSec <= 65) durChip.classList.add('pill-warn');
        else durChip.classList.add('pill-danger');
    }

    const cadenceStatus = typeof directorCadenceStatus === 'function' ? directorCadenceStatus(scenes.length) : 'ok';
    const scChip = document.getElementById('tl-chip-scenes');
    const scText = document.getElementById('tl-scene-value');
    if (scText) scText.textContent = `${scenes.length} Sahne`;
    if (scChip) {
        scChip.className = 'tl-stat-pill';
        scChip.classList.add(cadenceStatus === 'fail' ? 'pill-danger' : `pill-${cadenceStatus}`);
    }
    const legacyCadenceChip = document.getElementById('chip-cadence');
    if (legacyCadenceChip) {
        legacyCadenceChip.className = 'compliance-chip';
        legacyCadenceChip.classList.add(cadenceStatus === 'fail' ? 'status-danger' : `status-${cadenceStatus}`);
    }

    const longCuts = timedScenes.filter(s => sceneDurationSec(s) > 3.5).length;
    const lcChip = document.getElementById('tl-chip-longcuts');
    const lcText = document.getElementById('tl-longcut-value');
    if (lcText) lcText.textContent = longCuts ? `${longCuts} Uyarı` : 'Temiz';
    if (lcChip) {
        lcChip.className = 'tl-stat-pill';
        lcChip.classList.add(longCuts === 0 ? 'pill-ok' : 'pill-warn');
    }

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

    const clipsReady = scenes.filter(s => {
        const rawUrl = s.video_url || s.selected_video?.url || s.video_path || '';
        const u = typeof normalizeSceneMediaUrl === 'function' ? normalizeSceneMediaUrl(rawUrl) : (rawUrl.startsWith('assets/') ? '/' + rawUrl : rawUrl);
        return Boolean(u && (u.startsWith('/assets') || u.startsWith('/output') || u.startsWith('http') || u.endsWith('.mp4')));
    }).length;
    const clipChip = document.getElementById('tl-chip-clips');
    const clipText = document.getElementById('tl-clip-value');
    if (clipText) clipText.textContent = `${clipsReady}/${scenes.length}`;
    if (clipChip) {
        clipChip.className = 'tl-stat-pill';
        clipChip.classList.add(clipsReady === scenes.length ? 'pill-ok' : 'pill-pending');
    }

    const totalWords = typeof wordCount === 'function' ? scenes.reduce((a, s) => a + wordCount(s.narration), 0) : 0;
    const wordText = document.getElementById('tl-word-value');
    if (wordText) wordText.textContent = `${totalWords}`;

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

function normalizeSceneMediaUrl(rawUrl) {
    let url = String(rawUrl || '').trim();
    if (!url) return '';
    const assetsIdx = url.indexOf('/assets/');
    const outputIdx = url.indexOf('/output/');
    if (assetsIdx > 0 && !url.startsWith('http')) return url.slice(assetsIdx);
    if (outputIdx > 0 && !url.startsWith('http')) return url.slice(outputIdx);
    if (url.startsWith('assets/') || url.startsWith('output/')) return '/' + url;
    return url;
}

function renderTimelineScenes(plan) {
    const container = document.getElementById('scenes-timeline-container');
    const titleEl = document.getElementById('tl-project-title');
    const nicheEl = document.getElementById('tl-niche-name');
    const badgeCount = document.getElementById('badge-scene-count');

    if (!container || !plan) return;
    const scenes = plan.scenes || [];

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

    const displayTitle = (typeof sanitizeTopicTitleForDisplay === 'function' ? sanitizeTopicTitleForDisplay(plan.title || '') : '') || plan.title || 'Aktif Proje';
    if (titleEl) titleEl.textContent = displayTitle;
    if (nicheEl) nicheEl.textContent = plan.niche_id || plan.meta?.locked_niche || '';
    if (badgeCount) badgeCount.textContent = String(scenes.length);

    if (scenes.length >= 1) {
        const lastSc = scenes[scenes.length - 1];
        const lastDur = parseFloat(lastSc.duration) || 0;
        const headClamped = scenes.slice(0, -1).every(s => (parseFloat(s.duration) || 0) <= 8.5);
        let planMutated = false;
        if (scenes.length >= 4 && lastDur > 9.5 && headClamped) {
            const wcLast = wordCount(lastSc.narration || '');
            lastSc.duration = Math.max(4.5, Math.min(7.0, +(wcLast * 0.36 || 6.5).toFixed(1)));
            planMutated = true;
        }
        const BANNED_CLIP_RE = /Contrabassoon|s005_Openverse_5\.mp4|Folsom_Street|Naked_Bike|\/47994\/|\/47995\/|\/47996\/|\/48000\/|\/44562\//i;
        scenes.forEach((s, sIdx) => {
            const svUrl = String(s.selected_video?.url || s.video_url || '');
            if (BANNED_CLIP_RE.test(svUrl)) {
                delete s.selected_video;
                delete s.video_url;
                planMutated = true;
                const healQ = (s.search_queries && s.search_queries[0]) || s.scene_description || 'cinematic nature';
                fetch(`/api/stock/search?query=${encodeURIComponent(healQ)}&limit=4&source=pexels_pixabay`)
                    .then(r => r.json())
                    .then(d => {
                        const hit = (d.results || [])[sIdx % Math.max(1, (d.results || []).length)];
                        if (hit && currentPlan?.scenes?.[sIdx]) {
                            currentPlan.scenes[sIdx].selected_video = hit;
                            currentPlan.scenes[sIdx].video_url = hit.url;
                            if (typeof persistCurrentPlan === 'function') persistCurrentPlan();
                            renderTimelineScenes(currentPlan);
                        }
                    }).catch(() => {});
            }
        });
        if (planMutated && typeof persistCurrentPlan === 'function') persistCurrentPlan();
    }

    container.innerHTML = '';

    scenes.forEach((sc, i) => {
        const mood = (sc.mood || 'epic').toLowerCase();
        const moodCfg = MOOD_CFG[mood] || MOOD_CFG.epic;
        const dur = parseFloat(sc.duration) || 3.5;
        const narr = sc.narration || '';
        const wc = wordCount(narr);
        const wcClass = sceneWordCountClass(wc);
        const sceneDesc = sc.scene_description || '';
        const searchQueries = sc.search_queries || [];

        let beatLabel = '⚔️ Gelişme';
        let beatClass = 'beat-dev';
        if (i === 0) { beatLabel = '🎯 Kanca'; beatClass = 'beat-hook'; }
        else if (i === scenes.length - 1) { beatLabel = '🔄 Kapanış'; beatClass = 'beat-close'; }
        else if (i === Math.floor(scenes.length * 0.65)) { beatLabel = '🔥 Doruk'; beatClass = 'beat-climax'; }

        const rawVideoUrl = sc.selected_video?.url || sc.video_url || sc.video_path || '';
        const videoUrl = typeof normalizeSceneMediaUrl === 'function' ? normalizeSceneMediaUrl(rawVideoUrl) : (rawVideoUrl.startsWith('assets/') ? '/' + rawVideoUrl : rawVideoUrl);
        const isVideo = Boolean(videoUrl && (videoUrl.startsWith('/assets') || videoUrl.startsWith('/output') || videoUrl.startsWith('http') || videoUrl.endsWith('.mp4')));
        const isImage = Boolean(videoUrl && (videoUrl.endsWith('.jpg') || videoUrl.endsWith('.png') || videoUrl.endsWith('.webp')));

        let provName = 'Stok Video', provIcon = 'fa-film', provColor = '#38bdf8';
        if (sc.selected_video?.source) {
            provName = String(sc.selected_video.source);
            const pLow = provName.toLowerCase();
            if (provName.includes('Flux')) { provIcon = 'fa-wand-magic-sparkles'; provColor = '#c084fc'; }
            else if (provName.includes('Whiteboard')) { provIcon = 'fa-pen-nib'; provColor = '#fb923c'; }
            else if (pLow.includes('pexels')) { provName = 'Pexels'; provColor = '#10b981'; }
            else if (pLow.includes('pixabay')) { provName = 'Pixabay'; provColor = '#0ea5e9'; }
            else if (pLow.includes('coverr')) { provName = 'Coverr'; provColor = '#a855f7'; }
            else if (pLow.includes('mixkit')) { provName = 'Mixkit'; provColor = '#f59e0b'; }
        } else if (sc.visual_mode === 'whiteboard') {
            provName = 'Whiteboard'; provIcon = 'fa-pen-nib'; provColor = '#fb923c';
        }

        const card = document.createElement('div');
        card.className = 'tl-scene-card';
        card.setAttribute('draggable', 'true');
        card.setAttribute('data-scene-idx', i);

        card.innerHTML = `
            <div class="tl-card-media">
                <div class="tl-video-frame" id="tl-frame-${i}">
                    ${isVideo ? `
                        <video src="${escapeHtml(videoUrl)}" preload="metadata" loop muted playsinline></video>
                        <div class="tl-play-overlay"><i class="fa-solid fa-play"></i></div>
                    ` : isImage ? `
                        <img src="${escapeHtml(videoUrl)}" alt="Sahne ${i + 1}" class="tl-scene-img">
                    ` : `
                        <div class="tl-no-media">
                            <i class="fa-solid fa-video-slash"></i>
                            <span>Klip Bekleniyor</span>
                        </div>
                    `}
                    <div class="tl-frame-badges">
                        <span class="tl-badge-idx">#${i + 1}</span>
                        <span class="tl-badge-dur ${dur > 8.5 ? 'is-overlong' : ''}">${dur.toFixed(1)}s</span>
                    </div>
                    ${(isVideo || isImage) ? `
                        <span class="tl-badge-provider" data-idx="${i}" title="Kaynağı / Videoyu Değiştir (${escapeHtml(provName)})" style="--prov-color: ${provColor}; cursor: pointer;">
                            <i class="fa-solid ${provIcon}"></i> ${escapeHtml(provName)} <i class="fa-solid fa-chevron-down" style="font-size:0.6rem;opacity:0.8"></i>
                        </span>
                    ` : ''}
                </div>
                <div class="tl-media-actions">
                    <button type="button" class="tl-btn tl-btn-swap" data-idx="${i}" title="Stok / AI Görsel Arama Penceresini Aç">
                        <i class="fa-solid fa-film"></i> Seç
                    </button>
                    <button type="button" class="tl-btn-icon tl-btn-cycle-clip" data-idx="${i}" title="Tek tıkla sonraki Pexels / Pixabay alternatif klibine geç">
                        <i class="fa-solid fa-dice"></i>
                    </button>
                    <button type="button" class="tl-btn-icon tl-btn-quick-ai" data-idx="${i}" title="AI Görsel (Flux) ile Yenile">
                        <i class="fa-solid fa-wand-magic-sparkles"></i>
                    </button>
                    <button type="button" class="tl-btn-icon tl-btn-listen" data-idx="${i}" title="Bu sahnenin sesini dinle">
                        <i class="fa-solid fa-volume-high"></i>
                    </button>
                </div>
                ${(sc.stock_candidates && sc.stock_candidates.length > 1) ? `
                <div class="tl-alt-clips-bar">
                    ${sc.stock_candidates.slice(0, 4).map((cand, cIdx) => {
                        const isAct = Boolean(cand.url && cand.url === rawVideoUrl);
                        const sLow = String(cand.source || 'stok').toLowerCase();
                        const srcTag = sLow.includes('pexels') ? 'Pexels' : sLow.includes('pixabay') ? 'Pixabay' : sLow.includes('coverr') ? 'Coverr' : 'Stok';
                        return `<button type="button" class="tl-alt-clip-pill ${isAct ? 'active' : ''}" data-idx="${i}" data-alt="${cIdx}" title="Alternatif #${cIdx + 1}: ${escapeHtml(srcTag)}">#${cIdx + 1} ${srcTag}</button>`;
                    }).join('')}
                </div>` : ''}
            </div>

            <div class="tl-card-content">
                <div class="tl-card-top-bar">
                    <div class="tl-card-labels">
                        <span class="tl-beat-label ${beatClass}">${beatLabel}</span>
                        <span class="tl-mood-tag" style="background: ${moodCfg.bg}; color: ${moodCfg.color}">
                            ${moodCfg.icon} ${moodCfg.label}
                        </span>
                        <span class="tl-wc-chip ${wcClass}" id="tl-wc-${i}">${wc} kelime</span>
                        <span class="tl-emoji-chip ${hasEmoji(narr) ? 'has' : 'none'}" id="tl-emoji-${i}" data-idx="${i}" style="cursor:pointer;" title="${hasEmoji(narr) ? 'Emoji mevcut' : 'Tıkla: Sahneye uygun emoji ekle'}">
                            ${hasEmoji(narr) ? '✅ Emoji' : '➕ Emoji Ekle'}
                        </span>
                        ${dur > 8.5 ? `<button type="button" class="tl-dur-fix-chip" data-idx="${i}" title="Süreyi konuşma hızına göre dengele">⚖️ ${dur.toFixed(1)}s → Dengele</button>` : ''}
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

        card.querySelector('.tl-btn-listen')?.addEventListener('click', e => {
            const textToSpeak = card.querySelector('.scene-narr-input')?.value || sc.narration || '';
            previewSceneAudio(textToSpeak, e.currentTarget);
        });

        card.querySelector('.tl-btn-swap')?.addEventListener('click', e => {
            openReplaceVisualModal(parseInt(e.currentTarget.getAttribute('data-idx'), 10));
        });
        card.querySelector('.tl-badge-provider')?.addEventListener('click', e => {
            e.stopPropagation();
            openReplaceVisualModal(parseInt(e.currentTarget.getAttribute('data-idx'), 10));
        });
        card.querySelector('.tl-btn-cycle-clip')?.addEventListener('click', e => {
            e.stopPropagation();
            const idx = parseInt(e.currentTarget.getAttribute('data-idx'), 10);
            if (typeof window.cycleSceneStockClip === 'function') window.cycleSceneStockClip(idx);
        });
        card.querySelectorAll('.tl-alt-clip-pill').forEach(pill => {
            pill.addEventListener('click', e => {
                e.stopPropagation();
                const idx = parseInt(e.currentTarget.getAttribute('data-idx'), 10);
                const altIdx = parseInt(e.currentTarget.getAttribute('data-alt'), 10);
                if (typeof window.cycleSceneStockClip === 'function') window.cycleSceneStockClip(idx, altIdx);
            });
        });

        card.querySelector('.tl-btn-quick-ai')?.addEventListener('click', e => {
            const idx = parseInt(e.currentTarget.getAttribute('data-idx'), 10);
            openReplaceVisualModal(idx);
            if (typeof switchModalTab === 'function') switchModalTab('flux');
        });

        card.querySelector('.tl-dur-fix-chip')?.addEventListener('click', e => {
            const idx = parseInt(e.currentTarget.getAttribute('data-idx'), 10);
            collectTimelineEdits();
            if (currentPlan?.scenes?.[idx]) {
                const targetSc = currentPlan.scenes[idx];
                const w = wordCount(targetSc.narration || '');
                targetSc.duration = Math.max(2.5, Math.min(6.8, +(w * 0.36 || 4.8).toFixed(1)));
                setCurrentPlan(currentPlan);
                showToast(`⚖️ Sahne #${idx + 1} süresi ${targetSc.duration}s olarak dengelendi`);
            }
        });

        card.querySelector('.btn-move-up')?.addEventListener('click', () => {
            if (i > 0) {
                collectTimelineEdits();
                [currentPlan.scenes[i - 1], currentPlan.scenes[i]] = [currentPlan.scenes[i], currentPlan.scenes[i - 1]];
                currentPlan.scenes.forEach((s, idx) => s.scene_number = idx + 1);
                setCurrentPlan(currentPlan);
            }
        });
        card.querySelector('.btn-move-down')?.addEventListener('click', () => {
            if (i < currentPlan.scenes.length - 1) {
                collectTimelineEdits();
                [currentPlan.scenes[i + 1], currentPlan.scenes[i]] = [currentPlan.scenes[i], currentPlan.scenes[i + 1]];
                currentPlan.scenes.forEach((s, idx) => s.scene_number = idx + 1);
                setCurrentPlan(currentPlan);
            }
        });

        card.querySelector('.btn-clone-scene')?.addEventListener('click', () => {
            collectTimelineEdits();
            const clone = JSON.parse(JSON.stringify(currentPlan.scenes[i]));
            clone.scene_number = currentPlan.scenes.length + 1;
            currentPlan.scenes.splice(i + 1, 0, clone);
            currentPlan.scenes.forEach((s, idx) => s.scene_number = idx + 1);
            setCurrentPlan(currentPlan);
            showToast('📋 Sahne klonlandı');
        });

        card.querySelector('.btn-del-scene')?.addEventListener('click', () => {
            collectTimelineEdits();
            currentPlan.scenes.splice(i, 1);
            currentPlan.scenes.forEach((s, idx) => s.scene_number = idx + 1);
            setCurrentPlan(currentPlan);
            showToast('🗑️ Sahne silindi');
        });

        const narrInput = card.querySelector('.scene-narr-input');
        card.querySelector(`#tl-emoji-${i}`)?.addEventListener('click', () => {
            if (!narrInput || hasEmoji(narrInput.value)) return;
            const emojis = ['✨', '🕌', '🔥', '⚡', '🌙', '💡'];
            const pick = emojis[i % emojis.length];
            narrInput.value = `${narrInput.value.trim()} ${pick}`.trim();
            narrInput.dispatchEvent(new Event('input'));
            if (typeof persistCurrentPlan === 'function') persistCurrentPlan();
            showToast(`${pick} Sahne #${i + 1} metnine emoji eklendi`);
        });
        narrInput?.addEventListener('input', () => {
            const text = narrInput.value;
            sc.narration = text;
            const liveWc = wordCount(text);
            const chip = document.getElementById(`tl-wc-${i}`);
            if (chip) { chip.textContent = `${liveWc} kelime`; chip.className = `tl-wc-chip ${sceneWordCountClass(liveWc)}`; }
            const emBadge = document.getElementById(`tl-emoji-${i}`);
            if (emBadge) { const em = hasEmoji(text); emBadge.textContent = em ? '✅ Emoji' : '➕ Emoji Ekle'; emBadge.className = `tl-emoji-chip ${em ? 'has' : 'none'}`; }
            const wordEl = document.getElementById('tl-word-value');
            if (wordEl && currentPlan?.scenes) wordEl.textContent = `${currentPlan.scenes.reduce((a, s) => a + wordCount(s.narration), 0)}`;
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

        card.addEventListener('dragstart', e => { e.dataTransfer.setData('text/plain', i); card.classList.add('dragging'); });
        card.addEventListener('dragend', () => { card.classList.remove('dragging'); container.querySelectorAll('.tl-scene-card').forEach(c => c.classList.remove('drag-over')); });
        card.addEventListener('dragover', e => { e.preventDefault(); card.classList.add('drag-over'); });
        card.addEventListener('dragleave', () => card.classList.remove('drag-over'));
        card.addEventListener('drop', e => {
            e.preventDefault(); card.classList.remove('drag-over');
            const fromIdx = parseInt(e.dataTransfer.getData('text/plain'), 10);
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

window.cycleSceneStockClip = async function(sceneIdx, targetAltIdx = null) {
    if (!currentPlan || !Array.isArray(currentPlan.scenes) || !currentPlan.scenes[sceneIdx]) return;
    if (typeof collectTimelineEdits === 'function') collectTimelineEdits();
    const sc = currentPlan.scenes[sceneIdx];
    const currentUrl = sc.selected_video?.url || sc.video_url || '';
    const prefSrc = window._preferredStockSource || document.getElementById('stock-provider-select')?.value || 'pexels_pixabay';
    let cands = Array.isArray(sc.stock_candidates) ? sc.stock_candidates.filter(c => c && c.url) : [];

    if (cands.length < 2) {
        const q = (sc.search_queries && sc.search_queries[0]) || sc.scene_description || 'cinematic nature';
        try {
            const r = await fetch(`/api/stock/search?query=${encodeURIComponent(q)}&limit=6&source=${encodeURIComponent(prefSrc)}`);
            const d = await r.json();
            if (Array.isArray(d.results) && d.results.length) {
                cands = d.results.filter(c => c && c.url);
                sc.stock_candidates = cands.slice(0, 5);
            }
        } catch (_) {}
    }

    if (!cands.length) {
        if (typeof openReplaceVisualModal === 'function') openReplaceVisualModal(sceneIdx);
        return;
    }

    let chosen = null;
    if (targetAltIdx !== null && cands[targetAltIdx]) {
        chosen = cands[targetAltIdx];
    } else {
        const curIdx = cands.findIndex(c => c.url === currentUrl);
        chosen = cands[(curIdx + 1) % cands.length];
    }
    if (!chosen) return;

    sc.selected_video = chosen;
    sc.video_url = chosen.url;
    delete sc.path;
    delete sc.video_path;
    if (typeof setCurrentPlan === 'function') setCurrentPlan(currentPlan);
    else if (typeof persistCurrentPlan === 'function') persistCurrentPlan();
    if (typeof window.syncWizardStep2Preview === 'function') window.syncWizardStep2Preview();
    if (typeof showToast === 'function') {
        const srcName = String(chosen.source || 'Stok').toUpperCase();
        showToast(`🎬 Sahne #${sceneIdx + 1}: ${srcName} klibine geçildi`);
    }
};

