/**
 * ShortsAI Studio — Core State Object & Initialization (state.js)
 * Manages reactive application state, getters/setters, DOM element cache, and quality panel status.
 */

window.ShortsApp = window.ShortsApp || {};

// Shared State Container
window.ShortsApp.state = window.ShortsApp.state || {
    currentPlan: null,
    timelineReviewed: false,
    qualityPanelGreen: false,
    userManuallyPickedNiche: false,
    eventSource: null,
    allNiches: [],
    isRendering: false,
    selectedRedditPost: null,
    pendingFormatFingerprint: null,
    trendFormatFingerprintAggregate: null,
    lastTrendResults: [],
    suppressFingerprintClear: false,
    nicheResolveTimer: null,
    lockedNicheId: null,
    splitTouched: false,
    ttsVoiceCatalog: { tr: [], en: [], elevenlabs: [] },
    elevenlabsConfigured: false
};

// Global property accessors on window
(function() {
    const stateKeys = [
        'currentPlan', 'timelineReviewed', 'qualityPanelGreen', 'userManuallyPickedNiche',
        'eventSource', 'allNiches', 'isRendering', 'selectedRedditPost',
        'pendingFormatFingerprint', 'trendFormatFingerprintAggregate', 'lastTrendResults',
        'suppressFingerprintClear', 'nicheResolveTimer', 'lockedNicheId',
        'splitTouched', 'ttsVoiceCatalog', 'elevenlabsConfigured'
    ];
    stateKeys.forEach(key => {
        Object.defineProperty(window, key, {
            get() { return window.ShortsApp.state[key]; },
            set(val) { window.ShortsApp.state[key] = val; },
            configurable: true,
            enumerable: true
        });
    });
})();

// Cached DOM element references
var navButtons, tabPanes, pageTitle, pageDesc,
    inputTopic, selectNiche, selectSubPreset, selectLanguage, selectTtsVoice,
    selectGameplayCategory, gameplayCategoryWrap, chkSplitScreen,
    chkAntiDuplicate, chkKenBurns, chkZoompan, chkBrollInsert, chkCenterFace,
    chkEmphasisCard, chkEmphasisCardLab, chkAllowSimilarScript, chkAutoPublish,
    btnCreateScript, btnQuickRender, btnRegenerateScriptStudio,
    livePlayer, mockupPlaceholder, mockupStatusText,
    persistentMonitor, dockStepTitle, dockLogSnippet, dockProgressFill, dockProgressPct,
    btnToggleLog, btnCancelRender, btnCloseDock, dockSpinner,
    terminalPanel, terminalBody, btnCloseLog;

