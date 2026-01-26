# Stream Checker Web Service - Deployment & Integration Spec

## Overview

This document specifies the requirements and implementation plan for:
1. Packaging the `stream_checker` library for easy deployment
2. Deploying the API service on a Raspberry Pi
3. Building a polished web interface hosted on GitHub Pages
4. Connecting the GitHub Pages frontend to the Raspberry Pi API

## Architecture

```
GitHub Pages (Frontend)
    ↓ HTTP/HTTPS
    ↓ CORS-enabled API calls
Raspberry Pi (API Server)
    ↓ Uses
stream_checker Library
    ↓ Checks
Internet Audio Streams
```

**Key Considerations**:
- Frontend is static (HTML/CSS/JS) - no server-side code
- API runs on Raspberry Pi (local network or public IP)
- CORS must be configured to allow GitHub Pages origin
- API URL must be configurable in frontend
- HTTPS/HTTP mixed content considerations

---

## 1. Packaging & Deployment Strategy

### 1.1 Stream Checker Library Packaging

**Goal**: Make `stream_checker` easily installable on any machine without manual file copying.

**Options**:

#### Option A: Python Package (Recommended)
- Create `setup.py` or `pyproject.toml` in `stream_checker` project
- Package can be installed via:
  - `pip install -e .` (development)
  - `pip install .` (production)
  - `pip install git+https://github.com/user/stream_checker.git` (from repo)
  - `pip install stream_checker-1.0.0.tar.gz` (from wheel/sdist)

**Benefits**:
- Standard Python packaging
- Handles dependencies automatically
- Works with virtual environments
- Easy versioning

**Implementation**:
- Add `setup.py` or `pyproject.toml` to `stream_checker/`
- Define package metadata, dependencies, entry points
- Create distribution: `python setup.py sdist bdist_wheel`

#### Option B: Docker Container
- Package entire `stream_checker` + dependencies in Docker image
- Deploy as containerized service

**Benefits**:
- Consistent environment across machines
- Isolated dependencies
- Easy to scale

**Drawbacks**:
- Requires Docker on target machine
- More complex for simple deployments

#### Option C: Standalone Archive
- Create tar.gz/zip with all code + requirements.txt
- Manual installation instructions

**Benefits**:
- Simple, no build tools needed
- Works anywhere Python is installed

**Drawbacks**:
- Manual dependency installation
- Less standard

**Recommendation**: **Option A (Python Package)** - Most standard and maintainable.

---

### 1.2 Web Service Packaging

**Goal**: Separate deployment for:
- **Frontend**: Deploy to GitHub Pages (static files only)
- **API**: Deploy to Raspberry Pi (Python server)

**Structure**:
```
stream_checker-web/
├── api/                    # API server (for Raspberry Pi)
│   ├── app.py
│   └── __init__.py
├── frontend/               # Web interface (for GitHub Pages)
│   ├── index.html
│   ├── app.js
│   └── style.css
├── requirements.txt        # Python dependencies (for Raspberry Pi)
├── config.yaml            # Configuration (for Raspberry Pi)
├── setup.sh               # Installation script (for Raspberry Pi)
├── run.sh                 # Start script (for Raspberry Pi)
└── README.md              # Deployment instructions
```

**Deployment Methods**:

#### Frontend (GitHub Pages):
- Push `frontend/` directory to GitHub repository
- Enable GitHub Pages in repository settings
- Frontend accessible at `https://username.github.io/repo-name/`

#### API (Raspberry Pi):
- Method 1: Git clone + install
- Method 2: Archive distribution (tar.gz)
- Method 3: SCP/SFTP transfer

**Recommendation**: 
- **Frontend**: GitHub Pages (automatic deployment)
- **API**: Git clone or archive on Raspberry Pi

---

## 2. API Deployment Requirements (Raspberry Pi)

### 2.1 Prerequisites
- Raspberry Pi with Python 3.8+ installed
- Virtual environment support
- Network access (for stream checking)
- Public IP or port forwarding (for GitHub Pages to access)
- Optional: Dynamic DNS (if using dynamic IP)
- Optional: Systemd service (for auto-start)
- Optional: Reverse proxy (nginx) for HTTPS

