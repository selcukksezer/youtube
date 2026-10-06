/**
 * ShortsAI Studio — 35 Niches Library & Analysis (niches.js)
 * Covers 35 Niche templates, catalog rendering, search/sort/filter, collision matrix and profile application.
 */


// ══════════════════════════════════════════════════════════════
// 2. 35 NİŞİ YÜKLEME VE KARTLARI BASMA (Items 1 - 35)
// ══════════════════════════════════════════════════════════════
// ══════════════════════════════════════════════════════════════
// 2. NİŞ KÜTÜPHANESİ — Advanced v2.0
// ══════════════════════════════════════════════════════════════
let currentNicheViewMode = 'grid'; // 'grid' | 'list'
let currentModalNicheId = null;

// Helper: parse RPM string to max numeric value for sorting
function parseRpmMax(rpmStr) {
    if (!rpmStr) return 0;
    const nums = rpmStr.replace(/[$]/g, '').split('-').map(Number);
    return Math.max(...nums.filter(n => !isNaN(n)));
}

// Helper: competition level to sort order (low = best)
function compToNum(lvl) { return lvl === 'low' ? 3 : lvl === 'medium' ? 2 : 1; }

// Helper: Nişleri ana kategorilere eşleyen sınıflandırıcı
function getNicheCategoryGroup(n) {
    if (!n) return 'Diğer & Genel';
    const cat = (n.category || '').toLowerCase();
    const name = (n.name || '').toLowerCase();
    const nid = (n.id || '').toLowerCase();
    const full = `${name} ${cat} ${nid}`;

    // 1. Din & Maneviyat
    if (/din|maneviyat|ayet|hadis|huzur|dini/.test(full)) return 'Din & Maneviyat';

    // 2. Çocuk & Aile
    if (/çocuk|pedagoji|ebeveyn|aile animasyon/.test(full)) return 'Çocuk & Aile';

    // 3. Alışveriş & Ürünler
    if (/affiliate|ürün|alışveriş|e-ticaret|amazon|trendyol/.test(full)) return 'Alışveriş & Ürünler';

    // 4. Bilim, Uzay & Teknoloji (Quiz'den önce test edilmeli, 'yapay zeka' zeka ile karışmasın)
    if (/yapay zeka|ai araç|teknoloji & yapay zeka|astronomi|bilim & evren|gelecek simülasyonu|mit avcısı|bilim &/.test(full)) return 'Bilim, Uzay & Teknoloji';

    // 5. Gizem, Gerilim & Suç (Finans'tan önce test edilmeli, 'paranormal' para ile karışmasın)
    if (/paranormal|komplo teorileri|komplo|gerçek suç|cctv|gizli mikrofon|sızıntı/.test(full)) return 'Gizem, Gerilim & Suç';

    // 6. Psikoloji & Zihin (Oyun'dan önce test edilmeli)
    if (/psikoloji|beden dili|rüya tabir|manipülasyon|bilinçaltı|korku/.test(full)) return 'Psikoloji & Zihin';

    // 7. Felsefe & Kişisel Gelişim
    if (/felsefe|stoa|kişisel gelişim|karakter analizi|kitap özeti|sigma|motivasyon/.test(full)) return 'Felsefe & Kişisel Gelişim';

    // 8. Tarih & Mitoloji
    if (/tarih|mitoloji|medeniyet|arkeoloji|savaş|zaman makinesi|askeri taktik|tarihi şahsiyet/.test(full)) return 'Tarih & Mitoloji';

    // 9. Finans, Ekonomi & İş Dünyası
    if (/finans|kripto|borsa|\bpara\b|ekonomi|iş dünyası|girişim|zengin|şirket|fiyat/.test(full)) return 'Finans, Ekonomi & İş Dünyası';

    // 10. Sağlık, Spor & Fitness
    if (/sağlık|spor|fitness|futbol|beslenme|rekor/.test(full)) return 'Sağlık, Spor & Fitness';

    // 11. Quiz, Zeka & Bulmaca
    if (/quiz|zeka|bulmaca|tahmin|test|would you rather|tercih et|bilmece|illüzyon/.test(full)) return 'Quiz, Zeka & Bulmaca';

    // 12. Oyun & Gaming
    if (/oyun|gaming|easter egg|gameplay|split-screen/.test(full)) return 'Oyun & Gaming';

    // 13. Coğrafya, Seyahat & Kültür
    if (/coğrafya|seyahat|ülke|tehlikeli yerler|yasak|harita/.test(full)) return 'Coğrafya, Seyahat & Kültür';

    // 14. Sinema, Dizi & Sanat
    if (/sinema|dizi|film|sanat|edebiyat|şiir/.test(full)) return 'Sinema, Dizi & Sanat';

    // 15. Ses, Müzik & ASMR
    if (/ses|asmr|müzik|frekans|gece modu|dark mode|rahatlatıcı/.test(full)) return 'Ses, Müzik & ASMR';

    // 16. Doğa & Hayvanlar
    if (/hayvan|doğa|vahşi|deniz|talasofobi/.test(full)) return 'Doğa & Hayvanlar';

    // 17. Sosyal Medya, Mizah & Eğlence
    if (/sosyal|reddit|mizah|eğlence|itiraf|diyalog|röportaj|yorum|durdurma/.test(full)) return 'Sosyal Medya, Mizah & Eğlence';

    // 18. Haber, Gündem & Trendler
    if (/haber|gündem|trend|flaş|son dakika/.test(full)) return 'Haber, Gündem & Trendler';

    // 19. Yaşam, Eğitim & Otomobil
    if (/eğitim|dil|ingilizce|astroloji|otomobil|araba|hukuk|nostalji|hap bilgi/.test(full)) return 'Yaşam, Eğitim & Otomobil';

    return 'Diğer & Genel';
}

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

        // Select dropdown'ları doldur
        selectNiche.innerHTML = '';
        const batchNicheSelect = document.getElementById('batch-default-niche');
        const compareA = document.getElementById('compare-niche-a');
        const compareB = document.getElementById('compare-niche-b');
        const collisionA = document.getElementById('collision-niche-a');
        const collisionB = document.getElementById('collision-niche-b');
        if (batchNicheSelect) batchNicheSelect.innerHTML = '';
        if (compareA) compareA.innerHTML = '';
        if (compareB) compareB.innerHTML = '';
        if (collisionA) collisionA.innerHTML = '';
        if (collisionB) collisionB.innerHTML = '';

        // Başlık etiketini güncelle
        const nicheLabelSpan = document.querySelector('label[for="select-niche"] span:first-child');
        if (nicheLabelSpan) {
            nicheLabelSpan.innerHTML = `<i class="fa-solid fa-shapes text-warning"></i> Niş Şablonu (${allNiches.length} Niş)`;
        }

        // Kategorilere göre grupla ve her kategoride alfabetik sırala
        const nicheGroups = {};
        allNiches.forEach(n => {
            const groupName = getNicheCategoryGroup(n);
            if (!nicheGroups[groupName]) nicheGroups[groupName] = [];
            nicheGroups[groupName].push(n);
        });

        // Kategorileri Türkçe alfabetik sırala
        const sortedGroupNames = Object.keys(nicheGroups).sort((a, b) => a.localeCompare(b, 'tr'));

        sortedGroupNames.forEach(groupName => {
            const groupNiches = nicheGroups[groupName];
            // Kategori içindeki nişleri Türkçe alfabetik sırala
            groupNiches.sort((a, b) => (a.name || '').localeCompare(b.name || '', 'tr'));

            const optgroup = document.createElement('optgroup');
            optgroup.label = `📁 ${groupName} (${groupNiches.length})`;

            groupNiches.forEach(n => {
                const opt = document.createElement('option');
                opt.value = n.id;
                opt.textContent = `${n.name} (${n.category})`;
                optgroup.appendChild(opt);
            });

            selectNiche.appendChild(optgroup);
            if (batchNicheSelect) batchNicheSelect.appendChild(optgroup.cloneNode(true));
            if (compareA) compareA.appendChild(optgroup.cloneNode(true));
            if (compareB) compareB.appendChild(optgroup.cloneNode(true));
            if (collisionA) collisionA.appendChild(optgroup.cloneNode(true));
            if (collisionB) collisionB.appendChild(optgroup.cloneNode(true));
        });

        // Default compare B to second niche
        if (compareB && compareB.options.length > 1) compareB.selectedIndex = 1;
        if (collisionB && collisionB.options.length > 1) collisionB.selectedIndex = 2;

        // Render cards & update stats
        applyNicheFiltersAndRender();
        updateNicheStats(allNiches);
        const savedSettings = restoreStudioSettings();
        const preferredNiche = (savedSettings && savedSettings.niche) || (currentPlan && (currentPlan.niche_id || currentPlan.niche_profile?.id));
        if (preferredNiche && [...selectNiche.options].some(o => o.value === preferredNiche)) {
            selectNiche.value = preferredNiche;
        }
        if (selectNiche.value) await applyNicheProfile(selectNiche.value);
        if (savedSettings?.subtitlePreset && selectSubPreset) selectSubPreset.value = savedSettings.subtitlePreset;
        if (savedSettings?.kenBurns !== undefined && chkKenBurns) chkKenBurns.checked = !!savedSettings.kenBurns;
        if (savedSettings?.splitScreen !== undefined && chkSplitScreen) {
            chkSplitScreen.checked = !!savedSettings.splitScreen;
            if (gameplayCategoryWrap) gameplayCategoryWrap.style.display = savedSettings.splitScreen ? 'block' : 'none';
        }
        if (!userManuallyPickedNiche && !preferredNiche) {
            await resolveAndApplyNicheFromTopic({ toast: false });
        }
    } catch (err) {
        console.error("Niche yükleme hatası:", err);
    }
}

