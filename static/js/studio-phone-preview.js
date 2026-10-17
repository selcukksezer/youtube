/**
 * ShortsAI Studio — Category F (Items 51–60)
 * Sağdaki Canlı 9:16 Telefon Önizlemesi:
 *  51. Senaryo Sahneleri Arası Kaydırma (< S1 / S6 >)
 *  52. YouTube Shorts Güvenli Alan (Safe Zone) Izgarası
 *  53. Canlı Ses + Altyazı Senkron Provası (Animatic Preview)
 *  54. Altyazı Y-Konumu Sürükleme (Üst / Orta / Alt)
 *  55. Cihaz Çerçevesi Değiştirici (iPhone 16 Pro / Android / Çerçevesiz)
 *  56. YouTube Başlık & Kanal Adı Canlı Simülasyonu
 *  57. Kanca / Kapanış Sekmeli Kartını Küçültülebilir Yap
 *  58. Renk Filtresi (LUT) Canlı CSS Simülasyonu
 *  59. Tam Ekran Önizleme (⛶)
 *  60. Watermark / Logo Konumu Önizlemesi
 */
(function () {
    'use strict';

    let activePreviewSceneIdx = 0;
    let animaticTimer = null;
    let animaticPlaying = false;
    let watermarkCornerIdx = 0; // 0: Sağ Üst, 1: Sol Üst, 2: Sağ Alt, 3: Gizli
    const WATERMARK_CORNERS = [
        { cls: 'wm-top-right', label: 'Sağ Üst' },
        { cls: 'wm-top-left', label: 'Sol Üst' },
        { cls: 'wm-bottom-right', label: 'Sağ Alt' },
        { cls: 'wm-hidden', label: 'Gizli' }
    ];

    const LUT_CSS_FILTERS = {
        cinematic_contrast: 'contrast(1.16) saturate(1.12) brightness(0.97)',
        moody_dark: 'contrast(1.22) saturate(0.82) brightness(0.88)',
        warm_amber: 'sepia(0.24) saturate(1.25) contrast(1.08)',
        cyber_neon: 'saturate(1.42) contrast(1.18) hue-rotate(-8deg)',
        none: 'none'
    };

    function escapeHtmlSafe(str) {
        return String(str || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function getScenesList() {
        if (Array.isArray(window.currentPlan?.scenes) && window.currentPlan.scenes.length) {
            return window.currentPlan.scenes;
        }
        return [
            { narration: 'Bu kuralı öğrenene kadar hayatınız kontrolünüzde değildi...', duration: 4.0, mood: 'epic', highlight_word: 'KURALI' },
            { narration: 'Beynimiz belirsizlik anında en tanıdık tuzağa düşer.', duration: 4.5, mood: 'mysterious', highlight_word: 'BELİRSİZLİK' },
            { narration: 'İlk üç saniyede dikkati kilitleyen gizli mekanizma budur.', duration: 4.5, mood: 'dramatic', highlight_word: 'DİKKATİ' },
            { narration: 'Ve tam da bu yüzden asla unutmayın çünkü döngü burada başlar.', duration: 4.0, mood: 'epic', highlight_word: 'UNUTMAYIN' }
        ];
    }

    // ── 55, 59, 52: Header Toolbar inside .preview-mockup-card ───────────────
    function ensurePhoneHeaderControls() {
        const card = document.querySelector('.preview-mockup-card');
        const header = card?.querySelector('.box-header');
        if (!card || !header || document.getElementById('wiz-phone-top-controls')) return;

        const bar = document.createElement('div');
        bar.id = 'wiz-phone-top-controls';
        bar.className = 'wiz-phone-top-controls';
        bar.innerHTML = `
            <select id="select-phone-device-frame" class="wiz-phone-device-select" title="Cihaz Çerçevesi Değiştir (Madde 55)">
                <option value="device-iphone">📱 iPhone 16 Pro</option>
                <option value="device-android">📲 Android Dar</option>
                <option value="device-frameless">🖼️ Çerçevesiz 9:16</option>
            </select>
            <button type="button" class="wiz-phone-ctrl-btn" id="btn-phone-safe-zone" title="YouTube Shorts Güvenli Alan Izgarasını Aç/Kapat (Madde 52)">
                <i class="fa-solid fa-border-all"></i> Güvenli Alan
            </button>
            <button type="button" class="wiz-phone-ctrl-btn" id="btn-phone-watermark-cycle" title="Filigran / Logo Konumu Değiştir (Madde 60)">
                <i class="fa-solid fa-stamp"></i> <span id="lbl-phone-wm-pos">Logo: Sağ Üst</span>
            </button>
            <button type="button" class="wiz-phone-ctrl-btn" id="btn-phone-fullscreen" title="Tam Ekran / Büyük Önizleme (Madde 59)">
                <i class="fa-solid fa-expand"></i>
            </button>
        `;
        header.after(bar);

        const phoneFrame = card.querySelector('.phone-frame');
        document.getElementById('select-phone-device-frame')?.addEventListener('change', (e) => {
            if (!phoneFrame) return;
            phoneFrame.classList.remove('device-iphone', 'device-android', 'device-frameless');
            phoneFrame.classList.add(e.target.value);
        });

        document.getElementById('btn-phone-safe-zone')?.addEventListener('click', (e) => {
            const grid = document.getElementById('phone-safe-zone-overlay');
            if (!grid) return;
            const open = grid.classList.toggle('hidden') === false;
            e.currentTarget.classList.toggle('is-active', open);
        });

        document.getElementById('btn-phone-watermark-cycle')?.addEventListener('click', () => {
            watermarkCornerIdx = (watermarkCornerIdx + 1) % WATERMARK_CORNERS.length;
            syncWatermarkBadge();
        });

        document.getElementById('btn-phone-fullscreen')?.addEventListener('click', (e) => {
            const expanded = card.classList.toggle('is-expanded-preview');
            e.currentTarget.classList.toggle('is-active', expanded);
            e.currentTarget.innerHTML = expanded
                ? '<i class="fa-solid fa-compress"></i>'
                : '<i class="fa-solid fa-expand"></i>';
        });
    }

    // ── 52, 54, 56, 60: Overlays inside #live-phone-screen ───────────────────
    function ensurePhoneScreenOverlays() {
        const screen = document.getElementById('live-phone-screen');
        if (!screen) return;

        // 52. Safe Zone Grid Overlay
        if (!document.getElementById('phone-safe-zone-overlay')) {
            const sz = document.createElement('div');
            sz.id = 'phone-safe-zone-overlay';
            sz.className = 'phone-safe-zone-overlay hidden';
            sz.innerHTML = `
                <div class="sz-danger-top"><span>⛔ ÜST ARAYÜZ ALANI</span></div>
                <div class="sz-safe-center"><span>✅ GÜVENLİ ALTYAZI & ODAK ALANI</span></div>
                <div class="sz-danger-right"><span>⛔ BUTONLAR</span></div>
                <div class="sz-danger-bottom"><span>⛔ KANAL & BAŞLIK ALANI</span></div>
            `;
            screen.appendChild(sz);
        }

        // 60. Watermark Badge
        if (!document.getElementById('phone-watermark-badge')) {
            const wm = document.createElement('div');
            wm.id = 'phone-watermark-badge';
            wm.className = 'phone-watermark-badge wm-top-right';
            wm.title = 'Konumu değiştirmek için tıklayın';
            wm.innerHTML = `<i class="fa-solid fa-circle-play"></i> <span id="phone-wm-text">@shorts_studio</span>`;
            wm.addEventListener('click', () => {
                watermarkCornerIdx = (watermarkCornerIdx + 1) % WATERMARK_CORNERS.length;
                syncWatermarkBadge();
            });
            screen.appendChild(wm);
        }

        // 56. YouTube Channel & Title Live Simulation
        if (!document.getElementById('phone-yt-meta-sim')) {
            const meta = document.createElement('div');
            meta.id = 'phone-yt-meta-sim';
            meta.className = 'phone-yt-meta-sim';
            meta.innerHTML = `
                <div class="phone-yt-channel-row">
                    <span class="phone-yt-avatar">S</span>
                    <strong id="phone-yt-handle">@shorts_studio</strong>
                    <span class="phone-yt-sub-pill">Abone Ol</span>
                </div>
                <div class="phone-yt-title-line" id="phone-yt-title-line">
                    Beyninizin sizden sakladığı 3 saniyelik karar kuralı #shorts #viral
                </div>
            `;
            screen.appendChild(meta);
        }

        // 54. Make #mockup-sub-overlay draggable vertically (Üst / Orta / Alt)
        const subOverlay = document.getElementById('mockup-sub-overlay');
        if (subOverlay && !subOverlay.dataset.dragBound) {
            subOverlay.dataset.dragBound = '1';
            subOverlay.title = 'Altyazı konumunu değiştirmek için yukarı/aşağı sürükleyin';
            let dragging = false;
            subOverlay.addEventListener('mousedown', (e) => {
                dragging = true;
                subOverlay.classList.add('is-dragging');
                e.preventDefault();
            });
            window.addEventListener('mousemove', (e) => {
                if (!dragging) return;
                const rect = screen.getBoundingClientRect();
                if (!rect.height) return;
                const relY = (e.clientY - rect.top) / rect.height;
                if (relY < 0.36) setSubtitleYPosition('top');
                else if (relY < 0.64) setSubtitleYPosition('middle');
                else setSubtitleYPosition('bottom');
            });
            window.addEventListener('mouseup', () => {
                if (dragging) {
                    dragging = false;
                    subOverlay.classList.remove('is-dragging');
                }
            });
        }
    }

    function setSubtitleYPosition(pos) {
        const subOverlay = document.getElementById('mockup-sub-overlay');
        if (!subOverlay) return;
        subOverlay.classList.remove('sub-pos-top', 'sub-pos-middle', 'sub-pos-bottom');
        subOverlay.classList.add(`sub-pos-${pos}`);
        document.querySelectorAll('.wiz-sub-pos-btn').forEach(btn => {
            btn.classList.toggle('active', btn.getAttribute('data-pos') === pos);
        });
    }

    function syncWatermarkBadge() {
        const wm = document.getElementById('phone-watermark-badge');
        const lbl = document.getElementById('lbl-phone-wm-pos');
        const cfg = WATERMARK_CORNERS[watermarkCornerIdx] || WATERMARK_CORNERS[0];
        if (wm) {
            wm.className = `phone-watermark-badge ${cfg.cls}`;
        }
        if (lbl) lbl.textContent = `Logo: ${cfg.label}`;
    }

    // ── 51, 53, 54: Scene Stepper & Animatic Preview Bar below .phone-frame ──
    function ensurePhoneSceneStepperAndAnimatic() {
        const phoneFrame = document.querySelector('.preview-mockup-card .phone-frame');
        if (!phoneFrame || document.getElementById('wiz-phone-scene-stepper')) return;

        const panel = document.createElement('div');
        panel.id = 'wiz-phone-scene-stepper';
        panel.className = 'wiz-phone-scene-stepper';
        panel.innerHTML = `
            <div class="wiz-pss-nav-row">
                <button type="button" class="wiz-pss-btn" id="btn-pss-prev" title="Önceki Sahne">
                    <i class="fa-solid fa-chevron-left"></i>
                </button>
                <div class="wiz-pss-indicator">
                    <span class="wiz-pss-badge" id="wiz-pss-label">S1 / S4</span>
                    <span class="wiz-pss-beat" id="wiz-pss-beat">🎯 Kanca</span>
                </div>
                <button type="button" class="wiz-pss-btn" id="btn-pss-next" title="Sonraki Sahne">
                    <i class="fa-solid fa-chevron-right"></i>
                </button>
                <button type="button" class="wiz-pss-animatic-btn" id="btn-phone-animatic-play" title="Tam render almadan ses ve altyazı akışını prova et (Madde 53)">
                    <i class="fa-solid fa-play"></i> 3 Sn Prova Oynat
                </button>
            </div>
            <div class="wiz-pss-subpos-row" id="phone-sub-pos-strip">
                <span class="wiz-pss-subpos-lbl"><i class="fa-solid fa-arrows-up-down"></i> Altyazı Konumu:</span>
                <button type="button" class="wiz-sub-pos-btn" data-pos="top">Üst</button>
                <button type="button" class="wiz-sub-pos-btn active" data-pos="middle">Orta</button>
                <button type="button" class="wiz-sub-pos-btn" data-pos="bottom">Alt</button>
            </div>
        `;
        phoneFrame.after(panel);

        document.getElementById('btn-pss-prev')?.addEventListener('click', () => {
            const scenes = getScenesList();
            activePreviewSceneIdx = (activePreviewSceneIdx - 1 + scenes.length) % scenes.length;
            renderPhoneSceneAt(activePreviewSceneIdx);
        });
        document.getElementById('btn-pss-next')?.addEventListener('click', () => {
            const scenes = getScenesList();
            activePreviewSceneIdx = (activePreviewSceneIdx + 1) % scenes.length;
            renderPhoneSceneAt(activePreviewSceneIdx);
        });
        document.getElementById('btn-phone-animatic-play')?.addEventListener('click', toggleAnimaticPreview);

        panel.querySelectorAll('.wiz-sub-pos-btn').forEach(btn => {
            btn.addEventListener('click', () => setSubtitleYPosition(btn.getAttribute('data-pos') || 'middle'));
        });
    }

    function renderPhoneSceneAt(idx) {
        const scenes = getScenesList();
        if (!scenes.length) return;
        const safeIdx = Math.max(0, Math.min(idx, scenes.length - 1));
        activePreviewSceneIdx = safeIdx;
        const sc = scenes[safeIdx];

        const lbl = document.getElementById('wiz-pss-label');
        const beatEl = document.getElementById('wiz-pss-beat');
        if (lbl) lbl.textContent = `S${safeIdx + 1} / S${scenes.length}`;
        if (beatEl) {
            let beat = '⚔️ Gelişme';
            if (safeIdx === 0) beat = '🎯 Kanca';
            else if (safeIdx === scenes.length - 1) beat = '🔄 Kapanış';
            else if (safeIdx === Math.floor(scenes.length * 0.65)) beat = '🔥 Doruk';
            beatEl.textContent = `${beat} · ${(parseFloat(sc.duration) || 3.5).toFixed(1)}sn`;
        }

        const subOverlay = document.getElementById('mockup-sub-overlay');
        if (subOverlay) {
            const raw = String(sc.narration || '').replace(/\*\*[A-Z]+\*\*/g, '').trim();
            const words = raw.split(/\s+/).filter(Boolean).slice(0, 7);
            const hl = (sc.highlight_word || words[0] || 'SHORTS').toUpperCase();
            if (words.length) {
                const formatted = words.map((w, wi) => {
                    const cleanW = w.replace(/[.,!?;:"]/g, '').toUpperCase();
                    if (cleanW === hl || (wi === 0 && !sc.highlight_word)) {
                        return `<span class="sub-word-highlight">${escapeHtmlSafe(w.toUpperCase())}</span>`;
                    }
                    return escapeHtmlSafe(w.toUpperCase());
                }).join(' ');
                subOverlay.innerHTML = formatted;
            }
        }

        const statusText = document.getElementById('mockup-status-text');
        if (statusText && sc.scene_description) {
            statusText.textContent = `Sahne ${safeIdx + 1}: ${sc.scene_description.slice(0, 68)}`;
        }
    }

    // ── 53. Animatic Preview Player ──────────────────────────────────────────
    function toggleAnimaticPreview() {
        const btn = document.getElementById('btn-phone-animatic-play');
        if (animaticPlaying) {
            stopAnimaticPreview();
            return;
        }
        const scenes = getScenesList();
        if (!scenes.length) return;
        animaticPlaying = true;
        if (btn) {
            btn.classList.add('is-playing');
            btn.innerHTML = '<i class="fa-solid fa-stop"></i> Provayı Durdur';
        }
        activePreviewSceneIdx = 0;
        renderPhoneSceneAt(0);
        if (typeof previewSceneAudio === 'function' && scenes[0]?.narration) {
            previewSceneAudio(scenes[0].narration, null);
        }
        let stepCount = 0;
        animaticTimer = setInterval(() => {
            stepCount++;
            if (stepCount >= scenes.length) {
                stopAnimaticPreview();
                return;
            }
            renderPhoneSceneAt(stepCount);
        }, 1200);
    }

    function stopAnimaticPreview() {
        animaticPlaying = false;
        if (animaticTimer) {
            clearInterval(animaticTimer);
            animaticTimer = null;
        }
        if (typeof window.stopSceneAudioPreview === 'function') {
            window.stopSceneAudioPreview();
        }
        const btn = document.getElementById('btn-phone-animatic-play');
        if (btn) {
            btn.classList.remove('is-playing');
            btn.innerHTML = '<i class="fa-solid fa-play"></i> 3 Sn Prova Oynat';
        }
    }

    // ── 56 & 58: Sync YouTube Metadata & LUT CSS Filter ──────────────────────
    function syncPhoneLiveMetaAndLut() {
        const topic = document.getElementById('input-topic')?.value?.trim()
            || window.currentPlan?.title
            || 'Beyninizin sizden sakladığı 3 saniyelik karar kuralı';
        const chSelect = document.getElementById('select-upload-channel') || document.getElementById('pub-target-channel-select');
        const chName = chSelect?.selectedOptions?.[0]?.textContent?.trim() || 'shorts_studio';
        const cleanHandle = '@' + chName.replace(/[^a-zA-Z0-9_]/g, '_').toLowerCase().slice(0, 18);

        const handleEl = document.getElementById('phone-yt-handle');
        const wmText = document.getElementById('phone-wm-text');
        const titleEl = document.getElementById('phone-yt-title-line');
        if (handleEl) handleEl.textContent = cleanHandle === '@_' ? '@shorts_studio' : cleanHandle;
        if (wmText) wmText.textContent = handleEl?.textContent || '@shorts_studio';
        if (titleEl) titleEl.textContent = `${topic.slice(0, 62)} #shorts #viral`;

        const lutVal = (document.getElementById('select-color-lut') || document.getElementById('tl-select-style-profile') || document.getElementById('tl-select-helios-style'))?.value || 'cinematic_contrast';
        const videoArea = document.getElementById('phone-video-area');
        if (videoArea) {
            videoArea.style.filter = LUT_CSS_FILTERS[lutVal] || LUT_CSS_FILTERS.cinematic_contrast || 'none';
        }
    }

    // ── 57. Collapsible / Tabbed Hook & Loop Bridge Card ─────────────────────
    function enhanceLoopBridgeCard() {
        const bridgeCard = document.querySelector('.preview-mockup-card .loop-bridge-card');
        if (!bridgeCard || bridgeCard.dataset.compactEnhanced) return;
        bridgeCard.dataset.compactEnhanced = '1';

        const header = document.createElement('div');
        header.className = 'wiz-bridge-tabs-bar';
        header.innerHTML = `
            <button type="button" class="wiz-bridge-tab active" data-btab="hook">🎯 Kanca (0-3 sn)</button>
            <button type="button" class="wiz-bridge-tab" data-btab="loop">🔄 Kapanış Döngüsü</button>
            <button type="button" class="wiz-bridge-collapse-btn" id="btn-toggle-bridge-body" title="Daralt / Genişlet">
                <i class="fa-solid fa-chevron-up"></i>
            </button>
        `;
        bridgeCard.prepend(header);

        const cols = bridgeCard.querySelectorAll('.bridge-col');
        const arrow = bridgeCard.querySelector('.bridge-arrow');
        if (arrow) arrow.style.display = 'none';
        if (cols[1]) cols[1].classList.add('hidden');

        header.querySelectorAll('.wiz-bridge-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                header.querySelectorAll('.wiz-bridge-tab').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                const mode = tab.getAttribute('data-btab');
                bridgeCard.classList.remove('is-collapsed');
                if (cols[0]) cols[0].classList.toggle('hidden', mode !== 'hook');
                if (cols[1]) cols[1].classList.toggle('hidden', mode !== 'loop');
            });
        });

        document.getElementById('btn-toggle-bridge-body')?.addEventListener('click', (e) => {
            const collapsed = bridgeCard.classList.toggle('is-collapsed');
            e.currentTarget.innerHTML = collapsed
                ? '<i class="fa-solid fa-chevron-down"></i>'
                : '<i class="fa-solid fa-chevron-up"></i>';
        });
    }

    function syncPhonePreviewAll() {
        ensurePhoneHeaderControls();
        ensurePhoneScreenOverlays();
        ensurePhoneSceneStepperAndAnimatic();
        enhanceLoopBridgeCard();
        renderPhoneSceneAt(activePreviewSceneIdx);
        syncPhoneLiveMetaAndLut();
    }

    function initStudioPhonePreviewUX() {
        syncPhonePreviewAll();
        document.getElementById('input-topic')?.addEventListener('input', syncPhoneLiveMetaAndLut);
        (document.getElementById('select-color-lut') || document.getElementById('tl-select-style-profile') || document.getElementById('tl-select-helios-style'))?.addEventListener('change', syncPhoneLiveMetaAndLut);
        (document.getElementById('select-upload-channel') || document.getElementById('pub-target-channel-select'))?.addEventListener('change', syncPhoneLiveMetaAndLut);
    }

    window.syncPhonePreviewAll = syncPhonePreviewAll;
    window.renderPhoneSceneAt = renderPhoneSceneAt;

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initStudioPhonePreviewUX);
    } else {
        initStudioPhonePreviewUX();
    }
})();
