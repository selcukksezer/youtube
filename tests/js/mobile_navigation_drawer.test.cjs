const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');

const read = (relativePath) => fs.readFileSync(
    path.join(__dirname, '..', '..', relativePath),
    'utf8',
);

const indexHtml = read('static/index.html');
const styles = read('static/style.css');
const navigation = read('static/js/navigation.js');

test('mobile shell exposes an accessible navigation toggle and backdrop', () => {
    assert.match(indexHtml, /<aside class="sidebar" id="app-sidebar">/);
    assert.match(indexHtml, /<nav class="nav-links" aria-label="Ana menü">/);
    assert.match(indexHtml, /id="mobile-nav-toggle"[\s\S]*?aria-controls="app-sidebar"[\s\S]*?aria-expanded="false"/);
    assert.match(indexHtml, /id="mobile-nav-backdrop"[\s\S]*?aria-label="Menüyü kapat"/);
});

test('mobile navigation supports close, focus return, and modal background handling', () => {
    assert.match(navigation, /function setMobileNavOpen\(open, returnFocus = false\)/);
    assert.match(navigation, /mobileNavMain\.setAttribute\('inert', ''\)/);
    assert.match(navigation, /event\.propertyName !== 'transform'/);
    assert.match(navigation, /prefers-reduced-motion/);
    assert.match(navigation, /if \(event\.key === 'Escape'\)/);
    assert.match(navigation, /mobileNavToggle\.focus\(\)/);
    assert.match(navigation, /if \(mobileNavMedia\.matches\) setMobileNavOpen\(false, true\)/);
});

test('mobile header compacts status controls while keeping the terminal button accessible', () => {
    assert.match(indexHtml, /id="header-btn-open-terminal"[\s\S]*?aria-label="Canlı render konsolunu ve terminal kayıtlarını aç"/);
    assert.match(styles, /@media \(max-width: 768px\)[\s\S]*?#header-btn-open-terminal\s*\{[^}]*padding:\s*6px !important/);
    assert.match(styles, /@media \(max-width: 768px\)[\s\S]*?#header-terminal-text\s*\{\s*display:\s*none/);
    assert.match(styles, /@media \(max-width: 768px\)[\s\S]*?#chip-server-health\s*\{[^}]*white-space:\s*nowrap/);
});

test('Studio and multi-column forms collapse at narrow widths', () => {
    assert.match(styles, /@media \(max-width: 1200px\)[\s\S]*?\.studio-grid\s*\{\s*grid-template-columns:\s*minmax\(0,\s*1fr\)/);
    assert.match(styles, /@media \(max-width: 1200px\)[\s\S]*?\.header-right,\s*\.stat-pill-group\s*\{[^}]*flex-wrap:\s*wrap/);
    assert.match(styles, /@media \(max-width: 768px\)[\s\S]*?\.studio-grid,[\s\S]*?\.form-row-2,[\s\S]*?grid-template-columns:\s*minmax\(0,\s*1fr\)/);
    assert.match(styles, /\.select-styled\s*\{[^}]*min-width:\s*0;[^}]*max-width:\s*100%;/s);
    assert.match(styles, /#studio-flow-rail\s*\{\s*display:\s*grid;\s*grid-template-columns:\s*repeat\(3,\s*minmax\(0,\s*1fr\)\)/);
    assert.match(styles, /#studio-ai-quota-strip\s*\{[^}]*flex-wrap:\s*wrap/);
    assert.match(styles, /#studio-ai-quota-strip > div\s*\{\s*width:\s*100%/);
    assert.match(styles, /#studio-lang-selector-strip\s*\{[^}]*flex-direction:\s*column;[^}]*align-items:\s*stretch !important/);
    assert.match(styles, /#studio-lang-selector-strip \.lang-pill-group\s*\{[^}]*width:\s*100%/);
    assert.match(styles, /#studio-lang-selector-strip \.lang-pill-btn\s*\{[^}]*flex:\s*1 1 0;[^}]*min-width:\s*0/);
    assert.match(styles, /@media \(prefers-reduced-motion: reduce\)/);
});
