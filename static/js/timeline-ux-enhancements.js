/**
 * ShortsAI Studio — Category G (Items 61–70)
 * Sahne & Zaman Çizelgesi Editörü (#pane-timeline / PJ Sekmesi):
 *  61. Sürükle-Bırak Sahne Sıralaması (Drag Handle ⋮⋮)
 *  62. Görsel Seçici Galeri Çekmecesi (6 alternatif klip satır içi çekmecesi)
 *  63. Sahne Böl / Birleştir (Split / Merge)
 *  64. Zaman Çizelgesi Cetveli (Timeline Ruler: 00:00 — 00:06 — ... — 00:39)
 *  65. Sahne Bazlı Geçiş Seçici (Kesme / Crossfade / Whip Pan / Glitch)
 *  66. Değişiklikleri Geri Al / İleri Al (Ctrl+Z / Ctrl+Y — 10 adımlı geçmiş)
 *  67. Kirli Durum (Unsaved Changes) Rozeti & Sesi/Kaliteyi Güncelle
 *  68. Kendi Dosyanı Sürükle-Bırak (.mp4 / .png doğrudan sahne kartına)
 *  69. Sahne Vurgu Kelimesi Seçici (Çift tıkla / çip seç -> highlight_word)
 *  70. Toplu Görsel Yenileme (Tüm Görselleri Yenile)
 */
