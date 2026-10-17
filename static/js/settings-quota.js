/**
 * ShortsAI Studio — Settings Modal, API Key Management, Hardware/System Status & Roadmap (settings-quota.js)
 * Covers API key configuration, Google AI Pro model selection, 500-Item Roadmap explorer, and live health probes.
 */

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
            hint('input-key-sonilo', data.keys?.sonilo, 'sonilo');
            hint('input-key-deepseek', data.keys?.deepseek, 'deepseek');
            hint('input-key-openai', data.keys?.openai, 'openai');
            hint('input-key-grok', data.keys?.grok, 'grok');
            hint('input-key-youtube-data', data.keys?.youtube_data, 'youtube_data');
            hint('input-key-telegram-token', data.keys?.telegram, 'telegram_bot_token');
            hint('input-key-discord-webhook', data.keys?.discord, 'discord_webhook_url');
            hint('input-key-postbridge', data.keys?.postbridge, 'postbridge');
            hint('input-key-azure-speech', data.keys?.azure_speech, 'azure_speech');
            if (data.telegram_chat_id) {
                const chatEl = document.getElementById('input-key-telegram-chat');
                if (chatEl) chatEl.value = data.telegram_chat_id;
            }
            if (data.azure_speech_region) {
                const regEl = document.getElementById('input-key-azure-region');
                if (regEl) regEl.value = data.azure_speech_region;
            }
        }
        if (data.elevenlabs && typeof renderElevenlabsQuota === 'function') renderElevenlabsQuota(data.elevenlabs);
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
        if (typeof updateAiQuotaDisplay === 'function') await updateAiQuotaDisplay();
        await loadGoogleAiProPanel();
        await loadHardwareSpecs();
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
                    text:${fam.text || 0} img:${fam.image || 0} vid:${fam.video || 0}
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
        if (typeof loadBgmList === 'function') await loadBgmList();
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
                voice_gender: window.selectTtsVoice?.value === 'auto' ? 'auto' : ((typeof findVoiceMeta === 'function' ? findVoiceMeta(window.selectTtsVoice?.value)?.gender : null) || 'male'),
                tts_voice: (window.selectTtsVoice?.value && window.selectTtsVoice.value !== 'auto') ? window.selectTtsVoice.value : null,
                language: window.selectLanguage?.value || 'tr',
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
        const sel = document.getElementById('select-bgm-track');
        if (sel && data.filename) {
            const opt = document.createElement('option');
            opt.value = data.filename; opt.textContent = data.filename; opt.selected = true;
            sel.appendChild(opt);
        }
    } catch (e) { alert(e.message); }
});