function updateNicheStats(niches) {
    const shown = niches.length;
    const avgViral = shown ? Math.round(niches.reduce((a, n) => a + (n.viral_score || 75), 0) / shown) : '--';
    const topRpm = shown ? niches.reduce((best, n) => {
        const v = parseRpmMax(n.rpm_tier);
        return v > parseRpmMax(best) ? n.rpm_tier : best;
    }, '$0') : '--';
    const tier1Count = niches.filter(n => n.tier1_compatible).length;
    const el1 = document.getElementById('niche-count-shown');
    const el2 = document.getElementById('niche-stat-avg-viral');
    const el3 = document.getElementById('niche-stat-top-rpm');
    const el4 = document.getElementById('niche-stat-tier1');
    if (el1) el1.textContent = shown;
    if (el2) el2.textContent = avgViral;
    if (el3) el3.textContent = topRpm;
    if (el4) el4.textContent = tier1Count;
}

function applyNicheFiltersAndRender() {
    const searchVal = (document.getElementById('niche-search-input')?.value || '').toLowerCase();
    const activeCat = document.querySelector('.filter-pill.active')?.getAttribute('data-cat') || 'all';
    const rpmFilter = document.getElementById('niche-rpm-filter')?.value || 'all';
    const viralFilter = document.getElementById('niche-viral-filter')?.value || 'all';
    const sortBy = document.getElementById('niche-sort-select')?.value || 'viral_score';

    let filtered = allNiches.filter(n => {
        if (searchVal && !(n.name.toLowerCase().includes(searchVal) || n.category.toLowerCase().includes(searchVal))) return false;
        if (activeCat !== 'all' && !n.category.toLowerCase().includes(activeCat.toLowerCase())) return false;
        if (rpmFilter === 'low' && parseRpmMax(n.rpm_tier) > 7) return false;
        if (rpmFilter === 'mid' && (parseRpmMax(n.rpm_tier) < 8 || parseRpmMax(n.rpm_tier) > 15)) return false;
        if (rpmFilter === 'high' && parseRpmMax(n.rpm_tier) < 16) return false;
        if (viralFilter !== 'all' && (n.viral_score || 75) < parseInt(viralFilter)) return false;
        return true;
    });

    // Sort
    filtered.sort((a, b) => {
        if (sortBy === 'viral_score') return (b.viral_score || 75) - (a.viral_score || 75);
        if (sortBy === 'rpm') return parseRpmMax(b.rpm_tier) - parseRpmMax(a.rpm_tier);
        if (sortBy === 'retention') return (b.avg_retention_pct || 70) - (a.avg_retention_pct || 70);
        if (sortBy === 'competition_low') return compToNum(b.competition_level) - compToNum(a.competition_level);
        if (sortBy === 'alphabetic') return a.name.localeCompare(b.name, 'tr');
        return 0;
    });

    renderNicheCards(filtered);
    updateNicheStats(filtered);
}

