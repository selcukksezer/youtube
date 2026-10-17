/**
 * ShortsAI Studio — Live SSE Event Handler & Post-Render SEO / Share Advisory (render-sse-handler.js)
 * Manages EventSource stream, real-time progress/log/completion events, SEO title refiner, and share/discard decisions.
 */

function initSSE() {
    if (eventSource) eventSource.close();
    eventSource = new EventSource('/api/events');

    const parseAndDispatch = (eventType, rawData) => {
        try {
            let data = rawData;
            if (typeof rawData === 'string' && (rawData.startsWith('{') || rawData.startsWith('['))) {
                try { data = JSON.parse(rawData); } catch (_) {}
            }
            if (data && typeof data === 'object' && 'type' in data && 'data' in data && !('percent' in data)) {
                handleServerEvent(data.type, data.data);
            } else {
                handleServerEvent(eventType, data);
            }
        } catch (err) {
            handleServerEvent(eventType, rawData);
        }
    };

    eventSource.onmessage = (e) => {
        try {
            const payload = JSON.parse(e.data);
            if (payload && payload.type) {
                handleServerEvent(payload.type, payload.data);
            } else {
                handleServerEvent('message', payload);
            }
        } catch (err) {
            handleServerEvent('log', e.data);
        }
    };

    ['progress', 'log', 'complete', 'error', 'plan_updated'].forEach((evt) => {
        eventSource.addEventListener(evt, (e) => {
            parseAndDispatch(evt, e.data);
        });
    });

    eventSource.onerror = () => {
        console.warn("SSE bağlantısı yeniden kuruluyor...");
    };
}

