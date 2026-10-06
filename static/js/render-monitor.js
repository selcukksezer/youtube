/**
 * ShortsAI Studio — Live SSE Stream & Render Pipeline (render-monitor.js)
 * Manages video rendering initiation, real-time SSE progress, persistent dock monitor, cancel render and terminal log drawer.
 */


async function restoreRenderState() {
    try {
        const res = await fetch('/api/status');
        if (!res.ok) return;
        const state = await res.json();
        if (!state.is_rendering) {
            updateTerminalTriggers(false, 0);
            return;
        }

        isRendering = true;
        persistentMonitor.classList.remove('hidden');
        terminalPanel.classList.remove('hidden'); // Sayfa yenilendiğinde de terminal açık kalsın

        const percent = Number(state.percent || 0);
        dockProgressFill.style.width = `${percent}%`;
        dockProgressPct.textContent = `%${percent}`;
        dockStepTitle.textContent = state.step || 'İşlem yürütülüyor...';

        updateTerminalTriggers(true, percent);

        const logs = state.logs || [];
        if (logs.length) {
            dockLogSnippet.textContent = logs[logs.length - 1];
            terminalBody.textContent = logs.map(log => log.startsWith('[') ? log : `[Sistem] ${log}`).join('\n') + '\n';
            terminalBody.scrollTop = terminalBody.scrollHeight;
        }
        initSSE();
    } catch (error) {
        console.error('Render durumu geri yüklenemedi:', error);
    }
}

function updateTerminalTriggers(active, pct = 0) {
    const headerBadge = document.getElementById('header-render-badge');
    const floatingTrigger = document.getElementById('floating-terminal-trigger');
    const floatingPct = document.getElementById('floating-render-pct');

    if (headerBadge) {
        if (active) {
            headerBadge.style.display = 'inline-block';
            headerBadge.textContent = `%${pct}`;
            headerBadge.style.background = pct >= 80 ? '#10b981' : '#38bdf8';
        } else {
            headerBadge.style.display = 'none';
        }
    }

    if (floatingTrigger && floatingPct) {
        // Eğer render aktifse ve dock kapalıysa yüzen butonu göster
        const isDockHidden = persistentMonitor?.classList.contains('hidden');
        if (active && isDockHidden) {
            floatingTrigger.style.display = 'block';
            floatingPct.textContent = `%${pct}`;
        } else if (!active) {
            floatingTrigger.style.display = 'none';
        }
    }
}

function showTerminalAndDock() {
    if (persistentMonitor) persistentMonitor.classList.remove('hidden');
    if (terminalPanel) terminalPanel.classList.remove('hidden');
    const floatingTrigger = document.getElementById('floating-terminal-trigger');
    if (floatingTrigger) floatingTrigger.style.display = 'none';
    if (terminalBody) terminalBody.scrollTop = terminalBody.scrollHeight;
}



// 10. CANLI SSE İZLEME & RENDER BORU HATTI
// ══════════════════════════════════════════════════════════════
(btnQuickRender || document.getElementById('btn-quick-render'))?.addEventListener('click', () => {
    if (currentPlan?.scenes?.length) {
        collectTimelineEdits();
        persistCurrentPlan();
        startRenderProcess(currentPlan);
    } else {
        // No plan yet — quality path: offer script-first
        const goScript = confirm(
            'Henuz senaryo yok.\n\nOK = once senaryo olustur (kalite yolu)\nIptal = dogrudan render (AI yeniden yazar)'
        );
        if (goScript) {
            btnCreateScript?.click();
            return;
        }
        startRenderProcess(null);
    }
});

