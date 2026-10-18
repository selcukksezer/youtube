/**
 * Shorts Studio — Category D (Items 31–40): Step 03 Visual Engines, BGM & FX UX Controller
 * Implements:
 *  31. Visual Engine Selector Cards (#wiz-visual-engine-cards)
 *  32. BGM Mood Chips with Instant Audio Preview (#wiz-bgm-mood-chips)
 *  33. BGM / Narration Auto-Ducking Decibel Balance Slider (#wiz-ducking-balance-bar)
 *  34. Live Visual Subtitle Style Selector (#wiz-step3-subtitle-cards)
 *  35. Subtitle Safe-Zone Position Guide (#wiz-subtitle-safezone-picker)
 *  36. One-Click Split-Screen Gameplay Selector Cards (#wiz-split-screen-cards)
 *  37. Quick Visual FX Preset Bundles (#wiz-fx-quick-bundles)
 *  38. Scene Transition Hover Preview Strip (#wiz-transition-preview-strip)
 *  39. Automatic SFX Intensity 3-Way Selector (#wiz-sfx-intensity-bar)
 *  40. Channel Watermark / @handle Corner Pinning (#wiz-watermark-bar)
 */

const WIZ_STEP3_PREFS_KEY = 'shorts_step3_visual_fx_v1';

const VISUAL_ENGINE_CARDS = [
    { val: 'auto', icon: '🎬', title: 'Akıllı Hibrit Stok', sub: 'Pexels / Pixabay 9:16', badge: 'Önerilen · 0 TL' },
    { val: 'flux', icon: '🤖', title: 'AI Görsel (Flux)', sub: 'Pollinations SDXL + Ken Burns', badge: 'AI Sanatı · 0 TL' },
    { val: 'mixed', icon: '🎥', title: 'AI Video + Hibrit', sub: 'Kanca AI (Veo/Helios) + Stok', badge: 'Sinematik' },
    { val: 'whiteboard', icon: '✏️', title: 'Whiteboard Çizim', sub: 'El Çizimi Line-Art Animasyon', badge: 'Eğitici · 0 TL' }
];

const BGM_MOOD_PRESETS = [
    { id: 'tension', label: '⚡ Gerilim & Gizem', freq: [146.8, 174.6, 220.0], match: ['tension', 'mystery', 'suspense', 'dark_pulse'] },
    { id: 'epic', label: '🏛️ Sinematik Epik', freq: [130.8, 196.0, 261.6], match: ['epic', 'stoic', 'cinematic', 'heroic'] },
    { id: 'lofi', label: '🎧 Lo-Fi Odak', freq: [220.0, 277.2, 329.6], match: ['lofi', 'chill', 'study', 'ambient'] },
    { id: 'dark', label: '🌑 Korku Atmosferi', freq: [110.0, 116.5, 164.8], match: ['horror', 'dark', 'drone', 'creepy'] },
    { id: 'upbeat', label: '🔥 Hızlı Tempo', freq: [261.6, 329.6, 392.0], match: ['upbeat', 'fast', 'phonk', 'energetic'] }
];

const SUBTITLE_QUICK_CARDS = [
    { id: 'capcut_yellow', title: 'Hormozi Sarı-Beyaz', sample: 'ZİHNİNİ <span style="color:#ffd700">KONTROL</span> ET', badge: 'En Yüksek Tutundurma' },
    { id: 'mrbeast_style', title: 'MrBeast Kalın Kutu', sample: '<span style="background:#facc15;color:#111;padding:1px 5px;border-radius:3px">5 GERÇEK</span> BİLGİ', badge: 'Viral Hype' },
    { id: 'cinematic_minimal', title: 'Minimalist Sinematik', sample: 'SESSİZ <span style="color:#e2e8f0;font-weight:400">DİSİPLİN</span>', badge: 'Stoa & Belgesel' },
    { id: 'cyber_green', title: 'Neon Karaoke', sample: 'YAPAY <span style="color:#4ade80;text-shadow:0 0 8px #4ade80">ZEKÂ</span> ÇAĞI', badge: 'Teknoloji & Finans' }
];

