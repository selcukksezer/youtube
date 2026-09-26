/**
 * ShortsAI Studio — Studio & Script Generation (studio.js)
 * Handles topic suggestion, prompt enhancement, viral hooks, script generation, quick action strip and Kids Song integration.
 */


let kidsSongTimer = null;
let kidsSongBaseUrl = 'http://127.0.0.1:3210';
let currentStudioRoute = '/cocuk-sarki';
let isKidsStudioBooting = false;

function getStudioFullUrl(route) {
    const cleanBase = kidsSongBaseUrl.replace(/\/$/, '');
    const target = route || currentStudioRoute || '/cocuk-sarki';
    const cleanRoute = target.startsWith('/') ? target : '/' + target;
    return cleanBase + cleanRoute;
}

function setStudioRoute(route) {
    currentStudioRoute = route;
    document.querySelectorAll('.btn-studio-nav').forEach(btn => {
        btn.classList.toggle('active', btn.getAttribute('data-studio-route') === route);
    });
    const frame = document.getElementById('kids-song-frame');
    if (frame) {
        frame.src = getStudioFullUrl(route);
    }
}

async function refreshKidsSong() {
    const badgeEl = document.getElementById('kids-song-badge');
    const statusEl = document.getElementById('kids-song-status');
    const offlineScreen = document.getElementById('kids-song-offline-screen');
    const frameContainer = document.getElementById('kids-song-frame-container');
    const frame = document.getElementById('kids-song-frame');
    const startBtn = document.getElementById('btn-kids-song-start');
    const stopBtn = document.getElementById('btn-kids-song-stop');
    const placeholderTitle = document.getElementById('kids-placeholder-title');
    const placeholderDesc = document.getElementById('kids-placeholder-desc');
    const noteEl = document.getElementById('kids-song-note');

    if (!badgeEl) return;

    try {
        const res = await fetch('/api/kids-song/status');
        const data = await res.json();
        if (data.url) kidsSongBaseUrl = data.url;

        if (data.running) {
            isKidsStudioBooting = false;
            badgeEl.className = 'badge-status status-online';
            badgeEl.textContent = '● Çevrimiçi';
            if (statusEl) statusEl.textContent = `Stüdyo motoru aktif (Port ${data.port || 3210})`;
            
            if (offlineScreen) offlineScreen.style.display = 'none';
            if (frameContainer) frameContainer.style.display = 'block';
            if (startBtn) startBtn.style.display = 'none';
            if (stopBtn) stopBtn.style.display = 'inline-flex';

            if (frame) {
                const expected = getStudioFullUrl(currentStudioRoute);
                if (!frame.src || frame.src === 'about:blank') {
                    frame.src = expected;
                }
            }
        } else if (isKidsStudioBooting || data.managed) {
            badgeEl.className = 'badge-status status-starting';
            badgeEl.textContent = '● Başlatılıyor...';
            if (statusEl) statusEl.textContent = 'Stüdyo hazırlanıyor, Next.js derleniyor...';
            
            if (offlineScreen) offlineScreen.style.display = 'flex';
            if (frameContainer) frameContainer.style.display = 'none';
            if (placeholderTitle) placeholderTitle.textContent = 'Çocuk Şarkı Stüdyosu Başlatılıyor...';
            if (placeholderDesc) placeholderDesc.textContent = 'Google Flow ve Suno MV motoru açılıyor. İlk açılış 20-30 saniye sürebilir.';
            if (startBtn) startBtn.style.display = 'none';
            if (stopBtn) stopBtn.style.display = 'inline-flex';
        } else {
            badgeEl.className = 'badge-status status-offline';
            badgeEl.textContent = '● Çevrimdışı';
            if (statusEl) statusEl.textContent = data.message || 'Stüdyo kapalı';

            if (offlineScreen) offlineScreen.style.display = 'flex';
            if (frameContainer) frameContainer.style.display = 'none';
            if (placeholderTitle) placeholderTitle.textContent = 'Çocuk Şarkı Stüdyosu Kapalı';
            if (placeholderDesc) placeholderDesc.textContent = 'Tek tıkla stüdyoyu başlatın; Google Flow & Suno MV motoru tam entegre çalışır.';
            if (startBtn) startBtn.style.display = 'inline-flex';
            if (stopBtn) stopBtn.style.display = 'none';
        }

        if (noteEl) {
            noteEl.textContent = data.log_tail ? `Son log: ${data.log_tail}` : '';
        }

        // Sol menüdeki proje sayısını dinamik güncelle
        try {
            const pRes = await fetch('/api/kids-song/projects');
            const pData = await pRes.json();
            const navBadge = document.getElementById('badge-kids-song-count');
            if (navBadge && pData.projects) {
                const count = pData.projects.length;
                navBadge.textContent = count;
                navBadge.style.display = count > 0 ? 'inline-block' : 'none';
            }
        } catch (e) {}
    } catch (err) {
        badgeEl.className = 'badge-status status-offline';
        badgeEl.textContent = '● Bağlantı Hatası';
        if (statusEl) statusEl.textContent = 'Arka plan durum sorgusu başarısız.';
    }
}

async function triggerKidsStudioStart() {
    isKidsStudioBooting = true;
    refreshKidsSong();
    try {
        const res = await fetch('/api/kids-song/start', { method: 'POST' });
        const data = await res.json();
        if (data.ok && data.url) kidsSongBaseUrl = data.url;
    } catch (err) {
        console.error('Stüdyo başlatma hatası:', err);
    }
    setTimeout(refreshKidsSong, 1500);
}

function loadKidsSong() {
    refreshKidsSong();
    // Otomatik Başlatma: Kullanıcı sekmeye geldiğinde stüdyo kapalıysa kendiliğinden aç
    fetch('/api/kids-song/status')
        .then(res => res.json())
        .then(data => {
            if (!data.running && !isKidsStudioBooting && !data.managed) {
                triggerKidsStudioStart();
            }
        })
        .catch(() => {});

    if (!kidsSongTimer) {
        kidsSongTimer = setInterval(() => {
            const pane = document.getElementById('pane-kids-song');
            if (pane && pane.classList.contains('active')) {
                refreshKidsSong();
            }
        }, 3000);
    }
}

// Buton Event Listeners
document.querySelectorAll('.btn-studio-nav').forEach(btn => {
    btn.addEventListener('click', () => {
        const route = btn.getAttribute('data-studio-route');
        if (route) setStudioRoute(route);
    });
});

