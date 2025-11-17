// Luau Tools - Advanced Obfuscator, Deobfuscator, and Utilities

// ============= OBFUSCATOR =============

let obfuscationSettings = {
    renameVariables: true,
    encryptStrings: true,
    controlFlow: true,
    deadCode: true,
    encodeNumbers: true,
    antiTamper: false,
    intensity: 'heavy',
    customKey: ''
};

// Reserved Lua/Luau keywords and built-in functions
const RESERVED_WORDS = new Set([
    'and', 'break', 'do', 'else', 'elseif', 'end', 'false', 'for', 'function',
    'if', 'in', 'local', 'nil', 'not', 'or', 'repeat', 'return', 'then',
    'true', 'until', 'while', 'continue',
    'game', 'workspace', 'script', 'print', 'warn', 'wait', 'task', 'spawn',
    'delay', 'tick', 'time', 'typeof', 'type', 'pairs', 'ipairs', 'next',
    'select', 'unpack', 'table', 'math', 'string', 'coroutine', 'bit32',
    'utf8', 'os', 'debug', 'Instance', 'Vector2', 'Vector3', 'CFrame',
    'UDim', 'UDim2', 'Color3', 'BrickColor', 'Region3', 'Rect', 'Ray',
    'Enum', 'require', 'tonumber', 'tostring', 'pcall', 'xpcall',
    'error', 'assert', 'getmetatable', 'setmetatable', 'rawget', 'rawset'
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
    const intensity = obfuscationSettings.intensity;

    if (intensity === 'heavy') {
        // Ultra confusing characters
        const chars = ['I', 'l', '1', 'i', 'O', '0', 'o'];
        const length = 16;
        let name = '';
        for (let i = 0; i < length; i++) {
            name += chars[Math.floor(Math.random() * chars.length)];
        }
        return '_' + name;
    } else if (intensity === 'medium') {
        // Mix of confusing and normal
        const chars = 'IlO0oabcdefghijklmnopqrstuvwxyz_';
        const length = 12;
        let name = prefix + '_';
        for (let i = 0; i < length; i++) {
            name += chars[Math.floor(Math.random() * chars.length)];
        }
        return name;
    } else {
        // Light - just random letters
        const chars = 'abcdefghijklmnopqrstuvwxyz';
        const length = 8;
        let name = prefix + '_';
        for (let i = 0; i < length; i++) {
            name += chars[Math.floor(Math.random() * chars.length)];
        }
        return name;
    }
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
        const stringTable = [];
        let stringIndex = 0;

        // Step 1: String Encryption (do this FIRST before other transformations)
        if (obfuscationSettings.encryptStrings) {
            // Encrypt double-quoted strings
            obfuscated = obfuscated.replace(/"([^"]*)"/g, (match, str) => {
                if (str.length === 0) return '""';
                const index = stringIndex++;
                stringTable.push(str);
                return `__STRENC__${index}__`;
            });

            // Encrypt single-quoted strings
            obfuscated = obfuscated.replace(/'([^']*)'/g, (match, str) => {
                if (str.length === 0) return "''";
                const index = stringIndex++;
                stringTable.push(str);
                return `__STRENC__${index}__`;
            });
        }

        // Step 2: Rename variables
        if (obfuscationSettings.renameVariables) {
            const localPattern = /local\s+function\s+([a-zA-Z_][a-zA-Z0-9_]*)|local\s+([a-zA-Z_][a-zA-Z0-9_]*)/g;
            let match;
            const tempInput = obfuscated;

            while ((match = localPattern.exec(tempInput)) !== null) {
                const varName = match[1] || match[2];
                if (varName && !RESERVED_WORDS.has(varName) && !varMap.has(varName)) {
                    varMap.set(varName, generateRandomName());
                }
            }

            // Find function parameters
            const paramPattern = /function\s*\(([^)]*)\)/g;
            while ((match = paramPattern.exec(tempInput)) !== null) {
                if (match[1].trim()) {
                    const params = match[1].split(',').map(p => p.trim());
                    params.forEach(param => {
                        if (param && !RESERVED_WORDS.has(param) && !varMap.has(param)) {
                            varMap.set(param, generateRandomName());
                        }
                    });
                }
            }

            // Replace variables
            varMap.forEach((newName, oldName) => {
                const regex = new RegExp(`\\b${oldName}\\b`, 'g');
                obfuscated = obfuscated.replace(regex, newName);
            });
        }

        // Step 3: Number encoding
        if (obfuscationSettings.encodeNumbers) {
            obfuscated = obfuscated.replace(/\b(\d+)\b/g, (match) => {
                const num = parseInt(match);
                if (num === 0 || num === 1) return match;

                const encodings = [
                    `(${num})`,
                    `(0x${num.toString(16)})`,
                ];

                if (obfuscationSettings.intensity !== 'light') {
                    if (num > 5) encodings.push(`(${num-3}+3)`);
                    if (num % 2 === 0) encodings.push(`(${num/2}+${num/2})`);
                    if (num > 10) encodings.push(`(${Math.floor(num/2)}*2${num%2?'+1':''})`);
                }

                if (obfuscationSettings.intensity === 'heavy') {
                    if (num > 100) encodings.push(`(${Math.floor(num/10)}*10+${num%10})`);
                    if (num > 50) encodings.push(`(${num-10}+10)`);
                }

                return encodings[Math.floor(Math.random() * encodings.length)];
            });
        }

        // Step 4: Add string decryption if needed
        if (obfuscationSettings.encryptStrings && stringTable.length > 0) {
            // Build the string table with proper Luau syntax
            const tableEntries = stringTable.map((str, idx) => {
                // Escape special characters
                const escaped = str
                    .replace(/\\/g, '\\\\')
                    .replace(/"/g, '\\"')
                    .replace(/\n/g, '\\n')
                    .replace(/\r/g, '\\r')
                    .replace(/\t/g, '\\t');
                return `"${escaped}"`;
            });

            const stringTableCode = `local __STRINGS__ = {${tableEntries.join(',')}}
local function __STR__(i) return __STRINGS__[i+1] end
`;
            // Replace placeholders with string accessor calls
            for (let i = 0; i < stringTable.length; i++) {
                obfuscated = obfuscated.replace(
                    new RegExp(`__STRENC__${i}__`, 'g'),
                    `__STR__(${i})`
                );
            }

            obfuscated = stringTableCode + obfuscated;
        }

        // Step 5: Dead code injection
        if (obfuscationSettings.deadCode) {
            const deadCodeSnippets = [];
            const intensity = obfuscationSettings.intensity === 'heavy' ? 8 : obfuscationSettings.intensity === 'medium' ? 4 : 2;

            for (let i = 0; i < intensity; i++) {
                const varName = generateRandomName('_junk');
                const snippets = [
                    `local ${varName}=(function() return nil end)()`,
                    `local ${varName}=math.random(1,999999)`,
                    `local ${varName}=tostring({})`,
                    `local ${varName}=tick()*0`,
                    `local ${varName}=(function() local x=1 for i=1,0 do x=x+1 end return x end)()`,
                ];
                deadCodeSnippets.push(snippets[Math.floor(Math.random() * snippets.length)]);
            }

            obfuscated = deadCodeSnippets.join('\n') + '\n' + obfuscated;
        }

        // Step 6: Control flow obfuscation (safe version)
        if (obfuscationSettings.controlFlow) {
            const cfVar = generateRandomName('_CF');
            obfuscated = `local ${cfVar}=(1==1)\n` + obfuscated;

            if (obfuscationSettings.intensity === 'heavy') {
                // Add opaque predicates (conditions that are always true/false but look complex)
                const predicates = [
                    `local ${generateRandomName('_OP')}=(math.abs(-1)==1)`,
                    `local ${generateRandomName('_OP')}=(tostring(1)=="1")`,
                    `local ${generateRandomName('_OP')}=(#{1,2}==2)`,
                ];
                obfuscated = predicates.join('\n') + '\n' + obfuscated;
            }
        }

        // Step 7: Anti-tamper
        if (obfuscationSettings.antiTamper) {
            const atVar = generateRandomName('_AT');
            const antiTamper = `local ${atVar}=script
local ${generateRandomName('_CHECK')}=(function()
    if ${atVar} and ${atVar}.Parent then
        return true
    end
    return false
end)()
`;
            obfuscated = antiTamper + obfuscated;
        }

        // Step 8: Add wrapper comment
        const header = `-- Obfuscated with Tigos Hub Luau Obfuscator
-- Intensity: ${obfuscationSettings.intensity}
-- Techniques: ${[
    obfuscationSettings.renameVariables && 'Variable Renaming',
    obfuscationSettings.encryptStrings && 'String Encryption',
    obfuscationSettings.encodeNumbers && 'Number Encoding',
    obfuscationSettings.controlFlow && 'Control Flow',
    obfuscationSettings.deadCode && 'Dead Code',
    obfuscationSettings.antiTamper && 'Anti-Tamper'
].filter(Boolean).join(', ')}

`;
        obfuscated = header + obfuscated;

        output.value = obfuscated;
        showToast('Code obfuscated successfully! ' + stringTable.length + ' strings encrypted', 'success');

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
        let stringsDecoded = 0;

        // Remove obfuscator header comments
        deobfuscated = deobfuscated.replace(/-- Obfuscated with.*?\n\n/s, '');

        // Step 1: Detect and decode string table
        const stringTableMatch = deobfuscated.match(/local __STRINGS__ = \{(.*?)\}\s*local function __STR__\(i\) return __STRINGS__\[i\+1\] end/s);
        if (stringTableMatch) {
            try {
                // Extract string table
                const tableContent = stringTableMatch[1];
                const strings = [];

                // Parse the string table more carefully
                let currentString = '';
                let inString = false;
                let escaped = false;

                for (let i = 0; i < tableContent.length; i++) {
                    const char = tableContent[i];

                    if (escaped) {
                        currentString += char;
                        escaped = false;
                        continue;
                    }

                    if (char === '\\') {
                        escaped = true;
                        currentString += char;
                        continue;
                    }

                    if (char === '"') {
                        if (inString) {
                            strings.push(currentString);
                            currentString = '';
                            inString = false;
                        } else {
                            inString = true;
                        }
                        continue;
                    }

                    if (inString) {
                        currentString += char;
                    }
                }

                // Remove the string table and decoder function
                deobfuscated = deobfuscated.replace(/local __STRINGS__ = \{.*?\}\s*local function __STR__\(i\) return __STRINGS__\[i\+1\] end\s*/s, '');

                // Replace __STR__(n) calls with actual strings
                deobfuscated = deobfuscated.replace(/__STR__\((\d+)\)/g, (match, index) => {
                    const idx = parseInt(index);
                    if (idx >= 0 && idx < strings.length) {
                        stringsDecoded++;
                        return `"${strings[idx]}"`;
                    }
                    return match;
                });

            } catch (e) {
                console.error('Error decoding string table:', e);
            }
        }

        // Step 2: Decode hex numbers
        deobfuscated = deobfuscated.replace(/\(0x([0-9a-fA-F]+)\)/g, (match, hex) => {
            return parseInt(hex, 16).toString();
        });

        // Step 3: Simplify math expressions
        // Simple addition
        deobfuscated = deobfuscated.replace(/\((\d+)\+(\d+)\)/g, (match, a, b) => {
            const result = parseInt(a) + parseInt(b);
            return result.toString();
        });

        // Simple subtraction
        deobfuscated = deobfuscated.replace(/\((\d+)-(\d+)\)/g, (match, a, b) => {
            const result = parseInt(a) - parseInt(b);
            return result.toString();
        });

        // Simple multiplication
        deobfuscated = deobfuscated.replace(/\((\d+)\*(\d+)\)/g, (match, a, b) => {
            const result = parseInt(a) * parseInt(b);
            return result.toString();
        });

        // Remove simple parentheses around numbers
        deobfuscated = deobfuscated.replace(/\((\d+)\)/g, '$1');

        // Step 4: Remove dead code patterns
        deobfuscated = deobfuscated.replace(/local _junk_[a-zA-Z0-9_]+=\(function\(\) return nil end\)\(\)\s*/g, '');
        deobfuscated = deobfuscated.replace(/local _junk_[a-zA-Z0-9_]+=math\.random\([^)]+\)\s*/g, '');
        deobfuscated = deobfuscated.replace(/local _junk_[a-zA-Z0-9_]+=tostring\(\{\}\)\s*/g, '');
        deobfuscated = deobfuscated.replace(/local _junk_[a-zA-Z0-9_]+=tick\(\)\*0\s*/g, '');
        deobfuscated = deobfuscated.replace(/local _junk_[a-zA-Z0-9_]+=\(function\(\).*?end\)\(\)\s*/gs, '');
        deobfuscated = deobfuscated.replace(/local _unused_[a-zA-Z0-9_]+=.*?\n/g, '');
        deobfuscated = deobfuscated.replace(/local _dummy_[a-zA-Z0-9_]+=.*?\n/g, '');

        // Step 5: Remove control flow variables
        deobfuscated = deobfuscated.replace(/local _CF_[a-zA-Z0-9_]+=\(1==1\)\s*/g, '');
        deobfuscated = deobfuscated.replace(/local _CF_[a-zA-Z0-9_]+=true\s*/g, '');

        // Remove opaque predicates
        deobfuscated = deobfuscated.replace(/local _OP_[a-zA-Z0-9_]+=\(.*?\)\s*/g, '');

        // Step 6: Remove anti-tamper code
        deobfuscated = deobfuscated.replace(/local _AT_[a-zA-Z0-9_]+=script\s*/g, '');
        deobfuscated = deobfuscated.replace(/local _CHECK_[a-zA-Z0-9_]+=\(function\(\).*?end\)\(\)\s*/gs, '');

        // Step 7: Clean up extra blank lines
        deobfuscated = deobfuscated.replace(/\n\n\n+/g, '\n\n');

        // Step 8: Beautify
        deobfuscated = beautifyLuau(deobfuscated);

        output.value = deobfuscated;

        const messages = [];
        if (stringsDecoded > 0) messages.push(`${stringsDecoded} strings decoded`);
        messages.push('Code deobfuscated and beautified!');

        showToast(messages.join(' - '), 'success');

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

        // Decrease indent for end, else, elseif, until
        if (trimmed === 'end' || trimmed.startsWith('end ') || trimmed.startsWith('end;')) {
            indent = Math.max(0, indent - 1);
        }
        if (trimmed.startsWith('else') || trimmed.startsWith('elseif') || trimmed.startsWith('until')) {
            const tempIndent = Math.max(0, indent - 1);
            beautified.push(' '.repeat(tempIndent * indentSize) + trimmed);
            return;
        }

        // Add indented line
        beautified.push(' '.repeat(indent * indentSize) + trimmed);

        // Increase indent after keywords
        if (trimmed.includes(' then') || trimmed.endsWith(' then')) {
            indent++;
        }
        if (trimmed.includes(' do') || trimmed.endsWith(' do') || trimmed === 'do') {
            indent++;
        }
        if (trimmed.startsWith('function') || trimmed.includes('= function')) {
            indent++;
        }
        if (trimmed.startsWith('repeat')) {
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

    let minified = input
        .replace(/--\[\[[\s\S]*?\]\]/g, '')
        .replace(/--[^\n]*/g, '')
        .split('\n')
        .map(line => line.trim())
        .filter(line => line.length > 0)
        .join(' ')
        .replace(/\s+/g, ' ');

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
        issues.push({ type: 'performance', message: 'Infinite loop without wait() - may cause timeout' });
    }

    if (/_G\[/.test(input) || /_G\./.test(input)) {
        issues.push({ type: 'warning', message: 'Usage of _G - consider ModuleScripts instead' });
    }

    if (/getfenv|setfenv/.test(input)) {
        issues.push({ type: 'security', message: 'getfenv/setfenv detected - security risk' });
    }

    if (/loadstring/.test(input)) {
        issues.push({ type: 'security', message: 'loadstring() detected - major security risk' });
    }

    if (stats.comments === 0 && stats.lines > 20) {
        issues.push({ type: 'warning', message: 'No comments - consider adding documentation' });
    }

    // Check if code might be obfuscated
    if (/__STRINGS__|__STR__|_junk_|_CF_/.test(input)) {
        issues.push({ type: 'warning', message: 'Code appears to be obfuscated' });
    }

    let report = '<div style="font-family: monospace;">';
    report += '<h4 style="color: var(--accent); margin-bottom: 12px;">📊 Code Statistics</h4>';
    report += '<div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; margin-bottom: 16px; background: var(--bg-surface); padding: 12px; border-radius: 8px;">';
    report += `<p><strong>Lines:</strong> ${stats.lines}</p>`;
    report += `<p><strong>Functions:</strong> ${stats.functions}</p>`;
    report += `<p><strong>Locals:</strong> ${stats.locals}</p>`;
    report += `<p><strong>Loops:</strong> ${stats.loops}</p>`;
    report += `<p><strong>Comments:</strong> ${stats.comments}</p>`;
    report += `<p><strong>Code Density:</strong> ${((stats.lines - stats.comments) / stats.lines * 100).toFixed(1)}%</p>`;
    report += '</div>';

    if (issues.length > 0) {
        report += '<h4 style="color: var(--warning); margin-top: 16px; margin-bottom: 12px;">⚠️ Issues Found</h4>';
        issues.forEach(issue => {
            const colors = {deprecated: '#ff9800', performance: '#f44336', warning: '#ff9800', security: '#d32f2f'};
            const icons = {deprecated: 'exclamation-triangle', performance: 'tachometer-alt', warning: 'exclamation-circle', security: 'shield-alt'};
            report += `<div style="background: var(--bg-surface); padding: 10px; margin: 8px 0; border-left: 3px solid ${colors[issue.type]}; border-radius: 4px;">`;
            report += `<p style="color: ${colors[issue.type]}; margin: 0;"><i class="fas fa-${icons[issue.type]}"></i> <strong>${issue.type.toUpperCase()}:</strong> ${issue.message}</p>`;
            report += `</div>`;
        });
    } else {
        report += '<div style="background: var(--bg-surface); padding: 16px; border-radius: 8px; margin-top: 16px;">';
        report += '<p style="color: var(--success); margin: 0;"><i class="fas fa-check-circle"></i> <strong>No issues found!</strong> Code looks good.</p>';
        report += '</div>';
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
        showToast('Error: ' + e.message, 'error');
    }
}

