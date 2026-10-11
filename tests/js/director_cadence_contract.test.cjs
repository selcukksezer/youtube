const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const root = path.join(__dirname, '..', '..');
const stateSource = fs.readFileSync(path.join(root, 'static', 'js', 'state.js'), 'utf8');
const timelineSource = fs.readFileSync(path.join(root, 'static', 'js', 'timeline.js'), 'utf8');

function extractFunction(source, name) {
    const match = source.match(new RegExp(`^function ${name}\\([^\\n]*\\) \\{[\\s\\S]*?^\\}`, 'm'));
    assert.ok(match, `${name} must be defined`);
    return match[0];
}

function createHarness() {
    const elements = new Map();
    const context = {
        sceneDurationSec: (scene) => Number(scene.duration),
        getNarrationIssues: () => [],
        document: {
            getElementById(id) {
                if (!elements.has(id)) {
                    const classes = new Set();
                    elements.set(id, {
                        className: '',
                        textContent: '',
                        style: {},
                        classList: {
                            add(value) { classes.add(value); },
                            contains(value) { return classes.has(value); },
                        },
                    });
                }
                return elements.get(id);
            },
        },
    };
    const functions = [
        extractFunction(stateSource, 'directorCadenceStatus'),
        extractFunction(stateSource, 'getComplianceIssues'),
        extractFunction(timelineSource, 'updateComplianceDashboard'),
        'globalThis.directorCadenceStatus = directorCadenceStatus;',
        'globalThis.getComplianceIssues = getComplianceIssues;',
        'globalThis.updateComplianceDashboard = updateComplianceDashboard;',
    ].join('\n');
    vm.runInNewContext(functions, context);
    return { context, elements };
}

function makeScenes(count) {
    return Array.from({ length: count }, (_, index) => ({
        duration: 6.5,
        narration: `Narration ${index}`,
        search_queries: [],
    }));
}

test('six Director scenes are treated as on-target across the quality UI', () => {
    const { context, elements } = createHarness();
    const scenes = makeScenes(6);

    assert.equal(context.directorCadenceStatus(scenes.length), 'ok');
    context.updateComplianceDashboard(scenes);
    assert.equal(elements.get('chip-cadence').classList.contains('status-ok'), true);

    const cadenceWarnings = Array.from(context.getComplianceIssues(scenes).soft)
        .filter((warning) => warning.startsWith('Cadence:'));
    assert.deepEqual(cadenceWarnings, []);
});

test('non-six scene counts remain visible as cadence advisories', () => {
    for (const count of [5, 7]) {
        const { context, elements } = createHarness();
        const scenes = makeScenes(count);
        assert.equal(context.directorCadenceStatus(count), 'warn');
        context.updateComplianceDashboard(scenes);
        assert.equal(elements.get('chip-cadence').classList.contains('status-warn'), true);

        const cadenceWarning = Array.from(context.getComplianceIssues(scenes).soft)
            .find((warning) => warning.startsWith('Cadence:'));
        assert.equal(cadenceWarning, `Cadence: ${count} sahne (Director hedefi 6)`);
    }
});

test('fewer than four scenes remain a cadence failure in the dashboard', () => {
    const { context, elements } = createHarness();

    assert.equal(context.directorCadenceStatus(3), 'fail');
    context.updateComplianceDashboard(makeScenes(3));
    assert.equal(elements.get('chip-cadence').classList.contains('status-danger'), true);
});