document.getElementById('btn-kids-song-start')?.addEventListener('click', triggerKidsStudioStart);
document.getElementById('btn-kids-placeholder-start')?.addEventListener('click', triggerKidsStudioStart);

document.getElementById('btn-kids-song-stop')?.addEventListener('click', async () => {
    isKidsStudioBooting = false;
    try {
        await fetch('/api/kids-song/stop', { method: 'POST' });
    } catch (err) {
        console.error(err);
    }
    refreshKidsSong();
});

document.getElementById('btn-kids-song-reload')?.addEventListener('click', () => {
    const frame = document.getElementById('kids-song-frame');
    if (frame) {
        frame.src = getStudioFullUrl(currentStudioRoute);
    }
    refreshKidsSong();
});

document.getElementById('btn-kids-song-keys')?.addEventListener('click', async () => {
    const statusEl = document.getElementById('kids-song-status');
    if (statusEl) statusEl.textContent = 'API anahtarları aktarılıyor...';
    try {
        const res = await fetch('/api/kids-song/settings/transfer', { method: 'POST' });
        const data = await res.json();
        if (statusEl) statusEl.textContent = data.message || 'Anahtarlar stüdyoya başarıyla aktarıldı!';
    } catch (err) {
        if (statusEl) statusEl.textContent = 'Ayar aktarımı başarısız.';
    }
});

document.getElementById('btn-kids-song-import')?.addEventListener('click', async () => {
    const statusEl = document.getElementById('kids-song-status');
    if (statusEl) statusEl.textContent = 'Tamamlanan video galeriye aktarılıyor...';
    try {
        const listRes = await fetch('/api/kids-song/projects');
        const listData = await listRes.json();
        const projects = (listData.projects || []);
        const readyProject = projects.find(p => p.status === 'completed' || p.label === 'render bitti') || projects[0];

        if (!readyProject) {
            if (statusEl) statusEl.textContent = 'Aktarılacak tamamlanmış bir video bulunamadı.';
            return;
        }

        const impRes = await fetch('/api/kids-song/projects/' + encodeURIComponent(readyProject.id) + '/import', { method: 'POST' });
        const impData = await impRes.json();
        if (impData.ok) {
            if (statusEl) statusEl.textContent = `Video başarıyla galeriye aktarıldı: ${impData.filename}`;
            if (typeof loadGalleryVideos === 'function') loadGalleryVideos();
            if (typeof renderGallery === 'function') renderGallery();
        } else {
            if (statusEl) statusEl.textContent = impData.error || 'Galeriye aktarılamadı (Final video henüz hazır değil).';
        }
    } catch (err) {
        if (statusEl) statusEl.textContent = 'Galeriye aktarma işlemi başarısız.';
    }
});

// AI Çocuk Şarkısı Söz ve Konsept Sihirbazı
const wizardModal = document.getElementById('modal-kids-ai-wizard');
const wizardOpenBtn = document.getElementById('btn-kids-ai-wizard');
const wizardCloseBtn = document.getElementById('btn-close-kids-wizard');
const wizardRunBtn = document.getElementById('btn-run-kids-wizard');
const wizardCreateBtn = document.getElementById('btn-kids-wizard-create');
const wizardResultArea = document.getElementById('kids-ai-result-area');

wizardOpenBtn?.addEventListener('click', () => {
    if (wizardModal) wizardModal.style.display = 'flex';
});

wizardCloseBtn?.addEventListener('click', () => {
    if (wizardModal) wizardModal.style.display = 'none';
});

document.querySelectorAll('.badge-preset').forEach(preset => {
    preset.addEventListener('click', () => {
        const topicInput = document.getElementById('kids-ai-topic');
        if (topicInput) {
            topicInput.value = preset.getAttribute('data-preset') || '';
            topicInput.focus();
        }
    });
});

wizardRunBtn?.addEventListener('click', async () => {
    const topic = document.getElementById('kids-ai-topic')?.value || 'Sevimli Hayvanlar';
    const ageGroup = document.getElementById('kids-ai-age')?.value || '3-5';
    const mood = document.getElementById('kids-ai-mood')?.value || 'Neşeli ve Enerjik';
    
    wizardRunBtn.disabled = true;
    wizardRunBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Yapay Zeka Şarkı Yazıyor...';

    try {
        const res = await fetch('/api/kids-song/generate-song-idea', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topic, age_group: ageGroup, mood })
        });
        const data = await res.json();
        if (data.ok && data.idea) {
            const idea = data.idea;
            const titleEl = document.getElementById('kids-ai-title');
            const lyricsEl = document.getElementById('kids-ai-lyrics');
            const sunoEl = document.getElementById('kids-ai-suno');

            if (titleEl) titleEl.value = idea.title || `${topic} Şarkısı`;
            if (lyricsEl) lyricsEl.value = idea.lyrics || '';
            if (sunoEl) sunoEl.value = idea.suno_prompt || '';

            if (wizardResultArea) wizardResultArea.style.display = 'block';
        }
    } catch (err) {
        console.error('AI Şarkı üretme hatası:', err);
    } finally {
        wizardRunBtn.disabled = false;
        wizardRunBtn.innerHTML = '<i class="fa-solid fa-sparkles"></i> Yeniden Üret';
    }
});

wizardCreateBtn?.addEventListener('click', async () => {
    const title = document.getElementById('kids-ai-title')?.value || 'Yeni Çocuk Şarkısı';
    const topic = document.getElementById('kids-ai-topic')?.value || '';
    const lyrics = document.getElementById('kids-ai-lyrics')?.value || '';

    wizardCreateBtn.disabled = true;
    wizardCreateBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Proje Açılıyor...';

    try {
        const res = await fetch('/api/kids-song/projects', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, topic, lyrics })
        });
        const data = await res.json();
        if (data.ok && data.project) {
            if (wizardModal) wizardModal.style.display = 'none';
            const frame = document.getElementById('kids-song-frame');
            if (frame) {
                frame.src = getStudioFullUrl(data.project.render_path || '/cocuk-sarki');
            }
            const statusEl = document.getElementById('kids-song-status');
            if (statusEl) statusEl.textContent = `Proje başarıyla açıldı: ${title}`;
            refreshKidsSong();
        }
    } catch (err) {
        console.error('Proje açma hatası:', err);
    } finally {
        wizardCreateBtn.disabled = false;
        wizardCreateBtn.innerHTML = '<i class="fa-solid fa-circle-check"></i> Bu Şarkıyla Stüdyoda Proje Başlat';
    }
});



