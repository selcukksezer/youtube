/**
 * ShortsAI Studio — AI Helper Actions, Viral Audit, Research & Advanced Engines (studio-ai-tools.js)
 * Handles topic banks, trend/gap/Reddit research, quick action strip, and advanced AI production tools.
 */

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

const NICHE_SAMPLE_TOPICS = {
    'en': {
        '7_dark_psychology': '3 Dark Psychology Secrets Manipulation Experts Never Tell You',
        '6_stoic_philosophy': 'Marcus Aurelius: 3 Stoic Rules That Destroy Anger and Anxiety',
        '1_news_flash': 'BREAKING: Urgent Global Market Shift Shocking Financial Analysts Today',
        '2_reddit_confessions': 'I Found My Boss In A Secret Meeting He Did Not Know I Was Listening',
        '3_split_gameplay': 'Minecraft Parkour: 3 Psychological Life Hacks That Change Everything',
        '4_would_you_rather': 'Would You Rather: 10 Million Dollars Right Now or Travel Back to 2010?',
        '5_guess_flag_country': 'Can You Guess The Country From These 3 Surprising Clues in 5 Seconds?',
        '8_crypto_market': 'Bitcoin Whale Alert: 3 Massive Crypto Signals Everyone is Missing',
        '9_five_facts': '5 Mind-Blowing Facts About Space That Scientists Cannot Explain',
        '10_religious_quotes': '3 Islamic Lessons on Patience and Inner Peace That Transform Your Heart',
        '11_language_learning': '5 English Idioms That Native Speakers Use Daily But You Were Never Taught',
        '12_amazon_affiliate': '3 Viral Amazon Gadgets You Actually Need Under $25',
        '13_mystery_paranormal': 'The Terrifying Mystery of The Bridgewater Triangle No One Solved',
        '14_movie_summaries': 'The Ending of Inception Finally Explained: Was He Still In A Dream?',
        '15_football_transfers': 'The Most Shocking 100 Million Transfer In Football History',
        '16_wealth_entrepreneurship': 'How A 21-Year Old Built An 8-Figure Empire With Zero Experience',
        '17_before_after_evolution': 'How Earth Looked 100 Million Years Ago vs How It Looks Today',
        '18_astrology_horoscope': 'The 3 Most Dangerous Zodiac Signs When Provoked to Anger',
        '19_historical_battles': 'The Clever Military Tactic That Won The Battle of Marathon Against All Odds',
        '20_whatsapp_chat_story': 'Scary WhatsApp Text Messages Sent At 3 AM That Chilled Me To The Bone',
        '21_ai_tools_hacks': '3 Free AI Tools That Are So Powerful They Almost Feel Illegal',
        '22_emoji_guess_game': 'Guess The Famous Hollywood Movie Using Only These 3 Emojis',
        '23_fitness_nutrition_hacks': '3 High-Protein Breakfast Hacks That Burn Belly Fat Effortlessly',
        '24_sigma_character_study': 'The Silent Rule of The Sigma Mindset That Makes You Unstoppable',
        '25_celebrity_net_worth': 'How Keanu Reeves Secretly Spends His Millions Helping Others',
        '26_dangerous_places': 'The Deadliest Island On Earth Where Humans Are Forbidden To Visit',
        '27_common_myths_busted': '5 Scientific Myths You Still Believe That Are Completely False',
        '28_dream_meanings': 'What It Really Means When You Fall or Fly In Your Dreams',
        '29_optical_illusions_iq': 'Only 1% of Geniuses Can Spot The Hidden Animal In This Image in 5 Seconds',
        '30_poetry_quotes': 'The Most Heartbreaking Quote About Love That Will Stay With You Forever',
        '31_supercars_automotive': 'The Secret Engineering Reason Bugatti Chiron Can Exceed 300 MPH',
        '32_legal_consumer_hacks': '3 Hidden Consumer Rights Stores Never Want You To Know About',
        '33_parenting_child_hacks': 'The 3-Second Phrase Child Psychologists Use To Stop Tantrums Instantly',
        '34_gaming_easter_eggs': '5 Insane GTA Secrets That Took Players Over 10 Years To Find',
        '35_animal_kingdom_stories': "The Deadliest Predator In The Ocean Isn't A Great White Shark",
        '36_kids_animation': 'Learn The Colors and Animals Fun Adventure for Kids',
        '37_interactive_quiz': '99% of People Fail This 3-Question Common Sense Trivia Quiz',
    },
    'tr': {
        '6_stoic_philosophy': "Marcus Aurelius'un Öfkeyi Yok Eden 3 Stoacı Kuralı",
        '7_dark_psychology': 'Karanlık Psikolojinin En Tehlikeli 3 Manipülasyon Sırrı',
        '1_news_flash': 'SON DAKİKA: Piyasaları Sarsan Kritik Açıklama ve Flaş Gelişmeler',
        '2_reddit_confessions': 'Patronumun Gizli Toplantısını Yanlışlıkla Dinledim ve Hayatım Değişti',
        '3_split_gameplay': 'Minecraft Parkur Eşliğinde İnsan Psikolojisinin 3 Tuhaf Kuralı',
        '4_would_you_rather': 'Hangisini Seçerdin: Hemen 10 Milyon Dolar mı, 10 Yıl Geriye Gitmek mi?',
        '5_guess_flag_country': 'Bu 3 İpucundan Hangi Ülke Olduğunu 5 Saniyede Tahmin Edebilir misin?',
        '8_crypto_market': 'Bitcoin ve Kriptoda Balinaların Gizlice Topladığı 3 Kritik Gösterge',
        '9_five_facts': 'Evren Hakkında Bilim İnsanlarının Bile Açıklayamadığı 5 Büyüleyici Gerçek',
        '10_religious_quotes': 'Kalbe Huzur Veren ve Sabrı Öğreten 3 Manevi Ayet ve Hadis',
        '11_language_learning': 'Ana Dili İngilizce Olanların Sürekli Kullandığı 5 Harika Deyim',
        '12_amazon_affiliate': 'Hayatınızı Kolaylaştıracak 3 Viral Amazon Ürünü',
        '13_mystery_paranormal': 'Bermuda Şeytan Üçgeni Hakkında Kimsenin Açıklayamadığı 3 Gizemli Olay',
        '14_movie_summaries': 'Inception Filminin Gerçek Sonu: Fırıldak Aslında Duruyor mu?',
        '15_football_transfers': 'Futbol Tarihinin En Pahalı ve En Şok Edici 3 Transfer Skandalı',
        '16_wealth_entrepreneurship': 'Sıfır Sermaye ile Milyon Dolarlık Şirket Kuran Girişimcinin 3 Sırrı',
        '17_before_after_evolution': '100 Yıl Önceki Dünya ile Günümüz Dünyasının Şaşırtıcı Karşılaştırması',
        '18_astrology_horoscope': 'Öfkesi En Korkunç 3 Burç: Sakın Onları Çileden Çıkarmayın!',
        '19_historical_battles': 'Tarihin Akışını Değiştiren En Zekice 3 Askeri Savaş Taktiği',
        '20_whatsapp_chat_story': "Gece 03:00'te Gelen Gizemli WhatsApp Mesajları ve Tüyler Ürperten Son",
        '21_ai_tools_hacks': 'Kullanması Yasa Dışı Gibi Gelen 3 Harika Ücretsiz Yapay Zeka Aracı',
        '22_emoji_guess_game': 'Sadece Bu 3 Emojiden Hangi Efsane Filmi Anlatıyoruz? Tahmin Et!',
        '23_fitness_nutrition_hacks': 'Göbek Yağlarını Hızla Eriten ve Tok Tutan 3 Kahvaltı Sırrı',
        '24_sigma_character_study': 'Sigma Karakterinin Asla Taviz Vermediği 3 Sessiz Kural',
        '25_celebrity_net_worth': 'Keanu Reeves Servetini Nasıl Harcıyor? Şaşırtıcı Gerçekler',
        '26_dangerous_places': 'Dünyanın En Tehlikeli Yılan Adası: İnsanların Girişi Neden Yasak?',
        '27_common_myths_busted': 'Doğru Bildiğiniz Ama Tamamen Yanlış Olan 5 Bilimsel Efsane',
        '28_dream_meanings': 'Rüyada Yüksekten Düşmenin veya Uçmanın Gerçek Psikolojik Anlamı',
        '29_optical_illusions_iq': "Bu Görseldeki Gizli Hayvanı Sadece Yüksek IQ'ya Sahip Olanlar 5 Saniyede Buluyor",
        '30_poetry_quotes': "Nazım Hikmet ve Cemal Süreya'dan Kalbe Dokunan En Güzel Aşk Sözleri",
        '31_supercars_automotive': "Bugatti Chiron'un 400 km Hıza Ulaşmasını Sağlayan İnanılmaz Mühendislik",
        '32_legal_consumer_hacks': 'Mağazaların ve Şirketlerin Sizden Sakladığı 3 Tüketici Hakkı',
        '33_parenting_child_hacks': 'Çocuk Psikologlarının Ağlama Krizini Bitirmek İçin Kullandığı 3 Saniye Kuralı',
        '34_gaming_easter_eggs': "GTA 5'te 10 Yıldır Gizli Kalan En Korkunç 5 Easter Egg",
        '35_animal_kingdom_stories': 'Okyanusların En Acımasız Avcısı Katil Balinaların Şok Eden Taktikleri',
        '36_kids_animation': 'Sevimli Hayvanlar ve Renkleri Öğreniyoruz Çocuk Şarkısı',
        '37_interactive_quiz': "İnsanların %95'inin Yanıldığı 3 Soruluk Mantık ve Genel Kültür Testi",
    }
};

