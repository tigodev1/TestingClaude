// Luau Tools - Advanced Obfuscator, Deobfuscator, and Utilities

// ============= OBFUSCATOR =============

let obfuscationSettings = {
    renameVariables: true,
    encryptStrings: true,
    controlFlow: true,
    deadCode: true,
    encodeNumbers: true,
    antiTamper: true,
    intensity: 'heavy', // light, medium, heavy
    customKey: ''
};

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
    const chars = 'IlO0'; // Confusing characters
    const length = obfuscationSettings.intensity === 'heavy' ? 8 : obfuscationSettings.intensity === 'medium' ? 6 : 4;
    let name = prefix + '_';
    for (let i = 0; i < length; i++) {
        name += chars[Math.floor(Math.random() * chars.length)];
    }
    return name;
}

function encryptString(str, key) {
    // XOR encryption with base64
    const keyStr = key || obfuscationSettings.customKey || 'default_key';
    let encrypted = '';
    for (let i = 0; i < str.length; i++) {
        encrypted += String.fromCharCode(str.charCodeAt(i) ^ keyStr.charCodeAt(i % keyStr.length));
    }
    return btoa(encrypted);
}

function generateStringDecryptor(key) {
    const keyStr = key || obfuscationSettings.customKey || 'default_key';
    const keyEncoded = Array.from(keyStr).map(c => c.charCodeAt(0)).join(',');
    return `local function _D(s) local k={${keyEncoded}} local r="" local d=game:GetService("HttpService"):JSONDecode(game:GetService("HttpService"):GetAsync("https://raw.githubusercontent.com/base64/lua/master/base64.lua")) for i=1,#s do r=r..string.char(bit32.bxor(s:byte(i),k[(i-1)%#k+1])) end return r end`;
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

        // Step 1: Rename variables and functions
        if (obfuscationSettings.renameVariables) {
            // Find local variables
            const localPattern = /local\s+([a-zA-Z_][a-zA-Z0-9_]*)/g;
            let match;
            while ((match = localPattern.exec(input)) !== null) {
                if (!varMap.has(match[1])) {
                    varMap.set(match[1], generateRandomName());
                }
            }

            // Replace variables
            varMap.forEach((newName, oldName) => {
                const regex = new RegExp(`\\b${oldName}\\b`, 'g');
                obfuscated = obfuscated.replace(regex, newName);
            });
        }

        // Step 2: Encrypt strings
        if (obfuscationSettings.encryptStrings) {
            const stringPattern = /"([^"]*)"|'([^']*)'/g;
            const strings = [];
            obfuscated = obfuscated.replace(stringPattern, (match, dq, sq) => {
                const str = dq || sq;
                const encrypted = encryptString(str);
                strings.push(encrypted);
                return `_D("${encrypted}")`;
            });

            if (strings.length > 0) {
                const decryptor = `local function _D(e)local k='${obfuscationSettings.customKey||'k'}'local d=''local b='ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'e=e:gsub('[^'..b..'=]','')local a=''for c in e:gmatch'.'do a=a..(({[0]='000000',[1]='000001',[2]='000010',[3]='000011',[4]='000100',[5]='000101',[6]='000110',[7]='000111',[8]='001000',[9]='001001',A='001010',B='001011',C='001100',D='001101',E='001110',F='001111',G='010000',H='010001',I='010010',J='010011',K='010100',L='010101',M='010110',N='010111',O='011000',P='011001',Q='011010',R='011011',S='011100',T='011101',U='011110',V='011111',W='100000',X='100001',Y='100010',Z='100011',a='100100',b='100101',c='100110',d='100111',e='101000',f='101001',g='101010',h='101011',i='101100',j='101101',k='101110',l='101111',m='110000',n='110001',o='110010',p='110011',q='110100',r='110101',s='110110',t='110111',u='111000',v='111001',w='111010',x='111011',y='111100',z='111101',['+']='111110',['/']='111111'})[c]or'')end for i=1,#a,8 do local byte=tonumber(a:sub(i,i+7),2)if byte then d=d..string.char(bit32.bxor(byte,k:byte((i-1)/8%#k+1)))end end return d end\n`;
                obfuscated = decryptor + obfuscated;
            }
        }

        // Step 3: Encode numbers
        if (obfuscationSettings.encodeNumbers) {
            obfuscated = obfuscated.replace(/\b(\d+)\b/g, (match) => {
                const num = parseInt(match);
                if (num === 0) return '0';
                const encodings = [
                    `(${num}+0)`,
                    `(${Math.floor(num/2)}*2${num%2?'+1':''})`,
                    `(0x${num.toString(16)})`,
                    `tonumber("${num}")`
                ];
                return encodings[Math.floor(Math.random() * encodings.length)];
            });
        }

        // Step 4: Control flow obfuscation
        if (obfuscationSettings.controlFlow) {
            // Add random control flow
            const lines = obfuscated.split('\n');
            const controlFlowVar = generateRandomName('cf');
            obfuscated = `local ${controlFlowVar}=true\n` + lines.map((line, i) => {
                if (line.trim() && Math.random() > 0.7 && obfuscationSettings.intensity === 'heavy') {
                    return `if ${controlFlowVar} then ${line} end`;
                }
                return line;
            }).join('\n');
        }

        // Step 5: Inject dead code
        if (obfuscationSettings.deadCode) {
            const deadCodeSnippets = [
                `local ${generateRandomName('dc')}=function()return nil end`,
                `local ${generateRandomName('dc')}=math.random(1,100)`,
                `local ${generateRandomName('dc')}=tostring({})`
            ];
            const intensity = obfuscationSettings.intensity === 'heavy' ? 5 : obfuscationSettings.intensity === 'medium' ? 3 : 1;
            for (let i = 0; i < intensity; i++) {
                const snippet = deadCodeSnippets[Math.floor(Math.random() * deadCodeSnippets.length)];
                obfuscated = snippet + '\n' + obfuscated;
            }
        }

        // Step 6: Anti-tamper
        if (obfuscationSettings.antiTamper) {
            const antiTamper = `local ${generateRandomName('at')}=function()local s=debug.getinfo(1,'S').source if s~='@'..script:GetFullName()then while true do end end end\n`;
            obfuscated = antiTamper + obfuscated;
        }

        output.value = obfuscated;
        showToast('Code obfuscated successfully!', 'success');
    } catch (e) {
        showToast('Error obfuscating code: ' + e.message, 'error');
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

        // Remove common obfuscation patterns
        // 1. Decode simple number encodings
        deobfuscated = deobfuscated.replace(/\(0x([0-9a-fA-F]+)\)/g, (match, hex) => {
            return parseInt(hex, 16).toString();
        });

        deobfuscated = deobfuscated.replace(/tonumber\("(\d+)"\)/g, '$1');

        // 2. Simplify math expressions
        deobfuscated = deobfuscated.replace(/\((\d+)\+0\)/g, '$1');

        // 3. Remove unnecessary parentheses
        deobfuscated = deobfuscated.replace(/\((\d+)\)/g, '$1');

        // 4. Beautify code
        deobfuscated = beautifyLuau(deobfuscated);

        output.value = deobfuscated;
        showToast('Code deobfuscated! Note: Advanced encryption may require manual analysis', 'success');
    } catch (e) {
        showToast('Error deobfuscating code: ' + e.message, 'error');
    }
}

