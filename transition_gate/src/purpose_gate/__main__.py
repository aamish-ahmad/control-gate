"""Usage: PYTHONPATH=src python -m purpose_gate examples/ambiguous_goal.json"""
import json
import sys
from .engine import decide


def main() -> int:
    if len(sys.argv) != 2:
        print('Usage: python -m purpose_gate INPUT.json', file=sys.stderr)
        return 2
    try:
        with open(sys.argv[1], encoding='utf-8') as handle:
            raw = json.load(handle)
        print(json.dumps(decide(raw).as_dict(), indent=2))
        return 0
    except (ValueError, OSError, TypeError, OverflowError) as exc:
        print(f'Invalid input: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
