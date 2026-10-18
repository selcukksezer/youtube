/**
 * ShortsAI Studio — Core Studio Orchestration & Generation Flows (studio.js)
 * Handles core script generation, topic suggestion, niche profile application, and language switching.
 */

document.getElementById('btn-new-topic')?.addEventListener('click', clearCurrentScenario);

function showScriptGenerationToast(validation, forceRegenerate, qualityRepair) {
    if (qualityRepair?.status === 'repaired') {
        showToast('Senaryo kalite uyarıları yapay zekâ tarafından otomatik düzeltildi.', 'success');
        return;
    }
    if (qualityRepair && !['not_needed'].includes(qualityRepair.status)) {
        showToast('Senaryo kalite sorunlarının bir kısmı otomatik düzeltilemedi; timeline raporunu inceleyin.', 'warn');
        return;
    }
    if (validation?.hard_fail || validation?.ok === false) {
        showToast('Senaryo üretildi ancak kalite kapısı renderı engelliyor; timeline uyarılarını düzeltin.', 'warn');
        return;
    }
    showToast(
        forceRegenerate ? 'Senaryo başarıyla yeniden yazıldı' : 'Senaryo hazır — timeline\'da inceleyin',
        'success',
    );
}

async function generateScriptFromTopic({ forceRegenerate = false } = {}) {
    const topic = (inputTopic?.value || '').trim();
    if (!topic) {
        alert('Lütfen bir video konusu girin!');
        inputTopic?.focus();
        return;
    }
    const continuityInput = document.getElementById('input-series-continuity');
    const continuityContext = continuityInput?.value.trim() || '';
    if (selectedRedditPost && continuityContext) {
        showToast('Reddit hikâyesi yeniden yazımında seri devamlılığı notları desteklenmiyor.', 'warning');
        return;
    }

    const planTopic = (currentPlan?.title || currentPlan?.topic || currentPlan?.keyword || '').trim();
    const topicChanged = hasExistingPlan() && planTopic && (topic.toLowerCase() !== planTopic.toLowerCase());

    if (!forceRegenerate && hasExistingPlan() && !topicChanged && !planHasBrokenNarration(currentPlan)) {
        navigateToScenario();
        return;
    }

    const btnRegenerateStudio = document.getElementById('btn-regenerate-script-studio');
    const btnRegenerateTimeline = document.getElementById('btn-regenerate-scenario');

    if (btnCreateScript) {
        btnCreateScript.dataset.generating = 'true';
        btnCreateScript.disabled = true;
        btnCreateScript.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> AI Senaryosu Yazılıyor...';
    }
    if (btnRegenerateStudio) {
        btnRegenerateStudio.disabled = true;
        btnRegenerateStudio.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Yazılıyor...';
    }
    if (btnRegenerateTimeline) {
        btnRegenerateTimeline.disabled = true;
    }

    showToast('AI senaryoyu oluşturuyor — sahneler ve kancalar hazırlanıyor...');

    try {
        if (!userManuallyPickedNiche && !selectNiche?.value) {
            await resolveAndApplyNicheFromTopic({ toast: false });
        }

        if (forceRegenerate) {
            window._studioVariationAttempt = (window._studioVariationAttempt || 0) + 1;
        } else {
            window._studioVariationAttempt = 0;
        }
        const prevNarr = currentPlan?.full_narration || (currentPlan?.scenes || []).map(s => s.narration).filter(Boolean).join(' ') || '';
        const isEn = (window.APP_STATE && window.APP_STATE.language === 'en') || document.getElementById('select-language')?.value === 'en';

        const res = await fetch('/api/script/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                keyword: topic,
                language: isEn ? 'en' : 'tr',
                niche: selectNiche?.value || '6_stoic_philosophy',
                reddit_post: selectedRedditPost,
                format_fingerprint: pendingFormatFingerprint || undefined,
                force_regenerate: !!forceRegenerate,
                variation_attempt: window._studioVariationAttempt || 0,
                previous_narration: forceRegenerate ? prevNarr : null,
                continuity_context: continuityContext || null,
                enable_outro: document.getElementById('chk-enable-outro')
                    ? !!document.getElementById('chk-enable-outro').checked
                    : true
            })
        });
        const data = await res.json();
        if (data.status === 'ok') {
            let plan = data.plan;
            const seriesContinuity = plan.series_continuity;
            const lockedNiche = plan.niche_id || plan.niche_profile?.id;
            if (!userManuallyPickedNiche && lockedNiche && selectNiche && selectNiche.value !== lockedNiche) {
                selectNiche.value = lockedNiche;
                await applyNicheProfile(lockedNiche);
            }
            const activeNiche = selectNiche ? selectNiche.value : lockedNiche;
            if (activeNiche) {
                const activeName = allNiches.find(n => n.id === activeNiche)?.name || activeNiche;
                showNicheLockBadge(activeNiche, activeName);
            }
            timelineReviewed = false;
            setCurrentPlan(plan, { skipQualityPanel: true });
            if (data.plagiarism) applyPlagiarismBadge(data.plagiarism);
            if (data.hook_variants?.variants?.length) {
                plan.hook_variants = data.hook_variants.variants;
            }
            const validation = await updateStudioQualityPanel(plan);
            if (validation?.plan) plan = validation.plan;
            if (seriesContinuity) plan.series_continuity = seriesContinuity;
            if (data.plagiarism) applyPlagiarismBadge(data.plagiarism);

            renderTimelineScenes(plan);
            persistCurrentPlan();
            saveStudioSettings();

            if (plan?.procedural_fallback || plan?.meta?.procedural_fallback) {
                showToast(
                    'AI kotası dolu (429) veya erişilemedi — prosedürel şablon senaryosu kullanıldı. Timeline\'da düzenleyebilir veya yeniden deneyebilirsiniz.',
                    'warning',
                );
            } else {
                showScriptGenerationToast(validation, forceRegenerate, data.script_quality_repair);
            }
            if (seriesContinuity?.applied === false) {
                showToast('AI üretimi kullanılamadığı için bu taslakta seri devamlılığı bağlamı uygulanmadı.', 'warning');
            }
            updateFlowRail('timeline');
            if (typeof window.onWizardScriptGenerated === 'function') {
                window.onWizardScriptGenerated();
            } else if (typeof window.syncWizardStep2Preview === 'function') {
                window.syncWizardStep2Preview();
            }
            if (!document.getElementById('pane-studio')?.classList.contains('active')) {
                switchTab('timeline');
            } else if (typeof window.setStudioWizardStep === 'function') {
                window.setStudioWizardStep(2, { scroll: false, force: true });
            }
        } else {
            const errMsg = data.detail || data.error || data.message || 'Senaryo oluşturulamadı.';
            alert('Senaryo oluşturulamadı: ' + errMsg);
        }
    } catch (err) {
        alert('Hata: ' + err.message);
    } finally {
        if (btnCreateScript) {
            btnCreateScript.disabled = false;
            delete btnCreateScript.dataset.generating;
        }
        if (btnRegenerateStudio) btnRegenerateStudio.disabled = false;
        if (btnRegenerateTimeline) btnRegenerateTimeline.disabled = false;
        updateScriptActionButtons();
    }
}