// ══════════════════════════════════════════════════════════════
// 9. SENARYO ÜRETİMİ & EDİTÖR
// ══════════════════════════════════════════════════════════════
document.getElementById('btn-new-topic')?.addEventListener('click', clearCurrentScenario);

async function generateScriptFromTopic({ forceRegenerate = false } = {}) {
    const topic = (inputTopic?.value || '').trim();
    if (!topic) {
        alert('Lütfen bir video konusu girin!');
        inputTopic?.focus();
        return;
    }

    const planTopic = (currentPlan?.title || currentPlan?.topic || currentPlan?.keyword || '').trim();
    const topicChanged = hasExistingPlan() && planTopic && (topic.toLowerCase() !== planTopic.toLowerCase());

    if (!forceRegenerate && hasExistingPlan() && !topicChanged && !planHasBrokenNarration(currentPlan)) {
        navigateToScenario();
        return;
    }

    const btnRegenerateStudio = document.getElementById('btn-regenerate-script-studio');
    const btnRegenerateTimeline = document.getElementById('btn-regenerate-scenario');

    if (btnCreateScript) {
        btnCreateScript.disabled = true;
        btnCreateScript.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> AI Senaryosu Yazılıyor...';
    }
    if (btnRegenerateStudio) {
        btnRegenerateStudio.disabled = true;
        btnRegenerateStudio.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Yazılıyor...';
    }
    if (btnRegenerateTimeline) {
        btnRegenerateTimeline.disabled = true;
    }

    showToast('AI senaryoyu oluşturuyor — sahneler ve kancalar hazırlanıyor...');

    if (!userManuallyPickedNiche && !selectNiche?.value) {
        await resolveAndApplyNicheFromTopic({ toast: false });
    }

    try {
        const res = await fetch('/api/script/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                keyword: topic,
                language: selectLanguage?.value || 'tr',
                niche: selectNiche?.value || '6_stoic_philosophy',
                reddit_post: selectedRedditPost,
                format_fingerprint: pendingFormatFingerprint || undefined
            })
        });
        const data = await res.json();
        if (data.status === 'ok') {
            let plan = data.plan;
            const lockedNiche = plan.niche_id || plan.niche_profile?.id;
            if (lockedNiche && selectNiche && selectNiche.value !== lockedNiche) {
                selectNiche.value = lockedNiche;
                await applyNicheProfile(lockedNiche);
            }
            if (lockedNiche) {
                const lockedName = allNiches.find(n => n.id === lockedNiche)?.name || lockedNiche;
                showNicheLockBadge(lockedNiche, lockedName);
            }
            timelineReviewed = false;
            setCurrentPlan(plan, { skipQualityPanel: true });
            if (data.plagiarism) applyPlagiarismBadge(data.plagiarism);
            if (data.hook_variants?.variants?.length) {
                plan.hook_variants = data.hook_variants.variants;
            }
            const validation = await updateStudioQualityPanel(plan);
            if (validation?.plan) plan = validation.plan;
            if (data.plagiarism) applyPlagiarismBadge(data.plagiarism);

            renderTimelineScenes(plan);
            persistCurrentPlan();
            saveStudioSettings();

            showToast(forceRegenerate ? 'Senaryo başarıyla yeniden yazıldı' : 'Senaryo hazır — timeline\'da inceleyin');
            updateFlowRail('timeline');
            switchTab('timeline');
        } else {
            const errMsg = data.detail || data.error || data.message || 'Senaryo oluşturulamadı.';
            alert('Senaryo oluşturulamadı: ' + errMsg);
        }
    } catch (err) {
        alert('Hata: ' + err.message);
    } finally {
        if (btnCreateScript) btnCreateScript.disabled = false;
        if (btnRegenerateStudio) btnRegenerateStudio.disabled = false;
        if (btnRegenerateTimeline) btnRegenerateTimeline.disabled = false;
        updateScriptActionButtons();
    }
}

(btnCreateScript || document.getElementById('btn-create-script'))?.addEventListener('click', () => generateScriptFromTopic());
document.getElementById('btn-regenerate-script-studio')?.addEventListener('click', () => generateScriptFromTopic({ forceRegenerate: true }));
document.getElementById('btn-regenerate-scenario')?.addEventListener('click', () => generateScriptFromTopic({ forceRegenerate: true }));

// ══════════════════════════════════════════════════════════════
// 9A. SAHNE & KURGU EDİTÖRÜ — 500 Madde Uyumlu Overhaul
// ══════════════════════════════════════════════════════════════

// Helper: Detect emojis in text (Madde 125)


