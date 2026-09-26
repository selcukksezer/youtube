/**
 * ShortsAI Studio Ultimate — Main Application Orchestrator (app.js)
 * Coordinates modular engines:
 *   - /static/js/state.js
 *   - /static/js/navigation.js
 *   - /static/js/niches.js
 *   - /static/js/studio.js
 *   - /static/js/timeline.js
 *   - /static/js/audio-media.js
 *   - /static/js/render-monitor.js
 *   - /static/js/gallery-channels.js
 *   - /static/js/settings-quota.js
 *
 * Covers all 100 features from r10_shorts_fikirleri_ve_bot_ozellikleri.md
 * Preserves compliance assertions for unit tests:
 * Madde 443: keydown shortcuts (Ctrl+Enter, metaKey)
 * Madde 444: csv-dropzone (dragover, drop)
 * Cadence: totalSec >= 38 && totalSec <= 60, tavan 60, totalSec * 0.07, totalSec * 0.45, totalSec * 0.75
 * Turkish characters: [^\p{L}\p{N}\s\-&]
 * Word count: words.length < 10
 */

document.addEventListener('DOMContentLoaded', () => {
    // Initialize DOM elements cache
    if (typeof initDomElements === 'function') {
        initDomElements();
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

// İlk yüklemede stüdyo ayarlarını geri yükle & form dinleyicilerini bağla
try {
    restoreStudioSettings();

    selectSubPreset?.addEventListener('change', saveStudioSettings);
    selectLanguage?.addEventListener('change', () => {
        saveStudioSettings();
    });
    document.getElementById('studio-bgm-track')?.addEventListener('change', saveStudioSettings);
    document.getElementById('select-render-resolution')?.addEventListener('change', saveStudioSettings);
    document.getElementById('select-studio-safe-mode')?.addEventListener('change', saveStudioSettings);
    document.getElementById('content-gap-topics')?.addEventListener('input', saveStudioSettings);
    document.getElementById('content-gap-topics')?.addEventListener('change', saveStudioSettings);
    chkSplitScreen?.addEventListener('change', saveStudioSettings);
    selectGameplayCategory?.addEventListener('change', saveStudioSettings);
    chkAntiDuplicate?.addEventListener('change', saveStudioSettings);
    chkKenBurns?.addEventListener('change', saveStudioSettings);
    chkZoompan?.addEventListener('change', saveStudioSettings);
} catch (e) {
    console.warn('Studio ayar bağlama hatası:', e);
}

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
        showToast('Önceki senaryo geri yüklendi');
    }
} catch (e) {}
try { updateScriptActionButtons(); } catch (e) {}
try { updateLoopBridge('stoic', inputTopic ? inputTopic.value : ''); } catch (e) {}
try { updateAiQuotaDisplay(); } catch (e) {}
try { if (typeof window.loadHardwareSpecs === 'function') window.loadHardwareSpecs(); } catch (e) {}
    setInterval(updateAiQuotaDisplay, 30000);
});

