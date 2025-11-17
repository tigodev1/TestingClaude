/**
 * Roblox DataStore Manager - Production App
 * Clean, polished version
 */

// ===== GLOBAL STATE =====
let currentDatastore = '';
let currentScope = 'global';
let currentKey = '';
let selectedEntries = new Set();
let isConnected = false;
let lastKnownRateLimit = 300;

// ===== INITIALIZATION =====
document.addEventListener('DOMContentLoaded', () => {
    console.log('DataStore Manager loaded');
    initNavigation();
    initTabs();
    loadLocalStats(); // Only load local stats, not API
    checkExistingConfig(); // Check if already configured

    // Start disconnected
    updateConnectionStatus(false);
});

// Check if config already exists on server
async function checkExistingConfig() {
    try {
        const response = await fetch('/api/config');
        const data = await response.json();

        if (data.is_configured && data.has_key) {
            // Populate the universe ID field (not API key for security)
            const universeInput = document.getElementById('universeIdInput');
            if (universeInput && data.universe_id) {
                universeInput.value = data.universe_id;
            }

            // Show that we have a saved key
            const apiKeyInput = document.getElementById('apiKeyInput');
            if (apiKeyInput && data.has_key) {
                apiKeyInput.placeholder = '••••••••••••••••••••• (saved - enter new key to change)';
            }

            // Config exists, try to restore connection
            showToast('Found saved configuration, reconnecting...', 'info');
            await testConnection();
        }
    } catch (error) {
        console.log('No existing config or error checking:', error);
    }
}

// ===== NAVIGATION =====
function initNavigation() {
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', function() {
            const page = this.dataset.page;
            if (page) {
                showPage(page);
            }
        });
    });
}

function showPage(pageName) {
    // Update active nav item
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
        if (item.dataset.page === pageName) {
            item.classList.add('active');
        }
    });

    // Show selected page, hide others
    document.querySelectorAll('.page').forEach(page => {
        page.classList.remove('active');
        page.style.display = 'none';
    });

    const targetPage = document.getElementById(`page-${pageName}`);
    if (targetPage) {
        targetPage.classList.add('active');
        targetPage.style.display = 'block';
    }

    // Load page-specific data
    switch(pageName) {
        case 'dashboard':
            loadDashboard();
            break;
        case 'analytics':
            if (typeof loadAnalyticsCharts === 'function') {
                loadAnalyticsCharts();
            }
            break;
        case 'history':
            loadFullHistory();
            break;
        case 'backups':
            loadBackups();
            break;
        case 'settings':
            loadRequestLog();
            break;
    }
}

// ===== TABS =====
function initTabs() {
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', function() {
            const tabName = this.dataset.tab;
            const parent = this.parentElement;

            // Update buttons
            parent.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            this.classList.add('active');

            // Update content
            const contentId = `tab-${tabName}`;
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
                content.style.display = 'none';
            });

            const targetContent = document.getElementById(contentId);
            if (targetContent) {
                targetContent.classList.add('active');
                targetContent.style.display = 'block';
            }
        });
    });
}

// ===== NOTIFICATIONS =====
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icons = {
        success: 'fa-check-circle',
        error: 'fa-times-circle',
        warning: 'fa-exclamation-triangle',
        info: 'fa-info-circle'
    };

    toast.innerHTML = `
        <i class="fas ${icons[type] || icons.info}"></i>
        <span>${escapeHtml(message)}</span>
    `;

    container.appendChild(toast);

    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// ===== MODALS =====
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.add('active');
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.classList.remove('active');
}

// ===== CONNECTION & CONFIG =====
function updateConnectionStatus(connected) {
    isConnected = connected;
    const statusEl = document.getElementById('connectionStatus');
    const welcomeBanner = document.getElementById('welcomeBanner');

    if (statusEl) {
        if (connected) {
            statusEl.className = 'status-indicator status-connected';
            statusEl.innerHTML = '<span class="status-dot"></span><span>Connected</span>';
        } else {
            statusEl.className = 'status-indicator status-disconnected';
            statusEl.innerHTML = '<span class="status-dot"></span><span>Not Connected</span>';
            // Reset rate limit display
            updateRateLimitDisplay(300);
        }
    }

    // Hide/show welcome banner
    if (welcomeBanner) {
        welcomeBanner.style.display = connected ? 'none' : 'block';
    }
}

function updateRateLimitDisplay(remaining) {
    lastKnownRateLimit = remaining;
    const percentage = (remaining / 300) * 100;

    const fillEl = document.getElementById('rateLimitFill');
    const textEl = document.getElementById('rateLimitText');

    if (fillEl) fillEl.style.width = `${percentage}%`;
    if (textEl) textEl.textContent = `${remaining}/300`;

    // Color code based on remaining
    if (fillEl) {
        if (remaining > 200) {
            fillEl.style.background = 'var(--success)';
        } else if (remaining > 100) {
            fillEl.style.background = 'var(--warning)';
        } else {
            fillEl.style.background = 'var(--danger)';
        }
    }
}

// Decrement rate limit locally (called after each API operation)
function decrementRateLimit() {
    if (lastKnownRateLimit > 0) {
        lastKnownRateLimit--;
        updateRateLimitDisplay(lastKnownRateLimit);
    }
    // Also fetch actual from server
    fetchActualRateLimit();
}

// Fetch actual rate limit from server
async function fetchActualRateLimit() {
    try {
        const response = await fetch('/api/rate-limit');
        const data = await response.json();
        if (data.remaining !== undefined) {
            updateRateLimitDisplay(data.remaining);
        }
    } catch (error) {
        console.log('Could not fetch rate limit:', error);
    }
}

async function saveConfig() {
    const apiKey = document.getElementById('apiKeyInput').value.trim();
    const universeId = document.getElementById('universeIdInput').value.trim();

    // Check if we have at least universe ID
    if (!universeId) {
        showToast('Please enter Universe ID', 'error');
        return;
    }

    if (!universeId.match(/^\d+$/)) {
        showToast('Universe ID must be a number', 'error');
        return;
    }

    // If no API key entered but we're already connected, just update universe ID
    if (!apiKey && isConnected) {
        showToast('Enter a new API key to change credentials', 'warning');
        return;
    }

    if (!apiKey) {
        showToast('Please enter API Key', 'error');
        return;
    }

    showToast('Saving configuration...', 'info');

    try {
        const response = await fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ api_key: apiKey, universe_id: universeId })
        });

        const data = await response.json();

        if (response.ok && data.status === 'success') {
            showToast('Configuration saved! Testing connection...', 'success');
            // Clear the API key field for security
            document.getElementById('apiKeyInput').value = '';
            document.getElementById('apiKeyInput').placeholder = '••••••••••••••••••••• (saved - enter new key to change)';
            // Wait a moment for server to process, then test
            await new Promise(resolve => setTimeout(resolve, 300));
            await testConnection();
        } else {
            showToast(`Failed: ${data.error || 'Unknown error'}`, 'error');
        }
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    }
}