### 2.2 Network Configuration

**Options for Raspberry Pi API Access**:

#### Option A: Public IP with Port Forwarding
- Raspberry Pi on local network
- Router port forwarding: External port → Pi:5000
- Access via: `http://your-public-ip:5000`

#### Option B: Dynamic DNS
- Use service like DuckDNS, No-IP, or similar
- Access via: `http://yourname.duckdns.org:5000`

#### Option C: VPN/Tunnel
- Use ngrok, localtunnel, or similar
- Access via: `https://random-id.ngrok.io`

#### Option D: Direct Public IP (if available)
- Raspberry Pi has public IP
- Access via: `http://your-ip:5000`

**Security Considerations**:
- Use HTTPS in production (reverse proxy with Let's Encrypt)
- Implement rate limiting (already in API)
- Consider API key authentication for production
- Firewall rules to restrict access if needed

### 2.2 Installation Script (`setup.sh`)

**Requirements**:
1. Create virtual environment
2. Install `stream_checker` package (from local or remote)
3. Install web service dependencies
4. Copy/configure `config.yaml`
5. Initialize database
6. Set permissions

**Script Structure**:
```bash
#!/bin/bash
# setup.sh - One-command setup for stream_checker-web

set -e  # Exit on error

echo "Setting up Stream Checker Web Service..."

# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install stream_checker
# Option A: From local path (if stream_checker is sibling directory)
if [ -d "../stream_checker" ]; then
    pip install -e ../stream_checker
else
    # Option B: From PyPI or git
    pip install stream-checker
fi

# 3. Install web dependencies
pip install -r requirements.txt

# 4. Configure
if [ ! -f "config.yaml" ]; then
    cp config.yaml.example config.yaml
    echo "Please edit config.yaml with your settings"
fi

# 5. Create database directory
mkdir -p data

echo "Setup complete! Run './run.sh' to start the server."
```

### 2.3 Run Script (`run.sh`)

**Requirements**:
1. Activate virtual environment
2. Start Flask server
3. Handle errors gracefully
4. Log output

**Script Structure**:
```bash
#!/bin/bash
# run.sh - Start the API server

cd "$(dirname "$0")"
source venv/bin/activate

# Set environment variables
export FLASK_APP=api/app.py
export FLASK_ENV=production  # or development

# Start server
echo "Starting Stream Checker API on http://0.0.0.0:5000"
python -m flask run --host=0.0.0.0 --port=5000
```

### 2.4 Systemd Service (Recommended for Raspberry Pi)

For production deployment with auto-start on Raspberry Pi:

**File**: `stream-checker-api.service`
```ini
[Unit]
Description=Stream Checker API Service
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/stream_checker-web
Environment="PATH=/home/pi/stream_checker-web/venv/bin"
ExecStart=/home/pi/stream_checker-web/venv/bin/python -m flask run --host=0.0.0.0 --port=5000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Installation**:
```bash
sudo cp stream-checker-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable stream-checker-api
sudo systemctl start stream-checker-api
```

### 2.5 Reverse Proxy with HTTPS (Optional but Recommended)

**Using nginx + Let's Encrypt**:

1. Install nginx:
```bash
sudo apt-get update
sudo apt-get install nginx
```

2. Configure nginx (`/etc/nginx/sites-available/stream-checker`):
```nginx
server {
    listen 80;
    server_name yourname.duckdns.org;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

3. Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/stream-checker /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

4. Install Let's Encrypt SSL:
```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d yourname.duckdns.org
```

---

## 3. Web Interface Requirements

### 3.1 User Experience Flow

1. **Input Screen**:
   - Clean, simple form
   - Stream URL input field
   - Phase selection (1-4, default: 4)
   - "Check Stream" button
   - Clear, prominent design

2. **Testing State**:
   - Show "Testing..." message immediately
   - Progress indicator (spinner/bar)
   - Disable form inputs
   - Show which phase is running (if possible)

3. **Results Display**:
   - Organized, visual layout
   - Health score prominently displayed (color-coded)
   - Sections for each phase:
     - Connectivity status
     - SSL certificate info
     - Stream parameters
     - Player test results
     - Audio analysis
     - Ad detection
   - Issues and recommendations
   - Expandable detailed JSON (for debugging)

### 3.2 Visual Design Requirements

**Color Scheme**:
- Health Score:
  - 80-100: Green (good)
  - 60-79: Orange (warning)
  - 0-59: Red (critical)
- Status indicators:
  - Success: Green checkmark
  - Warning: Orange triangle
  - Error: Red X
  - Processing: Blue spinner

**Layout**:
- Responsive design (mobile-friendly)
- Card-based sections
- Clear typography hierarchy
- Adequate spacing
- Professional appearance

**Components Needed**:
- Input form with validation
- Loading spinner/progress bar
- Status badges
- Result cards
- Collapsible sections
- JSON viewer (syntax highlighted)

### 3.3 Technical Requirements

**Frontend Stack**:
- Pure HTML/CSS/JavaScript (no build step required)
- OR: Simple build with vanilla JS + CSS
- Fetch API for HTTP requests
- Modern browser support (ES6+)

**Features**:
- Real-time status updates (polling or WebSocket)
- Error handling with user-friendly messages
- Form validation (URL format)
- Responsive layout
- Accessible (ARIA labels, keyboard navigation)

---

## 4. Frontend-API Integration

### 4.1 API Endpoints

#### POST `/api/streams/check`
**Request**:
```json
{
  "url": "https://example.com/stream.mp3",
  "phase": 4
}
```

**Response** (Synchronous - current implementation):
```json
{
  "test_run_id": "uuid",
  "stream_id": "hash",
  "status": "completed",
  "results": {
    "health_score": 85,
    "connectivity": {...},
    "ssl_certificate": {...},
    ...
  }
}
```

**Response** (Asynchronous - future enhancement):
```json
{
  "test_run_id": "uuid",
  "stream_id": "hash",
  "status": "processing",
  "message": "Stream check started"
}
```

#### GET `/api/jobs/{test_run_id}`
**Response**:
```json
{
  "test_run_id": "uuid",
  "status": "completed",
  "results": {...}
}
```

#### GET `/api/requests/stats`
**Response**:
```json
{
  "ip_address": "192.168.1.1",
  "requests_last_hour": 5,
  "rate_limit_per_hour": 600,
  "remaining_this_hour": 595
}
```

### 4.2 Frontend Implementation

**Critical**: API URL must be configurable since frontend is on GitHub Pages and API is on Raspberry Pi.

**JavaScript Flow**:

1. **API URL Configuration**:
   ```javascript
   // In app.js - configurable API endpoint
   const API_BASE_URL = window.API_BASE_URL || 'http://your-raspberry-pi-ip:5000/api';
   // Or use environment variable, config file, or URL parameter
   ```

2. **Form Submission**:
   ```javascript
   form.addEventListener('submit', async (e) => {
     e.preventDefault();
     const url = document.getElementById('streamUrl').value;
     const phase = parseInt(document.getElementById('phase').value);
     
     // Show loading state
     showLoadingState();
     
     try {
       const response = await fetch(`${API_BASE_URL}/streams/check`, {
         method: 'POST',
         headers: { 'Content-Type': 'application/json' },
         body: JSON.stringify({ url, phase })
       });
       
       const data = await response.json();
       
       if (response.ok) {
         displayResults(data);
       } else {
         showError(data.error);
       }
     } catch (error) {
       showError('Network error: ' + error.message);
     } finally {
       hideLoadingState();
     }
   });
   ```

**API URL Configuration Methods**:

**Method 1: Hardcoded (Simple)**:
```javascript
const API_BASE_URL = 'http://your-raspberry-pi-ip:5000/api';
```

**Method 2: URL Parameter**:
```javascript
// Use: https://username.github.io/repo/?api=http://pi-ip:5000
const urlParams = new URLSearchParams(window.location.search);
const API_BASE_URL = urlParams.get('api') || 'http://localhost:5000/api';
```

**Method 3: Config File**:
```javascript
// Load config.json from same directory
fetch('./config.json')
  .then(r => r.json())
  .then(config => {
    const API_BASE_URL = config.apiBaseUrl;
    // ... rest of code
  });
```

**Method 4: Environment Detection**:
```javascript
const API_BASE_URL = window.location.hostname === 'localhost' 
  ? 'http://localhost:5000/api'  // Local development
  : 'http://your-raspberry-pi-ip:5000/api';  // Production
```

**Recommendation**: Start with **Method 1** (hardcoded), add **Method 2** (URL parameter) for flexibility.

2. **Loading State**:
   - Disable form
   - Show spinner
   - Display "Testing stream..." message
   - Optionally show progress (if API supports it)

3. **Results Display**:
   - Parse response JSON
   - Render health score prominently
   - Display each phase's results in cards
   - Show issues/recommendations
   - Provide expandable JSON view

### 4.3 Error Handling

**Client-Side**:
- Network errors (connection failed)
- HTTP errors (400, 429, 500)
- Invalid URL format
- Timeout handling

**User-Friendly Messages**:
- "Unable to connect to server. Please check your connection."
- "Invalid stream URL. Please check the format."
- "Rate limit exceeded. Please try again in a few minutes."
- "Server error. Please try again later."

### 4.4 CORS Configuration (Critical for GitHub Pages)

**Problem**: GitHub Pages serves from `https://username.github.io` origin, but API is on Raspberry Pi. Browsers block cross-origin requests unless CORS is configured.

**Solution**: Configure Flask CORS to allow GitHub Pages origin.

**Current Code** (needs update):
```python
CORS(app)  # Allows all origins - OK for development, needs restriction for production
```

**Production Configuration**:
```python
# In api/app.py
CORS(app, resources={
    r"/api/*": {
        "origins": [
            "https://username.github.io",  # Your GitHub Pages URL
            "http://localhost:5000",        # Local development
            "http://127.0.0.1:5000"        # Local development
        ],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})
```

**Dynamic CORS** (if you have multiple GitHub Pages sites):
```python
# Allow any GitHub Pages subdomain
CORS(app, resources={
    r"/api/*": {
        "origins": [
            r"https://.*\.github\.io",  # Any GitHub Pages site
            "http://localhost:*",       # Local development
        ],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})
```

**Testing CORS**:
- Open browser console on GitHub Pages site
- Check for CORS errors when making API requests
- Verify `Access-Control-Allow-Origin` header in response

---

## 5. Implementation Plan

### Phase 1: Packaging (Priority: High)
- [ ] Create `setup.py` or `pyproject.toml` for `stream_checker`
- [ ] Test package installation
- [ ] Create `setup.sh` for Raspberry Pi API
- [ ] Create `run.sh` for Raspberry Pi API
- [ ] Test deployment on Raspberry Pi

### Phase 2: Frontend Enhancement (Priority: High)
- [ ] Improve UI/UX of existing `index.html`
- [ ] Add loading states and progress indicators
- [ ] Enhance results display with better formatting
- [ ] Add error handling and user feedback
- [ ] Make responsive for mobile devices
- [ ] **Add configurable API URL** (critical for GitHub Pages → Raspberry Pi)

### Phase 3: CORS Configuration (Priority: Critical)
- [ ] Update Flask CORS to allow GitHub Pages origin
- [ ] Test CORS from GitHub Pages
- [ ] Handle preflight OPTIONS requests
- [ ] Document CORS setup

### Phase 4: GitHub Pages Setup (Priority: High)
- [ ] Create GitHub repository
- [ ] Configure GitHub Pages (use `frontend/` directory or root)
- [ ] Test frontend deployment
- [ ] Update API URL in frontend code
- [ ] Test end-to-end: GitHub Pages → Raspberry Pi API

### Phase 5: Raspberry Pi Deployment (Priority: High)
- [ ] Deploy API to Raspberry Pi
- [ ] Configure network (port forwarding, dynamic DNS, etc.)
- [ ] Set up systemd service for auto-start
- [ ] Test API accessibility from internet
- [ ] Optional: Set up nginx reverse proxy with HTTPS

### Phase 6: API Integration Testing (Priority: Medium)
- [ ] Test frontend-API connection from GitHub Pages
- [ ] Handle CORS errors gracefully
- [ ] Add request timeout handling
- [ ] Implement rate limiting feedback
- [ ] Add request statistics display

### Phase 7: Documentation (Priority: Medium)
- [ ] Create step-by-step deployment guide
- [ ] Document GitHub Pages setup
- [ ] Document Raspberry Pi setup
- [ ] Document network configuration
- [ ] Create troubleshooting guide

### Phase 8: Optional Enhancements (Priority: Low)
- [ ] Asynchronous job processing (queue-based)
- [ ] WebSocket for real-time updates
- [ ] Job history page
- [ ] Export results (JSON/CSV)
- [ ] Authentication/authorization

---

## 6. Deployment Checklist

### Frontend (GitHub Pages):
- [ ] Create GitHub repository
- [ ] Push `frontend/` directory to repository
- [ ] Enable GitHub Pages in repository settings
  - Settings → Pages → Source: `main` branch, `/frontend` folder (or root)
- [ ] Verify frontend is accessible at `https://username.github.io/repo-name/`
- [ ] Update API URL in `app.js` to point to Raspberry Pi
- [ ] Test frontend loads correctly

### API (Raspberry Pi):
- [ ] Install Python 3.8+ on Raspberry Pi
- [ ] Clone/extract API code to Raspberry Pi
- [ ] Run `setup.sh` to install dependencies
- [ ] Configure `config.yaml` with appropriate settings
- [ ] Test API locally: `curl http://localhost:5000/api/health`
- [ ] Configure network access:
  - [ ] Set up port forwarding (if behind router)
  - [ ] OR configure dynamic DNS
  - [ ] OR set up ngrok/tunnel
- [ ] Update Flask CORS to allow GitHub Pages origin
- [ ] Test API from external network: `curl http://your-pi-ip:5000/api/health`
- [ ] Set up systemd service for auto-start (optional)
- [ ] Test end-to-end: GitHub Pages frontend → Raspberry Pi API

### End-to-End Testing:
- [ ] Open GitHub Pages frontend in browser
- [ ] Enter test stream URL
- [ ] Submit form
- [ ] Verify request reaches Raspberry Pi API
- [ ] Verify CORS headers are correct (check browser console)
- [ ] Verify results display correctly
- [ ] Test error handling (invalid URL, network error, etc.)

---

## 7. File Structure

### Repository Structure (for GitHub)

```
stream_checker-web/
├── api/                     # API code (for Raspberry Pi deployment)
│   ├── __init__.py
│   └── app.py
├── frontend/                # Frontend code (for GitHub Pages)
│   ├── index.html
│   ├── app.js
│   ├── style.css
│   └── config.json          # Optional: API URL configuration
├── docs/                    # Documentation
│   ├── DEPLOYMENT_SPEC.md
│   └── DEPLOYMENT_GUIDE.md
├── requirements.txt         # Python dependencies (for Raspberry Pi)
├── config.yaml.example      # Example configuration
├── setup.sh                # Installation script (for Raspberry Pi)
├── run.sh                  # Start script (for Raspberry Pi)
└── README.md               # Project documentation
```

### GitHub Pages Structure

GitHub Pages will serve from `frontend/` directory:
- `https://username.github.io/repo-name/index.html`
- Or configure to serve from root if preferred

### Raspberry Pi Structure

```
/home/pi/stream_checker-web/
├── api/
│   ├── __init__.py
│   └── app.py
├── data/                    # Database directory (created on setup)
├── venv/                    # Virtual environment (created on setup)
├── config.yaml              # Configuration file
├── requirements.txt
├── setup.sh
└── run.sh
```

---

## 8. Testing Strategy

### Unit Tests:
- API endpoint responses
- Error handling
- Configuration loading

### Integration Tests:
- Frontend form submission
- API request/response cycle
- Database operations
- Stream checking workflow

### Deployment Tests:
- Fresh machine setup
- Package installation
- Service startup
- End-to-end stream check

---

## 9. Security Considerations

### API Security:
- Rate limiting (already implemented)
- Input validation (already implemented)
- CORS configuration for production
- HTTPS in production (reverse proxy)
- Request logging (already implemented)

### Frontend Security:
- Input sanitization
- XSS prevention
- HTTPS for API calls
- No sensitive data in frontend code

---

## 10. Future Enhancements

### Short-term:
- Job queue for async processing
- Better progress reporting
- Result caching
- Request history page

### Long-term:
- User authentication
- Multi-user support
- Scheduled checks
- Email alerts
- Dashboard with analytics
- API key management

---

## Next Steps

1. **Review this spec** - Confirm requirements
2. **Start with Phase 1** - Package the library
3. **Enhance frontend** - Improve UI/UX
4. **Test deployment** - Try on target machine
5. **Iterate** - Refine based on feedback

---

## 8. GitHub Pages Specific Considerations

### 8.1 HTTPS Mixed Content

**Issue**: GitHub Pages serves over HTTPS, but Raspberry Pi API might be HTTP.

**Solutions**:
1. **Use HTTPS for API** (recommended):
   - Set up nginx reverse proxy with Let's Encrypt
   - Access API via `https://yourname.duckdns.org`

2. **Allow mixed content** (not recommended):
   - Add `<meta http-equiv="Content-Security-Policy" content="upgrade-insecure-requests">` to HTML
   - Browsers may still block

3. **Use HTTP for GitHub Pages** (not possible):
   - GitHub Pages only serves HTTPS

**Recommendation**: Use HTTPS for Raspberry Pi API.

### 8.2 API URL Configuration

Since GitHub Pages is static, API URL must be:
- Hardcoded in JavaScript, OR
- Configurable via URL parameter, OR
- Loaded from config file

**Best Practice**: Use URL parameter for flexibility:
```
https://username.github.io/repo/?api=https://your-pi.duckdns.org
```

### 8.3 CORS Preflight Requests

Browsers send OPTIONS request before POST (preflight). Flask must handle this:

```python
@app.route('/api/streams/check', methods=['OPTIONS'])
def handle_preflight():
    return '', 200
```

Or ensure CORS middleware handles it automatically.

### 8.4 GitHub Pages Branch/Directory

**Options**:
- Serve from `main` branch, `/frontend` folder
- Serve from `gh-pages` branch, root folder
- Serve from `main` branch, root folder (if frontend is in root)

**Recommendation**: Use `main` branch, `/frontend` folder for cleaner separation.

---

## 9. Raspberry Pi Specific Considerations

### 9.1 Performance

- Raspberry Pi can handle low-volume requests
- Stream checking is CPU/network intensive
- Consider limiting concurrent requests
- Monitor resource usage

### 9.2 Reliability

- Use systemd for auto-restart
- Set up monitoring/alerting
- Consider watchdog for process monitoring
- Regular backups of database

### 9.3 Network Stability

- Dynamic IP changes (use dynamic DNS)
- Power outages (use UPS if critical)
- Network interruptions (handle gracefully in code)

### 9.4 Security

- Change default passwords
- Keep system updated
- Use firewall (ufw)
- Consider fail2ban for API protection
- Use HTTPS (Let's Encrypt)

---

## Questions Resolved

1. ✅ **Target machine**: Raspberry Pi (Linux)
2. ✅ **Deployment method**: Git clone or archive for API, GitHub Pages for frontend
3. ✅ **Frontend hosting**: GitHub Pages (static)
4. ✅ **API hosting**: Raspberry Pi
5. ✅ **Expected traffic**: Low volume (confirmed)

## Remaining Questions

1. **Raspberry Pi network setup?** (Public IP, port forwarding, dynamic DNS, or tunnel?)
2. **GitHub repository name?** (For GitHub Pages URL)
3. **API authentication?** (Public access or API key?)
4. **HTTPS for API?** (Let's Encrypt or HTTP only?)

---

**Document Version**: 2.0  
**Last Updated**: 2026-01-25  
**Status**: Updated for GitHub Pages + Raspberry Pi Architecture