function isTopicSampleOrEmpty(val) {
    if (!val || !val.trim()) return true;
    const clean = val.trim().toLowerCase();
    for (const lang of ['en', 'tr']) {
        for (const key in NICHE_SAMPLE_TOPICS[lang]) {
            if (NICHE_SAMPLE_TOPICS[lang][key].toLowerCase() === clean) return true;
        }
    }
    if (clean.includes("marcus aurelius") || clean.includes("dark psychology secrets") || clean.includes("öfkeyi yok eden") || clean.includes("#shorts")) return true;
    return false;
}

document.getElementById('btn-load-niche-trends')?.addEventListener('click', async (event) => {
    const nicheId = window.selectNiche?.value;
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
        const isRealYoutube = Boolean(data.is_real_youtube);
        const badgeIcon = isRealYoutube ? 'fa-brands fa-youtube' : 'fa-solid fa-wand-magic-sparkles';
        const badgeBg = isRealYoutube ? 'rgba(30,58,138,0.4)' : 'rgba(88,28,135,0.35)';
        const badgeBorder = isRealYoutube ? 'rgba(96,165,250,0.3)' : 'rgba(192,132,252,0.35)';
        const badgeColor = isRealYoutube ? '#93c5fd' : '#e9d5ff';
        const sourceBadge = data.source_label ?
            `<div style="display:inline-flex; align-items:center; gap:6px; background:${badgeBg}; border:1px solid ${badgeBorder}; color:${badgeColor}; padding:4px 10px; border-radius:6px; font-size:11px; margin-bottom:8px;">
                <i class="${badgeIcon}"></i> <span>${escapeHtml(data.source_label)}</span>
            </div>` : '';
        window.lastTrendResults = data.trends || [];
        window.trendFormatFingerprintAggregate = data.format_fingerprint || null;
        const listIntro = isRealYoutube
            ? 'Son 24 saatte yayınlanan, görüntülenmeye göre sıralı YouTube başlık sinyalleri (tıklayarak konuya aktarın):'
            : 'YouTube verisi bulunamadı — nişe uygun AI başlık önerileri (tıklayarak konuya aktarın):';
        results.innerHTML = `
            ${sourceBadge}
            <div style="font-size: 11px; color: #67e8f9; margin: 2px 0 8px 0;">${listIntro}</div>
            ${window.lastTrendResults.map((trend, index) => {
                const viewsStr = trend.view_count_text || (typeof trend.view_count === 'number' && trend.view_count > 0 ? Number(trend.view_count).toLocaleString('tr-TR') + ' görüntülenme' : '');
                const metaLine = isRealYoutube && trend.channel
                    ? `<i class="fa-brands fa-youtube text-danger" style="margin-right:3px;"></i>${escapeHtml(trend.channel)}${viewsStr ? ` · ${escapeHtml(viewsStr)}` : ''}`
                    : `<i class="fa-solid fa-wand-magic-sparkles" style="margin-right:3px; color:#c4b5fd;"></i>AI öneri`;
                return `
                <button class="trend-topic-option" data-topic="${escapeHtml(trend.title)}" data-trend-index="${index}" style="display:block; width:100%; text-align:left; padding:9px 12px; margin-bottom:6px; border-radius:6px; background:rgba(15,23,42,.75); border:1px solid rgba(148,163,184,.18); color:#e2e8f0; cursor:pointer; transition:all 0.15s ease;">
                    <strong style="font-size:12px; color:#f8fafc;">${index + 1}. ${escapeHtml(trend.title)}</strong><br>
                    <span style="font-size:10px; color:#94a3b8;">${metaLine}</span>
                </button>
                `;
            }).join('')}
        `;
        results.querySelectorAll('.trend-topic-option').forEach(option => {
            option.addEventListener('click', () => {
                window.suppressFingerprintClear = true;
                if (window.inputTopic) window.inputTopic.value = option.dataset.topic;
                const idx = Number(option.dataset.trendIndex);
                const picked = window.lastTrendResults[idx];
                setPendingFormatFingerprint(picked?.format_fingerprint || window.trendFormatFingerprintAggregate);
                if (typeof updateLoopBridge === 'function') updateLoopBridge(nicheId, window.inputTopic?.value || '');
                updateFlowRail('topic');
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
    const nicheId = window.selectNiche?.value;
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
        const gapFingerprint = data.format_fingerprint || null;
        results.innerHTML = data.suggestions.length ? data.suggestions.map(suggestion => `
            <button class="trend-topic-option content-gap-option" data-topic="${escapeHtml(suggestion.topic)}" style="display:block; width:100%; text-align:left; padding:8px; margin-bottom:5px; border-radius:6px; background:rgba(15,23,42,.7); border:1px solid rgba(251,191,36,.2); color:#e2e8f0; cursor:pointer;">
                <strong style="font-size:12px;">${escapeHtml(suggestion.topic)}</strong>
                <span style="float:right; font-size:10px; color:#fbbf24;">Uygunluk ${suggestion.relevance}/100</span>
            </button>`).join('') : '<div class="alert-info-box">Kullanılabilir konu bulunamadı.</div>';
        results.querySelectorAll('.content-gap-option').forEach(option => option.addEventListener('click', () => {
            window.suppressFingerprintClear = true;
            if (window.inputTopic) window.inputTopic.value = option.dataset.topic;
            setPendingFormatFingerprint(gapFingerprint);
            if (typeof updateLoopBridge === 'function') updateLoopBridge(nicheId, window.inputTopic?.value || '');
            updateFlowRail('topic');
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
    if (!results) return;
    button.disabled = true;
    button.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Keşfediliyor...';
    try {
        const currentLang = document.getElementById('select-language')?.value || 'tr';
        const response = await fetch(`/api/research/reddit?subreddit=${encodeURIComponent(subreddit)}&lang=${encodeURIComponent(currentLang)}`);
        const data = await response.json();
        if (!response.ok || data.status !== 'ok') throw new Error(data.detail || 'Reddit gönderileri alınamadı.');

        let modeBadge = '<span class="badge" style="background: rgba(168, 85, 247, 0.2); color: #c084fc; font-size: 10px; padding: 2px 6px; border-radius: 4px;"><i class="fa-solid fa-wand-magic-sparkles"></i> Viral Arşiv Rotasyonu</span>';
        if (data.mode === 'oauth') {
            modeBadge = '<span class="badge" style="background: rgba(16, 185, 129, 0.2); color: #34d399; font-size: 10px; padding: 2px 6px; border-radius: 4px;"><i class="fa-solid fa-key"></i> Resmi OAuth API</span>';
        } else if (data.mode === 'ai_discovery') {
            modeBadge = '<span class="badge" style="background: rgba(245, 158, 11, 0.2); color: #fbbf24; font-size: 10px; padding: 2px 6px; border-radius: 4px;"><i class="fa-solid fa-sparkles"></i> Canlı AI Keşif (Taze İçerik)</span>';
        }

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
            window.selectedRedditPost = data.posts[Number(option.dataset.index)];
            if (window.inputTopic) window.inputTopic.value = window.selectedRedditPost.title;
            if (typeof updateLoopBridge === 'function') updateLoopBridge('2_reddit_confessions', window.inputTopic?.value || '');
            showToast('Reddit viral hikayesi seçildi. İlk sahneye kaynak kartı eklenecek ve metin insanlaştırılacak.');
        }));
    } catch (error) {
        results.innerHTML = `<div class="alert-info-box text-danger" style="font-size: 11px;">⚠️ ${escapeHtml(error.message)}</div>`;
    } finally {
        button.disabled = false;
        button.innerHTML = '<i class="fa-solid fa-arrows-rotate"></i> Güncel Gönderileri Getir';
    }
});

// Quick Action Strip
document.getElementById('qa-random-niche')?.addEventListener('click', async () => {
    if ((window.allNiches || []).length === 0 && typeof loadNiches === 'function') await loadNiches();
    if ((window.allNiches || []).length > 0) {
        const randomN = window.allNiches[Math.floor(Math.random() * window.allNiches.length)];
        if (window.selectNiche) window.selectNiche.value = randomN.id;
        if (typeof applyNicheProfile === 'function') await applyNicheProfile(randomN.id);
        if (typeof suggestTopic === 'function') suggestTopic();
        if (typeof switchTab === 'function') switchTab('studio');
        showToast(`🎲 Rastgele Niş Seçildi: ${randomN.name} (${randomN.category})`);
    } else if (typeof suggestTopic === 'function') {
        suggestTopic();
    }
});

document.getElementById('qa-latest-news')?.addEventListener('click', async () => {
    showToast('📡 En güncel son dakika flaş haberi taranıyor...');
    try {
        const res = await fetch('/api/rss/fetch?source=aa_guncel&limit=1');
        const data = await res.json();
        if (data.items && data.items.length > 0) {
            const news = data.items[0];
            if (window.inputTopic) window.inputTopic.value = news.title;
            if (window.selectNiche) window.selectNiche.value = "1_news_flash";
            if (typeof applyNicheProfile === 'function') await applyNicheProfile("1_news_flash");
            if (typeof updateLoopBridge === 'function') updateLoopBridge("1_news_flash", news.title);
            if (typeof switchTab === 'function') switchTab('studio');
            showToast(`📰 Son Dakika Haberi Yüklendi: ${news.title.slice(0, 45)}...`);
        } else {
            if (typeof switchTab === 'function') switchTab('rss-bot');
            if (typeof loadRssNews === 'function') loadRssNews();
        }
    } catch (e) {
        if (typeof switchTab === 'function') switchTab('rss-bot');
        if (typeof loadRssNews === 'function') loadRssNews();
    }
});

const btnSplitMode = document.getElementById('qa-split-mode');
btnSplitMode?.addEventListener('click', () => {
    if (!window.chkSplitScreen) return;
    window.chkSplitScreen.checked = !window.chkSplitScreen.checked;
    window.chkSplitScreen.dispatchEvent(new Event('change'));
    btnSplitMode.classList.toggle('active', window.chkSplitScreen.checked);
    const span = btnSplitMode.querySelector('span');
    if (span) span.textContent = window.chkSplitScreen.checked ? 'Split-Screen: AÇIK' : 'Split-Screen Modunu Aç';
    if (typeof switchTab === 'function') switchTab('studio');
    showToast(window.chkSplitScreen.checked ? '🎮 Split-Screen (Oynanış + Kurgu) Aktif!' : '⏹️ Split-Screen Modu Kapatıldı');
});

const btnTier1 = document.getElementById('qa-tier1-en');
btnTier1?.addEventListener('click', () => {
    const isCurrentlyEn = window.selectLanguage?.value === 'en';
    if (typeof setStudioLanguage === 'function') {
        setStudioLanguage(isCurrentlyEn ? 'tr' : 'en', { toast: true, autoTranslate: true });
    }
});

function showAdvancedAiOutput(html) {
    const box = document.getElementById('studio-advanced-engine-output') || document.getElementById('advanced-ai-engine-output');
    if (!box) return;
    box.classList.remove('hidden');
    box.style.display = 'block';
    box.innerHTML = html;
}

document.getElementById('btn-flow-viral-transform')?.addEventListener('click', async () => {
    const raw = document.getElementById('input-manuscript')?.value?.trim() || window.inputTopic?.value?.trim() || '';
    if (!raw) return showToast('Önce konu veya senaryo metni girin.', 'warn');
    const lang = window.selectLanguage?.value || 'tr';
    const targetNiche = window.selectNiche?.value || '12_amazon_affiliate';
    showAdvancedAiOutput('<i class="fa-solid fa-spinner fa-spin"></i> Viral Flow kanca dönüşümü yapılıyor...');
    try {
        const res = await fetch('/api/flow/transform_viral', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ raw_idea: raw, target_niche: targetNiche, language: lang, target_duration_sec: 45 })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Viral Flow dönüşümü başarısız oldu.');
        const result = data.result || data;
        const transformed = result.transformed_script || result.hook || JSON.stringify(result, null, 2);
        const msField = document.getElementById('input-manuscript');
        if (msField && typeof transformed === 'string') msField.value = transformed;
        showAdvancedAiOutput(`
            <div style="color:#c4b5fd; font-weight:700; margin-bottom:4px;">⚡ Viral Flow Dönüşümü Tamamlandı</div>
            <div style="white-space:pre-wrap;">${escapeHtml(typeof transformed === 'string' ? transformed : JSON.stringify(result, null, 2))}</div>
        `);
        showToast('⚡ Viral Flow metni hazırlandı!');
    } catch (e) {
        showAdvancedAiOutput(`<span class="text-danger">Hata: ${escapeHtml(e.message)}</span>`);
    }
});

document.getElementById('btn-facts-4act-gen')?.addEventListener('click', async () => {
    const topic = window.inputTopic?.value?.trim() || 'Tarihteki En Karanlık Sır';
    const niche = window.selectNiche?.value || '8_ancient_history';
    const lang = window.selectLanguage?.value || 'tr';
    showAdvancedAiOutput('<i class="fa-solid fa-spinner fa-spin"></i> 4-Perdeli (4-Act) Belgesel Senaryosu üretiliyor...');
    try {
        const res = await fetch('/api/facts/generate', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topic, niche, language: lang })
        });
        const data = await res.json();
        if (data.plan && typeof setCurrentPlan === 'function') setCurrentPlan(data.plan);
        const acts = data.acts || [];
        showAdvancedAiOutput(`
            <div style="color:#67e8f9; font-weight:700; margin-bottom:6px;">🎬 4-Perdeli Belgesel Planı Yüklendi (${acts.length || data.plan?.scenes?.length || 0} sahne)</div>
            ${acts.map((a, i) => `<div style="margin-bottom:4px;"><strong>Perde ${i + 1} (${escapeHtml(a.act || a.role || '')}):</strong> ${escapeHtml(a.narration || a.text || '')}</div>`).join('')}
        `);
        showToast('🎬 4-Perdeli Belgesel senaryosu Sahne Editörüne yüklendi!');
    } catch (e) {
        showAdvancedAiOutput(`<span class="text-danger">Hata: ${escapeHtml(e.message)}</span>`);
    }
});

