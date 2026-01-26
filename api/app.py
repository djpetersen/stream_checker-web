"""
Stream Checker Web API

Simple Flask API for submitting stream check requests.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import sys
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
        
        phase = data.get("phase", 4)
        if phase not in [1, 2, 3, 4]:
            return jsonify({"error": "Phase must be 1-4"}), 400
        
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
            "phase": phase
        }
        
        # Phase 1: Connectivity
        if phase >= 1:
            try:
                checker = ConnectivityChecker(
                    connection_timeout=config.get("security.connection_timeout", 30),
                    read_timeout=config.get("security.read_timeout", 60),
                    verify_ssl=config.get("security.verify_ssl", True)
                )
                phase_result = checker.check(url)
                result.update(phase_result)
                db.add_test_run(test_run_id, stream_id, 1, result)
            except Exception as e:
                logger.error(f"Phase 1 error: {e}", exc_info=True)
                result["connectivity"] = {
                    "status": "error",
                    "error": f"Phase 1 failed: {str(e)}"
                }
        
        # Phase 2: Player Test
        if phase >= 2:
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
                result["phase"] = 2
                db.add_test_run(test_run_id, stream_id, 2, result)
            except Exception as e:
                logger.error(f"Phase 2 error: {e}", exc_info=True)
                result["player_tests"] = {
                    "vlc": {
                        "status": "error",
                        "error": f"Phase 2 failed: {str(e)}"
                    }
                }
        
        # Phase 3: Audio Analysis
        if phase >= 3:
            try:
                analyzer = AudioAnalyzer(
                    sample_duration=config.get("stream_checker.default_sample_duration", 10),
                    silence_threshold_db=config.get("stream_checker.default_silence_threshold", -40),
                    silence_min_duration=2.0
                )
                audio_result = analyzer.analyze(url)
                result["audio_analysis"] = audio_result
                result["phase"] = 3
                db.add_test_run(test_run_id, stream_id, 3, result)
            except Exception as e:
                logger.error(f"Phase 3 error: {e}", exc_info=True)
                result["audio_analysis"] = {
                    "status": "error",
                    "error": f"Phase 3 failed: {str(e)}"
                }
        
        # Phase 4: Ad Detection
        if phase >= 4:
            try:
                detector = AdDetector(monitoring_duration=30, check_interval=2.0)
                ad_result = detector.detect(url)
                result["ad_detection"] = ad_result
                
                health_info = HealthScoreCalculator.calculate(result)
                result["health_score"] = health_info["health_score"]
                result["issues"] = health_info["issues"]
                result["recommendations"] = health_info["recommendations"]
                result["phase"] = 4
                db.add_test_run(test_run_id, stream_id, 4, result)
            except Exception as e:
                logger.error(f"Phase 4 error: {e}", exc_info=True)
                result["ad_detection"] = {
                    "status": "error",
                    "error": f"Phase 4 failed: {str(e)}"
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


if __name__ == "__main__":
    # Run development server
    # Use threaded=False to avoid fork crashes with subprocess on macOS
    # Note: This limits to one request at a time, but prevents crashes
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=False)
