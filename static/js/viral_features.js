/**
 * viral_features.js — 4 Core Powerhouse Features:
 * 1. 0 TL Pollinations Flux SDXL 9:16 AI Image-to-Video Engine (No Stock Dependency)
 * 2. 39-Language YouTube SEO & Localization Package Translator
 * 3. PIL High-CTR 9:16 & 16:9 Viral Thumbnail Generator
 * 4. Whiteboard / Hand-Drawn Line-Art Sketch Animation Engine
 */

// ── State for Viral Features ──
const ViralFeatures = {
    lastGeneratedThumbnails: {
        '9:16': null,
        '16:9': null
    },
    seo39Data: null,
    isProcessingBatch: false
};

// ── 1. 0 TL FLUX AI VISUAL GENERATION ──

async function generateSingleSceneFluxAI(sceneIndex) {
    if (!window.currentPlan || !window.currentPlan.scenes || !window.currentPlan.scenes[sceneIndex]) {
        return showToast('Geçerli bir sahne bulunamadı', 'warn');
    }
    const sc = window.currentPlan.scenes[sceneIndex];
    const prompt = sc.scene_description || (sc.search_queries && sc.search_queries[0]) || sc.narration || 'cinematic portrait';
    const dur = parseFloat(sc.duration) || 5.0;

    showToast(`🤖 Sahne #${sceneIndex + 1} için Flux AI görseli üretiliyor...`, 'info');

    try {
        const res = await fetch('/api/visual/generate_ai_scene', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                prompt: prompt,
                scene_index: sceneIndex,
                duration: dur
            })
        });
        const data = await res.json();
        if (!res.ok || data.status !== 'ok') {
            throw new Error(data.detail || 'Flux AI görseli üretilemedi.');
        }

        // Attach to scene
        sc.selected_video = {
            id: `flux_ai_${Date.now()}`,
            url: data.url,
            path: data.video_path,
            source: 'Flux SDXL (0 TL)',
            thumbnail: data.url
        };
        sc.visual_source_policy = 'ai';

        if (typeof renderTimelineScenes === 'function') {
            renderTimelineScenes(window.currentPlan);
        }
        showToast(`✅ Sahne #${sceneIndex + 1} Flux AI klibi hazır!`, 'success');
    } catch (err) {
        showToast(`❌ Flux AI hatası: ${err.message}`, 'error');
    }
}

async function batchGenerateFluxAIForScenes() {
    if (!window.currentPlan || !window.currentPlan.scenes || !window.currentPlan.scenes.length) {
        return showToast('Önce bir senaryo oluşturun.', 'warn');
    }
    if (ViralFeatures.isProcessingBatch) {
        return showToast('Şu anda bir toplu üretim devam ediyor.', 'warn');
    }

    const total = window.currentPlan.scenes.length;
    const confirmProceed = confirm(
        `Toplam ${total} sahne için Pollinations Flux SDXL 9:16 görselleri üretilecek.\n` +
        `Bu işlem stok video derdini tamamen çözer ve 0 TL'dir.\n\nDevam edilsin mi?`
    );
    if (!confirmProceed) return;

    ViralFeatures.isProcessingBatch = true;
    showToast(`🚀 Toplu Flux AI üretimi başlatıldı (0/${total})...`, 'info');

    let successCount = 0;
    for (let i = 0; i < total; i++) {
        const sc = window.currentPlan.scenes[i];
        const prompt = sc.scene_description || (sc.search_queries && sc.search_queries[0]) || sc.narration;
        const dur = parseFloat(sc.duration) || 5.0;

        showToast(`🤖 Sahne ${i + 1}/${total} Flux AI üretiliyor...`, 'info');
        try {
            const res = await fetch('/api/visual/generate_ai_scene', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    prompt: prompt,
                    scene_index: i,
                    duration: dur
                })
            });
            const data = await res.json();
            if (res.ok && data.status === 'ok') {
                sc.selected_video = {
                    id: `flux_ai_${Date.now()}_${i}`,
                    url: data.url,
                    path: data.video_path,
                    source: 'Flux SDXL (0 TL)',
                    thumbnail: data.url
                };
                sc.visual_source_policy = 'ai';
                successCount++;
            }
        } catch (e) {
            console.error(`Sahne ${i + 1} Flux hatası:`, e);
        }
    }

    ViralFeatures.isProcessingBatch = false;
    window.currentPlan.visual_mode = 'flux';
    if (typeof renderTimelineScenes === 'function') {
        renderTimelineScenes(window.currentPlan);
    }
    showToast(`🎉 ${successCount}/${total} sahne için 0 TL Flux AI klipleri başarıyla hazırlandı!`, 'success');
}