(btnCreateScript || document.getElementById('btn-create-script'))?.addEventListener('click', () => generateScriptFromTopic());
document.getElementById('btn-regenerate-script-studio')?.addEventListener('click', () => generateScriptFromTopic({ forceRegenerate: true }));
document.getElementById('btn-regenerate-scenario')?.addEventListener('click', () => generateScriptFromTopic({ forceRegenerate: true }));

inputTopic?.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && !event.isComposing) event.preventDefault();
});

inputTopic?.addEventListener('input', () => {
    if (!suppressFingerprintClear) clearPendingFormatFingerprint();
    suppressFingerprintClear = false;
    updateFlowRail('topic');
    updateLoopBridge(selectNiche ? selectNiche.value : '6_stoic_philosophy', inputTopic.value);
    updateScriptActionButtons();
    checkTopicLanguageAndSuggestTranslation();
    saveStudioSettings();
    if (!userManuallyPickedNiche) scheduleNicheResolveFromTopic();
});
inputTopic?.addEventListener('change', () => {
    updateScriptActionButtons();
    saveStudioSettings();
    if (!userManuallyPickedNiche) resolveAndApplyNicheFromTopic({ toast: true });
});
inputTopic?.addEventListener('blur', () => {
    saveStudioSettings();
    if (!userManuallyPickedNiche) resolveAndApplyNicheFromTopic({ toast: true });
});