document.getElementById('btn-podcast-debate-gen')?.addEventListener('click', async () => {
    const topic = window.inputTopic?.value?.trim() || 'Yapay Zeka İnsanlığın Sonu Mu?';
    const niche = window.selectNiche?.value || '10_ai_future_tech';
    const lang = window.selectLanguage?.value || 'tr';
    const host_name = document.getElementById('input-podcast-host-a')?.value?.trim() || 'Alex';
    const guest_name = document.getElementById('input-podcast-host-b')?.value?.trim() || 'Maya';
    showAdvancedAiOutput('<i class="fa-solid fa-spinner fa-spin"></i> 2-Sunuculu Podcast / Tartışma senaryosu üretiliyor...');
    try {
        const res = await fetch('/api/podcast/generate', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topic, niche, language: lang, turns: 6, host_name, guest_name })
        });
        const data = await res.json();
        if (data.plan && typeof setCurrentPlan === 'function') setCurrentPlan(data.plan);
        const scenes = data.plan?.scenes || [];
        showAdvancedAiOutput(`
            <div style="color:#f472b6; font-weight:700; margin-bottom:6px;">🎙️ 2-Sunuculu Podcast Senaryosu Yüklendi (${scenes.length} diyalog turu)</div>
            ${scenes.map(s => `<div style="margin-bottom:4px;"><strong style="color:#38bdf8;">[${escapeHtml(s.speaker || 'Sunucu')}]:</strong> ${escapeHtml(s.narration || '')}</div>`).join('')}
        `);
        showToast('🎙️ 2-Sunuculu Podcast senaryosu Sahne Editörüne yüklendi!');
    } catch (e) {
        showAdvancedAiOutput(`<span class="text-danger">Hata: ${escapeHtml(e.message)}</span>`);
    }
});