async function startRenderProcess(planToUse) {
    if (isRendering) return alert('Su anda aktif bir render islemi devam ediyor!');

    const topic = inputTopic.value.trim();
    if (!topic) return alert('Lutfen bir video konusu girin!');

    // Prefer live edited plan
    let plan = planToUse;
    if (plan?.scenes?.length) {
        collectTimelineEdits();
        plan = currentPlan || plan;
    }

    const scenes = plan?.scenes || [];
    const scriptQuality = plan?.meta?.script_quality || {};
    if (scriptQuality.hard_fail === true) {
        const issues = scriptQuality.issues || [];
        const reason = issues[0] || 'Script kalite kapisi hard-fail';
        alert(
            'Render ENGELLENDI — senaryo kalite kapisi:\n\n• '
            + (issues.length ? issues.join('\n• ') : reason)
        );
        switchTab('timeline');
        updateRenderButtonsBlocked(true, reason);
        showToast('Senaryo kalite hatasi — render kapali', 'warn');
        return;
    }

    if (scenes.length && !timelineReviewed && !qualityPanelGreen) {
        const proceedReview = confirm(
            'Plan henuz timeline\'da incelenmedi ve kalite paneli yesil degil.\n\n' +
            'Yine de render alinsin mi?\n(Iptal = timeline\'a git)'
        );
        if (!proceedReview) {
            switchTab('timeline');
            showToast('Once timeline\'i inceleyin veya kalite panelini yesil yapin', 'warn');
            return;
        }
    }

    if (scenes.length) {
        updateComplianceDashboard(scenes);
        let { hard, soft } = getComplianceIssues(scenes);
        if (hard.length) {
            const validation = await validatePlanViaApi(plan, { autoRepair: true });
            if (validation.plan) {
                plan = validation.plan;
                setCurrentPlan(plan);
                collectTimelineEdits();
            }
            if (validation.repaired && validation.fixes?.length) {
                showToast('Anlatim otomatik duzeltildi');
            }
            if (validation.ok) {
                hard = [];
            } else {
                ({ hard, soft } = getComplianceIssues(plan?.scenes || scenes));
            }
        }
        if (hard.length) {
            alert(
                'Render ENGELLENDI — kopuk anlatim (Madde 494):\n\n• '
                + hard.join('\n• ')
                + '\n\nTimeline\'dan cumleleri duzeltin veya yeni senaryo uretin.'
            );
            switchTab('timeline');
            updateRenderButtonsBlocked(true, hard[0]);
            showToast('Kopuk anlatim — render kapali', 'warn');
            return;
        }
        if (soft.length) {
            const proceed = confirm(
                'Kalite uyarisi (Madde 88/494):\n\n• ' + soft.join('\n• ') +
                '\n\nYine de render alinsin mi?\n(Zaman cizelgesinde Cadence/Sure duzeltmesi onerilir)'
            );
            if (!proceed) {
                switchTab('timeline');
                showToast('Once timeline kalitesini duzeltin', 'warn');
                return;
            }
        }
    }



    initSSE();
    updateFlowRail('render');

    persistentMonitor.classList.remove('hidden');
    dockStepTitle.textContent = "Islem Baslatiliyor...";
    dockLogSnippet.textContent = topic;
    dockProgressFill.style.width = "5%";
    dockProgressFill.style.backgroundColor = "";
    dockProgressPct.textContent = "%5";
    if (dockSpinner) dockSpinner.style.display = 'inline-block';
    setCancelButtonState('cancel');
    const planNote = plan?.scenes?.length
        ? `plan=${plan.scenes.length} sahne`
        : 'plan=yeniden uretilecek';
    terminalBody.textContent = `[${new Date().toLocaleTimeString()}] Render: ${topic} (${planNote})\n`;

    const payload = {
        keyword: topic,
        plan: plan,
        niche: selectNiche.value,
        language: document.getElementById('btn-quick-lang-en')?.classList.contains('active') ? 'en' : (selectLanguage?.value || 'tr'),
        voice_gender: (selectTtsVoice?.value === 'auto' ? 'auto' : (findVoiceMeta(selectTtsVoice?.value)?.gender || 'male')),
        tts_voice: (selectTtsVoice?.value && selectTtsVoice.value !== 'auto') ? selectTtsVoice.value : null,
        gameplay_category: selectGameplayCategory?.value || 'auto',
        subtitle_preset: selectSubPreset.value,
        subtitle_font_size: parseInt(subRangeSize?.value || '54', 10),
        subtitle_y_position: parseFloat(subRangeY?.value || '0.8'),
        bgm_track: document.getElementById('studio-bgm-track')?.value
            || document.getElementById('select-bgm-track')?.value
            || '',
        bgm_volume: parseFloat(
            document.getElementById('studio-ducking-vol')?.value
            || document.getElementById('range-ducking-vol')?.value
            || '0.12'
        ),
        reddit_post: selectedRedditPost,
        split_screen: chkSplitScreen ? !!chkSplitScreen.checked : false,
        gameplay_category: document.getElementById('select-gameplay-category')?.value || 'auto',
        enable_reddit_card: !!(document.getElementById('chk-reddit-card')?.checked),
        anti_duplicate: chkAntiDuplicate ? !!chkAntiDuplicate.checked : true,
        enable_ken_burns: !!(chkKenBurns && chkKenBurns.checked),
        enable_zoompan: !!(chkZoompan && chkZoompan.checked),
        resolution: document.getElementById('select-render-resolution')?.value || '1080p',
        visual_mode: (() => {
            const dropdownVal = document.getElementById('select-visual-engine')?.value;
            if (dropdownVal && dropdownVal !== 'auto') {
                if (plan && typeof plan === 'object' && dropdownVal !== 'mixed' && Array.isArray(plan.scenes)) {
                    plan.visual_mode = dropdownVal;
                    plan.scenes.forEach((scene) => {
                        if (scene && typeof scene === 'object') scene.visual_mode = dropdownVal;
                    });
                } else if (plan && typeof plan === 'object') {
                    plan.visual_mode = dropdownVal;
                }
                return dropdownVal;
            }
            return (plan?.visual_mode && plan.visual_mode !== 'auto') ? plan.visual_mode : (currentPlan?.visual_mode && currentPlan.visual_mode !== 'auto') ? currentPlan.visual_mode : (dropdownVal || 'auto');
        })(),
        auto_publish: !!(chkAutoPublish && chkAutoPublish.checked),
        allow_similar_script: !!(document.getElementById('chk-allow-similar-script')?.checked),
        force_render: !!(document.getElementById('chk-allow-similar-script')?.checked),
        resume: !!(document.getElementById('chk-resume-render')?.checked),
        whisper_align: !!(document.getElementById('chk-whisper-align')?.checked),
        enable_intro_whoosh: !!(document.getElementById('chk-intro-whoosh')?.checked),
        duck_attack_ms: parseInt(document.getElementById('range-duck-attack')?.value || '80', 10),
        duck_release_ms: parseInt(document.getElementById('range-duck-release')?.value || '200', 10),
        intro_blast: parseFloat(document.getElementById('range-bgm-blast')?.value || '0.85'),
        outro_swell_sec: parseFloat(document.getElementById('range-outro-swell-sec')?.value || '5'),
        enable_outro_swell: document.getElementById('audio-chk-outro-swell')
            ? !!document.getElementById('audio-chk-outro-swell').checked
            : true,
        enable_bgm: document.getElementById('chk-enable-bgm')
            ? !!document.getElementById('chk-enable-bgm').checked
            : true,
        enable_outro: document.getElementById('chk-enable-outro')
            ? !!document.getElementById('chk-enable-outro').checked
            : true,
        enable_hook_card: document.getElementById('chk-hook-card')?.checked ?? true,
        enable_broll_insert: !!(document.getElementById('chk-broll-insert')?.checked),
        enable_face_center: !!(document.getElementById('chk-center-face')?.checked),
        enable_emphasis_card: !!(document.getElementById('chk-emphasis-card')?.checked || document.getElementById('chk-emphasis-card-lab')?.checked),
        enable_audio_visualizer: !!(document.getElementById('chk-audio-visualizer')?.checked),
        enable_news_ticker: !!(document.getElementById('chk-news-ticker')?.checked)
    };
    if (plan && !plan.visual_mode) {
        plan.visual_mode = payload.visual_mode;
    }

    fetch('/api/video/render', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    }).then(res => {
        if (!res.ok) {
            return res.json().then(d => { throw new Error(d.detail || 'Render baslatilamadi'); });
        }
        showToast(plan?.scenes?.length
            ? 'Render basladi — timeline senaryosu kullaniliyor'
            : 'Render basladi — AI senaryo uretecek');
        isRendering = true;
        setCancelButtonState('cancel');
        persistCurrentPlan();
    }).catch(err => {
        const msg = err.message || '';
        const isSimErr = msg.toLowerCase().includes('benzer') || msg.toLowerCase().includes('intihal') || msg.toLowerCase().includes('originality');
        if (isSimErr) {
            const retry = confirm(msg + "\n\nİçerik/görseller farklı olduğu için 'Yine De Devam Et' seçeneğiyle render başlatılsın mı?");
            if (retry) {
                const chk = document.getElementById('chk-allow-similar-script');
                if (chk) chk.checked = true;
                persistentMonitor.classList.add('hidden');
                isRendering = false;
                setCancelButtonState('cancel');
                setTimeout(() => launchVideoRender(), 200);
                return;
            }
        } else {
            alert(msg);
        }
        persistentMonitor.classList.add('hidden');
        isRendering = false;
        setCancelButtonState('cancel');
    });
}

