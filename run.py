import os

from backend.app import app


if __name__ == "__main__":
    debug = os.getenv("TRANSITGRAPH_DEBUG", "").lower() in {
        "1", "true", "yes"
    }
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=debug
    )
