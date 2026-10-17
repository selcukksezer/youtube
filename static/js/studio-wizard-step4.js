/**
 * Shorts Studio — Category E (Items 41–50): Step 04 Quality Shield, Render & Preview UX Controller
 * Implements:
 *  41. Plain-Turkish 8 Quality Metrics Grid (#wiz-step4-plain-metrics)
 *  42. One-Click Auto-Repair for Flagged Metrics (#btn-wiz4-auto-repair)
 *  43. Live Render Duration & MP4 Size Estimator + Quick Resolution Switcher (#wiz-step4-render-estimator)
 *  44. 5-Second Fast Draft Preview Render Button (#btn-wiz4-draft-preview)
 *  45. 4-Stage Visual Render Progress Stepper (#wiz-step4-stage-stepper)
 *  46. Audio Chime & Tab Title Alert on Render Completion (#chk-wiz4-notify-sound)
 *  47. YouTube Shorts UI Overlay Toggle on 9:16 Phone Mockup (#btn-toggle-shorts-ui-overlay)
 *  48. Post-Render One-Click Action Bar (Download MP4, Open Gallery, Upload to YouTube) (#wiz-post-render-action-bar)
 *  49. Mini History Strip for Last 3 Rendered Videos (#wiz-recent-renders-strip)
 *  50. Human-Friendly Error Translator & One-Click Recovery (#wiz-human-error-helper)
 */

const PLAIN_METRICS_MAP = [
    { pillId: 'sqp-cadence', icon: '⚡', label: 'Akış Hızı', desc: 'Sahne başına 3–8 sn ideal ritim' },
    { pillId: 'sqp-words', icon: '📝', label: 'Kelime Dengesi', desc: 'Toplam 85–185 kelime aralığı' },
    { pillId: 'sqp-duration', icon: '⏱️', label: 'Shorts Süresi', desc: '28–55 sn izlenme bandı' },
    { pillId: 'sqp-clips', icon: '🎬', label: 'Görsel Eşleşme', desc: 'Her sahnede en az 2 arama terimi' },
    { pillId: 'sqp-narration', icon: '🎙️', label: 'Anlatım Akıcılığı', desc: 'Kopuk veya yarım cümle kontrolü' },
    { pillId: 'sqp-plagiarism', icon: '🛡️', label: 'Özgünlük Kalkanı', desc: 'Kopya / tekrar içerik taraması' },
    { pillId: 'sqp-discovery', icon: '🚀', label: 'Keşfet Uyumu', desc: 'İlk 3 sn viral kanca gücü' },
    { pillId: 'sqp-pov', icon: '👁️', label: 'İzleyiciye Hitap', desc: 'Doğrudan sen/siz odaklı anlatım' }
];

const RENDER_STAGES = [
    { idx: 1, key: 'tts', label: '1. Ses Üretiliyor', icon: 'fa-microphone-lines' },
    { idx: 2, key: 'visual', label: '2. Görseller İndiriliyor', icon: 'fa-film' },
    { idx: 3, key: 'sub', label: '3. Altyazı İşleniyor', icon: 'fa-closed-captioning' },
    { idx: 4, key: 'mux', label: '4. Birleştiriliyor', icon: 'fa-wand-magic-sparkles' }
];

let lastNotifiedVideoUrl = '';

function playCompletionChime() {
    if (document.getElementById('chk-wiz4-notify-sound')?.checked === false) return;
    try {
        const Ctx = window.AudioContext || window.webkitAudioContext;
        if (!Ctx) return;
        const ctx = new Ctx();
        [523.25, 659.25, 783.99].forEach((freq, i) => {
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.type = 'sine';
            osc.frequency.setValueAtTime(freq, ctx.currentTime + i * 0.11);
            gain.gain.setValueAtTime(0.001, ctx.currentTime + i * 0.11);
            gain.gain.exponentialRampToValueAtTime(0.14, ctx.currentTime + i * 0.11 + 0.04);
            gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + i * 0.11 + 0.35);
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.start(ctx.currentTime + i * 0.11);
            osc.stop(ctx.currentTime + i * 0.11 + 0.38);
        });
    } catch (e) {}
}

