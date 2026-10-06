/**
 * ShortsAI Studio — Timeline & Scene Editor (timeline.js)
 * Covers scene cards rendering, duration slider, word count validator, drag-drop reordering, and timeline actions.
 */


function hasEmoji(text) {
    return /[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{1F1E0}-\u{1F1FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}\u{FE00}-\u{FE0F}\u{1F900}-\u{1F9FF}\u{1FA00}-\u{1FA6F}\u{1FA70}-\u{1FAFF}\u{200D}\u{20E3}]/u.test(text || '');
}

// Helper: Word count
function wordCount(text) {
    return (text || '').trim().split(/\s+/).filter(Boolean).length;
}

// Helper: Clean cutaway markers from narration for display
function cleanNarration(text) {
    return (text || '').replace(/\s*\[Görsel Açı \d+\]\s*/g, '').replace(/\s*\[Kadraj \d+\]\s*/g, '').trim();
}

// Helper: Mood emoji map
const MOOD_ICONS = {
    epic: '🌟', dramatic: '🔴', calm: '🔵', mysterious: '🟣',
    energetic: '⚡', dark: '⬛', bright: '☀️'
};

// ── Compliance Dashboard Update ──
function updateComplianceDashboard(scenes) {
    if (!scenes || scenes.length === 0) {
        resetComplianceDashboard();
        return;
    }
    const timedScenes = scenes.filter(s => sceneDurationSec(s) !== null);
    if (!timedScenes.length) {
        resetComplianceDashboard();
        return;
    }

    const totalSec = timedScenes.reduce((acc, s) => acc + sceneDurationSec(s), 0);

    // Duration band — Madde 494
    const chipDur = document.getElementById('chip-duration-band');
    const chipDurText = document.getElementById('chip-duration-text');
    chipDurText.textContent = `Süre: ${totalSec.toFixed(1)}sn`;
    chipDur.className = 'compliance-chip';
    if (totalSec >= 38 && totalSec <= 60) {
        chipDur.classList.add('status-ok');
    } else if (totalSec > 60 && totalSec <= 65) {
        chipDur.classList.add('status-warn');
    } else {
        chipDur.classList.add('status-danger');
    }

    // Cadence — Madde 88 helper; 8-16 sahne izin, 14 kutsal değil
    const chipCad = document.getElementById('chip-cadence');
    const chipCadText = document.getElementById('chip-cadence-text');
    chipCadText.textContent = `Cadence: ${scenes.length} sahne`;
    chipCad.className = 'compliance-chip';
    if (scenes.length >= 8 && scenes.length <= 16) {
        chipCad.classList.add('status-ok');
    } else if (scenes.length >= 6) {
        chipCad.classList.add('status-warn');
    } else {
        chipCad.classList.add('status-danger');
    }

    // 3.2s advisory — Madde 76 soft warning (AI pacing allowed)
    const longCuts = timedScenes.filter(s => sceneDurationSec(s) > 3.2).length;
    const chip32 = document.getElementById('chip-32s-violations');
    const chip32Text = document.getElementById('chip-32s-text');
    chip32Text.textContent = longCuts ? `3.2sn Uyarı: ${longCuts}` : '3.2sn Uyarı: 0';
    chip32.className = 'compliance-chip';
    if (longCuts === 0) {
        chip32.classList.add('status-ok');
    } else {
        chip32.classList.add('status-warn');
    }

    // Duplicate search terms — Madde 247 (ignore cutaways + adjacent semantic pairs)
    let dupes = 0;
    const queryEntries = [];
    scenes.forEach((s, idx) => {
        if (s.is_visual_cutaway) return;
        const sq = s.search_queries || [];
        if (sq[0]) queryEntries.push({ q: sq[0].toLowerCase().trim(), idx });
    });
    const seen = {};
    queryEntries.forEach(({ q, idx }) => {
        if (seen[q] !== undefined && idx - seen[q] > 1) {
            dupes += 1;
        }
        seen[q] = idx;
    });
    const chipDup = document.getElementById('chip-duplicates');
    const chipDupText = document.getElementById('chip-duplicates-text');
    chipDupText.textContent = `Tekrar: ${dupes}`;
    chipDup.className = 'compliance-chip';
    if (dupes === 0) {
        chipDup.classList.add('status-ok');
    } else {
        chipDup.classList.add('status-warn');
    }

    // Story Arc Bar — Madde 274 (percent of actual duration)
    if (totalSec > 0) {
        const introEnd = totalSec * 0.07;
        const conflictEnd = totalSec * 0.45;
        const climaxEnd = totalSec * 0.75;
        const introEl = document.getElementById('arc-intro');
        const conflictEl = document.getElementById('arc-conflict');
        const climaxEl = document.getElementById('arc-climax');
        const loopEl = document.getElementById('arc-loop');
        if (introEl) introEl.style.width = `${(introEnd / totalSec) * 100}%`;
        if (conflictEl) conflictEl.style.width = `${((conflictEnd - introEnd) / totalSec) * 100}%`;
        if (climaxEl) climaxEl.style.width = `${((climaxEnd - conflictEnd) / totalSec) * 100}%`;
        if (loopEl) loopEl.style.width = `${((totalSec - climaxEnd) / totalSec) * 100}%`;
        const r = (n) => Math.round(n);
        const li = document.getElementById('arc-label-intro');
        const lc = document.getElementById('arc-label-conflict');
        const lx = document.getElementById('arc-label-climax');
        const ll = document.getElementById('arc-label-loop');
        if (li) li.textContent = `🎬 Giriş (0-${r(introEnd)}sn)`;
        if (lc) lc.textContent = `⚔️ Çatışma (${r(introEnd)}-${r(conflictEnd)}sn)`;
        if (lx) lx.textContent = `🔥 Doruk (${r(conflictEnd)}-${r(climaxEnd)}sn)`;
        if (ll) ll.textContent = `🔄 Döngü (${r(climaxEnd)}-${r(totalSec)}sn)`;
    }
}

