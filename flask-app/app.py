import os
from flask import Flask

app = Flask(__name__)


@app.route("/", methods=["GET"])
def hello_world():
    name = os.environ.get("MSG_NAME", "Azure Kubernetes")
    print(f"debug_mode: ENV VAR - {name}")
    return f"Hello, World - {name}"


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