// ══════════════════════════════════════════════════════════════
// 14. VİRAL KONU BANKASI & KONU ÖNERİCİ (Item 1-35)
// ══════════════════════════════════════════════════════════════
// 15. VIRAL KONU HAVUZU & VARYASYONLAR (Items 306 - 325)
// ══════════════════════════════════════════════════════════════
const VIRAL_TOPIC_BANK = {
    "1_news_flash": [
        "Tüm Dünyayı Sarsan Son Dakika Açıklaması!",
        "Uzmanlar Uyardı: Bu Hafta Başlayan Kritik Gelişme!",
        "Teknoloji Dünyasında Deprem Yaratan Flaş Karar!",
        "Tüm Piyasaları Altüst Eden Beklenmedik Olay!"
    ],
    "2_reddit_confessions": [
        "AITA: Düğünü Terk Eden Nişanlıma Verdiğim Cevap",
        "Gizli Sırrımı 5 Yıl Sonra İtiraf Etmek Zorunda Kaldım...",
        "İş Yerindeki En Büyük Skandalı Ortaya Çıkardığım Gün",
        "Ailemin Benden Sakladığı Büyük Gerçeği Öğrendim"
    ],
    "3_split_gameplay": [
        "Tarihin En İnanılmaz Kaçış Hikayesi",
        "Bu Gizemli Olayı Çözen Kimse Çıkmadı!",
        "Yeraltı Tünellerinde Kaybolan Adamın Hikayesi",
        "Dünyanın En Tehlikeli Yollarında Yaşananlar"
    ],
    "4_would_you_rather": [
        "Geleceği Görmek mi, Geçmişi Değiştirmek mi? (%90 Zorlandı)",
        "Sonsuz Para mı, Sonsuz Sağlık mı? Zorlu Tercih Düellosu",
        "Asla Uyumamak mı, Asla Yemek Yememek mi?",
        "Zihin Okuma Yeteneği mi, Görünmezlik mi?"
    ],
    "5_guess_flag_country": [
        "Sadece Gerçek Coğrafya Dahileri Bu 3 Bayrağı Bilebiliyor!",
        "Bu Başkent Hangi Ülkeye Ait? (%95 Yanıldı)",
        "5 Saniyede Ülkeyi Tahmin Et: Dünya Bayrakları Quiz",
        "Hangi Ülkenin Para Birimi? Testi Geçebilecek Misin?"
    ],
    "6_stoic_philosophy": [
        "Marcus Aurelius'un Öfkeyi Yok Eden 3 Stoacı Kuralı",
        "Seneca: Zamanını Çalan İnsanlardan Kurtulmanın 4 Yolu",
        "Epiktetos'un Zihinsel Dayanıklılık Formülü: Asla Şikayet Etme",
        "Hiçbir Şeyi Kafana Takmamanın 3 Stoacı Sırrı"
    ],
    "7_dark_psychology": [
        "3 Dark Psychology Secrets Manipulation Experts Never Tell You",
        "İnsanların Yalan Söylediğini Ele Veren 3 Mikro İpucu",
        "Manipülasyon Ustalarının Kullandığı Ters Psikoloji Tuzağı",
        "Sohbette Üstünlük Kurmanızı Sağlayan 3 Sessizlik Kuralı"
    ],
    "8_crypto_market": [
        "Bitcoin Halving Sonrası Zengin Eden 3 Döngü Kuralı",
        "Kripto Balinalarının Topladığı 3 Gizli Altcoin",
        "Fakir İnsanların Yaptığı ve Asla Zengin Olamadıkları 4 Hata",
        "Bileşik Getirinin Gücü: Günde 1 Dolarla Nasıl Portföy Büyütülür?"
    ],
    "9_five_facts": [
        "Dünya Hakkında Asla Bilmediğiniz 5 Şaşırtıcı Gerçek",
        "Tarihin En Tuhaf 5 Rastlantısı",
        "İnsan Vücudunun Bilinmeyen 5 Gizli Özelliği",
        "Okyanusların En Derin Noktasındaki 5 Korkutucu Sır"
    ],
    "27_common_myths_busted": [
        "Herkesin Doğru Bildiği 5 Büyük Bilimsel Yanılgı!",
        "Yıllardır İnanılan ve Tamamen Yalan Olan 4 Şehir Efsanesi",
        "Tarih Kitaplarında Yanlış Anlatılan 3 Büyük Olay",
        "Sağlık Konusunda Doğru Sanılan 5 Tehlikeli Yanılgı"
    ],
    "general": [
        "Herkesin Doğru Bildiği 5 Büyük Bilimsel Yanılgı!",
        "Günde Sadece 10 Dakika Yaparak Hayatını Değiştirecek Alışkanlık",
        "Milyonerlerin Sabah Rutinindeki 3 Gizli Adım",
        "Bilinçaltının Çalışma Prensibi: Neden Hep Aynı Hatayı Yapıyoruz?"
    ]
};

// Konu Öner — wired after escapeHtml (see topic suggest panel block below)

function autoDetectNicheFromTopicLocal() {
    const topicText = (inputTopic?.value || '').trim().toLowerCase();
    if (!topicText || !selectNiche) return null;

    let targetId = null;
    if (/stoa|marcus|aurelius|seneca|epiktetos|stoac/.test(topicText)) targetId = '6_stoic_philosophy';
    else if (/whatsapp|mesajlaşma|mesaj hikay|chat story|sohbet ekran/.test(topicText)) targetId = '20_whatsapp_chat_story';
    else if (/yanılgı|mit |efsane|yanlış bilinen|doğru bilinen|bilimsel/.test(topicText)) targetId = '27_common_myths_busted';
    else if (/karanlık psikoloji|manipülasyon|manipulation|dark psychology/.test(topicText)) targetId = '7_dark_psychology';
    else if (/kripto|bitcoin|borsa|altın|hisse|dolar|enflasyon/.test(topicText)) targetId = '8_crypto_market';
    else if (/\d+\s+(?:büyük|ilginç|önemli|sır|kural|adım|ipucu)|şaşırtıcı gerçek/.test(topicText)) targetId = '9_five_facts';
    else if (/aita|itiraf|confession|reddit/.test(topicText)) targetId = '2_reddit_confessions';
    else if (/tercih et|would you rather/.test(topicText)) targetId = '4_would_you_rather';
    else if (/bayrak|ülke tahmin|hangi ülke/.test(topicText)) targetId = '5_guess_flag_country';
    else if (/paranormal|ufo|bermuda|51\.\s*bölge|gizem.*korku/.test(topicText)) targetId = '13_mystery_paranormal';
    else if (/son dakika|flaş|haber|deprem|kaza|trafik/.test(topicText)) targetId = '1_news_flash';
    return targetId;
}

async function resolveAndApplyNicheFromTopic({ toast = true } = {}) {
    const topicText = (inputTopic?.value || '').trim();
    if (!topicText || !selectNiche) return null;
    if (userManuallyPickedNiche) {
        applyNichePanelVisibility(selectNiche.value);
        return selectNiche.value;
    }

    const currentNiche = selectNiche.value || '1_news_flash';
    let targetId = null;
    let nicheName = '';

    try {
        const res = await fetch(
            `/api/niches/resolve-from-topic?topic=${encodeURIComponent(topicText)}&niche=${encodeURIComponent(currentNiche)}`
        );
        if (res.ok) {
            const data = await res.json();
            targetId = data.resolved_niche || currentNiche;
            nicheName = data.niche_name || targetId;
        }
    } catch (err) {
        console.warn('Niş çözümleme API hatası, yerel eşleştirme kullanılıyor:', err);
    }

    if (!targetId) {
        targetId = autoDetectNicheFromTopicLocal();
        nicheName = allNiches.find(n => n.id === targetId)?.name || targetId || '';
    }

    if (!targetId) {
        applyNichePanelVisibility(currentNiche);
        return currentNiche;
    }

    const opt = selectNiche.querySelector(`option[value="${targetId}"]`);
    if (!opt) {
        applyNichePanelVisibility(currentNiche);
        return currentNiche;
    }

    const changed = selectNiche.value !== targetId;
    if (changed) {
        selectNiche.value = targetId;
        await applyNicheProfile(targetId);
        showNicheLockBadge(targetId, nicheName || opt.textContent);
        if (toast) {
            showToast(`Niş otomatik: ${nicheName || opt.textContent} (konu uyumu)`);
        }
    } else {
        applyNichePanelVisibility(targetId);
        updateLoopBridge(targetId, topicText);
        showNicheLockBadge(targetId, nicheName || opt.textContent);
    }

    return targetId;
}

