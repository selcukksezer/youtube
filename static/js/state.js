/**
 * ShortsAI Studio — State & Core Utilities (state.js)
 * Manages reactive application state, local storage persistence, DOM bindings, and quality checks.
 */

window.ShortsApp = window.ShortsApp || {};

// Shared State Container
window.ShortsApp.state = {
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
    chkAntiDuplicate, chkKenBurns, chkZoompan, chkAutoPublish,
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

    window.inputTopic = inputTopic;
    window.selectNiche = selectNiche;
    window.selectSubPreset = selectSubPreset;
    window.selectLanguage = selectLanguage;
    window.selectTtsVoice = selectTtsVoice;
    window.selectGameplayCategory = selectGameplayCategory;
    window.gameplayCategoryWrap = gameplayCategoryWrap;
    window.chkSplitScreen = chkSplitScreen;
    window.chkAntiDuplicate = chkAntiDuplicate;
    window.chkKenBurns = chkKenBurns;
    window.chkZoompan = chkZoompan;
    window.chkBrollInsert = chkBrollInsert;
    window.chkCenterFace = chkCenterFace;
    window.chkEmphasisCard = chkEmphasisCard;
    window.chkEmphasisCardLab = chkEmphasisCardLab;
    window.chkAllowSimilarScript = chkAllowSimilarScript;
    if (chkAllowSimilarScript) {
        chkAllowSimilarScript.addEventListener('change', () => {
            const plag = currentPlan?.plagiarism || currentPlan?.meta?.plagiarism;
            if (plag) applyPlagiarismBadge(plag);
        });
    }
    window.chkAutoPublish = chkAutoPublish;
    window.btnCreateScript = btnCreateScript;
    window.btnQuickRender = btnQuickRender;
    window.btnRegenerateScriptStudio = btnRegenerateScriptStudio;
    window.navButtons = navButtons;
    window.tabPanes = tabPanes;
    window.pageTitle = pageTitle;
    window.pageDesc = pageDesc;
    window.persistentMonitor = persistentMonitor;
    window.dockStepTitle = dockStepTitle;
    window.dockLogSnippet = dockLogSnippet;
    window.dockProgressFill = dockProgressFill;
    window.dockProgressPct = dockProgressPct;
    window.btnToggleLog = btnToggleLog;
    window.btnCancelRender = btnCancelRender;
    window.btnCloseDock = btnCloseDock;
    window.dockSpinner = dockSpinner;
    window.terminalPanel = terminalPanel;
    window.terminalBody = terminalBody;
    window.btnCloseLog = btnCloseLog;
}

// Call immediately on script load because script tag is located at bottom of body
initDomElements();


const PLAN_STORAGE_KEY = 'shortsCurrentPlan';
const PLAN_SCHEMA_VERSION = 2;