const SPLIT_SCREEN_CARDS = [
    { id: 'off', icon: '📱', title: 'Tam Ekran 9:16', sub: 'Bölünmüş ekran kapalı' },
    { id: 'minecraft_parkour', icon: '⛏️', title: 'Minecraft Parkur', sub: 'Yüksek dikkat tutucu' },
    { id: 'gta_car_ramp', icon: '🏎️', title: 'GTA V Rampası', sub: 'Hızlı aksiyon akışı' },
    { id: 'subway_surfers_style', icon: '🏃', title: 'Subway Surfers', sub: 'Klasik viral alt akış' },
    { id: 'asmr_kinetic_sand', icon: '⏳', title: 'Kinetik Kum ASMR', sub: 'Tatmin edici kesim' },
    { id: 'soap_cutting', icon: '🧼', title: 'Sabun Kesme', sub: 'Rahatlatıcı görsel döngü' }
];

const FX_BUNDLES = [
    {
        id: 'clean_cinematic',
        label: '🎬 Temiz Sinematik',
        desc: 'Kanca kartı + Ken Burns + Whisper hizalama',
        on: ['chk-hook-card', 'chk-ken-burns', 'chk-anti-duplicate', 'chk-whisper-align']
    },
    {
        id: 'dark_doc',
        label: '🌑 Karanlık Belgesel',
        desc: 'Zoompan kamera + B-Roll + Vurgu kartı + Ses spektrumu',
        on: ['chk-hook-card', 'chk-ken-burns', 'chk-zoompan', 'chk-broll-insert', 'chk-emphasis-card', 'chk-audio-visualizer', 'chk-anti-duplicate', 'chk-whisper-align']
    },
    {
        id: 'high_contrast_viral',
        label: '⚡ Yüksek Kontrast Viral',
        desc: 'Split-screen + B-Roll + Vurgu kartı + Hızlı kamera',
        on: ['chk-hook-card', 'chk-split-screen', 'chk-zoompan', 'chk-broll-insert', 'chk-emphasis-card', 'chk-center-face', 'chk-anti-duplicate', 'chk-whisper-align']
    },
    {
        id: 'vhs_news_retro',
        label: '📼 VHS Retro & Haber',
        desc: 'Canlı haber bandı (Ticker) + Ses spektrumu + Kanca kartı',
        on: ['chk-hook-card', 'chk-ken-burns', 'chk-news-ticker', 'chk-audio-visualizer', 'chk-anti-duplicate']
    }
];

const TRANSITION_STYLES = [
    { id: 'whip_pan', label: '⚡ Whip Pan', desc: 'Hızlı yatay savrulma', animClass: 'anim-whip' },
    { id: 'glitch', label: '📺 Glitch Kesme', desc: 'Siber RGB kayması', animClass: 'anim-glitch' },
    { id: 'zoom_punch', label: '🔍 Dinamik Zoom', desc: 'Merkeze ani yaklaşma', animClass: 'anim-zoom' },
    { id: 'flash_cut', label: '📸 Beyaz Flash', desc: 'Parlak kare geçişi', animClass: 'anim-flash' }
];

function getStep3Prefs() {
    try {
        return JSON.parse(localStorage.getItem(WIZ_STEP3_PREFS_KEY) || '{}') || {};
    } catch (e) {
        return {};
    }
}

function saveStep3Prefs(patch) {
    const next = { ...getStep3Prefs(), ...patch };
    try { localStorage.setItem(WIZ_STEP3_PREFS_KEY, JSON.stringify(next)); } catch (e) {}
    return next;
}

function playBgmMoodChord(freqs) {
    try {
        const Ctx = window.AudioContext || window.webkitAudioContext;
        if (!Ctx) return;
        const ctx = new Ctx();
        (freqs || [196, 246.9, 293.6]).forEach((f, idx) => {
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.type = idx === 0 ? 'triangle' : 'sine';
            osc.frequency.setValueAtTime(f, ctx.currentTime);
            gain.gain.setValueAtTime(0.001, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.09, ctx.currentTime + 0.08);
            gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.75);
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.start();
            osc.stop(ctx.currentTime + 0.78);
        });
    } catch (e) {}
}

