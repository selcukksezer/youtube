/**
 * Shorts Studio — Category B (Items 11–20): Step 01 Idea, Topic & Niche UX Controller
 * Implements:
 *  11. Visual Niche Quick Cards (#wiz-niche-quick-cards)
 *  12. Live Character & Word Counter (#wiz-topic-char-counter)
 *  13. Instant 3 Viral Idea Chips per Niche (#wiz-instant-idea-chips)
 *  14. Live Subtitle Style Preview (#wiz-sub-style-preview-pill & 9:16 Phone Mockup)
 *  15. Recent 5 Topics History Strip (#wiz-topic-history-strip)
 *  16. Live Viral Hook Power Badge (#wiz-hook-power-badge)
 *  17. Niche Change Auto-Sync Notification with [Geri Al] (#wiz-niche-autosync-bar)
 *  18. Trend Source Filter Chips (Tümü | YouTube | Reddit | Trends) (#wiz-trend-source-filter)
 *  19. Topic Pinning / Save for Later Queue (#btn-pin-current-topic & #wiz-pinned-topics-bar)
 *  20. Language Switch Flag + Voice Sync Confirmation Badge (#wiz-lang-voice-sync-badge)
 */

const WIZ_RECENT_TOPICS_KEY = 'shorts_studio_recent_topics_v1';
const WIZ_PINNED_TOPICS_KEY = 'shorts_studio_pinned_topics_v1';

const WIZ_NICHE_QUICK_PRESETS = [
    {
        match: ['stoa', 'stoic', '1_stoic', 'philosophy', 'felsefe'],
        fallbackVal: '1_stoic_wisdom',
        icon: '🏛️',
        title: 'Stoa & Disiplin',
        rpm: '$12–$18 RPM',
        retention: '%81 İzlenme',
        subPreset: 'cinematic_minimal',
        ideas: [
            "Marcus Aurelius'un Öfkeyi 10 Saniyede Bitiren 3 Stoacı Kuralı",
            "Seneca'nın Zaman Kaybeden İnsanları Uyaran Unutulmuş Mektubu",
            "Epictetus: Kontrol Edemediğin Şeyleri Bırakmanın 3 Zihinsel Sırrı",
            "Stoacılara Göre Sabah Uyanınca Asla Yapmamanız Gereken Hata"
        ]
    },
    {
        match: ['five_facts', '9_five_facts', 'facts', 'bilgi', 'science'],
        fallbackVal: '9_five_facts',
        icon: '🧠',
        title: '5 İlginç Bilgi',
        rpm: '$6–$11 RPM',
        retention: '%78 İzlenme',
        subPreset: 'mrbeast_style',
        ideas: [
            "Beyninizin Bu Bilgiyi Duyduktan Sonra Asla Eskisi Gibi Olmayacak 5 Gerçek!",
            "İnsan Vücudunun Bilim İnsanlarını Hâlâ Şaşırtan 5 Gizli Süper Gücü",
            "Uzayda Astronotların Asla Anlatmadığı 5 Ürkütücü Fizik Gerçeği",
            "Derin Okyanuslarda Keşfedilen ve Açıklanamayan 5 Doğa Olayı"
        ]
    },
    {
        match: ['finance', 'wealth', 'money', 'finans', 'crypto', 'ekonomi'],
        fallbackVal: '2_wealth_finance',
        icon: '💎',
        title: 'Finans & Servet',
        rpm: '$18–$28 RPM',
        retention: '%76 İzlenme',
        subPreset: 'crypto_gold',
        ideas: [
            "Zenginlerin Maaşlı Çalışanlardan Sakladığı 3 Parasal Kaldıraç Kuralı",
            "Enflasyon Döneminde Paranın Değerini Koruyan 4 Tarihsel Strateji",
            "Warren Buffett'ın İlk 100.000 Dolar İçin Verdiği Acımasız Tavsiye",
            "Psikolojik Fiyatlandırma: Markaların Sizi Harcamaya İkna Eden 3 Hilesi"
        ]
    },
    {
        match: ['psych', 'psikoloji', 'dark', 'manipulation', 'mind'],
        fallbackVal: '3_dark_psychology',
        icon: '🎭',
        title: 'Psikoloji & Zihin',
        rpm: '$11–$17 RPM',
        retention: '%83 İzlenme',
        subPreset: 'psychology_violet',
        ideas: [
            "Bir İnsanın Size Yalan Söylediğini Ele Veren 3 Mikro Beden Dili İşareti",
            "İlk 7 Saniyede Saygı Uyandıran İnsanların Kullandığı Konuşma Tekniği",
            "Narsist İnsanların Sizi Suçlu Hissettirmek İçin Kullandığı 3 Cümle",
            "Sessiz Kalmanın Tartışmalarda Size Kazandırdığı Psikolojik Üstünlük"
        ]
    },
    {
        match: ['tech', 'ai', 'yapay', 'future', 'cyber'],
        fallbackVal: '4_ai_future_tech',
        icon: '🤖',
        title: 'Yapay Zeka & Tek',
        rpm: '$15–$24 RPM',
        retention: '%79 İzlenme',
        subPreset: 'cyber_green',
        ideas: [
            "Önümüzdeki 24 Ayda Tamamen Değişecek 5 Beyaz Yaka Meslek",
            "Yapay Zeka Modellerinin Kendi Aralarında Kurduğu Gizli İletişim Deneyi",
            "Kuantum Bilgisayarların Mevcut Şifreleri Saniyeler İçinde Çözme Gerçeği",
            "Silikon Vadisi Mühendislerinin Çocuklarına Telefon Vermeme Nedeni"
        ]
    },
    {
        match: ['history', 'tarih', 'mystery', 'gizem', 'ancient'],
        fallbackVal: '5_ancient_history',
        icon: '⏳',
        title: 'Tarih & Gizem',
        rpm: '$9–$15 RPM',
        retention: '%82 İzlenme',
        subPreset: 'history_sepia',
        ideas: [
            "İskenderiye Kütüphanesi Yandığında İnsanlığın Kaybettiği 3 İcat",
            "Göbeklitepe'de Arkeologların Hâlâ Çözemediği 12.000 Yıllık Astronomi Sırrı",
            "Roma İmparatorluğunu İçten Çökerten Beklenmedik Ekonomik Hata",
            "Antik Mısır Piramitlerinin İnşasında Kullanılan Su Kanalı Mühendisliği"
        ]
    }
];