let lastTopicSuggestions = [];

function renderTopicSuggestCards(suggestions, nicheName) {
    const panel = document.getElementById('topic-suggest-panel');
    const body = document.getElementById('topic-suggest-body');
    const titleEl = document.getElementById('topic-suggest-title');
    if (!panel || !body) return;
    lastTopicSuggestions = suggestions || [];
    panel.classList.remove('hidden');
    const isEn = (selectLanguage?.value || 'tr') === 'en';
    if (titleEl && nicheName) {
        titleEl.innerHTML = `<i class="fa-solid fa-wand-magic-sparkles"></i> ${escapeHtml(nicheName)} — ${isEn ? '5 Topic Suggestions' : '5 Konu Önerisi'}`;
    }
    if (!suggestions || !suggestions.length) {
        body.innerHTML = `<div class="topic-suggest-empty">${isEn ? 'No topics found for this niche. Try again.' : 'Bu niş için uygun konu bulunamadı. Yeniden deneyin.'}</div>`;
        return;
    }
    body.innerHTML = suggestions.map((s, idx) => {
        const src = TOPIC_SOURCE_LABELS[s.source] || TOPIC_SOURCE_LABELS.ai;
        const hook = s.hook ? `<div class="topic-suggest-card-hook">${escapeHtml(s.hook)}</div>` : '';
        const sourceDetail = s.source_detail
            ? `<span class="topic-suggest-source-detail">${escapeHtml(s.source_detail)}</span>`
            : '';
        const scoreLabel = isEn ? `Relevance ${s.confidence || s.relevance || 0}/100` : `Uygunluk ${s.confidence || s.relevance || 0}/100`;
        return `
            <button type="button" class="topic-suggest-card" data-suggest-idx="${idx}">
                <div class="topic-suggest-card-title">${idx + 1}. ${escapeHtml(s.title)}</div>
                ${hook}
                <div class="topic-suggest-card-meta">
                    <span class="topic-suggest-badge ${src.cls}"><i class="${src.icon}"></i> ${src.label}</span>
                    ${sourceDetail}
                    <span class="topic-suggest-score">${scoreLabel}</span>
                </div>
            </button>`;
    }).join('');
    body.querySelectorAll('.topic-suggest-card').forEach(card => {
        card.addEventListener('click', () => {
            const idx = Number(card.dataset.suggestIdx);
            const picked = lastTopicSuggestions[idx];
            if (!picked) return;
            if (inputTopic) inputTopic.value = picked.title;
            setPendingFormatFingerprint(picked.format_fingerprint || null);
            updateLoopBridge(selectNiche?.value || '1_news_flash', picked.title);
            resolveAndApplyNicheFromTopic({ toast: false }).catch(() => {});
            panel.classList.add('hidden');
            showToast(`Konu seçildi: ${picked.title.slice(0, 60)}${picked.title.length > 60 ? '…' : ''}`);
        });
    });
}