function syncPhoneMockupStep3Overlays() {
    const prefs = getStep3Prefs();
    const videoArea = document.getElementById('phone-video-area');
    if (!videoArea) return;

    // Item 40: Watermark badge on 9:16 Phone Preview (unified with #phone-watermark-badge)
    let wmBadge = document.getElementById('mockup-watermark-badge');
    if (!wmBadge) {
        wmBadge = document.createElement('div');
        wmBadge.id = 'mockup-watermark-badge';
        wmBadge.className = 'mockup-watermark-badge hidden';
        videoArea.appendChild(wmBadge);
    }
    const wmEnabled = prefs.watermarkEnabled !== false && Boolean((prefs.watermarkText || '@shortsstudio').trim());
    wmBadge.classList.add('hidden');
    wmBadge.setAttribute('data-pos', prefs.watermarkPos || 'top-right');
    wmBadge.textContent = (prefs.watermarkText || '@shortsstudio').trim();
    const unifiedWm = document.getElementById('phone-watermark-badge');
    const unifiedWmText = document.getElementById('phone-wm-text');
    if (unifiedWmText && prefs.watermarkText) {
        unifiedWmText.textContent = prefs.watermarkText.trim();
    }
    if (unifiedWm && !wmEnabled) {
        unifiedWm.classList.add('wm-hidden');
    }

    // Item 35: Safe-Zone vertical alignment on 9:16 Phone Preview
    const subOverlay = document.getElementById('mockup-sub-overlay');
    const yVal = parseFloat(document.getElementById('sub-range-y')?.value || prefs.safeZoneY || '0.76');
    if (subOverlay && !subOverlay.classList.contains('sub-pos-top') && !subOverlay.classList.contains('sub-pos-middle') && !subOverlay.classList.contains('sub-pos-bottom')) {
        const bottomPx = yVal <= 0.65 ? 118 : (yVal >= 0.82 ? 52 : 82);
        subOverlay.style.bottom = `${bottomPx}px`;
    }

    // Item 36: Split-Screen visual indicator on 9:16 Phone Preview
    let splitBadge = document.getElementById('mockup-split-preview-pill');
    if (!splitBadge) {
        splitBadge = document.createElement('div');
        splitBadge.id = 'mockup-split-preview-pill';
        splitBadge.className = 'mockup-split-preview-pill hidden';
        videoArea.appendChild(splitBadge);
    }
    const splitOn = Boolean(document.getElementById('chk-split-screen')?.checked);
    const gpCat = document.getElementById('select-gameplay-category')?.value || 'minecraft_parkour';
    const gpCard = SPLIT_SCREEN_CARDS.find((c) => c.id === gpCat) || SPLIT_SCREEN_CARDS[1];
    splitBadge.classList.toggle('hidden', !splitOn);
    if (splitOn) {
        splitBadge.innerHTML = `<span>${gpCard.icon} ALT EKRAN: ${gpCard.title.toUpperCase()}</span>`;
    }
}