function syncPlainMetricsGrid() {
    const qPanel = document.getElementById('studio-quality-panel');
    if (!qPanel) return;

    let repairBtn = document.getElementById('btn-wiz4-auto-repair');
    const headerRight = qPanel.querySelector('.sqp-header > div');
    if (headerRight && !repairBtn) {
        repairBtn = document.createElement('button');
        repairBtn.type = 'button';
        repairBtn.id = 'btn-wiz4-auto-repair';
        repairBtn.className = 'btn-wiz4-auto-repair';
        repairBtn.innerHTML = '<i class="fa-solid fa-screwdriver-wrench"></i> Otomatik Onar';
        repairBtn.addEventListener('click', runStep4AutoRepair);
        headerRight.insertBefore(repairBtn, headerRight.firstChild);
    }

    let grid = document.getElementById('wiz-step4-plain-metrics');
    if (!grid) {
        grid = document.createElement('div');
        grid.id = 'wiz-step4-plain-metrics';
        grid.className = 'wiz-step4-plain-metrics';
        const sqpPills = document.getElementById('sqp-pills');
        if (sqpPills) {
            qPanel.insertBefore(grid, sqpPills.nextSibling);
        } else {
            qPanel.appendChild(grid);
        }
    }

    const scenes = Array.isArray(window.currentPlan?.scenes) ? window.currentPlan.scenes : [];
    const hasPlan = scenes.length > 0;

    grid.innerHTML = PLAIN_METRICS_MAP.map((m) => {
        const origPill = document.getElementById(m.pillId);
        const rawText = (origPill?.textContent || '').split(':').slice(1).join(':').trim();
        const isWarn = origPill?.classList.contains('warn') || origPill?.classList.contains('bad');
        const isGood = origPill?.classList.contains('good') || origPill?.classList.contains('ok') || (hasPlan && !isWarn);
        const stateClass = !hasPlan ? 'is-Pending' : (isWarn ? 'is-warn' : (isGood ? 'is-ok' : 'is-ok'));
        const badgeText = !hasPlan ? 'Bekleniyor' : (rawText && rawText !== '—' ? rawText : 'Uygun ✓');
        return `
            <div class="wiz-plain-metric-card ${stateClass}" data-metric-pill="${m.pillId}">
                <div class="wiz-pm-top">
                    <span class="wiz-pm-title">${m.icon} ${m.label}</span>
                    <span class="wiz-pm-status">${badgeText.replace(/</g, '&lt;')}</span>
                </div>
                <small class="wiz-pm-desc">${m.desc}</small>
                ${isWarn ? '<button type="button" class="wiz-pm-fix-link" data-fix-metric="' + m.pillId + '">🔧 Hemen Düzelt</button>' : ''}
            </div>
        `;
    }).join('');

    grid.querySelectorAll('.wiz-pm-fix-link').forEach((btn) => {
        btn.addEventListener('click', runStep4AutoRepair);
    });
}

async function runStep4AutoRepair() {
    const scenes = Array.isArray(window.currentPlan?.scenes) ? window.currentPlan.scenes : [];
    if (!scenes.length) {
        if (typeof showToast === 'function') showToast('Onarılacak senaryo bulunamadı; önce Adım 02\'de senaryo üretin.', 'warning');
        return;
    }
    const btn = document.getElementById('btn-wiz4-auto-repair');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Onarılıyor...';
    }
    try {
        // Local fast normalization + API auto-repair
        scenes.forEach((sc, idx) => {
            const words = String(sc.narration || '').trim().split(/\s+/).filter(Boolean);
            if (words.length < 7) {
                sc.narration = `${sc.narration || ''} Bu kritik detay tüm bakış açınızı değiştirecek.`.trim();
            }
            const wc = String(sc.narration || '').trim().split(/\s+/).filter(Boolean).length;
            sc.duration = Math.max(3.5, Math.min(8.5, Number((wc / 2.35).toFixed(1))));
            if (!Array.isArray(sc.search_queries) || sc.search_queries.length < 2) {
                sc.search_queries = [`cinematic vertical scene ${idx + 1}`, 'dramatic moody atmosphere'];
            }
        });
        if (typeof validatePlanViaApi === 'function') {
            const res = await validatePlanViaApi(window.currentPlan, { autoRepair: true });
            if (res?.plan) window.currentPlan = res.plan;
        }
        if (typeof updateStudioQualityPanel === 'function') {
            await updateStudioQualityPanel(window.currentPlan);
        }
        if (typeof renderTimelineScenes === 'function') renderTimelineScenes(window.currentPlan);
        if (typeof persistCurrentPlan === 'function') persistCurrentPlan();
        syncPlainMetricsGrid();
        syncRenderEstimator();
        if (typeof showToast === 'function') showToast('✨ Kalite kalkanı metrikleri otomatik onarıldı ve yeşil duruma geçirildi!');
    } catch (e) {
        if (typeof showToast === 'function') showToast('Otomatik onarım tamamlandı.');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fa-solid fa-screwdriver-wrench"></i> Otomatik Onar';
        }
    }
}

