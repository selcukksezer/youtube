/**
 * ShortsAI Studio — Settings, AI Quota & Roadmap Explorer (settings-quota.js)
 * Covers Application settings, AI Model selector, Live AI Quota & Rate Limit monitor, and 500-Item Roadmap browser.
 */


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

