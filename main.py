"""Progress Claw OS runtime entry point."""

import os

from dashboard.backend.app import app, start_background_workers


def main() -> None:
    start_background_workers()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)


if __name__ == "__main__":
    main()
