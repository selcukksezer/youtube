/**
 * ShortsAI Studio — Navigation & Shell (navigation.js)
 * Handles tab routing, hashchange navigation, theme switcher, hotkeys, and dropzone.
 */


// ══════════════════════════════════════════════════════════════
// 1. TAB ROUTING & NAVIGATION
// ══════════════════════════════════════════════════════════════
const TAB_METADATA = {
    "studio": { title: "Hızlı Üretim Stüdyosu", desc: "Konunuzu belirleyin, 35 niş arasından seçim yapın ve tek tıkla viral Shorts üretin." },
    "clipper": { title: "Uzun Videodan Shorts", desc: "Dosya veya URL. Örtüşen öneri düşer. Kesim 9:16 ve söz sınırında." },
    "timeline": { title: "Sahne & Kurgu Editörü", desc: "AI tarafından üretilen sahneleri, süreleri ve arama terimlerini özelleştirin." },
    "niches": { title: "35 R10 Viral Niş Kütüphanesi", desc: "En çok izlenen ve gelir getiren 35 niş şablonundan birini seçin." },
    "rss-bot": { title: "Oto-Haber & RSS Botu", desc: "Canlı haber kaynaklarını tarayıp anında 45 saniyelik Shorts'a dönüştürün." },
    "batch": { title: "Toplu Üretim & CSV Kuyruğu", desc: "Çoklu konu listesini kuyruğa ekleyin ve 14 günlük ısınma (warm-up) sınırıyla üretin." },
    "growth": { title: "Büyüme, A/B Test & Algoritma Taktikleri", desc: "CTR artıran A/B varyantları, topluluk anketleri ve telif risk denetimi." },
    "effects": { title: "Split-Screen & Görsel FX Stüdyosu", desc: "Bölünmüş ekran oynanış kurgusu, Smart Crop ve Anti-Duplicate koruması." },
    "subtitles": { title: "CapCut Karaoke Altyazı Laboratuvarı", desc: "Kelime kelime yanan neon altyazılar, ön tanımlı profesyonel renk şablonları." },
    "audio": { title: "Ses, SFX & Müzik Konsolu", desc: "Audio Ducking, doğal Türkçe sesler ve geçiş Whoosh/Pop/Ding efektleri." },
    "channels": { title: "Kanal & Otomatik Yayın Dağıtımı", desc: "YouTube API v3 ile planlı yükleme ve TikTok/Reels çapraz paylaşım formatı." },
    "gallery": { title: "Video Galerisi & Arşiv", desc: "Tamamlanan Full HD videolarınızı izleyin, indirin veya kanala yükleyin." },
    "roadmap500": { title: "Yol Haritası", desc: "Sistem özellikleri ve teknik parametrelerin canlı durum gezgini." },
    "settings": { title: "Sistem & API Ayarları", desc: "0 TL maliyet katmanı, kota izleyici ve API anahtarı yönetimi." },
    "kids-song": { title: "Çocuk Şarkı MV Stüdyosu", desc: "Master ses ve sözden Flow klipleri, sonra tek final MP4." }
};

const NAV_COLLAPSIBLE_TABS = {
    'rss-bot': 0, 'batch': 0, 'growth': 0,
    'effects': 1, 'subtitles': 1, 'audio': 1, 'roadmap500': 1,
    'channels': 2, 'gallery': 2, 'settings': 2
};

function syncNavCollapsibles(tabId) {
    document.querySelectorAll('.nav-collapsible').forEach((details, idx) => {
        details.open = NAV_COLLAPSIBLE_TABS[tabId] === idx;
    });
}

function switchTab(tabId, updateHistory = true) {
    if (!tabId || !TAB_METADATA[tabId]) {
        tabId = 'studio';
    }

    const earlyStyle = document.getElementById('early-tab-style');
    if (earlyStyle) earlyStyle.remove();

    syncNavCollapsibles(tabId);

    const buttons = document.querySelectorAll('.nav-btn');
    const panes = document.querySelectorAll('.tab-pane');

    buttons.forEach(btn => {
        btn.classList.toggle('active', btn.getAttribute('data-tab') === tabId);
    });
    panes.forEach(pane => {
        pane.classList.toggle('active', pane.id === `pane-${tabId}`);
    });

    const pageTitle = document.getElementById('current-page-title');
    const pageDesc = document.getElementById('current-page-desc');
    if (TAB_METADATA[tabId]) {
        if (pageTitle) pageTitle.textContent = TAB_METADATA[tabId].title;
        if (pageDesc) pageDesc.textContent = TAB_METADATA[tabId].desc;
    }

    try {
        localStorage.setItem('activeShortsTab', tabId);
        if (updateHistory) {
            if (window.location.hash !== `#${tabId}`) {
                window.location.hash = tabId;
            }
        }
    } catch (e) {}

    // On-demand tab loaders
    if (tabId === 'niches' && (!allNiches || allNiches.length === 0)) {
        if (typeof loadNiches === 'function') loadNiches();
    }
    if (tabId === 'roadmap500' && typeof loadRoadmapItems === 'function') loadRoadmapItems();
    if (tabId === 'rss-bot' && typeof loadRssNews === 'function') loadRssNews();
    if (tabId === 'timeline') timelineReviewed = true;
    if (tabId === 'gallery' && typeof loadGallery === 'function') loadGallery();
    if (tabId === 'settings') {
        if (typeof loadSettings === 'function') loadSettings();
        if (typeof window.loadHardwareSpecs === 'function') window.loadHardwareSpecs();
    }
    if (tabId === 'audio' && typeof loadBgmList === 'function') loadBgmList();
    if (tabId === 'kids-song' && typeof loadKidsSong === 'function') loadKidsSong();
}

