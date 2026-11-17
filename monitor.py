from flask import Flask, jsonify
import urllib.request
import urllib.error
import threading
import time

from datetime import datetime

app = Flask(__name__)


# Details of our independent services
SERVICES = [
    {"name": "Service-1", "url": "http://127.0.0.1:5001/health"},
    {"name": "Service-2", "url": "http://127.0.0.1:5002/health"},
    {"name": "Service-3", "url": "http://127.0.0.1:5003/health"}
]

# Store the latest service status
service_status = {}

def check_service(service):
    try:
        request = urllib.request.Request(
            service["url"],
            headers={"User-Agent": "Service-Monitor"}
        )

        with urllib.request.urlopen(request, timeout=2) as response:
            return {
                "name": service["name"],
                "status": "healthy",
                "details": "Service is responding"
            }

    except Exception:
        return {
            "name": service["name"],
            "status": "failed",
            "details": "Service is not responding"
        }


def monitor_services():
    global service_status

    while True:
        for service in SERVICES:
            result = check_service(service)
            service_status[service["name"]] = result

            print(
                f'{result["name"]}: {result["status"]}'
            )

        print("-" * 40)
        time.sleep(3)


@app.route("/")
def home():
    return jsonify({
        "message": "Central Monitoring System is running!"
    })


@app.route("/api/status")
def get_status():
    return jsonify({
        "timestamp": datetime.now().isoformat(),
        "total_services": len(service_status),
        "services": list(service_status.values())
    })


if __name__ == "__main__":

    monitor_thread = threading.Thread(
        target=monitor_services,
        daemon=True
    )

    monitor_thread.start()

    print("Central Monitoring System Started!")

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False,
        use_reloader=False
    )