"""Progress Claw OS runtime entry point."""

import os
import threading

from dashboard.backend.app import add_event, app, camera_worker, initialize_start_output


def main() -> None:
    add_event("Progress Claw OS runtime started")
    initialize_start_output()
    threading.Thread(target=camera_worker, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)


if __name__ == "__main__":
    main()
