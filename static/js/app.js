/**
 * Roblox DataStore Manager - Frontend Application
 * Advanced Open Cloud Management Tool
 */

// Global State
let currentDatastore = '';
let currentScope = 'global';
let currentKey = '';
let selectedEntries = new Set();
let allEntries = [];

// Initialize Application
document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initTabs();
    loadStats();
    loadHistory();

    // Auto-refresh rate limit status
    setInterval(updateRateLimitStatus, 5000);
});

// ===== NAVIGATION =====

function initNavigation() {
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', () => {
            const page = item.dataset.page;
            showPage(page);
        });
    });
}

function showPage(pageName) {
    // Update nav items
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.toggle('active', item.dataset.page === pageName);
    });

    // Update page visibility
    document.querySelectorAll('.page').forEach(page => {
        page.classList.toggle('active', page.id === `page-${pageName}`);
    });

    // Load page-specific data
    if (pageName === 'history') {
        loadFullHistory();
    } else if (pageName === 'backups') {
        loadBackups();
    } else if (pageName === 'settings') {
        loadRequestLog();
    }
}

// ===== TABS =====

function initTabs() {
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => {
            const tabName = tab.dataset.tab;

            // Update tab buttons
            tab.parentElement.querySelectorAll('.tab').forEach(t => {
                t.classList.toggle('active', t === tab);
            });

            // Update tab content
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.toggle('active', content.id === `tab-${tabName}`);
            });
        });
    });
}

// ===== TOAST NOTIFICATIONS =====

function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icons = {
        success: 'fa-check-circle',
        error: 'fa-times-circle',
        warning: 'fa-exclamation-triangle',
        info: 'fa-info-circle'
    };

    toast.innerHTML = `
        <i class="fas ${icons[type]}"></i>
        <span>${message}</span>
    `;

    container.appendChild(toast);

    // Auto remove after 4 seconds
    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// ===== MODALS =====

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}

function openModal(modalId) {
    document.getElementById(modalId).classList.add('active');
}

// ===== API CONFIGURATION =====

async function saveConfig() {
    const apiKey = document.getElementById('apiKeyInput').value;
    const universeId = document.getElementById('universeIdInput').value;

    if (!apiKey || !universeId) {
        showToast('Please enter both API Key and Universe ID', 'error');
        return;
    }

    try {
        const response = await fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ api_key: apiKey, universe_id: universeId })
        });

        if (response.ok) {
            showToast('Configuration saved successfully', 'success');
            updateConnectionStatus(true);
        } else {
            showToast('Failed to save configuration', 'error');
        }
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    }
}

async function testConnection() {
    try {
        const response = await fetch('/api/test-connection', { method: 'POST' });
        const data = await response.json();

        if (data.status === 'success') {
            showToast('Connection successful!', 'success');
            updateConnectionStatus(true);
            updateRateLimitDisplay(data.rate_limit);
        } else {
            showToast(`Connection failed: ${data.message}`, 'error');
            updateConnectionStatus(false);
        }
    } catch (error) {
        showToast(`Connection error: ${error.message}`, 'error');
        updateConnectionStatus(false);
    }
}

function updateConnectionStatus(connected) {
    const status = document.getElementById('connectionStatus');
    if (connected) {
        status.className = 'status-indicator status-connected';
        status.innerHTML = '<span class="status-dot"></span><span>Connected</span>';
    } else {
        status.className = 'status-indicator status-disconnected';
        status.innerHTML = '<span class="status-dot"></span><span>Not Connected</span>';
    }
}

async function updateRateLimitStatus() {
    try {
        const response = await fetch('/api/request-log');
        const data = await response.json();
        if (data.rate_limit) {
            updateRateLimitDisplay(data.rate_limit);
        }
    } catch (error) {
        // Silently fail
    }
}

function updateRateLimitDisplay(rateLimit) {
    const remaining = rateLimit.remaining || 300;
    const percentage = (remaining / 300) * 100;

    document.getElementById('rateLimitFill').style.width = `${percentage}%`;
    document.getElementById('rateLimitText').textContent = `${remaining}/300`;
}

// ===== DASHBOARD =====