// ── Main render function ──
function renderTimelineScenes(plan) {
    const container = document.getElementById('scenes-timeline-container');
    const titleEl = document.getElementById('timeline-project-title');
    const totalScenesEl = document.getElementById('timeline-total-scenes');
    const totalDurEl = document.getElementById('timeline-total-duration');
    const badgeSceneCount = document.getElementById('badge-scene-count');

    if (!container || !plan) return;

    const scenes = plan.scenes || [];
    if (!scenes.length) {
        titleEl.textContent = 'Aktif Proje Senaryosu';
        updateTimelineTopicDesc(null);
        totalScenesEl.textContent = '0';
        if (badgeSceneCount) badgeSceneCount.textContent = '0';
        totalDurEl.textContent = '0 sn';
        container.innerHTML = `
            <div class="empty-state-box">
                <i class="fa-solid fa-film"></i>
                <p>Henüz bir senaryo oluşturulmadı. Hızlı Üretim sekmesinden senaryo üretebilirsiniz.</p>
            </div>`;
        updateScriptActionButtons();
        return;
    }

    const displayTitle = sanitizeTopicTitleForDisplay(plan.title || inputTopic?.value || '') || plan.title || 'Adsız';
    titleEl.textContent = `Proje: ${displayTitle}`;
    updateTimelineTopicDesc(plan);
    totalScenesEl.textContent = scenes.length;
    if (badgeSceneCount) badgeSceneCount.textContent = scenes.length;

    const totalSec = scenes.reduce((acc, s) => acc + (parseFloat(s.duration) || 6), 0);
    totalDurEl.textContent = `${totalSec.toFixed(1)} sn`;

    // Build duplicate query map for highlighting
    const queryFreq = {};
    scenes.forEach(s => {
        const q = ((s.search_queries && s.search_queries[0]) || '').toLowerCase().trim();
        if (q) queryFreq[q] = (queryFreq[q] || 0) + 1;
    });

    container.innerHTML = '';
    scenes.forEach((sc, i) => {
        const mood = (sc.mood || 'epic').toLowerCase();
        const isCutaway = sc.is_visual_cutaway === true;
        const dur = sceneDurationSec(sc);
        const durationViolation = false; // 3.2s is advisory only — AI pacing allowed
        const narr = isCutaway ? cleanNarration(sc.narration) : (sc.narration || '');
        const wc = wordCount(narr);
        const hasEm = hasEmoji(narr);
        const searchQueries = sc.search_queries || [];
        const sceneDesc = sc.scene_description || '';

        // Word count class
        let wcClass = 'count-ok';
        if (wc < 10) wcClass = 'count-danger';
        else if (wc > 20) wcClass = 'count-warn';

        // Build CSS classes
        let cardClasses = `scene-item-card mood-${mood}`;
        if (isCutaway) cardClasses += ' is-cutaway';
        if (durationViolation) cardClasses += ' duration-violation';

        const row = document.createElement('div');
        row.className = cardClasses;
        row.setAttribute('draggable', 'true');
        row.setAttribute('data-scene-idx', i);

        // Build search query tags HTML
        let queryTagsHtml = '';
        searchQueries.forEach((q, qi) => {
            const isDupe = qi === 0 && queryFreq[q.toLowerCase().trim()] > 1;
            const labels = ['spesifik', 'orta', 'genel'];
            queryTagsHtml += `<span class="search-query-tag${isDupe ? ' duplicate' : ''}" title="${labels[qi] || ''}">${q}</span>`;
        });

        // Stock / AI / Whiteboard video badge & controls
        let stockVideoHtml = '';
        if (sc.selected_video && sc.selected_video.url) {
            const vid = sc.selected_video;
            const isFlux = (vid.source || '').includes('Flux');
            const isWb = (vid.source || '').includes('Whiteboard');
            const badgeIcon = isFlux ? 'fa-wand-magic-sparkles' : (isWb ? 'fa-pen-nib' : 'fa-video');
            const badgeColor = isFlux ? '#c084fc' : (isWb ? '#fb923c' : '#38bdf8');
            stockVideoHtml = `
                <div class="scene-stock-badge-container">
                    ${vid.thumbnail ? `<img src="${vid.thumbnail}" class="scene-stock-thumb" alt="Klip">` : ''}
                    <span class="scene-stock-provider-tag" style="color: ${badgeColor}; border-color: rgba(255,255,255,0.15);">
                        <i class="fa-solid ${badgeIcon}"></i> ${vid.source || 'Görsel'}
                    </span>
                    <a href="${vid.url}" target="_blank" class="scene-stock-preview-btn"><i class="fa-solid fa-play"></i> Önizle</a>
                    <button type="button" class="btn-swap-stock" data-idx="${i}" title="Stok Video Değiştir"><i class="fa-solid fa-rotate"></i> Stok</button>
                    <button type="button" class="btn-gen-ai-visual" data-idx="${i}" title="0 TL Flux AI Görseli Üret" style="background: rgba(168,85,247,0.18); color: #c084fc; border: 1px solid rgba(168,85,247,0.3); border-radius: 4px; padding: 2px 6px; font-size: 11px; cursor: pointer;"><i class="fa-solid fa-wand-magic-sparkles"></i> Flux AI</button>
                    <button type="button" class="btn-gen-whiteboard" data-idx="${i}" title="Whiteboard Çizimi Üret" style="background: rgba(249,115,22,0.18); color: #fb923c; border: 1px solid rgba(249,115,22,0.3); border-radius: 4px; padding: 2px 6px; font-size: 11px; cursor: pointer;"><i class="fa-solid fa-pen-nib"></i> Çizim</button>
                </div>
            `;
        } else {
            const isWbMode = sc.visual_mode === 'whiteboard' || window.currentPlan?.visual_mode === 'whiteboard';
            stockVideoHtml = `
                <div class="scene-stock-badge-container" style="display: flex; gap: 6px; align-items: center; flex-wrap: wrap;">
                    ${isWbMode
                    ? `<span class="scene-stock-provider-tag" style="color: #fb923c; border-color: rgba(249,115,22,0.3); background: rgba(249,115,22,0.1);"><i class="fa-solid fa-pen-nib"></i> Whiteboard Çizim Modu</span>`
                    : `<span style="font-size: 10px; color: #64748b;"><i class="fa-solid fa-film"></i> Görsel seçilmedi</span>`
                }
                    <button type="button" class="btn-fetch-single-stock" data-idx="${i}"><i class="fa-solid fa-cloud-arrow-down"></i> Stok</button>
                    <button type="button" class="btn-gen-ai-visual" data-idx="${i}" title="0 TL Flux AI Görseli Üret" style="background: rgba(168,85,247,0.18); color: #c084fc; border: 1px solid rgba(168,85,247,0.3); border-radius: 4px; padding: 2px 6px; font-size: 11px; cursor: pointer;"><i class="fa-solid fa-wand-magic-sparkles"></i> Flux AI</button>
                    <button type="button" class="btn-gen-whiteboard" data-idx="${i}" title="Whiteboard Çizimi Üret" style="background: rgba(249,115,22,0.18); color: #fb923c; border: 1px solid rgba(249,115,22,0.3); border-radius: 4px; padding: 2px 6px; font-size: 11px; cursor: pointer;"><i class="fa-solid fa-pen-nib"></i> Çizim</button>
                </div>
            `;
        }

        row.innerHTML = `
            <div class="scene-idx">
                <span class="scene-idx-number">#${i + 1}</span>
                <span class="mood-badge mood-${mood}">${MOOD_ICONS[mood] || '🎬'} ${mood}</span>
                ${isCutaway ? '<span class="cutaway-badge">📐 Açı</span>' : ''}
            </div>
            <div class="scene-body">
                <div class="scene-body-row">
                    <div>
                        <div class="scene-field-label">
                            Seslendirme Metni
                            <span class="word-count-chip ${wcClass}">${wc} klm</span>
                            <span class="emoji-indicator ${hasEm ? 'has-emoji' : 'no-emoji'}">${hasEm ? '✅ Emoji' : '⚠️ Emoji yok'}</span>
                        </div>
                        <textarea class="input-styled scene-narr-input" rows="2" style="resize: vertical; min-height: 36px;">${escapeHtml(narr)}</textarea>
                    </div>
                    <div>
                        <div class="scene-field-label">Görsel Açıklama <span class="field-meta">(scene_description)</span></div>
                        <input type="text" class="input-styled scene-desc-input" value="${escapeHtml(sceneDesc)}" placeholder="İngilizce görsel açıklama...">
                        ${stockVideoHtml}
                    </div>
                </div>
                <div class="scene-body-row-3">
                    <div>
                        <div class="scene-field-label">Stok Arama Terimleri <span class="field-meta">(Madde 89)</span></div>
                        <input type="text" class="input-styled scene-query-input" value="${escapeHtml(searchQueries[0] || '')}" placeholder="Ana arama terimi...">
                        <div class="search-query-tags">${queryTagsHtml}</div>
                    </div>
                    <div>
                        <div class="scene-field-label">Süre</div>
                        <input type="number" class="input-styled scene-dur-input" min="1" max="15" step="0.25" value="${dur}">
                    </div>
                    <div class="scene-actions">
                        <button class="btn-sm btn-clone-scene" data-idx="${i}" title="Sahneyi Klonla"><i class="fa-solid fa-copy"></i></button>
                        <button class="btn-sm btn-del-scene" data-idx="${i}" title="Sahneyi Sil"><i class="fa-solid fa-trash"></i></button>
                    </div>
                </div>
            </div>
        `;
        container.appendChild(row);
    });

    // ── Event handlers ──

    // Swap stock video for single scene
    container.querySelectorAll('.btn-swap-stock').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const idx = parseInt(e.currentTarget.getAttribute('data-idx'));
            const sc = currentPlan.scenes[idx];
            const q = (sc.search_queries && sc.search_queries[0]) || sc.scene_description || 'cinematic motion';
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
            btn.disabled = true;
            try {
                const res = await fetch(`/api/stock/search?query=${encodeURIComponent(q)}&limit=6`);
                const data = await res.json();
                if (data.results && data.results.length > 0) {
                    const currentId = sc.selected_video?.id;
                    const alt = data.results.find(v => v.id !== currentId) || data.results[0];
                    sc.selected_video = alt;
                    renderTimelineScenes(currentPlan);
                    showToast(`🎬 Sahne #${idx + 1} için yeni stok video seçildi!`);
                } else {
                    showToast('⚠️ Alternatif video bulunamadı.', 'warn');
                    btn.innerHTML = '<i class="fa-solid fa-rotate"></i> Değiştir';
                    btn.disabled = false;
                }
            } catch (err) {
                showToast('Hata: ' + err.message, 'error');
                btn.innerHTML = '<i class="fa-solid fa-rotate"></i> Değiştir';
                btn.disabled = false;
            }
        });
    });

    // Fetch single stock video
    container.querySelectorAll('.btn-fetch-single-stock').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const idx = parseInt(e.currentTarget.getAttribute('data-idx'));
            const sc = currentPlan.scenes[idx];
            const q = (sc.search_queries && sc.search_queries[0]) || sc.scene_description || 'cinematic motion';
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
            btn.disabled = true;
            try {
                const niche = currentPlan.niche_id || currentPlan.meta?.locked_niche || '';
                const res = await fetch(`/api/stock/search?query=${encodeURIComponent(q)}&limit=3&niche_id=${encodeURIComponent(niche)}`);
                const data = await res.json();
                if (data.results && data.results.length > 0) {
                    sc.selected_video = data.results[0];
                    renderTimelineScenes(currentPlan);
                    showToast(`🎬 Sahne #${idx + 1} için stok video çekildi!`);
                } else {
                    showToast('⚠️ Video bulunamadı.', 'warn');
                    btn.innerHTML = '<i class="fa-solid fa-cloud-arrow-down"></i> Stok Çek';
                    btn.disabled = false;
                }
            } catch (err) {
                showToast('Hata: ' + err.message, 'error');
                btn.innerHTML = '<i class="fa-solid fa-cloud-arrow-down"></i> Stok Çek';
                btn.disabled = false;
            }
        });
    });

    // Delete scene
    container.querySelectorAll('.btn-del-scene').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const idx = parseInt(e.currentTarget.getAttribute('data-idx'));
            currentPlan.scenes.splice(idx, 1);
            renderTimelineScenes(currentPlan);
        });
    });

    // Clone scene
    container.querySelectorAll('.btn-clone-scene').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const idx = parseInt(e.currentTarget.getAttribute('data-idx'));
            const clone = JSON.parse(JSON.stringify(currentPlan.scenes[idx]));
            clone.scene_number = currentPlan.scenes.length + 1;
            clone.is_visual_cutaway = false;
            currentPlan.scenes.splice(idx + 1, 0, clone);
            renderTimelineScenes(currentPlan);
            showToast('📋 Sahne klonlandı');
        });
    });

    // ── Drag & Drop ──
    let dragSrcIdx = null;
    container.querySelectorAll('.scene-item-card').forEach(card => {
        card.addEventListener('dragstart', (e) => {
            dragSrcIdx = parseInt(card.getAttribute('data-scene-idx'));
            card.classList.add('dragging');
            e.dataTransfer.effectAllowed = 'move';
        });
        card.addEventListener('dragend', () => {
            card.classList.remove('dragging');
            container.querySelectorAll('.scene-item-card').forEach(c => c.classList.remove('drag-over'));
        });
        card.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'move';
            card.classList.add('drag-over');
        });
        card.addEventListener('dragleave', () => {
            card.classList.remove('drag-over');
        });
        card.addEventListener('drop', (e) => {
            e.preventDefault();
            const targetIdx = parseInt(card.getAttribute('data-scene-idx'));
            if (dragSrcIdx !== null && dragSrcIdx !== targetIdx && currentPlan && currentPlan.scenes) {
                const [moved] = currentPlan.scenes.splice(dragSrcIdx, 1);
                currentPlan.scenes.splice(targetIdx, 0, moved);
                // Renumber
                currentPlan.scenes.forEach((s, si) => s.scene_number = si + 1);
                renderTimelineScenes(currentPlan);
                showToast('🔀 Sahne sırası güncellendi');
            }
            dragSrcIdx = null;
        });
    });

    // Update compliance dashboard
    updateComplianceDashboard(scenes);
}

