/**
 * ShortsAI Studio — Plan Editor, Series Outline, Manuscript Import, Topic-Niche Resolution & Kids Studio (studio-plan-editor.js)
 * Handles series episode planning, manuscript-to-scenes import, topic/script translation, niche auto-detection, and Kids Song Studio.
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
    if (frame) frame.src = getStudioFullUrl(route);
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
                if (!frame.src || frame.src === 'about:blank') frame.src = expected;
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
        if (noteEl) noteEl.textContent = data.log_tail ? `Son log: ${data.log_tail}` : '';

        const navBadge = document.getElementById('badge-kids-song-count');
        if (data.running) {
            try {
                const pRes = await fetch('/api/kids-song/projects');
                if (pRes.ok) {
                    const pData = await pRes.json();
                    if (navBadge && pData.projects) {
                        const count = pData.projects.length;
                        navBadge.textContent = count;
                        navBadge.style.display = count > 0 ? 'inline-block' : 'none';
                    }
                }
            } catch (e) {}
        } else if (navBadge) {
            navBadge.style.display = 'none';
        }
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
    } catch (err) { console.error('Stüdyo başlatma hatası:', err); }
    setTimeout(refreshKidsSong, 1500);
}

function loadKidsSong() {
    refreshKidsSong();
    if (!kidsSongTimer) {
        kidsSongTimer = setInterval(() => {
            const pane = document.getElementById('pane-kids-song');
            if (pane && pane.classList.contains('active')) refreshKidsSong();
        }, 3000);
    }
}

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
    try { await fetch('/api/kids-song/stop', { method: 'POST' }); } catch (err) { console.error(err); }
    refreshKidsSong();
});

document.getElementById('btn-kids-song-reload')?.addEventListener('click', () => {
    const frame = document.getElementById('kids-song-frame');
    if (frame) frame.src = getStudioFullUrl(currentStudioRoute);
    refreshKidsSong();
});

document.getElementById('btn-kids-song-keys')?.addEventListener('click', async () => {
    const statusEl = document.getElementById('kids-song-status');
    if (statusEl) statusEl.textContent = 'API anahtarları aktarılıyor...';
    try {
        const res = await fetch('/api/kids-song/settings/transfer', { method: 'POST' });
        const data = await res.json();
        if (statusEl) statusEl.textContent = data.message || 'Anahtarlar stüdyoya başarıyla aktarıldı!';
    } catch (err) { if (statusEl) statusEl.textContent = 'Ayar aktarımı başarısız.'; }
});

document.getElementById('btn-kids-song-import')?.addEventListener('click', async () => {
    const statusEl = document.getElementById('kids-song-status');
    if (statusEl) statusEl.textContent = 'Tamamlanan video galeriye aktarılıyor...';
    try {
        const stRes = await fetch('/api/kids-song/status');
        const stData = await stRes.json();
        if (!stData.running) {
            if (statusEl) statusEl.textContent = 'Önce Çocuk Şarkı Stüdyosunu başlatın.';
            return;
        }
        const listRes = await fetch('/api/kids-song/projects');
        if (!listRes.ok) {
            if (statusEl) statusEl.textContent = 'Proje listesi alınamadı.';
            return;
        }
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
            if (typeof loadGallery === 'function') loadGallery();
            if (typeof loadGalleryVideos === 'function') loadGalleryVideos();
            if (typeof renderGallery === 'function') renderGallery();
        } else {
            if (statusEl) statusEl.textContent = impData.error || 'Galeriye aktarılamadı (Final video henüz hazır değil).';
        }
    } catch (err) { if (statusEl) statusEl.textContent = 'Galeriye aktarma işlemi başarısız.'; }
});

const wizardModal = document.getElementById('modal-kids-ai-wizard');
const wizardOpenBtn = document.getElementById('btn-kids-ai-wizard');
const wizardCloseBtn = document.getElementById('btn-close-kids-wizard');
const wizardRunBtn = document.getElementById('btn-run-kids-wizard');
const wizardCreateBtn = document.getElementById('btn-kids-wizard-create');
const wizardResultArea = document.getElementById('kids-ai-result-area');

wizardOpenBtn?.addEventListener('click', () => {
    if (wizardModal) {
        wizardModal.classList.remove('hidden');
        wizardModal.style.display = 'flex';
    }
});
wizardCloseBtn?.addEventListener('click', () => {
    if (wizardModal) {
        wizardModal.style.display = 'none';
        wizardModal.classList.add('hidden');
    }
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
            method: 'POST', headers: { 'Content-Type': 'application/json' },
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
    } catch (err) { console.error('AI Şarkı üretme hatası:', err); }
    finally {
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
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, topic, lyrics })
        });
        const data = await res.json();
        if (data.ok && data.project) {
            if (wizardModal) wizardModal.style.display = 'none';
            const frame = document.getElementById('kids-song-frame');
            if (frame) frame.src = getStudioFullUrl(data.project.render_path || '/cocuk-sarki');
            const statusEl = document.getElementById('kids-song-status');
            if (statusEl) statusEl.textContent = `Proje başarıyla açıldı: ${title}`;
            refreshKidsSong();
        }
    } catch (err) { console.error('Proje açma hatası:', err); }
    finally {
        wizardCreateBtn.disabled = false;
        wizardCreateBtn.innerHTML = '<i class="fa-solid fa-circle-check"></i> Bu Şarkıyla Stüdyoda Proje Başlat';
    }
});

function appendSeriesDetail(card, label, value) {
    const paragraph = document.createElement('p');
    paragraph.className = 'series-episode-card__detail';
    const strong = document.createElement('strong');
    strong.textContent = `${label}: `;
    paragraph.append(strong, document.createTextNode(value));
    card.appendChild(paragraph);
}

function renderSeriesPlan(outline) {
    const results = document.getElementById('series-plan-results');
    if (!results) return;

    const isEnglish = window.APP_STATE?.language === 'en';
    const labels = isEnglish
        ? { premise: 'Series premise', summary: 'Summary', question: 'Central question', hook: 'Ending hook', continuity: 'Carries forward', use: 'Prepare this episode' }
        : { premise: 'Seri öncülü', summary: 'Özet', question: 'Ana soru', hook: 'Bölüm sonu kancası', continuity: 'Devamlılık', use: 'Bu bölümü hazırla' };
    results.replaceChildren();
    results.classList.remove('hidden');

    const premise = document.createElement('p');
    premise.className = 'series-plan-premise';
    premise.textContent = `${labels.premise}: ${outline.series_premise}`;
    results.appendChild(premise);

    const list = document.createElement('div');
    list.className = 'series-plan-list';
    for (const episode of outline.episodes) {
        const card = document.createElement('article');
        card.className = 'series-episode-card';

        const heading = document.createElement('h4');
        heading.textContent = `${episode.number}. ${episode.title}`;
        card.appendChild(heading);
        appendSeriesDetail(card, labels.summary, episode.summary);
        appendSeriesDetail(card, labels.question, episode.central_question);
        appendSeriesDetail(card, labels.hook, episode.cliffhanger);
        appendSeriesDetail(card, labels.continuity, episode.continuity_note);

        const useButton = document.createElement('button');
        useButton.type = 'button';
        useButton.className = 'btn btn-outline btn-sm series-episode-card__action';
        useButton.textContent = labels.use;
        useButton.addEventListener('click', () => {
            if (window.selectedRedditPost) {
                showToast(
                    isEnglish ? 'Series planning is unavailable while a Reddit source is selected.' : 'Reddit gönderisi seçiliyken seri taslağı kullanılamaz.',
                    'warning',
                );
                return;
            }
            const priorEpisodes = outline.episodes
                .filter(item => item.number < episode.number)
                .map(item => `${item.number}. ${item.title}\n${item.summary}\nOpen hook: ${item.cliffhanger}\nContinuity: ${item.continuity_note}`);
            const episodeTarget = [
                `CURRENT EPISODE TARGET: ${episode.title}`,
                `SUMMARY: ${episode.summary}`,
                `CENTRAL QUESTION: ${episode.central_question}`,
                `REQUIRED ENDING HOOK: ${episode.cliffhanger}`,
                `CONTINUITY NOTE: ${episode.continuity_note}`,
            ].join('\n');
            const continuityBlocks = [
                `SERIES PREMISE: ${outline.series_premise}`,
                priorEpisodes.length ? `PREVIOUS EPISODES:\n${priorEpisodes.join('\n\n')}` : '',
                episodeTarget,
            ].filter(Boolean);

            const continuityInput = document.getElementById('input-series-continuity');
            if (window.inputTopic) window.inputTopic.value = episode.title;
            if (continuityInput) continuityInput.value = continuityBlocks.join('\n\n').slice(-4000);
            const outroToggle = document.getElementById('chk-enable-outro');
            if (outroToggle) outroToggle.checked = false;
            showToast(
                isEnglish ? 'Episode topic and continuity notes are ready. Generate the script when ready.' : 'Bölüm konusu ve devamlılık notları hazır. Senaryo üretimini başlatabilirsiniz.',
                'success',
            );
            window.inputTopic?.focus();
        });
        card.appendChild(useButton);
        list.appendChild(card);
    }
    results.appendChild(list);
}

async function generateShortsSeriesOutline() {
    const topic = (window.inputTopic?.value || '').trim();
    if (topic.length < 3) {
        alert('Önce en az 3 karakterlik bir video konusu girin.');
        window.inputTopic?.focus();
        return;
    }
    if (window.selectedRedditPost) {
        showToast('Reddit hikâyesi seçiliyken seri taslağı üretilemez.', 'warning');
        return;
    }

    const button = document.getElementById('btn-plan-series');
    const results = document.getElementById('series-plan-results');
    const isEnglish = window.APP_STATE?.language === 'en';
    const originalLabel = button?.innerHTML;
    if (button) {
        button.disabled = true;
        button.textContent = isEnglish ? 'Planning series…' : 'Seri taslağı hazırlanıyor…';
    }
    if (results) {
        results.classList.remove('hidden');
        results.textContent = isEnglish ? 'Building a connected episode arc…' : 'Bağlantılı bölüm akışı kuruluyor…';
    }

    try {
        const response = await fetch('/api/series/plan', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                topic,
                niche: window.selectNiche?.value || '1_news_flash',
                language: isEnglish ? 'en' : 'tr',
                episode_count: Number(document.getElementById('select-series-episode-count')?.value || 3),
            }),
        });
        const data = await response.json();
        if (!response.ok || data.status !== 'ok' || !data.outline) {
            throw new Error(data.detail || 'Seri taslağı oluşturulamadı.');
        }
        renderSeriesPlan(data.outline);
    } catch (error) {
        if (results) {
            results.classList.add('hidden');
            results.replaceChildren();
        }
        alert(`${isEnglish ? 'Series outline failed' : 'Seri taslağı oluşturulamadı'}: ${error.message}`);
    } finally {
        if (button) {
            button.disabled = false;
            button.innerHTML = originalLabel;
        }
    }
}

async function importManuscriptAsScenes() {
    const manuscriptInput = document.getElementById('input-manuscript');
    const status = document.getElementById('manuscript-import-status');
    const button = document.getElementById('btn-import-manuscript');
    const text = (manuscriptInput?.value || '').trim();
    if (text.length < 30) {
        showToast('Sahnelere aktarmak için en az 30 karakterlik bir metin girin.', 'warning');
        manuscriptInput?.focus();
        return;
    }

    const originalLabel = button?.innerHTML;
    if (button) {
        button.disabled = true;
        button.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Sahnelere ayrılıyor...';
    }
    if (status) status.textContent = 'Anlatım korunarak sahneler hazırlanıyor...';

    try {
        const response = await fetch('/api/script/from-manuscript', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text,
                title: (window.inputTopic?.value || '').trim() || null,
                language: window.selectLanguage?.value || window.APP_STATE?.language || 'tr',
                niche: window.selectNiche?.value || '1_news_flash',
            }),
        });
        const data = await response.json();
        if (!response.ok || data.status !== 'ok' || !data.plan?.scenes?.length) {
            throw new Error(data.detail || 'Metin sahnelere aktarılamadı.');
        }

        let plan = data.plan;
        if (window.inputTopic) window.inputTopic.value = plan.title;
        window.timelineReviewed = false;
        setCurrentPlan(plan, { skipQualityPanel: true });
        const validation = await updateStudioQualityPanel(plan);
        if (validation?.plan) plan = validation.plan;
        if (typeof renderTimelineScenes === 'function') renderTimelineScenes(plan);
        persistCurrentPlan();
        saveStudioSettings();
        updateFlowRail('timeline');
        if (typeof switchTab === 'function') switchTab('timeline');
        if (status) status.textContent = `${plan.scenes.length} sahne hazır; anlatım metni korundu.`;
        showToast(`Metin ${plan.scenes.length} sahneye aktarıldı. Timeline'da görselleri inceleyin.`, 'success');
    } catch (error) {
        if (status) status.textContent = error.message;
        showToast(`Metin içe aktarılamadı: ${error.message}`, 'error');
    } finally {
        if (button) {
            button.disabled = false;
            button.innerHTML = originalLabel;
        }
    }
}

document.getElementById('btn-plan-series')?.addEventListener('click', generateShortsSeriesOutline);
document.getElementById('btn-import-manuscript')?.addEventListener('click', importManuscriptAsScenes);
document.getElementById('btn-use-current-script-continuity')?.addEventListener('click', () => {
    const currentNarration = window.currentPlan?.full_narration
        || (window.currentPlan?.scenes || []).map(scene => scene.narration).filter(Boolean).join(' ');
    const continuityInput = document.getElementById('input-series-continuity');
    if (!currentNarration || !continuityInput) {
        showToast('Önceki senaryo bulunamadı; önce bir senaryo üretin veya yükleyin.', 'warning');
        return;
    }
    continuityInput.value = currentNarration.slice(0, 4000);
    showToast('Mevcut senaryo devamlılık bağlamına eklendi. Gerekirse özeti düzenleyin.', 'success');
});

function autoDetectNicheFromTopicLocal() {
    const topicText = (inputTopic?.value || '').trim().toLowerCase();
    if (!topicText || !selectNiche) return null;
    if (/stoa|marcus|aurelius|seneca|epiktetos|stoac/.test(topicText)) return '6_stoic_philosophy';
    if (/whatsapp|mesajlaşma|mesaj hikay|chat story|sohbet ekran/.test(topicText)) return '20_whatsapp_chat_story';
    if (/yanılgı|mit |efsane|yanlış bilinen|doğru bilinen|bilimsel/.test(topicText)) return '27_common_myths_busted';
    if (/karanlık psikoloji|manipülasyon|manipulation|dark psychology/.test(topicText)) return '7_dark_psychology';
    if (/kripto|bitcoin|borsa|altın|hisse|dolar|enflasyon/.test(topicText)) return '8_crypto_market';
    if (/\d+\s+(?:büyük|ilginç|önemli|sır|kural|adım|ipucu)|şaşırtıcı gerçek/.test(topicText)) return '9_five_facts';
    if (/aita|itiraf|confession|reddit/.test(topicText)) return '2_reddit_confessions';
    if (/tercih et|would you rather/.test(topicText)) return '4_would_you_rather';
    if (/bayrak|ülke tahmin|hangi ülke/.test(topicText)) return '5_guess_flag_country';
    if (/paranormal|ufo|bermuda|51\.\s*bölge|gizem.*korku/.test(topicText)) return '13_mystery_paranormal';
    if (/son dakika|flaş|haber|deprem|kaza|trafik/.test(topicText)) return '1_news_flash';
    return null;
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
        if (toast) showToast(`Niş otomatik: ${nicheName || opt.textContent} (konu uyumu)`);
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

function updateLoopBridge(nicheId, topic) {
    const hookSpan = document.getElementById('preview-hook-text');
    const loopSpan = document.getElementById('preview-loop-text');
    const subOverlay = document.getElementById('mockup-sub-overlay');
    if (!hookSpan || !loopSpan) return;

    const topicText = topic || inputTopic?.value || "Bu Gizemli Konu";
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
