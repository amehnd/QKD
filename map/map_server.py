from flask import Flask, render_template, request
import json
import os

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("map.html")


@app.route("/save", methods=["POST"])
def save():

    data = request.json

    os.makedirs("map", exist_ok=True)

    with open("map/selected_coordinates.json", "w") as f:
        json.dump(data, f, indent=4)

    return {"status": "saved"}


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5050, debug=True, use_reloader=False)