async function testConnection() {
    showToast('Testing connection...', 'info');

    try {
        const response = await fetch('/api/test-connection', { method: 'POST' });
        const data = await response.json();

        if (data.status === 'success') {
            showToast('Connected to Roblox API!', 'success');
            updateConnectionStatus(true);
            updateRateLimitDisplay(299); // Account for test call
            loadLocalStats(); // Refresh stats

            // Show success banner
            const welcomeBanner = document.getElementById('welcomeBanner');
            if (welcomeBanner) {
                welcomeBanner.innerHTML = `
                    <h3><i class="fas fa-check-circle" style="color: var(--success);"></i> Connected!</h3>
                    <p>Your API is configured and working. Start exploring your datastores!</p>
                    <button class="btn btn-primary" onclick="showPage('datastores')">
                        <i class="fas fa-database"></i> Browse DataStores
                    </button>
                `;
            }
        } else {
            showToast(`Connection failed: ${data.message}`, 'error');
            updateConnectionStatus(false);
        }
    } catch (error) {
        showToast(`Connection error: ${error.message}`, 'error');
        updateConnectionStatus(false);
    }
}

// ===== DASHBOARD =====
function loadLocalStats() {
    // Load stats from local database only (no Roblox API calls)
    fetch('/api/stats')
        .then(res => res.json())
        .then(data => {
            const ops = document.getElementById('statOperations');
            const success = document.getElementById('statSuccess');
            const failed = document.getElementById('statFailed');
            const backups = document.getElementById('statBackups');

            if (ops) ops.textContent = data.total_operations || 0;
            if (success) success.textContent = data.successful_operations || 0;
            if (failed) failed.textContent = data.failed_operations || 0;
            if (backups) backups.textContent = data.total_backups || 0;
        })
        .catch(err => console.error('Stats error:', err));
}

async function loadDashboard() {
    loadLocalStats();
    await loadHistory();
}

// ===== DATASTORES =====
async function loadAllDatastores() {
    if (!isConnected) {
        showToast('Please configure your API key first', 'warning');
        showPage('settings');
        return;
    }

    showToast('Loading datastores...', 'info');

    try {
        const response = await fetch('/api/datastores/all');
        const data = await response.json();

        if (data.error) {
            showToast(`Error: ${data.error}`, 'error');
            return;
        }

        const tbody = document.getElementById('datastoreList');
        if (!tbody) return;

        if (!data.datastores || data.datastores.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="3" class="empty-state">
                        <i class="fas fa-database"></i>
                        <p>No datastores found</p>
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = data.datastores.map(ds => `
            <tr>
                <td><strong>${escapeHtml(ds.name)}</strong></td>
                <td>${ds.createdTime || 'N/A'}</td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="exploreDatastore('${escapeHtml(ds.name)}')">
                        <i class="fas fa-folder-open"></i> Explore
                    </button>
                    <button class="btn btn-sm btn-success" onclick="quickExport('${escapeHtml(ds.name)}')">
                        <i class="fas fa-download"></i> Export
                    </button>
                </td>
            </tr>
        `).join('');

        showToast(`Loaded ${data.count} datastores`, 'success');
        decrementRateLimit(); // API call made
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    }
}

function exploreDatastore(name) {
    document.getElementById('explorerDatastore').value = name;
    showPage('explorer');
    loadEntries();
}

async function quickExport(name) {
    document.getElementById('exportDatastore').value = name;
    await exportDatastore();
}

// ===== ENTRIES =====
async function loadEntries() {
    if (!isConnected) {
        showToast('Please configure your API key first', 'warning');
        return;
    }

    const datastoreName = document.getElementById('explorerDatastore').value.trim();
    const scope = document.getElementById('explorerScope').value.trim() || 'global';
    const prefix = document.getElementById('explorerPrefix').value.trim();

    if (!datastoreName) {
        showToast('Please enter a datastore name', 'error');
        return;
    }

    currentDatastore = datastoreName;
    currentScope = scope;

    showToast('Loading entries...', 'info');

    try {
        const params = new URLSearchParams({
            datastore: datastoreName,
            scope: scope,
            prefix: prefix
        });

        const response = await fetch(`/api/entries?${params}`);
        const data = await response.json();

        if (data.error) {
            showToast(`Error: ${data.error}`, 'error');
            return;
        }

        displayEntries(data.keys || []);
        showToast(`Loaded ${(data.keys || []).length} entries`, 'success');
        decrementRateLimit();
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    }
}

async function loadAllEntriesBtn() {
    if (!isConnected) {
        showToast('Please configure your API key first', 'warning');
        return;
    }

    const datastoreName = document.getElementById('explorerDatastore').value.trim();
    const scope = document.getElementById('explorerScope').value.trim() || 'global';
    const prefix = document.getElementById('explorerPrefix').value.trim();

    if (!datastoreName) {
        showToast('Please enter a datastore name', 'error');
        return;
    }

    currentDatastore = datastoreName;
    currentScope = scope;

    showToast('Loading all entries (may take a while)...', 'info');

    try {
        const params = new URLSearchParams({
            datastore: datastoreName,
            scope: scope,
            prefix: prefix
        });

        const response = await fetch(`/api/entries/all?${params}`);
        const data = await response.json();

        if (data.error) {
            showToast(`Error: ${data.error}`, 'error');
            return;
        }

        displayEntries(data.keys || []);
        showToast(`Loaded ${data.count} entries`, 'success');
        // Multiple API calls for pagination
        const apiCalls = Math.ceil(data.count / 100) || 1;
        for (let i = 0; i < apiCalls; i++) decrementRateLimit();
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    }
}

function displayEntries(entries) {
    selectedEntries.clear();

    const card = document.getElementById('entriesCard');
    const countEl = document.getElementById('entryCount');
    const tbody = document.getElementById('entriesList');

    if (card) card.style.display = 'block';
    if (countEl) countEl.textContent = entries.length;
    if (!tbody) return;

    if (entries.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="4" class="empty-state">
                    <i class="fas fa-inbox"></i>
                    <p>No entries found</p>
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = entries.map(entry => `
        <tr>
            <td><input type="checkbox" class="entry-checkbox" value="${escapeHtml(entry.key)}" onchange="toggleEntrySelection('${escapeHtml(entry.key)}')"></td>
            <td><code>${escapeHtml(entry.key)}</code></td>
            <td><span class="badge badge-info">${entry.scope || currentScope}</span></td>
            <td>
                <button class="btn btn-sm btn-primary" onclick="viewEntry('${escapeHtml(entry.key)}')">
                    <i class="fas fa-eye"></i> View
                </button>
                <button class="btn btn-sm btn-danger" onclick="deleteEntry('${escapeHtml(entry.key)}')">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

function toggleEntrySelection(key) {
    if (selectedEntries.has(key)) {
        selectedEntries.delete(key);
    } else {
        selectedEntries.add(key);
    }
}

function toggleSelectAll() {
    const selectAll = document.getElementById('selectAllEntries');
    if (!selectAll) return;

    const checked = selectAll.checked;
    document.querySelectorAll('.entry-checkbox').forEach(cb => {
        cb.checked = checked;
        if (checked) {
            selectedEntries.add(cb.value);
        } else {
            selectedEntries.delete(cb.value);
        }
    });
}

async function viewEntry(key) {
    currentKey = key;
    showToast('Loading entry...', 'info');

    try {
        const params = new URLSearchParams({
            datastore: currentDatastore,
            key: key,
            scope: currentScope
        });

        const response = await fetch(`/api/entry?${params}`);
        const data = await response.json();

        if (data.error) {
            showToast(`Error: ${data.error}`, 'error');
            return;
        }

        // Show details card
        const detailsCard = document.getElementById('entryDetailsCard');
        if (detailsCard) detailsCard.style.display = 'block';

        // Update key name
        const keyEl = document.getElementById('currentEntryKey');
        if (keyEl) keyEl.textContent = key;

        // Update editor
        const editor = document.getElementById('entryValueEditor');
        if (editor) editor.value = JSON.stringify(data.value, null, 2);

        // Update tree view
        const treeView = document.getElementById('treeView');
        if (treeView) treeView.innerHTML = jsonToTreeView(data.value);

        // Update metadata
        const versionEl = document.getElementById('entryVersion');
        const createdEl = document.getElementById('entryCreated');
        const updatedEl = document.getElementById('entryUpdated');
        const userIdsEl = document.getElementById('entryUserIds');
        const attrsEl = document.getElementById('entryAttributes');

        if (versionEl) versionEl.value = data.metadata.version || '';
        if (createdEl) createdEl.value = data.metadata.created_time || '';
        if (updatedEl) updatedEl.value = data.metadata.updated_time || '';
        if (userIdsEl) userIdsEl.value = JSON.stringify(data.metadata.user_ids || []);
        if (attrsEl) attrsEl.value = JSON.stringify(data.metadata.attributes || {}, null, 2);

        showToast('Entry loaded', 'success');
        decrementRateLimit();
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    }
}

async function saveEntry() {
    try {
        const valueStr = document.getElementById('entryValueEditor').value;
        const userIdsStr = document.getElementById('entryUserIds').value || '[]';
        const attrsStr = document.getElementById('entryAttributes').value || '{}';

        const value = JSON.parse(valueStr);
        const userIds = JSON.parse(userIdsStr);
        const attributes = JSON.parse(attrsStr);

        const params = new URLSearchParams({
            datastore: currentDatastore,
            key: currentKey,
            scope: currentScope
        });

        const response = await fetch(`/api/entry?${params}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ value, user_ids: userIds, attributes })
        });

        const data = await response.json();

        if (data.error) {
            showToast(`Error: ${data.error}`, 'error');
            return;
        }

        const versionEl = document.getElementById('entryVersion');
        const updatedEl = document.getElementById('entryUpdated');
        if (versionEl) versionEl.value = data.version || '';
        if (updatedEl) updatedEl.value = data.updated_time || '';

        showToast('Entry saved successfully!', 'success');
        decrementRateLimit();
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    }
}