// ── Add scene manually ──
document.getElementById('btn-add-scene-manual')?.addEventListener('click', () => {
    if (!currentPlan) currentPlan = { title: inputTopic.value, scenes: [] };
    currentPlan.scenes.push({
        scene_number: currentPlan.scenes.length + 1,
        narration: "Yeni sahne anlatım parçası...",
        scene_description: "Wide angle cinematic shot of the scene",
        search_queries: ["cinematic nature", "landscape aerial", "nature"],
        duration: 3,
        mood: "epic"
    });
    renderTimelineScenes(currentPlan);
    showToast('➕ Yeni sahne eklendi');
});

// ── Smart Buttons ──

// Auto-fetch stock videos for all scenes — Item 89 & 130
document.getElementById('btn-fetch-stock-clips')?.addEventListener('click', async () => {
    if (!currentPlan || !currentPlan.scenes || currentPlan.scenes.length === 0) {
        return showToast('⚠️ Önce senaryo oluşturun', 'warn');
    }
    const btn = document.getElementById('btn-fetch-stock-clips');
    const oldHtml = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Stok Videolar Çekiliyor...';
    showToast('📡 Pexels ve Pixabay kütüphanelerinden en iyi dikey videolar taranıyor...');
    try {
        collectTimelineEdits();
        const res = await fetch('/api/stock/fetch_for_scenes', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                scenes: currentPlan.scenes,
                niche_id: currentPlan.niche_id || currentPlan.meta?.locked_niche || ''
            })
        });
        const data = await res.json();
        if (data.status === 'ok' && data.scenes) {
            currentPlan.scenes = data.scenes;
            renderTimelineScenes(currentPlan);
            const assigned = data.assigned ?? data.scenes.filter(s => s.selected_video?.url).length;
            if (assigned > 0) {
                showToast(`🎬 ${assigned}/${data.total || data.scenes.length} sahne için stok/görsel atandı`);
            } else if (data.paid_keys === false) {
                showToast('⚠️ PEXELS_API_KEY / PIXABAY_API_KEY boş — keyless kaynak da sonuç vermedi. Anahtar ekle veya custom_backgrounds doldur.', 'warn');
            } else {
                showToast('⚠️ Stok eşleşmesi bulunamadı — sorguları zenginleştirip tekrar dene', 'warn');
            }
        }
    } catch (err) {
        showToast('⚠️ Stok video çekme hatası: ' + err.message, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = oldHtml;
    }
});

