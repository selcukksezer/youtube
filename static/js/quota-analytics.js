/**
 * ShortsAI Studio — Quota Usage Charts, Provider Circuit Breaker Badges & Telemetry (quota-analytics.js)
 * Manages live AI quota & rate limit monitoring across header, sidebar, studio bar, and quota modal.
 */

let currentQuotaTab = 'all';
let lastQuotaData = null;

function renderSingleQuotaDetail(catKey) {
    if (!lastQuotaData) return;
    const catLabel = document.getElementById('single-view-cat-label');
    const nameEl = document.getElementById('mini-ai-name');
    const m1Label = document.getElementById('single-metric-1-label');
    const m1Val = document.getElementById('mini-quota-rpm-display');
    const m1Unit = document.getElementById('single-metric-1-unit');
    const m1Fill = document.getElementById('mini-rpm-fill');
    const m2Label = document.getElementById('single-metric-2-label');
    const m2Val = document.getElementById('mini-quota-rpd-display');
    const m2Rem = document.getElementById('mini-rpd-remaining');
    const m2Fill = document.getElementById('mini-rpd-fill');

    if (catKey === 'ai') {
        const activeName = lastQuotaData.active_provider_name || 'Google Gemini Flash';
        const rpmUsed = lastQuotaData.current_rpm_used || 0;
        const rpmLimit = lastQuotaData.rpm_limit || 15;
        const rpdUsed = lastQuotaData.daily_used || 0;
        const rpdLimit = lastQuotaData.rpd_limit || 1500;
        const dailyRemaining = lastQuotaData.daily_remaining !== undefined ? lastQuotaData.daily_remaining : Math.max(0, rpdLimit - rpdUsed);
        const remStr = typeof dailyRemaining === 'number' ? dailyRemaining.toLocaleString('tr-TR') : dailyRemaining;

        if (catLabel) catLabel.textContent = 'AI MOTORU';
        if (nameEl) nameEl.textContent = activeName;
        if (m1Label) m1Label.textContent = 'Anlık Hız';
        if (m1Val) m1Val.textContent = lastQuotaData.is_api_key_missing ? 'Yerel' : `${rpmUsed}/${rpmLimit}`;
        if (m1Unit) m1Unit.textContent = 'RPM';
        if (m1Fill) {
            const pct = rpmLimit > 0 ? Math.min(100, (rpmUsed / rpmLimit) * 100) : 0;
            m1Fill.style.width = `${pct}%`;
        }
        if (m2Label) m2Label.textContent = 'Günlük İstek';
        if (m2Val) m2Val.textContent = lastQuotaData.is_api_key_missing ? 'Sınırsız' : `${rpdUsed}/${rpdLimit.toLocaleString('tr-TR')}`;
        if (m2Rem) m2Rem.textContent = `${remStr} kaldı`;
        if (m2Fill) {
            const pct = rpdLimit > 0 ? Math.min(100, (rpdUsed / rpdLimit) * 100) : 0;
            m2Fill.style.width = `${pct}%`;
        }
    } else if (catKey === 'stock') {
        const pPexels = lastQuotaData.providers?.Pexels || {};
        const pPixabay = lastQuotaData.providers?.Pixabay || {};
        const pexRem = pPexels.remaining_calls !== undefined ? pPexels.remaining_calls.toLocaleString('tr-TR') : '25.000';
        const pixRem = pPixabay.remaining_calls !== undefined ? pPixabay.remaining_calls.toLocaleString('tr-TR') : '100';

        if (catLabel) catLabel.textContent = 'STOK VİDEO MOTORLARI';
        if (nameEl) nameEl.textContent = 'Pexels & Pixabay API';
        if (m1Label) m1Label.textContent = 'Pexels Kalan';
        if (m1Val) m1Val.textContent = `${pexRem}`;
        if (m1Unit) m1Unit.textContent = '/ 25.000';
        if (m1Fill) m1Fill.style.width = `${pPexels.health_pct || 85}%`;
        if (m2Label) m2Label.textContent = 'Pixabay Kalan';
        if (m2Val) m2Val.textContent = `${pixRem}`;
        if (m2Rem) m2Rem.textContent = `${pPixabay.status_badge || 'Canlı'}`;
        if (m2Fill) m2Fill.style.width = `${pPixabay.health_pct || 100}%`;
    } else if (catKey === 'tts') {
        const pEleven = lastQuotaData.providers?.ElevenLabs || {};

        if (catLabel) catLabel.textContent = 'SESLENDİRME MOTORU';
        if (nameEl) nameEl.textContent = pEleven.has_key ? 'ElevenLabs & Edge-TTS' : 'Microsoft Edge Neural TTS';
        if (m1Label) m1Label.textContent = 'Edge-TTS';
        if (m1Val) m1Val.textContent = 'Limitsiz';
        if (m1Unit) m1Unit.textContent = '0 TL Stack';
        if (m1Fill) m1Fill.style.width = '100%';
        if (m2Label) m2Label.textContent = 'ElevenLabs';
        if (m2Val) m2Val.textContent = pEleven.has_key && pEleven.remaining_calls !== undefined ? `${pEleven.remaining_calls.toLocaleString('tr-TR')}` : 'Yedek Mod';
        if (m2Rem) m2Rem.textContent = pEleven.has_key ? 'karakter kaldı' : 'Edge aktif';
        if (m2Fill) m2Fill.style.width = `${pEleven.health_pct || 100}%`;
    } else if (catKey === 'youtube') {
        const pYt = lastQuotaData.providers?.YouTube || {};
        const ytUsed = pYt.daily_used || 0;
        const ytLimit = pYt.rpd_limit || 10000;
        const ytRem = pYt.remaining_calls !== undefined ? pYt.remaining_calls : (ytLimit - ytUsed);

        if (catLabel) catLabel.textContent = 'YOUTUBE YAYIN & API';
        if (nameEl) nameEl.textContent = pYt.has_key ? 'YouTube Data API v3' : 'Otomatik Tarayıcı Yükleyici (0 Kota)';
        if (m1Label) m1Label.textContent = 'Günlük Kota';
        if (m1Val) m1Val.textContent = pYt.has_key ? `${ytUsed}/${ytLimit.toLocaleString('tr-TR')}` : '0 Kota';
        if (m1Unit) m1Unit.textContent = 'Birim';
        if (m1Fill) m1Fill.style.width = pYt.has_key ? `${Math.min(100, (ytUsed / ytLimit) * 100)}%` : '100%';
        if (m2Label) m2Label.textContent = 'Kapasite';
        if (m2Val) m2Val.textContent = pYt.has_key ? `${(ytRem / 1600).toFixed(1)} Video` : 'Sınırsız';
        if (m2Rem) m2Rem.textContent = pYt.has_key ? `${ytRem.toLocaleString('tr-TR')} birim kaldı` : 'Tarayıcı modu aktif';
        if (m2Fill) m2Fill.style.width = '100%';
    }
}

