// Stream Checker Web Frontend

// Configure API URL from URL parameter, or use default
// Usage: https://username.github.io/repo/?api=http://your-raspberry-pi:5000
function getApiBaseUrl() {
    const urlParams = new URLSearchParams(window.location.search);
    const apiParam = urlParams.get('api');
    
    if (apiParam) {
        // Remove trailing slash if present
        return apiParam.replace(/\/$/, '') + '/api';
    }
    
    // Default: localhost for development, or set your Raspberry Pi URL here
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        return 'http://localhost:5000/api';
    }
    
    // Production default - UPDATE THIS with your Raspberry Pi URL
    return 'http://YOUR-RASPBERRY-PI-IP:5000/api';
}

const API_BASE_URL = getApiBaseUrl();

// Display API URL in console for debugging
console.log('API Base URL:', API_BASE_URL);

// Load stats on page load
document.addEventListener('DOMContentLoaded', () => {
    // Show API URL if not localhost (for debugging)
    if (!window.location.hostname.includes('localhost') && !window.location.hostname.includes('127.0.0.1')) {
        const apiInfo = document.createElement('div');
        apiInfo.id = 'apiInfo';
        apiInfo.style.cssText = 'padding: 10px; background: #2a2a45; margin-bottom: 20px; border-radius: 5px; font-size: 12px; color: #b0b0b0; border: 1px solid #3a3a5c;';
        apiInfo.innerHTML = `<strong>API:</strong> ${API_BASE_URL} | <a href="?api=${encodeURIComponent(API_BASE_URL.replace('/api', ''))}">Change</a>`;
        document.querySelector('.container main').insertBefore(apiInfo, document.querySelector('.input-section'));
    }
    
    loadStats();
});

// Handle select all / deselect all buttons and checkbox styling
document.addEventListener('DOMContentLoaded', () => {
    const selectAllBtn = document.getElementById('selectAllBtn');
    const deselectAllBtn = document.getElementById('deselectAllBtn');
    const testCheckboxes = document.querySelectorAll('input[name="tests"]');
    
    // Function to update checkbox styling
    const updateCheckboxStyle = (checkbox) => {
        const option = checkbox.closest('.test-option');
        if (checkbox.checked) {
            option.classList.add('checked');
        } else {
            option.classList.remove('checked');
        }
    };
    
    // Initialize styling for all checkboxes
    testCheckboxes.forEach(cb => {
        updateCheckboxStyle(cb);
        cb.addEventListener('change', () => {
            updateCheckboxStyle(cb);
        });
    });
    
    if (selectAllBtn) {
        selectAllBtn.addEventListener('click', () => {
            testCheckboxes.forEach(cb => {
                cb.checked = true;
                updateCheckboxStyle(cb);
            });
        });
    }
    
    if (deselectAllBtn) {
        deselectAllBtn.addEventListener('click', () => {
            testCheckboxes.forEach(cb => {
                cb.checked = false;
                updateCheckboxStyle(cb);
            });
        });
    }
    
    // Auto-select connectivity if any other test is selected
    testCheckboxes.forEach(cb => {
        cb.addEventListener('change', () => {
            updateCheckboxStyle(cb);
            if (cb.id !== 'test-connectivity' && cb.checked) {
                const connectivityCheckbox = document.getElementById('test-connectivity');
                connectivityCheckbox.checked = true;
                updateCheckboxStyle(connectivityCheckbox);
            }
        });
    });
});

