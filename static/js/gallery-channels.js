/**
 * ShortsAI Studio — Video Gallery, Preview Modal, Quality Gate Badges & Share Decision (gallery-channels.js)
 * Covers Video Gallery, YouTube Publish Hub modal, News RSS Bot, Batch Queue, and Growth Tactics.
 */

let currentRssItems = [];
const FALLBACK_RSS_ITEMS = [
    { title: 'James Webb Teleskobu Evrenin İlk Galaksisinde Açıklanamayan Işık Sinyali Yakaladı', description: 'Bilim insanları derin uzay gözlemlerinde mevcut astrofizik modelleriyle açıklanamayan yüksek enerjili bir ışıma tespit etti.', suggested_niche: '3_space_cosmos', published_at: '12 dk önce' },
    { title: 'Göbeklitepe Yakınlarında Mühürlenmiş Yeni Bir Yeraltı Odası Keşfedildi', description: 'Şanlıurfa Taş Tepeler projesinde arkeologlar 11.500 yıllık dikilitaşlarla çevrili yeni bir ritüel alanı ortaya çıkardı.', suggested_niche: '2_hidden_history', published_at: '28 dk önce' },
    { title: 'Yapay Zeka Modelleri Kendi Aralarında İnsanların Anlamadığı Kısa Kod Dili Geliştirdi', description: 'Çoklu ajan deneylerinde dil modellerinin görevleri %40 daha hızlı çözmek için sembolik bir protokol ürettiği gözlemlendi.', suggested_niche: '4_ai_future_tech', published_at: '41 dk önce' }
];

async function loadRssNews() {
    const list = document.getElementById('rss-news-list');
    const badge = document.getElementById('rss-news-count-badge');
    const sourceSelect = document.getElementById('select-rss-source');
    const source = sourceSelect ? sourceSelect.value : 'aa_guncel';
    if (!list) return;
    if (!list.children.length || list.querySelector('.empty-state-box')) {
        list.innerHTML = '<div class="empty-state-box"><i class="fa-solid fa-spinner fa-spin"></i><p>Haberler taranıyor...</p></div>';
    } else if (badge) {
        badge.textContent = 'Taranıyor...';
    }

    try {
        const res = await fetch(`/api/rss/fetch?source=${source}&limit=10`);
        const data = await res.json();
        const items = (data.items && data.items.length) ? data.items : FALLBACK_RSS_ITEMS;
        currentRssItems = items;
        if (badge) badge.textContent = `${items.length} Haber`;
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
                        <p style="font-size: 11px; color: #94A3B8; margin-top: 4px;">${escapeHtml((item.description || '').slice(0, 140))}...</p>
                    </div>
                    <div style="display: flex; gap: 6px; align-items: center;">
                        <button class="btn btn-primary btn-sm btn-convert-viral-rss" data-title="${encodeURIComponent(item.title)}" data-desc="${encodeURIComponent(item.description || '')}" data-niche="${encodeURIComponent(item.suggested_niche || '1_news_flash')}" title="Başlığı psikolojik merak/şok sorusuna çevirip stüdyoya aktarır">
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

        list.querySelectorAll('.btn-convert-rss').forEach(b => {
            b.addEventListener('click', (e) => {
                const rawTitle = decodeURIComponent(e.currentTarget.getAttribute('data-title'));
                const niche = decodeURIComponent(e.currentTarget.getAttribute('data-niche') || '1_news_flash');
                if (window.inputTopic) window.inputTopic.value = rawTitle;
                if (window.selectNiche) {
                    window.selectNiche.value = niche;
                    if (typeof applyNicheProfile === 'function') applyNicheProfile(niche);
                }
                if (typeof switchTab === 'function') switchTab('studio');
                updateFlowRail('topic');
                showToast('Haber stüdyoya aktarıldı — Senaryoyu incele ile devam edin');
            });
        });

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
                        body: JSON.stringify({ title: rawTitle, description: desc, suggested_niche: niche })
                    });
                    const resData = await res.json();
                    const idea = resData.idea || {};
                    const finalTitle = idea.question_title || rawTitle;
                    const finalNiche = idea.suggested_niche || niche;

                    if (window.inputTopic) window.inputTopic.value = finalTitle;
                    if (window.selectNiche) {
                        window.selectNiche.value = finalNiche;
                        if (typeof applyNicheProfile === 'function') applyNicheProfile(finalNiche);
                    }
                    if (typeof switchTab === 'function') switchTab('studio');
                    updateFlowRail('topic');
                    showToast(`⚡ Viral Kanca Hazır: "${finalTitle}" (${idea.strategy || 'merak'})`);
                } catch (err) {
                    if (window.inputTopic) window.inputTopic.value = rawTitle;
                    if (typeof switchTab === 'function') switchTab('studio');
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
            body: JSON.stringify({ text: topics, niche: defaultNiche, language: 'tr' })
        });
        const data = await res.json();
        if (data.status === 'ok' || data.enqueued != null) {
            const count = data.enqueued ?? data.added_count ?? 0;
            showToast(`✅ ${count} haber toplu üretim kuyruğuna alındı!`);
            if (typeof switchTab === 'function') switchTab('batch');
            refreshBatchQueue();
        } else {
            showToast(data.detail || 'Kuyruğa eklenemedi', 'error');
        }
    } catch (e) {
        showToast(`Hata: ${e.message}`, 'error');
    }
});