// Cadence fix — Madde 88
document.getElementById('btn-fix-cadence')?.addEventListener('click', () => {
    if (!currentPlan || !currentPlan.scenes || currentPlan.scenes.length === 0) return showToast('Once senaryo olusturun', 'warn');
    collectTimelineEdits();
    const scenes = currentPlan.scenes;
    const totalDuration = scenes.reduce((acc, s) => acc + (parseFloat(s.duration) || 6), 0);
    if (totalDuration < 30 || scenes.length >= 14) return showToast('✅ Cadence zaten yeterli');

    let cutsNeeded = 14 - scenes.length;
    let cutawayCounter = 1;
    const cutawayAdjs = ['macro closeup', 'cinematic angle', 'reaction detail', 'slow motion cutaway'];
    const expanded = [];
    for (const sc of scenes) {
        const dur = parseFloat(sc.duration) || 6;
        if (cutsNeeded > 0 && dur >= 3.5) {
            const half1 = Math.round((dur / 2) * 100) / 100;
            const half2 = Math.round((dur - half1) * 100) / 100;
            cutsNeeded--;

            const words = (sc.narration || '').split(' ');
            let narr1 = sc.narration || '';
            let narr2 = `${sc.narration || ''} [Görsel Açı ${cutawayCounter}]`;
            if (words.length >= 6) {
                const mid = Math.floor(words.length / 2);
                narr1 = words.slice(0, mid).join(' ');
                narr2 = words.slice(mid).join(' ');
            }

            const sq = sc.search_queries || ['cinematic visual'];
            const cadj = cutawayAdjs[cutawayCounter % cutawayAdjs.length];
            const q1 = sq[0] || 'cinematic motion';
            const q2 = sq[1] ? `${sq[1]} ${cadj}` : `${q1} ${cadj}`;
            const queries1 = [q1, sq[1] || 'dramatic lighting'];
            const queries2 = [q2, sq[2] || 'cinematic slow motion'];

            const sc1 = { ...sc, duration: half1, narration: narr1, search_queries: queries1 };
            const sc2 = { ...sc, duration: half2, is_visual_cutaway: true, narration: narr2, search_queries: queries2, scene_description: `Cutaway dynamic angle showing ${q2}` };
            cutawayCounter++;
            expanded.push(sc1, sc2);
        } else {
            expanded.push({ ...sc });
        }
    }
    // Further split if needed
    while (expanded.length < 14) {
        const maxIdx = expanded.reduce((best, s, i) => (s.duration || 0) > (expanded[best].duration || 0) ? i : best, 0);
        if ((expanded[maxIdx].duration || 0) < 1.5) break;
        const target = expanded[maxIdx];
        const h1 = Math.round((target.duration / 2) * 100) / 100;
        const h2 = Math.round((target.duration - h1) * 100) / 100;

        const words = (target.narration || '').split(' ');
        let narr1 = target.narration || '';
        let narr2 = `${target.narration || ''} [Kadraj ${cutawayCounter}]`;
        if (words.length >= 6) {
            const mid = Math.floor(words.length / 2);
            narr1 = words.slice(0, mid).join(' ');
            narr2 = words.slice(mid).join(' ');
        }

        const sq = target.search_queries || ['cinematic visual'];
        const cadj = cutawayAdjs[cutawayCounter % cutawayAdjs.length];
        const q1 = sq[0] || 'cinematic motion';
        const q2 = sq[1] ? `${sq[1]} ${cadj}` : `${q1} ${cadj}`;

        const t1 = { ...target, duration: h1, narration: narr1, search_queries: [q1, sq[1] || 'dramatic lighting'] };
        const t2 = { ...target, duration: h2, is_visual_cutaway: true, narration: narr2, search_queries: [q2, sq[2] || 'cinematic slow motion'], scene_description: `Cutaway dynamic angle showing ${q2}` };
        cutawayCounter++;
        expanded.splice(maxIdx, 1, t1, t2);
    }
    expanded.forEach((s, i) => s.scene_number = i + 1);
    currentPlan.scenes = expanded;
    renderTimelineScenes(currentPlan);
    showToast(`✂️ Cadence düzeltildi: ${expanded.length} sahne`);
});

