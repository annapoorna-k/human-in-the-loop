from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from hitl_refund.cli import main  # noqa: E402
from hitl_refund.logging_config import configure_logging  # noqa: E402


if __name__ == "__main__":
    configure_logging()
    main()