function setQuotaTab(tabKey) {
    currentQuotaTab = tabKey;
    document.querySelectorAll('#ssp-quota-tabs .ssp-tab').forEach(b => {
        b.classList.toggle('active', b.getAttribute('data-quota-tab') === tabKey);
    });
    const allView = document.getElementById('ssp-all-quotas-view');
    const singleView = document.getElementById('ssp-single-quota-view');

    if (tabKey === 'all') {
        if (allView) allView.style.display = 'flex';
        if (singleView) singleView.style.display = 'none';
    } else {
        if (allView) allView.style.display = 'none';
        if (singleView) singleView.style.display = 'block';
        renderSingleQuotaDetail(tabKey);
    }
}

async function updateAiQuotaDisplay(passedData = null) {
    if (window.isRendering && !passedData) return;
    try {
        const qData = passedData || await (await fetch('/api/quota/stats')).json();
        if (!qData) return;
        lastQuotaData = qData;

        const activeName = qData.active_provider_name || 'Google Gemini Flash';
        const rpmUsed = qData.current_rpm_used || 0;
        const rpmLimit = qData.rpm_limit || 15;
        const rpdUsed = qData.daily_used || 0;
        const rpdLimit = qData.rpd_limit || 1500;
        const dailyRemaining = qData.daily_remaining !== undefined ? qData.daily_remaining : Math.max(0, rpdLimit - rpdUsed);
        const isExhausted = qData.is_exhausted || false;
        const healthPct = qData.overall_health_pct || 100;
        const remStr = typeof dailyRemaining === 'number' ? dailyRemaining.toLocaleString('tr-TR') : dailyRemaining;

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

        const qAiName = document.getElementById('all-q-ai-name');
        const qAiBadge = document.getElementById('all-q-ai-badge');
        const qAiMetric = document.getElementById('all-q-ai-metric');
        const qAiPct = document.getElementById('all-q-ai-pct');
        const qAiBar = document.getElementById('all-q-ai-bar');

        const qStockBadge = document.getElementById('all-q-stock-badge');
        const qStockMetric = document.getElementById('all-q-stock-metric');
        const qStockPct = document.getElementById('all-q-stock-pct');
        const qStockBar = document.getElementById('all-q-stock-bar');

        const qTtsBadge = document.getElementById('all-q-tts-badge');
        const qTtsMetric = document.getElementById('all-q-tts-metric');
        const qTtsPct = document.getElementById('all-q-tts-pct');
        const qTtsBar = document.getElementById('all-q-tts-bar');

        const qYtBadge = document.getElementById('all-q-yt-badge');
        const qYtMetric = document.getElementById('all-q-yt-metric');
        const qYtPct = document.getElementById('all-q-yt-pct');
        const qYtBar = document.getElementById('all-q-yt-bar');

        if (qAiName) qAiName.textContent = activeName;
        if (qAiBadge) qAiBadge.textContent = qData.is_api_key_missing ? 'Yerel Mod' : `${remStr} Kaldı`;
        if (qAiMetric) qAiMetric.textContent = qData.is_api_key_missing ? '0 TL Failsafe Aktif' : `${rpmUsed}/${rpmLimit} RPM · ${rpdUsed}/${rpdLimit.toLocaleString('tr-TR')} RPD`;
        if (qAiPct) qAiPct.textContent = `%${healthPct}`;
        if (qAiBar) qAiBar.style.width = `${healthPct}%`;

        const provs = qData.providers || {};
        const pex = provs['Pexels'] || {};
        const pix = provs['Pixabay'] || {};
        const pexRem = pex.remaining_calls !== undefined ? pex.remaining_calls.toLocaleString('tr-TR') : '25.000';
        const pixRem = pix.remaining_calls !== undefined ? pix.remaining_calls.toLocaleString('tr-TR') : '100';
        const stockHealth = Math.min(pex.health_pct || 100, pix.health_pct || 100);

        if (qStockBadge) qStockBadge.textContent = pex.status_badge || 'Canlı Senkron';
        if (qStockMetric) qStockMetric.textContent = `Pexels: ${pexRem} · Pixabay: ${pixRem}`;
        if (qStockPct) qStockPct.textContent = `%${stockHealth}`;
        if (qStockBar) qStockBar.style.width = `${stockHealth}%`;

        const eleven = provs['ElevenLabs'] || {};
        if (qTtsBadge) qTtsBadge.textContent = eleven.has_key && eleven.remaining_calls !== undefined ? `${eleven.remaining_calls.toLocaleString('tr-TR')} Kar.` : '0 TL Limitsiz';
        if (qTtsMetric) qTtsMetric.textContent = eleven.has_key ? `ElevenLabs: ${eleven.remaining_calls?.toLocaleString('tr-TR')} kar · Edge: Hazır` : 'Edge Neural TTS (TR+EN Sınırsız)';
        if (qTtsPct) qTtsPct.textContent = '%100';
        if (qTtsBar) qTtsBar.style.width = '100%';

        const yt = provs['YouTube'] || {};
        const ytUsed = yt.daily_used || 0;
        const ytLimit = yt.rpd_limit || 10000;
        const ytRem = yt.remaining_calls !== undefined ? yt.remaining_calls : (ytLimit - ytUsed);
        if (qYtBadge) qYtBadge.textContent = yt.has_key ? `${ytRem.toLocaleString('tr-TR')} Birim` : 'Tarayıcı Modu';
        if (qYtMetric) qYtMetric.textContent = yt.has_key ? `${ytUsed}/${ytLimit.toLocaleString('tr-TR')} Birim (~${(ytRem / 1600).toFixed(0)} video)` : '0 Kota (Tarayıcı Yükleyici)';
        if (qYtPct) qYtPct.textContent = `%${yt.health_pct || 100}`;
        if (qYtBar) qYtBar.style.width = `${yt.health_pct || 100}%`;

        renderSingleQuotaDetail(currentQuotaTab === 'all' ? 'ai' : currentQuotaTab);

        const renderHint = document.getElementById('mini-render-hint');
        const renderHintText = document.getElementById('mini-render-hint-text');
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

        const miniBadge = document.getElementById('mini-quota-badge');
        const miniFill = document.getElementById('mini-quota-fill');
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

        const studioAiName = document.getElementById('studio-ai-name');
        const studioAiRpm = document.getElementById('studio-ai-rpm');
        const studioAiRpd = document.getElementById('studio-ai-rpd');
        const studioPulse = document.getElementById('studio-ai-pulse');

        if (studioAiName) studioAiName.textContent = activeName;
        if (studioAiRpm) studioAiRpm.innerHTML = qData.is_api_key_missing ? `<i class="fa-solid fa-shield"></i> Yerel Motor` : `<i class="fa-solid fa-gauge-high"></i> ${rpmUsed} / ${rpmLimit} RPM`;
        if (studioAiRpd) {
            studioAiRpd.innerHTML = qData.is_api_key_missing ? `<i class="fa-solid fa-key"></i> Gemini Anahtarı Ekleyin` : `<i class="fa-solid fa-calendar-day"></i> ${rpdUsed} / ${rpdLimit.toLocaleString('tr-TR')} (${remStr} Kaldı)`;
        }
        if (studioPulse) {
            studioPulse.className = qData.is_api_key_missing ? 'pulse-dot cyan' : (isExhausted ? 'pulse-dot yellow' : 'pulse-dot green');
        }

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
            modalProvidersList.innerHTML = Object.entries(qData.providers).map(([, pInfo]) => {
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

        const statsBox = document.getElementById('quota-stats-display');
        const detailsBox = document.getElementById('quota-exhaustion-details');
        if (statsBox) {
            const usageRows = qData.usage && Object.keys(qData.usage).length > 0
                ? Object.entries(qData.usage).map(([k, v]) => `<div style="padding: 2px 0;">• ${k}: <strong>${v} çağrı</strong></div>`).join("")
                : '<div style="color: #94a3b8;">Henüz API çağrısı yapılmadı.</div>';
            const errorRows = qData.errors && Object.keys(qData.errors).length > 0
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
document.getElementById('sidebar-quota-card')?.addEventListener('click', (e) => {
    if (e.target.closest('#ssp-quota-tabs') || e.target.closest('.ssp-quota-row-item')) {
        return;
    }
    openQuotaModal();
});
document.getElementById('btn-sidebar-quota-link')?.addEventListener('click', (e) => {
    e.stopPropagation();
    openQuotaModal();
});

document.querySelectorAll('#ssp-quota-tabs .ssp-tab').forEach(btn => {
    btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const tab = btn.getAttribute('data-quota-tab');
        setQuotaTab(tab);
    });
});

document.querySelectorAll('.ssp-quota-row-item').forEach(row => {
    row.addEventListener('click', (e) => {
        e.stopPropagation();
        const targetTab = row.getAttribute('data-switch-to');
        if (targetTab) setQuotaTab(targetTab);
    });
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
        const res = await fetch('/api/config', {
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