function setCancelButtonState(mode) {
    if (!btnCancelRender) return;
    if (mode === 'cancelling') {
        btnCancelRender.disabled = true;
        btnCancelRender.className = 'btn btn-sm btn-danger';
        btnCancelRender.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> İptal Ediliyor...';
    } else if (mode === 'close') {
        btnCancelRender.disabled = false;
        btnCancelRender.className = 'btn btn-sm btn-secondary';
        btnCancelRender.innerHTML = '<i class="fa-solid fa-xmark"></i> Kapat';
    } else {
        btnCancelRender.disabled = false;
        btnCancelRender.className = 'btn btn-sm btn-danger';
        btnCancelRender.innerHTML = '<i class="fa-solid fa-circle-xmark"></i> İptal Et';
    }
}

function initSSE() {
    if (eventSource) eventSource.close();
    eventSource = new EventSource('/api/events');

    const parseAndDispatch = (eventType, rawData) => {
        try {
            let data = rawData;
            if (typeof rawData === 'string' && (rawData.startsWith('{') || rawData.startsWith('['))) {
                try { data = JSON.parse(rawData); } catch (_) {}
            }
            // If data is wrapped as {type, data}, dispatch the inner type
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

    // Canonical Section 10.1 SSE event listeners
    ['progress', 'log', 'complete', 'error'].forEach((evt) => {
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
        const pct = data.percent || 0;
        dockProgressFill.style.width = `${pct}%`;
        dockProgressPct.textContent = `%${pct}`;
        dockStepTitle.textContent = data.step || "İşleniyor...";
        updateTerminalTriggers(true, pct);
    } else if (type === 'log') {
        dockLogSnippet.textContent = data;
        terminalBody.textContent += `[${new Date().toLocaleTimeString()}] ${data}\n`;
        terminalBody.scrollTop = terminalBody.scrollHeight;
    } else if (type === 'complete') {
        dockProgressFill.style.width = `100%`;
        dockProgressPct.textContent = `%100`;
        dockStepTitle.textContent = "Video hazir";
        if (dockSpinner) dockSpinner.style.display = 'none';
        isRendering = false;
        setCancelButtonState('close');
        updateTerminalTriggers(false, 100);

        // Always land on Studio so preview + SEO are visible
        switchTab('studio');
        updateFlowRail('seo');

        if (data.url) {
            livePlayer.src = data.url + (data.url.includes('?') ? '&' : '?') + 't=' + Date.now();
            livePlayer.classList.remove('hidden');
            mockupPlaceholder.classList.add('hidden');
        }

        const seoBox = document.getElementById('video-complete-seo-box');
        if (seoBox) {
            const titleInp = document.getElementById('seo-title-val');
            const tagsInp = document.getElementById('seo-tags-val');
            const commentInp = document.getElementById('seo-comment-val');
            const proofLink = document.getElementById('link-download-proof');

            if (data.seo) {
                if (titleInp) titleInp.value = data.seo.seo_title || data.keyword || '';
                if (tagsInp) tagsInp.value = (data.seo.tags || []).join(', ');
                if (commentInp) commentInp.value = data.seo.pinned_comment || '';
            }
            if (proofLink && data.proof_url) proofLink.href = data.proof_url;

            const sharePanel = document.getElementById('video-share-decision-panel');
            if (sharePanel && data.video_id) {
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

            // Quality gate strip
            let qgEl = document.getElementById('studio-qg-strip');
            if (!qgEl) {
                qgEl = document.createElement('div');
                qgEl.id = 'studio-qg-strip';
                qgEl.className = 'studio-qg-strip';
                seoBox.insertBefore(qgEl, seoBox.firstChild);
            }
            qgEl.innerHTML = renderQualityGateCard(data.quality_gate || {});
            const post = (data.quality_gate || {}).post || data.quality_gate || {};
            qgEl.classList.toggle('is-fail', post.ok === false);

            seoBox.classList.remove('hidden');
            try { seoBox.scrollIntoView({ behavior: 'smooth', block: 'nearest' }); } catch (_) {}
            refreshFeedDistributionAdvisory(25);
        }

        const durMsg = data.director?.duration
            ? ` ${Number(data.director.duration).toFixed(1)}sn`
            : '';
        showToast(`Video hazir${durMsg} — SEO paketini kopyalayin`);
        loadGallery();
    } else if (type === 'error') {
        dockStepTitle.textContent = "Hata Oluştu";
        dockLogSnippet.textContent = data;
        dockProgressFill.style.backgroundColor = "#EF4444";
        if (dockSpinner) dockSpinner.style.display = 'none';
        showToast(`❌ Hata: ${data}`);
        isRendering = false;
        setCancelButtonState('close');
        updateTerminalTriggers(false, 0);

        const isSimErr = String(data).toLowerCase().includes('benzer') || String(data).toLowerCase().includes('intihal');
        if (isSimErr) {
            const btnForce = document.getElementById('btn-force-similar-script');
            if (btnForce) btnForce.classList.remove('hidden');
            terminalBody.textContent += `\n[İpucu] Bu senaryoyu zorla render etmek için 'Yine De Devam Et' anahtarını açın veya 'Yine De Devam Et' butonuna tıklayın.\n`;
        }
    }
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

btnToggleLog?.addEventListener('click', () => {
    terminalPanel.classList.toggle('hidden');
});

btnCloseLog?.addEventListener('click', () => {
    terminalPanel.classList.add('hidden');
});

function dismissMonitorDock() {
    persistentMonitor.classList.add('hidden');
    terminalPanel.classList.add('hidden');
    if (isRendering) {
        // Render sürüyorsa sağ alttaki yüzen tetikleyiciyi aktif et
        const curPct = parseInt(dockProgressPct?.textContent?.replace('%', '')) || 0;
        updateTerminalTriggers(true, curPct);
    } else {
        setCancelButtonState('cancel');
        updateTerminalTriggers(false, 0);
    }
}

btnCloseDock?.addEventListener('click', dismissMonitorDock);
document.getElementById('header-btn-open-terminal')?.addEventListener('click', showTerminalAndDock);
document.getElementById('btn-floating-open-terminal')?.addEventListener('click', showTerminalAndDock);

btnCancelRender?.addEventListener('click', async () => {
    // Durum 1: Render şu anda aktif değilse (hata oluşmuş, tamamlanmış vb.) -> paneli doğrudan kapat
    if (!isRendering) {
        dismissMonitorDock();
        return;
    }

    // Durum 2: Aktif video render işlemi çalışıyorsa kullanıcıdan onay al
    if (confirm('Aktif video üretimini iptal etmek istiyor musunuz?')) {
        setCancelButtonState('cancelling');
        try {
            const response = await fetch('/api/video/cancel', { method: 'POST' });
            const data = await response.json();
            showToast(`⛔ ${data.message}`);

            // Eğer aktif render yoksa veya iptal hemen tamamlandıysa
            if (data.active === false || (data.message && data.message.includes('bulunmuyor'))) {
                isRendering = false;
                setTimeout(() => {
                    dismissMonitorDock();
                }, 500);
            }
        } catch (error) {
            showToast('İptal isteği gönderilemedi.');
            setCancelButtonState('cancel');
        }
    }
});

// ══════════════════════════════════════════════════════════════

