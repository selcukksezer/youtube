/**
 * ShortsAI Studio — BGM Library, Ducking Controls, AI Mood Matcher & SRT Tools (bgm-library.js)
 * Manages BGM catalog loading, custom upload, royalty-free search, AI mood matching, ducking sliders, and SRT translation/kinetic preview.
 */

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
            el.innerHTML = '<option value="">🎵 Otomatik (Akıllı Niş / Telifsiz Seçim)</option><option value="none">🔇 Müziksiz (Sadece Seslendirme &amp; SFX)</option>';
            detailed.forEach(t => {
                const fn = t.filename || t;
                const opt = document.createElement('option');
                opt.value = fn;
                const label = t.display || fn;
                opt.textContent = t.downloaded === false ? `${label} (indirilecek)` : label;
                el.appendChild(opt);
            });
            const savedBgm = restoreStudioSettings()?.bgmTrack;
            const candidate = prev || savedBgm;
            if (candidate && [...el.options].some(o => o.value === candidate)) el.value = candidate;
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

// 9. DUCKING SLIDER ETİKETLERİ, SRT ÇEVİRİCİ & AI MÜZİK RUH HALİ EŞLEŞTİRİCİ
// ══════════════════════════════════════════════════════════════
document.getElementById('audio-chk-enable-ducking')?.addEventListener('change', (e) => {
    const block = document.getElementById('ducking-detail-block');
    if (block) {
        block.style.opacity = e.target.checked ? '1' : '0.45';
        block.style.pointerEvents = e.target.checked ? 'auto' : 'none';
    }
});

document.getElementById('range-ducking-vol')?.addEventListener('input', (e) => {
    const val = Math.round(parseFloat(e.target.value || '0.12') * 100);
    const lbl = document.getElementById('val-ducking');
    if (lbl) lbl.textContent = `%${val} (Konuşurken kısık)`;
});
document.getElementById('range-bgm-blast')?.addEventListener('input', (e) => {
    const val = Math.round(parseFloat(e.target.value || '0.85') * 100);
    const lbl = document.getElementById('val-bgm-blast');
    if (lbl) lbl.textContent = `%${val} (Sessizde patlama)`;
});
document.getElementById('range-duck-attack')?.addEventListener('input', (e) => {
    const lbl = document.getElementById('val-duck-attack');
    if (lbl) lbl.textContent = `${e.target.value} ms`;
});
document.getElementById('range-duck-release')?.addEventListener('input', (e) => {
    const lbl = document.getElementById('val-duck-release');
    if (lbl) lbl.textContent = `${e.target.value} ms`;
});
document.getElementById('range-outro-swell-sec')?.addEventListener('input', (e) => {
    const lbl = document.getElementById('val-outro-swell');
    if (lbl) lbl.textContent = `${e.target.value} sn`;
});

// SRT Altyazı Çevirici
document.getElementById('btn-translate-srt')?.addEventListener('click', async () => {
    const out = document.getElementById('sub-tools-output');
    let srtText = document.getElementById('sub-input-srt')?.value?.trim() || '';
    if (!srtText && window.currentPlan?.scenes?.length) {
        let t = 0;
        srtText = window.currentPlan.scenes.map((s, idx) => {
            const dur = parseFloat(s.duration) || 3.5;
            const start = new Date(t * 1000).toISOString().substr(11, 8) + ',000';
            t += dur;
            const end = new Date(t * 1000).toISOString().substr(11, 8) + ',000';
            return `${idx + 1}\n${start} --> ${end}\n${s.narration || ''}`;
        }).join('\n\n');
        const inp = document.getElementById('sub-input-srt');
        if (inp) inp.value = srtText;
    }
    if (!srtText) return showToast('Çevrilecek SRT veya aktif sahne bulunamadı.', 'warn');
    const target_lang = document.getElementById('sub-select-target-lang')?.value || 'en';
    if (out) { out.classList.remove('hidden'); out.style.display = 'block'; out.textContent = '⏳ SRT zaman kodları korunarak çevriliyor...'; }
    try {
        const res = await fetch('/api/subtitles/translate', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                srt_text: srtText,
                srt_content: srtText,
                target_language: target_lang,
                target_lang
            })
        });
        const data = await res.json();
        if (!res.ok) {
            throw new Error(data.detail || 'Altyazı çevirisi başarısız oldu.');
        }
        const translated = data.srt_text || data.translated_srt || data.srt || '';
        if (out) {
            out.classList.remove('hidden');
            out.style.display = 'block';
            out.textContent = translated || 'Çeviri tamamlandı.';
        }
        showToast(`🌍 SRT altyazı (${target_lang.toUpperCase()}) diline çevrildi!`);
    } catch (err) {
        if (out) { out.classList.remove('hidden'); out.style.display = 'block'; out.textContent = 'Hata: ' + err.message; }
    }
});