// Handle form submission
document.getElementById('streamForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const url = document.getElementById('streamUrl').value;
    
    // Get selected tests from checkboxes
    const selectedTests = {};
    document.querySelectorAll('input[name="tests"]:checked').forEach(cb => {
        selectedTests[cb.value] = true;
    });
    
    // Validate: at least one test must be selected
    if (Object.keys(selectedTests).length === 0) {
        alert('Please select at least one test to run.');
        return;
    }
    
    const submitBtn = document.getElementById('submitBtn');
    
    // Disable submit button
    submitBtn.disabled = true;
    submitBtn.textContent = 'Checking...';
    
    // Show status section with loading state
    const statusSection = document.getElementById('statusSection');
    const statusMessage = document.getElementById('statusMessage');
    const progressBar = document.getElementById('progressBar');
    const progressFill = document.getElementById('progressFill');
    
    statusSection.style.display = 'block';
    document.getElementById('resultsSection').style.display = 'none';
    statusMessage.style.color = '#667eea';
    progressBar.style.display = 'block';
    progressFill.style.width = '5%';
    
    // Map test IDs to friendly names and determine test order
    const testNames = {
        'connectivity': 'Basic Connectivity',
        'stream_info': 'Stream Information',
        'metadata': 'Metadata',
        'player_test': 'Player Compatibility',
        'audio_analysis': 'Audio Quality',
        'ad_detection': 'Ad Detection'
    };
    
    // Determine test order based on what's selected
    const testOrder = [];
    if (selectedTests.connectivity) {
        testOrder.push('connectivity');
        if (selectedTests.stream_info) testOrder.push('stream_info');
        if (selectedTests.metadata) testOrder.push('metadata');
    }
    if (selectedTests.player_test) testOrder.push('player_test');
    if (selectedTests.audio_analysis) testOrder.push('audio_analysis');
    if (selectedTests.ad_detection) testOrder.push('ad_detection');
    
    // Calculate progress segments (each test gets equal share of progress)
    const totalTests = testOrder.length;
    const progressPerTest = totalTests > 0 ? (90 - 5) / totalTests : 85; // Start at 5%, end at 90%
    
    // Animate progress with detailed status messages
    let currentTestIndex = 0;
    let progress = 5;
    
    // Update status message for current test
    const updateStatusMessage = () => {
        if (currentTestIndex < testOrder.length) {
            const currentTest = testOrder[currentTestIndex];
            const testName = testNames[currentTest] || currentTest;
            statusMessage.textContent = `Testing ${testName}...`;
        } else {
            statusMessage.textContent = 'Finalizing results...';
        }
    };
    
    // Initial status message
    updateStatusMessage();
    
    const progressInterval = setInterval(() => {
        // Calculate which test we should be on based on progress
        const targetProgress = 5 + (currentTestIndex + 1) * progressPerTest;
        
        if (progress < targetProgress) {
            progress = Math.min(progress + 3, targetProgress);
            progressFill.style.width = progress + '%';
        } else if (currentTestIndex < testOrder.length - 1) {
            // Move to next test
            currentTestIndex++;
            updateStatusMessage();
        } else if (progress < 90) {
            // Continue to 90% while finalizing
            progress = Math.min(progress + 2, 90);
            progressFill.style.width = progress + '%';
        }
    }, 400);
    
    try {
        const response = await fetch(`${API_BASE_URL}/streams/check`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url, tests: selectedTests }),
            // Add timeout
            signal: AbortSignal.timeout(300000) // 5 minutes timeout
        });
        
        clearInterval(progressInterval);
        statusMessage.textContent = 'Finalizing results...';
        progressFill.style.width = '100%';
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            const errorMsg = errorData.error || errorData.message || `HTTP ${response.status}: ${response.statusText}`;
            throw new Error(errorMsg);
        }
        
        const data = await response.json();
        
        // Validate response structure
        if (!data || (!data.results && !data.test_run_id)) {
            throw new Error('Invalid response format from server');
        }
        
        // Show results
        displayResults(data);
        statusMessage.textContent = '✓ Check completed successfully!';
        statusMessage.style.color = '#28a745';
        progressFill.style.background = 'linear-gradient(90deg, #28a745 0%, #20c997 100%)';
        
        // Reload stats
        loadStats();
        
    } catch (error) {
        clearInterval(progressInterval);
        statusMessage.textContent = 'Processing error...';
        progressFill.style.width = '100%';
        progressFill.style.background = 'linear-gradient(90deg, #dc3545 0%, #c82333 100%)';
        
        let errorMessage = 'An error occurred';
        
        if (error.name === 'AbortError' || error.message.includes('timeout')) {
            errorMessage = 'Request timed out. The stream check is taking too long.';
        } else if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
            errorMessage = 'Unable to connect to API server. Please check:\n' +
                          '1. The API server is running\n' +
                          '2. The API URL is correct\n' +
                          '3. CORS is properly configured\n' +
                          '4. Your network connection\n\n' +
                          `Current API URL: ${API_BASE_URL}`;
        } else if (error.message.includes('Invalid response')) {
            errorMessage = `Invalid response from server. The API may have encountered an error.\n\nAPI URL: ${API_BASE_URL}`;
        } else {
            errorMessage = `${error.message}\n\nAPI URL: ${API_BASE_URL}`;
        }
        
        statusMessage.textContent = `✗ Error: ${errorMessage}`;
        statusMessage.style.color = '#dc3545';
        statusMessage.style.whiteSpace = 'pre-line';
        
        // Show error in results section too
        document.getElementById('resultsSection').style.display = 'block';
        document.getElementById('resultsContent').innerHTML = `
            <div class="result-item" style="border-left-color: #dc3545;">
                <h3 style="color: #dc3545;">Error</h3>
                <p style="white-space: pre-line;">${errorMessage}</p>
                <p style="font-size: 12px; color: #b0b0b0; margin-top: 10px;">
                    Error Details: ${error.message || 'Unknown error'}
                </p>
            </div>
        `;
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Check Stream';
        // Hide progress bar after a delay
        setTimeout(() => {
            progressBar.style.display = 'none';
        }, 2000);
    }
});

