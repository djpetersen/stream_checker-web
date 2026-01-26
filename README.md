# Stream Checker Web Service

Web interface and API for the Stream Checker application.

## Overview

This project provides a web interface and REST API for submitting stream URLs to be checked. It connects to a Raspberry Pi worker (or local worker) that runs the actual stream checking using the `stream_checker` library.

## Architecture

```
Web Page (HTML/JS) → API Server (Flask/FastAPI) → Queue → Worker (Raspberry Pi)
```

## Setup

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Install Stream Checker Library

For development:
```bash
pip install -e ../stream_checker
```

For production:
```bash
pip install git+https://github.com/djpetersen/stream_checker.git
```

### Configuration

Copy `config.example.yaml` to `config.yaml` and configure:
- Database path
- Queue settings
- Worker connection
- Security settings

### Run API Server

```bash
python api/app.py
```

### Run Worker (on Raspberry Pi)

```bash
python worker/worker.py
```

## Project Structure

```
stream_checker-web/
├── api/                    # API server code
│   ├── app.py             # Main Flask/FastAPI app
│   ├── routes/            # API endpoints
│   └── models/            # API models
├── frontend/              # Web frontend
│   ├── index.html
│   ├── app.js
│   └── style.css
├── worker/                # Worker code (optional)
│   └── worker.py
├── requirements.txt
└── README.md
```

## API Endpoints

- `POST /api/streams/check` - Submit stream URL for checking
- `GET /api/jobs/{job_id}` - Get job status
- `GET /api/jobs/{job_id}/results` - Get results
- `GET /api/requests/history` - Get request history (admin)

## Development

This project uses the `stream_checker` library as a dependency. The library contains all the core stream checking logic.
