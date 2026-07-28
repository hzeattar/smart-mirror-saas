from __future__ import annotations

import argparse
from pathlib import Path

from rembg import remove


def main(input_path: Path, output_path: Path) -> None:
    if not input_path.exists():
        raise FileNotFoundError(input_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(remove(input_path.read_bytes()))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Remove a garment image background with rembg.")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    main(args.input, args.output)