// Kinetik Altyazı Sayfalarını Önizle
document.getElementById('btn-preview-kinetic-pages')?.addEventListener('click', async () => {
    const out = document.getElementById('sub-tools-output');
    const text = (window.currentPlan?.scenes?.map(s => s.narration).join(' '))
        || document.getElementById('sub-input-srt')?.value?.trim()
        || document.getElementById('input-topic')?.value?.trim()
        || 'Zihninizi kontrol edemezseniz, başkaları sizin yerinize kontrol eder.';
    const words = text.replace(/\n+/g, ' ').split(/\s+/).filter(Boolean);
    let cursor = 0;
    const word_timings = words.map(w => {
        const item = { word: w, start: +cursor.toFixed(2), end: +(cursor + 0.32).toFixed(2) };
        cursor += 0.34;
        return item;
    });
    try {
        const res = await fetch('/api/subtitles/kinetic_pages', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ word_timings, max_words_per_page: 3 })
        });
        const data = await res.json();
        const pages = data.pages || [];
        if (out) {
            out.classList.remove('hidden');
            out.style.display = 'block';
            out.innerHTML = `<strong style="color:#38bdf8;">✨ Kinetik Altyazı Sayfaları (${pages.length} Sayfa):</strong>\n` +
                pages.map((p, i) => `[${(p.start ?? 0).toFixed(2)}s - ${(p.end ?? 0).toFixed(2)}s] Sayfa #${i + 1}: ${(p.words || []).map(w => w.word || w).join(' ')}`).join('\n');
        }
        showToast(`✨ ${pages.length} kinetik altyazı sayfası oluşturuldu`);
    } catch (err) {
        if (out) { out.classList.remove('hidden'); out.style.display = 'block'; out.textContent = 'Hata: ' + err.message; }
    }
});

// AI Müzik Ruh Hali Eşleştirici
document.getElementById('btn-audio-mood-match')?.addEventListener('click', async () => {
    const out = document.getElementById('audio-mood-search-results');
    const scenes = window.currentPlan?.scenes || [];
    const topic = document.getElementById('input-topic')?.value || 'Epic Stoic Motivation';
    const text = scenes.map(s => s.narration).join(' ') || topic;
    if (out) { out.classList.remove('hidden'); out.style.display = 'block'; out.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Senaryo duygusu analiz ediliyor...'; }
    try {
        const res = await fetch('/api/music/mood_match', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ script_text: text, niche_id: document.getElementById('select-niche')?.value || '' })
        });
        const data = await res.json();
        const mood = data.mood || data.recommended_mood || 'epic';
        const rawTrack = data.recommended_track || data.track || '';
        const track = (typeof rawTrack === 'object' && rawTrack !== null) ? (rawTrack.filename || rawTrack.title || '') : String(rawTrack || '');
        if (track) {
            const sel = document.getElementById('select-bgm-track');
            const studioSel = document.getElementById('studio-bgm-track');
            if (sel && [...sel.options].some(o => o.value === track)) sel.value = track;
            if (studioSel && [...studioSel.options].some(o => o.value === track)) studioSel.value = track;
        }
        if (out) {
            out.classList.remove('hidden');
            out.style.display = 'block';
            out.innerHTML = `<div>🎵 Tespit Edilen Ruh Hali: <strong style="color:#34d399;">${escapeHtml(String(mood).toUpperCase())}</strong> ${track ? `· Önerilen BGM: <code>${escapeHtml(track)}</code>` : ''}</div>`;
        }
        showToast(`🎵 AI Müzik Ruh Hali: ${mood}`);
    } catch (err) {
        if (out) { out.classList.remove('hidden'); out.style.display = 'block'; out.textContent = 'Hata: ' + err.message; }
    }
});

