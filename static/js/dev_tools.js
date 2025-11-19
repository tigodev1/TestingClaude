// Dev Tools - All Roblox Development Utilities

// ============= UUID GENERATOR =============
function generateUUIDs() {
    const format = document.getElementById('uuidFormat').value;
    const count = parseInt(document.getElementById('uuidCount').value);
    let uuids = [];

    for (let i = 0; i < count; i++) {
        if (format === 'v4') {
            uuids.push(generateUUID());
        } else if (format === 'custom') {
            uuids.push(generateCustomGUID());
        } else if (format === 'short') {
            uuids.push(generateShortID());
        }
    }

    document.getElementById('uuidOutput').value = uuids.join('\n');
}

function generateUUID() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
        const r = Math.random() * 16 | 0;
        const v = c === 'x' ? r : (r & 0x3 | 0x8);
        return v.toString(16);
    });
}

function generateCustomGUID() {
    return 'xxxxxxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'.replace(/[x]/g, () =>
        Math.floor(Math.random() * 16).toString(16)
    );
}

function generateShortID() {
    return Math.random().toString(36).substr(2, 9);
}

function copyAllUUIDs() {
    const text = document.getElementById('uuidOutput').value;
    navigator.clipboard.writeText(text);
    showToast('UUIDs copied to clipboard!', 'success');
}

// ============= COLOR PICKER =============
document.addEventListener('DOMContentLoaded', () => {
    const picker = document.getElementById('colorPicker');
    if (picker) {
        picker.addEventListener('input', updateColorValues);
        updateColorValues(); // Initialize
    }
});

function updateColorValues() {
    const hex = document.getElementById('colorPicker').value;
    const rgb = hexToRgb(hex);

    document.getElementById('color3Value').value = `Color3.new(${(rgb.r/255).toFixed(3)}, ${(rgb.g/255).toFixed(3)}, ${(rgb.b/255).toFixed(3)})`;
    document.getElementById('color3RGB').value = `Color3.fromRGB(${rgb.r}, ${rgb.g}, ${rgb.b})`;

    const hsv = rgbToHsv(rgb.r, rgb.g, rgb.b);
    document.getElementById('color3HSV').value = `Color3.fromHSV(${hsv.h.toFixed(3)}, ${hsv.s.toFixed(3)}, ${hsv.v.toFixed(3)})`;
    document.getElementById('colorHex').value = hex;
}

function hexToRgb(hex) {
    const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? {
        r: parseInt(result[1], 16),
        g: parseInt(result[2], 16),
        b: parseInt(result[3], 16)
    } : null;
}

function rgbToHsv(r, g, b) {
    r /= 255; g /= 255; b /= 255;
    const max = Math.max(r, g, b), min = Math.min(r, g, b);
    let h, s, v = max;
    const d = max - min;
    s = max === 0 ? 0 : d / max;
    if (max === min) {
        h = 0;
    } else {
        switch (max) {
            case r: h = (g - b) / d + (g < b ? 6 : 0); break;
            case g: h = (b - r) / d + 2; break;
            case b: h = (r - g) / d + 4; break;
        }
        h /= 6;
    }
    return { h, s, v };
}

function copyColor3() {
    const text = document.getElementById('color3Value').value;
    navigator.clipboard.writeText(text);
    showToast('Color3 value copied!', 'success');
}

// ============= VECTOR CALCULATOR =============
function calcVectorMagnitude() {
    const x = parseFloat(document.getElementById('vec3X').value);
    const y = parseFloat(document.getElementById('vec3Y').value);
    const z = parseFloat(document.getElementById('vec3Z').value);
    const magnitude = Math.sqrt(x*x + y*y + z*z);
    document.getElementById('vectorOutput').value = `Magnitude: ${magnitude.toFixed(3)}`;
}

function calcVectorUnit() {
    const x = parseFloat(document.getElementById('vec3X').value);
    const y = parseFloat(document.getElementById('vec3Y').value);
    const z = parseFloat(document.getElementById('vec3Z').value);
    const magnitude = Math.sqrt(x*x + y*y + z*z);
    if (magnitude === 0) {
        document.getElementById('vectorOutput').value = 'Error: Cannot create unit vector from zero vector';
        return;
    }
    const ux = x / magnitude;
    const uy = y / magnitude;
    const uz = z / magnitude;
    document.getElementById('vectorOutput').value = `Vector3.new(${ux.toFixed(3)}, ${uy.toFixed(3)}, ${uz.toFixed(3)})`;
}

function generateVector3Code() {
    const x = parseFloat(document.getElementById('vec3X').value);
    const y = parseFloat(document.getElementById('vec3Y').value);
    const z = parseFloat(document.getElementById('vec3Z').value);
    document.getElementById('vectorOutput').value = `Vector3.new(${x}, ${y}, ${z})`;
}