document.getElementById('btn-save-settings')?.addEventListener('click', async () => {
    const gKey = document.getElementById('input-key-gemini')?.value.trim() || '';
    const deepSeekKey = document.getElementById('input-key-deepseek')?.value.trim() || '';
    const openAiKey = document.getElementById('input-key-openai')?.value.trim() || '';
    const grokKey = document.getElementById('input-key-grok')?.value.trim() || '';
    const pKey = document.getElementById('input-key-pexels')?.value.trim() || '';
    const pxKey = document.getElementById('input-key-pixabay')?.value.trim() || '';
    const youtubeDataKey = document.getElementById('input-key-youtube-data')?.value.trim() || '';
    const redditClientId = document.getElementById('input-key-reddit-id')?.value.trim() || '';
    const redditClientSecret = document.getElementById('input-key-reddit-secret')?.value.trim() || '';
    const elevenlabsKey = document.getElementById('input-key-elevenlabs')?.value.trim() || '';
    const soniloKey = document.getElementById('input-key-sonilo')?.value.trim() || '';
    const telegramToken = document.getElementById('input-key-telegram-token')?.value.trim() || '';
    const telegramChatId = document.getElementById('input-key-telegram-chat')?.value.trim() || '';
    const discordWebhook = document.getElementById('input-key-discord-webhook')?.value.trim() || '';
    const postbridgeKey = document.getElementById('input-key-postbridge')?.value.trim() || '';
    const azureSpeechKey = document.getElementById('input-key-azure-speech')?.value.trim() || '';
    const azureRegion = document.getElementById('input-key-azure-region')?.value.trim() || '';

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
    if (soniloKey) payload.sonilo_key = soniloKey;
    if (telegramToken) payload.telegram_bot_token = telegramToken;
    if (telegramChatId) payload.telegram_chat_id = telegramChatId;
    if (discordWebhook) payload.discord_webhook_url = discordWebhook;
    if (postbridgeKey) payload.postbridge_api_key = postbridgeKey;
    if (azureSpeechKey) payload.azure_speech_key = azureSpeechKey;
    if (azureRegion) payload.azure_speech_region = azureRegion;

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
        if (soniloKey) {
            const soniloInput = document.getElementById('input-key-sonilo');
            if (soniloInput) {
                const masked = body.key_hints?.sonilo || ('••••' + soniloKey.slice(-4));
                soniloInput.value = '';
                soniloInput.placeholder = `${masked} (Kayıtlı)`;
            }
        }
        await loadSettings();
        if (typeof loadTtsVoiceCatalog === 'function') await loadTtsVoiceCatalog(true);
    } catch (e) {
        showToast('Ayar kaydetme hatası: ' + e.message, 'error');
    }
});

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

function renderFilteredRoadmap(showAll = false) {
    const grid = document.getElementById('roadmap-items-grid');
    const counterBadge = document.getElementById('roadmap-counter-badge');
    const searchVal = (document.getElementById('input-roadmap-search')?.value || '').toLowerCase().trim();
    if (!grid) return;

    let filtered = allRoadmapItems;

    if (currentRoadmapSec !== 'all') {
        const secNum = parseInt(currentRoadmapSec, 10);
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
    const limit = showAll === true ? filtered.length : 100;
    filtered.slice(0, limit).forEach(it => {
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

    if (filtered.length > limit) {
        const moreNote = document.createElement('div');
        moreNote.style.cssText = 'grid-column: 1/-1; text-align: center; color: #94A3B8; font-size: 12px; padding: 12px; display: flex; align-items: center; justify-content: center; gap: 12px;';
        moreNote.innerHTML = `<span>...ve diğer ${filtered.length - limit} madde</span><button type="button" class="btn btn-sm btn-secondary" id="btn-roadmap-show-all">Tümünü Göster (${filtered.length})</button>`;
        moreNote.querySelector('#btn-roadmap-show-all')?.addEventListener('click', () => renderFilteredRoadmap(true));
        grid.appendChild(moreNote);
    }
}

document.querySelectorAll('#roadmap-section-filters .filter-pill').forEach(pill => {
    pill.addEventListener('click', (e) => {
        document.querySelectorAll('#roadmap-section-filters .filter-pill').forEach(p => p.classList.remove('active'));
        e.currentTarget.classList.add('active');
        currentRoadmapSec = e.currentTarget.getAttribute('data-sec');
        renderFilteredRoadmap();
    });
});

let searchDebounce = null;
document.getElementById('input-roadmap-search')?.addEventListener('input', () => {
    clearTimeout(searchDebounce);
    searchDebounce = setTimeout(renderFilteredRoadmap, 200);
});

document.querySelectorAll('.btn-test-api-key').forEach(btn => {
    btn.addEventListener('click', async () => {
        const provider = btn.getAttribute('data-provider');
        const inputId = btn.getAttribute('data-input');
        const keyVal = document.getElementById(inputId)?.value?.trim() || '';
        const oldHtml = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
        try {
            const res = await fetch('/api/keys/test', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ provider, api_key: keyVal, key: keyVal })
            });
            const data = await res.json();
            if (res.ok && (data.valid || data.status === 'ok')) {
                btn.innerHTML = '<i class="fa-solid fa-check text-success"></i> Geçerli';
                showToast(`✅ ${provider.toUpperCase()}: ${data.detail || data.message || 'Anahtar doğrulandı!'}`);
            } else {
                btn.innerHTML = '<i class="fa-solid fa-xmark text-danger"></i> Hata';
                showToast(`❌ ${provider.toUpperCase()}: ${data.detail || data.message || 'Geçersiz anahtar'}`, 'error');
            }
        } catch (err) {
            btn.innerHTML = 'Hata';
            showToast(`Test hatası: ${err.message}`, 'error');
        } finally {
            setTimeout(() => { btn.disabled = false; btn.innerHTML = oldHtml; }, 2500);
        }
    });
});