// Enrich search queries — Madde 89
document.getElementById('btn-enrich-queries')?.addEventListener('click', () => {
    if (!currentPlan || !currentPlan.scenes) return showToast('Once senaryo olusturun', 'warn');
    collectTimelineEdits();
    const adjectives = ['cinematic', 'drone', 'aerial', 'slow motion', 'macro', 'atmospheric', '4k', 'moody'];
    currentPlan.scenes.forEach((sc, i) => {
        const sq = sc.search_queries || [];
        sc.search_queries = sq.map((q, qi) => {
            const ql = q.toLowerCase();
            if (!adjectives.some(a => ql.includes(a))) {
                return `${q} ${adjectives[(i + qi) % adjectives.length]}`;
            }
            return q;
        });
    });
    setCurrentPlan(currentPlan);
    showToast('Arama terimleri zenginlestirildi');
});

// Balance durations — Madde 494
document.getElementById('btn-balance-durations')?.addEventListener('click', () => {
    if (!currentPlan || !currentPlan.scenes || currentPlan.scenes.length === 0) return showToast('Once senaryo olusturun', 'warn');
    collectTimelineEdits();
    const scenes = currentPlan.scenes;
    const totalSec = scenes.reduce((acc, s) => acc + (parseFloat(s.duration) || 6), 0);
    const targetTotal = totalSec < 38 ? 38 : 60;
    if (totalSec >= 38 && totalSec <= 60) return showToast('Sure izin bandinda (38-60sn, tavan 60)');

    const ratio = targetTotal / totalSec;
    const maxPerScene = 7.5;
    scenes.forEach(s => {
        s.duration = Math.max(1.5, Math.min(maxPerScene, Math.round((parseFloat(s.duration) || 3) * ratio * 4) / 4));
    });
    renderTimelineScenes(currentPlan);
    const newTotal = scenes.reduce((acc, s) => acc + s.duration, 0);
    persistCurrentPlan();
    showToast(`Sureler dengelendi: ${newTotal.toFixed(1)}sn`);
});

