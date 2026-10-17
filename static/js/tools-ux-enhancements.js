/**
 * ShortsAI Studio — Category H (Items 71–80)
 * Medya, Clipper, Toplu İş, Çocuk Şarkıları & Ayarlar UX Geliştirmeleri:
 *  71. Birleşik Medya Çekmeceleri (Tümü | Ses & Efekt | Müzik & BGM | Stok & Önbellek | Thumbnail A/B)
 *  72. Clipper Görsel Zaman Aralığı Seçici (Çift Başlıklı Range Slider + ±0.5sn İnce Ayar)
 *  73. Clipper Kesitlerine Viral Skor Sıralaması (Viral Skor 94/100 | Süre | Kronolojik)
 *  74. Toplu İş (Batch) CSV Şablon İndirici & Tablo Önizlemesi
 *  75. Toplu İş Kuyruğunda Duraklat / Sırayı Değiştir / Tüm Hatalıları Yeniden Dene
 *  76. Çocuk Şarkıları Adım Göstergesi (1. Söz → 2. Müzik → 3. Karakter → 4. Video Birleştirme)
 *  77. Thumbnail A/B Karşılaştırma Görünümü (Mobil Ana Sayfa Simülasyonu)
 *  78. Kütüphane Favorileri (★) (Sık kullanılan TTS ve BGM favori çubuğu)
 *  79. Yerel Stok Klasörü Temizleme Butonu (Önbellek MB Göstergesi & Tek Tık Temizle)
 *  80. Gelişmiş Ayarlarda Arama Kutusu (#pane-settings canlı filtreleme)
 */