// ── 2. WHITEBOARD / ÇİZİM MODU ──

async function generateSingleSceneWhiteboard(sceneIndex) {
    if (!window.currentPlan || !window.currentPlan.scenes || !window.currentPlan.scenes[sceneIndex]) {
        return showToast('Geçerli bir sahne bulunamadı', 'warn');
    }
    const sc = window.currentPlan.scenes[sceneIndex];
    const prompt = sc.scene_description || (sc.search_queries && sc.search_queries[0]) || sc.narration || 'sketch drawing';
    const dur = parseFloat(sc.duration) || 5.0;

    showToast(`✏️ Sahne #${sceneIndex + 1} için Whiteboard çizimi üretiliyor...`, 'info');

    try {
        const res = await fetch('/api/whiteboard/preview', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                prompt: prompt,
                scene_index: sceneIndex,
                duration: dur
            })
        });
        const data = await res.json();
        if (!res.ok || data.status !== 'ok') {
            throw new Error(data.detail || 'Whiteboard animasyonu üretilemedi.');
        }

        sc.selected_video = {
            id: `whiteboard_${Date.now()}`,
            url: data.url,
            path: data.video_path,
            source: 'Whiteboard Çizim',
            thumbnail: data.url
        };
        sc.visual_mode = 'whiteboard';

        if (typeof renderTimelineScenes === 'function') {
            renderTimelineScenes(window.currentPlan);
        }
        showToast(`✅ Sahne #${sceneIndex + 1} Whiteboard animasyonu hazır!`, 'success');
    } catch (err) {
        showToast(`❌ Whiteboard hatası: ${err.message}`, 'error');
    }
}

async function batchConvertScenesToWhiteboard() {
    if (!window.currentPlan || !window.currentPlan.scenes || !window.currentPlan.scenes.length) {
        return showToast('Önce bir senaryo oluşturun.', 'warn');
    }
    const total = window.currentPlan.scenes.length;
    const confirmProceed = confirm(
        `Tüm ${total} sahne Whiteboard (el çizimi line-art) moduna çevrilecek.\n` +
        `Render aşamasında sahneler beyaz tuval üzerine el çizimi efektiyle çizilecektir.\n\nMod aktif edilsin mi?`
    );
    if (!confirmProceed) return;

    window.currentPlan.visual_mode = 'whiteboard';
    window.currentPlan.scenes.forEach(sc => {
        sc.visual_mode = 'whiteboard';
    });

    // Also update visual engine selector if present
    const selectEngine = document.getElementById('select-visual-engine');
    if (selectEngine) selectEngine.value = 'whiteboard';

    if (typeof renderTimelineScenes === 'function') {
        renderTimelineScenes(window.currentPlan);
    }
    showToast(`✏️ Whiteboard Çizim Modu aktif edildi! Render sırasında tüm sahneler çizim animasyonuyla üretilecek.`, 'success');
}


// ── 3. 39 DİLLİ YOUTUBE SEO ÇEVİRİCİ ──