async function suggestTopic(ev) {
    const isRetry = ev && (ev.target?.id === 'btn-retry-topic-suggest' || ev.currentTarget?.id === 'btn-retry-topic-suggest');
    const nicheId = selectNiche?.value;
    const panel = document.getElementById('topic-suggest-panel');
    const body = document.getElementById('topic-suggest-body');
    const btn = document.getElementById('btn-suggest-topic');
    if (!nicheId) {
        showToast('Önce bir niş şablonu seçin.', 'warn');
        return;
    }
    const isEn = (window.APP_STATE && window.APP_STATE.language === 'en') || document.getElementById('select-language')?.value === 'en';
    const language = isEn ? 'en' : 'tr';
    const rawHint = (inputTopic?.value || '').trim();
    const isSample = typeof isTopicSampleOrEmpty === 'function' ? isTopicSampleOrEmpty(rawHint) : false;
    const topicHint = (!isRetry && rawHint && !isSample && !rawHint.includes('#')) ? rawHint : undefined;
    if (panel) panel.classList.remove('hidden');
    if (body) body.innerHTML = `<div class="topic-suggest-loading"><i class="fa-solid fa-spinner fa-spin"></i> ${isEn ? 'Searching for fresh and unique topics…' : 'Yeni ve benzersiz konular araştırılıyor…'}</div>`;
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
                topic_hint: topicHint,
                refresh: true,
            }),
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || (isEn ? 'Could not fetch topic suggestions.' : 'Konu önerileri alınamadı.'));
        if (data.topic_hint_ignored) {
            showToast(
                isEn
                    ? 'Your current title does not match this niche; suggestions were generated for the selected niche.'
                    : 'Mevcut başlık seçili nişle uyuşmadı; öneriler seçili nişe göre üretildi.',
                'warn',
            );
        }
        renderTopicSuggestCards(data.suggestions, data.niche_name);
    } catch (err) {
        if (body) body.innerHTML = `<div class="topic-suggest-error">${escapeHtml(err.message || (isEn ? 'Connection error' : 'Bağlantı hatası'))}</div>`;
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
    profileBox.classList.add('hidden');
    profileBox.replaceChildren();
    try {
        const response = await fetch(`/api/niches/${encodeURIComponent(nicheId)}/profile`);
        const data = await response.json();
        const profile = data.profile;
        if (!profile) throw new Error('Yanıtta niş üretim profili yok.');
        const rules = profile.production_rules || {};
        if (!splitTouched && chkSplitScreen) {
            chkSplitScreen.checked = Boolean(rules.split_screen);
        }
        if (chkKenBurns) chkKenBurns.checked = Boolean(rules.ken_burns);
        if (rules.subtitle_preset && selectSubPreset) selectSubPreset.value = rules.subtitle_preset;
        profileBox.innerHTML = `
            <div style="display: flex; justify-content: space-between; gap: 8px; align-items: center;">
                <strong style="font-size: 12px; color: #67e8f9;"><i class="fa-solid fa-sliders"></i> Aktif Niş Profili: ${escapeHtml(profile.name)}</strong>
                <span class="niche-tag">${escapeHtml(profile.category)}</span>
            </div>
            <div style="font-size: 11px; color: #cbd5e1; margin-top: 6px;">Ton: ${escapeHtml(profile.tone)}</div>
            <div style="font-size: 11px; color: #94a3b8; margin-top: 4px;">${rules.split_screen ? 'Split-screen' : 'Tam ekran'} · ${escapeHtml(rules.subtitle_preset)} altyazı · Dinamik hareket · Neon ilerleme</div>
        `;
        profileBox.classList.remove('hidden');
        updateLoopBridge(nicheId, inputTopic?.value || '');
        applyNichePanelVisibility(nicheId);
        const gapField = document.getElementById('content-gap-topics');
        if (gapField && Array.isArray(profile.content_gap_examples) && profile.content_gap_examples.length) {
            gapField.placeholder = profile.content_gap_examples.map(line => `Örn: ${line}`).join('\n');
        }
        if (typeof window.refreshWizardStep1UI === 'function') window.refreshWizardStep1UI();
        if (typeof window.syncWizardStep2Preview === 'function') window.syncWizardStep2Preview();
    } catch (error) {
        profileBox.textContent = 'Niş üretim profili yüklenemedi.';
        profileBox.classList.remove('hidden');
        console.error('Niş profili yükleme hatası:', error);
    }
}

function ensureTtsVoiceForLanguage(lang) {
    if (!selectTtsVoice || !selectTtsVoice.value || selectTtsVoice.value === 'auto') return;

    const catalogs = [
        ...(ttsVoiceCatalog[lang] || []),
        ...(ttsVoiceCatalog.local || []),
        ...LOCAL_OFFLINE_VOICES,
        ...(ttsVoiceCatalog.elevenlabs || []),
    ];
    if (catalogs.some(voice => voice.id === selectTtsVoice.value)) return;

    const fallbackVoice = lang === 'en' ? 'en-US-GuyNeural' : 'tr-TR-AhmetNeural';
    selectTtsVoice.value = [...selectTtsVoice.options].some(option => option.value === fallbackVoice)
        ? fallbackVoice
        : 'auto';
}

