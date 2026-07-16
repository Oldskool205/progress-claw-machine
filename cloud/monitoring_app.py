"""Standalone diagnostic-only Cloud Monitoring application."""

from pathlib import Path

from flask import Flask, redirect

from cloud.routes import bp as cloud_bp
from services.logging.structured import configure_logging


configure_logging()
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
app = Flask(
    __name__,
    template_folder=str(
        _PROJECT_ROOT / "dashboard" / "frontend" / "templates"
    ),
)
app.register_blueprint(cloud_bp)


@app.route("/", methods=["GET"])
def root():
    return redirect("/cloud")