(function () {
    'use strict';

    const MAX_HISTORY = 10;
    const tlUndoStack = [];
    const tlRedoStack = [];
    let isApplyingHistory = false;
    let isTimelineDirty = false;
    let lastSnapshotJson = '';

    const TRANSITIONS = [
        { id: 'cut', label: '⚡ Kesme' },
        { id: 'crossfade', label: '🌊 Crossfade' },
        { id: 'whip_pan', label: '💨 Whip Pan' },
        { id: 'glitch', label: '⚡ Glitch' }
    ];

    function escapeHtmlSafe(str) {
        return String(str || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function formatTimeMMSS(sec) {
        const s = Math.max(0, Math.round(Number(sec) || 0));
        const m = Math.floor(s / 60);
        const rem = s % 60;
        return `${String(m).padStart(2, '0')}:${String(rem).padStart(2, '0')}`;
    }

    function pushTimelineHistorySnapshot(markDirty = true) {
        if (isApplyingHistory || !window.currentPlan?.scenes) return;
        const snap = JSON.stringify(window.currentPlan.scenes);
        if (snap === lastSnapshotJson) return;
        if (lastSnapshotJson) {
            tlUndoStack.push(lastSnapshotJson);
            if (tlUndoStack.length > MAX_HISTORY) tlUndoStack.shift();
            tlRedoStack.length = 0;
        }
        lastSnapshotJson = snap;
        if (markDirty) setTimelineDirty(true);
        updateUndoRedoButtons();
    }

    function performTimelineUndo() {
        if (!tlUndoStack.length || !window.currentPlan) return;
        isApplyingHistory = true;
        try {
            tlRedoStack.push(JSON.stringify(window.currentPlan.scenes || []));
            const prev = JSON.parse(tlUndoStack.pop());
            lastSnapshotJson = JSON.stringify(prev);
            window.currentPlan.scenes = prev;
            if (typeof setCurrentPlan === 'function') setCurrentPlan(window.currentPlan);
            if (typeof showToast === 'function') showToast('↩ Son sahne değişikliği geri alındı', 'info');
        } finally {
            isApplyingHistory = false;
            updateUndoRedoButtons();
        }
    }

    function performTimelineRedo() {
        if (!tlRedoStack.length || !window.currentPlan) return;
        isApplyingHistory = true;
        try {
            tlUndoStack.push(JSON.stringify(window.currentPlan.scenes || []));
            const next = JSON.parse(tlRedoStack.pop());
            lastSnapshotJson = JSON.stringify(next);
            window.currentPlan.scenes = next;
            if (typeof setCurrentPlan === 'function') setCurrentPlan(window.currentPlan);
            if (typeof showToast === 'function') showToast('↪ Sahne değişikliği ileri alındı', 'info');
        } finally {
            isApplyingHistory = false;
            updateUndoRedoButtons();
        }
    }

    function updateUndoRedoButtons() {
        const uBtn = document.getElementById('btn-tl-undo');
        const rBtn = document.getElementById('btn-tl-redo');
        if (uBtn) {
            uBtn.disabled = tlUndoStack.length === 0;
            uBtn.title = `Geri Al (Ctrl+Z) · ${tlUndoStack.length} adım`;
        }
        if (rBtn) {
            rBtn.disabled = tlRedoStack.length === 0;
            rBtn.title = `İleri Al (Ctrl+Y) · ${tlRedoStack.length} adım`;
        }
    }

    // ── 67. Dirty State (Unsaved Changes) Banner ─────────────────────────────
    function setTimelineDirty(dirty) {
        isTimelineDirty = Boolean(dirty);
        const banner = document.getElementById('tl-dirty-state-banner');
        if (banner) {
            banner.classList.toggle('hidden', !isTimelineDirty);
        }
    }

    // ── 66, 67, 70: Toolbar Buttons & Dirty Banner ───────────────────────────
    function ensureTimelineToolbarEnhancements() {
        const toolbarLeft = document.querySelector('#pane-timeline .tl-toolbar-left');
        if (toolbarLeft && !document.getElementById('btn-tl-undo')) {
            const extraHtml = document.createElement('div');
            extraHtml.className = 'tl-ux-toolbar-group';
            extraHtml.innerHTML = `
                <button type="button" class="tl-btn tl-btn-ghost" id="btn-tl-undo" disabled title="Geri Al (Ctrl+Z)">
                    <i class="fa-solid fa-rotate-left"></i> Geri Al
                </button>
                <button type="button" class="tl-btn tl-btn-ghost" id="btn-tl-redo" disabled title="İleri Al (Ctrl+Y)">
                    <i class="fa-solid fa-rotate-right"></i> İleri Al
                </button>
                <button type="button" class="tl-btn tl-btn-secondary" id="btn-tl-refresh-all-visuals" title="Tüm sahnelerin stok/AI görsellerini tek tıkla yeniden çek (Madde 70)">
                    <i class="fa-solid fa-images"></i> Tüm Görselleri Yenile
                </button>
            `;
            toolbarLeft.appendChild(extraHtml);

            document.getElementById('btn-tl-undo')?.addEventListener('click', performTimelineUndo);
            document.getElementById('btn-tl-redo')?.addEventListener('click', performTimelineRedo);
            document.getElementById('btn-tl-refresh-all-visuals')?.addEventListener('click', () => {
                const stockBtn = document.getElementById('btn-fetch-stock-clips');
                if (stockBtn) stockBtn.click();
            });
        }

        const arcContainer = document.querySelector('#pane-timeline .tl-arc-container');
        if (arcContainer && !document.getElementById('tl-dirty-state-banner')) {
            const dirtyBanner = document.createElement('div');
            dirtyBanner.id = 'tl-dirty-state-banner';
            dirtyBanner.className = 'tl-dirty-state-banner hidden';
            dirtyBanner.innerHTML = `
                <div class="tl-dirty-left">
                    <span class="tl-dirty-dot"></span>
                    <strong>Değişiklikler yapıldı</strong>
                    <span>Senaryo veya süreler düzenlendi — ses ve kalite metriklerini senkronize edin.</span>
                </div>
                <button type="button" class="tl-dirty-sync-btn" id="btn-tl-sync-dirty">
                    <i class="fa-solid fa-arrows-rotate"></i> Sesi &amp; Kaliteyi Güncelle
                </button>
            `;
            arcContainer.before(dirtyBanner);

            document.getElementById('btn-tl-sync-dirty')?.addEventListener('click', () => {
                if (typeof collectTimelineEdits === 'function') collectTimelineEdits();
                if (typeof updateComplianceDashboard === 'function' && window.currentPlan?.scenes) {
                    updateComplianceDashboard(window.currentPlan.scenes);
                }
                if (typeof window.syncWizardStep4UI === 'function') window.syncWizardStep4UI();
                if (typeof window.syncPhonePreviewAll === 'function') window.syncPhonePreviewAll();
                setTimelineDirty(false);
                if (typeof showToast === 'function') showToast('✅ Ses, süre ve kalite kalkanı güncellendi!', 'success');
            });
        }

        // 64. Proportional Timeline Ruler
        const scenesContainer = document.getElementById('scenes-timeline-container');
        if (scenesContainer && !document.getElementById('tl-proportional-ruler')) {
            const ruler = document.createElement('div');
            ruler.id = 'tl-proportional-ruler';
            ruler.className = 'tl-proportional-ruler';
            scenesContainer.before(ruler);
        }
    }

    // ── 64. Render Proportional Timeline Ruler ───────────────────────────────
    function renderTimelineRuler(scenes) {
        const ruler = document.getElementById('tl-proportional-ruler');
        if (!ruler) return;
        if (!Array.isArray(scenes) || !scenes.length) {
            ruler.innerHTML = '';
            ruler.classList.add('hidden');
            return;
        }
        ruler.classList.remove('hidden');

        const totalSec = scenes.reduce((acc, s) => acc + (parseFloat(s.duration) || 3.5), 0) || 1;
        let elapsed = 0;
        const segmentsHtml = scenes.map((sc, i) => {
            const dur = parseFloat(sc.duration) || 3.5;
            const startStr = formatTimeMMSS(elapsed);
            elapsed += dur;
            const endStr = formatTimeMMSS(elapsed);
            const widthPct = Math.max(8, (dur / totalSec) * 100);
            const hl = sc.highlight_word ? ` · ★${sc.highlight_word}` : '';
            return `
                <button type="button" class="tl-ruler-seg" data-rscene="${i}" style="flex: ${widthPct} 1 0%;" title="Sahne #${i + 1} (${startStr} – ${endStr}) · Tıklayınca sahneye git">
                    <span class="tl-ruler-top">
                        <strong>S${i + 1}</strong>
                        <em>${startStr}</em>
                    </span>
                    <span class="tl-ruler-sub">${dur.toFixed(1)}sn${escapeHtmlSafe(hl)}</span>
                </button>
            `;
        }).join('');

        ruler.innerHTML = `
            <div class="tl-ruler-header">
                <span><i class="fa-solid fa-ruler-horizontal"></i> Zaman Çizelgesi Cetveli (00:00 — ${formatTimeMMSS(totalSec)})</span>
                <small>Sahneye odaklanmak için segmente tıklayın</small>
            </div>
            <div class="tl-ruler-track">${segmentsHtml}</div>
        `;

        ruler.querySelectorAll('.tl-ruler-seg').forEach(btn => {
            btn.addEventListener('click', () => {
                const idx = parseInt(btn.getAttribute('data-rscene') || '0', 10);
                const card = document.querySelector(`#scenes-timeline-container .tl-scene-card[data-scene-idx="${idx}"]`);
                if (card) {
                    card.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    card.classList.add('tl-card-pulse');
                    setTimeout(() => card.classList.remove('tl-card-pulse'), 1400);
                }
            });
        });
    }

    // ── 61, 62, 63, 65, 68, 69: Enhance Each Rendered .tl-scene-card ─────────
    function enhanceTimelineSceneCards() {
        ensureTimelineToolbarEnhancements();
        const scenes = window.currentPlan?.scenes || [];
        renderTimelineRuler(scenes);
        if (!scenes.length) return;

        if (!lastSnapshotJson) {
            lastSnapshotJson = JSON.stringify(scenes);
        }

        const container = document.getElementById('scenes-timeline-container');
        if (!container) return;

        // Clear old transition connectors before re-inserting
        container.querySelectorAll('.tl-transition-connector').forEach(el => el.remove());

        const cards = Array.from(container.querySelectorAll('.tl-scene-card'));
        cards.forEach((card, i) => {
            const sc = scenes[i];
            if (!sc) return;

            // 61. Prominent Drag Handle (⋮⋮)
            const topLabels = card.querySelector('.tl-card-labels');
            if (topLabels && !card.querySelector('.tl-drag-handle')) {
                const handle = document.createElement('span');
                handle.className = 'tl-drag-handle';
                handle.title = 'Sahneyi sürükleyip sırasını değiştirin (Madde 61)';
                handle.innerHTML = `<i class="fa-solid fa-grip-vertical"></i> S${i + 1}`;
                topLabels.prepend(handle);
            }

            // 63. Split / Merge Buttons in .tl-card-actions
            const actionsBox = card.querySelector('.tl-card-actions');
            if (actionsBox && !card.querySelector('.btn-tl-split-scene')) {
                const splitBtn = document.createElement('button');
                splitBtn.type = 'button';
                splitBtn.className = 'tl-btn-icon btn-tl-split-scene';
                splitBtn.title = 'Sahneyi ortadan ikiye böl (Split — Madde 63)';
                splitBtn.innerHTML = '<i class="fa-solid fa-scissors"></i>';
                splitBtn.addEventListener('click', () => splitSceneAt(i));

                const mergeBtn = document.createElement('button');
                mergeBtn.type = 'button';
                mergeBtn.className = 'tl-btn-icon btn-tl-merge-scene';
                mergeBtn.title = 'Sonraki sahneyle birleştir (Merge — Madde 63)';
                mergeBtn.disabled = i >= scenes.length - 1;
                mergeBtn.innerHTML = '<i class="fa-solid fa-link"></i>';
                mergeBtn.addEventListener('click', () => mergeSceneWithNext(i));

                actionsBox.prepend(mergeBtn);
                actionsBox.prepend(splitBtn);
            }

            // 62. Inline 6-Clip Visual Selector Drawer
            const mediaActions = card.querySelector('.tl-media-actions');
            if (mediaActions && !card.querySelector('.btn-tl-inline-gallery')) {
                const galBtn = document.createElement('button');
                galBtn.type = 'button';
                galBtn.className = 'tl-btn-icon btn-tl-inline-gallery';
                galBtn.title = '6 Alternatif Görsel Çekmecesini Aç (Madde 62)';
                galBtn.innerHTML = '<i class="fa-solid fa-grip"></i>';
                galBtn.addEventListener('click', () => toggleInlineVisualDrawer(card, i));
                mediaActions.appendChild(galBtn);
            }

            // 68. Local File Drag-and-Drop onto .tl-video-frame
            const frame = card.querySelector('.tl-video-frame');
            if (frame && !frame.dataset.fileDropBound) {
                frame.dataset.fileDropBound = '1';
                const dropHint = document.createElement('span');
                dropHint.className = 'tl-file-drop-hint';
                dropHint.textContent = '📂 .mp4/.png Bırak';
                frame.appendChild(dropHint);

                frame.addEventListener('dragover', (e) => {
                    if (e.dataTransfer?.types?.includes('Files')) {
                        e.preventDefault();
                        e.stopPropagation();
                        frame.classList.add('is-file-dragover');
                    }
                });
                frame.addEventListener('dragleave', () => frame.classList.remove('is-file-dragover'));
                frame.addEventListener('drop', (e) => {
                    const files = e.dataTransfer?.files;
                    if (!files || !files.length) return;
                    e.preventDefault();
                    e.stopPropagation();
                    frame.classList.remove('is-file-dragover');
                    const file = files[0];
                    const blobUrl = URL.createObjectURL(file);
                    pushTimelineHistorySnapshot(true);
                    sc.video_url = blobUrl;
                    sc.selected_video = { source: `Yerel: ${file.name.slice(0, 18)}`, url: blobUrl };
                    if (typeof setCurrentPlan === 'function') setCurrentPlan(window.currentPlan);
                    if (typeof showToast === 'function') showToast(`📂 "${file.name}" Sahne #${i + 1} görseli olarak atandı`);
                });
            }

            // 69. Highlight Word Selector (Double-click or Word Chips)
            const narrField = card.querySelector('.tl-field');
            const narrTextarea = card.querySelector('.scene-narr-input');
            if (narrField && narrTextarea && !card.querySelector('.tl-highlight-word-bar')) {
                const words = String(sc.narration || '')
                    .replace(/[^\p{L}\p{N}\s'-]/gu, '')
                    .split(/\s+/)
                    .filter(w => w.length >= 3)
                    .slice(0, 8);
                const currentHl = sc.highlight_word || '';
                const bar = document.createElement('div');
                bar.className = 'tl-highlight-word-bar';
                bar.innerHTML = `
                    <span class="tl-hl-label" title="Altyazıda sarı/büyük vurgulanacak kelime (Madde 69)">
                        🎯 Vurgu Kelimesi: <strong id="tl-hl-active-${i}">${escapeHtmlSafe(currentHl || 'Otomatik')}</strong>
                    </span>
                    <div class="tl-hl-chips">
                        ${words.map(w => `<button type="button" class="tl-hl-word-chip ${currentHl.toLowerCase() === w.toLowerCase() ? 'active' : ''}" data-word="${escapeHtmlSafe(w)}">${escapeHtmlSafe(w)}</button>`).join('')}
                    </div>
                `;
                narrField.appendChild(bar);

                bar.querySelectorAll('.tl-hl-word-chip').forEach(chip => {
                    chip.addEventListener('click', () => {
                        const w = chip.getAttribute('data-word') || '';
                        pushTimelineHistorySnapshot(true);
                        sc.highlight_word = w.toUpperCase();
                        bar.querySelectorAll('.tl-hl-word-chip').forEach(c => c.classList.toggle('active', c === chip));
                        const actEl = document.getElementById(`tl-hl-active-${i}`);
                        if (actEl) actEl.textContent = sc.highlight_word;
                        renderTimelineRuler(scenes);
                        if (typeof window.renderPhoneSceneAt === 'function') window.renderPhoneSceneAt(i);
                    });
                });

                narrTextarea.addEventListener('dblclick', () => {
                    const sel = narrTextarea.value.substring(narrTextarea.selectionStart, narrTextarea.selectionEnd).trim();
                    if (sel && sel.length >= 2) {
                        pushTimelineHistorySnapshot(true);
                        sc.highlight_word = sel.replace(/[.,!?;:"]/g, '').toUpperCase();
                        const actEl = document.getElementById(`tl-hl-active-${i}`);
                        if (actEl) actEl.textContent = sc.highlight_word;
                        if (typeof showToast === 'function') showToast(`🎯 Vurgu kelimesi: "${sc.highlight_word}"`);
                    }
                });

                narrTextarea.addEventListener('change', () => pushTimelineHistorySnapshot(true));
            }

            // 65. Scene-to-Scene Transition Connector
            if (i < cards.length - 1) {
                const curTrans = sc.transition || 'cut';
                const conn = document.createElement('div');
                conn.className = 'tl-transition-connector';
                conn.innerHTML = `
                    <span class="tl-trans-line"></span>
                    <div class="tl-trans-pills" role="group" aria-label="Sahne ${i + 1} - ${i + 2} Geçiş Efekti">
                        <span class="tl-trans-title">S${i + 1}→S${i + 2} Geçiş:</span>
                        ${TRANSITIONS.map(t => `
                            <button type="button" class="tl-trans-pill ${curTrans === t.id ? 'active' : ''}" data-trans="${t.id}">
                                ${t.label}
                            </button>
                        `).join('')}
                    </div>
                    <span class="tl-trans-line"></span>
                `;
                conn.querySelectorAll('.tl-trans-pill').forEach(btn => {
                    btn.addEventListener('click', () => {
                        pushTimelineHistorySnapshot(true);
                        sc.transition = btn.getAttribute('data-trans') || 'cut';
                        conn.querySelectorAll('.tl-trans-pill').forEach(b => b.classList.toggle('active', b === btn));
                    });
                });
                card.after(conn);
            }
        });
    }

    // ── 62. Toggle Inline 6-Clip Drawer ──────────────────────────────────────
    async function toggleInlineVisualDrawer(card, idx) {
        let drawer = card.querySelector('.tl-inline-visual-drawer');
        if (drawer) {
            drawer.remove();
            return;
        }
        const sc = window.currentPlan?.scenes?.[idx];
        if (!sc) return;

        drawer = document.createElement('div');
        drawer.className = 'tl-inline-visual-drawer';
        const q = (sc.search_queries && sc.search_queries[0]) || sc.scene_description || 'cinematic vertical';
        let activeSrc = document.getElementById('tl-stock-provider-select')?.value || 'pexels_pixabay';
        drawer.innerHTML = `
            <div class="tl-ivd-head" style="flex-wrap:wrap;gap:6px;">
                <span>🖼️ "${escapeHtmlSafe(q.slice(0, 32))}" için Hızlı Seçim</span>
                <div class="tl-ivd-sources" style="display:inline-flex;gap:4px;margin-left:auto;">
                    <button type="button" class="tl-chip-btn ivd-src-btn active" data-src="pexels_pixabay" style="font-size:0.68rem;padding:2px 7px;">🌟 Pexels+Pixabay</button>
                    <button type="button" class="tl-chip-btn ivd-src-btn" data-src="pexels" style="font-size:0.68rem;padding:2px 7px;">🟢 Pexels</button>
                    <button type="button" class="tl-chip-btn ivd-src-btn" data-src="pixabay" style="font-size:0.68rem;padding:2px 7px;">🔵 Pixabay</button>
                    <button type="button" class="tl-chip-btn ivd-src-btn" data-src="coverr" style="font-size:0.68rem;padding:2px 7px;">🟣 Coverr</button>
                </div>
                <button type="button" class="tl-ivd-close">✕</button>
            </div>
            <div class="tl-ivd-grid">Yükleniyor...</div>
        `;
        card.querySelector('.tl-card-content')?.prepend(drawer);
        drawer.querySelector('.tl-ivd-close')?.addEventListener('click', () => drawer.remove());

        const loadDrawerClips = async (srcMode) => {
            const grid = drawer.querySelector('.tl-ivd-grid');
            if (!grid) return;
            grid.innerHTML = `<span><i class="fa-solid fa-spinner fa-spin"></i> ${escapeHtmlSafe(srcMode.toUpperCase())} aranıyor...</span>`;
            try {
                const niche = window.currentPlan?.niche_id || '';
                const res = await fetch(`/api/stock/search?query=${encodeURIComponent(q)}&limit=6&niche_id=${encodeURIComponent(niche)}&source=${encodeURIComponent(srcMode)}`);
                const data = await res.json();
                const items = (data.results || []).slice(0, 6);
                if (!items.length) {
                    grid.innerHTML = `<span class="tl-ivd-empty">Bu kaynakta sonuç yok — üstten diğer kaynağı seçin veya Değiştir modalını açın.</span>`;
                    return;
                }
                grid.innerHTML = items.map((it, rIdx) => `
                    <button type="button" class="tl-ivd-item" data-ridx="${rIdx}">
                        ${it.thumbnail ? `<img src="${escapeHtmlSafe(it.thumbnail)}" alt="Klip ${rIdx + 1}">` : `<span class="tl-ivd-fallback"><i class="fa-solid fa-film"></i></span>`}
                        <small>${escapeHtmlSafe((it.source || 'Stok').toUpperCase())} · ${it.duration || 5}s</small>
                    </button>
                `).join('');
                grid.querySelectorAll('.tl-ivd-item').forEach(btn => {
                    btn.addEventListener('click', () => {
                        const chosen = items[parseInt(btn.getAttribute('data-ridx') || '0', 10)];
                        if (!chosen) return;
                        pushTimelineHistorySnapshot(true);
                        sc.selected_video = chosen;
                        sc.video_url = chosen.url || chosen.preview_url || '';
                        if (typeof setCurrentPlan === 'function') setCurrentPlan(window.currentPlan);
                        if (typeof showToast === 'function') showToast(`🎬 Sahne #${idx + 1} (${(chosen.source || 'Stok').toUpperCase()}) seçildi`);
                    });
                });
            } catch (err) {
                grid.innerHTML = `<span class="tl-ivd-empty">Arama hatası: ${escapeHtmlSafe(err.message)}</span>`;
            }
        };

        drawer.querySelectorAll('.ivd-src-btn').forEach(b => {
            b.classList.toggle('active', b.getAttribute('data-src') === activeSrc);
            b.addEventListener('click', () => {
                activeSrc = b.getAttribute('data-src') || 'pexels_pixabay';
                drawer.querySelectorAll('.ivd-src-btn').forEach(x => x.classList.toggle('active', x === b));
                loadDrawerClips(activeSrc);
            });
        });

        await loadDrawerClips(activeSrc);
    }

    // ── 63. Split & Merge Helpers ────────────────────────────────────────────
    function splitSceneAt(idx) {
        const scenes = window.currentPlan?.scenes;
        if (!scenes || !scenes[idx]) return;
        pushTimelineHistorySnapshot(true);
        const sc = scenes[idx];
        const narr = String(sc.narration || '').trim();
        const words = narr.split(/\s+/).filter(Boolean);
        const mid = Math.max(1, Math.ceil(words.length / 2));
        const part1 = words.slice(0, mid).join(' ') || 'Bölüm 1';
        const part2 = words.slice(mid).join(' ') || 'Bölüm 2...';
        const halfDur = Math.max(2.0, +((parseFloat(sc.duration) || 4.0) / 2).toFixed(1));

        const sc1 = { ...JSON.parse(JSON.stringify(sc)), narration: part1, duration: halfDur };
        const sc2 = { ...JSON.parse(JSON.stringify(sc)), narration: part2, duration: halfDur };
        scenes.splice(idx, 1, sc1, sc2);
        scenes.forEach((s, si) => { s.scene_number = si + 1; });
        if (typeof setCurrentPlan === 'function') setCurrentPlan(window.currentPlan);
        if (typeof showToast === 'function') showToast(`✂️ Sahne #${idx + 1} iki sahneye bölündü`);
    }

    function mergeSceneWithNext(idx) {
        const scenes = window.currentPlan?.scenes;
        if (!scenes || !scenes[idx] || !scenes[idx + 1]) return;
        pushTimelineHistorySnapshot(true);
        const cur = scenes[idx];
        const nxt = scenes[idx + 1];
        cur.narration = `${String(cur.narration || '').trim()} ${String(nxt.narration || '').trim()}`.trim();
        cur.duration = Math.min(12.0, +((parseFloat(cur.duration) || 3.5) + (parseFloat(nxt.duration) || 3.5)).toFixed(1));
        scenes.splice(idx + 1, 1);
        scenes.forEach((s, si) => { s.scene_number = si + 1; });
        if (typeof setCurrentPlan === 'function') setCurrentPlan(window.currentPlan);
        if (typeof showToast === 'function') showToast(`🔗 Sahne #${idx + 1} ve #${idx + 2} birleştirildi`);
    }

    function hookRenderTimelineScenes() {
        const orig = window.renderTimelineScenes;
        if (typeof orig === 'function' && !orig._catGHooked) {
            const wrapped = function (plan) {
                const res = orig.apply(this, arguments);
                enhanceTimelineSceneCards();
                if (typeof window.syncPhonePreviewAll === 'function') window.syncPhonePreviewAll();
                return res;
            };
            wrapped._catGHooked = true;
            window.renderTimelineScenes = wrapped;
        }
    }

    function initTimelineUXEnhancements() {
        ensureTimelineToolbarEnhancements();
        hookRenderTimelineScenes();
        enhanceTimelineSceneCards();

        document.addEventListener('keydown', (e) => {
            const activePane = document.querySelector('#pane-timeline.active');
            if (!activePane) return;
            const tag = (e.target?.tagName || '').toLowerCase();
            if (tag === 'input' || tag === 'textarea') return;
            if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z' && !e.shiftKey) {
                e.preventDefault();
                performTimelineUndo();
            } else if ((e.ctrlKey || e.metaKey) && (e.key.toLowerCase() === 'y' || (e.shiftKey && e.key.toLowerCase() === 'z'))) {
                e.preventDefault();
                performTimelineRedo();
            }
        });
    }

    window.enhanceTimelineSceneCards = enhanceTimelineSceneCards;

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initTimelineUXEnhancements);
    } else {
        initTimelineUXEnhancements();
    }
})();
