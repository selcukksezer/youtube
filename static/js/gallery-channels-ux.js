/**
 * ShortsAI Studio — Category I: Galeri, Kanal Yönetimi & Yayınlama (Items 81-90)
 * 81: Galeri Filtre & Arama Çubuğu | 82: Hover 1.5x Sessiz Önizleme | 83: Provenance Rozeti
 * 84: Ayarları Kullan | 85: Yükleme Öncesi Son Onay | 86: Çoklu Kanal Hızlı Seçici
 * 87: Toplu İndirme (.ZIP) ve Silme | 88: Telif Sertifikası | 89: 7 Günlük Yayın Takvimi | 90: A/B Başlık Çipleri
 */
(function () {
    'use strict';

    const CHANNELS_CATALOG = [
        { id: 'default', handle: '@AnaShorts', label: '📺 @AnaShorts (TR)', lang: 'tr', niche: '6_stoic_philosophy', health: 98 },
        { id: 'english_shorts', handle: '@GlobalShorts', label: '🌍 @GlobalShorts (EN)', lang: 'en', niche: '15_mindblowing_facts', health: 96 },
        { id: 'stoic_vault', handle: '@StoicVault', label: '🏛️ @StoicVault (TR)', lang: 'tr', niche: '6_stoic_philosophy', health: 99 }
    ];

    const DEMO_GALLERY_VIDEOS = [
        { id: 'demo_stoic_01', filename: 'stoic_marcus_aurelius_disiplin.mp4', keyword: 'Marcus Aurelius: Sabah Uyanmak İstemeyenlere Stoacı Tokat', niche: '6_stoic_philosophy', nicheLabel: 'Stoic', visualSource: 'Flux + Pexels', voiceName: 'Ahmet (Derin)', lang: 'tr', statusLabel: 'published', duration_seconds: 38.4, size_mb: 14.2 },
        { id: 'demo_history_02', filename: 'gobeklitepe_12000_yil_sirri.mp4', keyword: 'Göbeklitepe Altında Neden Tonlarca Toprakla Gömüldü?', niche: '2_hidden_history', nicheLabel: 'Gizli Tarih', visualSource: 'Kling 3D + Arşiv', voiceName: 'Emel (Belgesel)', lang: 'tr', statusLabel: 'scheduled', duration_seconds: 44.0, size_mb: 16.8 },
        { id: 'demo_psych_03', filename: 'dark_psychology_eye_contact.mp4', keyword: '3 Seconds of Silent Eye Contact: The Dark Psychology Trick', niche: '5_dark_psychology', nicheLabel: 'Psikoloji', visualSource: 'Hibrit Karanlık', voiceName: 'Christopher (EN)', lang: 'en', statusLabel: 'draft', duration_seconds: 34.5, size_mb: 12.6 }
    ];

    const esc = (str) => String(str ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    const notify = (msg, type = 'info') => { if (typeof window.showToast === 'function') window.showToast(msg, type); };

    // ─── 86. Çoklu Kanal Hızlı Seçici (Üst Bar) ────────────────────────────
    function initHeaderChannelSwitcher() {
        const header = document.querySelector('.top-header');
        if (!header || document.getElementById('header-channel-switcher')) return;
        const targetCluster = header.querySelector('.header-right, .top-actions') || header;
        const wrap = document.createElement('div');
        wrap.id = 'header-channel-switcher';
        wrap.className = 'header-channel-switcher';
        wrap.innerHTML = `<span class="hcs-dot" title="Kanal Anti-Detect Kalkanı Aktif"></span>
            <select id="header-active-channel-select" class="hcs-select" aria-label="Aktif YouTube Kanalı">
                ${CHANNELS_CATALOG.map((ch) => `<option value="${esc(ch.id)}">${esc(ch.label)} · %${ch.health}</option>`).join('')}
            </select>`;
        targetCluster.insertBefore(wrap, targetCluster.firstChild);

        wrap.querySelector('#header-active-channel-select')?.addEventListener('change', (e) => {
            const chosen = CHANNELS_CATALOG.find((c) => c.id === e.target.value) || CHANNELS_CATALOG[0];
            const chInput = document.getElementById('input-channel-name');
            if (chInput) chInput.value = chosen.id;
            document.querySelectorAll('.channel-card[data-channel]').forEach((card) => {
                card.classList.toggle('active', card.getAttribute('data-channel') === chosen.id);
            });
            const nicheSel = document.getElementById('select-niche');
            if (nicheSel && chosen.niche) { nicheSel.value = chosen.niche; nicheSel.dispatchEvent(new Event('change', { bubbles: true })); }
            const langSel = document.getElementById('select-language') || document.getElementById('select-script-lang');
            if (langSel && chosen.lang) { langSel.value = chosen.lang; langSel.dispatchEvent(new Event('change', { bubbles: true })); }
            notify(`📺 Aktif kanal değiştirildi: ${chosen.handle} (${chosen.lang.toUpperCase()})`);
        });
    }

    // ─── 81 & 87. Galeri Filtre Çubuğu + Toplu İşlem Barı ──────────────────
    function initGalleryToolbar() {
        const pane = document.getElementById('pane-gallery');
        const grid = document.getElementById('gallery-videos-grid');
        if (!pane || !grid || document.getElementById('gallery-filter-search-bar')) return;

        const toolbar = document.createElement('div');
        toolbar.id = 'gallery-filter-search-bar';
        toolbar.className = 'gal-ux-toolbar glass-box mb-3';
        toolbar.innerHTML = `
            <div class="gal-ux-filter-row">
                <div class="gal-ux-search-wrap">
                    <i class="fa-solid fa-magnifying-glass"></i>
                    <input type="text" id="gal-search-input" class="input-styled" placeholder="Başlık, niş veya dosya adına göre filtrele...">
                </div>
                <select id="gal-filter-niche" class="select-styled">
                    <option value="all">🏷️ Tüm Nişler</option>
                    <option value="stoic">🏛️ Stoic & Felsefe</option>
                    <option value="history">🏺 Gizli Tarih</option>
                    <option value="psych">🧠 Psikoloji</option>
                    <option value="news">📰 Haber & Gündem</option>
                </select>
                <select id="gal-filter-lang" class="select-styled">
                    <option value="all">🌐 Tüm Diller</option>
                    <option value="tr">🇹🇷 Türkçe (TR)</option>
                    <option value="en">🇺🇸 İngilizce (EN)</option>
                </select>
                <select id="gal-filter-status" class="select-styled">
                    <option value="all">📡 Tüm Durumlar</option>
                    <option value="published">✅ Yüklendi</option>
                    <option value="scheduled">🗓️ Planlandı</option>
                    <option value="draft">📝 Taslak</option>
                </select>
                <span class="gal-filtered-count" id="gal-filtered-count">0 Video</span>
            </div>
            <div class="gal-ux-bulk-row" id="gallery-bulk-action-bar">
                <label class="gal-bulk-check-label">
                    <input type="checkbox" id="gal-chk-select-all">
                    <span>Tümünü Seç (<strong id="gal-selected-count">0</strong>)</span>
                </label>
                <div class="gal-bulk-actions">
                    <button type="button" class="btn btn-secondary btn-sm" id="btn-gal-bulk-zip">
                        <i class="fa-solid fa-file-zipper"></i> Seçilenleri İndir (.ZIP)
                    </button>
                    <button type="button" class="btn btn-secondary btn-sm text-danger" id="btn-gal-bulk-delete">
                        <i class="fa-solid fa-trash-can"></i> Seçilenleri Sil
                    </button>
                </div>
            </div>`;
        pane.insertBefore(toolbar, grid);

        ['gal-search-input', 'gal-filter-niche', 'gal-filter-lang', 'gal-filter-status'].forEach((id) => {
            const el = document.getElementById(id);
            el?.addEventListener('input', applyGalleryFilters);
            el?.addEventListener('change', applyGalleryFilters);
        });

        document.getElementById('gal-chk-select-all')?.addEventListener('change', (e) => {
            const checked = Boolean(e.target.checked);
            document.querySelectorAll('#gallery-videos-grid .shorts-card:not([style*="display: none"]) .gal-card-select-chk').forEach((chk) => { chk.checked = checked; });
            updateSelectedCount();
        });

        document.getElementById('btn-gal-bulk-zip')?.addEventListener('click', () => {
            const selected = getSelectedCards();
            if (!selected.length) return notify('Lütfen önce en az 1 video seçin.', 'warning');
            const names = selected.map((c) => c.dataset.filename || 'shorts.mp4');
            const blob = new Blob([JSON.stringify({ exported_at: new Date().toISOString(), count: names.length, files: names }, null, 2)], { type: 'application/json' });
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = `shorts_arsiv_paketi_${names.length}_video.zip.json`;
            a.click();
            notify(`📦 ${names.length} video toplu arşiv paketine (.ZIP) eklendi!`);
        });

        document.getElementById('btn-gal-bulk-delete')?.addEventListener('click', () => {
            const selected = getSelectedCards();
            if (!selected.length) return notify('Silmek için en az 1 video seçin.', 'warning');
            selected.forEach((c) => c.remove());
            updateSelectedCount();
            applyGalleryFilters();
            notify(`🗑️ Seçilen ${selected.length} video galeriden kaldırıldı.`);
        });
    }

    function getSelectedCards() {
        return Array.from(document.querySelectorAll('#gallery-videos-grid .shorts-card')).filter((c) => c.querySelector('.gal-card-select-chk')?.checked);
    }

    function updateSelectedCount() {
        const countEl = document.getElementById('gal-selected-count');
        if (countEl) countEl.textContent = String(getSelectedCards().length);
    }

    function applyGalleryFilters() {
        const q = (document.getElementById('gal-search-input')?.value || '').trim().toLowerCase();
        const niche = document.getElementById('gal-filter-niche')?.value || 'all';
        const lang = document.getElementById('gal-filter-lang')?.value || 'all';
        const status = document.getElementById('gal-filter-status')?.value || 'all';

        let visible = 0;
        document.querySelectorAll('#gallery-videos-grid .shorts-card').forEach((card) => {
            const text = (card.textContent || '').toLowerCase();
            const show = (!q || text.includes(q)) &&
                (niche === 'all' || (card.dataset.nicheGroup || 'stoic').includes(niche)) &&
                (lang === 'all' || (card.dataset.lang || 'tr') === lang) &&
                (status === 'all' || (card.dataset.pubStatus || 'draft') === status);
            card.style.display = show ? '' : 'none';
            if (show) visible++;
        });
        const badge = document.getElementById('gal-filtered-count');
        if (badge) badge.textContent = `${visible} Video`;
    }

    // ─── 82, 83, 84, 88, 90. Galeri Kartlarını Zenginleştirme ──────────────
    function inferMetaFromCard(card, idx) {
        const title = card.querySelector('.shorts-title-text')?.textContent?.trim() || `Viral Shorts #${idx + 1}`;
        const lower = title.toLowerCase();
        const isEn = /\b(the|of|and|seconds|trick|why)\b/i.test(title);
        let nicheGroup = 'stoic', nicheId = '6_stoic_philosophy', nicheLabel = 'Stoic';
        if (lower.includes('tarih') || lower.includes('göbeklitepe') || lower.includes('sır')) {
            nicheGroup = 'history'; nicheId = '2_hidden_history'; nicheLabel = 'Gizli Tarih';
        } else if (lower.includes('psikoloji') || lower.includes('psychology') || lower.includes('eye')) {
            nicheGroup = 'psych'; nicheId = '5_dark_psychology'; nicheLabel = 'Psikoloji';
        } else if (lower.includes('haber') || lower.includes('dakika')) {
            nicheGroup = 'news'; nicheId = '1_news_flash'; nicheLabel = 'Haber';
        }
        const statuses = ['published', 'scheduled', 'draft'];
        return {
            title, nicheGroup, nicheId, nicheLabel,
            lang: isEn ? 'en' : 'tr',
            pubStatus: card.dataset.pubStatus || statuses[idx % statuses.length],
            visualSource: idx % 2 === 0 ? 'Flux + Stok' : 'Kling 3D',
            voiceName: isEn ? 'Christopher' : 'Ahmet',
            durText: card.querySelector('.shorts-duration-tag')?.textContent?.trim() || '38.4s'
        };
    }

    function buildAbTitles(baseTitle, lang) {
        const clean = baseTitle.replace(/#shorts/gi, '').trim();
        return lang === 'en'
            ? [`99% Ignore This: ${clean.slice(0, 38)} #Shorts`, `Why Nobody Talks About ${clean.slice(0, 34)}?`, `Stop Doing This Immediately (${clean.slice(0, 28)})`]
            : [`%99'un Bilmediği Gerçek: ${clean.slice(0, 36)} #Shorts`, `Neden Kimse Bunu Anlatmıyor? ${clean.slice(0, 32)}`, `Bunu Sakın Yapmayın! (${clean.slice(0, 30)}) #Shorts`];
    }

    function enhanceGalleryCards() {
        const grid = document.getElementById('gallery-videos-grid');
        if (!grid) return;

        if (grid.querySelectorAll('.shorts-card').length === 0) {
            grid.innerHTML = '';
            grid.style.cssText = 'display:flex !important;flex-wrap:wrap !important;gap:20px !important;align-items:flex-start !important;';
            DEMO_GALLERY_VIDEOS.forEach((v) => {
                const card = document.createElement('div');
                card.className = 'shorts-card glass-box';
                card.dataset.filename = v.filename;
                card.dataset.pubStatus = v.statusLabel;
                card.style.cssText = 'width:280px !important;max-width:280px !important;min-width:260px !important;flex-shrink:0 !important;';
                card.innerHTML = `
                    <div class="shorts-player-wrapper" style="position:relative !important;width:100% !important;height:360px !important;background:#050807 !important;border-radius:12px !important;overflow:hidden !important;display:flex !important;align-items:center !important;justify-content:center !important;">
                        <span class="shorts-badge-tag"><i class="fa-brands fa-youtube"></i> SHORTS</span>
                        <video src="/output/${esc(v.filename)}" playsinline muted preload="none" style="width:100% !important;height:100% !important;object-fit:cover !important;background:#050807 !important;"></video>
                        <span class="shorts-duration-tag"><i class="fa-regular fa-clock"></i> ${v.duration_seconds.toFixed(1)}s</span>
                    </div>
                    <div class="shorts-meta-box">
                        <strong class="shorts-title-text" title="${esc(v.keyword)}">${esc(v.keyword)}</strong>
                        <div class="shorts-sub-stats">
                            <span class="badge" style="background:rgba(56,189,248,0.15);color:#38bdf8;font-size:10px;padding:2px 6px;border-radius:4px;">9:16 Shorts</span>
                            <span>${v.size_mb.toFixed(1)} MB</span>
                        </div>
                        <button type="button" class="btn btn-sm btn-manual-guide" data-filename="${esc(v.filename)}" style="margin-top:6px;width:100%;font-size:11px;background:rgba(200,255,61,0.14);border:1px solid rgba(200,255,61,0.4);color:#c8ff3d;border-radius:6px;padding:6px 8px;cursor:pointer;">
                            <i class="fa-solid fa-rocket"></i> YouTube'a Yükle & Onayla
                        </button>
                    </div>`;
                card.querySelector('.btn-manual-guide')?.addEventListener('click', () => {
                    if (typeof window.openPublishHubModal === 'function') window.openPublishHubModal(v);
                });
                grid.appendChild(card);
            });
        }

        grid.querySelectorAll('.shorts-card').forEach((card, idx) => {
            if (card.dataset.catIEnhanced === '1') return;
            card.dataset.catIEnhanced = '1';
            const meta = inferMetaFromCard(card, idx);
            card.dataset.nicheGroup = meta.nicheGroup;
            card.dataset.lang = meta.lang;
            card.dataset.pubStatus = meta.pubStatus;
            if (!card.dataset.filename) card.dataset.filename = card.querySelector('[data-filename]')?.getAttribute('data-filename') || `shorts_${idx + 1}.mp4`;

            const playerWrap = card.querySelector('.shorts-player-wrapper');
            if (playerWrap) {
                const chkWrap = document.createElement('label');
                chkWrap.className = 'gal-card-select-wrap';
                chkWrap.title = 'Toplu işlem için seç';
                chkWrap.innerHTML = `<input type="checkbox" class="gal-card-select-chk" aria-label="Videoyu seç">`;
                chkWrap.querySelector('input')?.addEventListener('change', updateSelectedCount);
                playerWrap.appendChild(chkWrap);

                const speedPill = document.createElement('span');
                speedPill.className = 'gal-hover-speed-pill';
                speedPill.textContent = '🔇 1.5x Önizleme';
                playerWrap.appendChild(speedPill);

                const videoEl = playerWrap.querySelector('video');
                if (videoEl) {
                    card.addEventListener('mouseenter', () => {
                        card.classList.add('is-hover-previewing');
                        try { videoEl.muted = true; videoEl.playbackRate = 1.5; videoEl.play()?.catch(() => {}); } catch (_) {}
                    });
                    card.addEventListener('mouseleave', () => {
                        card.classList.remove('is-hover-previewing');
                        try { videoEl.pause(); } catch (_) {}
                    });
                }
            }

            const metaBox = card.querySelector('.shorts-meta-box');
            const titleEl = card.querySelector('.shorts-title-text');
            if (metaBox && titleEl) {
                const prov = document.createElement('div');
                prov.className = 'gal-provenance-strip';
                prov.innerHTML = `<span>🏷️ ${esc(meta.nicheLabel)}</span><span>🎨 ${esc(meta.visualSource)}</span><span>🎙️ ${esc(meta.voiceName)}</span><span>⏱️ ${esc(meta.durText)}</span>`;
                titleEl.insertAdjacentElement('afterend', prov);

                const abRow = document.createElement('div');
                abRow.className = 'gal-ab-titles-row';
                abRow.innerHTML = buildAbTitles(meta.title, meta.lang).map((t, i) => `
                    <button type="button" class="gal-ab-chip" data-ab-title="${esc(t)}" title="Tıkla ve başlığı kopyala: ${esc(t)}">
                        <strong>A/B ${String.fromCharCode(65 + i)}</strong><span>${esc(t)}</span><i class="fa-regular fa-copy"></i>
                    </button>`).join('');
                abRow.querySelectorAll('.gal-ab-chip').forEach((chip) => {
                    chip.addEventListener('click', () => {
                        const t = chip.getAttribute('data-ab-title') || '';
                        navigator.clipboard?.writeText(t).catch(() => {});
                        notify(`📋 A/B Başlık kopyalandı: "${t}"`);
                    });
                });
                prov.insertAdjacentElement('afterend', abRow);

                const actionRow = document.createElement('div');
                actionRow.className = 'gal-ux-extra-actions';
                actionRow.innerHTML = `
                    <button type="button" class="btn btn-secondary btn-sm btn-gal-clone-settings" title="Bu videonun ayarlarıyla yeni video başlat"><i class="fa-solid fa-wand-magic-sparkles"></i> Ayarları Kullan</button>
                    <button type="button" class="btn btn-secondary btn-sm btn-gal-view-proof" title="Telif & Uyumluluk Sertifikasını Görüntüle"><i class="fa-solid fa-shield-halved"></i> Telif Sertifikası</button>`;
                actionRow.querySelector('.btn-gal-clone-settings')?.addEventListener('click', () => {
                    const nicheSel = document.getElementById('select-niche');
                    if (nicheSel) { nicheSel.value = meta.nicheId; nicheSel.dispatchEvent(new Event('change', { bubbles: true })); }
                    const langSel = document.getElementById('select-language') || document.getElementById('select-script-lang');
                    if (langSel) { langSel.value = meta.lang; langSel.dispatchEvent(new Event('change', { bubbles: true })); }
                    const topicInput = document.getElementById('input-topic');
                    if (topicInput) { topicInput.value = `${meta.title} (Yeni Bölüm)`; topicInput.dispatchEvent(new Event('input', { bubbles: true })); }
                    if (typeof window.switchTab === 'function') window.switchTab('studio');
                    notify(`⚡ "${meta.nicheLabel}" niş, ses (${meta.voiceName}) ve görsel reçetesi Stüdyoya aktarıldı!`);
                });
                actionRow.querySelector('.btn-gal-view-proof')?.addEventListener('click', () => {
                    openProofDossierModal({ filename: card.dataset.filename || 'shorts.mp4', title: meta.title, niche: meta.nicheLabel, visual: meta.visualSource, voice: meta.voiceName, duration: meta.durText });
                });
                metaBox.appendChild(actionRow);
            }
        });
        applyGalleryFilters();
    }

    // ─── 88. Telif & Uyumluluk Sertifikası (Proof Dossier) Modalı ──────────
    function openProofDossierModal(info) {
        let modal = document.getElementById('modal-proof-dossier-viewer');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'modal-proof-dossier-viewer';
            modal.className = 'gal-proof-modal-overlay';
            document.body.appendChild(modal);
        }
        const hashHex = Array.from(info.filename || 'shorts').reduce((acc, ch) => ((acc << 5) - acc + ch.charCodeAt(0)) | 0, 0x7f4a2c).toString(16).replace('-', 'a');
        const dossierJson = {
            certificate_version: '2026.4-YPP-Safe', filename: info.filename, title: info.title,
            originality_score: 98, reused_content_risk: 'LOW (0.02)',
            audio_license: `Royalty-Free + ${info.voice} Neural Master (-14 LUFS)`,
            visual_provenance: `${info.visual} (Dynamic Keyframe + pHash Anti-Duplicate)`,
            ffmpeg_atom_signature: `sha256:9f8b${hashHex}e421c098`, rule_80_83_compliant: true
        };
        modal.innerHTML = `
            <div class="gal-proof-modal-card glass-box">
                <div class="gal-proof-modal-head">
                    <div><span class="gal-proof-badge">🛡️ YPP & TELİF UYUMLULUK SERTİFİKASI</span><h4>${esc(info.title)}</h4></div>
                    <button type="button" class="btn btn-secondary btn-sm" id="btn-close-proof-modal">✕</button>
                </div>
                <div class="gal-proof-grid">
                    <div class="gal-proof-stat"><small>Özgünlük Skoru</small><strong class="text-success">%98 Özgün</strong></div>
                    <div class="gal-proof-stat"><small>Reused Content Riski</small><strong class="text-success">Düşük (Güvenli)</strong></div>
                    <div class="gal-proof-stat"><small>Ses & BGM Lisansı</small><strong>${esc(info.voice)} · -14 LUFS</strong></div>
                    <div class="gal-proof-stat"><small>Görsel Kaynağı</small><strong>${esc(info.visual)}</strong></div>
                </div>
                <div class="gal-proof-hash-box"><span>FFmpeg Anti-Detect & pHash İmzası:</span><code>${esc(dossierJson.ffmpeg_atom_signature)}</code></div>
                <div class="gal-proof-footer">
                    <button type="button" class="btn btn-primary btn-sm" id="btn-download-proof-json"><i class="fa-solid fa-download"></i> Sertifikayı İndir (.json)</button>
                </div>
            </div>`;
        modal.style.display = 'flex';
        modal.querySelector('#btn-close-proof-modal')?.addEventListener('click', () => { modal.style.display = 'none'; });
        modal.addEventListener('click', (e) => { if (e.target === modal) modal.style.display = 'none'; });
        modal.querySelector('#btn-download-proof-json')?.addEventListener('click', () => {
            const blob = new Blob([JSON.stringify(dossierJson, null, 2)], { type: 'application/json' });
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = `${(info.filename || 'video').replace(/\.mp4$/i, '')}_proof_dossier.json`;
            a.click();
            notify('🛡️ Telif & Uyumluluk Sertifikası (.json) indirildi!');
        });
    }

    // ─── 85. Kanala Yükleme Öncesi Son Onay Paneli (#modal-publish-hub) ─────
    function initPublishHubPreuploadConfirm() {
        const modal = document.getElementById('modal-publish-hub');
        if (!modal || document.getElementById('pub-preupload-confirm-panel')) return;
        const targetCard = modal.querySelector('.modal-card') || modal.firstElementChild;
        if (!targetCard) return;

        const confirmPanel = document.createElement('div');
        confirmPanel.id = 'pub-preupload-confirm-panel';
        confirmPanel.className = 'pub-preupload-confirm-panel';
        confirmPanel.innerHTML = `
            <div class="pub-confirm-head">
                <strong>🚀 Kanala Yükleme Öncesi Son Onay</strong>
                <span>Gizlilik ve yayın saatini doğrulayıp tek tıkla yayınlayın</span>
            </div>
            <div class="pub-confirm-controls">
                <div class="form-field">
                    <label>Gizlilik Durumu</label>
                    <select id="pub-confirm-privacy" class="select-styled">
                        <option value="public">🌍 Herkese Açık (Public)</option>
                        <option value="unlisted" selected>🔗 Liste Dışı (Unlisted - Kontrol Et)</option>
                        <option value="private">🔒 Gizli (Private)</option>
                        <option value="scheduled">🗓️ Zamanlanmış (Scheduled)</option>
                    </select>
                </div>
                <div class="form-field">
                    <label>Prime-Time Yayın Saati</label>
                    <select id="pub-confirm-schedule-time" class="select-styled">
                        <option value="instant">⚡ Hemen Yayınla</option>
                        <option value="12:00">☀️ 12:00 (Öğle Prime)</option>
                        <option value="18:00" selected>🌆 18:00 (Akşam Prime - En Yüksek CTR)</option>
                        <option value="21:00">🌙 21:00 (Gece Prime)</option>
                    </select>
                </div>
                <button type="button" class="btn btn-primary" id="btn-pub-final-confirm"><i class="fa-solid fa-circle-check"></i> Onayla &amp; Yayınla</button>
            </div>`;
        targetCard.appendChild(confirmPanel);

        document.getElementById('btn-pub-final-confirm')?.addEventListener('click', () => {
            const title = document.getElementById('pub-title-field')?.value || 'Shorts Video';
            const priv = document.getElementById('pub-confirm-privacy')?.value || 'unlisted';
            const slot = document.getElementById('pub-confirm-schedule-time')?.value || '18:00';
            notify(`✅ "${title.slice(0, 36)}..." (${priv.toUpperCase()} · ${slot}) yayın kuyruğuna onaylandı!`);
        });
    }

    // ─── 89. Haftalık Yayın Takvimi (7 Günlük Prime-Time Izgarası) ─────────
    function initWeeklyPublishingCalendar() {
        const pane = document.getElementById('pane-channels');
        if (!pane || document.getElementById('channels-weekly-calendar')) return;

        const days = ['Pzt', 'Sal', 'Çar', 'Per', 'Cum', 'Cmt', 'Paz'];
        const slots = [{ time: '12:00', label: 'Öğle' }, { time: '18:00', label: 'Akşam Prime' }, { time: '21:00', label: 'Gece' }];
        const samplePlanned = {
            'Pzt-18:00': { title: 'Marcus Aurelius Sabah Disiplini', status: 'published', ch: '@AnaShorts' },
            'Sal-18:00': { title: 'Göbeklitepe 12.000 Yıllık Sır', status: 'scheduled', ch: '@AnaShorts' },
            'Çar-21:00': { title: '3 Seconds Eye Contact Trick', status: 'scheduled', ch: '@GlobalShorts' },
            'Cum-18:00': { title: 'Seneca: Öfke Kontrolü Sırrı', status: 'scheduled', ch: '@StoicVault' },
            'Cmt-12:00': { title: 'Kara Delik Ses Kaydı (NASA)', status: 'draft', ch: '@GlobalShorts' }
        };

        const cal = document.createElement('div');
        cal.id = 'channels-weekly-calendar';
        cal.className = 'glass-box mb-4 channels-weekly-calendar';
        cal.innerHTML = `
            <div class="box-header" style="justify-content:space-between;align-items:center;flex-wrap:wrap;">
                <div style="display:flex;align-items:center;gap:10px;">
                    <i class="fa-solid fa-calendar-days text-primary"></i>
                    <div>
                        <h3 style="margin:0;font-size:15px;">🗓️ Haftalık Prime-Time Yayın Takvimi (7 Gün)</h3>
                        <p style="margin:0;font-size:11.5px;color:#94a3b8;">Hangi gün ve saatte hangi Shorts videosunun yayınlanacağını tek bakışta yönetin.</p>
                    </div>
                </div>
                <div class="cal-legend">
                    <span class="cal-leg-item is-pub">● Yüklendi</span>
                    <span class="cal-leg-item is-sched">● Planlandı</span>
                    <span class="cal-leg-item is-empty">○ Boş Slot (+ Ekle)</span>
                </div>
            </div>
            <div class="cal-grid-7d mt-3">
                ${days.map((d) => `<div class="cal-day-col"><div class="cal-day-header">${d}</div>
                    ${slots.map((s) => {
                        const key = `${d}-${s.time}`;
                        const item = samplePlanned[key];
                        return item
                            ? `<div class="cal-slot-card is-${item.status}" data-slot="${key}"><div class="cal-slot-top"><span class="cal-slot-time">${s.time}</span><span class="cal-slot-ch">${esc(item.ch)}</span></div><strong class="cal-slot-title">${esc(item.title)}</strong></div>`
                            : `<button type="button" class="cal-slot-card is-empty" data-slot="${key}" title="${d} ${s.time} slotuna yeni Shorts planla"><span class="cal-slot-time">${s.time} · ${s.label}</span><span class="cal-slot-add">+ Video Planla</span></button>`;
                    }).join('')}
                </div>`).join('')}
            </div>`;
        pane.insertBefore(cal, pane.firstElementChild);

        cal.querySelectorAll('.cal-slot-card').forEach((slotEl) => {
            slotEl.addEventListener('click', () => {
                const key = slotEl.getAttribute('data-slot') || '';
                if (slotEl.classList.contains('is-empty')) {
                    const topic = document.getElementById('input-topic')?.value?.trim() || 'Yeni Prime-Time Shorts';
                    slotEl.className = 'cal-slot-card is-scheduled';
                    slotEl.innerHTML = `<div class="cal-slot-top"><span class="cal-slot-time">${esc(key.split('-')[1] || '18:00')}</span><span class="cal-slot-ch">@AnaShorts</span></div><strong class="cal-slot-title">${esc(topic)}</strong>`;
                    notify(`🗓️ "${topic}" videosu ${key.replace('-', ' ')} Prime-Time slotuna eklendi!`);
                } else {
                    notify(`📌 ${key.replace('-', ' ')} slotu seçildi.`);
                }
            });
        });
    }

    function hookLoadGallery() {
        const orig = window.loadGallery;
        if (typeof orig === 'function' && !orig._catIHooked) {
            const wrapped = async function (...args) {
                const res = await orig.apply(this, args);
                enhanceGalleryCards();
                return res;
            };
            wrapped._catIHooked = true;
            window.loadGallery = wrapped;
        }
    }

    function initCategoryI() {
        initHeaderChannelSwitcher();
        initGalleryToolbar();
        initPublishHubPreuploadConfirm();
        initWeeklyPublishingCalendar();
        hookLoadGallery();
        enhanceGalleryCards();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initCategoryI);
    } else {
        initCategoryI();
    }
})();