function getViralScoreColor(score) {
    if (score >= 90) return '#f59e0b'; // gold — elite
    if (score >= 80) return '#10b981'; // green — good
    if (score >= 70) return '#06b6d4'; // cyan — decent
    return '#64748b'; // grey
}

function getCompetitionBadge(level) {
    if (level === 'low') return '<span style="background:rgba(16,185,129,0.15);color:#34d399;border:1px solid rgba(16,185,129,0.3);border-radius:6px;padding:2px 7px;font-size:10px;font-weight:600;">🟢 Az Rekabet</span>';
    if (level === 'medium') return '<span style="background:rgba(245,158,11,0.15);color:#fbbf24;border:1px solid rgba(245,158,11,0.3);border-radius:6px;padding:2px 7px;font-size:10px;font-weight:600;">🟡 Orta Rekabet</span>';
    return '<span style="background:rgba(239,68,68,0.15);color:#f87171;border:1px solid rgba(239,68,68,0.3);border-radius:6px;padding:2px 7px;font-size:10px;font-weight:600;">🔴 Yüksek Rekabet</span>';
}

function getRpmBadgeColor(rpmStr) {
    const max = parseRpmMax(rpmStr);
    if (max >= 16) return { bg: 'rgba(245,158,11,0.15)', color: '#fbbf24', border: 'rgba(245,158,11,0.35)' };
    if (max >= 8) return { bg: 'rgba(16,185,129,0.12)', color: '#34d399', border: 'rgba(16,185,129,0.3)' };
    return { bg: 'rgba(100,116,139,0.15)', color: '#94a3b8', border: 'rgba(100,116,139,0.25)' };
}

