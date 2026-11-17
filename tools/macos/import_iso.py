#!/usr/bin/env python3
"""Import a user-owned original PC disc without executing its Windows installer."""
import argparse
import json
import pathlib
import sys
from check_game import inspect
from iso_import import import_disc

root = pathlib.Path(__file__).resolve().parents[2]
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('iso', type=pathlib.Path)
    parser.add_argument('--destination', type=pathlib.Path, default=root/'work/imported-disc')
    args = parser.parse_args()
    try:
        game = import_disc(args.iso.expanduser().resolve(), args.destination.expanduser().resolve(), root/'third_party/unshield')
        result = inspect(game)
        print(json.dumps(result, indent=2))
        sys.exit(0 if result['supported'] else 2)
    except (ValueError, OSError) as e:
        sys.exit(str(e))
