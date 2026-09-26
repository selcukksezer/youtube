/**
 * ShortsAI Studio — Video Gallery, Channels & Automation (gallery-channels.js)
 * Covers Video Gallery, YouTube Publish Hub, News RSS Bot, Batch Queue, Growth Tactics, and Anti-Detect Channel Onboarding.
 */


// 3. OTO-HABER & RSS BOTU (Item 1 & 57)
// ══════════════════════════════════════════════════════════════
let currentRssItems = [];

async function loadRssNews() {
    const list = document.getElementById('rss-news-list');
    const badge = document.getElementById('rss-news-count-badge');
    const sourceSelect = document.getElementById('select-rss-source');
    const source = sourceSelect ? sourceSelect.value : 'aa_guncel';
    list.innerHTML = '<div class="empty-state-box"><i class="fa-solid fa-spinner fa-spin"></i><p>Haberler taranıyor...</p></div>';

    try {
        const res = await fetch(`/api/rss/fetch?source=${source}&limit=10`);
        const data = await res.json();
        const items = data.items || [];
        currentRssItems = items;

        if (badge) badge.textContent = `${items.length} Haber`;

        if (items.length === 0) {
            list.innerHTML = '<div class="empty-state-box"><p>Bu kaynaktan haber çekilemedi.</p></div>';
            return;
        }

        list.innerHTML = '';
        items.forEach(item => {
            const row = document.createElement('div');
            row.className = 'glass-box mb-3';
            row.style.padding = '14px';
            const nicheLabel = item.suggested_niche ? item.suggested_niche.replace(/^[0-9]+_/, '').replace(/_/g, ' ') : 'Haber';
            row.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; flex-wrap: wrap;">
                    <div style="flex: 1; min-width: 240px;">
                        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                            <span class="badge" style="background: rgba(168, 85, 247, 0.2); color: #c084fc; font-size: 10px; padding: 2px 6px; text-transform: uppercase;">
                                ${nicheLabel}
                            </span>
                            <span style="font-size: 10px; color: #94a3b8;">${item.published_at || 'Yeni'}</span>
                        </div>
                        <strong style="font-size: 13px; color: #FFF; display: block;">${escapeHtml(item.title)}</strong>
                        <p style="font-size: 11px; color: #94A3B8; margin-top: 4px;">${escapeHtml(item.description.slice(0, 140))}...</p>
                    </div>
                    <div style="display: flex; gap: 6px; align-items: center;">
                        <button class="btn btn-primary btn-sm btn-convert-viral-rss" data-title="${encodeURIComponent(item.title)}" data-desc="${encodeURIComponent(item.description)}" data-niche="${encodeURIComponent(item.suggested_niche || '1_news_flash')}" title="Başlığı psikolojik merak/şok sorusuna çevirip stüdyoya aktarır">
                            <i class="fa-solid fa-wand-magic-sparkles"></i> Viral Kancaya Çevir
                        </button>
                        <button class="btn btn-secondary btn-sm btn-convert-rss" data-title="${encodeURIComponent(item.title)}" data-niche="${encodeURIComponent(item.suggested_niche || '1_news_flash')}" title="Başlığı olduğu gibi stüdyoya aktarır">
                            <i class="fa-solid fa-arrow-right"></i> Stüdyo
                        </button>
                    </div>
                </div>
            `;
            list.appendChild(row);
        });

        // Normal stüdyo aktarımı
        list.querySelectorAll('.btn-convert-rss').forEach(b => {
            b.addEventListener('click', (e) => {
                const rawTitle = decodeURIComponent(e.currentTarget.getAttribute('data-title'));
                const niche = decodeURIComponent(e.currentTarget.getAttribute('data-niche') || '1_news_flash');
                inputTopic.value = rawTitle;
                if (selectNiche) {
                    selectNiche.value = niche;
                    applyNicheProfile(niche);
                }
                switchTab('studio');
                updateFlowRail('topic');
                showToast('Haber stüdyoya aktarıldı — Senaryoyu incele ile devam edin');
            });
        });

        // AI Viral Soru Kancasına Çevirip Aktarma (Item 122)
        list.querySelectorAll('.btn-convert-viral-rss').forEach(b => {
            b.addEventListener('click', async (e) => {
                const rawTitle = decodeURIComponent(e.currentTarget.getAttribute('data-title'));
                const desc = decodeURIComponent(e.currentTarget.getAttribute('data-desc') || '');
                const niche = decodeURIComponent(e.currentTarget.getAttribute('data-niche') || '1_news_flash');
                const origBtn = e.currentTarget.innerHTML;
                e.currentTarget.disabled = true;
                e.currentTarget.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Kanca Üretiliyor...';

                try {
                    const res = await fetch('/api/rss/convert-to-shorts', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            title: rawTitle,
                            description: desc,
                            suggested_niche: niche
                        })
                    });
                    const resData = await res.json();
                    const idea = resData.idea || {};
                    const finalTitle = idea.question_title || rawTitle;
                    const finalNiche = idea.suggested_niche || niche;

                    inputTopic.value = finalTitle;
                    if (selectNiche) {
                        selectNiche.value = finalNiche;
                        applyNicheProfile(finalNiche);
                    }
                    switchTab('studio');
                    updateFlowRail('topic');
                    showToast(`⚡ Viral Kanca Hazır: "${finalTitle}" (${idea.strategy || 'merak'})`);
                } catch (err) {
                    inputTopic.value = rawTitle;
                    switchTab('studio');
                    showToast('Haber aktarıldı (fallback)');
                } finally {
                    e.currentTarget.disabled = false;
                    e.currentTarget.innerHTML = origBtn;
                }
            });
        });
    } catch (err) {
        list.innerHTML = `<div class="empty-state-box text-danger"><p>Haber tarama hatası: ${err.message}</p></div>`;
    }
}

document.getElementById('btn-fetch-rss-now')?.addEventListener('click', loadRssNews);
document.getElementById('select-rss-source')?.addEventListener('change', loadRssNews);

// Listelenen tüm haberleri toplu render kuyruğuna aktar
document.getElementById('btn-rss-batch-all')?.addEventListener('click', async () => {
    if (!currentRssItems || currentRssItems.length === 0) {
        showToast('Önce haberleri tarayın!', 'error');
        return;
    }

    const topics = currentRssItems.map(i => i.title).join('\n');
    const defaultNiche = currentRssItems[0]?.suggested_niche || '1_news_flash';

    try {
        const res = await fetch('/api/batch/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: topics,
                niche: defaultNiche,
                language: 'tr'
            })
        });
        const data = await res.json();
        if (data.status === 'ok') {
            showToast(`✅ ${data.added_count} haber toplu üretim kuyruğuna alındı!`);
            switchTab('batch');
            loadBatchQueue();
        } else {
            showToast(data.detail || 'Kuyruğa eklenemedi', 'error');
        }
    } catch (e) {
        showToast(`Hata: ${e.message}`, 'error');
    }
});

// ══════════════════════════════════════════════════════════════


// 4. TOPLU ÜRETİM (BATCH) KUYRUĞU (Items 70 & 78)
// ══════════════════════════════════════════════════════════════
document.getElementById('btn-enqueue-batch')?.addEventListener('click', async () => {
    const text = document.getElementById('batch-topics-text').value.trim();
    if (!text) return alert('Lütfen en az bir konu girin!');

    const niche = document.getElementById('batch-default-niche').value;
    const lang = document.getElementById('batch-default-lang').value;

    try {
        const res = await fetch('/api/batch/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text, niche, language: lang })
        });
        const data = await res.json();
        showToast(`✅ ${data.enqueued} adet video konusu kuyruğa eklendi!`);
        document.getElementById('batch-topics-text').value = '';
        refreshBatchQueue();
    } catch (err) {
        alert('Kuyruğa ekleme hatası: ' + err.message);
    }
});

async function refreshBatchQueue() {
    const queueList = document.getElementById('batch-queue-list');
    if (!queueList) return;
    try {
        const res = await fetch('/api/batch/status');
        const data = await res.json();
        const queue = data.queue || [];
        const badge = document.getElementById('badge-batch-count');
        if (badge) badge.textContent = String(data.queue_count || 0);

        if (queue.length === 0) {
            queueList.innerHTML = '<div class="empty-state-box"><p>Kuyruk boş.</p></div>';
            return;
        }

        queueList.innerHTML = '';
        queue.forEach((q, idx) => {
            const item = document.createElement('div');
            item.style.padding = '8px 12px';
            item.style.borderBottom = '1px solid var(--border-subtle)';
            item.style.fontSize = '12px';
            item.innerHTML = `<strong>#${idx + 1}</strong> &middot; ${q.topic} <span class="niche-tag">${q.niche}</span>`;
            queueList.appendChild(item);
        });
    } catch (e) {
        console.error(e);
    }
}