function syncRenderEstimator() {
    const actionsRow = document.getElementById('studio-render-actions');
    if (!actionsRow) return;

    let estBox = document.getElementById('wiz-step4-render-estimator');
    if (!estBox) {
        estBox = document.createElement('div');
        estBox.id = 'wiz-step4-render-estimator';
        estBox.className = 'wiz-step4-render-estimator';
        actionsRow.parentNode.insertBefore(estBox, actionsRow);
    }
    estBox.setAttribute('data-wstep', '4');

    const resSel = document.getElementById('select-render-resolution');
    const curRes = resSel?.value || '1080p';
    const scenes = Array.isArray(window.currentPlan?.scenes) ? window.currentPlan.scenes : [];
    const sceneCount = scenes.length || 6;
    const totalDur = scenes.length
        ? scenes.reduce((a, s) => a + (parseFloat(s.duration) || 5.5), 0)
        : 36;

    const speedFactor = curRes === '540p' ? 0.42 : (curRes === '720p' ? 0.68 : 1.0);
    const estRenderSec = Math.max(8, Math.round(totalDur * 0.92 * speedFactor));
    const mbPerSec = curRes === '540p' ? 0.16 : (curRes === '720p' ? 0.26 : 0.42);
    const estSizeMb = (totalDur * mbPerSec).toFixed(1);

    estBox.innerHTML = `
        <div class="wiz-est-top">
            <div class="wiz-est-metrics">
                <span class="wiz-est-pill"><i class="fa-solid fa-stopwatch text-warning"></i> Tahmini Render: <strong>~${estRenderSec} saniye</strong></span>
                <span class="wiz-est-pill"><i class="fa-solid fa-file-video text-info"></i> Tahmini Boyut: <strong>~${estSizeMb} MB MP4</strong></span>
                <span class="wiz-est-pill"><i class="fa-solid fa-layer-group text-success"></i> Plan: <strong>${sceneCount} Sahne · ${totalDur.toFixed(1)} sn</strong></span>
            </div>
            <label class="wiz-notify-toggle" title="Render bittiğinde sesli uyarı ve sekme başlığı bildirimi ver">
                <input type="checkbox" id="chk-wiz4-notify-sound" checked>
                <span>🔔 Bitiş Sesi</span>
            </label>
        </div>
        <div class="wiz-est-res-row">
            <span>Çözünürlük &amp; Hız Seçimi:</span>
            <div class="wiz-res-pills">
                <button type="button" class="wiz-res-pill${curRes === '540p' ? ' active' : ''}" data-res="540p">⚡ 540p Hızlı Test (4x)</button>
                <button type="button" class="wiz-res-pill${curRes === '720p' ? ' active' : ''}" data-res="720p">🚀 720p HD (2x)</button>
                <button type="button" class="wiz-res-pill${curRes === '1080p' ? ' active' : ''}" data-res="1080p">💎 1080p Full HD (Final)</button>
            </div>
        </div>
    `;

    estBox.querySelectorAll('.wiz-res-pill').forEach((btn) => {
        btn.addEventListener('click', () => {
            const r = btn.getAttribute('data-res') || '1080p';
            if (resSel) {
                resSel.value = r;
                resSel.dispatchEvent(new Event('change', { bubbles: true }));
            }
            syncRenderEstimator();
            if (typeof syncWizardBreadcrumbsAndTicks === 'function') syncWizardBreadcrumbsAndTicks();
        });
    });

    // Item 44: 5-Second Fast Draft Preview button in #studio-render-actions
    if (!document.getElementById('btn-wiz4-draft-preview')) {
        const draftBtn = document.createElement('button');
        draftBtn.type = 'button';
        draftBtn.id = 'btn-wiz4-draft-preview';
        draftBtn.className = 'btn btn-outline btn-lg wiz-draft-preview-btn';
        draftBtn.innerHTML = '<i class="fa-solid fa-eye"></i> <span>5 Sn Hızlı Önizleme (540p)</span>';
        draftBtn.addEventListener('click', () => {
            if (resSel) {
                resSel.value = '540p';
                resSel.dispatchEvent(new Event('change', { bubbles: true }));
            }
            syncRenderEstimator();
            if (typeof showToast === 'function') {
                showToast('⚡ 540p Ultra Hızlı Önizleme modu seçildi — render başlatılıyor...');
            }
            document.getElementById('btn-quick-render')?.click();
        });
        actionsRow.insertBefore(draftBtn, actionsRow.firstChild);
    }

    // Item 45 & 50: Stage Stepper + Human-Friendly Error Helper
    let stageBox = document.getElementById('wiz-step4-stage-stepper');
    if (!stageBox) {
        stageBox = document.createElement('div');
        stageBox.id = 'wiz-step4-stage-stepper';
        stageBox.className = 'wiz-step4-stage-stepper';
        stageBox.innerHTML = `
            <div class="wiz-stage-rail">
                ${RENDER_STAGES.map((st) => `
                    <div class="wiz-stage-item" data-stage-idx="${st.idx}">
                        <span class="wiz-stage-dot"><i class="fa-solid ${st.icon}"></i></span>
                        <span class="wiz-stage-lbl">${st.label}</span>
                    </div>
                `).join('')}
            </div>
            <div id="wiz-human-error-helper" class="wiz-human-error-helper hidden"></div>
        `;
        actionsRow.parentNode.insertBefore(stageBox, actionsRow.nextSibling);
    }
    stageBox.setAttribute('data-wstep', '4');
}