function getCtaBadge(cta) {
    const map = { comment: '💬 Yorum', vote: '🗳️ Oylama', save: '🔖 Kaydetme', subscribe: '🔔 Abone' };
    return map[cta] || '💬 Yorum';
}

function renderNicheCards(nichesToRender) {
    const grid = document.getElementById('niches-cards-grid');
    if (!grid) return;
    grid.innerHTML = '';

    if (nichesToRender.length === 0) {
        grid.innerHTML = '<div class="empty-state-box"><i class="fa-solid fa-filter-circle-xmark"></i><p>Filtrelerle eşleşen niş bulunamadı.</p></div>';
        return;
    }

    const isListMode = currentNicheViewMode === 'list';
    grid.className = isListMode ? 'niches-list-view' : 'niches-cards-grid';

    nichesToRender.forEach((n, idx) => {
        const viralScore = n.viral_score || 75;
        const retention = n.avg_retention_pct || 70;
        const viralColor = getViralScoreColor(viralScore);
        const rpmColor = getRpmBadgeColor(n.rpm_tier);
        const rank = idx + 1;
        const isTopTier = viralScore >= 90;

        const card = document.createElement('div');
        card.className = isListMode ? 'niche-card niche-card-list' : 'niche-card niche-card-v2';
        card.setAttribute('data-niche-id', n.id);
        card.style.cssText = `cursor:pointer;transition:all 0.25s cubic-bezier(0.4,0,0.2,1);border:1px solid ${isTopTier ? 'rgba(245,158,11,0.35)' : 'rgba(148,163,184,0.12)'};`;

        card.innerHTML = `
            ${isTopTier ? `<div style="position:absolute;top:-1px;right:14px;background:linear-gradient(135deg,#f59e0b,#f97316);color:#000;font-size:9px;font-weight:800;padding:3px 10px;border-radius:0 0 8px 8px;letter-spacing:0.5px;text-transform:uppercase;">⭐ Elite</div>` : ''}
            <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;margin-bottom:10px;">
                <div style="display:flex;gap:10px;align-items:center;flex:1;min-width:0;">
                    <div style="width:38px;height:38px;border-radius:10px;background:linear-gradient(135deg,${viralColor}22,${viralColor}44);border:1px solid ${viralColor}44;display:flex;align-items:center;justify-content:center;flex-shrink:0;">
                        <i class="fa-solid ${n.icon || 'fa-fire'}" style="color:${viralColor};font-size:15px;"></i>
                    </div>
                    <div style="flex:1;min-width:0;">
                        <h4 style="margin:0;font-size:13px;font-weight:700;color:#e2e8f0;line-height:1.3;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${escapeHtml(n.name)}">${escapeHtml(n.name)}</h4>
                        <span style="font-size:10px;color:#64748b;">${escapeHtml(n.category)}</span>
                    </div>
                </div>
                <div style="display:flex;flex-direction:column;align-items:flex-end;gap:4px;flex-shrink:0;">
                    <div style="font-size:18px;font-weight:800;color:${viralColor};line-height:1;">${viralScore}</div>
                    <div style="font-size:9px;color:#64748b;text-align:right;">Viral Score</div>
                </div>
            </div>

            <!-- Viral Score Bar -->
            <div style="margin-bottom:10px;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
                    <span style="font-size:10px;color:#64748b;">🔥 Viral Potansiyel</span>
                    <span style="font-size:10px;color:${viralColor};font-weight:600;">${viralScore}/100</span>
                </div>
                <div style="height:4px;background:rgba(148,163,184,0.15);border-radius:4px;overflow:hidden;">
                    <div class="niche-score-bar" style="height:100%;width:0%;background:linear-gradient(90deg,${viralColor}aa,${viralColor});border-radius:4px;transition:width 0.8s ease;" data-target="${viralScore}"></div>
                </div>
            </div>

            <!-- Key Metrics Row -->
            <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px;margin-bottom:10px;">
                <div style="background:${rpmColor.bg};border:1px solid ${rpmColor.border};border-radius:7px;padding:5px 7px;text-align:center;">
                    <div style="font-size:11px;font-weight:700;color:${rpmColor.color};">${escapeHtml(n.rpm_tier || '$2-5')}</div>
                    <div style="font-size:9px;color:#64748b;">RPM</div>
                </div>
                <div style="background:rgba(6,182,212,0.08);border:1px solid rgba(6,182,212,0.2);border-radius:7px;padding:5px 7px;text-align:center;">
                    <div style="font-size:11px;font-weight:700;color:#67e8f9;">${retention}%</div>
                    <div style="font-size:9px;color:#64748b;">Retention</div>
                </div>
                <div style="background:rgba(148,163,184,0.06);border:1px solid rgba(148,163,184,0.15);border-radius:7px;padding:5px 7px;text-align:center;">
                    <div style="font-size:10px;font-weight:600;color:#94a3b8;">${getCtaBadge(n.cta_type)}</div>
                    <div style="font-size:9px;color:#64748b;">CTA Türü</div>
                </div>
            </div>

            <!-- Badges Row -->
            <div style="display:flex;flex-wrap:wrap;gap:5px;margin-bottom:10px;">
                ${getCompetitionBadge(n.competition_level)}
                ${n.tier1_compatible ? '<span style="background:rgba(6,182,212,0.12);color:#67e8f9;border:1px solid rgba(6,182,212,0.25);border-radius:6px;padding:2px 7px;font-size:10px;">🌍 Tier-1</span>' : ''}
                ${n.has_split_screen ? '<span style="background:rgba(139,92,246,0.12);color:#c4b5fd;border:1px solid rgba(139,92,246,0.25);border-radius:6px;padding:2px 7px;font-size:10px;">🎮 Split-Screen</span>' : ''}
                ${n.episodic_capable ? '<span style="background:rgba(16,185,129,0.1);color:#6ee7b7;border:1px solid rgba(16,185,129,0.2);border-radius:6px;padding:2px 7px;font-size:10px;">📺 Seri</span>' : ''}
            </div>

            <!-- Best Posting Time -->
            <div style="font-size:10px;color:#64748b;margin-bottom:10px;">
                🕐 En İyi: <span style="color:#94a3b8;">${escapeHtml(n.best_posting_time || '12:00-15:00 TRT')}</span>
            </div>

            <!-- Action Buttons -->
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:6px;">
                <button class="btn btn-primary niche-use-btn" data-niche-id="${n.id}" style="font-size:11px;padding:7px 10px;" onclick="event.stopPropagation()">
                    <i class="fa-solid fa-arrow-right"></i> Bu Nişle Üret
                </button>
                <button class="btn btn-secondary niche-detail-btn" data-niche-id="${n.id}" style="font-size:11px;padding:7px 10px;" onclick="event.stopPropagation()">
                    <i class="fa-solid fa-expand"></i> Detay & A/B
                </button>
            </div>
        `;

        // Click card body → open modal
        card.addEventListener('click', () => openNicheModal(n.id));
        grid.appendChild(card);
    });

    // Animate viral score bars after render
    requestAnimationFrame(() => {
        document.querySelectorAll('.niche-score-bar').forEach(bar => {
            bar.style.width = bar.getAttribute('data-target') + '%';
        });
    });

    // Action button events
    grid.querySelectorAll('.niche-use-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const nId = e.currentTarget.getAttribute('data-niche-id');
            const selected = allNiches.find(x => x.id === nId);
            if (selected) {
                selectNiche.value = selected.id;
                applyNicheProfile(selected.id);
                // Seed topic from niche hook if empty or generic
                const hook = (selected.hook_style || selected.name || '').trim();
                if (hook && inputTopic) {
                    const cur = inputTopic.value.trim();
                    if (!cur || cur.length < 8) {
                        inputTopic.value = hook.length > 120 ? hook.slice(0, 117) + '...' : hook;
                    }
                }
                switchTab('studio');
                updateFlowRail('topic');
                showToast(`Nis secildi: ${selected.name} — konuyu netlestirip senaryo uretin`);
            }
        });
    });

    grid.querySelectorAll('.niche-detail-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            openNicheModal(e.currentTarget.getAttribute('data-niche-id'));
        });
    });
}