function initDomElements() {
    navButtons = document.querySelectorAll('.nav-btn');
    tabPanes = document.querySelectorAll('.tab-pane');
    pageTitle = document.getElementById('current-page-title');
    pageDesc = document.getElementById('current-page-desc');
    inputTopic = document.getElementById('input-topic');
    selectNiche = document.getElementById('select-niche');
    selectSubPreset = document.getElementById('select-subtitle-preset');
    selectLanguage = document.getElementById('select-language');
    selectTtsVoice = document.getElementById('select-tts-voice');
    selectGameplayCategory = document.getElementById('select-gameplay-category');
    gameplayCategoryWrap = document.getElementById('gameplay-category-wrap');
    chkSplitScreen = document.getElementById('chk-split-screen');
    chkAntiDuplicate = document.getElementById('chk-anti-duplicate');
    chkKenBurns = document.getElementById('chk-ken-burns');
    chkZoompan = document.getElementById('chk-zoompan');
    chkBrollInsert = document.getElementById('chk-broll-insert');
    chkCenterFace = document.getElementById('chk-center-face');
    chkEmphasisCard = document.getElementById('chk-emphasis-card');
    chkEmphasisCardLab = document.getElementById('chk-emphasis-card-lab');
    if (chkEmphasisCard && chkEmphasisCardLab) {
        chkEmphasisCard.addEventListener('change', () => { chkEmphasisCardLab.checked = chkEmphasisCard.checked; });
        chkEmphasisCardLab.addEventListener('change', () => { chkEmphasisCard.checked = chkEmphasisCardLab.checked; });
    }
    const fxEnabledCount = document.getElementById('fx-enabled-count');
    const fxOptionToggles = document.querySelectorAll(
        '#render-enhancement-options .switches-grid input[type="checkbox"]'
    );
    if (fxEnabledCount) {
        const updateFxEnabledCount = () => {
            const enabledCount = Array.from(fxOptionToggles).filter(toggle => toggle.checked).length;
            fxEnabledCount.textContent = `${enabledCount} açık`;
        };
        fxOptionToggles.forEach(toggle => toggle.addEventListener('change', updateFxEnabledCount));
        chkEmphasisCardLab?.addEventListener('change', updateFxEnabledCount);
        updateFxEnabledCount();
    }
    chkAllowSimilarScript = document.getElementById('chk-allow-similar-script');
    chkAutoPublish = document.getElementById('chk-auto-publish');
    btnCreateScript = document.getElementById('btn-create-script');
    btnQuickRender = document.getElementById('btn-quick-render');
    btnRegenerateScriptStudio = document.getElementById('btn-regenerate-script-studio');
    livePlayer = document.getElementById('live-preview-player');
    mockupPlaceholder = document.getElementById('mockup-placeholder');
    mockupStatusText = document.getElementById('mockup-status-text');
    persistentMonitor = document.getElementById('persistent-monitor');
    dockStepTitle = document.getElementById('dock-step-title');
    dockLogSnippet = document.getElementById('dock-log-snippet');
    dockProgressFill = document.getElementById('dock-progress-fill');
    dockProgressPct = document.getElementById('dock-progress-pct');
    btnToggleLog = document.getElementById('btn-toggle-terminal-log');
    btnCancelRender = document.getElementById('btn-cancel-render');
    btnCloseDock = document.getElementById('btn-close-dock');
    dockSpinner = document.getElementById('dock-spinner');
    terminalPanel = document.getElementById('terminal-log-panel');
    terminalBody = document.getElementById('terminal-log-body');
    btnCloseLog = document.getElementById('btn-close-log');

    if (chkAllowSimilarScript) {
        chkAllowSimilarScript.addEventListener('change', () => {
            const plag = currentPlan?.plagiarism || currentPlan?.meta?.plagiarism;
            if (plag) applyPlagiarismBadge(plag);
        });
    }
    Object.assign(window, {
        inputTopic, selectNiche, selectSubPreset, selectLanguage, selectTtsVoice,
        selectGameplayCategory, gameplayCategoryWrap, chkSplitScreen, chkAntiDuplicate,
        chkKenBurns, chkZoompan, chkBrollInsert, chkCenterFace, chkEmphasisCard,
        chkEmphasisCardLab, chkAllowSimilarScript, chkAutoPublish, btnCreateScript,
        btnQuickRender, btnRegenerateScriptStudio, navButtons, tabPanes, pageTitle,
        pageDesc, persistentMonitor, dockStepTitle, dockLogSnippet, dockProgressFill,
        dockProgressPct, btnToggleLog, btnCancelRender, btnCloseDock, dockSpinner,
        terminalPanel, terminalBody, btnCloseLog
    });
}

initDomElements();