function handleServerEvent(type, data) {
    if (type === 'progress') {
        const pct = data?.percent || 0;
        if (dockProgressFill) dockProgressFill.style.width = `${pct}%`;
        if (dockProgressPct) dockProgressPct.textContent = `%${pct}`;
        if (dockStepTitle) dockStepTitle.textContent = data?.step || "İşleniyor...";
        updateTerminalTriggers(true, pct);
    } else if (type === 'log') {
        if (dockLogSnippet) dockLogSnippet.textContent = data;
        if (terminalBody) {
            terminalBody.textContent += `[${new Date().toLocaleTimeString()}] ${data}\n`;
            terminalBody.scrollTop = terminalBody.scrollHeight;
        }
    } else if (type === 'plan_updated') {
        if (data && data.plan) {
            console.log('🎬 SSE plan_updated alındı, kurgu senkronize ediliyor...', data);
            if (typeof setCurrentPlan === 'function') setCurrentPlan(data.plan);
            if (typeof showToast === 'function') showToast('🎬 Senaryo ve gerçek video klipleri kurgu editörüne bağlandı!');
        }
    } else if (type === 'complete') {
        if (dockProgressFill) dockProgressFill.style.width = `100%`;
        if (dockProgressPct) dockProgressPct.textContent = `%100`;
        if (dockStepTitle) dockStepTitle.textContent = "Video hazir";
        if (dockSpinner) dockSpinner.style.display = 'none';
        isRendering = false;
        setCancelButtonState('close');
        updateTerminalTriggers(false, 100);

        if (data?.plan && typeof setCurrentPlan === 'function') {
            setCurrentPlan(data.plan);
        } else if (typeof loadLatestRenderedProjectToTimeline === 'function') {
            loadLatestRenderedProjectToTimeline(true);
        }

        switchTab('studio');
        updateFlowRail('seo');

        if (data?.url && livePlayer) {
            livePlayer.src = data.url + (data.url.includes('?') ? '&' : '?') + 't=' + Date.now();
            livePlayer.classList.remove('hidden');
            mockupPlaceholder?.classList.add('hidden');
        }

        const seoBox = document.getElementById('video-complete-seo-box');
        if (seoBox) {
            const titleInp = document.getElementById('seo-title-val');
            const tagsInp = document.getElementById('seo-tags-val');
            const commentInp = document.getElementById('seo-comment-val');
            const proofLink = document.getElementById('link-download-proof');

            if (data?.seo) {
                if (titleInp) titleInp.value = data.seo.seo_title || data.keyword || '';
                if (tagsInp) tagsInp.value = (data.seo.tags || []).join(', ');
                if (commentInp) commentInp.value = data.seo.pinned_comment || '';
                renderSeoTitleIdeas(data.seo.title_ideas, titleInp);
            }
            if (proofLink && data?.proof_url) proofLink.href = data.proof_url;

            const sharePanel = document.getElementById('video-share-decision-panel');
            if (sharePanel && data?.video_id) {
                sharePanel.dataset.videoId = String(data.video_id);
                sharePanel.dataset.projectSlug = data.project_slug || '';
                sharePanel.dataset.filename = data.filename || '';
                sharePanel.classList.remove('hidden');
                sharePanel.classList.remove('is-resolved');
                const hint = document.getElementById('video-share-decision-hint');
                if (hint) {
                    hint.textContent = 'Paylaş → proof + SEO saklanır. Sil → video, kanıt ve geçici dosyalar diskten kaldırılır.';
                }
            }

            let qgEl = document.getElementById('studio-qg-strip');
            if (!qgEl) {
                qgEl = document.createElement('div');
                qgEl.id = 'studio-qg-strip';
                qgEl.className = 'studio-qg-strip';
                seoBox.insertBefore(qgEl, seoBox.firstChild);
            }
            qgEl.innerHTML = renderQualityGateCard(data?.quality_gate || {});
            const post = (data?.quality_gate || {}).post || data?.quality_gate || {};
            qgEl.classList.toggle('is-fail', post.ok === false);

            seoBox.classList.remove('hidden');
            try { seoBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); } catch (_) {}
            refreshFeedDistributionAdvisory(25);
        }

        const durMsg = data?.director?.duration
            ? ` ${Number(data.director.duration).toFixed(1)}sn`
            : '';
        showToast(`Video hazir${durMsg} — SEO paketini kopyalayin`);
        loadGallery();
    } else if (type === 'error') {
        if (dockStepTitle) dockStepTitle.textContent = "Hata Oluştu";
        if (dockLogSnippet) dockLogSnippet.textContent = data;
        if (dockProgressFill) dockProgressFill.style.backgroundColor = "#EF4444";
        if (dockSpinner) dockSpinner.style.display = 'none';
        showToast(`❌ Hata: ${data}`);
        isRendering = false;
        setCancelButtonState('close');
        updateTerminalTriggers(false, 0);

        const isSimErr = String(data).toLowerCase().includes('benzer') || String(data).toLowerCase().includes('intihal');
        if (isSimErr) {
            const btnForce = document.getElementById('btn-force-similar-script');
            if (btnForce) btnForce.classList.remove('hidden');
            if (terminalBody) {
                terminalBody.textContent += `\n[İpucu] Bu senaryoyu zorla render etmek için 'Yine De Devam Et' anahtarını açın veya 'Yine De Devam Et' butonuna tıklayın.\n`;
            }
        }
    }
}

