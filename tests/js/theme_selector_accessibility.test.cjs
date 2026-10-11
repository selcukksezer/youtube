const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const indexHtml = fs.readFileSync(
    path.join(__dirname, '..', '..', 'static', 'index.html'),
    'utf8',
);
const navigationSource = fs.readFileSync(
    path.join(__dirname, '..', '..', 'static', 'js', 'navigation.js'),
    'utf8',
);
const sidebarStyles = fs.readFileSync(
    path.join(__dirname, '..', '..', 'static', 'settings-quota.css'),
    'utf8',
);

test('theme choices are named native buttons with an announced active state', () => {
    const themeGroup = indexHtml.match(
        /<div class="theme-dots theme-dots-sm" role="group" aria-label="Tema seçimi">([\s\S]*?)<\/div>/,
    );
    assert.ok(themeGroup, 'theme choices must be exposed as an accessible group');

    for (const [color, label] of [
        ['violet', 'Elektrik Mor'],
        ['cyan', 'Cyber Cyan'],
        ['emerald', 'Zümrüt Yeşil'],
        ['amber', 'Neon Amber'],
    ]) {
        assert.match(
            themeGroup[1],
            new RegExp(
                `<button type="button" class="theme-dot ${color}(?: active)?"[^>]*data-color="${color}"[^>]*aria-label="${label} temasını seç"[^>]*aria-pressed="(?:true|false)"`,
            ),
            `${color} theme must be a labeled button with pressed state`,
        );
    }
});

test('selecting a theme synchronizes active styling and aria-pressed without changing persistence', () => {
    assert.match(
        navigationSource,
        /d\.setAttribute\('aria-pressed', String\(isActive\)\)/,
    );
    assert.match(navigationSource, /localStorage\.setItem\('shorts_theme', colorName\)/);
    assert.match(navigationSource, /dot\.addEventListener\('click'/);
});

test('theme controls provide 44px targets and a visible keyboard focus ring', () => {
    assert.match(sidebarStyles, /flex:\s*0 0 44px/);
    assert.match(sidebarStyles, /width:\s*44px/);
    assert.match(sidebarStyles, /\.theme-dots-sm \.theme-dot:focus-visible\s*\{[^}]*outline:\s*2px/s);
});
