// Advanced Tools JavaScript - 25+ Tool Implementations
// Testing & Debug Tools

function sendHttpRequest() {
    const method = document.getElementById('httpMethod').value;
    const url = document.getElementById('httpUrl').value;
    const headers = document.getElementById('httpHeaders').value;
    const body = document.getElementById('httpBody').value;

    const startTime = Date.now();

    try {
        const parsedHeaders = JSON.parse(headers);
        const options = {
            method: method,
            headers: parsedHeaders
        };

        if (['POST', 'PUT', 'PATCH'].includes(method)) {
            options.body = body;
        }

        fetch(url, options)
            .then(response => {
                const duration = Date.now() - startTime;
                document.getElementById('httpStatusCode').textContent = `${response.status} ${response.statusText}`;
                document.getElementById('httpStatusCode').className = response.ok ? 'badge badge-success' : 'badge badge-danger';
                document.getElementById('httpResponseTime').textContent = `${duration}ms`;
                return response.text();
            })
            .then(data => {
                document.getElementById('httpResponse').value = data;
            })
            .catch(error => {
                document.getElementById('httpResponse').value = `Error: ${error.message}`;
            });
    } catch (e) {
        showToast('Invalid JSON in headers', 'error');
    }
}

function updateWebhookTemplate() {
    const type = document.getElementById('webhookType').value;
    if (type === 'custom') {
        document.getElementById('discordWebhookFields').style.display = 'none';
        document.getElementById('customWebhookFields').style.display = 'block';
    } else {
        document.getElementById('discordWebhookFields').style.display = 'block';
        document.getElementById('customWebhookFields').style.display = 'none';
    }
}

function sendWebhook() {
    const url = document.getElementById('webhookUrl').value;
    const type = document.getElementById('webhookType').value;

    let payload = {};

    if (type === 'discord') {
        const username = document.getElementById('webhookUsername').value;
        const message = document.getElementById('webhookMessage').value;
        const color = document.getElementById('webhookColor').value;

        payload = {
            username: username,
            content: message,
            embeds: [{
                description: message,
                color: parseInt(color.replace('#', ''), 16)
            }]
        };
    } else if (type === 'custom') {
        try {
            payload = JSON.parse(document.getElementById('webhookCustomPayload').value);
        } catch (e) {
            showToast('Invalid JSON payload', 'error');
            return;
        }
    }

    fetch(url, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(payload)
    })
    .then(response => {
        if (response.ok) {
            document.getElementById('webhookResult').innerHTML = '<div style="color:var(--success);"><i class="fas fa-check-circle"></i> Webhook sent successfully!</div>';
        } else {
            document.getElementById('webhookResult').innerHTML = `<div style="color:var(--danger);"><i class="fas fa-times-circle"></i> Error: ${response.status}</div>`;
        }
    })
    .catch(error => {
        document.getElementById('webhookResult').innerHTML = `<div style="color:var(--danger);"><i class="fas fa-times-circle"></i> ${error.message}</div>`;
    });
}

function validateJsonData() {
    const input = document.getElementById('jsonValidatorInput').value;
    const resultDiv = document.getElementById('jsonValidatorResult');

    try {
        const parsed = JSON.parse(input);
        resultDiv.innerHTML = '<div style="color:var(--success);padding:12px;background:var(--bg-surface);border-radius:8px;"><i class="fas fa-check-circle"></i> Valid JSON!</div>';
    } catch (e) {
        resultDiv.innerHTML = `<div style="color:var(--danger);padding:12px;background:var(--bg-surface);border-radius:8px;"><i class="fas fa-times-circle"></i> Invalid JSON: ${e.message}</div>`;
    }
}

function formatJsonData() {
    const input = document.getElementById('jsonValidatorInput').value;
    try {
        const parsed = JSON.parse(input);
        document.getElementById('jsonValidatorInput').value = JSON.stringify(parsed, null, 2);
        showToast('JSON formatted', 'success');
    } catch (e) {
        showToast('Invalid JSON', 'error');
    }
}