function injectStep3RenderSettingsEnhancements() {
    const settingsBody = document.querySelector('#studio-render-settings .studio-render-settings__body');
    if (!settingsBody || document.getElementById('wiz-step3-ux-hub')) return;

    const prefs = getStep3Prefs();
    const hub = document.createElement('div');
    hub.id = 'wiz-step3-ux-hub';
    hub.className = 'wiz-step3-ux-hub';

    const curEngine = document.getElementById('select-visual-engine')?.value || 'auto';
    const curSub = document.getElementById('select-subtitle-preset')?.value || 'capcut_yellow';
    const curDuck = Math.round(parseFloat(document.getElementById('range-ducking-vol')?.value || prefs.duckingVol || '0.12') * 100);
    const curSafeY = String(prefs.safeZoneY || '0.76');
    const curSfx = prefs.sfxIntensity || 'balanced';
    const curTrans = prefs.transitionStyle || 'whip_pan';
    const curWmText = prefs.watermarkText || '@shortsstudio';
    const curWmPos = prefs.watermarkPos || 'top-right';
    const curWmOn = prefs.watermarkEnabled !== false;

    hub.innerHTML = `
        <!-- Item 31: Görsel Motor Seçici Kartları -->
        <div class="wiz-s3-block">
            <div class="wiz-s3-head">
                <span><i class="fa-solid fa-film text-warning"></i> 31 · Görsel Sahne Motoru Seçimi</span>
                <small>Sahne videolarının üretim kaynağı</small>
            </div>
            <div id="wiz-visual-engine-cards" class="wiz-visual-engine-cards">
                ${VISUAL_ENGINE_CARDS.map((c) => `
                    <button type="button" class="wiz-vengine-card${c.val === curEngine ? ' active' : ''}" data-vengine="${c.val}">
                        <div class="wiz-ve-top">
                            <span class="wiz-ve-icon">${c.icon}</span>
                            <span class="wiz-ve-badge">${c.badge}</span>
                        </div>
                        <strong>${c.title}</strong>
                        <small>${c.sub}</small>
                    </button>
                `).join('')}
            </div>
        </div>

        <!-- Item 32 & 33: BGM Ruh Hali Çipleri + Auto-Ducking Desibel Dengesi -->
        <div class="wiz-s3-block">
            <div class="wiz-s3-head">
                <span><i class="fa-solid fa-music text-info"></i> 32 · BGM Ruh Hali (Mood) &amp; Anında Önizleme</span>
                <small>Tıklayınca atmosferi dinletir ve uygun müziği seçer</small>
            </div>
            <div id="wiz-bgm-mood-chips" class="wiz-bgm-mood-chips">
                ${BGM_MOOD_PRESETS.map((m) => `
                    <button type="button" class="wiz-mood-chip${prefs.bgmMood === m.id ? ' active' : ''}" data-mood-id="${m.id}">
                        <span>${m.label}</span>
                        <i class="fa-solid fa-play wiz-mood-play-icon"></i>
                    </button>
                `).join('')}
            </div>
            <div id="wiz-ducking-balance-bar" class="wiz-ducking-balance-bar">
                <div class="wiz-duck-top">
                    <span><i class="fa-solid fa-sliders"></i> 33 · Auto-Ducking (Müzik / Seslendirme Dengesi)</span>
                    <strong id="wiz-ducking-label">%${curDuck} Müzik · %100 Net Seslendirme</strong>
                </div>
                <div class="wiz-duck-controls">
                    <input type="range" id="studio-ducking-vol" min="0.04" max="0.35" step="0.01" value="${(curDuck / 100).toFixed(2)}">
                    <div class="wiz-duck-presets">
                        <button type="button" class="wiz-duck-preset" data-duck="0.08">%8 Fısıltı</button>
                        <button type="button" class="wiz-duck-preset" data-duck="0.12">%12 Dengeli</button>
                        <button type="button" class="wiz-duck-preset" data-duck="0.20">%20 Güçlü</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Item 34 & 35: Altyazı Stili Canlı Görsel Seçici + Safe-Zone Konum Rehberi -->
        <div class="wiz-s3-block">
            <div class="wiz-s3-head">
                <span><i class="fa-solid fa-closed-captioning text-success"></i> 34 · Canlı Altyazı Stili &amp; 35 · Shorts Safe-Zone Rehberi</span>
                <small>Sağdaki 9:16 telefon önizlemesinde anında güncellenir</small>
            </div>
            <div id="wiz-step3-subtitle-cards" class="wiz-step3-subtitle-cards">
                ${SUBTITLE_QUICK_CARDS.map((s) => `
                    <button type="button" class="wiz-sub-card${s.id === curSub ? ' active' : ''}" data-sub-preset="${s.id}">
                        <div class="wiz-sub-sample">${s.sample}</div>
                        <div class="wiz-sub-meta">
                            <strong>${s.title}</strong>
                            <span>${s.badge}</span>
                        </div>
                    </button>
                `).join('')}
            </div>
            <div id="wiz-subtitle-safezone-picker" class="wiz-subtitle-safezone-picker">
                <span class="wiz-sz-shield"><i class="fa-solid fa-shield-check text-success"></i> Safe-Zone Konumu (Beğen/Yorum butonlarıyla çakışmaz):</span>
                <div class="wiz-sz-btns">
                    <button type="button" class="wiz-sz-btn${curSafeY === '0.62' ? ' active' : ''}" data-safe-y="0.62">Üst-Orta (%62)</button>
                    <button type="button" class="wiz-sz-btn${curSafeY === '0.76' ? ' active' : ''}" data-safe-y="0.76">Alt-Orta (%76 · İdeal ✓)</button>
                    <button type="button" class="wiz-sz-btn${curSafeY === '0.84' ? ' active' : ''}" data-safe-y="0.84">Alt Bant (%84)</button>
                </div>
            </div>
        </div>

        <!-- Item 38, 39 & 40: Geçiş Efekti, SFX Yoğunluğu ve Kanal Filigranı -->
        <div class="wiz-s3-block wiz-s3-row-triple">
            <div class="wiz-s3-subbox">
                <div class="wiz-s3-head">
                    <span><i class="fa-solid fa-wand-sparkles text-warning"></i> 38 · Sahne Geçiş Efekti (Hover Önizleme)</span>
                </div>
                <div id="wiz-transition-preview-strip" class="wiz-transition-preview-strip">
                    ${TRANSITION_STYLES.map((t) => `
                        <button type="button" class="wiz-trans-chip ${t.animClass}${curTrans === t.id ? ' active' : ''}" data-trans-id="${t.id}" title="${t.desc}">
                            <span class="wiz-trans-demo"></span>
                            <span>${t.label}</span>
                        </button>
                    `).join('')}
                </div>
            </div>

            <div class="wiz-s3-subbox">
                <div class="wiz-s3-head">
                    <span><i class="fa-solid fa-volume-high text-info"></i> 39 · Otomatik SFX (Whoosh/Boom) Yoğunluğu</span>
                </div>
                <div id="wiz-sfx-intensity-bar" class="wiz-sfx-intensity-bar">
                    <button type="button" class="wiz-sfx-btn${curSfx === 'off' ? ' active' : ''}" data-sfx-mode="off">🔇 Kapalı</button>
                    <button type="button" class="wiz-sfx-btn${curSfx === 'balanced' ? ' active' : ''}" data-sfx-mode="balanced">⚖️ Dengeli</button>
                    <button type="button" class="wiz-sfx-btn${curSfx === 'intense' ? ' active' : ''}" data-sfx-mode="intense">💥 Yoğun</button>
                </div>
            </div>

            <div class="wiz-s3-subbox">
                <div class="wiz-s3-head">
                    <span><i class="fa-solid fa-stamp text-primary"></i> 40 · Kanal Filigranı / @İmza Sabitleme</span>
                </div>
                <div id="wiz-watermark-bar" class="wiz-watermark-bar">
                    <label class="wiz-wm-toggle">
                        <input type="checkbox" id="chk-wiz-watermark" ${curWmOn ? 'checked' : ''}>
                        <span>Aktif</span>
                    </label>
                    <input type="text" id="wiz-watermark-text" class="input-styled" value="${curWmText.replace(/"/g, '&quot;')}" placeholder="@kanaladi" maxlength="28">
                    <select id="wiz-watermark-pos" class="select-styled">
                        <option value="top-right" ${curWmPos === 'top-right' ? 'selected' : ''}>Sağ Üst</option>
                        <option value="top-left" ${curWmPos === 'top-left' ? 'selected' : ''}>Sol Üst</option>
                        <option value="top-center" ${curWmPos === 'top-center' ? 'selected' : ''}>Üst Orta</option>
                    </select>
                </div>
            </div>
        </div>
    `;

    settingsBody.insertBefore(hub, settingsBody.firstChild);
    bindStep3HubEvents(hub);
}