function openSEO39Modal() {
    const modal = document.getElementById('modal-seo-39');
    if (!modal) return;

    // Fill current topic / title
    const currentTitle = (window.currentPlan && window.currentPlan.title) || document.getElementById('input-topic')?.value || '';
    const currentDesc = (window.currentPlan && window.currentPlan.full_narration) || '';

    const inputTitle = document.getElementById('seo39-src-title');
    const inputDesc = document.getElementById('seo39-src-desc');
    if (inputTitle && !inputTitle.value) inputTitle.value = currentTitle;
    if (inputDesc && !inputDesc.value) inputDesc.value = currentDesc;

    modal.style.display = 'flex';
    modal.classList.remove('hidden');
}

function closeSEO39Modal() {
    const modal = document.getElementById('modal-seo-39');
    if (modal) {
        modal.style.display = 'none';
        modal.classList.add('hidden');
    }
}

async function executeSEO39Translation() {
    const title = document.getElementById('seo39-src-title')?.value.trim();
    const desc = document.getElementById('seo39-src-desc')?.value.trim();
    const srcLang = document.getElementById('seo39-src-lang')?.value || 'tr';
    const statusBox = document.getElementById('seo39-status-box');
    const resultsContainer = document.getElementById('seo39-results-grid');
    const btnTranslate = document.getElementById('btn-execute-seo39');

    if (!title) {
        return showToast('Lütfen çevrilecek başlığı girin.', 'warn');
    }

    if (btnTranslate) {
        btnTranslate.disabled = true;
        btnTranslate.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> 39 Dile Çevriliyor...';
    }
    if (statusBox) {
        statusBox.style.display = 'block';
        statusBox.innerHTML = '<i class="fa-solid fa-cloud-arrow-down fa-spin"></i> YouTube 39 dil çeviri motoru çalışıyor (0 TL)...';
    }

    try {
        const res = await fetch('/api/seo/translate_39', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title: title,
                description: desc || title,
                source_lang: srcLang
            })
        });
        const data = await res.json();
        if (!res.ok || data.status !== 'ok') {
            throw new Error(data.detail || 'Çeviri işlemi başarısız.');
        }

        ViralFeatures.seo39Data = data;

        // Render results
        if (statusBox) {
            statusBox.innerHTML = `✅ <strong>${data.total_languages} Dil Başarıyla Çevrildi!</strong> (YouTube Data API v3 Uyumlu)`;
            statusBox.style.color = '#34d399';
        }

        renderSEO39Cards(data.translations || {});
        showToast(`🎉 ${data.total_languages} YouTube dili için SEO paketi oluşturuldu!`, 'success');
    } catch (err) {
        if (statusBox) {
            statusBox.innerHTML = `❌ Çeviri hatası: ${err.message}`;
            statusBox.style.color = '#f87171';
        }
        showToast(`Çeviri hatası: ${err.message}`, 'error');
    } finally {
        if (btnTranslate) {
            btnTranslate.disabled = false;
            btnTranslate.innerHTML = '<i class="fa-solid fa-wand-sparkles"></i> 39 Dile Tek Tıkla Çevir (0 TL)';
        }
    }
}

function renderSEO39Cards(translations) {
    const container = document.getElementById('seo39-results-grid');
    if (!container) return;

    const entries = Object.entries(translations);
    if (!entries.length) {
        container.innerHTML = '<p style="color:#64748b;font-size:12px;">Henüz çeviri yapılmadı.</p>';
        return;
    }

    let html = '';
    entries.forEach(([langCode, item]) => {
        const langName = item.language_name || langCode.toUpperCase();
        html += `
            <div class="glass-box" style="padding: 10px 12px; background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                    <span style="font-weight: 700; font-size: 12px; color: #38bdf8;">
                        <span style="background: rgba(56, 189, 248, 0.15); padding: 2px 6px; border-radius: 4px; font-size: 11px; margin-right: 6px;">${langCode}</span>
                        ${langName}
                    </span>
                    <button type="button" class="btn btn-xs btn-outline-secondary btn-copy-lang" data-lang="${langCode}" style="font-size: 10px; padding: 2px 6px;">
                        <i class="fa-regular fa-copy"></i> Kopyala
                    </button>
                </div>
                <div style="font-size: 12px; color: #f1f5f9; font-weight: 600; margin-bottom: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${escapeHtml(item.title)}">
                    ${escapeHtml(item.title)}
                </div>
                <div style="font-size: 11px; color: #94a3b8; max-height: 40px; overflow: hidden; text-overflow: ellipsis;">
                    ${escapeHtml(item.description)}
                </div>
            </div>
        `;
    });

    container.innerHTML = html;

    // Attach copy button handlers
    container.querySelectorAll('.btn-copy-lang').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const lang = e.currentTarget.getAttribute('data-lang');
            const item = translations[lang];
            if (!item) return;
            const textToCopy = `[${item.language_name || lang}]\nBAŞLIK: ${item.title}\nAÇIKLAMA:\n${item.description}`;
            navigator.clipboard.writeText(textToCopy).then(() => {
                showToast(`📋 ${item.language_name || lang} çevirisi panoya kopyalandı!`);
            });
        });
    });
}