const WIZ_SUBTITLE_STYLES = {
    capcut_yellow: { label: 'CapCut Neon Sarı', fg: '#facc15', bg: 'rgba(0,0,0,0.82)', border: '#facc15', shadow: '0 2px 8px rgba(250,204,21,0.35)' },
    cyber_green: { label: 'Cyberpunk Yeşil', fg: '#4ade80', bg: 'rgba(6,28,18,0.88)', border: '#22c55e', shadow: '0 0 12px rgba(74,222,128,0.4)' },
    red_fire: { label: 'Ateş Kırmızısı', fg: '#f87171', bg: 'rgba(32,8,8,0.88)', border: '#ef4444', shadow: '0 0 12px rgba(239,68,68,0.4)' },
    clean_white: { label: 'Minimalist Beyaz', fg: '#f8fafc', bg: 'rgba(15,23,42,0.78)', border: '#94a3b8', shadow: 'none' },
    high_contrast_retention: { label: 'Yüksek Kontrast', fg: '#fde047', bg: '#000000', border: '#fde047', shadow: '0 2px 10px rgba(0,0,0,0.9)' },
    tiktok_bold: { label: 'TikTok Kalın Sarı', fg: '#fef08a', bg: 'rgba(17,24,39,0.88)', border: '#f59e0b', shadow: '0 2px 6px rgba(245,158,11,0.3)' },
    mrbeast_style: { label: 'MrBeast Sarı Kutu', fg: '#090d16', bg: '#facc15', border: '#ffffff', shadow: '0 4px 14px rgba(250,204,21,0.45)' },
    cinematic_minimal: { label: 'Sinematik Minimal', fg: '#e2e8f0', bg: 'rgba(9,13,22,0.72)', border: 'rgba(226,232,240,0.3)', shadow: 'none' },
    crypto_gold: { label: 'Kripto Altın', fg: '#fbbf24', bg: 'rgba(24,18,6,0.9)', border: '#d97706', shadow: '0 0 12px rgba(251,191,36,0.35)' },
    luxury_elegance: { label: 'Lüks Altın', fg: '#fde68a', bg: 'rgba(17,17,17,0.88)', border: '#ca8a04', shadow: 'none' },
    horror_blood: { label: 'Korku Kırmızısı', fg: '#fca5a5', bg: 'rgba(28,4,4,0.92)', border: '#dc2626', shadow: '0 0 14px rgba(220,38,38,0.45)' },
    history_sepia: { label: 'Tarih Sepya', fg: '#fed7aa', bg: 'rgba(35,23,12,0.88)', border: '#ea580c', shadow: 'none' },
    space_neon_blue: { label: 'Uzay Neon Mavi', fg: '#38bdf8', bg: 'rgba(8,22,38,0.88)', border: '#0284c7', shadow: '0 0 12px rgba(56,189,248,0.4)' },
    fitness_punch: { label: 'Fitness Turuncu', fg: '#fb923c', bg: 'rgba(30,14,4,0.9)', border: '#f97316', shadow: '0 2px 10px rgba(249,115,22,0.35)' },
    psychology_violet: { label: 'Psikoloji Mor', fg: '#c4b5fd', bg: 'rgba(22,12,38,0.88)', border: '#8b5cf6', shadow: '0 0 12px rgba(167,139,250,0.35)' },
    wisdom_emerald: { label: 'Bilgelik Zümrüt', fg: '#6ee7b7', bg: 'rgba(6,28,22,0.88)', border: '#10b981', shadow: '0 0 12px rgba(16,185,129,0.35)' }
};

