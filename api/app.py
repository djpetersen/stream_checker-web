"""
Stream Checker Web API

Simple Flask API for submitting stream check requests.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import sys
import json
from pathlib import Path

# Add parent directory to path to import stream_checker
# In production, install stream_checker as a package instead
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "stream_checker"))

try:
    from stream_checker.database.models import Database
    from stream_checker.security.key_management import generate_test_run_id, generate_stream_id
    from stream_checker.security.validation import URLValidator, ValidationError
    from stream_checker.utils.request_utils import get_client_ip, get_user_agent, get_referer
    from stream_checker.core.connectivity import ConnectivityChecker
    from stream_checker.core.player_test import test_player_connectivity
    from stream_checker.core.audio_analysis import AudioAnalyzer
    from stream_checker.core.ad_detection import AdDetector, HealthScoreCalculator
    from stream_checker.utils.config import Config
    from stream_checker.utils.logging import setup_logging
except ImportError as e:
    print(f"Error importing stream_checker: {e}")
    print("Make sure stream_checker is installed or in the parent directory")
    sys.exit(1)

# Initialize Flask app
app = Flask(__name__)

# Configure CORS for GitHub Pages and local development
# Allow GitHub Pages origins (any *.github.io subdomain) and localhost
CORS(app, resources={
    r"/api/*": {
        "origins": [
            r"https://.*\.github\.io",  # Any GitHub Pages site
            "http://localhost:*",        # Local development (any port)
            "http://127.0.0.1:*",        # Local development (any port)
            "https://localhost:*",       # Local HTTPS development
        ],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "max_age": 3600
    }
})

# Setup logging
logger = setup_logging(level="INFO")

# Initialize database
config = Config()
db_path = config.get_path("database.path")
db = Database(db_path)

# Initialize URL validator
url_validator = URLValidator(
    allowed_schemes=config.get("security.allowed_schemes", ["http", "https"]),
    block_private_ips=config.get("security.block_private_ips", False),
    max_url_length=config.get("security.max_url_length", 2048)
)


# Custom error handlers for better JSON responses
@app.errorhandler(405)
def method_not_allowed(e):
    """Return JSON error for 405 Method Not Allowed"""
    return jsonify({
        "error": "Method Not Allowed",
        "message": f"The requested method is not allowed for this endpoint. Check the API documentation for the correct HTTP method.",
        "status": 405
    }), 405


@app.errorhandler(404)
def not_found(e):
    """Return JSON error for 404 Not Found"""
    return jsonify({
        "error": "Not Found",
        "message": "The requested endpoint was not found. Check the API documentation for available endpoints.",
        "status": 404
    }), 404


@app.route("/", methods=["GET"])
def root():
    """Root endpoint - API information"""
    return jsonify({
        "service": "stream_checker_api",
        "version": "1.0.0",
        "endpoints": {
            "health": "/api/health (GET)",
            "check_stream": "/api/streams/check (POST)",
            "job_status": "/api/jobs/<test_run_id> (GET)",
            "job_results": "/api/jobs/<test_run_id>/results (GET)",
            "request_stats": "/api/requests/stats (GET)",
            "log_listening": "/api/listening/log (POST)",
            "listening_history": "/api/listening/history (GET)"
        }
    }), 200


@app.route("/api", methods=["GET"])
def api_root():
    """API root endpoint"""
    return jsonify({
        "service": "stream_checker_api",
        "endpoints": {
            "health": "/api/health (GET)",
            "check_stream": "/api/streams/check (POST)",
            "job_status": "/api/jobs/<test_run_id> (GET)",
            "job_results": "/api/jobs/<test_run_id>/results (GET)",
            "request_stats": "/api/requests/stats (GET)",
            "log_listening": "/api/listening/log (POST)",
            "listening_history": "/api/listening/history (GET)"
        }
    }), 200


@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "stream_checker_api"}), 200


@app.route("/api/streams/check", methods=["POST"])
def check_stream():
    """
    Submit a stream URL for checking
    
    Request body:
    {
        "url": "https://example.com/stream.mp3",
        "phase": 4  # Optional: 1-4, default: 4
    }
    
    Returns:
    {
        "job_id": "uuid",
        "stream_id": "hash",
        "status": "processing",
        "message": "Stream check started"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body required"}), 400
        
        url = data.get("url")
        if not url:
            return jsonify({"error": "URL is required"}), 400
        
        # Handle both old format (phase) and new format (tests)
        tests = data.get("tests")
        phase = data.get("phase")
        
        # If new format (tests object), map to phase
        if tests:
            if not isinstance(tests, dict):
                return jsonify({"error": "tests must be an object"}), 400
            
            # Validate at least one test is selected
            if not any(tests.values()):
                return jsonify({"error": "At least one test must be selected"}), 400
            
            # Auto-select connectivity if any other test is selected
            if any(tests.get(k) for k in ["stream_info", "metadata", "player_test", "audio_analysis", "ad_detection"]):
                tests["connectivity"] = True
            
            # Map tests to phase number (for backward compatibility with internal logic)
            # Determine max phase needed based on selected tests
            phase = 1  # Always need phase 1 for connectivity
            if tests.get("player_test"):
                phase = max(phase, 2)
            if tests.get("audio_analysis"):
                phase = max(phase, 3)
            if tests.get("ad_detection"):
                phase = max(phase, 4)
        elif phase:
            # Old format: convert phase to tests object
            tests = {
                "connectivity": True,
                "stream_info": True,
                "metadata": True,
                "player_test": phase >= 2,
                "audio_analysis": phase >= 3,
                "ad_detection": phase >= 4
            }
            if phase not in [1, 2, 3, 4]:
                return jsonify({"error": "Phase must be 1-4"}), 400
        else:
            # Default: all tests
            tests = {
                "connectivity": True,
                "stream_info": True,
                "metadata": True,
                "player_test": True,
                "audio_analysis": True,
                "ad_detection": True
            }
            phase = 4
        
        # Get client IP
        ip_address = get_client_ip(request) or "unknown"
        
        # Check rate limiting
        request_count = db.get_ip_request_count(ip_address, time_window_minutes=60)
        max_requests = config.get("security.max_urls_per_minute", 10) * 60  # Per hour
        if request_count >= max_requests:
            return jsonify({
                "error": "Rate limit exceeded",
                "message": f"Maximum {max_requests} requests per hour",
                "retry_after": 3600
            }), 429
        
        # Validate URL
        try:
            url_validator.validate_and_raise(url)
        except ValidationError as e:
            return jsonify({"error": str(e)}), 400
        
        # Generate IDs
        test_run_id = generate_test_run_id()
        stream_id = generate_stream_id(url)
        
        # Log request
        try:
            request_id = db.log_request(
                ip_address=ip_address,
                stream_url=url,
                test_run_id=test_run_id,
                stream_id=stream_id,
                user_agent=get_user_agent(request),
                referer=get_referer(request),
                request_method="POST"
            )
            logger.info(f"Request logged: request_id={request_id}, ip={ip_address}, url={url}")
        except Exception as e:
            logger.error(f"Error logging request: {e}")
            # Continue even if logging fails
        
        # Add stream to database
        try:
            db.add_stream(stream_id, url)
        except Exception as e:
            logger.warning(f"Error adding stream to database: {e}")
        
        # TODO: For now, run synchronously
        # Later: Add to queue for async processing
        # For low volume, synchronous is fine
        
        # Run stream check
        result = {
            "test_run_id": test_run_id,
            "stream_id": stream_id,
            "stream_url": url,
            "tests_requested": [k for k, v in tests.items() if v],
            "tests_completed": []
        }
        
        # Connectivity (always run if selected, or if any other test is selected)
        if tests.get("connectivity", True):
            try:
                checker = ConnectivityChecker(
                    connection_timeout=config.get("security.connection_timeout", 30),
                    read_timeout=config.get("security.read_timeout", 60),
                    verify_ssl=config.get("security.verify_ssl", True)
                )
                phase_result = checker.check(url)
                result.update(phase_result)
                
                # Remove phase from result (internal only)
                result.pop("phase", None)
                
                # Only include stream_info and metadata if requested
                if not tests.get("stream_info"):
                    result.pop("stream_parameters", None)
                    result.pop("stream_type", None)
                if not tests.get("metadata"):
                    result.pop("metadata", None)
                
                result["tests_completed"].append("connectivity")
                if tests.get("stream_info"):
                    result["tests_completed"].append("stream_info")
                if tests.get("metadata"):
                    result["tests_completed"].append("metadata")
                
                db.add_test_run(test_run_id, stream_id, 1, result)
            except Exception as e:
                logger.error(f"Connectivity test error: {e}", exc_info=True)
                result["connectivity"] = {
                    "status": "error",
                    "error": f"Connectivity test failed: {str(e)}"
                }
        
        # Player Test
        if tests.get("player_test") and phase >= 2:
            try:
                player_result = test_player_connectivity(
                    url,
                    playback_duration=config.get("stream_checker.default_sample_duration", 5),
                    connection_timeout=config.get("security.connection_timeout", 30)
                )
                result["player_tests"] = {"vlc": player_result}
                result["connection_quality"] = {
                    "stable": player_result.get("status") == "success",
                    "packet_loss_detected": False
                }
                result["tests_completed"].append("player_test")
                db.add_test_run(test_run_id, stream_id, 2, result)
            except Exception as e:
                logger.error(f"Player test error: {e}", exc_info=True)
                result["player_tests"] = {
                    "vlc": {
                        "status": "error",
                        "error": f"Player test failed: {str(e)}"
                    }
                }
        
        # Audio Analysis
        if tests.get("audio_analysis") and phase >= 3:
            try:
                analyzer = AudioAnalyzer(
                    sample_duration=config.get("stream_checker.default_sample_duration", 10),
                    silence_threshold_db=config.get("stream_checker.default_silence_threshold", -40),
                    silence_min_duration=2.0
                )
                audio_result = analyzer.analyze(url)
                result["audio_analysis"] = audio_result
                result["tests_completed"].append("audio_analysis")
                db.add_test_run(test_run_id, stream_id, 3, result)
            except Exception as e:
                logger.error(f"Audio analysis error: {e}", exc_info=True)
                result["audio_analysis"] = {
                    "status": "error",
                    "error": f"Audio analysis failed: {str(e)}"
                }
        
        # Ad Detection
        if tests.get("ad_detection") and phase >= 4:
            try:
                # Get duration from tests dict (could be an object with duration_seconds or just True)
                duration = 60  # Default duration
                if isinstance(tests.get("ad_detection"), dict):
                    duration = tests["ad_detection"].get("duration_seconds", 60)
                elif tests.get("ad_detection") is True:
                    duration = 60  # Default when just True
                
                # Ensure duration is within valid range (10-300 seconds)
                duration = max(10, min(300, int(duration)))
                
                detector = AdDetector(monitoring_duration=duration, check_interval=2.0)
                ad_result = detector.detect(url)
                result["ad_detection"] = ad_result
                
                health_info = HealthScoreCalculator.calculate(result)
                result["health_score"] = health_info["health_score"]
                result["issues"] = health_info["issues"]
                result["recommendations"] = health_info["recommendations"]
                result["tests_completed"].append("ad_detection")
                db.add_test_run(test_run_id, stream_id, 4, result)
            except Exception as e:
                logger.error(f"Ad detection error: {e}", exc_info=True)
                result["ad_detection"] = {
                    "status": "error",
                    "error": f"Ad detection failed: {str(e)}"
                }
                # Still try to calculate health score with available data
                try:
                    health_info = HealthScoreCalculator.calculate(result)
                    result["health_score"] = health_info["health_score"]
                    result["issues"] = health_info["issues"]
                    result["recommendations"] = health_info["recommendations"]
                except Exception:
                    pass
        
        # Request was already logged at the beginning, no need to log again
        
        return jsonify({
            "test_run_id": test_run_id,
            "stream_id": stream_id,
            "status": "completed",
            "results": result
        }), 200
        
    except Exception as e:
        logger.error(f"Error processing stream check: {e}", exc_info=True)
        return jsonify({"error": "Internal server error", "message": str(e)}), 500


@app.route("/api/jobs/<test_run_id>", methods=["GET"])
def get_job_status(test_run_id):
    """Get job status by test_run_id"""
    try:
        # Get latest test run from database
        # For now, just check if it exists
        # TODO: Implement proper job status tracking
        
        history = db.get_request_history(limit=100)
        for req in history:
            if req.get("test_run_id") == test_run_id:
                return jsonify({
                    "test_run_id": test_run_id,
                    "status": "completed",
                    "request_timestamp": req.get("request_timestamp")
                }), 200
        
        return jsonify({"error": "Job not found"}), 404
        
    except Exception as e:
        logger.error(f"Error getting job status: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/jobs/<test_run_id>/results", methods=["GET"])
def get_job_results(test_run_id):
    """Get job results by test_run_id"""
    try:
        # Get results from database
        # TODO: Implement proper result retrieval
        
        history = db.get_request_history(limit=1000)
        for req in history:
            if req.get("test_run_id") == test_run_id:
                stream_id = req.get("stream_id")
                if stream_id:
                    stream_history = db.get_stream_history(stream_id, limit=1)
                    if stream_history:
                        return jsonify({
                            "test_run_id": test_run_id,
                            "results": stream_history[0].get("results", {})
                        }), 200
        
        return jsonify({"error": "Results not found"}), 404
        
    except Exception as e:
        logger.error(f"Error getting job results: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/requests/stats", methods=["GET"])
def get_request_stats():
    """Get request statistics for current IP"""
    try:
        ip_address = get_client_ip(request) or "unknown"
        
        count_last_hour = db.get_ip_request_count(ip_address, time_window_minutes=60)
        count_last_day = db.get_ip_request_count(ip_address, time_window_minutes=1440)
        
        max_per_hour = config.get("security.max_urls_per_minute", 10) * 60
        
        return jsonify({
            "ip_address": ip_address,
            "requests_last_hour": count_last_hour,
            "requests_last_day": count_last_day,
            "rate_limit_per_hour": max_per_hour,
            "remaining_this_hour": max(0, max_per_hour - count_last_hour)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting request stats: {e}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/tests/all", methods=["GET"])
def get_all_tests():
    """Get test runs with pagination support"""
    try:
        import sqlite3
        from pathlib import Path
        
        # Get pagination parameters
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Validate pagination parameters
        if limit < 1 or limit > 500:
            limit = 50
        if offset < 0:
            offset = 0
        
        # Get test runs from database
        db_path = Path(config.get_path("database.path")).expanduser()
        
        tests = []
        total_count = 0
        with sqlite3.connect(str(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get total count for pagination info
            cursor.execute("SELECT COUNT(DISTINCT tr.test_run_id) as count FROM test_runs tr")
            total_row = cursor.fetchone()
            total_count = total_row["count"] if total_row else 0
            
            # Get paginated test runs with their latest phase results and IP addresses
            cursor.execute("""
                SELECT 
                    tr.test_run_id,
                    tr.stream_id,
                    tr.timestamp,
                    tr.phase,
                    tr.results,
                    s.url as stream_url,
                    rl.ip_address
                FROM test_runs tr
                LEFT JOIN streams s ON tr.stream_id = s.stream_id
                LEFT JOIN request_logs rl ON tr.test_run_id = rl.test_run_id
                ORDER BY tr.timestamp DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))
            
            rows = cursor.fetchall()
            
            for row in rows:
                try:
                    results = json.loads(row["results"]) if row["results"] else {}
                    tests.append({
                        "test_run_id": row["test_run_id"],
                        "stream_id": row["stream_id"],
                        "stream_url": row["stream_url"],
                        "timestamp": row["timestamp"],
                        "phase": row["phase"],
                        "ip_address": row["ip_address"] if row["ip_address"] else None,
                        "results": results
                    })
                except json.JSONDecodeError:
                    continue
        
        return jsonify({
            "tests": tests,
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total_count
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting all tests: {e}", exc_info=True)
        return jsonify({"error": "Internal server error", "message": str(e)}), 500


@app.route("/api/listening/log", methods=["POST"])
def log_listening_session():
    """Log a listening session (play to pause/stop, or unpause to pause/stop)"""
    try:
        # Handle both JSON and blob (from sendBeacon) requests
        data = None
        if request.content_type and 'application/json' in request.content_type:
            data = request.get_json()
        else:
            # Try to parse as JSON from raw data (for sendBeacon blob)
            try:
                data = json.loads(request.data.decode('utf-8'))
            except (ValueError, UnicodeDecodeError):
                pass
        
        if not data:
            # Try one more time with get_json(force=True)
            try:
                data = request.get_json(force=True)
            except:
                pass
        
        if not data:
            logger.warning(f"Could not parse listening session data. Content-Type: {request.content_type}, Data length: {len(request.data)}")
            return jsonify({"error": "No JSON data provided"}), 400
        
        # Validate required fields
        required_fields = ["stream_url", "start_timestamp", "end_timestamp", "listening_time_seconds", "action_type"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Validate action_type
        if data["action_type"] not in ("pause", "stop"):
            return jsonify({"error": "action_type must be 'pause' or 'stop'"}), 400
        
        # Validate listening_time_seconds
        try:
            listening_time = float(data["listening_time_seconds"])
            if listening_time < 0:
                return jsonify({"error": "listening_time_seconds must be non-negative"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "listening_time_seconds must be a number"}), 400
        
        # Parse timestamps
        try:
            from datetime import datetime
            start_timestamp = datetime.fromisoformat(data["start_timestamp"].replace('Z', '+00:00'))
            end_timestamp = datetime.fromisoformat(data["end_timestamp"].replace('Z', '+00:00'))
        except (ValueError, AttributeError) as e:
            return jsonify({"error": f"Invalid timestamp format: {e}"}), 400
        
        # Get IP address and user agent
        ip_address = get_client_ip(request) or "unknown"
        user_agent = get_user_agent(request)
        
        logger.info(f"Logging listening session: IP={ip_address}, URL={data['stream_url']}, Duration={listening_time}s, Action={data['action_type']}")
        
        # Log the listening session
        try:
            session_id = db.log_listening_session(
                ip_address=ip_address,
                stream_url=data["stream_url"],
                start_timestamp=start_timestamp,
                end_timestamp=end_timestamp,
                listening_time_seconds=listening_time,
                action_type=data["action_type"],
                user_agent=user_agent
            )
            
            logger.info(f"Successfully logged listening session: session_id={session_id}")
            
            return jsonify({
                "success": True,
                "session_id": session_id,
                "message": "Listening session logged successfully"
            }), 200
        except Exception as db_error:
            logger.error(f"Database error logging listening session: {db_error}", exc_info=True)
            return jsonify({"error": "Database error", "message": str(db_error)}), 500
        
    except Exception as e:
        logger.error(f"Error logging listening session: {e}", exc_info=True)
        return jsonify({"error": "Internal server error", "message": str(e)}), 500


@app.route("/api/listening/history", methods=["GET"])
def get_listening_history():
    """Get listening session history with optional filters and pagination"""
    try:
        ip_address = request.args.get('ip_address')
        stream_url = request.args.get('stream_url')
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Validate pagination parameters
        if limit < 1 or limit > 500:
            limit = 50
        if offset < 0:
            offset = 0
        
        # Get listening history from database with pagination
        # We need to get total count and paginated results
        import sqlite3
        from pathlib import Path
        
        db_path = Path(config.get_path("database.path")).expanduser()
        
        with sqlite3.connect(str(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Build WHERE clause for filters
            where_clauses = ["1=1"]
            params = []
            
            if ip_address:
                where_clauses.append("ip_address = ?")
                params.append(ip_address)
            
            if stream_url:
                where_clauses.append("stream_url = ?")
                params.append(stream_url)
            
            where_clause = " AND ".join(where_clauses)
            
            # Get total count
            cursor.execute(f"SELECT COUNT(*) as count FROM listening_sessions WHERE {where_clause}", params)
            total_row = cursor.fetchone()
            total_count = total_row["count"] if total_row else 0
            
            # Get paginated results
            query = f"""
                SELECT session_id, ip_address, stream_url, user_agent,
                       start_timestamp, end_timestamp, listening_time_seconds, action_type, created_at
                FROM listening_sessions
                WHERE {where_clause}
                ORDER BY start_timestamp DESC
                LIMIT ? OFFSET ?
            """
            params.extend([limit, offset])
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            sessions = [
                {
                    "session_id": row["session_id"],
                    "ip_address": row["ip_address"],
                    "stream_url": row["stream_url"],
                    "user_agent": row["user_agent"],
                    "start_timestamp": row["start_timestamp"],
                    "end_timestamp": row["end_timestamp"],
                    "listening_time_seconds": row["listening_time_seconds"],
                    "action_type": row["action_type"],
                    "created_at": row["created_at"]
                }
                for row in rows
            ]
        
        return jsonify({
            "sessions": sessions,
            "total": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total_count
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting listening history: {e}", exc_info=True)
        return jsonify({"error": "Internal server error", "message": str(e)}), 500


@app.route("/api/tests/<test_run_id>/detailed", methods=["GET"])
def get_test_detailed(test_run_id):
    """Get detailed results for a specific test run"""
    try:
        import sqlite3
        from pathlib import Path
        
        # Get test run from database
        db_path = Path(config.get_path("database.path")).expanduser()
        
        with sqlite3.connect(str(db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get test run with highest phase (most complete results)
            cursor.execute("""
                SELECT 
                    tr.test_run_id,
                    tr.stream_id,
                    tr.timestamp,
                    tr.phase,
                    tr.results,
                    s.url as stream_url,
                    s.name as stream_name,
                    s.created_at as stream_created_at,
                    s.last_tested as stream_last_tested,
                    s.test_count,
                    rl.ip_address
                FROM test_runs tr
                LEFT JOIN streams s ON tr.stream_id = s.stream_id
                LEFT JOIN request_logs rl ON tr.test_run_id = rl.test_run_id
                WHERE tr.test_run_id = ?
                ORDER BY tr.phase DESC
                LIMIT 1
            """, (test_run_id,))
            
            row = cursor.fetchone()
            
            if not row:
                return jsonify({"error": "Test run not found"}), 404
            
            try:
                results = json.loads(row["results"]) if row["results"] else {}
                
                # Get all phases for this test run (history)
                cursor.execute("""
                    SELECT phase, timestamp, results
                    FROM test_runs
                    WHERE test_run_id = ?
                    ORDER BY phase ASC
                """, (test_run_id,))
                
                phase_history = []
                for phase_row in cursor.fetchall():
                    try:
                        phase_results = json.loads(phase_row["results"]) if phase_row["results"] else {}
                        phase_history.append({
                            "phase": phase_row["phase"],
                            "timestamp": phase_row["timestamp"],
                            "results": phase_results
                        })
                    except json.JSONDecodeError:
                        continue
                
                return jsonify({
                    "test_run_id": row["test_run_id"],
                    "stream_id": row["stream_id"],
                    "stream_url": row["stream_url"],
                    "stream_name": row["stream_name"],
                    "stream_created_at": row["stream_created_at"],
                    "stream_last_tested": row["stream_last_tested"],
                    "stream_test_count": row["test_count"],
                    "timestamp": row["timestamp"],
                    "phase": row["phase"],
                    "ip_address": row["ip_address"] if row["ip_address"] else None,
                    "results": results,
                    "phase_history": phase_history
                }), 200
                
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing JSON for test_run_id {test_run_id}: {e}")
                return jsonify({"error": "Invalid JSON in database"}), 500
        
    except Exception as e:
        logger.error(f"Error getting detailed test: {e}", exc_info=True)
        return jsonify({"error": "Internal server error", "message": str(e)}), 500


if __name__ == "__main__":
    # Run development server
    # Use threaded=False to avoid fork crashes with subprocess on macOS
    # Note: This limits to one request at a time, but prevents crashes
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=False)