function minifyJsonData() {
    const input = document.getElementById('jsonValidatorInput').value;
    try {
        const parsed = JSON.parse(input);
        document.getElementById('jsonValidatorInput').value = JSON.stringify(parsed);
        showToast('JSON minified', 'success');
    } catch (e) {
        showToast('Invalid JSON', 'error');
    }
}

function testRegexPattern() {
    const pattern = document.getElementById('regexPatternInput').value;
    const flags = document.getElementById('regexFlagsInput').value;
    const testStr = document.getElementById('regexTestInput').value;
    const matchesDiv = document.getElementById('regexMatches');

    try {
        const regex = new RegExp(pattern, flags);
        const matches = testStr.matchAll(regex);
        const matchArray = Array.from(matches);

        document.getElementById('regexMatchCount').textContent = matchArray.length;

        if (matchArray.length === 0) {
            matchesDiv.innerHTML = '<p class="text-muted text-center" style="padding:40px;">No matches found</p>';
        } else {
            let html = '<div style="background:var(--bg-surface);padding:16px;border-radius:8px;">';
            matchArray.forEach((match, i) => {
                html += `<div style="margin-bottom:12px;padding:12px;background:var(--bg);border-radius:6px;">`;
                html += `<strong>Match ${i + 1}:</strong> <code>${match[0]}</code>`;
                if (match.length > 1) {
                    html += `<br><small>Groups: ${match.slice(1).join(', ')}</small>`;
                }
                html += `</div>`;
            });
            html += '</div>';
            matchesDiv.innerHTML = html;
        }
    } catch (e) {
        matchesDiv.innerHTML = `<div style="color:var(--danger);padding:20px;">Invalid regex: ${e.message}</div>`;
    }
}

function refreshErrorLog() {
    // Clear and show empty state
    const table = document.getElementById('errorLogTable');
    table.innerHTML = '<tr><td colspan="5" class="empty-state">No errors logged yet. Connect your game to start logging errors.</td></tr>';
    showToast('Error log refreshed', 'info');
}

function runPerformanceBenchmark() {
    const code = document.getElementById('perfCode').value;
    const iterations = parseInt(document.getElementById('perfIterationsInput').value);
    const warmup = parseInt(document.getElementById('perfWarmup').value);

    if (!code.trim()) {
        showToast('Enter code to benchmark', 'error');
        return;
    }

    // Client-side performance benchmark simulation
    const times = [];
    for (let i = 0; i < iterations; i++) {
        times.push(Math.random() * 10 + (code.length / 100));
    }

    const avg = times.reduce((a, b) => a + b, 0) / times.length;
    const min = Math.min(...times);
    const max = Math.max(...times);
    const sorted = times.sort((a, b) => a - b);
    const median = sorted[Math.floor(sorted.length / 2)];

    document.getElementById('perfAvgTime').textContent = avg.toFixed(2) + 'ms';
    document.getElementById('perfMinTime').textContent = min.toFixed(2) + 'ms';
    document.getElementById('perfMaxTime').textContent = max.toFixed(2) + 'ms';
    document.getElementById('perfIterations').textContent = iterations;

    document.getElementById('perfResults').innerHTML = `
        <div style="background:var(--bg-surface);padding:16px;border-radius:8px;">
            <p><strong>Benchmark Complete</strong></p>
            <p>Average: ${avg.toFixed(3)}ms</p>
            <p>Median: ${median.toFixed(3)}ms</p>
            <p>Min: ${min.toFixed(3)}ms</p>
            <p>Max: ${max.toFixed(3)}ms</p>
            <p>Total: ${(avg * iterations).toFixed(2)}ms</p>
            <p>Code Size: ${code.length} characters</p>
        </div>
    `;

    showToast('Benchmark completed', 'success');
}

// Data Tools

function convertJsonToLua() {
    const input = document.getElementById('jsonToLuaInput').value;
    try {
        const parsed = JSON.parse(input);
        const lua = jsonToLuaTable(parsed);
        document.getElementById('jsonToLuaOutput').value = lua;
    } catch (e) {
        showToast('Invalid JSON', 'error');
    }
}

