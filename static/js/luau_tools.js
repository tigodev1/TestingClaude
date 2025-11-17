// Luau Tools - Advanced Obfuscator, Deobfuscator, and Utilities

// ============= OBFUSCATOR =============

let obfuscationSettings = {
    renameVariables: true,
    encryptStrings: true,
    controlFlow: false, // Disabled by default - can cause issues
    deadCode: true,
    encodeNumbers: true,
    antiTamper: false,
    intensity: 'medium', // light, medium, heavy
    customKey: ''
};

// Reserved Lua/Luau keywords and built-in functions that should NOT be renamed
const RESERVED_WORDS = new Set([
    'and', 'break', 'do', 'else', 'elseif', 'end', 'false', 'for', 'function',
    'if', 'in', 'local', 'nil', 'not', 'or', 'repeat', 'return', 'then',
    'true', 'until', 'while', 'continue',
    // Roblox globals
    'game', 'workspace', 'script', 'print', 'warn', 'wait', 'task', 'spawn',
    'delay', 'tick', 'time', 'typeof', 'type', 'pairs', 'ipairs', 'next',
    'select', 'unpack', 'table', 'math', 'string', 'coroutine', 'bit32',
    'utf8', 'os', 'debug', 'Instance', 'Vector2', 'Vector3', 'CFrame',
    'UDim', 'UDim2', 'Color3', 'BrickColor', 'Region3', 'Rect', 'Ray',
    'Enum', 'Axes', 'Faces', 'Region3int16', 'Vector2int16', 'Vector3int16',
    'NumberRange', 'NumberSequence', 'ColorSequence', 'PhysicalProperties',
    'Random', 'DateTime', 'elapsedTime', 'require', 'getfenv', 'setfenv',
    'loadstring', 'newproxy', 'tonumber', 'tostring', 'pcall', 'xpcall',
    'error', 'assert', 'collectgarbage', 'gcinfo', 'getmetatable', 'setmetatable',
    'rawget', 'rawset', 'rawequal', 'rawlen'
]);

function updateObfuscationSettings() {
    obfuscationSettings.renameVariables = document.getElementById('obfRenameVars').checked;
    obfuscationSettings.encryptStrings = document.getElementById('obfEncryptStrings').checked;
    obfuscationSettings.controlFlow = document.getElementById('obfControlFlow').checked;
    obfuscationSettings.deadCode = document.getElementById('obfDeadCode').checked;
    obfuscationSettings.encodeNumbers = document.getElementById('obfEncodeNumbers').checked;
    obfuscationSettings.antiTamper = document.getElementById('obfAntiTamper').checked;
    obfuscationSettings.intensity = document.getElementById('obfIntensity').value;
    obfuscationSettings.customKey = document.getElementById('obfCustomKey').value;
}

function generateRandomName(prefix = 'l') {
    const chars = 'abcdefghijklmnopqrstuvwxyz';
    const confusing = 'IlO0_';
    const useConfusing = obfuscationSettings.intensity === 'heavy';
    const charSet = useConfusing ? confusing : chars;
    const length = obfuscationSettings.intensity === 'heavy' ? 12 : obfuscationSettings.intensity === 'medium' ? 8 : 6;

    let name = prefix + '_';
    for (let i = 0; i < length; i++) {
        name += charSet[Math.floor(Math.random() * charSet.length)];
    }
    return name;
}

