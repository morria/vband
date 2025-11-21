"""Allow vband to be executed as a module with python -m vband."""

import sys
from .cli import main

if __name__ == "__main__":
    sys.exit(main())
