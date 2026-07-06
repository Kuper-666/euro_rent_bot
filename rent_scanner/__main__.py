import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import dns_fix  # noqa: F401 — патч DNS для Windows (запускается как отдельный процесс)

from .app import cli
if __name__ == "__main__":
    cli()