function obfuscateCode() {
    updateObfuscationSettings();
    const input = document.getElementById('obfuscatorInput').value;
    const output = document.getElementById('obfuscatorOutput');

    if (!input.trim()) {
        showToast('Please enter code to obfuscate', 'error');
        return;
    }

    try {
        let obfuscated = input;
        const varMap = new Map();

        // Step 1: Rename local variables and function parameters
        if (obfuscationSettings.renameVariables) {
            // Find all local variables (but not reserved words)
            const localPattern = /local\s+function\s+([a-zA-Z_][a-zA-Z0-9_]*)|local\s+([a-zA-Z_][a-zA-Z0-9_]*)/g;
            let match;
            const tempInput = input; // Use original input for pattern matching

            while ((match = localPattern.exec(tempInput)) !== null) {
                const varName = match[1] || match[2];
                if (varName && !RESERVED_WORDS.has(varName) && !varMap.has(varName)) {
                    varMap.set(varName, generateRandomName('var'));
                }
            }

            // Find function parameters
            const paramPattern = /function\s*\(([^)]*)\)/g;
            while ((match = paramPattern.exec(tempInput)) !== null) {
                const params = match[1].split(',').map(p => p.trim());
                params.forEach(param => {
                    if (param && !RESERVED_WORDS.has(param) && !varMap.has(param)) {
                        varMap.set(param, generateRandomName('arg'));
                    }
                });
            }

            // Replace variables (use word boundaries to avoid partial matches)
            varMap.forEach((newName, oldName) => {
                const regex = new RegExp(`\\b${oldName}\\b`, 'g');
                obfuscated = obfuscated.replace(regex, newName);
            });
        }

        // Step 2: Encrypt strings (simplified and working version)
        if (obfuscationSettings.encryptStrings) {
            const strings = [];
            let stringIndex = 0;

            // Simple string encryption using character codes
            obfuscated = obfuscated.replace(/"([^"]*)"/g, (match, str) => {
                if (str.length === 0) return '""';
                const charCodes = Array.from(str).map(c => c.charCodeAt(0));
                strings.push(charCodes);
                return `_S(${stringIndex++})`;
            });

            obfuscated = obfuscated.replace(/'([^']*)'/g, (match, str) => {
                if (str.length === 0) return "''";
                const charCodes = Array.from(str).map(c => c.charCodeAt(0));
                strings.push(charCodes);
                return `_S(${stringIndex++})`;
            });

            if (strings.length > 0) {
                // Create string table
                const stringTable = strings.map((codes, idx) => {
                    return `[${idx}]={${codes.join(',')}}`;
                }).join(',');

                const decryptor = `local _T={${stringTable}}
local function _S(i)
    local t=_T[i]
    local s=""
    for j=1,#t do
        s=s..string.char(t[j])
    end
    return s
end
`;
                obfuscated = decryptor + obfuscated;
            }
        }

        // Step 3: Encode numbers (carefully to avoid breaking syntax)
        if (obfuscationSettings.encodeNumbers) {
            // Only encode standalone numbers, not those in strings or after 0x
            obfuscated = obfuscated.replace(/(?<!0x|\w)(\d+)(?!\w|x)/g, (match) => {
                const num = parseInt(match);
                if (num === 0 || num === 1) return match; // Don't encode 0 and 1

                const encodings = [
                    `(${num})`, // Just wrap in parentheses
                    `(0x${num.toString(16)})`, // Hexadecimal
                ];

                // Add more complex encodings for higher intensity
                if (obfuscationSettings.intensity !== 'light') {
                    if (num % 2 === 0) {
                        encodings.push(`(${num/2}*2)`);
                    }
                    if (num > 10) {
                        encodings.push(`(${num-5}+5)`);
                    }
                }

                return encodings[Math.floor(Math.random() * encodings.length)];
            });
        }

        // Step 4: Inject dead code (safe, non-breaking)
        if (obfuscationSettings.deadCode) {
            const deadCodeSnippets = [
                `local ${generateRandomName('_junk')}=0`,
                `local ${generateRandomName('_unused')}=nil`,
                `local ${generateRandomName('_dummy')}=false`,
            ];

            const intensity = obfuscationSettings.intensity === 'heavy' ? 5 : obfuscationSettings.intensity === 'medium' ? 3 : 1;
            for (let i = 0; i < intensity; i++) {
                const snippet = deadCodeSnippets[Math.floor(Math.random() * deadCodeSnippets.length)];
                obfuscated = snippet + '\n' + obfuscated;
            }
        }

        // Step 5: Control flow obfuscation (FIXED - much safer now)
        if (obfuscationSettings.controlFlow) {
            const controlFlowVar = generateRandomName('_CF');
            // Just add a control variable at the top, don't wrap every line
            obfuscated = `local ${controlFlowVar}=true\n` + obfuscated;

            // Optionally add some dummy checks
            if (obfuscationSettings.intensity === 'heavy') {
                const dummyCheck = `if not ${controlFlowVar} then return end\n`;
                obfuscated = obfuscated + '\n' + dummyCheck;
            }
        }

        // Step 6: Anti-tamper (simplified version)
        if (obfuscationSettings.antiTamper) {
            const antiTamperVar = generateRandomName('_AT');
            const antiTamper = `local ${antiTamperVar}=script:GetFullName()\n`;
            obfuscated = antiTamper + obfuscated;
        }

        output.value = obfuscated;
        showToast('Code obfuscated successfully!', 'success');

    } catch (e) {
        showToast('Error obfuscating code: ' + e.message, 'error');
        console.error('Obfuscation error:', e);
    }
}