let wizIdeaRotationOffset = 0;
let wizLastNicheSnapshot = null;
window.selectedTrendSource = 'all';

function loadJsonArray(key, fallback = []) {
    try {
        const raw = localStorage.getItem(key);
        const parsed = raw ? JSON.parse(raw) : fallback;
        return Array.isArray(parsed) ? parsed : fallback;
    } catch (_) {
        return fallback;
    }
}

function saveJsonArray(key, arr) {
    try {
        localStorage.setItem(key, JSON.stringify(arr));
    } catch (_) {}
}

function computeViralHookPower(topic) {
    const clean = (topic || '').trim();
    if (!clean) return { score: 0, label: 'Konu Girin', cls: 'is-empty' };
    const words = clean.split(/\s+/).filter(Boolean);
    let score = 5.2;
    if (words.length >= 5 && words.length <= 13) score += 1.6;
    else if (words.length >= 3) score += 0.7;
    if (/\d+/.test(clean)) score += 1.1;
    if (/[?!]/.test(clean)) score += 0.6;
    if (/(neden|asla|sır|kural|gerçek|saklanan|yasak|gizli|inanılmaz|şaşırtan|hatası|psikolojik|bilim|why|never|secret|truth|rules|facts)/i.test(clean)) {
        score += 1.3;
    }
    if (clean.length >= 32 && clean.length <= 88) score += 0.5;
    score = Math.min(9.9, Math.max(2.5, +score.toFixed(1)));
    if (score >= 8.0) return { score, label: `${score}/10 · Yüksek Viral Kanca`, cls: 'is-high' };
    if (score >= 6.4) return { score, label: `${score}/10 · İyi Kanca`, cls: 'is-mid' };
    return { score, label: `${score}/10 · Merak Öğesi Ekleyin`, cls: 'is-low' };
}

function findMatchingNichePreset(nicheVal = '') {
    const low = String(nicheVal || '').toLowerCase();
    for (const p of WIZ_NICHE_QUICK_PRESETS) {
        if (p.match.some(m => low.includes(m))) return p;
    }
    return WIZ_NICHE_QUICK_PRESETS[0];
}