function renderSeoTitleIdeas(packageData, titleInput) {
    const container = document.getElementById('seo-title-ideas');
    if (!container) return;
    container.replaceChildren();

    const titles = Array.isArray(packageData?.titles) ? packageData.titles : [];
    if (!titles.length) {
        container.classList.add('hidden');
        return;
    }

    let activeTitle = titleInput?.value?.trim() || String(titles[0] || '');
    const thumbnails = Array.isArray(packageData.thumbnail_texts)
        ? packageData.thumbnail_texts
        : [];
    const recommended = new Map(
        (Array.isArray(packageData.recommended) ? packageData.recommended : [])
            .filter((item) => Number.isInteger(item?.index))
            .map((item) => [item.index, String(item.reason || '')])
    );

    titles.forEach((rawTitle, index) => {
        if (typeof rawTitle !== 'string' || !rawTitle.trim()) return;
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'seo-title-idea';
        const main = document.createElement('span');
        main.className = 'seo-title-idea-main';
        const title = document.createElement('strong');
        title.textContent = rawTitle;
        main.appendChild(title);

        const thumbnail = String(thumbnails[index] || '').trim();
        if (thumbnail) {
            const thumbnailLabel = document.createElement('small');
            thumbnailLabel.textContent = `Kapak yazısı: ${thumbnail}`;
            main.appendChild(thumbnailLabel);
        }
        button.appendChild(main);

        if (recommended.has(index)) {
            const badge = document.createElement('span');
            badge.className = 'seo-title-idea-badge';
            badge.textContent = 'ÖNERİLEN';
            button.appendChild(badge);
            button.title = recommended.get(index);
        }

        button.addEventListener('click', () => {
            activeTitle = rawTitle;
            if (titleInput) titleInput.value = rawTitle;
            showToast('Başlık seçildi. Kopyalamak için başlık yanındaki kopyala düğmesini kullanın.');
        });
        container.appendChild(button);
    });

    const refiner = document.createElement('section');
    refiner.className = 'seo-title-refiner';
    const heading = document.createElement('strong');
    heading.textContent = 'Geri bildirimle iyileştir';
    refiner.appendChild(heading);

    const history = document.createElement('div');
    history.className = 'seo-title-refinement-history';
    history.setAttribute('aria-live', 'polite');
    refiner.appendChild(history);

    const feedback = document.createElement('textarea');
    feedback.className = 'input-styled';
    feedback.rows = 2;
    feedback.maxLength = 400;
    feedback.placeholder = 'Örn. Daha sade ve merak uyandırıcı olsun.';
    feedback.setAttribute('aria-label', 'Başlık iyileştirme geri bildirimi');
    refiner.appendChild(feedback);

    const submit = document.createElement('button');
    submit.type = 'button';
    submit.className = 'btn btn-sm btn-secondary';
    submit.textContent = 'Başlığı iyileştir';
    refiner.appendChild(submit);

    const status = document.createElement('small');
    status.className = 'seo-title-refinement-status';
    status.setAttribute('role', 'status');
    refiner.appendChild(status);

    const appendMessage = (label, text) => {
        const message = document.createElement('p');
        const messageLabel = document.createElement('strong');
        messageLabel.textContent = `${label}: `;
        message.appendChild(messageLabel);
        message.appendChild(document.createTextNode(text));
        history.appendChild(message);
    };

    submit.addEventListener('click', async () => {
        const creatorFeedback = feedback.value.trim();
        if (!activeTitle) {
            status.textContent = 'Önce bir başlık seçin.';
            return;
        }
        if (!creatorFeedback) {
            status.textContent = 'Başlığı nasıl değiştirmek istediğinizi yazın.';
            feedback.focus();
            return;
        }

        submit.disabled = true;
        status.textContent = 'Başlık iyileştiriliyor...';
        try {
            const response = await fetch('/api/video/title-ideas/refine', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    current_title: activeTitle,
                    feedback: creatorFeedback,
                    summary: String(packageData.summary || ''),
                    language: String(packageData.language || 'tr')
                })
            });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(typeof data.detail === 'string' ? data.detail : 'Başlık iyileştirilemedi.');
            }
            const refinement = data.refinement;
            if (data.status !== 'ok' || typeof refinement?.title !== 'string' || !refinement.title.trim()) {
                throw new Error('Sunucu geçerli bir başlık döndürmedi.');
            }

            activeTitle = refinement.title;
            if (titleInput) titleInput.value = activeTitle;
            appendMessage('Siz', creatorFeedback);
            appendMessage('Yeni başlık', `${activeTitle}${refinement.reason ? ` — ${refinement.reason}` : ''}`);
            feedback.value = '';
            status.textContent = 'Başlık güncellendi. İsterseniz yeni bir geri bildirimle devam edin.';
        } catch (error) {
            const detail = error instanceof Error ? error.message : 'Bilinmeyen ağ hatası.';
            status.textContent = `Başlık iyileştirilemedi: ${detail}`;
        } finally {
            submit.disabled = false;
        }
    });
    container.appendChild(refiner);
    container.classList.toggle('hidden', container.childElementCount === 0);
}

// 500-Madde SEO & İtiraz Kopyalama Butonları
document.getElementById('btn-copy-seo-title')?.addEventListener('click', () => {
    const val = document.getElementById('seo-title-val')?.value;
    if (val) {
        navigator.clipboard.writeText(val);
        showToast('📋 CTR Başlığı panoya kopyalandı!');
    }
});

document.getElementById('btn-copy-seo-tags')?.addEventListener('click', () => {
    const val = document.getElementById('seo-tags-val')?.value;
    if (val) {
        navigator.clipboard.writeText(val);
        showToast('🏷️ 15 Viral Etiket panoya kopyalandı!');
    }
});