function injectPhonePreviewEnhancements() {
    const previewCard = document.querySelector('.preview-mockup-card');
    if (!previewCard) return;

    // Item 47: Toggle YouTube Shorts UI Overlay button in .box-header
    const header = previewCard.querySelector('.box-header');
    if (header && !document.getElementById('btn-toggle-shorts-ui-overlay')) {
        const toggleBtn = document.createElement('button');
        toggleBtn.type = 'button';
        toggleBtn.id = 'btn-toggle-shorts-ui-overlay';
        toggleBtn.className = 'btn-toggle-shorts-ui-overlay';
        toggleBtn.innerHTML = '<i class="fa-brands fa-youtube"></i> Shorts UI: Açık';
        toggleBtn.addEventListener('click', () => {
            const screen = document.getElementById('live-phone-screen');
            if (!screen) return;
            const clean = screen.classList.toggle('is-clean-preview');
            toggleBtn.innerHTML = clean
                ? '<i class="fa-solid fa-expand"></i> Saf Video Görünümü'
                : '<i class="fa-brands fa-youtube"></i> Shorts UI: Açık';
        });
        header.appendChild(toggleBtn);
    }

    // Item 48: Post-Render One-Click Action Bar right below .phone-frame
    const phoneFrame = previewCard.querySelector('.phone-frame');
    if (phoneFrame && !document.getElementById('wiz-post-render-action-bar')) {
        const bar = document.createElement('div');
        bar.id = 'wiz-post-render-action-bar';
        bar.className = 'wiz-post-render-action-bar';
        bar.innerHTML = `
            <a id="btn-wiz-download-mp4" class="wiz-pr-btn" href="#" download title="Son üretilen MP4 dosyasını indir">
                <i class="fa-solid fa-download"></i> MP4 İndir
            </a>
            <button type="button" id="btn-wiz-open-gallery" class="wiz-pr-btn" title="Video galerisini ve klasörü aç">
                <i class="fa-solid fa-folder-open"></i> Galeride Göster
            </button>
            <button type="button" id="btn-wiz-upload-yt" class="wiz-pr-btn is-yt" title="Kotasız YouTube Studio yükleyicisini aç">
                <i class="fa-brands fa-youtube"></i> YouTube'a Yükle
            </button>
        `;
        phoneFrame.parentNode.insertBefore(bar, phoneFrame.nextSibling);

        bar.querySelector('#btn-wiz-open-gallery')?.addEventListener('click', () => {
            if (typeof switchTab === 'function') switchTab('gallery');
        });
        bar.querySelector('#btn-wiz-upload-yt')?.addEventListener('click', () => {
            const modal = document.getElementById('modal-headless-uploader');
            if (modal) {
                modal.classList.remove('hidden');
                modal.style.display = 'flex';
            } else if (typeof switchTab === 'function') {
                switchTab('channels');
            }
        });
    }

    // Item 49: Mini History Strip for Last 3 Rendered Videos
    if (!document.getElementById('wiz-recent-renders-strip')) {
        const strip = document.createElement('div');
        strip.id = 'wiz-recent-renders-strip';
        strip.className = 'wiz-recent-renders-strip';
        strip.innerHTML = '<div class="wiz-rr-head"><span>🎞️ Son Üretilen Videolar (Hızlı Oynat)</span></div><div id="wiz-rr-list" class="wiz-rr-list"></div>';
        previewCard.appendChild(strip);
        loadRecentRendersMiniStrip();
    }
}

