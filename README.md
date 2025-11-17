# Roblox DataStore Manager

An advanced, feature-rich desktop application for managing Roblox DataStores using the Open Cloud API. Built with Python and a modern web-based UI.

## Features

### Core Functionality
- **Browse DataStores** - List and explore all datastores in your experience
- **View & Edit Entries** - Read, create, update, and delete datastore entries
- **JSON Editor** - Syntax-highlighted editor with tree view visualization
- **Version History** - View and restore previous versions of entries
- **Metadata Management** - Set user IDs and custom attributes

### Advanced Features
- **Bulk Operations**
  - Export entire datastores to JSON
  - Import data from JSON files
  - Bulk delete multiple keys
  - Automatic pagination for large datasets

- **Backup System**
  - Local backup history tracking
  - Export with full metadata
  - Timestamped backup files

- **Rate Limit Management**
  - Real-time rate limit monitoring
  - Automatic request throttling
  - 300 requests/minute per universe

- **Operation History**
  - Complete audit log of all operations
  - Success/failure tracking
  - Detailed error logging

- **API Request Logging**
  - HTTP request/response tracking
  - Response time monitoring
  - Debugging information

### UI Features
- Modern dark theme interface
- Real-time connection status
- Toast notifications
- Responsive design
- Bookmarking system (coming soon)

## Quick Start

### Method 1: Automated Installation (Recommended)

1. **Download** or clone this repository
2. **Double-click** `install.bat`
   - Automatically installs Python if needed
   - Creates virtual environment
   - Installs all dependencies
3. **Double-click** `start.bat` to launch the application
4. **Open** http://127.0.0.1:5000 in your browser

### Method 2: Manual Installation

```bash
# Clone the repository
git clone <repository-url>
cd roblox-datastore-manager

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

### Method 3: Standalone Executable

1. Run `install.bat` first
2. Double-click `build_exe.bat`
3. Find `RobloxDataStoreManager.exe` in the `dist` folder
4. Run the executable directly - no Python required!

## Configuration

### Getting Your API Key

1. Go to [Roblox Creator Dashboard](https://create.roblox.com/credentials)
2. Click "Create API Key"
3. Name your key (e.g., "DataStore Manager")
4. Select "DataStores" permission
5. Add your experience/universe
6. Set IP restrictions (use `0.0.0.0/0` for any IP, or restrict to your IP)
7. Copy the generated API key

### Finding Your Universe ID

1. Go to [Roblox Create](https://create.roblox.com)
2. Select your experience
3. Go to Settings > Basic Info
4. Copy the "Universe ID" (not Place ID!)

### Configuring the Application

1. Launch the application
2. Go to **Settings** tab
3. Enter your API Key
4. Enter your Universe ID
5. Click "Save Configuration"
6. Click "Test Connection" to verify

## Usage Guide

### Dashboard
- View operation statistics
- Monitor rate limits
- Quick access to common actions
- Recent operation history

### DataStores Tab
- Click "Load DataStores" to fetch all datastores
- Use search to filter datastores
- Click "Explore" to browse entries
- Click "Export" for quick backup

### Explorer Tab
- Enter datastore name and scope
- Load entries with optional prefix filter
- View/edit entry values in JSON editor
- Switch between JSON, Tree View, and Metadata tabs
- Create new entries
- Delete single or multiple entries
- View version history

### Bulk Operations
- **Export**: Save entire datastore to JSON file
- **Import**: Load data from JSON array
- **Bulk Delete**: Delete multiple keys at once

### Backups Tab
- View backup history
- Track export timestamps
- See entry counts

### History Tab
- Full operation audit log
- Filter by operation type
- Track success/failure rates

## API Endpoints (Internal)

The application provides a REST API at `http://127.0.0.1:5000`:

```
GET  /api/config              - Get configuration
POST /api/config              - Update configuration
POST /api/test-connection     - Test API connection
GET  /api/datastores          - List datastores
GET  /api/datastores/all      - List all datastores (paginated)
GET  /api/entries             - List entries
GET  /api/entries/all         - List all entries (paginated)
GET  /api/entry               - Get entry value
POST /api/entry               - Set entry value
DELETE /api/entry             - Delete entry
POST /api/entry/increment     - Increment entry
GET  /api/versions            - List version history
GET  /api/version             - Get specific version
POST /api/bulk/delete         - Bulk delete entries
POST /api/export              - Export datastore
POST /api/import              - Import data
GET  /api/history             - Get operation history
GET  /api/bookmarks           - Get bookmarked keys
GET  /api/backups             - Get backup history
GET  /api/request-log         - Get API request log
GET  /api/stats               - Get dashboard statistics
```

## Rate Limits

Roblox Open Cloud API has the following rate limits:
- **300 requests per minute per universe**
- Automatic throttling is built into the application
- Rate limit status is displayed in the sidebar

## Security Best Practices

1. **Never share your API key**
2. **Use IP restrictions** when creating API keys
3. **Set minimal permissions** (only what you need)
4. **Regularly rotate API keys**
5. **Monitor the operation history** for suspicious activity

## Troubleshooting

### Connection Failed
- Verify API key is correct
- Check Universe ID is correct (not Place ID)
- Ensure API key has DataStore permissions
- Check IP restrictions on your API key

### Rate Limited
- Wait for the rate limit to reset (shown in UI)
- Reduce operation frequency
- Use bulk operations for efficiency

### No DataStores Found
- Ensure your game has DataStores created in-game first
- Check permissions on your API key
- Verify Universe ID

### Build Fails
- Ensure Python 3.8+ is installed
- Run `install.bat` first
- Check for antivirus interference

## Project Structure

```
roblox-datastore-manager/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── install.bat           # Automated installer
├── start.bat             # Application launcher
├── build_exe.bat         # Executable builder
├── README.md             # This file
├── .gitignore            # Git ignore rules
├── src/
│   ├── __init__.py
│   └── roblox_api.py     # Roblox API client
├── templates/
│   └── index.html        # Main UI template
├── static/
│   ├── css/
│   │   └── style.css     # UI styles
│   └── js/
│       └── app.js        # Frontend logic
├── data/                  # Local database
├── backups/              # Backup files
└── dist/                 # Built executables
```

## Contributing

Contributions are welcome! Please feel free to submit pull requests.

## License

MIT License - feel free to use this for any purpose.

## Acknowledgments

- Built using Roblox Open Cloud API v1
- Inspired by [OpenCloudTools](https://devforum.roblox.com/t/opencloudtools-open-source-datastoremessagingservice-tools/1818516)
- UI inspired by modern dashboard designs

## Disclaimer

This is an unofficial tool and is not affiliated with Roblox Corporation. Use at your own risk. Always backup your data before making changes.

---

Made with care for the Roblox developer community.