// Hallucination check — Madde 90
document.getElementById('btn-hallucination-check')?.addEventListener('click', () => {
    if (!currentPlan || !currentPlan.scenes) return showToast('⚠️ Önce senaryo oluşturun', 'warn');
    const issues = [];
    const title = (currentPlan.title || '').toLowerCase();
    const ancientMarkers = ['marcus aurelius', 'roma', 'antik', 'stoa', 'osmanlı', 'fatih', 'platon', 'aristoteles', 'sezar'];
    const isAncient = ancientMarkers.some(m => title.includes(m));
    const yearPattern = /\b(1[0-9]{3}|20[0-9]{2})\b/g;

    currentPlan.scenes.forEach((sc, i) => {
        const narr = sc.narration || '';
        let match;
        while ((match = yearPattern.exec(narr)) !== null) {
            const yr = parseInt(match[1]);
            if (yr > 2030) {
                issues.push(`Sahne #${i + 1}: Gelecek yıl (${yr}) — halüsinasyon`);
            } else if (isAncient && yr >= 1800) {
                issues.push(`Sahne #${i + 1}: Antik konu için modern yıl (${yr}) — anakronizm`);
            }
        }
    });

    if (issues.length === 0) {
        showToast('✅ Halüsinasyon tespit edilmedi — temiz');
    } else {
        showToast(`⚠️ ${issues.length} potansiyel halüsinasyon tespit edildi`, 'warn');
        alert('Halüsinasyon Raporu:\n\n' + issues.join('\n'));
    }
});