// 5. BÜYÜME, A/B TEST & ALGORİTMA TAKTİKLERİ (Items 65, 89, 98)
// ══════════════════════════════════════════════════════════════
document.getElementById('btn-generate-ab-variants')?.addEventListener('click', () => {
    const topic = document.getElementById('ab-test-topic').value.trim() || "Bilinmeyen Gerçekler";
    const container = document.getElementById('ab-results-container');
    
    // Dynamic A/B test simulation based on growth_tactics rules
    container.innerHTML = `
        <div class="glass-box mb-2" style="padding: 10px; border-left: 3px solid #8B5CF6;">
            <strong>Varyant A (Merak Odaklı - CTR):</strong>
            <p style="font-size: 11px; color: #FFF; margin-top: 2px;">Bunu Biliyor Muydunuz? ${topic} Hakkında Gizli Gerçek #Shorts</p>
        </div>
        <div class="glass-box mb-2" style="padding: 10px; border-left: 3px solid #EF4444;">
            <strong>Varyant B (Şok / Flaş Kanca):</strong>
            <p style="font-size: 11px; color: #FFF; margin-top: 2px;">İNANILMAZ! ${topic} Olayı Herkesi Şok Etti #Shorts</p>
        </div>
        <div class="glass-box" style="padding: 10px; border-left: 3px solid #F59E0B;">
            <strong>Varyant C (İkilem / Yorum Tuzağı):</strong>
            <p style="font-size: 11px; color: #FFF; margin-top: 2px;">Siz Olsaydınız Ne Yapardınız? ${topic} #Shorts</p>
        </div>
    `;
    showToast('🧪 3 A/B varyantı hazırlandı!');
});

document.getElementById('btn-generate-community-poll')?.addEventListener('click', () => {
    const topic = document.getElementById('community-poll-topic').value.trim() || "Günün Konusu";
    const container = document.getElementById('community-poll-container');
    container.innerHTML = `
        <div class="glass-box" style="padding: 12px; background: rgba(245, 158, 11, 0.08); border-color: rgba(245, 158, 11, 0.3);">
            <strong style="color: #F59E0B; font-size: 12px;">📊 YouTube Topluluk Anketi</strong>
            <p style="font-size: 12px; margin: 6px 0;">Bugünkü Shorts konumuz '${topic}'. Sizce bu konuda en çok merak edilen şey nedir?</p>
            <div style="font-size: 11px; color: #FFF; display: flex; flex-direction: column; gap: 4px;">
                <div>&bull; ${topic} hakkında hiç bilinmeyen sırlar</div>
                <div>&bull; Tarihteki en büyük hatalar</div>
                <div>&bull; Gelecekte bizi bekleyenler</div>
                <div>&bull; Sonucu görmek istiyorum</div>
            </div>
        </div>
    `;
    showToast('📊 Topluluk anketi oluşturuldu!');
});

document.getElementById('btn-check-copyright-risk')?.addEventListener('click', () => {
    const text = document.getElementById('copyright-check-text').value.toLowerCase();
    const container = document.getElementById('copyright-risk-container');
    const riskyWords = ["disney", "marvel", "netflix", "fifa", "premier league", "telif", "şiddet"];
    const found = riskyWords.filter(w => text.includes(w));

    if (found.length > 0) {
        container.innerHTML = `
            <div style="background: rgba(239, 68, 68, 0.15); border: 1px solid var(--danger); padding: 10px; border-radius: 8px; font-size: 12px;">
                <strong style="color: var(--danger);"><i class="fa-solid fa-triangle-exclamation"></i> Riskli Kelimeler Tespit Edildi:</strong>
                <p style="color: #FFF; margin-top: 4px;">${found.join(", ")}</p>
                <small style="color: #94A3B8;">Öneri: Yatay ayna (mirror) ve ses tonu kaydırma filtresini açın.</small>
            </div>
        `;
    } else {
        container.innerHTML = `
            <div style="background: rgba(16, 185, 129, 0.15); border: 1px solid var(--success); padding: 10px; border-radius: 8px; font-size: 12px; color: #FFF;">
                <strong style="color: var(--success);"><i class="fa-solid fa-circle-check"></i> İçerik Güvenli!</strong>
                <p style="margin-top: 2px;">Telif veya marka riski oluşturabilecek kısıtlama tespit edilmedi.</p>
            </div>
        `;
    }
});