function generateCFrameCode() {
    const x = parseFloat(document.getElementById('cfX').value);
    const y = parseFloat(document.getElementById('cfY').value);
    const z = parseFloat(document.getElementById('cfZ').value);
    const rx = parseFloat(document.getElementById('cfRotX').value) * (Math.PI / 180);
    const ry = parseFloat(document.getElementById('cfRotY').value) * (Math.PI / 180);
    const rz = parseFloat(document.getElementById('cfRotZ').value) * (Math.PI / 180);

    let code = `CFrame.new(${x}, ${y}, ${z})`;
    if (rx !== 0 || ry !== 0 || rz !== 0) {
        code += ` * CFrame.Angles(${rx.toFixed(3)}, ${ry.toFixed(3)}, ${rz.toFixed(3)})`;
    }
    document.getElementById('cframeOutput').value = code;
}

// ============= BASE64 =============
function encodeBase64() {
    const input = document.getElementById('base64Input').value;
    const encoded = btoa(unescape(encodeURIComponent(input)));
    document.getElementById('base64Output').value = encoded;
}

function decodeBase64() {
    try {
        const input = document.getElementById('base64Input').value;
        const decoded = decodeURIComponent(escape(atob(input)));
        document.getElementById('base64Output').value = decoded;
    } catch (e) {
        document.getElementById('base64Output').value = 'Error: Invalid Base64 string';
    }
}

function clearBase64() {
    document.getElementById('base64Input').value = '';
    document.getElementById('base64Output').value = '';
}

function copyBase64Output() {
    const text = document.getElementById('base64Output').value;
    navigator.clipboard.writeText(text);
    showToast('Copied to clipboard!', 'success');
}

// ============= TIMESTAMP =============
function setCurrentTimestamp() {
    document.getElementById('unixInput').value = Math.floor(Date.now() / 1000);
}

function convertFromUnix() {
    const unix = parseInt(document.getElementById('unixInput').value);
    const date = new Date(unix * 1000);
    const formatted = date.toISOString().slice(0, 16);
    document.getElementById('datetimeInput').value = formatted;
}

function convertToUnix() {
    const datetime = document.getElementById('datetimeInput').value;
    const unix = Math.floor(new Date(datetime).getTime() / 1000);
    document.getElementById('unixInput').value = unix;
}