function copySEO39AsYouTubeJSON() {
    if (!ViralFeatures.seo39Data || !ViralFeatures.seo39Data.localizations) {
        return showToast('Önce 39 dil çevirisi yapın.', 'warn');
    }
    const jsonStr = JSON.stringify(ViralFeatures.seo39Data.localizations, null, 2);
    navigator.clipboard.writeText(jsonStr).then(() => {
        showToast('📋 YouTube Data API v3 "localizations" JSON panoya kopyalandı!', 'success');
    });
}


// ── 4. OTOMATİK THUMBNAIL / VIRAL KAPAK ÜRETİCİ ──

function openThumbnailModal() {
    const modal = document.getElementById('modal-thumbnail-generator');
    if (!modal) return;

    const currentTitle = (window.currentPlan && window.currentPlan.title) || document.getElementById('input-topic')?.value || '';
    const inputTitle = document.getElementById('thumb-input-title');
    const inputAccent = document.getElementById('thumb-input-accent');

    if (inputTitle && !inputTitle.value) inputTitle.value = currentTitle;
    if (inputAccent && !inputAccent.value) {
        // Pick first punchy word
        const words = currentTitle.split(' ').filter(w => w.length > 2);
        inputAccent.value = words[words.length - 1] || 'ŞOK';
    }

    modal.style.display = 'flex';
    modal.classList.remove('hidden');
}

function closeThumbnailModal() {
    const modal = document.getElementById('modal-thumbnail-generator');
    if (modal) {
        modal.style.display = 'none';
        modal.classList.add('hidden');
    }
}

async function executeThumbnailGeneration() {
    const title = document.getElementById('thumb-input-title')?.value.trim() || 'Viral Shorts Video';
    const accent = document.getElementById('thumb-input-accent')?.value.trim();
    const btnGen = document.getElementById('btn-execute-gen-thumb');
    const preview916 = document.getElementById('thumb-img-916');
    const preview169 = document.getElementById('thumb-img-169');

    if (btnGen) {
        btnGen.disabled = true;
        btnGen.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Kapak Üretiliyor...';
    }

    try {
        // 1. Generate 9:16 Shorts Cover
        const res916 = await fetch('/api/thumbnail/custom_generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title: title,
                aspect_ratio: '9:16',
                accent_text: accent
            })
        });
        const data916 = await res916.json();

        // 2. Generate 16:9 Landscape Cover
        const res169 = await fetch('/api/thumbnail/custom_generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title: title,
                aspect_ratio: '16:9',
                accent_text: accent
            })
        });
        const data169 = await res169.json();

        if (data916.status === 'ok') {
            ViralFeatures.lastGeneratedThumbnails['9:16'] = data916.url;
            if (preview916) preview916.src = `${data916.url}?t=${Date.now()}`;
        }
        if (data169.status === 'ok') {
            ViralFeatures.lastGeneratedThumbnails['16:9'] = data169.url;
            if (preview169) preview169.src = `${data169.url}?t=${Date.now()}`;
        }

        showToast('✨ 9:16 ve 16:9 Viral Kapaklar başarıyla üretildi!', 'success');
    } catch (err) {
        showToast(`Kapak üretimi hatası: ${err.message}`, 'error');
    } finally {
        if (btnGen) {
            btnGen.disabled = false;
            btnGen.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i> Otomatik Kapak Üret';
        }
    }
}