function restoreStudioSettings() {
    try {
        const raw = localStorage.getItem(STUDIO_SETTINGS_STORAGE_KEY);
        if (!raw) return null;
        const s = JSON.parse(raw);
        if (!s || typeof s !== 'object') return null;

        if (s.userManuallyPickedNiche !== undefined) {
            userManuallyPickedNiche = Boolean(s.userManuallyPickedNiche);
        }
        if (s.topic && inputTopic && (!inputTopic.value.trim() || inputTopic.value.includes('Marcus Aurelius'))) {
            inputTopic.value = s.topic;
        }
        if (s.niche && selectNiche && [...selectNiche.options].some(o => o.value === s.niche)) {
            selectNiche.value = s.niche;
        }
        if (s.subtitlePreset && selectSubPreset) {
            selectSubPreset.value = s.subtitlePreset;
        }
        if (s.language && selectLanguage) {
            const restoredLanguage = s.language === 'en' ? 'en' : 'tr';
            selectLanguage.value = restoredLanguage;
            const btnTr = document.getElementById('btn-quick-lang-tr');
            const btnEn = document.getElementById('btn-quick-lang-en');
            if (btnTr && btnEn) {
                btnTr.setAttribute('aria-pressed', String(restoredLanguage === 'tr'));
                btnEn.setAttribute('aria-pressed', String(restoredLanguage === 'en'));
                if (restoredLanguage === 'en') {
                    btnTr.classList.remove('active');
                    btnTr.classList.add('btn-outline');
                    btnEn.classList.add('active');
                    btnEn.classList.remove('btn-outline');
                    if (inputTopic) inputTopic.placeholder = 'e.g.: 3 Dark Psychology Secrets Manipulation Experts Never Tell You #Shorts';
                } else {
                    btnEn.classList.remove('active');
                    btnEn.classList.add('btn-outline');
                    btnTr.classList.add('active');
                    btnTr.classList.remove('btn-outline');
                    if (inputTopic) inputTopic.placeholder = "Örn: Marcus Aurelius'un Öfkeyi Yok Eden 3 Stoacı Kuralı";
                }
            }
        }
        if (s.ttsVoice && selectTtsVoice && [...selectTtsVoice.options].some(o => o.value === s.ttsVoice)) {
            selectTtsVoice.value = s.ttsVoice;
        }
        if (s.bgmTrack) {
            const el = document.getElementById('studio-bgm-track');
            if (el && [...el.options].some(o => o.value === s.bgmTrack)) el.value = s.bgmTrack;
        }
        if (s.resolution) {
            const el = document.getElementById('select-render-resolution');
            if (el) el.value = s.resolution;
        }
        if (s.safeMode) {
            const el = document.getElementById('select-studio-safe-mode');
            if (el) el.value = s.safeMode;
        }
        if (s.contentGaps) {
            const el = document.getElementById('content-gap-topics');
            if (el) el.value = s.contentGaps;
            const researchTools = document.getElementById('topic-research-tools');
            if (researchTools) researchTools.open = true;
        }
        if (s.splitScreen !== undefined && chkSplitScreen) {
            chkSplitScreen.checked = !!s.splitScreen;
            splitTouched = true;
            if (gameplayCategoryWrap) gameplayCategoryWrap.style.display = s.splitScreen ? 'block' : 'none';
        }
        if (s.gameplayCategory && selectGameplayCategory) {
            selectGameplayCategory.value = s.gameplayCategory;
        }
        if (s.antiDuplicate !== undefined && chkAntiDuplicate) chkAntiDuplicate.checked = !!s.antiDuplicate;
        if (s.kenBurns !== undefined && chkKenBurns) chkKenBurns.checked = !!s.kenBurns;
        if (s.zoompan !== undefined && chkZoompan) chkZoompan.checked = !!s.zoompan;
        if (s.brollInsert !== undefined && chkBrollInsert) chkBrollInsert.checked = !!s.brollInsert;
        if (s.centerFace !== undefined && chkCenterFace) chkCenterFace.checked = !!s.centerFace;
        if (s.emphasisCard !== undefined) {
            if (chkEmphasisCard) chkEmphasisCard.checked = !!s.emphasisCard;
            if (chkEmphasisCardLab) chkEmphasisCardLab.checked = !!s.emphasisCard;
        }
        if (s.enableBgm !== undefined) {
            const studioBgm = document.getElementById('chk-enable-bgm');
            const audioBgm = document.getElementById('audio-chk-enable-bgm');
            if (studioBgm) studioBgm.checked = !!s.enableBgm;
            if (audioBgm) audioBgm.checked = !!s.enableBgm;
        }
        if (s.enableOutro !== undefined) {
            const studioOutro = document.getElementById('chk-enable-outro');
            const audioOutro = document.getElementById('audio-chk-enable-outro');
            if (studioOutro) studioOutro.checked = !!s.enableOutro;
            if (audioOutro) audioOutro.checked = !!s.enableOutro;
        }
        if (s.introWhoosh !== undefined) {
            const studioWhoosh = document.getElementById('chk-intro-whoosh');
            const audioWhoosh = document.getElementById('audio-chk-intro-whoosh');
            if (studioWhoosh) studioWhoosh.checked = !!s.introWhoosh;
            if (audioWhoosh) audioWhoosh.checked = !!s.introWhoosh;
        }
        return s;
    } catch (e) {
        return null;
    }
}