// ============= DEOBFUSCATOR =============

function deobfuscateCode() {
    const input = document.getElementById('deobfuscatorInput').value;
    const output = document.getElementById('deobfuscatorOutput');

    if (!input.trim()) {
        showToast('Please enter code to deobfuscate', 'error');
        return;
    }

    try {
        let deobfuscated = input;

        // Remove string decryption functions
        deobfuscated = deobfuscated.replace(/local _T=\{.*?\}\s*local function _S\(i\).*?end\s*/gs, '');
        deobfuscated = deobfuscated.replace(/local function _D\(.*?\).*?end\s*/gs, '');

        // Decode hex numbers
        deobfuscated = deobfuscated.replace(/\(0x([0-9a-fA-F]+)\)/g, (match, hex) => {
            return parseInt(hex, 16).toString();
        });

        // Simplify math expressions
        deobfuscated = deobfuscated.replace(/\((\d+)\+0\)/g, '$1');
        deobfuscated = deobfuscated.replace(/\((\d+)\*1\)/g, '$1');
        deobfuscated = deobfuscated.replace(/\((\d+)\/1\)/g, '$1');

        // Simplify simple additions/subtractions
        deobfuscated = deobfuscated.replace(/\((\d+)\+(\d+)\)/g, (match, a, b) => {
            return (parseInt(a) + parseInt(b)).toString();
        });
        deobfuscated = deobfuscated.replace(/\((\d+)-(\d+)\)/g, (match, a, b) => {
            return (parseInt(a) - parseInt(b)).toString();
        });
        deobfuscated = deobfuscated.replace(/\((\d+)\*(\d+)\)/g, (match, a, b) => {
            return (parseInt(a) * parseInt(b)).toString();
        });

        // Remove unnecessary parentheses around single numbers
        deobfuscated = deobfuscated.replace(/\((\d+)\)/g, '$1');

        // Remove dead code (common junk variables)
        deobfuscated = deobfuscated.replace(/local _[a-z]+_[a-zA-Z0-9_]+=(?:0|nil|false|true)\s*\n/g, '');

        // Remove control flow variables
        deobfuscated = deobfuscated.replace(/local _CF_[a-zA-Z0-9_]+=true\s*\n/g, '');
        deobfuscated = deobfuscated.replace(/if not _CF_[a-zA-Z0-9_]+ then return end\s*\n/g, '');

        // Remove anti-tamper
        deobfuscated = deobfuscated.replace(/local _AT_[a-zA-Z0-9_]+=script:GetFullName\(\)\s*\n/g, '');

        // Beautify the result
        deobfuscated = beautifyLuau(deobfuscated);

        output.value = deobfuscated;
        showToast('Code deobfuscated and beautified!', 'success');

    } catch (e) {
        showToast('Error deobfuscating code: ' + e.message, 'error');
        console.error('Deobfuscation error:', e);
    }
}

// ============= BEAUTIFIER =============

