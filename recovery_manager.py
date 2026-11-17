import subprocess
import sys
import time
import threading
import urllib.request
import csv
import hashlib
import json

from datetime import datetime
from pathlib import Path
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

PROJECT_DIR = Path(__file__).resolve().parents[2]
SERVICE_FILE = PROJECT_DIR / "services" / "service.py"
LOG_FILE = PROJECT_DIR / "recovery_history.csv"

SERVICES = [
    {"name": "Service-1", "port": 5001},
    {"name": "Service-2", "port": 5002},
    {"name": "Service-3", "port": 5003}
]

processes = {}
service_status = {}
recovery_count = {s["name"]: 0 for s in SERVICES}
response_times = {s["name"]: None for s in SERVICES}

# Prevent simultaneous access to the history CSV
history_lock = threading.Lock()


def get_record_id(record):
    values = [
        record.get("Timestamp", ""),
        record.get("Service", ""),
        record.get("Port", ""),
        record.get("Result", "")
    ]

    record_text = json.dumps(values)
    return hashlib.sha256(record_text.encode()).hexdigest()


def log_recovery(name, port, result):

    with history_lock:
        file_exists = LOG_FILE.exists()

        with open(LOG_FILE, "a", newline="") as file:
            writer = csv.writer(file)

            if not file_exists or LOG_FILE.stat().st_size == 0:
                writer.writerow(
                    ["Timestamp", "Service", "Port", "Result"]
                )

            writer.writerow([
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                name,
                port,
                result
            ])


def start_service(service):

    name = service["name"]
    port = service["port"]

    process = subprocess.Popen(
        [
            sys.executable,
            str(SERVICE_FILE),
            "--name", name,
            "--port", str(port)
        ],
        cwd=str(PROJECT_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    processes[name] = process
    print(f"{name} started on port {port}")


def check_service(service):

    name = service["name"]
    url = f'http://127.0.0.1:{service["port"]}/health'

    start_time = time.perf_counter()

    try:
        req = urllib.request.Request(url)

        with urllib.request.urlopen(req, timeout=2) as response:

            elapsed = (
                time.perf_counter() - start_time
            ) * 1000

            response_times[name] = round(elapsed, 2)

            return response.status == 200

    except Exception:
        response_times[name] = None
        return False


def start_all_services():

    for service in SERVICES:
        start_service(service)

    time.sleep(2)


def monitor_and_recover():

    while True:

        for service in SERVICES:

            name = service["name"]

            if check_service(service):

                service_status[name] = "healthy"
                print(f"{name}: healthy")

            else:

                print(f"{name}: FAILED!")
                service_status[name] = "recovering"

                recovery_count[name] += 1

                print(f"Recovering {name}...")

                old_process = processes.get(name)

                if old_process and old_process.poll() is None:

                    old_process.terminate()

                    try:
                        old_process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        old_process.kill()
                        old_process.wait()

                start_service(service)

                time.sleep(1.5)

                if check_service(service):

                    service_status[name] = "healthy"
                    print(f"{name}: RECOVERED!")

                    log_recovery(
                        name, service["port"], "RECOVERED"
                    )

                else:

                    service_status[name] = "failed"
                    print(f"{name}: Recovery unsuccessful")

                    log_recovery(
                        name, service["port"], "FAILED"
                    )

        print("-" * 40)
        time.sleep(3)


@app.route("/api/status")
def get_status():

    return jsonify({
        "total_services": len(SERVICES),

        "services": [
            {
                "name": s["name"],
                "port": s["port"],
                "status": service_status.get(
                    s["name"], "starting"
                ),
                "recoveries": recovery_count[s["name"]],
                "response_time": response_times[s["name"]]
            }
            for s in SERVICES
        ]
    })


def get_recovery_analytics():

    with history_lock:

        if not LOG_FILE.exists():
            history = []
        else:
            with open(LOG_FILE, "r", newline="") as file:
                history = list(csv.DictReader(file))

    total = len(history)

    successful = sum(
        1 for event in history
        if event["Result"] == "RECOVERED"
    )

    failed = sum(
        1 for event in history
        if event["Result"] == "FAILED"
    )

    success_rate = (
        round((successful / total) * 100, 2)
        if total > 0 else 0
    )

    return {
        "total_attempts": total,
        "successful": successful,
        "failed": failed,
        "success_rate": success_rate
    }


@app.route("/api/analytics")
def recovery_analytics():
    return jsonify(get_recovery_analytics())


# GET: Show activity logs
# DELETE: Permanently delete one selected activity log

@app.route("/api/history", methods=["GET", "DELETE"])
def get_history():

    if request.method == "GET":

        with history_lock:
            if not LOG_FILE.exists():
                return jsonify([])

            with open(LOG_FILE, "r", newline="") as file:
                records = list(csv.DictReader(file))

        for record in records:
            record["id"] = get_record_id(record)

        return jsonify(records)

    data = request.get_json(silent=True) or {}
    record_id = data.get("id")

    if not record_id:
        return jsonify({"error": "Missing record ID"}), 400

    with history_lock:

        if not LOG_FILE.exists():
            return jsonify({"error": "History file not found"}), 404

        with open(LOG_FILE, "r", newline="") as file:
            reader = csv.DictReader(file)
            fields = reader.fieldnames
            records = list(reader)

        selected_index = next(
            (
                i for i, record in enumerate(records)
                if get_record_id(record) == record_id
            ),
            None
        )

        if selected_index is None:
            return jsonify({"error": "Record not found"}), 404

        # Delete ONLY the selected record
        records.pop(selected_index)

        with open(LOG_FILE, "w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fields)
            writer.writeheader()
            writer.writerows(records)

    return jsonify({"success": True})




@app.route("/")
def home():

    return jsonify({
        "message": "Automatic Recovery System is running!"
    })


if __name__ == "__main__":

    print("Starting Automatic Recovery System...")

    start_all_services()

    monitor_thread = threading.Thread(
        target=monitor_and_recover,
        daemon=True
    )

    monitor_thread.start()

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False,
        use_reloader=False
    )