async function loadStats() {
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();

        document.getElementById('statOperations').textContent = data.total_operations || 0;
        document.getElementById('statSuccess').textContent = data.successful_operations || 0;
        document.getElementById('statFailed').textContent = data.failed_operations || 0;
        document.getElementById('statBackups').textContent = data.total_backups || 0;

        if (data.rate_limit) {
            updateRateLimitDisplay(data.rate_limit);
        }
    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

// ===== DATASTORES =====

async function loadAllDatastores() {
    showToast('Loading datastores...', 'info');

    try {
        const response = await fetch('/api/datastores/all');
        const data = await response.json();

        if (data.error) {
            showToast(`Error: ${data.error}`, 'error');
            return;
        }

        const tbody = document.getElementById('datastoreList');
        if (data.datastores.length === 0) {
            tbody.innerHTML = '<tr><td colspan="3" class="empty-state">No datastores found</td></tr>';
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
    const datastoreName = document.getElementById('explorerDatastore').value;
    const scope = document.getElementById('explorerScope').value || 'global';
    const prefix = document.getElementById('explorerPrefix').value;

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
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    }
}

async function loadAllEntriesBtn() {
    const datastoreName = document.getElementById('explorerDatastore').value;
    const scope = document.getElementById('explorerScope').value || 'global';
    const prefix = document.getElementById('explorerPrefix').value;

    if (!datastoreName) {
        showToast('Please enter a datastore name', 'error');
        return;
    }

    currentDatastore = datastoreName;
    currentScope = scope;
    showToast('Loading all entries (this may take a while)...', 'info');

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
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    }
}

function displayEntries(entries) {
    allEntries = entries;
    selectedEntries.clear();

    document.getElementById('entriesCard').style.display = 'block';
    document.getElementById('entryCount').textContent = entries.length;

    const tbody = document.getElementById('entriesList');
    if (entries.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="empty-state">No entries found</td></tr>';
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
    const selectAll = document.getElementById('selectAllEntries').checked;
    document.querySelectorAll('.entry-checkbox').forEach(cb => {
        cb.checked = selectAll;
        if (selectAll) {
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

        // Display entry details
        document.getElementById('entryDetailsCard').style.display = 'block';
        document.getElementById('currentEntryKey').textContent = key;
        document.getElementById('entryValueEditor').value = JSON.stringify(data.value, null, 2);
        document.getElementById('treeView').innerHTML = jsonToTreeView(data.value);

        // Metadata
        document.getElementById('entryVersion').value = data.metadata.version || '';
        document.getElementById('entryCreated').value = data.metadata.created_time || '';
        document.getElementById('entryUpdated').value = data.metadata.updated_time || '';
        document.getElementById('entryUserIds').value = JSON.stringify(data.metadata.user_ids || []);
        document.getElementById('entryAttributes').value = JSON.stringify(data.metadata.attributes || {}, null, 2);

        showToast('Entry loaded', 'success');
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    }
}

async function saveEntry() {
    try {
        const value = JSON.parse(document.getElementById('entryValueEditor').value);
        const userIds = JSON.parse(document.getElementById('entryUserIds').value || '[]');
        const attributes = JSON.parse(document.getElementById('entryAttributes').value || '{}');

        const params = new URLSearchParams({
            datastore: currentDatastore,
            key: currentKey,
            scope: currentScope
        });

        const response = await fetch(`/api/entry?${params}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                value: value,
                user_ids: userIds,
                attributes: attributes
            })
        });

        const data = await response.json();

        if (data.error) {
            showToast(`Error: ${data.error}`, 'error');
            return;
        }

        showToast('Entry saved successfully', 'success');
        document.getElementById('entryVersion').value = data.version || '';
        document.getElementById('entryUpdated').value = data.updated_time || '';
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    }
}

async function deleteEntry(key) {
    if (!confirm(`Are you sure you want to delete "${key}"?`)) {
        return;
    }

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
        loadEntries(); // Reload entries
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    }
}

async function bulkDeleteSelected() {
    if (selectedEntries.size === 0) {
        showToast('No entries selected', 'warning');
        return;
    }

    if (!confirm(`Are you sure you want to delete ${selectedEntries.size} entries?`)) {
        return;
    }

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

// ===== CREATE ENTRY =====

function createEntryModal() {
    openModal('createEntryModal');
}

async function createNewEntry() {
    const key = document.getElementById('newEntryKey').value;
    const valueStr = document.getElementById('newEntryValue').value;

    if (!key || !valueStr) {
        showToast('Please enter both key and value', 'error');
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
            body: JSON.stringify({
                value: value,
                exclusive_create: true
            })
        });

        const data = await response.json();

        if (data.error) {
            showToast(`Error: ${data.error}`, 'error');
            return;
        }

        showToast('Entry created successfully', 'success');
        closeModal('createEntryModal');
        loadEntries();
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    }
}

// ===== INCREMENT =====

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

        showToast(`Entry incremented. New value: ${data.value}`, 'success');
        closeModal('incrementModal');
        viewEntry(currentKey); // Reload entry
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
        const versionsList = document.getElementById('versionsList');

        if (versions.length === 0) {
            versionsList.innerHTML = '<p class="empty-state">No versions found</p>';
        } else {
            versionsList.innerHTML = `
                <div class="table-container">
                    <table>
                        <thead>
                            <tr>
                                <th>Version</th>
                                <th>Created</th>
                                <th>Deleted</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${versions.map(v => `
                                <tr>
                                    <td><code>${v.version}</code></td>
                                    <td>${v.createdTime || ''}</td>
                                    <td>${v.deleted ? '<span class="badge badge-danger">Yes</span>' : '<span class="badge badge-success">No</span>'}</td>
                                    <td>
                                        <button class="btn btn-sm btn-secondary" onclick="restoreVersion('${v.version}')">
                                            <i class="fas fa-undo"></i> Restore
                                        </button>
                                    </td>
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

        // Update the editor with the old version
        document.getElementById('entryValueEditor').value = JSON.stringify(data.value, null, 2);
        showToast('Version loaded into editor. Click "Save Changes" to restore.', 'info');
        closeModal('versionModal');
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    }
}

// ===== BULK OPERATIONS =====

async function exportDatastore() {
    const datastoreName = document.getElementById('exportDatastore').value;
    const scope = document.getElementById('exportScope').value || 'global';
    const includeMetadata = document.getElementById('exportMetadata').checked;

    if (!datastoreName) {
        showToast('Please enter a datastore name', 'error');
        return;
    }

    showToast('Exporting datastore (this may take a while)...', 'info');

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

        showToast(`Exported ${data.entry_count} entries to ${data.filename}`, 'success');

        // Download the JSON
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
    const datastoreName = document.getElementById('importDatastore').value;
    const scope = document.getElementById('importScope').value || 'global';
    const dataStr = document.getElementById('importData').value;
    const overwrite = document.getElementById('importOverwrite').checked;

    if (!datastoreName || !dataStr) {
        showToast('Please enter datastore name and import data', 'error');
        return;
    }

    try {
        const entries = JSON.parse(dataStr);

        showToast('Importing data...', 'info');

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

        showToast(`Import complete: ${data.success} succeeded, ${data.failed} failed, ${data.skipped} skipped`, 'success');
    } catch (error) {
        showToast(`Error: ${error.message}`, 'error');
    }
}

async function bulkDelete() {
    const datastoreName = document.getElementById('bulkDeleteDatastore').value;
    const keysStr = document.getElementById('bulkDeleteKeys').value;

    if (!datastoreName || !keysStr) {
        showToast('Please enter datastore name and keys', 'error');
        return;
    }

    const keys = keysStr.split('\n').map(k => k.trim()).filter(k => k);

    if (!confirm(`Are you sure you want to delete ${keys.length} keys?`)) {
        return;
    }

    showToast('Deleting keys...', 'info');

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
                <td>${h.success ? '<span class="badge badge-success">Success</span>' : '<span class="badge badge-danger">Failed</span>'}</td>
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
                <td><small>${escapeHtml(h.details || '-').substring(0, 50)}</small></td>
                <td>${h.success ? '<span class="badge badge-success">Success</span>' : '<span class="badge badge-danger">Failed</span>'}</td>
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
    div.textContent = text;
    return div.innerHTML;
}

function jsonToTreeView(obj, indent = 0) {
    if (obj === null) {
        return '<span class="tree-null">null</span>';
    }

    if (typeof obj === 'string') {
        return `<span class="tree-string">"${escapeHtml(obj)}"</span>`;
    }

    if (typeof obj === 'number') {
        return `<span class="tree-number">${obj}</span>`;
    }

    if (typeof obj === 'boolean') {
        return `<span class="tree-boolean">${obj}</span>`;
    }

    if (Array.isArray(obj)) {
        if (obj.length === 0) return '[]';
        const items = obj.map((item, i) =>
            `<div class="tree-item" style="padding-left: ${indent + 20}px;">
                <span class="tree-key">[${i}]:</span> ${jsonToTreeView(item, indent + 20)}
            </div>`
        ).join('');
        return `[<br>${items}]`;
    }

    if (typeof obj === 'object') {
        const keys = Object.keys(obj);
        if (keys.length === 0) return '{}';
        const items = keys.map(key =>
            `<div class="tree-item" style="padding-left: ${indent + 20}px;">
                <span class="tree-key">"${escapeHtml(key)}":</span> ${jsonToTreeView(obj[key], indent + 20)}
            </div>`
        ).join('');
        return `{<br>${items}}`;
    }

    return String(obj);
}

// Export/Import Modal helpers
function exportModal() {
    showPage('bulk');
    document.getElementById('exportDatastore').focus();
}

function importModal() {
    showPage('bulk');
    document.getElementById('importDatastore').focus();
}
