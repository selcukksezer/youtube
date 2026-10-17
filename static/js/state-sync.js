/**
 * ShortsAI Studio — State Synchronization & Persistence Helpers (state-sync.js)
 * Handles form-to-state and state-to-form synchronization, localStorage persistence, and plan validation.
 */

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
        return words.length < 5;
    });
}

function saveStudioSettings() {
    try {
        const settings = {
            topic: (window.inputTopic?.value || '').trim(),
            niche: window.selectNiche?.value || '',
            subtitlePreset: window.selectSubPreset?.value || '',
            language: window.selectLanguage?.value || '',
            ttsVoice: window.selectTtsVoice?.value || '',
            bgmTrack: document.getElementById('studio-bgm-track')?.value || '',
            resolution: document.getElementById('select-render-resolution')?.value || '',
            safeMode: document.getElementById('select-studio-safe-mode')?.value || '',
            contentGaps: document.getElementById('content-gap-topics')?.value || '',
            splitScreen: window.chkSplitScreen ? !!window.chkSplitScreen.checked : false,
            gameplayCategory: window.selectGameplayCategory?.value || '',
            antiDuplicate: window.chkAntiDuplicate ? !!window.chkAntiDuplicate.checked : true,
            kenBurns: window.chkKenBurns ? !!window.chkKenBurns.checked : true,
            zoompan: window.chkZoompan ? !!window.chkZoompan.checked : false,
            brollInsert: window.chkBrollInsert ? !!window.chkBrollInsert.checked : false,
            centerFace: window.chkCenterFace ? !!window.chkCenterFace.checked : false,
            emphasisCard: (window.chkEmphasisCard ? !!window.chkEmphasisCard.checked : (window.chkEmphasisCardLab ? !!window.chkEmphasisCardLab.checked : false)),
            enableBgm: document.getElementById('chk-enable-bgm')
                ? !!document.getElementById('chk-enable-bgm').checked
                : true,
            enableOutro: document.getElementById('chk-enable-outro')
                ? !!document.getElementById('chk-enable-outro').checked
                : true,
            introWhoosh: !!document.getElementById('chk-intro-whoosh')?.checked,
            userManuallyPickedNiche: !!window.userManuallyPickedNiche,
            savedAt: Date.now()
        };
        localStorage.setItem(STUDIO_SETTINGS_STORAGE_KEY, JSON.stringify(settings));
    } catch (e) {}
}

function updateTimelineTopicDesc(plan) {
    const descEl = document.getElementById('tl-project-topic-title') || document.getElementById('timeline-project-desc') || document.getElementById('tl-project-title');
    if (!descEl) return;
    const raw = (window.inputTopic?.value || plan?.title || '').trim();
    const clean = sanitizeTopicTitleForDisplay(raw);
    if (raw && clean && raw !== clean) {
        descEl.textContent = `Konu: ${clean}`;
    } else if (clean) {
        descEl.textContent = clean;
    } else {
        descEl.textContent = 'Her sahnenin metnini, süresini, arama terimlerini ve mood\'unu özelleştirin.';
    }
}