document.getElementById('btn-virality-slop-audit')?.addEventListener('click', async () => {
    const scriptText = (window.currentPlan?.scenes?.map(s => s.narration).join(' ')) || document.getElementById('input-manuscript')?.value?.trim() || window.inputTopic?.value?.trim() || '';
    if (!scriptText) return showToast('Denetlenecek senaryo veya konu bulunamadı.', 'warn');
    showAdvancedAiOutput('<i class="fa-solid fa-spinner fa-spin"></i> Virality & AI Slop denetimi çalışıyor...');
    try {
        const res = await fetch('/api/script/virality_audit', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ script_text: scriptText, hook_text: window.currentPlan?.scenes?.[0]?.narration || window.inputTopic?.value || '' })
        });
        const data = await res.json();
        const audit = data.audit || data;
        showAdvancedAiOutput(`
            <div style="color:#34d399; font-weight:700; margin-bottom:4px;">🔬 Virality &amp; AI Slop Denetim Raporu</div>
            <div>Viral Skor: <strong>${escapeHtml(String(audit.virality_score ?? audit.score ?? 85))}/100</strong> · AI Klişe (Slop) Riski: <strong>${escapeHtml(String(audit.slop_risk || audit.ai_slop_level || 'Düşük'))}</strong></div>
            ${audit.recommendations?.length ? `<ul style="margin:6px 0 0 16px; padding:0;">${audit.recommendations.map(r => `<li>${escapeHtml(r)}</li>`).join('')}</ul>` : ''}
        `);
    } catch (e) {
        showAdvancedAiOutput(`<span class="text-danger">Hata: ${escapeHtml(e.message)}</span>`);
    }
});