async function deleteEntry(key) {
    if (!confirm(`Are you sure you want to delete "${key}"?`)) return;

    try {
        const params = new URLSearchParams({
            datastore: currentDatastore,
            key: key,
            scope: currentScope
        });

        const response = await fetch(`/api/entry?${params}`, { method: 'DELETE' });
        const data = await response.json();

        if (data.error) {
            showToast(`Error: ${data.error}`, 'error');
            return;
        }

        showToast(`Entry "${key}" deleted`, 'success');
        decrementRateLimit();
        loadEntries();
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    }
}

async function bulkDeleteSelected() {
    if (selectedEntries.size === 0) {
        showToast('No entries selected', 'warning');
        return;
    }

    if (!confirm(`Delete ${selectedEntries.size} entries?`)) return;

    try {
        const response = await fetch('/api/bulk/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                datastore: currentDatastore,
                keys: Array.from(selectedEntries),
                scope: currentScope
            })
        });

        const data = await response.json();

        if (data.error) {
            showToast(`Error: ${data.error}`, 'error');
            return;
        }

        showToast(`Deleted ${data.success_count} entries`, 'success');
        loadEntries();
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    }
}

// ===== CREATE/INCREMENT ENTRY =====
function createEntryModal() {
    openModal('createEntryModal');
}

async function createNewEntry() {
    const key = document.getElementById('newEntryKey').value.trim();
    const valueStr = document.getElementById('newEntryValue').value.trim();

    if (!key || !valueStr) {
        showToast('Please enter key and value', 'error');
        return;
    }

    try {
        const value = JSON.parse(valueStr);
        const params = new URLSearchParams({
            datastore: currentDatastore,
            key: key,
            scope: currentScope
        });

        const response = await fetch(`/api/entry?${params}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ value, exclusive_create: true })
        });

        const data = await response.json();

        if (data.error) {
            showToast(`Error: ${data.error}`, 'error');
            return;
        }

        showToast('Entry created!', 'success');
        closeModal('createEntryModal');
        loadEntries();
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    }
}

function incrementEntryModal() {
    openModal('incrementModal');
}

async function incrementEntry() {
    const incrementBy = parseFloat(document.getElementById('incrementValue').value);

    try {
        const params = new URLSearchParams({
            datastore: currentDatastore,
            key: currentKey,
            scope: currentScope
        });

        const response = await fetch(`/api/entry/increment?${params}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ increment_by: incrementBy })
        });

        const data = await response.json();

        if (data.error) {
            showToast(`Error: ${data.error}`, 'error');
            return;
        }

        showToast(`New value: ${data.value}`, 'success');
        closeModal('incrementModal');
        viewEntry(currentKey);
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    }
}