function updateScriptActionButtons() {
    const btn = document.getElementById('btn-create-script');
    const btnNewTopic = document.getElementById('btn-new-topic');
    const btnRegenerateStudio = document.getElementById('btn-regenerate-script-studio');
    const btnRegenerateTimeline = document.getElementById('btn-regenerate-scenario');
    const btnTranslateScript = document.getElementById('btn-translate-script');
    const btnCopyStudio = document.getElementById('btn-copy-script-studio');
    if (!btn) return;

    const currentTopic = (inputTopic?.value || '').trim();
    const planTopic = (currentPlan?.title || currentPlan?.topic || currentPlan?.keyword || '').trim();
    const ready = hasExistingPlan() && Boolean(currentTopic);
    const sourceLanguage = String(currentPlan?.language || currentPlan?.lang || window.APP_STATE?.language || 'tr').slice(0, 2);
    const targetLanguage = selectLanguage?.value || window.APP_STATE?.language || 'tr';
    const topicChanged = ready && Boolean(planTopic) && (currentTopic.toLowerCase() !== planTopic.toLowerCase());
    const activePlanReady = ready && !topicChanged;
    const isGenerating = btn.dataset.generating === 'true';

    btnNewTopic?.classList.toggle('hidden', !activePlanReady);
    btnRegenerateStudio?.classList.toggle('hidden', !activePlanReady);
    btnRegenerateTimeline?.classList.toggle('hidden', !hasExistingPlan());
    btnTranslateScript?.classList.toggle('hidden', !activePlanReady || sourceLanguage === targetLanguage);
    btnCopyStudio?.classList.toggle('hidden', !activePlanReady);
    btn.disabled = isGenerating || (!ready && !currentTopic);
    if (btnTranslateScript && sourceLanguage !== targetLanguage) {
        const targetName = targetLanguage === 'en' ? 'İngilizceye' : 'Türkçeye';
        const spanEl = btnTranslateScript.querySelector('span');
        if (spanEl) spanEl.textContent = `Senaryoyu ${targetName} Çevir`;
    }
    if (typeof window.syncWizardStep2Preview === 'function') {
        window.syncWizardStep2Preview();
    }

    if (isGenerating) return;

    if (ready) {
        if (topicChanged) {
            btn.className = 'btn btn-primary btn-lg';
            btn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i><span id="btn-create-script-label">Yeni Konu İçin Senaryo Yaz</span>';
        } else {
            btn.className = 'btn btn-secondary btn-lg';
            btn.innerHTML = '<i class="fa-solid fa-clapperboard"></i><span id="btn-create-script-label">Senaryoyu İncele & Düzenle</span>';
        }
        if (btnRegenerateStudio) {
            btnRegenerateStudio.innerHTML = '<i class="fa-solid fa-arrows-rotate"></i><span>Senaryoyu Yeniden Yaz</span>';
        }
    } else if (currentTopic) {
        btn.className = 'btn btn-primary btn-lg';
        btn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i><span id="btn-create-script-label">Senaryo Yaz</span>';
    } else {
        btn.className = 'btn btn-secondary btn-lg';
        btn.innerHTML = '<i class="fa-solid fa-pen-to-square"></i><span id="btn-create-script-label">Konu girin</span>';
    }
}

function setSqpPill(id, text, state) {
    const el = document.getElementById(id);
    if (!el) return;
    el.className = `sqp-pill ${state || 'neutral'}`;
    const icon = el.querySelector('i');
    el.textContent = '';
    if (icon) el.appendChild(icon);
    el.append(document.createTextNode(' ' + text));
}