function scheduleNicheResolveFromTopic() {
    clearTimeout(nicheResolveTimer);
    nicheResolveTimer = setTimeout(() => {
        resolveAndApplyNicheFromTopic({ toast: true }).catch(() => {});
    }, 350);
}

inputTopic?.addEventListener('input', () => {
    if (!suppressFingerprintClear) clearPendingFormatFingerprint();
    suppressFingerprintClear = false;
    updateFlowRail('topic');
    updateLoopBridge(selectNiche ? selectNiche.value : '6_stoic_philosophy', inputTopic.value);
    updateScriptActionButtons();
    saveStudioSettings();
    if (!userManuallyPickedNiche) scheduleNicheResolveFromTopic();
});
inputTopic?.addEventListener('change', () => {
    updateScriptActionButtons();
    saveStudioSettings();
    if (!userManuallyPickedNiche) resolveAndApplyNicheFromTopic({ toast: true });
});
inputTopic?.addEventListener('blur', () => {
    saveStudioSettings();
    if (!userManuallyPickedNiche) resolveAndApplyNicheFromTopic({ toast: true });
});




let lastTopicSuggestions = [];

function renderTopicSuggestCards(suggestions, nicheName) {
    const panel = document.getElementById('topic-suggest-panel');
    const body = document.getElementById('topic-suggest-body');
    const titleEl = document.getElementById('topic-suggest-title');
    if (!panel || !body) return;
    lastTopicSuggestions = suggestions || [];
    panel.classList.remove('hidden');
    if (titleEl && nicheName) {
        titleEl.innerHTML = `<i class="fa-solid fa-wand-magic-sparkles"></i> ${escapeHtml(nicheName)} — 5 Konu Önerisi`;
    }
    if (!suggestions || !suggestions.length) {
        body.innerHTML = '<div class="topic-suggest-empty">Bu niş için uygun konu bulunamadı. Yeniden deneyin.</div>';
        return;
    }
    body.innerHTML = suggestions.map((s, idx) => {
        const src = TOPIC_SOURCE_LABELS[s.source] || TOPIC_SOURCE_LABELS.ai;
        const hook = s.hook ? `<div class="topic-suggest-card-hook">${escapeHtml(s.hook)}</div>` : '';
        return `
            <button type="button" class="topic-suggest-card" data-suggest-idx="${idx}">
                <div class="topic-suggest-card-title">${idx + 1}. ${escapeHtml(s.title)}</div>
                ${hook}
                <div class="topic-suggest-card-meta">
                    <span class="topic-suggest-badge ${src.cls}"><i class="${src.icon}"></i> ${src.label}</span>
                    <span class="topic-suggest-score">Uygunluk ${s.confidence || s.relevance || 0}/100</span>
                </div>
            </button>`;
    }).join('');
    body.querySelectorAll('.topic-suggest-card').forEach(card => {
        card.addEventListener('click', () => {
            const idx = Number(card.dataset.suggestIdx);
            const picked = lastTopicSuggestions[idx];
            if (!picked) return;
            inputTopic.value = picked.title;
            setPendingFormatFingerprint(picked.format_fingerprint || null);
            updateLoopBridge(selectNiche?.value || '1_news_flash', picked.title);
            resolveAndApplyNicheFromTopic({ toast: false }).catch(() => {});
            panel.classList.add('hidden');
            showToast(`Konu seçildi: ${picked.title.slice(0, 60)}${picked.title.length > 60 ? '…' : ''}`);
        });
    });
}

async function suggestTopic(ev) {
    const isRetry = ev && (ev.target?.id === 'btn-retry-topic-suggest' || ev.currentTarget?.id === 'btn-retry-topic-suggest');
    const nicheId = selectNiche?.value;
    const panel = document.getElementById('topic-suggest-panel');
    const body = document.getElementById('topic-suggest-body');
    const btn = document.getElementById('btn-suggest-topic');
    if (!nicheId) {
        showToast('Önce bir niş şablonu seçin.', 'warn');
        return;
    }
    const language = document.getElementById('select-language')?.value || 'tr';
    const rawHint = (inputTopic?.value || '').trim();
    const topicHint = (!isRetry && rawHint && !rawHint.includes('Marcus Aurelius')) ? rawHint : undefined;
    if (panel) panel.classList.remove('hidden');
    if (body) body.innerHTML = '<div class="topic-suggest-loading"><i class="fa-solid fa-spinner fa-spin"></i> Yeni ve benzersiz konular araştırılıyor…</div>';
    if (btn) {
        btn.classList.add('is-loading');
        btn.disabled = true;
    }
    try {
        const res = await fetch('/api/topics/suggest', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                niche_id: nicheId,
                language,
                count: 5,
                topic_hint: topicHint,
                refresh: true,
            }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Konu önerileri alınamadı.');
        renderTopicSuggestCards(data.suggestions, data.niche_name);
    } catch (err) {
        if (body) body.innerHTML = `<div class="topic-suggest-error">${escapeHtml(err.message || 'Bağlantı hatası')}</div>`;
        console.error('Konu öner hatası:', err);
    } finally {
        if (btn) {
            btn.classList.remove('is-loading');
            btn.disabled = false;
        }
    }
}

document.getElementById('btn-suggest-topic')?.addEventListener('click', suggestTopic);
document.getElementById('btn-retry-topic-suggest')?.addEventListener('click', suggestTopic);
document.getElementById('btn-close-topic-suggest')?.addEventListener('click', () => {
    document.getElementById('topic-suggest-panel')?.classList.add('hidden');
});