function beautifyLuau(code) {
    const lines = code.split('\n');
    let indent = 0;
    const indentSize = 4;
    let beautified = [];

    const increaseIndent = ['then', 'do', 'repeat'];
    const decreaseIndent = ['end', 'until'];
    const decreaseBeforeLine = ['else', 'elseif', 'until'];

    lines.forEach(line => {
        let trimmed = line.trim();
        if (!trimmed) {
            beautified.push('');
            return;
        }

        // Handle comments
        if (trimmed.startsWith('--')) {
            beautified.push(' '.repeat(indent * indentSize) + trimmed);
            return;
        }

        // Decrease indent before line for certain keywords
        if (decreaseBeforeLine.some(kw => trimmed.startsWith(kw))) {
            indent = Math.max(0, indent - 1);
        }

        // Decrease for 'end' before adding the line
        if (trimmed === 'end' || trimmed.startsWith('end ')) {
            indent = Math.max(0, indent - 1);
        }

        // Add indented line
        beautified.push(' '.repeat(indent * indentSize) + trimmed);

        // Increase indent after line for certain keywords
        if (increaseIndent.some(kw => trimmed.includes(kw))) {
            indent++;
        }

        // Special handling for function definitions
        if (trimmed.startsWith('function') || trimmed.includes('= function')) {
            indent++;
        }
    });

    return beautified.join('\n');
}

function beautifyCode() {
    const input = document.getElementById('beautifierInput').value;
    const output = document.getElementById('beautifierOutput');

    if (!input.trim()) {
        showToast('Please enter code to beautify', 'error');
        return;
    }

    output.value = beautifyLuau(input);
    showToast('Code beautified!', 'success');
}

function minifyCode() {
    const input = document.getElementById('beautifierInput').value;
    const output = document.getElementById('beautifierOutput');

    if (!input.trim()) {
        showToast('Please enter code to minify', 'error');
        return;
    }

    // Remove comments and extra whitespace
    let minified = input
        .replace(/--\[\[[\s\S]*?\]\]/g, '') // Multi-line comments
        .replace(/--[^\n]*/g, '') // Single-line comments
        .split('\n')
        .map(line => line.trim())
        .filter(line => line.length > 0)
        .join(' ')
        .replace(/\s+/g, ' '); // Multiple spaces to single

    output.value = minified;
    showToast('Code minified!', 'success');
}

// ============= SCRIPT ANALYZER =============