function directorCadenceStatus(sceneCount) {
    if (sceneCount === 6) return 'ok';
    return sceneCount >= 4 ? 'warn' : 'fail';
}

function directorWordCountStatus(wordCount) {
    if (wordCount < 85 || wordCount > 195) return 'fail';
    if (wordCount > 110) return 'warn';
    return 'ok';
}

function directorDurationStatus(duration) {
    if (duration < 38 || duration > 65) return 'fail';
    if (duration < 50 || duration > 60.25) return 'warn';
    return 'ok';
}

function updateStudioPlanSummary(scenes) {
    const totalSec = scenes.reduce((acc, scene) => acc + (parseFloat(scene.duration) || 6), 0);
    const totalWords = scenes.reduce((acc, scene) => acc + wordCount(cleanNarration(scene.narration)), 0);
    const queries = scenes.map(scene => ((scene.search_queries || [])[0] || '').toLowerCase().trim()).filter(Boolean);
    const uniqueClips = new Set(queries).size;
    const dupes = queries.length - uniqueClips;

    setSqpPill('sqp-cadence', `Cadence: ${scenes.length} sahne`, directorCadenceStatus(scenes.length));
    setSqpPill('sqp-words', `Kelime: ${totalWords}`, directorWordCountStatus(totalWords));
    setSqpPill('sqp-duration', `Sure: ${totalSec.toFixed(1)}sn`, directorDurationStatus(totalSec));
    setSqpPill('sqp-clips', `Klip: ${uniqueClips}/${scenes.length}`, dupes === 0 ? 'ok' : 'warn');
}