function generateUUID() {
    const uuid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
        const r = Math.random() * 16 | 0;
        return (c === 'x' ? r : (r & 0x3 | 0x8)).toString(16);
    });
    document.getElementById('uuidOutput').value = uuid;
    showToast('UUID generated!', 'success');
}

function generateRBXGUID() {
    const guid = '{XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX}'.replace(/X/g, () =>
        Math.floor(Math.random() * 16).toString(16).toUpperCase()
    );
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
        const matches = Array.from(testString.matchAll(new RegExp(pattern, flags + (flags.includes('g') ? '' : 'g'))));
        let result = '<div style="font-family: monospace;">';
        if (matches.length > 0) {
            result += `<p style="color: var(--success); margin-bottom: 12px;"><i class="fas fa-check-circle"></i> <strong>${matches.length} match(es)</strong></p>`;
            matches.forEach((match, i) => {
                result += `<div style="background: var(--bg-surface); padding: 8px; margin: 6px 0; border-radius: 4px;">`;
                result += `<p style="margin: 4px 0;"><strong>Match ${i + 1}:</strong> <code style="background: var(--bg-secondary); padding: 2px 8px; border-radius: 4px;">${match[0]}</code></p>`;
                if (match.length > 1) {
                    for (let j = 1; j < match.length; j++) {
                        result += `<p style="margin: 4px 0 4px 20px; color: var(--text-secondary);">Group ${j}: <code style="background: var(--bg-secondary); padding: 2px 8px; border-radius: 4px;">${match[j] || ''}</code></p>`;
                    }
                }
                result += `</div>`;
            });
        } else {
            result += '<p style="color: var(--warning);"><i class="fas fa-info-circle"></i> No matches found</p>';
        }
        result += '</div>';
        output.innerHTML = result;
        showToast('Regex tested!', 'success');
    } catch (e) {
        output.innerHTML = `<p style="color: var(--danger);"><i class="fas fa-exclamation-triangle"></i> <strong>Error:</strong> ${e.message}</p>`;
        showToast('Invalid regex', 'error');
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
        reader.onerror = () => showToast('Error reading file', 'error');
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
        reader.onerror = () => showToast('Error reading file', 'error');
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
