/**
 * ShortsAI Studio — Render Pipeline & Persistent Monitor Dock (render-monitor.js)
 * Manages video rendering initiation, state restoration, persistent dock monitor, cancel render and terminal log drawer.
 */

// Kullanıcı terminali elle kapattıysa otomatik yeniden açılmasın
let terminalUserClosed = false;


async function restoreRenderState() {
    try {
        const res = await fetch('/api/status');
        if (!res.ok) return;
        const state = await res.json();
        const isActive = Boolean(state.is_rendering);
        const hasTerminalResult = Boolean(state.video_url || state.error);
        if (!isActive && !hasTerminalResult) {
            updateTerminalTriggers(false, 0);
            return;
        }

        persistentMonitor.classList.remove('hidden');
        // Terminal artık açılışta zorla açılmıyor — kullanıcı "Terminal Logları" ile açar

        const percent = Number(state.percent || 0);
        dockProgressFill.style.width = `${percent}%`;
        dockProgressPct.textContent = `%${percent}`;

        const logs = state.logs || [];
        if (logs.length) {
            dockLogSnippet.textContent = logs[logs.length - 1];
            terminalBody.textContent = logs.map(log => log.startsWith('[') ? log : `[Sistem] ${log}`).join('\n') + '\n';
            terminalBody.scrollTop = terminalBody.scrollHeight;
        }

        if (!isActive) {
            isRendering = false;
            if (dockSpinner) dockSpinner.style.display = 'none';
            setCancelButtonState('close');
            updateTerminalTriggers(false, percent);

            if (state.video_url) {
                dockProgressFill.style.width = '100%';
                dockProgressPct.textContent = '%100';
                dockStepTitle.textContent = 'Video hazır';
                dockLogSnippet.textContent = state.video_url;
                livePlayer.autoplay = false;
                livePlayer.src = state.video_url + (state.video_url.includes('?') ? '&' : '?') + 't=' + Date.now();
                livePlayer.classList.remove('hidden');
                livePlayer.pause();
                livePlayer.addEventListener('loadedmetadata', function onMeta() {
                    livePlayer.removeEventListener('loadedmetadata', onMeta);
                    if (livePlayer.paused && livePlayer.currentTime === 0) {
                        try { livePlayer.currentTime = 0.15; } catch (e) {}
                    }
                });
                mockupPlaceholder.classList.add('hidden');
                if (typeof window.syncPhonePreviewAll === 'function') window.syncPhonePreviewAll();
            } else {
                dockStepTitle.textContent = 'Hata Oluştu';
                dockLogSnippet.textContent = state.error;
                dockProgressFill.style.backgroundColor = '#EF4444';
            }
            return;
        }

        isRendering = true;
        dockStepTitle.textContent = state.step || 'İşlem yürütülüyor...';
        updateTerminalTriggers(true, percent);
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
    if (terminalPanel && !terminalUserClosed) terminalPanel.classList.remove('hidden');
    const floatingTrigger = document.getElementById('floating-terminal-trigger');
    if (floatingTrigger) floatingTrigger.style.display = 'none';
    if (terminalBody) terminalBody.scrollTop = terminalBody.scrollHeight;
}

function formatRenderErrorDetail(detail) {
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
        return detail.map(error => {
            if (typeof error === 'string') return error;
            if (!error || typeof error !== 'object') return String(error);

            const location = Array.isArray(error.loc)
                ? error.loc.filter(part => part !== 'body').map(String).join('.')
                : '';
            const message = typeof error.msg === 'string' ? error.msg : '';
            if (location && message) return `${location}: ${message}`;
            if (message) return message;
            return JSON.stringify(error);
        }).join('\n');
    }
    if (!detail || typeof detail !== 'object') return 'Render başlatılamadı.';

    const lines = [];
    if (detail.message) lines.push(String(detail.message));

    const quality = detail.script_quality;
    if (quality && typeof quality === 'object') {
        const limits = quality.limits || {};
        const summary = [];
        if (Number.isFinite(quality.duration)) summary.push(`Süre: ${quality.duration.toFixed(1)} sn`);
        if (Number.isFinite(quality.word_count)) {
            summary.push(`Kelime: ${quality.word_count} (gerekli: ${limits.min_words ?? 85}-${limits.max_words ?? 195})`);
        }
        if (Number.isFinite(quality.scene_count)) {
            summary.push(`Sahne: ${quality.scene_count} (hedef: ${limits.min_scenes ?? 6}-${limits.max_scenes ?? 12}; sınır: ${limits.hard_min_scenes ?? 4}-${limits.hard_max_scenes ?? 24})`);
        }
        if (summary.length) lines.push(summary.join(' · '));

        const issueMessages = (quality.issues || []).map(issue => {
            const value = String(issue);
            let match = value.match(/^duration_out_of_band:(\d+(?:\.\d+)?)$/);
            if (match) return `Toplam süre ${match[1]} sn; 38-65 sn aralığında olmalı.`;
            match = value.match(/^word_count_out_of_band(?::(\d+))?$/);
            if (match) return `Toplam kelime sayısı 85-195 aralığında olmalı${match[1] ? ` (mevcut: ${match[1]})` : ''}.`;
            match = value.match(/^scene_count_out_of_band:(\d+)$/);
            if (match) return `Sahne sayısı en az 4 olmalı (mevcut: ${match[1]}).`;
            match = value.match(/^scene_count_exceeds_limit:(\d+)$/);
            if (match) return `Sahne sayısı en fazla ${limits.hard_max_scenes ?? 24} olmalı (mevcut: ${match[1]}).`;
            match = value.match(/^scene_(\d+)_words_below_(\d+)$/);
            if (match) return `${Number(match[1]) + 1}. sahnenin anlatımı en az ${match[2]} kelime olmalı.`;
            match = value.match(/^scene_(\d+)_narration_invalid$/);
            if (match) return `${Number(match[1]) + 1}. sahnenin anlatımı metin olmalı.`;
            match = value.match(/^scene_(\d+)_narration_placeholder$/);
            if (match) return `${Number(match[1]) + 1}. sahnenin anlatımı örnek veya yer tutucu metin içeremez.`;
            match = value.match(/^scene_(\d+)_visual_description_invalid$/);
            if (match) return `${Number(match[1]) + 1}. sahnenin görsel açıklaması eksik veya geçersiz.`;
            match = value.match(/^scene_(\d+)_queries_insufficient$/);
            if (match) return `${Number(match[1]) + 1}. sahne için en az 2 arama terimi gerekli.`;
            match = value.match(/^scene_(\d+)_queries_invalid$/);
            if (match) return `${Number(match[1]) + 1}. sahnenin arama terimleri metin listesinden oluşmalı.`;
            match = value.match(/^scene_(\d+)_queries_above_(\d+)$/);
            if (match) return `${Number(match[1]) + 1}. sahne en fazla ${match[2]} arama terimi içerebilir.`;
            match = value.match(/^scene_(\d+)_(claim_ids|must_exclude|caption_emphasis)_invalid$/);
            if (match) return `${Number(match[1]) + 1}. sahnenin ${match[2]} alanı metin listesi olmalı.`;
            match = value.match(/^scene_(\d+)_(claim_ids|must_exclude|caption_emphasis)_above_(\d+)$/);
            if (match) return `${Number(match[1]) + 1}. sahnenin ${match[2]} alanı en fazla ${match[3]} öğe içerebilir.`;
            if (value === 'scenes_missing') return 'Senaryoda sahne bulunamadı.';
            return value;
        });
        if (issueMessages.length) lines.push(`Düzeltilmesi gerekenler:\n• ${issueMessages.join('\n• ')}`);
    }

    return lines.length ? lines.join('\n\n') : JSON.stringify(detail, null, 2);
}

