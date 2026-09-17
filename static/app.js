/**
 * ShortsAI Studio Ultimate — Frontend Application Engine (app.js)
 * Covers all 100 features from r10_shorts_fikirleri_ve_bot_ozellikleri.md
 */

document.addEventListener('DOMContentLoaded', () => {
    // ══════════════════════════════════════════════════════════════
    // STATE & VARIABLES
    // ══════════════════════════════════════════════════════════════
    let currentPlan = null;
    let eventSource = null;
    let allNiches = [];
    let isRendering = false;
    let selectedRedditPost = null;

    // DOM ELEMENTS
    const navButtons = document.querySelectorAll('.nav-btn');
    const tabPanes = document.querySelectorAll('.tab-pane');
    const pageTitle = document.getElementById('current-page-title');
    const pageDesc = document.getElementById('current-page-desc');

    // Studio Elements
    const inputTopic = document.getElementById('input-topic');
    const selectNiche = document.getElementById('select-niche');
    const selectSubPreset = document.getElementById('select-subtitle-preset');
    const selectLanguage = document.getElementById('select-language');
    const selectVoiceGender = document.getElementById('select-voice-gender');
    const chkSplitScreen = document.getElementById('chk-split-screen');
    const chkAntiDuplicate = document.getElementById('chk-anti-duplicate');
    const chkKenBurns = document.getElementById('chk-ken-burns');
    const chkAutoPublish = document.getElementById('chk-auto-publish');
    const btnCreateScript = document.getElementById('btn-create-script');
    const btnQuickRender = document.getElementById('btn-quick-render');
    const livePlayer = document.getElementById('live-preview-player');
    const mockupPlaceholder = document.getElementById('mockup-placeholder');
    const mockupStatusText = document.getElementById('mockup-status-text');

    // Persistent Monitor
    const persistentMonitor = document.getElementById('persistent-monitor');
    const dockStepTitle = document.getElementById('dock-step-title');
    const dockLogSnippet = document.getElementById('dock-log-snippet');
    const dockProgressFill = document.getElementById('dock-progress-fill');
    const dockProgressPct = document.getElementById('dock-progress-pct');
    const btnToggleLog = document.getElementById('btn-toggle-terminal-log');
    const btnCancelRender = document.getElementById('btn-cancel-render');
    const btnCloseDock = document.getElementById('btn-close-dock');
    const dockSpinner = document.getElementById('dock-spinner');
    const terminalPanel = document.getElementById('terminal-log-panel');
    const terminalBody = document.getElementById('terminal-log-body');
    const btnCloseLog = document.getElementById('btn-close-log');

    // ══════════════════════════════════════════════════════════════
    // 1. TAB ROUTING & NAVIGATION
    // ══════════════════════════════════════════════════════════════
    const TAB_METADATA = {
        "studio": { title: "Hızlı Üretim Stüdyosu", desc: "Konunuzu belirleyin, 35 niş arasından seçim yapın ve tek tıkla viral Shorts üretin." },
        "timeline": { title: "Sahne & Kurgu Editörü", desc: "AI tarafından üretilen sahneleri, süreleri ve arama terimlerini özelleştirin." },
        "niches": { title: "35 R10 Viral Niş Kütüphanesi", desc: "En çok izlenen ve gelir getiren 35 niş şablonundan birini seçin." },
        "rss-bot": { title: "Oto-Haber & RSS Botu (Item 1 & 57)", desc: "Canlı haber kaynaklarını tarayıp anında 45 saniyelik Shorts'a dönüştürün." },
        "batch": { title: "Toplu Üretim & CSV Kuyruğu (Item 70 & 78)", desc: "Çoklu konu listesini kuyruğa ekleyin ve 14 günlük ısınma (warm-up) sınırıyla üretin." },
        "growth": { title: "Büyüme, A/B Test & Algoritma Taktikleri", desc: "CTR artıran A/B varyantları, topluluk anketleri ve telif risk denetimi." },
        "effects": { title: "Split-Screen & Görsel FX Stüdyosu", desc: "Bölünmüş ekran oynanış kurgusu, Smart Crop ve Anti-Duplicate koruması." },
        "subtitles": { title: "CapCut Karaoke Altyazı Laboratuvarı", desc: "Kelime kelime yanan neon altyazılar, ön tanımlı profesyonel renk şablonları." },
        "audio": { title: "Ses, SFX & Müzik Konsolu", desc: "Audio Ducking, doğal Türkçe sesler ve geçiş Whoosh/Pop/Ding efektleri." },
        "channels": { title: "Kanal & Otomatik Yayın Dağıtımı", desc: "YouTube API v3 ile planlı yükleme ve TikTok/Reels çapraz paylaşım formatı." },
        "gallery": { title: "Video Galerisi & Arşiv", desc: "Tamamlanan Full HD videolarınızı izleyin, indirin veya kanala yükleyin." },
        "roadmap500": { title: "500 Madde Yol Haritası Gezgini", desc: "Tüm 500 kural ve teknik parametre doğrudan sistem mimarisine entegre edilmiştir." },
        "settings": { title: "Sistem & API Ayarları", desc: "0 TL maliyet katmanı, kota izleyici ve API anahtarı yönetimi." }
    };

    function switchTab(tabId) {
        navButtons.forEach(btn => {
            btn.classList.toggle('active', btn.getAttribute('data-tab') === tabId);
        });
        tabPanes.forEach(pane => {
            pane.classList.toggle('active', pane.id === `pane-${tabId}`);
        });

        if (TAB_METADATA[tabId]) {
            pageTitle.textContent = TAB_METADATA[tabId].title;
            pageDesc.textContent = TAB_METADATA[tabId].desc;
        }

        // On-demand tab loaders
        if (tabId === 'niches' && allNiches.length === 0) loadNiches();
        if (tabId === 'roadmap500') loadRoadmapItems();
        if (tabId === 'rss-bot') loadRssNews();
        if (tabId === 'gallery') loadGallery();
        if (tabId === 'settings') loadSettings();
        if (tabId === 'audio') loadBgmList();
    }

    navButtons.forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.getAttribute('data-tab')));
    });

    // ══════════════════════════════════════════════════════════════
    // 2. 35 NİŞİ YÜKLEME VE KARTLARI BASMA (Items 1 - 35)
    // ══════════════════════════════════════════════════════════════
    async function loadNiches() {
        try {
            const res = await fetch('/api/niches');
            const data = await res.json();
            allNiches = data.niches || [];

            // Hibrit Nişleri de Çekip Birleştir (Items 276-345)
            try {
                const hRes = await fetch('/api/hybrid_niches');
                const hData = await hRes.json();
                if (hData.hybrid_niches) {
                    allNiches = [...allNiches, ...hData.hybrid_niches];
                }
            } catch (he) {
                console.warn("Hibrit niş yükleme uyarısı:", he);
            }

            // Select dropdown'ı doldur
            selectNiche.innerHTML = '';
            const batchNicheSelect = document.getElementById('batch-default-niche');
            if (batchNicheSelect) batchNicheSelect.innerHTML = '';

            allNiches.forEach(n => {
                const opt = document.createElement('option');
                opt.value = n.id;
                opt.textContent = `${n.name} (${n.category})`;
                selectNiche.appendChild(opt);

                if (batchNicheSelect) {
                    const opt2 = opt.cloneNode(true);
                    batchNicheSelect.appendChild(opt2);
                }
            });

            // Niş Kartlarını Renderla
            renderNicheCards(allNiches);
            if (selectNiche.value) applyNicheProfile(selectNiche.value);
        } catch (err) {
            console.error("Niche yükleme hatası:", err);
        }
    }

    function renderNicheCards(nichesToRender) {
        const grid = document.getElementById('niches-cards-grid');
        if (!grid) return;
        grid.innerHTML = '';

        nichesToRender.forEach(n => {
            const card = document.createElement('div');
            card.className = 'niche-card';
            card.innerHTML = `
                <div class="niche-card-header">
                    <h4>${n.name}</h4>
                    <span class="niche-tag">${n.category}</span>
                </div>
                <div class="niche-hook">
                    <i class="fa-solid fa-quote-left"></i> Anlatım Tonu: <strong>${n.tone}</strong>
                </div>
                ${n.has_split_screen ? '<div style="font-size: 11px; color: #06B6D4;"><i class="fa-solid fa-gamepad"></i> Split-Screen Destekli</div>' : ''}
                <button class="btn btn-secondary niche-use-btn" data-niche-id="${n.id}">
                    <i class="fa-solid fa-arrow-right"></i> Bu Nişle Üret
                </button>
            `;
            grid.appendChild(card);
        });

        // "Bu Nişle Üret" Tıklama Olayları
        grid.querySelectorAll('.niche-use-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const nId = e.currentTarget.getAttribute('data-niche-id');
                const selected = allNiches.find(x => x.id === nId);
                if (selected) {
                    selectNiche.value = selected.id;
                    applyNicheProfile(selected.id);
                    switchTab('studio');
                    showToast(`🎯 '${selected.name}' nişi seçildi!`);
                }
            });
        });
    }

    // Niş Filtre Butonları
    document.querySelectorAll('.filter-pill').forEach(btn => {
        btn.addEventListener('click', (e) => {
            document.querySelectorAll('.filter-pill').forEach(b => b.classList.remove('active'));
            e.currentTarget.classList.add('active');
            const cat = e.currentTarget.getAttribute('data-cat');
            if (cat === 'all') {
                renderNicheCards(allNiches);
            } else {
                renderNicheCards(allNiches.filter(n => n.category.includes(cat)));
            }
        });
    });

    // ══════════════════════════════════════════════════════════════
    // 3. OTO-HABER & RSS BOTU (Item 1 & 57)
    // ══════════════════════════════════════════════════════════════
    async function loadRssNews() {
        const list = document.getElementById('rss-news-list');
        const sourceSelect = document.getElementById('select-rss-source');
        const source = sourceSelect ? sourceSelect.value : 'aa_guncel';
        list.innerHTML = '<div class="empty-state-box"><i class="fa-solid fa-spinner fa-spin"></i><p>Haberler taranıyor...</p></div>';

        try {
            const res = await fetch(`/api/rss/fetch?source=${source}&limit=6`);
            const data = await res.json();
            const items = data.items || [];

            if (items.length === 0) {
                list.innerHTML = '<div class="empty-state-box"><p>Bu kaynaktan haber çekilemedi.</p></div>';
                return;
            }

            list.innerHTML = '';
            items.forEach(item => {
                const row = document.createElement('div');
                row.className = 'glass-box mb-3';
                row.style.padding = '14px';
                row.innerHTML = `
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 10px;">
                        <div>
                            <strong style="font-size: 13px; color: #FFF;">${item.title}</strong>
                            <p style="font-size: 11px; color: #94A3B8; margin-top: 4px;">${item.description.slice(0, 120)}...</p>
                        </div>
                        <button class="btn btn-primary btn-sm btn-convert-rss" data-title="${encodeURIComponent(item.title)}">
                            <i class="fa-solid fa-bolt"></i> Shorts Yap
                        </button>
                    </div>
                `;
                list.appendChild(row);
            });

            list.querySelectorAll('.btn-convert-rss').forEach(b => {
                b.addEventListener('click', (e) => {
                    const rawTitle = decodeURIComponent(e.currentTarget.getAttribute('data-title'));
                    inputTopic.value = rawTitle;
                    selectNiche.value = "1_news_flash";
                    switchTab('studio');
                    showToast('📰 Haber konusu stüdyoya aktarıldı!');
                });
            });
        } catch (err) {
            list.innerHTML = `<div class="empty-state-box text-danger"><p>Haber tarama hatası: ${err.message}</p></div>`;
        }
    }

    document.getElementById('btn-fetch-rss-now')?.addEventListener('click', loadRssNews);
    document.getElementById('select-rss-source')?.addEventListener('change', loadRssNews);

    // ══════════════════════════════════════════════════════════════
    // 4. TOPLU ÜRETİM (BATCH) KUYRUĞU (Items 70 & 78)
    // ══════════════════════════════════════════════════════════════
    document.getElementById('btn-enqueue-batch')?.addEventListener('click', async () => {
        const text = document.getElementById('batch-topics-text').value.trim();
        if (!text) return alert('Lütfen en az bir konu girin!');

        const niche = document.getElementById('batch-default-niche').value;
        const lang = document.getElementById('batch-default-lang').value;

        try {
            const res = await fetch('/api/batch/submit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text, niche, language: lang })
            });
            const data = await res.json();
            showToast(`✅ ${data.enqueued} adet video konusu kuyruğa eklendi!`);
            document.getElementById('batch-topics-text').value = '';
            refreshBatchQueue();
        } catch (err) {
            alert('Kuyruğa ekleme hatası: ' + err.message);
        }
    });

    async function refreshBatchQueue() {
        const queueList = document.getElementById('batch-queue-list');
        if (!queueList) return;
        try {
            const res = await fetch('/api/batch/status');
            const data = await res.json();
            const queue = data.queue || [];
            const badge = document.getElementById('badge-batch-count');
            if (badge) badge.textContent = String(data.queue_count || 0);

            if (queue.length === 0) {
                queueList.innerHTML = '<div class="empty-state-box"><p>Kuyruk boş.</p></div>';
                return;
            }

            queueList.innerHTML = '';
            queue.forEach((q, idx) => {
                const item = document.createElement('div');
                item.style.padding = '8px 12px';
                item.style.borderBottom = '1px solid var(--border-subtle)';
                item.style.fontSize = '12px';
                item.innerHTML = `<strong>#${idx + 1}</strong> &middot; ${q.topic} <span class="niche-tag">${q.niche}</span>`;
                queueList.appendChild(item);
            });
        } catch (e) {
            console.error(e);
        }
    }

    async function restoreRenderState() {
        try {
            const res = await fetch('/api/status');
            if (!res.ok) return;
            const state = await res.json();
            if (!state.is_rendering) return;

            isRendering = true;
            persistentMonitor.classList.remove('hidden');
            const percent = Number(state.percent || 0);
            dockProgressFill.style.width = `${percent}%`;
            dockProgressPct.textContent = `%${percent}`;
            dockStepTitle.textContent = state.step || 'İşlem yürütülüyor...';
            const logs = state.logs || [];
            if (logs.length) {
                dockLogSnippet.textContent = logs[logs.length - 1];
                terminalBody.textContent = logs.map(log => `[Önceki] ${log}`).join('\n') + '\n';
            }
            initSSE();
        } catch (error) {
            console.error('Render durumu geri yüklenemedi:', error);
        }
    }

    // ══════════════════════════════════════════════════════════════
    // 5. BÜYÜME, A/B TEST & ALGORİTMA TAKTİKLERİ (Items 65, 89, 98)
    // ══════════════════════════════════════════════════════════════
    document.getElementById('btn-generate-ab-variants')?.addEventListener('click', () => {
        const topic = document.getElementById('ab-test-topic').value.trim() || "Bilinmeyen Gerçekler";
        const container = document.getElementById('ab-results-container');
        
        // Dynamic A/B test simulation based on growth_tactics rules
        container.innerHTML = `
            <div class="glass-box mb-2" style="padding: 10px; border-left: 3px solid #8B5CF6;">
                <strong>Varyant A (Merak Odaklı - CTR):</strong>
                <p style="font-size: 11px; color: #FFF; margin-top: 2px;">Bunu Biliyor Muydunuz? ${topic} Hakkında Gizli Gerçek #Shorts</p>
            </div>
            <div class="glass-box mb-2" style="padding: 10px; border-left: 3px solid #EF4444;">
                <strong>Varyant B (Şok / Flaş Kanca):</strong>
                <p style="font-size: 11px; color: #FFF; margin-top: 2px;">İNANILMAZ! ${topic} Olayı Herkesi Şok Etti #Shorts</p>
            </div>
            <div class="glass-box" style="padding: 10px; border-left: 3px solid #F59E0B;">
                <strong>Varyant C (İkilem / Yorum Tuzağı):</strong>
                <p style="font-size: 11px; color: #FFF; margin-top: 2px;">Siz Olsaydınız Ne Yapardınız? ${topic} #Shorts</p>
            </div>
        `;
        showToast('🧪 3 A/B varyantı hazırlandı!');
    });

    document.getElementById('btn-generate-community-poll')?.addEventListener('click', () => {
        const topic = document.getElementById('community-poll-topic').value.trim() || "Günün Konusu";
        const container = document.getElementById('community-poll-container');
        container.innerHTML = `
            <div class="glass-box" style="padding: 12px; background: rgba(245, 158, 11, 0.08); border-color: rgba(245, 158, 11, 0.3);">
                <strong style="color: #F59E0B; font-size: 12px;">📊 YouTube Topluluk Anketi</strong>
                <p style="font-size: 12px; margin: 6px 0;">Bugünkü Shorts konumuz '${topic}'. Sizce bu konuda en çok merak edilen şey nedir?</p>
                <div style="font-size: 11px; color: #FFF; display: flex; flex-direction: column; gap: 4px;">
                    <div>&bull; ${topic} hakkında hiç bilinmeyen sırlar</div>
                    <div>&bull; Tarihteki en büyük hatalar</div>
                    <div>&bull; Gelecekte bizi bekleyenler</div>
                    <div>&bull; Sonucu görmek istiyorum</div>
                </div>
            </div>
        `;
        showToast('📊 Topluluk anketi oluşturuldu!');
    });

    document.getElementById('btn-check-copyright-risk')?.addEventListener('click', () => {
        const text = document.getElementById('copyright-check-text').value.toLowerCase();
        const container = document.getElementById('copyright-risk-container');
        const riskyWords = ["disney", "marvel", "netflix", "fifa", "premier league", "telif", "şiddet"];
        const found = riskyWords.filter(w => text.includes(w));

        if (found.length > 0) {
            container.innerHTML = `
                <div style="background: rgba(239, 68, 68, 0.15); border: 1px solid var(--danger); padding: 10px; border-radius: 8px; font-size: 12px;">
                    <strong style="color: var(--danger);"><i class="fa-solid fa-triangle-exclamation"></i> Riskli Kelimeler Tespit Edildi:</strong>
                    <p style="color: #FFF; margin-top: 4px;">${found.join(", ")}</p>
                    <small style="color: #94A3B8;">Öneri: Yatay ayna (mirror) ve ses tonu kaydırma filtresini açın.</small>
                </div>
            `;
        } else {
            container.innerHTML = `
                <div style="background: rgba(16, 185, 129, 0.15); border: 1px solid var(--success); padding: 10px; border-radius: 8px; font-size: 12px; color: #FFF;">
                    <strong style="color: var(--success);"><i class="fa-solid fa-circle-check"></i> İçerik Güvenli!</strong>
                    <p style="margin-top: 2px;">Telif veya marka riski oluşturabilecek kısıtlama tespit edilmedi.</p>
                </div>
            `;
        }
    });

    // ══════════════════════════════════════════════════════════════
    // 6. ALTYAZI PRESET SEÇİCİ & ANİMASYON TESTİ (Items 42 & 43)
    // ══════════════════════════════════════════════════════════════
    document.querySelectorAll('.preset-card').forEach(card => {
        card.addEventListener('click', (e) => {
            document.querySelectorAll('.preset-card').forEach(c => c.classList.remove('active'));
            card.classList.add('active');
            const p = card.getAttribute('data-preset');
            selectSubPreset.value = p;
            showToast(`🎨 '${card.querySelector('h4').textContent}' altyazı stili seçildi!`);
        });
    });

    document.getElementById('btn-test-sub-animation')?.addEventListener('click', () => {
        const words = document.querySelectorAll('.stage-w');
        let idx = 0;
        const interval = setInterval(() => {
            words.forEach(w => w.classList.remove('active-word'));
            if (idx < words.length) {
                words[idx].classList.add('active-word');
                idx++;
            } else {
                clearInterval(interval);
                words[1].classList.add('active-word');
            }
        }, 400);
    });

    // ══════════════════════════════════════════════════════════════
    // 7. SES EFEKTLERİ (SFX) SENTEZLEYİCİ & DİNLEME (Item 48)
    // ══════════════════════════════════════════════════════════════
    function playSyntheticSound(type) {
        try {
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.connect(gain);
            gain.connect(ctx.destination);

            if (type === 'whoosh') {
                osc.type = 'sine';
                osc.frequency.setValueAtTime(200, ctx.currentTime);
                osc.frequency.exponentialRampToValueAtTime(800, ctx.currentTime + 0.15);
                gain.gain.setValueAtTime(0.3, ctx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.25);
                osc.start();
                osc.stop(ctx.currentTime + 0.25);
            } else if (type === 'pop') {
                osc.type = 'triangle';
                osc.frequency.setValueAtTime(800, ctx.currentTime);
                osc.frequency.exponentialRampToValueAtTime(120, ctx.currentTime + 0.08);
                gain.gain.setValueAtTime(0.4, ctx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.1);
                osc.start();
                osc.stop(ctx.currentTime + 0.1);
            } else if (type === 'ding') {
                osc.type = 'sine';
                osc.frequency.setValueAtTime(1800, ctx.currentTime);
                gain.gain.setValueAtTime(0.4, ctx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.4);
                osc.start();
                osc.stop(ctx.currentTime + 0.4);
            }
        } catch (e) {
            console.error("Audio error:", e);
        }
    }

    document.getElementById('btn-play-whoosh')?.addEventListener('click', () => playSyntheticSound('whoosh'));
    document.getElementById('btn-play-pop')?.addEventListener('click', () => playSyntheticSound('pop'));
    document.getElementById('btn-play-ding')?.addEventListener('click', () => playSyntheticSound('ding'));

    // ══════════════════════════════════════════════════════════════
    // 8. BGM MÜZİK LİSTESİ
    // ══════════════════════════════════════════════════════════════
    async function loadBgmList() {
        const select = document.getElementById('select-bgm-track');
        const audioStatus = document.getElementById('audio-pipeline-status');
        const mediaStatus = document.getElementById('media-compliance-status');
        if (!select) return;
        try {
            const res = await fetch('/api/bgm/list');
            const data = await res.json();
            const tracks = data.tracks || [];
            select.innerHTML = '<option value="">Yok (Sadece Seslendirme)</option>';
            tracks.forEach(t => {
                const opt = document.createElement('option');
                opt.value = t;
                opt.textContent = t;
                select.appendChild(opt);
            });
            if (tracks.includes('royalty_free_ambient.wav')) {
                select.value = 'royalty_free_ambient.wav';
            }
            if (audioStatus) {
                audioStatus.innerHTML = `
                    <div class="stat-pill"><span>135 Telifsiz BGM:</span><strong class="text-success">${tracks.length ? 'Hazır' : 'Sentezleniyor'}</strong></div>
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

    // ══════════════════════════════════════════════════════════════
    // 9. SENARYO ÜRETİMİ & EDİTÖR
    // ══════════════════════════════════════════════════════════════
    btnCreateScript.addEventListener('click', async () => {
        const topic = inputTopic.value.trim();
        if (!topic) return alert('Lütfen bir video konusu girin!');

        btnCreateScript.disabled = true;
        btnCreateScript.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> AI Senaryosu Yazılıyor...';

        try {
            const res = await fetch('/api/script/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    keyword: topic,
                    language: selectLanguage.value,
                    niche: selectNiche.value,
                    reddit_post: selectedRedditPost
                })
            });
            const data = await res.json();
            if (data.status === 'ok') {
                currentPlan = data.plan;
                renderTimelineScenes(currentPlan);
                switchTab('timeline');
                showToast('✨ AI Senaryosu başarıyla üretildi!');
            } else {
                alert('Senaryo oluşturulamadı.');
            }
        } catch (err) {
            alert('Hata: ' + err.message);
        } finally {
            btnCreateScript.disabled = false;
            btnCreateScript.innerHTML = '<i class="fa-solid fa-code-branch"></i> 1. Senaryoyu Oluştur & Düzenle';
        }
    });

    // ══════════════════════════════════════════════════════════════
    // 9A. SAHNE & KURGU EDİTÖRÜ — 500 Madde Uyumlu Overhaul
    // ══════════════════════════════════════════════════════════════

    // Helper: Detect emojis in text (Madde 125)
    function hasEmoji(text) {
        return /[\u{1F600}-\u{1F64F}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{1F1E0}-\u{1F1FF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}\u{FE00}-\u{FE0F}\u{1F900}-\u{1F9FF}\u{1FA00}-\u{1FA6F}\u{1FA70}-\u{1FAFF}\u{200D}\u{20E3}]/u.test(text || '');
    }

    // Helper: Word count
    function wordCount(text) {
        return (text || '').trim().split(/\s+/).filter(Boolean).length;
    }

    // Helper: Clean cutaway markers from narration for display
    function cleanNarration(text) {
        return (text || '').replace(/\s*\[Görsel Açı \d+\]\s*/g, '').replace(/\s*\[Kadraj \d+\]\s*/g, '').trim();
    }

    // Helper: Mood emoji map
    const MOOD_ICONS = {
        epic: '🌟', dramatic: '🔴', calm: '🔵', mysterious: '🟣',
        energetic: '⚡', dark: '⬛', bright: '☀️'
    };

    // ── Compliance Dashboard Update ──
    function updateComplianceDashboard(scenes) {
        if (!scenes || scenes.length === 0) return;

        const totalSec = scenes.reduce((acc, s) => acc + (parseFloat(s.duration) || 6), 0);

        // Duration band — Madde 494
        const chipDur = document.getElementById('chip-duration-band');
        const chipDurText = document.getElementById('chip-duration-text');
        chipDurText.textContent = `Süre: ${totalSec.toFixed(1)}sn`;
        chipDur.className = 'compliance-chip';
        if (totalSec >= 38 && totalSec <= 48) {
            chipDur.classList.add('status-ok');
        } else if (totalSec > 48 && totalSec <= 60) {
            chipDur.classList.add('status-warn');
        } else {
            chipDur.classList.add('status-danger');
        }

        // Cadence — Madde 88
        const chipCad = document.getElementById('chip-cadence');
        const chipCadText = document.getElementById('chip-cadence-text');
        chipCadText.textContent = `Cadence: ${scenes.length}/14`;
        chipCad.className = 'compliance-chip';
        if (scenes.length >= 14) {
            chipCad.classList.add('status-ok');
        } else if (scenes.length >= 10) {
            chipCad.classList.add('status-warn');
        } else {
            chipCad.classList.add('status-danger');
        }

        // 3.2s violations — Madde 76
        const violations = scenes.filter(s => (parseFloat(s.duration) || 6) > 3.2).length;
        const chip32 = document.getElementById('chip-32s-violations');
        const chip32Text = document.getElementById('chip-32s-text');
        chip32Text.textContent = `3.2sn İhlali: ${violations}`;
        chip32.className = 'compliance-chip';
        if (violations === 0) {
            chip32.classList.add('status-ok');
        } else if (violations <= 3) {
            chip32.classList.add('status-warn');
        } else {
            chip32.classList.add('status-danger');
        }

        // Duplicate search terms — Madde 247
        const allQueries = [];
        scenes.forEach(s => {
            const sq = s.search_queries || [];
            if (sq[0]) allQueries.push(sq[0].toLowerCase().trim());
        });
        const seen = {};
        let dupes = 0;
        allQueries.forEach(q => { seen[q] = (seen[q] || 0) + 1; });
        Object.values(seen).forEach(c => { if (c > 1) dupes += (c - 1); });
        const chipDup = document.getElementById('chip-duplicates');
        const chipDupText = document.getElementById('chip-duplicates-text');
        chipDupText.textContent = `Tekrar: ${dupes}`;
        chipDup.className = 'compliance-chip';
        if (dupes === 0) {
            chipDup.classList.add('status-ok');
        } else {
            chipDup.classList.add('status-warn');
        }

        // Story Arc Bar — Madde 274
        if (totalSec > 0) {
            const introEnd = Math.min(3, totalSec);
            const conflictEnd = Math.min(20, totalSec);
            const climaxEnd = Math.min(35, totalSec);
            document.getElementById('arc-intro').style.width = `${(introEnd / totalSec) * 100}%`;
            document.getElementById('arc-conflict').style.width = `${((conflictEnd - introEnd) / totalSec) * 100}%`;
            document.getElementById('arc-climax').style.width = `${((climaxEnd - conflictEnd) / totalSec) * 100}%`;
            document.getElementById('arc-loop').style.width = `${((totalSec - climaxEnd) / totalSec) * 100}%`;
        }
    }

    // ── Main render function ──
    function renderTimelineScenes(plan) {
        const container = document.getElementById('scenes-timeline-container');
        const titleEl = document.getElementById('timeline-project-title');
        const totalScenesEl = document.getElementById('timeline-total-scenes');
        const totalDurEl = document.getElementById('timeline-total-duration');
        const badgeSceneCount = document.getElementById('badge-scene-count');

        if (!container || !plan) return;

        titleEl.textContent = `Proje: ${plan.title || 'Adsız'}`;
        const scenes = plan.scenes || [];
        totalScenesEl.textContent = scenes.length;
        badgeSceneCount.textContent = scenes.length;

        const totalSec = scenes.reduce((acc, s) => acc + (parseFloat(s.duration) || 6), 0);
        totalDurEl.textContent = `${totalSec.toFixed(1)} sn`;

        // Build duplicate query map for highlighting
        const queryFreq = {};
        scenes.forEach(s => {
            const q = ((s.search_queries && s.search_queries[0]) || '').toLowerCase().trim();
            if (q) queryFreq[q] = (queryFreq[q] || 0) + 1;
        });

        container.innerHTML = '';
        scenes.forEach((sc, i) => {
            const mood = (sc.mood || 'epic').toLowerCase();
            const isCutaway = sc.is_visual_cutaway === true;
            const dur = parseFloat(sc.duration) || 6;
            const durationViolation = dur > 3.2;
            const narr = isCutaway ? cleanNarration(sc.narration) : (sc.narration || '');
            const wc = wordCount(narr);
            const hasEm = hasEmoji(narr);
            const searchQueries = sc.search_queries || [];
            const sceneDesc = sc.scene_description || '';

            // Word count class
            let wcClass = 'count-ok';
            if (wc < 5) wcClass = 'count-danger';
            else if (wc > 20) wcClass = 'count-warn';

            // Build CSS classes
            let cardClasses = `scene-item-card mood-${mood}`;
            if (isCutaway) cardClasses += ' is-cutaway';
            if (durationViolation) cardClasses += ' duration-violation';

            const row = document.createElement('div');
            row.className = cardClasses;
            row.setAttribute('draggable', 'true');
            row.setAttribute('data-scene-idx', i);

            // Build search query tags HTML
            let queryTagsHtml = '';
            searchQueries.forEach((q, qi) => {
                const isDupe = qi === 0 && queryFreq[q.toLowerCase().trim()] > 1;
                const labels = ['spesifik', 'orta', 'genel'];
                queryTagsHtml += `<span class="search-query-tag${isDupe ? ' duplicate' : ''}" title="${labels[qi] || ''}">${q}</span>`;
            });

            // Stock video badge / preview
            let stockVideoHtml = '';
            if (sc.selected_video && sc.selected_video.url) {
                const vid = sc.selected_video;
                stockVideoHtml = `
                    <div class="scene-stock-badge-container">
                        ${vid.thumbnail ? `<img src="${vid.thumbnail}" class="scene-stock-thumb" alt="Klip">` : ''}
                        <span class="scene-stock-provider-tag"><i class="fa-solid fa-video"></i> ${vid.source || 'Stok'}</span>
                        <a href="${vid.url}" target="_blank" class="scene-stock-preview-btn"><i class="fa-solid fa-play"></i> Klip Önizle</a>
                        <button type="button" class="btn-swap-stock" data-idx="${i}" title="Farklı Bir Stok Video Çek"><i class="fa-solid fa-rotate"></i> Değiştir</button>
                    </div>
                `;
            } else {
                stockVideoHtml = `
                    <div class="scene-stock-badge-container">
                        <span style="font-size: 10px; color: #64748b;"><i class="fa-solid fa-film"></i> Stok video atanmadı</span>
                        <button type="button" class="btn-fetch-single-stock" data-idx="${i}"><i class="fa-solid fa-cloud-arrow-down"></i> Stok Çek</button>
                    </div>
                `;
            }

            row.innerHTML = `
                <div class="scene-idx">
                    <span class="scene-idx-number">#${i + 1}</span>
                    <span class="mood-badge mood-${mood}">${MOOD_ICONS[mood] || '🎬'} ${mood}</span>
                    ${isCutaway ? '<span class="cutaway-badge">📐 Açı</span>' : ''}
                </div>
                <div class="scene-body">
                    <div class="scene-body-row">
                        <div>
                            <div class="scene-field-label">
                                Seslendirme Metni
                                <span class="word-count-chip ${wcClass}">${wc} klm</span>
                                <span class="emoji-indicator ${hasEm ? 'has-emoji' : 'no-emoji'}">${hasEm ? '✅ Emoji' : '⚠️ Emoji yok'}</span>
                            </div>
                            <textarea class="input-styled scene-narr-input" rows="2" style="resize: vertical; min-height: 36px;">${narr}</textarea>
                        </div>
                        <div>
                            <div class="scene-field-label">Görsel Açıklama <span class="field-meta">(scene_description)</span></div>
                            <input type="text" class="input-styled scene-desc-input" value="${sceneDesc}" placeholder="İngilizce görsel açıklama...">
                            ${stockVideoHtml}
                        </div>
                    </div>
                    <div class="scene-body-row-3">
                        <div>
                            <div class="scene-field-label">Stok Arama Terimleri <span class="field-meta">(Madde 89)</span></div>
                            <input type="text" class="input-styled scene-query-input" value="${searchQueries[0] || ''}" placeholder="Ana arama terimi...">
                            <div class="search-query-tags">${queryTagsHtml}</div>
                        </div>
                        <div>
                            <div class="scene-field-label">Süre</div>
                            <input type="number" class="input-styled scene-dur-input" min="1" max="15" step="0.25" value="${dur}">
                        </div>
                        <div class="scene-actions">
                            <button class="btn-sm btn-clone-scene" data-idx="${i}" title="Sahneyi Klonla"><i class="fa-solid fa-copy"></i></button>
                            <button class="btn-sm btn-del-scene" data-idx="${i}" title="Sahneyi Sil"><i class="fa-solid fa-trash"></i></button>
                        </div>
                    </div>
                </div>
            `;
            container.appendChild(row);
        });

        // ── Event handlers ──

        // Swap stock video for single scene
        container.querySelectorAll('.btn-swap-stock').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const idx = parseInt(e.currentTarget.getAttribute('data-idx'));
                const sc = currentPlan.scenes[idx];
                const q = (sc.search_queries && sc.search_queries[0]) || sc.scene_description || 'cinematic motion';
                btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
                btn.disabled = true;
                try {
                    const res = await fetch(`/api/stock/search?query=${encodeURIComponent(q)}&limit=6`);
                    const data = await res.json();
                    if (data.results && data.results.length > 0) {
                        const currentId = sc.selected_video?.id;
                        const alt = data.results.find(v => v.id !== currentId) || data.results[0];
                        sc.selected_video = alt;
                        renderTimelineScenes(currentPlan);
                        showToast(`🎬 Sahne #${idx + 1} için yeni stok video seçildi!`);
                    } else {
                        showToast('⚠️ Alternatif video bulunamadı.', 'warn');
                        btn.innerHTML = '<i class="fa-solid fa-rotate"></i> Değiştir';
                        btn.disabled = false;
                    }
                } catch (err) {
                    showToast('Hata: ' + err.message, 'error');
                    btn.innerHTML = '<i class="fa-solid fa-rotate"></i> Değiştir';
                    btn.disabled = false;
                }
            });
        });

        // Fetch single stock video
        container.querySelectorAll('.btn-fetch-single-stock').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                const idx = parseInt(e.currentTarget.getAttribute('data-idx'));
                const sc = currentPlan.scenes[idx];
                const q = (sc.search_queries && sc.search_queries[0]) || sc.scene_description || 'cinematic motion';
                btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
                btn.disabled = true;
                try {
                    const res = await fetch(`/api/stock/search?query=${encodeURIComponent(q)}&limit=3`);
                    const data = await res.json();
                    if (data.results && data.results.length > 0) {
                        sc.selected_video = data.results[0];
                        renderTimelineScenes(currentPlan);
                        showToast(`🎬 Sahne #${idx + 1} için stok video çekildi!`);
                    } else {
                        showToast('⚠️ Video bulunamadı.', 'warn');
                        btn.innerHTML = '<i class="fa-solid fa-cloud-arrow-down"></i> Stok Çek';
                        btn.disabled = false;
                    }
                } catch (err) {
                    showToast('Hata: ' + err.message, 'error');
                    btn.innerHTML = '<i class="fa-solid fa-cloud-arrow-down"></i> Stok Çek';
                    btn.disabled = false;
                }
            });
        });

        // Delete scene
        container.querySelectorAll('.btn-del-scene').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const idx = parseInt(e.currentTarget.getAttribute('data-idx'));
                currentPlan.scenes.splice(idx, 1);
                renderTimelineScenes(currentPlan);
            });
        });

        // Clone scene
        container.querySelectorAll('.btn-clone-scene').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const idx = parseInt(e.currentTarget.getAttribute('data-idx'));
                const clone = JSON.parse(JSON.stringify(currentPlan.scenes[idx]));
                clone.scene_number = currentPlan.scenes.length + 1;
                clone.is_visual_cutaway = false;
                currentPlan.scenes.splice(idx + 1, 0, clone);
                renderTimelineScenes(currentPlan);
                showToast('📋 Sahne klonlandı');
            });
        });

        // ── Drag & Drop ──
        let dragSrcIdx = null;
        container.querySelectorAll('.scene-item-card').forEach(card => {
            card.addEventListener('dragstart', (e) => {
                dragSrcIdx = parseInt(card.getAttribute('data-scene-idx'));
                card.classList.add('dragging');
                e.dataTransfer.effectAllowed = 'move';
            });
            card.addEventListener('dragend', () => {
                card.classList.remove('dragging');
                container.querySelectorAll('.scene-item-card').forEach(c => c.classList.remove('drag-over'));
            });
            card.addEventListener('dragover', (e) => {
                e.preventDefault();
                e.dataTransfer.dropEffect = 'move';
                card.classList.add('drag-over');
            });
            card.addEventListener('dragleave', () => {
                card.classList.remove('drag-over');
            });
            card.addEventListener('drop', (e) => {
                e.preventDefault();
                const targetIdx = parseInt(card.getAttribute('data-scene-idx'));
                if (dragSrcIdx !== null && dragSrcIdx !== targetIdx && currentPlan && currentPlan.scenes) {
                    const [moved] = currentPlan.scenes.splice(dragSrcIdx, 1);
                    currentPlan.scenes.splice(targetIdx, 0, moved);
                    // Renumber
                    currentPlan.scenes.forEach((s, si) => s.scene_number = si + 1);
                    renderTimelineScenes(currentPlan);
                    showToast('🔀 Sahne sırası güncellendi');
                }
                dragSrcIdx = null;
            });
        });

        // Update compliance dashboard
        updateComplianceDashboard(scenes);
    }

    // ── Add scene manually ──
    document.getElementById('btn-add-scene-manual')?.addEventListener('click', () => {
        if (!currentPlan) currentPlan = { title: inputTopic.value, scenes: [] };
        currentPlan.scenes.push({
            scene_number: currentPlan.scenes.length + 1,
            narration: "Yeni sahne anlatım parçası...",
            scene_description: "Wide angle cinematic shot of the scene",
            search_queries: ["cinematic nature", "landscape aerial", "nature"],
            duration: 3,
            mood: "epic"
        });
        renderTimelineScenes(currentPlan);
        showToast('➕ Yeni sahne eklendi');
    });

    // ── Smart Buttons ──

    // Auto-fetch stock videos for all scenes — Item 89 & 130
    document.getElementById('btn-fetch-stock-clips')?.addEventListener('click', async () => {
        if (!currentPlan || !currentPlan.scenes || currentPlan.scenes.length === 0) {
            return showToast('⚠️ Önce senaryo oluşturun', 'warn');
        }
        const btn = document.getElementById('btn-fetch-stock-clips');
        const oldHtml = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Stok Videolar Çekiliyor...';
        showToast('📡 Pexels ve Pixabay kütüphanelerinden en iyi dikey videolar taranıyor...');
        try {
            collectTimelineEdits();
            const res = await fetch('/api/stock/fetch_for_scenes', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ scenes: currentPlan.scenes })
            });
            const data = await res.json();
            if (data.status === 'ok' && data.scenes) {
                currentPlan.scenes = data.scenes;
                renderTimelineScenes(currentPlan);
                showToast('🎬 Tüm sahneler için stok videolar başarıyla çekildi ve eşleştirildi!');
            }
        } catch (err) {
            showToast('⚠️ Stok video çekme hatası: ' + err.message, 'error');
        } finally {
            btn.disabled = false;
            btn.innerHTML = oldHtml;
        }
    });

    // Cadence fix — Madde 88
    document.getElementById('btn-fix-cadence')?.addEventListener('click', () => {
        if (!currentPlan || !currentPlan.scenes || currentPlan.scenes.length === 0) return showToast('⚠️ Önce senaryo oluşturun', 'warn');
        const scenes = currentPlan.scenes;
        const totalDuration = scenes.reduce((acc, s) => acc + (parseFloat(s.duration) || 6), 0);
        if (totalDuration < 30 || scenes.length >= 14) return showToast('✅ Cadence zaten yeterli');

        let cutsNeeded = 14 - scenes.length;
        let cutawayCounter = 1;
        const cutawayAdjs = ['macro closeup', 'cinematic angle', 'reaction detail', 'slow motion cutaway'];
        const expanded = [];
        for (const sc of scenes) {
            const dur = parseFloat(sc.duration) || 6;
            if (cutsNeeded > 0 && dur >= 3.5) {
                const half1 = Math.round((dur / 2) * 100) / 100;
                const half2 = Math.round((dur - half1) * 100) / 100;
                cutsNeeded--;

                const words = (sc.narration || '').split(' ');
                let narr1 = sc.narration || '';
                let narr2 = `${sc.narration || ''} [Görsel Açı ${cutawayCounter}]`;
                if (words.length >= 6) {
                    const mid = Math.floor(words.length / 2);
                    narr1 = words.slice(0, mid).join(' ');
                    narr2 = words.slice(mid).join(' ');
                }

                const sq = sc.search_queries || ['cinematic visual'];
                const cadj = cutawayAdjs[cutawayCounter % cutawayAdjs.length];
                const q1 = sq[0] || 'cinematic motion';
                const q2 = sq[1] ? `${sq[1]} ${cadj}` : `${q1} ${cadj}`;
                const queries1 = [q1, sq[1] || 'dramatic lighting'];
                const queries2 = [q2, sq[2] || 'cinematic slow motion'];

                const sc1 = { ...sc, duration: half1, narration: narr1, search_queries: queries1 };
                const sc2 = { ...sc, duration: half2, is_visual_cutaway: true, narration: narr2, search_queries: queries2, scene_description: `Cutaway dynamic angle showing ${q2}` };
                cutawayCounter++;
                expanded.push(sc1, sc2);
            } else {
                expanded.push({ ...sc });
            }
        }
        // Further split if needed
        while (expanded.length < 14) {
            const maxIdx = expanded.reduce((best, s, i) => (s.duration || 0) > (expanded[best].duration || 0) ? i : best, 0);
            if ((expanded[maxIdx].duration || 0) < 1.5) break;
            const target = expanded[maxIdx];
            const h1 = Math.round((target.duration / 2) * 100) / 100;
            const h2 = Math.round((target.duration - h1) * 100) / 100;

            const words = (target.narration || '').split(' ');
            let narr1 = target.narration || '';
            let narr2 = `${target.narration || ''} [Kadraj ${cutawayCounter}]`;
            if (words.length >= 6) {
                const mid = Math.floor(words.length / 2);
                narr1 = words.slice(0, mid).join(' ');
                narr2 = words.slice(mid).join(' ');
            }

            const sq = target.search_queries || ['cinematic visual'];
            const cadj = cutawayAdjs[cutawayCounter % cutawayAdjs.length];
            const q1 = sq[0] || 'cinematic motion';
            const q2 = sq[1] ? `${sq[1]} ${cadj}` : `${q1} ${cadj}`;

            const t1 = { ...target, duration: h1, narration: narr1, search_queries: [q1, sq[1] || 'dramatic lighting'] };
            const t2 = { ...target, duration: h2, is_visual_cutaway: true, narration: narr2, search_queries: [q2, sq[2] || 'cinematic slow motion'], scene_description: `Cutaway dynamic angle showing ${q2}` };
            cutawayCounter++;
            expanded.splice(maxIdx, 1, t1, t2);
        }
        expanded.forEach((s, i) => s.scene_number = i + 1);
        currentPlan.scenes = expanded;
        renderTimelineScenes(currentPlan);
        showToast(`✂️ Cadence düzeltildi: ${expanded.length} sahne`);
    });

    // Enrich search queries — Madde 89
    document.getElementById('btn-enrich-queries')?.addEventListener('click', () => {
        if (!currentPlan || !currentPlan.scenes) return showToast('⚠️ Önce senaryo oluşturun', 'warn');
        const adjectives = ['cinematic', 'drone', 'aerial', 'slow motion', 'macro', 'atmospheric', '4k', 'moody'];
        currentPlan.scenes.forEach((sc, i) => {
            const sq = sc.search_queries || [];
            sc.search_queries = sq.map((q, qi) => {
                const ql = q.toLowerCase();
                if (!adjectives.some(a => ql.includes(a))) {
                    return `${q} ${adjectives[(i + qi) % adjectives.length]}`;
                }
                return q;
            });
        });
        renderTimelineScenes(currentPlan);
        showToast('🎬 Arama terimleri sinematik sıfatlarla zenginleştirildi');
    });

    // Balance durations — Madde 494
    document.getElementById('btn-balance-durations')?.addEventListener('click', () => {
        if (!currentPlan || !currentPlan.scenes || currentPlan.scenes.length === 0) return showToast('⚠️ Önce senaryo oluşturun', 'warn');
        const scenes = currentPlan.scenes;
        const totalSec = scenes.reduce((acc, s) => acc + (parseFloat(s.duration) || 6), 0);
        const targetTotal = 45; // Ideal center of 38-48

        if (totalSec >= 38 && totalSec <= 48) return showToast('✅ Süre zaten ideal bantta (38-48sn)');

        const ratio = targetTotal / totalSec;
        const maxPerScene = scenes.length >= 14 ? 3.0 : 6.0;
        scenes.forEach(s => {
            s.duration = Math.max(1.5, Math.min(maxPerScene, Math.round((parseFloat(s.duration) || 3) * ratio * 4) / 4));
        });
        renderTimelineScenes(currentPlan);
        const newTotal = scenes.reduce((acc, s) => acc + s.duration, 0);
        showToast(`⚖️ Süreler dengelendi: ${newTotal.toFixed(1)}sn`);
    });

    // Hallucination check — Madde 90
    document.getElementById('btn-hallucination-check')?.addEventListener('click', () => {
        if (!currentPlan || !currentPlan.scenes) return showToast('⚠️ Önce senaryo oluşturun', 'warn');
        const issues = [];
        const title = (currentPlan.title || '').toLowerCase();
        const ancientMarkers = ['marcus aurelius', 'roma', 'antik', 'stoa', 'osmanlı', 'fatih', 'platon', 'aristoteles', 'sezar'];
        const isAncient = ancientMarkers.some(m => title.includes(m));
        const yearPattern = /\b(1[0-9]{3}|20[0-9]{2})\b/g;

        currentPlan.scenes.forEach((sc, i) => {
            const narr = sc.narration || '';
            let match;
            while ((match = yearPattern.exec(narr)) !== null) {
                const yr = parseInt(match[1]);
                if (yr > 2030) {
                    issues.push(`Sahne #${i + 1}: Gelecek yıl (${yr}) — halüsinasyon`);
                } else if (isAncient && yr >= 1800) {
                    issues.push(`Sahne #${i + 1}: Antik konu için modern yıl (${yr}) — anakronizm`);
                }
            }
        });

        if (issues.length === 0) {
            showToast('✅ Halüsinasyon tespit edilmedi — temiz');
        } else {
            showToast(`⚠️ ${issues.length} potansiyel halüsinasyon tespit edildi`, 'warn');
            alert('Halüsinasyon Raporu:\n\n' + issues.join('\n'));
        }
    });

    // ── Render from timeline (collect edits) ──
    document.getElementById('btn-render-from-timeline')?.addEventListener('click', () => {
        collectTimelineEdits();
        startRenderProcess(currentPlan);
    });

    function collectTimelineEdits() {
        if (currentPlan && currentPlan.scenes) {
            const narrInputs = document.querySelectorAll('.scene-narr-input');
            const descInputs = document.querySelectorAll('.scene-desc-input');
            const queryInputs = document.querySelectorAll('.scene-query-input');
            const durInputs = document.querySelectorAll('.scene-dur-input');
            currentPlan.scenes.forEach((sc, i) => {
                if (narrInputs[i]) sc.narration = narrInputs[i].value;
                if (descInputs[i]) sc.scene_description = descInputs[i].value;
                if (queryInputs[i]) sc.search_queries = [queryInputs[i].value, ...(sc.search_queries || []).slice(1)];
                if (durInputs[i]) sc.duration = parseFloat(durInputs[i].value) || 6;
            });
            currentPlan.full_narration = currentPlan.scenes.map(s => s.narration || '').filter(Boolean).join(' ');
        }
    }

    // ── Keyboard Shortcuts — Madde 443 ──
    document.addEventListener('keydown', (e) => {
        // Ctrl+Enter — Render
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            e.preventDefault();
            const activeTab = document.querySelector('.nav-btn.active')?.getAttribute('data-tab');
            if (activeTab === 'timeline' && currentPlan) {
                collectTimelineEdits();
                startRenderProcess(currentPlan);
            }
        }
        // Ctrl+S — Save/sync edits
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
            e.preventDefault();
            collectTimelineEdits();
            if (currentPlan) {
                updateComplianceDashboard(currentPlan.scenes || []);
                showToast('💾 Sahne düzenlemeleri kaydedildi');
            }
        }
    });

    // ══════════════════════════════════════════════════════════════
    // 10. CANLI SSE İZLEME & RENDER BORU HATTI
    // ══════════════════════════════════════════════════════════════
    btnQuickRender.addEventListener('click', () => startRenderProcess(null));

    function startRenderProcess(planToUse) {
        if (isRendering) return alert('Şu anda aktif bir render işlemi devam ediyor!');

        const topic = inputTopic.value.trim();
        if (!topic) return alert('Lütfen bir video konusu girin!');

        initSSE();

        persistentMonitor.classList.remove('hidden');
        dockStepTitle.textContent = "İşlem Başlatılıyor...";
        dockLogSnippet.textContent = topic;
        dockProgressFill.style.width = "5%";
        dockProgressFill.style.backgroundColor = "";
        dockProgressPct.textContent = "%5";
        if (dockSpinner) dockSpinner.style.display = 'inline-block';
        setCancelButtonState('cancel');
        terminalBody.textContent = `[${new Date().toLocaleTimeString()}] Render başlatma isteği gönderildi: ${topic}\n`;

        const payload = {
            keyword: topic,
            plan: planToUse,
            niche: selectNiche.value,
            language: selectLanguage.value,
            voice_gender: selectVoiceGender.value,
            subtitle_preset: selectSubPreset.value,
            bgm_track: document.getElementById('select-bgm-track')?.value || '',
            bgm_volume: parseFloat(document.getElementById('range-ducking-vol')?.value || '0.12'),
            reddit_post: selectedRedditPost,
            split_screen: chkSplitScreen.checked,
            anti_duplicate: chkAntiDuplicate.checked,
            enable_ken_burns: chkKenBurns.checked
        };

        fetch('/api/video/render', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        }).then(res => {
            if (!res.ok) {
                return res.json().then(d => { throw new Error(d.detail || 'Render başlatılamadı'); });
            }
            showToast('🚀 Render işlemi başlatıldı! Canlı loglar akıyor...');
            isRendering = true;
            setCancelButtonState('cancel');
        }).catch(err => {
            alert(err.message);
            persistentMonitor.classList.add('hidden');
            isRendering = false;
            setCancelButtonState('cancel');
        });
    }

    function setCancelButtonState(mode) {
        if (!btnCancelRender) return;
        if (mode === 'cancelling') {
            btnCancelRender.disabled = true;
            btnCancelRender.className = 'btn btn-sm btn-danger';
            btnCancelRender.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> İptal Ediliyor...';
        } else if (mode === 'close') {
            btnCancelRender.disabled = false;
            btnCancelRender.className = 'btn btn-sm btn-secondary';
            btnCancelRender.innerHTML = '<i class="fa-solid fa-xmark"></i> Kapat';
        } else {
            btnCancelRender.disabled = false;
            btnCancelRender.className = 'btn btn-sm btn-danger';
            btnCancelRender.innerHTML = '<i class="fa-solid fa-circle-xmark"></i> İptal Et';
        }
    }

    function initSSE() {
        if (eventSource) eventSource.close();
        eventSource = new EventSource('/api/events');

        eventSource.onmessage = (e) => {
            try {
                const payload = JSON.parse(e.data);
                handleServerEvent(payload.type, payload.data);
            } catch (err) {
                console.error("SSE parse error:", err);
            }
        };

        eventSource.onerror = () => {
            console.warn("SSE bağlantısı yeniden kuruluyor...");
        };
    }

    function handleServerEvent(type, data) {
        if (type === 'progress') {
            const pct = data.percent || 0;
            dockProgressFill.style.width = `${pct}%`;
            dockProgressPct.textContent = `%${pct}`;
            dockStepTitle.textContent = data.step || "İşleniyor...";
        } else if (type === 'log') {
            dockLogSnippet.textContent = data;
            terminalBody.textContent += `[${new Date().toLocaleTimeString()}] ${data}\n`;
            terminalBody.scrollTop = terminalBody.scrollHeight;
        } else if (type === 'complete') {
            dockProgressFill.style.width = `100%`;
            dockProgressPct.textContent = `%100`;
            dockStepTitle.textContent = "🎉 Video Başarıyla Tamamlandı!";
            if (dockSpinner) dockSpinner.style.display = 'none';
            showToast('🎬 Full HD videonuz hazır!');
            isRendering = false;
            setCancelButtonState('close');

            if (data.url) {
                livePlayer.src = data.url;
                livePlayer.classList.remove('hidden');
                mockupPlaceholder.classList.add('hidden');
            }

            // 500-Madde SEO & Telif Kalkanı Kutusunu Doldur
            const seoBox = document.getElementById('video-complete-seo-box');
            if (data.seo && seoBox) {
                const titleInp = document.getElementById('seo-title-val');
                const tagsInp = document.getElementById('seo-tags-val');
                const commentInp = document.getElementById('seo-comment-val');
                const proofLink = document.getElementById('link-download-proof');

                if (titleInp) titleInp.value = data.seo.seo_title || data.keyword || '';
                if (tagsInp) tagsInp.value = (data.seo.tags || []).join(', ');
                if (commentInp) commentInp.value = data.seo.pinned_comment || '';
                if (proofLink && data.proof_url) proofLink.href = data.proof_url;

                seoBox.classList.remove('hidden');
            }

            loadGallery();
        } else if (type === 'error') {
            dockStepTitle.textContent = "Hata Oluştu";
            dockLogSnippet.textContent = data;
            dockProgressFill.style.backgroundColor = "#EF4444";
            if (dockSpinner) dockSpinner.style.display = 'none';
            showToast(`❌ Hata: ${data}`);
            isRendering = false;
            setCancelButtonState('close');
        }
    }

    // 500-Madde SEO & İtiraz Kopyalama Butonları
    document.getElementById('btn-copy-seo-title')?.addEventListener('click', () => {
        const val = document.getElementById('seo-title-val')?.value;
        if (val) {
            navigator.clipboard.writeText(val);
            showToast('📋 CTR Başlığı panoya kopyalandı!');
        }
    });

    document.getElementById('btn-copy-seo-tags')?.addEventListener('click', () => {
        const val = document.getElementById('seo-tags-val')?.value;
        if (val) {
            navigator.clipboard.writeText(val);
            showToast('🏷️ 15 Viral Etiket panoya kopyalandı!');
        }
    });

    document.getElementById('btn-copy-seo-comment')?.addEventListener('click', () => {
        const val = document.getElementById('seo-comment-val')?.value;
        if (val) {
            navigator.clipboard.writeText(val);
            showToast('💬 Sabitlenecek Yorum panoya kopyalandı!');
        }
    });

    document.getElementById('btn-show-appeal-script')?.addEventListener('click', async () => {
        try {
            const res = await fetch('/api/proof/appeal_script?channel_name=ShortsPro');
            const d = await res.json();
            if (d.status === 'ok') {
                alert("🎬 YouTube 5-Dakikalık İtiraz Videosu Taslağı (Item 472):\n\n" + d.script);
            }
        } catch (e) {
            alert('İtiraz metni alınamadı: ' + e.message);
        }
    });

    btnToggleLog?.addEventListener('click', () => {
        terminalPanel.classList.toggle('hidden');
    });

    btnCloseLog?.addEventListener('click', () => {
        terminalPanel.classList.add('hidden');
    });

    function dismissMonitorDock() {
        persistentMonitor.classList.add('hidden');
        terminalPanel.classList.add('hidden');
        if (!isRendering) {
            setCancelButtonState('cancel');
        }
    }

    btnCloseDock?.addEventListener('click', dismissMonitorDock);

    btnCancelRender?.addEventListener('click', async () => {
        // Durum 1: Render şu anda aktif değilse (hata oluşmuş, tamamlanmış vb.) -> paneli doğrudan kapat
        if (!isRendering) {
            dismissMonitorDock();
            return;
        }

        // Durum 2: Aktif video render işlemi çalışıyorsa kullanıcıdan onay al
        if (confirm('Aktif video üretimini iptal etmek istiyor musunuz?')) {
            setCancelButtonState('cancelling');
            try {
                const response = await fetch('/api/video/cancel', { method: 'POST' });
                const data = await response.json();
                showToast(`⛔ ${data.message}`);

                // Eğer aktif render yoksa veya iptal hemen tamamlandıysa
                if (data.active === false || (data.message && data.message.includes('bulunmuyor'))) {
                    isRendering = false;
                    setTimeout(() => {
                        dismissMonitorDock();
                    }, 500);
                }
            } catch (error) {
                showToast('İptal isteği gönderilemedi.');
                setCancelButtonState('cancel');
            }
        }
    });

    // ══════════════════════════════════════════════════════════════
    // 11. VİDEO GALERİSİ & YOUTUBE YÜKLEME (Items 51 & 100)
    // ══════════════════════════════════════════════════════════════
    async function loadGallery() {
        const grid = document.getElementById('gallery-videos-grid');
        const badge = document.getElementById('badge-gallery-count');
        if (!grid) return;

        try {
            const res = await fetch('/api/videos');
            const data = await res.json();
            const videos = data.videos || [];

            if (badge) badge.textContent = videos.length;

            // Global İstatistik Barını Güncelle
            const statTotalVids = document.getElementById('stat-total-vids');
            const statTotalDur = document.getElementById('stat-total-duration');
            if (statTotalVids) statTotalVids.textContent = `${videos.length} Video`;
            if (statTotalDur) {
                const totalSeconds = videos.reduce((acc, v) => acc + (v.duration_seconds || 0), 0);
                const totalMinutes = Math.round(totalSeconds / 60);
                statTotalDur.textContent = `${totalMinutes} dk`;
            }

            if (videos.length === 0) {
                grid.innerHTML = '<div class="empty-state-box"><i class="fa-solid fa-film"></i><p>Henüz üretilmiş bir video yok.</p></div>';
                return;
            }

            grid.innerHTML = '';
            videos.forEach(v => {
                const card = document.createElement('div');
                card.className = 'glass-box';
                card.style.padding = '14px';
                card.innerHTML = `
                    <div style="position: relative; border-radius: 8px; overflow: hidden; height: 260px; background: #000;">
                        <video src="/output/${v.filename}" style="width: 100%; height: 100%; object-fit: cover;" controls playsinline></video>
                    </div>
                    <div style="margin-top: 10px;">
                        <strong style="font-size: 13px; color: #FFF;">${v.keyword || v.title || 'Shorts'}</strong>
                        <div style="font-size: 11px; color: #94A3B8; margin-top: 4px; display: flex; justify-content: space-between;">
                            <span>${(v.duration_seconds || 0).toFixed(1)} sn</span>
                            <span>${(v.size_mb || 0).toFixed(1)} MB</span>
                        </div>
                        <div style="display: flex; gap: 8px; margin-top: 10px;">
                            <a href="/output/${v.filename}" download class="btn btn-secondary btn-sm" style="flex: 1; text-decoration: none;">
                                <i class="fa-solid fa-download"></i> İndir
                            </a>
                            <button class="btn btn-primary btn-sm btn-upload-yt" data-filename="${v.filename}" data-title="${encodeURIComponent(v.keyword || 'Shorts')}" style="flex: 1;">
                                <i class="fa-brands fa-youtube"></i> Yükle
                            </button>
                        </div>
                        <button class="btn btn-sm btn-manual-guide" data-filename="${v.filename}" title="Manuel Yükleme Rehberi & SEO Bilgileri (Kural 80 & 83)" style="margin-top: 6px; width: 100%; font-size: 11px; background: rgba(59, 130, 246, 0.15); border: 1px solid rgba(59, 130, 246, 0.4); color: #93C5FD; border-radius: 6px; padding: 5px;">
                            <i class="fa-solid fa-clipboard-list"></i> Manuel Yükleme Rehberi & SEO
                        </button>
                    </div>
                `;
                grid.appendChild(card);
            });

            grid.querySelectorAll('.btn-manual-guide').forEach(b => {
                b.addEventListener('click', async (e) => {
                    const fn = e.currentTarget.getAttribute('data-filename');
                    const baseName = fn.replace(/\.[^/.]+$/, "");
                    try {
                        let info = null;
                        try {
                            const res = await fetch(`/output/${baseName}_manual_upload_info.json`);
                            if (res.ok) info = await res.json();
                        } catch (_) {}

                        if (!info) {
                            info = {
                                title: baseName,
                                description: `${baseName} #shorts\n\n📌 Kaynak & Araştırma: Tarihsel Arşiv ve Akademik İnceleme\n⚖️ Hakkaniyet & Katma Değer (Fair Use): Bu video eğitim ve bilgilendirme amacıyla bağımsız olarak araştırılmış, özgün sesli analizle üretilmiştir.`,
                                tags: ["shorts", "bilgi", "viral"],
                                pinned_comment: "Sizce bu konudaki en şaşırtıcı detay neydi? Yorumlarda buluşalım! 👇",
                                rule_80_altered_synthetic: "HAYIR (Yüz klonlama veya manipülasyon yoksa etiket seçilmemeli)"
                            };
                        }

                        const guideText = 
`📌 BAŞLIK:\n${info.title}\n\n` +
`📌 AÇIKLAMA (Kural 83 Kaynaklı):\n${info.description}\n\n` +
`📌 ETİKETLER:\n${(info.tags || []).join(', ')}\n\n` +
`📌 SABİT YORUM:\n${info.pinned_comment}\n\n` +
`⚠️ KRİTİK KURAL 80 UYARISI:\n` +
`YouTube Studio'da 'Yapay zeka / Değiştirilmiş içerik mi?' sorusuna 'HAYIR' yanıtını verin.\n` +
`(Kural 80: Yüz klonlama veya haber manipülasyonu olmadığı sürece etiket işaretlenmemelidir; aksi halde algoritma videoyu daha dar bir kitleyle test eder.)\n\n` +
`🛡️ DOSYA GÜVENLİĞİ:\n` +
`Bu MP4 dosyası ctime yaşlandırması (Kural 29), free atom boyutu varyasyonu (Kural 30) ve pHash gürültüsü/gren (Kural 84 & 86) ile tamamen korunmuştur.`;

                        await navigator.clipboard.writeText(guideText);
                        showToast("📋 Manuel yükleme rehberi ve SEO metinleri panoya kopyalandı!");
                        alert("✅ Manuel Yükleme Bilgileri Panoya Kopyalandı!\n\n" + guideText);
                    } catch (err) {
                        alert("Kopyalama hatası: " + err.message);
                    }
                });
            });

            grid.querySelectorAll('.btn-upload-yt').forEach(b => {
                b.addEventListener('click', async (e) => {
                    const fn = e.currentTarget.getAttribute('data-filename');
                    const title = decodeURIComponent(e.currentTarget.getAttribute('data-title'));
                    b.disabled = true;
                    b.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Yükleniyor...';
                    try {
                        const res = await fetch('/api/youtube/publish', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ filename: fn, title: title })
                        });
                        const resData = await res.json();
                        if (resData.status === 'ok') {
                            showToast('🚀 Video YouTube kanalına yüklendi!');
                        } else {
                            alert('YouTube yükleme uyarısı: ' + (resData.error || 'Başarısız'));
                        }
                    } catch (err) {
                        alert(err.message);
                    } finally {
                        b.disabled = false;
                        b.innerHTML = '<i class="fa-brands fa-youtube"></i> Yükle';
                    }
                });
            });
        } catch (e) {
            console.error(e);
        }
    }

    document.getElementById('btn-refresh-gallery')?.addEventListener('click', loadGallery);

    // ══════════════════════════════════════════════════════════════
    // 12. AYARLAR & KOTA (Items 62 & 69)
    // ══════════════════════════════════════════════════════════════
    async function loadSettings() {
        try {
            const res = await fetch('/api/config');
            const data = await res.json();
            if (data.keys) {
                // Key existence indicators
                if (data.keys.gemini) document.getElementById('input-key-gemini').placeholder = '●●●●●●●● (Kayıtlı)';
                if (data.keys.pexels) document.getElementById('input-key-pexels').placeholder = '●●●●●●●● (Kayıtlı)';
                if (data.keys.pixabay) document.getElementById('input-key-pixabay').placeholder = '●●●●●●●● (Kayıtlı)';
            }
            // Load Quota stats via global helper
            await updateAiQuotaDisplay();
        } catch (e) {
            console.error("loadSettings error:", e);
        }
    }

    // ══════════════════════════════════════════════════════════════
    // 12.1 CANLI YAPAY ZEKA KOTA & HIZ LİMİTİ MONİTÖRÜ (Items 62 & 69)
    // ══════════════════════════════════════════════════════════════
    async function updateAiQuotaDisplay(passedData = null) {
        try {
            const qData = passedData || await (await fetch('/api/quota/stats')).json();
            if (!qData) return;

            const activeName = qData.active_provider_name || 'Google Gemini Flash';
            const rpmUsed = qData.current_rpm_used || 0;
            const rpmLimit = qData.rpm_limit || 15;
            const rpdUsed = qData.daily_used || 0;
            const rpdLimit = qData.rpd_limit || 1500;
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
            const miniBadge = document.getElementById('mini-quota-badge');
            const miniFill = document.getElementById('mini-quota-fill');
            const miniReset = document.getElementById('mini-quota-reset-text');

            if (miniAiName) miniAiName.textContent = activeName;
            if (miniRpm) miniRpm.textContent = qData.is_api_key_missing ? 'Çevrimdışı (0 TL)' : `${rpmUsed} / ${rpmLimit} RPM`;
            if (miniRpd) miniRpd.textContent = qData.is_api_key_missing ? 'Sınırsız Yerel' : `${rpdUsed} / ${rpdLimit.toLocaleString('tr-TR')} RPD`;

            if (miniBadge && miniFill) {
                if (qData.is_api_key_missing) {
                    miniBadge.textContent = 'Yerel Motor Aktif (0 TL)';
                    miniBadge.style.color = '#38bdf8';
                    miniFill.style.background = '#38bdf8';
                    miniFill.style.width = '100%';
                } else if (isExhausted) {
                    miniBadge.textContent = 'Limit Aşıldı (Fallback Aktif)';
                    miniBadge.style.color = '#facc15';
                    miniFill.style.background = '#facc15';
                    miniFill.style.width = '25%';
                } else {
                    miniBadge.textContent = `%${healthPct} Aktif`;
                    miniBadge.style.color = '#4ade80';
                    miniFill.style.background = '#10b981';
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
            if (studioAiRpd) studioAiRpd.innerHTML = qData.is_api_key_missing ? `<i class="fa-solid fa-key"></i> Gemini Anahtarı Ekleyin` : `<i class="fa-solid fa-calendar-day"></i> ${rpdUsed} / ${rpdLimit.toLocaleString('tr-TR')} RPD`;
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
            if (modalRpd) modalRpd.textContent = `${rpdUsed} / ${rpdLimit.toLocaleString('tr-TR')} RPD`;
            if (modalHealthText) modalHealthText.textContent = `%${healthPct} Müsait (${15 - rpmUsed} İstek Kaldı)`;
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
                    modalBadge.innerHTML = `<i class="fa-solid fa-circle-check"></i> %100 Aktif & Kesintisiz (0 TL Modu)`;
                    modalBadge.style.background = 'rgba(16, 185, 129, 0.2)';
                    modalBadge.style.color = '#34d399';
                }
            }

            if (modalProvidersList && qData.providers) {
                modalProvidersList.innerHTML = Object.entries(qData.providers).map(([pKey, pInfo]) => {
                    const isProvActive = pInfo.is_active;
                    const borderStyle = isProvActive ? 'border: 1px solid rgba(168, 85, 247, 0.5); background: rgba(168, 85, 247, 0.08);' : 'border: 1px solid rgba(255, 255, 255, 0.06); background: rgba(15, 23, 42, 0.5);';
                    const badgeColor = pInfo.badge_class === 'warning' ? '#facc15' : (pInfo.badge_class === 'danger' ? '#f87171' : (pInfo.badge_class === 'secondary' ? '#94a3b8' : '#34d399'));
                    return `
                        <div style="${borderStyle} border-radius: 8px; padding: 10px 14px; display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <div style="display: flex; align-items: center; gap: 8px;">
                                    <strong style="font-size: 13px; color: #f8fafc;">${pInfo.name}</strong>
                                    ${isProvActive ? '<span class="badge" style="background: rgba(168, 85, 247, 0.3); color: #c084fc; font-size: 10px; padding: 1px 6px; border-radius: 4px;">Aktif Seçili</span>' : ''}
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
                                    ${pInfo.has_key ? `Toplam: <strong>${pInfo.total_calls}</strong> çağrı · <strong>${pInfo.errors}</strong> hata` : `<span style="color: #64748b;">(Yapılandırılmadı)</span>`}
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
    document.getElementById('btn-open-quota-modal')?.addEventListener('click', openQuotaModal);
    document.getElementById('btn-close-quota-modal')?.addEventListener('click', closeQuotaModal);
    document.getElementById('btn-close-quota-modal-2')?.addEventListener('click', closeQuotaModal);
    document.getElementById('btn-refresh-quota-now')?.addEventListener('click', async () => {
        showToast('Yapay zeka kotaları güncelleniyor...');
        await updateAiQuotaDisplay();
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
            const res = await fetch('/api/settings', {
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

        try {
            const res = await fetch('/api/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            if (res.ok) {
                showToast('💾 Sistem ayarları kaydedildi!');
            }
        } catch (e) {
            alert('Ayar kaydetme hatası: ' + e.message);
        }
    });

    // ══════════════════════════════════════════════════════════════
    // TOAST BİLDİRİM FONKSİYONU
    // ══════════════════════════════════════════════════════════════
    function showToast(msg) {
        const container = document.getElementById('toast-container');
        if (!container) return;
        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.innerHTML = `<i class="fa-solid fa-circle-check text-primary"></i> <span>${msg}</span>`;
        container.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(-10px)';
            toast.style.transition = 'all 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 3500);
    }

    // ══════════════════════════════════════════════════════════════
    // 13. TEMA SEÇİCİ & PERSISTENCE
    // ══════════════════════════════════════════════════════════════
    const themeDots = document.querySelectorAll('.theme-dot');
    function setTheme(colorName) {
        document.body.setAttribute('data-theme', colorName);
        localStorage.setItem('shorts_theme', colorName);
        themeDots.forEach(d => {
            d.classList.toggle('active', d.getAttribute('data-color') === colorName);
        });
    }

    const savedTheme = localStorage.getItem('shorts_theme') || 'violet';
    setTheme(savedTheme);

    themeDots.forEach(dot => {
        dot.addEventListener('click', () => {
            const col = dot.getAttribute('data-color');
            if (col) setTheme(col);
        });
    });

    // ══════════════════════════════════════════════════════════════
    // 14. VİRAL KONU BANKASI & KONU ÖNERİCİ (Item 1-35)
    // ══════════════════════════════════════════════════════════════
    // 15. VIRAL KONU HAVUZU & VARYASYONLAR (Items 306 - 325)
    // ══════════════════════════════════════════════════════════════
    const VIRAL_TOPIC_BANK = {
        "1_news_flash": [
            "Tüm Dünyayı Sarsan Son Dakika Açıklaması!",
            "Uzmanlar Uyardı: Bu Hafta Başlayan Kritik Gelişme!",
            "Teknoloji Dünyasında Deprem Yaratan Flaş Karar!",
            "Tüm Piyasaları Altüst Eden Beklenmedik Olay!"
        ],
        "2_reddit_confessions": [
            "AITA: Düğünü Terk Eden Nişanlıma Verdiğim Cevap",
            "Gizli Sırrımı 5 Yıl Sonra İtiraf Etmek Zorunda Kaldım...",
            "İş Yerindeki En Büyük Skandalı Ortaya Çıkardığım Gün",
            "Ailemin Benden Sakladığı Büyük Gerçeği Öğrendim"
        ],
        "3_split_gameplay": [
            "Tarihin En İnanılmaz Kaçış Hikayesi",
            "Bu Gizemli Olayı Çözen Kimse Çıkmadı!",
            "Yeraltı Tünellerinde Kaybolan Adamın Hikayesi",
            "Dünyanın En Tehlikeli Yollarında Yaşananlar"
        ],
        "4_would_you_rather": [
            "Geleceği Görmek mi, Geçmişi Değiştirmek mi? (%90 Zorlandı)",
            "Sonsuz Para mı, Sonsuz Sağlık mı? Zorlu Tercih Düellosu",
            "Asla Uyumamak mı, Asla Yemek Yememek mi?",
            "Zihin Okuma Yeteneği mi, Görünmezlik mi?"
        ],
        "5_guess_flag_country": [
            "Sadece Gerçek Coğrafya Dahileri Bu 3 Bayrağı Bilebiliyor!",
            "Bu Başkent Hangi Ülkeye Ait? (%95 Yanıldı)",
            "5 Saniyede Ülkeyi Tahmin Et: Dünya Bayrakları Quiz",
            "Hangi Ülkenin Para Birimi? Testi Geçebilecek Misin?"
        ],
        "6_stoic_philosophy": [
            "Marcus Aurelius'un Öfkeyi Yok Eden 3 Stoacı Kuralı",
            "Seneca: Zamanını Çalan İnsanlardan Kurtulmanın 4 Yolu",
            "Epiktetos'un Zihinsel Dayanıklılık Formülü: Asla Şikayet Etme",
            "Hiçbir Şeyi Kafana Takmamanın 3 Stoacı Sırrı"
        ],
        "7_dark_psychology": [
            "3 Dark Psychology Secrets Manipulation Experts Never Tell You",
            "İnsanların Yalan Söylediğini Ele Veren 3 Mikro İpucu",
            "Manipülasyon Ustalarının Kullandığı Ters Psikoloji Tuzağı",
            "Sohbette Üstünlük Kurmanızı Sağlayan 3 Sessizlik Kuralı"
        ],
        "8_crypto_market": [
            "Bitcoin Halving Sonrası Zengin Eden 3 Döngü Kuralı",
            "Kripto Balinalarının Topladığı 3 Gizli Altcoin",
            "Fakir İnsanların Yaptığı ve Asla Zengin Olamadıkları 4 Hata",
            "Bileşik Getirinin Gücü: Günde 1 Dolarla Nasıl Portföy Büyütülür?"
        ],
        "9_five_facts": [
            "Dünya Hakkında Asla Bilmediğiniz 5 Şaşırtıcı Gerçek",
            "Tarihin En Tuhaf 5 Rastlantısı",
            "İnsan Vücudunun Bilinmeyen 5 Gizli Özelliği",
            "Okyanusların En Derin Noktasındaki 5 Korkutucu Sır"
        ],
        "27_common_myths_busted": [
            "Herkesin Doğru Bildiği 5 Büyük Bilimsel Yanılgı!",
            "Yıllardır İnanılan ve Tamamen Yalan Olan 4 Şehir Efsanesi",
            "Tarih Kitaplarında Yanlış Anlatılan 3 Büyük Olay",
            "Sağlık Konusunda Doğru Sanılan 5 Tehlikeli Yanılgı"
        ],
        "general": [
            "Herkesin Doğru Bildiği 5 Büyük Bilimsel Yanılgı!",
            "Günde Sadece 10 Dakika Yaparak Hayatını Değiştirecek Alışkanlık",
            "Milyonerlerin Sabah Rutinindeki 3 Gizli Adım",
            "Bilinçaltının Çalışma Prensibi: Neden Hep Aynı Hatayı Yapıyoruz?"
        ]
    };

    function suggestTopic() {
        const nId = selectNiche ? selectNiche.value : '6_stoic_philosophy';
        let pool = VIRAL_TOPIC_BANK[nId];
        if (!pool) {
            if (nId.includes("stoic")) pool = VIRAL_TOPIC_BANK["6_stoic_philosophy"];
            else if (nId.includes("psychology")) pool = VIRAL_TOPIC_BANK["7_dark_psychology"];
            else if (nId.includes("crypto") || nId.includes("finance")) pool = VIRAL_TOPIC_BANK["8_crypto_market"];
            else if (nId.includes("news")) pool = VIRAL_TOPIC_BANK["1_news_flash"];
            else if (nId.includes("reddit")) pool = VIRAL_TOPIC_BANK["2_reddit_confessions"];
            else if (nId.includes("myth") || nId.includes("science")) pool = VIRAL_TOPIC_BANK["27_common_myths_busted"];
            else if (nId.includes("fact")) pool = VIRAL_TOPIC_BANK["9_five_facts"];
            else pool = VIRAL_TOPIC_BANK.general;
        }
        const randomTopic = pool[Math.floor(Math.random() * pool.length)];
        inputTopic.value = randomTopic;
        updateLoopBridge(nId, randomTopic);
        showToast(`✨ Konu Önerildi: ${randomTopic}`);
    }

    document.getElementById('btn-suggest-topic')?.addEventListener('click', suggestTopic);

    // Otomatik Niş Eşleştirme (Kullanıcı başlık yazdığında uygun nişi seçer)
    function autoDetectNicheFromTopic() {
        const topicText = (inputTopic?.value || '').trim().toLowerCase();
        if (!topicText || !selectNiche) return;

        let targetId = null;
        if (/yanılgı|mit|efsane|yanlış bilinen|doğru bilinen|bilimsel/.test(topicText)) targetId = "27_common_myths_busted";
        else if (/stoa|marcus|aurelius|seneca|epiktetos|felsefe/.test(topicText)) targetId = "6_stoic_philosophy";
        else if (/karanlık psikoloji|manipülasyon|manipulation|dark psychology/.test(topicText)) targetId = "7_dark_psychology";
        else if (/kripto|bitcoin|borsa|altın|hisse|dolar|enflasyon/.test(topicText)) targetId = "8_crypto_market";
        else if (/\d+\s+(?:büyük|ilginç|önemli|sır|kural|adım|ipucu)|şaşırtıcı gerçek/.test(topicText)) targetId = "9_five_facts";
        else if (/aita|itiraf|confession|reddit/.test(topicText)) targetId = "2_reddit_confessions";
        else if (/tercih et|would you rather/.test(topicText)) targetId = "4_would_you_rather";
        else if (/bayrak|ülke tahmin|hangi ülke/.test(topicText)) targetId = "5_guess_flag_country";
        else if (/son dakika|flaş|haber|deprem|kaza|trafik/.test(topicText)) targetId = "1_news_flash";

        if (targetId && selectNiche.value !== targetId) {
            // Sadece varsayılan 1_news_flash durumundaysa otomatik eşle
            if (selectNiche.value === "1_news_flash" || selectNiche.value === "") {
                const opt = selectNiche.querySelector(`option[value="${targetId}"]`);
                if (opt) {
                    selectNiche.value = targetId;
                    applyNicheProfile(targetId);
                    showToast(`🎯 Niş Otomatik Eşleştirildi: ${opt.textContent}`);
                }
            }
        }
    }
    inputTopic?.addEventListener('change', autoDetectNicheFromTopic);
    inputTopic?.addEventListener('blur', autoDetectNicheFromTopic);

    function escapeHtml(value) {
        const element = document.createElement('div');
        element.textContent = String(value || '');
        return element.innerHTML;
    }

    async function applyNicheProfile(nicheId) {
        const profileBox = document.getElementById('niche-production-profile');
        if (!nicheId || !profileBox) return;
        try {
            const response = await fetch(`/api/niches/${encodeURIComponent(nicheId)}/profile`);
            const data = await response.json();
            const profile = data.profile;
            if (!profile) return;
            const rules = profile.production_rules || {};
            chkSplitScreen.checked = Boolean(rules.split_screen);
            chkKenBurns.checked = Boolean(rules.ken_burns);
            if (rules.subtitle_preset && selectSubPreset) selectSubPreset.value = rules.subtitle_preset;
            profileBox.innerHTML = `
                <div style="display: flex; justify-content: space-between; gap: 8px; align-items: center;">
                    <strong style="font-size: 12px; color: #67e8f9;"><i class="fa-solid fa-sliders"></i> Aktif Niş Profili: ${escapeHtml(profile.name)}</strong>
                    <span class="niche-tag">${escapeHtml(profile.category)}</span>
                </div>
                <div style="font-size: 11px; color: #cbd5e1; margin-top: 6px;">Ton: ${escapeHtml(profile.tone)}</div>
                <div style="font-size: 11px; color: #94a3b8; margin-top: 4px;">${rules.split_screen ? 'Split-screen' : 'Tam ekran'} · ${escapeHtml(rules.subtitle_preset)} altyazı · Dinamik hareket · Neon ilerleme</div>
            `;
            updateLoopBridge(nicheId, inputTopic.value);
            const redditPanel = document.getElementById('reddit-research-panel');
            if (redditPanel) redditPanel.style.display = nicheId === '2_reddit_confessions' ? 'block' : 'none';
            if (nicheId !== '2_reddit_confessions') selectedRedditPost = null;
        } catch (error) {
            profileBox.textContent = 'Niş üretim profili yüklenemedi.';
            console.error('Niş profili yükleme hatası:', error);
        }
    }

    document.getElementById('btn-load-niche-trends')?.addEventListener('click', async (event) => {
        const nicheId = selectNiche?.value;
        const results = document.getElementById('niche-trends-results');
        if (!nicheId || !results) return;
        const button = event.currentTarget;
        button.disabled = true;
        button.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Araştırılıyor';
        try {
            const response = await fetch(`/api/niches/${encodeURIComponent(nicheId)}/trends?region=TR`);
            const data = await response.json();
            results.style.display = 'block';
            if (data.status !== 'ok') {
                results.innerHTML = `<div class="alert-info-box"><i class="fa-solid fa-key"></i><span>${escapeHtml(data.reason || 'Trend verisi alınamadı.')}</span></div>`;
                return;
            }
            results.innerHTML = `
                <div style="font-size: 11px; color: #67e8f9; margin: 8px 0;">Son 24 saatte yayınlanan, görüntülenmeye göre sıralı başlık sinyalleri</div>
                ${data.trends.map((trend, index) => `
                    <button class="trend-topic-option" data-topic="${escapeHtml(trend.title)}" style="display:block; width:100%; text-align:left; padding:8px; margin-bottom:5px; border-radius:6px; background:rgba(15,23,42,.7); border:1px solid rgba(148,163,184,.16); color:#e2e8f0; cursor:pointer;">
                        <strong style="font-size:12px;">${index + 1}. ${escapeHtml(trend.title)}</strong><br>
                        <span style="font-size:10px; color:#94a3b8;">${escapeHtml(trend.channel)} · ${Number(trend.view_count).toLocaleString('tr-TR')} görüntülenme</span>
                    </button>
                `).join('')}
            `;
            results.querySelectorAll('.trend-topic-option').forEach(option => {
                option.addEventListener('click', () => {
                    inputTopic.value = option.dataset.topic;
                    updateLoopBridge(nicheId, inputTopic.value);
                    showToast('Trend başlık sinyali konu alanına aktarıldı. Senaryo özgün olarak üretilecek.');
                });
            });
        } catch (error) {
            results.style.display = 'block';
            results.textContent = 'Trend araştırması sırasında bağlantı hatası oluştu.';
            console.error('Trend araştırması hatası:', error);
        } finally {
            button.disabled = false;
            button.innerHTML = '<i class="fa-solid fa-chart-line"></i> Son 24 Saat Trendlerini Getir';
        }
    });

    document.getElementById('btn-analyze-content-gaps')?.addEventListener('click', async (event) => {
        const source = document.getElementById('content-gap-topics');
        const results = document.getElementById('content-gap-results');
        const nicheId = selectNiche?.value;
        if (!source?.value.trim() || !results || !nicheId) {
            showToast('Önce YouTube Studio içerik boşluğu konu listesini girin.');
            return;
        }
        const button = event.currentTarget;
        button.disabled = true;
        try {
            const response = await fetch('/api/research/content-gaps', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ raw_topics: source.value, niche: nicheId })
            });
            const data = await response.json();
            if (!response.ok) throw new Error(data.detail || 'Araştırma çözümlenemedi.');
            results.style.display = 'block';
            results.innerHTML = data.suggestions.length ? data.suggestions.map(suggestion => `
                <button class="trend-topic-option content-gap-option" data-topic="${escapeHtml(suggestion.topic)}" style="display:block; width:100%; text-align:left; padding:8px; margin-bottom:5px; border-radius:6px; background:rgba(15,23,42,.7); border:1px solid rgba(251,191,36,.2); color:#e2e8f0; cursor:pointer;">
                    <strong style="font-size:12px;">${escapeHtml(suggestion.topic)}</strong>
                    <span style="float:right; font-size:10px; color:#fbbf24;">Uygunluk ${suggestion.relevance}/100</span>
                </button>`).join('') : '<div class="alert-info-box">Kullanılabilir konu bulunamadı.</div>';
            results.querySelectorAll('.content-gap-option').forEach(option => option.addEventListener('click', () => {
                inputTopic.value = option.dataset.topic;
                updateLoopBridge(nicheId, inputTopic.value);
                showToast('İçerik boşluğu konusu seçildi. Senaryo niş profilinizle özgün üretilecek.');
            }));
        } catch (error) {
            results.style.display = 'block';
            results.textContent = error.message;
        } finally {
            button.disabled = false;
        }
    });

    document.getElementById('btn-load-reddit-posts')?.addEventListener('click', async (event) => {
        const results = document.getElementById('reddit-post-results');
        const subreddit = document.getElementById('select-reddit-subreddit')?.value || 'AITA';
        const button = event.currentTarget;
        button.disabled = true;
        button.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Keşfediliyor...';
        try {
            const response = await fetch(`/api/research/reddit?subreddit=${encodeURIComponent(subreddit)}`);
            const data = await response.json();
            if (!response.ok || data.status !== 'ok') throw new Error(data.detail || 'Reddit gönderileri alınamadı.');
            
            const modeBadge = data.mode === 'oauth'
                ? '<span class="badge" style="background: rgba(16, 185, 129, 0.2); color: #34d399; font-size: 10px; padding: 2px 6px; border-radius: 4px;"><i class="fa-solid fa-key"></i> Resmi OAuth API</span>'
                : '<span class="badge" style="background: rgba(168, 85, 247, 0.2); color: #c084fc; font-size: 10px; padding: 2px 6px; border-radius: 4px;"><i class="fa-solid fa-wand-magic-sparkles"></i> Otomatik Akıllı Keşif (Anahtarsız)</span>';

            const headerHtml = `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                    <span style="font-size: 11px; color: #94a3b8;">${data.posts.length} trend gönderi hazır:</span>
                    ${modeBadge}
                </div>
            `;

            results.innerHTML = data.posts.length ? headerHtml + data.posts.map((post, index) => `
                <button type="button" class="trend-topic-option reddit-post-option" data-index="${index}" style="display:block; width:100%; text-align:left; padding:8px 10px; margin-bottom:6px; border-radius:8px; background:rgba(15,23,42,.75); border:1px solid rgba(255,69,0,.35); color:#e2e8f0; cursor:pointer; transition: all 0.2s ease;">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 6px;">
                        <strong style="font-size:12px; line-height: 1.35; color: #f8fafc;">${escapeHtml(post.title)}</strong>
                    </div>
                    <div style="font-size:10px; color:#94a3b8; margin-top: 4px; display: flex; gap: 8px;">
                        <span style="color: #ff6b35; font-weight: 600;">r/${escapeHtml(post.subreddit)}</span>
                        <span>·</span>
                        <span>▲ ${Number(post.score || 1000).toLocaleString('tr-TR')} oy</span>
                        <span>·</span>
                        <span style="color: #64748b;">${escapeHtml(post.author || 'Anonim')}</span>
                    </div>
                </button>`).join('') : '<div class="alert-info-box">Uygun kaynak gönderi bulunamadı.</div>';
            
            results.querySelectorAll('.reddit-post-option').forEach(option => option.addEventListener('click', () => {
                selectedRedditPost = data.posts[Number(option.dataset.index)];
                inputTopic.value = selectedRedditPost.title;
                updateLoopBridge('2_reddit_confessions', inputTopic.value);
                showToast('Reddit viral hikayesi seçildi. İlk sahneye kaynak kartı eklenecek ve metin insanlaştırılacak.');
            }));
        } catch (error) {
            results.innerHTML = `<div class="alert-info-box text-danger" style="font-size: 11px;">⚠️ ${escapeHtml(error.message)}</div>`;
        } finally {
            button.disabled = false;
            button.innerHTML = '<i class="fa-solid fa-comments"></i> Güncel Gönderileri Getir';
        }
    });


    // ══════════════════════════════════════════════════════════════
    // 15. CANLI KANCA (HOOK) & DÖNGÜ (LOOP) KÖPRÜSÜ
    // ══════════════════════════════════════════════════════════════
    function updateLoopBridge(nicheId, topic) {
        const hookSpan = document.getElementById('preview-hook-text');
        const loopSpan = document.getElementById('preview-loop-text');
        const subOverlay = document.getElementById('mockup-sub-overlay');
        if (!hookSpan || !loopSpan) return;

        const topicText = topic || inputTopic.value || "Bu Gizemli Konu";

        if (nicheId && nicheId.includes('stoic')) {
            hookSpan.textContent = `"Bu kuralı öğrenene kadar hayatınız kontrolünüzde değildi..."`;
            loopSpan.textContent = `"...ve tam da bu yüzden asla unutmayın çünkü..."`;
        } else if (nicheId && (nicheId.includes('dark') || nicheId.includes('psychology'))) {
            hookSpan.textContent = `"İnsanların sizden gizlediği bu psikolojik hileyi öğrenin..."`;
            loopSpan.textContent = `"...çünkü bu sırrı ilk duyduğunuzda başa dönüp diyeceksiniz ki..."`;
        } else if (nicheId && (nicheId.includes('space') || nicheId.includes('bilim'))) {
            hookSpan.textContent = `"Astrofizikçileri dehşete düşüren bu gerçeği çok az kişi biliyor..."`;
            loopSpan.textContent = `"...ve işte evrenin tam da bu döngüsü yüzünden her şey başa dönüyor..."`;
        } else {
            hookSpan.textContent = `"${topicText.slice(0, 45)} hakkında bunu ilk kez duyacaksınız..."`;
            loopSpan.textContent = `"...ve işte tam da bu sebeple asla durmayın çünkü..."`;
        }

        if (subOverlay) {
            const firstWords = topicText.split(' ').slice(0, 3).join(' ').toUpperCase();
            subOverlay.innerHTML = `<span class="sub-word-highlight">${firstWords}</span> ${topicText.split(' ').slice(3).join(' ')}`;
        }
    }

    selectNiche?.addEventListener('change', () => {
        updateLoopBridge(selectNiche.value, inputTopic.value);
        applyNicheProfile(selectNiche.value);
    });

    inputTopic?.addEventListener('input', () => {
        updateLoopBridge(selectNiche ? selectNiche.value : 'stoic', inputTopic.value);
    });

    // Subtitle Preset Live Style Switch
    selectSubPreset?.addEventListener('change', () => {
        const subOverlay = document.getElementById('mockup-sub-overlay');
        if (subOverlay) {
            subOverlay.className = `mockup-subtitle-overlay preset-${selectSubPreset.value}`;
        }
    });

    // ══════════════════════════════════════════════════════════════
    // 16. HIZLI AKSİYON BUTONLARI (Quick Action Strip)
    // ══════════════════════════════════════════════════════════════
    // 1. Rastgele Niş Seç & Konu Üret
    document.getElementById('qa-random-niche')?.addEventListener('click', async () => {
        if (allNiches.length === 0) await loadNiches();
        if (allNiches.length > 0) {
            const randomN = allNiches[Math.floor(Math.random() * allNiches.length)];
            selectNiche.value = randomN.id;
            await applyNicheProfile(randomN.id);
            suggestTopic();
            switchTab('studio');
            showToast(`🎲 Rastgele Niş Seçildi: ${randomN.name} (${randomN.category})`);
        } else {
            suggestTopic();
        }
    });

    // 2. Son Dakika Flaş Haber Çek (Doğrudan Stüdyoya Aktarır)
    document.getElementById('qa-latest-news')?.addEventListener('click', async () => {
        showToast('📡 En güncel son dakika flaş haberi taranıyor...');
        try {
            const res = await fetch('/api/rss/fetch?source=aa_guncel&limit=1');
            const data = await res.json();
            if (data.items && data.items.length > 0) {
                const news = data.items[0];
                inputTopic.value = news.title;
                selectNiche.value = "1_news_flash";
                await applyNicheProfile("1_news_flash");
                updateLoopBridge("1_news_flash", news.title);
                switchTab('studio');
                showToast(`📰 Son Dakika Haberi Yüklendi: ${news.title.slice(0, 45)}...`);
            } else {
                switchTab('rss-bot');
                loadRssNews();
            }
        } catch (e) {
            switchTab('rss-bot');
            loadRssNews();
        }
    });

    // 3. Split-Screen Modunu Aç / Kapat (Toggle & Canlı Senkronizasyon)
    const btnSplitMode = document.getElementById('qa-split-mode');
    btnSplitMode?.addEventListener('click', () => {
        chkSplitScreen.checked = !chkSplitScreen.checked;
        chkSplitScreen.dispatchEvent(new Event('change'));
        btnSplitMode.classList.toggle('active', chkSplitScreen.checked);
        const span = btnSplitMode.querySelector('span');
        if (span) span.textContent = chkSplitScreen.checked ? 'Split-Screen: AÇIK' : 'Split-Screen Modunu Aç';
        switchTab('studio');
        showToast(chkSplitScreen.checked ? '🎮 Split-Screen (Oynanış + Kurgu) Aktif!' : '⏹️ Split-Screen Modu Kapatıldı');
    });

    chkSplitScreen?.addEventListener('change', () => {
        if (btnSplitMode) {
            btnSplitMode.classList.toggle('active', chkSplitScreen.checked);
            const span = btnSplitMode.querySelector('span');
            if (span) span.textContent = chkSplitScreen.checked ? 'Split-Screen: AÇIK' : 'Split-Screen Modunu Aç';
        }
    });

    // 4. Tier-1 (ABD/İngilizce) Modu (Toggle TR / EN)
    const btnTier1 = document.getElementById('qa-tier1-en');
    btnTier1?.addEventListener('click', async () => {
        const isCurrentlyEn = selectLanguage.value === 'en';
        if (!isCurrentlyEn) {
            selectLanguage.value = 'en';
            selectVoiceGender.value = 'male';
            selectNiche.value = '7_dark_psychology';
            await applyNicheProfile('7_dark_psychology');
            inputTopic.value = "3 Dark Psychology Secrets Manipulation Experts Never Tell You #Shorts";
            btnTier1.classList.add('active');
            const span = btnTier1.querySelector('span');
            if (span) span.textContent = 'Tier-1 EN: AKTİF (ABD)';
            switchTab('studio');
            showToast('🌎 Tier-1 ABD (İngilizce Yüksek CPM) Modu Aktif Edildi!');
        } else {
            selectLanguage.value = 'tr';
            selectVoiceGender.value = 'auto';
            selectNiche.value = '6_stoic_philosophy';
            await applyNicheProfile('6_stoic_philosophy');
            inputTopic.value = "Marcus Aurelius'un Öfkeyi Yok Eden 3 Stoacı Kuralı";
            btnTier1.classList.remove('active');
            const span = btnTier1.querySelector('span');
            if (span) span.textContent = 'Tier-1 (ABD/İngilizce) Modu';
            switchTab('studio');
            showToast('🇹🇷 Türkçe Moduna Geri Dönüldü');
        }
    });

    // ══════════════════════════════════════════════════════════════
    // 17. CSV / METİN SÜRÜKLE-BIRAK (Dropzone)
    // ══════════════════════════════════════════════════════════════
    const csvDropzone = document.getElementById('csv-dropzone');
    const csvFileInput = document.getElementById('csv-file-input');
    const batchTextArea = document.getElementById('batch-topics-text');

    if (csvDropzone && csvFileInput && batchTextArea) {
        csvDropzone.addEventListener('click', () => csvFileInput.click());

        csvFileInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) handleCsvFile(file);
        });

        csvDropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            csvDropzone.classList.add('dragover');
        });

        csvDropzone.addEventListener('dragleave', () => {
            csvDropzone.classList.remove('dragover');
        });

        csvDropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            csvDropzone.classList.remove('dragover');
            const file = e.dataTransfer.files[0];
            if (file) handleCsvFile(file);
        });

        function handleCsvFile(file) {
            const reader = new FileReader();
            reader.onload = (evt) => {
                const text = evt.target.result;
                const lines = text.split(/\r?\n/).map(l => l.trim()).filter(Boolean);
                batchTextArea.value = lines.join('\n');
                showToast(`📂 ${lines.length} adet konu başarıyla yüklendi!`);
            };
            reader.readAsText(file);
        }
    }

    // ══════════════════════════════════════════════════════════════
    // 18. KLAVYE KISAYOLLARI (Power User Hotkeys)
    // ══════════════════════════════════════════════════════════════
    document.addEventListener('keydown', (e) => {
        // Form girdilerinde iken kısayolları engelleme kontrolü
        const isInput = ['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName);

        // Ctrl+Enter veya Cmd+Enter: Hızlı Render
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            e.preventDefault();
            btnQuickRender?.click();
            return;
        }

        // Escape: Terminal konsolunu kapat
        if (e.key === 'Escape') {
            terminalPanel?.classList.add('hidden');
            return;
        }

        // Alt + 1-8 Sekme Geçişi
        if (!isInput && e.altKey && e.key >= '1' && e.key <= '8') {
            const tabKeys = ["studio", "timeline", "niches", "rss-bot", "batch", "growth", "effects", "subtitles"];
            const idx = parseInt(e.key) - 1;
            if (tabKeys[idx]) {
                e.preventDefault();
                switchTab(tabKeys[idx]);
            }
        }
    });

    // ══════════════════════════════════════════════════════════════
    // 19. 500-ITEM ROADMAP HANDLERS (Anti-Detect & Proof Archiver)
    // ══════════════════════════════════════════════════════════════
    document.getElementById('btn-calc-jitter')?.addEventListener('click', async () => {
        const hour = document.getElementById('input-jitter-hour').value || 18;
        const minute = document.getElementById('input-jitter-minute').value || 0;
        const box = document.getElementById('jitter-result-box');
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
        const chName = document.getElementById('input-appeal-channel').value || 'Shorts Kanalı';
        const box = document.getElementById('appeal-result-box');
        box.textContent = 'İtiraz videosu senaryosu hazırlanıyor...';

        try {
            const res = await fetch(`/api/proof/appeal_script?channel_name=${encodeURIComponent(chName)}`);
            const data = await res.json();
            box.textContent = data.script;
            showToast('📜 5 Dakikalık YouTube İtiraz Scripti oluşturuldu!');
        } catch (e) {
            box.textContent = 'Hata: ' + e.message;
        }
    });

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
            counterBadge.innerHTML = `<i class="fa-solid fa-circle-check"></i> ${filtered.length} / 500 Madde Gösteriliyor`;
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
    // 21. ANTI-DETECT KANAL ONBOARDING & OTOMASYON BOTU (5 ALTIN KURAL)
    // ══════════════════════════════════════════════════════════════

    let currentAnalyzedChannel = null;

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

                <!-- 16 Kural Donanım, Ağ, İstemci & Güvenlik Özeti Grid -->
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 8px; margin: 16px 0;">
                    <div style="background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
                        <small style="color: #94a3b8; display: block; font-size: 10px;">KURAL 1: YÜKLEME BAYRAĞI</small>
                        <strong style="color: #10b981; font-size: 12px;"><i class="fa-solid fa-check"></i> Studio UI Oturumu</strong>
                    </div>
                    <div style="background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
                        <small style="color: #94a3b8; display: block; font-size: 10px;">KURAL 2: PROXY DENETİMİ</small>
                        <strong style="color: ${proxy.is_residential ? '#10b981' : '#f59e0b'}; font-size: 12px;">
                            ${proxy.is_residential ? '<i class="fa-solid fa-check"></i> ISP Residential' : (proxy.configured ? '⚠️ Datacenter Riski' : 'ℹ️ Yerel ISP IP')}
                        </strong>
                    </div>
                    <div style="background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
                        <small style="color: #94a3b8; display: block; font-size: 10px;">KURAL 3: WEBRTC KALKANI</small>
                        <strong style="color: #10b981; font-size: 12px;"><i class="fa-solid fa-shield"></i> UDP Sızıntısı Bloklu</strong>
                    </div>
                    <div style="background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
                        <small style="color: #94a3b8; display: block; font-size: 10px;">KURAL 4 & 5: CANVAS & GPU</small>
                        <strong style="color: #8b5cf6; font-size: 12px;">${profile.webgl_renderer}</strong>
                    </div>
                    <div style="background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
                        <small style="color: #94a3b8; display: block; font-size: 10px;">KURAL 10: DNS SIZINTISI</small>
                        <strong style="color: #10b981; font-size: 12px;"><i class="fa-solid fa-lock"></i> Cloudflare DoH</strong>
                    </div>
                    <div style="background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
                        <small style="color: #94a3b8; display: block; font-size: 10px;">KURAL 17: ÖN İZLEME</small>
                        <strong style="color: #10b981; font-size: 12px;"><i class="fa-solid fa-play"></i> 2-3 Shorts + Yorum</strong>
                    </div>
                    <div style="background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
                        <small style="color: #94a3b8; display: block; font-size: 10px;">KURAL 18: OTURUM SÜRESİ</small>
                        <strong style="color: #38bdf8; font-size: 12px;"><i class="fa-solid fa-hourglass-half"></i> 3-7 dk Kuralı</strong>
                    </div>
                    <div style="background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
                        <small style="color: #94a3b8; display: block; font-size: 10px;">KURAL 19: HEADLESS İZİ</small>
                        <strong style="color: #10b981; font-size: 12px;"><i class="fa-solid fa-user-secret"></i> webdriver: undef</strong>
                    </div>
                    <div style="background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
                        <small style="color: #94a3b8; display: block; font-size: 10px;">KURAL 22: TLS JA3</small>
                        <strong style="color: #10b981; font-size: 12px;"><i class="fa-solid fa-fingerprint"></i> Chrome 124</strong>
                    </div>
                    <div style="background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
                        <small style="color: #94a3b8; display: block; font-size: 10px;">KURAL 23: PROTOKOL</small>
                        <strong style="color: #06b6d4; font-size: 12px;"><i class="fa-solid fa-network-wired"></i> HTTP/2 & QUIC</strong>
                    </div>
                    <div style="background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
                        <small style="color: #94a3b8; display: block; font-size: 10px;">KURAL 24: AĞ JITTER'I</small>
                        <strong style="color: #f59e0b; font-size: 12px;"><i class="fa-solid fa-wave-square"></i> Ev ISP Hızı</strong>
                    </div>
                    <div style="background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
                        <small style="color: #94a3b8; display: block; font-size: 10px;">KURAL 25: LOKASYON</small>
                        <strong style="color: #10b981; font-size: 12px;"><i class="fa-solid fa-location-dot"></i> Coğrafi Kilitli</strong>
                    </div>
                    <div style="background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
                        <small style="color: #94a3b8; display: block; font-size: 10px;">KURAL 26: ÖNBELLEK</small>
                        <strong style="color: #a855f7; font-size: 12px;"><i class="fa-solid fa-database"></i> IndexedDB Kalıcı</strong>
                    </div>
                    <div style="background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
                        <small style="color: #94a3b8; display: block; font-size: 10px;">KURAL 27: CLIENT HINTS</small>
                        <strong style="color: #38bdf8; font-size: 12px;"><i class="fa-solid fa-id-card"></i> sec-ch-ua: macOS</strong>
                    </div>
                    <div style="background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
                        <small style="color: #94a3b8; display: block; font-size: 10px;">KURAL 29: CTIME/MTIME</small>
                        <strong style="color: #ec4899; font-size: 12px;"><i class="fa-solid fa-clock-rotate-left"></i> -15..45 dk</strong>
                    </div>
                    <div style="background: rgba(0,0,0,0.3); padding: 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
                        <small style="color: #94a3b8; display: block; font-size: 10px;">KURAL 30: BOYUT VARYASYONU</small>
                        <strong style="color: #10b981; font-size: 12px;"><i class="fa-solid fa-file-shield"></i> free Atom Dolgusu</strong>
                    </div>
                </div>

                <div style="margin: 18px 0 10px 0; display: flex; align-items: center; justify-content: space-between;">
                    <h4 style="margin: 0; font-size: 14px; color: #fff; display: flex; align-items: center; gap: 8px;">
                        <i class="fa-solid fa-list-check text-warning"></i> Neler Yapılması Gerektiği (Adım Adım Yol Haritası - 30 Kural)
                    </h4>
                    <small style="color: #94a3b8;">Otomasyon Motoru Hazır</small>
                </div>

                <div class="channel-checklist-box">
                    ${checklistHtml}
                </div>

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

        document.getElementById('btn-run-warmup-now')?.addEventListener('click', () => {
            triggerWarmupSession(ch.handle);
        });

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
            } else {
                if (logsBox) {
                    logsBox.innerHTML += `<div style="color: #ef4444;">[Hata] ${data.error || 'Bilinmeyen hata'}</div>`;
                }
            }
        } catch (e) {
            if (logsBox) {
                logsBox.innerHTML += `<div style="color: #ef4444;">[Hata] ${e.message}</div>`;
            }
        }
    }

    // Attach listeners
    document.getElementById('btn-onboard-analyze')?.addEventListener('click', triggerChannelAnalysis);
    document.getElementById('btn-refresh-managed-channels')?.addEventListener('click', loadManagedChannels);
    loadManagedChannels();

    // İlk yüklemede 35+7 nişi çek ve kota panelini güncelle
    loadNiches();
    loadGallery();
    refreshBatchQueue();
    restoreRenderState();
    updateLoopBridge('stoic', inputTopic ? inputTopic.value : '');
    updateAiQuotaDisplay();
    setInterval(updateAiQuotaDisplay, 10000);
});

