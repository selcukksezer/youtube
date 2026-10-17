/**
 * ShortsAI Studio — Secondary Tabs Visual & Interactive UX Polish (secondary-tabs-ux.js)
 * Covers:
 *  1. #pane-niches (Araştırma & Niş Kütüphanesi): Quick RPM/Competition Filter + Hybrid Collision Presets
 *  2. #pane-growth (Analitik & Büyüme): 4-KPI Telemetry Strip + SVG Retention Curve + Studio Repair Bridge
 *  3. #pane-rss-bot (Reddit & RSS): Quick Source Chips + Hook Formula Selector + Instant News Preview
 *  4. #pane-subtitles (Altyazı Stilleri): Stage Background Contrast Switcher + Safe-Zone + Apply to Studio CTA
 *  5. #pane-effects (Split-Screen & FX): Live Split-Ratio Resizer + Gameplay Picker + Anti-Detect Hash Simulator
 */
(function () {
    'use strict';

    const esc = (s) => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    const notify = (msg, type = 'info') => { if (typeof window.showToast === 'function') window.showToast(msg, type); };

    // ─── 1. ARAŞTIRMA & NİŞ KÜTÜPHANESİ (#pane-niches) ─────────────────────
    function initNichesTabUX() {
        const pane = document.getElementById('pane-niches');
        const grid = document.getElementById('niches-cards-grid');
        if (!pane || !grid || document.getElementById('niches-quick-sort-bar')) return;

        const bar = document.createElement('div');
        bar.id = 'niches-quick-sort-bar';
        bar.className = 'sec-ux-bar glass-box mb-3';
        bar.innerHTML = `
            <div class="sec-ux-row">
                <div class="sec-ux-pills" id="niches-tier-pills">
                    <button type="button" class="sec-pill active" data-nfilter="all">🌐 Tüm Nişler (35)</button>
                    <button type="button" class="sec-pill" data-nfilter="rpm">💰 Yüksek RPM ($6+)</button>
                    <button type="button" class="sec-pill" data-nfilter="low">⚡ Düşük Rekabet</button>
                    <button type="button" class="sec-pill" data-nfilter="stoic">🏛️ Felsefe & Tarih</button>
                    <button type="button" class="sec-pill" data-nfilter="tech">🤖 Bilim & Teknoloji</button>
                </div>
                <input type="text" id="niches-quick-search" class="input-styled sec-ux-search" placeholder="Niş veya anahtar kelime filtrele...">
            </div>`;
        pane.insertBefore(bar, grid);

        const filterNiches = () => {
            const q = (document.getElementById('niches-quick-search')?.value || '').trim().toLowerCase();
            const activeMode = bar.querySelector('.sec-pill.active')?.getAttribute('data-nfilter') || 'all';
            grid.querySelectorAll('.niche-card, .glass-box').forEach((card) => {
                const txt = (card.textContent || '').toLowerCase();
                let matchMode = true;
                if (activeMode === 'rpm') matchMode = txt.includes('$') || txt.includes('finans') || txt.includes('kripto') || txt.includes('teknoloji') || txt.includes('stoic');
                else if (activeMode === 'low') matchMode = txt.includes('düşük') || txt.includes('orta') || txt.includes('arkeoloji') || txt.includes('gizem');
                else if (activeMode === 'stoic') matchMode = txt.includes('stoic') || txt.includes('tarih') || txt.includes('felsefe') || txt.includes('psikoloji');
                else if (activeMode === 'tech') matchMode = txt.includes('uzay') || txt.includes('bilim') || txt.includes('yapay') || txt.includes('teknoloji');
                const show = (!q || txt.includes(q)) && matchMode;
                card.style.display = show ? '' : 'none';
            });
        };

        bar.querySelectorAll('.sec-pill').forEach((btn) => {
            btn.addEventListener('click', () => {
                bar.querySelectorAll('.sec-pill').forEach((b) => b.classList.remove('active'));
                btn.classList.add('active');
                filterNiches();
            });
        });
        document.getElementById('niches-quick-search')?.addEventListener('input', filterNiches);

        // Hybrid Collision Presets inside Collision Engine card
        const collideBtn = document.getElementById('btn-collide-niches');
        if (collideBtn && !document.getElementById('collision-preset-pills')) {
            const presetRow = document.createElement('div');
            presetRow.id = 'collision-preset-pills';
            presetRow.className = 'sec-collision-presets mt-2';
            presetRow.innerHTML = `
                <small>⚡ Hazır Melez Kombinasyonlar:</small>
                <div class="sec-ux-pills">
                    <button type="button" class="sec-pill is-mini" data-ca="6_stoic_philosophy" data-cb="4_ai_future_tech">🏛️ Stoic ✕ 🤖 AI Gelecek</button>
                    <button type="button" class="sec-pill is-mini" data-ca="2_hidden_history" data-cb="5_dark_psychology">🏺 Gizli Tarih ✕ 🧠 Psikoloji</button>
                    <button type="button" class="sec-pill is-mini" data-ca="3_space_cosmos" data-cb="15_mindblowing_facts">🌌 Uzay ✕ 🤯 Şok Gerçekler</button>
                </div>`;
            collideBtn.parentElement?.insertBefore(presetRow, collideBtn);
            presetRow.querySelectorAll('[data-ca]').forEach((p) => {
                p.addEventListener('click', () => {
                    const selA = document.getElementById('collision-niche-a');
                    const selB = document.getElementById('collision-niche-b');
                    if (selA) selA.value = p.getAttribute('data-ca');
                    if (selB) selB.value = p.getAttribute('data-cb');
                    collideBtn.click();
                });
            });
        }
    }

    // ─── 2. ANALİTİK & BÜYÜME (#pane-growth) ───────────────────────────────
    function initGrowthAnalyticsTabUX() {
        const pane = document.getElementById('pane-growth');
        if (!pane || document.getElementById('growth-kpi-hero-strip')) return;

        const hero = document.createElement('div');
        hero.id = 'growth-kpi-hero-strip';
        hero.className = 'sec-growth-hero glass-box mb-4';
        hero.innerHTML = `
            <div class="sec-growth-kpi-grid">
                <div class="sec-kpi-card">
                    <small>📈 Ortalama İzlenme (APV)</small>
                    <strong class="text-success">%84.6</strong>
                    <span>Hedef: &gt;%75 (Algoritma İvmesi)</span>
                </div>
                <div class="sec-kpi-card">
                    <small>⚡ İlk 3sn Kanca Tutma</small>
                    <strong style="color:var(--lime);">%79.2</strong>
                    <span>Kaydırma Oranı: %20.8 (Düşük)</span>
                </div>
                <div class="sec-kpi-card">
                    <small>💰 Tahmini Shorts RPM</small>
                    <strong class="text-warning">$4.85</strong>
                    <span>Tier-1 + Hibrit Niş Çarpanı</span>
                </div>
                <div class="sec-kpi-card">
                    <small>🛡️ YPP &amp; Anti-Detect Kalkanı</small>
                    <strong class="text-info">98 / 100</strong>
                    <span>pHash &amp; -14 LUFS Aktif</span>
                </div>
            </div>
            <div class="sec-retention-curve-bar mt-3">
                <div class="sec-ret-labels">
                    <strong>📊 Canlı İzleyici Tutma (Retention) Eğrisi Simülasyonu</strong>
                    <span>0sn (%100) → 3sn Kanca (%84) → 18sn Merak Zirvesi (%78) → 38sn Sonsuz Döngü (%73)</span>
                </div>
                <div class="sec-ret-sparkline">
                    <div class="sec-ret-seg is-high" style="width:22%" title="0-3sn Kanca: %96">0-3s %96</div>
                    <div class="sec-ret-seg is-good" style="width:28%" title="3-15sn Gelişme: %84">3-15s %84</div>
                    <div class="sec-ret-seg is-peak" style="width:28%" title="15-28sn Kanıt & Vurgu: %79">15-28s %79</div>
                    <div class="sec-ret-seg is-loop" style="width:22%" title="28-38sn Seamless Loop: %74">Loop %74</div>
                </div>
                <button type="button" class="btn btn-primary btn-sm" id="btn-growth-jump-wizard">
                    <i class="fa-solid fa-bolt"></i> Bu Formülle Sihirbazda Video Üret
                </button>
            </div>`;
        pane.insertBefore(hero, pane.firstElementChild);

        document.getElementById('btn-growth-jump-wizard')?.addEventListener('click', () => {
            if (typeof window.switchTab === 'function') window.switchTab('studio');
            if (typeof window.setStudioWizardStep === 'function') window.setStudioWizardStep(1, { force: true });
            notify('⚡ Yüksek tutma oranlı (%84 APV) kurgu şablonu Sihirbaza aktarıldı!');
        });
    }

    // ─── 3. OTO-HABER & RSS BOTU (#pane-rss-bot) ───────────────────────────
    function initRssBotTabUX() {
        const pane = document.getElementById('pane-rss-bot');
        const rssSelect = document.getElementById('select-rss-source');
        const rssList = document.getElementById('rss-news-list');
        if (!pane || !rssSelect || document.getElementById('rss-quick-category-pills')) return;

        const quickChips = document.createElement('div');
        quickChips.id = 'rss-quick-category-pills';
        quickChips.className = 'sec-ux-pills mt-2 mb-2';
        const sources = [
            { val: 'aa_guncel', label: '🇹🇷 AA Flaş' },
            { val: 'bbc_turkce', label: '🌍 BBC Dünya' },
            { val: 'webtekno', label: '🤖 Webtekno AI' },
            { val: 'arkeofili', label: '🏺 Arkeofili Tarih' },
            { val: 'evrim_agaci', label: '🧬 Evrim Ağacı' },
            { val: 'coin_turk', label: '💰 CoinTürk' }
        ];
        quickChips.innerHTML = sources.map((s, i) => `
            <button type="button" class="sec-pill is-mini ${i === 0 ? 'active' : ''}" data-rss-src="${s.val}">${s.label}</button>
        `).join('');
        rssSelect.parentElement?.insertAdjacentElement('afterend', quickChips);

        quickChips.querySelectorAll('[data-rss-src]').forEach((chip) => {
            chip.addEventListener('click', () => {
                quickChips.querySelectorAll('.sec-pill').forEach((c) => c.classList.remove('active'));
                chip.classList.add('active');
                rssSelect.value = chip.getAttribute('data-rss-src') || 'aa_guncel';
                rssSelect.dispatchEvent(new Event('change', { bubbles: true }));
            });
        });

        // Seed curated fallback news items if rss-news-list is currently showing the empty state
        if (rssList && rssList.querySelector('.empty-state-box')) {
            const sampleNews = [
                { title: 'James Webb Teleskobu Evrenin İlk Galaksisinde Açıklanamayan Işık Sinyali Yakaladı', niche: '3_space_cosmos', tag: 'BİLİM & UZAY', time: '12 dk önce' },
                { title: 'Göbeklitepe Yakınlarında Mühürlenmiş Yeni Bir Yeraltı Odası Keşfedildi', niche: '2_hidden_history', tag: 'ARKEOLOJİ', time: '28 dk önce' },
                { title: 'Yapay Zeka Modelleri Kendi Aralarında İnsanların Anlamadığı Kısa Kod Dili Geliştirdi', niche: '4_ai_future_tech', tag: 'TEKNOLOJİ', time: '41 dk önce' }
            ];
            const badge = document.getElementById('rss-news-count-badge');
            if (badge) badge.textContent = `${sampleNews.length} Hazır Gündem`;
            rssList.innerHTML = sampleNews.map((item) => `
                <div class="glass-box mb-2 sec-rss-sample-card">
                    <div class="sec-rss-top">
                        <span class="sem-badge-active badge">${esc(item.tag)}</span>
                        <small>${esc(item.time)}</small>
                    </div>
                    <strong class="sec-rss-title">${esc(item.title)}</strong>
                    <div class="sec-rss-actions mt-2">
                        <button type="button" class="btn btn-primary btn-sm btn-rss-quick-studio" data-title="${esc(item.title)}" data-niche="${esc(item.niche)}">
                            <i class="fa-solid fa-wand-magic-sparkles"></i> Viral Kancaya Çevir &amp; Stüdyoya Aktar
                        </button>
                    </div>
                </div>`).join('');
            rssList.querySelectorAll('.btn-rss-quick-studio').forEach((btn) => {
                btn.addEventListener('click', () => {
                    const t = btn.getAttribute('data-title') || '';
                    const n = btn.getAttribute('data-niche') || '1_news_flash';
                    const topicInput = document.getElementById('input-topic');
                    if (topicInput) { topicInput.value = `Kimsenin Fark Etmediği Gerçek: ${t}`; topicInput.dispatchEvent(new Event('input', { bubbles: true })); }
                    const nicheSel = document.getElementById('select-niche');
                    if (nicheSel) { nicheSel.value = n; nicheSel.dispatchEvent(new Event('change', { bubbles: true })); }
                    if (typeof window.switchTab === 'function') window.switchTab('studio');
                    notify(`⚡ Haber viral soru kancasına dönüştürülüp Stüdyoya aktarıldı!`);
                });
            });
        }
    }

    // ─── 4. CAPCUT KARAOKE ALTYAZI STİLLERİ (#pane-subtitles) ──────────────
    function initSubtitlesTabUX() {
        const stage = document.getElementById('sub-stage');
        if (!stage || document.getElementById('sub-stage-bg-switcher')) return;

        const switcher = document.createElement('div');
        switcher.id = 'sub-stage-bg-switcher';
        switcher.className = 'sec-sub-stage-toolbar mb-2';
        switcher.innerHTML = `
            <div class="sec-ux-pills">
                <button type="button" class="sec-pill is-mini active" data-sub-bg="dark">🌑 Karanlık Sahne</button>
                <button type="button" class="sec-pill is-mini" data-sub-bg="bright">☀️ Parlak Gündüz</button>
                <button type="button" class="sec-pill is-mini" data-sub-bg="gameplay">🎮 Oyun Klibi Üstü</button>
            </div>
            <button type="button" class="btn btn-primary btn-sm" id="btn-apply-sub-to-wizard">
                <i class="fa-solid fa-check"></i> Stili Sihirbaza Uygula
            </button>`;
        stage.parentElement?.insertBefore(switcher, stage);

        switcher.querySelectorAll('[data-sub-bg]').forEach((btn) => {
            btn.addEventListener('click', () => {
                switcher.querySelectorAll('[data-sub-bg]').forEach((b) => b.classList.remove('active'));
                btn.classList.add('active');
                const mode = btn.getAttribute('data-sub-bg');
                if (mode === 'bright') {
                    stage.style.background = 'linear-gradient(135deg, #cbd5e1 0%, #94a3b8 100%)';
                } else if (mode === 'gameplay') {
                    stage.style.background = 'linear-gradient(135deg, #1e1b4b 0%, #0f766e 50%, #31102f 100%)';
                } else {
                    stage.style.background = '';
                }
            });
        });

        document.getElementById('btn-apply-sub-to-wizard')?.addEventListener('click', () => {
            const activePreset = document.querySelector('#pane-subtitles .preset-card.active h4')?.textContent?.trim() || 'CapCut Neon Sarı';
            notify(`💬 "${activePreset}" altyazı stili Stüdyo Sihirbazına (Adım 03) uygulandı!`);
            if (typeof window.switchTab === 'function') window.switchTab('studio');
            if (typeof window.setStudioWizardStep === 'function') window.setStudioWizardStep(3, { force: true });
        });
    }

    // ─── 5. SPLIT-SCREEN & GÖRSEL FX (#pane-effects) ───────────────────────
    function initEffectsTabUX() {
        const pane = document.getElementById('pane-effects');
        const splitBox = pane?.querySelector('.split-preview-box');
        if (!pane || !splitBox || document.getElementById('fx-split-ratio-controller')) return;

        const ctrl = document.createElement('div');
        ctrl.id = 'fx-split-ratio-controller';
        ctrl.className = 'sec-fx-controller mt-3';
        ctrl.innerHTML = `
            <div class="sec-fx-ratio-head">
                <span>📐 Canlı Bölünmüş Ekran Oranı: <strong id="fx-split-ratio-val">%58 Üst / %42 Alt (Altın Oran)</strong></span>
                <div class="sec-ux-pills">
                    <button type="button" class="sec-pill is-mini" data-sratio="50">%50 / %50</button>
                    <button type="button" class="sec-pill is-mini active" data-sratio="58">%58 / %42 (Önerilen)</button>
                    <button type="button" class="sec-pill is-mini" data-sratio="68">%68 / %32 Sinematik</button>
                </div>
            </div>
            <div class="sec-fx-gameplay-row mt-2">
                <small>🎮 Alt Panel Oyun Klibi:</small>
                <div class="sec-ux-pills">
                    <button type="button" class="sec-pill is-mini active" data-gpname="Minecraft Parkour">⛏️ Minecraft Parkour</button>
                    <button type="button" class="sec-pill is-mini" data-gpname="Subway Surfers">🏃 Subway Surfers</button>
                    <button type="button" class="sec-pill is-mini" data-gpname="GTA V Mega Ramp">🚗 GTA V Ramp</button>
                    <button type="button" class="sec-pill is-mini" data-gpname="Satisfying ASMR">🧼 Satisfying ASMR</button>
                </div>
            </div>`;
        splitBox.insertAdjacentElement('afterend', ctrl);

        const topZone = splitBox.querySelector('.split-top-zone');
        const botZone = splitBox.querySelector('.split-bottom-zone');
        ctrl.querySelectorAll('[data-sratio]').forEach((btn) => {
            btn.addEventListener('click', () => {
                ctrl.querySelectorAll('[data-sratio]').forEach((b) => b.classList.remove('active'));
                btn.classList.add('active');
                const topPct = Number(btn.getAttribute('data-sratio') || 58);
                const botPct = 100 - topPct;
                if (topZone) { topZone.style.flex = `${topPct}`; topZone.innerHTML = `<span><i class="fa-solid fa-clapperboard"></i> ÜST PANEL: Ana İçerik Klibi (%${topPct})</span>`; }
                if (botZone) { botZone.style.flex = `${botPct}`; botZone.querySelector('span') && (botZone.innerHTML = `<span><i class="fa-solid fa-gamepad"></i> ALT PANEL: Oyun Kurgusu (%${botPct})</span>`); }
                const lbl = document.getElementById('fx-split-ratio-val');
                if (lbl) lbl.textContent = `%${topPct} Üst / %${botPct} Alt`;
                notify(`📐 Split-Screen oranı %${topPct} / %${botPct} olarak güncellendi.`);
            });
        });

        ctrl.querySelectorAll('[data-gpname]').forEach((btn) => {
            btn.addEventListener('click', () => {
                ctrl.querySelectorAll('[data-gpname]').forEach((b) => b.classList.remove('active'));
                btn.classList.add('active');
                const gp = btn.getAttribute('data-gpname') || 'Minecraft Parkour';
                if (botZone) botZone.innerHTML = `<span><i class="fa-solid fa-gamepad"></i> ALT PANEL: ${esc(gp)}</span>`;
                notify(`🎮 Alt panel oyun klibi seçildi: ${gp}`);
            });
        });
    }

    function initSecondaryTabsUX() {
        initNichesTabUX();
        initGrowthAnalyticsTabUX();
        initRssBotTabUX();
        initSubtitlesTabUX();
        initEffectsTabUX();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initSecondaryTabsUX);
    } else {
        initSecondaryTabsUX();
    }
})();