// ============= HASH GENERATOR =============
async function generateHash() {
    const input = document.getElementById('hashInput').value;
    const type = document.getElementById('hashType').value;

    const encoder = new TextEncoder();
    const data = encoder.encode(input);

    let algorithm = type === 'md5' ? 'MD5' : 'SHA-256';

    if (type === 'md5') {
        // Simple MD5 implementation (not cryptographically secure, for demo only)
        document.getElementById('hashOutput').value = 'MD5 not available in browser - use SHA-256 instead';
        return;
    }

    const hashBuffer = await crypto.subtle.digest(algorithm, data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');

    document.getElementById('hashOutput').value = hashHex;
}

function copyHash() {
    const text = document.getElementById('hashOutput').value;
    navigator.clipboard.writeText(text);
    showToast('Hash copied!', 'success');
}

// ============= REMOTEEVENT GENERATOR =============
function generateRemoteEvent() {
    const name = document.getElementById('remoteName').value || 'MyEvent';
    const location = document.getElementById('remoteLocation').value;
    const params = document.getElementById('remoteParams').value.split(',').map(p => p.trim()).filter(p => p);

    const serverCode = `-- Server Script
local ${name} = ${location}:WaitForChild("${name}")

${name}.OnServerEvent:Connect(function(player${params.length > 0 ? ', ' + params.join(', ') : ''})
    -- Your server logic here
    print(player.Name .. " fired ${name}")
${params.length > 0 ? params.map(p => `    print("${p}:", ${p})`).join('\n') : ''}
end)`;

    const clientCode = `-- Client Script
local ${name} = ${location}:WaitForChild("${name}")

-- Fire to server
${name}:FireServer(${params.join(', ')})`;

    document.getElementById('remoteServerCode').value = serverCode;
    document.getElementById('remoteClientCode').value = clientCode;
}

// ============= DATASTORE MODULE GENERATOR =============
function generateDataStoreModule() {
    const name = document.getElementById('dsModuleName').value || 'PlayerData';
    const defaultData = document.getElementById('dsDefaultData').value;

    const code = `-- DataStore Manager Module
local DataStoreService = game:GetService("DataStoreService")
local ${name}Store = DataStoreService:GetDataStore("${name}")

local DataManager = {}

local DEFAULT_DATA = ${defaultData}

function DataManager:LoadData(player)
    local success, data = pcall(function()
        return ${name}Store:GetAsync("Player_" .. player.UserId)
    end)

    if success then
        return data or DEFAULT_DATA
    else
        warn("Failed to load data for " .. player.Name)
        return DEFAULT_DATA
    end
end

function DataManager:SaveData(player, data)
    local success, err = pcall(function()
        ${name}Store:SetAsync("Player_" .. player.UserId, data)
    end)

    if success then
        print("Data saved for " .. player.Name)
    else
        warn("Failed to save data for " .. player.Name .. ": " .. tostring(err))
    end
end

function DataManager:UpdateData(player, updateFunction)
    local success, err = pcall(function()
        ${name}Store:UpdateAsync("Player_" .. player.UserId, updateFunction)
    end)

    if not success then
        warn("Failed to update data: " .. tostring(err))
    end
end

return DataManager`;

    document.getElementById('dsModuleOutput').value = code;
}

// ============= GUI BUILDER =============
function addGUIElement() {
    const container = document.getElementById('guiElements');
    const elem = document.createElement('div');
    elem.className = 'gui-element mb-2';
    elem.innerHTML = `<div class="grid-3 gap-2">
        <input type="text" class="form-input" placeholder="Element Name" value="Element${container.children.length}">
        <select class="form-input">
            <option value="Frame">Frame</option>
            <option value="TextLabel">TextLabel</option>
            <option value="TextButton">TextButton</option>
            <option value="ImageLabel">ImageLabel</option>
            <option value="ImageButton">ImageButton</option>
            <option value="TextBox">TextBox</option>
        </select>
        <button class="btn btn-sm btn-danger" onclick="removeGUIElement(this)">Remove</button>
    </div>`;
    container.appendChild(elem);
}

function removeGUIElement(btn) {
    btn.closest('.gui-element').remove();
}

function generateGUICode() {
    const name = document.getElementById('guiName').value || 'MyGUI';
    const type = document.getElementById('guiType').value;

    const elements = Array.from(document.querySelectorAll('.gui-element')).map(elem => {
        const inputs = elem.querySelectorAll('input, select');
        return {
            name: inputs[0].value,
            type: inputs[1].value
        };
    });

    let code = `-- GUI Script
local ${name} = Instance.new("${type}")
${name}.Name = "${name}"
${name}.Parent = game.Players.LocalPlayer:WaitForChild("PlayerGui")
${type === 'ScreenGui' ? `${name}.ResetOnSpawn = false` : ''}

`;

    elements.forEach(elem => {
        code += `local ${elem.name} = Instance.new("${elem.type}")
${elem.name}.Name = "${elem.name}"
${elem.name}.Parent = ${name}
-- Configure ${elem.name} properties here

`;
    });

    document.getElementById('guiOutput').value = code;
}

// ============= SERVICE GENERATOR =============
function addServiceMethod() {
    const container = document.getElementById('serviceMethods');
    const method = document.createElement('div');
    method.className = 'service-method mb-2';
    method.innerHTML = `<div class="grid-2 gap-2">
        <input type="text" class="form-input" placeholder="Method Name" value="Method${container.children.length}">
        <input type="text" class="form-input" placeholder="Parameters (comma-sep)" value="">
    </div>`;
    container.appendChild(method);
}

function generateServiceModule() {
    const name = document.getElementById('serviceName').value || 'MyService';
    const methods = Array.from(document.querySelectorAll('.service-method')).map(elem => {
        const inputs = elem.querySelectorAll('input');
        return {
            name: inputs[0].value,
            params: inputs[1].value.split(',').map(p => p.trim()).filter(p => p)
        };
    });

    const methodsCode = methods.map(m =>
        `function ${name}:${m.name}(${m.params.join(', ')})
    -- TODO: Implement ${m.name}
end`
    ).join('\n\n');

    const code = `-- ${name} Module
local ${name} = {}
${name}.__index = ${name}

function ${name}.new()
    local self = setmetatable({}, ${name})
    -- Initialize service
    return self
end

function ${name}:Init()
    -- Initialization logic
    print("${name} initialized")
end

${methodsCode}

return ${name}`;

    document.getElementById('serviceOutput').value = code;
}

// ============= TWEEN GENERATOR =============
function generateTweenCode() {
    const obj = document.getElementById('tweenObject').value || 'part';
    const duration = document.getElementById('tweenDuration').value;
    const easing = document.getElementById('tweenEasing').value;
    const direction = document.getElementById('tweenDirection').value;
    const properties = document.getElementById('tweenProperties').value;

    const code = `-- Tween Code
local TweenService = game:GetService("TweenService")

local tweenInfo = TweenInfo.new(
    ${duration}, -- Duration
    Enum.EasingStyle.${easing}, -- Easing Style
    Enum.EasingDirection.${direction}, -- Easing Direction
    0, -- Repeat Count
    false, -- Reverse
    0 -- Delay Time
)

local goal = ${properties}

local tween = TweenService:Create(${obj}, tweenInfo, goal)
tween:Play()`;

    document.getElementById('tweenOutput').value = code;
}

// ============= ID CONVERTER =============
function convertAssetId() {
    const id = document.getElementById('assetIdInput').value;
    const output = `rbxassetid://${id}\n\nDirect URL:\nhttps://assetdelivery.roblox.com/v1/asset/?id=${id}`;
    document.getElementById('idConverterOutput').value = output;
}

function lookupUniverseInfo() {
    const id = document.getElementById('universeIdInput').value;
    const output = `Universe ID: ${id}\n\nAPI Endpoint:\nhttps://games.roblox.com/v1/games?universeIds=${id}`;
    document.getElementById('idConverterOutput').value = output;
}

function generatePlaceUrl() {
    const id = document.getElementById('placeIdInput').value;
    const output = `Place ID: ${id}\n\nGame URL:\nhttps://www.roblox.com/games/${id}/\n\nDirect Join:\nroblox://placeId=${id}`;
    document.getElementById('idConverterOutput').value = output;
}

// ============= ASSET EXTRACTOR =============
function extractAssetIds() {
    const input = document.getElementById('assetExtractInput').value;
    const regex = /(?:rbxassetid:\/\/|assetid=|asset\/\?id=|assets\/)(\d+)/gi;
    const matches = [...input.matchAll(regex)];
    const ids = [...new Set(matches.map(m => m[1]))];

    if (ids.length === 0) {
        document.getElementById('extractedIds').value = 'No asset IDs found';
    } else {
        document.getElementById('extractedIds').value = `Found ${ids.length} unique asset ID(s):\n\n` + ids.join('\n');
    }
}

// ============= RBX ENCODER =============
function encodeURL() {
    const input = document.getElementById('rbxEncodeInput').value;
    document.getElementById('rbxEncodeOutput').value = encodeURIComponent(input);
}

function decodeURL() {
    const input = document.getElementById('rbxEncodeInput').value;
    try {
        document.getElementById('rbxEncodeOutput').value = decodeURIComponent(input);
    } catch (e) {
        document.getElementById('rbxEncodeOutput').value = 'Error: Invalid URL encoding';
    }
}

function encodeHTML() {
    const input = document.getElementById('rbxEncodeInput').value;
    const div = document.createElement('div');
    div.textContent = input;
    document.getElementById('rbxEncodeOutput').value = div.innerHTML;
}

function decodeHTML() {
    const input = document.getElementById('rbxEncodeInput').value;
    const div = document.createElement('div');
    div.innerHTML = input;
    document.getElementById('rbxEncodeOutput').value = div.textContent;
}

function escapeString() {
    const input = document.getElementById('rbxEncodeInput').value;
    document.getElementById('rbxEncodeOutput').value = JSON.stringify(input);
}

// ============= NAME GENERATOR =============
const variableNames = ['playerData', 'currentValue', 'totalAmount', 'isActive', 'hasPermission', 'maxLimit', 'itemCount', 'elapsedTime'];
const functionNames = ['initialize', 'updateValue', 'calculateTotal', 'checkStatus', 'processRequest', 'handleEvent', 'validateInput', 'formatOutput'];
const classNames = ['DataManager', 'PlayerController', 'InventorySystem', 'GameLogic', 'UIHandler', 'NetworkService', 'AudioManager', 'EffectsController'];
const playerNames = ['CoolGamer123', 'ProBuilder99', 'SpeedRunner42', 'MasterChef007', 'NinjaWarrior', 'DragonSlayer', 'PixelArtist', 'CodeWizard'];
const placeNames = ['Adventure Island', 'Battle Arena', 'Racing Track', 'Survival Zone', 'Building Simulator', 'Roleplay Town', 'Parkour Challenge', 'Tycoon Empire'];

function generateNames() {
    const type = document.getElementById('nameType').value;
    const count = parseInt(document.getElementById('nameCount').value);
    let names = [];

    let source;
    switch (type) {
        case 'variable': source = variableNames; break;
        case 'function': source = functionNames; break;
        case 'class': source = classNames; break;
        case 'player': source = playerNames; break;
        case 'place': source = placeNames; break;
    }

    for (let i = 0; i < count; i++) {
        names.push(source[Math.floor(Math.random() * source.length)] + (type !== 'place' && type !== 'player' ? Math.floor(Math.random() * 100) : ''));
    }

    document.getElementById('nameOutput').value = names.join('\n');
}

// ============= UTILITY FUNCTIONS =============
function copyCode(elementId) {
    const text = document.getElementById(elementId).value;
    navigator.clipboard.writeText(text);
    showToast('Code copied to clipboard!', 'success');
}