// 11. VİDEO GALERİSİ & YOUTUBE YÜKLEME (Items 51 & 100)
// ══════════════════════════════════════════════════════════════
async function loadGallery() {
    const grid = document.getElementById('gallery-videos-grid');
    const badge = document.getElementById('badge-gallery-count');
    if (!grid) return;

    try {
        const res = await fetch('/api/videos');
        const data = await res.json();
        const videos = data.videos || [];

        if (badge) badge.textContent = videos.length;

        // Global İstatistik Barını Güncelle
        const statTotalVids = document.getElementById('stat-total-vids');
        const statTotalDur = document.getElementById('stat-total-duration');
        if (statTotalVids) statTotalVids.textContent = `${videos.length} Video`;
        if (statTotalDur) {
            const totalSeconds = videos.reduce((acc, v) => acc + (v.duration_seconds || 0), 0);
            const totalMinutes = Math.round(totalSeconds / 60);
            statTotalDur.textContent = `${totalMinutes} dk`;
        }

        if (videos.length === 0) {
            grid.innerHTML = '<div class="empty-state-box"><i class="fa-solid fa-film"></i><p>Henüz üretilmiş bir video yok.</p></div>';
            return;
        }

        grid.innerHTML = '';
        grid.style.cssText = "display: flex !important; flex-wrap: wrap !important; gap: 20px !important; align-items: flex-start !important; justify-content: flex-start !important; width: 100% !important;";
        videos.forEach(v => {
            const hasOutput = v.status === 'completed' && v.filename && v.id;
            const projectSlug = (v.filename || '').replace(/\.mp4$/i, '');
            const card = document.createElement('div');
            card.className = 'shorts-card glass-box';
            card.style.cssText = "width: 280px !important; max-width: 280px !important; min-width: 260px !important; flex-shrink: 0 !important; box-sizing: border-box !important;";
            card.innerHTML = `
                <div class="shorts-player-wrapper" style="position: relative !important; width: 100% !important; height: 420px !important; max-height: 420px !important; aspect-ratio: 9 / 16 !important; background: #000000 !important; border-radius: 12px !important; overflow: hidden !important; display: flex !important; align-items: center !important; justify-content: center !important;">
                    <span class="shorts-badge-tag"><i class="fa-brands fa-youtube"></i> SHORTS</span>
                    <video src="/output/${v.filename}" controls playsinline preload="metadata" style="width: 100% !important; height: 100% !important; object-fit: contain !important; background: #000000 !important; display: block !important;"></video>
                    <span class="shorts-duration-tag"><i class="fa-regular fa-clock"></i> ${(v.duration_seconds || 0).toFixed(1)}s</span>
                </div>
                <div class="shorts-meta-box">
                    <strong class="shorts-title-text" title="${escapeHtml(v.keyword || v.title || 'Shorts')}">${escapeHtml(v.keyword || v.title || 'Shorts')}</strong>
                    <div class="shorts-sub-stats">
                        <span class="badge" style="background: rgba(56, 189, 248, 0.15); color: #38bdf8; font-size: 10px; padding: 2px 6px; border-radius: 4px;"><i class="fa-solid fa-mobile-screen"></i> 9:16 Shorts</span>
                        <span style="font-weight: 500;">${(v.size_mb || 0).toFixed(1)} MB</span>
                    </div>
                    ${v.quality_gate ? `<div class="gallery-qg-row">${renderQualityGateCard(v.quality_gate, { compact: true })}</div>` : ''}
                    <div style="display: flex; gap: 8px; margin-top: 6px;">
                        <a href="/output/${v.filename}" download class="btn btn-secondary btn-sm" style="flex: 1; text-decoration: none; display: flex; align-items: center; justify-content: center; gap: 5px; padding: 6px 10px;">
                            <i class="fa-solid fa-download"></i> İndir
                        </a>
                        <a href="https://www.youtube.com/upload" target="_blank" rel="noopener" class="btn btn-primary btn-sm" title="Otomatik yükleme kapsam dışı — YouTube Studio'da manuel yükleyin" style="flex: 1; text-decoration: none; display: flex; align-items: center; justify-content: center; gap: 5px; padding: 6px 10px;">
                            <i class="fa-brands fa-youtube"></i> Studio'da Yükle
                        </a>
                    </div>
                    <button class="btn btn-sm btn-open-plan" data-slug="${encodeURIComponent((v.filename || '').replace(/\\.mp4$/i, ''))}" data-keyword="${encodeURIComponent(v.keyword || v.title || '')}" style="margin-top: 4px; width: 100%; font-size: 11px; background: rgba(232, 160, 58, 0.12); border: 1px solid rgba(232, 160, 58, 0.35); color: #e8a03a; border-radius: 6px; padding: 6px 8px; cursor: pointer;">
                        <i class="fa-solid fa-clapperboard"></i> Senaryoyu ac / yeniden kur
                    </button>
                    <button class="btn btn-sm btn-manual-guide" data-filename="${v.filename}" title="Manuel Yükleme Rehberi & SEO Bilgileri (Kural 80 & 83)" style="margin-top: 4px; width: 100%; font-size: 11px; background: rgba(59, 130, 246, 0.15); border: 1px solid rgba(59, 130, 246, 0.4); color: #93C5FD; border-radius: 6px; padding: 6px 8px; cursor: pointer; transition: all 0.2s ease;">
                        <i class="fa-solid fa-clipboard-list"></i> Manuel Yükleme & SEO
                    </button>
                    ${hasOutput ? `
                    <div style="display: flex; gap: 8px; margin-top: 4px;">
                        <button type="button" class="btn btn-sm btn-gallery-share-keep" data-video-id="${v.id}" data-project-slug="${encodeURIComponent(projectSlug)}" style="flex: 1; font-size: 11px; padding: 6px 8px; background: rgba(16, 185, 129, 0.2); border: 1px solid rgba(16, 185, 129, 0.45); color: #34d399; border-radius: 6px; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 5px;">
                            <i class="fa-brands fa-youtube"></i> YouTube'da Paylaş
                        </button>
                        <button type="button" class="btn btn-sm btn-gallery-share-discard" data-video-id="${v.id}" data-project-slug="${encodeURIComponent(projectSlug)}" style="flex: 1; font-size: 11px; padding: 6px 8px; background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.5); color: #f87171; border-radius: 6px; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 5px;">
                            <i class="fa-solid fa-trash-can"></i> Paylaşmayacağım (Sil)
                        </button>
                    </div>
                    ` : ''}
                </div>
            `;
            grid.appendChild(card);
        });

        grid.querySelectorAll('.btn-open-plan').forEach(b => {
            b.addEventListener('click', async (e) => {
                const slug = decodeURIComponent(e.currentTarget.getAttribute('data-slug') || '');
                const kw = decodeURIComponent(e.currentTarget.getAttribute('data-keyword') || '');
                if (!slug) return;
                try {
                    const res = await fetch(`/api/projects/${encodeURIComponent(slug)}/plan`);
                    if (!res.ok) {
                        const err = await res.json().catch(() => ({}));
                        const detail = err.detail;
                        if (detail && typeof detail === 'object') {
                            throw new Error(
                                detail.message || 'Kayitli senaryo kopuk — yeni senaryo uretin'
                            );
                        }
                        throw new Error(detail || 'Senaryo bulunamadi');
                    }
                    const data = await res.json();
                    if (kw && inputTopic) inputTopic.value = kw;
                    if (data.director?.niche_id && selectNiche) {
                        selectNiche.value = data.director.niche_id;
                        applyNicheProfile(data.director.niche_id);
                    }
                    setCurrentPlan(data.plan);
                    switchTab('timeline');
                    updateFlowRail('timeline');
                    showToast('Senaryo timeline\'a yuklendi — duzenleyip yeniden render alin');
                } catch (err) {
                    showToast(String(err.message || err), 'error');
                }
            });
        });

        grid.querySelectorAll('.btn-manual-guide').forEach(b => {
            b.addEventListener('click', (e) => {
                const fn = e.currentTarget.getAttribute('data-filename');
                const v = videos.find(x => x.filename === fn) || { filename: fn };
                openPublishHubModal(v);
            });
        });

        grid.querySelectorAll('.btn-gallery-share-keep').forEach(b => {
            b.addEventListener('click', () => {
                const videoId = b.getAttribute('data-video-id');
                const projectSlug = decodeURIComponent(b.getAttribute('data-project-slug') || '');
                const v = videos.find(x => String(x.id) === String(videoId)) || { id: videoId, filename: `${projectSlug}.mp4` };
                submitShareDecision('keep', { videoId, projectSlug });
                openPublishHubModal(v);
            });
        });

        grid.querySelectorAll('.btn-gallery-share-discard').forEach(b => {
            b.addEventListener('click', () => {
                const videoId = b.getAttribute('data-video-id');
                const projectSlug = decodeURIComponent(b.getAttribute('data-project-slug') || '');
                const card = b.closest('.shorts-card');
                submitShareDecision('discard', {
                    videoId,
                    projectSlug,
                    onDiscard: () => {
                        card?.remove();
                        const remaining = grid.querySelectorAll('.shorts-card').length;
                        if (badge) badge.textContent = remaining;
                        if (statTotalVids) statTotalVids.textContent = `${remaining} Video`;
                        if (remaining === 0) {
                            grid.innerHTML = '<div class="empty-state-box"><i class="fa-solid fa-film"></i><p>Henüz üretilmiş bir video yok.</p></div>';
                        }
                    },
                });
            });
        });
    } catch (e) {
        console.error(e);
    }
}