// 10. CANLI SSE İZLEME & RENDER BORU HATTI
// ══════════════════════════════════════════════════════════════
(btnQuickRender || document.getElementById('btn-quick-render'))?.addEventListener('click', () => {
    if (currentPlan?.scenes?.length) {
        collectTimelineEdits();
        persistCurrentPlan();
        startRenderProcess(currentPlan);
    } else {
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
    terminalUserClosed = false;
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

    const renderLanguage = selectLanguage?.value === 'en' ? 'en' : 'tr';
    if (typeof ensureTtsVoiceForLanguage === 'function') {
        ensureTtsVoiceForLanguage(renderLanguage);
    }

    const payload = {
        keyword: topic,
        plan: plan,
        niche: selectNiche.value,
        language: renderLanguage,
        voice_gender: (selectTtsVoice?.value === 'auto' ? 'auto' : (findVoiceMeta(selectTtsVoice?.value)?.gender || 'male')),
        tts_voice: (selectTtsVoice?.value && selectTtsVoice.value !== 'auto') ? selectTtsVoice.value : null,
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
        duck_attack_ms: (document.getElementById('audio-chk-enable-ducking') && !document.getElementById('audio-chk-enable-ducking').checked)
            ? 200
            : Math.min(200, Math.max(20, parseInt(document.getElementById('range-duck-attack')?.value || '80', 10))),
        duck_release_ms: (document.getElementById('audio-chk-enable-ducking') && !document.getElementById('audio-chk-enable-ducking').checked)
            ? 600
            : Math.min(600, Math.max(50, parseInt(document.getElementById('range-duck-release')?.value || '200', 10))),
        intro_blast: parseFloat(document.getElementById('range-bgm-blast')?.value || '0.85'),
        outro_swell_sec: parseFloat(document.getElementById('range-outro-swell-sec')?.value || '5'),
        enable_outro_swell: document.getElementById('audio-chk-outro-swell')
            ? !!document.getElementById('audio-chk-outro-swell').checked
            : true,
        enable_bgm: document.getElementById('chk-enable-bgm')
            ? !!document.getElementById('chk-enable-bgm').checked
            : true,
        enable_sonilo_sfx: !!document.getElementById('chk-enable-sonilo-sfx')?.checked,
        enable_outro: document.getElementById('chk-enable-outro')
            ? !!document.getElementById('chk-enable-outro').checked
            : true,
        enable_hook_card: document.getElementById('chk-hook-card')?.checked ?? true,
        enable_broll_insert: !!(document.getElementById('chk-broll-insert')?.checked),
        enable_face_center: !!(document.getElementById('chk-center-face')?.checked),
        enable_emphasis_card: !!(document.getElementById('chk-emphasis-card')?.checked || document.getElementById('chk-emphasis-card-lab')?.checked),
        enable_audio_visualizer: !!(document.getElementById('chk-audio-visualizer')?.checked),
        enable_news_ticker: !!(document.getElementById('chk-news-ticker')?.checked),
        transition_style: document.querySelector('#wiz-transition-preview-strip .wiz-trans-chip.active')?.getAttribute('data-trans-id')
            || plan?.transition_style
            || currentPlan?.transition_style
            || 'whip_pan'
    };
    if (plan && !plan.visual_mode) {
        plan.visual_mode = payload.visual_mode;
    }
    if (plan && typeof plan === 'object') {
        plan.transition_style = payload.transition_style;
    }

    fetch('/api/video/render', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    }).then(res => {
        if (!res.ok) {
            return res.json().catch(() => null).then(errorBody => {
                const detail = errorBody?.detail ?? errorBody?.message ?? errorBody;
                const message = formatRenderErrorDetail(detail);
                throw new Error(message || `HTTP ${res.status}: ${res.statusText || 'Render isteği reddedildi.'}`);
            });
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
                setTimeout(() => startRenderProcess(currentPlan), 200);
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
    const closeDockBtn = document.getElementById('btn-close-dock');
    if (mode === 'cancelling') {
        btnCancelRender.disabled = true;
        btnCancelRender.className = 'btn btn-sm btn-danger';
        btnCancelRender.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> İptal Ediliyor...';
        if (closeDockBtn) closeDockBtn.style.display = '';
    } else if (mode === 'close') {
        btnCancelRender.disabled = false;
        btnCancelRender.className = 'btn btn-sm btn-secondary';
        btnCancelRender.innerHTML = '<i class="fa-solid fa-xmark"></i> Kapat';
        // İptal butonu zaten "Kapat" oldu — ikinci Kapat butonunu gizle
        if (closeDockBtn) closeDockBtn.style.display = 'none';
    } else {
        btnCancelRender.disabled = false;
        btnCancelRender.className = 'btn btn-sm btn-danger';
        btnCancelRender.innerHTML = '<i class="fa-solid fa-circle-xmark"></i> İptal Et';
        if (closeDockBtn) closeDockBtn.style.display = '';
    }
}

btnToggleLog?.addEventListener('click', () => {
    terminalPanel?.classList.toggle('hidden');
    if (terminalPanel && !terminalPanel.classList.contains('hidden')) terminalUserClosed = false;
});

btnCloseLog?.addEventListener('click', () => {
    terminalPanel?.classList.add('hidden');
    terminalUserClosed = true;
});

function dismissMonitorDock() {
    persistentMonitor?.classList.add('hidden');
    terminalPanel?.classList.add('hidden');
    if (isRendering) {
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
    if (!isRendering) {
        dismissMonitorDock();
        return;
    }

    if (confirm('Aktif video üretimini iptal etmek istiyor musunuz?')) {
        setCancelButtonState('cancelling');
        try {
            const response = await fetch('/api/video/cancel', { method: 'POST' });
            const data = await response.json();
            showToast(`⛔ ${data.message}`);

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