// ── Niche Detail Modal ──
async function openNicheModal(nicheId) {
    currentModalNicheId = nicheId;
    const n = allNiches.find(x => x.id === nicheId);
    if (!n) return;
    const modal = document.getElementById('niche-detail-modal');
    const viralColor = getViralScoreColor(n.viral_score || 75);
    const rpmC = getRpmBadgeColor(n.rpm_tier);

    // Icon wrap
    const iconWrap = document.getElementById('niche-modal-icon-wrap');
    iconWrap.style.background = `linear-gradient(135deg,${viralColor}44,${viralColor}66)`;
    iconWrap.innerHTML = `<i class="fa-solid ${n.icon || 'fa-fire'}"></i>`;

    // Title
    document.getElementById('niche-modal-title').textContent = n.name;

    // Badges
    document.getElementById('niche-modal-badges').innerHTML = `
        <span class="niche-tag">${escapeHtml(n.category)}</span>
        ${getCompetitionBadge(n.competition_level)}
        ${n.tier1_compatible ? '<span style="background:rgba(6,182,212,0.12);color:#67e8f9;border:1px solid rgba(6,182,212,0.25);border-radius:6px;padding:2px 8px;font-size:11px;">🌍 Tier-1</span>' : ''}
    `;

    // Stats
    document.getElementById('niche-modal-stats').innerHTML = `
        <div style="display:flex;flex-direction:column;gap:10px;">
            ${[
                ['🔥 Viral Skor', `<span style="color:${viralColor};font-weight:800;font-size:20px;">${n.viral_score || 75}</span><span style="color:#64748b;font-size:12px;">/100</span>`, viralColor],
                ['💰 RPM Bandı', `<span style="color:${rpmC.color};font-weight:700;">${escapeHtml(n.rpm_tier || '$2-5')}</span>`, rpmC.color],
                ['👁 Ort. Retention', `<span style="color:#67e8f9;font-weight:700;">${n.avg_retention_pct || 70}%</span>`, '#67e8f9'],
                ['🕐 En İyi Paylaşım', `<span style="color:#94a3b8;font-size:12px;">${escapeHtml(n.best_posting_time || '--')}</span>`, '#94a3b8'],
                ['🎯 CTA Türü', `<span style="color:#c4b5fd;">${getCtaBadge(n.cta_type)}</span>`, '#c4b5fd'],
                ['📺 Seri Formatı', n.episodic_capable ? '<span style="color:#34d399;">✅ Uygun</span>' : '<span style="color:#64748b;">❌ Değil</span>', '#34d399'],
            ].map(([label, val]) => `
                <div style="display:flex;justify-content:space-between;align-items:center;padding:8px 12px;background:rgba(15,23,42,0.5);border-radius:8px;border:1px solid rgba(148,163,184,0.08);">
                    <span style="font-size:12px;color:#64748b;">${label}</span>
                    <span style="font-size:13px;">${val}</span>
                </div>
            `).join('')}
        </div>
    `;

    // Keywords
    document.getElementById('niche-modal-keywords').innerHTML = (n.trending_keywords || []).map(kw =>
        `<span style="background:rgba(6,182,212,0.1);color:#67e8f9;border:1px solid rgba(6,182,212,0.2);border-radius:20px;padding:3px 10px;font-size:11px;">${escapeHtml(kw)}</span>`
    ).join('');

    // A/B Hooks
    const abColors = ['#10b981', '#f59e0b', '#8b5cf6'];
    const abLabels = ['A — Merak Kancası', 'B — Şok Kancası', 'C — Tartışma Kancası'];
    const hooks = n.ab_test_hook_variants || [n.hook_style || ''];
    document.getElementById('niche-modal-ab-hooks').innerHTML = hooks.slice(0, 3).map((hook, i) => `
        <div style="margin-bottom:10px;padding:12px;background:rgba(${i===0?'16,185,129':i===1?'245,158,11':'139,92,246'},0.08);border:1px solid rgba(${i===0?'16,185,129':i===1?'245,158,11':'139,92,246'},0.2);border-radius:10px;">
            <div style="font-size:10px;font-weight:700;color:${abColors[i]};text-transform:uppercase;letter-spacing:0.5px;margin-bottom:6px;">${abLabels[i]}</div>
            <div style="font-size:12px;color:#cbd5e1;line-height:1.5;">"${escapeHtml(hook)}"</div>
            <button class="ab-hook-use-btn" data-hook="${escapeHtml(hook)}" style="margin-top:8px;background:rgba(${i===0?'16,185,129':i===1?'245,158,11':'139,92,246'},0.15);border:1px solid rgba(${i===0?'16,185,129':i===1?'245,158,11':'139,92,246'},0.3);color:${abColors[i]};border-radius:6px;padding:4px 10px;font-size:11px;cursor:pointer;">
                Bu Kancayı Kullan
            </button>
        </div>
    `).join('');

    // Trends placeholder
    document.getElementById('niche-modal-trends').innerHTML = '<div style="color:#64748b;font-size:12px;padding:8px;">Yükleniyor...</div>';

    // Show modal
    modal.style.display = 'block';

    // Setup use button
    document.getElementById('btn-modal-use-niche').onclick = () => {
        selectNiche.value = nicheId;
        applyNicheProfile(nicheId);
        const hook = (n.hook_style || n.name || '').trim();
        if (hook && inputTopic && (!inputTopic.value.trim() || inputTopic.value.trim().length < 8)) {
            inputTopic.value = hook.length > 120 ? hook.slice(0, 117) + '...' : hook;
        }
        switchTab('studio');
        updateFlowRail('topic');
        closeNicheModal();
        showToast(`Nis: ${n.name} — konuyu duzenleyip senaryo uretin`);
    };

    // AB hook use buttons
    document.querySelectorAll('.ab-hook-use-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const hook = e.currentTarget.getAttribute('data-hook');
            if (inputTopic) inputTopic.value = hook;
            showToast('🧪 A/B kanca konuya aktarıldı!');
        });
    });

    // Load trending topics
    loadModalTrends(nicheId);

    // Setup reload trends button
    document.getElementById('btn-modal-load-trends').onclick = () => loadModalTrends(nicheId);
}