// Telifsiz BGM Ara & İndir
document.getElementById('btn-audio-rf-search')?.addEventListener('click', async () => {
    const out = document.getElementById('audio-mood-search-results');
    const q = document.getElementById('audio-rf-search-query')?.value?.trim() || 'dark ambient cinematic';
    if (out) { out.classList.remove('hidden'); out.style.display = 'block'; out.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> "${escapeHtml(q)}" için telifsiz müzik aranıyor...`; }
    try {
        const [searchRes, vlRes] = await Promise.all([
            fetch(`/api/audio/royalty-free/search?query=${encodeURIComponent(q)}&mood=${encodeURIComponent(q)}`),
            fetch('/api/voicelab/library').catch(() => null)
        ]);
        const data = await searchRes.json();
        const vlData = vlRes && vlRes.ok ? await vlRes.json() : {};
        const results = data.results || data.tracks || [];
        const vlTracks = vlData.tracks || vlData.local_voices_or_beds || vlData.bgm_tracks || [];
        if (out) {
            out.classList.remove('hidden');
            out.style.display = 'block';
            out.innerHTML = `
                <div style="margin-bottom:6px; color:#38bdf8; font-weight:700;">🎼 Bulunan Telifsiz Parçalar (${results.length}) · Yerel VoiceLab (${vlTracks.length})</div>
                <div style="display:flex; flex-direction:column; gap:5px;">
                    ${results.slice(0, 6).map((r, i) => `
                        <div style="display:flex; justify-content:space-between; align-items:center; background:rgba(15,23,42,0.75); padding:5px 8px; border-radius:6px;">
                            <span>${i + 1}. <strong>${escapeHtml(r.title || r.name || r.filename || 'BGM Track')}</strong> <small style="color:#94a3b8;">(${escapeHtml(r.source || r.mood || 'RF')})</small></span>
                            <button type="button" class="btn btn-xs btn-outline btn-fetch-rf-item" data-mood="${escapeHtml(r.mood || q)}">İndir &amp; Seç</button>
                        </div>
                    `).join('') || '<div>Doğrudan eşleşme bulunamadı, otomatik sentez/havuz indirilebilir: <button type="button" class="btn btn-xs btn-outline btn-fetch-rf-item" data-mood="' + escapeHtml(q) + '">Havuza İndir</button></div>'}
                </div>
            `;
            out.querySelectorAll('.btn-fetch-rf-item').forEach(btn => {
                btn.addEventListener('click', async () => {
                    const mood = btn.getAttribute('data-mood') || q;
                    btn.disabled = true;
                    btn.textContent = 'İndiriliyor...';
                    try {
                        const fRes = await fetch('/api/audio/royalty-free/fetch', {
                            method: 'POST', headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ mood, query: q })
                        });
                        const fData = await fRes.json();
                        await loadBgmList();
                        if (fData.filename) {
                            const sel = document.getElementById('select-bgm-track');
                            const studioSel = document.getElementById('studio-bgm-track');
                            if (sel) sel.value = fData.filename;
                            if (studioSel) studioSel.value = fData.filename;
                        }
                        showToast(`🎵 Telifsiz BGM hazır: ${fData.filename || mood}`);
                    } catch (e) {
                        showToast('İndirme hatası: ' + e.message, 'error');
                    } finally {
                        btn.disabled = false;
                        btn.textContent = 'Seçildi';
                    }
                });
            });
        }
    } catch (err) {
        if (out) out.textContent = 'Hata: ' + err.message;
    }
});