document.getElementById('btn-enqueue-batch')?.addEventListener('click', async () => {
    const textEl = document.getElementById('batch-topics-text');
    const text = textEl?.value.trim() || '';
    if (!text) return alert('Lütfen en az bir konu girin!');

    const niche = document.getElementById('batch-default-niche')?.value || '1_news_flash';
    const lang = document.getElementById('batch-default-lang')?.value || 'tr';

    try {
        const res = await fetch('/api/batch/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text, niche, language: lang })
        });
        const data = await res.json();
        showToast(`✅ ${data.enqueued} adet video konusu kuyruğa eklendi!`);
        if (textEl) textEl.value = '';
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

document.getElementById('btn-generate-ab-variants')?.addEventListener('click', async () => {
    const topic = document.getElementById('ab-test-topic')?.value?.trim() || document.getElementById('input-topic')?.value?.trim() || "Bilinmeyen Gerçekler";
    const niche = document.getElementById('select-niche')?.value || '6_stoic_philosophy';
    const container = document.getElementById('ab-results-container');
    if (!container) return;

    try {
        const res = await fetch(`/api/niches/${encodeURIComponent(niche)}/ab_variants?topic=${encodeURIComponent(topic)}`);
        const data = await res.json();
        const variants = data.variants || data.data?.variants || [];
        if (variants.length) {
            const colors = ['#8B5CF6', '#EF4444', '#F59E0B', '#10B981'];
            container.innerHTML = variants.map((v, idx) => `
                <div class="glass-box mb-2" style="padding: 10px; border-left: 3px solid ${colors[idx % colors.length]};">
                    <strong>Varyant ${String.fromCharCode(65 + idx)} (${escapeHtml(v.angle || v.style || v.strategy || v.variant || 'Viral Kanca')}):</strong>
                    <p style="font-size: 11px; color: #FFF; margin-top: 2px;">${escapeHtml(v.title || v.hook || String(v))}</p>
                </div>
            `).join('');
            showToast(`🧪 ${variants.length} gerçek A/B varyantı üretildi!`);
            return;
        }
    } catch (_) {}

    container.innerHTML = `
        <div class="glass-box mb-2" style="padding: 10px; border-left: 3px solid #8B5CF6;">
            <strong>Varyant A (Merak Odaklı - CTR):</strong>
            <p style="font-size: 11px; color: #FFF; margin-top: 2px;">Bunu Biliyor Muydunuz? ${escapeHtml(topic)} Hakkında Gizli Gerçek #Shorts</p>
        </div>
        <div class="glass-box mb-2" style="padding: 10px; border-left: 3px solid #EF4444;">
            <strong>Varyant B (Şok / Flaş Kanca):</strong>
            <p style="font-size: 11px; color: #FFF; margin-top: 2px;">İNANILMAZ! ${escapeHtml(topic)} Olayı Herkesi Şok Etti #Shorts</p>
        </div>
        <div class="glass-box" style="padding: 10px; border-left: 3px solid #F59E0B;">
            <strong>Varyant C (İkilem / Yorum Tuzağı):</strong>
            <p style="font-size: 11px; color: #FFF; margin-top: 2px;">Siz Olsaydınız Ne Yapardınız? ${escapeHtml(topic)} #Shorts</p>
        </div>
    `;
    showToast('🧪 3 A/B varyantı hazırlandı!');
});

document.getElementById('btn-generate-community-poll')?.addEventListener('click', async () => {
    const topic = document.getElementById('community-poll-topic')?.value?.trim() || document.getElementById('input-topic')?.value?.trim() || "Günün Konusu";
    const niche = document.getElementById('select-niche')?.value || '6_stoic_philosophy';
    const container = document.getElementById('community-poll-container');
    if (!container) return;

    try {
        const res = await fetch(`/api/growth/operator-pack?topic=${encodeURIComponent(topic)}&niche=${encodeURIComponent(niche)}`);
        const data = await res.json();
        const pack = data.operator_pack || data;
        const poll = pack.community_poll || {};
        const options = poll.options || [
            `${topic} hakkında hiç bilinmeyen sırlar`,
            `Tarihteki en büyük hatalar`,
            `Gelecekte bizi bekleyenler`,
            `Sonucu görmek istiyorum`
        ];
        container.innerHTML = `
            <div class="glass-box" style="padding: 12px; background: rgba(245, 158, 11, 0.08); border-color: rgba(245, 158, 11, 0.3);">
                <strong style="color: #F59E0B; font-size: 12px;">📊 YouTube Topluluk Anketi &amp; Operatör Paketi</strong>
                <p style="font-size: 12px; margin: 6px 0;">${escapeHtml(poll.question || `Bugünkü Shorts konumuz '${topic}'. Sizce bu konuda en kritik nokta nedir?`)}</p>
                <div style="font-size: 11px; color: #FFF; display: flex; flex-direction: column; gap: 4px;">
                    ${options.map(o => `<div>&bull; ${escapeHtml(String(o))}</div>`).join('')}
                </div>
                ${pack.pinned_comment ? `<div style="margin-top:8px; font-size:11px; color:#38bdf8;">📌 <strong>Sabit Yorum:</strong> ${escapeHtml(pack.pinned_comment)}</div>` : ''}
            </div>
        `;
        showToast('📊 Topluluk anketi ve operatör paketi oluşturuldu!');
    } catch (_) {}
});

document.getElementById('btn-check-copyright-risk')?.addEventListener('click', async () => {
    const text = document.getElementById('copyright-check-text')?.value?.trim() || (window.currentPlan?.scenes?.map(s => s.narration).join(' ')) || '';
    const niche_id = document.getElementById('select-niche')?.value || '';
    const container = document.getElementById('copyright-risk-container');
    if (!container) return;

    try {
        const res = await fetch('/api/compliance/copyright-risk', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text, niche_id })
        });
        const data = await res.json();
        const report = data.report || data;
        const level = report.risk_level || 'low';
        const score = report.risk_score ?? 0;
        const terms = report.matched_terms || [];
        const recs = report.recommendations || [];
        const isHigh = level === 'high' || level === 'medium' || terms.length > 0;
        container.innerHTML = `
            <div style="background: ${isHigh ? 'rgba(239, 68, 68, 0.15)' : 'rgba(16, 185, 129, 0.15)'}; border: 1px solid ${isHigh ? 'var(--danger)' : 'var(--success)'}; padding: 10px; border-radius: 8px; font-size: 12px; color: #FFF;">
                <strong style="color: ${isHigh ? 'var(--danger)' : 'var(--success)'};">
                    <i class="fa-solid ${isHigh ? 'fa-triangle-exclamation' : 'fa-circle-check'}"></i>
                    Telif &amp; Politika Risk Seviyesi: ${escapeHtml(String(level).toUpperCase())} (Skor: ${score}/100)
                </strong>
                ${terms.length ? `<p style="margin-top:4px;">Eşleşen Terimler: <strong>${escapeHtml(terms.join(', '))}</strong></p>` : '<p style="margin-top:4px;">Telif veya marka kısıtlaması tespit edilmedi.</p>'}
                ${recs.length ? `<small style="color:#94A3B8; display:block; margin-top:4px;">Öneri: ${escapeHtml(recs.join(' · '))}</small>` : ''}
            </div>
        `;
    } catch (e) {
        container.innerHTML = `<div class="text-danger">Hata: ${escapeHtml(e.message)}</div>`;
    }
});