document.getElementById('btn-check-ollama-status')?.addEventListener('click', async () => {
    const out = document.getElementById('settings-health-probe-output');
    if (out) { out.style.display = 'block'; out.textContent = '⏳ Yerel Ollama LLM sunucusu kontrol ediliyor...'; }
    try {
        const res = await fetch('/api/ollama/status');
        const data = await res.json();
        if (out) {
            out.style.display = 'block';
            out.innerHTML = `<strong style="color:${data.available ? '#34d399' : '#fbbf24'};">🖥️ Yerel Ollama Durumu: ${data.available ? 'AKTİF' : 'KAPALI'}</strong>\n` +
                escapeHtml(JSON.stringify(data, null, 2));
        }
        showToast(data.available ? '✅ Yerel Ollama aktif!' : 'ℹ️ Yerel Ollama çalışmıyor (Bulut/Prosedürel mod aktif)');
    } catch (e) {
        if (out) out.textContent = 'Hata: ' + e.message;
    }
});

document.getElementById('btn-check-public-apis-live')?.addEventListener('click', async () => {
    const out = document.getElementById('settings-health-probe-output');
    if (out) { out.style.display = 'block'; out.textContent = '⏳ Public APIs canlı erişilebilirlik testi yürütülüyor...'; }
    try {
        const res = await fetch('/api/system/public-apis/status?live=true');
        const data = await res.json();
        if (out) {
            out.style.display = 'block';
            out.innerHTML = `<strong style="color:#38bdf8;">🌐 Public APIs Canlı Ping Sonucu:</strong>\n<pre style="white-space:pre-wrap; margin:4px 0 0; font-family:inherit;">${escapeHtml(JSON.stringify(data, null, 2))}</pre>`;
        }
        showToast('🌐 Public APIs canlı sağlık kontrolü tamamlandı');
    } catch (e) {
        if (out) out.textContent = 'Hata: ' + e.message;
    }
});

let _cachedHardwareSpecs = null;

