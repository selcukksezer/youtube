/**
 * Public APIs fallback panel. Snapshot in the repo so the studio list works offline.
 * Pexels and Pixabay stay the default. This list is fallback only.
 */
(function loadPublicApisFallbackPanel() {
    const list = document.getElementById('public-apis-fallback-list');
    const panel = document.getElementById('public-apis-fallback');
    if (!list || !panel) return;

    function paint(rows) {
        if (!rows || !rows.length) return;
        list.innerHTML = '';
        rows.forEach((row) => {
            const item = document.createElement('li');
            item.dataset.fallback = row.id || '';
            const kind = row.kind ? ` (${row.kind})` : '';
            item.textContent = `${row.name || row.id}${kind}`;
            list.appendChild(item);
        });
    }

    fetch('/static/data/public-apis-snapshot.json')
        .then((res) => (res.ok ? res.json() : null))
        .then((data) => {
            const rows = data && Array.isArray(data.fallbacks) ? data.fallbacks : [];
            paint(rows);
        })
        .catch(() => {
            /* HTML already shows the Wikipedia fallback line. */
        });
})();