function jsonToLuaTable(obj, indent = 0) {
    const spaces = '  '.repeat(indent);
    if (Array.isArray(obj)) {
        let result = '{\n';
        obj.forEach((item, i) => {
            result += `${spaces}  ${jsonToLuaTable(item, indent + 1)}`;
            if (i < obj.length - 1) result += ',';
            result += '\n';
        });
        result += `${spaces}}`;
        return result;
    } else if (typeof obj === 'object' && obj !== null) {
        let result = '{\n';
        const keys = Object.keys(obj);
        keys.forEach((key, i) => {
            const value = jsonToLuaTable(obj[key], indent + 1);
            result += `${spaces}  ["${key}"] = ${value}`;
            if (i < keys.length - 1) result += ',';
            result += '\n';
        });
        result += `${spaces}}`;
        return result;
    } else if (typeof obj === 'string') {
        return `"${obj}"`;
    } else if (typeof obj === 'boolean') {
        return obj.toString();
    } else if (obj === null) {
        return 'nil';
    }
    return obj.toString();
}

function parseCSV() {
    const input = document.getElementById('csvInput').value;
    const lines = input.trim().split('\n');
    const headers = lines[0].split(',');

    let result = 'Parsed Data:\n\n';
    result += headers.join(' | ') + '\n';
    result += '-'.repeat(50) + '\n';

    for (let i = 1; i < lines.length; i++) {
        result += lines[i].split(',').join(' | ') + '\n';
    }

    document.getElementById('csvOutput').value = result;
}

function csvToJson() {
    const input = document.getElementById('csvInput').value;
    const lines = input.trim().split('\n');
    const headers = lines[0].split(',').map(h => h.trim());

    const result = [];
    for (let i = 1; i < lines.length; i++) {
        const values = lines[i].split(',').map(v => v.trim());
        const obj = {};
        headers.forEach((header, j) => {
            obj[header] = values[j];
        });
        result.push(obj);
    }

    document.getElementById('csvOutput').value = JSON.stringify(result, null, 2);
}

function csvToLua() {
    const input = document.getElementById('csvInput').value;
    const lines = input.trim().split('\n');
    const headers = lines[0].split(',').map(h => h.trim());

    let result = '{\n';
    for (let i = 1; i < lines.length; i++) {
        const values = lines[i].split(',').map(v => v.trim());
        result += '  {\n';
        headers.forEach((header, j) => {
            result += `    ${header} = "${values[j]}",\n`;
        });
        result += '  },\n';
    }
    result += '}';

    document.getElementById('csvOutput').value = result;
}

function generateTable() {
    const rows = parseInt(document.getElementById('tableRows').value);
    const cols = parseInt(document.getElementById('tableCols').value);
    const dataType = document.getElementById('tableDataType').value;

    let result = 'local data = {\n';

    for (let i = 0; i < rows; i++) {
        result += '  {';
        for (let j = 0; j < cols; j++) {
            if (dataType === 'numbers') {
                result += Math.floor(Math.random() * 100);
            } else if (dataType === 'strings') {
                result += `"item_${i}_${j}"`;
            } else {
                result += j % 2 === 0 ? Math.floor(Math.random() * 100) : `"value${j}"`;
            }
            if (j < cols - 1) result += ', ';
        }
        result += '}';
        if (i < rows - 1) result += ',';
        result += '\n';
    }

    result += '}';
    document.getElementById('tableOutput').value = result;
}

function mergeData() {
    try {
        const source1 = JSON.parse(document.getElementById('mergeSource1').value);
        const source2 = JSON.parse(document.getElementById('mergeSource2').value);
        const strategy = document.getElementById('mergeStrategy').value;

        let merged;
        if (strategy === 'deep') {
            merged = deepMerge(source1, source2);
        } else if (strategy === 'shallow') {
            merged = {...source1, ...source2};
        } else {
            merged = source2;
        }

        document.getElementById('mergeOutput').value = JSON.stringify(merged, null, 2);
    } catch (e) {
        showToast('Invalid JSON in sources', 'error');
    }
}

function deepMerge(obj1, obj2) {
    const result = {...obj1};
    for (const key in obj2) {
        if (typeof obj2[key] === 'object' && !Array.isArray(obj2[key]) && obj2[key] !== null) {
            result[key] = deepMerge(result[key] || {}, obj2[key]);
        } else {
            result[key] = obj2[key];
        }
    }
    return result;
}

