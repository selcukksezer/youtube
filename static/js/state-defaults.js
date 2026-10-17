/**
 * ShortsAI Studio — Default State Schema, Constants & Niche UI Mappings (state-defaults.js)
 * Provides default state presets, constants, niche family mappings, and quality gate UI cards.
 */

window.ShortsApp = window.ShortsApp || {};

window.ShortsApp.DEFAULT_STATE = {
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

window.ShortsApp.state = window.ShortsApp.state || { ...window.ShortsApp.DEFAULT_STATE };

const PLAN_STORAGE_KEY = 'shortsCurrentPlan';
const PLAN_SCHEMA_VERSION = 2;
const STUDIO_SETTINGS_STORAGE_KEY = 'shortsStudioSettings';

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

const NARRATION_DANGLING = new Set([
    've', 'ama', 'cunku', 'çünkü', 'icin', 'için', 'ise', 'senin', 'kendi', 'olan', 'asla',
    'onlara', 'degil', 'değil', 'kusuru', 'bozan', 'ruhunu', 'imparator', 'kaleni', 'ic', 'iç',
    'en', 'ust', 'üst', 'kural', 'her', 'sey', 'şey', 'fani', 'marcus'
]);

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
    if (typeof switchTab === 'function') switchTab('roadmap500');
    const searchEl = document.getElementById('input-roadmap-search');
    if (searchEl) {
        searchEl.value = String(itemNum);
        if (typeof renderFilteredRoadmap === 'function') renderFilteredRoadmap();
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

function formatPipelineAuditWarning(warning) {
    const text = String(warning || '');
    const sceneWarnings = [];
    const addSceneWarning = (sceneNumber, message) => {
        const scene = Number(sceneNumber);
        if (Number.isInteger(scene) && scene > 0) {
            sceneWarnings.push({ scene, message });
        }
    };

    const frameWarning = text.match(/^visual_frame_(near_black|unavailable):scene_(\d+)/);
    if (frameWarning) {
        addSceneWarning(
            frameWarning[2],
            frameWarning[1] === 'near_black' ? 'Örnek kare çok karanlık' : 'Örnek kare alınamadı'
        );
    }
    const stockMatches = text.match(/^stock_match_low_confidence_scenes:(.+)$/);
    if (stockMatches) {
        stockMatches[1].split(',').forEach(scene =>
            addSceneWarning(scene, 'Stok metadata eşleşme puanı düşük')
        );
    }
    const duplicatePairs = text.match(/^visual_frames_near_duplicate:(.+)$/);
    if (duplicatePairs) {
        duplicatePairs[1].split(',').forEach(pair => {
            const [left, right] = pair.split('-');
            addSceneWarning(left, `Örnek kare Sahne ${right} ile benzer`);
            addSceneWarning(right, `Örnek kare Sahne ${left} ile benzer`);
        });
    }
    if (text.startsWith('semantic_mismatch:')) {
        [...text.matchAll(/scene\[(\d+)\]score=([\d.]+)/g)].forEach(match =>
            addSceneWarning(match[1], `Metin/metadata eşleşmesi düşük (${Math.round(Number(match[2]) * 100)}%)`)
        );
    }

    if (!sceneWarnings.length) {
        return `<li>${escapeHtml(text.replace(/_/g, ' '))}</li>`;
    }
    return sceneWarnings.map(({ scene, message }) =>
        `<li><button type="button" class="qg-scene-jump" data-scene-number="${scene}">Sahne ${scene}</button>: ${escapeHtml(message)}</li>`
    ).join('');
}

function renderQualityGateCard(qg, { compact = false } = {}) {
    if (!qg) return '';
    const post = qg.post || qg;
    const pipelineAudit = qg.pipeline_audit || {};
    const auditReport = pipelineAudit.report || {};
    const signalReport = auditReport.signal_analysis || {};
    const preRenderReport = pipelineAudit.pre_render?.report || {};
    const visualFrameAudit = preRenderReport.visual_frame_audit || {};
    const renderDiagnostics = qg.render_diagnostics || {};
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
    const metrics = [
        auditReport.resolution,
        auditReport.fps != null ? `${Number(auditReport.fps).toFixed(2)} FPS` : '',
        signalReport.peak_volume_dbfs != null ? `Ses tepesi ${Number(signalReport.peak_volume_dbfs).toFixed(1)} dBFS` : '',
    ].filter(Boolean);
    if (preRenderReport.avg_stock_semantic_score != null) {
        metrics.push(
            `Stok eşleşme ${Math.round(Number(preRenderReport.avg_stock_semantic_score) * 100)}%` +
            ` · düşük ${preRenderReport.low_stock_match_count || 0}` +
            ` · stok sahne ${preRenderReport.stock_scene_count || 0}`
        );
    }
    if (visualFrameAudit.available) {
        metrics.push(
            `Örnek kare ${visualFrameAudit.sampled_scene_count || 0}/${visualFrameAudit.scene_count || 0}`
        );
    }
    const telemetry = renderDiagnostics.pipeline || {};
    if (telemetry.total_duration_sec != null) {
        metrics.push(`Pipeline ${Number(telemetry.total_duration_sec).toFixed(1)}sn`);
    }
    const stageRows = telemetry.stages || [];
    const slowestStage = stageRows.reduce((slowest, stage) =>
        !slowest || Number(stage.duration_sec || 0) > Number(slowest.duration_sec || 0)
            ? stage
            : slowest
    , null);
    if (slowestStage) {
        metrics.push(
            `En uzun aşama ${slowestStage.name}: ${Number(slowestStage.duration_sec || 0).toFixed(1)}sn`
        );
    }
    const providerRows = Object.entries(renderDiagnostics.provider_search?.providers || {});
    const slowestProvider = providerRows.sort(
        (left, right) => Number(right[1].max_ms || 0) - Number(left[1].max_ms || 0)
    )[0];
    if (slowestProvider) {
        metrics.push(
            `En yavaş stok arama ${slowestProvider[0]}: ${Number(slowestProvider[1].max_ms || 0).toFixed(0)}ms`
        );
    }
    const metricHtml = metrics.length
        ? `<span class="studio-qg-meta">Render: ${metrics.map(escapeHtml).join(' · ')}</span>`
        : '';
    const auditWarnings = pipelineAudit.warnings || [];
    const auditWarningHtml = auditWarnings.length
        ? `<ul class="studio-qg-issues">${auditWarnings.map(warning =>
            formatPipelineAuditWarning(warning)
        ).join('')}</ul>`
        : '';
    const visualAuditLink = visualFrameAudit.contact_sheet_written && visualFrameAudit.url
        ? `<a href="${escapeHtml(visualFrameAudit.url)}" target="_blank" rel="noopener noreferrer">Sahne örnek karelerini incele</a>`
        : '';
    return `
        <div class="studio-qg-card ${ok ? '' : 'is-fail'}">
            <strong class="${statusClass}">Kalite Kapısı: ${statusText}</strong>
            <span class="studio-qg-meta">skor ${score} · süre ${dur}</span>
            ${metricHtml}
            ${visualAuditLink ? `<span class="studio-qg-meta">${visualAuditLink}</span>` : ''}
            ${issueHtml}
            ${auditWarningHtml}
        </div>`;
}

document.addEventListener('click', (e) => {
    const sceneButton = e.target?.closest?.('.qg-scene-jump');
    if (sceneButton) {
        e.preventDefault();
        const sceneNumber = Number(sceneButton.getAttribute('data-scene-number'));
        if (!Number.isInteger(sceneNumber) || sceneNumber < 1) return;
        if (typeof switchTab === 'function') switchTab('timeline');
        window.setTimeout(() => {
            const sceneCard = document.querySelector(
                `.scene-item-card[data-scene-idx="${sceneNumber - 1}"]`
            );
            if (!sceneCard) {
                showToast('Bu sahnenin düzenleme planı şu an açık değil.', 'warn');
                return;
            }
            sceneCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
            sceneCard.classList.add('qg-scene-highlight');
            window.setTimeout(() => sceneCard.classList.remove('qg-scene-highlight'), 1800);
        }, 80);
        return;
    }
    const link = e.target?.closest?.('.qg-roadmap-link');
    if (!link) return;
    e.preventDefault();
    const itemNum = parseInt(link.getAttribute('data-roadmap-item'), 10);
    if (itemNum) openRoadmapDeepLink(itemNum);
});

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
    const hit = (window.allNiches || []).find(n => n.id === nicheId);
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
    if (!isRedditNiche(nicheId)) window.selectedRedditPost = null;
}

function showNicheLockBadge(nicheId, nicheName) {
    const badge = document.getElementById('niche-lock-badge');
    const label = document.getElementById('niche-lock-label');
    if (!badge || !label) return;
    window.lockedNicheId = nicheId || null;
    if (!nicheId) {
        badge.classList.add('hidden');
        label.textContent = '—';
        return;
    }
    const name = nicheName || (window.allNiches || []).find(n => n.id === nicheId)?.name || nicheId;
    label.textContent = name;
    badge.classList.remove('hidden');
}

function resetComplianceDashboard() {
    [
        ['tl-dur-value', '0s'], ['tl-scene-value', '0'], ['tl-longcut-value', '—'],
        ['tl-dupe-value', '—'], ['tl-clip-value', '0/0'], ['tl-word-value', '0']
    ].forEach(([id, val]) => { const el = document.getElementById(id); if (el) el.textContent = val; });
    const chipDur = document.getElementById('tl-chip-duration') || document.getElementById('chip-duration-band');
    const chipCad = document.getElementById('tl-chip-scenes') || document.getElementById('chip-cadence');
    const chip32 = document.getElementById('tl-chip-longcuts') || document.getElementById('chip-32s-violations');
    const chipDup = document.getElementById('tl-chip-dupes') || document.getElementById('chip-duplicates');
    if (chipDur && chipDur.id === 'chip-duration-band') {
        chipDur.className = 'compliance-chip';
        const t = document.getElementById('chip-duration-text');
        if (t) t.textContent = 'Süre: —';
    }
    if (chipCad && chipCad.id === 'chip-cadence') {
        chipCad.className = 'compliance-chip';
        const t = document.getElementById('chip-cadence-text');
        if (t) t.textContent = 'Cadence: —';
    }
    if (chip32 && chip32.id === 'chip-32s-violations') {
        chip32.className = 'compliance-chip status-ok';
        const t = document.getElementById('chip-32s-text');
        if (t) t.textContent = '3.2sn Uyarı: 0';
    }
    if (chipDup && chipDup.id === 'chip-duplicates') {
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