function setStudioLanguage(lang, options = {}) {
    const isEn = (lang === 'en');
    const targetLang = isEn ? 'en' : 'tr';

    const selLang = document.getElementById('select-language');
    if (selLang) {
        selLang.value = targetLang;
    }

    const btnTr = document.getElementById('btn-quick-lang-tr');
    const btnEn = document.getElementById('btn-quick-lang-en');
    if (btnTr && btnEn) {
        btnTr.setAttribute('aria-pressed', String(!isEn));
        btnEn.setAttribute('aria-pressed', String(isEn));
        if (isEn) {
            btnTr.classList.remove('active');
            btnTr.classList.add('btn-outline');
            btnEn.classList.add('active');
            btnEn.classList.remove('btn-outline');
        } else {
            btnEn.classList.remove('active');
            btnEn.classList.add('btn-outline');
            btnTr.classList.add('active');
            btnTr.classList.remove('btn-outline');
        }
    }

    saveStudioSettings();

    if (inputTopic) {
        if (isEn) {
            inputTopic.placeholder = 'e.g.: 3 Dark Psychology Secrets Manipulation Experts Never Tell You';
        } else {
            inputTopic.placeholder = "Örn: Marcus Aurelius'un Öfkeyi Yok Eden 3 Stoacı Kuralı";
        }
    }

    if (typeof populateTtsVoiceSelect === 'function') {
        populateTtsVoiceSelect(targetLang);
    }
    ensureTtsVoiceForLanguage(targetLang);
    if (selectTtsVoice && isEn) {
        if ([...selectTtsVoice.options].some(o => o.value === 'en-US-GuyNeural')) {
            selectTtsVoice.value = 'en-US-GuyNeural';
        }
    }

    const currentTopic = (inputTopic?.value || '').trim();
    const btnTranslate = document.getElementById('btn-translate-topic');
    const currentNiche = selectNiche?.value || (isEn ? '7_dark_psychology' : '6_stoic_philosophy');

    if (isEn) {
        if (typeof isTopicSampleOrEmpty === 'function' && isTopicSampleOrEmpty(currentTopic)) {
            const enSample = NICHE_SAMPLE_TOPICS?.['en']?.[currentNiche] || '3 Dark Psychology Secrets Manipulation Experts Never Tell You';
            if (inputTopic) inputTopic.value = enSample;
            if (btnTranslate) btnTranslate.style.display = 'none';
        } else {
            const hasTr = /[çğıöşüÇĞİÖŞÜ]/.test(currentTopic) || /\b(ve|ile|bir|için|nasıl|neden)\b/i.test(currentTopic);
            if (btnTranslate && hasTr) {
                btnTranslate.style.display = 'inline-flex';
            }
            if (options.autoTranslate && hasTr) {
                translateCurrentTopicToEnglish();
            }
        }
    } else {
        if (btnTranslate) btnTranslate.style.display = 'none';
        if (typeof isTopicSampleOrEmpty === 'function' && isTopicSampleOrEmpty(currentTopic)) {
            const trSample = NICHE_SAMPLE_TOPICS?.['tr']?.[currentNiche] || "Marcus Aurelius'un Öfkeyi Yok Eden 3 Stoacı Kuralı";
            if (inputTopic) inputTopic.value = trSample;
        }
    }

    const btnTier1El = document.getElementById('qa-tier1-en');
    if (btnTier1El) {
        btnTier1El.classList.toggle('active', isEn);
        const span = btnTier1El.querySelector('span');
        if (span) span.textContent = isEn ? 'Tier-1 EN: AKTİF (ABD)' : 'Tier-1 (ABD/İngilizce) Modu';
    }

    if (selectNiche && inputTopic) {
        updateLoopBridge(selectNiche.value, inputTopic.value);
    }
    updateScriptActionButtons();
    saveStudioSettings();
    if (options.toast) {
        showToast(isEn ? '🇺🇸 İngilizce (Global / Tier-1) Modu Aktif' : '🇹🇷 Türkçe Modu Aktif');
    }
}

function checkTopicLanguageAndSuggestTranslation() {
    const btnTranslate = document.getElementById('btn-translate-topic');
    if (!btnTranslate || !inputTopic) return;
    const currentLang = selectLanguage?.value || 'tr';
    const text = (inputTopic.value || '').trim();
    if (currentLang === 'en' && text) {
        const hasTurkishChars = /[çğıöşüÇĞİÖŞÜ]/.test(text);
        const hasTurkishWords = /\b(ve|ile|bir|için|nasıl|neden|kural|sır|en|hakkında|taktiği|gerçek|büyük)\b/i.test(text);
        btnTranslate.style.display = (hasTurkishChars || hasTurkishWords) ? 'inline-flex' : 'none';
    } else {
        btnTranslate.style.display = 'none';
    }
}