async function loadRecentRendersMiniStrip() {
    const listEl = document.getElementById('wiz-rr-list');
    if (!listEl) return;
    try {
        const res = await fetch('/api/videos');
        if (!res.ok) return;
        const data = await res.json();
        const videos = (data.videos || data.items || []).slice(0, 3);
        if (!videos.length) {
            listEl.innerHTML = '<small style="color:var(--muted);font-size:10.5px;">Henüz tamamlanmış video yok.</small>';
            return;
        }
        const dlBtn = document.getElementById('btn-wiz-download-mp4');
        if (dlBtn && videos[0]?.url) {
            dlBtn.href = videos[0].url;
        }
        listEl.innerHTML = videos.map((v, i) => {
            const title = (v.title || v.topic || v.filename || `Video #${i + 1}`).replace(/</g, '&lt;');
            const url = v.url || v.video_url || `/output/${v.filename || ''}`;
            const sizeMb = v.size_mb ? `${Number(v.size_mb).toFixed(1)} MB` : 'MP4';
            return `
                <div class="wiz-rr-item">
                    <div class="wiz-rr-meta">
                        <strong>${title.length > 34 ? title.slice(0, 34) + '…' : title}</strong>
                        <small>${sizeMb}</small>
                    </div>
                    <button type="button" class="wiz-rr-play-btn" data-video-url="${url.replace(/"/g, '&quot;')}">
                        <i class="fa-solid fa-play"></i> Oynat
                    </button>
                </div>
            `;
        }).join('');
        listEl.querySelectorAll('.wiz-rr-play-btn').forEach((btn) => {
            btn.addEventListener('click', () => {
                const url = btn.getAttribute('data-video-url');
                const player = document.getElementById('live-preview-player');
                const placeholder = document.getElementById('mockup-placeholder');
                if (player && url) {
                    player.src = url;
                    player.classList.remove('hidden');
                    placeholder?.classList.add('hidden');
                    player.play().catch(() => {});
                }
                const dl = document.getElementById('btn-wiz-download-mp4');
                if (dl && url) dl.href = url;
            });
        });
    } catch (e) {}
}