async function loadModalTrends(nicheId) {
    const trendsEl = document.getElementById('niche-modal-trends');
    if (!trendsEl) return;
    trendsEl.innerHTML = '<div style="color:#64748b;font-size:12px;padding:8px;"><i class="fa-solid fa-spinner fa-spin"></i> Trend konular aranıyor...</div>';
    try {
        const res = await fetch(`/api/niches/${encodeURIComponent(nicheId)}/trending_topics`);
        const data = await res.json();
        const topics = data.topics || [];
        if (topics.length === 0) {
            trendsEl.innerHTML = '<div style="color:#64748b;font-size:12px;padding:8px;">Trend bulunamadı.</div>';
            return;
        }
        trendsEl.innerHTML = topics.slice(0, 5).map(t => `
            <div style="padding:8px;border-bottom:1px solid rgba(148,163,184,0.08);cursor:pointer;transition:background 0.15s;" 
                 class="trend-topic-row"
                 onclick="(function(){ document.getElementById('input-topic').value='${escapeHtml(t.title).replace(/'/g, "\\'")}'; })()">
                <div style="font-size:11px;color:#cbd5e1;line-height:1.4;">${escapeHtml(t.title)}</div>
                <div style="font-size:10px;color:#64748b;margin-top:2px;">${escapeHtml(t.view_count_text || '')}</div>
            </div>
        `).join('');
    } catch(e) {
        trendsEl.innerHTML = '<div style="color:#64748b;font-size:12px;padding:8px;">Trend yüklenemedi.</div>';
    }
}