function injectStep3EnhancementBundles() {
    const fxDetails = document.getElementById('render-enhancement-options');
    const switchesGrid = fxDetails?.querySelector('.switches-grid');
    if (!fxDetails || !switchesGrid || document.getElementById('wiz-fx-quick-bundles')) return;

    const topContainer = document.createElement('div');
    topContainer.id = 'wiz-step3-fx-top';
    topContainer.className = 'wiz-step3-fx-top';

    const splitOn = Boolean(document.getElementById('chk-split-screen')?.checked);
    const curGp = splitOn ? (document.getElementById('select-gameplay-category')?.value || 'minecraft_parkour') : 'off';

    topContainer.innerHTML = `
        <!-- Item 36: Split-Screen Tek Tık Seçici -->
        <div class="wiz-s3-block">
            <div class="wiz-s3-head">
                <span><i class="fa-solid fa-gamepad text-info"></i> 36 · Split-Screen (Tatmin Edici Alt Video) Tek Tık Seçici</span>
                <small>Seçildiğinde bölünmüş ekran otomatik açılır</small>
            </div>
            <div id="wiz-split-screen-cards" class="wiz-split-screen-cards">
                ${SPLIT_SCREEN_CARDS.map((g) => `
                    <button type="button" class="wiz-split-card${curGp === g.id ? ' active' : ''}" data-split-id="${g.id}">
                        <span class="wiz-split-icon">${g.icon}</span>
                        <div>
                            <strong>${g.title}</strong>
                            <small>${g.sub}</small>
                        </div>
                    </button>
                `).join('')}
            </div>
        </div>

        <!-- Item 37: Görsel Efekt (FX) Hızlı Paketleri -->
        <div class="wiz-s3-block">
            <div class="wiz-s3-head">
                <span><i class="fa-solid fa-bolt text-warning"></i> 37 · Görsel Efekt (FX) Hızlı Paketleri</span>
                <small>14 teknik filtreyi tek tıkla hazır stile göre ayarlar</small>
            </div>
            <div id="wiz-fx-quick-bundles" class="wiz-fx-quick-bundles">
                ${FX_BUNDLES.map((b) => `
                    <button type="button" class="wiz-fx-bundle-btn" data-bundle-id="${b.id}">
                        <strong>${b.label}</strong>
                        <small>${b.desc}</small>
                    </button>
                `).join('')}
            </div>
        </div>
    `;

    fxDetails.insertBefore(topContainer, switchesGrid);
    bindStep3FxTopEvents(topContainer);
}