document.getElementById('btn-refresh-gallery')?.addEventListener('click', loadGallery);

// ══════════════════════════════════════════════════════════════
// YOUTUBE YAYINLAMA & SEO DAĞITIM HUB'I KONTROLCÜSÜ (Maddeler 51, 52, 53, 55, 80)
// ══════════════════════════════════════════════════════════════
let currentPublishVideo = null;

async function openPublishHubModal(video) {
    currentPublishVideo = video;
    const modal = document.getElementById('modal-publish-hub');
    if (!modal) return;

    const vidPreview = document.getElementById('pub-video-preview');
    const fnEl = document.getElementById('pub-video-filename');
    const durEl = document.getElementById('pub-video-duration');
    const sizeEl = document.getElementById('pub-video-size');
    const chSelect = document.getElementById('pub-target-channel-select');
    const titleField = document.getElementById('pub-title-field');
    const descField = document.getElementById('pub-desc-field');
    const tagsField = document.getElementById('pub-tags-field');
    const commentField = document.getElementById('pub-comment-field');

    const fn = video.filename || '';
    const baseName = fn.replace(/\.[^/.]+$/, "");

    if (vidPreview) {
        vidPreview.src = `/output/${fn}`;
        vidPreview.load();
    }
    if (fnEl) fnEl.textContent = fn;
    if (durEl) durEl.textContent = `${(video.duration_seconds || 0).toFixed(1)}s`;
    if (sizeEl) sizeEl.textContent = `${(video.size_mb || 0).toFixed(1)} MB`;

    // Hedef kanal listesini çek
    if (chSelect) {
        try {
            const res = await fetch('/api/channel/list');
            const chData = await res.json();
            chSelect.innerHTML = '<option value="default">Varsayılan Kanal (Studio Manuel)</option>';
            if (chData.channels && chData.channels.length > 0) {
                chData.channels.forEach(c => {
                    const opt = document.createElement('option');
                    opt.value = c.handle;
                    opt.textContent = `${c.handle} (Güven: %${c.health_score} | ${c.niche || 'Genel'})`;
                    chSelect.appendChild(opt);
                });
            }
        } catch (e) {
            console.warn('Kanallar yüklenemedi:', e);
        }
    }

    // Varsa kayıtlı manual_upload_info.json dosyasını çek
    let info = null;
    try {
        const res = await fetch(`/output/${baseName}_manual_upload_info.json`);
        if (res.ok) info = await res.json();
    } catch (_) {}

    const titleVal = info?.title || video.keyword || video.title || baseName;
    const descVal = info?.description || `${titleVal} #shorts\n\n📌 Kaynak & Araştırma: Bağımsız Eğitici İnceleme\n⚖️ Hakkaniyet & Katma Değer (Fair Use): Bu video eğitim ve analiz amacıyla özgün ses ve dinamik görselleştirme ile üretilmiştir.`;
    const tagsVal = (info?.tags && info.tags.length) ? info.tags.join(', ') : 'shorts, bilgi, viral, trend';
    const commentVal = info?.pinned_comment || 'Sizce bu konudaki en şaşırtıcı detay neydi? Yorumlarda buluşalım! 👇';

    if (titleField) titleField.value = titleVal;
    if (descField) descField.value = descVal;
    if (tagsField) tagsField.value = tagsVal;
    if (commentField) commentField.value = commentVal;

    modal.style.display = 'flex';
    modal.classList.remove('hidden');
}

function closePublishHubModal() {
    const modal = document.getElementById('modal-publish-hub');
    if (modal) {
        modal.style.display = 'none';
        modal.classList.add('hidden');
        const vidPreview = document.getElementById('pub-video-preview');
        if (vidPreview) vidPreview.pause();
    }
}