// ===== VERSIONS =====
async function viewVersions() {
    showToast('Loading versions...', 'info');

    try {
        const params = new URLSearchParams({
            datastore: currentDatastore,
            key: currentKey,
            scope: currentScope
        });

        const response = await fetch(`/api/versions?${params}`);
        const data = await response.json();

        if (data.error) {
            showToast(`Error: ${data.error}`, 'error');
            return;
        }

        const versions = data.versions || [];
        const listEl = document.getElementById('versionsList');

        if (!listEl) return;

        if (versions.length === 0) {
            listEl.innerHTML = '<p class="empty-state">No versions found</p>';
        } else {
            listEl.innerHTML = `
                <div class="table-container">
                    <table>
                        <thead>
                            <tr><th>Version</th><th>Created</th><th>Deleted</th><th>Action</th></tr>
                        </thead>
                        <tbody>
                            ${versions.map(v => `
                                <tr>
                                    <td><code>${v.version}</code></td>
                                    <td>${v.createdTime || ''}</td>
                                    <td>${v.deleted ? '<span class="badge badge-danger">Yes</span>' : '<span class="badge badge-success">No</span>'}</td>
                                    <td><button class="btn btn-sm btn-secondary" onclick="restoreVersion('${v.version}')"><i class="fas fa-undo"></i> Restore</button></td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            `;
        }

        openModal('versionModal');
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    }
}

async function restoreVersion(version) {
    try {
        const params = new URLSearchParams({
            datastore: currentDatastore,
            key: currentKey,
            version: version,
            scope: currentScope
        });

        const response = await fetch(`/api/version?${params}`);
        const data = await response.json();

        if (data.error) {
            showToast(`Error: ${data.error}`, 'error');
            return;
        }

        const editor = document.getElementById('entryValueEditor');
        if (editor) editor.value = JSON.stringify(data.value, null, 2);

        showToast('Version loaded. Click "Save" to restore.', 'info');
        closeModal('versionModal');
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    }
}

// ===== BULK OPERATIONS =====
async function exportDatastore() {
    const datastoreName = document.getElementById('exportDatastore').value.trim();
    const scope = document.getElementById('exportScope').value.trim() || 'global';
    const includeMetadata = document.getElementById('exportMetadata').checked;

    if (!datastoreName) {
        showToast('Please enter datastore name', 'error');
        return;
    }

    showToast('Exporting... (this may take a while)', 'info');

    try {
        const response = await fetch('/api/export', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                datastore: datastoreName,
                scope: scope,
                include_metadata: includeMetadata
            })
        });

        const data = await response.json();

        if (data.error) {
            showToast(`Error: ${data.error}`, 'error');
            return;
        }

        showToast(`Exported ${data.entry_count} entries!`, 'success');

        // Download file
        const blob = new Blob([JSON.stringify(data.data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${datastoreName}_export.json`;
        a.click();
        URL.revokeObjectURL(url);
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    }
}

async function importDatastore() {
    const datastoreName = document.getElementById('importDatastore').value.trim();
    const scope = document.getElementById('importScope').value.trim() || 'global';
    const dataStr = document.getElementById('importData').value.trim();
    const overwrite = document.getElementById('importOverwrite').checked;

    if (!datastoreName || !dataStr) {
        showToast('Please enter datastore and data', 'error');
        return;
    }

    try {
        const entries = JSON.parse(dataStr);
        showToast('Importing...', 'info');

        const response = await fetch('/api/import', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                datastore: datastoreName,
                entries: entries,
                scope: scope,
                overwrite: overwrite
            })
        });

        const data = await response.json();

        if (data.error) {
            showToast(`Error: ${data.error}`, 'error');
            return;
        }

        showToast(`Imported: ${data.success} ok, ${data.failed} failed, ${data.skipped} skipped`, 'success');
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    }
}

async function bulkDelete() {
    const datastoreName = document.getElementById('bulkDeleteDatastore').value.trim();
    const keysStr = document.getElementById('bulkDeleteKeys').value.trim();

    if (!datastoreName || !keysStr) {
        showToast('Please enter datastore and keys', 'error');
        return;
    }

    const keys = keysStr.split('\n').map(k => k.trim()).filter(k => k);

    if (!confirm(`Delete ${keys.length} keys?`)) return;

    showToast('Deleting...', 'info');

    try {
        const response = await fetch('/api/bulk/delete', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                datastore: datastoreName,
                keys: keys,
                scope: 'global'
            })
        });

        const data = await response.json();

        if (data.error) {
            showToast(`Error: ${data.error}`, 'error');
            return;
        }

        showToast(`Deleted ${data.success_count}/${keys.length} keys`, 'success');
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    }
}

// ===== HISTORY =====
async function loadHistory() {
    try {
        const response = await fetch('/api/history?limit=10');
        const data = await response.json();

        const tbody = document.getElementById('recentHistoryTable');
        if (!tbody) return;

        const history = data.history || [];

        if (history.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="empty-state">No operations yet</td></tr>';
            return;
        }

        tbody.innerHTML = history.map(h => `
            <tr>
                <td>${new Date(h.timestamp).toLocaleString()}</td>
                <td><span class="badge badge-info">${h.operation_type}</span></td>
                <td>${escapeHtml(h.datastore_name || '-')}</td>
                <td><code>${escapeHtml(h.key_name || '-')}</code></td>
                <td>${h.success ? '<span class="badge badge-success">OK</span>' : '<span class="badge badge-danger">FAIL</span>'}</td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Failed to load history:', error);
    }
}

async function loadFullHistory() {
    try {
        const response = await fetch('/api/history?limit=100');
        const data = await response.json();

        const tbody = document.getElementById('fullHistoryTable');
        if (!tbody) return;

        const history = data.history || [];

        if (history.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="empty-state">No operations yet</td></tr>';
            return;
        }

        tbody.innerHTML = history.map(h => `
            <tr>
                <td>${new Date(h.timestamp).toLocaleString()}</td>
                <td><span class="badge badge-info">${h.operation_type}</span></td>
                <td>${escapeHtml(h.datastore_name || '-')}</td>
                <td><code>${escapeHtml(h.key_name || '-')}</code></td>
                <td><small>${escapeHtml((h.error_message || '-').substring(0, 50))}</small></td>
                <td>${h.success ? '<span class="badge badge-success">OK</span>' : '<span class="badge badge-danger">FAIL</span>'}</td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Failed to load history:', error);
    }
}

// ===== BACKUPS =====
async function loadBackups() {
    try {
        const response = await fetch('/api/backups');
        const data = await response.json();

        const tbody = document.getElementById('backupsList');
        if (!tbody) return;

        const backups = data.backups || [];

        if (backups.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="empty-state">No backups yet</td></tr>';
            return;
        }

        tbody.innerHTML = backups.map(b => `
            <tr>
                <td>${new Date(b.timestamp).toLocaleString()}</td>
                <td>${escapeHtml(b.datastore_name)}</td>
                <td>${b.entry_count}</td>
                <td><code>${escapeHtml(b.backup_file)}</code></td>
            </tr>
        `).join('');
    } catch (error) {
        console.error('Failed to load backups:', error);
    }
}

// ===== REQUEST LOG =====
async function loadRequestLog() {
    try {
        const response = await fetch('/api/request-log');
        const data = await response.json();

        const tbody = document.getElementById('requestLogTable');
        if (!tbody) return;

        const logs = data.log || [];

        if (logs.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="empty-state">No requests logged</td></tr>';
            return;
        }

        tbody.innerHTML = logs.reverse().map(l => {
            const statusClass = l.status >= 200 && l.status < 300 ? 'badge-success' :
                               l.status >= 400 ? 'badge-danger' : 'badge-warning';
            return `
                <tr>
                    <td>${new Date(l.timestamp).toLocaleTimeString()}</td>
                    <td><span class="badge badge-info">${l.method}</span></td>
                    <td><small>${escapeHtml(l.url.replace('https://apis.roblox.com', ''))}</small></td>
                    <td><span class="badge ${statusClass}">${l.status}</span></td>
                    <td>${l.response_time_ms} ms</td>
                </tr>
            `;
        }).join('');
    } catch (error) {
        console.error('Failed to load request log:', error);
    }
}

// ===== UTILITIES =====
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
}