function bindStep3HubEvents(hub) {
    // 31. Visual Engine Cards
    hub.querySelectorAll('.wiz-vengine-card').forEach((btn) => {
        btn.addEventListener('click', () => {
            const val = btn.getAttribute('data-vengine') || 'auto';
            const sel = document.getElementById('select-visual-engine');
            if (sel) {
                sel.value = val;
                sel.dispatchEvent(new Event('change', { bubbles: true }));
            }
            hub.querySelectorAll('.wiz-vengine-card').forEach((b) => b.classList.toggle('active', b === btn));
            if (window.currentPlan && typeof window.currentPlan === 'object') {
                window.currentPlan.visual_mode = val;
            }
            saveStep3Prefs({ visualEngine: val });
            if (typeof showToast === 'function') showToast(`Görsel motor seçildi: ${btn.querySelector('strong')?.textContent || val}`);
        });
    });

    // 32. BGM Mood Chips
    hub.querySelectorAll('.wiz-mood-chip').forEach((btn) => {
        btn.addEventListener('click', () => {
            const moodId = btn.getAttribute('data-mood-id') || 'epic';
            const preset = BGM_MOOD_PRESETS.find((m) => m.id === moodId) || BGM_MOOD_PRESETS[0];
            hub.querySelectorAll('.wiz-mood-chip').forEach((b) => b.classList.toggle('active', b === btn));
            playBgmMoodChord(preset.freq);
            const chkBgm = document.getElementById('chk-enable-bgm');
            if (chkBgm) chkBgm.checked = true;
            const bgmSel = document.getElementById('studio-bgm-track');
            if (bgmSel && bgmSel.options.length > 2) {
                const matchedOpt = [...bgmSel.options].find((o) => preset.match.some((k) => o.value.toLowerCase().includes(k) || o.textContent.toLowerCase().includes(k)));
                if (matchedOpt) bgmSel.value = matchedOpt.value;
            }
            saveStep3Prefs({ bgmMood: moodId });
            if (typeof showToast === 'function') showToast(`${preset.label} atmosferi seçildi ve önizlendi.`);
        });
    });

    // 33. Auto-Ducking Slider
    const duckSlider = hub.querySelector('#studio-ducking-vol');
    const updateDuckVal = (rawVal) => {
        const num = Math.min(0.35, Math.max(0.04, parseFloat(rawVal || '0.12')));
        if (duckSlider) duckSlider.value = num.toFixed(2);
        const audioDuck = document.getElementById('range-ducking-vol');
        if (audioDuck) {
            audioDuck.value = num.toFixed(2);
            audioDuck.dispatchEvent(new Event('input', { bubbles: true }));
        }
        const lbl = document.getElementById('wiz-ducking-label');
        if (lbl) lbl.textContent = `%${Math.round(num * 100)} Müzik · %100 Net Seslendirme`;
        saveStep3Prefs({ duckingVol: num });
    };
    duckSlider?.addEventListener('input', () => updateDuckVal(duckSlider.value));
    hub.querySelectorAll('.wiz-duck-preset').forEach((b) => {
        b.addEventListener('click', () => updateDuckVal(b.getAttribute('data-duck')));
    });

    // 34. Subtitle Style Quick Cards
    hub.querySelectorAll('.wiz-sub-card').forEach((btn) => {
        btn.addEventListener('click', () => {
            const preset = btn.getAttribute('data-sub-preset') || 'capcut_yellow';
            const sel = document.getElementById('select-subtitle-preset');
            if (sel) {
                sel.value = preset;
                sel.dispatchEvent(new Event('change', { bubbles: true }));
            }
            hub.querySelectorAll('.wiz-sub-card').forEach((b) => b.classList.toggle('active', b === btn));
            if (typeof updateSubtitleSimulator === 'function') updateSubtitleSimulator();
            saveStep3Prefs({ subtitlePreset: preset });
        });
    });

    // 35. Safe-Zone Position Buttons
    hub.querySelectorAll('.wiz-sz-btn').forEach((btn) => {
        btn.addEventListener('click', () => {
            const yVal = btn.getAttribute('data-safe-y') || '0.76';
            const subY = document.getElementById('sub-range-y');
            if (subY) {
                subY.value = yVal;
                subY.dispatchEvent(new Event('input', { bubbles: true }));
            }
            hub.querySelectorAll('.wiz-sz-btn').forEach((b) => b.classList.toggle('active', b === btn));
            saveStep3Prefs({ safeZoneY: yVal });
            syncPhoneMockupStep3Overlays();
        });
    });

    // 38. Transition Style Strip
    const triggerPhoneTransDemo = (tid) => {
        const area = document.getElementById('phone-video-area');
        if (!area) return;
        area.classList.remove('trans-anim-whip_pan', 'trans-anim-glitch', 'trans-anim-zoom_punch', 'trans-anim-flash_cut');
        void area.offsetWidth;
        area.classList.add(`trans-anim-${tid}`);
    };
    hub.querySelectorAll('.wiz-trans-chip').forEach((btn) => {
        btn.setAttribute('aria-pressed', btn.classList.contains('active') ? 'true' : 'false');
        btn.addEventListener('mouseenter', () => triggerPhoneTransDemo(btn.getAttribute('data-trans-id') || 'whip_pan'));
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            const tid = btn.getAttribute('data-trans-id') || 'whip_pan';
            hub.querySelectorAll('.wiz-trans-chip').forEach((b) => {
                const isAct = b === btn;
                b.classList.toggle('active', isAct);
                b.setAttribute('aria-pressed', isAct ? 'true' : 'false');
            });
            const chkZoom = document.getElementById('chk-zoompan');
            if (chkZoom && tid === 'zoom_punch') chkZoom.checked = true;
            if (window.currentPlan && typeof window.currentPlan === 'object') {
                window.currentPlan.transition_style = tid;
            }
            saveStep3Prefs({ transitionStyle: tid });
            triggerPhoneTransDemo(tid);
            if (typeof showToast === 'function') showToast(`✨ Sahne geçiş efekti seçildi: ${btn.textContent.trim()}`);
        });
    });

    // 39. SFX Intensity 3-Way Selector
    hub.querySelectorAll('.wiz-sfx-btn').forEach((btn) => {
        btn.addEventListener('click', () => {
            const mode = btn.getAttribute('data-sfx-mode') || 'balanced';
            hub.querySelectorAll('.wiz-sfx-btn').forEach((b) => b.classList.toggle('active', b === btn));
            const chkWhoosh = document.getElementById('chk-intro-whoosh');
            const chkSonilo = document.getElementById('chk-enable-sonilo-sfx');
            if (chkWhoosh) chkWhoosh.checked = mode !== 'off';
            if (chkSonilo) chkSonilo.checked = mode === 'intense';
            if (mode !== 'off' && typeof playSyntheticSound === 'function') {
                playSyntheticSound(mode === 'intense' ? 'whoosh' : 'pop');
            }
            saveStep3Prefs({ sfxIntensity: mode });
        });
    });

    // 40. Channel Watermark Bar
    const syncWm = () => {
        const enabled = Boolean(document.getElementById('chk-wiz-watermark')?.checked);
        const text = (document.getElementById('wiz-watermark-text')?.value || '@shortsstudio').trim();
        const pos = document.getElementById('wiz-watermark-pos')?.value || 'top-right';
        saveStep3Prefs({ watermarkEnabled: enabled, watermarkText: text, watermarkPos: pos });
        if (window.currentPlan && typeof window.currentPlan === 'object') {
            window.currentPlan.watermark = enabled ? { text, position: pos } : null;
        }
        syncPhoneMockupStep3Overlays();
    };
    hub.querySelector('#chk-wiz-watermark')?.addEventListener('change', syncWm);
    hub.querySelector('#wiz-watermark-text')?.addEventListener('input', syncWm);
    hub.querySelector('#wiz-watermark-pos')?.addEventListener('change', syncWm);
}