document.getElementById('btn-scan-youtube-trending')?.addEventListener('click', async () => {
    const lang = window.selectLanguage?.value || 'tr';
    const geo = lang === 'en' ? 'US' : 'TR';
    showAdvancedAiOutput(`<i class="fa-solid fa-spinner fa-spin"></i> YouTube ${geo} canlı trend konular taranıyor...`);
    try {
        const res = await fetch(`/api/trending/scan?geo=${geo}&limit=8`);
        const data = await res.json();
        const items = data.trends || data.items || [];
        if (!items.length) {
            showAdvancedAiOutput('Trend verisi bulunamadı.');
            return;
        }
        showAdvancedAiOutput(`
            <div style="color:#fbbf24; font-weight:700; margin-bottom:6px;">🔥 Canlı Trend Konular (${geo}) — Tıklayarak Konuya Aktarın</div>
            <div style="display:flex; flex-direction:column; gap:4px;">
                ${items.map((it, idx) => {
                    const title = typeof it === 'string' ? it : (it.title || it.topic || it.query || '');
                    return `<button type="button" class="btn btn-xs btn-outline trend-pick-item" data-title="${escapeHtml(title)}" style="text-align:left; justify-content:flex-start;">${idx + 1}. ${escapeHtml(title)}</button>`;
                }).join('')}
            </div>
        `);
        (document.getElementById('studio-advanced-engine-output') || document.getElementById('advanced-ai-engine-output'))?.querySelectorAll('.trend-pick-item').forEach(btn => {
            btn.addEventListener('click', () => {
                if (window.inputTopic) window.inputTopic.value = btn.getAttribute('data-title') || '';
                showToast('🔥 Trend konu stüdyoya aktarıldı!');
            });
        });
    } catch (e) {
        showAdvancedAiOutput(`<span class="text-danger">Hata: ${escapeHtml(e.message)}</span>`);
    }
});