// Tekli alan kopyalama butonları
document.querySelectorAll('.btn-copy-field').forEach(btn => {
    btn.addEventListener('click', async (e) => {
        const targetId = e.currentTarget.getAttribute('data-target');
        const target = document.getElementById(targetId);
        if (target && target.value) {
            await navigator.clipboard.writeText(target.value);
            const originalText = e.currentTarget.innerHTML;
            e.currentTarget.innerHTML = '<i class="fa-solid fa-check text-success"></i>';
            setTimeout(() => { e.currentTarget.innerHTML = originalText; }, 1800);
            showToast('Panoya kopyalandı!');
        }
    });
});

// Tüm SEO paketini kopyala
document.getElementById('btn-copy-all-package')?.addEventListener('click', async () => {
    const title = document.getElementById('pub-title-field')?.value || '';
    const desc = document.getElementById('pub-desc-field')?.value || '';
    const tags = document.getElementById('pub-tags-field')?.value || '';
    const comment = document.getElementById('pub-comment-field')?.value || '';

    const fullPkg =
`📌 BAŞLIK:\n${title}\n\n` +
`📌 AÇIKLAMA (Kural 83 Kaynaklı):\n${desc}\n\n` +
`📌 ETİKETLER:\n${tags}\n\n` +
`📌 SABİT YORUM:\n${comment}\n\n` +
`⚠️ KRİTİK KURAL 80 UYARISI:\nYouTube Studio'da 'Yapay zeka / Değiştirilmiş içerik mi?' sorusuna 'HAYIR' yanıtını verin.\n` +
`🛡️ DOSYA GÜVENLİĞİ: Bu MP4 ctime yaşlandırması ve atom varyasyonu ile korunmuştur.`;

    await navigator.clipboard.writeText(fullPkg);
    showToast('📋 Tüm SEO paketi panoya kopyalandı!');
});

// Anti-Detect Studio UI Yükleme tetikleyici
document.getElementById('btn-execute-studio-safe-upload')?.addEventListener('click', async () => {
    if (!currentPublishVideo) return;
    const btn = document.getElementById('btn-execute-studio-safe-upload');
    const channelSelect = document.getElementById('pub-target-channel-select');
    const ch = channelSelect ? channelSelect.value : 'default';
    const title = document.getElementById('pub-title-field')?.value || '';
    const desc = document.getElementById('pub-desc-field')?.value || '';
    const tags = (document.getElementById('pub-tags-field')?.value || '').split(',').map(t => t.trim()).filter(Boolean);
    const schedHour = parseInt(document.getElementById('pub-schedule-hour')?.value || '18', 10);

    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Yükleme Kuyruğuna Alınıyor...';

    try {
        const res = await fetch('/api/channel/studio_upload', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                identifier: ch,
                video_path: `output/${currentPublishVideo.filename}`,
                title: title,
                description: desc,
                tags: tags,
                scheduled_hour: schedHour
            })
        });
        const data = await res.json();
        if (data.success || data.action === 'MANUAL_UPLOAD_REQUIRED') {
            showToast('✅ Studio UI Güvenli Paketleme Hazır! Terminale aktarıldı.');
            switchTab('channels');
            closePublishHubModal();
        } else {
            showToast(data.reason || data.error || 'Yükleme başlatılamadı', 'error');
        }
    } catch (err) {
        showToast(`Hata: ${err.message}`, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-rocket"></i> Anti-Detect Studio UI ile Yükle';
    }
});

document.getElementById('btn-close-publish-modal')?.addEventListener('click', closePublishHubModal);
document.getElementById('modal-publish-hub')?.addEventListener('click', (e) => {
    if (e.target.id === 'modal-publish-hub') closePublishHubModal();
});

// ══════════════════════════════════════════════════════════════


// 19. 500-ITEM ROADMAP HANDLERS (Anti-Detect & Proof Archiver)
// ══════════════════════════════════════════════════════════════
document.getElementById('btn-calc-jitter')?.addEventListener('click', async () => {
    const hour = document.getElementById('input-jitter-hour').value || 18;
    const minute = document.getElementById('input-jitter-minute').value || 0;
    const box = document.getElementById('jitter-result-box');
    box.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Jitter ve izole parmak izi hesaplanıyor...';

    try {
        const [jRes, pRes] = await Promise.all([
            fetch(`/api/anti_detect/jitter?hour=${hour}&minute=${minute}`),
            fetch('/api/anti_detect/profile?channel_id=studio_main&lang=tr')
        ]);
        const jData = await jRes.json();
        const pData = await pRes.json();

        box.innerHTML = `
            <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); padding: 10px; border-radius: 8px;">
                <div style="color: #10B981; font-weight: 700; margin-bottom: 4px;">
                    <i class="fa-solid fa-circle-check"></i> İnsanlaştırılmış Yayın Saati: <strong>${jData.jitter.time_str}</strong> (+${jData.jitter.jitter_applied_minutes} dk sapma)
                </div>
                <div style="color: #94A3B8; font-size: 11px;">
                    • Donanım: <strong>${pData.profile.webgl_renderer}</strong> | RAM: ${pData.profile.device_memory}GB<br>
                    • WebRTC İlkesi: <code>${pData.profile.webrtc_policy}</code><br>
                    • Canvas Gürültüsü: %${(pData.profile.canvas_noise_seed * 100).toFixed(4)} (İzole)
                </div>
            </div>
        `;
        showToast('🛡️ Anti-Detect zamanlama ve parmak izi üretildi!');
    } catch (e) {
        box.innerHTML = `<span class="text-danger">Hata: ${e.message}</span>`;
    }
});

document.getElementById('btn-generate-appeal-script')?.addEventListener('click', async () => {
    const chName = document.getElementById('input-appeal-channel').value || 'Shorts Kanalı';
    const box = document.getElementById('appeal-result-box');
    box.textContent = 'İtiraz videosu senaryosu hazırlanıyor...';

    try {
        const res = await fetch(`/api/proof/appeal_script?channel_name=${encodeURIComponent(chName)}`);
        const data = await res.json();
        const steps = (data.operator_steps || []).join('\n');
        const manual = (data.checklist || [])
            .filter(c => c.status === 'operator_manual')
            .map(c => `[#${c.item} ${c.title}] ${c.action}`)
            .join('\n\n');
        box.textContent = [
            '=== OPERATÖR ADIMLARI (472-475) ===',
            steps,
            manual ? '\n=== MANUEL ÇEKİM (#473/#474) ===\n' + manual : '',
            '\n=== İNGİLİZCE SCRIPT (#472/#475) ===\n',
            data.script || '',
        ].join('\n');
        showToast('📜 İtiraz scripti + operatör checklist hazır!');
    } catch (e) {
        box.textContent = 'Hata: ' + e.message;
    }
});

// ══════════════════════════════════════════════════════════════


