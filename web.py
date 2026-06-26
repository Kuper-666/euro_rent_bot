import os
from flask import Flask

app = Flask(__name__)

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")


def _load(name):
    path = os.path.join(TEMPLATES_DIR, name)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


@app.route("/")
def home():
    return _load("home.html"), 200


@app.route("/b2b")
def b2b():
    return _load("b2b.html"), 200
