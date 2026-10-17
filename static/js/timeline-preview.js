/**
 * ShortsAI Studio — Timeline Media Preview, Clip Replacement Modal & Director Pro Tools (timeline-preview.js)
 * Handles scene TTS audio preview, stock/Flux/Whiteboard clip replacement modal, asset preparation, and Director Pro AI tools.
 */

const MOOD_CFG = {
    epic:       { icon: '🌟', label: 'Epic',       color: '#fbbf24', bg: 'rgba(251,191,36,0.12)' },
    dramatic:   { icon: '🔴', label: 'Dramatic',   color: '#ef4444', bg: 'rgba(239,68,68,0.12)' },
    calm:       { icon: '🔵', label: 'Calm',       color: '#38bdf8', bg: 'rgba(56,189,248,0.12)' },
    mysterious: { icon: '🟣', label: 'Mysterious', color: '#a78bfa', bg: 'rgba(167,139,250,0.12)' },
    energetic:  { icon: '⚡', label: 'Energetic',  color: '#fb923c', bg: 'rgba(251,146,60,0.12)' },
    dark:       { icon: '⬛', label: 'Dark',       color: '#94a3b8', bg: 'rgba(148,163,184,0.08)' },
    bright:     { icon: '☀️', label: 'Bright',     color: '#34d399', bg: 'rgba(52,211,153,0.12)' }
};

let activeAudioPreview = null;
window.stopSceneAudioPreview = function () {
    if (activeAudioPreview) {
        activeAudioPreview.pause();
        activeAudioPreview = null;
    }
};
async function previewSceneAudio(text, btnEl) {
    if (!text || !text.trim()) return showToast('Seslendirilecek metin boş', 'warn');
    window.stopSceneAudioPreview();
    const originalHtml = btnEl?.innerHTML || '';
    if (btnEl) {
        btnEl.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
        btnEl.disabled = true;
    }
    try {
        const voiceId = document.getElementById('select-tts-voice')?.value || 'tr-TR-AhmetNeural';
        const language = document.getElementById('select-language')?.value || window.currentPlan?.language || 'tr';
        const res = await fetch('/api/tts/preview', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text, voice: voiceId, language })
        });
        if (!res.ok) throw new Error('TTS sunucu hatası');
        const blob = await res.blob();
        activeAudioPreview = new Audio(URL.createObjectURL(blob));
        activeAudioPreview.play();
        activeAudioPreview.onended = () => { if (btnEl) { btnEl.innerHTML = originalHtml; btnEl.disabled = false; } };
        activeAudioPreview.onerror = () => { if (btnEl) { btnEl.innerHTML = originalHtml; btnEl.disabled = false; } showToast('Ses çalınamadı', 'error'); };
    } catch (e) {
        if (btnEl) { btnEl.innerHTML = originalHtml; btnEl.disabled = false; }
        showToast('TTS Hatası: ' + e.message, 'error');
    }
}

function copyFullScriptText() {
    if (typeof collectTimelineEdits === 'function') collectTimelineEdits();
    if (!window.currentPlan?.scenes?.length) return showToast('Kopyalanacak senaryo yok', 'warn');

    const title = window.currentPlan.title || 'YouTube Shorts Senaryosu';
    const totalSec = window.currentPlan.scenes.reduce((a, s) => a + (parseFloat(s.duration) || 3.5), 0);
    const totalWords = window.currentPlan.scenes.reduce((a, s) => a + wordCount(s.narration), 0);

    let text = `🎬 BAŞLIK: ${title}\n`;
    text += `⏱️ SÜRE: ${totalSec.toFixed(1)}sn | 📝 ${totalWords} kelime | 🎞️ ${window.currentPlan.scenes.length} sahne\n`;
    text += `═══════════════════════════════════════════\n\n`;

    window.currentPlan.scenes.forEach((sc, idx) => {
        text += `[SAHNE ${idx + 1}] (${(parseFloat(sc.duration) || 3.5).toFixed(1)}s | ${sc.mood || 'epic'})\n`;
        text += `SESLENDİRME: ${(sc.narration || '').trim()}\n`;
        if (sc.scene_description) text += `GÖRSEL: ${sc.scene_description.trim()}\n`;
        if (sc.search_queries?.[0]) text += `ARAMA: ${sc.search_queries[0].trim()}\n`;
        text += `\n`;
    });

    text += `═══════════════════════════════════════════\n🎙️ KESİNTİSİZ METİN:\n`;
    text += window.currentPlan.scenes.map(s => (s.narration || '').trim()).filter(Boolean).join('\n\n') + '\n';

    if (navigator.clipboard?.writeText) {
        navigator.clipboard.writeText(text).then(() => showToast(`📋 ${totalWords} kelime panoya kopyalandı`)).catch(() => fallbackCopy(text, totalWords));
    } else fallbackCopy(text, totalWords);
}