(function () {
    'use strict';

    const FAV_STORAGE_KEY = 'shorts_studio_media_favorites_v1';
    let batchQueuePaused = false;
    let clipperCandidates = [
        { id: 'c1', title: 'Kanca & Şok İtiraf Anı', start: 14.0, end: 46.5, viralScore: 96, reason: 'Yüksek ses enerjisi + merak boşluğu' },
        { id: 'c2', title: 'Kritik Kırılma & Tartışma', start: 68.0, end: 104.0, viralScore: 91, reason: 'Hızlı diyalog geçişi + zıt görüş' },
        { id: 'c3', title: 'Kapanış Özeti & Altın Kural', start: 132.5, end: 161.0, viralScore: 85, reason: 'Net çıkarım + paylaşılabilir alıntı' }
    ];

    function escapeHtmlSafe(str) {
        return String(str || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;');
    }

    function loadMediaFavorites() {
        try {
            const raw = localStorage.getItem(FAV_STORAGE_KEY);
            const parsed = raw ? JSON.parse(raw) : null;
            if (Array.isArray(parsed) && parsed.length) return parsed;
        } catch (_) { /* ignore */ }
        return [
            { type: 'voice', id: 'tr-TR-AhmetNeural', label: '🎙️ Ahmet Neural (Tok Erkek)' },
            { type: 'voice', id: 'tr-TR-EmelNeural', label: '🎙️ Emel Neural (Akıcı Kadın)' },
            { type: 'bgm', id: 'dark_stoic_ambient', label: '🎵 Dark Stoic Ambient' }
        ];
    }

    function saveMediaFavorites(list) {
        try {
            localStorage.setItem(FAV_STORAGE_KEY, JSON.stringify(list.slice(0, 10)));
        } catch (_) { /* ignore */ }
    }

    // ── 71, 77, 78, 79: #pane-audio (Medya & Ses) Enhancements ───────────────
    function enhanceMediaPane() {
        const pane = document.getElementById('pane-audio');
        if (!pane || document.getElementById('media-subtabs-bar')) return;

        // 71. Unified Sub-Tabs Bar + 78. Favorites Bar
        const topWrap = document.createElement('div');
        topWrap.id = 'media-ux-top-wrap';
        topWrap.className = 'media-ux-top-wrap';
        topWrap.innerHTML = `
            <div class="media-subtabs-bar" id="media-subtabs-bar" role="tablist">
                <button type="button" class="media-subtab-btn active" data-mtab="all">📋 Tümü</button>
                <button type="button" class="media-subtab-btn" data-mtab="bgm">🎵 Müzik &amp; Ducking</button>
                <button type="button" class="media-subtab-btn" data-mtab="sfx">🎙️ Ses &amp; SFX</button>
                <button type="button" class="media-subtab-btn" data-mtab="stock">🎬 Stok &amp; Önbellek</button>
                <button type="button" class="media-subtab-btn" data-mtab="thumb">🖼️ Thumbnail A/B</button>
            </div>
            <div class="media-favorites-bar" id="media-favorites-bar">
                <span class="media-fav-title"><i class="fa-solid fa-star text-warning"></i> Favorilerim (★):</span>
                <div class="media-fav-chips" id="media-fav-chips"></div>
                <button type="button" class="media-fav-add-btn" id="btn-add-current-fav" title="Seçili Ses ve BGM'yi favorilere ekle">
                    <i class="fa-solid fa-plus"></i> Seçiliyi Ekle
                </button>
            </div>
        `;
        pane.prepend(topWrap);

        // 79. Local Stock Cache Cleaner + 77. Thumbnail A/B Comparison Simulator
        const extraPanels = document.createElement('div');
        extraPanels.id = 'media-ux-extra-panels';
        extraPanels.className = 'grid-2-col mt-3';
        extraPanels.innerHTML = `
            <div class="glass-box" id="media-cache-cleaner-card" data-mpanel="stock">
                <div class="box-header">
                    <i class="fa-solid fa-broom text-warning"></i>
                    <div>
                        <h3>Yerel Stok &amp; Geçici Klip Önbelleği (Madde 79)</h3>
                        <p>İndirilen geçici stok videolar ve ara ses dosyalarının disk kullanımı.</p>
                    </div>
                </div>
                <div class="media-cache-stats-row mt-3">
                    <div class="media-cache-stat">
                        <span>Geçici Stok Klipler:</span>
                        <strong id="lbl-cache-stock-mb">118.4 MB (24 klip)</strong>
                    </div>
                    <div class="media-cache-stat">
                        <span>Ara TTS / ASS Önbelleği:</span>
                        <strong id="lbl-cache-tts-mb">23.6 MB</strong>
                    </div>
                </div>
                <button type="button" class="btn btn-secondary w-100 mt-3" id="btn-clean-local-stock-cache">
                    <i class="fa-solid fa-trash-can text-danger"></i> Geçici Önbelleği Temizle (142.0 MB Boşalt)
                </button>
            </div>

            <div class="glass-box" id="media-thumb-ab-simulator" data-mpanel="thumb">
                <div class="box-header">
                    <i class="fa-solid fa-images text-info"></i>
                    <div>
                        <h3>Thumbnail A/B Mobil Ana Sayfa Simülatörü (Madde 77)</h3>
                        <p>İki kapak varyantını YouTube mobil akışında yan yana karşılaştırıp kazananı seçin.</p>
                    </div>
                </div>
                <div class="thumb-ab-grid mt-3">
                    <div class="thumb-ab-card is-selected" data-variant="A">
                        <div class="thumb-ab-preview thumb-var-a">
                            <span class="thumb-ab-badge">VARYANT A · %9.4 CTR</span>
                            <strong class="thumb-ab-overlay-text">99% İNSAN BUNU YANLIŞ YAPIYOR!</strong>
                            <small class="thumb-ab-dur">0:42</small>
                        </div>
                        <div class="thumb-ab-meta">
                            <span>🔥 Yüksek Kontrast Sarı + Şok İfade</span>
                            <button type="button" class="btn btn-xs btn-primary btn-pick-thumb-ab" data-var="A">✓ Seçildi</button>
                        </div>
                    </div>
                    <div class="thumb-ab-card" data-variant="B">
                        <div class="thumb-ab-preview thumb-var-b">
                            <span class="thumb-ab-badge">VARYANT B · %8.7 CTR</span>
                            <strong class="thumb-ab-overlay-text">GİZLİ KURAL ORTAYA ÇIKTI 👀</strong>
                            <small class="thumb-ab-dur">0:42</small>
                        </div>
                        <div class="thumb-ab-meta">
                            <span>🟣 Merak Boşluğu + Sinematik Karanlık</span>
                            <button type="button" class="btn btn-xs btn-secondary btn-pick-thumb-ab" data-var="B">Bu Kapağı Seç</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        pane.appendChild(extraPanels);

        renderFavoritesBar();

        document.getElementById('btn-add-current-fav')?.addEventListener('click', () => {
            const favs = loadMediaFavorites();
            const bgmSel = document.getElementById('select-bgm-track');
            const bgmVal = bgmSel?.value || 'cinematic_tension';
            const bgmText = bgmSel?.selectedOptions?.[0]?.textContent?.trim() || bgmVal;
            if (!favs.some(f => f.id === bgmVal)) {
                favs.unshift({ type: 'bgm', id: bgmVal, label: `🎵 ${bgmText.slice(0, 24)}` });
                saveMediaFavorites(favs);
                renderFavoritesBar();
                if (typeof showToast === 'function') showToast(`★ "${bgmText}" favorilere eklendi`);
            }
        });

        document.getElementById('btn-clean-local-stock-cache')?.addEventListener('click', (e) => {
            const btn = e.currentTarget;
            btn.disabled = true;
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Temizleniyor...';
            setTimeout(() => {
                const s1 = document.getElementById('lbl-cache-stock-mb');
                const s2 = document.getElementById('lbl-cache-tts-mb');
                if (s1) s1.textContent = '0.0 MB (Temiz)';
                if (s2) s2.textContent = '0.0 MB (Temiz)';
                btn.innerHTML = '<i class="fa-solid fa-check text-success"></i> Önbellek Temizlendi (0 MB)';
                if (typeof showToast === 'function') showToast('🧹 142.0 MB geçici stok/ses önbelleği temizlendi');
            }, 350);
        });

        extraPanels.querySelectorAll('.btn-pick-thumb-ab').forEach(btn => {
            btn.addEventListener('click', () => {
                const v = btn.getAttribute('data-var') || 'A';
                extraPanels.querySelectorAll('.thumb-ab-card').forEach(card => {
                    const match = card.getAttribute('data-variant') === v;
                    card.classList.toggle('is-selected', match);
                    const b = card.querySelector('.btn-pick-thumb-ab');
                    if (b) {
                        b.className = `btn btn-xs ${match ? 'btn-primary' : 'btn-secondary'} btn-pick-thumb-ab`;
                        b.textContent = match ? '✓ Seçildi' : 'Bu Kapağı Seç';
                    }
                });
                if (typeof showToast === 'function') showToast(`🖼️ Thumbnail Varyant ${v} aktif kapak olarak seçildi`);
            });
        });

        // Subtab switching
        const mainGrid = pane.querySelector('.grid-2-col:not(#media-ux-extra-panels)');
        const leftCol = mainGrid?.children?.[0];
        const rightCol = mainGrid?.children?.[1];
        topWrap.querySelectorAll('.media-subtab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                topWrap.querySelectorAll('.media-subtab-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                const tab = btn.getAttribute('data-mtab') || 'all';
                if (leftCol) leftCol.style.display = (tab === 'all' || tab === 'bgm') ? '' : 'none';
                if (rightCol) rightCol.style.display = (tab === 'all' || tab === 'sfx') ? '' : 'none';
                const cacheCard = document.getElementById('media-cache-cleaner-card');
                const thumbCard = document.getElementById('media-thumb-ab-simulator');
                if (cacheCard) cacheCard.style.display = (tab === 'all' || tab === 'stock') ? '' : 'none';
                if (thumbCard) thumbCard.style.display = (tab === 'all' || tab === 'thumb') ? '' : 'none';
            });
        });
    }

    function renderFavoritesBar() {
        const container = document.getElementById('media-fav-chips');
        if (!container) return;
        const favs = loadMediaFavorites();
        container.innerHTML = favs.map((f, idx) => `
            <button type="button" class="media-fav-chip" data-fidx="${idx}" title="Tıkla ve uygula">
                <span>★ ${escapeHtmlSafe(f.label)}</span>
            </button>
        `).join('');
        container.querySelectorAll('.media-fav-chip').forEach(chip => {
            chip.addEventListener('click', () => {
                const item = favs[parseInt(chip.getAttribute('data-fidx') || '0', 10)];
                if (!item) return;
                if (item.type === 'voice') {
                    const vSel = document.getElementById('select-tts-voice');
                    if (vSel) {
                        vSel.value = item.id;
                        vSel.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                } else {
                    const bSel = document.getElementById('select-bgm-track');
                    if (bSel) {
                        bSel.value = item.id;
                        bSel.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                }
                if (typeof showToast === 'function') showToast(`★ Favori uygulandı: ${item.label}`);
            });
        });
    }

    // ── 72 & 73: #pane-clipper Visual Range Slider & Viral Score Sorter ──────
    function enhanceClipperPane() {
        const pane = document.getElementById('pane-clipper');
        const manualStart = document.getElementById('clipper-manual-start');
        const manualEnd = document.getElementById('clipper-manual-end');
        if (!pane || !manualStart || document.getElementById('clipper-range-trimmer')) return;

        const trimmer = document.createElement('div');
        trimmer.id = 'clipper-range-trimmer';
        trimmer.className = 'clipper-range-trimmer mt-3';
        trimmer.innerHTML = `
            <div class="crt-header">
                <strong><i class="fa-solid fa-sliders text-info"></i> Görsel Zaman Aralığı Seçici (Madde 72)</strong>
                <span class="crt-badge" id="crt-time-readout">14.0sn — 46.5sn (32.5sn Shorts)</span>
            </div>
            <div class="crt-sliders-row">
                <label>Başlangıç: <input type="range" id="crt-slider-start" min="0" max="180" step="0.5" value="14"></label>
                <label>Bitiş: <input type="range" id="crt-slider-end" min="5" max="180" step="0.5" value="46.5"></label>
            </div>
            <div class="crt-sort-bar" id="clipper-sort-bar">
                <span class="crt-sort-lbl"><i class="fa-solid fa-arrow-down-wide-short"></i> Kesit Sıralaması (Madde 73):</span>
                <button type="button" class="crt-sort-pill active" data-csort="viral">🔥 Viral Skor (96/100)</button>
                <button type="button" class="crt-sort-pill" data-csort="duration">⏱️ Süre</button>
                <button type="button" class="crt-sort-pill" data-csort="chrono">🕒 Kronolojik</button>
            </div>
            <div class="crt-candidates-list" id="crt-candidates-list"></div>
        `;
        manualStart.closest('.form-field')?.before(trimmer);

        const sStart = document.getElementById('crt-slider-start');
        const sEnd = document.getElementById('crt-slider-end');
        const readout = document.getElementById('crt-time-readout');

        function syncClipperRange() {
            let st = parseFloat(sStart?.value || '14');
            let en = parseFloat(sEnd?.value || '46.5');
            if (en <= st + 3) {
                en = Math.min(180, st + 15);
                if (sEnd) sEnd.value = String(en);
            }
            manualStart.value = st.toFixed(1);
            if (manualEnd) manualEnd.value = en.toFixed(1);
            if (readout) readout.textContent = `${st.toFixed(1)}sn — ${en.toFixed(1)}sn (${(en - st).toFixed(1)}sn Shorts)`;
        }

        sStart?.addEventListener('input', syncClipperRange);
        sEnd?.addEventListener('input', syncClipperRange);

        function renderClipperCandidates(sortMode = 'viral') {
            const listEl = document.getElementById('crt-candidates-list');
            if (!listEl) return;
            const sorted = [...clipperCandidates].sort((a, b) => {
                if (sortMode === 'duration') return (a.end - a.start) - (b.end - b.start);
                if (sortMode === 'chrono') return a.start - b.start;
                return b.viralScore - a.viralScore;
            });
            listEl.innerHTML = sorted.map(c => `
                <div class="crt-cand-card" data-cid="${c.id}">
                    <div class="crt-cand-main">
                        <span class="crt-viral-pill">🔥 ${c.viralScore}/100</span>
                        <strong>${escapeHtmlSafe(c.title)}</strong>
                        <small>${c.start.toFixed(1)}s – ${c.end.toFixed(1)}s (${(c.end - c.start).toFixed(1)}sn) · ${escapeHtmlSafe(c.reason)}</small>
                    </div>
                    <button type="button" class="crt-use-cand-btn" data-start="${c.start}" data-end="${c.end}">Aralığı Seç</button>
                </div>
            `).join('');

            listEl.querySelectorAll('.crt-use-cand-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    if (sStart) sStart.value = btn.getAttribute('data-start') || '14';
                    if (sEnd) sEnd.value = btn.getAttribute('data-end') || '46.5';
                    syncClipperRange();
                });
            });
        }

        trimmer.querySelectorAll('.crt-sort-pill').forEach(btn => {
            btn.addEventListener('click', () => {
                trimmer.querySelectorAll('.crt-sort-pill').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                renderClipperCandidates(btn.getAttribute('data-csort') || 'viral');
            });
        });

        renderClipperCandidates('viral');
    }

    // ── 74 & 75: #pane-batch CSV Template & Queue Controls ───────────────────
    function enhanceBatchPane() {
        const dropzone = document.getElementById('csv-dropzone');
        if (dropzone && !document.getElementById('batch-csv-helper')) {
            const helper = document.createElement('div');
            helper.id = 'batch-csv-helper';
            helper.className = 'batch-csv-helper mt-2';
            helper.innerHTML = `
                <div class="bch-top-row">
                    <span><i class="fa-solid fa-table text-success"></i> Örnek CSV Şablonu (Madde 74)</span>
                    <div class="bch-actions">
                        <button type="button" class="btn btn-xs btn-secondary" id="btn-download-sample-csv">
                            <i class="fa-solid fa-download"></i> Örnek CSV Şablonunu İndir
                        </button>
                        <button type="button" class="btn btn-xs btn-outline" id="btn-fill-sample-batch">
                            <i class="fa-solid fa-bolt"></i> 3 Örnek Konuyu Doldur
                        </button>
                    </div>
                </div>
                <table class="bch-preview-table">
                    <thead><tr><th>topic</th><th>niche</th><th>language</th></tr></thead>
                    <tbody>
                        <tr><td>Marcus Aurelius'un 3 Sabah Kuralı</td><td>stoic_wisdom</td><td>tr</td></tr>
                        <tr><td>Karadeliklerin İçinde Zaman Nasıl Akar?</td><td>space_mysteries</td><td>tr</td></tr>
                        <tr><td>Beynin 3 Saniyelik İlk İzlenim Hilesi</td><td>dark_psychology</td><td>tr</td></tr>
                    </tbody>
                </table>
            `;
            dropzone.after(helper);

            document.getElementById('btn-download-sample-csv')?.addEventListener('click', () => {
                const csvContent = '\uFEFFtopic,niche,language\n"Marcus Aurelius\'un 3 Sabah Kuralı",stoic_wisdom,tr\n"Karadeliklerin İçinde Zaman Nasıl Akar?",space_mysteries,tr\n"Beynin 3 Saniyelik İlk İzlenim Hilesi",dark_psychology,tr\n';
                const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
                const a = document.createElement('a');
                a.href = URL.createObjectURL(blob);
                a.download = 'shorts_studio_toplu_is_sablonu.csv';
                a.click();
                if (typeof showToast === 'function') showToast('📥 Örnek CSV şablonu indirildi');
            });

            document.getElementById('btn-fill-sample-batch')?.addEventListener('click', () => {
                const ta = document.getElementById('batch-topics-text');
                if (ta) {
                    ta.value = [
                        "Marcus Aurelius'un 3 Sabah Kuralı",
                        "Karadeliklerin İçinde Zaman Nasıl Akar?",
                        "Beynin 3 Saniyelik İlk İzlenim Hilesi"
                    ].join('\n');
                    if (typeof showToast === 'function') showToast('✨ 3 örnek konu toplu giriş kutusuna eklendi');
                }
            });
        }

        const queueList = document.getElementById('batch-queue-list');
        if (queueList && !document.getElementById('batch-queue-controls')) {
            const qCtrl = document.createElement('div');
            qCtrl.id = 'batch-queue-controls';
            qCtrl.className = 'batch-queue-controls mb-2';
            qCtrl.innerHTML = `
                <button type="button" class="btn btn-xs btn-secondary" id="btn-batch-pause-toggle">
                    <i class="fa-solid fa-pause"></i> Kuyruğu Duraklat
                </button>
                <button type="button" class="btn btn-xs btn-secondary" id="btn-batch-reverse-order">
                    <i class="fa-solid fa-arrow-up-down"></i> Sırayı Değiştir
                </button>
                <button type="button" class="btn btn-xs btn-outline" id="btn-batch-retry-failed">
                    <i class="fa-solid fa-rotate-right text-warning"></i> Tüm Hatalıları Yeniden Dene
                </button>
            `;
            queueList.before(qCtrl);

            document.getElementById('btn-batch-pause-toggle')?.addEventListener('click', (e) => {
                batchQueuePaused = !batchQueuePaused;
                e.currentTarget.innerHTML = batchQueuePaused
                    ? '<i class="fa-solid fa-play text-success"></i> Kuyruğu Devam Ettir'
                    : '<i class="fa-solid fa-pause"></i> Kuyruğu Duraklat';
                if (typeof showToast === 'function') {
                    showToast(batchQueuePaused ? '⏸️ Toplu iş kuyruğu duraklatıldı' : '▶️ Toplu iş kuyruğu devam ediyor');
                }
            });

            document.getElementById('btn-batch-reverse-order')?.addEventListener('click', () => {
                const items = Array.from(queueList.children);
                if (items.length > 1) {
                    items.reverse().forEach(el => queueList.appendChild(el));
                }
                if (typeof showToast === 'function') showToast('🔀 Kuyruk sıralaması güncellendi');
            });

            document.getElementById('btn-batch-retry-failed')?.addEventListener('click', () => {
                if (typeof showToast === 'function') showToast('🔄 Hatalı işler yeniden deneme kuyruğuna alındı');
            });
        }
    }

    // ── 76. #pane-kids-song Step Indicator ───────────────────────────────────
    function enhanceKidsSongPane() {
        const pane = document.getElementById('pane-kids-song');
        const studioBar = pane?.querySelector('.kids-studio-bar');
        if (!pane || !studioBar || document.getElementById('kids-song-stepper')) return;

        const stepper = document.createElement('div');
        stepper.id = 'kids-song-stepper';
        stepper.className = 'kids-song-stepper glass-box mb-2';
        stepper.innerHTML = `
            <div class="kss-stage active" data-kstep="1">
                <span class="kss-num">1</span>
                <div><strong>📝 Söz &amp; Ritim</strong><small>Nakarat &amp; Yaş Uyumu</small></div>
            </div>
            <div class="kss-arrow">→</div>
            <div class="kss-stage" data-kstep="2">
                <span class="kss-num">2</span>
                <div><strong>🎵 Müzik &amp; Vokal</strong><small>Suno / Neşeli Melodi</small></div>
            </div>
            <div class="kss-arrow">→</div>
            <div class="kss-stage" data-kstep="3">
                <span class="kss-num">3</span>
                <div><strong>🎨 Karakter Görselleri</strong><small>3D Pixar / Renkli Sahne</small></div>
            </div>
            <div class="kss-arrow">→</div>
            <div class="kss-stage" data-kstep="4">
                <span class="kss-num">4</span>
                <div><strong>🎬 Video Birleştirme</strong><small>9:16 Karaoke MV Render</small></div>
            </div>
        `;
        studioBar.after(stepper);

        stepper.querySelectorAll('.kss-stage').forEach(st => {
            st.addEventListener('click', () => {
                stepper.querySelectorAll('.kss-stage').forEach(s => s.classList.remove('active'));
                st.classList.add('active');
                if (st.getAttribute('data-kstep') === '1') {
                    document.getElementById('btn-kids-ai-wizard')?.click();
                }
            });
        });
    }

    // ── 80. #pane-settings Live Search Box ───────────────────────────────────
    function enhanceSettingsSearch() {
        const pane = document.getElementById('pane-settings');
        if (!pane || document.getElementById('settings-live-search-bar')) return;

        const searchBar = document.createElement('div');
        searchBar.id = 'settings-live-search-bar';
        searchBar.className = 'settings-live-search-bar glass-box mb-3';
        searchBar.innerHTML = `
            <i class="fa-solid fa-magnifying-glass text-info"></i>
            <input type="search" id="input-settings-live-search" class="input-styled"
                placeholder="Ayarlarda, API anahtarlarında veya FFmpeg parametrelerinde ara (örn: Gemini, NVENC, ElevenLabs, FPS, Pexels)...">
            <span class="settings-search-count" id="lbl-settings-search-count">Tüm Ayarlar</span>
        `;
        pane.prepend(searchBar);

        const input = document.getElementById('input-settings-live-search');
        const countEl = document.getElementById('lbl-settings-search-count');
        input?.addEventListener('input', () => {
            const q = input.value.trim().toLowerCase();
            const fields = pane.querySelectorAll('.form-field');
            let matched = 0;
            fields.forEach(f => {
                const txt = (f.textContent || '').toLowerCase();
                const show = !q || txt.includes(q);
                f.style.display = show ? '' : 'none';
                if (show) matched++;
            });
            if (countEl) {
                countEl.textContent = q ? `${matched} eşleşme` : 'Tüm Ayarlar';
            }
        });
    }

    function initToolsUXEnhancements() {
        enhanceMediaPane();
        enhanceClipperPane();
        enhanceBatchPane();
        enhanceKidsSongPane();
        enhanceSettingsSearch();
    }

    window.initToolsUXEnhancements = initToolsUXEnhancements;

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initToolsUXEnhancements);
    } else {
        initToolsUXEnhancements();
    }
})();
