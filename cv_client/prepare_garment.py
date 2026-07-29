from __future__ import annotations

import argparse
from pathlib import Path

from smart_mirror.garment_assets import SUPPORTED_CATEGORIES, prepare_garment_asset


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(
        description="Prepare a real store garment photo as a transparent Smart Mirror texture."
    )
    command.add_argument("source", type=Path, help="Front-facing source photograph")
    command.add_argument("output", type=Path, help="Output transparent PNG path")
    command.add_argument("--category", required=True, choices=sorted(SUPPORTED_CATEGORIES))
    command.add_argument("--canvas", type=int, default=1024, help="Square output canvas size")
    return command


if __name__ == "__main__":
    args = parser().parse_args()
    metadata = prepare_garment_asset(
        args.source,
        args.output,
        args.category,
        canvas_size=(args.canvas, args.canvas),
    )
    print(f"Prepared: {args.output}")
    print(f"Category: {metadata.category}")
    print(f"Background: {metadata.background_method}")
    print(f"Content: {metadata.content_width} x {metadata.content_height}")
    print(f"Alpha coverage: {metadata.alpha_coverage:.1%}")
    print(f"Metadata: {args.output.with_suffix(args.output.suffix + '.json')}")