document.getElementById('btn-v2-save-project')?.addEventListener('click', async () => {
    const topic = window.inputTopic?.value?.trim() || window.currentPlan?.title || 'Yeni V2 Proje';
    const niche = window.selectNiche?.value || window.currentPlan?.niche_id || '6_stoic_philosophy';
    try {
        const res = await fetch('/api/v2/projects', {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title: topic, topic, niche, language: window.selectLanguage?.value || 'tr', visual_mode: document.getElementById('select-visual-engine')?.value || 'auto', plan: window.currentPlan || null })
        });
        const data = await res.json();
        const proj = data.project || data;
        showAdvancedAiOutput(`<div style="color:#38bdf8; font-weight:700;">💾 V2 Proje Kaydedildi: <code>${escapeHtml(proj.id || proj.project_id || 'ok')}</code> (${escapeHtml(proj.topic || topic)})</div>`);
        showToast('💾 V2 Proje başarıyla kaydedildi');
    } catch (e) { showToast('V2 Proje kayıt hatası: ' + e.message, 'error'); }
});

document.getElementById('btn-v2-list-projects')?.addEventListener('click', async () => {
    showAdvancedAiOutput('<i class="fa-solid fa-spinner fa-spin"></i> Kayıtlı V2 projeleri yükleniyor...');
    try {
        const res = await fetch('/api/v2/projects');
        const data = await res.json();
        const projects = data.projects || [];
        if (!projects.length) return showAdvancedAiOutput('Henüz kayıtlı V2 projesi bulunmuyor.');
        showAdvancedAiOutput(`
            <div style="color:#38bdf8; font-weight:700; margin-bottom:6px;">📂 Kayıtlı V2 Projeleri (${projects.length})</div>
            <div style="display:flex; flex-direction:column; gap:6px;">
                ${projects.slice(0, 10).map(p => `
                    <div style="display:flex; justify-content:space-between; align-items:center; gap:8px; background:rgba(15,23,42,0.8); padding:6px 10px; border-radius:6px; border:1px solid rgba(255,255,255,0.08);">
                        <div><strong style="color:#f8fafc;">${escapeHtml(p.topic || p.title || p.id)}</strong> <span style="font-size:10px; color:#94a3b8;">[${escapeHtml(p.status || 'draft')}]</span></div>
                        <button type="button" class="btn btn-xs btn-outline btn-load-v2-proj" data-id="${escapeHtml(p.id)}">Yükle</button>
                    </div>
                `).join('')}
            </div>
        `);
        (document.getElementById('studio-advanced-engine-output') || document.getElementById('advanced-ai-engine-output'))?.querySelectorAll('.btn-load-v2-proj').forEach(btn => {
            btn.addEventListener('click', async () => {
                const pid = btn.getAttribute('data-id');
                const r = await fetch(`/api/v2/projects/${encodeURIComponent(pid)}`);
                const d = await r.json();
                const pr = d.project || d;
                if (pr.topic && window.inputTopic) window.inputTopic.value = pr.topic;
                if (pr.niche && window.selectNiche) window.selectNiche.value = pr.niche;
                if (pr.plan && typeof setCurrentPlan === 'function') setCurrentPlan(pr.plan);
                showToast(`📂 Proje yüklendi: ${pr.topic || pid}`);
            });
        });
    } catch (e) { showAdvancedAiOutput(`<span class="text-danger">Hata: ${escapeHtml(e.message)}</span>`); }
});