async function updateStudioQualityPanel(plan, { silent = false } = {}) {
    const panel = document.getElementById('studio-quality-panel');
    const badge = document.getElementById('sqp-status-badge');
    const issuesEl = document.getElementById('sqp-issues');
    const pills = document.getElementById('sqp-pills');
    const advisoryGroup = document.getElementById('sqp-advisory-group');
    const advisoriesEl = document.getElementById('sqp-advisories');
    if (!panel || !badge) return { ok: false, issues: ['Panel yok'] };

    if (!plan?.scenes?.length) {
        pills?.classList.add('hidden');
        const scriptQuality = plan?.meta?.script_quality || {};
        const scriptHardFail = scriptQuality.hard_fail === true;
        badge.className = `sqp-status-badge ${scriptHardFail ? 'blocked' : 'waiting'}`;
        badge.textContent = scriptHardFail ? 'Senaryo kalite kapisi: BLOKE' : 'Senaryo bekleniyor';
        setSqpPill('sqp-cadence', 'Cadence: —', 'neutral');
        setSqpPill('sqp-words', 'Kelime: —', 'neutral');
        setSqpPill('sqp-duration', 'Sure: —', 'neutral');
        setSqpPill('sqp-clips', 'Klip: —', 'neutral');
        setSqpPill('sqp-narration', 'Anlatim: —', 'neutral');
        setSqpPill('sqp-plagiarism', 'Özgünlük: —', 'neutral');
        setSqpPill('sqp-discovery', 'Keşfet: —', 'neutral');
        setSqpPill('sqp-pov', 'POV: —', 'neutral');
        if (issuesEl) {
            const scriptIssues = [
                ...(scriptQuality.issues || []).map(issue => `Senaryo kalite: ${issue}`),
                ...(scriptQuality.warnings || []).map(warning => `Senaryo kalite uyarısı: ${warning}`),
            ];
            issuesEl.classList.toggle('hidden', !scriptIssues.length);
            issuesEl.innerHTML = scriptIssues.map(issue => `<li>${formatQualityIssueWithRoadmap(issue)}</li>`).join('');
        }
        if (advisoryGroup && advisoriesEl) {
            advisoriesEl.replaceChildren();
            advisoryGroup.classList.add('hidden');
        }
        updateRenderButtonsBlocked(
            true,
            scriptQuality.issues?.[0] || 'Once senaryo olusturun',
            !scriptHardFail
        );
        return { ok: false, issues: scriptQuality.issues || ['Senaryo yok'], script_quality: scriptQuality, hard_fail: scriptHardFail };
    }

    pills?.classList.remove('hidden');
    updateStudioPlanSummary(plan.scenes);

    badge.className = 'sqp-status-badge warn';
    badge.textContent = 'Dogrulaniyor...';

    const validation = await validatePlanViaApi(plan, { autoRepair: true });
    if (validation.quality_repair?.status === 'repaired') {
        showToast('Senaryo kalite sorunları otomatik düzeltildi.', 'success');
    } else if (validation.quality_repair && validation.quality_repair.status !== 'not_needed') {
        showToast('Senaryo kalite sorunlarının bir kısmı düzeltilemedi; kalite raporunu inceleyin.', 'warn');
    } else if (validation.repaired && validation.fixes?.length) {
        showToast('Anlatim otomatik duzeltildi');
    }
    const continuityAdvisories = Array.isArray(validation.scene_continuity_advisories)
        ? validation.scene_continuity_advisories
        : [];
    const storyWarnings = validation.script_quality?.story_quality?.warnings || [];
    if (advisoryGroup && advisoriesEl) {
        advisoriesEl.replaceChildren();
        [...continuityAdvisories, ...storyWarnings.map(formatQualityGateIssue)].forEach(advisory => {
            const item = document.createElement('li');
            item.textContent = String(advisory);
            advisoriesEl.appendChild(item);
        });
        advisoryGroup.classList.toggle('hidden', continuityAdvisories.length === 0);
    }
    let activePlan = plan;
    if (validation.plan) {
        activePlan = validation.plan === plan
            ? plan
            : {
                ...validation.plan,
                meta: { ...(plan.meta || {}), ...(validation.plan.meta || {}) }
            };
    }
    const scriptQuality = validation.script_quality || activePlan.meta?.script_quality || {};
    if (validation.script_quality) {
        activePlan = {
            ...activePlan,
            meta: { ...(activePlan.meta || {}), script_quality: validation.script_quality }
        };
    }
    updateStudioPlanSummary(activePlan.scenes || []);
    if (activePlan !== currentPlan) {
        currentPlan = activePlan;
        persistCurrentPlan();
        if (typeof renderTimelineScenes === 'function') {
            try { renderTimelineScenes(activePlan); } catch (_) {}
        }
    }

    if (
        (!validation.quality_repair || validation.quality_repair.status === 'not_needed')
        && validation.repaired
        && validation.fixes?.length
        && !silent
    ) {
        showToast('Anlatim otomatik duzeltildi');
    }

    const narrOk = validation.narration_ok ?? validation.ok;
    setSqpPill('sqp-narration', narrOk ? 'Anlatim: OK' : 'Anlatim: SORUN', narrOk ? 'ok' : 'fail');

    const hc = activePlan.human_craft || activePlan.meta?.human_craft || {};
    const disc = hc.discovery_beast || activePlan.meta?.discovery_beast || validation.compliance?.discovery_beast || {};
    const discScore = disc.score;
    const discPass = disc.pass === true;
    if (discScore != null) {
        setSqpPill(
            'sqp-discovery',
            `Keşfet: ${Math.round(discScore)}${discPass ? '' : ' ✗'}`,
            discPass ? 'ok' : (discScore >= 45 ? 'warn' : 'fail')
        );
    } else {
        setSqpPill('sqp-discovery', 'Keşfet: —', 'neutral');
    }
    const pov = hc.pov_angle || '—';
    const hook = (hc.mute_hook_line || '').slice(0, 28);
    setSqpPill('sqp-pov', hook ? `POV: ${pov} · ${hook}` : `POV: ${pov}`, hc.pov_angle ? 'ok' : 'neutral');

    const scriptHardFail = scriptQuality.hard_fail === true;
    if (issuesEl) {
        const craftIssues = [];
        if (disc.fail_reasons?.length) {
            craftIssues.push(...disc.fail_reasons.map(r => `keşfet:${r}`));
        }
        const scriptIssues = [
            ...(scriptQuality.issues || []).map(issue => `Senaryo kalite: ${issue}`),
            ...(scriptQuality.warnings || []).map(warning => `Senaryo kalite uyarısı: ${warning}`),
        ];
        const allIssues = [...(validation.issues || []), ...craftIssues, ...scriptIssues];
        if (allIssues.length) {
            issuesEl.classList.remove('hidden');
            issuesEl.innerHTML = allIssues.map(i => `<li>${formatQualityIssueWithRoadmap(i)}</li>`).join('');
        } else {
            issuesEl.classList.add('hidden');
            issuesEl.innerHTML = '';
        }
    }
    qualityPanelGreen = !scriptHardFail && narrOk && (discPass || discScore == null);
    if (qualityPanelGreen) {
        badge.className = 'sqp-status-badge ok';
        badge.textContent = 'Render hazir';
        updateRenderButtonsBlocked(false);
    } else {
        badge.className = 'sqp-status-badge blocked';
        badge.textContent = scriptHardFail
            ? 'Senaryo kalite kapisi: BLOKE'
            : (discPass === false ? 'Keşfet skoru düşük' : 'Render kapali');
        updateRenderButtonsBlocked(
            true,
            scriptQuality.issues?.[0] || validation.issues?.[0] || disc.fail_reasons?.[0] || 'Anlatim kalite kapisi'
        );
    }

    return { ...validation, plan: activePlan, script_quality: scriptQuality, hard_fail: scriptHardFail };
}