let _galleryLoadInFlight = null;

async function loadGallery() {
    const grid = document.getElementById('gallery-videos-grid');
    const badge = document.getElementById('badge-gallery-count');
    if (!grid) return;
    if (_galleryLoadInFlight) return _galleryLoadInFlight;

    _galleryLoadInFlight = (async () => {
    try {
        const res = await fetch('/api/videos');
        const data = await res.json();
        const videos = data.videos || [];

        if (badge) badge.textContent = videos.length;

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
            const thumbUrl = v.thumbnail_url ? escapeHtml(v.thumbnail_url) : '';
            const preloadMode = thumbUrl ? 'none' : 'metadata';
            const posterAttr = thumbUrl ? `poster="${thumbUrl}"` : '';
            const card = document.createElement('div');
            card.className = 'shorts-card glass-box';
            card.style.cssText = "width: 280px !important; max-width: 280px !important; min-width: 260px !important; flex-shrink: 0 !important; box-sizing: border-box !important;";
            card.innerHTML = `
                <div class="shorts-player-wrapper" style="position: relative !important; width: 100% !important; height: 420px !important; max-height: 420px !important; aspect-ratio: 9 / 16 !important; background: #000000 !important; border-radius: 12px !important; overflow: hidden !important; display: flex !important; align-items: center !important; justify-content: center !important;">
                    <span class="shorts-badge-tag"><i class="fa-brands fa-youtube"></i> SHORTS</span>
                    <video src="/output/${v.filename}" controls playsinline preload="${preloadMode}" ${posterAttr} style="width: 100% !important; height: 100% !important; object-fit: contain !important; background: #000000 !important; display: block !important;"></video>
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
                            throw new Error(detail.message || 'Kayitli senaryo kopuk — yeni senaryo uretin');
                        }
                        throw new Error(detail || 'Senaryo bulunamadi');
                    }
                    const data = await res.json();
                    if (kw && window.inputTopic) window.inputTopic.value = kw;
                    if (data.director?.niche_id && window.selectNiche) {
                        window.selectNiche.value = data.director.niche_id;
                        if (typeof applyNicheProfile === 'function') applyNicheProfile(data.director.niche_id);
                    }
                    setCurrentPlan(data.plan);
                    if (typeof switchTab === 'function') switchTab('timeline');
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
                if (typeof submitShareDecision === 'function') submitShareDecision('keep', { videoId, projectSlug });
                openPublishHubModal(v);
            });
        });

        grid.querySelectorAll('.btn-gallery-share-discard').forEach(b => {
            b.addEventListener('click', () => {
                const videoId = b.getAttribute('data-video-id');
                const projectSlug = decodeURIComponent(b.getAttribute('data-project-slug') || '');
                const card = b.closest('.shorts-card');
                if (typeof submitShareDecision === 'function') {
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
                }
            });
        });
    } catch (e) {
        console.error(e);
    } finally {
        _galleryLoadInFlight = null;
    }
    })();
    return _galleryLoadInFlight;
}

window.loadGallery = loadGallery;
document.getElementById('btn-refresh-gallery')?.addEventListener('click', () => window.loadGallery());

window.currentPublishVideo = null;

async function openPublishHubModal(video) {
    window.currentPublishVideo = video;
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

document.getElementById('btn-close-publish-modal')?.addEventListener('click', closePublishHubModal);
document.getElementById('modal-publish-hub')?.addEventListener('click', (e) => {
    if (e.target.id === 'modal-publish-hub') closePublishHubModal();
});
window.loadGallery = loadGallery;