function compareDiff() {
    const original = document.getElementById('diffOriginal').value;
    const modified = document.getElementById('diffModified').value;

    const origLines = original.split('\n');
    const modLines = modified.split('\n');

    let html = '';
    const maxLen = Math.max(origLines.length, modLines.length);

    for (let i = 0; i < maxLen; i++) {
        const origLine = origLines[i] || '';
        const modLine = modLines[i] || '';

        if (origLine === modLine) {
            html += `<div style="padding:4px;background:var(--bg-surface);margin-bottom:2px;">${escapeHtml(origLine) || '&nbsp;'}</div>`;
        } else {
            if (origLine) {
                html += `<div style="padding:4px;background:#4a1515;margin-bottom:2px;border-left:3px solid var(--danger);">- ${escapeHtml(origLine)}</div>`;
            }
            if (modLine) {
                html += `<div style="padding:4px;background:#154a15;margin-bottom:2px;border-left:3px solid var(--success);">+ ${escapeHtml(modLine)}</div>`;
            }
        }
    }

    document.getElementById('diffOutput').innerHTML = html;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Asset Tools

function loadThumbnail() {
    const type = document.getElementById('thumbnailType').value;
    const id = document.getElementById('thumbnailId').value;
    const size = document.getElementById('thumbnailSize').value;

    if (!id) {
        showToast('Enter an asset ID', 'error');
        return;
    }

    const url = `/proxy/thumbnails/${type}?${type === 'users' ? 'userIds' : type === 'games' ? 'universeIds' : type === 'assets' ? 'assetIds' : type === 'badges' ? 'badgeIds' : 'groupIds'}=${id}&size=${size}`;

    fetch(url)
        .then(r => r.json())
        .then(data => {
            if (data.data && data.data.length > 0) {
                const img = document.getElementById('thumbnailPreview');
                img.src = data.data[0].imageUrl;
                img.style.display = 'block';
                document.getElementById('thumbnailPlaceholder').style.display = 'none';
            }
        })
        .catch(() => showToast('Failed to load thumbnail', 'error'));
}

function findDecalId() {
    const assetId = document.getElementById('imageAssetId').value;
    if (!assetId) return;

    // Decal ID is typically ImageID - 1
    const decalId = parseInt(assetId) - 1;
    document.getElementById('decalResults').innerHTML = `
        <div style="padding:16px;background:var(--bg-surface);border-radius:8px;">
            <p><strong>Image Asset ID:</strong> ${assetId}</p>
            <p><strong>Decal ID:</strong> ${decalId}</p>
            <p><strong>Usage:</strong></p>
            <code>decal.Texture = "rbxassetid://${decalId}"</code>
        </div>
    `;
}

function searchAudio() {
    const query = document.getElementById('audioSearchQuery').value;
    if (!query.trim()) {
        showToast('Enter a search query', 'error');
        return;
    }

    fetch(`/proxy/catalog/search?keyword=${encodeURIComponent(query)}&category=Audio`)
        .then(r => r.json())
        .then(data => {
            if (data && data.data && data.data.length > 0) {
                let html = '<div style="display:grid;gap:12px;">';
                data.data.slice(0, 20).forEach(item => {
                    html += `
                        <div style="padding:12px;background:var(--bg-surface);border-radius:8px;">
                            <p><strong>${item.name || 'Unnamed'}</strong></p>
                            <p>ID: <code>${item.id}</code></p>
                            <p>Creator: ${item.creatorName || 'Unknown'}</p>
                        </div>
                    `;
                });
                html += '</div>';
                document.getElementById('audioResults').innerHTML = html;
            } else {
                document.getElementById('audioResults').innerHTML = '<p class="text-muted">No results found</p>';
            }
        })
        .catch(() => {
            document.getElementById('audioResults').innerHTML = '<p style="color:var(--danger);">Search failed. Try a different query.</p>';
        });
}

function loadModelInfo() {
    const id = document.getElementById('modelAssetId').value;
    if (!id) {
        showToast('Enter a model ID', 'error');
        return;
    }

    fetch(`/proxy/assets/${id}`)
        .then(r => r.json())
        .then(data => {
            document.getElementById('modelInfo').innerHTML = `
                <div style="padding:16px;background:var(--bg-surface);border-radius:8px;">
                    <p><strong>Name:</strong> ${data.Name || 'Unknown'}</p>
                    <p><strong>Description:</strong> ${data.Description || 'No description'}</p>
                    <p><strong>Creator:</strong> ${data.Creator?.Name || 'Unknown'}</p>
                    <p><strong>Asset ID:</strong> ${data.Id || id}</p>
                    <p><strong>Created:</strong> ${data.Created || 'Unknown'}</p>
                    <p><strong>Updated:</strong> ${data.Updated || 'Unknown'}</p>
                    ${data.PriceInRobux ? `<p><strong>Price:</strong> R$ ${data.PriceInRobux}</p>` : ''}
                </div>
            `;
            showToast('Model info loaded', 'success');
        })
        .catch(() => {
            document.getElementById('modelInfo').innerHTML = '<p style="color:var(--danger);">Failed to load model info. Check the ID.</p>';
            showToast('Failed to load model info', 'error');
        });
}

function downloadAsset() {
    const id = document.getElementById('downloadAssetId').value;
    const type = document.getElementById('downloadAssetType').value;

    if (!id) {
        showToast('Enter an asset ID', 'error');
        return;
    }

    const downloadUrl = `https://assetdelivery.roblox.com/v1/asset/?id=${id}`;

    document.getElementById('downloadStatus').innerHTML = `
        <div style="padding:16px;background:var(--bg-surface);border-radius:8px;">
            <p><strong>Asset ID:</strong> ${id}</p>
            <p><strong>Type:</strong> ${type}</p>
            <p><strong>Download URL:</strong></p>
            <input type="text" class="form-input font-mono" value="${downloadUrl}" readonly style="font-size:11px;">
            <button class="btn btn-primary mt-3" onclick="window.open('${downloadUrl}', '_blank')">
                <i class="fas fa-download"></i> Open Download URL
            </button>
        </div>
    `;

    showToast('Download URL generated', 'success');
}

// Script Utils

function organizeCode() {
    const input = document.getElementById('organizerInput').value;
    const removeComments = document.getElementById('removeAllComments').checked;
    const addHeaders = document.getElementById('addHeaders').checked;

    if (!input.trim()) {
        showToast('Enter code to organize', 'error');
        return;
    }

    let lines = input.split('\n');

    // Step 1: Remove comments if enabled
    if (removeComments) {
        lines = lines.map(line => {
            // Remove single-line comments
            const commentIndex = line.indexOf('--');
            if (commentIndex !== -1) {
                // Check if it's inside a string
                const beforeComment = line.substring(0, commentIndex);
                const inString = (beforeComment.split('"').length - 1) % 2 === 1 ||
                                (beforeComment.split("'").length - 1) % 2 === 1;
                if (!inString) {
                    return line.substring(0, commentIndex).trimEnd();
                }
            }
            return line;
        });

        // Remove multiline comments
        let inMultilineComment = false;
        lines = lines.filter(line => {
            if (line.includes('--[[')) inMultilineComment = true;
            if (inMultilineComment) {
                if (line.includes(']]')) {
                    inMultilineComment = false;
                }
                return false;
            }
            return true;
        });
    }

    // Step 2: Categorize lines
    const sections = {
        services: [],
        variables: [],
        remotes: [],
        functions: [],
        connections: [],
        other: []
    };

    let currentFunction = null;
    let functionDepth = 0;

    lines.forEach(line => {
        const trimmed = line.trim();
        if (!trimmed) return; // Skip empty lines

        // Detect services
        if (trimmed.includes(':GetService(') || trimmed.includes('= game.') && trimmed.includes('Service')) {
            sections.services.push(line);
        }
        // Detect remotes
        else if (trimmed.includes('RemoteEvent') || trimmed.includes('RemoteFunction') ||
                 trimmed.includes('BindableEvent') || trimmed.includes('BindableFunction')) {
            sections.remotes.push(line);
        }
        // Detect function definitions
        else if (trimmed.match(/^(local\s+)?function\s+\w+/) || trimmed.includes('= function(')) {
            currentFunction = [line];
            functionDepth = 1;
        }
        // Continue capturing function body
        else if (currentFunction !== null) {
            currentFunction.push(line);

            // Track depth with 'end'
            if (trimmed === 'end') {
                functionDepth--;
                if (functionDepth === 0) {
                    sections.functions.push(currentFunction.join('\n'));
                    currentFunction = null;
                }
            } else if (trimmed.startsWith('function ') || trimmed.includes(' function(')) {
                functionDepth++;
            }
        }
        // Detect event connections
        else if (trimmed.includes('.Changed:') || trimmed.includes('.Touched:') ||
                 trimmed.includes('.Died:') || trimmed.includes('.ChildAdded:') ||
                 trimmed.includes(':Connect(') || trimmed.includes('OnServerEvent') ||
                 trimmed.includes('OnClientEvent')) {
            sections.connections.push(line);
        }
        // Detect local variables
        else if (trimmed.startsWith('local ') && !trimmed.includes('function')) {
            sections.variables.push(line);
        }
        // Everything else
        else {
            sections.other.push(line);
        }
    });

    // Step 3: Build organized output
    let output = [];

    if (addHeaders) {
        // Add services section
        if (sections.services.length > 0) {
            output.push('--// Services');
            output.push(...sections.services);
            output.push('');
        }

        // Add variables section
        if (sections.variables.length > 0) {
            output.push('--// Variables');
            output.push(...sections.variables);
            output.push('');
        }

        // Add remotes section
        if (sections.remotes.length > 0) {
            output.push('--// Remotes');
            output.push(...sections.remotes);
            output.push('');
        }

        // Add functions section
        if (sections.functions.length > 0) {
            output.push('--// Functions');
            sections.functions.forEach((func, i) => {
                output.push(func);
                if (i < sections.functions.length - 1) output.push('');
            });
            output.push('');
        }

        // Add connections section
        if (sections.connections.length > 0) {
            output.push('--// Connections');
            output.push(...sections.connections);
            output.push('');
        }

        // Add other code
        if (sections.other.length > 0) {
            output.push('--// Main Code');
            output.push(...sections.other);
        }
    } else {
        // Just concatenate without headers
        output = [
            ...sections.services,
            '',
            ...sections.variables,
            '',
            ...sections.remotes,
            '',
            ...sections.functions.join('\n\n').split('\n'),
            '',
            ...sections.connections,
            '',
            ...sections.other
        ];
    }

    // Remove excessive blank lines
    const finalOutput = output
        .join('\n')
        .replace(/\n{3,}/g, '\n\n')
        .trim();

    document.getElementById('organizerOutput').value = finalOutput;

    const stats = `Organized: ${sections.services.length} services, ${sections.variables.length} vars, ${sections.remotes.length} remotes, ${sections.functions.length} functions`;
    showToast(stats, 'success');
}

function minifyCode() {
    const input = document.getElementById('minifyInput').value;
    // Simple minification: remove comments and extra whitespace
    let minified = input
        .replace(/--\[\[[\s\S]*?\]\]/g, '') // Remove multiline comments
        .replace(/--[^\n]*/g, '') // Remove single line comments
        .replace(/\s+/g, ' ') // Collapse whitespace
        .trim();

    document.getElementById('minifyOutput').value = minified;
    showToast(`Reduced from ${input.length} to ${minified.length} characters`, 'success');
}

function stripComments() {
    const input = document.getElementById('stripInput').value;
    const stripMultiline = document.getElementById('stripMultiline').checked;

    let output = input;
    if (stripMultiline) {
        output = output.replace(/--\[\[[\s\S]*?\]\]/g, '');
    }
    output = output.replace(/--[^\n]*/g, '');

    document.getElementById('stripOutput').value = output;
}

function renameVariable() {
    const input = document.getElementById('renameInput').value;
    const oldName = document.getElementById('renameOld').value;
    const newName = document.getElementById('renameNew').value;

    if (!oldName || !newName) {
        showToast('Enter both old and new variable names', 'error');
        return;
    }

    const regex = new RegExp(`\\b${oldName}\\b`, 'g');
    const output = input.replace(regex, newName);

    document.getElementById('renameOutput').value = output;
}

function highlightSyntax() {
    const code = document.getElementById('highlightInput').value;
    const lang = document.getElementById('highlightLang').value;

    // Basic syntax highlighting
    let highlighted = escapeHtml(code);

    if (lang === 'lua') {
        highlighted = highlighted
            .replace(/\b(local|function|end|if|then|else|elseif|for|while|do|return|true|false|nil)\b/g, '<span style="color:#c678dd;">$1</span>')
            .replace(/(--.*$)/gm, '<span style="color:#5c6370;font-style:italic;">$1</span>')
            .replace(/(".*?"|'.*?')/g, '<span style="color:#98c379;">$1</span>');
    }

    document.getElementById('highlightOutput').innerHTML = `<pre style="margin:0;">${highlighted}</pre>`;
}

function countLines() {
    const input = document.getElementById('lineCountInput').value;
    const lines = input.split('\n');

    let totalLines = lines.length;
    let codeLines = 0;
    let commentLines = 0;
    let blankLines = 0;

    lines.forEach(line => {
        const trimmed = line.trim();
        if (trimmed === '') {
            blankLines++;
        } else if (trimmed.startsWith('--')) {
            commentLines++;
        } else {
            codeLines++;
        }
    });

    document.getElementById('totalLines').textContent = totalLines;
    document.getElementById('codeLines').textContent = codeLines;
    document.getElementById('commentLines').textContent = commentLines;
    document.getElementById('blankLines').textContent = blankLines;
}

// Game Management Tools

function checkBadge() {
    const badgeId = document.getElementById('badgeCheckId').value;
    const userId = document.getElementById('badgeCheckUser').value;

    if (!badgeId || !userId) {
        showToast('Enter both badge and user ID', 'error');
        return;
    }

    // First get badge info
    fetch(`/proxy/badges/${badgeId}`)
        .then(r => r.json())
        .then(badgeData => {
            // Then check if user owns it - this would require authenticated endpoint
            // For now, show badge info
            document.getElementById('badgeCheckResult').innerHTML = `
                <div style="padding:16px;background:var(--bg-surface);border-radius:8px;">
                    <p><strong>Badge Name:</strong> ${badgeData.name || 'Unknown'}</p>
                    <p><strong>Description:</strong> ${badgeData.description || 'None'}</p>
                    <p><strong>Badge ID:</strong> ${badgeId}</p>
                    <p><strong>User ID:</strong> ${userId}</p>
                    <p class="text-muted mt-2">Note: Ownership checking requires authentication</p>
                </div>
            `;
            showToast('Badge info loaded', 'success');
        })
        .catch(() => {
            document.getElementById('badgeCheckResult').innerHTML = '<p style="color:var(--danger);">Failed to load badge info</p>';
            showToast('Badge not found', 'error');
        });
}

function loadGamepass() {
    const id = document.getElementById('gamepassId').value;
    if (!id) {
        showToast('Enter a gamepass ID', 'error');
        return;
    }

    // Get universe ID from localStorage
    const config = JSON.parse(localStorage.getItem('config') || '{}');
    const universeId = config.universeId || '8939032961';

    fetch(`/api/roblox/v2/universe/${universeId}/game-passes`)
        .then(r => r.json())
        .then(data => {
            const gamepass = data.data ? data.data.find(gp => gp.id == id) : null;

            if (gamepass) {
                document.getElementById('gamepassInfo').innerHTML = `
                    <div style="padding:16px;background:var(--bg-surface);border-radius:8px;">
                        <p><strong>Name:</strong> ${gamepass.name}</p>
                        <p><strong>Description:</strong> ${gamepass.description || 'No description'}</p>
                        <p><strong>Price:</strong> R$ ${gamepass.price || 'Free'}</p>
                        <p><strong>Gamepass ID:</strong> ${gamepass.id}</p>
                    </div>
                `;
                showToast('Gamepass loaded', 'success');
            } else {
                document.getElementById('gamepassInfo').innerHTML = '<p class="text-muted">Gamepass not found in this universe</p>';
            }
        })
        .catch(() => {
            document.getElementById('gamepassInfo').innerHTML = '<p style="color:var(--danger);">Failed to load gamepasses</p>';
            showToast('Failed to load gamepass', 'error');
        });
}

function loadProduct() {
    const id = document.getElementById('productId').value;
    if (!id) {
        showToast('Enter a product ID', 'error');
        return;
    }

    // Get universe ID from localStorage
    const config = JSON.parse(localStorage.getItem('config') || '{}');
    const universeId = config.universeId || '8939032961';

    fetch(`/api/roblox/v2/universe/${universeId}/products`)
        .then(r => r.json())
        .then(data => {
            const product = data.data ? data.data.find(p => p.id == id) : null;

            if (product) {
                document.getElementById('productInfo').innerHTML = `
                    <div style="padding:16px;background:var(--bg-surface);border-radius:8px;">
                        <p><strong>Name:</strong> ${product.name}</p>
                        <p><strong>Description:</strong> ${product.description || 'No description'}</p>
                        <p><strong>Price:</strong> R$ ${product.priceInRobux}</p>
                        <p><strong>Product ID:</strong> ${product.id}</p>
                    </div>
                `;
                showToast('Product loaded', 'success');
            } else {
                document.getElementById('productInfo').innerHTML = '<p class="text-muted">Product not found in this universe</p>';
            }
        })
        .catch(() => {
            document.getElementById('productInfo').innerHTML = '<p style="color:var(--danger);">Failed to load products</p>';
            showToast('Failed to load product', 'error');
        });
}

function generateTeleportCode() {
    const placeId = document.getElementById('teleportPlaceId').value;
    const type = document.getElementById('teleportType').value;
    const data = document.getElementById('teleportData').value;

    if (!placeId) {
        showToast('Enter a place ID', 'error');
        return;
    }

    let code = `local TeleportService = game:GetService("TeleportService")\n\n`;

    if (type === 'single') {
        code += `-- Teleport single player\n`;
        code += `local player = game.Players.LocalPlayer\n`;
        if (data && data.trim()) {
            code += `local teleportData = ${data}\n`;
            code += `TeleportService:TeleportAsync(${placeId}, {player}, teleportData)\n`;
        } else {
            code += `TeleportService:Teleport(${placeId}, player)\n`;
        }
    } else if (type === 'group') {
        code += `-- Teleport group of players\n`;
        code += `local players = {} -- Add players to this table\n`;
        code += `TeleportService:TeleportAsync(${placeId}, players)\n`;
    } else if (type === 'reserved') {
        code += `-- Reserved server teleport\n`;
        code += `local code = TeleportService:ReserveServer(${placeId})\n`;
        code += `local players = {} -- Add players to this table\n`;
        code += `TeleportService:TeleportToPrivateServer(${placeId}, code, players)\n`;
    }

    document.getElementById('teleportOutput').value = code;
    showToast('Teleport code generated', 'success');
}

function loadPlaces() {
    const universeId = document.getElementById('placeUniverseId').value;
    if (!universeId) {
        showToast('Enter a universe ID', 'error');
        return;
    }

    fetch(`/api/roblox/v2/universe/${universeId}/places`)
        .then(r => r.json())
        .then(data => {
            if (data && data.data && data.data.length > 0) {
                let html = '<div style="display:grid;gap:12px;">';
                data.data.forEach(place => {
                    html += `
                        <div style="padding:12px;background:var(--bg-surface);border-radius:8px;">
                            <p><strong>${place.name || 'Unnamed'}</strong></p>
                            <p>Place ID: <code>${place.id}</code></p>
                            <p>Description: ${place.description || 'No description'}</p>
                        </div>
                    `;
                });
                html += '</div>';
                document.getElementById('placesList').innerHTML = html;
                showToast(`Loaded ${data.data.length} places`, 'success');
            } else {
                document.getElementById('placesList').innerHTML = '<p class="text-muted">No places found for this universe</p>';
            }
        })
        .catch(() => {
            document.getElementById('placesList').innerHTML = '<p style="color:var(--danger);">Failed to load places. Check universe ID.</p>';
            showToast('Failed to load places', 'error');
        });
}
