/**
 * ShortsAI Studio — Category J: Görsel Hiyerarşi, Erişilebilirlik & Mikro Etkileşimler (Items 91-100)
 * 91: Komut Paleti (⌘K / Ctrl+K) | 92: İskelet Yükleyiciler (Shimmer Skeletons) | 93: Aksiyonlu Bildirimler (Toasts)
 * 94: Sabit (Sticky) Telefon Önizlemesi | 95: Yüksek Kontrastlı Odak Halkaları (:focus-visible)
 * 96: Tutarlı 4-Renk Semantik Rozet Dili | 97: Kısaltılmış Metinlerde Tam Başlık İpucu (Tooltip)
 * 98: Mobil/Dar Ekran Alt Çekmece Önizlemesi | 99: Boş Durumlarda Tek Tıkla Başlatıcı | 100: Yoğunluk Modu (Kompakt/Standart)
 */
(function () {
    'use strict';

    const esc = (s) => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    const notify = (msg, type = 'info') => { if (typeof window.showToast === 'function') window.showToast(msg, type); };

    const CMD_ITEMS = [
        { id: 'wiz-1', icon: '💡', title: 'Adım 01: Fikir, Konu & Niş Seçimi', cat: 'Sihirbaz', run: () => goWizard(1) },
        { id: 'wiz-2', icon: '🎙️', title: 'Adım 02: Senaryo & Seslendirme (TTS)', cat: 'Sihirbaz', run: () => goWizard(2) },
        { id: 'wiz-3', icon: '🎨', title: 'Adım 03: Görsel Motorlar, BGM & Efektler', cat: 'Sihirbaz', run: () => goWizard(3) },
        { id: 'wiz-4', icon: '🛡️', title: 'Adım 04: Kalite Kalkanı & Render Başlat', cat: 'Sihirbaz', run: () => goWizard(4) },
        { id: 'tab-timeline', icon: '🎬', title: 'Sahne & Zaman Çizelgesi Editörü (PJ)', cat: 'Sekme', run: () => window.switchTab?.('timeline') },
        { id: 'tab-clipper', icon: '✂️', title: 'Uzun Videodan Shorts Kesici (Clipper)', cat: 'Sekme', run: () => window.switchTab?.('clipper') },
        { id: 'tab-gallery', icon: '🎞️', title: 'Video Galerisi & Üretim Arşivi', cat: 'Sekme', run: () => window.switchTab?.('gallery') },
        { id: 'tab-channels', icon: '📺', title: 'Kanal Yönetimi & 7 Günlük Yayın Takvimi', cat: 'Sekme', run: () => window.switchTab?.('channels') },
        { id: 'tab-audio', icon: '🎵', title: 'Medya, BGM & Ses Efektleri Konsolu', cat: 'Sekme', run: () => window.switchTab?.('audio') },
        { id: 'tab-subtitles', icon: '💬', title: 'CapCut Karaoke Altyazı Stilleri', cat: 'Sekme', run: () => window.switchTab?.('subtitles') },
        { id: 'tab-settings', icon: '⚙️', title: 'Sistem, Donanım & API Ayarları', cat: 'Sekme', run: () => window.switchTab?.('settings') },
        { id: 'niche-stoic', icon: '🏛️', title: 'Niş Seç: Stoic Felsefe & Disiplin', cat: 'Niş', run: () => selectNicheCmd('6_stoic_philosophy', 'Stoic Felsefe') },
        { id: 'niche-history', icon: '🏺', title: 'Niş Seç: Gizli Tarih & Arkeoloji', cat: 'Niş', run: () => selectNicheCmd('2_hidden_history', 'Gizli Tarih') },
        { id: 'niche-psych', icon: '🧠', title: 'Niş Seç: Karanlık Psikoloji & İkna', cat: 'Niş', run: () => selectNicheCmd('5_dark_psychology', 'Psikoloji') },
        { id: 'voice-ahmet', icon: '🗣️', title: 'Ses Seç: Ahmet (Derin Belgesel - TR)', cat: 'Ses', run: () => selectVoiceCmd('tr-TR-AhmetNeural') },
        { id: 'voice-emel', icon: '🗣️', title: 'Ses Seç: Emel (Akıcı Anlatıcı - TR)', cat: 'Ses', run: () => selectVoiceCmd('tr-TR-EmelNeural') },
        { id: 'act-density', icon: '📐', title: 'Görünüm Yoğunluğunu Değiştir (Kompakt / Standart)', cat: 'Aksiyon', run: () => toggleDensityMode() },
        { id: 'act-quickstart', icon: '✨', title: '60 Saniyede Hızlı Viral Video Başlat', cat: 'Aksiyon', run: () => triggerQuickStartVideo() }
    ];

    function goWizard(step) {
        if (typeof window.switchTab === 'function') window.switchTab('studio');
        if (typeof window.setStudioWizardStep === 'function') window.setStudioWizardStep(step, { force: true });
    }

    function selectNicheCmd(val, label) {
        goWizard(1);
        const sel = document.getElementById('select-niche');
        if (sel) { sel.value = val; sel.dispatchEvent(new Event('change', { bubbles: true })); }
        notify(`🏷️ "${label}" nişi seçildi.`);
    }

    function selectVoiceCmd(voiceId) {
        goWizard(2);
        const sel = document.getElementById('select-tts-voice');
        if (sel) { sel.value = voiceId; sel.dispatchEvent(new Event('change', { bubbles: true })); }
        notify(`🎙️ Seslendirmen değiştirildi: ${voiceId}`);
    }

    // ─── 91. Komut Paleti (⌘K / Ctrl+K) & 100. Yoğunluk Modu ───────────────
    function initHeaderMicroControls() {
        const header = document.querySelector('.top-header');
        if (!header || document.getElementById('btn-open-cmd-palette')) return;
        const target = header.querySelector('.header-right, .top-actions') || header;

        const cmdBtn = document.createElement('button');
        cmdBtn.type = 'button';
        cmdBtn.id = 'btn-open-cmd-palette';
        cmdBtn.className = 'top-btn ux-cmd-trigger-btn';
        cmdBtn.title = 'Hızlı Komut Paletini Aç (⌘K veya Ctrl+K)';
        cmdBtn.innerHTML = `<i class="fa-solid fa-magnifying-glass"></i> <span>Komut Ara</span> <kbd>⌘K</kbd>`;
        cmdBtn.addEventListener('click', openCommandPalette);

        const densityBtn = document.createElement('button');
        densityBtn.type = 'button';
        densityBtn.id = 'btn-density-toggle';
        densityBtn.className = 'top-btn ux-density-btn';
        densityBtn.title = 'Madde 100: Kompakt / Standart yoğunluk görünümü';
        const savedCompact = localStorage.getItem('shorts_ui_density') === 'compact';
        if (savedCompact) document.body.classList.add('density-compact');
        updateDensityButtonLabel(densityBtn);
        densityBtn.addEventListener('click', toggleDensityMode);

        target.insertBefore(densityBtn, target.firstChild);
        target.insertBefore(cmdBtn, target.firstChild);
    }

    function updateDensityButtonLabel(btn) {
        const el = btn || document.getElementById('btn-density-toggle');
        if (!el) return;
        const isCompact = document.body.classList.contains('density-compact');
        el.innerHTML = `<i class="fa-solid ${isCompact ? 'fa-compress' : 'fa-expand'}"></i> <span>${isCompact ? 'Kompakt' : 'Standart'}</span>`;
        el.setAttribute('aria-pressed', isCompact ? 'true' : 'false');
    }

    function toggleDensityMode() {
        const isCompact = document.body.classList.toggle('density-compact');
        try { localStorage.setItem('shorts_ui_density', isCompact ? 'compact' : 'standard'); } catch (_) {}
        updateDensityButtonLabel();
        notify(`📐 Görünüm modu: ${isCompact ? 'Kompakt (Yüksek Yoğunluk)' : 'Standart (Ferah)'}`);
    }

    let _cmdActiveIndex = 0;
    let _cmdFiltered = CMD_ITEMS.slice();

    function ensureCommandPaletteModal() {
        let modal = document.getElementById('cmd-palette-modal');
        if (modal) return modal;
        modal = document.createElement('div');
        modal.id = 'cmd-palette-modal';
        modal.className = 'cmd-palette-overlay';
        modal.setAttribute('role', 'dialog');
        modal.setAttribute('aria-modal', 'true');
        modal.setAttribute('aria-label', 'Hızlı Komut Paleti');
        modal.innerHTML = `
            <div class="cmd-palette-card glass-box">
                <div class="cmd-palette-search-bar">
                    <i class="fa-solid fa-terminal text-primary"></i>
                    <input type="text" id="cmd-palette-input" placeholder="Sekme, niş, seslendirmen veya hızlı aksiyon ara... (Örn: Stoic, Ahmet, Clipper)" autocomplete="off">
                    <kbd class="cmd-esc-hint">ESC</kbd>
                </div>
                <div class="cmd-palette-results" id="cmd-palette-results" role="listbox"></div>
                <div class="cmd-palette-footer">
                    <span><kbd>↑↓</kbd> Gezin</span>
                    <span><kbd>↵ Enter</kbd> Çalıştır</span>
                    <span><kbd>⌘K</kbd> Kapat</span>
                </div>
            </div>`;
        document.body.appendChild(modal);

        const input = modal.querySelector('#cmd-palette-input');
        input?.addEventListener('input', () => {
            _cmdActiveIndex = 0;
            renderCommandList(input.value);
        });
        input?.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                _cmdActiveIndex = (_cmdActiveIndex + 1) % Math.max(1, _cmdFiltered.length);
                renderCommandList(input.value);
            } else if (e.key === 'ArrowUp') {
                e.preventDefault();
                _cmdActiveIndex = (_cmdActiveIndex - 1 + Math.max(1, _cmdFiltered.length)) % Math.max(1, _cmdFiltered.length);
                renderCommandList(input.value);
            } else if (e.key === 'Enter') {
                e.preventDefault();
                const chosen = _cmdFiltered[_cmdActiveIndex];
                if (chosen) executeCommandItem(chosen);
            } else if (e.key === 'Escape') {
                closeCommandPalette();
            }
        });
        modal.addEventListener('click', (e) => { if (e.target === modal) closeCommandPalette(); });
        return modal;
    }

    function renderCommandList(query = '') {
        const listEl = document.getElementById('cmd-palette-results');
        if (!listEl) return;
        const q = query.trim().toLowerCase();
        _cmdFiltered = CMD_ITEMS.filter((item) => !q || item.title.toLowerCase().includes(q) || item.cat.toLowerCase().includes(q));
        if (_cmdFiltered.length === 0) {
            listEl.innerHTML = `<div class="cmd-empty">Eşleşen komut bulunamadı: "${esc(query)}"</div>`;
            return;
        }
        listEl.innerHTML = _cmdFiltered.map((item, idx) => `
            <button type="button" class="cmd-result-item ${idx === _cmdActiveIndex ? 'is-active' : ''}" data-cmd-idx="${idx}" role="option" aria-selected="${idx === _cmdActiveIndex}">
                <span class="cmd-item-icon">${item.icon}</span>
                <span class="cmd-item-title">${esc(item.title)}</span>
                <span class="cmd-item-cat">${esc(item.cat)}</span>
            </button>`).join('');
        listEl.querySelectorAll('.cmd-result-item').forEach((btn) => {
            btn.addEventListener('click', () => {
                const idx = Number(btn.getAttribute('data-cmd-idx') || 0);
                if (_cmdFiltered[idx]) executeCommandItem(_cmdFiltered[idx]);
            });
        });
    }

    function executeCommandItem(item) {
        closeCommandPalette();
        item.run();
    }

    function openCommandPalette() {
        const modal = ensureCommandPaletteModal();
        modal.style.display = 'flex';
        _cmdActiveIndex = 0;
        renderCommandList('');
        const input = document.getElementById('cmd-palette-input');
        if (input) { input.value = ''; setTimeout(() => input.focus(), 20); }
    }

    function closeCommandPalette() {
        const modal = document.getElementById('cmd-palette-modal');
        if (modal) modal.style.display = 'none';
    }

    document.addEventListener('keydown', (e) => {
        if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
            e.preventDefault();
            const modal = document.getElementById('cmd-palette-modal');
            if (modal && modal.style.display === 'flex') closeCommandPalette();
            else openCommandPalette();
        }
    });

    // ─── 92. İskelet Yükleyiciler & 99. Boş Durum (Empty State) Başlatıcı ──
    function triggerQuickStartVideo() {
        goWizard(1);
        const topicEl = document.getElementById('input-topic');
        if (topicEl) {
            topicEl.value = 'Marcus Aurelius: Zihnini Kontrol Etmenin 3 Stoacı Kuralı';
            topicEl.dispatchEvent(new Event('input', { bubbles: true }));
        }
        notify('✨ Örnek viral konu yüklendi! Şimdi "Senaryoyu Oluştur" ile 60 saniyede üretimi başlatın.');
    }

    window.renderShimmerSkeleton = function (rows = 3) {
        return `<div class="ux-shimmer-stack" aria-busy="true">${Array.from({ length: rows }).map((_, i) => `<div class="shimmer-skeleton" style="width:${92 - i * 12}%"></div>`).join('')}</div>`;
    };

    function enhanceEmptyStatesAndSkeletons() {
        document.querySelectorAll('.empty-state-box').forEach((box) => {
            if (box.dataset.catJEnhanced === '1') return;
            box.dataset.catJEnhanced = '1';
            const hasSpinner = Boolean(box.querySelector('.fa-spin, .fa-spinner'));
            if (hasSpinner) {
                const skel = document.createElement('div');
                skel.className = 'ux-shimmer-wrap';
                skel.innerHTML = window.renderShimmerSkeleton(2);
                box.appendChild(skel);
            } else if (!box.querySelector('.btn-empty-state-quickstart')) {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'btn btn-secondary btn-sm btn-empty-state-quickstart mt-2';
                btn.innerHTML = `<i class="fa-solid fa-wand-magic-sparkles"></i> İlk Videonu 60 Saniyede Oluştur`;
                btn.addEventListener('click', triggerQuickStartVideo);
                box.appendChild(btn);
            }
        });
    }

    // ─── 93. Aksiyonlu Bildirimler (Actionable Toasts) ─────────────────────
    function inferToastAction(text) {
        const lower = (text || '').toLowerCase();
        if (lower.includes('senaryo') || lower.includes('sahne') || lower.includes('timeline')) {
            return { label: 'Sahne Editörünü Aç', fn: () => window.switchTab?.('timeline') };
        }
        if (lower.includes('galeri') || lower.includes('arşiv') || lower.includes('video')) {
            return { label: 'Galeriyi Aç', fn: () => window.switchTab?.('gallery') };
        }
        if (lower.includes('kanal') || lower.includes('takvim') || lower.includes('yayın')) {
            return { label: 'Takvimi Gör', fn: () => window.switchTab?.('channels') };
        }
        return { label: 'Stüdyo', fn: () => window.switchTab?.('studio') };
    }

    function initActionableToastObserver() {
        const container = document.getElementById('toast-container');
        if (!container || container.dataset.catJToastObserved === '1') return;
        container.dataset.catJToastObserved = '1';

        const observer = new MutationObserver((mutations) => {
            mutations.forEach((m) => {
                m.addedNodes.forEach((node) => {
                    if (node.nodeType === 1 && node.classList.contains('toast') && !node.querySelector('.toast-action-btn')) {
                        const act = inferToastAction(node.textContent || '');
                        const btn = document.createElement('button');
                        btn.type = 'button';
                        btn.className = 'toast-action-btn';
                        btn.textContent = act.label;
                        btn.addEventListener('click', () => {
                            act.fn();
                            node.remove();
                        });
                        node.appendChild(btn);
                    }
                });
            });
        });
        observer.observe(container, { childList: true });
    }

    // ─── 94. Sticky 9:16 Önizleme & 98. Mobil/Dar Ekran Alt Çekmece ────────
    function initStickyPreviewAndMobileDrawer() {
        const stageRail = document.querySelector('.stage-rail, .preview-mockup-card');
        if (stageRail) stageRail.classList.add('is-sticky-stage-rail');

        if (!document.getElementById('mobile-preview-drawer-fab')) {
            const fab = document.createElement('button');
            fab.type = 'button';
            fab.id = 'mobile-preview-drawer-fab';
            fab.className = 'mobile-preview-drawer-fab';
            fab.innerHTML = `<i class="fa-solid fa-mobile-screen-button"></i> <span>9:16 Önizlemeyi Gör</span>`;
            fab.addEventListener('click', () => {
                const open = document.body.classList.toggle('mobile-preview-drawer-open');
                fab.querySelector('span').textContent = open ? 'Önizlemeyi Kapat' : '9:16 Önizlemeyi Gör';
            });
            document.body.appendChild(fab);
            // 1080px üstü geniş ekranda FAB'ı CSS cascade'den bağımsız gizle
            // (bazı masaüstü görünümlerde display:none kuralı ezilebiliyordu)
            const fabMq = window.matchMedia('(max-width: 1080px)');
            const syncFabVisibility = () => {
                fab.style.setProperty('display', fabMq.matches ? 'inline-flex' : 'none', 'important');
            };
            if (fabMq.addEventListener) fabMq.addEventListener('change', syncFabVisibility);
            else if (fabMq.addListener) fabMq.addListener(syncFabVisibility);
            syncFabVisibility();
        }
    }

    // ─── 96. Tutarlı 4-Renk Semantik Rozet Standardı ───────────────────────
    function normalizeSemanticBadges() {
        document.querySelectorAll('.badge, .pro-chip, .nav-badge, .compliance-chip').forEach((el) => {
            const t = (el.textContent || '').toLowerCase();
            if (t.includes('geçti') || t.includes('aktif') || t.includes('hazır') || t.includes('0 tl') || t.includes('canlı')) {
                el.classList.add('sem-badge-ready');
            } else if (t.includes('uyarı') || t.includes('planlandı') || t.includes('dinlendirme')) {
                el.classList.add('sem-badge-warn');
            } else if (t.includes('hata') || t.includes('risk') || t.includes('kaldı')) {
                el.classList.add('sem-badge-danger');
            }
        });
    }

    // ─── 97. Kısaltılmış Metinlerde Tam Başlık İpucu (Floating Tooltip) ────
    function initTruncatedTextTooltips() {
        let tip = document.getElementById('ux-floating-tooltip');
        if (!tip) {
            tip = document.createElement('div');
            tip.id = 'ux-floating-tooltip';
            tip.className = 'ux-floating-tooltip';
            tip.setAttribute('role', 'tooltip');
            document.body.appendChild(tip);
        }

        document.addEventListener('mouseover', (e) => {
            const target = e.target.closest?.('.shorts-title-text, .cal-slot-title, .gal-ab-chip span, .topic-card-title, [title]');
            if (!target) {
                tip.style.display = 'none';
                return;
            }
            const isTruncated = target.scrollWidth > target.clientWidth + 2 || target.classList.contains('shorts-title-text');
            const fullText = target.getAttribute('title') || target.textContent?.trim() || '';
            if (!isTruncated || fullText.length < 22) {
                tip.style.display = 'none';
                return;
            }
            tip.textContent = fullText;
            tip.style.display = 'block';
            const rect = target.getBoundingClientRect();
            tip.style.top = `${Math.max(8, rect.top - 36)}px`;
            tip.style.left = `${Math.min(window.innerWidth - 320, Math.max(8, rect.left))}px`;
        });

        document.addEventListener('mouseout', (e) => {
            if (e.target.closest?.('.shorts-title-text, .cal-slot-title, .gal-ab-chip span, [title]')) {
                tip.style.display = 'none';
            }
        });
    }

    function initCategoryJ() {
        initHeaderMicroControls();
        ensureCommandPaletteModal();
        enhanceEmptyStatesAndSkeletons();
        initActionableToastObserver();
        initStickyPreviewAndMobileDrawer();
        normalizeSemanticBadges();
        initTruncatedTextTooltips();
        setTimeout(() => {
            enhanceEmptyStatesAndSkeletons();
            normalizeSemanticBadges();
        }, 450);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initCategoryJ);
    } else {
        initCategoryJ();
    }
})();
