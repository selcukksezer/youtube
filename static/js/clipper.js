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

    async function post(render) {
        const target = box();
        if (target) target.textContent = 'Çalışıyor...';
        const file = document.getElementById('clipper-file')?.files?.[0];
        const body = new FormData();
        body.append('url', document.getElementById('clipper-url')?.value || '');
        body.append('num_clips', String(Math.max(1, Math.min(5, num('clipper-count', 3)))));
        body.append('start_ost', String(num('clipper-start-ost', 0)));
        body.append('end_ost', String(num('clipper-end-ost', 0)));
        body.append('deleted_ids', JSON.stringify(deletedIds()));
        body.append('render', render ? 'true' : 'false');
        if (window.__clipperWords) body.append('words', JSON.stringify(window.__clipperWords));
        if (window.__clipperSegments) body.append('segments', JSON.stringify(window.__clipperSegments));
        const manualStart = num('clipper-manual-start', NaN);
        const manualEnd = num('clipper-manual-end', NaN);
        let highlights = window.__clipperHighlights || null;
        if (Number.isFinite(manualStart) && Number.isFinite(manualEnd) && manualEnd > manualStart) {
            highlights = [{ start_time: manualStart, end_time: manualEnd, score: 1, title: 'Manuel' }];
        }
        if (highlights) body.append('highlights', JSON.stringify(highlights));
        if (file) body.append('file', file);
        const response = await fetch('/api/clipper', { method: 'POST', body: body });
        const data = await response.json().catch(function () { return {}; });
        if (!response.ok) {
            if (target) target.textContent = data.detail || 'Kesici hata';
            return;
        }
        if (Array.isArray(data.highlights)) window.__clipperHighlights = data.highlights;
        if (target) target.textContent = JSON.stringify(data, null, 2);
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
})();