function updateTopicCounterAndHookBadge() {
    const input = document.getElementById('input-topic');
    if (!input) return;
    const val = input.value || '';
    const trimmed = val.trim();
    const charLen = trimmed.length;
    const wc = trimmed ? trimmed.split(/\s+/).filter(Boolean).length : 0;

    const counterEl = document.getElementById('wiz-topic-char-counter');
    if (counterEl) {
        let hint = 'İdeal aralık: 30–90 karakter';
        let stateCls = 'is-neutral';
        if (charLen > 0 && charLen < 22) { hint = 'Biraz daha detay/merak ekleyin'; stateCls = 'is-warn'; }
        else if (charLen >= 22 && charLen <= 95) { hint = 'İdeal Shorts Kanca Uzunluğu ✓'; stateCls = 'is-ok'; }
        else if (charLen > 95) { hint = 'Başlık uzun — ilk 60 karakter kritik'; stateCls = 'is-warn'; }
        counterEl.className = `wiz-topic-char-counter ${stateCls}`;
        counterEl.textContent = `${charLen} / 90 karakter · ${wc} kelime · ${hint}`;
    }

    const badgeEl = document.getElementById('wiz-hook-power-badge');
    if (badgeEl) {
        const power = computeViralHookPower(trimmed);
        badgeEl.className = `wiz-hook-power-badge ${power.cls}`;
        badgeEl.innerHTML = `<i class="fa-solid fa-fire-flame-curved"></i> Kanca: <strong>${power.label}</strong>`;
    }

    const pinBtn = document.getElementById('btn-pin-current-topic');
    if (pinBtn) {
        const pinned = loadJsonArray(WIZ_PINNED_TOPICS_KEY);
        const isPinned = trimmed && pinned.includes(trimmed);
        pinBtn.classList.toggle('is-pinned', Boolean(isPinned));
        pinBtn.innerHTML = isPinned ? '<i class="fa-solid fa-thumbtack"></i> Sabitlendi' : '<i class="fa-solid fa-thumbtack"></i> Sabitle';
    }
}

function renderInstantIdeaChips() {
    const wrap = document.getElementById('wiz-instant-idea-chips');
    const selectNiche = document.getElementById('select-niche');
    if (!wrap) return;
    const preset = findMatchingNichePreset(selectNiche?.value || '');
    const pool = preset.ideas || [];
    const picked = [];
    for (let i = 0; i < Math.min(3, pool.length); i++) {
        picked.push(pool[(wizIdeaRotationOffset + i) % pool.length]);
    }
    wrap.innerHTML = `
        <span class="wiz-idea-label"><i class="fa-solid fa-bolt text-warning"></i> Anlık 3 Fikir (${preset.title}):</span>
        <div class="wiz-idea-chips-row">
            ${picked.map(idea => `
                <button type="button" class="wiz-idea-chip" data-idea="${ idea.replace(/"/g, '&quot;') }">
                    ✨ ${idea}
                </button>
            `).join('')}
            <button type="button" class="wiz-idea-refresh-btn" id="btn-wiz-rotate-ideas" title="Farklı 3 fikir göster">
                <i class="fa-solid fa-dice"></i> Yenile
            </button>
        </div>
    `;
    wrap.querySelectorAll('.wiz-idea-chip').forEach(btn => {
        btn.addEventListener('click', () => {
            const idea = btn.getAttribute('data-idea') || '';
            const input = document.getElementById('input-topic');
            if (input && idea) {
                input.value = idea;
                rememberRecentTopic(idea);
                input.dispatchEvent(new Event('input', { bubbles: true }));
                input.dispatchEvent(new Event('change', { bubbles: true }));
            }
        });
    });
    wrap.querySelector('#btn-wiz-rotate-ideas')?.addEventListener('click', () => {
        wizIdeaRotationOffset = (wizIdeaRotationOffset + 1) % Math.max(1, pool.length);
        renderInstantIdeaChips();
    });
}

function rememberRecentTopic(topic) {
    const clean = (topic || '').trim();
    if (!clean || clean.length < 8) return;
    const list = loadJsonArray(WIZ_RECENT_TOPICS_KEY).filter(item => item !== clean);
    list.unshift(clean);
    saveJsonArray(WIZ_RECENT_TOPICS_KEY, list.slice(0, 5));
    renderRecentTopicsStrip();
}

