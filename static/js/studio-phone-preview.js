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
    let previewViewMode = 'auto'; // 'auto' | 'video' | 'draft'
    let lastKnownVideoSrc = '';
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
        return String(str || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function normalizeTrSlug(str) {
        const map = { 'ç': 'c', 'Ç': 'c', 'ğ': 'g', 'Ğ': 'g', 'ı': 'i', 'I': 'i', 'İ': 'i', 'ö': 'o', 'Ö': 'o', 'ş': 's', 'Ş': 's', 'ü': 'u', 'Ü': 'u' };
        return String(str || '').replace(/[çÇğĞıIİöÖşŞüÜ]/g, ch => map[ch] || ch).toLowerCase().replace(/[^a-z0-9_]+/g, '_').replace(/^_+|_+$/g, '');
    }

    function getScenesList() {
        if (Array.isArray(window.currentPlan?.scenes) && window.currentPlan.scenes.length) return window.currentPlan.scenes;
        return [
            { narration: 'Bu kuralı öğrenene kadar hayatınız kontrolünüzde değildi...', duration: 4.0, mood: 'epic', highlight_word: 'KURALI' },
            { narration: 'Beynimiz belirsizlik anında en tanıdık tuzağa düşer.', duration: 4.5, mood: 'mysterious', highlight_word: 'BELİRSİZLİK' },
            { narration: 'İlk üç saniyede dikkati kilitleyen gizli mekanizma budur.', duration: 4.5, mood: 'dramatic', highlight_word: 'DİKKATİ' },
            { narration: 'Ve tam da bu yüzden asla unutmayın çünkü döngü burada başlar.', duration: 4.0, mood: 'epic', highlight_word: 'UNUTMAYIN' }
        ];
    }

    function hasLoadedActualVideo() {
        const src = (document.getElementById('live-preview-player')?.getAttribute('src') || '').trim();
        return Boolean(src && src !== '#' && !src.endsWith('/#'));
    }

    function syncSpinningDiscState() {
        const screen = document.getElementById('live-phone-screen');
        const player = document.getElementById('live-preview-player');
        const active = Boolean(player && !player.paused && !player.ended && !player.classList.contains('hidden')) || animaticPlaying;
        screen?.classList.toggle('is-playing', active);
        screen?.querySelector('.sound-disc i')?.classList.toggle('fa-spin', active);
    }

    function setPhonePreviewMode(mode) {
        const hasVideo = hasLoadedActualVideo();
        const player = document.getElementById('live-preview-player');
        const placeholder = document.getElementById('mockup-placeholder');
        const screen = document.getElementById('live-phone-screen');
        if (!screen) return;
        const effectiveMode = (mode === 'video' && hasVideo) ? 'video' : (mode === 'draft' ? 'draft' : (hasVideo ? 'video' : 'draft'));
        previewViewMode = effectiveMode;
        screen.classList.toggle('has-actual-video', hasVideo);
        screen.classList.toggle('is-video-mode', effectiveMode === 'video');
        screen.classList.toggle('is-draft-mode', effectiveMode === 'draft');

        if (player && placeholder) {
            if (effectiveMode === 'video' && hasVideo) {
                player.classList.remove('hidden');
                placeholder.classList.add('hidden');
                // Render edilmiş MP4 zaten gömülü altyazı/başlık içerdiği için sahte katmanları varsayılan olarak kapat
                if (!screen.dataset.userToggledClean) {
                    screen.classList.add('is-clean-preview');
                    const toggleBtn = document.getElementById('btn-toggle-shorts-ui-overlay');
                    if (toggleBtn) {
                        toggleBtn.classList.add('is-clean');
                        toggleBtn.innerHTML = '<i class="fa-solid fa-eye-slash"></i> <span>Shorts UI: Kapalı</span>';
                    }
                }
            } else {
                if (player && !player.paused) player.pause();
                player.classList.add('hidden');
                placeholder.classList.remove('hidden');
                if (!screen.dataset.userToggledClean) {
                    screen.classList.remove('is-clean-preview');
                    const toggleBtn = document.getElementById('btn-toggle-shorts-ui-overlay');
                    if (toggleBtn) {
                        toggleBtn.classList.remove('is-clean');
                        toggleBtn.innerHTML = '<i class="fa-brands fa-youtube"></i> <span>Shorts UI: Açık</span>';
                    }
                }
            }
        }

        const modeSwitch = document.getElementById('wiz-phone-mode-switch');
        if (modeSwitch) {
            modeSwitch.classList.toggle('has-video', hasVideo);
            modeSwitch.querySelectorAll('.wiz-pms-btn').forEach(btn => {
                const m = btn.getAttribute('data-pmode');
                btn.classList.toggle('active', m === effectiveMode);
                if (m === 'video') {
                    btn.disabled = !hasVideo;
                    btn.title = hasVideo ? 'Üretilen MP4 videoyu göster' : 'Henüz üretilmiş MP4 video yok';
                }
            });
        }

        syncSpinningDiscState();
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
            <div class="wiz-phone-mode-switch" id="wiz-phone-mode-switch" role="group" aria-label="Önizleme Modu">
                <button type="button" class="wiz-pms-btn" data-pmode="video" title="Üretilen MP4 Videoyu Göster">
                    <i class="fa-solid fa-film"></i> Video
                </button>
                <button type="button" class="wiz-pms-btn active" data-pmode="draft" title="Sahne & Altyazı Taslağını Göster">
                    <i class="fa-solid fa-sliders"></i> Taslak
                </button>
            </div>
            <select id="select-phone-device-frame" class="wiz-phone-device-select" title="Cihaz Çerçevesi Değiştir (Madde 55)">
                <option value="device-iphone">📱 iPhone 16 Pro</option>
                <option value="device-android">📲 Android Dar</option>
                <option value="device-frameless">🖼️ Çerçevesiz 9:16</option>
            </select>
            <button type="button" class="wiz-phone-ctrl-btn" id="btn-phone-safe-zone" title="YouTube Shorts Güvenli Alan Izgarasını Aç/Kapat (Madde 52)">
                <i class="fa-solid fa-border-all"></i> <span>Güvenli Alan</span>
            </button>
            <button type="button" class="wiz-phone-ctrl-btn" id="btn-phone-watermark-cycle" title="Filigran / Logo Konumu Değiştir (Madde 60)">
                <i class="fa-solid fa-stamp"></i> <span id="lbl-phone-wm-pos">Logo: Sağ Üst</span>
            </button>
            <button type="button" class="wiz-phone-ctrl-btn is-icon-only" id="btn-phone-fullscreen" title="Büyük Önizleme Modu (Madde 59)">
                <i class="fa-solid fa-expand"></i>
            </button>
        `;
        header.after(bar);

        bar.querySelectorAll('.wiz-pms-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const targetMode = btn.getAttribute('data-pmode') || 'draft';
                if (targetMode === 'video' && !hasLoadedActualVideo()) return;
                setPhonePreviewMode(targetMode);
            });
        });

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

        // Bind video play/pause listeners once & enforce no-autoplay
        const player = document.getElementById('live-preview-player');
        if (player && !player.dataset.previewBound) {
            player.dataset.previewBound = '1';
            player.autoplay = false;
            player.removeAttribute('autoplay');
            player.addEventListener('play', syncSpinningDiscState);
            player.addEventListener('pause', syncSpinningDiscState);
            player.addEventListener('ended', syncSpinningDiscState);

            const attrObs = new MutationObserver(() => {
                const currentSrc = (player.getAttribute('src') || '').trim();
                if (currentSrc && currentSrc !== lastKnownVideoSrc) {
                    lastKnownVideoSrc = currentSrc;
                    setPhonePreviewMode('video');
                    syncPhoneLiveMetaAndLut();
                } else if (!currentSrc && lastKnownVideoSrc) {
                    lastKnownVideoSrc = '';
                    setPhonePreviewMode('draft');
                }
            });
            attrObs.observe(player, { attributes: true, attributeFilter: ['src', 'class'] });
        }

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
                    <span class="phone-yt-avatar" id="phone-yt-avatar">S</span>
                    <strong id="phone-yt-handle">@shorts_studio</strong>
                    <span class="phone-yt-sub-pill">Abone Ol</span>
                </div>
                <div class="phone-yt-title-line" id="phone-yt-title-line">
                    9:16 Dikey Shorts Kurgu Önizlemesi #shorts #viral
                </div>
            `;
            screen.appendChild(meta);
        }

        // 54. Make #mockup-sub-overlay draggable vertically (Üst / Orta / Alt)
        const subOverlay = document.getElementById('mockup-sub-overlay');
        if (subOverlay && !subOverlay.dataset.dragBound) {
            subOverlay.dataset.dragBound = '1';
            subOverlay.classList.add('sub-pos-middle');
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
                <div class="wiz-sub-pos-group">
                    <button type="button" class="wiz-sub-pos-btn" data-pos="top">Üst</button>
                    <button type="button" class="wiz-sub-pos-btn active" data-pos="middle">Orta</button>
                    <button type="button" class="wiz-sub-pos-btn" data-pos="bottom">Alt</button>
                </div>
            </div>
        `;
        phoneFrame.after(panel);

        document.getElementById('btn-pss-prev')?.addEventListener('click', () => {
            const scenes = getScenesList();
            activePreviewSceneIdx = (activePreviewSceneIdx - 1 + scenes.length) % scenes.length;
            setPhonePreviewMode('draft');
            renderPhoneSceneAt(activePreviewSceneIdx);
        });
        document.getElementById('btn-pss-next')?.addEventListener('click', () => {
            const scenes = getScenesList();
            activePreviewSceneIdx = (activePreviewSceneIdx + 1) % scenes.length;
            setPhonePreviewMode('draft');
            renderPhoneSceneAt(activePreviewSceneIdx);
        });
        document.getElementById('btn-phone-animatic-play')?.addEventListener('click', toggleAnimaticPreview);

        panel.querySelectorAll('.wiz-sub-pos-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                setPhonePreviewMode('draft');
                setSubtitleYPosition(btn.getAttribute('data-pos') || 'middle');
            });
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
        if (statusText) {
            const desc = sc.scene_description || sc.narration || '';
            statusText.textContent = desc
                ? `Sahne ${safeIdx + 1}: ${String(desc).slice(0, 72)}`
                : 'Render tamamlandığında videonuz burada hazır bekler.';
        }

        // Sync Hook & Loop Bridge Card with real scene narrations when available
        const hookSpan = document.getElementById('preview-hook-text');
        const loopSpan = document.getElementById('preview-loop-text');
        if (hookSpan && scenes[0]?.narration) {
            hookSpan.textContent = `"${String(scenes[0].narration).replace(/\*\*[A-Z]+\*\*/g, '').trim().slice(0, 95)}"`;
        }
        if (loopSpan && scenes[scenes.length - 1]?.narration) {
            loopSpan.textContent = `"${String(scenes[scenes.length - 1].narration).replace(/\*\*[A-Z]+\*\*/g, '').trim().slice(0, 95)}"`;
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
        setPhonePreviewMode('draft');
        animaticPlaying = true;
        syncSpinningDiscState();
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
        syncSpinningDiscState();
    }

    // ── 56 & 58: Sync YouTube Metadata & LUT CSS Filter ──────────────────────
    function syncPhoneLiveMetaAndLut() {
        const seoTitle = document.getElementById('seo-title-val')?.value?.trim();
        const inputTopic = document.getElementById('input-topic')?.value?.trim();
        const planTitle = window.currentPlan?.title || window.currentPlan?.topic;
        const latestVideoTitle = window.__latestRenderedVideo?.title || window.__latestRenderedVideo?.topic;
        const topic = seoTitle || inputTopic || planTitle || latestVideoTitle || '9:16 Dikey Shorts Stüdyo Önizlemesi';

        const chSelect = document.getElementById('select-upload-channel') || document.getElementById('pub-target-channel-select');
        const rawChName = (chSelect?.selectedOptions?.[0]?.textContent || '').trim();
        const isDefaultChannel = !rawChName || /varsay[ıi]lan|kanal se[çc]/i.test(rawChName);
        const slug = isDefaultChannel ? 'shorts_studio' : (normalizeTrSlug(rawChName).slice(0, 18) || 'shorts_studio');
        const cleanHandle = '@' + slug;

        const handleEl = document.getElementById('phone-yt-handle');
        const avatarEl = document.getElementById('phone-yt-avatar');
        const wmText = document.getElementById('phone-wm-text');
        const titleEl = document.getElementById('phone-yt-title-line');
        if (handleEl) handleEl.textContent = cleanHandle;
        if (avatarEl) avatarEl.textContent = (slug[0] || 'S').toUpperCase();
        if (wmText) wmText.textContent = cleanHandle;
        if (titleEl) {
            const cleanTopic = topic.replace(/#shorts/gi, '').replace(/#viral/gi, '').trim();
            titleEl.textContent = `${cleanTopic.slice(0, 62)} #shorts #viral`;
        }

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
        setPhonePreviewMode(previewViewMode === 'auto' ? (hasLoadedActualVideo() ? 'video' : 'draft') : previewViewMode);
    }

    function initStudioPhonePreviewUX() {
        syncPhonePreviewAll();
        document.getElementById('input-topic')?.addEventListener('input', syncPhoneLiveMetaAndLut);
        (document.getElementById('select-color-lut') || document.getElementById('tl-select-style-profile') || document.getElementById('tl-select-helios-style'))?.addEventListener('change', syncPhoneLiveMetaAndLut);
        (document.getElementById('select-upload-channel') || document.getElementById('pub-target-channel-select'))?.addEventListener('change', syncPhoneLiveMetaAndLut);
    }

    window.syncPhonePreviewAll = syncPhonePreviewAll;
    window.renderPhoneSceneAt = renderPhoneSceneAt;
    window.setPhonePreviewMode = setPhonePreviewMode;

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initStudioPhonePreviewUX);
    } else {
        initStudioPhonePreviewUX();
    }
})();
