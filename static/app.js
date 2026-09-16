/**
 * ShortsAI Studio Pro — Ana Frontend İstemci Mantığı
 * Tamamen reaktif, dayanıklı ve zengin özellikli YouTube Shorts Web Stüdyosu
 */

document.addEventListener('DOMContentLoaded', () => {
    // --------------------------------------------------------------------------
    // Küresel Uygulama Durumu (State)
    // --------------------------------------------------------------------------
    let currentPlan = null;
    let eventSource = null;
    let isRendering = false;
    let activeBgmAudio = null;
    let activeBgmTrackName = '';
    let karaokeAnimationTimer = null;

    // DOM Referansları
    const navItems = document.querySelectorAll('.nav-item');
    const tabPages = document.querySelectorAll('.tab-page');
    const pageTitle = document.getElementById('page-title');
    const pageSubtitle = document.getElementById('page-subtitle');

    const topicInput = document.getElementById('topic-input');
    const langSelect = document.getElementById('lang-select');
    const voiceSelect = document.getElementById('voice-select');
    const bgmSelect = document.getElementById('bgm-select');
    const bgmVolumeRange = document.getElementById('bgm-volume-range');
    const bgmVolVal = document.getElementById('bgm-vol-val');
    const toggleSfx = document.getElementById('toggle-sfx');
    const sfxVolumeRange = document.getElementById('sfx-volume-range');
    const sfxVolVal = document.getElementById('sfx-vol-val');
    const btnPreviewBgmInline = document.getElementById('btn-preview-bgm-inline');

    const btnGenerateScript = document.getElementById('btn-generate-script');
    const btnRenderDirect = document.getElementById('btn-render-direct');
    const btnRenderEdited = document.getElementById('btn-render-edited');
    const btnReplanAi = document.getElementById('btn-replan-ai');
    const btnAddNewScene = document.getElementById('btn-add-new-scene');

    const scenesContainer = document.getElementById('scenes-container');
    const totalDurationDisplay = document.getElementById('total-duration-display');
    const totalScenesDisplay = document.getElementById('total-scenes-display');
    const sceneCountBadge = document.getElementById('scene-count-badge');
    const galleryCountBadge = document.getElementById('gallery-count-badge');
    const bgmCountBadge = document.getElementById('bgm-count-badge');

    // 9:16 Simülatör Elemanları
    const phoneSubWrapper = document.getElementById('phone-sub-wrapper');
    const phoneSubDisplay = document.getElementById('phone-sub-display');
    const subFontFamily = document.getElementById('sub-font-family');
    const subHighlightColor = document.getElementById('sub-highlight-color');
    const subBaseColor = document.getElementById('sub-base-color');
    const subStrokeColor = document.getElementById('sub-stroke-color');
    const subStrokeWidth = document.getElementById('sub-stroke-width');
    const subFontSize = document.getElementById('sub-font-size');
    const subYPos = document.getElementById('sub-y-pos');
    const btnTestSubAnim = document.getElementById('btn-test-sub-anim');

    // Monitör ve Konsol
    const monitorPanel = document.getElementById('monitor-panel');
    const monitorStatusText = document.getElementById('monitor-status-text');
    const monitorKeywordText = document.getElementById('monitor-keyword-text');
    const progressPctText = document.getElementById('progress-pct-text');
    const progressBarFill = document.getElementById('progress-bar-fill');
    const consoleLogs = document.getElementById('console-logs');
    const btnCancelRender = document.getElementById('btn-cancel-render');

    // Trend Tarayıcısı
    const btnScanTrends = document.getElementById('btn-scan-trends');
    const trendingResultsContainer = document.getElementById('trending-results-container');

    // Müzik Çalar
    const globalBgmAudio = document.getElementById('global-bgm-audio');
    const playerTrackName = document.getElementById('player-track-name');
    const btnPlayerPlayToggle = document.getElementById('btn-player-play-toggle');
    const playerVolumeSlider = document.getElementById('player-volume-slider');
    const playerTimeDisplay = document.getElementById('player-time-display');

    // Modal
    const videoModal = document.getElementById('video-modal');
    const modalCloseBtn = document.getElementById('modal-close-btn');
    const modalVideoTitle = document.getElementById('modal-video-title');
    const modalPlayer = document.getElementById('modal-player');
    const modalTitleCopy = document.getElementById('modal-title-copy');
    const modalTagsInput = document.getElementById('modal-tags-input');
    const modalDownloadBtn = document.getElementById('modal-download-btn');

    // --------------------------------------------------------------------------
    // Başlık ve Sekme Haritası
    // --------------------------------------------------------------------------
    const TAB_METADATA = {
        'studio': { title: 'İçerik Üretim Stüdyosu', subtitle: 'Yapay Zeka Destekli Otomatik Dikey YouTube Shorts Üretim Paneli' },
        'editor': { title: 'Sahne Zaman Çizelgesi & Metin Düzenleyici', subtitle: 'Sahneleri sürükleyin, süresini değiştirin, yeni sahne ekleyin veya silin' },
        'subtitles': { title: '9:16 Altyazı Tasarımcısı & Telefon Simülatörü', subtitle: 'Dikey mobil ekranda kelime kelime vurgulanan karaoke altyazı şablonlarını özelleştirin' },
        'audio-sfx': { title: 'Müzik Kütüphanesi & SFX Konsolu', subtitle: 'Arka plan müziklerini tarayıcıda önceden dinleyin, yükleyin ve geçiş seslerini test edin' },
        'gallery': { title: 'Üretilen YouTube Shorts Galerisi', subtitle: 'Hazır Full HD dikey videolarınızı izleyin, indirin ve YouTube etiketlerini kopyalayın' },
        'settings': { title: 'Sistem Entegrasyonları & API Ayarları', subtitle: 'AI motorları (Gemini/OpenAI) ve stok video servislerinin anahtarlarını test edin' }
    };

    function switchTab(tabId) {
        navItems.forEach(item => {
            if (item.dataset.tab === tabId) item.classList.add('active');
            else item.classList.remove('active');
        });

        tabPages.forEach(page => {
            if (page.id === `tab-${tabId}`) page.classList.add('active');
            else page.classList.remove('active');
        });

        if (TAB_METADATA[tabId]) {
            pageTitle.textContent = TAB_METADATA[tabId].title;
            pageSubtitle.textContent = TAB_METADATA[tabId].subtitle;
        }

        if (tabId === 'gallery') loadGallery();
        if (tabId === 'audio-sfx') loadBgmTracks();
        if (tabId === 'subtitles') updateSimulatorStyles();
    }

    navItems.forEach(item => {
        item.addEventListener('click', () => switchTab(item.dataset.tab));
    });

    // Adım Rehberi Tıklamaları
    document.querySelectorAll('.step-card').forEach(card => {
        card.addEventListener('click', () => {
            const step = parseInt(card.dataset.step);
            if (step === 1) { switchTab('studio'); topicInput.focus(); }
            else if (step === 2) {
                if (currentPlan) switchTab('editor');
                else { switchTab('studio'); btnGenerateScript.click(); }
            }
            else if (step === 3) switchTab('subtitles');
            else if (step === 4) { switchTab('studio'); btnRenderDirect.click(); }
        });
    });

    // Hazır Konu Butonları
    document.querySelectorAll('.preset-pill').forEach(btn => {
        btn.addEventListener('click', () => {
            topicInput.value = btn.dataset.topic;
            showToast(`Konu aktarıldı: ${btn.dataset.topic}`);
            switchTab('studio');
        });
    });

    // --------------------------------------------------------------------------
    // Ses ve Altyazı Canlı Önizleme Mantığı
    // --------------------------------------------------------------------------
    function updateSimulatorStyles() {
        if (!phoneSubWrapper || !phoneSubDisplay) return;

        const font = subFontFamily.value;
        const hlColor = subHighlightColor.value;
        const baseColor = subBaseColor.value;
        const strokeColor = subStrokeColor.value;
        const strokeW = parseInt(subStrokeWidth.value);
        const fontSize = parseInt(subFontSize.value);
        const yPos = parseFloat(subYPos.value);

        // Ekran dikey konumu (0.8 = alttan %20)
        const bottomPercent = Math.round((1.0 - yPos) * 100);
        phoneSubWrapper.style.bottom = `${bottomPercent}%`;

        // Tipografi ve Renkler
        phoneSubDisplay.style.fontFamily = font;
        phoneSubDisplay.style.fontSize = `${Math.round(fontSize * 0.38)}px`; // Mockup ölçekleme
        phoneSubDisplay.style.color = baseColor;
        phoneSubDisplay.style.webkitTextStroke = `${Math.max(1, Math.round(strokeW * 0.4))}px ${strokeColor}`;

        const hlSpan = phoneSubDisplay.querySelector('.highlight-word');
        if (hlSpan) {
            hlSpan.style.color = hlColor;
        }

        // Değer etiketlerini güncelle
        document.getElementById('highlight-hex-label').textContent = hlColor.toUpperCase();
        document.getElementById('base-hex-label').textContent = baseColor.toUpperCase();
        document.getElementById('stroke-hex-label').textContent = strokeColor.toUpperCase();
        document.getElementById('stroke-width-label').textContent = `${strokeW}px`;
        document.getElementById('sub-size-val').textContent = `${fontSize}px`;
        document.getElementById('sub-pos-val').textContent = `%${Math.round(yPos * 100)}`;
    }

    [subFontFamily, subHighlightColor, subBaseColor, subStrokeColor, subStrokeWidth, subFontSize, subYPos].forEach(input => {
        if (input) input.addEventListener('input', updateSimulatorStyles);
    });

    // Altyazı Hazır Stil Şablonları
    document.querySelectorAll('.btn-sub-preset').forEach(btn => {
        btn.addEventListener('click', () => {
            if (btn.dataset.hl) subHighlightColor.value = btn.dataset.hl;
            if (btn.dataset.base) subBaseColor.value = btn.dataset.base;
            if (btn.dataset.font) subFontFamily.value = btn.dataset.font;
            updateSimulatorStyles();
            showToast(`Stil şablonu uygulandı: ${btn.textContent.trim()}`);
        });
    });

    // Karaoke Animasyon Simülasyonu
    if (btnTestSubAnim) {
        btnTestSubAnim.addEventListener('click', () => {
            if (karaokeAnimationTimer) clearInterval(karaokeAnimationTimer);

            const sampleWords = ["BU", "BİR", "KARAOKE", "ALTYAZI", "ÖNİZLEME", "ÖRNEĞİDİR"];
            let wordIndex = 0;

            karaokeAnimationTimer = setInterval(() => {
                let html = "";
                sampleWords.forEach((w, i) => {
                    if (i === wordIndex) {
                        html += `<span class="highlight-word" style="color:${subHighlightColor.value}; text-shadow:0 0 12px ${subHighlightColor.value}; font-size:1.08em;">${w}</span> `;
                    } else {
                        html += `${w} `;
                    }
                });
                phoneSubDisplay.innerHTML = html.trim();

                wordIndex = (wordIndex + 1) % sampleWords.length;
            }, 380);

            setTimeout(() => {
                if (karaokeAnimationTimer) {
                    clearInterval(karaokeAnimationTimer);
                    phoneSubDisplay.innerHTML = `Bu Bir <span class="highlight-word" style="color:${subHighlightColor.value}">KARAOKE</span> Altyazı Örneğidir`;
                }
            }, 5500);
        });
    }

    // Ses Slider Değer Güncellemeleri
    bgmVolumeRange.addEventListener('input', (e) => {
        bgmVolVal.textContent = `%${Math.round(e.target.value * 100)}`;
        if (globalBgmAudio) globalBgmAudio.volume = parseFloat(e.target.value);
    });

    sfxVolumeRange.addEventListener('input', (e) => {
        sfxVolVal.textContent = `%${Math.round(e.target.value * 100)}`;
    });

    // --------------------------------------------------------------------------
    // Dahili BGM ve SFX Ses Çalar
    // --------------------------------------------------------------------------
    function playTrack(filename) {
        if (!filename) return;
        activeBgmTrackName = filename;
        playerTrackName.textContent = filename;
        globalBgmAudio.src = `/bgm_audio/${encodeURIComponent(filename)}`;
        globalBgmAudio.volume = parseFloat(playerVolumeSlider.value);
        globalBgmAudio.play();
        btnPlayerPlayToggle.innerHTML = '<i class="fa-solid fa-pause"></i>';
        if (btnPreviewBgmInline) btnPreviewBgmInline.innerHTML = '<i class="fa-solid fa-pause"></i>';
    }

    function togglePlayback() {
        if (!globalBgmAudio.src || globalBgmAudio.src.endsWith('/')) {
            const firstOpt = bgmSelect.value || (bgmSelect.options[1] ? bgmSelect.options[1].value : '');
            if (firstOpt) playTrack(firstOpt);
            return;
        }

        if (globalBgmAudio.paused) {
            globalBgmAudio.play();
            btnPlayerPlayToggle.innerHTML = '<i class="fa-solid fa-pause"></i>';
            if (btnPreviewBgmInline) btnPreviewBgmInline.innerHTML = '<i class="fa-solid fa-pause"></i>';
        } else {
            globalBgmAudio.pause();
            btnPlayerPlayToggle.innerHTML = '<i class="fa-solid fa-play"></i>';
            if (btnPreviewBgmInline) btnPreviewBgmInline.innerHTML = '<i class="fa-solid fa-play"></i>';
        }
    }

    if (btnPlayerPlayToggle) btnPlayerPlayToggle.addEventListener('click', togglePlayback);
    if (btnPreviewBgmInline) {
        btnPreviewBgmInline.addEventListener('click', () => {
            const sel = bgmSelect.value;
            if (!sel) return showToast("Önce bir arka plan müziği seçin.");
            if (activeBgmTrackName !== sel) playTrack(sel);
            else togglePlayback();
        });
    }

    if (playerVolumeSlider) {
        playerVolumeSlider.addEventListener('input', (e) => {
            globalBgmAudio.volume = parseFloat(e.target.value);
        });
    }

    globalBgmAudio.addEventListener('timeupdate', () => {
        const cur = Math.floor(globalBgmAudio.currentTime);
        const m = Math.floor(cur / 60);
        const s = cur % 60;
        playerTimeDisplay.textContent = `${m}:${s < 10 ? '0' : ''}${s}`;
    });

    globalBgmAudio.addEventListener('ended', () => {
        btnPlayerPlayToggle.innerHTML = '<i class="fa-solid fa-play"></i>';
        if (btnPreviewBgmInline) btnPreviewBgmInline.innerHTML = '<i class="fa-solid fa-play"></i>';
    });

    // SFX Test Sesleri (Web Audio API Synthesizer)
    function playSyntheticSFX(type) {
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        const now = ctx.currentTime;

        if (type === 'whoosh') {
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.type = 'sine';
            osc.frequency.setValueAtTime(150, now);
            osc.frequency.exponentialRampToValueAtTime(800, now + 0.12);
            osc.frequency.exponentialRampToValueAtTime(120, now + 0.25);
            gain.gain.setValueAtTime(0.01, now);
            gain.gain.linearRampToValueAtTime(0.35, now + 0.12);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.25);
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.start(now);
            osc.stop(now + 0.25);
        } else if (type === 'pop') {
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.type = 'sine';
            osc.frequency.setValueAtTime(850, now);
            osc.frequency.exponentialRampToValueAtTime(100, now + 0.12);
            gain.gain.setValueAtTime(0.4, now);
            gain.gain.exponentialRampToValueAtTime(0.001, now + 0.12);
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.start(now);
            osc.stop(now + 0.12);
        }
    }

    document.getElementById('btn-test-whoosh')?.addEventListener('click', () => playSyntheticSFX('whoosh'));
    document.getElementById('btn-test-pop')?.addEventListener('click', () => playSyntheticSFX('pop'));

    // --------------------------------------------------------------------------
    // Müzik Listesi Çekme & Yükleme & Silme
    // --------------------------------------------------------------------------
    async function loadBgmTracks() {
        try {
            const res = await fetch('/api/bgm/list');
            const data = await res.json();
            const tracks = data.tracks || [];

            bgmCountBadge.textContent = `${tracks.length} Parça`;
            bgmSelect.innerHTML = '<option value="">Yok (Sadece Seslendirme)</option>';

            const trackListContainer = document.getElementById('track-list-container');
            trackListContainer.innerHTML = '';

            if (tracks.length === 0) {
                trackListContainer.innerHTML = '<div class="empty-state">Henüz müzik yüklenmedi. Yukarıdaki alana sürükleyebilirsiniz.</div>';
                return;
            }

            tracks.forEach(track => {
                // Select kutusuna ekle
                const opt = document.createElement('option');
                opt.value = track;
                opt.textContent = track;
                bgmSelect.appendChild(opt);

                // Liste kartı oluştur
                const item = document.createElement('div');
                item.className = 'track-item';
                item.innerHTML = `
                    <div class="track-item-name">
                        <i class="fa-solid fa-music"></i>
                        <span>${track}</span>
                    </div>
                    <div class="track-item-actions">
                        <button class="btn btn-secondary btn-sm btn-play-track" title="Dinle">
                            <i class="fa-solid fa-play"></i>
                        </button>
                        <button class="btn btn-secondary btn-sm btn-select-track" title="Stüdyo için Seç">
                            Seç
                        </button>
                        <button class="btn btn-outline btn-sm btn-del-track" style="color:var(--danger);" title="Sil">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    </div>
                `;

                item.querySelector('.btn-play-track').addEventListener('click', () => playTrack(track));
                item.querySelector('.btn-select-track').addEventListener('click', () => {
                    bgmSelect.value = track;
                    showToast(`Arka plan müziği seçildi: ${track}`);
                });
                item.querySelector('.btn-del-track').addEventListener('click', async () => {
                    if (confirm(`'${track}' dosyasını kalıcı olarak silmek istediğinize emin misiniz?`)) {
                        await fetch(`/api/bgm/${encodeURIComponent(track)}`, { method: 'DELETE' });
                        showToast(`Müzik silindi: ${track}`);
                        loadBgmTracks();
                    }
                });

                trackListContainer.appendChild(item);
            });
        } catch (err) {
            console.error("BGM listesi hatası:", err);
        }
    }

    // Müzik Sürükle Bırak Yükleme
    const dropzone = document.getElementById('dropzone');
    const bgmFileInput = document.getElementById('bgm-file-input');

    if (dropzone && bgmFileInput) {
        dropzone.addEventListener('click', () => bgmFileInput.click());
        dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.style.borderColor = 'var(--primary)'; });
        dropzone.addEventListener('dragleave', () => { dropzone.style.borderColor = 'var(--border-glass)'; });
        dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropzone.style.borderColor = 'var(--border-glass)';
            if (e.dataTransfer.files.length) uploadBgmFile(e.dataTransfer.files[0]);
        });
        bgmFileInput.addEventListener('change', () => {
            if (bgmFileInput.files.length) uploadBgmFile(bgmFileInput.files[0]);
        });
    }

    async function uploadBgmFile(file) {
        const formData = new FormData();
        formData.append('file', file);
        try {
            showToast("Müzik yükleniyor...");
            const res = await fetch('/api/bgm/upload', { method: 'POST', body: formData });
            const data = await res.json();
            if (res.ok) {
                showToast(`Müzik yüklendi: ${data.filename}`);
                loadBgmTracks();
            } else {
                alert(data.detail || "Müzik yüklenemedi.");
            }
        } catch (err) {
            alert(`Yükleme hatası: ${err.message}`);
        }
    }

    // --------------------------------------------------------------------------
    // İnteraktif Sahne Zaman Çizelgesi & Editör Mantığı
    // --------------------------------------------------------------------------
    function updateTimelineMetrics() {
        if (!currentPlan || !currentPlan.scenes) {
            totalDurationDisplay.textContent = '0 sn';
            totalScenesDisplay.textContent = '0';
            sceneCountBadge.textContent = '0';
            return;
        }

        const totalSec = currentPlan.scenes.reduce((acc, sc) => acc + (parseFloat(sc.duration) || 6), 0);
        totalDurationDisplay.textContent = `${Math.round(totalSec)} sn`;
        totalScenesDisplay.textContent = currentPlan.scenes.length;
        sceneCountBadge.textContent = currentPlan.scenes.length;
    }

    function renderSceneEditor(plan) {
        currentPlan = plan;
        scenesContainer.innerHTML = '';
        const scenes = plan.scenes || [];
        updateTimelineMetrics();

        if (scenes.length === 0) {
            scenesContainer.innerHTML = '<div class="empty-state">Henüz bir sahne bulunmuyor.</div>';
            return;
        }

        scenes.forEach((sc, idx) => {
            const card = document.createElement('div');
            card.className = 'scene-item-card';
            card.dataset.index = idx;

            const qList = sc.search_queries || [sc.search_query || 'nature'];
            const q1 = qList[0] || '';
            const q2 = qList[1] || '';
            const q3 = qList[2] || '';

            card.innerHTML = `
                <div class="scene-card-topbar">
                    <div class="scene-title-badge">
                        <span class="scene-index-badge">Sahne ${idx + 1}</span>
                        <div class="scene-duration-picker">
                            <i class="fa-solid fa-clock"></i> Süre:
                            <input type="number" class="scene-dur-val" value="${sc.duration || 6}" min="3" max="15"> sn
                        </div>
                    </div>
                    <div class="scene-card-controls">
                        <button class="btn btn-secondary btn-sm btn-move-up" title="Yukarı Taşı" ${idx === 0 ? 'disabled' : ''}>
                            <i class="fa-solid fa-arrow-up"></i>
                        </button>
                        <button class="btn btn-secondary btn-sm btn-move-down" title="Aşağı Taşı" ${idx === scenes.length - 1 ? 'disabled' : ''}>
                            <i class="fa-solid fa-arrow-down"></i>
                        </button>
                        <button class="btn btn-outline btn-sm btn-del-scene" style="color:var(--danger);" title="Sahneyi Sil">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                    </div>
                </div>

                <div class="scene-grid-inputs">
                    <div class="form-group mb-0">
                        <label>Görsel Sahne Tanımı (İngilizce)</label>
                        <input type="text" class="scene-desc-input" value="${sc.scene_description || ''}" placeholder="Ekranda ne görünecek...">
                    </div>
                    <div class="form-group mb-0">
                        <label>Stok Arama Kelimeleri [Spesifik / Orta / Genel]</label>
                        <div class="queries-input-wrapper">
                            <input type="text" class="scene-q1" value="${q1}" placeholder="Spesifik terim">
                            <input type="text" class="scene-q2" value="${q2}" placeholder="Orta terim">
                            <input type="text" class="scene-q3" value="${q3}" placeholder="Genel terim">
                        </div>
                    </div>
                </div>

                <div class="form-group mb-0 mt-3">
                    <label>Seslendirme Metni (Narration)</label>
                    <textarea class="scene-textarea scene-narration-input">${sc.narration || ''}</textarea>
                </div>
            `;

            // Süre Değişikliği
            card.querySelector('.scene-dur-val').addEventListener('change', (e) => {
                sc.duration = parseFloat(e.target.value) || 6;
                updateTimelineMetrics();
            });

            // Yukarı Taşı
            card.querySelector('.btn-move-up').addEventListener('click', () => {
                if (idx > 0) {
                    saveDomToPlan();
                    const temp = currentPlan.scenes[idx - 1];
                    currentPlan.scenes[idx - 1] = currentPlan.scenes[idx];
                    currentPlan.scenes[idx] = temp;
                    renderSceneEditor(currentPlan);
                }
            });

            // Aşağı Taşı
            card.querySelector('.btn-move-down').addEventListener('click', () => {
                if (idx < currentPlan.scenes.length - 1) {
                    saveDomToPlan();
                    const temp = currentPlan.scenes[idx + 1];
                    currentPlan.scenes[idx + 1] = currentPlan.scenes[idx];
                    currentPlan.scenes[idx] = temp;
                    renderSceneEditor(currentPlan);
                }
            });

            // Sahneyi Sil
            card.querySelector('.btn-del-scene').addEventListener('click', () => {
                if (currentPlan.scenes.length <= 1) {
                    return alert("Videoda en az 1 sahne bulunmalıdır.");
                }
                saveDomToPlan();
                currentPlan.scenes.splice(idx, 1);
                renderSceneEditor(currentPlan);
                showToast(`Sahne ${idx + 1} silindi.`);
            });

            scenesContainer.appendChild(card);
        });
    }

    function saveDomToPlan() {
        if (!currentPlan || !currentPlan.scenes) return;
        const cards = document.querySelectorAll('.scene-item-card');
        let fullNarr = "";

        cards.forEach((c, i) => {
            if (currentPlan.scenes[i]) {
                const dur = parseFloat(c.querySelector('.scene-dur-val')?.value) || 6;
                const desc = c.querySelector('.scene-desc-input')?.value || '';
                const q1 = c.querySelector('.scene-q1')?.value || '';
                const q2 = c.querySelector('.scene-q2')?.value || '';
                const q3 = c.querySelector('.scene-q3')?.value || '';
                const narr = c.querySelector('.scene-narration-input')?.value || '';

                currentPlan.scenes[i].duration = dur;
                currentPlan.scenes[i].scene_description = desc;
                currentPlan.scenes[i].search_queries = [q1, q2, q3].filter(q => q.trim().length > 0);
                currentPlan.scenes[i].narration = narr;
                fullNarr += narr + " ";
            }
        });

        currentPlan.full_narration = fullNarr.trim();
        updateTimelineMetrics();
    }

    // Yeni Sahne Ekle Butonu
    if (btnAddNewScene) {
        btnAddNewScene.addEventListener('click', () => {
            if (!currentPlan) {
                currentPlan = {
                    title: topicInput.value.trim() || "Video",
                    visual_theme: "cinematic documentary",
                    full_narration: "",
                    scenes: []
                };
            }
            saveDomToPlan();

            currentPlan.scenes.push({
                scene_number: currentPlan.scenes.length + 1,
                duration: 6,
                scene_description: "Cinematic close-up of a dramatic scene",
                search_queries: ["cinematic nature", "dark background", "space stars"],
                narration: "Bu yeni eklenen sahnenin açıklayıcı anlatım metnidir."
            });

            renderSceneEditor(currentPlan);
            showToast("Yeni sahne zaman çizelgesine eklendi.");
        });
    }

    // --------------------------------------------------------------------------
    // Yapay Zeka ile Senaryo Üretme
    // --------------------------------------------------------------------------
    btnGenerateScript.addEventListener('click', async () => {
        const topic = topicInput.value.trim();
        if (!topic) return alert('Lütfen bir video konusu girin!');

        btnGenerateScript.disabled = true;
        btnGenerateScript.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Senaryo Oluşturuluyor...';

        try {
            const res = await fetch('/api/script/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ keyword: topic, language: langSelect.value })
            });
            const data = await res.json();
            if (data.status === 'ok') {
                currentPlan = data.plan;
                renderSceneEditor(currentPlan);
                switchTab('editor');
                showToast('✨ AI Senaryosu hazır! Sahneleri düzenleyebilirsiniz.');
            } else {
                alert('Senaryo oluşturulamadı.');
            }
        } catch (err) {
            alert(`Senaryo hatası: ${err.message}`);
        } finally {
            btnGenerateScript.disabled = false;
            btnGenerateScript.innerHTML = '<i class="fa-solid fa-code-branch"></i> Önce Senaryoyu Oluştur & Düzenle';
        }
    });

    btnReplanAi?.addEventListener('click', () => btnGenerateScript.click());

    // --------------------------------------------------------------------------
    // Render Pipeline & Canlı İzleme (Persistent Status & SSE)
    // --------------------------------------------------------------------------
    function initSSE() {
        if (eventSource) eventSource.close();
        eventSource = new EventSource('/api/events');

        eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.type === 'log') {
                    appendConsoleLog(data.data);
                } else if (data.type === 'progress') {
                    const pct = data.data.percent || 0;
                    progressBarFill.style.width = `${pct}%`;
                    progressPctText.textContent = `%${pct}`;
                    if (data.data.step) monitorStatusText.textContent = data.data.step;
                } else if (data.type === 'complete') {
                    isRendering = false;
                    progressBarFill.style.width = '100%';
                    progressPctText.textContent = '%100';
                    monitorStatusText.textContent = 'Render Tamamlandı!';
                    document.getElementById('chip-render-text').textContent = 'Sistem Hazır';
                    showToast('🎉 Video başarıyla tamamlandı!');
                    
                    loadGallery();

                    if (data.data && data.data.url) {
                        modalVideoTitle.textContent = data.data.keyword || topicInput.value;
                        modalPlayer.src = data.data.url;
                        modalDownloadBtn.href = data.data.url;
                        modalTitleCopy.value = data.data.keyword || topicInput.value;
                        const safeTag = (data.data.keyword || 'Trend').replace(/[^\w\s]/gi, '').replace(/\s+/g, '');
                        modalTagsInput.value = `#Shorts #${safeTag} #Viral #YouTubeShorts #Bilgi`;
                        videoModal.classList.remove('hidden');
                        modalPlayer.play().catch(() => {});
                    }
                } else if (data.type === 'error') {
                    isRendering = false;
                    const isCancel = data.data && (data.data.includes('iptal') || data.data.includes('cancelled'));
                    document.getElementById('chip-render-text').textContent = isCancel ? 'İptal Edildi' : 'Hata Oluştu';
                    if (isCancel) {
                        progressBarFill.style.width = '0%';
                        progressPctText.textContent = '%0';
                        monitorStatusText.textContent = 'İşlem İptal Edildi';
                    }
                    appendConsoleLog(`[${isCancel ? 'İPTAL' : 'HATA'}] ${data.data}`);
                    showToast(`${data.data}`);
                }
            } catch (e) {}
        };
    }

    function appendConsoleLog(msg) {
        const line = document.createElement('div');
        line.className = 'log-line';
        line.textContent = `[${new Date().toLocaleTimeString()}] ${msg}`;
        consoleLogs.appendChild(line);
        consoleLogs.scrollTop = consoleLogs.scrollHeight;
    }

    async function launchRender(customPlan = null) {
        saveDomToPlan();
        const planToUse = customPlan || currentPlan;
        const topic = (topicInput.value.trim()) || (planToUse ? planToUse.title : 'Shorts Video');
        if (!topic) return alert('Lütfen bir video konusu girin!');

        monitorPanel.classList.remove('hidden');
        monitorStatusText.textContent = 'Render başlatılıyor...';
        monitorKeywordText.textContent = `Konu: ${topic}`;
        progressBarFill.style.width = '2%';
        progressPctText.textContent = '%2';
        consoleLogs.innerHTML = '<div class="log-line info">[Sistem] İşlem başlatıldı, arka plan motoruna bağlanılıyor...</div>';
        document.getElementById('chip-render-text').textContent = 'Render Ediliyor';
        isRendering = true;

        initSSE();

        const payload = {
            keyword: topic,
            plan: planToUse,
            language: langSelect.value,
            voice_gender: voiceSelect.value,
            bgm_track: bgmSelect.value,
            bgm_volume: parseFloat(bgmVolumeRange.value),
            subtitle_highlight_color: subHighlightColor.value,
            subtitle_color: subBaseColor.value,
            subtitle_font_size: parseInt(subFontSize.value),
            subtitle_y_position: parseFloat(subYPos.value)
        };

        try {
            const res = await fetch('/api/video/render', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const resData = await res.json();
            if (res.ok) {
                showToast('🚀 Render işlemi başlatıldı! Canlı loglar akıyor...');
            } else {
                alert(`Hata: ${resData.detail || resData.message || 'Render başlatılamadı.'}`);
                monitorPanel.classList.add('hidden');
                document.getElementById('chip-render-text').textContent = 'Sistem Hazır';
            }
        } catch (err) {
            alert(`Render başlatma hatası: ${err.message}`);
            monitorPanel.classList.add('hidden');
            document.getElementById('chip-render-text').textContent = 'Sistem Hazır';
        }
    }

    btnRenderDirect.addEventListener('click', () => launchRender(currentPlan));
    btnRenderEdited.addEventListener('click', () => launchRender(currentPlan));

    // Dil ve Ses Değişim Takibi
    if (langSelect) {
        langSelect.addEventListener('change', () => {
            const isTr = langSelect.value === 'tr';
            const langChip = document.getElementById('chip-lang-val');
            if (langChip) langChip.textContent = isTr ? 'Türkçe' : 'İngilizce';
            if (voiceSelect && voiceSelect.options.length >= 2) {
                voiceSelect.options[0].textContent = isTr ? 'Erkek Sesi (Ahmet)' : 'Erkek Sesi (Guy)';
                voiceSelect.options[1].textContent = isTr ? 'Kadın Sesi (Emel)' : 'Kadın Sesi (Jenny)';
            }
            showToast(`Dil seçildi: ${isTr ? 'Türkçe (TR)' : 'İngilizce (EN)'}`);
        });
    }

    if (voiceSelect) {
        voiceSelect.addEventListener('change', () => {
            const voiceChip = document.getElementById('chip-voice-val');
            if (voiceChip) {
                voiceChip.textContent = voiceSelect.value === 'male' ? 'Erkek Ses' : 'Kadın Ses';
            }
        });
    }

    // Render İptal Butonu
    if (btnCancelRender) {
        btnCancelRender.addEventListener('click', async () => {
            if (confirm("Render işlemini durdurmak ve iptal etmek istediğinize emin misiniz?")) {
                btnCancelRender.disabled = true;
                btnCancelRender.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> İptal Ediliyor...';
                try {
                    await fetch('/api/video/cancel', { method: 'POST' });
                    showToast("Render durdurma sinyali gönderildi...");
                } catch (e) {
                    showToast("İptal isteği iletilemedi: " + e.message);
                } finally {
                    setTimeout(() => {
                        btnCancelRender.disabled = false;
                        btnCancelRender.innerHTML = '<i class="fa-solid fa-ban"></i> İptal Et';
                    }, 2000);
                }
            }
        });
    }

    // Modal Kapatma
    if (modalCloseBtn) {
        modalCloseBtn.addEventListener('click', () => {
            videoModal.classList.add('hidden');
            modalPlayer.pause();
        });
    }

    // Kopyalama Butonları
    document.querySelectorAll('.btn-copy').forEach(btn => {
        btn.addEventListener('click', () => {
            const targetId = btn.dataset.target;
            const input = document.getElementById(targetId);
            if (input) {
                navigator.clipboard.writeText(input.value);
                showToast("Panoya kopyalandı!");
            }
        });
    });

    // --------------------------------------------------------------------------
    // YouTube Viral Shorts Trend Tarayıcısı Pro
    // --------------------------------------------------------------------------
    if (btnScanTrends) {
        btnScanTrends.addEventListener('click', async () => {
            const topic = topicInput.value.trim() || 'Uzay';
            const timeFilter = document.getElementById('trend-time-filter')?.value || 'week';
            const categoryFilter = document.getElementById('trend-category-filter')?.value || 'all';
            const sortFilter = document.getElementById('trend-sort-filter')?.value || 'views';

            btnScanTrends.disabled = true;
            btnScanTrends.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Canlı Analiz Ediliyor...';

            try {
                const url = `/api/trending/scan?topic=${encodeURIComponent(topic)}&time_filter=${timeFilter}&category=${categoryFilter}&sort_by=${sortFilter}`;
                const res = await fetch(url);
                const data = await res.json();
                const trends = data.trends || [];

                trendingResultsContainer.innerHTML = '';
                if (trends.length === 0) {
                    trendingResultsContainer.innerHTML = '<div class="empty-state">Bu kriterlere uygun trend Shorts bulunamadı.</div>';
                } else {
                    trends.forEach(t => {
                        const card = document.createElement('div');
                        card.className = 'trend-card';
                        card.innerHTML = `
                            <div>
                                <div class="trend-header-badges">
                                    <span class="badge" style="background:rgba(236,72,153,0.2); color:#f472b6; font-weight:700;">
                                        <i class="fa-solid fa-fire"></i> %${t.viral_score || 95} Viral Skor
                                    </span>
                                    <span style="font-size:11px; color:var(--text-muted);"><i class="fa-solid fa-eye"></i> ${t.view_count}</span>
                                </div>

                                ${t.thumbnail ? `<div class="trend-thumb">
                                    <img src="${t.thumbnail}" onerror="this.style.display='none'">
                                </div>` : ''}

                                <div class="trend-title">${t.title}</div>
                                <div class="trend-meta"><i class="fa-solid fa-user"></i> ${t.channel || 'YouTube Popüler'} &bull; ${t.published_at || 'Yeni'}</div>
                                <div class="trend-hook-pill">${t.hook_analysis || '🔥 Viral Kanca'}</div>
                            </div>
                            <div style="display:flex; gap:8px;">
                                <a href="${t.url}" target="_blank" class="btn btn-secondary btn-sm" style="text-decoration:none;">
                                    <i class="fa-solid fa-up-right-from-square"></i> İzle
                                </a>
                                <button class="btn btn-primary btn-sm btn-use-viral" style="flex:1;">
                                    <i class="fa-solid fa-wand-magic-sparkles"></i> Bu Kancayla Üret
                                </button>
                            </div>
                        `;

                        card.querySelector('.btn-use-viral').addEventListener('click', () => {
                            topicInput.value = t.script_prompt || t.title;
                            showToast(`Viral konu aktarıldı: ${t.title}`);
                            btnGenerateScript.click();
                        });

                        trendingResultsContainer.appendChild(card);
                    });
                }
            } catch (err) {
                showToast(`Trend tarama hatası: ${err.message}`);
            } finally {
                btnScanTrends.disabled = false;
                btnScanTrends.innerHTML = '<i class="fa-solid fa-magnifying-glass-chart"></i> Viral Trendleri Tara';
            }
        });
    }

    // --------------------------------------------------------------------------
    // Video Galerisi & YouTube Dağıtımı
    // --------------------------------------------------------------------------
    async function loadGallery() {
        const galleryContainer = document.getElementById('gallery-container');
        try {
            const res = await fetch('/api/gallery');
            const data = await res.json();
            const videos = data.videos || [];

            galleryCountBadge.textContent = `${videos.length}`;
            galleryContainer.innerHTML = '';

            if (videos.length === 0) {
                galleryContainer.innerHTML = '<div class="empty-state"><i class="fa-solid fa-film empty-icon"></i><p>Henüz üretilmiş bir video bulunmuyor. Stüdyo sekmesinden ilk videonuzu oluşturun!</p></div>';
                return;
            }

            videos.forEach(v => {
                const card = document.createElement('div');
                card.className = 'video-card';
                card.dataset.title = v.title.toLowerCase();

                card.innerHTML = `
                    <video src="${v.url}" controls preload="metadata"></video>
                    <div class="video-card-body">
                        <div class="video-card-title">${v.title}</div>
                        <div class="video-card-meta">
                            <span><i class="fa-solid fa-calendar-days"></i> ${v.created_at}</span>
                            <span><i class="fa-solid fa-hard-drive"></i> ${v.size_mb} MB</span>
                        </div>
                        <div class="video-card-actions">
                            <a href="${v.url}" download class="btn btn-secondary" title="İndir">
                                <i class="fa-solid fa-download"></i> İndir
                            </a>
                            <button class="btn btn-secondary btn-copy-meta" title="YouTube SEO Bilgilerini Kopyala">
                                <i class="fa-brands fa-youtube" style="color:#ff0000;"></i> SEO
                            </button>
                            <button class="btn btn-outline btn-del-video" style="color:var(--danger);" title="Sil">
                                <i class="fa-solid fa-trash"></i>
                            </button>
                        </div>
                    </div>
                `;

                card.querySelector('.btn-copy-meta').addEventListener('click', () => {
                    modalVideoTitle.textContent = v.title;
                    modalPlayer.src = v.url;
                    modalDownloadBtn.href = v.url;
                    modalTitleCopy.value = v.title;
                    const cleanTag = v.title.replace(/[^\w\s]/gi, '').replace(/\s+/g, '');
                    modalTagsInput.value = `#Shorts #${cleanTag} #Viral #YapayZeka #YouTubeShorts`;
                    videoModal.classList.remove('hidden');
                });

                card.querySelector('.btn-del-video').addEventListener('click', async () => {
                    if (confirm(`'${v.filename}' videosunu silmek istediğinize emin misiniz?`)) {
                        await fetch(`/api/gallery/${encodeURIComponent(v.filename)}`, { method: 'DELETE' });
                        showToast("Video ve altyazı dosyaları silindi.");
                        loadGallery();
                    }
                });

                galleryContainer.appendChild(card);
            });
        } catch (err) {
            console.error("Galeri yükleme hatası:", err);
        }
    }

    // Galeri Arama Filtresi
    document.getElementById('gallery-search-input')?.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase();
        document.querySelectorAll('.video-card').forEach(c => {
            if (c.dataset.title.includes(query)) c.style.display = 'flex';
            else c.style.display = 'none';
        });
    });

    document.getElementById('btn-refresh-gallery')?.addEventListener('click', loadGallery);

    // --------------------------------------------------------------------------
    // Sistem Ayarları & API Testleri
    // --------------------------------------------------------------------------
    async function loadConfig() {
        try {
            const res = await fetch('/api/config');
            const cfg = await res.json();

            document.getElementById('sidebar-ai-engine').textContent = `${cfg.ai_provider} (${cfg.ai_model})`;
            document.getElementById('chip-lang-val').textContent = cfg.language === 'tr' ? 'Türkçe' : 'İngilizce';
            document.getElementById('chip-voice-val').textContent = cfg.tts_gender === 'male' ? 'Erkek Ses' : 'Kadın Ses';

            langSelect.value = cfg.language;
            voiceSelect.value = cfg.tts_gender;

            if (cfg.subtitle) {
                subHighlightColor.value = cfg.subtitle.highlight_color || '#FFD700';
                subBaseColor.value = cfg.subtitle.color || '#FFFFFF';
                subFontSize.value = cfg.subtitle.font_size || 54;
                subYPos.value = cfg.subtitle.y_position || 0.8;
                updateSimulatorStyles();
            }

            if (cfg.keys) {
                if (cfg.keys.gemini) document.getElementById('key-gemini').placeholder = '●●●●●●●● (Tanımlı & Aktif)';
                if (cfg.keys.openai) document.getElementById('key-openai').placeholder = '●●●●●●●● (Tanımlı & Aktif)';
                if (cfg.keys.pexels) document.getElementById('key-pexels').placeholder = '●●●●●●●● (Tanımlı & Aktif)';
                if (cfg.keys.pixabay) document.getElementById('key-pixabay').placeholder = '●●●●●●●● (Tanımlı & Aktif)';
            }
        } catch (err) {
            console.error("Config yükleme hatası:", err);
        }
    }

    // API Key Test Butonları
    document.querySelectorAll('.btn-test-key').forEach(btn => {
        btn.addEventListener('click', async () => {
            const provider = btn.dataset.provider;
            const input = document.getElementById(`key-${provider}`);
            const val = input.value.trim();
            if (!val) return alert(`Lütfen test etmek için ${provider} API anahtarını girin.`);

            btn.disabled = true;
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Test Ediliyor';

            try {
                const res = await fetch('/api/keys/test', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ provider: provider, api_key: val })
                });
                const data = await res.json();
                if (res.ok) {
                    showToast(`✅ ${data.message}`);
                    btn.innerHTML = '<i class="fa-solid fa-circle-check" style="color:var(--emerald);"></i> Başarılı';
                } else {
                    alert(`Bağlantı Hatası: ${data.detail || 'Test başarısız'}`);
                    btn.innerHTML = '<i class="fa-solid fa-circle-xmark" style="color:var(--danger);"></i> Hata';
                }
            } catch (err) {
                alert(`Test hatası: ${err.message}`);
                btn.innerHTML = '<i class="fa-solid fa-plug"></i> Test Et';
            } finally {
                btn.disabled = false;
            }
        });
    });

    // Ayarlar Formu Kaydetme
    document.getElementById('settings-form')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const body = {};
        const gem = document.getElementById('key-gemini').value.trim();
        const oai = document.getElementById('key-openai').value.trim();
        const pex = document.getElementById('key-pexels').value.trim();
        const pix = document.getElementById('key-pixabay').value.trim();
        const rate = document.getElementById('setting-tts-rate').value.trim();
        const pitch = document.getElementById('setting-tts-pitch').value.trim();

        if (gem) body.gemini_key = gem;
        if (oai) body.openai_key = oai;
        if (pex) body.pexels_key = pex;
        if (pix) body.pixabay_key = pix;
        if (rate) body.tts_rate = rate;
        if (pitch) body.tts_pitch = pitch;

        await fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        showToast("Ayarlar başarıyla kaydedildi!");
        loadConfig();
    });

    // --------------------------------------------------------------------------
    // Sayfa Yenilenmesinde Render Durumunu Kurtarma (Restore Status)
    // --------------------------------------------------------------------------
    async function restoreRenderStatus() {
        try {
            const res = await fetch('/api/status');
            const data = await res.json();

            if (data.is_rendering) {
                isRendering = true;
                monitorPanel.classList.remove('hidden');
                monitorStatusText.textContent = data.step || 'Render devam ediyor...';
                monitorKeywordText.textContent = `Konu: ${data.keyword || 'Shorts Video'}`;
                progressBarFill.style.width = `${data.percent || 0}%`;
                progressPctText.textContent = `%${data.percent || 0}`;
                document.getElementById('chip-render-text').textContent = 'Render Ediliyor';

                consoleLogs.innerHTML = '';
                (data.logs || []).forEach(log => appendConsoleLog(log));

                initSSE();
            }
        } catch (err) {}
    }

    // --------------------------------------------------------------------------
    // Yardımcı: Toast Bildirimi
    // --------------------------------------------------------------------------
    function showToast(msg) {
        const toast = document.getElementById('toast-notification');
        const toastMsg = document.getElementById('toast-message');
        if (toast && toastMsg) {
            toastMsg.textContent = msg;
            toast.classList.add('show');
            setTimeout(() => toast.classList.remove('show'), 3200);
        }
    }

    // --------------------------------------------------------------------------
    // Başlangıç Yüklemeleri
    // --------------------------------------------------------------------------
    loadConfig();
    loadBgmTracks();
    loadGallery();
    restoreRenderStatus();
    updateSimulatorStyles();
});
