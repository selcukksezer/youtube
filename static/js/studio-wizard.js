/**
 * Shorts Studio — 4-Step Setup Wizard Controller (studio-wizard.js)
 * Implements Category A (Items 1–10) User-Friendly Wizard Flow:
 *  1. Mandatory Topic Gate (#wizard-topic-gate-bar & .is-topic-locked)
 *  2. Step Completion Checkmarks (✓ on flow cards & step pills)
 *  3. Interactive Breadcrumb Summary Chips (#wizard-breadcrumb-chips)
 *  4. One-Click Quick Produce Mode (#btn-wiz1-quick-produce)
 *  5. Keyboard Step Navigation (Alt + ArrowLeft / ArrowRight)
 *  6. Auto-Advance Toggle (#chk-wizard-auto-advance)
 *  7. Per-Step Reset to Defaults (#btn-wizard-reset-step)
 *  8. Unfinished Work Resume Banner (#wizard-resume-banner)
 *  9. Estimated Duration Badges (.step-eta-badge)
 * 10. Smooth Directional Step Transition Animation (.wiz-anim-next / .wiz-anim-prev)
 */

const WIZARD_STEPS = [
    { step: 1, code: '01', title: 'Fikir', desc: 'Konu, dil ve niş seçimi', flow: 'topic', eta: '~5 sn kurulum' },
    { step: 2, code: '02', title: 'Senaryo', desc: 'Ses, altyazı ve hook akışı', flow: 'timeline', eta: '~8 sn AI senaryo' },
    { step: 3, code: '03', title: 'Doğrulama', desc: 'Görsel motor ve 14 FX', flow: 'timeline', eta: '~5 sn görsel/FX' },
    { step: 4, code: '04', title: 'Render', desc: 'Kalite kalkanı & 1080×1920', flow: 'render', eta: '~35 sn GPU render' }
];

const TOP_TABS_ORDER = [
    { tab: 'studio', code: 'ÜR', label: 'Üretim Sihirbazı' },
    { tab: 'timeline', code: 'PJ', label: 'Sahne & Plan' },
    { tab: 'clipper', code: 'CL', label: 'Clipper' },
    { tab: 'kids-song', code: 'ÇŞ', label: 'Çocuk Şarkıları' },
    { tab: 'batch', code: 'BT', label: 'Toplu İş' },
    { tab: 'audio', code: 'MD', label: 'Medya & Ses' },
    { tab: 'subtitles', code: 'AL', label: 'Altyazı' },
    { tab: 'effects', code: 'FX', label: 'Split & FX' },
    { tab: 'niches', code: 'AR', label: 'Araştırma & Niş' },
    { tab: 'rss-bot', code: 'RR', label: 'Reddit & RSS' },
    { tab: 'channels', code: 'KY', label: 'Kanal & Yayın' },
    { tab: 'growth', code: 'AN', label: 'Analitik & Büyüme' },
    { tab: 'gallery', code: 'GL', label: 'Galeri' },
    { tab: 'roadmap500', code: 'RM', label: 'Yol Haritası' },
    { tab: 'settings', code: 'SA', label: 'Sistem & Ayarlar' }
];

const WIZARD_STORAGE_STEP_KEY = 'shorts_wizard_last_step';
const WIZARD_STORAGE_AUTO_ADV_KEY = 'shorts_wizard_auto_advance';

let currentWizardStep = 1;
const visitedWizardSteps = new Set([1]);