function bindStep3FxTopEvents(container) {
    // 36. Split-Screen Gameplay Selector Cards
    container.querySelectorAll('.wiz-split-card').forEach((btn) => {
        btn.addEventListener('click', () => {
            const splitId = btn.getAttribute('data-split-id') || 'off';
            const chkSplit = document.getElementById('chk-split-screen');
            const gpSel = document.getElementById('select-gameplay-category');
            const gpWrap = document.getElementById('gameplay-category-wrap');
            const isOn = splitId !== 'off';
            if (chkSplit) {
                chkSplit.checked = isOn;
                chkSplit.dispatchEvent(new Event('change', { bubbles: true }));
            }
            if (isOn && gpSel) {
                gpSel.value = splitId;
                gpSel.dispatchEvent(new Event('change', { bubbles: true }));
            }
            if (gpWrap) gpWrap.style.display = isOn ? 'block' : 'none';
            container.querySelectorAll('.wiz-split-card').forEach((b) => b.classList.toggle('active', b === btn));
            if (typeof syncWizardBreadcrumbsAndTicks === 'function') syncWizardBreadcrumbsAndTicks();
            syncPhoneMockupStep3Overlays();
        });
    });

    // 37. Quick Visual FX Preset Bundles
    container.querySelectorAll('.wiz-fx-bundle-btn').forEach((btn) => {
        btn.addEventListener('click', () => {
            const bid = btn.getAttribute('data-bundle-id');
            const bundle = FX_BUNDLES.find((b) => b.id === bid);
            if (!bundle) return;
            const allFxIds = [
                'chk-hook-card', 'chk-split-screen', 'chk-reddit-card', 'chk-anti-duplicate',
                'chk-ken-burns', 'chk-zoompan', 'chk-broll-insert', 'chk-center-face',
                'chk-emphasis-card', 'chk-audio-visualizer', 'chk-news-ticker', 'chk-whisper-align'
            ];
            allFxIds.forEach((id) => {
                const el = document.getElementById(id);
                if (el) {
                    el.checked = bundle.on.includes(id);
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                }
            });
            container.querySelectorAll('.wiz-fx-bundle-btn').forEach((b) => b.classList.toggle('active', b === btn));
            if (typeof showToast === 'function') showToast(`${bundle.label} FX paketi uygulandı.`);
            syncPhoneMockupStep3Overlays();
        });
    });
}

function syncWizardStep3UI() {
    injectStep3RenderSettingsEnhancements();
    injectStep3EnhancementBundles();
    syncPhoneMockupStep3Overlays();
}
window.syncWizardStep3UI = syncWizardStep3UI;

document.addEventListener('DOMContentLoaded', () => {
    syncWizardStep3UI();
});