function displayResults(data) {
    const resultsSection = document.getElementById('resultsSection');
    const resultsContent = document.getElementById('resultsContent');
    
    resultsSection.style.display = 'block';
    
    const results = data.results || data;
    
    let html = `
        <div class="result-item">
            <strong>Test Run ID:</strong> ${results.test_run_id || 'N/A'}<br>
            <strong>Stream ID:</strong> ${results.stream_id || 'N/A'}<br>
            <strong>Status:</strong> <span class="status-${data.status || 'completed'}">${data.status || 'completed'}</span>
            ${results.tests_completed ? `<br><strong>Tests Completed:</strong> ${results.tests_completed.join(', ')}` : ''}
        </div>
    `;
    
    // Health Score - Prominently displayed
    if (results.health_score !== undefined) {
        const score = results.health_score;
        const color = score >= 80 ? '#28a745' : score >= 60 ? '#ffc107' : '#dc3545';
        const emoji = score >= 80 ? '✓' : score >= 60 ? '⚠' : '✗';
        const status = score >= 80 ? 'Good' : score >= 60 ? 'Warning' : 'Critical';
        
        html += `
            <div class="result-item health-score" style="border-left: 4px solid ${color}; background: ${color}15;">
                <div style="display: flex; align-items: center; gap: 15px;">
                    <div style="font-size: 48px; color: ${color};">${emoji}</div>
                    <div>
                        <h2 style="margin: 0; color: ${color};">
                            Health Score: <span style="font-size: 1.2em;">${score}/100</span>
                        </h2>
                        <p style="margin: 5px 0 0 0; color: #b0b0b0; font-size: 14px;">Status: ${status}</p>
                    </div>
                </div>
            </div>
        `;
    }
    
    // Connectivity
    if (results.connectivity) {
        const conn = results.connectivity;
        // Check if HTTP status indicates an error (4xx, 5xx)
        const httpStatus = conn.http_status;
        const isHttpError = httpStatus && (httpStatus >= 400);
        const statusColor = (conn.status === 'success' && !isHttpError) ? '#28a745' : conn.status === 'error' || isHttpError ? '#dc3545' : '#ffc107';
        const statusIcon = (conn.status === 'success' && !isHttpError) ? '✓' : conn.status === 'error' || isHttpError ? '✗' : '⚠';
        const statusText = isHttpError ? `${conn.status} (HTTP ${httpStatus})` : (conn.status || 'unknown');
        
        html += `
            <div class="result-item">
                <h3>🔗 Connectivity</h3>
                <p><strong>Status:</strong> <span style="color: ${statusColor};">${statusIcon} ${statusText}</span></p>
                ${conn.response_time_ms ? `<p><strong>Response Time:</strong> ${conn.response_time_ms} ms</p>` : ''}
                ${conn.http_status ? `
                    <p><strong>HTTP Status:</strong> 
                        <code style="color: ${isHttpError ? '#dc3545' : '#28a745'}; font-weight: bold;">${conn.http_status}</code>
                        ${isHttpError ? ` <span style="color: #dc3545;">(${getHttpStatusText(conn.http_status)})</span>` : ''}
                    </p>
                ` : ''}
                ${conn.content_type ? `<p><strong>Content Type:</strong> <code>${conn.content_type}</code></p>` : ''}
                ${conn.final_url && conn.final_url !== results.stream_url ? `<p><strong>Final URL:</strong> <code style="font-size: 0.9em;">${conn.final_url}</code></p>` : ''}
                ${conn.error ? `<p style="color: #dc3545;"><strong>Error:</strong> ${conn.error}</p>` : ''}
                ${isHttpError ? `<p style="color: #dc3545; margin-top: 10px;"><strong>Details:</strong> The server returned an error status. This may indicate the stream URL is invalid, the resource was not found, or the server is experiencing issues.</p>` : ''}
            </div>
        `;
    }
    
    // SSL Certificate
    if (results.ssl_certificate && results.ssl_certificate.valid !== undefined) {
        const ssl = results.ssl_certificate;
        const sslColor = ssl.valid ? '#28a745' : '#dc3545';
        const sslIcon = ssl.valid ? '✓' : '✗';
        const expiryColor = ssl.days_until_expiration !== undefined && ssl.days_until_expiration < 30 ? '#ffc107' : '#28a745';
        html += `
            <div class="result-item">
                <h3>🔒 SSL Certificate</h3>
                <p><strong>Valid:</strong> <span style="color: ${sslColor};">${sslIcon} ${ssl.valid ? 'Yes' : 'No'}</span></p>
                ${ssl.days_until_expiration !== undefined ? 
                    `<p><strong>Days Until Expiration:</strong> <span style="color: ${expiryColor};">${ssl.days_until_expiration}</span></p>` : ''}
                ${ssl.issuer ? `<p><strong>Issuer:</strong> ${ssl.issuer}</p>` : ''}
            </div>
        `;
    }
    
    // Stream Type
    if (results.stream_type && results.stream_type.type) {
        const streamType = results.stream_type;
        const typeColors = {
            'Icecast': '#4a90e2',
            'Shoutcast': '#e24a4a',
            'ICY Stream': '#9b59b6',
            'HLS': '#2ecc71',
            'Direct HTTP/HTTPS': '#f39c12',
            'Unknown/Other': '#95a5a6'
        };
        const typeColor = typeColors[streamType.type] || '#95a5a6';
        const confidenceColors = {
            'high': '#28a745',
            'medium': '#ffc107',
            'low': '#dc3545'
        };
        const confidenceColor = confidenceColors[streamType.confidence] || '#95a5a6';
        
        html += `
            <div class="result-item">
                <h3>🔍 Stream Type</h3>
                <p><strong>Type:</strong> <span style="color: ${typeColor}; font-weight: bold; font-size: 1.1em;">${streamType.type}</span></p>
                ${streamType.server_version ? `<p><strong>Server Version:</strong> <code>${streamType.server_version}</code></p>` : ''}
                ${streamType.detected_via && streamType.detected_via.length > 0 ? 
                    `<p><strong>Detected Via:</strong> <code>${streamType.detected_via.join(', ')}</code></p>` : ''}
                ${streamType.confidence ? 
                    `<p><strong>Confidence:</strong> <span style="color: ${confidenceColor}; font-weight: bold;">${streamType.confidence.charAt(0).toUpperCase() + streamType.confidence.slice(1)}</span></p>` : ''}
            </div>
        `;
    }
    
    // Stream Parameters
    if (results.stream_parameters) {
        const params = results.stream_parameters;
        // Check if we have any actual parameter data
        const hasParams = params.bitrate_kbps || params.codec || params.sample_rate_hz || params.channels || 
                         params.container_format || params.bitrate_mode || params.duration_seconds;
        
        html += `
            <div class="result-item">
                <h3>📊 Stream Parameters</h3>
                ${hasParams ? `
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px;">
                        ${params.bitrate_kbps ? `<div><strong>Bitrate:</strong><br><span style="font-size: 1.2em; color: #9d7aff;">${params.bitrate_kbps} kbps</span></div>` : ''}
                        ${params.codec ? `<div><strong>Codec:</strong><br><code style="font-size: 1.1em;">${params.codec}</code></div>` : ''}
                        ${params.sample_rate_hz ? `<div><strong>Sample Rate:</strong><br><span style="font-size: 1.2em; color: #9d7aff;">${params.sample_rate_hz} Hz</span></div>` : ''}
                        ${params.channels ? `<div><strong>Channels:</strong><br><span style="font-size: 1.2em; color: #667eea;">${params.channels}</span></div>` : ''}
                        ${params.container_format ? `<div><strong>Container:</strong><br><code>${params.container_format}</code></div>` : ''}
                        ${params.bitrate_mode ? `<div><strong>Bitrate Mode:</strong><br><code>${params.bitrate_mode}</code></div>` : ''}
                        ${params.duration_seconds ? `<div><strong>Duration:</strong><br><span>${params.duration_seconds} seconds</span></div>` : ''}
                    </div>
                ` : `
                    <p style="color: #b0b0b0; font-style: italic;">
                        Stream parameters could not be extracted. This may occur if:
                        <ul style="margin: 10px 0 0 20px; color: #b0b0b0;">
                            <li>The stream URL returned an error (e.g., 404 Not Found)</li>
                            <li>The stream format is not supported</li>
                            <li>The stream requires authentication</li>
                            <li>The connection failed before parameters could be read</li>
                        </ul>
                    </p>
                `}
            </div>
        `;
    }
    
    // Player Tests
    if (results.player_tests && results.player_tests.vlc) {
        const vlc = results.player_tests.vlc;
        const playerColor = vlc.status === 'success' ? '#28a745' : vlc.status === 'error' ? '#dc3545' : '#ffc107';
        const playerIcon = vlc.status === 'success' ? '✓' : vlc.status === 'error' ? '✗' : '⚠';
        html += `
            <div class="result-item">
                <h3>▶️ Player Test (VLC)</h3>
                <p><strong>Status:</strong> <span style="color: ${playerColor};">${playerIcon} ${vlc.status || 'unknown'}</span></p>
                ${vlc.connection_time_ms ? `<p><strong>Connection Time:</strong> ${vlc.connection_time_ms} ms</p>` : ''}
                ${vlc.error ? `<p style="color: #dc3545;"><strong>Error:</strong> ${vlc.error}</p>` : ''}
            </div>
        `;
    }
    
    // Audio Analysis
    if (results.audio_analysis) {
        const audio = results.audio_analysis;
        const silenceColor = audio.silence_detection && audio.silence_detection.silence_detected ? '#ffc107' : '#28a745';
        const silenceIcon = audio.silence_detection && audio.silence_detection.silence_detected ? '⚠' : '✓';
        
        html += `
            <div class="result-item">
                <h3>🎵 Audio Analysis</h3>
                ${audio.silence_detection ? `
                    <p><strong>Silence Detected:</strong> 
                        <span style="color: ${silenceColor};">${silenceIcon} ${audio.silence_detection.silence_detected ? 'Yes' : 'No'}</span>
                    </p>
                    ${audio.silence_detection.silence_percentage !== undefined && audio.silence_detection.silence_percentage !== null ? 
                        `<p><strong>Silence Percentage:</strong> ${audio.silence_detection.silence_percentage.toFixed(1)}%</p>` : ''}
                ` : ''}
                ${audio.audio_quality && typeof audio.audio_quality === 'object' ? `
                    <div style="margin-top: 10px;">
                        <strong>Audio Quality:</strong>
                        ${audio.audio_quality.average_volume_db !== undefined && audio.audio_quality.average_volume_db !== null ? 
                            `<p>Average Volume: ${audio.audio_quality.average_volume_db.toFixed(1)} dB</p>` : ''}
                        ${audio.audio_quality.peak_volume_db !== undefined && audio.audio_quality.peak_volume_db !== null ? 
                            `<p>Peak Volume: ${audio.audio_quality.peak_volume_db.toFixed(1)} dB</p>` : ''}
                    </div>
                ` : ''}
            </div>
        `;
    }
    
    // Issues and Recommendations
    if (results.issues && results.issues.length > 0) {
        html += `
            <div class="result-item issues">
                <h3>Issues</h3>
                <ul>
                    ${results.issues.map(issue => `<li>${issue}</li>`).join('')}
                </ul>
            </div>
        `;
    }
    
    if (results.recommendations && results.recommendations.length > 0) {
        html += `
            <div class="result-item recommendations">
                <h3>Recommendations</h3>
                <ul>
                    ${results.recommendations.map(rec => `<li>${rec}</li>`).join('')}
                </ul>
            </div>
        `;
    }
    
    // Full JSON (collapsible)
    html += `
        <div class="result-item">
            <details>
                <summary>Full JSON Results</summary>
                <pre><code>${JSON.stringify(results, null, 2)}</code></pre>
            </details>
        </div>
    `;
    
    resultsContent.innerHTML = html;
}