function getComplianceIssues(scenes) {
    if (!scenes || !scenes.length) return { hard: ['Senaryo yok — once senaryo olusturun'], soft: [] };
    const soft = [];
    const timedScenes = scenes.filter(s => sceneDurationSec(s) !== null);
    if (!timedScenes.length) return { hard: [], soft: [] };
    const totalSec = timedScenes.reduce((acc, s) => acc + sceneDurationSec(s), 0);
    if (totalSec < 38 || totalSec > 60) {
        soft.push(`Sure bandi: ${totalSec.toFixed(1)}sn (izin 38-60, tavan 60)`);
    }
    if (directorCadenceStatus(scenes.length) !== 'ok') {
        soft.push(`Cadence: ${scenes.length} sahne (Director hedefi 6)`);
    }
    const longCuts = timedScenes.filter(s => sceneDurationSec(s) > 3.2).length;
    if (longCuts > 3) {
        soft.push(`${longCuts} sahne 3.2sn ustu`);
    }
    const hard = getNarrationIssues(scenes);
    return { hard, soft };
}

function updateRenderButtonsBlocked(blocked, reason, allowDirectRender = false) {
    const scriptQuality = currentPlan?.meta?.script_quality || {};
    const scriptHardFail = scriptQuality.hard_fail === true;
    const blockAll = !!blocked || scriptHardFail;
    if (scriptHardFail) reason = scriptQuality.issues?.[0] || reason;
    const btns = [
        { button: document.getElementById('btn-render-from-timeline'), blocked: blockAll },
        {
            button: document.getElementById('btn-quick-render'),
            blocked: scriptHardFail || (blockAll && !allowDirectRender)
        }
    ].filter(({ button }) => button);
    btns.forEach(({ button, blocked: buttonBlocked }) => {
        button.disabled = buttonBlocked;
        button.title = buttonBlocked ? (reason || 'Kopuk anlatim — once senaryoyu duzeltin') : '';
        button.classList.toggle('render-blocked', buttonBlocked);
    });
}

const TOPIC_SOURCE_LABELS = {
    youtube: { label: 'YouTube', icon: 'fa-brands fa-youtube', cls: 'youtube' },
    ai: { label: 'AI', icon: 'fa-solid fa-wand-magic-sparkles', cls: 'ai' },
    trend: { label: 'Trend', icon: 'fa-solid fa-chart-line', cls: 'trend' },
    reddit: { label: 'Reddit', icon: 'fa-brands fa-reddit-alien', cls: 'reddit' },
    google_trends: { label: 'Google Trends', icon: 'fa-solid fa-arrow-trend-up', cls: 'trend' },
    rss: { label: 'RSS', icon: 'fa-solid fa-rss', cls: 'trend' },
};

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDomElements);
} else {
    initDomElements();
}