function persistCurrentPlan() {
    try {
        if (window.currentPlan && Array.isArray(window.currentPlan.scenes) && window.currentPlan.scenes.length) {
            localStorage.setItem(PLAN_STORAGE_KEY, JSON.stringify({
                planVersion: PLAN_SCHEMA_VERSION,
                plan: window.currentPlan,
                topic: window.inputTopic?.value || '',
                niche: window.selectNiche?.value || '',
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
        window.currentPlan = packed.plan;
        if (packed.topic && window.inputTopic && (!window.inputTopic.value.trim() || window.inputTopic.value.includes('Marcus Aurelius'))) {
            window.inputTopic.value = packed.topic;
        }
        if (packed.niche && window.selectNiche) window.selectNiche.value = packed.niche;
        return true;
    } catch (e) {
        return false;
    }
}

function setCurrentPlan(plan, opts = {}) {
    window.currentPlan = plan;
    if (plan) {
        if (opts.renderTimeline !== false && typeof renderTimelineScenes === 'function') {
            try { renderTimelineScenes(plan); } catch (_) {}
        }
        persistCurrentPlan();
        updateFlowRail('timeline');
        if (!opts.skipQualityPanel && typeof updateStudioQualityPanel === 'function') {
            updateStudioQualityPanel(plan).catch(() => {});
        }
    }
    if (typeof updateScriptActionButtons === 'function') updateScriptActionButtons();
    try {
        window.dispatchEvent(new CustomEvent('shorts:planChanged', { detail: { plan, opts } }));
    } catch (_) {}
}

function hasExistingPlan() {
    return !!(window.currentPlan?.scenes?.length);
}

function navigateToScenario({ silent = false } = {}) {
    if (!hasExistingPlan()) {
        showToast('Once senaryo olusturun', 'warn');
        return false;
    }
    if (typeof renderTimelineScenes === 'function') renderTimelineScenes(window.currentPlan);
    updateFlowRail('timeline');
    if (typeof switchTab === 'function') switchTab('timeline');
    if (!silent) showToast('Senaryo acildi — duzenleyip render alabilirsiniz');
    return true;
}

function clearCurrentScenario() {
    if (!hasExistingPlan()) {
        window.inputTopic?.focus();
        return;
    }
    if (!confirm('Mevcut senaryo silinecek. Yeni konu ile devam edilsin mi?')) return;

    window.currentPlan = null;
    window.timelineReviewed = false;
    window.qualityPanelGreen = false;
    try { localStorage.removeItem(PLAN_STORAGE_KEY); } catch (e) {}
    if (typeof renderTimelineScenes === 'function') renderTimelineScenes({ title: '', scenes: [] });
    if (typeof updateStudioQualityPanel === 'function') updateStudioQualityPanel(null).catch(() => {});
    updateFlowRail('topic');
    if (typeof updateScriptActionButtons === 'function') updateScriptActionButtons();
    saveStudioSettings();
    window.inputTopic?.focus();
    showToast('Senaryo temizlendi — yeni konu girin');
}

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
        title: plan.title || window.inputTopic?.value?.trim() || '',
        niche: window.selectNiche?.value || plan.niche_id || '1_news_flash',
        language: window.selectLanguage?.value || 'tr',
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
            scene_continuity_advisories: data.scene_continuity_advisories || [],
            script_quality: data.script_quality || {},
            narration_ok: data.narration_ok ?? data.ok,
            quality_repair: data.quality_repair
        };
    }
    return {
        ok: false,
        issues: collectValidationIssues(data, outPlan, plan),
        plan: outPlan,
        repaired: !!data.repaired,
        fixes: data.fixes || [],
        pre_render_score: data.pre_render_score,
        scene_continuity_advisories: data.scene_continuity_advisories || [],
        script_quality: data.script_quality || {},
        narration_ok: data.narration_ok ?? data.ok,
        quality_repair: data.quality_repair
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
                    quality_repair: result.quality_repair || repairResult.quality_repair,
                    repaired: true,
                    fixes: [...(result.fixes || []), ...(repairResult.fixes || [])],
                    scene_continuity_advisories: repairResult.scene_continuity_advisories || result.scene_continuity_advisories || []
                };
            }
            if (repairResult.repaired || repairResult.fixes?.length) {
                result = {
                    ...repairResult,
                    quality_repair: result.quality_repair || repairResult.quality_repair,
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
        setSqpPill('sqp-plagiarism', `Benzerlik: %${pct} (Atlandı)`, 'warn');
    } else {
        setSqpPill(
            'sqp-plagiarism',
            ok ? `Özgünlük: %${pct}` : `İntihal riski: %${pct}`,
            ok ? (pct <= 25 ? 'ok' : 'warn') : 'fail'
        );
    }
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
    window.pendingFormatFingerprint = fp && typeof fp === 'object' ? fp : null;
}

function clearPendingFormatFingerprint() {
    window.pendingFormatFingerprint = null;
    window.trendFormatFingerprintAggregate = null;
}

function sceneDurationSec(scene) {
    const d = parseFloat(scene?.duration);
    return Number.isFinite(d) && d > 0 ? d : null;
}