// Helper function to get HTTP status text
function getHttpStatusText(status) {
    const statusTexts = {
        400: 'Bad Request',
        401: 'Unauthorized',
        403: 'Forbidden',
        404: 'Not Found',
        405: 'Method Not Allowed',
        408: 'Request Timeout',
        429: 'Too Many Requests',
        500: 'Internal Server Error',
        502: 'Bad Gateway',
        503: 'Service Unavailable',
        504: 'Gateway Timeout'
    };
    return statusTexts[status] || 'Unknown Error';
}

async function loadStats() {
    try {
        const response = await fetch(`${API_BASE_URL}/requests/stats`, {
            signal: AbortSignal.timeout(5000)
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        const statsContent = document.getElementById('statsContent');
        if (statsContent) {
            statsContent.innerHTML = `
                <p><strong>IP Address:</strong> ${data.ip_address}</p>
                <p><strong>Requests (Last Hour):</strong> ${data.requests_last_hour}</p>
                <p><strong>Requests (Last Day):</strong> ${data.requests_last_day}</p>
                <p><strong>Remaining (This Hour):</strong> ${data.remaining_this_hour} / ${data.rate_limit_per_hour}</p>
            `;
        }
    } catch (error) {
        const statsContent = document.getElementById('statsContent');
        if (statsContent) {
            let errorMsg = 'Error loading stats';
            if (error.name === 'AbortError' || error.message.includes('timeout')) {
                errorMsg = 'Stats request timed out. API server may be slow or unreachable.';
            } else if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
                errorMsg = `Unable to connect to API server at ${API_BASE_URL}. Please check if the server is running.`;
            } else {
                errorMsg = `Error loading stats: ${error.message}`;
            }
            statsContent.innerHTML = `<p style="color: #dc3545;">${errorMsg}</p>`;
        }
        console.error('Error loading stats:', error);
    }
}
