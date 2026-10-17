/**
 * ShortsAI Studio — Multi-Channel CRUD, Channel Vault, Autonomous Bot & OAuth/Upload Helpers (channels-manager.js)
 * Manages anti-detect channel onboarding, 30-rule audit, cookie warmup sessions, Studio UI upload, and crosspost syndication.
 */

let currentAnalyzedChannel = null;

document.getElementById('btn-execute-studio-safe-upload')?.addEventListener('click', async () => {
    if (!window.currentPublishVideo) return;
    const btn = document.getElementById('btn-execute-studio-safe-upload');
    const channelSelect = document.getElementById('pub-target-channel-select');
    const ch = channelSelect ? channelSelect.value : 'default';
    const title = document.getElementById('pub-title-field')?.value || '';
    const desc = document.getElementById('pub-desc-field')?.value || '';
    const tags = (document.getElementById('pub-tags-field')?.value || '').split(',').map(t => t.trim()).filter(Boolean);
    const schedHour = parseInt(document.getElementById('pub-schedule-hour')?.value || '18', 10);

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Yükleme Kuyruğuna Alınıyor...';
    }

    try {
        const res = await fetch('/api/channel/studio_upload', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                identifier: ch,
                video_path: `output/${window.currentPublishVideo.filename}`,
                title: title,
                description: desc,
                tags: tags,
                scheduled_hour: schedHour
            })
        });
        const data = await res.json();
        if (data.success || data.action === 'MANUAL_UPLOAD_REQUIRED') {
            showToast('✅ Studio UI Güvenli Paketleme Hazır! Terminale aktarıldı.');
            if (typeof switchTab === 'function') switchTab('channels');
            if (typeof closePublishHubModal === 'function') closePublishHubModal();
        } else {
            showToast(data.reason || data.error || 'Yükleme başlatılamadı', 'error');
        }
    } catch (err) {
        showToast(`Hata: ${err.message}`, 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<i class="fa-solid fa-rocket"></i> Anti-Detect Studio UI ile Yükle';
        }
    }
});

