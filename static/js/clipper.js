(function () {
    function box() {
        return document.getElementById('clipper-result');
    }

    function num(id, fallback) {
        const raw = document.getElementById(id)?.value;
        const value = Number(raw);
        return Number.isFinite(value) ? value : fallback;
    }

    function deletedIds() {
        return (document.getElementById('clipper-deleted')?.value || '')
            .split(',')
            .map(function (part) { return part.trim(); })
            .filter(Boolean);
    }

    function renderResult(data, target) {
        if (!target) return;
        target.textContent = '';
        if (typeof data.source_subtitle_url === 'string' && data.source_subtitle_url.startsWith('/output/')) {
            const link = document.createElement('a');
            link.href = data.source_subtitle_url;
            link.download = '';
            link.textContent = 'Kaynak videonun tam SRT altyazısını indir';
            target.append(link, document.createElement('br'), document.createElement('br'));
        }
        if (Array.isArray(data.clips) && data.clips.length) {
            data.clips.forEach(function (clip, index) {
                const row = document.createElement('span');
                row.append(document.createTextNode(`Klip ${index + 1}: `));
                [
                    ['Videoyu indir', clip.video_url],
                    ['SRT altyazısını indir', clip.subtitle_url]
                ].forEach(function (entry, entryIndex) {
                    const url = entry[1];
                    if (typeof url !== 'string' || !url.startsWith('/output/')) return;
                    if (entryIndex) row.append(document.createTextNode(' · '));
                    const link = document.createElement('a');
                    link.href = url;
                    link.download = '';
                    link.textContent = entry[0];
                    row.append(link);
                });
                target.append(row, document.createElement('br'));
            });
            target.append(document.createElement('br'));
        }
        target.append(document.createTextNode(JSON.stringify(data, null, 2)));
    }

    async function post(render, forceLowQuality) {
        const target = box();
        if (target) target.textContent = 'Çalışıyor...';
        const file = document.getElementById('clipper-file')?.files?.[0];
        const url = document.getElementById('clipper-url')?.value || '';
        const body = new FormData();
        body.append('url', url);
        body.append('num_clips', String(Math.max(1, Math.min(5, num('clipper-count', 3)))));
        body.append('hotwords', document.getElementById('clipper-hotwords')?.value || '');
        body.append('start_ost', String(num('clipper-start-ost', 0)));
        body.append('end_ost', String(num('clipper-end-ost', 0)));
        body.append('deleted_ids', JSON.stringify(deletedIds()));
        body.append('render', render ? 'true' : 'false');
        body.append('force_low_quality', forceLowQuality ? 'true' : 'false');
        body.append(
            'compile_clips',
            document.getElementById('clipper-compile')?.checked ? 'true' : 'false'
        );
        body.append(
            'speaker_split',
            document.getElementById('clipper-speaker-split')?.checked ? 'true' : 'false'
        );
        body.append(
            'speaker_activity_layout',
            document.getElementById('clipper-speaker-activity')?.checked ? 'true' : 'false'
        );
        const multimodal = document.getElementById('clipper-multimodal')?.checked === true;
        body.append('analysis_mode', multimodal ? 'multimodal' : 'transcript');
        body.append('external_analysis_consent', multimodal ? 'true' : 'false');
        if (window.__clipperWords) body.append('words', JSON.stringify(window.__clipperWords));
        if (window.__clipperSegments) body.append('segments', JSON.stringify(window.__clipperSegments));
        const manualStart = num('clipper-manual-start', NaN);
        const manualEnd = num('clipper-manual-end', NaN);
        let highlights = render ? window.__clipperHighlights || null : null;
        if (
            render &&
            Number.isFinite(manualStart) &&
            Number.isFinite(manualEnd) &&
            manualEnd > manualStart
        ) {
            highlights = [{ start_time: manualStart, end_time: manualEnd, score: 1, title: 'Manuel' }];
        }
        if (highlights) body.append('highlights', JSON.stringify(highlights));
        if (file) body.append('file', file);
        const response = await fetch('/api/clipper', { method: 'POST', body: body });
        const data = await response.json().catch(function () { return {}; });
        if (
            response.status === 409 &&
            data.detail?.code === 'source_quality_confirmation_required'
        ) {
            const message = String(data.detail.message || 'Kaynak çözünürlüğü düşük.');
            if (window.confirm(message)) return post(render, true);
            if (target) target.textContent = message;
            return;
        }
        if (!response.ok) {
            const detail = data.detail;
            if (target) {
                target.textContent = typeof detail === 'string'
                    ? detail
                    : 'Kesici hata';
            }
            return;
        }
        if (Array.isArray(data.highlights)) window.__clipperHighlights = data.highlights;
        renderResult(data, target);
    }

    async function teardown() {
        const target = box();
        const file = document.getElementById('clipper-file')?.files?.[0];
        const url = document.getElementById('clipper-url')?.value || '';
        if (!file && !url.trim()) {
            if (target) target.textContent = 'Analiz için video dosyası veya URL gerekli.';
            return;
        }
        if (target) target.textContent = 'Kurgu ritmi yerel olarak analiz ediliyor...';
        const body = new FormData();
        body.append('url', url);
        if (file) body.append('file', file);
        const response = await fetch('/api/clipper/teardown', { method: 'POST', body: body });
        const data = await response.json().catch(function () { return {}; });
        if (!response.ok) {
            if (target) target.textContent = data.detail || 'Kurgu analizi başarısız';
            return;
        }
        if (target) target.textContent = JSON.stringify(data, null, 2);
    }

    async function narrateFromFrames() {
        const target = document.getElementById('clipper-narration-result');
        const button = document.getElementById('clipper-narrate');
        const file = document.getElementById('clipper-file')?.files?.[0];
        const url = document.getElementById('clipper-url')?.value || '';
        const consent = document.getElementById('clipper-narration-consent')?.checked === true;
        if (!file && !url.trim()) {
            if (target) target.textContent = 'Önce analiz edilecek video dosyası veya URL seçin.';
            return;
        }
        if (!consent) {
            if (target) target.textContent = 'Kareleri Google Gemini’a göndermek için açık onay gerekli.';
            return;
        }

        const body = new FormData();
        body.append('url', url);
        body.append('narration_theme', document.getElementById('clipper-narration-focus')?.value || '');
        body.append('visual_analysis_consent', 'true');
        if (file) body.append('file', file);
        if (button) button.disabled = true;
        if (target) target.textContent = 'En fazla 8 kare analiz edilip anlatım taslağı hazırlanıyor...';
        try {
            const response = await fetch('/api/clipper/narration', { method: 'POST', body: body });
            const data = await response.json().catch(function () { return {}; });
            if (!response.ok) {
                if (target) target.textContent = data.detail || 'Görsel anlatım taslağı üretilemedi.';
                return;
            }
            const observations = Array.isArray(data.frame_observations)
                ? data.frame_observations.map(function (item, index) {
                    return `${index + 1}. ${item}`;
                }).join('\n')
                : '';
            if (target) {
                target.textContent = [
                    `Özet: ${data.summary || ''}`,
                    '',
                    'Anlatım taslağı:',
                    data.narration || '',
                    '',
                    'Kare gözlemleri:',
                    observations,
                ].join('\n');
            }
        } finally {
            if (button) button.disabled = false;
        }
    }

    document.getElementById('clipper-suggest')?.addEventListener('click', function () {
        post(false).catch(function (err) {
            const target = box();
            if (target) target.textContent = String(err);
        });
    });
    document.getElementById('clipper-cut')?.addEventListener('click', function () {
        post(true).catch(function (err) {
            const target = box();
            if (target) target.textContent = String(err);
        });
    });
    document.getElementById('clipper-teardown')?.addEventListener('click', function () {
        teardown().catch(function (err) {
            const target = box();
            if (target) target.textContent = String(err);
        });
    });
    document.getElementById('clipper-narrate')?.addEventListener('click', function () {
        narrateFromFrames().catch(function (err) {
            const target = document.getElementById('clipper-narration-result');
            if (target) target.textContent = String(err);
        });
    });
})();
