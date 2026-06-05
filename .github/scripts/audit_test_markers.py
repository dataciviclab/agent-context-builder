#!/usr/bin/env python3
"""Backward-compatibility shim — delegates to ``lab_connectors.testing.audit_markers``."""
import sys
try:
    from lab_connectors.testing.audit_markers import main
except ImportError:
    print("ERROR: lab-connectors not installed.\n\nInstall: pip install lab-connectors", file=sys.stderr)
    sys.exit(2)
if __name__ == "__main__":
    raise SystemExit(main())