// ── Render from timeline (collect edits) ──
document.getElementById('btn-render-from-timeline')?.addEventListener('click', () => {
    collectTimelineEdits();
    startRenderProcess(currentPlan);
});

function collectTimelineEdits() {
    if (currentPlan && currentPlan.scenes) {
        const narrInputs = document.querySelectorAll('.scene-narr-input');
        const descInputs = document.querySelectorAll('.scene-desc-input');
        const queryInputs = document.querySelectorAll('.scene-query-input');
        const durInputs = document.querySelectorAll('.scene-dur-input');
        currentPlan.scenes.forEach((sc, i) => {
            if (narrInputs[i]) sc.narration = narrInputs[i].value;
            if (descInputs[i]) sc.scene_description = descInputs[i].value;
            if (queryInputs[i]) sc.search_queries = [queryInputs[i].value, ...(sc.search_queries || []).slice(1)];
            if (durInputs[i]) sc.duration = parseFloat(durInputs[i].value) || 6;
        });
        currentPlan.full_narration = currentPlan.scenes.map(s => s.narration || '').filter(Boolean).join(' ');
        persistCurrentPlan();
        const hard = getNarrationIssues(currentPlan.scenes);
        updateRenderButtonsBlocked(hard.length > 0, hard[0]);
    }
}

// ── Keyboard Shortcuts — Madde 443 ──
document.addEventListener('keydown', (e) => {
    // Ctrl+Enter — Render
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        const activeTab = document.querySelector('.nav-btn.active')?.getAttribute('data-tab');
        if (activeTab === 'timeline' && currentPlan) {
            collectTimelineEdits();
            startRenderProcess(currentPlan);
        }
    }
    // Ctrl+S — Save/sync edits
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        collectTimelineEdits();
        if (currentPlan) {
            updateComplianceDashboard(currentPlan.scenes || []);
            showToast('💾 Sahne düzenlemeleri kaydedildi');
        }
    }
});

// ══════════════════════════════════════════════════════════════

