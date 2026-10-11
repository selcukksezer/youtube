const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const stateSource = fs.readFileSync(
    path.join(__dirname, '..', '..', 'static', 'js', 'state.js'),
    'utf8',
);
const indexSource = fs.readFileSync(
    path.join(__dirname, '..', '..', 'static', 'index.html'),
    'utf8',
);
const panelMatch = stateSource.match(
    /^async function updateStudioQualityPanel\(plan, \{ silent = false \} = \{\}\) \{[\s\S]*?^\}/m,
);

assert.ok(panelMatch, 'state.js must define updateStudioQualityPanel');
assert.match(
    panelMatch[0],
    /const scriptQuality = validation\.script_quality \|\| activePlan\.meta\?\.script_quality \|\| \{\};/,
    'the server quality report must be authoritative',
);

function extractFunction(name) {
    const match = stateSource.match(new RegExp(`^function ${name}\\([^\\n]*\\) \\{[\\s\\S]*?^\\}`, 'm'));
    assert.ok(match, `${name} must be defined`);
    return match[0];
}

function element() {
    const classes = new Set();
    return {
        className: '',
        textContent: '',
        innerHTML: '',
        style: {},
        classList: {
            add(value) { classes.add(value); },
            remove(value) { classes.delete(value); },
            contains(value) { return classes.has(value); },
            toggle(value, enabled) {
                if (enabled) classes.add(value);
                else classes.delete(value);
            },
        },
        replaceChildren() {},
        appendChild() {},
    };
}

function createPanelHarness(plan, validation) {
    const elements = new Map();
    const calls = { blocked: [], persisted: 0, pills: new Map() };
    const context = {
        currentPlan: plan,
        qualityPanelGreen: false,
        document: {
            getElementById(id) {
                if (!elements.has(id)) elements.set(id, element());
                return elements.get(id);
            },
            createElement: element,
        },
        cleanNarration: (text) => text || '',
        wordCount: (text) => String(text).trim().split(/\s+/).filter(Boolean).length,
        setSqpPill: (id, label, status) => calls.pills.set(id, { label, status }),
        validatePlanViaApi: async () => validation,
        formatQualityGateIssue: (issue) => issue,
        formatQualityIssueWithRoadmap: (issue) => issue,
        updateRenderButtonsBlocked: (blocked, reason) => calls.blocked.push({ blocked, reason }),
        persistCurrentPlan: () => calls.persisted++,
        renderTimelineScenes() {},
        showToast() {},
    };
    vm.runInNewContext(
        [
            extractFunction('directorCadenceStatus'),
            extractFunction('directorWordCountStatus'),
            extractFunction('directorDurationStatus'),
            extractFunction('updateStudioPlanSummary'),
            panelMatch[0],
            'globalThis.updateStudioQualityPanel = updateStudioQualityPanel;',
        ].join('\n'),
        context,
    );
    return { context, calls, elements };
}

test('quality metric placeholders start hidden before a script exists', () => {
    assert.match(indexSource, /class="sqp-pills hidden" id="sqp-pills"/);
});

test('a hard-failing server quality report blocks a narratively valid plan', async () => {
    const plan = {
        scenes: Array.from({ length: 6 }, (_, index) => ({
            narration: `Narration sentence ${index} is complete.`,
            duration: 11,
            search_queries: [`scene ${index} wide`],
        })),
        meta: {},
    };
    const normalizedPlan = {
        ...plan,
        scenes: Array.from({ length: 6 }, (_, index) => ({
            narration: `${Array.from({ length: 15 }, (_, word) => `scene${index}word${word}`).join(' ')}.`,
            duration: 8.5,
            search_queries: [`normalized scene ${index} wide`],
        })),
        meta: {},
    };
    const quality = {
        hard_fail: true,
        issues: ['numeric_source_conflicts:4:24hours'],
        warnings: [],
        story_quality: { warnings: [] },
    };
    const validation = {
        ok: true,
        plan: normalizedPlan,
        script_quality: quality,
        issues: [],
        scene_continuity_advisories: [],
    };
    const { context, calls, elements } = createPanelHarness(plan, validation);

    const result = await context.updateStudioQualityPanel(plan);

    assert.equal(result.hard_fail, true);
    assert.equal(result.plan.meta.script_quality.hard_fail, true);
    assert.equal(context.qualityPanelGreen, false);
    assert.equal(context.currentPlan.meta.script_quality.hard_fail, true);
    assert.equal(elements.get('sqp-pills').classList.contains('hidden'), false);
    assert.equal(calls.blocked.at(-1).blocked, true);
    assert.match(calls.blocked.at(-1).reason, /numeric_source_conflicts/);
    assert.deepEqual(calls.pills.get('sqp-duration'), { label: 'Sure: 51.0sn', status: 'ok' });
    assert.deepEqual(calls.pills.get('sqp-words'), { label: 'Kelime: 90', status: 'ok' });
});

test('a scenario-free quality panel keeps direct render available but blocks timeline render', async () => {
    const elements = new Map();
    const getElement = id => {
        if (!elements.has(id)) elements.set(id, element());
        return elements.get(id);
    };
    const context = {
        currentPlan: null,
        document: {
            getElementById: getElement,
            createElement: element,
        },
        setSqpPill() {},
        formatQualityIssueWithRoadmap: issue => issue,
    };
    vm.runInNewContext(
        [
            extractFunction('updateRenderButtonsBlocked'),
            panelMatch[0],
            'globalThis.updateStudioQualityPanel = updateStudioQualityPanel;',
        ].join('\n'),
        context,
    );

    await context.updateStudioQualityPanel(null);
    assert.equal(getElement('sqp-pills').classList.contains('hidden'), true);
    assert.equal(getElement('btn-render-from-timeline').disabled, true);
    assert.equal(getElement('btn-quick-render').disabled, false);

    context.currentPlan = {
        scenes: [],
        meta: { script_quality: { hard_fail: true, issues: ['source conflict'] } },
    };
    await context.updateStudioQualityPanel(context.currentPlan);
    assert.equal(getElement('sqp-pills').classList.contains('hidden'), true);
    assert.equal(getElement('btn-render-from-timeline').disabled, true);
    assert.equal(getElement('btn-quick-render').disabled, true);
    assert.equal(getElement('btn-quick-render').title, 'source conflict');
});
