#!/usr/bin/env python3
"""Detect people in an input image.

Command-line entry point that accepts an image path and runs people
detection on it. The detection backend is intentionally pluggable: wire a
real model into ``detect_people`` to return bounding boxes. Until a backend
is configured the command reports that detection is unavailable rather than
silently returning zero people.

Usage:
    python detect_people.py --image path/to/photo.jpg
    python detect_people.py --image path/to/photo.jpg --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


class DetectionUnavailableError(RuntimeError):
    """Raised when no people-detection backend has been configured."""


def detect_people(image_path: Path) -> list[dict[str, int]]:
    """Return detected people as a list of bounding boxes for ``image_path``.

    Each box is a dict with ``x``, ``y``, ``width`` and ``height`` keys.
    This is a scaffold: integrate a detection model (e.g. an object-detection
    API or a local model) here and return its results.
    """
    raise DetectionUnavailableError(
        "No people-detection backend is configured. "
        "Implement detect_people() to wire in a model."
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Detect people in an input image.",
    )
    parser.add_argument(
        "-i",
        "--image",
        required=True,
        type=Path,
        help="Path to the input image to analyze.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Emit the result as JSON.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if not args.image.exists():
        print(f"error: image not found: {args.image}", file=sys.stderr)
        return 2

    try:
        people = detect_people(args.image)
    except DetectionUnavailableError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3

    if args.as_json:
        print(json.dumps({"image": str(args.image), "people": people}, indent=2))
    else:
        print(f"Detected {len(people)} person(s) in {args.image}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