function closeNicheModal() {
    const modal = document.getElementById('niche-detail-modal');
    if (modal) modal.style.display = 'none';
    currentModalNicheId = null;
}

document.getElementById('btn-close-niche-modal')?.addEventListener('click', closeNicheModal);
document.getElementById('niche-detail-modal')?.addEventListener('click', (e) => {
    if (e.target === e.currentTarget) closeNicheModal();
});

// ── Filter Pills (Delegated) ──
document.addEventListener('click', (e) => {
    const pill = e.target.closest('.filter-pill');
    if (pill) {
        document.querySelectorAll('.filter-pill').forEach(b => b.classList.remove('active'));
        pill.classList.add('active');
        applyNicheFiltersAndRender();
    }
});

// ── Search / Sort / Filter change handlers ──
document.getElementById('niche-search-input')?.addEventListener('input', applyNicheFiltersAndRender);
document.getElementById('niche-sort-select')?.addEventListener('change', applyNicheFiltersAndRender);
document.getElementById('niche-rpm-filter')?.addEventListener('change', applyNicheFiltersAndRender);
document.getElementById('niche-viral-filter')?.addEventListener('change', applyNicheFiltersAndRender);

// ── View Mode Toggle ──
document.getElementById('btn-niche-view-grid')?.addEventListener('click', () => {
    currentNicheViewMode = 'grid';
    applyNicheFiltersAndRender();
});
document.getElementById('btn-niche-view-list')?.addEventListener('click', () => {
    currentNicheViewMode = 'list';
    applyNicheFiltersAndRender();
});

