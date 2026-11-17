from flask import Flask, jsonify
import argparse
import time

app = Flask(__name__)

start_time = time.time()

@app.route("/")
def home():
    return jsonify({
        "message": "Distributed Service is running!"
    })

@app.route("/health")
def health():
    return jsonify({
        "service": SERVICE_NAME,
        "status": "healthy",
        "uptime": round(time.time() - start_time, 2)
    })

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", default="Service-1")
    parser.add_argument("--port", type=int, default=5001)
    args = parser.parse_args()

    SERVICE_NAME = args.name

    print(f"{SERVICE_NAME} starting on port {args.port}")

    app.run(
        host="127.0.0.1",
        port=args.port,
        debug=False,
        use_reloader=False
    )
    