function renderRecentTopicsStrip() {
    const strip = document.getElementById('wiz-topic-history-strip');
    if (!strip) return;
    const list = loadJsonArray(WIZ_RECENT_TOPICS_KEY);
    if (!list.length) {
        strip.classList.add('hidden');
        return;
    }
    strip.classList.remove('hidden');
    strip.innerHTML = `
        <span class="wiz-hist-label"><i class="fa-solid fa-clock-rotate-left"></i> Son Konular:</span>
        ${list.map(t => `
            <button type="button" class="wiz-hist-pill" data-topic="${t.replace(/"/g, '&quot;')}" title="${t.replace(/"/g, '&quot;')}">
                ${t.length > 42 ? t.slice(0, 40) + '…' : t}
            </button>
        `).join('')}
    `;
    strip.querySelectorAll('.wiz-hist-pill').forEach(btn => {
        btn.addEventListener('click', () => {
            const t = btn.getAttribute('data-topic') || '';
            const input = document.getElementById('input-topic');
            if (input && t) {
                input.value = t;
                input.dispatchEvent(new Event('input', { bubbles: true }));
                input.dispatchEvent(new Event('change', { bubbles: true }));
            }
        });
    });
}

function renderPinnedTopicsBar() {
    const bar = document.getElementById('wiz-pinned-topics-bar');
    if (!bar) return;
    const pinned = loadJsonArray(WIZ_PINNED_TOPICS_KEY);
    if (!pinned.length) {
        bar.classList.add('hidden');
        return;
    }
    bar.classList.remove('hidden');
    bar.innerHTML = `
        <span class="wiz-pin-label"><i class="fa-solid fa-thumbtack text-warning"></i> Sabitlenenler (${pinned.length}):</span>
        <div class="wiz-pin-list">
            ${pinned.map((t, idx) => `
                <span class="wiz-pin-chip">
                    <button type="button" class="wiz-pin-use" data-idx="${idx}">${t.length > 44 ? t.slice(0, 42) + '…' : t}</button>
                    <button type="button" class="wiz-pin-del" data-idx="${idx}" title="Kaldır">&times;</button>
                </span>
            `).join('')}
        </div>
    `;
    bar.querySelectorAll('.wiz-pin-use').forEach(btn => {
        btn.addEventListener('click', () => {
            const t = pinned[Number(btn.getAttribute('data-idx'))];
            const input = document.getElementById('input-topic');
            if (input && t) {
                input.value = t;
                input.dispatchEvent(new Event('input', { bubbles: true }));
                input.dispatchEvent(new Event('change', { bubbles: true }));
            }
        });
    });
    bar.querySelectorAll('.wiz-pin-del').forEach(btn => {
        btn.addEventListener('click', () => {
            const idx = Number(btn.getAttribute('data-idx'));
            pinned.splice(idx, 1);
            saveJsonArray(WIZ_PINNED_TOPICS_KEY, pinned);
            renderPinnedTopicsBar();
            updateTopicCounterAndHookBadge();
        });
    });
}

function updateSubtitleLivePreview() {
    const sel = document.getElementById('select-subtitle-preset');
    const pill = document.getElementById('wiz-sub-style-preview-pill');
    if (!sel) return;
    const cfg = WIZ_SUBTITLE_STYLES[sel.value] || WIZ_SUBTITLE_STYLES.capcut_yellow;
    if (pill) {
        pill.style.color = cfg.fg;
        pill.style.background = cfg.bg;
        pill.style.borderColor = cfg.border;
        pill.style.boxShadow = cfg.shadow;
        pill.innerHTML = `<i class="fa-solid fa-closed-captioning"></i> Önizleme: <strong>"ASLA ESKİSİ GİBİ OLMAYACAK!"</strong>`;
    }
    const phoneCap = document.querySelector('#mockup-sub-overlay .sub-word-highlight, #mockup-sub-overlay, #pane-studio .phone-screen .caption strong');
    if (phoneCap) {
        phoneCap.style.color = cfg.fg;
        phoneCap.style.textShadow = cfg.shadow !== 'none' ? cfg.shadow : '0 1px 4px rgba(0,0,0,0.8)';
    }
}

function updateLangVoiceSyncBadge() {
    const badge = document.getElementById('wiz-lang-voice-sync-badge');
    if (!badge) return;
    const isEn = document.getElementById('btn-quick-lang-en')?.classList.contains('active')
        || document.getElementById('select-language')?.value === 'en';
    const voiceSel = document.getElementById('select-tts-voice');
    const voiceLabel = voiceSel?.selectedOptions?.[0]?.textContent?.trim() || 'Otomatik Neural';
    if (isEn) {
        badge.innerHTML = `🇺🇸 <strong>EN Tier-1 Ses Senkron</strong> · ${voiceLabel.slice(0, 28)}`;
        badge.className = 'wiz-lang-voice-sync-badge is-en';
    } else {
        badge.innerHTML = `🇹🇷 <strong>TR Ses Senkron</strong> · ${voiceLabel.slice(0, 28)}`;
        badge.className = 'wiz-lang-voice-sync-badge is-tr';
    }
}

function renderVisualNicheQuickCards() {
    const container = document.getElementById('wiz-niche-quick-cards');
    const selectNiche = document.getElementById('select-niche');
    if (!container || !selectNiche) return;

    const currentVal = (selectNiche.value || '').toLowerCase();
    container.innerHTML = WIZ_NICHE_QUICK_PRESETS.map((p, idx) => {
        const isActive = p.match.some(m => currentVal.includes(m));
        return `
            <button type="button" class="wiz-niche-card-chip ${isActive ? 'is-active' : ''}" data-pidx="${idx}">
                <span class="wiz-nc-top">
                    <span class="wiz-nc-title">${p.icon} ${p.title}</span>
                    <span class="wiz-nc-rpm">${p.rpm}</span>
                </span>
                <span class="wiz-nc-sub">${p.retention} · Tıkla Seç</span>
            </button>
        `;
    }).join('');

    container.querySelectorAll('.wiz-niche-card-chip').forEach(btn => {
        btn.addEventListener('click', () => {
            const p = WIZ_NICHE_QUICK_PRESETS[Number(btn.getAttribute('data-pidx'))];
            if (!p) return;
            const prevSnapshot = {
                niche: selectNiche.value,
                sub: document.getElementById('select-subtitle-preset')?.value || 'capcut_yellow'
            };
            const opts = Array.from(selectNiche.options);
            const found = opts.find(o => p.match.some(m => o.value.toLowerCase().includes(m) || o.textContent.toLowerCase().includes(m)));
            if (found) {
                selectNiche.value = found.value;
            }
            const subSel = document.getElementById('select-subtitle-preset');
            if (subSel && p.subPreset) {
                subSel.value = p.subPreset;
                subSel.dispatchEvent(new Event('change', { bubbles: true }));
            }
            wizLastNicheSnapshot = prevSnapshot;
            selectNiche.dispatchEvent(new Event('change', { bubbles: true }));
            showNicheAutoSyncBanner(p.title);
            renderVisualNicheQuickCards();
            renderInstantIdeaChips();
        });
    });
}

function showNicheAutoSyncBanner(nicheLabel) {
    const bar = document.getElementById('wiz-niche-autosync-bar');
    if (!bar) return;
    bar.classList.remove('hidden');
    bar.innerHTML = `
        <span><i class="fa-solid fa-wand-magic-sparkles text-primary"></i> <strong>${nicheLabel}</strong> seçildi — Altyazı stili, ses tonu ve kanca fikirleri otomatik eşleştirildi.</span>
        <button type="button" class="btn btn-xs btn-outline" id="btn-wiz-undo-niche-sync"><i class="fa-solid fa-rotate-left"></i> Geri Al</button>
    `;
    bar.querySelector('#btn-wiz-undo-niche-sync')?.addEventListener('click', () => {
        if (wizLastNicheSnapshot) {
            const selectNiche = document.getElementById('select-niche');
            const subSel = document.getElementById('select-subtitle-preset');
            if (selectNiche && wizLastNicheSnapshot.niche) {
                selectNiche.value = wizLastNicheSnapshot.niche;
                selectNiche.dispatchEvent(new Event('change', { bubbles: true }));
            }
            if (subSel && wizLastNicheSnapshot.sub) {
                subSel.value = wizLastNicheSnapshot.sub;
                subSel.dispatchEvent(new Event('change', { bubbles: true }));
            }
            renderVisualNicheQuickCards();
            renderInstantIdeaChips();
        }
        bar.classList.add('hidden');
    });
}

function initWizardStep1CategoryB() {
    const formCard = document.querySelector('#pane-studio .studio-form-card');
    if (!formCard || document.getElementById('wiz-topic-char-counter')) return;

    // Item 20: Language + Voice Sync Confirmation Badge inside #studio-lang-selector-strip
    const langStrip = document.getElementById('studio-lang-selector-strip');
    if (langStrip && !document.getElementById('wiz-lang-voice-sync-badge')) {
        const syncBadge = document.createElement('span');
        syncBadge.id = 'wiz-lang-voice-sync-badge';
        syncBadge.className = 'wiz-lang-voice-sync-badge is-tr';
        langStrip.appendChild(syncBadge);
    }

    // Topic field enhancements (Items 12, 13, 15, 16, 18, 19)
    const inputTopic = document.getElementById('input-topic');
    const topicField = inputTopic?.closest('.form-field');
    if (topicField) {
        const labelRow = topicField.querySelector('.field-label-row');
        if (labelRow) {
            // Item 16: Hook Power Badge + Item 18: Trend Source Filter + Item 19: Pin Button
            const actionWrap = labelRow.querySelector('div') || labelRow;
            const hookBadge = document.createElement('span');
            hookBadge.id = 'wiz-hook-power-badge';
            hookBadge.className = 'wiz-hook-power-badge is-empty';
            actionWrap.insertBefore(hookBadge, actionWrap.firstChild);

            const trendFilter = document.createElement('div');
            trendFilter.id = 'wiz-trend-source-filter';
            trendFilter.className = 'wiz-trend-source-filter';
            trendFilter.innerHTML = `
                <button type="button" class="wiz-src-chip active" data-src="all" title="Tüm Trend Kaynakları">Tümü</button>
                <button type="button" class="wiz-src-chip" data-src="youtube" title="YouTube Shorts Trendleri">YT</button>
                <button type="button" class="wiz-src-chip" data-src="reddit" title="Reddit Viral Konular">Reddit</button>
                <button type="button" class="wiz-src-chip" data-src="trends" title="Google Trends">Trends</button>
            `;
            actionWrap.insertBefore(trendFilter, document.getElementById('btn-suggest-topic'));

            const pinBtn = document.createElement('button');
            pinBtn.type = 'button';
            pinBtn.id = 'btn-pin-current-topic';
            pinBtn.className = 'link-btn wiz-pin-topic-btn';
            pinBtn.title = 'Bu konuyu daha sonra üretmek için sabitle';
            pinBtn.innerHTML = '<i class="fa-solid fa-thumbtack"></i> Sabitle';
            actionWrap.appendChild(pinBtn);

            trendFilter.querySelectorAll('.wiz-src-chip').forEach(chip => {
                chip.addEventListener('click', () => {
                    trendFilter.querySelectorAll('.wiz-src-chip').forEach(c => c.classList.remove('active'));
                    chip.classList.add('active');
                    window.selectedTrendSource = chip.getAttribute('data-src') || 'all';
                    if (typeof showToast === 'function') {
                        showToast(`📡 Konu öneri kaynağı: ${chip.textContent}`);
                    }
                });
            });

            pinBtn.addEventListener('click', () => {
                const val = (inputTopic.value || '').trim();
                if (!val) {
                    if (typeof showToast === 'function') showToast('Sabitlemek için önce bir konu yazın veya seçin.', 'warning');
                    return;
                }
                const pinned = loadJsonArray(WIZ_PINNED_TOPICS_KEY);
                const idx = pinned.indexOf(val);
                if (idx >= 0) {
                    pinned.splice(idx, 1);
                    if (typeof showToast === 'function') showToast('📌 Konu sabitlenenlerden çıkarıldı.');
                } else {
                    pinned.unshift(val);
                    if (typeof showToast === 'function') showToast('📌 Konu "Daha Sonra Üret" listesine sabitlendi!');
                }
                saveJsonArray(WIZ_PINNED_TOPICS_KEY, pinned.slice(0, 8));
                renderPinnedTopicsBar();
                updateTopicCounterAndHookBadge();
            });
        }

        // Item 12: Live char/word counter + Item 13: Instant 3 ideas + Item 15: Recent history + Item 19: Pinned bar
        const metaStack = document.createElement('div');
        metaStack.className = 'wiz-topic-meta-stack';
        metaStack.innerHTML = `
            <div class="wiz-topic-char-counter is-neutral" id="wiz-topic-char-counter">0 / 90 karakter · 0 kelime</div>
            <div class="wiz-instant-idea-chips" id="wiz-instant-idea-chips"></div>
            <div class="wiz-pinned-topics-bar hidden" id="wiz-pinned-topics-bar"></div>
            <div class="wiz-topic-history-strip hidden" id="wiz-topic-history-strip"></div>
        `;
        const iconBox = topicField.querySelector('.topic-title-field');
        if (iconBox && iconBox.nextSibling) {
            topicField.insertBefore(metaStack, iconBox.nextSibling);
        } else {
            topicField.appendChild(metaStack);
        }
    }

    // Item 11: Visual Niche Cards + Item 17: Niche Auto-Sync Banner + Item 14: Subtitle Live Preview Pill
    const selectNiche = document.getElementById('select-niche');
    const nicheRow = selectNiche?.closest('.form-row-2');
    if (nicheRow) {
        const nicheCardsWrap = document.createElement('div');
        nicheCardsWrap.id = 'wiz-niche-quick-cards';
        nicheCardsWrap.className = 'wiz-niche-quick-cards';
        nicheCardsWrap.setAttribute('data-wstep', '1');
        nicheRow.parentNode.insertBefore(nicheCardsWrap, nicheRow);

        const autoSyncBar = document.createElement('div');
        autoSyncBar.id = 'wiz-niche-autosync-bar';
        autoSyncBar.className = 'wiz-niche-autosync-bar hidden';
        autoSyncBar.setAttribute('data-wstep', '1');
        nicheRow.parentNode.insertBefore(autoSyncBar, nicheRow.nextSibling);
    }

    const subPresetSel = document.getElementById('select-subtitle-preset');
    if (subPresetSel && subPresetSel.parentElement) {
        const subPreview = document.createElement('div');
        subPreview.id = 'wiz-sub-style-preview-pill';
        subPreview.className = 'wiz-sub-style-preview-pill';
        subPresetSel.parentElement.appendChild(subPreview);
        subPresetSel.addEventListener('change', updateSubtitleLivePreview);
    }

    inputTopic?.addEventListener('input', updateTopicCounterAndHookBadge);
    inputTopic?.addEventListener('change', () => {
        updateTopicCounterAndHookBadge();
        rememberRecentTopic(inputTopic.value);
    });

    selectNiche?.addEventListener('change', () => {
        renderVisualNicheQuickCards();
        renderInstantIdeaChips();
    });

    document.getElementById('btn-quick-lang-tr')?.addEventListener('click', () => setTimeout(updateLangVoiceSyncBadge, 30));
    document.getElementById('btn-quick-lang-en')?.addEventListener('click', () => setTimeout(updateLangVoiceSyncBadge, 30));
    document.getElementById('select-language')?.addEventListener('change', updateLangVoiceSyncBadge);
    document.getElementById('select-tts-voice')?.addEventListener('change', updateLangVoiceSyncBadge);

    updateTopicCounterAndHookBadge();
    renderInstantIdeaChips();
    renderRecentTopicsStrip();
    renderPinnedTopicsBar();
    updateSubtitleLivePreview();
    updateLangVoiceSyncBadge();
    renderVisualNicheQuickCards();
    setTimeout(renderVisualNicheQuickCards, 600);
}

window.initWizardStep1CategoryB = initWizardStep1CategoryB;
document.addEventListener('DOMContentLoaded', initWizardStep1CategoryB);