async function applyNicheProfile(nicheId) {
    const profileBox = document.getElementById('niche-production-profile');
    if (!nicheId || !profileBox) return;
    try {
        const response = await fetch(`/api/niches/${encodeURIComponent(nicheId)}/profile`);
        const data = await response.json();
        const profile = data.profile;
        if (!profile) return;
        const rules = profile.production_rules || {};
        if (!splitTouched && chkSplitScreen) {
            chkSplitScreen.checked = Boolean(rules.split_screen);
        }
        chkKenBurns.checked = Boolean(rules.ken_burns);
        if (rules.subtitle_preset && selectSubPreset) selectSubPreset.value = rules.subtitle_preset;
        profileBox.innerHTML = `
            <div style="display: flex; justify-content: space-between; gap: 8px; align-items: center;">
                <strong style="font-size: 12px; color: #67e8f9;"><i class="fa-solid fa-sliders"></i> Aktif Niş Profili: ${escapeHtml(profile.name)}</strong>
                <span class="niche-tag">${escapeHtml(profile.category)}</span>
            </div>
            <div style="font-size: 11px; color: #cbd5e1; margin-top: 6px;">Ton: ${escapeHtml(profile.tone)}</div>
            <div style="font-size: 11px; color: #94a3b8; margin-top: 4px;">${rules.split_screen ? 'Split-screen' : 'Tam ekran'} · ${escapeHtml(rules.subtitle_preset)} altyazı · Dinamik hareket · Neon ilerleme</div>
        `;
        updateLoopBridge(nicheId, inputTopic.value);
        applyNichePanelVisibility(nicheId);
        const gapField = document.getElementById('content-gap-topics');
        if (gapField && Array.isArray(profile.content_gap_examples) && profile.content_gap_examples.length) {
            gapField.placeholder = profile.content_gap_examples.map(line => `Örn: ${line}`).join('\n');
        }
    } catch (error) {
        profileBox.textContent = 'Niş üretim profili yüklenemedi.';
        console.error('Niş profili yükleme hatası:', error);
    }
}

document.getElementById('btn-load-niche-trends')?.addEventListener('click', async (event) => {
    const nicheId = selectNiche?.value;
    const results = document.getElementById('niche-trends-results');
    if (!nicheId || !results) return;
    const button = event.currentTarget;
    button.disabled = true;
    button.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Araştırılıyor';
    try {
        const response = await fetch(`/api/niches/${encodeURIComponent(nicheId)}/trends?region=TR`);
        const data = await response.json();
        results.style.display = 'block';
        if (data.status !== 'ok') {
            results.innerHTML = `<div class="alert-info-box"><i class="fa-solid fa-key"></i><span>${escapeHtml(data.reason || 'Trend verisi alınamadı.')}</span></div>`;
            return;
        }
        const isRealYoutube = Boolean(data.is_real_youtube);
        const badgeIcon = isRealYoutube ? 'fa-brands fa-youtube' : 'fa-solid fa-wand-magic-sparkles';
        const badgeBg = isRealYoutube ? 'rgba(30,58,138,0.4)' : 'rgba(88,28,135,0.35)';
        const badgeBorder = isRealYoutube ? 'rgba(96,165,250,0.3)' : 'rgba(192,132,252,0.35)';
        const badgeColor = isRealYoutube ? '#93c5fd' : '#e9d5ff';
        const sourceBadge = data.source_label ?
            `<div style="display:inline-flex; align-items:center; gap:6px; background:${badgeBg}; border:1px solid ${badgeBorder}; color:${badgeColor}; padding:4px 10px; border-radius:6px; font-size:11px; margin-bottom:8px;">
                <i class="${badgeIcon}"></i> <span>${escapeHtml(data.source_label)}</span>
            </div>` : '';
        lastTrendResults = data.trends || [];
        trendFormatFingerprintAggregate = data.format_fingerprint || null;
        const listIntro = isRealYoutube
            ? 'Son 24 saatte yayınlanan, görüntülenmeye göre sıralı YouTube başlık sinyalleri (tıklayarak konuya aktarın):'
            : 'YouTube verisi bulunamadı — nişe uygun AI başlık önerileri (tıklayarak konuya aktarın):';
        results.innerHTML = `
            ${sourceBadge}
            <div style="font-size: 11px; color: #67e8f9; margin: 2px 0 8px 0;">${listIntro}</div>
            ${lastTrendResults.map((trend, index) => {
                const viewsStr = trend.view_count_text || (typeof trend.view_count === 'number' && trend.view_count > 0 ? Number(trend.view_count).toLocaleString('tr-TR') + ' görüntülenme' : '');
                const metaLine = isRealYoutube && trend.channel
                    ? `<i class="fa-brands fa-youtube text-danger" style="margin-right:3px;"></i>${escapeHtml(trend.channel)}${viewsStr ? ` · ${escapeHtml(viewsStr)}` : ''}`
                    : `<i class="fa-solid fa-wand-magic-sparkles" style="margin-right:3px; color:#c4b5fd;"></i>AI öneri`;
                return `
                <button class="trend-topic-option" data-topic="${escapeHtml(trend.title)}" data-trend-index="${index}" style="display:block; width:100%; text-align:left; padding:9px 12px; margin-bottom:6px; border-radius:6px; background:rgba(15,23,42,.75); border:1px solid rgba(148,163,184,.18); color:#e2e8f0; cursor:pointer; transition:all 0.15s ease;">
                    <strong style="font-size:12px; color:#f8fafc;">${index + 1}. ${escapeHtml(trend.title)}</strong><br>
                    <span style="font-size:10px; color:#94a3b8;">${metaLine}</span>
                </button>
                `;
            }).join('')}
        `;
        results.querySelectorAll('.trend-topic-option').forEach(option => {
            option.addEventListener('click', () => {
                suppressFingerprintClear = true;
                inputTopic.value = option.dataset.topic;
                const idx = Number(option.dataset.trendIndex);
                const picked = lastTrendResults[idx];
                setPendingFormatFingerprint(picked?.format_fingerprint || trendFormatFingerprintAggregate);
                updateLoopBridge(nicheId, inputTopic.value);
                updateFlowRail('topic');
                showToast('Trend başlık sinyali konu alanına aktarıldı. Senaryo özgün olarak üretilecek.');
            });
        });
    } catch (error) {
        results.style.display = 'block';
        results.textContent = 'Trend araştırması sırasında bağlantı hatası oluştu.';
        console.error('Trend araştırması hatası:', error);
    } finally {
        button.disabled = false;
        button.innerHTML = '<i class="fa-solid fa-chart-line"></i> Son 24 Saat Trendlerini Getir';
    }
});