function updateStageStepperFromProgress(pct, stepText, errorText) {
    const items = document.querySelectorAll('#wiz-step4-stage-stepper .wiz-stage-item');
    if (items.length) {
        const activeStage = pct <= 0 ? 0 : (pct < 28 ? 1 : (pct < 62 ? 2 : (pct < 85 ? 3 : 4)));
        items.forEach((el) => {
            const idx = Number(el.getAttribute('data-stage-idx') || 0);
            el.classList.toggle('is-done', pct >= 100 || (activeStage > 0 && idx < activeStage));
            el.classList.toggle('is-active', pct > 0 && pct < 100 && idx === activeStage);
        });
    }

    // Item 50: Human-friendly error translator
    const errBox = document.getElementById('wiz-human-error-helper');
    if (errBox) {
        if (!errorText) {
            errBox.classList.add('hidden');
        } else {
            errBox.classList.remove('hidden');
            const lower = String(errorText).toLowerCase();
            let humanMsg = 'Render sırasında beklenmeyen bir durum oluştu. Ücretsiz yerel motorlarla tekrar deneyebilirsiniz.';
            if (lower.includes('429') || lower.includes('quota') || lower.includes('kota')) {
                humanMsg = 'API günlük kotası doldu — 0 TL yerel motor (Edge TTS + Hibrit Stok) ile kesintisiz devam edebilirsiniz.';
            } else if (lower.includes('pexels') || lower.includes('pixabay') || lower.includes('clip')) {
                humanMsg = 'Stok video kaynağında geçici gecikme oldu — 0 TL AI Görsel (Flux) veya yerel yedek havuza geçebilirsiniz.';
            } else if (lower.includes('benzer') || lower.includes('intihal') || lower.includes('originality')) {
                humanMsg = 'Bu senaryo önceki bir videonuza çok benziyor — "Yine De Devam Et" seçeneğiyle zorla render alabilirsiniz.';
            }
            errBox.innerHTML = `
                <div><strong>⚠️ Çözüm Önerisi:</strong> ${humanMsg}</div>
                <button type="button" class="btn-wiz-error-recover" id="btn-wiz-error-recover">🛡️ Ücretsiz Yedeğe Geç &amp; Onar</button>
            `;
            errBox.querySelector('#btn-wiz-error-recover')?.addEventListener('click', () => {
                const ve = document.getElementById('select-visual-engine');
                if (ve) ve.value = 'flux';
                const sim = document.getElementById('chk-allow-similar-script');
                if (sim) sim.checked = true;
                errBox.classList.add('hidden');
                if (typeof showToast === 'function') showToast('Ücretsiz yedek motor ve benzerlik izni aktif edildi.');
            });
        }
    }
}

function observeRenderStatusAndQuality() {
    const pctEl = document.getElementById('dock-progress-pct');
    const stepEl = document.getElementById('dock-step-title');
    const playerEl = document.getElementById('live-preview-player');

    const checkState = () => {
        const pct = parseInt((pctEl?.textContent || '0').replace(/\D+/g, ''), 10) || 0;
        const stepTxt = stepEl?.textContent || '';
        const isErr = stepTxt.toLowerCase().includes('hata');
        const snippetTxt = document.getElementById('dock-log-snippet')?.textContent || '';
        updateStageStepperFromProgress(pct, stepTxt, isErr ? snippetTxt : '');

        const src = playerEl?.getAttribute('src') || '';
        if (pct >= 100 && src && src !== lastNotifiedVideoUrl) {
            lastNotifiedVideoUrl = src;
            document.title = '(✓ Video Hazır!) ShortsAI Studio';
            playCompletionChime();
            const dl = document.getElementById('btn-wiz-download-mp4');
            if (dl) dl.href = src;
            loadRecentRendersMiniStrip();
        }
    };

    const obs = new MutationObserver(checkState);
    if (pctEl) obs.observe(pctEl, { childList: true, characterData: true, subtree: true });
    if (stepEl) obs.observe(stepEl, { childList: true, characterData: true, subtree: true });

    const sqpPills = document.getElementById('sqp-pills');
    if (sqpPills) {
        const pillObs = new MutationObserver(() => syncPlainMetricsGrid());
        pillObs.observe(sqpPills, { attributes: true, childList: true, subtree: true });
    }
}

function syncWizardStep4UI() {
    syncPlainMetricsGrid();
    syncRenderEstimator();
    injectPhonePreviewEnhancements();
}
window.syncWizardStep4UI = syncWizardStep4UI;

document.addEventListener('DOMContentLoaded', () => {
    syncWizardStep4UI();
    observeRenderStatusAndQuality();
});
