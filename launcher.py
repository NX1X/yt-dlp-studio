"""
YT-DLP Studio Launcher

Main entry point for the application.

Usage:
    python launcher.py
"""

import sys
from pathlib import Path

# Add src directory to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from src.app import App
from src.utils.logger import get_logger

logger = get_logger()


def main():
    """
    Main entry point.

    Creates and runs the application.
    """
    try:
        # Create app
        app = App()

        # Run and get exit code
        exit_code = app.run()

        logger.info(f"Application exited with code {exit_code}")
        sys.exit(exit_code)

    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        print(f"FATAL ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