document.getElementById('btn-analyze-content-gaps')?.addEventListener('click', async (event) => {
    const source = document.getElementById('content-gap-topics');
    const results = document.getElementById('content-gap-results');
    const nicheId = selectNiche?.value;
    if (!source?.value.trim() || !results || !nicheId) {
        showToast('Önce YouTube Studio içerik boşluğu konu listesini girin.');
        return;
    }
    const button = event.currentTarget;
    button.disabled = true;
    try {
        const response = await fetch('/api/research/content-gaps', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ raw_topics: source.value, niche: nicheId })
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || 'Araştırma çözümlenemedi.');
        results.style.display = 'block';
        const gapFingerprint = data.format_fingerprint || null;
        results.innerHTML = data.suggestions.length ? data.suggestions.map(suggestion => `
            <button class="trend-topic-option content-gap-option" data-topic="${escapeHtml(suggestion.topic)}" style="display:block; width:100%; text-align:left; padding:8px; margin-bottom:5px; border-radius:6px; background:rgba(15,23,42,.7); border:1px solid rgba(251,191,36,.2); color:#e2e8f0; cursor:pointer;">
                <strong style="font-size:12px;">${escapeHtml(suggestion.topic)}</strong>
                <span style="float:right; font-size:10px; color:#fbbf24;">Uygunluk ${suggestion.relevance}/100</span>
            </button>`).join('') : '<div class="alert-info-box">Kullanılabilir konu bulunamadı.</div>';
        results.querySelectorAll('.content-gap-option').forEach(option => option.addEventListener('click', () => {
            suppressFingerprintClear = true;
            inputTopic.value = option.dataset.topic;
            setPendingFormatFingerprint(gapFingerprint);
            updateLoopBridge(nicheId, inputTopic.value);
            updateFlowRail('topic');
            showToast('İçerik boşluğu konusu seçildi. Senaryo niş profilinizle özgün üretilecek.');
        }));
    } catch (error) {
        results.style.display = 'block';
        results.textContent = error.message;
    } finally {
        button.disabled = false;
    }
});

document.getElementById('btn-load-reddit-posts')?.addEventListener('click', async (event) => {
    const results = document.getElementById('reddit-post-results');
    const subreddit = document.getElementById('select-reddit-subreddit')?.value || 'AITA';
    const button = event.currentTarget;
    button.disabled = true;
    button.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Keşfediliyor...';
    try {
        const currentLang = document.getElementById('select-language')?.value || 'tr';
        const response = await fetch(`/api/research/reddit?subreddit=${encodeURIComponent(subreddit)}&lang=${encodeURIComponent(currentLang)}`);
        const data = await response.json();
        if (!response.ok || data.status !== 'ok') throw new Error(data.detail || 'Reddit gönderileri alınamadı.');
        
        let modeBadge = '<span class="badge" style="background: rgba(168, 85, 247, 0.2); color: #c084fc; font-size: 10px; padding: 2px 6px; border-radius: 4px;"><i class="fa-solid fa-wand-magic-sparkles"></i> Viral Arşiv Rotasyonu</span>';
        if (data.mode === 'oauth') {
            modeBadge = '<span class="badge" style="background: rgba(16, 185, 129, 0.2); color: #34d399; font-size: 10px; padding: 2px 6px; border-radius: 4px;"><i class="fa-solid fa-key"></i> Resmi OAuth API</span>';
        } else if (data.mode === 'ai_discovery') {
            modeBadge = '<span class="badge" style="background: rgba(245, 158, 11, 0.2); color: #fbbf24; font-size: 10px; padding: 2px 6px; border-radius: 4px;"><i class="fa-solid fa-sparkles"></i> Canlı AI Keşif (Taze İçerik)</span>';
        }

        const headerHtml = `
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <span style="font-size: 11px; color: #94a3b8;">${data.posts.length} trend gönderi hazır:</span>
                ${modeBadge}
            </div>
        `;

        results.innerHTML = data.posts.length ? headerHtml + data.posts.map((post, index) => `
            <button type="button" class="trend-topic-option reddit-post-option" data-index="${index}" style="display:block; width:100%; text-align:left; padding:8px 10px; margin-bottom:6px; border-radius:8px; background:rgba(15,23,42,.75); border:1px solid rgba(255,69,0,.35); color:#e2e8f0; cursor:pointer; transition: all 0.2s ease;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 6px;">
                    <strong style="font-size:12px; line-height: 1.35; color: #f8fafc;">${escapeHtml(post.title)}</strong>
                </div>
                <div style="font-size:10px; color:#94a3b8; margin-top: 4px; display: flex; gap: 8px;">
                    <span style="color: #ff6b35; font-weight: 600;">r/${escapeHtml(post.subreddit)}</span>
                    <span>·</span>
                    <span>▲ ${Number(post.score || 1000).toLocaleString('tr-TR')} oy</span>
                    <span>·</span>
                    <span style="color: #64748b;">${escapeHtml(post.author || 'Anonim')}</span>
                </div>
            </button>`).join('') : '<div class="alert-info-box">Uygun kaynak gönderi bulunamadı.</div>';
        
        results.querySelectorAll('.reddit-post-option').forEach(option => option.addEventListener('click', () => {
            selectedRedditPost = data.posts[Number(option.dataset.index)];
            inputTopic.value = selectedRedditPost.title;
            updateLoopBridge('2_reddit_confessions', inputTopic.value);
            showToast('Reddit viral hikayesi seçildi. İlk sahneye kaynak kartı eklenecek ve metin insanlaştırılacak.');
        }));
    } catch (error) {
        results.innerHTML = `<div class="alert-info-box text-danger" style="font-size: 11px;">⚠️ ${escapeHtml(error.message)}</div>`;
    } finally {
        button.disabled = false;
        button.innerHTML = '<i class="fa-solid fa-arrows-rotate"></i> Güncel Gönderileri Getir';
    }
});


// ══════════════════════════════════════════════════════════════