window.switchTab = switchTab;

// Global delegated click listener for navigation buttons (guaranteed to catch clicks on icons, text, badges, etc.)
document.addEventListener('click', (e) => {
    const btn = e.target.closest('.nav-btn');
    if (btn) {
        const tab = btn.getAttribute('data-tab');
        if (tab) {
            e.preventDefault();
            switchTab(tab);
        }
    }
});

window.addEventListener('hashchange', () => {
    const hashTab = (window.location.hash || '').replace('#', '').trim();
    if (hashTab && TAB_METADATA[hashTab]) {
        switchTab(hashTab, false);
    }
});

// Sayfa açıldığında veya yenilendiğinde (F5) kalınan sekmeyi EN BAŞTA geri yükle
try {
    const hashTab = (window.location.hash || '').replace('#', '').trim();
    const storedTab = localStorage.getItem('activeShortsTab');
    const targetTab = hashTab || storedTab || 'studio';
    if (targetTab && TAB_METADATA[targetTab]) {
        switchTab(targetTab, false);
    }
} catch (e) {
    console.warn('Tab restore error:', e);
}

// ══════════════════════════════════════════════════════════════
// ÇOCUK ŞARKI MV STÜDYOSU — BİREBİR TAM ENTEGRASYON MANTIĞI
// ══════════════════════════════════════════════════════════════


// ══════════════════════════════════════════════════════════════
// 13. TEMA SEÇİCİ & PERSISTENCE
// ══════════════════════════════════════════════════════════════
const themeDots = document.querySelectorAll('.theme-dot');
function setTheme(colorName) {
    document.body.setAttribute('data-theme', colorName);
    localStorage.setItem('shorts_theme', colorName);
    themeDots.forEach(d => {
        d.classList.toggle('active', d.getAttribute('data-color') === colorName);
    });
}

const savedTheme = localStorage.getItem('shorts_theme') || 'violet';
setTheme(savedTheme);

themeDots.forEach(dot => {
    dot.addEventListener('click', () => {
        const col = dot.getAttribute('data-color');
        if (col) setTheme(col);
    });
});

// ══════════════════════════════════════════════════════════════


// ══════════════════════════════════════════════════════════════
// 17. CSV / METİN SÜRÜKLE-BIRAK (Dropzone)
// ══════════════════════════════════════════════════════════════
const csvDropzone = document.getElementById('csv-dropzone');
const csvFileInput = document.getElementById('csv-file-input');
const batchTextArea = document.getElementById('batch-topics-text');

if (csvDropzone && csvFileInput && batchTextArea) {
    csvDropzone.addEventListener('click', () => csvFileInput.click());

    csvFileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) handleCsvFile(file);
    });

    csvDropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        csvDropzone.classList.add('dragover');
    });

    csvDropzone.addEventListener('dragleave', () => {
        csvDropzone.classList.remove('dragover');
    });

    csvDropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        csvDropzone.classList.remove('dragover');
        const file = e.dataTransfer.files[0];
        if (file) handleCsvFile(file);
    });

    function handleCsvFile(file) {
        const reader = new FileReader();
        reader.onload = (evt) => {
            const text = evt.target.result;
            const lines = text.split(/\r?\n/).map(l => l.trim()).filter(Boolean);
            batchTextArea.value = lines.join('\n');
            showToast(`📂 ${lines.length} adet konu başarıyla yüklendi!`);
        };
        reader.readAsText(file);
    }
}

// ══════════════════════════════════════════════════════════════


// 18. KLAVYE KISAYOLLARI (Power User Hotkeys)
// ══════════════════════════════════════════════════════════════
document.addEventListener('keydown', (e) => {
    // Form girdilerinde iken kısayolları engelleme kontrolü
    const isInput = ['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName);

    // Ctrl+Enter veya Cmd+Enter: Hızlı Render
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        btnQuickRender?.click();
        return;
    }

    // Escape: Terminal konsolunu kapat
    if (e.key === 'Escape') {
        terminalPanel?.classList.add('hidden');
        return;
    }

    // Alt + 1-8 Sekme Geçişi
    if (!isInput && e.altKey && e.key >= '1' && e.key <= '8') {
        const tabKeys = ["studio", "timeline", "niches", "rss-bot", "batch", "growth", "effects", "subtitles"];
        const idx = parseInt(e.key) - 1;
        if (tabKeys[idx]) {
            e.preventDefault();
            switchTab(tabKeys[idx]);
        }
    }
});

// ══════════════════════════════════════════════════════════════