function jsonToTreeView(obj, indent = 0) {
    if (obj === null) return '<span class="tree-null">null</span>';
    if (typeof obj === 'string') return `<span class="tree-string">"${escapeHtml(obj)}"</span>`;
    if (typeof obj === 'number') return `<span class="tree-number">${obj}</span>`;
    if (typeof obj === 'boolean') return `<span class="tree-boolean">${obj}</span>`;

    if (Array.isArray(obj)) {
        if (obj.length === 0) return '[]';
        return '[<br>' + obj.map((item, i) =>
            `<div style="padding-left: ${indent + 20}px;"><span class="tree-key">[${i}]:</span> ${jsonToTreeView(item, indent + 20)}</div>`
        ).join('') + ']';
    }

    if (typeof obj === 'object') {
        const keys = Object.keys(obj);
        if (keys.length === 0) return '{}';
        return '{<br>' + keys.map(key =>
            `<div style="padding-left: ${indent + 20}px;"><span class="tree-key">"${escapeHtml(key)}":</span> ${jsonToTreeView(obj[key], indent + 20)}</div>`
        ).join('') + '}';
    }

    return String(obj);
}

function exportModal() {
    showPage('bulk');
    document.getElementById('exportDatastore').focus();
}

function importModal() {
    showPage('bulk');
    document.getElementById('importDatastore').focus();
}

// ===== ORDERED DATASTORE OPERATIONS =====
async function loadOrderedEntries() {
    if (!isConnected) {
        showToast('Please configure your API key first', 'warning');
        return;
    }

    const datastoreName = document.getElementById('orderedDatastore').value.trim();
    const scope = document.getElementById('orderedScope').value.trim() || 'global';
    const ascending = document.getElementById('orderedAscending').checked;
    const limit = parseInt(document.getElementById('orderedLimit').value) || 100;

    if (!datastoreName) {
        showToast('Please enter a datastore name', 'error');
        return;
    }

    showToast('Loading ordered entries (retrying on timeout)...', 'info');

    try {
        const params = new URLSearchParams({
            datastore: datastoreName,
            scope: scope,
            ascending: ascending,
            limit: limit
        });

        const response = await fetch(`/api/ordered/list?${params}`);
        const data = await response.json();

        if (data.error) {
            // Better error messages for common issues
            if (data.error.includes('NOT_FOUND') || data.error.includes('not found')) {
                showToast(`Ordered DataStore "${datastoreName}" not found. Create it first by adding an entry below, or check the name.`, 'warning');
            } else if (data.error.includes('timeout')) {
                showToast('Request timed out. Roblox API may be slow. Try again.', 'warning');
            } else {
                showToast(`Error: ${data.error}`, 'error');
            }
            return;
        }

        displayOrderedEntries(data.entries || []);
        showToast(`Loaded ${data.count} ordered entries`, 'success');
        decrementRateLimit();
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    }
}

function displayOrderedEntries(entries) {
    const card = document.getElementById('orderedEntriesCard');
    const countEl = document.getElementById('orderedEntryCount');
    const tbody = document.getElementById('orderedEntriesList');

    if (card) card.style.display = 'block';
    if (countEl) countEl.textContent = entries.length;
    if (!tbody) return;

    if (entries.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="4" class="empty-state">
                    <i class="fas fa-list-ol"></i>
                    <p>No ordered entries found</p>
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = entries.map((entry, index) => `
        <tr>
            <td><strong>#${index + 1}</strong></td>
            <td><code>${escapeHtml(entry.id || entry.key)}</code></td>
            <td><span class="badge badge-primary">${entry.value}</span></td>
            <td>
                <button class="btn btn-sm btn-warning" onclick="updateOrderedEntry('${escapeHtml(entry.id || entry.key)}', ${entry.value})">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="btn btn-sm btn-danger" onclick="deleteOrderedEntry('${escapeHtml(entry.id || entry.key)}')">
                    <i class="fas fa-trash"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

async function createOrderedEntry() {
    const datastoreName = document.getElementById('orderedDatastore').value.trim();
    const key = document.getElementById('newOrderedKey').value.trim();
    const value = parseInt(document.getElementById('newOrderedValue').value);

    if (!datastoreName || !key || isNaN(value)) {
        showToast('Please enter datastore, key, and numeric value', 'error');
        return;
    }

    try {
        const params = new URLSearchParams({
            datastore: datastoreName,
            key: key,
            scope: document.getElementById('orderedScope').value.trim() || 'global'
        });

        const response = await fetch(`/api/ordered/entry?${params}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ value: value })
        });

        const data = await response.json();

        if (data.error) {
            showToast(`Error: ${data.error}`, 'error');
            return;
        }

        showToast('Ordered entry created!', 'success');
        document.getElementById('newOrderedKey').value = '';
        document.getElementById('newOrderedValue').value = '';
        loadOrderedEntries();
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    }
}

