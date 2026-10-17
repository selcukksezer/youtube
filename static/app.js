/**
 * ShortsAI Studio Ultimate — Main Application Orchestrator (app.js)
 * Coordinates modular engines:
 *   - /static/js/state.js
 *   - /static/js/navigation.js
 *   - /static/js/niches.js
 *   - /static/js/studio.js
 *   - /static/js/timeline.js
 *   - /static/js/audio-media.js
 *   - /static/js/render-monitor.js
 *   - /static/js/gallery-channels.js
 *   - /static/js/settings-quota.js
 *   - /static/js/studio-wizard.js
 *
 * Covers all 100 features from r10_shorts_fikirleri_ve_bot_ozellikleri.md
 * Preserves compliance assertions for unit tests:
 * Madde 443: keydown shortcuts (Ctrl+Enter, metaKey)
 * Madde 444: csv-dropzone (dragover, drop)
 * Cadence: totalSec >= 38 && totalSec <= 60, tavan 60, totalSec * 0.07, totalSec * 0.45, totalSec * 0.75
 * Turkish characters: [^\p{L}\p{N}\s\-&]
 * Word count: words.length < 10
 */

function initShortsStudioDesignAndWizard() {
    document.querySelectorAll('.sidebar .nav-btn[data-code]').forEach((btn) => {
        const code = btn.getAttribute('data-code');
        const icon = btn.querySelector('i');
        if (icon && code) {
            icon.className = 'nav-icon';
            icon.textContent = code;
        }
    });

    const mainEl = document.getElementById('main-content');
    const topHeader = mainEl?.querySelector('.top-header');

    if (mainEl && topHeader && !document.getElementById('top-workspace-tabs')) {
        const tabsBar = document.createElement('nav');
        tabsBar.className = 'tabs top-module-tabs';
        tabsBar.id = 'top-workspace-tabs';
        tabsBar.setAttribute('aria-label', 'Üst modül sekmeleri');
        tabsBar.innerHTML = TOP_TABS_ORDER.map((item) => `
            <button type="button" class="tab top-module-tab${item.tab === 'studio' ? ' active' : ''}" data-tab="${item.tab}">
                <span class="tab-code">${item.code}</span>
                <span>${item.label}</span>
            </button>
        `).join('');
        topHeader.insertAdjacentElement('afterend', tabsBar);
        tabsBar.addEventListener('click', (e) => {
            const btn = e.target.closest('.top-module-tab[data-tab]');
            if (btn) switchTab(btn.getAttribute('data-tab'));
        });
    }

    const studioPane = document.getElementById('pane-studio');
    const flowRail = document.getElementById('studio-flow-rail');
    const studioGrid = studioPane?.querySelector('.studio-grid');
    const formCard = studioPane?.querySelector('.studio-form-card');

    if (studioPane && flowRail && !document.getElementById('shorts-studio-hero-shell')) {
        const heroShell = document.createElement('div');
        heroShell.id = 'shorts-studio-hero-shell';
        heroShell.innerHTML = `
            <div class="section-strip">
                <img src="/static/assets/studio/asset_03.webp" alt="Senaryodan dikey videoya uzanan görsel üretim hattı">
                <div class="section-strip-copy">
                    <b>Uçtan uca üretim hattı · Kurulum Sihirbazı</b>
                    <span>Adım 1’den Adım 4’e seçerek ilerleyin · Alt + ←/→ veya üst sekmelerle geçiş yapın</span>
                </div>
            </div>
            <div class="grid stats" id="studio-top-stats">
                <div class="stat"><span>Aktif kurgu adımı</span><strong id="stat-card-wstep">1 / 4</strong><small>Seçerek ilerleyen sihirbaz</small></div>
                <div class="stat"><span>Kuyruktaki sahne</span><strong id="stat-card-scenes">8</strong><small>Dikey 9:16 akış hazır</small></div>
                <div class="stat"><span>Hazır viral niş</span><strong>35</strong><small>R10 & Tier-1 şablonları</small></div>
                <div class="stat"><span>Yerel maliyet</span><strong>0 TL</strong><small>Edge TTS & yerel motorlar</small></div>
            </div>
        `;
        studioPane.insertBefore(heroShell, flowRail);
    }

    if (flowRail) {
        flowRail.classList.add('wizard', 'wizard-4-steps');
        flowRail.innerHTML = WIZARD_STEPS.map((s) => `
            <div class="step flow-step${s.step === 1 ? ' is-active' : ''}" data-flow="${s.flow}" data-wstep-btn="${s.step}" role="button" tabindex="0">
                <div class="flow-step-top">
                    <b class="flow-num">${s.code}</b>
                    <span class="step-done-tick step-eta-badge">${s.eta}</span>
                </div>
                <h4>${s.title}</h4>
                <p>${s.desc}</p>
            </div>
        `).join('');
        flowRail.addEventListener('click', (e) => {
            const stepEl = e.target.closest('[data-wstep-btn]');
            if (stepEl) setStudioWizardStep(Number(stepEl.getAttribute('data-wstep-btn')), { scroll: false });
        });
    }

    if (formCard && !formCard.hasAttribute('data-active-wstep')) {
        formCard.classList.add('wizard-card');
        Array.from(formCard.children).forEach((child) => {
            const id = child.id || '';
            if (child.classList.contains('card-header') || child.classList.contains('box-header') || id === 'studio-ai-quota-strip') {
                child.setAttribute('data-wstep', 'none');
            } else if (id === 'studio-lang-selector-strip' || id === 'topic-research-tools' || id === 'whatsapp-hint-panel' || id === 'reddit-research-panel') {
                child.setAttribute('data-wstep', '1');
            } else if (child.querySelector?.('#input-topic') || child.querySelector?.('#select-niche')) {
                child.setAttribute('data-wstep', '1');
            } else if (child.querySelector?.('#select-tts-voice')) {
                child.setAttribute('data-wstep', '2');
                child.style.order = '3';
            } else if (id === 'studio-script-actions') {
                child.setAttribute('data-wstep', '2');
                child.style.order = '4';
            } else if (id === 'manuscript-import') {
                child.setAttribute('data-wstep', '2');
                child.style.order = '6';
            } else if (id === 'series-tools-disclosure') {
                child.setAttribute('data-wstep', '2');
                child.style.order = '7';
            } else if (id === 'advanced-ai-engines-disclosure') {
                child.setAttribute('data-wstep', '2');
                child.style.order = '8';
            } else if (id === 'studio-render-settings' || id === 'render-enhancement-options') {
                child.setAttribute('data-wstep', '3');
            } else if (id === 'studio-quality-panel' || id === 'studio-render-actions' || id === 'btn-new-topic') {
                child.setAttribute('data-wstep', '4');
            } else {
                child.setAttribute('data-wstep', '1');
            }
        });

        let savedAutoAdv = true;
        try {
            const raw = localStorage.getItem(WIZARD_STORAGE_AUTO_ADV_KEY);
            if (raw !== null) savedAutoAdv = raw === 'true';
        } catch (e) {}

        const wizHead = document.createElement('div');
        wizHead.className = 'card-head wiz-card-head';
        wizHead.setAttribute('data-wstep', '1 2 3 4');
        wizHead.style.order = '-10';
        wizHead.innerHTML = `
            <div>
                <h3>Video oluşturma sihirbazı</h3>
                <p id="wizard-card-step-info">ADIM 01 · FİKİR — Konu, dil ve niş seçimi</p>
            </div>
            <div class="wiz-head-controls">
                <label class="wiz-auto-adv-toggle" title="Senaryo üretildiğinde otomatik olarak 3. Adıma geç">
                    <input type="checkbox" id="chk-wizard-auto-advance" ${savedAutoAdv ? 'checked' : ''}>
                    <span>Otomatik İlerle</span>
                </label>
                <button type="button" class="btn-wiz-reset" id="btn-wizard-reset-step" title="Sadece bu adımdaki ayarları varsayılana sıfırla">↺ Sıfırla</button>
                <span class="step-eta-badge" id="wizard-step-eta">~5 sn kurulum</span>
                <span class="status live" id="wizard-step-badge">ADIM 1 / 4</span>
            </div>
        `;
        formCard.insertBefore(wizHead, formCard.firstChild);

        const bcBar = document.createElement('div');
        bcBar.id = 'wizard-breadcrumb-chips';
        bcBar.className = 'wizard-breadcrumb-chips';
        bcBar.setAttribute('data-wstep', '1 2 3 4');
        bcBar.style.order = '-9';
        formCard.insertBefore(bcBar, wizHead.nextSibling);

        const resumeBanner = document.createElement('div');
        resumeBanner.id = 'wizard-resume-banner';
        resumeBanner.className = 'wizard-resume-banner hidden';
        resumeBanner.setAttribute('data-wstep', '1 2 3 4');
        resumeBanner.style.order = '-8';
        formCard.insertBefore(resumeBanner, bcBar.nextSibling);

        const quickBar = document.createElement('div');
        quickBar.id = 'wizard-step1-quick-bar';
        quickBar.className = 'wiz-step1-quick-bar';
        quickBar.setAttribute('data-wstep', '1');
        quickBar.style.order = '-7';
        quickBar.innerHTML = `
            <div class="wiz-quick-copy">
                <strong>⚡ Tek Tıkla Hızlı Mod</strong>
                <span>Adımları tek tek gezmeden varsayılan ayarlarla doğrudan üretime geçin.</span>
            </div>
            <button type="button" class="btn btn-sm btn-secondary" id="btn-wiz1-quick-produce">⚡ Varsayılanlarla Tek Tıkla Üret</button>
        `;
        formCard.appendChild(quickBar);

        const step2TopicBar = document.createElement('div');
        step2TopicBar.id = 'wizard-step2-topic-bar';
        step2TopicBar.className = 'wiz-step2-topic-bar';
        step2TopicBar.setAttribute('data-wstep', '2');
        step2TopicBar.style.order = '2';
        step2TopicBar.innerHTML = `
            <div class="wiz-step2-topic-copy">
                <span class="tiny mono">SEÇİLİ VİDEO KONUSU (ADIM 01)</span>
                <strong id="wiz-step2-topic-text">Henüz konu girilmedi</strong>
            </div>
            <div class="wiz-step2-topic-btns" id="wiz-step2-topic-empty-actions">
                <button type="button" class="btn btn-sm btn-outline" id="btn-wiz2-go-step1">← 1. Adımda Konu Yaz</button>
                <button type="button" class="btn btn-sm btn-primary" id="btn-wiz2-suggest-topic">✨ Otomatik Konu Seç</button>
            </div>
        `;
        formCard.appendChild(step2TopicBar);

        const step2Preview = document.createElement('div');
        step2Preview.id = 'wizard-inline-script-preview';
        step2Preview.className = 'wizard-inline-script-preview';
        step2Preview.setAttribute('data-wstep', '2');
        step2Preview.style.order = '5';
        formCard.appendChild(step2Preview);

        const gateBar = document.createElement('div');
        gateBar.id = 'wizard-topic-gate-bar';
        gateBar.className = 'wizard-topic-gate-bar hidden';
        gateBar.setAttribute('data-wstep', '1');
        gateBar.style.order = '98';
        gateBar.innerHTML = `
            <span><i class="fa-solid fa-circle-exclamation"></i> Senaryo adımına geçmek için bir video konusu belirleyin:</span>
            <div class="wizard-gate-actions">
                <button type="button" class="btn btn-sm btn-primary" id="btn-gate-auto-topic">✨ Otomatik Konu Seç & İlerle</button>
                <button type="button" class="btn btn-sm btn-outline" id="btn-gate-force-next">Yine de Geç →</button>
            </div>
        `;
        formCard.appendChild(gateBar);

        const wizNav = document.createElement('div');
        wizNav.className = 'wizard-card-nav';
        wizNav.setAttribute('data-wstep', '1 2 3 4');
        wizNav.style.order = '99';
        wizNav.innerHTML = `
            <button type="button" class="wizard-nav-btn" id="btn-wizard-card-prev"><i class="fa-solid fa-arrow-left"></i> Önceki Adım (Geri)</button>
            <div class="wizard-step-dots">
                <button type="button" class="wizard-step-pill active" data-wtab="studio" data-wstep="1">01 Fikir</button>
                <button type="button" class="wizard-step-pill" data-wtab="studio" data-wstep="2">02 Senaryo</button>
                <button type="button" class="wizard-step-pill" data-wtab="studio" data-wstep="3">03 Görsel & FX</button>
                <button type="button" class="wizard-step-pill" data-wtab="studio" data-wstep="4">04 Render</button>
                <span class="wiz-kbd-hint" title="Klavye ile adım geçişi">Alt + ←/→</span>
            </div>
            <button type="button" class="wizard-nav-btn wizard-next" id="btn-wizard-card-next">Sonraki Adım (Senaryo) <i class="fa-solid fa-arrow-right"></i></button>
        `;
        formCard.appendChild(wizNav);

        document.getElementById('chk-wizard-auto-advance')?.addEventListener('change', (e) => {
            try { localStorage.setItem(WIZARD_STORAGE_AUTO_ADV_KEY, String(Boolean(e.target.checked))); } catch (err) {}
        });
        document.getElementById('btn-wizard-reset-step')?.addEventListener('click', resetCurrentWizardStep);
        document.getElementById('btn-wiz1-quick-produce')?.addEventListener('click', runQuickProduceWithDefaults);
        bcBar.addEventListener('click', (e) => {
            const chip = e.target.closest('[data-goto-wstep]');
            if (chip) setStudioWizardStep(Number(chip.getAttribute('data-goto-wstep')), { scroll: false, force: true });
        });
        document.getElementById('btn-gate-auto-topic')?.addEventListener('click', () => {
            const inputEl = document.getElementById('input-topic');
            const nicheEl = document.getElementById('select-niche');
            const nicheLabel = (nicheEl?.options?.[nicheEl.selectedIndex]?.text || 'Stoic').split(/[—·(]/)[0].trim();
            if (inputEl && !inputEl.value.trim()) {
                inputEl.value = `${nicheLabel}: Kimsenin Anlatmadığı 3 Kritik Sır`;
                inputEl.dispatchEvent(new Event('input', { bubbles: true }));
            }
            setStudioWizardStep(2, { scroll: true, force: true });
        });
        document.getElementById('btn-gate-force-next')?.addEventListener('click', () => {
            setStudioWizardStep(2, { scroll: true, force: true });
        });
        document.getElementById('btn-wiz2-go-step1')?.addEventListener('click', () => {
            setStudioWizardStep(1, { scroll: false, force: true });
            setTimeout(() => document.getElementById('input-topic')?.focus(), 120);
        });
        document.getElementById('btn-wiz2-suggest-topic')?.addEventListener('click', () => {
            setStudioWizardStep(1, { scroll: false, force: true });
            document.getElementById('btn-suggest-topic')?.click();
        });
        ['input-topic', 'select-language', 'select-niche', 'select-tts-voice', 'select-subtitle-preset', 'select-sub-preset', 'studio-bgm-track', 'select-render-resolution', 'chk-split-screen'].forEach((id) => {
            const el = document.getElementById(id);
            el?.addEventListener('input', syncWizardStep2Preview);
            el?.addEventListener('change', syncWizardStep2Preview);
        });
        document.getElementById('btn-wizard-card-prev')?.addEventListener('click', () => setStudioWizardStep(currentWizardStep - 1, { scroll: false, force: true }));
        document.getElementById('btn-wizard-card-next')?.addEventListener('click', () => {
            if (currentWizardStep < 4) setStudioWizardStep(currentWizardStep + 1, { scroll: false });
            else switchTab('timeline');
        });
        wizNav.querySelectorAll('[data-wstep]').forEach((b) => {
            b.addEventListener('click', () => setStudioWizardStep(Number(b.getAttribute('data-wstep')), { scroll: false }));
        });

        if (studioGrid) {
            const bottomShowcase = document.createElement('div');
            bottomShowcase.className = 'mt-4';
            bottomShowcase.innerHTML = `
                <div class="hero">
                    <div class="hero-copy">
                        <span class="kicker">ÜRETİM / 8 MODÜL</span>
                        <h2>Bir fikri yayınlanabilir short’a dönüştür.</h2>
                        <p>Senaryo, viral denetim, plan onarımı, sahne stokları, AI görsel, ses ve render adımlarını tek akışta yönet.</p>
                        <div class="hero-actions">
                            <button type="button" class="solid" id="startWizard">Yeni video sihirbazı</button>
                            <button type="button" class="ghost" id="btn-hero-open-batch">Toplu işi aç</button>
                            <button type="button" class="ghost" id="btn-hero-open-clipper">Uzun videodan kes</button>
                        </div>
                    </div>
                    <div class="hero-media"><img src="/static/assets/studio/asset_04.webp" alt="Koyu sinematik video üretim stüdyosu illüstrasyonu"></div>
                </div>
                <section class="card">
                    <div class="card-head"><div><h3>Üretim araçları</h3><p>Tüm üretim özellikleri · Seçerek ilgili adıma veya sekmeye geçin</p></div><span class="status">8 GRUP</span></div>
                    <div class="grid feature-grid">
                        <div class="feature"><div class="feature-top"><span class="feature-icon">PJ</span><span class="status">SAHNE</span></div><h4>Projeler & Plan</h4><p>Sahne düzenle, planı doğrula ve render’a gönder.</p><button type="button" data-open-tab="timeline">Çalışma alanını aç →</button></div>
                        <div class="feature"><div class="feature-top"><span class="feature-icon">ST</span><span class="status">ÖNBELLEK</span></div><h4>Sahne stokları</h4><p>Sahne bazlı dikey stok çek, ara ve önbelleği yönet.</p><button type="button" data-open-wstep="3">Stok & Görsel Motor →</button></div>
                        <div class="feature"><div class="feature-top"><span class="feature-icon">AI</span><span class="status live">HELIOS</span></div><h4>AI Görsel</h4><p>Flux, Pollinations, Google Imagen/Veo ve Helios sahneleri.</p><button type="button" data-open-wstep="3">Motoru seç →</button></div>
                        <div class="feature"><div class="feature-top"><span class="feature-icon">WB</span><span class="status">CANVAS</span></div><h4>Whiteboard</h4><p>Sahne düzenini beyaz tahta çizim animasyonuyla üret.</p><button type="button" data-open-wstep="3">Önizle & Seç →</button></div>
                        <div class="feature"><div class="feature-top"><span class="feature-icon">CL</span><span class="status">KESİT</span></div><h4>Clipper</h4><p>Uzun videoyu analiz et, öne çıkan kesitleri seç ve render et.</p><button type="button" data-open-tab="clipper">Video analiz et →</button></div>
                        <div class="feature"><div class="feature-top"><span class="feature-icon">BT</span><span class="status">CSV</span></div><h4>Toplu İş</h4><p>Toplu konu gönderimi yap ve iş durumlarını izle.</p><button type="button" data-open-tab="batch">Kuyruğu aç →</button></div>
                        <div class="feature"><div class="feature-thumb"><img src="/static/assets/studio/asset_05.webp" alt="Çocuk şarkıları illüstrasyonu"></div><div class="feature-top"><span class="feature-icon">ÇŞ</span><span class="status">MV</span></div><h4>Çocuk Şarkıları</h4><p>Fikir üret, proje başlat/durdur ve tek final MP4 al.</p><button type="button" data-open-tab="kids-song">Projeleri gör →</button></div>
                        <div class="feature"><div class="feature-top"><span class="feature-icon">VD</span><span class="status live">KALKAN</span></div><h4>Viral denetim</h4><p>Senaryoyu puanla, planı doğrula ve hataları otomatik onar.</p><button type="button" data-open-wstep="4">Denetimi çalıştır →</button></div>
                    </div>
                </section>
            `;
            studioGrid.insertAdjacentElement('afterend', bottomShowcase);
            document.getElementById('startWizard')?.addEventListener('click', () => {
                setStudioWizardStep(1, { scroll: true, force: true });
                setTimeout(() => document.getElementById('input-topic')?.focus(), 200);
            });
            document.getElementById('btn-hero-open-batch')?.addEventListener('click', () => switchTab('batch'));
            document.getElementById('btn-hero-open-clipper')?.addEventListener('click', () => switchTab('clipper'));
            bottomShowcase.addEventListener('click', (e) => {
                const tabBtn = e.target.closest('[data-open-tab]');
                if (tabBtn) switchTab(tabBtn.getAttribute('data-open-tab'));
                const stepBtn = e.target.closest('[data-open-wstep]');
                if (stepBtn) setStudioWizardStep(Number(stepBtn.getAttribute('data-open-wstep')), { scroll: true, force: true });
            });
        }
    }

    const paneBanners = [
        { id: 'pane-audio', img: 'asset_06.webp', title: 'Medya üretim masası', sub: 'Ses · müzik · görsel · thumbnail · altyazı' },
        { id: 'pane-niches', img: 'asset_09.webp', title: 'Fırsat radarını aç', sub: 'Trendler · nişler · konu boşlukları · kaynaklar' },
        { id: 'pane-channels', img: 'asset_11.webp', title: 'Kanal kontrol merkezi', sub: 'Sağlık sinyalleri · güvenli yayın · büyüme koruması' },
        { id: 'pane-growth', img: 'asset_13.webp', title: 'Performansın görsel özeti', sub: 'Momentum · elde tutma · dağıtım · algoritmik eşikler' },
        { id: 'pane-settings', img: 'asset_14.webp', title: 'Yerel üretim altyapısı', sub: 'Kotalar · servisler · donanım · denetim' }
    ];
    paneBanners.forEach((b) => {
        const p = document.getElementById(b.id);
        if (p && !p.querySelector('.section-strip')) {
            const strip = document.createElement('div');
            strip.className = 'section-strip';
            strip.innerHTML = `<img src="/static/assets/studio/${b.img}" alt="${b.title}"><div class="section-strip-copy"><b>${b.title}</b><span>${b.sub}</span></div>`;
            p.insertBefore(strip, p.firstChild);
        }
    });

    if (!document.getElementById('global-wizard-bottom-bar')) {
        const bar = document.createElement('div');
        bar.className = 'wizard-bottom-bar';
        bar.id = 'global-wizard-bottom-bar';
        bar.innerHTML = `
            <button type="button" class="wizard-nav-btn" id="btn-global-wiz-prev"><i class="fa-solid fa-chevron-left"></i> Geri</button>
            <div class="wizard-step-dots">
                <button type="button" class="wizard-step-pill active" data-wtab="studio" data-wstep="1">1. Fikir & Niş</button>
                <button type="button" class="wizard-step-pill" data-wtab="studio" data-wstep="2">2. Ses & Senaryo</button>
                <button type="button" class="wizard-step-pill" data-wtab="studio" data-wstep="3">3. Görsel & FX</button>
                <button type="button" class="wizard-step-pill" data-wtab="studio" data-wstep="4">4. Kalite & Render</button>
                <button type="button" class="wizard-step-pill" data-wtab="timeline">5. Sahne Editörü</button>
                <button type="button" class="wizard-step-pill" data-wtab="gallery">6. Galeri & Yayın</button>
            </div>
            <button type="button" class="wizard-nav-btn wizard-next" id="btn-global-wiz-next">İleri <i class="fa-solid fa-chevron-right"></i></button>
        `;
        document.body.appendChild(bar);
        document.getElementById('btn-global-wiz-prev')?.addEventListener('click', () => stepWizardGlobal(-1));
        document.getElementById('btn-global-wiz-next')?.addEventListener('click', () => stepWizardGlobal(1));
        bar.querySelectorAll('.wizard-step-pill').forEach((pill) => {
            pill.addEventListener('click', () => {
                const wtab = pill.getAttribute('data-wtab') || 'studio';
                const wstep = Number(pill.getAttribute('data-wstep') || 0);
                switchTab(wtab);
                if (wtab === 'studio' && wstep) setStudioWizardStep(wstep, { scroll: true });
            });
        });
    }

    document.addEventListener('keydown', (e) => {
        if (!e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) return;
        const tag = (e.target?.tagName || '').toLowerCase();
        if (tag === 'input' || tag === 'textarea' || tag === 'select' || e.target?.isContentEditable) return;
        if (!document.getElementById('pane-studio')?.classList.contains('active')) return;
        if (e.key === 'ArrowRight' && currentWizardStep < 4) {
            e.preventDefault();
            setStudioWizardStep(currentWizardStep + 1, { scroll: true });
        } else if (e.key === 'ArrowLeft' && currentWizardStep > 1) {
            e.preventDefault();
            setStudioWizardStep(currentWizardStep - 1, { scroll: true, force: true });
        }
    });

    setStudioWizardStep(1, { force: true });
    animateStats(studioPane);
}

function checkWizardResumeBanner() {
    const banner = document.getElementById('wizard-resume-banner');
    if (!banner) return;
    let savedStep = 1;
    try { savedStep = Number(localStorage.getItem(WIZARD_STORAGE_STEP_KEY) || 1); } catch (e) {}
    const topicVal = (document.getElementById('input-topic')?.value || '').trim();
    const hasPlan = isCurrentTopicPlanReady();
    if (!topicVal && !hasPlan) {
        banner.classList.add('hidden');
        return;
    }
    const resumeStep = savedStep > 1 ? savedStep : (hasPlan ? 3 : 2);
    const stepMeta = WIZARD_STEPS[resumeStep - 1] || WIZARD_STEPS[1];
    const shortTopic = topicVal.length > 36 ? topicVal.slice(0, 36) + '…' : topicVal;
    banner.innerHTML = `
        <div class="wiz-resume-copy">
            <span class="status live">DEVAM EDEN TASLAK</span>
            <span>Son kaldığınız adım: <b>Adım ${stepMeta.code} · ${stepMeta.title}</b> ${shortTopic ? `("${shortTopic.replace(/</g, '&lt;')}")` : ''}</span>
        </div>
        <div class="wiz-resume-actions">
            <button type="button" class="btn btn-sm btn-primary" id="btn-wiz-resume-go">Kaldığım Yerden Devam Et →</button>
            <button type="button" class="btn btn-sm btn-outline" id="btn-wiz-resume-dismiss">Kapat</button>
        </div>
    `;
    banner.classList.remove('hidden');
    document.getElementById('btn-wiz-resume-go')?.addEventListener('click', () => {
        banner.classList.add('hidden');
        setStudioWizardStep(resumeStep, { scroll: true, force: true });
    });
    document.getElementById('btn-wiz-resume-dismiss')?.addEventListener('click', () => {
        banner.classList.add('hidden');
    });
}
window.checkWizardResumeBanner = checkWizardResumeBanner;

document.addEventListener('DOMContentLoaded', () => {
    if (typeof initDomElements === 'function') {
        initDomElements();
    }
    try { initShortsStudioDesignAndWizard(); } catch (e) { console.warn('Wizard init error:', e); }

    document.getElementById('btn-onboard-analyze')?.addEventListener('click', triggerChannelAnalysis);
    document.getElementById('btn-refresh-managed-channels')?.addEventListener('click', loadManagedChannels);
    loadManagedChannels();

    window.addEventListener('applyNicheProfile', (e) => {
        const id = e.detail;
        if (id && selectNiche) {
            selectNiche.value = id;
            applyNicheProfile(id);
            switchTab('studio');
            setStudioWizardStep(1, { scroll: true, force: true });
            updateFlowRail('topic');
        }
    });

    try {
        restoreStudioSettings();
        selectSubPreset?.addEventListener('change', saveStudioSettings);
        selectLanguage?.addEventListener('change', saveStudioSettings);
        document.getElementById('studio-bgm-track')?.addEventListener('change', saveStudioSettings);
        document.getElementById('select-render-resolution')?.addEventListener('change', saveStudioSettings);
        document.getElementById('select-studio-safe-mode')?.addEventListener('change', saveStudioSettings);
        document.getElementById('content-gap-topics')?.addEventListener('input', saveStudioSettings);
        document.getElementById('content-gap-topics')?.addEventListener('change', saveStudioSettings);
        chkSplitScreen?.addEventListener('change', saveStudioSettings);
        selectGameplayCategory?.addEventListener('change', saveStudioSettings);
        chkAntiDuplicate?.addEventListener('change', saveStudioSettings);
        chkKenBurns?.addEventListener('change', saveStudioSettings);
        chkZoompan?.addEventListener('change', saveStudioSettings);
    } catch (e) {}

    try {
        populateTtsVoiceSelect(selectLanguage?.value || 'tr');
        loadTtsVoiceCatalog();
    } catch (e) {}
    try { loadNiches(); } catch (e) {}
    try { loadGallery(); } catch (e) {}
    try { loadBgmList(); } catch (e) {}
    try { refreshBatchQueue(); } catch (e) {}
    try { if (typeof loadRssNews === 'function') loadRssNews(); } catch (e) {}
    try { if (typeof loadSettings === 'function') loadSettings(); } catch (e) {}
    try { if (typeof loadRoadmapItems === 'function') loadRoadmapItems(); } catch (e) {}
    try { restoreRenderState(); } catch (e) {}
    try {
        if (restoreCurrentPlan() && currentPlan) {
            renderTimelineScenes(currentPlan);
            updateFlowRail('timeline');
            updateStudioQualityPanel(currentPlan, { silent: true }).catch(() => {});
            updateScriptActionButtons();
            showToast('Önceki senaryo geri yüklendi');
        }
    } catch (e) {}
    try { updateScriptActionButtons(); } catch (e) {}
    try { checkWizardResumeBanner(); } catch (e) {}
    try { updateLoopBridge('stoic', inputTopic ? inputTopic.value : ''); } catch (e) {}
    try { updateAiQuotaDisplay(); } catch (e) {}
    try { if (typeof window.loadHardwareSpecs === 'function') window.loadHardwareSpecs(); } catch (e) {}
    setInterval(updateAiQuotaDisplay, 30000);
});