// ============= BEAUTIFIER =============

function beautifyLuau(code) {
    const lines = code.split('\n');
    let indent = 0;
    const indentSize = 4;
    let beautified = [];

    const increaseIndent = ['then', 'do', 'repeat', 'function'];
    const decreaseIndent = ['end', 'until', 'else', 'elseif'];
    const decreaseBeforeLine = ['else', 'elseif', 'until'];

    lines.forEach(line => {
        let trimmed = line.trim();
        if (!trimmed) {
            beautified.push('');
            return;
        }

        // Decrease indent before line for certain keywords
        if (decreaseBeforeLine.some(kw => trimmed.startsWith(kw))) {
            indent = Math.max(0, indent - 1);
        }

        // Add indented line
        beautified.push(' '.repeat(indent * indentSize) + trimmed);

        // Adjust indent for next line
        if (increaseIndent.some(kw => trimmed.includes(kw))) {
            indent++;
        }
        if (decreaseIndent.some(kw => trimmed.includes(kw))) {
            indent = Math.max(0, indent - 1);
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
        .replace(/\s+/g, ' ') // Multiple spaces to single
        .replace(/\s*([=+\-*/<>(){}[\],;])\s*/g, '$1') // Remove spaces around operators
        .trim();

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
        loops: (input.match(/\b(for|while|repeat)\b/g) || []).length
    };

    // Check for deprecated functions
    const deprecated = [
        { pattern: /wait\(\)/, msg: 'wait() without argument is deprecated, use task.wait()' },
        { pattern: /spawn\(/, msg: 'spawn() is deprecated, use task.spawn()' },
        { pattern: /delay\(/, msg: 'delay() is deprecated, use task.delay()' },
        { pattern: /LoadLibrary\(/, msg: 'LoadLibrary is deprecated' },
        { pattern: /\.RobloxLocked/, msg: 'RobloxLocked is deprecated' }
    ];

    deprecated.forEach(({ pattern, msg }) => {
        if (pattern.test(input)) {
            issues.push({ type: 'deprecated', message: msg });
        }
    });

    // Check for potential issues
    if (/while\s+true\s+do/.test(input) && !/wait\(|task\.wait\(/.test(input)) {
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

    // Generate report
    let report = '<div style="font-family: monospace;">';
    report += '<h4>Code Statistics:</h4>';
    report += `<p>Lines: ${stats.lines}</p>`;
    report += `<p>Functions: ${stats.functions}</p>`;
    report += `<p>Local Variables: ${stats.locals}</p>`;
    report += `<p>Loops: ${stats.loops}</p>`;

    if (issues.length > 0) {
        report += '<h4>Issues Found:</h4>';
        issues.forEach(issue => {
            const color = {
                deprecated: '#ff9800',
                performance: '#f44336',
                warning: '#ff9800',
                security: '#d32f2f'
            }[issue.type];
            report += `<p style="color: ${color};"><i class="fas fa-exclamation-triangle"></i> ${issue.message}</p>`;
        });
    } else {
        report += '<p style="color: var(--success);"><i class="fas fa-check-circle"></i> No issues found!</p>';
    }

    report += '</div>';
    output.innerHTML = report;
    showToast('Analysis complete!', 'success');
}

// ============= UTILITIES =============

function encodeBase64() {
    const input = document.getElementById('base64Input').value;
    const output = document.getElementById('base64Output');
    try {
        output.value = btoa(input);
        showToast('Encoded to Base64', 'success');
    } catch (e) {
        showToast('Error encoding: ' + e.message, 'error');
    }
}

function decodeBase64() {
    const input = document.getElementById('base64Input').value;
    const output = document.getElementById('base64Output');
    try {
        output.value = atob(input);
        showToast('Decoded from Base64', 'success');
    } catch (e) {
        showToast('Error decoding: ' + e.message, 'error');
    }
}

async function generateHash() {
    const input = document.getElementById('hashInput').value;
    const output = document.getElementById('hashOutput');
    const algorithm = document.getElementById('hashAlgorithm').value;

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

    try {
        const regex = new RegExp(pattern, flags);
        const matches = testString.match(regex);

        let result = '<div style="font-family: monospace;">';
        if (matches) {
            result += `<p style="color: var(--success);"><i class="fas fa-check-circle"></i> ${matches.length} match(es) found:</p>`;
            matches.forEach((match, i) => {
                result += `<p>Match ${i + 1}: <code style="background: var(--bg-secondary); padding: 2px 6px;">${match}</code></p>`;
            });
        } else {
            result += '<p style="color: var(--warning);">No matches found</p>';
        }
        result += '</div>';
        output.innerHTML = result;
    } catch (e) {
        output.innerHTML = `<p style="color: var(--danger);">Error: ${e.message}</p>`;
    }
}

// ============= FILE OPERATIONS =============

function uploadObfuscatorFile() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.lua,.luau,.txt';
    input.onchange = (e) => {
        const file = e.target.files[0];
        const reader = new FileReader();
        reader.onload = (event) => {
            document.getElementById('obfuscatorInput').value = event.target.result;
            showToast(`Loaded ${file.name}`, 'success');
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
        const reader = new FileReader();
        reader.onload = (event) => {
            document.getElementById('deobfuscatorInput').value = event.target.result;
            showToast(`Loaded ${file.name}`, 'success');
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
    output.select();
    document.execCommand('copy');
    showToast('Copied to clipboard!', 'success');
}

function copyDeobfuscatorOutput() {
    const output = document.getElementById('deobfuscatorOutput');
    output.select();
    document.execCommand('copy');
    showToast('Copied to clipboard!', 'success');
}