async function updateOrderedEntry(key, currentValue) {
    const newValue = prompt(`Update value for "${key}":`, currentValue);
    if (newValue === null) return;

    const parsedValue = parseInt(newValue);
    if (isNaN(parsedValue)) {
        showToast('Value must be a number', 'error');
        return;
    }

    try {
        const datastoreName = document.getElementById('orderedDatastore').value.trim();
        const params = new URLSearchParams({
            datastore: datastoreName,
            key: key,
            scope: document.getElementById('orderedScope').value.trim() || 'global'
        });

        const response = await fetch(`/api/ordered/entry?${params}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ value: parsedValue })
        });

        const data = await response.json();

        if (data.error) {
            showToast(`Error: ${data.error}`, 'error');
            return;
        }

        showToast('Entry updated!', 'success');
        loadOrderedEntries();
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    }
}

async function deleteOrderedEntry(key) {
    if (!confirm(`Delete ordered entry "${key}"?`)) return;

    try {
        const datastoreName = document.getElementById('orderedDatastore').value.trim();
        const params = new URLSearchParams({
            datastore: datastoreName,
            key: key,
            scope: document.getElementById('orderedScope').value.trim() || 'global'
        });

        const response = await fetch(`/api/ordered/entry?${params}`, { method: 'DELETE' });
        const data = await response.json();

        if (data.error) {
            showToast(`Error: ${data.error}`, 'error');
            return;
        }

        showToast('Entry deleted!', 'success');
        loadOrderedEntries();
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    }
}

// ===== DELETE ALL KEYS =====
async function deleteAllKeys() {
    const datastoreName = document.getElementById('deleteAllDatastore').value.trim();

    if (!datastoreName) {
        showToast('Please enter a datastore name', 'error');
        return;
    }

    const confirmText = prompt(
        `⚠️ DANGER: This will delete ALL keys in "${datastoreName}"!\n\n` +
        `Type the datastore name to confirm:`
    );

    if (confirmText !== datastoreName) {
        showToast('Deletion cancelled - name did not match', 'info');
        return;
    }

    showToast('Deleting all keys... This may take a while.', 'warning');

    try {
        const response = await fetch('/api/bulk/delete-all', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                datastore: datastoreName,
                scope: 'global',
                confirm: true
            })
        });

        const data = await response.json();

        if (data.error) {
            showToast(`Error: ${data.error}`, 'error');
            return;
        }

        showToast(data.message, 'success');
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    }
}

// ===== OPEN CLOUD API FUNCTIONS =====

// Game Info
async function loadGameInfo() {
    if (!isConnected) {
        showToast('Please configure API first', 'warning');
        return;
    }

    showToast('Loading game info...', 'info');

    try {
        const response = await fetch('/api/universe/info');
        const data = await response.json();

        if (data.error) {
            showToast(`Error: ${data.error}`, 'error');
            return;
        }

        const display = document.getElementById('gameInfoDisplay');
        const likePct = data.upvotes + data.downvotes > 0
            ? Math.round((data.upvotes / (data.upvotes + data.downvotes)) * 100)
            : 0;

        display.innerHTML = `
            <div style="display: grid; grid-template-columns: auto 1fr; gap: 24px; align-items: start; text-align: left;">
                <img src="${data.thumbnail || ''}" alt="Game Icon" style="width: 150px; height: 150px; border-radius: 12px; background: var(--bg-card);" onerror="this.style.display='none'">
                <div>
                    <h2 style="margin: 0 0 8px 0; color: var(--text-primary);">${escapeHtml(data.name)}</h2>
                    <p style="color: var(--text-secondary); margin-bottom: 16px; font-size: 14px;">${escapeHtml(data.description || 'No description').substring(0, 200)}...</p>

                    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px;">
                        <div class="stat-card">
                            <div class="stat-value">${formatLargeNumber(data.visits)}</div>
                            <div class="stat-label">Visits</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${formatLargeNumber(data.playing)}</div>
                            <div class="stat-label">Playing</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${formatLargeNumber(data.favorites)}</div>
                            <div class="stat-label">Favorites</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${likePct}%</div>
                            <div class="stat-label">Like Ratio</div>
                        </div>
                    </div>

                    <div style="margin-top: 16px; display: flex; gap: 16px;">
                        <div style="color: var(--success);">
                            <i class="fas fa-thumbs-up"></i> ${formatLargeNumber(data.upvotes)} Likes
                        </div>
                        <div style="color: var(--danger);">
                            <i class="fas fa-thumbs-down"></i> ${formatLargeNumber(data.downvotes)} Dislikes
                        </div>
                    </div>
                </div>
            </div>
        `;

        showToast('Game info loaded!', 'success');
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    }
}

// User Lookup - Advanced
async function lookupUser() {
    const userInput = document.getElementById('userIdInput').value.trim();
    if (!userInput) {
        showToast('Please enter a User ID or Username', 'error');
        return;
    }

    const btn = document.getElementById('userLookupBtn');
    btn.classList.add('loading');
    showToast('Looking up user...', 'info');

    // Hide previous results
    document.getElementById('userInfoCard').style.display = 'none';
    document.getElementById('userGamesCard').style.display = 'none';
    document.getElementById('userGroupGamesCard').style.display = 'none';
    document.getElementById('userGroupsCard').style.display = 'none';

    try {
        let userId = userInput;

        // If not a number, resolve username to ID first
        if (!userInput.match(/^\d+$/)) {
            showToast('Resolving username...', 'info');
            const resolveResponse = await fetch(`/api/user/resolve?username=${encodeURIComponent(userInput)}`);
            const resolveData = await resolveResponse.json();

            if (resolveData.error) {
                showToast(`User not found: ${resolveData.error}`, 'error');
                btn.classList.remove('loading');
                return;
            }

            userId = resolveData.id;
            showToast(`Found user: ${resolveData.displayName} (ID: ${userId})`, 'success');
        }

        // Get user info
        const userResponse = await fetch(`/api/user/info?user_id=${userId}`);
        const userData = await userResponse.json();

        if (userData.error) {
            showToast(`Error: ${userData.error}`, 'error');
            btn.classList.remove('loading');
            return;
        }

        // Display user info card
        const userCard = document.getElementById('userInfoCard');
        const userDisplay = document.getElementById('userInfoDisplay');
        userCard.style.display = 'block';

        // Update profile link
        document.getElementById('userProfileLink').href = `https://www.roblox.com/users/${userData.id}/profile`;

        const accountAge = Math.floor((Date.now() - new Date(userData.created).getTime()) / (1000 * 60 * 60 * 24));
        const accountYears = (accountAge / 365).toFixed(1);

        userDisplay.innerHTML = `
            <div style="display: grid; grid-template-columns: auto 1fr; gap: 24px; padding: 20px;">
                <div style="text-align: center;">
                    <img src="${userData.thumbnail || ''}" alt="Avatar" style="width: 150px; height: 150px; border-radius: 12px; background: var(--bg-tertiary); box-shadow: 0 4px 12px rgba(0,0,0,0.3);" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%22150%22 height=%22150%22><rect fill=%22%23333%22 width=%22150%22 height=%22150%22/></svg>'">
                    ${userData.isBanned ? '<div style="margin-top: 8px;"><span class="badge badge-danger" style="font-size: 14px;"><i class="fas fa-ban"></i> BANNED</span></div>' : ''}
                </div>
                <div>
                    <div style="margin-bottom: 16px;">
                        <h2 style="margin: 0 0 4px 0; font-size: 28px; font-weight: 700;">${escapeHtml(userData.displayName)}</h2>
                        <p style="color: var(--text-secondary); margin: 0; font-size: 16px;">@${escapeHtml(userData.name)}</p>
                    </div>

                    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 16px;">
                        <div class="stat-card" style="padding: 12px; text-align: center;">
                            <div class="stat-value" style="font-size: 20px; color: var(--accent-primary);">${formatLargeNumber(userData.friends || 0)}</div>
                            <div class="stat-label" style="font-size: 11px;"><i class="fas fa-user-friends"></i> Friends</div>
                        </div>
                        <div class="stat-card" style="padding: 12px; text-align: center;">
                            <div class="stat-value" style="font-size: 20px; color: var(--success);">${formatLargeNumber(userData.followers || 0)}</div>
                            <div class="stat-label" style="font-size: 11px;"><i class="fas fa-heart"></i> Followers</div>
                        </div>
                        <div class="stat-card" style="padding: 12px; text-align: center;">
                            <div class="stat-value" style="font-size: 20px; color: var(--warning);">${accountYears}</div>
                            <div class="stat-label" style="font-size: 11px;"><i class="fas fa-clock"></i> Years</div>
                        </div>
                        <div class="stat-card" style="padding: 12px; text-align: center;">
                            <div class="stat-value" style="font-size: 14px; color: var(--info);">${userData.id}</div>
                            <div class="stat-label" style="font-size: 11px;"><i class="fas fa-id-badge"></i> User ID</div>
                        </div>
                    </div>

                    <div style="background: var(--bg-tertiary); padding: 12px; border-radius: 8px; margin-bottom: 12px;">
                        <p style="margin: 0; font-size: 14px; color: var(--text-secondary); line-height: 1.5;">
                            ${escapeHtml(userData.description || 'No description provided').substring(0, 300)}${(userData.description || '').length > 300 ? '...' : ''}
                        </p>
                    </div>

                    <p style="margin: 0; color: var(--text-secondary); font-size: 12px;">
                        <i class="fas fa-calendar"></i> Joined: ${new Date(userData.created).toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}
                        <span style="margin: 0 8px;">|</span>
                        <i class="fas fa-clock"></i> Account Age: ${accountAge} days
                    </p>
                </div>
            </div>
        `;

        // Get user's games
        showToast('Loading user games...', 'info');
        const gamesResponse = await fetch(`/api/user/games?user_id=${userId}`);
        const gamesData = await gamesResponse.json();

        const gamesCard = document.getElementById('userGamesCard');
        const gamesGrid = document.getElementById('userGamesGrid');
        const gamesCount = document.getElementById('userGamesCount');
        const noGames = document.getElementById('userNoGames');
        gamesCard.style.display = 'block';

        if (!gamesData.error && gamesData.games && gamesData.games.length > 0) {
            gamesCount.textContent = gamesData.games.length;
            noGames.style.display = 'none';
            gamesGrid.style.display = 'grid';

            gamesGrid.innerHTML = gamesData.games.map(game => {
                const likeRatio = game.upvotes + game.downvotes > 0
                    ? Math.round((game.upvotes / (game.upvotes + game.downvotes)) * 100)
                    : 0;

                return `
                    <div style="background: var(--bg-tertiary); border-radius: 12px; overflow: hidden; border: 1px solid var(--border); transition: transform 0.2s, box-shadow 0.2s;" onmouseover="this.style.transform='translateY(-4px)';this.style.boxShadow='0 8px 24px rgba(0,0,0,0.3)';" onmouseout="this.style.transform='';this.style.boxShadow='';">
                        <div style="position: relative;">
                            <img src="${game.thumbnail || ''}" alt="${escapeHtml(game.name)}" style="width: 100%; height: 180px; object-fit: cover; background: var(--bg-card);" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%22512%22 height=%22512%22><rect fill=%22%23222%22 width=%22512%22 height=%22512%22/><text x=%22256%22 y=%22256%22 text-anchor=%22middle%22 fill=%22%23666%22 font-size=%2248%22>No Image</text></svg>'">
                            <div style="position: absolute; top: 8px; right: 8px; background: rgba(0,0,0,0.7); padding: 4px 8px; border-radius: 6px; font-size: 11px;">
                                <span style="color: ${likeRatio >= 70 ? 'var(--success)' : likeRatio >= 50 ? 'var(--warning)' : 'var(--danger)'};">
                                    <i class="fas fa-thumbs-up"></i> ${likeRatio}%
                                </span>
                            </div>
                            ${game.playing > 0 ? `
                                <div style="position: absolute; bottom: 8px; left: 8px; background: var(--success); padding: 4px 8px; border-radius: 6px; font-size: 11px; color: white; font-weight: 600;">
                                    <i class="fas fa-circle" style="font-size: 8px;"></i> ${formatLargeNumber(game.playing)} Playing
                                </div>
                            ` : ''}
                        </div>
                        <div style="padding: 16px;">
                            <h4 style="margin: 0 0 12px 0; font-size: 16px; font-weight: 600; line-height: 1.3; color: var(--text-primary);">${escapeHtml(game.name)}</h4>
                            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 12px; font-size: 12px;">
                                <div style="color: var(--text-secondary);">
                                    <i class="fas fa-eye" style="color: var(--info);"></i> ${formatLargeNumber(game.visits)} visits
                                </div>
                                <div style="color: var(--text-secondary);">
                                    <i class="fas fa-star" style="color: var(--warning);"></i> ${formatLargeNumber(game.favorites)} favs
                                </div>
                                <div style="color: var(--text-secondary);">
                                    <i class="fas fa-thumbs-up" style="color: var(--success);"></i> ${formatLargeNumber(game.upvotes)}
                                </div>
                                <div style="color: var(--text-secondary);">
                                    <i class="fas fa-thumbs-down" style="color: var(--danger);"></i> ${formatLargeNumber(game.downvotes)}
                                </div>
                            </div>
                            <a href="https://www.roblox.com/games/${game.rootPlaceId || game.id}" target="_blank" style="display: block; background: linear-gradient(135deg, #00b06f, #00d47e); color: white; text-align: center; padding: 10px; border-radius: 8px; text-decoration: none; font-weight: 600; transition: opacity 0.2s;" onmouseover="this.style.opacity='0.9'" onmouseout="this.style.opacity='1'">
                                <i class="fas fa-play"></i> PLAY
                            </a>
                        </div>
                    </div>
                `;
            }).join('');
        } else {
            gamesCount.textContent = '0';
            gamesGrid.style.display = 'none';
            noGames.style.display = 'block';
        }

        // Get user's groups
        showToast('Loading user groups...', 'info');
        const groupsResponse = await fetch(`/api/user/groups?user_id=${userId}`);
        const groupsData = await groupsResponse.json();

        const groupsCard = document.getElementById('userGroupsCard');
        const groupsGrid = document.getElementById('userGroupsGrid');
        const groupsCount = document.getElementById('userGroupsCount');
        const noGroups = document.getElementById('userNoGroups');
        groupsCard.style.display = 'block';

        if (!groupsData.error && groupsData.groups && groupsData.groups.length > 0) {
            groupsCount.textContent = groupsData.groups.length;
            noGroups.style.display = 'none';
            groupsGrid.style.display = 'grid';

            groupsGrid.innerHTML = groupsData.groups.map(group => `
                <div style="background: var(--bg-tertiary); border-radius: 10px; padding: 16px; border: 1px solid var(--border); display: flex; gap: 12px; align-items: center; transition: background 0.2s;" onmouseover="this.style.background='var(--bg-card)'" onmouseout="this.style.background='var(--bg-tertiary)'">
                    <img src="${group.thumbnail || ''}" alt="${escapeHtml(group.name)}" style="width: 64px; height: 64px; border-radius: 8px; background: var(--bg-card);" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%2264%22 height=%2264%22><rect fill=%22%23333%22 width=%2264%22 height=%2264%22/></svg>'">
                    <div style="flex: 1; min-width: 0;">
                        <h5 style="margin: 0 0 4px 0; font-size: 14px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">${escapeHtml(group.name)}</h5>
                        <p style="margin: 0 0 4px 0; font-size: 12px; color: var(--text-secondary);">
                            <i class="fas fa-users"></i> ${formatLargeNumber(group.memberCount)} members
                        </p>
                        <div style="display: inline-block; background: ${getRoleColor(group.roleRank)}; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 500;">
                            ${escapeHtml(group.role)}
                        </div>
                    </div>
                    <a href="https://www.roblox.com/groups/${group.id}" target="_blank" style="color: var(--accent-primary); text-decoration: none;">
                        <i class="fas fa-external-link-alt"></i>
                    </a>
                </div>
            `).join('');

            // Get group games (games the user has access to through their groups)
            showToast('Loading group games...', 'info');
            const groupGamesResponse = await fetch(`/api/user/group-games?user_id=${userId}`);
            const groupGamesData = await groupGamesResponse.json();

            const groupGamesCard = document.getElementById('userGroupGamesCard');
            const groupGamesGrid = document.getElementById('userGroupGamesGrid');
            const groupGamesCount = document.getElementById('userGroupGamesCount');
            const noGroupGames = document.getElementById('userNoGroupGames');
            groupGamesCard.style.display = 'block';

            if (!groupGamesData.error && groupGamesData.games && groupGamesData.games.length > 0) {
                groupGamesCount.textContent = groupGamesData.games.length;
                noGroupGames.style.display = 'none';
                groupGamesGrid.style.display = 'grid';

                groupGamesGrid.innerHTML = groupGamesData.games.map(game => {
                    const likeRatio = game.upvotes + game.downvotes > 0
                        ? Math.round((game.upvotes / (game.upvotes + game.downvotes)) * 100)
                        : 0;

                    return `
                        <div style="background: var(--bg-tertiary); border-radius: 12px; overflow: hidden; border: 1px solid var(--border); transition: transform 0.2s, box-shadow 0.2s;" onmouseover="this.style.transform='translateY(-4px)';this.style.boxShadow='0 8px 24px rgba(0,0,0,0.3)';" onmouseout="this.style.transform='';this.style.boxShadow='';">
                            <div style="position: relative;">
                                <img src="${game.thumbnail || ''}" alt="${escapeHtml(game.name)}" style="width: 100%; height: 180px; object-fit: cover; background: var(--bg-card);" onerror="this.src='data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%22512%22 height=%22512%22><rect fill=%22%23222%22 width=%22512%22 height=%22512%22/><text x=%22256%22 y=%22256%22 text-anchor=%22middle%22 fill=%22%23666%22 font-size=%2248%22>No Image</text></svg>'">
                                <div style="position: absolute; top: 8px; left: 8px; background: rgba(124, 58, 237, 0.9); padding: 4px 8px; border-radius: 6px; font-size: 10px; color: white; font-weight: 600;">
                                    <i class="fas fa-building"></i> ${escapeHtml(game.groupName || 'Group')}
                                </div>
                                <div style="position: absolute; top: 8px; right: 8px; background: rgba(0,0,0,0.7); padding: 4px 8px; border-radius: 6px; font-size: 11px;">
                                    <span style="color: ${likeRatio >= 70 ? 'var(--success)' : likeRatio >= 50 ? 'var(--warning)' : 'var(--danger)'};">
                                        <i class="fas fa-thumbs-up"></i> ${likeRatio}%
                                    </span>
                                </div>
                                ${game.playing > 0 ? `
                                    <div style="position: absolute; bottom: 8px; left: 8px; background: var(--success); padding: 4px 8px; border-radius: 6px; font-size: 11px; color: white; font-weight: 600;">
                                        <i class="fas fa-circle" style="font-size: 8px;"></i> ${formatLargeNumber(game.playing)} Playing
                                    </div>
                                ` : ''}
                            </div>
                            <div style="padding: 16px;">
                                <h4 style="margin: 0 0 12px 0; font-size: 16px; font-weight: 600; line-height: 1.3; color: var(--text-primary);">${escapeHtml(game.name)}</h4>
                                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 12px; font-size: 12px;">
                                    <div style="color: var(--text-secondary);">
                                        <i class="fas fa-eye" style="color: var(--info);"></i> ${formatLargeNumber(game.visits)} visits
                                    </div>
                                    <div style="color: var(--text-secondary);">
                                        <i class="fas fa-star" style="color: var(--warning);"></i> ${formatLargeNumber(game.favorites)} favs
                                    </div>
                                    <div style="color: var(--text-secondary);">
                                        <i class="fas fa-thumbs-up" style="color: var(--success);"></i> ${formatLargeNumber(game.upvotes)}
                                    </div>
                                    <div style="color: var(--text-secondary);">
                                        <i class="fas fa-thumbs-down" style="color: var(--danger);"></i> ${formatLargeNumber(game.downvotes)}
                                    </div>
                                </div>
                                <a href="https://www.roblox.com/games/${game.rootPlaceId || game.id}" target="_blank" style="display: block; background: linear-gradient(135deg, #00b06f, #00d47e); color: white; text-align: center; padding: 10px; border-radius: 8px; text-decoration: none; font-weight: 600; transition: opacity 0.2s;" onmouseover="this.style.opacity='0.9'" onmouseout="this.style.opacity='1'">
                                    <i class="fas fa-play"></i> PLAY
                                </a>
                            </div>
                        </div>
                    `;
                }).join('');
            } else {
                groupGamesCount.textContent = '0';
                groupGamesGrid.style.display = 'none';
                noGroupGames.style.display = 'block';
            }
        } else {
            groupsCount.textContent = '0';
            groupsGrid.style.display = 'none';
            noGroups.style.display = 'block';
        }

        showToast('User lookup complete!', 'success');
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    } finally {
        btn.classList.remove('loading');
    }
}

// Helper function for role colors
function getRoleColor(rank) {
    if (rank >= 250) return 'var(--danger)'; // Owner-level
    if (rank >= 200) return 'var(--warning)'; // Admin-level
    if (rank >= 100) return 'var(--info)'; // Moderator-level
    if (rank > 1) return 'var(--success)'; // Member+
    return 'var(--text-secondary)'; // Guest/Member
}

// Helper function for large numbers
function formatLargeNumber(num) {
    if (!num) return '0';
    if (num >= 1000000000) return (num / 1000000000).toFixed(1) + 'B';
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
    return num.toString();
}