function animateStats(scope) {
    if (!scope || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    scope.querySelectorAll('.stat strong').forEach((el) => {
        const finalText = el.dataset.final || el.textContent.trim();
        el.dataset.final = finalText;
        const match = finalText.match(/^([^0-9]*)([0-9]+(?:[.,][0-9]+)?)(.*)$/);
        if (!match) return;
        const [, prefix, raw, suffix] = match;
        const target = parseFloat(raw.replace(',', '.'));
        if (!Number.isFinite(target) || target === 0) return;
        const decimals = (raw.split(/[.,]/)[1] || '').length;
        const start = performance.now();
        const duration = 560;
        el.classList.add('counting');
        function frame(now) {
            const p = Math.min(1, (now - start) / duration);
            const e = 1 - Math.pow(1 - p, 3);
            const val = target * e;
            const txt = decimals
                ? val.toFixed(decimals).replace('.', raw.indexOf(',') > -1 ? ',' : '.')
                : Math.round(val).toLocaleString('tr-TR');
            el.textContent = prefix + txt + suffix;
            if (p < 1) requestAnimationFrame(frame);
            else {
                el.textContent = finalText;
                el.classList.remove('counting');
            }
        }
        requestAnimationFrame(frame);
    });
}

function isCurrentTopicPlanReady() {
    const topicVal = (document.getElementById('input-topic')?.value || '').trim();
    const planTopic = (window.currentPlan?.title || window.currentPlan?.topic || window.currentPlan?.keyword || '').trim();
    const scenes = Array.isArray(window.currentPlan?.scenes) ? window.currentPlan.scenes : [];
    return scenes.length > 0 && Boolean(topicVal) && (!planTopic || topicVal.toLowerCase() === planTopic.toLowerCase());
}

function getWizardStepCompletion() {
    const topicVal = (document.getElementById('input-topic')?.value || '').trim();
    const step1Done = Boolean(topicVal);
    const step2Done = isCurrentTopicPlanReady();
    const step3Done = step1Done && (step2Done || visitedWizardSteps.has(3));
    const step4Done = step2Done && visitedWizardSteps.has(4);
    return { 1: step1Done, 2: step2Done, 3: step3Done, 4: step4Done };
}

function syncWizardBreadcrumbsAndTicks() {
    const completion = getWizardStepCompletion();
    const topicVal = (document.getElementById('input-topic')?.value || '').trim();
    const langSel = document.getElementById('select-language');
    const langCode = (langSel?.value || 'tr').toUpperCase();
    const nicheSel = document.getElementById('select-niche');
    const nicheText = (nicheSel?.options?.[nicheSel.selectedIndex]?.text || 'Stoic').split(/[—·(]/)[0].trim();
    const voiceSel = document.getElementById('select-tts-voice');
    const voiceText = (voiceSel?.options?.[voiceSel.selectedIndex]?.text || 'Otomatik Ses').split(/[—·(]/)[0].trim();
    const scenesCount = isCurrentTopicPlanReady() ? (window.currentPlan?.scenes?.length || 0) : 0;
    const splitOn = document.getElementById('chk-split-screen')?.checked;
    const resVal = document.getElementById('select-render-resolution')?.value || '1080p';

    // 1. Update Breadcrumb Summary Chips (Item 3)
    const bcContainer = document.getElementById('wizard-breadcrumb-chips');
    if (bcContainer) {
        const shortTopic = topicVal
            ? (topicVal.length > 24 ? topicVal.slice(0, 24) + '…' : topicVal)
            : 'Konu seçilmedi';
        const chips = [
            { step: 1, label: `01 · ${langCode} · ${nicheText} · ${shortTopic}`, done: completion[1] },
            { step: 2, label: `02 · ${voiceText} · ${scenesCount ? `${scenesCount} Sahne` : 'Senaryo Yok'}`, done: completion[2] },
            { step: 3, label: `03 · ${splitOn ? 'Split-Screen + FX' : 'Tam Ekran 9:16'}`, done: completion[3] },
            { step: 4, label: `04 · ${resVal} · ${completion[2] ? 'Render Hazır' : 'Taslak'}`, done: completion[4] }
        ];
        bcContainer.innerHTML = chips.map((c) => `
            <button type="button" class="wiz-bc-chip${c.step === currentWizardStep ? ' is-current' : ''}${c.done ? ' is-done' : ''}" data-goto-wstep="${c.step}" title="Adım ${c.step} ayarlarına git">
                <span class="wiz-bc-tick">${c.done ? '✓' : c.step}</span>
                <span>${c.label.replace(/</g, '&lt;')}</span>
            </button>
        `).join('');
    }

    // 2. Update Step Completion Ticks on Top 4 Flow Cards (Item 2 & Item 9)
    document.querySelectorAll('#studio-flow-rail .step, #studio-flow-rail .flow-step').forEach((el, idx) => {
        const s = idx + 1;
        const done = Boolean(completion[s]);
        el.classList.toggle('is-active', s === currentWizardStep);
        el.classList.toggle('is-done', done);
        const tickEl = el.querySelector('.step-done-tick');
        if (tickEl) {
            tickEl.textContent = done ? '✓ Tamam' : WIZARD_STEPS[idx]?.eta || '';
            tickEl.classList.toggle('is-tick', done);
        }
    });

    // 3. Update Step Pills in Card Footer & Global Bottom Bar (Item 2)
    document.querySelectorAll('.wizard-step-pill[data-wstep]').forEach((pill) => {
        const s = Number(pill.getAttribute('data-wstep') || 0);
        if (!s) return;
        const done = Boolean(completion[s]);
        pill.classList.toggle('is-done', done);
        const baseLabel = pill.getAttribute('data-base-label') || pill.textContent.replace(/\s*✓$/, '').trim();
        pill.setAttribute('data-base-label', baseLabel);
        pill.textContent = done ? `${baseLabel} ✓` : baseLabel;
    });

    // 4. Mandatory Topic Gate on Step 1 Next Button (Item 1)
    const nextBtn = document.getElementById('btn-wizard-card-next');
    const gateBar = document.getElementById('wizard-topic-gate-bar');
    const locked = currentWizardStep === 1 && !completion[1];
    if (nextBtn) {
        nextBtn.classList.toggle('is-topic-locked', locked);
        if (currentWizardStep < 4) {
            const nextTitle = WIZARD_STEPS[currentWizardStep].title;
            nextBtn.innerHTML = locked
                ? `<i class="fa-solid fa-lock"></i> Sonraki Adım (${nextTitle})`
                : `Sonraki Adım (${nextTitle}) <i class="fa-solid fa-arrow-right"></i>`;
        } else {
            nextBtn.innerHTML = `Sahne & Plan Editörüne Geç <i class="fa-solid fa-sliders"></i>`;
        }
    }
    if (gateBar && (!locked || currentWizardStep !== 1)) {
        gateBar.classList.add('hidden');
    }
}

function syncWizardStep2Preview() {
    const topicVal = (document.getElementById('input-topic')?.value || '').trim();
    const topicTextEl = document.getElementById('wiz-step2-topic-text');
    const topicEmptyActions = document.getElementById('wiz-step2-topic-empty-actions');
    if (topicTextEl) {
        topicTextEl.textContent = topicVal || 'Henüz konu girilmedi — 1. Adımda konu yazın veya öneri alın';
        topicTextEl.style.color = topicVal ? 'var(--ink)' : 'var(--amber)';
    }
    if (topicEmptyActions) {
        topicEmptyActions.style.display = topicVal ? 'none' : 'flex';
    }
    syncWizardBreadcrumbsAndTicks();

    const previewBox = document.getElementById('wizard-inline-script-preview');
    if (!previewBox) return;
    const scenes = Array.isArray(window.currentPlan?.scenes) ? window.currentPlan.scenes : [];
    const isPlanForCurrentTopic = isCurrentTopicPlanReady();

    if (!isPlanForCurrentTopic) {
        previewBox.innerHTML = `
            <div class="wiz-script-empty">
                <span class="status">SENARYO BEKLENİYOR</span>
                <p>${topicVal
                    ? `<b>"${topicVal.replace(/</g, '&lt;')}"</b> konusu hazır. Yukarıdaki <b>Senaryo Yaz</b> butonuna tıkladığınızda yapay zekâ kanca ve sahne metinlerini burada oluşturur.`
                    : `Senaryo üretmek için önce <b>01 Fikir</b> adımında bir konu belirleyin veya <b>Konu Öner</b> butonunu kullanın.`}</p>
            </div>
        `;
        return;
    }

    const totalSec = scenes.reduce((acc, s) => acc + (parseFloat(s.duration) || 3.5), 0).toFixed(1);
    const rowsHtml = scenes.slice(0, 8).map((sc, i) => `
        <div class="list-row">
            <span class="list-icon">${String(i + 1).padStart(2, '0')}</span>
            <div>
                <h4>${i === 0 ? '🎯 Kanca' : i === scenes.length - 1 ? '🔄 Kapanış' : `Sahne ${i + 1}`} · ${(parseFloat(sc.duration) || 3.5).toFixed(1)}s</h4>
                <p>${String(sc.narration || '').replace(/</g, '&lt;')}</p>
            </div>
            <span class="check">✓</span>
        </div>
    `).join('');
    previewBox.innerHTML = `
        <div class="wiz-script-ready">
            <div class="card-head" style="margin-bottom:8px;">
                <div>
                    <h4 style="margin:0;font-size:13px;">Hazırlanan Senaryo Akışı (${scenes.length} Sahne · ${totalSec}s)</h4>
                    <p style="margin:2px 0 0;font-size:11px;color:var(--muted);">Senaryo hazır · İsterseniz 03 Görsel & FX adımına geçin veya detaylı sahne editörünü açın.</p>
                </div>
                <span class="status live">HAZIR</span>
            </div>
            <div class="list">${rowsHtml}</div>
        </div>
    `;
}
window.syncWizardStep2Preview = syncWizardStep2Preview;

function setStudioWizardStep(stepNum, options = {}) {
    const targetStep = Math.max(1, Math.min(4, Number(stepNum) || 1));

    // Item 1: Mandatory Topic Gate when trying to leave Step 1 forward without a topic
    if (currentWizardStep === 1 && targetStep > 1 && !options.force) {
        const topicVal = (document.getElementById('input-topic')?.value || '').trim();
        if (!topicVal) {
            const gateBar = document.getElementById('wizard-topic-gate-bar');
            if (gateBar) gateBar.classList.remove('hidden');
            document.getElementById('input-topic')?.focus();
            if (typeof showToast === 'function') {
                showToast('Önce bir video konusu yazın veya "Otomatik Konu Seç" butonuna tıklayın.', 'warning');
            }
            return false;
        }
    }

    const prevStep = currentWizardStep;
    currentWizardStep = targetStep;
    visitedWizardSteps.add(targetStep);

    try { localStorage.setItem(WIZARD_STORAGE_STEP_KEY, String(targetStep)); } catch (e) {}

    const formCard = document.querySelector('#pane-studio .studio-form-card');
    if (formCard) {
        formCard.setAttribute('data-active-wstep', String(targetStep));
        if (prevStep !== targetStep) {
            const animClass = targetStep > prevStep ? 'wiz-anim-next' : 'wiz-anim-prev';
            formCard.classList.remove('wiz-anim-next', 'wiz-anim-prev');
            void formCard.offsetWidth;
            formCard.classList.add(animClass);
        }
    }

    if (targetStep === 2) {
        if (typeof updateScriptActionButtons === 'function') updateScriptActionButtons();
        syncWizardStep2Preview();
    }
    if (targetStep === 3) {
        const rs = document.getElementById('studio-render-settings');
        const re = document.getElementById('render-enhancement-options');
        if (rs) rs.open = true;
        if (re) re.open = true;
        if (typeof window.syncWizardStep3UI === 'function') window.syncWizardStep3UI();
    }
    if (targetStep === 4) {
        if (typeof window.syncWizardStep4UI === 'function') window.syncWizardStep4UI();
    }

    const meta = WIZARD_STEPS[targetStep - 1];
    const badge = document.getElementById('wizard-step-badge');
    if (badge) badge.textContent = `ADIM ${targetStep} / 4`;
    const etaBadge = document.getElementById('wizard-step-eta');
    if (etaBadge && meta) etaBadge.textContent = meta.eta;
    const statWstep = document.getElementById('stat-card-wstep');
    if (statWstep) statWstep.textContent = `${targetStep} / 4`;
    const info = document.getElementById('wizard-card-step-info');
    if (info && meta) {
        info.textContent = `ADIM ${meta.code} · ${meta.title.toUpperCase()} — ${meta.desc}`;
    }

    const prevBtn = document.getElementById('btn-wizard-card-prev');
    if (prevBtn) prevBtn.disabled = targetStep <= 1;

    syncWizardBreadcrumbsAndTicks();
    syncGlobalWizardBar();

    if (options.scroll && formCard && typeof formCard.scrollIntoView === 'function') {
        formCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
    return true;
}
window.setStudioWizardStep = setStudioWizardStep;
window.switchWizardStep = (step, opts = { force: true }) => setStudioWizardStep(step, opts);

// Item 6: Auto-Advance callback when script generation finishes
window.onWizardScriptGenerated = function () {
    syncWizardStep2Preview();
    const autoAdv = document.getElementById('chk-wizard-auto-advance')?.checked;
    if (autoAdv && document.getElementById('pane-studio')?.classList.contains('active')) {
        if (typeof showToast === 'function') {
            showToast('Senaryo hazır! Otomatik olarak Adım 03 (Görsel & FX) açılıyor…');
        }
        setTimeout(() => {
            if (currentWizardStep === 2) {
                setStudioWizardStep(3, { scroll: true, force: true });
            }
        }, 1200);
    }
};

// Item 7: Per-Step Reset to Defaults
function resetCurrentWizardStep() {
    if (currentWizardStep === 1) {
        const inputEl = document.getElementById('input-topic');
        if (inputEl) inputEl.value = '';
        const langEl = document.getElementById('select-language');
        if (langEl) langEl.value = 'tr';
        const nicheEl = document.getElementById('select-niche');
        if (nicheEl && nicheEl.options.length) nicheEl.selectedIndex = 0;
        const subEl = document.getElementById('select-subtitle-preset') || document.getElementById('select-sub-style') || document.getElementById('select-sub-preset');
        if (subEl) subEl.value = 'hormozi';
    } else if (currentWizardStep === 2) {
        const voiceEl = document.getElementById('select-tts-voice');
        if (voiceEl && voiceEl.options.length) voiceEl.selectedIndex = 0;
        window.currentPlan = null;
        try { localStorage.removeItem('shorts_current_plan_v1'); } catch (e) {}
    } else if (currentWizardStep === 3) {
        ['chk-split-screen', 'chk-ken-burns', 'chk-zoompan'].forEach((id) => {
            const el = document.getElementById(id);
            if (el) el.checked = id === 'chk-ken-burns';
        });
        const bgmEl = document.getElementById('studio-bgm-track');
        if (bgmEl) bgmEl.value = 'auto';
    } else if (currentWizardStep === 4) {
        const resEl = document.getElementById('select-render-resolution');
        if (resEl) resEl.value = '1080p';
        const safeEl = document.getElementById('select-studio-safe-mode');
        if (safeEl) safeEl.value = 'standard';
    }
    if (typeof updateScriptActionButtons === 'function') updateScriptActionButtons();
    if (typeof saveStudioSettings === 'function') saveStudioSettings();
    syncWizardStep2Preview();
    if (typeof showToast === 'function') {
        showToast(`Adım 0${currentWizardStep} varsayılan ayarlara sıfırlandı.`);
    }
}

// Item 4: One-Click Quick Produce Mode
async function runQuickProduceWithDefaults() {
    const inputEl = document.getElementById('input-topic');
    let topicVal = (inputEl?.value || '').trim();
    if (!topicVal) {
        const nicheEl = document.getElementById('select-niche');
        const nicheLabel = (nicheEl?.options?.[nicheEl.selectedIndex]?.text || 'Stoic Felsefesi').split(/[—·(]/)[0].trim();
        topicVal = `${nicheLabel}: Çoğu İnsanın Çok Geç Fark Ettiği 3 Gerçek`;
        if (inputEl) {
            inputEl.value = topicVal;
            inputEl.dispatchEvent(new Event('input', { bubbles: true }));
        }
        if (typeof showToast === 'function') {
            showToast(`Hızlı üretim için konu seçildi: "${topicVal}"`);
        }
    }
    setStudioWizardStep(4, { scroll: true, force: true });
    setTimeout(() => {
        const directBtn = document.getElementById('btn-quick-render') || document.getElementById('btn-start-render') || document.getElementById('btn-direct-render');
        if (directBtn && !directBtn.disabled) {
            directBtn.click();
        } else if (typeof generateScriptFromTopic === 'function') {
            generateScriptFromTopic(false);
        }
    }, 220);
}

function syncGlobalWizardBar() {
    const activePane = document.querySelector('.tab-pane.active');
    const activeTab = activePane ? activePane.id.replace(/^pane-/, '') : 'studio';
    document.querySelectorAll('.top-module-tab[data-tab]').forEach((b) => {
        b.classList.toggle('active', b.getAttribute('data-tab') === activeTab);
    });
    document.querySelectorAll('.wizard-step-pill').forEach((pill) => {
        const pTab = pill.getAttribute('data-wtab');
        const pStep = Number(pill.getAttribute('data-wstep') || 0);
        const isActive = activeTab === 'studio' ? (pTab === 'studio' && pStep === currentWizardStep) : (pTab === activeTab && !pStep);
        pill.classList.toggle('active', isActive);
    });
}

window.onShortsTabSwitched = function (tabId) {
    syncGlobalWizardBar();
    const pane = document.getElementById(`pane-${tabId}`);
    if (pane) animateStats(pane);
};

function stepWizardGlobal(delta) {
    const activePane = document.querySelector('.tab-pane.active');
    const activeTab = activePane ? activePane.id.replace(/^pane-/, '') : 'studio';
    if (activeTab === 'studio') {
        const nextStep = currentWizardStep + delta;
        if (nextStep >= 1 && nextStep <= 4) {
            setStudioWizardStep(nextStep, { scroll: true });
            return;
        }
        if (nextStep > 4) {
            switchTab('timeline');
            return;
        }
    }
    const idx = TOP_TABS_ORDER.findIndex((t) => t.tab === activeTab);
    const targetIdx = (idx + delta + TOP_TABS_ORDER.length) % TOP_TABS_ORDER.length;
    const targetTab = TOP_TABS_ORDER[targetIdx]?.tab || 'studio';
    switchTab(targetTab);
    if (targetTab === 'studio') {
        setStudioWizardStep(delta < 0 ? 4 : 1, { force: true });
    }
}
window.switchWizardStep = setStudioWizardStep;