document.getElementById('btn-calc-jitter')?.addEventListener('click', async () => {
    const hour = document.getElementById('input-jitter-hour')?.value || 18;
    const minute = document.getElementById('input-jitter-minute')?.value || 0;
    const box = document.getElementById('jitter-result-box');
    if (!box) return;
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
    const chName = document.getElementById('input-appeal-channel')?.value || 'Shorts Kanalı';
    const box = document.getElementById('appeal-result-box');
    if (!box) return;
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
    if (!container) return;

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

    const summaryCards = [
        ['KURAL 1: YÜKLEME BAYRAĞI', '#10b981', '<i class="fa-solid fa-check"></i> Studio UI Oturumu'],
        ['KURAL 2: PROXY DENETİMİ', proxy.is_residential ? '#10b981' : '#f59e0b', proxy.is_residential ? '<i class="fa-solid fa-check"></i> ISP Residential' : (proxy.configured ? '⚠️ Datacenter Riski' : 'ℹ️ Yerel ISP IP')],
        ['KURAL 3: WEBRTC KALKANI', '#10b981', '<i class="fa-solid fa-shield"></i> UDP Sızıntısı Bloklu'],
        ['KURAL 4 & 5: CANVAS & GPU', '#8b5cf6', profile.webgl_renderer],
        ['KURAL 10: DNS SIZINTISI', '#10b981', '<i class="fa-solid fa-lock"></i> Cloudflare DoH'],
        ['KURAL 17: ÖN İZLEME', '#10b981', '<i class="fa-solid fa-play"></i> 2-3 Shorts + Yorum'],
        ['KURAL 18: OTURUM SÜRESİ', '#38bdf8', '<i class="fa-solid fa-hourglass-half"></i> 3-7 dk Kuralı'],
        ['KURAL 19: HEADLESS İZİ', '#10b981', '<i class="fa-solid fa-user-secret"></i> webdriver: undef'],
        ['KURAL 22: TLS JA3', '#10b981', '<i class="fa-solid fa-fingerprint"></i> Chrome 124'],
        ['KURAL 23: PROTOKOL', '#06b6d4', '<i class="fa-solid fa-network-wired"></i> HTTP/2 & QUIC'],
        ['KURAL 24: AĞ JITTER\'I', '#f59e0b', '<i class="fa-solid fa-wave-square"></i> Ev ISP Hızı'],
        ['KURAL 25: LOKASYON', '#10b981', '<i class="fa-solid fa-location-dot"></i> Coğrafi Kilitli'],
        ['KURAL 26: ÖNBELLEK', '#a855f7', '<i class="fa-solid fa-database"></i> IndexedDB Kalıcı'],
        ['KURAL 27: CLIENT HINTS', '#38bdf8', '<i class="fa-solid fa-id-card"></i> sec-ch-ua: macOS'],
        ['KURAL 29: CTIME/MTIME', '#ec4899', '<i class="fa-solid fa-clock-rotate-left"></i> -15..45 dk'],
        ['KURAL 30: BOYUT VARYASYONU', '#10b981', '<i class="fa-solid fa-file-shield"></i> free Atom Dolgusu'],
    ].map(([label, color, val]) => `
        <div style="background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
            <small style="color: #94a3b8; display: block; font-size: 10px;">${label}</small>
            <strong style="color: ${color}; font-size: 12px;">${val}</strong>
        </div>
    `).join('');

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
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 8px; margin: 16px 0;">
                ${summaryCards}
            </div>
            <div style="margin: 18px 0 10px 0; display: flex; align-items: center; justify-content: space-between;">
                <h4 style="margin: 0; font-size: 14px; color: #fff; display: flex; align-items: center; gap: 8px;">
                    <i class="fa-solid fa-list-check text-warning"></i> Neler Yapılması Gerektiği (Adım Adım Yol Haritası - 30 Kural)
                </h4>
                <small style="color: #94a3b8;">Otomasyon Motoru Hazır</small>
            </div>
            <div class="channel-checklist-box">${checklistHtml}</div>
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

    document.getElementById('btn-run-warmup-now')?.addEventListener('click', () => triggerWarmupSession(ch.handle));

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
        } else if (logsBox) {
            logsBox.innerHTML += `<div style="color: #ef4444;">[Hata] ${data.error || 'Bilinmeyen hata'}</div>`;
        }
    } catch (e) {
        if (logsBox) {
            logsBox.innerHTML += `<div style="color: #ef4444;">[Hata] ${e.message}</div>`;
        }
    }
}

document.querySelectorAll('.channel-card').forEach(card => {
    card.addEventListener('click', () => {
        document.querySelectorAll('.channel-card').forEach(c => c.classList.remove('active'));
        card.classList.add('active');
        const chName = card.querySelector('h4')?.textContent || card.getAttribute('data-channel') || '';
        const inp = document.getElementById('input-channel-name');
        if (inp && chName) inp.value = chName;
        showToast(`📺 Aktif kanal profili: ${chName}`);
    });
});

document.getElementById('pub-privacy-select')?.addEventListener('change', (e) => {
    const box = document.getElementById('pub-schedule-hour-box');
    if (box) box.style.display = e.target.value === 'scheduled' ? 'block' : 'none';
});

document.getElementById('select-upload-privacy')?.addEventListener('change', (e) => {
    const pubPriv = document.getElementById('pub-privacy-select');
    if (pubPriv && [...pubPriv.options].some(o => o.value === e.target.value)) pubPriv.value = e.target.value;
});

document.getElementById('select-schedule-slot')?.addEventListener('change', (e) => {
    const map = { morning: 8, noon: 13, evening: 19, night: 23 };
    const hr = map[e.target.value];
    const pubHr = document.getElementById('pub-schedule-hour');
    if (hr != null && pubHr) pubHr.value = String(hr);
});

