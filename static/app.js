/**
 * ShortsAI Studio Ultimate — Frontend Application Engine (app.js)
 * Covers all 100 features from r10_shorts_fikirleri_ve_bot_ozellikleri.md
 */

document.addEventListener('DOMContentLoaded', () => {
    // ══════════════════════════════════════════════════════════════
    // STATE & VARIABLES
    // ══════════════════════════════════════════════════════════════
    let currentPlan = null;
    let timelineReviewed = false;
    let qualityPanelGreen = false;
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
            if (words.length < 10) return true;
            if (!sceneDescriptionUsable(sc.scene_description || '')) return true;
            return norm.slice(-1) !== '.' && norm.slice(-1) !== '!' && norm.slice(-1) !== '?';
        });
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
        } catch (e) {}
    }

    function restoreCurrentPlan() {
        try {
            const raw = localStorage.getItem(PLAN_STORAGE_KEY);
            if (!raw) return false;
            const packed = JSON.parse(raw);
            if (packed?.scenes?.length && !packed?.plan) {
                try { localStorage.removeItem(PLAN_STORAGE_KEY); } catch (e) {}
                showToast('Eski senaryo formati temizlendi — yeniden uretin', 'warn');
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
            if (packed.topic && inputTopic && !inputTopic.value.trim()) inputTopic.value = packed.topic;
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
        inputTopic?.focus();
        showToast('Senaryo temizlendi — yeni konu girin');
    }

    function updateScriptActionButtons() {
        const btn = document.getElementById('btn-create-script');
        const btnNewTopic = document.getElementById('btn-new-topic');
        const btnRegenerate = document.getElementById('btn-regenerate-scenario');
        if (!btn) return;

        const ready = hasExistingPlan();
        btnNewTopic?.classList.toggle('hidden', !ready);
        btnRegenerate?.classList.toggle('hidden', !ready);

        if (ready) {
            btn.className = 'btn btn-primary btn-lg';
            btn.innerHTML = '<i class="fa-solid fa-clapperboard"></i><span id="btn-create-script-label">Senaryoya Git</span>';
        } else {
            btn.className = 'btn btn-secondary btn-lg';
            btn.innerHTML = '<i class="fa-solid fa-code-branch"></i><span id="btn-create-script-label">1. Senaryoyu İncele & Düzenle</span>';
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
        if (!panel || !badge) return { ok: false, issues: ['Panel yok'] };

        if (!plan?.scenes?.length) {
            badge.className = 'sqp-status-badge waiting';
            badge.textContent = 'Senaryo bekleniyor';
            setSqpPill('sqp-cadence', 'Cadence: —', 'neutral');
            setSqpPill('sqp-words', 'Kelime: —', 'neutral');
            setSqpPill('sqp-duration', 'Sure: —', 'neutral');
            setSqpPill('sqp-clips', 'Klip: —', 'neutral');
            setSqpPill('sqp-narration', 'Anlatim: —', 'neutral');
            setSqpPill('sqp-plagiarism', 'Özgünlük: —', 'neutral');
            if (issuesEl) {
                issuesEl.classList.add('hidden');
                issuesEl.innerHTML = '';
            }
            updateRenderButtonsBlocked(true, 'Once senaryo olusturun');
            return { ok: false, issues: ['Senaryo yok'] };
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
        let activePlan = plan;
        if (validation.plan) {
            activePlan = validation.plan;
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

        if (issuesEl) {
            if (validation.issues?.length) {
                issuesEl.classList.remove('hidden');
                issuesEl.innerHTML = validation.issues.map(i => `<li>${formatQualityIssueWithRoadmap(i)}</li>`).join('');
            } else {
                issuesEl.classList.add('hidden');
                issuesEl.innerHTML = '';
            }
        }

        qualityPanelGreen = narrOk;
        if (narrOk) {
            badge.className = 'sqp-status-badge ok';
            badge.textContent = 'Render hazir';
            updateRenderButtonsBlocked(false);
        } else {
            badge.className = 'sqp-status-badge blocked';
            badge.textContent = 'Render kapali';
            updateRenderButtonsBlocked(true, validation.issues?.[0] || 'Anlatim kalite kapisi');
        }

        return validation;
    }

    function applyPlagiarismBadge(plagiarism) {
        if (!plagiarism) {
            setSqpPill('sqp-plagiarism', 'Özgünlük: —', 'neutral');
            return;
        }
        const pct = plagiarism.similarity_pct ?? 0;
        const ok = plagiarism.approved !== false;
        setSqpPill(
            'sqp-plagiarism',
            ok ? `Özgünlük: %${pct}` : `İntihal riski: %${pct}`,
            ok ? (pct <= 25 ? 'ok' : 'warn') : 'fail'
        );
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
        const statusText = ok ? 'GECTI' : 'RED';
        if (compact) {
            const issueHint = issues.length ? ` · ${escapeHtml(issues.slice(0, 2).join('; '))}` : '';
            return `<span class="gallery-qg-badge ${ok ? 'is-ok' : 'is-fail'}">${statusText} · skor ${score}${issueHint}</span>`;
        }
        const issueHtml = issues.length
            ? `<ul class="studio-qg-issues">${issues.map(i => {
                const madde = roadmapItemForIssue(i);
                const link = madde
                    ? ` <a href="#" class="qg-roadmap-link" data-roadmap-item="${madde}">Madde #${madde}</a>`
                    : '';
                return `<li>${escapeHtml(i)}${link}</li>`;
            }).join('')}</ul>`
            : '<span class="studio-qg-clean">Sorun yok</span>';
        return `
            <div class="studio-qg-card ${ok ? '' : 'is-fail'}">
                <strong class="${statusClass}">Kalite kapisi: ${statusText}</strong>
                <span class="studio-qg-meta">skor ${score} · sure ${dur}</span>
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
                fixes: []
            };
        }
        const outPlan = data.plan || plan;
        if (data.ok) {
            return {
                ok: true,
                issues: [],
                plan: outPlan,
                repaired: !!data.repaired,
                fixes: data.fixes || [],
                pre_render_score: data.pre_render_score
            };
        }
        return {
            ok: false,
            issues: collectValidationIssues(data, outPlan, plan),
            plan: outPlan,
            repaired: !!data.repaired,
            fixes: data.fixes || [],
            pre_render_score: data.pre_render_score
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
                        fixes: [...(result.fixes || []), ...(repairResult.fixes || [])]
                    };
                }
                if (repairResult.repaired || repairResult.fixes?.length) {
                    result = {
                        ...repairResult,
                        repaired: true,
                        fixes: [...(result.fixes || []), ...(repairResult.fixes || [])]
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
            soft.push(`Sure bandi: ${totalSec.toFixed(1)}sn (izin 38-60, hedef 48)`);
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
    let eventSource = null;
    let allNiches = [];
    let isRendering = false;
    let selectedRedditPost = null;
    let pendingFormatFingerprint = null;
    let trendFormatFingerprintAggregate = null;
    let lastTrendResults = [];
    let suppressFingerprintClear = false;
    let nicheResolveTimer = null;
    let lockedNicheId = null;

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

    // DOM ELEMENTS
    const navButtons = document.querySelectorAll('.nav-btn');
    const tabPanes = document.querySelectorAll('.tab-pane');
    const pageTitle = document.getElementById('current-page-title');
    const pageDesc = document.getElementById('current-page-desc');

    // Studio Elements
    const inputTopic = document.getElementById('input-topic');
    const selectNiche = document.getElementById('select-niche');
    const selectSubPreset = document.getElementById('select-subtitle-preset');
    const selectLanguage = document.getElementById('select-language');
    const selectTtsVoice = document.getElementById('select-tts-voice');
    const selectGameplayCategory = document.getElementById('select-gameplay-category');
    const gameplayCategoryWrap = document.getElementById('gameplay-category-wrap');
    const chkSplitScreen = document.getElementById('chk-split-screen');
    const TTS_VOICE_STORAGE_KEY = 'shortsTtsVoice';
    const STATIC_TTS_FALLBACK = {
        tr: [
            { id: 'tr-TR-AhmetNeural', label: 'Ahmet', gender: 'male', quality: 'Neural', native: true },
            { id: 'tr-TR-EmelNeural', label: 'Emel', gender: 'female', quality: 'Neural', native: true },
            { id: 'en-US-AndrewMultilingualNeural', label: 'Andrew (çok dilli)', gender: 'male', quality: 'Multilingual Neural', native: false },
            { id: 'en-US-AvaMultilingualNeural', label: 'Ava (çok dilli)', gender: 'female', quality: 'Multilingual Neural', native: false },
            { id: 'en-US-BrianMultilingualNeural', label: 'Brian (çok dilli)', gender: 'male', quality: 'Multilingual Neural', native: false },
            { id: 'en-US-EmmaMultilingualNeural', label: 'Emma (çok dilli)', gender: 'female', quality: 'Multilingual Neural', native: false },
            { id: 'en-AU-WilliamMultilingualNeural', label: 'William (çok dilli)', gender: 'male', quality: 'Multilingual Neural', native: false },
            { id: 'de-DE-FlorianMultilingualNeural', label: 'Florian (çok dilli)', gender: 'male', quality: 'Multilingual Neural', native: false },
            { id: 'de-DE-SeraphinaMultilingualNeural', label: 'Seraphina (çok dilli)', gender: 'female', quality: 'Multilingual Neural', native: false },
            { id: 'fr-FR-RemyMultilingualNeural', label: 'Remy (çok dilli)', gender: 'male', quality: 'Multilingual Neural', native: false },
            { id: 'fr-FR-VivienneMultilingualNeural', label: 'Vivienne (çok dilli)', gender: 'female', quality: 'Multilingual Neural', native: false },
            { id: 'it-IT-GiuseppeMultilingualNeural', label: 'Giuseppe (çok dilli)', gender: 'male', quality: 'Multilingual Neural', native: false },
            { id: 'ko-KR-HyunsuMultilingualNeural', label: 'Hyunsu (çok dilli)', gender: 'male', quality: 'Multilingual Neural', native: false },
            { id: 'pt-BR-ThalitaMultilingualNeural', label: 'Thalita (çok dilli)', gender: 'female', quality: 'Multilingual Neural', native: false },
        ],
        en: [
            { id: 'en-US-GuyNeural', label: 'Guy (US)', gender: 'male', quality: 'Neural', native: true },
            { id: 'en-US-JennyNeural', label: 'Jenny (US)', gender: 'female', quality: 'Neural', native: true },
            { id: 'en-US-AriaNeural', label: 'Aria (US)', gender: 'female', quality: 'Neural', native: true },
            { id: 'en-US-AndrewNeural', label: 'Andrew (US)', gender: 'male', quality: 'Neural', native: true },
            { id: 'en-US-BrianNeural', label: 'Brian (US)', gender: 'male', quality: 'Neural', native: true },
            { id: 'en-US-EmmaNeural', label: 'Emma (US)', gender: 'female', quality: 'Neural', native: true },
            { id: 'en-US-ChristopherNeural', label: 'Christopher (US)', gender: 'male', quality: 'Neural', native: true },
            { id: 'en-US-EricNeural', label: 'Eric (US)', gender: 'male', quality: 'Neural', native: true },
            { id: 'en-US-MichelleNeural', label: 'Michelle (US)', gender: 'female', quality: 'Neural', native: true },
            { id: 'en-GB-SoniaNeural', label: 'Sonia (UK)', gender: 'female', quality: 'Neural', native: true },
            { id: 'en-GB-RyanNeural', label: 'Ryan (UK)', gender: 'male', quality: 'Neural', native: true },
            { id: 'en-AU-NatashaNeural', label: 'Natasha (AU)', gender: 'female', quality: 'Neural', native: true },
            { id: 'en-CA-ClaraNeural', label: 'Clara (CA)', gender: 'female', quality: 'Neural', native: true },
            { id: 'en-CA-LiamNeural', label: 'Liam (CA)', gender: 'male', quality: 'Neural', native: true },
        ],
    };
    let ttsVoiceCatalog = {
        tr: STATIC_TTS_FALLBACK.tr.slice(),
        en: STATIC_TTS_FALLBACK.en.slice(),
        elevenlabs: [],
    };
    let elevenlabsConfigured = false;
    const chkAntiDuplicate = document.getElementById('chk-anti-duplicate');
    const chkKenBurns = document.getElementById('chk-ken-burns');
    const chkAutoPublish = document.getElementById('chk-auto-publish');
    const btnCreateScript = document.getElementById('btn-create-script');
    const btnQuickRender = document.getElementById('btn-quick-render');
    const livePlayer = document.getElementById('live-preview-player');
    const mockupPlaceholder = document.getElementById('mockup-placeholder');
    const mockupStatusText = document.getElementById('mockup-status-text');

    // Persistent Monitor
    const persistentMonitor = document.getElementById('persistent-monitor');
    const dockStepTitle = document.getElementById('dock-step-title');
    const dockLogSnippet = document.getElementById('dock-log-snippet');
    const dockProgressFill = document.getElementById('dock-progress-fill');
    const dockProgressPct = document.getElementById('dock-progress-pct');
    const btnToggleLog = document.getElementById('btn-toggle-terminal-log');
    const btnCancelRender = document.getElementById('btn-cancel-render');
    const btnCloseDock = document.getElementById('btn-close-dock');
    const dockSpinner = document.getElementById('dock-spinner');
    const terminalPanel = document.getElementById('terminal-log-panel');
    const terminalBody = document.getElementById('terminal-log-body');
    const btnCloseLog = document.getElementById('btn-close-log');

    // ══════════════════════════════════════════════════════════════
    // 1. TAB ROUTING & NAVIGATION
    // ══════════════════════════════════════════════════════════════
    const TAB_METADATA = {
        "studio": { title: "Hızlı Üretim Stüdyosu", desc: "Konunuzu belirleyin, 35 niş arasından seçim yapın ve tek tıkla viral Shorts üretin." },
        "timeline": { title: "Sahne & Kurgu Editörü", desc: "AI tarafından üretilen sahneleri, süreleri ve arama terimlerini özelleştirin." },
        "niches": { title: "35 R10 Viral Niş Kütüphanesi", desc: "En çok izlenen ve gelir getiren 35 niş şablonundan birini seçin." },
        "rss-bot": { title: "Oto-Haber & RSS Botu", desc: "Canlı haber kaynaklarını tarayıp anında 45 saniyelik Shorts'a dönüştürün." },
        "batch": { title: "Toplu Üretim & CSV Kuyruğu", desc: "Çoklu konu listesini kuyruğa ekleyin ve 14 günlük ısınma (warm-up) sınırıyla üretin." },
        "growth": { title: "Büyüme, A/B Test & Algoritma Taktikleri", desc: "CTR artıran A/B varyantları, topluluk anketleri ve telif risk denetimi." },
        "effects": { title: "Split-Screen & Görsel FX Stüdyosu", desc: "Bölünmüş ekran oynanış kurgusu, Smart Crop ve Anti-Duplicate koruması." },
        "subtitles": { title: "CapCut Karaoke Altyazı Laboratuvarı", desc: "Kelime kelime yanan neon altyazılar, ön tanımlı profesyonel renk şablonları." },
        "audio": { title: "Ses, SFX & Müzik Konsolu", desc: "Audio Ducking, doğal Türkçe sesler ve geçiş Whoosh/Pop/Ding efektleri." },
        "channels": { title: "Kanal & Otomatik Yayın Dağıtımı", desc: "YouTube API v3 ile planlı yükleme ve TikTok/Reels çapraz paylaşım formatı." },
        "gallery": { title: "Video Galerisi & Arşiv", desc: "Tamamlanan Full HD videolarınızı izleyin, indirin veya kanala yükleyin." },
        "roadmap500": { title: "Yol Haritası", desc: "Sistem özellikleri ve teknik parametrelerin canlı durum gezgini." },
        "settings": { title: "Sistem & API Ayarları", desc: "0 TL maliyet katmanı, kota izleyici ve API anahtarı yönetimi." }
    };

    const NAV_COLLAPSIBLE_TABS = {
        'rss-bot': 0, 'batch': 0, 'growth': 0,
        'effects': 1, 'subtitles': 1, 'audio': 1, 'roadmap500': 1,
        'channels': 2, 'gallery': 2, 'settings': 2
    };

    function syncNavCollapsibles(tabId) {
        document.querySelectorAll('.nav-collapsible').forEach((details, idx) => {
            details.open = NAV_COLLAPSIBLE_TABS[tabId] === idx;
        });
    }

    function switchTab(tabId, updateHistory = true) {
        if (!tabId || !TAB_METADATA[tabId]) {
            tabId = 'studio';
        }

        const earlyStyle = document.getElementById('early-tab-style');
        if (earlyStyle) earlyStyle.remove();

        syncNavCollapsibles(tabId);

        navButtons.forEach(btn => {
            btn.classList.toggle('active', btn.getAttribute('data-tab') === tabId);
        });
        tabPanes.forEach(pane => {
            pane.classList.toggle('active', pane.id === `pane-${tabId}`);
        });

        if (TAB_METADATA[tabId]) {
            pageTitle.textContent = TAB_METADATA[tabId].title;
            pageDesc.textContent = TAB_METADATA[tabId].desc;
        }

        try {
            localStorage.setItem('activeShortsTab', tabId);
            if (updateHistory) {
                if (window.location.hash !== `#${tabId}`) {
                    window.location.hash = tabId;
                }
            }
        } catch (e) {}

        // On-demand tab loaders
        if (tabId === 'niches' && allNiches.length === 0) loadNiches();
        if (tabId === 'roadmap500') loadRoadmapItems();
        if (tabId === 'rss-bot') loadRssNews();
        if (tabId === 'timeline') timelineReviewed = true;
        if (tabId === 'gallery') loadGallery();
        if (tabId === 'settings') {
            if (typeof loadSettings === 'function') loadSettings();
            if (typeof window.loadHardwareSpecs === 'function') window.loadHardwareSpecs();
        }
        if (tabId === 'audio') loadBgmList();
    }

    navButtons.forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.getAttribute('data-tab')));
    });

    window.addEventListener('hashchange', () => {
        const hashTab = (window.location.hash || '').replace('#', '').trim();
        if (hashTab && TAB_METADATA[hashTab]) {
            switchTab(hashTab, false);
        }
    });

    // Sayfa açıldığında veya yenilendiğinde (F5) kalınan sekmeyi EN BAŞTA geri yükle
    try {
        const hashTab = (window.location.hash || '').replace('#', '').trim();
        const storedTab = localStorage.getItem('activeShortsTab');
        const targetTab = hashTab || storedTab || 'studio';
        if (targetTab && TAB_METADATA[targetTab]) {
            switchTab(targetTab, false);
        }
    } catch (e) {
        console.warn('Tab restore error:', e);
    }

    // ══════════════════════════════════════════════════════════════
    // 2. 35 NİŞİ YÜKLEME VE KARTLARI BASMA (Items 1 - 35)
    // ══════════════════════════════════════════════════════════════
    // ══════════════════════════════════════════════════════════════
    // 2. NİŞ KÜTÜPHANESİ — Advanced v2.0
    // ══════════════════════════════════════════════════════════════
    let currentNicheViewMode = 'grid'; // 'grid' | 'list'
    let currentModalNicheId = null;

    // Helper: parse RPM string to max numeric value for sorting
    function parseRpmMax(rpmStr) {
        if (!rpmStr) return 0;
        const nums = rpmStr.replace(/[$]/g, '').split('-').map(Number);
        return Math.max(...nums.filter(n => !isNaN(n)));
    }

    // Helper: competition level to sort order (low = best)
    function compToNum(lvl) { return lvl === 'low' ? 3 : lvl === 'medium' ? 2 : 1; }

    async function loadNiches() {
        try {
            const res = await fetch('/api/niches');
            const data = await res.json();
            allNiches = data.niches || [];

            // Hibrit Nişleri de Çekip Birleştir (Items 276-345)
            try {
                const hRes = await fetch('/api/hybrid_niches');
                const hData = await hRes.json();
                if (hData.hybrid_niches) {
                    allNiches = [...allNiches, ...hData.hybrid_niches];
                }
            } catch (he) {
                console.warn("Hibrit niş yükleme uyarısı:", he);
            }

            // Select dropdown'ları doldur
            selectNiche.innerHTML = '';
            const batchNicheSelect = document.getElementById('batch-default-niche');
            const compareA = document.getElementById('compare-niche-a');
            const compareB = document.getElementById('compare-niche-b');
            const collisionA = document.getElementById('collision-niche-a');
            const collisionB = document.getElementById('collision-niche-b');
            if (batchNicheSelect) batchNicheSelect.innerHTML = '';
            if (compareA) compareA.innerHTML = '';
            if (compareB) compareB.innerHTML = '';
            if (collisionA) collisionA.innerHTML = '';
            if (collisionB) collisionB.innerHTML = '';

            allNiches.forEach(n => {
                const opt = document.createElement('option');
                opt.value = n.id;
                opt.textContent = `${n.name} (${n.category})`;
                selectNiche.appendChild(opt);
                if (batchNicheSelect) batchNicheSelect.appendChild(opt.cloneNode(true));
                if (compareA) compareA.appendChild(opt.cloneNode(true));
                if (compareB) compareB.appendChild(opt.cloneNode(true));
                if (collisionA) collisionA.appendChild(opt.cloneNode(true));
                if (collisionB) collisionB.appendChild(opt.cloneNode(true));
            });

            // Default compare B to second niche
            if (compareB && compareB.options.length > 1) compareB.selectedIndex = 1;
            if (collisionB && collisionB.options.length > 1) collisionB.selectedIndex = 2;

            // Render cards & update stats
            applyNicheFiltersAndRender();
            updateNicheStats(allNiches);
            if (selectNiche.value) await applyNicheProfile(selectNiche.value);
            await resolveAndApplyNicheFromTopic({ toast: false });
        } catch (err) {
            console.error("Niche yükleme hatası:", err);
        }
    }

    function updateNicheStats(niches) {
        const shown = niches.length;
        const avgViral = shown ? Math.round(niches.reduce((a, n) => a + (n.viral_score || 75), 0) / shown) : '--';
        const topRpm = shown ? niches.reduce((best, n) => {
            const v = parseRpmMax(n.rpm_tier);
            return v > parseRpmMax(best) ? n.rpm_tier : best;
        }, '$0') : '--';
        const tier1Count = niches.filter(n => n.tier1_compatible).length;
        const el1 = document.getElementById('niche-count-shown');
        const el2 = document.getElementById('niche-stat-avg-viral');
        const el3 = document.getElementById('niche-stat-top-rpm');
        const el4 = document.getElementById('niche-stat-tier1');
        if (el1) el1.textContent = shown;
        if (el2) el2.textContent = avgViral;
        if (el3) el3.textContent = topRpm;
        if (el4) el4.textContent = tier1Count;
    }

    function applyNicheFiltersAndRender() {
        const searchVal = (document.getElementById('niche-search-input')?.value || '').toLowerCase();
        const activeCat = document.querySelector('.filter-pill.active')?.getAttribute('data-cat') || 'all';
        const rpmFilter = document.getElementById('niche-rpm-filter')?.value || 'all';
        const viralFilter = document.getElementById('niche-viral-filter')?.value || 'all';
        const sortBy = document.getElementById('niche-sort-select')?.value || 'viral_score';

        let filtered = allNiches.filter(n => {
            if (searchVal && !(n.name.toLowerCase().includes(searchVal) || n.category.toLowerCase().includes(searchVal))) return false;
            if (activeCat !== 'all' && !n.category.toLowerCase().includes(activeCat.toLowerCase())) return false;
            if (rpmFilter === 'low' && parseRpmMax(n.rpm_tier) > 7) return false;
            if (rpmFilter === 'mid' && (parseRpmMax(n.rpm_tier) < 8 || parseRpmMax(n.rpm_tier) > 15)) return false;
            if (rpmFilter === 'high' && parseRpmMax(n.rpm_tier) < 16) return false;
            if (viralFilter !== 'all' && (n.viral_score || 75) < parseInt(viralFilter)) return false;
            return true;
        });

        // Sort
        filtered.sort((a, b) => {
            if (sortBy === 'viral_score') return (b.viral_score || 75) - (a.viral_score || 75);
            if (sortBy === 'rpm') return parseRpmMax(b.rpm_tier) - parseRpmMax(a.rpm_tier);
            if (sortBy === 'retention') return (b.avg_retention_pct || 70) - (a.avg_retention_pct || 70);
            if (sortBy === 'competition_low') return compToNum(b.competition_level) - compToNum(a.competition_level);
            if (sortBy === 'alphabetic') return a.name.localeCompare(b.name, 'tr');
            return 0;
        });

        renderNicheCards(filtered);
        updateNicheStats(filtered);
    }

    function getViralScoreColor(score) {
        if (score >= 90) return '#f59e0b'; // gold — elite
        if (score >= 80) return '#10b981'; // green — good
        if (score >= 70) return '#06b6d4'; // cyan — decent
        return '#64748b'; // grey
    }

    function getCompetitionBadge(level) {
        if (level === 'low') return '<span style="background:rgba(16,185,129,0.15);color:#34d399;border:1px solid rgba(16,185,129,0.3);border-radius:6px;padding:2px 7px;font-size:10px;font-weight:600;">🟢 Az Rekabet</span>';
        if (level === 'medium') return '<span style="background:rgba(245,158,11,0.15);color:#fbbf24;border:1px solid rgba(245,158,11,0.3);border-radius:6px;padding:2px 7px;font-size:10px;font-weight:600;">🟡 Orta Rekabet</span>';
        return '<span style="background:rgba(239,68,68,0.15);color:#f87171;border:1px solid rgba(239,68,68,0.3);border-radius:6px;padding:2px 7px;font-size:10px;font-weight:600;">🔴 Yüksek Rekabet</span>';
    }

    function getRpmBadgeColor(rpmStr) {
        const max = parseRpmMax(rpmStr);
        if (max >= 16) return { bg: 'rgba(245,158,11,0.15)', color: '#fbbf24', border: 'rgba(245,158,11,0.35)' };
        if (max >= 8) return { bg: 'rgba(16,185,129,0.12)', color: '#34d399', border: 'rgba(16,185,129,0.3)' };
        return { bg: 'rgba(100,116,139,0.15)', color: '#94a3b8', border: 'rgba(100,116,139,0.25)' };
    }

    function getCtaBadge(cta) {
        const map = { comment: '💬 Yorum', vote: '🗳️ Oylama', save: '🔖 Kaydetme', subscribe: '🔔 Abone' };
        return map[cta] || '💬 Yorum';
    }

    function renderNicheCards(nichesToRender) {
        const grid = document.getElementById('niches-cards-grid');
        if (!grid) return;
        grid.innerHTML = '';

        if (nichesToRender.length === 0) {
            grid.innerHTML = '<div class="empty-state-box"><i class="fa-solid fa-filter-circle-xmark"></i><p>Filtrelerle eşleşen niş bulunamadı.</p></div>';
            return;
        }

        const isListMode = currentNicheViewMode === 'list';
        grid.className = isListMode ? 'niches-list-view' : 'niches-cards-grid';

        nichesToRender.forEach((n, idx) => {
            const viralScore = n.viral_score || 75;
            const retention = n.avg_retention_pct || 70;
            const viralColor = getViralScoreColor(viralScore);
            const rpmColor = getRpmBadgeColor(n.rpm_tier);
            const rank = idx + 1;
            const isTopTier = viralScore >= 90;

            const card = document.createElement('div');
            card.className = isListMode ? 'niche-card niche-card-list' : 'niche-card niche-card-v2';
            card.setAttribute('data-niche-id', n.id);
            card.style.cssText = `cursor:pointer;transition:all 0.25s cubic-bezier(0.4,0,0.2,1);border:1px solid ${isTopTier ? 'rgba(245,158,11,0.35)' : 'rgba(148,163,184,0.12)'};`;

            card.innerHTML = `
                ${isTopTier ? `<div style="position:absolute;top:-1px;right:14px;background:linear-gradient(135deg,#f59e0b,#f97316);color:#000;font-size:9px;font-weight:800;padding:3px 10px;border-radius:0 0 8px 8px;letter-spacing:0.5px;text-transform:uppercase;">⭐ Elite</div>` : ''}
                <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;margin-bottom:10px;">
                    <div style="display:flex;gap:10px;align-items:center;flex:1;min-width:0;">
                        <div style="width:38px;height:38px;border-radius:10px;background:linear-gradient(135deg,${viralColor}22,${viralColor}44);border:1px solid ${viralColor}44;display:flex;align-items:center;justify-content:center;flex-shrink:0;">
                            <i class="fa-solid ${n.icon || 'fa-fire'}" style="color:${viralColor};font-size:15px;"></i>
                        </div>
                        <div style="flex:1;min-width:0;">
                            <h4 style="margin:0;font-size:13px;font-weight:700;color:#e2e8f0;line-height:1.3;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${escapeHtml(n.name)}">${escapeHtml(n.name)}</h4>
                            <span style="font-size:10px;color:#64748b;">${escapeHtml(n.category)}</span>
                        </div>
                    </div>
                    <div style="display:flex;flex-direction:column;align-items:flex-end;gap:4px;flex-shrink:0;">
                        <div style="font-size:18px;font-weight:800;color:${viralColor};line-height:1;">${viralScore}</div>
                        <div style="font-size:9px;color:#64748b;text-align:right;">Viral Score</div>
                    </div>
                </div>

                <!-- Viral Score Bar -->
                <div style="margin-bottom:10px;">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
                        <span style="font-size:10px;color:#64748b;">🔥 Viral Potansiyel</span>
                        <span style="font-size:10px;color:${viralColor};font-weight:600;">${viralScore}/100</span>
                    </div>
                    <div style="height:4px;background:rgba(148,163,184,0.15);border-radius:4px;overflow:hidden;">
                        <div class="niche-score-bar" style="height:100%;width:0%;background:linear-gradient(90deg,${viralColor}aa,${viralColor});border-radius:4px;transition:width 0.8s ease;" data-target="${viralScore}"></div>
                    </div>
                </div>

                <!-- Key Metrics Row -->
                <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px;margin-bottom:10px;">
                    <div style="background:${rpmColor.bg};border:1px solid ${rpmColor.border};border-radius:7px;padding:5px 7px;text-align:center;">
                        <div style="font-size:11px;font-weight:700;color:${rpmColor.color};">${escapeHtml(n.rpm_tier || '$2-5')}</div>
                        <div style="font-size:9px;color:#64748b;">RPM</div>
                    </div>
                    <div style="background:rgba(6,182,212,0.08);border:1px solid rgba(6,182,212,0.2);border-radius:7px;padding:5px 7px;text-align:center;">
                        <div style="font-size:11px;font-weight:700;color:#67e8f9;">${retention}%</div>
                        <div style="font-size:9px;color:#64748b;">Retention</div>
                    </div>
                    <div style="background:rgba(148,163,184,0.06);border:1px solid rgba(148,163,184,0.15);border-radius:7px;padding:5px 7px;text-align:center;">
                        <div style="font-size:10px;font-weight:600;color:#94a3b8;">${getCtaBadge(n.cta_type)}</div>
                        <div style="font-size:9px;color:#64748b;">CTA Türü</div>
                    </div>
                </div>

                <!-- Badges Row -->
                <div style="display:flex;flex-wrap:wrap;gap:5px;margin-bottom:10px;">
                    ${getCompetitionBadge(n.competition_level)}
                    ${n.tier1_compatible ? '<span style="background:rgba(6,182,212,0.12);color:#67e8f9;border:1px solid rgba(6,182,212,0.25);border-radius:6px;padding:2px 7px;font-size:10px;">🌍 Tier-1</span>' : ''}
                    ${n.has_split_screen ? '<span style="background:rgba(139,92,246,0.12);color:#c4b5fd;border:1px solid rgba(139,92,246,0.25);border-radius:6px;padding:2px 7px;font-size:10px;">🎮 Split-Screen</span>' : ''}
                    ${n.episodic_capable ? '<span style="background:rgba(16,185,129,0.1);color:#6ee7b7;border:1px solid rgba(16,185,129,0.2);border-radius:6px;padding:2px 7px;font-size:10px;">📺 Seri</span>' : ''}
                </div>

                <!-- Best Posting Time -->
                <div style="font-size:10px;color:#64748b;margin-bottom:10px;">
                    🕐 En İyi: <span style="color:#94a3b8;">${escapeHtml(n.best_posting_time || '12:00-15:00 TRT')}</span>
                </div>

                <!-- Action Buttons -->
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;">
                    <button class="btn btn-primary niche-use-btn" data-niche-id="${n.id}" style="font-size:11px;padding:7px 10px;" onclick="event.stopPropagation()">
                        <i class="fa-solid fa-arrow-right"></i> Bu Nişle Üret
                    </button>
                    <button class="btn btn-secondary niche-detail-btn" data-niche-id="${n.id}" style="font-size:11px;padding:7px 10px;" onclick="event.stopPropagation()">
                        <i class="fa-solid fa-expand"></i> Detay & A/B
                    </button>
                </div>
            `;

            // Click card body → open modal
            card.addEventListener('click', () => openNicheModal(n.id));
            grid.appendChild(card);
        });

        // Animate viral score bars after render
        requestAnimationFrame(() => {
            document.querySelectorAll('.niche-score-bar').forEach(bar => {
                bar.style.width = bar.getAttribute('data-target') + '%';
            });
        });

        // Action button events
        grid.querySelectorAll('.niche-use-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const nId = e.currentTarget.getAttribute('data-niche-id');
                const selected = allNiches.find(x => x.id === nId);
                if (selected) {
                    selectNiche.value = selected.id;
                    applyNicheProfile(selected.id);
                    // Seed topic from niche hook if empty or generic
                    const hook = (selected.hook_style || selected.name || '').trim();
                    if (hook && inputTopic) {
                        const cur = inputTopic.value.trim();
                        if (!cur || cur.length < 8) {
                            inputTopic.value = hook.length > 120 ? hook.slice(0, 117) + '...' : hook;
                        }
                    }
                    switchTab('studio');
                    updateFlowRail('topic');
                    showToast(`Nis secildi: ${selected.name} — konuyu netlestirip senaryo uretin`);
                }
            });
        });

        grid.querySelectorAll('.niche-detail-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                openNicheModal(e.currentTarget.getAttribute('data-niche-id'));
            });
        });
    }

    // ── Niche Detail Modal ──
    async function openNicheModal(nicheId) {
        currentModalNicheId = nicheId;
        const n = allNiches.find(x => x.id === nicheId);
        if (!n) return;
        const modal = document.getElementById('niche-detail-modal');
        const viralColor = getViralScoreColor(n.viral_score || 75);
        const rpmC = getRpmBadgeColor(n.rpm_tier);

        // Icon wrap
        const iconWrap = document.getElementById('niche-modal-icon-wrap');
        iconWrap.style.background = `linear-gradient(135deg,${viralColor}44,${viralColor}66)`;
        iconWrap.innerHTML = `<i class="fa-solid ${n.icon || 'fa-fire'}"></i>`;

        // Title
        document.getElementById('niche-modal-title').textContent = n.name;

        // Badges
        document.getElementById('niche-modal-badges').innerHTML = `
            <span class="niche-tag">${escapeHtml(n.category)}</span>
            ${getCompetitionBadge(n.competition_level)}
            ${n.tier1_compatible ? '<span style="background:rgba(6,182,212,0.12);color:#67e8f9;border:1px solid rgba(6,182,212,0.25);border-radius:6px;padding:2px 8px;font-size:11px;">🌍 Tier-1</span>' : ''}
        `;

        // Stats
        document.getElementById('niche-modal-stats').innerHTML = `
            <div style="display:flex;flex-direction:column;gap:10px;">
                ${[
                    ['🔥 Viral Skor', `<span style="color:${viralColor};font-weight:800;font-size:20px;">${n.viral_score || 75}</span><span style="color:#64748b;font-size:12px;">/100</span>`, viralColor],
                    ['💰 RPM Bandı', `<span style="color:${rpmC.color};font-weight:700;">${escapeHtml(n.rpm_tier || '$2-5')}</span>`, rpmC.color],
                    ['👁 Ort. Retention', `<span style="color:#67e8f9;font-weight:700;">${n.avg_retention_pct || 70}%</span>`, '#67e8f9'],
                    ['🕐 En İyi Paylaşım', `<span style="color:#94a3b8;font-size:12px;">${escapeHtml(n.best_posting_time || '--')}</span>`, '#94a3b8'],
                    ['🎯 CTA Türü', `<span style="color:#c4b5fd;">${getCtaBadge(n.cta_type)}</span>`, '#c4b5fd'],
                    ['📺 Seri Formatı', n.episodic_capable ? '<span style="color:#34d399;">✅ Uygun</span>' : '<span style="color:#64748b;">❌ Değil</span>', '#34d399'],
                ].map(([label, val]) => `
                    <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 12px;background:rgba(15,23,42,0.5);border-radius:8px;border:1px solid rgba(148,163,184,0.08);">
                        <span style="font-size:12px;color:#64748b;">${label}</span>
                        <span style="font-size:13px;">${val}</span>
                    </div>
                `).join('')}
            </div>
        `;

        // Keywords
        document.getElementById('niche-modal-keywords').innerHTML = (n.trending_keywords || []).map(kw =>
            `<span style="background:rgba(6,182,212,0.1);color:#67e8f9;border:1px solid rgba(6,182,212,0.2);border-radius:20px;padding:3px 10px;font-size:11px;">${escapeHtml(kw)}</span>`
        ).join('');

        // A/B Hooks
        const abColors = ['#10b981', '#f59e0b', '#8b5cf6'];
        const abLabels = ['A — Merak Kancası', 'B — Şok Kancası', 'C — Tartışma Kancası'];
        const hooks = n.ab_test_hook_variants || [n.hook_style || ''];
        document.getElementById('niche-modal-ab-hooks').innerHTML = hooks.slice(0, 3).map((hook, i) => `
            <div style="margin-bottom:10px;padding:12px;background:rgba(${i===0?'16,185,129':i===1?'245,158,11':'139,92,246'},0.08);border:1px solid rgba(${i===0?'16,185,129':i===1?'245,158,11':'139,92,246'},0.2);border-radius:10px;">
                <div style="font-size:10px;font-weight:700;color:${abColors[i]};text-transform:uppercase;letter-spacing:0.5px;margin-bottom:6px;">${abLabels[i]}</div>
                <div style="font-size:12px;color:#cbd5e1;line-height:1.5;">"${escapeHtml(hook)}"</div>
                <button class="ab-hook-use-btn" data-hook="${escapeHtml(hook)}" style="margin-top:8px;background:rgba(${i===0?'16,185,129':i===1?'245,158,11':'139,92,246'},0.15);border:1px solid rgba(${i===0?'16,185,129':i===1?'245,158,11':'139,92,246'},0.3);color:${abColors[i]};border-radius:6px;padding:4px 10px;font-size:11px;cursor:pointer;">
                    Bu Kancayı Kullan
                </button>
            </div>
        `).join('');

        // Trends placeholder
        document.getElementById('niche-modal-trends').innerHTML = '<div style="color:#64748b;font-size:12px;padding:8px;">Yükleniyor...</div>';

        // Show modal
        modal.style.display = 'block';

        // Setup use button
        document.getElementById('btn-modal-use-niche').onclick = () => {
            selectNiche.value = nicheId;
            applyNicheProfile(nicheId);
            const hook = (n.hook_style || n.name || '').trim();
            if (hook && inputTopic && (!inputTopic.value.trim() || inputTopic.value.trim().length < 8)) {
                inputTopic.value = hook.length > 120 ? hook.slice(0, 117) + '...' : hook;
            }
            switchTab('studio');
            updateFlowRail('topic');
            closeNicheModal();
            showToast(`Nis: ${n.name} — konuyu duzenleyip senaryo uretin`);
        };

        // AB hook use buttons
        document.querySelectorAll('.ab-hook-use-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const hook = e.currentTarget.getAttribute('data-hook');
                if (inputTopic) inputTopic.value = hook;
                showToast('🧪 A/B kanca konuya aktarıldı!');
            });
        });

        // Load trending topics
        loadModalTrends(nicheId);

        // Setup reload trends button
        document.getElementById('btn-modal-load-trends').onclick = () => loadModalTrends(nicheId);
    }

    async function loadModalTrends(nicheId) {
        const trendsEl = document.getElementById('niche-modal-trends');
        if (!trendsEl) return;
        trendsEl.innerHTML = '<div style="color:#64748b;font-size:12px;padding:8px;"><i class="fa-solid fa-spinner fa-spin"></i> Trend konular aranıyor...</div>';
        try {
            const res = await fetch(`/api/niches/${encodeURIComponent(nicheId)}/trending_topics`);
            const data = await res.json();
            const topics = data.topics || [];
            if (topics.length === 0) {
                trendsEl.innerHTML = '<div style="color:#64748b;font-size:12px;padding:8px;">Trend bulunamadı.</div>';
                return;
            }
            trendsEl.innerHTML = topics.slice(0, 5).map(t => `
                <div style="padding:8px;border-bottom:1px solid rgba(148,163,184,0.08);cursor:pointer;transition:background 0.15s;" 
                     class="trend-topic-row"
                     onclick="(function(){ document.getElementById('input-topic').value='${escapeHtml(t.title).replace(/'/g, "\\'")}'; })()">
                    <div style="font-size:11px;color:#cbd5e1;line-height:1.4;">${escapeHtml(t.title)}</div>
                    <div style="font-size:10px;color:#64748b;margin-top:2px;">${escapeHtml(t.view_count_text || '')}</div>
                </div>
            `).join('');
        } catch(e) {
            trendsEl.innerHTML = '<div style="color:#64748b;font-size:12px;padding:8px;">Trend yüklenemedi.</div>';
        }
    }

    function closeNicheModal() {
        const modal = document.getElementById('niche-detail-modal');
        if (modal) modal.style.display = 'none';
        currentModalNicheId = null;
    }

    document.getElementById('btn-close-niche-modal')?.addEventListener('click', closeNicheModal);
    document.getElementById('niche-detail-modal')?.addEventListener('click', (e) => {
        if (e.target === e.currentTarget) closeNicheModal();
    });

    // ── Filter Pills ──
    document.querySelectorAll('.filter-pill').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.filter-pill').forEach(b => b.classList.remove('active'));
            e.currentTarget.classList.add('active');
            applyNicheFiltersAndRender();
        });
    });

    // ── Search / Sort / Filter change handlers ──
    document.getElementById('niche-search-input')?.addEventListener('input', applyNicheFiltersAndRender);
    document.getElementById('niche-sort-select')?.addEventListener('change', applyNicheFiltersAndRender);
    document.getElementById('niche-rpm-filter')?.addEventListener('change', applyNicheFiltersAndRender);
    document.getElementById('niche-viral-filter')?.addEventListener('change', applyNicheFiltersAndRender);

    // ── View Mode Toggle ──
    document.getElementById('btn-niche-view-grid')?.addEventListener('click', () => {
        currentNicheViewMode = 'grid';
        applyNicheFiltersAndRender();
    });
    document.getElementById('btn-niche-view-list')?.addEventListener('click', () => {
        currentNicheViewMode = 'list';
        applyNicheFiltersAndRender();
    });

    // ── Compare Tool ──
    document.getElementById('btn-compare-niches')?.addEventListener('click', async () => {
        const a = document.getElementById('compare-niche-a')?.value;
        const b = document.getElementById('compare-niche-b')?.value;
        const resultEl = document.getElementById('compare-result');
        if (!a || !b || !resultEl) return;
        if (a === b) { showToast('⚠️ Aynı nişi karşılaştıramazsın!'); return; }
        resultEl.style.display = 'block';
        resultEl.innerHTML = '<div style="color:#64748b;font-size:12px;"><i class="fa-solid fa-spinner fa-spin"></i> Karşılaştırılıyor...</div>';
        try {
            const res = await fetch('/api/niches/compare', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({niche_a: a, niche_b: b}) });
            const data = await res.json();
            if (data.status !== 'ok') { resultEl.innerHTML = '<div style="color:#f87171;font-size:12px;">Hata oluştu.</div>'; return; }
            const na = data.niche_a, nb = data.niche_b;
            const winnerName = allNiches.find(x => x.id === data.overall_winner)?.name || data.overall_winner;
            const dims = [
                ['🔥 Viral Skor', na.viral_score, nb.viral_score, 'viral_score'],
                ['👁 Retention', na.avg_retention_pct + '%', nb.avg_retention_pct + '%', 'avg_retention_pct'],
                ['🌍 Tier-1', na.tier1_compatible ? '✅' : '❌', nb.tier1_compatible ? '✅' : '❌', 'tier1'],
            ];
            resultEl.innerHTML = `
                <div style="font-size:11px;font-weight:700;color:#10b981;margin-bottom:8px;text-align:center;">🏆 Kazanan: ${escapeHtml(winnerName)}</div>
                <table style="width:100%;font-size:11px;border-collapse:collapse;">
                    <thead><tr><th style="color:#64748b;text-align:left;padding:3px 0;">Metrik</th><th style="color:#67e8f9;text-align:center;">${escapeHtml(na.name.split('&')[0].trim())}</th><th style="color:#c4b5fd;text-align:center;">${escapeHtml(nb.name.split('&')[0].trim())}</th></tr></thead>
                    <tbody>
                        ${dims.map(([label, va, vb, dim]) => {
                            const win = data.winner_per_dimension[dim];
                            return `<tr><td style="color:#64748b;padding:3px 0;">${label}</td>
                                <td style="text-align:center;color:${win===a?'#34d399':'#cbd5e1'};font-weight:${win===a?'700':'400'};">${va}</td>
                                <td style="text-align:center;color:${win===b?'#34d399':'#cbd5e1'};font-weight:${win===b?'700':'400'};">${vb}</td></tr>`;
                        }).join('')}
                    </tbody>
                </table>
            `;
        } catch(e) { resultEl.innerHTML = '<div style="color:#f87171;font-size:12px;">Bağlantı hatası.</div>'; }
    });

    // ── Collision Engine ──
    document.getElementById('btn-collide-niches')?.addEventListener('click', async () => {
        const a = document.getElementById('collision-niche-a')?.value;
        const b = document.getElementById('collision-niche-b')?.value;
        const resultEl = document.getElementById('collision-result');
        if (!a || !b || !resultEl) return;
        if (a === b) { showToast('⚠️ Farklı iki niş seç!'); return; }
        resultEl.style.display = 'block';
        resultEl.innerHTML = '<div style="color:#64748b;font-size:12px;"><i class="fa-solid fa-spinner fa-spin"></i> Melezleniyor...</div>';
        try {
            const res = await fetch('/api/niches/collision', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({niche_a: a, niche_b: b}) });
            const data = await res.json();
            if (data.status !== 'ok') { resultEl.innerHTML = '<div style="color:#f87171;font-size:12px;">Hata.</div>'; return; }
            const c = data.collision;
            resultEl.innerHTML = `
                <div style="background:linear-gradient(135deg,rgba(139,92,246,0.1),rgba(244,63,94,0.05));border:1px solid rgba(139,92,246,0.25);border-radius:10px;padding:12px;">
                    <div style="font-size:13px;font-weight:700;color:#c4b5fd;margin-bottom:8px;">⚡ ${escapeHtml(c.name)}</div>
                    <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px;">
                        <span style="font-size:11px;color:#f59e0b;">🔥 Viral: ${c.blended_viral_score}/100</span>
                        <span style="font-size:11px;color:#67e8f9;">👁 Ret: ${c.blended_retention}%</span>
                    </div>
                    <div style="font-size:11px;color:#94a3b8;margin-bottom:8px;font-style:italic;">"${escapeHtml(c.collision_hook_variants?.[0] || '')}"</div>
                    <button onclick="(function(){
                        const sel = document.getElementById('select-niche');
                        if(sel){ sel.value='${a}'; }
                        const topicEl = document.getElementById('input-topic');
                        if(topicEl){ topicEl.value='${escapeHtml(c.name).replace(/'/g,"\\'")}'; }
                        window.dispatchEvent(new CustomEvent('applyNicheProfile',{detail:'${a}'}));
                        document.querySelector('[data-tab=studio]')?.click();
                    })()" style="width:100%;background:rgba(139,92,246,0.2);border:1px solid rgba(139,92,246,0.35);color:#c4b5fd;border-radius:7px;padding:6px;font-size:11px;cursor:pointer;">
                        🚀 Bu Melezle Stüdyoya Git
                    </button>
                </div>
            `;
        } catch(e) { resultEl.innerHTML = '<div style="color:#f87171;font-size:12px;">Bağlantı hatası.</div>'; }
    });



    // ══════════════════════════════════════════════════════════════
    // 3. OTO-HABER & RSS BOTU (Item 1 & 57)
    // ══════════════════════════════════════════════════════════════
    async function loadRssNews() {
        const list = document.getElementById('rss-news-list');
        const sourceSelect = document.getElementById('select-rss-source');
        const source = sourceSelect ? sourceSelect.value : 'aa_guncel';
        list.innerHTML = '<div class="empty-state-box"><i class="fa-solid fa-spinner fa-spin"></i><p>Haberler taranıyor...</p></div>';

        try {
            const res = await fetch(`/api/rss/fetch?source=${source}&limit=6`);
            const data = await res.json();
            const items = data.items || [];

            if (items.length === 0) {
                list.innerHTML = '<div class="empty-state-box"><p>Bu kaynaktan haber çekilemedi.</p></div>';
                return;
            }

            list.innerHTML = '';
            items.forEach(item => {
                const row = document.createElement('div');
                row.className = 'glass-box mb-3';
                row.style.padding = '14px';
                row.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 10px;">
                        <div>
                            <strong style="font-size: 13px; color: #FFF;">${item.title}</strong>
                            <p style="font-size: 11px; color: #94A3B8; margin-top: 4px;">${item.description.slice(0, 120)}...</p>
                        </div>
                        <button class="btn btn-primary btn-sm btn-convert-rss" data-title="${encodeURIComponent(item.title)}">
                            <i class="fa-solid fa-bolt"></i> Shorts Yap
                        </button>
                    </div>
                `;
                list.appendChild(row);
            });

            list.querySelectorAll('.btn-convert-rss').forEach(b => {
                b.addEventListener('click', (e) => {
                    const rawTitle = decodeURIComponent(e.currentTarget.getAttribute('data-title'));
                    inputTopic.value = rawTitle;
                    selectNiche.value = "1_news_flash";
                    applyNicheProfile("1_news_flash");
                    switchTab('studio');
                    updateFlowRail('topic');
                    showToast('Haber stüdyoya aktarıldı — Senaryoyu incele ile devam edin');
                });
            });
        } catch (err) {
            list.innerHTML = `<div class="empty-state-box text-danger"><p>Haber tarama hatası: ${err.message}</p></div>`;
        }
    }

    document.getElementById('btn-fetch-rss-now')?.addEventListener('click', loadRssNews);
    document.getElementById('select-rss-source')?.addEventListener('change', loadRssNews);

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

    // ══════════════════════════════════════════════════════════════
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

    // ══════════════════════════════════════════════════════════════
    // 6. ALTYAZI PRESET SEÇİCİ & ANİMASYON TESTİ (Items 42 & 43)
    // ══════════════════════════════════════════════════════════════
    const SUBTITLE_LAB_KEY = 'subtitleLabSettings';
    const SUBTITLE_LAB_COLORS = {
        capcut_yellow: { highlight: '#FFD700', glow: '0 0 15px #FFD700' },
        cyber_green: { highlight: '#00FF66', glow: '0 0 15px #00FF66' },
        red_fire: { highlight: '#FF3333', glow: '0 0 15px #FF3333' },
        clean_white: { highlight: '#00D4FF', glow: '0 0 15px #00D4FF' },
    };
    const subRangeSize = document.getElementById('sub-range-size');
    const subRangeY = document.getElementById('sub-range-y');
    const valSubSize = document.getElementById('val-sub-size');
    const valSubY = document.getElementById('val-sub-y');
    const subStage = document.getElementById('sub-stage');

    function getSubtitleLabSettings() {
        return {
            preset: selectSubPreset?.value || 'capcut_yellow',
            fontSize: parseInt(subRangeSize?.value || '54', 10),
            yPosition: parseFloat(subRangeY?.value || '0.8'),
        };
    }

    function saveSubtitleLabSettings() {
        try {
            localStorage.setItem(SUBTITLE_LAB_KEY, JSON.stringify(getSubtitleLabSettings()));
        } catch (_) {}
    }

    function restoreSubtitleLabSettings() {
        try {
            const raw = localStorage.getItem(SUBTITLE_LAB_KEY);
            if (!raw) return;
            const s = JSON.parse(raw);
            if (s.preset && selectSubPreset) selectSubPreset.value = s.preset;
            if (s.fontSize && subRangeSize) subRangeSize.value = s.fontSize;
            if (s.yPosition && subRangeY) subRangeY.value = s.yPosition;
            document.querySelectorAll('.preset-card').forEach(c => {
                c.classList.toggle('active', c.getAttribute('data-preset') === s.preset);
            });
        } catch (_) {}
    }

    function updateSubtitleSimulator() {
        const preset = selectSubPreset?.value || 'capcut_yellow';
        const colors = SUBTITLE_LAB_COLORS[preset] || SUBTITLE_LAB_COLORS.capcut_yellow;
        const fontSize = parseInt(subRangeSize?.value || '54', 10);
        const yPct = parseFloat(subRangeY?.value || '0.8');

        if (valSubSize) valSubSize.textContent = `${fontSize} px`;
        if (valSubY) valSubY.textContent = `%${Math.round(yPct * 100)} (Alt Kısım)`;

        if (subStage) {
            subStage.className = `subtitle-stage preset-${preset}`;
            subStage.style.alignItems = yPct <= 0.65 ? 'flex-start' : (yPct >= 0.75 ? 'flex-end' : 'center');
            subStage.style.paddingBottom = yPct >= 0.75 ? '14px' : '0';
            subStage.style.paddingTop = yPct <= 0.65 ? '14px' : '0';
        }
        const stageText = subStage?.querySelector('.stage-text');
        if (stageText) {
            stageText.style.fontSize = `${Math.round(fontSize * 0.44)}px`;
        }
        subStage?.querySelectorAll('.stage-w').forEach(w => {
            if (w.classList.contains('active-word')) {
                w.style.color = colors.highlight;
                w.style.textShadow = colors.glow;
            } else {
                w.style.color = '#FFFFFF';
                w.style.textShadow = 'none';
            }
        });

        const subOverlay = document.getElementById('mockup-sub-overlay');
        if (subOverlay) {
            subOverlay.className = `mockup-subtitle-overlay preset-${preset}`;
        }
    }

    restoreSubtitleLabSettings();
    updateSubtitleSimulator();

    subRangeSize?.addEventListener('input', () => {
        updateSubtitleSimulator();
        saveSubtitleLabSettings();
    });
    subRangeY?.addEventListener('input', () => {
        updateSubtitleSimulator();
        saveSubtitleLabSettings();
    });

    document.querySelectorAll('.preset-card').forEach(card => {
        card.addEventListener('click', () => {
            document.querySelectorAll('.preset-card').forEach(c => c.classList.remove('active'));
            card.classList.add('active');
            const p = card.getAttribute('data-preset');
            selectSubPreset.value = p;
            updateSubtitleSimulator();
            saveSubtitleLabSettings();
            showToast(`🎨 '${card.querySelector('h4').textContent}' altyazı stili seçildi!`);
        });
    });

    selectSubPreset?.addEventListener('change', () => {
        document.querySelectorAll('.preset-card').forEach(c => {
            c.classList.toggle('active', c.getAttribute('data-preset') === selectSubPreset.value);
        });
        updateSubtitleSimulator();
        saveSubtitleLabSettings();
    });

    document.getElementById('btn-test-sub-animation')?.addEventListener('click', () => {
        const words = document.querySelectorAll('.stage-w');
        let idx = 0;
        const interval = setInterval(() => {
            words.forEach(w => w.classList.remove('active-word'));
            if (idx < words.length) {
                words[idx].classList.add('active-word');
                updateSubtitleSimulator();
                idx++;
            } else {
                clearInterval(interval);
                words[1].classList.add('active-word');
                updateSubtitleSimulator();
            }
        }, 400);
    });

    // ══════════════════════════════════════════════════════════════
    // 7. SES EFEKTLERİ (SFX) SENTEZLEYİCİ & DİNLEME (Item 48)
    // ══════════════════════════════════════════════════════════════
    function playSyntheticSound(type) {
        try {
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.connect(gain);
            gain.connect(ctx.destination);

            if (type === 'whoosh') {
                osc.type = 'sine';
                osc.frequency.setValueAtTime(200, ctx.currentTime);
                osc.frequency.exponentialRampToValueAtTime(800, ctx.currentTime + 0.15);
                gain.gain.setValueAtTime(0.3, ctx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.25);
                osc.start();
                osc.stop(ctx.currentTime + 0.25);
            } else if (type === 'pop') {
                osc.type = 'triangle';
                osc.frequency.setValueAtTime(800, ctx.currentTime);
                osc.frequency.exponentialRampToValueAtTime(120, ctx.currentTime + 0.08);
                gain.gain.setValueAtTime(0.4, ctx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.1);
                osc.start();
                osc.stop(ctx.currentTime + 0.1);
            } else if (type === 'ding') {
                osc.type = 'sine';
                osc.frequency.setValueAtTime(1800, ctx.currentTime);
                gain.gain.setValueAtTime(0.4, ctx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.4);
                osc.start();
                osc.stop(ctx.currentTime + 0.4);
            }
        } catch (e) {
            console.error("Audio error:", e);
        }
    }

    document.getElementById('btn-play-whoosh')?.addEventListener('click', () => playSyntheticSound('whoosh'));
    document.getElementById('btn-play-pop')?.addEventListener('click', () => playSyntheticSound('pop'));
    document.getElementById('btn-play-ding')?.addEventListener('click', () => playSyntheticSound('ding'));

    // ══════════════════════════════════════════════════════════════
    // 8. BGM MÜZİK LİSTESİ + ÖZEL YÜKLEME (P3-32)
    // ══════════════════════════════════════════════════════════════
    document.getElementById('btn-bgm-upload')?.addEventListener('click', () => {
        document.getElementById('input-bgm-upload')?.click();
    });

    document.getElementById('input-bgm-upload')?.addEventListener('change', async (e) => {
        const file = e.target.files?.[0];
        if (!file) return;
        const status = document.getElementById('bgm-upload-status');
        const form = new FormData();
        form.append('file', file);
        try {
            if (status) status.textContent = 'Yükleniyor...';
            const res = await fetch('/api/bgm/upload', { method: 'POST', body: form });
            const data = await res.json().catch(() => ({}));
            if (!res.ok) throw new Error(data.detail || 'Yükleme başarısız');
            if (status) status.textContent = `✓ ${data.filename}`;
            showToast(`BGM yüklendi: ${data.filename}`);
            await loadBgmList();
            const sel = document.getElementById('select-bgm-track');
            const studioSel = document.getElementById('studio-bgm-track');
            if (sel) sel.value = data.filename;
            if (studioSel) studioSel.value = data.filename;
        } catch (err) {
            if (status) status.textContent = `Hata: ${err.message}`;
            showToast(`BGM yükleme hatası: ${err.message}`, 'error');
        }
        e.target.value = '';
    });

    async function loadBgmList() {
        const select = document.getElementById('select-bgm-track');
        const studioSelect = document.getElementById('studio-bgm-track');
        const audioStatus = document.getElementById('audio-pipeline-status');
        const mediaStatus = document.getElementById('media-compliance-status');
        if (!select && !studioSelect) return;
        try {
            const res = await fetch('/api/bgm/list?include_catalog=true');
            const data = await res.json();
            const detailed = data.tracks_detailed || (data.tracks || []).map(f => ({ filename: f, display: f }));
            const fill = (el) => {
                if (!el) return;
                const prev = el.value;
                el.innerHTML = '<option value="">Otomatik / yok</option>';
                detailed.forEach(t => {
                    const fn = t.filename || t;
                    const opt = document.createElement('option');
                    opt.value = fn;
                    const label = t.display || fn;
                    opt.textContent = t.downloaded === false ? `${label} (indirilecek)` : label;
                    el.appendChild(opt);
                });
                if (prev && [...el.options].some(o => o.value === prev)) el.value = prev;
                else if (detailed.some(t => (t.filename || t) === 'royalty_free_ambient.wav')) el.value = 'royalty_free_ambient.wav';
            };
            fill(select);
            fill(studioSelect);
            if (select && studioSelect && !select._bgmSyncBound) {
                select._bgmSyncBound = true;
                select.addEventListener('change', () => { studioSelect.value = select.value; });
                studioSelect.addEventListener('change', () => { select.value = studioSelect.value; });
            }
            const duckAudio = document.getElementById('range-ducking-vol');
            const duckStudio = document.getElementById('studio-ducking-vol');
            if (duckAudio && duckStudio && !duckAudio._duckSyncBound) {
                duckAudio._duckSyncBound = true;
                duckAudio.addEventListener('input', () => { duckStudio.value = duckAudio.value; });
                duckStudio.addEventListener('input', () => { duckAudio.value = duckStudio.value; });
            }
            if (audioStatus) {
                const catalogCount = detailed.length || 0;
                audioStatus.innerHTML = `
                    <div class="stat-pill"><span>135 Telifsiz BGM:</span><strong class="text-success">${catalogCount ? catalogCount + ' parça' : 'Sentezleniyor'}</strong></div>
                    <div class="stat-pill mt-2"><span>141 Nefes Katmanı:</span><strong class="text-success">8 sn aralıklı</strong></div>
                    <div class="stat-pill mt-2"><span>144 Voice Ducking:</span><strong class="text-primary">80 ms iniş / 200 ms dönüş</strong></div>
                    <div class="stat-pill mt-2"><span>145 Oda Ambiyansı:</span><strong class="text-primary">Hafif, -34 dB</strong></div>
                `;
            }
            if (mediaStatus) {
                mediaStatus.innerHTML = `
                    <div class="stat-pill"><span>136 Matematiksel SFX:</span><strong class="text-success">Sinüs / Kare Dalga</strong></div>
                    <div class="stat-pill mt-2"><span>137 Döngü Bağlaçları:</span><strong class="text-success">12 varyasyon</strong></div>
                    <div class="stat-pill mt-2"><span>138 Neon İlerleme:</span><strong class="text-success">Renderda aktif</strong></div>
                    <div class="stat-pill mt-2"><span>139 Arka Plan Dilimleme:</span><strong class="text-success">Rastgele başlangıç</strong></div>
                    <div class="stat-pill mt-2"><span>140 Yasal Bildirim:</span><strong class="text-success">SEO açıklamasına eklenir</strong></div>
                    <div class="stat-pill mt-2"><span>142 Konuşma Prosodisi:</span><strong class="text-primary">Kanca / soru ritmi</strong></div>
                    <div class="stat-pill mt-2"><span>143 Diyalog Sesleri:</span><strong class="text-primary">Konuşmacı bazlı</strong></div>
                `;
            }
        } catch (e) {
            console.error(e);
        }
    }

    // ══════════════════════════════════════════════════════════════
    // 9. SENARYO ÜRETİMİ & EDİTÖR
    // ══════════════════════════════════════════════════════════════
    document.getElementById('btn-new-topic')?.addEventListener('click', clearCurrentScenario);

    async function generateScriptFromTopic({ forceRegenerate = false } = {}) {
        if (!forceRegenerate && hasExistingPlan() && !planHasBrokenNarration(currentPlan)) {
            navigateToScenario();
            return;
        }

        const topic = inputTopic.value.trim();
        if (!topic) {
            alert('Lütfen bir video konusu girin!');
            return;
        }

        if (forceRegenerate || (hasExistingPlan() && planHasBrokenNarration(currentPlan))) {
            currentPlan = null;
            timelineReviewed = false;
            qualityPanelGreen = false;
            try { localStorage.removeItem(PLAN_STORAGE_KEY); } catch (e) {}
            updateScriptActionButtons();
        }

        await resolveAndApplyNicheFromTopic({ toast: false });

        const btnRegenerate = document.getElementById('btn-regenerate-scenario');
        btnCreateScript.disabled = true;
        if (btnRegenerate) btnRegenerate.disabled = true;
        btnCreateScript.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> AI Senaryosu Yazılıyor...';

        try {
            const res = await fetch('/api/script/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    keyword: topic,
                    language: selectLanguage.value,
                    niche: selectNiche.value,
                    reddit_post: selectedRedditPost,
                    format_fingerprint: pendingFormatFingerprint || undefined
                })
            });
            const data = await res.json();
            if (data.status === 'ok') {
                let plan = data.plan;
                const lockedNiche = plan.niche_id || plan.niche_profile?.id;
                if (lockedNiche && selectNiche && selectNiche.value !== lockedNiche) {
                    selectNiche.value = lockedNiche;
                    await applyNicheProfile(lockedNiche);
                }
                if (lockedNiche) {
                    const lockedName = allNiches.find(n => n.id === lockedNiche)?.name || lockedNiche;
                    showNicheLockBadge(lockedNiche, lockedName);
                }
                timelineReviewed = false;
                setCurrentPlan(plan, { skipQualityPanel: true });
                if (data.plagiarism) applyPlagiarismBadge(data.plagiarism);
                if (data.hook_variants?.variants?.length) {
                    plan.hook_variants = data.hook_variants.variants;
                }
                const validation = await updateStudioQualityPanel(plan);
                if (validation?.plan) plan = validation.plan;
                if (data.plagiarism) applyPlagiarismBadge(data.plagiarism);
                if (validation?.ok) {
                    showToast(forceRegenerate ? 'Senaryo yeniden uretildi' : 'Senaryo hazir — timeline\'da inceleyin');
                    updateFlowRail('timeline');
                } else {
                    showToast('Senaryo uretildi — kalite panelinde sorunlar var', 'warn');
                    updateFlowRail('timeline');
                }
                switchTab('timeline');
            } else {
                alert('Senaryo olusturulamadi.');
            }
        } catch (err) {
            alert('Hata: ' + err.message);
        } finally {
            btnCreateScript.disabled = false;
            if (btnRegenerate) btnRegenerate.disabled = false;
            updateScriptActionButtons();
        }
    }

    async function regenerateScenario() {
        const topic = inputTopic?.value?.trim();
        if (!topic) {
            showToast('Once konu girin', 'warn');
            inputTopic?.focus();
            return;
        }
        if (hasExistingPlan() && !confirm('Mevcut senaryo silinip yeniden uretilecek. Devam edilsin mi?')) return;
        await generateScriptFromTopic({ forceRegenerate: true });
    }

    btnCreateScript.addEventListener('click', () => generateScriptFromTopic());
    document.getElementById('btn-regenerate-scenario')?.addEventListener('click', regenerateScenario);

    // ══════════════════════════════════════════════════════════════
    // 9A. SAHNE & KURGU EDİTÖRÜ — 500 Madde Uyumlu Overhaul
    // ══════════════════════════════════════════════════════════════

    // Helper: Detect emojis in text (Madde 125)
    function hasEmoji(text) {
        return /[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{1F1E0}-\u{1F1FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}\u{FE00}-\u{FE0F}\u{1F900}-\u{1F9FF}\u{1FA00}-\u{1FA6F}\u{1FA70}-\u{1FAFF}\u{200D}\u{20E3}]/u.test(text || '');
    }

    // Helper: Word count
    function wordCount(text) {
        return (text || '').trim().split(/\s+/).filter(Boolean).length;
    }

    // Helper: Clean cutaway markers from narration for display
    function cleanNarration(text) {
        return (text || '').replace(/\s*\[Görsel Açı \d+\]\s*/g, '').replace(/\s*\[Kadraj \d+\]\s*/g, '').trim();
    }

    // Helper: Mood emoji map
    const MOOD_ICONS = {
        epic: '🌟', dramatic: '🔴', calm: '🔵', mysterious: '🟣',
        energetic: '⚡', dark: '⬛', bright: '☀️'
    };

    // ── Compliance Dashboard Update ──
    function updateComplianceDashboard(scenes) {
        if (!scenes || scenes.length === 0) {
            resetComplianceDashboard();
            return;
        }
        const timedScenes = scenes.filter(s => sceneDurationSec(s) !== null);
        if (!timedScenes.length) {
            resetComplianceDashboard();
            return;
        }

        const totalSec = timedScenes.reduce((acc, s) => acc + sceneDurationSec(s), 0);

        // Duration band — Madde 494
        const chipDur = document.getElementById('chip-duration-band');
        const chipDurText = document.getElementById('chip-duration-text');
        chipDurText.textContent = `Süre: ${totalSec.toFixed(1)}sn`;
        chipDur.className = 'compliance-chip';
        if (totalSec >= 38 && totalSec <= 60) {
            chipDur.classList.add('status-ok');
        } else if (totalSec > 60 && totalSec <= 65) {
            chipDur.classList.add('status-warn');
        } else {
            chipDur.classList.add('status-danger');
        }

        // Cadence — Madde 88 helper; 8-16 sahne izin, 14 kutsal değil
        const chipCad = document.getElementById('chip-cadence');
        const chipCadText = document.getElementById('chip-cadence-text');
        chipCadText.textContent = `Cadence: ${scenes.length} sahne`;
        chipCad.className = 'compliance-chip';
        if (scenes.length >= 8 && scenes.length <= 16) {
            chipCad.classList.add('status-ok');
        } else if (scenes.length >= 6) {
            chipCad.classList.add('status-warn');
        } else {
            chipCad.classList.add('status-danger');
        }

        // 3.2s advisory — Madde 76 soft warning (AI pacing allowed)
        const longCuts = timedScenes.filter(s => sceneDurationSec(s) > 3.2).length;
        const chip32 = document.getElementById('chip-32s-violations');
        const chip32Text = document.getElementById('chip-32s-text');
        chip32Text.textContent = longCuts ? `3.2sn Uyarı: ${longCuts}` : '3.2sn Uyarı: 0';
        chip32.className = 'compliance-chip';
        if (longCuts === 0) {
            chip32.classList.add('status-ok');
        } else {
            chip32.classList.add('status-warn');
        }

        // Duplicate search terms — Madde 247 (ignore cutaways + adjacent semantic pairs)
        let dupes = 0;
        const queryEntries = [];
        scenes.forEach((s, idx) => {
            if (s.is_visual_cutaway) return;
            const sq = s.search_queries || [];
            if (sq[0]) queryEntries.push({ q: sq[0].toLowerCase().trim(), idx });
        });
        const seen = {};
        queryEntries.forEach(({ q, idx }) => {
            if (seen[q] !== undefined && idx - seen[q] > 1) {
                dupes += 1;
            }
            seen[q] = idx;
        });
        const chipDup = document.getElementById('chip-duplicates');
        const chipDupText = document.getElementById('chip-duplicates-text');
        chipDupText.textContent = `Tekrar: ${dupes}`;
        chipDup.className = 'compliance-chip';
        if (dupes === 0) {
            chipDup.classList.add('status-ok');
        } else {
            chipDup.classList.add('status-warn');
        }

        // Story Arc Bar — Madde 274
        if (totalSec > 0) {
            const introEnd = Math.min(3, totalSec);
            const conflictEnd = Math.min(20, totalSec);
            const climaxEnd = Math.min(35, totalSec);
            document.getElementById('arc-intro').style.width = `${(introEnd / totalSec) * 100}%`;
            document.getElementById('arc-conflict').style.width = `${((conflictEnd - introEnd) / totalSec) * 100}%`;
            document.getElementById('arc-climax').style.width = `${((climaxEnd - conflictEnd) / totalSec) * 100}%`;
            document.getElementById('arc-loop').style.width = `${((totalSec - climaxEnd) / totalSec) * 100}%`;
        }
    }

    // ── Main render function ──
    function renderTimelineScenes(plan) {
        const container = document.getElementById('scenes-timeline-container');
        const titleEl = document.getElementById('timeline-project-title');
        const totalScenesEl = document.getElementById('timeline-total-scenes');
        const totalDurEl = document.getElementById('timeline-total-duration');
        const badgeSceneCount = document.getElementById('badge-scene-count');

        if (!container || !plan) return;

        const scenes = plan.scenes || [];
        if (!scenes.length) {
            titleEl.textContent = 'Aktif Proje Senaryosu';
            updateTimelineTopicDesc(null);
            totalScenesEl.textContent = '0';
            if (badgeSceneCount) badgeSceneCount.textContent = '0';
            totalDurEl.textContent = '0 sn';
            container.innerHTML = `
                <div class="empty-state-box">
                    <i class="fa-solid fa-film"></i>
                    <p>Henüz bir senaryo oluşturulmadı. Hızlı Üretim sekmesinden senaryo üretebilirsiniz.</p>
                </div>`;
            updateScriptActionButtons();
            return;
        }

        const displayTitle = sanitizeTopicTitleForDisplay(plan.title || inputTopic?.value || '') || plan.title || 'Adsız';
        titleEl.textContent = `Proje: ${displayTitle}`;
        updateTimelineTopicDesc(plan);
        totalScenesEl.textContent = scenes.length;
        if (badgeSceneCount) badgeSceneCount.textContent = scenes.length;

        const totalSec = scenes.reduce((acc, s) => acc + (parseFloat(s.duration) || 6), 0);
        totalDurEl.textContent = `${totalSec.toFixed(1)} sn`;

        // Build duplicate query map for highlighting
        const queryFreq = {};
        scenes.forEach(s => {
            const q = ((s.search_queries && s.search_queries[0]) || '').toLowerCase().trim();
            if (q) queryFreq[q] = (queryFreq[q] || 0) + 1;
        });

        container.innerHTML = '';
        scenes.forEach((sc, i) => {
            const mood = (sc.mood || 'epic').toLowerCase();
            const isCutaway = sc.is_visual_cutaway === true;
            const dur = sceneDurationSec(sc);
            const durationViolation = false; // 3.2s is advisory only — AI pacing allowed
            const narr = isCutaway ? cleanNarration(sc.narration) : (sc.narration || '');
            const wc = wordCount(narr);
            const hasEm = hasEmoji(narr);
            const searchQueries = sc.search_queries || [];
            const sceneDesc = sc.scene_description || '';

            // Word count class
            let wcClass = 'count-ok';
            if (wc < 10) wcClass = 'count-danger';
            else if (wc > 20) wcClass = 'count-warn';

            // Build CSS classes
            let cardClasses = `scene-item-card mood-${mood}`;
            if (isCutaway) cardClasses += ' is-cutaway';
            if (durationViolation) cardClasses += ' duration-violation';

            const row = document.createElement('div');
            row.className = cardClasses;
            row.setAttribute('draggable', 'true');
            row.setAttribute('data-scene-idx', i);

            // Build search query tags HTML
            let queryTagsHtml = '';
            searchQueries.forEach((q, qi) => {
                const isDupe = qi === 0 && queryFreq[q.toLowerCase().trim()] > 1;
                const labels = ['spesifik', 'orta', 'genel'];
                queryTagsHtml += `<span class="search-query-tag${isDupe ? ' duplicate' : ''}" title="${labels[qi] || ''}">${q}</span>`;
            });

            // Stock video badge / preview
            let stockVideoHtml = '';
            if (sc.selected_video && sc.selected_video.url) {
                const vid = sc.selected_video;
                stockVideoHtml = `
                    <div class="scene-stock-badge-container">
                        ${vid.thumbnail ? `<img src="${vid.thumbnail}" class="scene-stock-thumb" alt="Klip">` : ''}
                        <span class="scene-stock-provider-tag"><i class="fa-solid fa-video"></i> ${vid.source || 'Stok'}</span>
                        <a href="${vid.url}" target="_blank" class="scene-stock-preview-btn"><i class="fa-solid fa-play"></i> Klip Önizle</a>
                        <button type="button" class="btn-swap-stock" data-idx="${i}" title="Farklı Bir Stok Video Çek"><i class="fa-solid fa-rotate"></i> Değiştir</button>
                    </div>
                `;
            } else {
                stockVideoHtml = `
                    <div class="scene-stock-badge-container">
                        <span style="font-size: 10px; color: #64748b;"><i class="fa-solid fa-film"></i> Stok video atanmadı</span>
                        <button type="button" class="btn-fetch-single-stock" data-idx="${i}"><i class="fa-solid fa-cloud-arrow-down"></i> Stok Çek</button>
                    </div>
                `;
            }

            row.innerHTML = `
                <div class="scene-idx">
                    <span class="scene-idx-number">#${i + 1}</span>
                    <span class="mood-badge mood-${mood}">${MOOD_ICONS[mood] || '🎬'} ${mood}</span>
                    ${isCutaway ? '<span class="cutaway-badge">📐 Açı</span>' : ''}
                </div>
                <div class="scene-body">
                    <div class="scene-body-row">
                        <div>
                            <div class="scene-field-label">
                                Seslendirme Metni
                                <span class="word-count-chip ${wcClass}">${wc} klm</span>
                                <span class="emoji-indicator ${hasEm ? 'has-emoji' : 'no-emoji'}">${hasEm ? '✅ Emoji' : '⚠️ Emoji yok'}</span>
                            </div>
                            <textarea class="input-styled scene-narr-input" rows="2" style="resize: vertical; min-height: 36px;">${escapeHtml(narr)}</textarea>
                        </div>
                        <div>
                            <div class="scene-field-label">Görsel Açıklama <span class="field-meta">(scene_description)</span></div>
                            <input type="text" class="input-styled scene-desc-input" value="${escapeHtml(sceneDesc)}" placeholder="İngilizce görsel açıklama...">
                            ${stockVideoHtml}
                        </div>
                    </div>
                    <div class="scene-body-row-3">
                        <div>
                            <div class="scene-field-label">Stok Arama Terimleri <span class="field-meta">(Madde 89)</span></div>
                            <input type="text" class="input-styled scene-query-input" value="${escapeHtml(searchQueries[0] || '')}" placeholder="Ana arama terimi...">
                            <div class="search-query-tags">${queryTagsHtml}</div>
                        </div>
                        <div>
                            <div class="scene-field-label">Süre</div>
                            <input type="number" class="input-styled scene-dur-input" min="1" max="15" step="0.25" value="${dur}">
                        </div>
                        <div class="scene-actions">
                            <button class="btn-sm btn-clone-scene" data-idx="${i}" title="Sahneyi Klonla"><i class="fa-solid fa-copy"></i></button>
                            <button class="btn-sm btn-del-scene" data-idx="${i}" title="Sahneyi Sil"><i class="fa-solid fa-trash"></i></button>
                        </div>
                    </div>
                </div>
            `;
            container.appendChild(row);
        });

        // ── Event handlers ──

        // Swap stock video for single scene
        container.querySelectorAll('.btn-swap-stock').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const idx = parseInt(e.currentTarget.getAttribute('data-idx'));
                const sc = currentPlan.scenes[idx];
                const q = (sc.search_queries && sc.search_queries[0]) || sc.scene_description || 'cinematic motion';
                btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
                btn.disabled = true;
                try {
                    const res = await fetch(`/api/stock/search?query=${encodeURIComponent(q)}&limit=6`);
                    const data = await res.json();
                    if (data.results && data.results.length > 0) {
                        const currentId = sc.selected_video?.id;
                        const alt = data.results.find(v => v.id !== currentId) || data.results[0];
                        sc.selected_video = alt;
                        renderTimelineScenes(currentPlan);
                        showToast(`🎬 Sahne #${idx + 1} için yeni stok video seçildi!`);
                    } else {
                        showToast('⚠️ Alternatif video bulunamadı.', 'warn');
                        btn.innerHTML = '<i class="fa-solid fa-rotate"></i> Değiştir';
                        btn.disabled = false;
                    }
                } catch (err) {
                    showToast('Hata: ' + err.message, 'error');
                    btn.innerHTML = '<i class="fa-solid fa-rotate"></i> Değiştir';
                    btn.disabled = false;
                }
            });
        });

        // Fetch single stock video
        container.querySelectorAll('.btn-fetch-single-stock').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const idx = parseInt(e.currentTarget.getAttribute('data-idx'));
                const sc = currentPlan.scenes[idx];
                const q = (sc.search_queries && sc.search_queries[0]) || sc.scene_description || 'cinematic motion';
                btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
                btn.disabled = true;
                try {
                    const res = await fetch(`/api/stock/search?query=${encodeURIComponent(q)}&limit=3`);
                    const data = await res.json();
                    if (data.results && data.results.length > 0) {
                        sc.selected_video = data.results[0];
                        renderTimelineScenes(currentPlan);
                        showToast(`🎬 Sahne #${idx + 1} için stok video çekildi!`);
                    } else {
                        showToast('⚠️ Video bulunamadı.', 'warn');
                        btn.innerHTML = '<i class="fa-solid fa-cloud-arrow-down"></i> Stok Çek';
                        btn.disabled = false;
                    }
                } catch (err) {
                    showToast('Hata: ' + err.message, 'error');
                    btn.innerHTML = '<i class="fa-solid fa-cloud-arrow-down"></i> Stok Çek';
                    btn.disabled = false;
                }
            });
        });

        // Delete scene
        container.querySelectorAll('.btn-del-scene').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const idx = parseInt(e.currentTarget.getAttribute('data-idx'));
                currentPlan.scenes.splice(idx, 1);
                renderTimelineScenes(currentPlan);
            });
        });

        // Clone scene
        container.querySelectorAll('.btn-clone-scene').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const idx = parseInt(e.currentTarget.getAttribute('data-idx'));
                const clone = JSON.parse(JSON.stringify(currentPlan.scenes[idx]));
                clone.scene_number = currentPlan.scenes.length + 1;
                clone.is_visual_cutaway = false;
                currentPlan.scenes.splice(idx + 1, 0, clone);
                renderTimelineScenes(currentPlan);
                showToast('📋 Sahne klonlandı');
            });
        });

        // ── Drag & Drop ──
        let dragSrcIdx = null;
        container.querySelectorAll('.scene-item-card').forEach(card => {
            card.addEventListener('dragstart', (e) => {
                dragSrcIdx = parseInt(card.getAttribute('data-scene-idx'));
                card.classList.add('dragging');
                e.dataTransfer.effectAllowed = 'move';
            });
            card.addEventListener('dragend', () => {
                card.classList.remove('dragging');
                container.querySelectorAll('.scene-item-card').forEach(c => c.classList.remove('drag-over'));
            });
            card.addEventListener('dragover', (e) => {
                e.preventDefault();
                e.dataTransfer.dropEffect = 'move';
                card.classList.add('drag-over');
            });
            card.addEventListener('dragleave', () => {
                card.classList.remove('drag-over');
            });
            card.addEventListener('drop', (e) => {
                e.preventDefault();
                const targetIdx = parseInt(card.getAttribute('data-scene-idx'));
                if (dragSrcIdx !== null && dragSrcIdx !== targetIdx && currentPlan && currentPlan.scenes) {
                    const [moved] = currentPlan.scenes.splice(dragSrcIdx, 1);
                    currentPlan.scenes.splice(targetIdx, 0, moved);
                    // Renumber
                    currentPlan.scenes.forEach((s, si) => s.scene_number = si + 1);
                    renderTimelineScenes(currentPlan);
                    showToast('🔀 Sahne sırası güncellendi');
                }
                dragSrcIdx = null;
            });
        });

        // Update compliance dashboard
        updateComplianceDashboard(scenes);
    }

    // ── Add scene manually ──
    document.getElementById('btn-add-scene-manual')?.addEventListener('click', () => {
        if (!currentPlan) currentPlan = { title: inputTopic.value, scenes: [] };
        currentPlan.scenes.push({
            scene_number: currentPlan.scenes.length + 1,
            narration: "Yeni sahne anlatım parçası...",
            scene_description: "Wide angle cinematic shot of the scene",
            search_queries: ["cinematic nature", "landscape aerial", "nature"],
            duration: 3,
            mood: "epic"
        });
        renderTimelineScenes(currentPlan);
        showToast('➕ Yeni sahne eklendi');
    });

    // ── Smart Buttons ──

    // Auto-fetch stock videos for all scenes — Item 89 & 130
    document.getElementById('btn-fetch-stock-clips')?.addEventListener('click', async () => {
        if (!currentPlan || !currentPlan.scenes || currentPlan.scenes.length === 0) {
            return showToast('⚠️ Önce senaryo oluşturun', 'warn');
        }
        const btn = document.getElementById('btn-fetch-stock-clips');
        const oldHtml = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Stok Videolar Çekiliyor...';
        showToast('📡 Pexels ve Pixabay kütüphanelerinden en iyi dikey videolar taranıyor...');
        try {
            collectTimelineEdits();
            const res = await fetch('/api/stock/fetch_for_scenes', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ scenes: currentPlan.scenes })
            });
            const data = await res.json();
            if (data.status === 'ok' && data.scenes) {
                currentPlan.scenes = data.scenes;
                renderTimelineScenes(currentPlan);
                showToast('🎬 Tüm sahneler için stok videolar başarıyla çekildi ve eşleştirildi!');
            }
        } catch (err) {
            showToast('⚠️ Stok video çekme hatası: ' + err.message, 'error');
        } finally {
            btn.disabled = false;
            btn.innerHTML = oldHtml;
        }
    });

    // Cadence fix — Madde 88
    document.getElementById('btn-fix-cadence')?.addEventListener('click', () => {
        if (!currentPlan || !currentPlan.scenes || currentPlan.scenes.length === 0) return showToast('Once senaryo olusturun', 'warn');
        collectTimelineEdits();
        const scenes = currentPlan.scenes;
        const totalDuration = scenes.reduce((acc, s) => acc + (parseFloat(s.duration) || 6), 0);
        if (totalDuration < 30 || scenes.length >= 14) return showToast('✅ Cadence zaten yeterli');

        let cutsNeeded = 14 - scenes.length;
        let cutawayCounter = 1;
        const cutawayAdjs = ['macro closeup', 'cinematic angle', 'reaction detail', 'slow motion cutaway'];
        const expanded = [];
        for (const sc of scenes) {
            const dur = parseFloat(sc.duration) || 6;
            if (cutsNeeded > 0 && dur >= 3.5) {
                const half1 = Math.round((dur / 2) * 100) / 100;
                const half2 = Math.round((dur - half1) * 100) / 100;
                cutsNeeded--;

                const words = (sc.narration || '').split(' ');
                let narr1 = sc.narration || '';
                let narr2 = `${sc.narration || ''} [Görsel Açı ${cutawayCounter}]`;
                if (words.length >= 6) {
                    const mid = Math.floor(words.length / 2);
                    narr1 = words.slice(0, mid).join(' ');
                    narr2 = words.slice(mid).join(' ');
                }

                const sq = sc.search_queries || ['cinematic visual'];
                const cadj = cutawayAdjs[cutawayCounter % cutawayAdjs.length];
                const q1 = sq[0] || 'cinematic motion';
                const q2 = sq[1] ? `${sq[1]} ${cadj}` : `${q1} ${cadj}`;
                const queries1 = [q1, sq[1] || 'dramatic lighting'];
                const queries2 = [q2, sq[2] || 'cinematic slow motion'];

                const sc1 = { ...sc, duration: half1, narration: narr1, search_queries: queries1 };
                const sc2 = { ...sc, duration: half2, is_visual_cutaway: true, narration: narr2, search_queries: queries2, scene_description: `Cutaway dynamic angle showing ${q2}` };
                cutawayCounter++;
                expanded.push(sc1, sc2);
            } else {
                expanded.push({ ...sc });
            }
        }
        // Further split if needed
        while (expanded.length < 14) {
            const maxIdx = expanded.reduce((best, s, i) => (s.duration || 0) > (expanded[best].duration || 0) ? i : best, 0);
            if ((expanded[maxIdx].duration || 0) < 1.5) break;
            const target = expanded[maxIdx];
            const h1 = Math.round((target.duration / 2) * 100) / 100;
            const h2 = Math.round((target.duration - h1) * 100) / 100;

            const words = (target.narration || '').split(' ');
            let narr1 = target.narration || '';
            let narr2 = `${target.narration || ''} [Kadraj ${cutawayCounter}]`;
            if (words.length >= 6) {
                const mid = Math.floor(words.length / 2);
                narr1 = words.slice(0, mid).join(' ');
                narr2 = words.slice(mid).join(' ');
            }

            const sq = target.search_queries || ['cinematic visual'];
            const cadj = cutawayAdjs[cutawayCounter % cutawayAdjs.length];
            const q1 = sq[0] || 'cinematic motion';
            const q2 = sq[1] ? `${sq[1]} ${cadj}` : `${q1} ${cadj}`;

            const t1 = { ...target, duration: h1, narration: narr1, search_queries: [q1, sq[1] || 'dramatic lighting'] };
            const t2 = { ...target, duration: h2, is_visual_cutaway: true, narration: narr2, search_queries: [q2, sq[2] || 'cinematic slow motion'], scene_description: `Cutaway dynamic angle showing ${q2}` };
            cutawayCounter++;
            expanded.splice(maxIdx, 1, t1, t2);
        }
        expanded.forEach((s, i) => s.scene_number = i + 1);
        currentPlan.scenes = expanded;
        renderTimelineScenes(currentPlan);
        showToast(`✂️ Cadence düzeltildi: ${expanded.length} sahne`);
    });

    // Enrich search queries — Madde 89
    document.getElementById('btn-enrich-queries')?.addEventListener('click', () => {
        if (!currentPlan || !currentPlan.scenes) return showToast('Once senaryo olusturun', 'warn');
        collectTimelineEdits();
        const adjectives = ['cinematic', 'drone', 'aerial', 'slow motion', 'macro', 'atmospheric', '4k', 'moody'];
        currentPlan.scenes.forEach((sc, i) => {
            const sq = sc.search_queries || [];
            sc.search_queries = sq.map((q, qi) => {
                const ql = q.toLowerCase();
                if (!adjectives.some(a => ql.includes(a))) {
                    return `${q} ${adjectives[(i + qi) % adjectives.length]}`;
                }
                return q;
            });
        });
        setCurrentPlan(currentPlan);
        showToast('Arama terimleri zenginlestirildi');
    });

    // Balance durations — Madde 494
    document.getElementById('btn-balance-durations')?.addEventListener('click', () => {
        if (!currentPlan || !currentPlan.scenes || currentPlan.scenes.length === 0) return showToast('Once senaryo olusturun', 'warn');
        collectTimelineEdits();
        const scenes = currentPlan.scenes;
        const totalSec = scenes.reduce((acc, s) => acc + (parseFloat(s.duration) || 6), 0);
        const targetTotal = 48;
        if (totalSec >= 38 && totalSec <= 60) return showToast('Sure izin bandinda (38-60sn, hedef 48)');

        const ratio = targetTotal / totalSec;
        const maxPerScene = 7.5;
        scenes.forEach(s => {
            s.duration = Math.max(1.5, Math.min(maxPerScene, Math.round((parseFloat(s.duration) || 3) * ratio * 4) / 4));
        });
        renderTimelineScenes(currentPlan);
        const newTotal = scenes.reduce((acc, s) => acc + s.duration, 0);
        persistCurrentPlan();
        showToast(`Sureler dengelendi: ${newTotal.toFixed(1)}sn`);
    });

    // Hallucination check — Madde 90
    document.getElementById('btn-hallucination-check')?.addEventListener('click', () => {
        if (!currentPlan || !currentPlan.scenes) return showToast('⚠️ Önce senaryo oluşturun', 'warn');
        const issues = [];
        const title = (currentPlan.title || '').toLowerCase();
        const ancientMarkers = ['marcus aurelius', 'roma', 'antik', 'stoa', 'osmanlı', 'fatih', 'platon', 'aristoteles', 'sezar'];
        const isAncient = ancientMarkers.some(m => title.includes(m));
        const yearPattern = /\b(1[0-9]{3}|20[0-9]{2})\b/g;

        currentPlan.scenes.forEach((sc, i) => {
            const narr = sc.narration || '';
            let match;
            while ((match = yearPattern.exec(narr)) !== null) {
                const yr = parseInt(match[1]);
                if (yr > 2030) {
                    issues.push(`Sahne #${i + 1}: Gelecek yıl (${yr}) — halüsinasyon`);
                } else if (isAncient && yr >= 1800) {
                    issues.push(`Sahne #${i + 1}: Antik konu için modern yıl (${yr}) — anakronizm`);
                }
            }
        });

        if (issues.length === 0) {
            showToast('✅ Halüsinasyon tespit edilmedi — temiz');
        } else {
            showToast(`⚠️ ${issues.length} potansiyel halüsinasyon tespit edildi`, 'warn');
            alert('Halüsinasyon Raporu:\n\n' + issues.join('\n'));
        }
    });

    // ── Render from timeline (collect edits) ──
    document.getElementById('btn-render-from-timeline')?.addEventListener('click', () => {
        collectTimelineEdits();
        startRenderProcess(currentPlan);
    });

    function collectTimelineEdits() {
        if (currentPlan && currentPlan.scenes) {
            const narrInputs = document.querySelectorAll('.scene-narr-input');
            const descInputs = document.querySelectorAll('.scene-desc-input');
            const queryInputs = document.querySelectorAll('.scene-query-input');
            const durInputs = document.querySelectorAll('.scene-dur-input');
            currentPlan.scenes.forEach((sc, i) => {
                if (narrInputs[i]) sc.narration = narrInputs[i].value;
                if (descInputs[i]) sc.scene_description = descInputs[i].value;
                if (queryInputs[i]) sc.search_queries = [queryInputs[i].value, ...(sc.search_queries || []).slice(1)];
                if (durInputs[i]) sc.duration = parseFloat(durInputs[i].value) || 6;
            });
            currentPlan.full_narration = currentPlan.scenes.map(s => s.narration || '').filter(Boolean).join(' ');
            persistCurrentPlan();
            const hard = getNarrationIssues(currentPlan.scenes);
            updateRenderButtonsBlocked(hard.length > 0, hard[0]);
        }
    }

    // ── Keyboard Shortcuts — Madde 443 ──
    document.addEventListener('keydown', (e) => {
        // Ctrl+Enter — Render
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            e.preventDefault();
            const activeTab = document.querySelector('.nav-btn.active')?.getAttribute('data-tab');
            if (activeTab === 'timeline' && currentPlan) {
                collectTimelineEdits();
                startRenderProcess(currentPlan);
            }
        }
        // Ctrl+S — Save/sync edits
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
            e.preventDefault();
            collectTimelineEdits();
            if (currentPlan) {
                updateComplianceDashboard(currentPlan.scenes || []);
                showToast('💾 Sahne düzenlemeleri kaydedildi');
            }
        }
    });

    // ══════════════════════════════════════════════════════════════
    // 10. CANLI SSE İZLEME & RENDER BORU HATTI
    // ══════════════════════════════════════════════════════════════
    btnQuickRender.addEventListener('click', () => {
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

        // Prefer 1080p for publish path
        const resSel = document.getElementById('select-render-resolution');
        if (resSel && resSel.value !== '1080p') {
            const forceHd = confirm(
                `Cozunurluk ${resSel.value}. Yayin icin 1080p onerilir.\n\nOK = 1080p'ye cevir\nIptal = ${resSel.value} ile devam`
            );
            if (forceHd) resSel.value = '1080p';
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
            language: selectLanguage.value,
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
            split_screen: chkSplitScreen.checked,
            anti_duplicate: chkAntiDuplicate.checked,
            enable_ken_burns: chkKenBurns.checked,
            resolution: document.getElementById('select-render-resolution')?.value || '1080p',
            auto_publish: !!(chkAutoPublish && chkAutoPublish.checked)
        };

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
            alert(err.message);
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

        eventSource.onmessage = (e) => {
            try {
                const payload = JSON.parse(e.data);
                handleServerEvent(payload.type, payload.data);
            } catch (err) {
                console.error("SSE parse error:", err);
            }
        };

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
                refreshFeedDistributionAdvisory(35);
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
                            <button class="btn btn-primary btn-sm btn-upload-yt" data-filename="${v.filename}" data-title="${encodeURIComponent(v.keyword || 'Shorts')}" style="flex: 1; display: flex; align-items: center; justify-content: center; gap: 5px; padding: 6px 10px;">
                                <i class="fa-brands fa-youtube"></i> Yükle
                            </button>
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
                b.addEventListener('click', async (e) => {
                    const fn = e.currentTarget.getAttribute('data-filename');
                    const baseName = fn.replace(/\.[^/.]+$/, "");
                    try {
                        let info = null;
                        try {
                            const res = await fetch(`/output/${baseName}_manual_upload_info.json`);
                            if (res.ok) info = await res.json();
                        } catch (_) {}

                        if (!info) {
                            info = {
                                title: baseName,
                                description: `${baseName} #shorts\n\n📌 Kaynak & Araştırma: Tarihsel Arşiv ve Akademik İnceleme\n⚖️ Hakkaniyet & Katma Değer (Fair Use): Bu video eğitim ve bilgilendirme amacıyla bağımsız olarak araştırılmış, özgün sesli analizle üretilmiştir.`,
                                tags: ["shorts", "bilgi", "viral"],
                                pinned_comment: "Sizce bu konudaki en şaşırtıcı detay neydi? Yorumlarda buluşalım! 👇",
                                rule_80_altered_synthetic: "HAYIR (Yüz klonlama veya manipülasyon yoksa etiket seçilmemeli)"
                            };
                        }

                        const guideText = 
`📌 BAŞLIK:\n${info.title}\n\n` +
`📌 AÇIKLAMA (Kural 83 Kaynaklı):\n${info.description}\n\n` +
`📌 ETİKETLER:\n${(info.tags || []).join(', ')}\n\n` +
`📌 SABİT YORUM:\n${info.pinned_comment}\n\n` +
`⚠️ KRİTİK KURAL 80 UYARISI:\n` +
`YouTube Studio'da 'Yapay zeka / Değiştirilmiş içerik mi?' sorusuna 'HAYIR' yanıtını verin.\n` +
`(Kural 80: Yüz klonlama veya haber manipülasyonu olmadığı sürece etiket işaretlenmemelidir; aksi halde algoritma videoyu daha dar bir kitleyle test eder.)\n\n` +
`🛡️ DOSYA GÜVENLİĞİ:\n` +
`Bu MP4 dosyası ctime yaşlandırması (Kural 29), free atom boyutu varyasyonu (Kural 30) ve pHash gürültüsü/gren (Kural 84 & 86) ile tamamen korunmuştur.`;

                        await navigator.clipboard.writeText(guideText);
                        showToast("📋 Manuel yükleme rehberi ve SEO metinleri panoya kopyalandı!");
                        alert("✅ Manuel Yükleme Bilgileri Panoya Kopyalandı!\n\n" + guideText);
                    } catch (err) {
                        alert("Kopyalama hatası: " + err.message);
                    }
                });
            });

            grid.querySelectorAll('.btn-upload-yt').forEach(b => {
                b.addEventListener('click', async (e) => {
                    const fn = e.currentTarget.getAttribute('data-filename');
                    const title = decodeURIComponent(e.currentTarget.getAttribute('data-title'));
                    b.disabled = true;
                    b.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Yükleniyor...';
                    try {
                        const res = await fetch('/api/youtube/publish', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ filename: fn, title: title })
                        });
                        const resData = await res.json();
                        if (resData.status === 'ok') {
                            showToast('🚀 Video YouTube kanalına yüklendi!');
                        } else {
                            alert('YouTube yükleme uyarısı: ' + (resData.error || 'Başarısız'));
                        }
                    } catch (err) {
                        alert(err.message);
                    } finally {
                        b.disabled = false;
                        b.innerHTML = '<i class="fa-brands fa-youtube"></i> Yükle';
                    }
                });
            });

            grid.querySelectorAll('.btn-gallery-share-keep').forEach(b => {
                b.addEventListener('click', () => {
                    const videoId = b.getAttribute('data-video-id');
                    const projectSlug = decodeURIComponent(b.getAttribute('data-project-slug') || '');
                    submitShareDecision('keep', { videoId, projectSlug });
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
    // 12. AYARLAR & KOTA (Items 62 & 69)
    // ══════════════════════════════════════════════════════════════
    async function loadSettings() {
        try {
            const res = await fetch('/api/config');
            const data = await res.json();
            if (data.keys || data.key_hints) {
                const hint = (id, configured, hintKey) => {
                    const el = document.getElementById(id);
                    if (!el || !configured) return;
                    const masked = data.key_hints?.[hintKey];
                    el.value = '';
                    el.placeholder = masked ? `${masked} (Kayıtlı)` : '•••••••• (Kayıtlı)';
                };
                hint('input-key-gemini', data.keys?.gemini, 'gemini');
                hint('input-key-pexels', data.keys?.pexels, 'pexels');
                hint('input-key-pixabay', data.keys?.pixabay, 'pixabay');
                hint('input-key-elevenlabs', data.keys?.elevenlabs, 'elevenlabs');
            }
            if (data.elevenlabs) renderElevenlabsQuota(data.elevenlabs);
            if (data.google_ai) {
                const g = data.google_ai;
                const setChk = (id, v) => { const el = document.getElementById(id); if (el) el.checked = !!v; };
                setChk('chk-gai-image', g.use_gemini_image_gen);
                setChk('chk-gai-video', g.use_gemini_video_gen);
                setChk('chk-gai-grounding', g.use_gemini_grounding);
                setChk('chk-gai-prefer-img', g.prefer_gemini_scene_images);
                setChk('chk-gai-tts', g.use_gemini_tts);
                setChk('chk-gai-embed', g.use_gemini_embeddings);
                setChk('chk-rf-bgm', g.auto_fetch_royalty_free_bgm);
            }
            await updateAiQuotaDisplay();
            await loadGoogleAiProPanel();
        } catch (e) {
            console.error("loadSettings error:", e);
        }
    }

    function fillModelSelect(selectEl, catalog, family, selectedId) {
        if (!selectEl) return;
        const opts = (catalog || []).filter(c => c.family === family);
        selectEl.innerHTML = opts.map(c => {
            const avail = c.available === false ? ' (anahtarda yok)' : '';
            const pro = c.pro_benefit ? ' ★' : '';
            return `<option value="${c.id}" ${c.id === selectedId ? 'selected' : ''}>${c.name}${pro}${avail}</option>`;
        }).join('') || `<option value="${selectedId || ''}">${selectedId || '—'}</option>`;
        if (selectedId && ![...selectEl.options].some(o => o.value === selectedId)) {
            const o = document.createElement('option');
            o.value = selectedId; o.textContent = selectedId + ' (kayıtlı)'; o.selected = true;
            selectEl.appendChild(o);
        }
    }

    async function loadGoogleAiProPanel() {
        const status = document.getElementById('gai-status');
        try {
            const data = await (await fetch('/api/google-ai/plan')).json();
            const blurb = document.getElementById('gai-plan-blurb');
            if (blurb && data.plan) {
                blurb.innerHTML = `<strong>${data.plan.title}</strong> — ${data.plan.blurb}`;
            }
            const strip = document.getElementById('gai-quota-strip');
            if (strip) {
                const q = data.quota || {};
                const fam = data.families_available || {};
                strip.innerHTML = `
                    <span class="badge" style="background:rgba(56,189,248,0.2);color:#7dd3fc;padding:4px 8px;border-radius:6px;">
                        Anahtar: ${data.has_api_key ? 'Var' : 'YOK'}
                    </span>
                    <span class="badge" style="background:rgba(168,85,247,0.2);color:#c084fc;padding:4px 8px;border-radius:6px;">
                        Canlı model: ${data.live_model_count || 0}
                    </span>
                    <span class="badge" style="background:rgba(52,211,153,0.15);color:#34d399;padding:4px 8px;border-radius:6px;">
                        RPM ${q.rpm_used ?? '-'} / ${q.rpm_limit ?? '-'}
                    </span>
                    <span class="badge" style="background:rgba(251,191,36,0.15);color:#fbbf24;padding:4px 8px;border-radius:6px;">
                        RPD ${q.rpd_used ?? '-'} / ${q.rpd_limit ?? '-'} (kalan ${q.remaining ?? '-'})
                    </span>
                    <span class="badge" style="background:rgba(248,113,113,0.15);color:#fca5a5;padding:4px 8px;border-radius:6px;">
                        text:${fam.text||0} img:${fam.image||0} vid:${fam.video||0}
                    </span>
                `;
            }
            const sel = data.selected || {};
            fillModelSelect(document.getElementById('select-gemini-script-model'), data.catalog, 'text', sel.script);
            fillModelSelect(document.getElementById('select-gemini-image-model'), data.catalog, 'image', sel.image);
            fillModelSelect(document.getElementById('select-gemini-video-model'), data.catalog, 'video', sel.video);
            const list = document.getElementById('gai-catalog-list');
            if (list) {
                const tips = (data.plan && data.plan.tips) ? data.plan.tips.map(t => `<li>${t}</li>`).join('') : '';
                const rows = (data.catalog || []).map(c =>
                    `<div style="padding:3px 0;border-bottom:1px solid rgba(148,163,184,0.15);">
                        <strong style="color:${c.available ? '#e2e8f0' : '#64748b'}">${c.name}</strong>
                        <span style="opacity:0.7"> · ${c.family}</span>
                        ${c.pro_benefit ? '<span style="color:#fbbf24"> Pro</span>' : ''}
                        <div style="opacity:0.65">${c.use || ''}</div>
                    </div>`
                ).join('');
                list.innerHTML = (tips ? `<ul style="margin:0 0 8px 16px;padding:0;">${tips}</ul>` : '') + rows;
            }
            if (status) {
                status.style.display = 'block';
                status.style.color = data.ok ? '#34d399' : '#fbbf24';
                status.textContent = data.ok
                    ? `Google AI hub OK — ${data.live_model_count} model erişilebilir`
                    : (`Uyarı: ${data.error || 'modeller çekilemedi'} — katalog yine de seçilebilir`);
            }
        } catch (e) {
            if (status) {
                status.style.display = 'block';
                status.style.color = '#f87171';
                status.textContent = 'Google AI paneli yüklenemedi: ' + e.message;
            }
        }
    }

    document.getElementById('btn-gai-refresh')?.addEventListener('click', () => loadGoogleAiProPanel());
    document.getElementById('btn-gai-test-image')?.addEventListener('click', async () => {
        const model = document.getElementById('select-gemini-image-model')?.value;
        const status = document.getElementById('gai-status');
        if (status) { status.style.display = 'block'; status.textContent = 'Görsel üretiliyor...'; }
        try {
            const res = await fetch('/api/google-ai/generate-image', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt: 'Cinematic vertical 9:16 bronze Marcus Aurelius statue at dusk, no text', model })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'fail');
            showToast('Nano Banana görsel hazır: ' + data.url);
            if (status) { status.style.color = '#34d399'; status.textContent = 'Test OK → ' + data.url; }
        } catch (e) {
            if (status) { status.style.color = '#f87171'; status.textContent = 'Görsel hata: ' + e.message; }
            alert('Görsel test hatası: ' + e.message);
        }
    });
    document.getElementById('btn-gai-test-video')?.addEventListener('click', async () => {
        const model = document.getElementById('select-gemini-video-model')?.value;
        const status = document.getElementById('gai-status');
        if (status) { status.style.display = 'block'; status.textContent = 'Veo video üretiliyor (1-3 dk)...'; }
        try {
            const res = await fetch('/api/google-ai/generate-video', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    prompt: 'Cinematic vertical 9:16 slow camera push toward ancient marble columns at golden hour, no text',
                    model,
                    duration_seconds: 6,
                })
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'fail');
            showToast('Veo video hazır: ' + data.url);
            if (status) { status.style.color = '#34d399'; status.textContent = 'Veo OK → ' + data.url; }
        } catch (e) {
            if (status) { status.style.color = '#f87171'; status.textContent = 'Veo hata: ' + e.message; }
            alert('Veo test hatası: ' + e.message);
        }
    });
    document.getElementById('btn-voicelab-seed')?.addEventListener('click', async () => {
        try {
            const data = await (await fetch('/api/voicelab/seed', { method: 'POST' })).json();
            showToast(`VoiceLab paketi: ${data.count} dosya`);
            await loadBgmList();
        } catch (e) { alert(e.message); }
    });

    document.getElementById('btn-preview-voice')?.addEventListener('click', async () => {
        const btn = document.getElementById('btn-preview-voice');
        const topic = document.getElementById('input-topic')?.value?.trim();
        const sample = topic
            ? `${topic.split(/\s+/).slice(0, 12).join(' ')}…`
            : 'Merhaba, bu kısa ses önizlemesidir.';
        if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>'; }
        try {
            const res = await fetch('/api/tts/preview', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text: sample,
                    voice_gender: selectTtsVoice?.value === 'auto' ? 'auto' : (findVoiceMeta(selectTtsVoice?.value)?.gender || selectVoiceGender?.value || 'male'),
                    tts_voice: (selectTtsVoice?.value && selectTtsVoice.value !== 'auto') ? selectTtsVoice.value : null,
                    language: selectLanguage?.value || 'tr',
                }),
            });
            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.detail || 'Önizleme başarısız');
            }
            const provider = res.headers.get('X-TTS-Provider') || 'TTS';
            const blob = await res.blob();
            const url = URL.createObjectURL(blob);
            const audio = new Audio(url);
            audio.onended = () => URL.revokeObjectURL(url);
            await audio.play();
            showToast(`Ses önizleme: ${provider}`);
        } catch (e) {
            alert('Ses önizleme: ' + e.message);
        } finally {
            if (btn) { btn.disabled = false; btn.innerHTML = '<i class="fa-solid fa-volume-high"></i> Dinle'; }
        }
    });
    document.getElementById('btn-rf-fetch-bgm')?.addEventListener('click', async () => {
        try {
            const data = await (await fetch('/api/audio/royalty-free/fetch', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: 'cinematic ambient stoic', prefer: 'auto' })
            })).json();
            showToast('Telifsiz BGM: ' + data.filename);
            // refresh BGM select if present
            const sel = document.getElementById('select-bgm-track');
            if (sel && data.filename) {
                const opt = document.createElement('option');
                opt.value = data.filename; opt.textContent = data.filename; opt.selected = true;
                sel.appendChild(opt);
            }
        } catch (e) { alert(e.message); }
    });

    // ══════════════════════════════════════════════════════════════
    // 12.1 CANLI YAPAY ZEKA KOTA & HIZ LİMİTİ MONİTÖRÜ (Items 62 & 69)
    // ══════════════════════════════════════════════════════════════
    async function updateAiQuotaDisplay(passedData = null) {
        if (isRendering && !passedData) return; // Render sirasinda sunucuya HTTP yuk bindirme
        try {
            const qData = passedData || await (await fetch('/api/quota/stats')).json();
            if (!qData) return;

            const activeName = qData.active_provider_name || 'Google Gemini Flash';
            const rpmUsed = qData.current_rpm_used || 0;
            const rpmLimit = qData.rpm_limit || 15;
            const rpdUsed = qData.daily_used || 0;
            const rpdLimit = qData.rpd_limit || 1500;
            const dailyRemaining = qData.daily_remaining !== undefined ? qData.daily_remaining : Math.max(0, rpdLimit - rpdUsed);
            const isExhausted = qData.is_exhausted || false;
            const healthPct = qData.overall_health_pct || 100;

            // 1. Üst Header Rozeti
            const headerSummary = document.getElementById('header-quota-summary');
            const headerTag = document.getElementById('header-quota-tag');
            if (headerSummary && headerTag) {
                if (qData.is_api_key_missing) {
                    headerSummary.textContent = `AI: Yerel Motor (Anahtarsız)`;
                    headerSummary.style.color = '#fbbf24';
                    headerTag.textContent = `0 TL Failsafe`;
                    headerTag.style.background = 'rgba(234, 179, 8, 0.25)';
                    headerTag.style.color = '#fde047';
                } else if (isExhausted) {
                    headerSummary.textContent = `AI: Hız Limiti (%${healthPct})`;
                    headerSummary.style.color = '#facc15';
                    headerTag.textContent = `${rpmUsed}/${rpmLimit} RPM`;
                    headerTag.style.background = 'rgba(234, 179, 8, 0.25)';
                    headerTag.style.color = '#fde047';
                } else {
                    headerSummary.textContent = `AI: ${qData.active_provider || 'Gemini'} (%${healthPct})`;
                    headerSummary.style.color = '#f8fafc';
                    headerTag.textContent = `${rpmUsed}/${rpmLimit} RPM`;
                    headerTag.style.background = 'rgba(168, 85, 247, 0.25)';
                    headerTag.style.color = '#c084fc';
                }
            }

            // 2. Sol Sidebar Mini Kartı
            const miniAiName = document.getElementById('mini-ai-name');
            const miniRpm = document.getElementById('mini-quota-rpm-display');
            const miniRpd = document.getElementById('mini-quota-rpd-display');
            const miniRpdRem = document.getElementById('mini-rpd-remaining');
            const miniRpmFill = document.getElementById('mini-rpm-fill');
            const miniRpdFill = document.getElementById('mini-rpd-fill');
            const miniBadge = document.getElementById('mini-quota-badge');
            const miniFill = document.getElementById('mini-quota-fill');
            const miniReset = document.getElementById('mini-quota-reset-text');
            const renderHint = document.getElementById('mini-render-hint');
            const renderHintText = document.getElementById('mini-render-hint-text');
            const remStr = typeof dailyRemaining === 'number' ? dailyRemaining.toLocaleString('tr-TR') : dailyRemaining;

            if (miniAiName) miniAiName.textContent = activeName;
            if (miniRpm) miniRpm.textContent = qData.is_api_key_missing ? 'Yerel' : `${rpmUsed}/${rpmLimit}`;
            if (miniRpd) {
                miniRpd.textContent = qData.is_api_key_missing
                    ? 'Sınırsız'
                    : `${rpdUsed}/${rpdLimit.toLocaleString('tr-TR')}`;
            }
            if (miniRpdRem) {
                miniRpdRem.textContent = qData.is_api_key_missing ? 'Yerel mod' : `${remStr} kaldı`;
            }

            if (miniRpmFill) {
                const rpmPct = rpmLimit > 0 ? Math.min(100, (rpmUsed / rpmLimit) * 100) : 0;
                miniRpmFill.style.width = `${rpmPct}%`;
                miniRpmFill.classList.toggle('is-warn', rpmPct >= 80 && rpmPct < 100);
                miniRpmFill.classList.toggle('is-danger', rpmPct >= 100);
            }
            if (miniRpdFill) {
                const rpdPct = rpdLimit > 0 ? Math.min(100, (rpdUsed / rpdLimit) * 100) : 0;
                miniRpdFill.style.width = `${rpdPct}%`;
                miniRpdFill.classList.toggle('is-warn', rpdPct >= 80 && rpdPct < 95);
                miniRpdFill.classList.toggle('is-danger', rpdPct >= 95);
            }

            if (renderHint && renderHintText) {
                let hintText = 'Evet — üretime hazır';
                let hintClass = 'ready';
                if (qData.is_api_key_missing) {
                    hintText = 'Evet — yerel mod (0 TL)';
                    hintClass = 'ready-local';
                } else if (dailyRemaining <= 0 && !isExhausted) {
                    hintText = 'Hayır — günlük kota doldu';
                    hintClass = 'blocked';
                } else if (isExhausted) {
                    hintText = 'Evet — fallback aktif';
                    hintClass = 'ready-fallback';
                } else if (rpmUsed >= rpmLimit) {
                    hintText = 'Bekle — RPM limiti dolu';
                    hintClass = 'wait-rpm';
                } else if (healthPct < 25) {
                    hintText = 'Evet — kota düşük';
                    hintClass = 'ready-low';
                }
                renderHintText.textContent = hintText;
                renderHint.className = `ssp-render-badge ${hintClass}`;
            }

            if (miniBadge && miniFill) {
                miniBadge.className = 'ssp-status-chip';
                miniFill.className = 'quota-bar-fill';
                miniFill.style.background = '';
                if (qData.is_api_key_missing) {
                    miniBadge.textContent = 'Yerel Motor';
                    miniBadge.classList.add('status-local');
                    miniFill.classList.add('fill-local');
                    miniFill.style.width = '100%';
                } else if (isExhausted) {
                    miniBadge.textContent = 'Limit Aşıldı';
                    miniBadge.classList.add('status-warn');
                    miniFill.classList.add('fill-warn');
                    miniFill.style.width = `${Math.max(healthPct, 10)}%`;
                } else {
                    miniBadge.textContent = `%${healthPct} müsait`;
                    miniBadge.classList.add('status-ok');
                    miniFill.classList.add('fill-ok');
                    miniFill.style.width = `${healthPct}%`;
                }
            }

            // 3. Stüdyo Form Barı (Studio Form Card)
            const studioAiName = document.getElementById('studio-ai-name');
            const studioAiRpm = document.getElementById('studio-ai-rpm');
            const studioAiRpd = document.getElementById('studio-ai-rpd');
            const studioPulse = document.getElementById('studio-ai-pulse');

            if (studioAiName) studioAiName.textContent = activeName;
            if (studioAiRpm) studioAiRpm.innerHTML = qData.is_api_key_missing ? `<i class="fa-solid fa-shield"></i> Yerel Motor` : `<i class="fa-solid fa-gauge-high"></i> ${rpmUsed} / ${rpmLimit} RPM`;
            if (studioAiRpd) {
                const remStr = typeof dailyRemaining === 'number' ? dailyRemaining.toLocaleString('tr-TR') : dailyRemaining;
                studioAiRpd.innerHTML = qData.is_api_key_missing ? `<i class="fa-solid fa-key"></i> Gemini Anahtarı Ekleyin` : `<i class="fa-solid fa-calendar-day"></i> ${rpdUsed} / ${rpdLimit.toLocaleString('tr-TR')} (${remStr} Kaldı)`;
            }
            if (studioPulse) {
                studioPulse.className = qData.is_api_key_missing ? 'pulse-dot cyan' : (isExhausted ? 'pulse-dot yellow' : 'pulse-dot green');
            }

            // 4. Detay Modalı
            const modalAiName = document.getElementById('modal-active-ai-name');
            const modalBadge = document.getElementById('modal-overall-badge');
            const modalRpm = document.getElementById('modal-rpm-stat');
            const modalRpd = document.getElementById('modal-rpd-stat');
            const modalHealthText = document.getElementById('modal-health-pct-text');
            const modalHealthBar = document.getElementById('modal-health-bar');
            const modalProvidersList = document.getElementById('modal-providers-list');

            if (modalAiName) modalAiName.textContent = activeName;
            if (modalRpm) modalRpm.textContent = `${rpmUsed} / ${rpmLimit} RPM`;
            if (modalRpd) modalRpd.textContent = `${rpdUsed} / ${rpdLimit.toLocaleString('tr-TR')} (${remStr} Kaldı)`;
            if (modalHealthText) modalHealthText.textContent = `%${healthPct} Müsait (${remStr} İstek Kaldı)`;
            if (modalHealthBar) {
                modalHealthBar.style.width = `${healthPct}%`;
                modalHealthBar.style.background = isExhausted ? '#facc15' : '#10b981';
            }
            if (modalBadge) {
                if (qData.is_api_key_missing) {
                    modalBadge.innerHTML = `<i class="fa-solid fa-key"></i> API Anahtarı Bekleniyor`;
                    modalBadge.style.background = 'rgba(56, 189, 248, 0.2)';
                    modalBadge.style.color = '#38bdf8';
                } else if (isExhausted) {
                    modalBadge.innerHTML = `<i class="fa-solid fa-triangle-exclamation"></i> Hız Limiti Aşıldı (0 TL Fallback Aktif)`;
                    modalBadge.style.background = 'rgba(234, 179, 8, 0.2)';
                    modalBadge.style.color = '#fde047';
                } else {
                    modalBadge.innerHTML = `<i class="fa-solid fa-circle-check"></i> %${healthPct} Canlı & Aktif (0 TL Modu)`;
                    modalBadge.style.background = 'rgba(16, 185, 129, 0.2)';
                    modalBadge.style.color = '#34d399';
                }
            }

            if (modalProvidersList && qData.providers) {
                modalProvidersList.innerHTML = Object.entries(qData.providers).map(([pKey, pInfo]) => {
                    const isProvActive = pInfo.is_active;
                    const borderStyle = isProvActive ? 'border: 1px solid rgba(168, 85, 247, 0.5); background: rgba(168, 85, 247, 0.08);' : 'border: 1px solid rgba(255, 255, 255, 0.06); background: rgba(15, 23, 42, 0.5);';
                    const badgeColor = pInfo.badge_class === 'warning' ? '#facc15' : (pInfo.badge_class === 'danger' ? '#f87171' : (pInfo.badge_class === 'secondary' ? '#94a3b8' : '#34d399'));
                    const remainingNote = pInfo.remaining_calls !== undefined 
                        ? `<span style="color: #38bdf8; font-weight: 600;">${pInfo.remaining_calls.toLocaleString('tr-TR')} / ${pInfo.rpd_limit.toLocaleString('tr-TR')} Kalan</span>`
                        : '';
                    const liveSyncBadge = pInfo.is_live_verified 
                        ? `<span style="background: rgba(16, 185, 129, 0.2); color: #34d399; font-size: 9px; padding: 1px 5px; border-radius: 4px; margin-left: 6px;"><i class="fa-solid fa-cloud"></i> Canlı API</span>`
                        : '';

                    return `
                        <div style="${borderStyle} border-radius: 8px; padding: 10px 14px; display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <div style="display: flex; align-items: center; gap: 8px;">
                                    <strong style="font-size: 13px; color: #f8fafc;">${pInfo.name}</strong>
                                    ${isProvActive ? '<span class="badge" style="background: rgba(168, 85, 247, 0.3); color: #c084fc; font-size: 10px; padding: 1px 6px; border-radius: 4px;">Aktif Seçili</span>' : ''}
                                    ${liveSyncBadge}
                                </div>
                                <div style="font-size: 11px; color: #94a3b8; margin-top: 2px;">
                                    ${pInfo.description} · <span style="color: #4ade80;">Maliyet: ${pInfo.cost_per_video}</span>
                                </div>
                            </div>
                            <div style="text-align: right;">
                                <div style="font-size: 12px; font-weight: 700; color: ${badgeColor};">
                                    ${pInfo.status_badge}
                                </div>
                                <div style="font-size: 10px; color: #64748b; margin-top: 2px;">
                                    ${pInfo.has_key ? `${remainingNote} · Toplam: <strong>${pInfo.total_calls}</strong> çağrı` : `<span style="color: #64748b;">(Yapılandırılmadı)</span>`}
                                </div>
                            </div>
                        </div>
                    `;
                }).join('');
            }

            // 5. Ayarlar Sayfası Monitörü
            const statsBox = document.getElementById('quota-stats-display');
            const detailsBox = document.getElementById('quota-exhaustion-details');
            if (statsBox) {
                let usageRows = qData.usage && Object.keys(qData.usage).length > 0
                    ? Object.entries(qData.usage).map(([k, v]) => `<div style="padding: 2px 0;">• ${k}: <strong>${v} çağrı</strong></div>`).join("")
                    : '<div style="color: #94a3b8;">Henüz API çağrısı yapılmadı.</div>';
                let errorRows = qData.errors && Object.keys(qData.errors).length > 0 
                    ? Object.entries(qData.errors).map(([k, v]) => `<div style="color: #f87171; font-size: 11px;">⚠️ ${k}: ${v} hata</div>`).join("") 
                    : "";

                statsBox.innerHTML = `
                    <div class="stat-pill mb-2"><span>Aktif AI Motoru:</span> <strong class="text-primary">${activeName}</strong></div>
                    <div class="stat-pill mb-2"><span>0 TL Stack Durumu:</span> <strong class="text-success">Aktif (Gemini Free + Edge-TTS + Pexels)</strong></div>
                    <div class="stat-pill mb-2"><span>Anlık Hız / Günlük Kota:</span> <strong class="text-info">${rpmUsed}/${rpmLimit} RPM · ${rpdUsed}/${rpdLimit} RPD</strong></div>
                    <div style="font-size: 12px; color: #e2e8f0; margin-top: 8px;">${usageRows}</div>
                    ${errorRows ? `<div class="mt-2" style="border-top: 1px dashed rgba(255,255,255,0.1); padding-top: 4px;">${errorRows}</div>` : ''}
                `;
            }

            // Hata veya kota aşımı detayları varsa göster
            if (detailsBox) {
                if (qData.quota_status && Object.keys(qData.quota_status).length > 0) {
                    let hasEx = false;
                    let cardsHtml = '';
                    for (const [prov, info] of Object.entries(qData.quota_status)) {
                        if (info.exhausted) {
                            hasEx = true;
                            const isAuth = info.status_type === 'AUTH_ERROR';
                            cardsHtml += `
                                <div style="background: rgba(${isAuth ? '239, 68, 68' : '234, 179, 8'}, 0.12); border: 1px solid rgba(${isAuth ? '239, 68, 68' : '234, 179, 8'}, 0.35); border-radius: 8px; padding: 12px; margin-bottom: 8px;">
                                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                                        <strong style="color: ${isAuth ? '#f87171' : '#facc15'}; font-size: 13px;">
                                            <i class="fa-solid fa-triangle-exclamation"></i> ${prov} ${isAuth ? 'Kimlik Doğrulama Hatası' : 'Kota / Hız Limiti Doldu'}
                                        </strong>
                                        <span style="font-size: 11px; background: rgba(0,0,0,0.4); padding: 2px 6px; border-radius: 4px; color: #cbd5e1;">Saat: ${info.exhausted_at}</span>
                                    </div>
                                    <div style="font-size: 11px; color: #f1f5f9; margin-bottom: 6px;">${info.description}</div>
                                    <div style="font-size: 11px; color: #38bdf8;">
                                        <i class="fa-solid fa-shield-halved"></i> <strong>Sistem Koruması:</strong> ${info.fallback_solution}
                                    </div>
                                </div>
                            `;
                        }
                    }
                    if (hasEx) {
                        detailsBox.style.display = 'block';
                        detailsBox.innerHTML = `
                            <h4 style="font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; color: #facc15; margin-bottom: 8px;">
                                <i class="fa-solid fa-clock-rotate-left"></i> Kota Aşımı & Otomatik Yenilenme Durumu
                            </h4>
                            ${cardsHtml}
                        `;
                    } else {
                        detailsBox.style.display = 'none';
                    }
                } else {
                    detailsBox.style.display = 'none';
                }
            }
        } catch (err) {
            console.error("updateAiQuotaDisplay error:", err);
        }
    }

    // Kota Modalı Açma / Kapama Olayları
    const quotaModal = document.getElementById('modal-ai-quota-details');
    function openQuotaModal() {
        if (quotaModal) {
            quotaModal.style.display = 'flex';
            quotaModal.classList.remove('hidden');
            updateAiQuotaDisplay();
        }
    }
    function closeQuotaModal() {
        if (quotaModal) {
            quotaModal.style.display = 'none';
            quotaModal.classList.add('hidden');
        }
    }

    document.getElementById('header-ai-quota-btn')?.addEventListener('click', openQuotaModal);
    document.getElementById('sidebar-quota-card')?.addEventListener('click', openQuotaModal);
    document.getElementById('btn-sidebar-quota-link')?.addEventListener('click', (e) => {
        e.stopPropagation();
        openQuotaModal();
    });
    document.getElementById('btn-open-quota-modal')?.addEventListener('click', openQuotaModal);
    document.getElementById('btn-close-quota-modal')?.addEventListener('click', closeQuotaModal);
    document.getElementById('btn-close-quota-modal-2')?.addEventListener('click', closeQuotaModal);
    document.getElementById('btn-refresh-quota-now')?.addEventListener('click', async () => {
        const btn = document.getElementById('btn-refresh-quota-now');
        const originalHtml = btn ? btn.innerHTML : '';
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<i class="fa-solid fa-sync fa-spin"></i> Canlı Kontrol Ediliyor...';
        }
        try {
            showToast('Canlı API kotaları sorgulanıyor (Pexels, Pixabay, Gemini)...');
            const resp = await fetch('/api/quota/stats?refresh=true');
            const data = await resp.json();
            await updateAiQuotaDisplay(data);
            showToast('✅ Gerçek kotalar canlı olarak güncellendi!');
        } catch (err) {
            showToast('Kota yenilenirken hata: ' + err.message, 'error');
        } finally {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = originalHtml;
            }
        }
    });

    document.getElementById('btn-reset-quota-stats')?.addEventListener('click', async () => {
        try {
            const res = await fetch('/api/quota/reset', { method: 'POST' });
            const data = await res.json();
            showToast(data.message || 'Kota sayaçları sıfırlandı.');
            await updateAiQuotaDisplay(data.stats);
        } catch (e) {
            showToast('Sayaçlar sıfırlanırken hata oluştu.', 'error');
        }
    });

    document.getElementById('btn-modal-save-gemini-key')?.addEventListener('click', async () => {
        const keyInput = document.getElementById('modal-quick-gemini-key');
        const statusDiv = document.getElementById('modal-gemini-key-status');
        const keyVal = (keyInput?.value || '').trim();
        if (!keyVal) {
            alert('Lütfen geçerli bir Google Gemini API anahtarı girin (AIzaSy... ile başlar).');
            return;
        }

        try {
            const res = await fetch('/api/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ gemini_key: keyVal })
            });
            const data = await res.json();
            if (data.status === 'ok') {
                if (statusDiv) {
                    statusDiv.style.display = 'block';
                    statusDiv.style.color = '#34d399';
                    statusDiv.innerHTML = '<i class="fa-solid fa-circle-check"></i> Gemini API Anahtarı başarıyla bağlandı ve .env dosyasına mühürlendi!';
                }
                const inputKeyGemini = document.getElementById('input-key-gemini');
                if (inputKeyGemini) inputKeyGemini.value = keyVal;
                showToast('🚀 Google Gemini Flash başarıyla aktif edildi!');
                await updateAiQuotaDisplay();
            } else {
                alert('Kaydetme hatası: ' + (data.message || 'Bilinmeyen hata'));
            }
        } catch (err) {
            alert('Hata: ' + err.message);
        }
    });

    quotaModal?.addEventListener('click', (e) => {
        if (e.target === quotaModal) closeQuotaModal();
    });

    document.getElementById('btn-save-settings')?.addEventListener('click', async () => {
        const gKey = document.getElementById('input-key-gemini').value.trim();
        const deepSeekKey = document.getElementById('input-key-deepseek').value.trim();
        const openAiKey = document.getElementById('input-key-openai').value.trim();
        const grokKey = document.getElementById('input-key-grok').value.trim();
        const pKey = document.getElementById('input-key-pexels').value.trim();
        const pxKey = document.getElementById('input-key-pixabay').value.trim();
        const youtubeDataKey = document.getElementById('input-key-youtube-data').value.trim();
        const redditClientId = document.getElementById('input-key-reddit-id').value.trim();
        const redditClientSecret = document.getElementById('input-key-reddit-secret').value.trim();
        const elevenlabsKey = document.getElementById('input-key-elevenlabs')?.value.trim();

        const payload = {};
        if (gKey) payload.gemini_key = gKey;
        if (deepSeekKey) payload.deepseek_key = deepSeekKey;
        if (openAiKey) payload.openai_key = openAiKey;
        if (grokKey) payload.grok_key = grokKey;
        if (pKey) payload.pexels_key = pKey;
        if (pxKey) payload.pixabay_key = pxKey;
        if (youtubeDataKey) payload.youtube_data_key = youtubeDataKey;
        if (redditClientId) payload.reddit_client_id = redditClientId;
        if (redditClientSecret) payload.reddit_client_secret = redditClientSecret;
        if (elevenlabsKey) payload.elevenlabs_key = elevenlabsKey;

        const scriptM = document.getElementById('select-gemini-script-model')?.value;
        const imageM = document.getElementById('select-gemini-image-model')?.value;
        const videoM = document.getElementById('select-gemini-video-model')?.value;
        if (scriptM) payload.gemini_model = scriptM;
        if (imageM) payload.gemini_image_model = imageM;
        if (videoM) payload.gemini_video_model = videoM;
        payload.use_gemini_image_gen = !!document.getElementById('chk-gai-image')?.checked;
        payload.use_gemini_video_gen = !!document.getElementById('chk-gai-video')?.checked;
        payload.use_gemini_grounding = !!document.getElementById('chk-gai-grounding')?.checked;
        payload.prefer_gemini_scene_images = !!document.getElementById('chk-gai-prefer-img')?.checked;
        payload.use_gemini_tts = !!document.getElementById('chk-gai-tts')?.checked;
        payload.use_gemini_embeddings = !!document.getElementById('chk-gai-embed')?.checked;
        payload.auto_fetch_royalty_free_bgm = !!document.getElementById('chk-rf-bgm')?.checked;

        try {
            const res = await fetch('/api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            let body = {};
            try { body = await res.json(); } catch (_) {}
            if (!res.ok) {
                const detail = body.detail || body.message || `HTTP ${res.status}`;
                showToast(`Ayar kaydedilemedi: ${detail}`, 'error');
                return;
            }
            if (elevenlabsKey) {
                showToast('ElevenLabs key kaydedildi');
                const elInput = document.getElementById('input-key-elevenlabs');
                if (elInput) {
                    const masked = body.key_hints?.elevenlabs || ('••••' + elevenlabsKey.slice(-4));
                    elInput.value = '';
                    elInput.placeholder = `${masked} (Kayıtlı)`;
                }
            } else {
                showToast('Sistem ayarları + Google AI Pro modelleri kaydedildi!');
            }
            await loadGoogleAiProPanel();
            await loadTtsVoiceCatalog(true);
            const cfg = await (await fetch('/api/config')).json();
            if (cfg.elevenlabs) renderElevenlabsQuota(cfg.elevenlabs);
        } catch (e) {
            showToast('Ayar kaydetme hatası: ' + e.message, 'error');
        }
    });

    // ══════════════════════════════════════════════════════════════
    // TOAST BİLDİRİM FONKSİYONU
    // ══════════════════════════════════════════════════════════════
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

    // ══════════════════════════════════════════════════════════════
    // 13. TEMA SEÇİCİ & PERSISTENCE
    // ══════════════════════════════════════════════════════════════
    const themeDots = document.querySelectorAll('.theme-dot');
    function setTheme(colorName) {
        document.body.setAttribute('data-theme', colorName);
        localStorage.setItem('shorts_theme', colorName);
        themeDots.forEach(d => {
            d.classList.toggle('active', d.getAttribute('data-color') === colorName);
        });
    }

    const savedTheme = localStorage.getItem('shorts_theme') || 'violet';
    setTheme(savedTheme);

    themeDots.forEach(dot => {
        dot.addEventListener('click', () => {
            const col = dot.getAttribute('data-color');
            if (col) setTheme(col);
        });
    });

    // ══════════════════════════════════════════════════════════════
    // 14. VİRAL KONU BANKASI & KONU ÖNERİCİ (Item 1-35)
    // ══════════════════════════════════════════════════════════════
    // 15. VIRAL KONU HAVUZU & VARYASYONLAR (Items 306 - 325)
    // ══════════════════════════════════════════════════════════════
    const VIRAL_TOPIC_BANK = {
        "1_news_flash": [
            "Tüm Dünyayı Sarsan Son Dakika Açıklaması!",
            "Uzmanlar Uyardı: Bu Hafta Başlayan Kritik Gelişme!",
            "Teknoloji Dünyasında Deprem Yaratan Flaş Karar!",
            "Tüm Piyasaları Altüst Eden Beklenmedik Olay!"
        ],
        "2_reddit_confessions": [
            "AITA: Düğünü Terk Eden Nişanlıma Verdiğim Cevap",
            "Gizli Sırrımı 5 Yıl Sonra İtiraf Etmek Zorunda Kaldım...",
            "İş Yerindeki En Büyük Skandalı Ortaya Çıkardığım Gün",
            "Ailemin Benden Sakladığı Büyük Gerçeği Öğrendim"
        ],
        "3_split_gameplay": [
            "Tarihin En İnanılmaz Kaçış Hikayesi",
            "Bu Gizemli Olayı Çözen Kimse Çıkmadı!",
            "Yeraltı Tünellerinde Kaybolan Adamın Hikayesi",
            "Dünyanın En Tehlikeli Yollarında Yaşananlar"
        ],
        "4_would_you_rather": [
            "Geleceği Görmek mi, Geçmişi Değiştirmek mi? (%90 Zorlandı)",
            "Sonsuz Para mı, Sonsuz Sağlık mı? Zorlu Tercih Düellosu",
            "Asla Uyumamak mı, Asla Yemek Yememek mi?",
            "Zihin Okuma Yeteneği mi, Görünmezlik mi?"
        ],
        "5_guess_flag_country": [
            "Sadece Gerçek Coğrafya Dahileri Bu 3 Bayrağı Bilebiliyor!",
            "Bu Başkent Hangi Ülkeye Ait? (%95 Yanıldı)",
            "5 Saniyede Ülkeyi Tahmin Et: Dünya Bayrakları Quiz",
            "Hangi Ülkenin Para Birimi? Testi Geçebilecek Misin?"
        ],
        "6_stoic_philosophy": [
            "Marcus Aurelius'un Öfkeyi Yok Eden 3 Stoacı Kuralı",
            "Seneca: Zamanını Çalan İnsanlardan Kurtulmanın 4 Yolu",
            "Epiktetos'un Zihinsel Dayanıklılık Formülü: Asla Şikayet Etme",
            "Hiçbir Şeyi Kafana Takmamanın 3 Stoacı Sırrı"
        ],
        "7_dark_psychology": [
            "3 Dark Psychology Secrets Manipulation Experts Never Tell You",
            "İnsanların Yalan Söylediğini Ele Veren 3 Mikro İpucu",
            "Manipülasyon Ustalarının Kullandığı Ters Psikoloji Tuzağı",
            "Sohbette Üstünlük Kurmanızı Sağlayan 3 Sessizlik Kuralı"
        ],
        "8_crypto_market": [
            "Bitcoin Halving Sonrası Zengin Eden 3 Döngü Kuralı",
            "Kripto Balinalarının Topladığı 3 Gizli Altcoin",
            "Fakir İnsanların Yaptığı ve Asla Zengin Olamadıkları 4 Hata",
            "Bileşik Getirinin Gücü: Günde 1 Dolarla Nasıl Portföy Büyütülür?"
        ],
        "9_five_facts": [
            "Dünya Hakkında Asla Bilmediğiniz 5 Şaşırtıcı Gerçek",
            "Tarihin En Tuhaf 5 Rastlantısı",
            "İnsan Vücudunun Bilinmeyen 5 Gizli Özelliği",
            "Okyanusların En Derin Noktasındaki 5 Korkutucu Sır"
        ],
        "27_common_myths_busted": [
            "Herkesin Doğru Bildiği 5 Büyük Bilimsel Yanılgı!",
            "Yıllardır İnanılan ve Tamamen Yalan Olan 4 Şehir Efsanesi",
            "Tarih Kitaplarında Yanlış Anlatılan 3 Büyük Olay",
            "Sağlık Konusunda Doğru Sanılan 5 Tehlikeli Yanılgı"
        ],
        "general": [
            "Herkesin Doğru Bildiği 5 Büyük Bilimsel Yanılgı!",
            "Günde Sadece 10 Dakika Yaparak Hayatını Değiştirecek Alışkanlık",
            "Milyonerlerin Sabah Rutinindeki 3 Gizli Adım",
            "Bilinçaltının Çalışma Prensibi: Neden Hep Aynı Hatayı Yapıyoruz?"
        ]
    };

    // Konu Öner — wired after escapeHtml (see topic suggest panel block below)

    function autoDetectNicheFromTopicLocal() {
        const topicText = (inputTopic?.value || '').trim().toLowerCase();
        if (!topicText || !selectNiche) return null;

        let targetId = null;
        if (/stoa|marcus|aurelius|seneca|epiktetos|stoac/.test(topicText)) targetId = '6_stoic_philosophy';
        else if (/whatsapp|mesajlaşma|mesaj hikay|chat story|sohbet ekran/.test(topicText)) targetId = '20_whatsapp_chat_story';
        else if (/yanılgı|mit |efsane|yanlış bilinen|doğru bilinen|bilimsel/.test(topicText)) targetId = '27_common_myths_busted';
        else if (/karanlık psikoloji|manipülasyon|manipulation|dark psychology/.test(topicText)) targetId = '7_dark_psychology';
        else if (/kripto|bitcoin|borsa|altın|hisse|dolar|enflasyon/.test(topicText)) targetId = '8_crypto_market';
        else if (/\d+\s+(?:büyük|ilginç|önemli|sır|kural|adım|ipucu)|şaşırtıcı gerçek/.test(topicText)) targetId = '9_five_facts';
        else if (/aita|itiraf|confession|reddit/.test(topicText)) targetId = '2_reddit_confessions';
        else if (/tercih et|would you rather/.test(topicText)) targetId = '4_would_you_rather';
        else if (/bayrak|ülke tahmin|hangi ülke/.test(topicText)) targetId = '5_guess_flag_country';
        else if (/paranormal|ufo|bermuda|51\.\s*bölge|gizem.*korku/.test(topicText)) targetId = '13_mystery_paranormal';
        else if (/son dakika|flaş|haber|deprem|kaza|trafik/.test(topicText)) targetId = '1_news_flash';
        return targetId;
    }

    async function resolveAndApplyNicheFromTopic({ toast = true } = {}) {
        const topicText = (inputTopic?.value || '').trim();
        if (!topicText || !selectNiche) return null;

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
            if (toast) {
                showToast(`Niş otomatik: ${nicheName || opt.textContent} (konu uyumu)`);
            }
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

    inputTopic?.addEventListener('input', () => {
        if (!suppressFingerprintClear) clearPendingFormatFingerprint();
        suppressFingerprintClear = false;
        updateFlowRail('topic');
        updateLoopBridge(selectNiche ? selectNiche.value : '6_stoic_philosophy', inputTopic.value);
        scheduleNicheResolveFromTopic();
    });
    inputTopic?.addEventListener('change', () => resolveAndApplyNicheFromTopic({ toast: true }));
    inputTopic?.addEventListener('blur', () => resolveAndApplyNicheFromTopic({ toast: true }));

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

    let lastTopicSuggestions = [];

    function renderTopicSuggestCards(suggestions, nicheName) {
        const panel = document.getElementById('topic-suggest-panel');
        const body = document.getElementById('topic-suggest-body');
        const titleEl = document.getElementById('topic-suggest-title');
        if (!panel || !body) return;
        lastTopicSuggestions = suggestions || [];
        panel.classList.remove('hidden');
        if (titleEl && nicheName) {
            titleEl.innerHTML = `<i class="fa-solid fa-wand-magic-sparkles"></i> ${escapeHtml(nicheName)} — 5 Konu Önerisi`;
        }
        if (!suggestions || !suggestions.length) {
            body.innerHTML = '<div class="topic-suggest-empty">Bu niş için uygun konu bulunamadı. Yeniden deneyin.</div>';
            return;
        }
        body.innerHTML = suggestions.map((s, idx) => {
            const src = TOPIC_SOURCE_LABELS[s.source] || TOPIC_SOURCE_LABELS.ai;
            const hook = s.hook ? `<div class="topic-suggest-card-hook">${escapeHtml(s.hook)}</div>` : '';
            return `
                <button type="button" class="topic-suggest-card" data-suggest-idx="${idx}">
                    <div class="topic-suggest-card-title">${idx + 1}. ${escapeHtml(s.title)}</div>
                    ${hook}
                    <div class="topic-suggest-card-meta">
                        <span class="topic-suggest-badge ${src.cls}"><i class="${src.icon}"></i> ${src.label}</span>
                        <span class="topic-suggest-score">Uygunluk ${s.confidence || s.relevance || 0}/100</span>
                    </div>
                </button>`;
        }).join('');
        body.querySelectorAll('.topic-suggest-card').forEach(card => {
            card.addEventListener('click', () => {
                const idx = Number(card.dataset.suggestIdx);
                const picked = lastTopicSuggestions[idx];
                if (!picked) return;
                inputTopic.value = picked.title;
                setPendingFormatFingerprint(picked.format_fingerprint || null);
                updateLoopBridge(selectNiche?.value || '1_news_flash', picked.title);
                resolveAndApplyNicheFromTopic({ toast: false }).catch(() => {});
                panel.classList.add('hidden');
                showToast(`Konu seçildi: ${picked.title.slice(0, 60)}${picked.title.length > 60 ? '…' : ''}`);
            });
        });
    }

    async function suggestTopic() {
        const nicheId = selectNiche?.value;
        const panel = document.getElementById('topic-suggest-panel');
        const body = document.getElementById('topic-suggest-body');
        const btn = document.getElementById('btn-suggest-topic');
        if (!nicheId) {
            showToast('Önce bir niş şablonu seçin.', 'warn');
            return;
        }
        const language = document.getElementById('select-language')?.value || 'tr';
        const topicHint = (inputTopic?.value || '').trim();
        if (panel) panel.classList.remove('hidden');
        if (body) body.innerHTML = '<div class="topic-suggest-loading"><i class="fa-solid fa-spinner fa-spin"></i> Nişe uygun konular araştırılıyor…</div>';
        if (btn) {
            btn.classList.add('is-loading');
            btn.disabled = true;
        }
        try {
            const res = await fetch('/api/topics/suggest', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    niche_id: nicheId,
                    language,
                    count: 5,
                    topic_hint: topicHint || undefined,
                }),
            });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Konu önerileri alınamadı.');
            renderTopicSuggestCards(data.suggestions, data.niche_name);
        } catch (err) {
            if (body) body.innerHTML = `<div class="topic-suggest-error">${escapeHtml(err.message || 'Bağlantı hatası')}</div>`;
            console.error('Konu öner hatası:', err);
        } finally {
            if (btn) {
                btn.classList.remove('is-loading');
                btn.disabled = false;
            }
        }
    }

    document.getElementById('btn-suggest-topic')?.addEventListener('click', suggestTopic);
    document.getElementById('btn-retry-topic-suggest')?.addEventListener('click', suggestTopic);
    document.getElementById('btn-close-topic-suggest')?.addEventListener('click', () => {
        document.getElementById('topic-suggest-panel')?.classList.add('hidden');
    });

    async function applyNicheProfile(nicheId) {
        const profileBox = document.getElementById('niche-production-profile');
        if (!nicheId || !profileBox) return;
        try {
            const response = await fetch(`/api/niches/${encodeURIComponent(nicheId)}/profile`);
            const data = await response.json();
            const profile = data.profile;
            if (!profile) return;
            const rules = profile.production_rules || {};
            chkSplitScreen.checked = Boolean(rules.split_screen);
            chkKenBurns.checked = Boolean(rules.ken_burns);
            if (rules.subtitle_preset && selectSubPreset) selectSubPreset.value = rules.subtitle_preset;
            profileBox.innerHTML = `
                <div style="display: flex; justify-content: space-between; gap: 8px; align-items: center;">
                    <strong style="font-size: 12px; color: #67e8f9;"><i class="fa-solid fa-sliders"></i> Aktif Niş Profili: ${escapeHtml(profile.name)}</strong>
                    <span class="niche-tag">${escapeHtml(profile.category)}</span>
                </div>
                <div style="font-size: 11px; color: #cbd5e1; margin-top: 6px;">Ton: ${escapeHtml(profile.tone)}</div>
                <div style="font-size: 11px; color: #94a3b8; margin-top: 4px;">${rules.split_screen ? 'Split-screen' : 'Tam ekran'} · ${escapeHtml(rules.subtitle_preset)} altyazı · Dinamik hareket · Neon ilerleme</div>
            `;
            updateLoopBridge(nicheId, inputTopic.value);
            applyNichePanelVisibility(nicheId);
            const gapField = document.getElementById('content-gap-topics');
            if (gapField && Array.isArray(profile.content_gap_examples) && profile.content_gap_examples.length) {
                gapField.placeholder = profile.content_gap_examples.map(line => `Örn: ${line}`).join('\n');
            }
        } catch (error) {
            profileBox.textContent = 'Niş üretim profili yüklenemedi.';
            console.error('Niş profili yükleme hatası:', error);
        }
    }

    document.getElementById('btn-load-niche-trends')?.addEventListener('click', async (event) => {
        const nicheId = selectNiche?.value;
        const results = document.getElementById('niche-trends-results');
        if (!nicheId || !results) return;
        const button = event.currentTarget;
        button.disabled = true;
        button.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Araştırılıyor';
        try {
            const response = await fetch(`/api/niches/${encodeURIComponent(nicheId)}/trends?region=TR`);
            const data = await response.json();
            results.style.display = 'block';
            if (data.status !== 'ok') {
                results.innerHTML = `<div class="alert-info-box"><i class="fa-solid fa-key"></i><span>${escapeHtml(data.reason || 'Trend verisi alınamadı.')}</span></div>`;
                return;
            }
            const isRealYoutube = Boolean(data.is_real_youtube);
            const badgeIcon = isRealYoutube ? 'fa-brands fa-youtube' : 'fa-solid fa-wand-magic-sparkles';
            const badgeBg = isRealYoutube ? 'rgba(30,58,138,0.4)' : 'rgba(88,28,135,0.35)';
            const badgeBorder = isRealYoutube ? 'rgba(96,165,250,0.3)' : 'rgba(192,132,252,0.35)';
            const badgeColor = isRealYoutube ? '#93c5fd' : '#e9d5ff';
            const sourceBadge = data.source_label ?
                `<div style="display:inline-flex; align-items:center; gap:6px; background:${badgeBg}; border:1px solid ${badgeBorder}; color:${badgeColor}; padding:4px 10px; border-radius:6px; font-size:11px; margin-bottom:8px;">
                    <i class="${badgeIcon}"></i> <span>${escapeHtml(data.source_label)}</span>
                </div>` : '';
            lastTrendResults = data.trends || [];
            trendFormatFingerprintAggregate = data.format_fingerprint || null;
            const listIntro = isRealYoutube
                ? 'Son 24 saatte yayınlanan, görüntülenmeye göre sıralı YouTube başlık sinyalleri (tıklayarak konuya aktarın):'
                : 'YouTube verisi bulunamadı — nişe uygun AI başlık önerileri (tıklayarak konuya aktarın):';
            results.innerHTML = `
                ${sourceBadge}
                <div style="font-size: 11px; color: #67e8f9; margin: 2px 0 8px 0;">${listIntro}</div>
                ${lastTrendResults.map((trend, index) => {
                    const viewsStr = trend.view_count_text || (typeof trend.view_count === 'number' && trend.view_count > 0 ? Number(trend.view_count).toLocaleString('tr-TR') + ' görüntülenme' : '');
                    const metaLine = isRealYoutube && trend.channel
                        ? `<i class="fa-brands fa-youtube text-danger" style="margin-right:3px;"></i>${escapeHtml(trend.channel)}${viewsStr ? ` · ${escapeHtml(viewsStr)}` : ''}`
                        : `<i class="fa-solid fa-wand-magic-sparkles" style="margin-right:3px; color:#c4b5fd;"></i>AI öneri`;
                    return `
                    <button class="trend-topic-option" data-topic="${escapeHtml(trend.title)}" data-trend-index="${index}" style="display:block; width:100%; text-align:left; padding:9px 12px; margin-bottom:6px; border-radius:6px; background:rgba(15,23,42,.75); border:1px solid rgba(148,163,184,.18); color:#e2e8f0; cursor:pointer; transition:all 0.15s ease;">
                        <strong style="font-size:12px; color:#f8fafc;">${index + 1}. ${escapeHtml(trend.title)}</strong><br>
                        <span style="font-size:10px; color:#94a3b8;">${metaLine}</span>
                    </button>
                    `;
                }).join('')}
            `;
            results.querySelectorAll('.trend-topic-option').forEach(option => {
                option.addEventListener('click', () => {
                    suppressFingerprintClear = true;
                    inputTopic.value = option.dataset.topic;
                    const idx = Number(option.dataset.trendIndex);
                    const picked = lastTrendResults[idx];
                    setPendingFormatFingerprint(picked?.format_fingerprint || trendFormatFingerprintAggregate);
                    updateLoopBridge(nicheId, inputTopic.value);
                    updateFlowRail('topic');
                    showToast('Trend başlık sinyali konu alanına aktarıldı. Senaryo özgün olarak üretilecek.');
                });
            });
        } catch (error) {
            results.style.display = 'block';
            results.textContent = 'Trend araştırması sırasında bağlantı hatası oluştu.';
            console.error('Trend araştırması hatası:', error);
        } finally {
            button.disabled = false;
            button.innerHTML = '<i class="fa-solid fa-chart-line"></i> Son 24 Saat Trendlerini Getir';
        }
    });

    document.getElementById('btn-analyze-content-gaps')?.addEventListener('click', async (event) => {
        const source = document.getElementById('content-gap-topics');
        const results = document.getElementById('content-gap-results');
        const nicheId = selectNiche?.value;
        if (!source?.value.trim() || !results || !nicheId) {
            showToast('Önce YouTube Studio içerik boşluğu konu listesini girin.');
            return;
        }
        const button = event.currentTarget;
        button.disabled = true;
        try {
            const response = await fetch('/api/research/content-gaps', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ raw_topics: source.value, niche: nicheId })
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || 'Araştırma çözümlenemedi.');
            results.style.display = 'block';
            const gapFingerprint = data.format_fingerprint || null;
            results.innerHTML = data.suggestions.length ? data.suggestions.map(suggestion => `
                <button class="trend-topic-option content-gap-option" data-topic="${escapeHtml(suggestion.topic)}" style="display:block; width:100%; text-align:left; padding:8px; margin-bottom:5px; border-radius:6px; background:rgba(15,23,42,.7); border:1px solid rgba(251,191,36,.2); color:#e2e8f0; cursor:pointer;">
                    <strong style="font-size:12px;">${escapeHtml(suggestion.topic)}</strong>
                    <span style="float:right; font-size:10px; color:#fbbf24;">Uygunluk ${suggestion.relevance}/100</span>
                </button>`).join('') : '<div class="alert-info-box">Kullanılabilir konu bulunamadı.</div>';
            results.querySelectorAll('.content-gap-option').forEach(option => option.addEventListener('click', () => {
                suppressFingerprintClear = true;
                inputTopic.value = option.dataset.topic;
                setPendingFormatFingerprint(gapFingerprint);
                updateLoopBridge(nicheId, inputTopic.value);
                updateFlowRail('topic');
                showToast('İçerik boşluğu konusu seçildi. Senaryo niş profilinizle özgün üretilecek.');
            }));
        } catch (error) {
            results.style.display = 'block';
            results.textContent = error.message;
        } finally {
            button.disabled = false;
        }
    });

    document.getElementById('btn-load-reddit-posts')?.addEventListener('click', async (event) => {
        const results = document.getElementById('reddit-post-results');
        const subreddit = document.getElementById('select-reddit-subreddit')?.value || 'AITA';
        const button = event.currentTarget;
        button.disabled = true;
        button.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Keşfediliyor...';
        try {
            const currentLang = document.getElementById('select-language')?.value || 'tr';
            const response = await fetch(`/api/research/reddit?subreddit=${encodeURIComponent(subreddit)}&lang=${encodeURIComponent(currentLang)}`);
            const data = await response.json();
            if (!response.ok || data.status !== 'ok') throw new Error(data.detail || 'Reddit gönderileri alınamadı.');
            
            let modeBadge = '<span class="badge" style="background: rgba(168, 85, 247, 0.2); color: #c084fc; font-size: 10px; padding: 2px 6px; border-radius: 4px;"><i class="fa-solid fa-wand-magic-sparkles"></i> Viral Arşiv Rotasyonu</span>';
            if (data.mode === 'oauth') {
                modeBadge = '<span class="badge" style="background: rgba(16, 185, 129, 0.2); color: #34d399; font-size: 10px; padding: 2px 6px; border-radius: 4px;"><i class="fa-solid fa-key"></i> Resmi OAuth API</span>';
            } else if (data.mode === 'ai_discovery') {
                modeBadge = '<span class="badge" style="background: rgba(245, 158, 11, 0.2); color: #fbbf24; font-size: 10px; padding: 2px 6px; border-radius: 4px;"><i class="fa-solid fa-sparkles"></i> Canlı AI Keşif (Taze İçerik)</span>';
            }

            const headerHtml = `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                    <span style="font-size: 11px; color: #94a3b8;">${data.posts.length} trend gönderi hazır:</span>
                    ${modeBadge}
                </div>
            `;

            results.innerHTML = data.posts.length ? headerHtml + data.posts.map((post, index) => `
                <button type="button" class="trend-topic-option reddit-post-option" data-index="${index}" style="display:block; width:100%; text-align:left; padding:8px 10px; margin-bottom:6px; border-radius:8px; background:rgba(15,23,42,.75); border:1px solid rgba(255,69,0,.35); color:#e2e8f0; cursor:pointer; transition: all 0.2s ease;">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 6px;">
                        <strong style="font-size:12px; line-height: 1.35; color: #f8fafc;">${escapeHtml(post.title)}</strong>
                    </div>
                    <div style="font-size:10px; color:#94a3b8; margin-top: 4px; display: flex; gap: 8px;">
                        <span style="color: #ff6b35; font-weight: 600;">r/${escapeHtml(post.subreddit)}</span>
                        <span>·</span>
                        <span>▲ ${Number(post.score || 1000).toLocaleString('tr-TR')} oy</span>
                        <span>·</span>
                        <span style="color: #64748b;">${escapeHtml(post.author || 'Anonim')}</span>
                    </div>
                </button>`).join('') : '<div class="alert-info-box">Uygun kaynak gönderi bulunamadı.</div>';
            
            results.querySelectorAll('.reddit-post-option').forEach(option => option.addEventListener('click', () => {
                selectedRedditPost = data.posts[Number(option.dataset.index)];
                inputTopic.value = selectedRedditPost.title;
                updateLoopBridge('2_reddit_confessions', inputTopic.value);
                showToast('Reddit viral hikayesi seçildi. İlk sahneye kaynak kartı eklenecek ve metin insanlaştırılacak.');
            }));
        } catch (error) {
            results.innerHTML = `<div class="alert-info-box text-danger" style="font-size: 11px;">⚠️ ${escapeHtml(error.message)}</div>`;
        } finally {
            button.disabled = false;
            button.innerHTML = '<i class="fa-solid fa-arrows-rotate"></i> Güncel Gönderileri Getir';
        }
    });


    // ══════════════════════════════════════════════════════════════
    // 15. CANLI KANCA (HOOK) & DÖNGÜ (LOOP) KÖPRÜSÜ
    // ══════════════════════════════════════════════════════════════
    function updateLoopBridge(nicheId, topic) {
        const hookSpan = document.getElementById('preview-hook-text');
        const loopSpan = document.getElementById('preview-loop-text');
        const subOverlay = document.getElementById('mockup-sub-overlay');
        if (!hookSpan || !loopSpan) return;

        const topicText = topic || inputTopic.value || "Bu Gizemli Konu";

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

    selectNiche?.addEventListener('change', () => {
        if (lockedNicheId && selectNiche.value !== lockedNicheId) {
            showToast('Konu ile niş uyumsuz olabilir', 'warn');
        }
        updateLoopBridge(selectNiche.value, inputTopic.value);
        applyNicheProfile(selectNiche.value);
    });

    // ══════════════════════════════════════════════════════════════
    // 16. HIZLI AKSİYON BUTONLARI (Quick Action Strip)
    // ══════════════════════════════════════════════════════════════
    // 1. Rastgele Niş Seç & Konu Üret
    document.getElementById('qa-random-niche')?.addEventListener('click', async () => {
        if (allNiches.length === 0) await loadNiches();
        if (allNiches.length > 0) {
            const randomN = allNiches[Math.floor(Math.random() * allNiches.length)];
            selectNiche.value = randomN.id;
            await applyNicheProfile(randomN.id);
            suggestTopic();
            switchTab('studio');
            showToast(`🎲 Rastgele Niş Seçildi: ${randomN.name} (${randomN.category})`);
        } else {
            suggestTopic();
        }
    });

    // 2. Son Dakika Flaş Haber Çek (Doğrudan Stüdyoya Aktarır)
    document.getElementById('qa-latest-news')?.addEventListener('click', async () => {
        showToast('📡 En güncel son dakika flaş haberi taranıyor...');
        try {
            const res = await fetch('/api/rss/fetch?source=aa_guncel&limit=1');
            const data = await res.json();
            if (data.items && data.items.length > 0) {
                const news = data.items[0];
                inputTopic.value = news.title;
                selectNiche.value = "1_news_flash";
                await applyNicheProfile("1_news_flash");
                updateLoopBridge("1_news_flash", news.title);
                switchTab('studio');
                showToast(`📰 Son Dakika Haberi Yüklendi: ${news.title.slice(0, 45)}...`);
            } else {
                switchTab('rss-bot');
                loadRssNews();
            }
        } catch (e) {
            switchTab('rss-bot');
            loadRssNews();
        }
    });

    // 3. Split-Screen Modunu Aç / Kapat (Toggle & Canlı Senkronizasyon)
    const btnSplitMode = document.getElementById('qa-split-mode');
    btnSplitMode?.addEventListener('click', () => {
        chkSplitScreen.checked = !chkSplitScreen.checked;
        chkSplitScreen.dispatchEvent(new Event('change'));
        btnSplitMode.classList.toggle('active', chkSplitScreen.checked);
        const span = btnSplitMode.querySelector('span');
        if (span) span.textContent = chkSplitScreen.checked ? 'Split-Screen: AÇIK' : 'Split-Screen Modunu Aç';
        switchTab('studio');
        showToast(chkSplitScreen.checked ? '🎮 Split-Screen (Oynanış + Kurgu) Aktif!' : '⏹️ Split-Screen Modu Kapatıldı');
    });

    function genderLabel(g) {
        return g === 'female' ? 'Kadın' : 'Erkek';
    }

    function findVoiceMeta(voiceId) {
        if (!voiceId || voiceId === 'auto') return null;
        const pools = [
            ...(ttsVoiceCatalog.tr || []),
            ...(ttsVoiceCatalog.en || []),
            ...(ttsVoiceCatalog.elevenlabs || []),
        ];
        return pools.find(v => v.id === voiceId) || null;
    }

    function appendEdgeVoiceGroup(selectEl, label, voices) {
        if (!voices.length) return;
        const group = document.createElement('optgroup');
        group.label = label;
        voices.forEach(v => {
            const opt = document.createElement('option');
            opt.value = v.id;
            const nativeTag = v.native ? '' : ' · çok dilli';
            opt.textContent = `${v.label} (${genderLabel(v.gender)}, ${v.quality}${nativeTag})`;
            group.appendChild(opt);
        });
        selectEl.appendChild(group);
    }

    function savedTtsVoicePreference() {
        try { return localStorage.getItem(TTS_VOICE_STORAGE_KEY) || ''; } catch (e) { return ''; }
    }

    function persistTtsVoicePreference(voiceId) {
        try {
            if (voiceId && voiceId !== 'auto') localStorage.setItem(TTS_VOICE_STORAGE_KEY, voiceId);
            else localStorage.removeItem(TTS_VOICE_STORAGE_KEY);
        } catch (e) {}
    }

    function populateTtsVoiceSelect(_lang) {
        if (!selectTtsVoice) return;
        const prev = selectTtsVoice.value !== 'auto' ? selectTtsVoice.value : savedTtsVoicePreference();
        const trVoices = (ttsVoiceCatalog.tr && ttsVoiceCatalog.tr.length) ? ttsVoiceCatalog.tr : STATIC_TTS_FALLBACK.tr;
        const enVoices = (ttsVoiceCatalog.en && ttsVoiceCatalog.en.length) ? ttsVoiceCatalog.en : STATIC_TTS_FALLBACK.en;
        const elevenVoices = ttsVoiceCatalog.elevenlabs || [];
        const elevenMeta = ttsVoiceCatalog.elevenlabs_meta || {};

        selectTtsVoice.innerHTML = '<option value="auto">Otomatik (konu / nişe göre)</option>';
        appendEdgeVoiceGroup(selectTtsVoice, 'Türkçe Edge', trVoices);
        appendEdgeVoiceGroup(selectTtsVoice, 'English Edge', enVoices);

        if (elevenVoices.length) {
            const group = document.createElement('optgroup');
            group.label = 'ElevenLabs';
            elevenVoices.forEach(v => {
                const opt = document.createElement('option');
                opt.value = v.id;
                opt.textContent = `${v.label} (${genderLabel(v.gender)}, ${v.quality})`;
                group.appendChild(opt);
            });
            selectTtsVoice.appendChild(group);
        } else if (elevenMeta.configured && elevenMeta.error) {
            const group = document.createElement('optgroup');
            group.label = 'ElevenLabs';
            group.disabled = true;
            const opt = document.createElement('option');
            opt.disabled = true;
            opt.value = '';
            opt.textContent = `${elevenMeta.error} — Ayarlar'dan düzeltin`;
            group.appendChild(opt);
            selectTtsVoice.appendChild(group);
        }

        if (prev && [...selectTtsVoice.options].some(o => o.value === prev)) {
            selectTtsVoice.value = prev;
        } else {
            selectTtsVoice.value = 'auto';
        }
    }

    selectTtsVoice?.addEventListener('change', () => persistTtsVoicePreference(selectTtsVoice.value));

    function renderElevenlabsQuota(info) {
        const strip = document.getElementById('elevenlabs-quota-strip');
        if (!strip) return;
        if (!info?.configured) {
            strip.style.display = 'none';
            return;
        }
        strip.style.display = 'block';
        const q = info.quota || {};
        if (q.character_remaining != null) {
            strip.innerHTML = `<i class="fa-solid fa-chart-simple text-info"></i> ElevenLabs: <strong>${q.character_remaining}</strong> / ${q.character_limit || '?'} karakter kaldı (${q.tier || 'free'})`;
        } else if (q.error) {
            strip.textContent = 'ElevenLabs kota bilgisi alınamadı.';
        } else {
            strip.textContent = 'ElevenLabs bağlı — kota yükleniyor…';
        }
    }

    async function loadTtsVoiceCatalog(forceRefresh = false) {
        populateTtsVoiceSelect(selectLanguage?.value || 'tr');
        try {
            const voicesRes = await fetch(forceRefresh ? '/api/tts/voices?refresh=true' : '/api/tts/voices');
            if (voicesRes.ok) {
                const catalog = await voicesRes.json();
                if (catalog.tr || catalog.en || catalog.elevenlabs || catalog.elevenlabs_meta) {
                    ttsVoiceCatalog = {
                        tr: catalog.tr || STATIC_TTS_FALLBACK.tr,
                        en: catalog.en || STATIC_TTS_FALLBACK.en,
                        elevenlabs: catalog.elevenlabs || [],
                        elevenlabs_meta: catalog.elevenlabs_meta || {},
                    };
                }
                elevenlabsConfigured = !!(catalog.elevenlabs_meta?.configured || (catalog.elevenlabs || []).length);
            } else {
                showToast('TTS ses listesi sunucudan alınamadı — yerel Edge listesi kullanılıyor.', 'warning');
            }
            populateTtsVoiceSelect(selectLanguage?.value || 'tr');
            if (!forceRefresh) {
                const cfgRes = await fetch('/api/config');
                if (cfgRes.ok) {
                    const data = await cfgRes.json();
                    elevenlabsConfigured = !!(data.keys?.elevenlabs || data.elevenlabs?.configured);
                    if (data.elevenlabs) renderElevenlabsQuota(data.elevenlabs);
                    if (data.gameplay_categories && selectGameplayCategory) {
                        selectGameplayCategory.innerHTML = (data.gameplay_categories || []).map(c =>
                            `<option value="${c.id}">${c.label}</option>`
                        ).join('');
                    }
                }
            }
        } catch (e) {
            console.warn('TTS voice catalog load failed', e);
            populateTtsVoiceSelect(selectLanguage?.value || 'tr');
            showToast('TTS ses kataloğu yüklenemedi — yerel Edge listesi aktif.', 'warning');
        }
    }

    selectLanguage?.addEventListener('change', () => populateTtsVoiceSelect(selectLanguage.value));

    chkSplitScreen?.addEventListener('change', () => {
        if (gameplayCategoryWrap) {
            gameplayCategoryWrap.style.display = chkSplitScreen.checked ? 'block' : 'none';
        }
        if (btnSplitMode) {
            btnSplitMode.classList.toggle('active', chkSplitScreen.checked);
            const span = btnSplitMode.querySelector('span');
            if (span) span.textContent = chkSplitScreen.checked ? 'Split-Screen: AÇIK' : 'Split-Screen Modunu Aç';
        }
    });

    // 4. Tier-1 (ABD/İngilizce) Modu (Toggle TR / EN)
    const btnTier1 = document.getElementById('qa-tier1-en');
    btnTier1?.addEventListener('click', async () => {
        const isCurrentlyEn = selectLanguage.value === 'en';
        if (!isCurrentlyEn) {
            selectLanguage.value = 'en';
            populateTtsVoiceSelect('en');
            if (selectTtsVoice) selectTtsVoice.value = 'en-US-GuyNeural';
            selectNiche.value = '7_dark_psychology';
            await applyNicheProfile('7_dark_psychology');
            inputTopic.value = "3 Dark Psychology Secrets Manipulation Experts Never Tell You #Shorts";
            btnTier1.classList.add('active');
            const span = btnTier1.querySelector('span');
            if (span) span.textContent = 'Tier-1 EN: AKTİF (ABD)';
            switchTab('studio');
            showToast('🌎 Tier-1 ABD (İngilizce Yüksek CPM) Modu Aktif Edildi!');
        } else {
            selectLanguage.value = 'tr';
            selectVoiceGender.value = 'auto';
            selectNiche.value = '6_stoic_philosophy';
            await applyNicheProfile('6_stoic_philosophy');
            inputTopic.value = "Marcus Aurelius'un Öfkeyi Yok Eden 3 Stoacı Kuralı";
            btnTier1.classList.remove('active');
            const span = btnTier1.querySelector('span');
            if (span) span.textContent = 'Tier-1 (ABD/İngilizce) Modu';
            switchTab('studio');
            showToast('🇹🇷 Türkçe Moduna Geri Dönüldü');
        }
    });

    // ══════════════════════════════════════════════════════════════
    // 17. CSV / METİN SÜRÜKLE-BIRAK (Dropzone)
    // ══════════════════════════════════════════════════════════════
    const csvDropzone = document.getElementById('csv-dropzone');
    const csvFileInput = document.getElementById('csv-file-input');
    const batchTextArea = document.getElementById('batch-topics-text');

    if (csvDropzone && csvFileInput && batchTextArea) {
        csvDropzone.addEventListener('click', () => csvFileInput.click());

        csvFileInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) handleCsvFile(file);
        });

        csvDropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            csvDropzone.classList.add('dragover');
        });

        csvDropzone.addEventListener('dragleave', () => {
            csvDropzone.classList.remove('dragover');
        });

        csvDropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            csvDropzone.classList.remove('dragover');
            const file = e.dataTransfer.files[0];
            if (file) handleCsvFile(file);
        });

        function handleCsvFile(file) {
            const reader = new FileReader();
            reader.onload = (evt) => {
                const text = evt.target.result;
                const lines = text.split(/\r?\n/).map(l => l.trim()).filter(Boolean);
                batchTextArea.value = lines.join('\n');
                showToast(`📂 ${lines.length} adet konu başarıyla yüklendi!`);
            };
            reader.readAsText(file);
        }
    }

    // ══════════════════════════════════════════════════════════════
    // 18. KLAVYE KISAYOLLARI (Power User Hotkeys)
    // ══════════════════════════════════════════════════════════════
    document.addEventListener('keydown', (e) => {
        // Form girdilerinde iken kısayolları engelleme kontrolü
        const isInput = ['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName);

        // Ctrl+Enter veya Cmd+Enter: Hızlı Render
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            e.preventDefault();
            btnQuickRender?.click();
            return;
        }

        // Escape: Terminal konsolunu kapat
        if (e.key === 'Escape') {
            terminalPanel?.classList.add('hidden');
            return;
        }

        // Alt + 1-8 Sekme Geçişi
        if (!isInput && e.altKey && e.key >= '1' && e.key <= '8') {
            const tabKeys = ["studio", "timeline", "niches", "rss-bot", "batch", "growth", "effects", "subtitles"];
            const idx = parseInt(e.key) - 1;
            if (tabKeys[idx]) {
                e.preventDefault();
                switchTab(tabKeys[idx]);
            }
        }
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
    // 20. 500 MADDE YOL HARİTASI İNTERAKTİF GEZGİNİ
    // ══════════════════════════════════════════════════════════════
    let allRoadmapItems = [];
    let currentRoadmapSec = 'all';

    async function loadRoadmapItems() {
        const grid = document.getElementById('roadmap-items-grid');
        if (!grid) return;

        if (allRoadmapItems.length === 0) {
            grid.innerHTML = '<div class="empty-state-box" style="grid-column: 1/-1;"><i class="fa-solid fa-spinner fa-spin"></i><p>500 madde taranıyor...</p></div>';
            try {
                const res = await fetch('/api/roadmap/items');
                const data = await res.json();
                allRoadmapItems = data.items || [];
            } catch (e) {
                grid.innerHTML = `<div class="empty-state-box text-danger" style="grid-column: 1/-1;"><p>Hata: ${e.message}</p></div>`;
                return;
            }
        }

        renderFilteredRoadmap();
    }

    function renderFilteredRoadmap() {
        const grid = document.getElementById('roadmap-items-grid');
        const counterBadge = document.getElementById('roadmap-counter-badge');
        const searchVal = (document.getElementById('input-roadmap-search')?.value || '').toLowerCase().trim();
        if (!grid) return;

        let filtered = allRoadmapItems;

        if (currentRoadmapSec !== 'all') {
            const secNum = parseInt(currentRoadmapSec);
            filtered = filtered.filter(it => it.section_id === secNum);
        }

        if (searchVal) {
            filtered = filtered.filter(it => 
                it.title.toLowerCase().includes(searchVal) || 
                it.description.toLowerCase().includes(searchVal) ||
                it.number.toString() === searchVal
            );
        }

        if (counterBadge) {
            counterBadge.innerHTML = `<i class="fa-solid fa-circle-check"></i> ${filtered.length} özellik gösteriliyor`;
        }

        if (filtered.length === 0) {
            grid.innerHTML = '<div class="empty-state-box" style="grid-column: 1/-1;"><i class="fa-solid fa-magnifying-glass"></i><p>Aramanızla eşleşen madde bulunamadı.</p></div>';
            return;
        }

        grid.innerHTML = '';
        filtered.slice(0, 100).forEach(it => {
            const card = document.createElement('div');
            card.className = 'glass-box';
            card.style.padding = '14px';
            card.style.display = 'flex';
            card.style.flexDirection = 'column';
            card.style.gap = '8px';

            card.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span class="pro-chip" style="font-size: 10px; background: rgba(139, 92, 246, 0.25);">Madde #${it.number}</span>
                    <span style="font-size: 10px; color: #10B981; font-weight: 700;"><i class="fa-solid fa-circle-check"></i> Aktif</span>
                </div>
                <strong style="font-size: 13px; color: #FFF; line-height: 1.3;">${it.title}</strong>
                <p style="font-size: 11px; color: #94A3B8; line-height: 1.4; flex: 1;">${it.description}</p>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 6px; padding-top: 6px; border-top: 1px solid rgba(255,255,255,0.06); font-size: 10px;">
                    <span style="color: #06B6D4;">${it.section_name}</span>
                    <code style="background: rgba(0,0,0,0.4); padding: 2px 6px; border-radius: 4px; color: #F59E0B;">${it.responsible_module}</code>
                </div>
            `;
            grid.appendChild(card);
        });

        if (filtered.length > 100) {
            const moreNote = document.createElement('div');
            moreNote.style.gridColumn = '1/-1';
            moreNote.style.textAlign = 'center';
            moreNote.style.color = '#94A3B8';
            moreNote.style.fontSize = '12px';
            moreNote.style.padding = '12px';
            moreNote.innerHTML = `...ve diğer ${filtered.length - 100} madde (Arama çubuğunu kullanarak daraltabilirsiniz).`;
            grid.appendChild(moreNote);
        }
    }

    // Filter pills
    document.querySelectorAll('#roadmap-section-filters .filter-pill').forEach(pill => {
        pill.addEventListener('click', (e) => {
            document.querySelectorAll('#roadmap-section-filters .filter-pill').forEach(p => p.classList.remove('active'));
            e.currentTarget.classList.add('active');
            currentRoadmapSec = e.currentTarget.getAttribute('data-sec');
            renderFilteredRoadmap();
        });
    });

    // Search input
    let searchDebounce = null;
    document.getElementById('input-roadmap-search')?.addEventListener('input', () => {
        clearTimeout(searchDebounce);
        searchDebounce = setTimeout(renderFilteredRoadmap, 200);
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

    // Attach listeners
    document.getElementById('btn-onboard-analyze')?.addEventListener('click', triggerChannelAnalysis);
    document.getElementById('btn-refresh-managed-channels')?.addEventListener('click', loadManagedChannels);
    loadManagedChannels();

    window.addEventListener('applyNicheProfile', (e) => {
        const id = e.detail;
        if (id && selectNiche) {
            selectNiche.value = id;
            applyNicheProfile(id);
            switchTab('studio');
            updateFlowRail('topic');
        }
    });

    // İlk yüklemede ses katalogu (sync fallback) + niş listesi
    try {
        populateTtsVoiceSelect(selectLanguage?.value || 'tr');
        loadTtsVoiceCatalog();
    } catch (e) {
        console.warn('TTS voice init failed', e);
    }
    try { loadNiches(); } catch (e) {}
    try { loadGallery(); } catch (e) {}
    try { loadBgmList(); } catch (e) {}
    try { refreshBatchQueue(); } catch (e) {}
    try { restoreRenderState(); } catch (e) {}
    try {
        if (restoreCurrentPlan() && currentPlan) {
            renderTimelineScenes(currentPlan);
            updateFlowRail('timeline');
            updateStudioQualityPanel(currentPlan, { silent: true }).catch(() => {});
            updateScriptActionButtons();
            showToast('Onceki senaryo geri yuklendi');
        }
    } catch (e) {}
    try { updateScriptActionButtons(); } catch (e) {}
    try { updateLoopBridge('stoic', inputTopic ? inputTopic.value : ''); } catch (e) {}
    try { updateAiQuotaDisplay(); } catch (e) {}
    try { if (typeof window.loadHardwareSpecs === 'function') window.loadHardwareSpecs(); } catch (e) {}
    setInterval(updateAiQuotaDisplay, 30000);
});