document.getElementById('btn-copy-seo-comment')?.addEventListener('click', () => {
    const val = document.getElementById('seo-comment-val')?.value;
    if (val) {
        navigator.clipboard.writeText(val);
        showToast('💬 Sabitlenecek Yorum panoya kopyalandı!');
    }
});

async function refreshFeedDistributionAdvisory(swipeRatePct) {
    const textEl = document.getElementById('feed-distribution-text');
    const labelEl = document.getElementById('feed-swipe-rate-label');
    if (labelEl) labelEl.textContent = `${Math.round(swipeRatePct)}%`;
    if (!textEl) return;
    try {
        const res = await fetch(`/api/analytics/feed-distribution?swipe_rate_pct=${encodeURIComponent(swipeRatePct)}`);
        const data = await res.json();
        const adv = data.advisory || {};
        const phase = adv.phase === 'expanded' ? '✅ Geniş dağıtım' : '⚠️ Feed durdu';
        textEl.textContent = `${phase} — ${adv.message || 'Analytics stub yüklenemedi.'}`;
    } catch (_) {
        textEl.textContent = 'Feed ivmesi stub — Studio Analytics ile karşılaştırın (Item 387).';
    }
}

document.getElementById('feed-swipe-rate-slider')?.addEventListener('input', (e) => {
    const val = Number(e.target.value || 35);
    refreshFeedDistributionAdvisory(val);
});

document.getElementById('btn-show-appeal-script')?.addEventListener('click', async () => {
    try {
        const res = await fetch('/api/proof/appeal_script?channel_name=ShortsPro');
        const d = await res.json();
        if (d.status === 'ok') {
            alert("🎬 YouTube 5-Dakikalık İtiraz Videosu Taslağı (Item 472):\n\n" + d.script);
        }
    } catch (e) {
        alert('İtiraz metni alınamadı: ' + e.message);
    }
});

async function submitShareDecision(decision, opts = {}) {
    const panel = document.getElementById('video-share-decision-panel');
    const fromGallery = Boolean(opts.videoId);
    const videoId = opts.videoId || panel?.dataset?.videoId;
    if (!videoId) {
        showToast('Video kimliği bulunamadı — render tamamlandı mı?');
        return;
    }
    if (decision === 'discard') {
        const ok = confirm(
            'Bu video paylaşıma uygun değilse tüm dosyalar silinecek:\n\n' +
            '• MP4 video\n• Proof kanıt dosyası\n• SEO paketi\n• Sahne/asset klasörü\n• Ses geçici dosyaları\n\n' +
            'Devam edilsin mi?'
        );
        if (!ok) return;
    }
    const projectSlug = opts.projectSlug ?? panel?.dataset?.projectSlug ?? undefined;
    try {
        const res = await fetch(`/api/videos/${videoId}/share-decision`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                decision,
                project_slug: projectSlug || undefined,
            }),
        });
        const d = await res.json();
        if (!res.ok) throw new Error(d.detail || d.message || res.statusText);
        if (panel && !fromGallery) panel.classList.add('is-resolved');
        const hint = document.getElementById('video-share-decision-hint');
        if (decision === 'keep') {
            showToast('Proof saklandı — YouTube Studio\'da manuel yükleyin');
            if (!fromGallery && hint) {
                hint.textContent = '✓ Proof ve SEO paketi saklandı. YouTube\'a manuel yükleyebilirsiniz.';
            }
            if (d.youtube_upload_url) window.open(d.youtube_upload_url, '_blank', 'noopener');
        } else {
            showToast('Video ve ilişkili dosyalar silindi');
            if (!fromGallery && hint) hint.textContent = '✓ Dosyalar diskten kaldırıldı.';
            if (typeof opts.onDiscard === 'function') {
                opts.onDiscard();
            } else {
                livePlayer?.classList?.add('hidden');
                mockupPlaceholder?.classList?.remove('hidden');
                if (livePlayer) livePlayer.removeAttribute('src');
                loadGallery();
            }
        }
    } catch (e) {
        showToast('Paylaşım kararı kaydedilemedi: ' + e.message);
    }
}

document.getElementById('btn-youtube-share-keep')?.addEventListener('click', () => submitShareDecision('keep'));
document.getElementById('btn-youtube-share-discard')?.addEventListener('click', () => submitShareDecision('discard'));