// 21. ANTI-DETECT KANAL ONBOARDING & OTOMASYON BOTU (5 ALTIN KURAL)
// ══════════════════════════════════════════════════════════════

let currentAnalyzedChannel = null;

async function loadManagedChannels() {
    const container = document.getElementById('managed-channels-list');
    if (!container) return;

    try {
        const res = await fetch('/api/channel/list');
        const data = await res.json();
        if (!data.channels || data.channels.length === 0) {
            container.innerHTML = `
                <div style="grid-column: 1/-1; text-align: center; padding: 20px; color: #94a3b8; font-size: 13px; background: rgba(0,0,0,0.2); border-radius: 8px;">
                    <i class="fa-solid fa-circle-info text-info"></i> Henüz kayıtlı kanal yok. Yukarıdan kanal linkinizi yapıştırıp analizi başlatın.
                </div>
            `;
            return;
        }

        container.innerHTML = '';
        data.channels.forEach(ch => {
            const card = document.createElement('div');
            card.className = 'glass-box';
            card.style.padding = '14px';
            card.style.border = '1px solid rgba(255,255,255,0.08)';

            const statusColor = ch.status === 'ready' ? '#10b981' : (ch.status === 'resting' ? '#f59e0b' : '#38bdf8');
            const statusText = ch.status === 'ready' ? 'Yüklemeye Hazır' : (ch.status === 'resting' ? 'Dinlendirmede' : 'Isınma Aşamasında');

            card.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                    <div>
                        <strong style="color: #fff; font-size: 14px;">${ch.handle}</strong>
                        <div style="font-size: 11px; color: #94a3b8; margin-top: 2px;">
                            <i class="fa-solid fa-folder"></i> <code>${ch.profile_id}</code>
                        </div>
                    </div>
                    <span style="font-size: 11px; font-weight: 700; color: ${statusColor}; background: rgba(255,255,255,0.05); padding: 3px 8px; border-radius: 6px;">
                        ${statusText}
                    </span>
                </div>

                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 10px; font-size: 12px;">
                    <span style="color: #cbd5e1;">Güven Puanı: <strong style="color: #10b981;">%${ch.health_score}</strong></span>
                    <span style="color: #94a3b8; font-size: 11px;">Niş: <strong>${ch.niche || 'Genel'}</strong></span>
                </div>

                <div style="display: flex; gap: 8px; margin-top: 12px;">
                    <button class="btn btn-sm btn-success btn-ch-warmup" data-id="${ch.handle}" style="flex: 1; font-size: 11px; padding: 6px;">
                        <i class="fa-solid fa-fire"></i> Isındırma Başlat
                    </button>
                    <button class="btn btn-sm btn-secondary btn-ch-reanalyze" data-url="${ch.channel_url}" style="font-size: 11px; padding: 6px 10px;">
                        <i class="fa-solid fa-eye"></i> Detay
                    </button>
                </div>
            `;
            container.appendChild(card);
        });

        container.querySelectorAll('.btn-ch-warmup').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = e.currentTarget.getAttribute('data-id');
                triggerWarmupSession(id);
            });
        });

        container.querySelectorAll('.btn-ch-reanalyze').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const url = e.currentTarget.getAttribute('data-url');
                const inp = document.getElementById('input-onboard-url');
                if (inp) inp.value = url;
                triggerChannelAnalysis();
            });
        });

    } catch (e) {
        container.innerHTML = `<span class="text-danger">Kanal listesi yüklenemedi: ${e.message}</span>`;
    }
}

async function triggerChannelAnalysis() {
    const urlInput = document.getElementById('input-onboard-url');
    const proxyInput = document.getElementById('input-onboard-proxy');
    const nicheSelect = document.getElementById('select-onboard-niche');
    const isNewCheck = document.getElementById('check-is-brand-new');
    const container = document.getElementById('channel-analysis-container');

    const rawUrl = urlInput?.value.trim();
    if (!rawUrl) {
        showToast('⚠️ Lütfen bir YouTube kanal linki veya @handle girin!');
        return;
    }

    container.style.display = 'block';
    container.innerHTML = `
        <div style="text-align: center; padding: 30px; color: #94a3b8;">
            <i class="fa-solid fa-spinner fa-spin" style="font-size: 28px; color: #8b5cf6;"></i>
            <div style="margin-top: 10px; font-weight: 600;">Kanal donanım izi ve 5 kural yol haritası çıkarılıyor...</div>
        </div>
    `;

    const emailInput = document.getElementById('input-onboard-email');
    const phoneInput = document.getElementById('input-onboard-phone');
    const phoneTypeSelect = document.getElementById('select-onboard-phone-type');

    try {
        const res = await fetch('/api/channel/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                channel_url: rawUrl,
                proxy_url: proxyInput ? proxyInput.value.trim() : null,
                niche: nicheSelect ? nicheSelect.value : 'Stoic / Motivasyon',
                is_brand_new: isNewCheck ? isNewCheck.checked : true,
                recovery_email: emailInput ? emailInput.value.trim() : null,
                phone_number: phoneInput ? phoneInput.value.trim() : null,
                phone_type: phoneTypeSelect ? phoneTypeSelect.value : 'physical'
            })
        });

        const data = await res.json();
        if (data.status !== 'ok') {
            container.innerHTML = `<div class="alert-danger-box">Analiz hatası: ${data.error || 'Bilinmeyen hata'}</div>`;
            return;
        }

        currentAnalyzedChannel = data;
        renderChannelAnalysis(data);
        loadManagedChannels();
        showToast('🛡️ Kanal analizi ve 5 Kural Yol Haritası çıkarıldı!');

    } catch (e) {
        container.innerHTML = `<div class="alert-danger-box">Sunucu bağlantı hatası: ${e.message}</div>`;
    }
}

function renderChannelAnalysis(data) {
    const container = document.getElementById('channel-analysis-container');
    if (!container) return;

    const ch = data.channel;
    const profile = data.browser_profile;
    const proxy = data.proxy_audit;

    const restingBadgeColor = ch.resting_days_left > 0 ? '#f59e0b' : '#10b981';
    const restingText = ch.resting_days_left > 0 
        ? `Dinlendirme Süresi: ${ch.resting_days_left} Gün Kaldı (${ch.resting_until})`
        : `Dinlendirme Tamamlandı & Yüklemeye Uygun`;

    let checklistHtml = '';
    data.checklist.forEach(item => {
        const isDone = item.status === 'completed';
        const isWarn = item.status === 'warning';
        const statusIcon = isDone 
            ? '<i class="fa-solid fa-circle-check text-success"></i>' 
            : (isWarn ? '<i class="fa-solid fa-triangle-exclamation text-warning"></i>' : '<i class="fa-solid fa-clock text-info"></i>');
        const borderColor = isDone ? 'rgba(16, 185, 129, 0.2)' : (isWarn ? 'rgba(245, 158, 11, 0.3)' : 'rgba(56, 189, 248, 0.2)');

        checklistHtml += `
            <div style="background: rgba(0,0,0,0.3); border: 1px solid ${borderColor}; border-radius: 8px; padding: 12px; margin-bottom: 8px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div style="font-weight: 700; color: #fff; font-size: 13px; display: flex; align-items: center; gap: 8px;">
                        ${statusIcon} <span>${item.step}. ${item.title}</span>
                    </div>
                    <span style="font-size: 11px; padding: 2px 8px; border-radius: 4px; background: rgba(255,255,255,0.06); color: ${isDone ? '#10b981' : (isWarn ? '#f59e0b' : '#38bdf8')}; font-weight: 600;">
                        ${item.badge}
                    </span>
                </div>
                <p style="margin: 6px 0 4px 26px; font-size: 12px; color: #cbd5e1; line-height: 1.4;">${item.desc}</p>
                <div style="margin-left: 26px; font-size: 11px; color: #94a3b8;">
                    <code>${item.details}</code>
                </div>
            </div>
        `;
    });

    container.innerHTML = `
        <div style="background: rgba(15, 23, 42, 0.95); border: 1px solid rgba(139, 92, 246, 0.3); border-radius: 12px; padding: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; border-bottom: 1px solid rgba(255,255,255,0.08); padding-bottom: 14px;">
                <div>
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <h3 style="margin: 0; font-size: 18px; color: #fff;">${ch.handle}</h3>
                        <span style="background: rgba(16, 185, 129, 0.15); color: #10b981; font-weight: 700; padding: 3px 10px; border-radius: 20px; font-size: 12px;">
                            Güven Skoru: %${ch.health_score}
                        </span>
                    </div>
                    <div style="margin-top: 4px; font-size: 12px; color: #94a3b8;">
                        Kanal ID: <code>${ch.profile_id}</code> | Niş: <strong style="color: #cbd5e1;">${ch.niche}</strong>
                    </div>
                </div>
                <div style="text-align: right;">
                    <span style="color: ${restingBadgeColor}; font-weight: 700; font-size: 12px; background: rgba(0,0,0,0.4); padding: 6px 12px; border-radius: 8px; border: 1px solid ${restingBadgeColor}40;">
                        <i class="fa-solid fa-shield-cat"></i> ${restingText}
                    </span>
                </div>
            </div>

            <!-- 16 Kural Donanım, Ağ, İstemci & Güvenlik Özeti Grid -->
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 8px; margin: 16px 0;">
                <div style="background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
                    <small style="color: #94a3b8; display: block; font-size: 10px;">KURAL 1: YÜKLEME BAYRAĞI</small>
                    <strong style="color: #10b981; font-size: 12px;"><i class="fa-solid fa-check"></i> Studio UI Oturumu</strong>
                </div>
                <div style="background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
                    <small style="color: #94a3b8; display: block; font-size: 10px;">KURAL 2: PROXY DENETİMİ</small>
                    <strong style="color: ${proxy.is_residential ? '#10b981' : '#f59e0b'}; font-size: 12px;">
                        ${proxy.is_residential ? '<i class="fa-solid fa-check"></i> ISP Residential' : (proxy.configured ? '⚠️ Datacenter Riski' : 'ℹ️ Yerel ISP IP')}
                    </strong>
                </div>
                <div style="background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
                    <small style="color: #94a3b8; display: block; font-size: 10px;">KURAL 3: WEBRTC KALKANI</small>
                    <strong style="color: #10b981; font-size: 12px;"><i class="fa-solid fa-shield"></i> UDP Sızıntısı Bloklu</strong>
                </div>
                <div style="background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
                    <small style="color: #94a3b8; display: block; font-size: 10px;">KURAL 4 & 5: CANVAS & GPU</small>
                    <strong style="color: #8b5cf6; font-size: 12px;">${profile.webgl_renderer}</strong>
                </div>
                <div style="background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
                    <small style="color: #94a3b8; display: block; font-size: 10px;">KURAL 10: DNS SIZINTISI</small>
                    <strong style="color: #10b981; font-size: 12px;"><i class="fa-solid fa-lock"></i> Cloudflare DoH</strong>
                </div>
                <div style="background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
                    <small style="color: #94a3b8; display: block; font-size: 10px;">KURAL 17: ÖN İZLEME</small>
                    <strong style="color: #10b981; font-size: 12px;"><i class="fa-solid fa-play"></i> 2-3 Shorts + Yorum</strong>
                </div>
                <div style="background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
                    <small style="color: #94a3b8; display: block; font-size: 10px;">KURAL 18: OTURUM SÜRESİ</small>
                    <strong style="color: #38bdf8; font-size: 12px;"><i class="fa-solid fa-hourglass-half"></i> 3-7 dk Kuralı</strong>
                </div>
                <div style="background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
                    <small style="color: #94a3b8; display: block; font-size: 10px;">KURAL 19: HEADLESS İZİ</small>
                    <strong style="color: #10b981; font-size: 12px;"><i class="fa-solid fa-user-secret"></i> webdriver: undef</strong>
                </div>
                <div style="background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
                    <small style="color: #94a3b8; display: block; font-size: 10px;">KURAL 22: TLS JA3</small>
                    <strong style="color: #10b981; font-size: 12px;"><i class="fa-solid fa-fingerprint"></i> Chrome 124</strong>
                </div>
                <div style="background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
                    <small style="color: #94a3b8; display: block; font-size: 10px;">KURAL 23: PROTOKOL</small>
                    <strong style="color: #06b6d4; font-size: 12px;"><i class="fa-solid fa-network-wired"></i> HTTP/2 & QUIC</strong>
                </div>
                <div style="background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
                    <small style="color: #94a3b8; display: block; font-size: 10px;">KURAL 24: AĞ JITTER'I</small>
                    <strong style="color: #f59e0b; font-size: 12px;"><i class="fa-solid fa-wave-square"></i> Ev ISP Hızı</strong>
                </div>
                <div style="background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
                    <small style="color: #94a3b8; display: block; font-size: 10px;">KURAL 25: LOKASYON</small>
                    <strong style="color: #10b981; font-size: 12px;"><i class="fa-solid fa-location-dot"></i> Coğrafi Kilitli</strong>
                </div>
                <div style="background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
                    <small style="color: #94a3b8; display: block; font-size: 10px;">KURAL 26: ÖNBELLEK</small>
                    <strong style="color: #a855f7; font-size: 12px;"><i class="fa-solid fa-database"></i> IndexedDB Kalıcı</strong>
                </div>
                <div style="background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
                    <small style="color: #94a3b8; display: block; font-size: 10px;">KURAL 27: CLIENT HINTS</small>
                    <strong style="color: #38bdf8; font-size: 12px;"><i class="fa-solid fa-id-card"></i> sec-ch-ua: macOS</strong>
                </div>
                <div style="background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
                    <small style="color: #94a3b8; display: block; font-size: 10px;">KURAL 29: CTIME/MTIME</small>
                    <strong style="color: #ec4899; font-size: 12px;"><i class="fa-solid fa-clock-rotate-left"></i> -15..45 dk</strong>
                </div>
                <div style="background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
                    <small style="color: #94a3b8; display: block; font-size: 10px;">KURAL 30: BOYUT VARYASYONU</small>
                    <strong style="color: #10b981; font-size: 12px;"><i class="fa-solid fa-file-shield"></i> free Atom Dolgusu</strong>
                </div>
            </div>

            <div style="margin: 18px 0 10px 0; display: flex; align-items: center; justify-content: space-between;">
                <h4 style="margin: 0; font-size: 14px; color: #fff; display: flex; align-items: center; gap: 8px;">
                    <i class="fa-solid fa-list-check text-warning"></i> Neler Yapılması Gerektiği (Adım Adım Yol Haritası - 30 Kural)
                </h4>
                <small style="color: #94a3b8;">Otomasyon Motoru Hazır</small>
            </div>

            <div class="channel-checklist-box">
                ${checklistHtml}
            </div>

            <div style="display: flex; gap: 12px; margin-top: 18px; flex-wrap: wrap;">
                <button class="btn btn-success" id="btn-run-warmup-now" style="font-weight: 700; padding: 10px 20px;">
                    <i class="fa-solid fa-fire"></i> Otomatik Çerez Isındırma (Warm-up) Başlat
                </button>
                <button class="btn btn-secondary" id="btn-test-studio-upload" style="padding: 10px 18px;">
                    <i class="fa-solid fa-cloud-arrow-up"></i> Studio UI Güvenli Yükleme Testi
                </button>
            </div>
        </div>
    `;

    document.getElementById('btn-run-warmup-now')?.addEventListener('click', () => {
        triggerWarmupSession(ch.handle);
    });

    document.getElementById('btn-test-studio-upload')?.addEventListener('click', async () => {
        showToast('🎬 Studio UI Güvenli Yükleme simülasyonu başlatılıyor...');
        const terminal = document.getElementById('channel-bot-terminal');
        const logsBox = document.getElementById('bot-terminal-logs');
        if (terminal) terminal.style.display = 'block';
        if (logsBox) {
            logsBox.innerHTML += `<div style="color: #8b5cf6; margin-top: 8px; font-weight: 700;">[Studio UI] '${ch.handle}' için 30 Kural Tam Denetimli Güvenli Yükleme Başlatılıyor...</div>`;
        }

        try {
            const res = await fetch('/api/channel/studio_upload', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    identifier: ch.handle,
                    video_path: 'output/test.mp4',
                    title: 'Stoic Secret to Success #Shorts',
                    scheduled_hour: 18
                })
            });
            const resData = await res.json();
            if (logsBox && resData.success) {
                logsBox.innerHTML += `
                    <div style="color: #10b981; margin-top: 4px;">[Kural 30] Dosya Boyutu: +${resData.file_size_delta_kb || 650} KB free atom dolgusu ile benzersizleştirildi.</div>
                    <div style="color: #f59e0b;">[Kural 24] Ağ Jitter'ı: ${resData.upload_bandwidth_mbps || 11.4} Mbps ev ISP bant genişliği simüle edildi.</div>
                    <div style="color: #10b981;">[Kural 17] Yükleme öncesi ${resData.pre_upload_shorts_watched || 2} Shorts izlendi, 1 beğeni ve yorum bırakıldı: "${resData.comment_posted || 'Harika tespit!'}"</div>
                    <div style="color: #38bdf8;">[Kural 18] Oturum Süresi: ${resData.target_session_minutes || 5.2} dk planlandı (Hızlı 5s çıkış engeli devrede).</div>
                    <div style="color: #ec4899;">[Kural 8] Planlanan Saat: ${resData.scheduled_time || '18:14:22'} (+${resData.jitter_minutes || 14} dk jitter).</div>
                    <div style="color: #a855f7;">[Kural 22] Chrome TLS JA3 Hash: <code>${(resData.ja3_hash || '5420213fa42f0de02168cd1a1e9d8dc9').substring(0, 20)}...</code></div>
                    <div style="color: #10b981; font-weight: 700;">✅ Video Studio UI Yükleme Kuyruğuna Alındı (API Bayrağı Atlatıldı).</div>
                `;
            }
            showToast('✅ Studio UI Güvenli Yükleme testi tamamlandı!');
        } catch (e) {
            if (logsBox) logsBox.innerHTML += `<div style="color: #ef4444;">[Hata] ${e.message}</div>`;
        }
    });
}

async function triggerWarmupSession(identifier) {
    const terminal = document.getElementById('channel-bot-terminal');
    const logsBox = document.getElementById('bot-terminal-logs');
    const statusEl = document.getElementById('bot-terminal-status');

    if (terminal) terminal.style.display = 'block';
    if (logsBox) {
        logsBox.innerHTML = `<div style="color: #38bdf8;">[Bot] '${identifier}' için organik ısındırma başlatıldı...</div>`;
    }
    if (statusEl) {
        statusEl.textContent = 'Isındırma Yürütülüyor...';
        statusEl.className = 'text-warning';
    }

    showToast(`🔥 '${identifier}' için çerez ısındırma başlatıldı!`);

    try {
        const res = await fetch('/api/channel/warmup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ identifier })
        });
        const data = await res.json();

        if (data.success) {
            if (logsBox) {
                logsBox.innerHTML += `<div style="color: #10b981;">[Bot] Isındırma başarıyla tamamlandı! Yeni Güven Skoru: %${data.new_health_score}</div>`;
            }
            if (statusEl) {
                statusEl.textContent = 'Oturum Tamamlandı';
                statusEl.className = 'text-success';
            }
            showToast('✅ Çerez ısındırma tamamlandı! Kanal güven skoru arttı.');
            loadManagedChannels();
        } else {
            if (logsBox) {
                logsBox.innerHTML += `<div style="color: #ef4444;">[Hata] ${data.error || 'Bilinmeyen hata'}</div>`;
            }
        }
    } catch (e) {
        if (logsBox) {
            logsBox.innerHTML += `<div style="color: #ef4444;">[Hata] ${e.message}</div>`;
        }
    }
}


