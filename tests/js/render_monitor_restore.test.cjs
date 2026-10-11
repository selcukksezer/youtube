const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const sourcePath = path.join(__dirname, '..', '..', 'static', 'js', 'render-monitor.js');
const source = fs.readFileSync(sourcePath, 'utf8');
const restoreFunction = source.match(/^async function restoreRenderState\(\) \{[\s\S]*?^\}/m);

assert.ok(restoreFunction, 'render-monitor.js must define restoreRenderState');

function createElement(hidden = false) {
    const classes = new Set(hidden ? ['hidden'] : []);
    return {
        classList: {
            add(value) { classes.add(value); },
            remove(value) { classes.delete(value); },
            contains(value) { return classes.has(value); },
        },
        style: {},
        textContent: '',
        scrollTop: 0,
        scrollHeight: 100,
        src: '',
    };
}

async function restoreRenderState(state) {
    const calls = { fetch: [], triggers: [], cancel: [], sse: 0 };
    const context = {
        fetch: async (url) => {
            calls.fetch.push(url);
            return { ok: true, json: async () => state };
        },
        persistentMonitor: createElement(true),
        terminalPanel: createElement(true),
        dockProgressFill: createElement(),
        dockProgressPct: createElement(),
        dockStepTitle: createElement(),
        dockLogSnippet: createElement(),
        terminalBody: createElement(),
        dockSpinner: createElement(),
        livePlayer: createElement(true),
        mockupPlaceholder: createElement(),
        isRendering: false,
        updateTerminalTriggers: (...args) => calls.triggers.push(args),
        setCancelButtonState: (value) => calls.cancel.push(value),
        initSSE: () => calls.sse++,
        console,
    };

    vm.runInNewContext(
        `${restoreFunction[0]}\nglobalThis.restoreRenderState = restoreRenderState;`,
        context,
    );
    await context.restoreRenderState();
    return { context, calls };
}

test('restores an active render and reconnects SSE', async () => {
    const { context, calls } = await restoreRenderState({
        is_rendering: true,
        percent: 42,
        step: 'Render ediliyor',
        logs: ['İş başladı', 'Klipler birleştiriliyor'],
    });

    assert.deepEqual(calls.fetch, ['/api/status']);
    assert.equal(context.isRendering, true);
    assert.equal(context.dockProgressFill.style.width, '42%');
    assert.equal(context.dockStepTitle.textContent, 'Render ediliyor');
    assert.match(context.terminalBody.textContent, /Klipler birleştiriliyor/);
    assert.equal(context.terminalBody.scrollTop, context.terminalBody.scrollHeight);
    assert.equal(calls.sse, 1);
    assert.deepEqual(calls.triggers, [[true, 42]]);
});

test('restores a completed render and its playable video', async () => {
    const { context, calls } = await restoreRenderState({
        is_rendering: false,
        percent: 100,
        video_url: '/output/ready.mp4',
        logs: ['Render tamamlandı'],
    });

    assert.equal(context.isRendering, false);
    assert.equal(context.dockStepTitle.textContent, 'Video hazır');
    assert.equal(context.dockProgressFill.style.width, '100%');
    assert.match(context.livePlayer.src, /^\/output\/ready\.mp4\?t=\d+$/);
    assert.equal(context.livePlayer.classList.contains('hidden'), false);
    assert.equal(context.mockupPlaceholder.classList.contains('hidden'), true);
    assert.equal(context.dockSpinner.style.display, 'none');
    assert.deepEqual(calls.cancel, ['close']);
    assert.equal(calls.sse, 0);
    assert.deepEqual(calls.triggers, [[false, 100]]);
});

test('restores a failed render and its error details', async () => {
    const { context, calls } = await restoreRenderState({
        is_rendering: false,
        percent: 63,
        error: 'FFmpeg failed',
        logs: ['Render stopped'],
    });

    assert.equal(context.isRendering, false);
    assert.equal(context.dockStepTitle.textContent, 'Hata Oluştu');
    assert.equal(context.dockLogSnippet.textContent, 'FFmpeg failed');
    assert.equal(context.dockProgressFill.style.backgroundColor, '#EF4444');
    assert.equal(context.dockSpinner.style.display, 'none');
    assert.deepEqual(calls.cancel, ['close']);
    assert.equal(calls.sse, 0);
    assert.deepEqual(calls.triggers, [[false, 63]]);
});

test('keeps the monitor hidden when there is no render result', async () => {
    const { context, calls } = await restoreRenderState({
        is_rendering: false,
        percent: 0,
        logs: [],
    });

    assert.equal(context.persistentMonitor.classList.contains('hidden'), true);
    assert.equal(context.terminalPanel.classList.contains('hidden'), true);
    assert.equal(calls.sse, 0);
    assert.deepEqual(calls.triggers, [[false, 0]]);
});