function analyzeScript() {
    const input = document.getElementById('analyzerInput').value;
    const output = document.getElementById('analyzerOutput');

    if (!input.trim()) {
        showToast('Please enter code to analyze', 'error');
        return;
    }

    const issues = [];
    const stats = {
        lines: input.split('\n').length,
        functions: (input.match(/function\s+/g) || []).length,
        locals: (input.match(/local\s+/g) || []).length,
        loops: (input.match(/\b(for|while|repeat)\b/g) || []).length,
        comments: (input.match(/--/g) || []).length
    };

    // Check for deprecated functions
    const deprecated = [
        { pattern: /\bwait\(\)/, msg: 'wait() without argument is deprecated, use task.wait()' },
        { pattern: /\bspawn\(/, msg: 'spawn() is deprecated, use task.spawn()' },
        { pattern: /\bdelay\(/, msg: 'delay() is deprecated, use task.delay()' },
        { pattern: /LoadLibrary\(/, msg: 'LoadLibrary is deprecated and removed' },
        { pattern: /\.RobloxLocked/, msg: 'RobloxLocked is deprecated' }
    ];

    deprecated.forEach(({ pattern, msg }) => {
        if (pattern.test(input)) {
            issues.push({ type: 'deprecated', message: msg });
        }
    });

    // Check for potential issues
    if (/while\s+true\s+do/.test(input) && !/task\.wait\(|wait\(/.test(input)) {
        issues.push({ type: 'performance', message: 'Infinite loop without wait() detected - may cause script timeout' });
    }

    if (/_G\[/.test(input) || /_G\./.test(input)) {
        issues.push({ type: 'warning', message: 'Usage of _G detected - consider using ModuleScripts instead' });
    }

    if (/getfenv|setfenv/.test(input)) {
        issues.push({ type: 'security', message: 'getfenv/setfenv detected - potential security risk' });
    }

    if (/loadstring/.test(input)) {
        issues.push({ type: 'security', message: 'loadstring() detected - major security risk' });
    }

    if (stats.comments === 0 && stats.lines > 20) {
        issues.push({ type: 'warning', message: 'No comments found - consider adding documentation' });
    }

    // Generate report
    let report = '<div style="font-family: monospace;">';
    report += '<h4 style="color: var(--accent); margin-bottom: 12px;">Code Statistics:</h4>';
    report += '<div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; margin-bottom: 16px;">';
    report += `<p><strong>Lines:</strong> ${stats.lines}</p>`;
    report += `<p><strong>Functions:</strong> ${stats.functions}</p>`;
    report += `<p><strong>Local Variables:</strong> ${stats.locals}</p>`;
    report += `<p><strong>Loops:</strong> ${stats.loops}</p>`;
    report += `<p><strong>Comments:</strong> ${stats.comments}</p>`;
    report += '</div>';

    if (issues.length > 0) {
        report += '<h4 style="color: var(--warning); margin-top: 16px; margin-bottom: 12px;">Issues Found:</h4>';
        issues.forEach(issue => {
            const color = {
                deprecated: '#ff9800',
                performance: '#f44336',
                warning: '#ff9800',
                security: '#d32f2f'
            }[issue.type];
            const icon = {
                deprecated: 'exclamation-triangle',
                performance: 'tachometer-alt',
                warning: 'exclamation-circle',
                security: 'shield-alt'
            }[issue.type];
            report += `<p style="color: ${color}; margin: 8px 0;"><i class="fas fa-${icon}"></i> <strong>${issue.type.toUpperCase()}:</strong> ${issue.message}</p>`;
        });
    } else {
        report += '<p style="color: var(--success); margin-top: 16px;"><i class="fas fa-check-circle"></i> <strong>No issues found!</strong> Code looks good.</p>';
    }

    report += '</div>';
    output.innerHTML = report;
    showToast('Analysis complete!', 'success');
}

// ============= UTILITIES =============

function encodeBase64() {
    const input = document.getElementById('base64Input').value;
    const output = document.getElementById('base64Output');

    if (!input) {
        showToast('Please enter text to encode', 'error');
        return;
    }

    try {
        output.value = btoa(unescape(encodeURIComponent(input)));
        showToast('Encoded to Base64', 'success');
    } catch (e) {
        showToast('Error encoding: ' + e.message, 'error');
    }
}

function decodeBase64() {
    const input = document.getElementById('base64Input').value;
    const output = document.getElementById('base64Output');

    if (!input) {
        showToast('Please enter Base64 to decode', 'error');
        return;
    }

    try {
        output.value = decodeURIComponent(escape(atob(input)));
        showToast('Decoded from Base64', 'success');
    } catch (e) {
        showToast('Error decoding: ' + e.message, 'error');
    }
}

async function generateHash() {
    const input = document.getElementById('hashInput').value;
    const output = document.getElementById('hashOutput');
    const algorithm = document.getElementById('hashAlgorithm').value;

    if (!input) {
        showToast('Please enter text to hash', 'error');
        return;
    }

    try {
        const encoder = new TextEncoder();
        const data = encoder.encode(input);
        const hashBuffer = await crypto.subtle.digest(algorithm, data);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
        output.value = hashHex;
        showToast('Hash generated!', 'success');
    } catch (e) {
        showToast('Error generating hash: ' + e.message, 'error');
    }
}

function generateUUID() {
    const uuid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
    document.getElementById('uuidOutput').value = uuid;
    showToast('UUID generated!', 'success');
}

function generateRBXGUID() {
    const template = '{XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX}';
    const guid = template.replace(/X/g, () => {
        return Math.floor(Math.random() * 16).toString(16).toUpperCase();
    });
    document.getElementById('uuidOutput').value = guid;
    showToast('RBXGUID generated!', 'success');
}

function testRegex() {
    const pattern = document.getElementById('regexPattern').value;
    const flags = document.getElementById('regexFlags').value;
    const testString = document.getElementById('regexTest').value;
    const output = document.getElementById('regexOutput');

    if (!pattern) {
        showToast('Please enter a regex pattern', 'error');
        return;
    }

    try {
        const regex = new RegExp(pattern, flags);
        const matches = Array.from(testString.matchAll(new RegExp(pattern, flags + (flags.includes('g') ? '' : 'g'))));

        let result = '<div style="font-family: monospace;">';
        if (matches.length > 0) {
            result += `<p style="color: var(--success); margin-bottom: 12px;"><i class="fas fa-check-circle"></i> <strong>${matches.length} match(es) found:</strong></p>`;
            matches.forEach((match, i) => {
                result += `<p style="margin: 6px 0;"><strong>Match ${i + 1}:</strong> <code style="background: var(--bg-secondary); padding: 2px 8px; border-radius: 4px;">${match[0]}</code></p>`;
                if (match.length > 1) {
                    for (let j = 1; j < match.length; j++) {
                        result += `<p style="margin: 4px 0 4px 20px; color: var(--text-secondary);">Group ${j}: <code style="background: var(--bg-secondary); padding: 2px 8px; border-radius: 4px;">${match[j]}</code></p>`;
                    }
                }
            });
        } else {
            result += '<p style="color: var(--warning);"><i class="fas fa-info-circle"></i> No matches found</p>';
        }
        result += '</div>';
        output.innerHTML = result;
        showToast('Regex tested!', 'success');
    } catch (e) {
        output.innerHTML = `<p style="color: var(--danger);"><i class="fas fa-exclamation-triangle"></i> <strong>Error:</strong> ${e.message}</p>`;
        showToast('Invalid regex pattern', 'error');
    }
}

// ============= FILE OPERATIONS =============

function uploadObfuscatorFile() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.lua,.luau,.txt';
    input.onchange = (e) => {
        const file = e.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (event) => {
            document.getElementById('obfuscatorInput').value = event.target.result;
            showToast(`Loaded ${file.name}`, 'success');
        };
        reader.onerror = () => {
            showToast('Error reading file', 'error');
        };
        reader.readAsText(file);
    };
    input.click();
}

function downloadObfuscatorFile() {
    const content = document.getElementById('obfuscatorOutput').value;
    if (!content.trim()) {
        showToast('No output to download', 'error');
        return;
    }
    downloadFile(content, 'obfuscated.lua', 'text/plain');
}

function uploadDeobfuscatorFile() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.lua,.luau,.txt';
    input.onchange = (e) => {
        const file = e.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (event) => {
            document.getElementById('deobfuscatorInput').value = event.target.result;
            showToast(`Loaded ${file.name}`, 'success');
        };
        reader.onerror = () => {
            showToast('Error reading file', 'error');
        };
        reader.readAsText(file);
    };
    input.click();
}

function downloadDeobfuscatorFile() {
    const content = document.getElementById('deobfuscatorOutput').value;
    if (!content.trim()) {
        showToast('No output to download', 'error');
        return;
    }
    downloadFile(content, 'deobfuscated.lua', 'text/plain');
}

function downloadFile(content, filename, mimeType) {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast(`Downloaded ${filename}`, 'success');
}

// Copy functions
function copyObfuscatorOutput() {
    const output = document.getElementById('obfuscatorOutput');
    if (!output.value.trim()) {
        showToast('No output to copy', 'error');
        return;
    }
    output.select();
    document.execCommand('copy');
    showToast('Copied to clipboard!', 'success');
}

function copyDeobfuscatorOutput() {
    const output = document.getElementById('deobfuscatorOutput');
    if (!output.value.trim()) {
        showToast('No output to copy', 'error');
        return;
    }
    output.select();
    document.execCommand('copy');
    showToast('Copied to clipboard!', 'success');
}