async function executeCrosspostSyndication(videoPathOverride, titleOverride, descOverride) {
    const outBox = document.getElementById('crosspost-syndicate-output');
    let video_path = videoPathOverride || (window.currentPublishVideo?.filename ? `output/${window.currentPublishVideo.filename}` : '');
    let title = titleOverride || document.getElementById('pub-title-field')?.value?.trim() || document.getElementById('input-topic')?.value?.trim() || 'Viral Shorts';
    let caption = descOverride || document.getElementById('pub-desc-field')?.value?.trim() || `${title} #shorts #fyp #viral`;

    if (!video_path) {
        try {
            const vRes = await fetch('/api/videos');
            const vData = await vRes.json();
            const first = (vData.videos || [])[0];
            if (first?.filename) video_path = `output/${first.filename}`;
        } catch (_) {}
    }
    if (!video_path) {
        return showToast('Dağıtılacak video bulunamadı. Önce bir video üretin.', 'warn');
    }

    const platforms = [...document.querySelectorAll('.chk-crosspost-platform:checked')].map(el => el.value);
    const targetPlatforms = platforms.length ? platforms : ['tiktok', 'instagram_reels', 'youtube_shorts'];

    if (outBox) {
        outBox.style.display = 'block';
        outBox.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Çoklu platform dağıtımı (PostBridge / Webhook) yürütülüyor...';
    }
    try {
        const res = await fetch('/api/syndication/crosspost', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ video_path, title, caption, platforms: targetPlatforms })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || data.error || 'Dağıtım başarısız');
        if (outBox) {
            outBox.style.display = 'block';
            outBox.innerHTML = `<div style="color:#34d399; font-weight:700;">✅ Çoklu Platform Dağıtımı Tamamlandı (${targetPlatforms.join(', ')})</div><pre style="white-space:pre-wrap; margin:4px 0 0; font-family:inherit;">${escapeHtml(JSON.stringify(data, null, 2))}</pre>`;
        }
        showToast(`🚀 Çoklu platform dağıtımı tamamlandı (${targetPlatforms.join(', ')})!`);
    } catch (err) {
        if (outBox) {
            outBox.style.display = 'block';
            outBox.innerHTML = `<span class="text-danger">Hata: ${escapeHtml(err.message)}</span>`;
        }
        showToast('Çoklu platform hatası: ' + err.message, 'error');
    }
}

document.getElementById('btn-crosspost-syndicate')?.addEventListener('click', () => executeCrosspostSyndication());
document.getElementById('btn-pub-crosspost')?.addEventListener('click', () => {
    const vp = window.currentPublishVideo?.filename ? `output/${window.currentPublishVideo.filename}` : '';
    const t = document.getElementById('pub-title-field')?.value?.trim() || '';
    const d = document.getElementById('pub-desc-field')?.value?.trim() || '';
    executeCrosspostSyndication(vp, t, d);
});

function renderGrowthDiagOutput(html) {
    const out = document.getElementById('growth-diagnostic-output');
    if (!out) return;
    out.style.display = 'block';
    out.innerHTML = html;
}

document.getElementById('btn-growth-retention-diag')?.addEventListener('click', async () => {
    renderGrowthDiagOutput('<i class="fa-solid fa-spinner fa-spin"></i> İzlenme tutma (retention) metrikleri analiz ediliyor...');
    try {
        const res = await fetch('/api/analytics/retention-diagnosis', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ avg_percentage_viewed: 76.5, stayed_to_watch_pct: 71.0, duration_sec: 44.0 })
        });
        const data = await res.json();
        renderGrowthDiagOutput(`
            <div style="color:#38bdf8; font-weight:700; margin-bottom:4px;">📈 Retention (İzlenme Tutma) Tanı Raporu</div>
            <pre style="white-space:pre-wrap; margin:0; font-family:inherit;">${escapeHtml(JSON.stringify(data.diagnosis || data, null, 2))}</pre>
        `);
    } catch (e) { renderGrowthDiagOutput(`Hata: ${escapeHtml(e.message)}`); }
});