document.getElementById('btn-plagiarism-stats')?.addEventListener('click', async () => {
    try {
        const res = await fetch('/api/plagiarism/stats');
        const data = await res.json();
        showAdvancedAiOutput(`
            <div style="color:#a78bfa; font-weight:700;">🛡️ İntihal &amp; Özgünlük Hafızası</div>
            <div>Kayıtlı Senaryo Sayısı: <strong>${data.total_fingerprints ?? 0}</strong></div>
            ${data.recent?.length ? `<div style="margin-top:4px; font-size:10px; color:#94a3b8;">Son Kayıtlar: ${data.recent.map(r => escapeHtml(r.topic || '')).join(' · ')}</div>` : ''}
        `);
    } catch (e) { showToast('İntihal istatistik hatası: ' + e.message, 'error'); }
});

document.getElementById('btn-plagiarism-clear')?.addEventListener('click', async () => {
    if (!confirm('İntihal kontrol hafızasını sıfırlamak istediğinize emin misiniz?')) return;
    try {
        const res = await fetch('/api/plagiarism/clear', { method: 'POST' });
        const data = await res.json();
        showAdvancedAiOutput(`<div style="color:#34d399;">🗑️ İntihal hafızası temizlendi (${data.cleared ?? 0} kayıt silindi).</div>`);
        showToast('🗑️ İntihal hafızası sıfırlandı');
    } catch (e) { showToast('İntihal sıfırlama hatası: ' + e.message, 'error'); }
});