// ── Compare Tool ──
document.getElementById('btn-compare-niches')?.addEventListener('click', async () => {
    const a = document.getElementById('compare-niche-a')?.value;
    const b = document.getElementById('compare-niche-b')?.value;
    const resultEl = document.getElementById('compare-result');
    if (!a || !b || !resultEl) return;
    if (a === b) { showToast('⚠️ Aynı nişi karşılaştıramazsın!'); return; }
    resultEl.style.display = 'block';
    resultEl.innerHTML = '<div style="color:#64748b;font-size:12px;"><i class="fa-solid fa-spinner fa-spin"></i> Karşılaştırılıyor...</div>';
    try {
        const res = await fetch('/api/niches/compare', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({niche_a: a, niche_b: b}) });
        const data = await res.json();
        if (data.status !== 'ok') { resultEl.innerHTML = '<div style="color:#f87171;font-size:12px;">Hata oluştu.</div>'; return; }
        const na = data.niche_a, nb = data.niche_b;
        const winnerName = allNiches.find(x => x.id === data.overall_winner)?.name || data.overall_winner;
        const dims = [
            ['🔥 Viral Skor', na.viral_score, nb.viral_score, 'viral_score'],
            ['👁 Retention', na.avg_retention_pct + '%', nb.avg_retention_pct + '%', 'avg_retention_pct'],
            ['🌍 Tier-1', na.tier1_compatible ? '✅' : '❌', nb.tier1_compatible ? '✅' : '❌', 'tier1'],
        ];
        resultEl.innerHTML = `
            <div style="font-size:11px;font-weight:700;color:#10b981;margin-bottom:8px;text-align:center;">🏆 Kazanan: ${escapeHtml(winnerName)}</div>
            <table style="width:100%;font-size:11px;border-collapse:collapse;">
                <thead><tr><th style="color:#64748b;text-align:left;padding:3px 0;">Metrik</th><th style="color:#67e8f9;text-align:center;">${escapeHtml(na.name.split('&')[0].trim())}</th><th style="color:#c4b5fd;text-align:center;">${escapeHtml(nb.name.split('&')[0].trim())}</th></tr></thead>
                <tbody>
                    ${dims.map(([label, va, vb, dim]) => {
                        const win = data.winner_per_dimension[dim];
                        return `<tr><td style="color:#64748b;padding:3px 0;">${label}</td>
                            <td style="text-align:center;color:${win===a?'#34d399':'#cbd5e1'};font-weight:${win===a?'700':'400'};">${va}</td>
                            <td style="text-align:center;color:${win===b?'#34d399':'#cbd5e1'};font-weight:${win===b?'700':'400'};">${vb}</td></tr>`;
                    }).join('')}
                </tbody>
            </table>
        `;
    } catch(e) { resultEl.innerHTML = '<div style="color:#f87171;font-size:12px;">Bağlantı hatası.</div>'; }
});

// ── Collision Engine ──
document.getElementById('btn-collide-niches')?.addEventListener('click', async () => {
    const a = document.getElementById('collision-niche-a')?.value;
    const b = document.getElementById('collision-niche-b')?.value;
    const resultEl = document.getElementById('collision-result');
    if (!a || !b || !resultEl) return;
    if (a === b) { showToast('⚠️ Farklı iki niş seç!'); return; }
    resultEl.style.display = 'block';
    resultEl.innerHTML = '<div style="color:#64748b;font-size:12px;"><i class="fa-solid fa-spinner fa-spin"></i> Melezleniyor...</div>';
    try {
        const res = await fetch('/api/niches/collision', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({niche_a: a, niche_b: b}) });
        const data = await res.json();
        if (data.status !== 'ok') { resultEl.innerHTML = '<div style="color:#f87171;font-size:12px;">Hata.</div>'; return; }
        const c = data.collision;
        resultEl.innerHTML = `
            <div style="background:linear-gradient(135deg,rgba(139,92,246,0.1),rgba(244,63,94,0.05));border:1px solid rgba(139,92,246,0.25);border-radius:10px;padding:12px;">
                <div style="font-size:13px;font-weight:700;color:#c4b5fd;margin-bottom:8px;">⚡ ${escapeHtml(c.name)}</div>
                <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px;">
                    <span style="font-size:11px;color:#f59e0b;">🔥 Viral: ${c.blended_viral_score}/100</span>
                    <span style="font-size:11px;color:#67e8f9;">👁 Ret: ${c.blended_retention}%</span>
                </div>
                <div style="font-size:11px;color:#94a3b8;margin-bottom:8px;font-style:italic;">"${escapeHtml(c.collision_hook_variants?.[0] || '')}"</div>
                <button onclick="(function(){
                    const sel = document.getElementById('select-niche');
                    if(sel){ sel.value='${a}'; }
                    const topicEl = document.getElementById('input-topic');
                    if(topicEl){ topicEl.value='${escapeHtml(c.name).replace(/'/g,"\\'")}'; }
                    window.dispatchEvent(new CustomEvent('applyNicheProfile',{detail:'${a}'}));
                    document.querySelector('[data-tab=studio]')?.click();
                })()" style="width:100%;background:rgba(139,92,246,0.2);border:1px solid rgba(139,92,246,0.35);color:#c4b5fd;border-radius:7px;padding:6px;font-size:11px;cursor:pointer;">
                    🚀 Bu Melezle Stüdyoya Git
                </button>
            </div>
        `;
    } catch(e) { resultEl.innerHTML = '<div style="color:#f87171;font-size:12px;">Bağlantı hatası.</div>'; }
});



// ══════════════════════════════════════════════════════════════