// ── INITIALIZATION & EVENT LISTENERS ──

document.addEventListener('DOMContentLoaded', () => {
    // 1. Batch buttons in Scene Timeline
    document.getElementById('btn-batch-flux-ai')?.addEventListener('click', batchGenerateFluxAIForScenes);
    document.getElementById('btn-batch-whiteboard')?.addEventListener('click', batchConvertScenesToWhiteboard);

    // 2. SEO 39 Modal Triggers
    document.getElementById('btn-open-seo39')?.addEventListener('click', openSEO39Modal);
    document.getElementById('btn-pub-open-seo39')?.addEventListener('click', openSEO39Modal);
    document.getElementById('btn-close-seo39')?.addEventListener('click', closeSEO39Modal);
    document.getElementById('btn-execute-seo39')?.addEventListener('click', executeSEO39Translation);
    document.getElementById('btn-copy-seo39-json')?.addEventListener('click', copySEO39AsYouTubeJSON);

    // 3. Thumbnail Modal Triggers
    document.getElementById('btn-open-thumbnail-gen')?.addEventListener('click', openThumbnailModal);
    document.getElementById('btn-pub-open-thumbnail')?.addEventListener('click', openThumbnailModal);
    document.getElementById('btn-close-thumbnail-modal')?.addEventListener('click', closeThumbnailModal);
    document.getElementById('btn-execute-gen-thumb')?.addEventListener('click', executeThumbnailGeneration);

    // 4. Download handlers for thumbnail
    document.getElementById('btn-download-thumb-916')?.addEventListener('click', () => {
        const url = ViralFeatures.lastGeneratedThumbnails['9:16'];
        if (!url) return showToast('Önce kapak üretin.', 'warn');
        const a = document.createElement('a');
        a.href = url;
        a.download = 'shorts_cover_9x16.jpg';
        a.click();
    });
    document.getElementById('btn-download-thumb-169')?.addEventListener('click', () => {
        const url = ViralFeatures.lastGeneratedThumbnails['16:9'];
        if (!url) return showToast('Önce kapak üretin.', 'warn');
        const a = document.createElement('a');
        a.href = url;
        a.download = 'youtube_thumbnail_16x9.jpg';
        a.click();
    });

    // 5. Close modals on background click
    ['modal-seo-39', 'modal-thumbnail-generator'].forEach(id => {
        const m = document.getElementById(id);
        if (m) {
            m.addEventListener('click', (e) => {
                if (e.target === m) m.style.display = 'none';
            });
        }
    });

    // Delegate scene-level AI and Whiteboard buttons in timeline container
    const scenesContainer = document.getElementById('scenes-timeline-container');
    if (scenesContainer) {
        scenesContainer.addEventListener('click', (e) => {
            const btnFlux = e.target.closest('.btn-gen-ai-visual');
            if (btnFlux) {
                const idx = parseInt(btnFlux.getAttribute('data-idx'), 10);
                if (!isNaN(idx)) generateSingleSceneFluxAI(idx);
                return;
            }

            const btnWb = e.target.closest('.btn-gen-whiteboard');
            if (btnWb) {
                const idx = parseInt(btnWb.getAttribute('data-idx'), 10);
                if (!isNaN(idx)) generateSingleSceneWhiteboard(idx);
                return;
            }
        });
    }

    // ── 6. MoneyPrinterV2: AFM (Affiliate Marketing) Modal ──
    const btnOpenAfm = document.getElementById('btn-open-afm-modal');
    if (btnOpenAfm) {
        btnOpenAfm.addEventListener('click', () => {
            const modal = document.getElementById('modal-afm-generator');
            if (modal) modal.style.display = 'flex';
        });
    }
    document.getElementById('btn-close-afm-modal')?.addEventListener('click', () => {
        const modal = document.getElementById('modal-afm-generator');
        if (modal) modal.style.display = 'none';
    });
    document.getElementById('btn-execute-afm-gen')?.addEventListener('click', async () => {
        const productInput = document.getElementById('afm-product-url')?.value.trim();
        const affiliateUrl = document.getElementById('afm-affiliate-url')?.value.trim();
        const hookStyle = document.getElementById('afm-hook-style')?.value || 'life_hack';
        const lang = document.getElementById('afm-lang')?.value || 'tr';
        const ctaText = document.getElementById('afm-cta-text')?.value.trim() || 'Link profilde ve ilk yorumda sabitli!';

        if (!productInput) {
            return showToast('Lütfen ürün linki veya ürün adı girin.', 'warn');
        }

        showToast('🛒 AFM: Ürün taranıyor ve viral satış senaryosu kurgulanıyor...', 'info');
        try {
            const res = await fetch('/api/affiliate/generate_plan', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    product_input: productInput,
                    affiliate_url: affiliateUrl,
                    hook_style: hookStyle,
                    language: lang,
                    cta_text: ctaText
                })
            });
            const data = await res.json();
            if (!res.ok || !data.ok) {
                throw new Error(data.detail || 'AFM planı oluşturulamadı.');
            }

            window.currentPlan = data;
            const topicInput = document.getElementById('topic-input') || document.getElementById('project-name-input');
            if (topicInput) topicInput.value = data.topic;

            if (typeof renderTimelineScenes === 'function') {
                renderTimelineScenes(data);
            }
            document.getElementById('modal-afm-generator').style.display = 'none';
            showToast('✅ AFM E-Ticaret Senaryosu Sahne Editörüne Yüklendi!', 'success');
        } catch (err) {
            showToast(`❌ AFM Hatası: ${err.message}`, 'error');
        }
    });

    // ── 7. MoneyPrinterV2: Headless Quota-Free Uploader Modal ──
    const btnOpenUploader = document.getElementById('btn-open-headless-uploader');
    if (btnOpenUploader) {
        btnOpenUploader.addEventListener('click', () => {
            const modal = document.getElementById('modal-headless-uploader');
            if (modal) modal.style.display = 'flex';
        });
    }
    document.getElementById('btn-close-headless-uploader')?.addEventListener('click', () => {
        const modal = document.getElementById('modal-headless-uploader');
        if (modal) modal.style.display = 'none';
    });
    document.getElementById('btn-execute-headless-upload')?.addEventListener('click', async () => {
        const videoPath = document.getElementById('uploader-video-path')?.value.trim();
        const title = document.getElementById('uploader-title')?.value.trim();
        const desc = document.getElementById('uploader-desc')?.value.trim();
        const vis = document.getElementById('uploader-visibility')?.value || 'unlisted';

        if (!videoPath) {
            return showToast('Lütfen yüklenecek video dosya yolunu girin.', 'warn');
        }

        showToast('🚀 Kotasız YouTube Studio yükleyicisi başlatılıyor...', 'info');
        try {
            const res = await fetch('/api/uploader/headless_upload', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    video_path: videoPath,
                    title: title || 'Viral Shorts Video',
                    description: desc || '',
                    visibility: vis
                })
            });
            const data = await res.json();
            if (!res.ok || !data.success) {
                throw new Error(data.error || 'Yükleme başarısız oldu.');
            }
            showToast(`🎉 YouTube'a Başarıyla Yüklendi! URL: ${data.url}`, 'success');
            document.getElementById('modal-headless-uploader').style.display = 'none';
        } catch (err) {
            showToast(`❌ Yükleme Hatası: ${err.message}`, 'error');
        }
    });
});