// 15. CANLI KANCA (HOOK) & DÖNGÜ (LOOP) KÖPRÜSÜ
// ══════════════════════════════════════════════════════════════
function updateLoopBridge(nicheId, topic) {
    const hookSpan = document.getElementById('preview-hook-text');
    const loopSpan = document.getElementById('preview-loop-text');
    const subOverlay = document.getElementById('mockup-sub-overlay');
    if (!hookSpan || !loopSpan) return;

    const topicText = topic || inputTopic.value || "Bu Gizemli Konu";

    if (nicheId && nicheId.includes('stoic')) {
        hookSpan.textContent = `"Bu kuralı öğrenene kadar hayatınız kontrolünüzde değildi..."`;
        loopSpan.textContent = `"...ve tam da bu yüzden asla unutmayın çünkü..."`;
    } else if (nicheId && (nicheId.includes('dark') || nicheId.includes('psychology'))) {
        hookSpan.textContent = `"İnsanların sizden gizlediği bu psikolojik hileyi öğrenin..."`;
        loopSpan.textContent = `"...çünkü bu sırrı ilk duyduğunuzda başa dönüp diyeceksiniz ki..."`;
    } else if (nicheId && (nicheId.includes('space') || nicheId.includes('bilim'))) {
        hookSpan.textContent = `"Astrofizikçileri dehşete düşüren bu gerçeği çok az kişi biliyor..."`;
        loopSpan.textContent = `"...ve işte evrenin tam da bu döngüsü yüzünden her şey başa dönüyor..."`;
    } else {
        hookSpan.textContent = `"${topicText.slice(0, 45)} hakkında bunu ilk kez duyacaksınız..."`;
        loopSpan.textContent = `"...ve işte tam da bu sebeple asla durmayın çünkü..."`;
    }

    if (subOverlay) {
        const firstWords = topicText.split(' ').slice(0, 3).join(' ').toUpperCase();
        subOverlay.innerHTML = `<span class="sub-word-highlight">${firstWords}</span> ${topicText.split(' ').slice(3).join(' ')}`;
    }
}

selectNiche?.addEventListener('change', () => {
    userManuallyPickedNiche = true;
    if (lockedNicheId && selectNiche.value !== lockedNicheId) {
        showToast('Konu ile niş uyumsuz olabilir', 'warn');
    }
    updateLoopBridge(selectNiche.value, inputTopic.value);
    applyNicheProfile(selectNiche.value);
    saveStudioSettings();
});

// ══════════════════════════════════════════════════════════════


// 16. HIZLI AKSİYON BUTONLARI (Quick Action Strip)
// ══════════════════════════════════════════════════════════════
// 1. Rastgele Niş Seç & Konu Üret
document.getElementById('qa-random-niche')?.addEventListener('click', async () => {
    if (allNiches.length === 0) await loadNiches();
    if (allNiches.length > 0) {
        const randomN = allNiches[Math.floor(Math.random() * allNiches.length)];
        selectNiche.value = randomN.id;
        await applyNicheProfile(randomN.id);
        suggestTopic();
        switchTab('studio');
        showToast(`🎲 Rastgele Niş Seçildi: ${randomN.name} (${randomN.category})`);
    } else {
        suggestTopic();
    }
});

// 2. Son Dakika Flaş Haber Çek (Doğrudan Stüdyoya Aktarır)
document.getElementById('qa-latest-news')?.addEventListener('click', async () => {
    showToast('📡 En güncel son dakika flaş haberi taranıyor...');
    try {
        const res = await fetch('/api/rss/fetch?source=aa_guncel&limit=1');
        const data = await res.json();
        if (data.items && data.items.length > 0) {
            const news = data.items[0];
            inputTopic.value = news.title;
            selectNiche.value = "1_news_flash";
            await applyNicheProfile("1_news_flash");
            updateLoopBridge("1_news_flash", news.title);
            switchTab('studio');
            showToast(`📰 Son Dakika Haberi Yüklendi: ${news.title.slice(0, 45)}...`);
        } else {
            switchTab('rss-bot');
            loadRssNews();
        }
    } catch (e) {
        switchTab('rss-bot');
        loadRssNews();
    }
});

// 3. Split-Screen Modunu Aç / Kapat (Toggle & Canlı Senkronizasyon)
const btnSplitMode = document.getElementById('qa-split-mode');
btnSplitMode?.addEventListener('click', () => {
    chkSplitScreen.checked = !chkSplitScreen.checked;
    chkSplitScreen.dispatchEvent(new Event('change'));
    btnSplitMode.classList.toggle('active', chkSplitScreen.checked);
    const span = btnSplitMode.querySelector('span');
    if (span) span.textContent = chkSplitScreen.checked ? 'Split-Screen: AÇIK' : 'Split-Screen Modunu Aç';
    switchTab('studio');
    showToast(chkSplitScreen.checked ? '🎮 Split-Screen (Oynanış + Kurgu) Aktif!' : '⏹️ Split-Screen Modu Kapatıldı');
});



// 4. Tier-1 (ABD/İngilizce) Modu (Toggle TR / EN)
const btnTier1 = document.getElementById('qa-tier1-en');
btnTier1?.addEventListener('click', async () => {
    const isCurrentlyEn = selectLanguage.value === 'en';
    if (!isCurrentlyEn) {
        selectLanguage.value = 'en';
        populateTtsVoiceSelect('en');
        if (selectTtsVoice) selectTtsVoice.value = 'en-US-GuyNeural';
        selectNiche.value = '7_dark_psychology';
        await applyNicheProfile('7_dark_psychology');
        inputTopic.value = "3 Dark Psychology Secrets Manipulation Experts Never Tell You #Shorts";
        btnTier1.classList.add('active');
        const span = btnTier1.querySelector('span');
        if (span) span.textContent = 'Tier-1 EN: AKTİF (ABD)';
        switchTab('studio');
        showToast('🌎 Tier-1 ABD (İngilizce Yüksek CPM) Modu Aktif Edildi!');
    } else {
        selectLanguage.value = 'tr';
        selectVoiceGender.value = 'auto';
        selectNiche.value = '6_stoic_philosophy';
        await applyNicheProfile('6_stoic_philosophy');
        inputTopic.value = "Marcus Aurelius'un Öfkeyi Yok Eden 3 Stoacı Kuralı";
        btnTier1.classList.remove('active');
        const span = btnTier1.querySelector('span');
        if (span) span.textContent = 'Tier-1 (ABD/İngilizce) Modu';
        switchTab('studio');
        showToast('🇹🇷 Türkçe Moduna Geri Dönüldü');
    }
});

// ══════════════════════════════════════════════════════════════