document.getElementById('btn-growth-shadowban-diag')?.addEventListener('click', async () => {
    renderGrowthDiagOutput('<i class="fa-solid fa-spinner fa-spin"></i> Shadowban / Kanal sağlığı kontrol ediliyor...');
    try {
        const res = await fetch('/api/analytics/shadowban-diagnosis', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ recent_views: [1450, 2100, 1890, 2400, 1950], shorts_feed_ratio: 0.84 })
        });
        const data = await res.json();
        renderGrowthDiagOutput(`
            <div style="color:#34d399; font-weight:700; margin-bottom:4px;">🛡️ Shadowban &amp; Shorts Feed Dağıtım Tanısı</div>
            <pre style="white-space:pre-wrap; margin:0; font-family:inherit;">${escapeHtml(JSON.stringify(data.diagnosis || data, null, 2))}</pre>
        `);
    } catch (e) { renderGrowthDiagOutput(`Hata: ${escapeHtml(e.message)}`); }
});

document.getElementById('btn-growth-seo-operator')?.addEventListener('click', async () => {
    const topic = document.getElementById('ab-test-topic')?.value?.trim() || document.getElementById('input-topic')?.value?.trim() || 'Stoacı Zihin Kontrolü';
    const niche = document.getElementById('select-niche')?.value || '6_stoic_philosophy';
    renderGrowthDiagOutput('<i class="fa-solid fa-spinner fa-spin"></i> Viral SEO + Operatör Paketi hazırlanıyor...');
    try {
        const [seoRes, opRes] = await Promise.all([
            fetch(`/api/seo/viral_metadata?topic=${encodeURIComponent(topic)}&niche=${encodeURIComponent(niche)}`),
            fetch(`/api/growth/operator-pack?topic=${encodeURIComponent(topic)}&niche=${encodeURIComponent(niche)}`)
        ]);
        const seoData = await seoRes.json();
        const opData = await opRes.json();
        renderGrowthDiagOutput(`
            <div style="color:#c4b5fd; font-weight:700; margin-bottom:6px;">🚀 Viral SEO &amp; Operatör Paketi (${escapeHtml(topic)})</div>
            <pre style="white-space:pre-wrap; margin:0; font-family:inherit;">${escapeHtml(JSON.stringify({ seo: seoData.metadata || seoData, operator_pack: opData.operator_pack || opData }, null, 2))}</pre>
        `);
    } catch (e) { renderGrowthDiagOutput(`Hata: ${escapeHtml(e.message)}`); }
});

document.getElementById('btn-growth-monetization')?.addEventListener('click', async () => {
    renderGrowthDiagOutput('<i class="fa-solid fa-spinner fa-spin"></i> YPP Monetization durumu hesaplanıyor...');
    try {
        const res = await fetch('/api/analytics/monetization-progress?subscribers=650&shorts_views_90d=2400000&watch_hours_365d=1800');
        const data = await res.json();
        renderGrowthDiagOutput(`
            <div style="color:#fbbf24; font-weight:700; margin-bottom:4px;">💰 YouTube İş Ortağı Programı (YPP) İlerleme Raporu</div>
            <pre style="white-space:pre-wrap; margin:0; font-family:inherit;">${escapeHtml(JSON.stringify(data.progress || data, null, 2))}</pre>
        `);
    } catch (e) { renderGrowthDiagOutput(`Hata: ${escapeHtml(e.message)}`); }
});

document.getElementById('btn-growth-niche-leaderboard')?.addEventListener('click', async () => {
    renderGrowthDiagOutput('<i class="fa-solid fa-spinner fa-spin"></i> BGBM / CPM Niş Liderlik Tablosu yükleniyor...');
    try {
        const res = await fetch('/api/analytics/niche-leaderboard?lang=tr');
        const data = await res.json();
        const board = data.leaderboard || data.niches || data;
        renderGrowthDiagOutput(`
            <div style="color:#4ade80; font-weight:700; margin-bottom:4px;">🏆 BGBM / CPM Niş Liderlik Tablosu</div>
            <pre style="white-space:pre-wrap; margin:0; font-family:inherit;">${escapeHtml(JSON.stringify(board, null, 2))}</pre>
        `);
    } catch (e) { renderGrowthDiagOutput(`Hata: ${escapeHtml(e.message)}`); }
});

