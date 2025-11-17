// JSON Tools Functions

function formatJSON() {
    const input = document.getElementById('jsonInput');
    const result = document.getElementById('jsonValidationResult');

    try {
        const parsed = JSON.parse(input.value);
        input.value = JSON.stringify(parsed, null, 2);
        result.style.display = 'block';
        result.innerHTML = '<div style="color: var(--success);"><i class="fas fa-check-circle"></i> JSON formatted successfully!</div>';
        setTimeout(() => result.style.display = 'none', 3000);
    } catch (e) {
        result.style.display = 'block';
        result.innerHTML = `<div style="color: var(--danger);"><i class="fas fa-exclamation-triangle"></i> Invalid JSON: ${e.message}</div>`;
    }
}

function minifyJSON() {
    const input = document.getElementById('jsonInput');
    const result = document.getElementById('jsonValidationResult');

    try {
        const parsed = JSON.parse(input.value);
        input.value = JSON.stringify(parsed);
        result.style.display = 'block';
        result.innerHTML = '<div style="color: var(--success);"><i class="fas fa-check-circle"></i> JSON minified successfully!</div>';
        setTimeout(() => result.style.display = 'none', 3000);
    } catch (e) {
        result.style.display = 'block';
        result.innerHTML = `<div style="color: var(--danger);"><i class="fas fa-exclamation-triangle"></i> Invalid JSON: ${e.message}</div>`;
    }
}

function validateJSON() {
    const input = document.getElementById('jsonInput');
    const result = document.getElementById('jsonValidationResult');

    try {
        const parsed = JSON.parse(input.value);
        const keys = Object.keys(parsed).length;
        const type = Array.isArray(parsed) ? 'Array' : typeof parsed;
        result.style.display = 'block';
        result.innerHTML = `<div style="color: var(--success);"><i class="fas fa-check-circle"></i> Valid JSON! Type: ${type}, ${Array.isArray(parsed) ? 'Length' : 'Keys'}: ${Array.isArray(parsed) ? parsed.length : keys}</div>`;
    } catch (e) {
        result.style.display = 'block';
        result.innerHTML = `<div style="color: var(--danger);"><i class="fas fa-exclamation-triangle"></i> Invalid JSON: ${e.message}</div>`;
    }
}

function copyJSON(elementId) {
    const input = document.getElementById(elementId);
    input.select();
    document.execCommand('copy');
    showToast('JSON copied to clipboard!', 'success');
}

function clearJSON() {
    document.getElementById('jsonInput').value = '';
    document.getElementById('jsonValidationResult').style.display = 'none';
}

function compareJSON() {
    const jsonA = document.getElementById('jsonA').value;
    const jsonB = document.getElementById('jsonB').value;
    const resultDiv = document.getElementById('jsonDiffResult');
    const outputDiv = document.getElementById('jsonDiffOutput');

    try {
        const objA = JSON.parse(jsonA);
        const objB = JSON.parse(jsonB);

        const diff = generateDiff(objA, objB);
        resultDiv.style.display = 'block';
        outputDiv.innerHTML = diff;
    } catch (e) {
        showToast(`Invalid JSON: ${e.message}`, 'error');
    }
}

function generateDiff(objA, objB, path = '') {
    let html = '';
    const allKeys = new Set([...Object.keys(objA || {}), ...Object.keys(objB || {})]);

    allKeys.forEach(key => {
        const fullPath = path ? `${path}.${key}` : key;
        const valA = objA ? objA[key] : undefined;
        const valB = objB ? objB[key] : undefined;

        if (valA === undefined && valB !== undefined) {
            html += `<div style="color: var(--success); margin: 4px 0;"><i class="fas fa-plus"></i> ${fullPath}: ${JSON.stringify(valB)}</div>`;
        } else if (valA !== undefined && valB === undefined) {
            html += `<div style="color: var(--danger); margin: 4px 0;"><i class="fas fa-minus"></i> ${fullPath}: ${JSON.stringify(valA)}</div>`;
        } else if (typeof valA === 'object' && typeof valB === 'object') {
            html += generateDiff(valA, valB, fullPath);
        } else if (valA !== valB) {
            html += `<div style="color: var(--warning); margin: 4px 0;"><i class="fas fa-not-equal"></i> ${fullPath}: ${JSON.stringify(valA)} → ${JSON.stringify(valB)}</div>`;
        }
    });

    return html || '<div style="color: var(--success);"><i class="fas fa-check-circle"></i> Objects are identical!</div>';
}

function jsonToQueryString() {
    const input = document.getElementById('jsonToQs').value;
    const output = document.getElementById('queryStringOutput');

    try {
        const obj = JSON.parse(input);
        const params = new URLSearchParams();

        Object.keys(obj).forEach(key => {
            params.append(key, obj[key]);
        });

        output.value = params.toString();
        showToast('Converted to query string!', 'success');
    } catch (e) {
        showToast(`Invalid JSON: ${e.message}`, 'error');
    }
}

function escapeJSON() {
    const input = document.getElementById('jsonEscapeInput').value;
    const output = document.getElementById('jsonEscapeOutput');

    try {
        const parsed = JSON.parse(input);
        output.value = JSON.stringify(JSON.stringify(parsed));
        showToast('JSON escaped!', 'success');
    } catch (e) {
        // If not valid JSON, just escape the string
        output.value = JSON.stringify(input);
    }
}

function unescapeJSON() {
    const input = document.getElementById('jsonEscapeInput').value;
    const output = document.getElementById('jsonEscapeOutput');

    try {
        const unescaped = JSON.parse(input);
        output.value = typeof unescaped === 'string' ? unescaped : JSON.stringify(unescaped, null, 2);
        showToast('JSON unescaped!', 'success');
    } catch (e) {
        showToast(`Invalid escaped JSON: ${e.message}`, 'error');
    }
}

function showJSONTree() {
    const input = document.getElementById('jsonInput').value;
    const treeView = document.getElementById('jsonTreeView');

    try {
        const parsed = JSON.parse(input);
        treeView.innerHTML = generateTree(parsed);
    } catch (e) {
        showToast(`Invalid JSON: ${e.message}`, 'error');
    }
}

function generateTree(obj, level = 0) {
    const indent = '  '.repeat(level);
    let html = '';

    if (typeof obj !== 'object' || obj === null) {
        return `<span style="color: var(--success);">${JSON.stringify(obj)}</span>`;
    }

    if (Array.isArray(obj)) {
        html += `<span style="color: var(--text-secondary);">[</span>\n`;
        obj.forEach((item, index) => {
            html += `${indent}  <span style="color: var(--text-secondary);">${index}:</span> ${generateTree(item, level + 1)}`;
            if (index < obj.length - 1) html += '<span style="color: var(--text-secondary);">,</span>';
            html += '\n';
        });
        html += `${indent}<span style="color: var(--text-secondary);">]</span>`;
    } else {
        html += `<span style="color: var(--text-secondary);">{</span>\n`;
        const keys = Object.keys(obj);
        keys.forEach((key, index) => {
            html += `${indent}  <span style="color: var(--accent);">"${key}"</span><span style="color: var(--text-secondary);">:</span> ${generateTree(obj[key], level + 1)}`;
            if (index < keys.length - 1) html += '<span style="color: var(--text-secondary);">,</span>';
            html += '\n';
        });
        html += `${indent}<span style="color: var(--text-secondary);">}</span>`;
    }

    return html;
}