function fallbackCopy(text, wc) {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.cssText = 'position:fixed;opacity:0';
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand('copy'); showToast(`📋 ${wc} kelime kopyalandı`); } catch (_) { showToast('Kopyalama başarısız', 'error'); }
    document.body.removeChild(ta);
}

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

async function prepareTimelineAssetsAndScript() {
    const btn = document.getElementById('btn-prepare-timeline');
    const oldHtml = btn ? btn.innerHTML : '';
    const topic = document.getElementById('input-topic')?.value?.trim() || window.currentPlan?.title || 'YouTube Shorts';
    const niche = document.getElementById('select-niche')?.value || window.currentPlan?.niche_id || '';

    if (btn) { btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Hazırlanıyor...'; btn.disabled = true; }
    showToast('🚀 AI senaryo + gerçek video klipleri hazırlanıyor...', 'info');

    try {
        const res = await fetch('/api/timeline/prepare', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ keyword: topic, topic, niche, niche_id: niche, plan: window.currentPlan })
        });
        const data = await res.json();
        if (data.status === 'ok' && data.plan) {
            if (data.project_slug) data.plan.project_slug = data.project_slug;
            setCurrentPlan(data.plan);
            showToast(`✨ ${data.plan.scenes.length} sahne hazırlandı`);
        } else throw new Error(data.message || data.detail || 'Hazırlık tamamlanamadı');
    } catch (err) { showToast('Hazırlama hatası: ' + err.message, 'error'); }
    finally { if (btn) { btn.innerHTML = oldHtml; btn.disabled = false; } }
}

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
            body: JSON.stringify({
                project_slug: currentPlan.project_slug || currentPlan.title || 'active_project',
                plan: currentPlan,
                scene_index: idx,
                ...payload
            })
        });
        const data = await res.json();

        if (data.status === 'ok') {
            if (data.project_slug) currentPlan.project_slug = data.project_slug;
            const clipUrl = data.video_url || data.clip_url;
            if (payload.replace_mode === 'stock') {
                sc.selected_video = payload.stock_video_data;
                sc.video_url = clipUrl || payload.stock_video_data?.url;
            } else if (payload.replace_mode === 'flux') {
                sc.video_url = clipUrl;
                sc.selected_video = { source: '0 TL Flux AI (SDXL)', url: clipUrl };
            } else if (payload.replace_mode === 'whiteboard') {
                sc.video_url = clipUrl;
                sc.selected_video = { source: 'Whiteboard Çizim', url: clipUrl };
            }
            setCurrentPlan(currentPlan);
            closeReplaceVisualModal();
            showToast(`🎬 Sahne #${idx + 1} güncellendi!`);
        } else throw new Error(data.detail || data.message || 'Değiştirilemedi');
    } catch (e) { showToast('Hata: ' + e.message, 'error'); }
}

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('btn-sync-latest-render')?.addEventListener('click', () => loadLatestRenderedProjectToTimeline());
    document.getElementById('btn-prepare-timeline')?.addEventListener('click', () => prepareTimelineAssetsAndScript());
    document.querySelectorAll('.btn-copy-full-script').forEach(btn => btn.addEventListener('click', () => copyFullScriptText()));
    document.getElementById('btn-copy-script-timeline')?.addEventListener('click', () => copyFullScriptText());
    document.getElementById('btn-copy-script-studio')?.addEventListener('click', () => copyFullScriptText());

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

    document.getElementById('btn-render-from-timeline')?.addEventListener('click', () => {
        collectTimelineEdits();
        if (typeof startRenderProcess === 'function') startRenderProcess(currentPlan);
    });

    document.getElementById('btn-close-visual-modal')?.addEventListener('click', closeReplaceVisualModal);
    document.getElementById('modal-change-scene-visual')?.addEventListener('click', e => { if (e.target.id === 'modal-change-scene-visual') closeReplaceVisualModal(); });
    document.querySelectorAll('.modal-tab-btn').forEach(btn => btn.addEventListener('click', () => switchModalTab(btn.getAttribute('data-tab'))));

    document.getElementById('btn-modal-do-stock-search')?.addEventListener('click', () => executeModalStockSearch());
    document.getElementById('modal-stock-search-input')?.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); executeModalStockSearch(e.target.value); } });

    document.getElementById('btn-modal-generate-flux')?.addEventListener('click', async () => {
        const prompt = document.getElementById('modal-flux-prompt-input')?.value?.trim();
        if (!prompt) return showToast('Flux prompt girin', 'warn');
        const btn = document.getElementById('btn-modal-generate-flux');
        const old = btn.innerHTML; btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Üretiliyor...'; btn.disabled = true;
        try { await applyClipReplacement({ replace_mode: 'flux', prompt, duration: currentPlan?.scenes?.[activeModalSceneIdx]?.duration || 3.5 }); }
        finally { btn.innerHTML = old; btn.disabled = false; }
    });

    document.getElementById('btn-modal-generate-whiteboard')?.addEventListener('click', async () => {
        const prompt = document.getElementById('modal-whiteboard-prompt-input')?.value?.trim();
        if (!prompt) return showToast('Whiteboard açıklaması girin', 'warn');
        const btn = document.getElementById('btn-modal-generate-whiteboard');
        const old = btn.innerHTML; btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Çiziliyor...'; btn.disabled = true;
        try { await applyClipReplacement({ replace_mode: 'whiteboard', prompt, duration: currentPlan?.scenes?.[activeModalSceneIdx]?.duration || 3.5 }); }
        finally { btn.innerHTML = old; btn.disabled = false; }
    });

    document.getElementById('btn-fetch-stock-clips')?.addEventListener('click', async () => {
        if (!window.currentPlan?.scenes?.length) return showToast('Önce senaryo oluşturun', 'warn');
        const btn = document.getElementById('btn-fetch-stock-clips');
        const old = btn.innerHTML; btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Çekiliyor...';
        showToast('📡 Stok videolar taranıyor...');
        try {
            if (typeof collectTimelineEdits === 'function') collectTimelineEdits();
            const res = await fetch('/api/stock/fetch_for_scenes', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ scenes: window.currentPlan.scenes, niche_id: window.currentPlan.niche_id || window.currentPlan.meta?.locked_niche || '' })
            });
            const data = await res.json();
            if (data.status === 'ok' && data.scenes) { window.currentPlan.scenes = data.scenes; setCurrentPlan(window.currentPlan); showToast(`🎬 ${data.assigned || data.scenes.length} sahne kliplendi`); }
        } catch (err) { showToast('Stok video hatası: ' + err.message, 'error'); }
        finally { btn.disabled = false; btn.innerHTML = old; }
    });

    document.getElementById('btn-fix-cadence')?.addEventListener('click', async () => {
        if (!window.currentPlan?.scenes?.length) return showToast('Önce senaryo oluşturun', 'warn');
        if (typeof collectTimelineEdits === 'function') collectTimelineEdits();
        let splitCount = 0;
        const expanded = [];
        window.currentPlan.scenes.forEach((s) => {
            const dur = parseFloat(s.duration) || 3.5;
            const narr = (s.narration || '').trim();
            if ((dur > 5.0 || window.currentPlan.scenes.length < 8) && narr.length > 45) {
                const sentences = narr.split(/(?<=[.!?])\s+/).filter(Boolean);
                if (sentences.length >= 2) {
                    const mid = Math.ceil(sentences.length / 2);
                    const p1 = sentences.slice(0, mid).join(' ');
                    const p2 = sentences.slice(mid).join(' ');
                    expanded.push({ ...s, narration: p1, duration: Math.max(2.0, +(dur / 2).toFixed(1)) });
                    expanded.push({ ...s, narration: p2, duration: Math.max(2.0, +(dur / 2).toFixed(1)), visual_beat: 'pattern_interrupt' });
                    splitCount++;
                    return;
                }
            }
            expanded.push(s);
        });
        expanded.forEach((s, idx) => s.scene_number = idx + 1);
        window.currentPlan.scenes = expanded;
        try {
            const res = await fetch('/api/pacing/guard', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ scenes: window.currentPlan.scenes })
            });
            const data = await res.json();
            setCurrentPlan(window.currentPlan);
            showToast(`⚡ Cadence optimize edildi (+${splitCount} sahne bölündü, Pacing durum: ${data.status || 'ok'})`);
        } catch (_) {
            setCurrentPlan(window.currentPlan);
            showToast(`⚡ Cadence optimize edildi (${window.currentPlan.scenes.length} sahne)`);
        }
    });

    document.getElementById('btn-enrich-queries')?.addEventListener('click', () => {
        if (!window.currentPlan?.scenes?.length) return showToast('Önce senaryo oluşturun', 'warn');
        if (typeof collectTimelineEdits === 'function') collectTimelineEdits();
        const adj = ['cinematic', 'aerial drone', 'slow motion', 'macro shot', 'atmospheric 4k', 'moody lighting'];
        window.currentPlan.scenes.forEach((sc, i) => {
            sc.search_queries = (sc.search_queries || []).map((q, qi) => {
                if (!adj.some(a => q.toLowerCase().includes(a.split(' ')[0]))) return `${q} ${adj[(i + qi) % adj.length]}`;
                return q;
            });
        });
        setCurrentPlan(window.currentPlan);
        showToast('✨ Arama terimleri zenginleştirildi');
    });

    document.getElementById('btn-balance-durations')?.addEventListener('click', async () => {
        if (!window.currentPlan?.scenes?.length) return showToast('Önce senaryo oluşturun', 'warn');
        if (typeof collectTimelineEdits === 'function') collectTimelineEdits();
        const scenes = window.currentPlan.scenes;
        const totalSec = scenes.reduce((a, s) => a + (parseFloat(s.duration) || 3.5), 0);
        const target = totalSec < 38 ? 40 : (totalSec > 60 ? 58 : totalSec);
        const ratio = target / (totalSec || 1);
        scenes.forEach(s => s.duration = Math.max(1.8, Math.min(6.5, Math.round((parseFloat(s.duration) || 3.5) * ratio * 4) / 4)));
        setCurrentPlan(window.currentPlan);
        const finalSec = scenes.reduce((a, s) => a + s.duration, 0).toFixed(1);
        try {
            const res = await fetch('/api/pacing/guard', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ scenes: window.currentPlan.scenes })
            });
            const data = await res.json();
            const warnCount = (data.warnings || data.violations || []).length;
            showToast(`⚖️ Süreler dengelendi: ${finalSec}sn (Pacing Guard: ${warnCount ? warnCount + ' uyarı' : 'Optimal'})`);
        } catch (_) {
            showToast(`⚖️ Süreler dengelendi: ${finalSec}sn`);
        }
    });

    document.getElementById('btn-hallucination-check')?.addEventListener('click', async () => {
        if (!window.currentPlan?.scenes?.length) return showToast('Önce senaryo oluşturun', 'warn');
        if (typeof collectTimelineEdits === 'function') collectTimelineEdits();
        try {
            const res = await fetch('/api/grounding/audit', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ scenes: window.currentPlan.scenes, niche_id: window.currentPlan.niche_id || '' })
            });
            const data = await res.json();
            const flagged = data.flagged_count ?? data.regrounded_count ?? (data.flagged_scenes || []).length ?? 0;
            if (flagged > 0) {
                showToast(`⚠️ Grounding denetimi: ${flagged} sahnede doğrulanmamış iddia tespit edildi`, 'warn');
            } else {
                showToast(`✅ Grounding / Halüsinasyon denetimi: Temiz (${window.currentPlan.scenes.length} sahne doğrulandı)`);
            }
        } catch (err) {
            showToast('Grounding denetimi hatası: ' + err.message, 'error');
        }
    });

    document.getElementById('btn-helios-enhance')?.addEventListener('click', async () => {
        if (!window.currentPlan?.scenes?.length) return showToast('Önce senaryo oluşturun', 'warn');
        if (typeof collectTimelineEdits === 'function') collectTimelineEdits();
        const btn = document.getElementById('btn-helios-enhance');
        const old = btn.innerHTML; btn.disabled = true; btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Helios...';
        try {
            const charAnchor = (document.getElementById('tl-input-char-desc') || document.getElementById('tl-input-char-lock'))?.value?.trim() || '';
            const res = await fetch('/api/helios/enhance_scenes', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ scenes: window.currentPlan.scenes, style_preset: 'cinematic_dramatic', character_anchor: charAnchor })
            });
            const data = await res.json();
            if (data.scenes) {
                window.currentPlan.scenes = data.scenes;
                setCurrentPlan(window.currentPlan);
                showToast(`☀️ Helios 14B: ${data.scenes.length} sahne sinematik kamera açılarıyla zenginleştirildi`);
            }
        } catch (err) { showToast('Helios hatası: ' + err.message, 'error'); }
        finally { btn.disabled = false; btn.innerHTML = old; }
    });

    document.getElementById('btn-toggle-director-pro-bar')?.addEventListener('click', () => {
        const drawer = document.getElementById('tl-director-pro-drawer');
        if (drawer) {
            const isHidden = drawer.classList.contains('hidden') || drawer.style.display === 'none';
            drawer.classList.toggle('hidden', !isHidden);
            drawer.style.display = isHidden ? 'block' : 'none';
        }
    });

    document.getElementById('btn-apply-style-profile')?.addEventListener('click', async () => {
        if (!window.currentPlan?.scenes?.length) return showToast('Önce senaryo oluşturun', 'warn');
        if (typeof collectTimelineEdits === 'function') collectTimelineEdits();
        const profile_id = document.getElementById('tl-select-style-profile')?.value || 'cinematic_noir';
        const character_description = (document.getElementById('tl-input-char-desc') || document.getElementById('tl-input-char-lock'))?.value?.trim() || '';
        const outEl = document.getElementById('tl-director-pro-status');
        try {
            const res = await fetch('/api/style-profiles/apply', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ scenes: window.currentPlan.scenes, profile_id, character_description })
            });
            const data = await res.json();
            if (data.status === 'ok' && data.scenes) {
                window.currentPlan.scenes = data.scenes;
                setCurrentPlan(window.currentPlan);
                if (outEl) {
                    outEl.classList.remove('hidden');
                    outEl.style.display = 'block';
                    outEl.textContent = `🎨 Stil Profili "${profile_id}" ve Karakter Kilidi ${data.scenes.length} sahneye uygulandı.`;
                }
                showToast(`🎨 Stil profili (${profile_id}) uygulandı`);
            }
        } catch (err) { showToast('Stil profili hatası: ' + err.message, 'error'); }
    });

    document.getElementById('btn-dubbing-pack')?.addEventListener('click', async () => {
        if (!window.currentPlan?.scenes?.length) return showToast('Önce senaryo oluşturun', 'warn');
        if (typeof collectTimelineEdits === 'function') collectTimelineEdits();
        const lang = document.getElementById('tl-select-dub-lang')?.value || 'en';
        const outEl = document.getElementById('tl-director-pro-status');
        const btn = document.getElementById('btn-dubbing-pack');
        const old = btn.innerHTML; btn.disabled = true; btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Dublaj...';
        try {
            const res = await fetch('/api/dubbing/apply', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ plan: window.currentPlan, target_languages: [lang] })
            });
            const data = await res.json();
            if (data.status === 'ok' && data.plan) {
                const track = data.dubbed_tracks?.[lang];
                if (track?.scenes?.length) {
                    window.currentPlan.scenes = track.scenes;
                    if (track.title) window.currentPlan.title = track.title;
                }
                window.currentPlan.dubbed_tracks = data.dubbed_tracks;
                setCurrentPlan(window.currentPlan);
                if (outEl) {
                    outEl.classList.remove('hidden');
                    outEl.style.display = 'block';
                    outEl.textContent = `🌍 "${lang.toUpperCase()}" Dublaj Paketi hazırlandı! Ses: ${track?.voice || 'Auto'} — ${window.currentPlan.scenes.length} sahne çevrildi.`;
                }
                showToast(`🌍 ${lang.toUpperCase()} dublaj paketi sahnelere uygulandı`);
            }
        } catch (err) { showToast('Dublaj hatası: ' + err.message, 'error'); }
        finally { btn.disabled = false; btn.innerHTML = old; }
    });

    document.getElementById('btn-punch-in-curve')?.addEventListener('click', async () => {
        if (!window.currentPlan?.scenes?.length) return showToast('Önce senaryo oluşturun', 'warn');
        if (typeof collectTimelineEdits === 'function') collectTimelineEdits();
        const outEl = document.getElementById('tl-director-pro-status');
        try {
            let applied = 0;
            for (const sc of window.currentPlan.scenes) {
                const res = await fetch('/api/punch_in/curve', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ duration_sec: parseFloat(sc.duration) || 3.5, fps: 30, intensity: 0.14 })
                });
                const data = await res.json();
                if (data.curve) {
                    sc.punch_in_curve = data.curve;
                    sc.visual_beat = sc.visual_beat || 'punch_in_zoom';
                    applied++;
                }
            }
            setCurrentPlan(window.currentPlan);
            if (outEl) {
                outEl.classList.remove('hidden');
                outEl.style.display = 'block';
                outEl.textContent = `🔍 Beat Punch-In Zoom eğrisi ${applied} sahneye (30 FPS keyframe dizisi) eklendi.`;
            }
            showToast(`🔍 ${applied} sahneye Beat Punch-In Zoom eğrisi eklendi`);
        } catch (err) { showToast('Punch-In hatası: ' + err.message, 'error'); }
    });
});

document.addEventListener('keydown', e => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        const activeTab = document.querySelector('.nav-btn.active')?.getAttribute('data-tab');
        if (activeTab === 'timeline' && window.currentPlan) {
            e.preventDefault();
            if (typeof collectTimelineEdits === 'function') collectTimelineEdits();
            if (typeof startRenderProcess === 'function') startRenderProcess(window.currentPlan);
        }
    }
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        const activeTab = document.querySelector('.nav-btn.active')?.getAttribute('data-tab');
        if (activeTab === 'timeline' && window.currentPlan) {
            e.preventDefault();
            if (typeof collectTimelineEdits === 'function') collectTimelineEdits();
            if (typeof updateComplianceDashboard === 'function') updateComplianceDashboard(window.currentPlan.scenes || []);
            showToast('💾 Kaydedildi');
        }
    }
});