function sanitizeTopicTitleForDisplay(title) {
    let t = (title || '').trim();
    if (!t) return '';
    t = t.replace(/[\u{10000}-\u{10FFFF}]/gu, '');
    t = t.replace(/[\u2600-\u27BF\uFE00-\uFE0F]/g, '');
    t = t.replace(/#[\p{L}\p{N}_]+/gu, ' ');
    t = t.replace(/[^\p{L}\p{N}\s\-&]/gu, ' ');
    t = t.replace(/\s+/g, ' ').trim();
    return t || (title || '').trim();
}

function sceneDescriptionUsable(text) {
    const raw = (text || '').trim();
    if (!raw || raw.length < 12) return false;
    if (/^(?:\(?\s*scene[_\s-]?description\s*\)?|\.\.\.|tbd|n\/a|placeholder|desc(?:ription)?)\s*$/i.test(raw)) return false;
    const lower = raw.toLowerCase();
    if (lower.includes('scene_description') && raw.length < 40) return false;
    if (['description', 'visual', 'n/a', 'tbd', '...'].includes(lower)) return false;
    return true;
}

function planHasBrokenNarration(plan) {
    const scenes = plan?.scenes || [];
    if (!scenes.length) return true;
    return scenes.some(sc => {
        const raw = (sc.narration || '').trim();
        if (!raw || raw === '.' || raw === '-' || raw === '—' || raw === '...') return true;
        const norm = raw
            .replace(/\*\*(?:URGENT|DRAMATIC|EPIC|CALM|MYSTERIOUS|ENERGETIC|DARK|BRIGHT|SECRET|WARNING|HOOK|CTA)\*\*\s*/gi, '')
            .replace(/[\u{10000}-\u{10FFFF}]/gu, '')
            .replace(/[\u2600-\u27BF\uFE00-\uFE0F]/g, '')
            .replace(/[#*_~^\\/|<>@=`\[\]{}]/g, ' ')
            .replace(/\s+/g, ' ')
            .trim();
        const words = norm.split(/\s+/).filter(Boolean);
        if (words.length < 5) return true;
        return false;
    });
}

const STUDIO_SETTINGS_STORAGE_KEY = 'shortsStudioSettings';

function saveStudioSettings() {
    try {
        const settings = {
            topic: (inputTopic?.value || '').trim(),
            niche: selectNiche?.value || '',
            subtitlePreset: selectSubPreset?.value || '',
            language: selectLanguage?.value || '',
            ttsVoice: selectTtsVoice?.value || '',
            bgmTrack: document.getElementById('studio-bgm-track')?.value || '',
            resolution: document.getElementById('select-render-resolution')?.value || '',
            safeMode: document.getElementById('select-studio-safe-mode')?.value || '',
            contentGaps: document.getElementById('content-gap-topics')?.value || '',
            splitScreen: chkSplitScreen ? !!chkSplitScreen.checked : false,
            gameplayCategory: selectGameplayCategory?.value || '',
            antiDuplicate: chkAntiDuplicate ? !!chkAntiDuplicate.checked : true,
            kenBurns: chkKenBurns ? !!chkKenBurns.checked : true,
            zoompan: chkZoompan ? !!chkZoompan.checked : false,
            brollInsert: chkBrollInsert ? !!chkBrollInsert.checked : false,
            centerFace: chkCenterFace ? !!chkCenterFace.checked : false,
            emphasisCard: (chkEmphasisCard ? !!chkEmphasisCard.checked : (chkEmphasisCardLab ? !!chkEmphasisCardLab.checked : false)),
            enableBgm: document.getElementById('chk-enable-bgm')
                ? !!document.getElementById('chk-enable-bgm').checked
                : true,
            enableOutro: document.getElementById('chk-enable-outro')
                ? !!document.getElementById('chk-enable-outro').checked
                : true,
            introWhoosh: !!document.getElementById('chk-intro-whoosh')?.checked,
            userManuallyPickedNiche: !!userManuallyPickedNiche,
            savedAt: Date.now()
        };
        localStorage.setItem(STUDIO_SETTINGS_STORAGE_KEY, JSON.stringify(settings));
    } catch (e) {}
}

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
        if (s.niche && selectNiche) {
            if ([...selectNiche.options].some(o => o.value === s.niche)) {
                selectNiche.value = s.niche;
            }
        }
        if (s.subtitlePreset && selectSubPreset) {
            selectSubPreset.value = s.subtitlePreset;
        }
        if (s.language && selectLanguage) {
            selectLanguage.value = s.language;
            const btnTr = document.getElementById('btn-quick-lang-tr');
            const btnEn = document.getElementById('btn-quick-lang-en');
            if (btnTr && btnEn) {
                if (s.language === 'en') {
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
        if (s.ttsVoice && selectTtsVoice) {
            if ([...selectTtsVoice.options].some(o => o.value === s.ttsVoice)) {
                selectTtsVoice.value = s.ttsVoice;
            }
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
        }
        if (s.splitScreen !== undefined && chkSplitScreen) {
            chkSplitScreen.checked = !!s.splitScreen;
            splitTouched = true;
            if (gameplayCategoryWrap) gameplayCategoryWrap.style.display = s.splitScreen ? 'block' : 'none';
        }
        if (s.gameplayCategory && selectGameplayCategory) {
            selectGameplayCategory.value = s.gameplayCategory;
        }
        if (s.antiDuplicate !== undefined && chkAntiDuplicate) {
            chkAntiDuplicate.checked = !!s.antiDuplicate;
        }
        if (s.kenBurns !== undefined && chkKenBurns) {
            chkKenBurns.checked = !!s.kenBurns;
        }
        if (s.zoompan !== undefined && chkZoompan) {
            chkZoompan.checked = !!s.zoompan;
        }
        if (s.brollInsert !== undefined && chkBrollInsert) {
            chkBrollInsert.checked = !!s.brollInsert;
        }
        if (s.centerFace !== undefined && chkCenterFace) {
            chkCenterFace.checked = !!s.centerFace;
        }
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

function updateTimelineTopicDesc(plan) {
    const descEl = document.getElementById('timeline-project-desc');
    if (!descEl) return;
    const raw = (inputTopic?.value || plan?.title || '').trim();
    const clean = sanitizeTopicTitleForDisplay(raw);
    if (raw && clean && raw !== clean) {
        descEl.textContent = `Konu: ${clean}`;
    } else {
        descEl.textContent = 'Her sahnenin metnini, süresini, arama terimlerini ve mood\'unu özelleştirin.';
    }
}

function persistCurrentPlan() {
    try {
        if (currentPlan && Array.isArray(currentPlan.scenes) && currentPlan.scenes.length) {
            localStorage.setItem(PLAN_STORAGE_KEY, JSON.stringify({
                planVersion: PLAN_SCHEMA_VERSION,
                plan: currentPlan,
                topic: inputTopic?.value || '',
                niche: selectNiche?.value || '',
                savedAt: Date.now()
            }));
        }
        saveStudioSettings();
    } catch (e) {}
}

function restoreCurrentPlan() {
    try {
        const raw = localStorage.getItem(PLAN_STORAGE_KEY);
        if (!raw) return false;
        const packed = JSON.parse(raw);
        if (packed?.scenes?.length && !packed?.plan) {
            try { localStorage.removeItem(PLAN_STORAGE_KEY); } catch (e) {}
            showToast('Eski senaryo formatı temizlendi — yeniden üretin', 'warn');
            return false;
        }
        if (!packed?.plan?.scenes?.length) return false;
        // Expire after 7 days
        if (packed.savedAt && Date.now() - packed.savedAt > 7 * 864e5) {
            try { localStorage.removeItem(PLAN_STORAGE_KEY); } catch (e) {}
            return false;
        }
        if (packed.planVersion !== PLAN_SCHEMA_VERSION) {
            try { localStorage.removeItem(PLAN_STORAGE_KEY); } catch (e) {}
            showToast('Eski senaryo sürümü temizlendi — yeniden üretin', 'warn');
            return false;
        }
        if (planHasBrokenNarration(packed.plan)) {
            try { localStorage.removeItem(PLAN_STORAGE_KEY); } catch (e) {}
            showToast('Bozuk senaryo temizlendi — yeniden üretin', 'warn');
            return false;
        }
        currentPlan = packed.plan;
        if (packed.topic && inputTopic && (!inputTopic.value.trim() || inputTopic.value.includes('Marcus Aurelius'))) {
            inputTopic.value = packed.topic;
        }
        if (packed.niche && selectNiche) selectNiche.value = packed.niche;
        return true;
    } catch (e) {
        return false;
    }
}

function setCurrentPlan(plan, opts = {}) {
    currentPlan = plan;
    if (plan) {
        if (opts.renderTimeline !== false && typeof renderTimelineScenes === 'function') {
            try { renderTimelineScenes(plan); } catch (_) {}
        }
        persistCurrentPlan();
        updateFlowRail('timeline');
        if (!opts.skipQualityPanel) {
            updateStudioQualityPanel(plan).catch(() => {});
        }
    }
    updateScriptActionButtons();
    try {
        window.dispatchEvent(new CustomEvent('shorts:planChanged', { detail: { plan, opts } }));
    } catch (_) {}
}

function hasExistingPlan() {
    return !!(currentPlan?.scenes?.length);
}

function navigateToScenario({ silent = false } = {}) {
    if (!hasExistingPlan()) {
        showToast('Once senaryo olusturun', 'warn');
        return false;
    }
    renderTimelineScenes(currentPlan);
    updateFlowRail('timeline');
    switchTab('timeline');
    if (!silent) showToast('Senaryo acildi — duzenleyip render alabilirsiniz');
    return true;
}

function clearCurrentScenario() {
    if (!hasExistingPlan()) {
        inputTopic?.focus();
        return;
    }
    if (!confirm('Mevcut senaryo silinecek. Yeni konu ile devam edilsin mi?')) return;

    currentPlan = null;
    timelineReviewed = false;
    qualityPanelGreen = false;
    try { localStorage.removeItem(PLAN_STORAGE_KEY); } catch (e) {}
    renderTimelineScenes({ title: '', scenes: [] });
    updateStudioQualityPanel(null).catch(() => {});
    updateFlowRail('topic');
    updateScriptActionButtons();
    saveStudioSettings();
    inputTopic?.focus();
    showToast('Senaryo temizlendi — yeni konu girin');
}

function updateScriptActionButtons() {
    const btn = document.getElementById('btn-create-script');
    const btnNewTopic = document.getElementById('btn-new-topic');
    const btnRegenerateStudio = document.getElementById('btn-regenerate-script-studio');
    const btnRegenerateTimeline = document.getElementById('btn-regenerate-scenario');
    if (!btn) return;

    const ready = hasExistingPlan();
    const currentTopic = (inputTopic?.value || '').trim();
    const planTopic = (currentPlan?.title || currentPlan?.topic || currentPlan?.keyword || '').trim();
    const topicChanged = ready && currentTopic && planTopic && (currentTopic.toLowerCase() !== planTopic.toLowerCase());

    btnNewTopic?.classList.toggle('hidden', !ready);
    btnRegenerateStudio?.classList.toggle('hidden', !ready);
    btnRegenerateTimeline?.classList.toggle('hidden', !ready);

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
    } else {
        btn.className = 'btn btn-secondary btn-lg';
        btn.innerHTML = '<i class="fa-solid fa-wand-magic-sparkles"></i><span id="btn-create-script-label">1. Senaryoyu İncele & Düzenle</span>';
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

async function updateStudioQualityPanel(plan, { silent = false } = {}) {
    const panel = document.getElementById('studio-quality-panel');
    const badge = document.getElementById('sqp-status-badge');
    const issuesEl = document.getElementById('sqp-issues');
    const advisoryGroup = document.getElementById('sqp-advisory-group');
    const advisoriesEl = document.getElementById('sqp-advisories');
    if (!panel || !badge) return { ok: false, issues: ['Panel yok'] };

    if (!plan?.scenes?.length) {
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
        updateRenderButtonsBlocked(true, scriptQuality.issues?.[0] || 'Once senaryo olusturun');
        return { ok: false, issues: scriptQuality.issues || ['Senaryo yok'], script_quality: scriptQuality, hard_fail: scriptHardFail };
    }

    const scenes = plan.scenes;
    const totalSec = scenes.reduce((acc, s) => acc + (parseFloat(s.duration) || 6), 0);
    const totalWords = scenes.reduce((acc, s) => acc + wordCount(cleanNarration(s.narration)), 0);
    const queries = scenes.map(s => ((s.search_queries || [])[0] || '').toLowerCase().trim()).filter(Boolean);
    const uniqueClips = new Set(queries).size;
    const dupes = queries.length - uniqueClips;

    const cadenceOk = scenes.length >= 8 && scenes.length <= 16;
    setSqpPill('sqp-cadence', `Cadence: ${scenes.length} sahne`, cadenceOk ? 'ok' : (scenes.length >= 6 ? 'warn' : 'fail'));
    setSqpPill('sqp-words', `Kelime: ${totalWords}`, totalWords >= 70 ? 'ok' : (totalWords >= 50 ? 'warn' : 'fail'));
    setSqpPill('sqp-duration', `Sure: ${totalSec.toFixed(1)}sn`, totalSec >= 38 && totalSec <= 60 ? 'ok' : 'warn');
    setSqpPill('sqp-clips', `Klip: ${uniqueClips}/${scenes.length}`, dupes === 0 ? 'ok' : 'warn');

    badge.className = 'sqp-status-badge warn';
    badge.textContent = 'Dogrulaniyor...';

    const validation = await validatePlanViaApi(plan, { autoRepair: true });
    const continuityAdvisories = Array.isArray(validation.scene_continuity_advisories)
        ? validation.scene_continuity_advisories
        : [];
    if (advisoryGroup && advisoriesEl) {
        advisoriesEl.replaceChildren();
        continuityAdvisories.forEach(advisory => {
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
        if (activePlan !== currentPlan) {
            currentPlan = activePlan;
            persistCurrentPlan();
            if (typeof renderTimelineScenes === 'function') {
                try { renderTimelineScenes(activePlan); } catch (_) {}
            }
        }
    }

    if (validation.repaired && validation.fixes?.length && !silent) {
        showToast('Anlatim otomatik duzeltildi');
    }

    const narrOk = validation.ok;
    setSqpPill('sqp-narration', narrOk ? 'Anlatim: OK' : 'Anlatim: SORUN', narrOk ? 'ok' : 'fail');

    // Human-craft / discovery beast (anti AI-slop)
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

    const scriptQuality = activePlan.meta?.script_quality || {};
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

    return { ...validation, script_quality: scriptQuality, hard_fail: scriptHardFail };
}

function applyPlagiarismBadge(plagiarism) {
    const btnForce = document.getElementById('btn-force-similar-script');
    const chkAllow = document.getElementById('chk-allow-similar-script');
    const isBypass = !!(chkAllow && chkAllow.checked);

    if (!plagiarism) {
        setSqpPill('sqp-plagiarism', 'Özgünlük: —', 'neutral');
        if (btnForce) btnForce.classList.add('hidden');
        return;
    }
    const pct = plagiarism.similarity_pct ?? 0;
    const backendApproved = plagiarism.approved !== false;
    const ok = backendApproved || isBypass;

    if (btnForce) {
        if (!backendApproved && !isBypass) {
            btnForce.classList.remove('hidden');
            btnForce.onclick = () => {
                if (chkAllow) chkAllow.checked = true;
                btnForce.classList.add('hidden');
                applyPlagiarismBadge(plagiarism);
                updateRenderButtonsBlocked(false);
                if (typeof showToast === 'function') {
                    showToast('Benzerlik eşiği yok sayıldı. Render açıldı.', 'success');
                }
            };
        } else {
            btnForce.classList.add('hidden');
        }
    }

    if (isBypass && !backendApproved) {
        setSqpPill(
            'sqp-plagiarism',
            `Benzerlik: %${pct} (Atlandı)`,
            'warn'
        );
    } else {
        setSqpPill(
            'sqp-plagiarism',
            ok ? `Özgünlük: %${pct}` : `İntihal riski: %${pct}`,
            ok ? (pct <= 25 ? 'ok' : 'warn') : 'fail'
        );
    }
}

const QG_ISSUE_ROADMAP = {
    post_duration_band: 494,
    av_delta: 452,
    duplicate_shots: 247,
    duplicate_content_hash: 247,
    duplicate_paths: 247,
    missing_output: 452,
    file_too_small: 452,
    low_resolution_test_mode: 129,
    fragment: 494,
    low_words: 494,
    empty_narration: 494,
    no_terminal: 494,
};

function roadmapItemForIssue(issue) {
    const text = String(issue || '').toLowerCase();
    const key = String(issue || '').split('_').slice(0, 2).join('_');
    if (QG_ISSUE_ROADMAP[issue]) return QG_ISSUE_ROADMAP[issue];
    if (QG_ISSUE_ROADMAP[key]) return QG_ISSUE_ROADMAP[key];
    if (String(issue).startsWith('av_delta')) return 452;
    if (String(issue).startsWith('fragment')) return 494;
    if (String(issue).startsWith('low_words')) return 494;
    if (/cadence|sahne/.test(text)) return 88;
    if (/3\.2|3,2/.test(text)) return 76;
    if (/sure|süre|duration|494|kelime|anlatim|anlatım|fragment/.test(text)) return 494;
    if (/duplicate|tekrar|klip/.test(text)) return 247;
    if (/hook|kanca/.test(text)) return 201;
    return null;
}

function formatQualityIssueWithRoadmap(issue) {
    const madde = roadmapItemForIssue(issue);
    const link = madde
        ? ` <a href="#" class="qg-roadmap-link" data-roadmap-item="${madde}">Madde #${madde}</a>`
        : '';
    return `${escapeHtml(issue)}${link}`;
}

function openRoadmapDeepLink(itemNum) {
    switchTab('roadmap500');
    const searchEl = document.getElementById('input-roadmap-search');
    if (searchEl) {
        searchEl.value = String(itemNum);
        renderFilteredRoadmap();
    }
}

function formatQualityGateIssue(issue) {
    if (!issue) return '';
    if (issue.startsWith('av_delta_')) {
        const delta = parseFloat(issue.replace('av_delta_', '')) || 0;
        return `Ses-Görüntü Senkronizasyonu (Fark: ${delta.toFixed(3)}s)`;
    }
    const map = {
        'low_resolution_test_mode': 'Hızlı Test Çözünürlüğü Modu (540p / 720p)',
        'post_duration_band': 'Hedef Süre Toleransı',
        'duplicate_shots': 'Tekrarlayan Görsel Sahne',
        'duplicate_content_hash': 'İçerik Parmak İzi Çakışması',
        'missing_output': 'Çıktı Dosyası Eksik',
        'file_too_small': 'Video Dosya Boyutu Düşük',
        'fragment_sentence_full': 'Cümle Bitişi Akıcılığı',
    };
    return map[issue] || issue.replace(/_/g, ' ');
}

function renderQualityGateCard(qg, { compact = false } = {}) {
    if (!qg) return '';
    const post = qg.post || qg;
    const ok = post.ok !== false;
    const score = post.score != null ? post.score : (qg.score != null ? qg.score : '—');
    const dur = post.video_duration != null
        ? `${Number(post.video_duration).toFixed(1)}sn`
        : (qg.duration != null ? `${Number(qg.duration).toFixed(1)}sn` : '—');
    const issues = post.issues || qg.issues || [];
    const statusClass = ok ? 'qg-ok' : 'qg-fail';
    const statusText = ok ? 'GEÇTİ' : 'RED';
    if (compact) {
        const issueHint = issues.length ? ` · ${escapeHtml(issues.slice(0, 2).map(formatQualityGateIssue).join('; '))}` : '';
        return `<span class="gallery-qg-badge ${ok ? 'is-ok' : 'is-fail'}">${statusText} · skor ${score}${issueHint}</span>`;
    }
    const issueHtml = issues.length
        ? `<ul class="studio-qg-issues">${issues.map(i => {
            const madde = roadmapItemForIssue(i);
            const link = madde
                ? ` <a href="#" class="qg-roadmap-link" data-roadmap-item="${madde}">Madde #${madde}</a>`
                : '';
            return `<li>${escapeHtml(formatQualityGateIssue(i))}${link}</li>`;
        }).join('')}</ul>`
        : '<span class="studio-qg-clean">Sorun yok</span>';
    return `
        <div class="studio-qg-card ${ok ? '' : 'is-fail'}">
            <strong class="${statusClass}">Kalite Kapısı: ${statusText}</strong>
            <span class="studio-qg-meta">skor ${score} · süre ${dur}</span>
            ${issueHtml}
        </div>`;
}

document.addEventListener('click', (e) => {
    const link = e.target.closest('.qg-roadmap-link');
    if (!link) return;
    e.preventDefault();
    const itemNum = parseInt(link.getAttribute('data-roadmap-item'), 10);
    if (itemNum) openRoadmapDeepLink(itemNum);
});

const NARRATION_DANGLING = new Set([
    've', 'ama', 'cunku', 'çünkü', 'icin', 'için', 'ise', 'senin', 'kendi', 'olan', 'asla',
    'onlara', 'degil', 'değil', 'kusuru', 'bozan', 'ruhunu', 'imparator', 'kaleni', 'ic', 'iç',
    'en', 'ust', 'üst', 'kural', 'her', 'sey', 'şey', 'fani', 'marcus'
]);

function normalizeNarrationForValidation(text) {
    if (!text) return '';
    let t = String(text).trim();
    t = t.replace(/\*\*(?:URGENT|DRAMATIC|EPIC|CALM|MYSTERIOUS|ENERGETIC|DARK|BRIGHT|SECRET|WARNING|HOOK|CTA)\*\*\s*/gi, '');
    t = t.replace(/\*\*([^*]+)\*\*/g, '$1').replace(/\*([^*]+)\*/g, '$1');
    t = t.replace(/[\u{10000}-\u{10FFFF}]/gu, '');
    t = t.replace(/[\u2600-\u27BF\uFE00-\uFE0F]/gu, '');
    t = t.replace(/[#*_~^\\/|<>@=`\[\]{}]/g, ' ');
    t = t.replace(/([.!?])\s*[^\w\s\u00C0-\u024F\u1E00-\u1EFF]+\s*$/u, '$1');
    if (t && !/[.!?]$/.test(t) && /[.!?]/.test(t)) {
        const m = t.match(/^(.*[.!?])/);
        if (m) t = m[1];
    }
    return t.replace(/\s+/g, ' ').trim();
}

function getNarrationIssues(scenes) {
    const hard = [];
    if (!scenes || !scenes.length) return hard;
    (scenes || []).forEach((sc, i) => {
        const raw = (sc.narration || '').trim();
        if (!raw) {
            hard.push(`Sahne ${i + 1}: bos anlatim`);
            return;
        }
        const narr = normalizeNarrationForValidation(raw);
        const words = narr.split(/\s+/).filter(Boolean);
        if (words.length < 10) {
            hard.push(`Sahne ${i + 1}: cok kisa (${words.length} kelime, min 10)`);
        }
        if (!/[.!?]$/.test(narr)) {
            hard.push(`Sahne ${i + 1}: cumle noktalama ile bitmiyor`);
        }
        const tail = (words[words.length - 1] || '').toLowerCase().replace(/[.,!?;:]+$/, '');
        if (NARRATION_DANGLING.has(tail)) {
            hard.push(`Sahne ${i + 1}: kopuk cumle ('${tail}' ile bitiyor)`);
        }
        const sentences = narr.split(/(?<=[.!?])\s+/).filter(Boolean);
        if (sentences.length === 1) {
            const sw = sentences[0].trim().split(/\s+/).filter(Boolean);
            if (sw.length > 0 && sw.length < 4 && /[.!?]$/.test(sentences[0].trim())) {
                hard.push(`Sahne ${i + 1}: parca cumle (${sw.length} kelime)`);
            }
        } else if (sentences.length > 1) {
            const last = sentences[sentences.length - 1].trim();
            const sw = last.split(/\s+/).filter(Boolean);
            if (sw.length > 0 && sw.length < 4 && /[.!?]$/.test(last)) {
                hard.push(`Sahne ${i + 1}: parca cumle (${sw.length} kelime)`);
            }
        }
    });
    return hard;
}

function parseApiError(res, data, fallback) {
    if (res.status === 404) {
        return 'API endpoint eksik — sunucuyu yeniden baslatin';
    }
    const detail = data?.detail;
    if (typeof detail === 'string') {
        if (detail === 'Not Found') {
            return 'API endpoint eksik — sunucuyu yeniden baslatin';
        }
        return detail;
    }
    if (Array.isArray(detail)) {
        return detail.map(d => d.msg || d).join('; ');
    }
    if (detail && typeof detail === 'object' && detail.message) {
        return String(detail.message);
    }
    return fallback || `Sunucu hatasi (${res.status})`;
}

function collectValidationIssues(data, outPlan, fallbackPlan) {
    const integrity = data.narration_integrity || [];
    const preIssues = (data.pre_render_score?.issues || []).filter(i =>
        i.startsWith('fragment') || i.startsWith('low_words')
        || i.startsWith('empty_narration') || i.startsWith('no_terminal')
    );
    const serverIssues = [
        ...integrity.map(i => `Sunucu: ${i}`),
        ...preIssues.map(i => `Sunucu: ${i}`)
    ];
    const localIssues = getNarrationIssues((outPlan || fallbackPlan)?.scenes || []);
    const issues = serverIssues.length ? serverIssues : localIssues;
    return [...new Set(issues.length ? issues : ['Anlatim kalite kapisi reddetti'])];
}

async function postPlanGate(path, plan, { autoRepair = true } = {}) {
    const payload = {
        plan,
        title: plan.title || inputTopic?.value?.trim() || '',
        niche: selectNiche?.value || plan.niche_id || '1_news_flash',
        language: selectLanguage?.value || 'tr',
        recompile: true,
        auto_repair: autoRepair
    };
    const res = await fetch(path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    let data = {};
    try {
        data = await res.json();
    } catch (_) {
        data = {};
    }
    if (!res.ok) {
        return {
            ok: false,
            issues: [parseApiError(res, data, 'Dogrulama basarisiz')],
            plan,
            repaired: false,
            fixes: [],
            scene_continuity_advisories: []
        };
    }
    const responsePlan = data.plan || plan;
    const outPlan = responsePlan === plan
        ? plan
        : { ...responsePlan, meta: { ...(plan.meta || {}), ...(responsePlan.meta || {}) } };
    if (data.ok) {
        return {
            ok: true,
            issues: [],
            plan: outPlan,
            repaired: !!data.repaired,
            fixes: data.fixes || [],
            pre_render_score: data.pre_render_score,
            scene_continuity_advisories: data.scene_continuity_advisories || []
        };
    }
    return {
        ok: false,
        issues: collectValidationIssues(data, outPlan, plan),
        plan: outPlan,
        repaired: !!data.repaired,
        fixes: data.fixes || [],
        pre_render_score: data.pre_render_score,
        scene_continuity_advisories: data.scene_continuity_advisories || []
    };
}

async function validatePlanViaApi(plan, { autoRepair = true } = {}) {
    if (!plan?.scenes?.length) return { ok: false, issues: ['Senaryo yok'] };
    try {
        let result = await postPlanGate('/api/plan/validate', plan, { autoRepair });
        if (!result.ok && autoRepair && !result.issues.some(i => i.includes('endpoint eksik'))) {
            const repairResult = await postPlanGate('/api/plan/repair', result.plan || plan, { autoRepair: false });
            if (repairResult.ok) {
                return {
                    ...repairResult,
                    repaired: true,
                    fixes: [...(result.fixes || []), ...(repairResult.fixes || [])],
                    scene_continuity_advisories: repairResult.scene_continuity_advisories || result.scene_continuity_advisories || []
                };
            }
            if (repairResult.repaired || repairResult.fixes?.length) {
                result = {
                    ...repairResult,
                    repaired: true,
                    fixes: [...(result.fixes || []), ...(repairResult.fixes || [])],
                    scene_continuity_advisories: repairResult.scene_continuity_advisories || result.scene_continuity_advisories || []
                };
            } else if (repairResult.issues?.length) {
                result = {
                    ...result,
                    issues: repairResult.issues,
                    plan: repairResult.plan || result.plan
                };
            }
        }
        return result;
    } catch (e) {
        return { ok: false, issues: getNarrationIssues(plan.scenes) };
    }
}

function updateRenderButtonsBlocked(blocked, reason) {
    const scriptQuality = currentPlan?.meta?.script_quality || {};
    const scriptHardFail = scriptQuality.hard_fail === true;
    blocked = !!blocked || scriptHardFail;
    if (scriptHardFail) reason = scriptQuality.issues?.[0] || reason;
    const btns = [
        document.getElementById('btn-render-from-timeline'),
        document.getElementById('btn-quick-render')
    ].filter(Boolean);
    btns.forEach(btn => {
        btn.disabled = !!blocked;
        btn.title = blocked ? (reason || 'Kopuk anlatim — once senaryoyu duzeltin') : '';
        btn.classList.toggle('render-blocked', !!blocked);
    });
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
    if (scenes.length < 8 || scenes.length > 16) {
        soft.push(`Cadence: ${scenes.length} sahne (izin 8-16)`);
    }
    const longCuts = timedScenes.filter(s => sceneDurationSec(s) > 3.2).length;
    if (longCuts > 3) {
        soft.push(`${longCuts} sahne 3.2sn ustu`);
    }
    const hard = getNarrationIssues(scenes);
    return { hard, soft };
}

function updateFlowRail(activeStep) {
    const rail = document.getElementById('studio-flow-rail');
    if (!rail) return;
    rail.querySelectorAll('[data-flow]').forEach(el => {
        const step = el.getAttribute('data-flow');
        el.classList.toggle('is-active', step === activeStep);
        el.classList.toggle('is-done', (
            (activeStep === 'timeline' && step === 'topic') ||
            (activeStep === 'render' && (step === 'topic' || step === 'timeline')) ||
            (activeStep === 'seo' && step !== 'seo')
        ));
    });
}

function setPendingFormatFingerprint(fp) {
    pendingFormatFingerprint = fp && typeof fp === 'object' ? fp : null;
}

function clearPendingFormatFingerprint() {
    pendingFormatFingerprint = null;
    trendFormatFingerprintAggregate = null;
}

function sceneDurationSec(scene) {
    const d = parseFloat(scene?.duration);
    return Number.isFinite(d) && d > 0 ? d : null;
}

function isRedditNiche(nicheId) {
    return Boolean(nicheId && (nicheId.includes('reddit') || nicheId === '2_reddit_confessions'));
}

function isNewsNiche(nicheId) {
    return Boolean(nicheId && (nicheId.includes('news') || nicheId === '1_news_flash'));
}

function isWhatsappNiche(nicheId) {
    return Boolean(nicheId && nicheId.includes('whatsapp'));
}

function getNicheFamily(nicheId) {
    const hit = allNiches.find(n => n.id === nicheId);
    if (hit?.niche_family) return hit.niche_family;
    if (isNewsNiche(nicheId)) return 'news';
    if (isRedditNiche(nicheId)) return 'reddit';
    if (isWhatsappNiche(nicheId)) return 'whatsapp';
    if (nicheId && (nicheId.includes('stoic') || nicheId === '6_stoic_philosophy' || nicheId === '24_sigma_character_study')) return 'stoic';
    return 'general';
}

function panelMatchesFamily(widgetFamilies, nicheFamily) {
    const allowed = (widgetFamilies || '').trim().split(/\s+/).filter(Boolean);
    if (!allowed.length || allowed.includes('all') || allowed.includes('general')) return true;
    if (nicheFamily === 'general') return allowed.includes('general');
    return allowed.includes(nicheFamily);
}

function applyNichePanelVisibility(nicheId) {
    const family = getNicheFamily(nicheId);
    document.querySelectorAll('[data-niche-family]').forEach(el => {
        const families = el.getAttribute('data-niche-family') || '';
        const show = panelMatchesFamily(families, family);
        el.style.display = show ? '' : 'none';
        if (!show && el.id === 'niche-trends-results') el.style.display = 'none';
    });
    if (!isRedditNiche(nicheId)) selectedRedditPost = null;
}

function showNicheLockBadge(nicheId, nicheName) {
    const badge = document.getElementById('niche-lock-badge');
    const label = document.getElementById('niche-lock-label');
    if (!badge || !label) return;
    lockedNicheId = nicheId || null;
    if (!nicheId) {
        badge.classList.add('hidden');
        label.textContent = '—';
        return;
    }
    const name = nicheName || allNiches.find(n => n.id === nicheId)?.name || nicheId;
    label.textContent = name;
    badge.classList.remove('hidden');
}

function resetComplianceDashboard() {
    const chipDur = document.getElementById('chip-duration-band');
    const chipCad = document.getElementById('chip-cadence');
    const chip32 = document.getElementById('chip-32s-violations');
    const chipDup = document.getElementById('chip-duplicates');
    if (chipDur) {
        chipDur.className = 'compliance-chip';
        const t = document.getElementById('chip-duration-text');
        if (t) t.textContent = 'Süre: —';
    }
    if (chipCad) {
        chipCad.className = 'compliance-chip';
        const t = document.getElementById('chip-cadence-text');
        if (t) t.textContent = 'Cadence: —';
    }
    if (chip32) {
        chip32.className = 'compliance-chip status-ok';
        const t = document.getElementById('chip-32s-text');
        if (t) t.textContent = '3.2sn Uyarı: 0';
    }
    if (chipDup) {
        chipDup.className = 'compliance-chip status-ok';
        const t = document.getElementById('chip-duplicates-text');
        if (t) t.textContent = 'Tekrar: 0';
    }
}



function showToast(msg, type = 'success') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = 'toast';
    const icon = type === 'error'
        ? 'fa-circle-xmark text-danger'
        : (type === 'warning' || type === 'warn')
            ? 'fa-triangle-exclamation text-warning'
            : 'fa-circle-check text-primary';
    toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${msg}</span>`;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(-10px)';
        toast.style.transition = 'all 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3500);
}



function escapeHtml(value) {
    const element = document.createElement('div');
    element.textContent = String(value || '');
    return element.innerHTML;
}

const TOPIC_SOURCE_LABELS = {
    youtube: { label: 'YouTube', icon: 'fa-brands fa-youtube', cls: 'youtube' },
    ai: { label: 'AI', icon: 'fa-solid fa-wand-magic-sparkles', cls: 'ai' },
    trend: { label: 'Trend', icon: 'fa-solid fa-chart-line', cls: 'trend' },
    reddit: { label: 'Reddit', icon: 'fa-brands fa-reddit-alien', cls: 'reddit' },
};


// Initialize DOM bindings on file load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDomElements);
} else {
    initDomElements();
}