async function translateCurrentTopicToEnglish() {
    const btn = document.getElementById('btn-translate-topic');
    const topicText = (inputTopic?.value || '').trim();
    if (!topicText) return;
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Çevriliyor...';
    }
    try {
        const res = await fetch('/api/topics/translate', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topic: topicText, target_lang: 'en' })
        });
        const data = await res.json();
        if (data.status === 'ok' && data.translated) {
            if (inputTopic) inputTopic.value = data.translated;
            if (btn) btn.style.display = 'none';
            showToast('🌐 Konu İngilizceye çevrildi!');
            updateLoopBridge(selectNiche?.value || '1_news_flash', data.translated);
            saveStudioSettings();
        } else {
            showToast(data.message || 'Çeviri yapılamadı', 'warn');
        }
    } catch (e) {
        showToast('Çeviri hatası: ' + e.message, 'warn');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fa-solid fa-language"></i> İngilizceye Çevir';
        }
    }
}

async function translateCurrentScript() {
    if (!currentPlan?.scenes?.length) {
        showToast('Önce çevrilecek bir senaryo oluşturun.', 'warn');
        return;
    }
    const targetLang = selectLanguage?.value || window.APP_STATE?.language || 'tr';
    const sourceLang = String(currentPlan.language || currentPlan.lang || window.APP_STATE?.language || 'tr').slice(0, 2);
    if (sourceLang === targetLang) {
        showToast('Senaryo zaten seçili dilde.', 'warn');
        return;
    }

    const button = document.getElementById('btn-translate-script');
    const originalLabel = button?.innerHTML;
    if (button) {
        button.disabled = true;
        button.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i><span>Çevriliyor...</span>';
    }
    showToast('Sahne görselleri korunarak senaryo çevriliyor...');
    try {
        const response = await fetch('/api/script/translate', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ plan: currentPlan, target_lang: targetLang })
        });
        const data = await response.json();
        if (!response.ok || data.status !== 'ok' || !data.plan) {
            throw new Error(data.detail || data.message || 'Senaryo çevrilemedi.');
        }

        let plan = data.plan;
        if (inputTopic && plan.title) inputTopic.value = plan.title;
        setCurrentPlan(plan, { skipQualityPanel: true });
        setStudioLanguage(targetLang, { toast: false });
        const validation = await updateStudioQualityPanel(plan);
        if (validation?.plan) plan = validation.plan;
        renderTimelineScenes(plan);
        persistCurrentPlan();
        saveStudioSettings();
        showToast('Senaryo çevrildi; sahne görselleri ve süreleri korundu.');
    } catch (error) {
        showToast(`Senaryo çevirisi başarısız: ${error.message}`, 'error');
    } finally {
        if (button) {
            button.disabled = false;
            button.innerHTML = originalLabel;
            updateScriptActionButtons();
        }
    }
}

document.getElementById('btn-quick-lang-tr')?.addEventListener('click', () => setStudioLanguage('tr', { toast: true }));
document.getElementById('btn-quick-lang-en')?.addEventListener('click', () => setStudioLanguage('en', { toast: true, autoTranslate: true }));
selectLanguage?.addEventListener('change', () => setStudioLanguage(selectLanguage.value, { toast: false, autoTranslate: true }));
document.getElementById('btn-translate-topic')?.addEventListener('click', translateCurrentTopicToEnglish);
document.getElementById('btn-translate-script')?.addEventListener('click', translateCurrentScript);

selectNiche?.addEventListener('change', () => {
    userManuallyPickedNiche = true;
    showNicheLockBadge(null);

    const currentLang = selectLanguage?.value || 'tr';
    if (inputTopic && typeof isTopicSampleOrEmpty === 'function' && isTopicSampleOrEmpty(inputTopic.value)) {
        const sample = NICHE_SAMPLE_TOPICS?.[currentLang]?.[selectNiche.value] ||
            (currentLang === 'en' ? '3 Secrets Manipulation Experts Never Tell You' : "Marcus Aurelius'un Öfkeyi Yok Eden 3 Stoacı Kuralı");
        inputTopic.value = sample;
    }
    checkTopicLanguageAndSuggestTranslation();
    updateLoopBridge(selectNiche.value, inputTopic?.value || '');
    applyNicheProfile(selectNiche.value);
    saveStudioSettings();
});