async function loadHardwareSpecs(notifyUser = false) {
    try {
        const res = await fetch('/api/hardware/specs');
        if (!res.ok) return;
        const data = await res.json();
        const specs = data.specs || {};
        _cachedHardwareSpecs = specs;

        const setTxt = (id, text) => { const el = document.getElementById(id); if (el) el.textContent = text; };
        setTxt('hw-cpu-name', specs.cpu?.name || 'CPU');
        setTxt('hw-cpu-threads', `${specs.cpu?.threads || 4} Thread (${specs.cpu?.physical_cores || 2} Fiziksel Çekirdek)`);
        setTxt('hw-gpu-name', specs.gpu?.name || 'Standart GPU');
        setTxt('hw-gpu-nvenc', specs.gpu?.has_nvenc ? 'NVENC Donanım Hızlandırma Aktif' : (specs.gpu?.has_videotoolbox ? 'VideoToolbox Donanım Hızlandırma Aktif' : 'CPU Yazılım Kodlama (libx264)'));
        setTxt('hw-ram-total', `${specs.ram?.total_gb ?? 8} GB Toplam RAM`);
        setTxt('hw-ram-avail', `~${specs.ram?.avail_gb ?? 4} GB Kullanılabilir`);
        setTxt('hw-recommended-label', specs.recommended_label || 'Dengeli Profil');

        const cfg = specs.current_config || {};
        const threadSel = document.getElementById('select-hw-threads');
        if (threadSel) {
            const maxT = Math.max(4, Number(specs.cpu?.threads) || 8);
            const curT = Number(cfg.render_threads || specs.recommended_threads || 4);
            const counts = [...new Set([2, 4, 6, 8, 12, 16, maxT].filter(n => n <= maxT))].sort((a, b) => a - b);
            threadSel.innerHTML = counts.map(n => `<option value="${n}" ${n === curT ? 'selected' : ''}>${n} Thread${n === specs.recommended_threads ? ' (Önerilen)' : ''}</option>`).join('');
        }
        const codecSel = document.getElementById('select-hw-codec');
        if (codecSel) {
            if (specs.gpu?.has_videotoolbox && ![...codecSel.options].some(o => o.value === 'h264_videotoolbox')) {
                const opt = document.createElement('option');
                opt.value = 'h264_videotoolbox';
                opt.textContent = 'Apple VideoToolbox (macOS GPU)';
                codecSel.insertBefore(opt, codecSel.firstChild);
            }
            if (cfg.gpu_codec) codecSel.value = cfg.gpu_codec;
        }
        const resSel = document.getElementById('select-hw-resolution');
        if (resSel && cfg.resolution) resSel.value = cfg.resolution;
        const safeSel = document.getElementById('select-hw-safe-mode');
        if (safeSel && cfg.safe_mode != null) safeSel.value = String(!!cfg.safe_mode);
        const fpsSel = document.getElementById('select-hw-fps-mode');
        if (fpsSel) fpsSel.value = cfg.fps_diversify === false ? String(Math.round(Number(cfg.fps) || 30)) : 'diversify';
        if (notifyUser) showToast('🖥️ Donanım özellikleri güncellendi');
    } catch (_) {}
}

document.getElementById('btn-detect-hardware-now')?.addEventListener('click', () => loadHardwareSpecs(true));

document.getElementById('btn-apply-hardware-max')?.addEventListener('click', async () => {
    const specs = _cachedHardwareSpecs || {};
    const codec = specs.gpu?.has_videotoolbox ? 'h264_videotoolbox' : (specs.gpu?.has_nvenc ? 'h264_nvenc' : 'libx264');
    try {
        const res = await fetch('/api/hardware/apply_profile', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                threads: specs.recommended_threads || 8,
                use_gpu: specs.recommended_use_gpu !== false,
                gpu_codec: codec,
                fps_diversify: true,
                resolution: '1080p',
                safe_mode: false
            })
        });
        const data = await res.json();
        showToast(data.message || '⚡ Maksimum donanım profili uygulandı!');
        await loadHardwareSpecs();
    } catch (e) { showToast('Donanım profili hatası: ' + e.message, 'error'); }
});

document.getElementById('btn-save-hardware-manual')?.addEventListener('click', async () => {
    const codec = document.getElementById('select-hw-codec')?.value || 'libx264';
    const threads = parseInt(document.getElementById('select-hw-threads')?.value || '8', 10);
    const fpsMode = document.getElementById('select-hw-fps-mode')?.value || 'diversify';
    const resolution = document.getElementById('select-hw-resolution')?.value || '1080p';
    const safeMode = document.getElementById('select-hw-safe-mode')?.value === 'true';
    try {
        const res = await fetch('/api/hardware/apply_profile', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                threads,
                use_gpu: codec !== 'libx264',
                gpu_codec: codec,
                fps_diversify: fpsMode === 'diversify',
                fixed_fps: fpsMode === 'diversify' ? 30.0 : parseFloat(fpsMode) || 30.0,
                resolution,
                safe_mode: safeMode
            })
        });
        const data = await res.json();
        showToast(data.message || '💾 Manuel donanım ayarları kaydedildi!');
        await loadHardwareSpecs();
    } catch (e) { showToast('Ayar kaydetme hatası: ' + e.message, 'error'); }
});

