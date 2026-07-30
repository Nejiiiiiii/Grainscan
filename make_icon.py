"""Convert GUI/logo4.png into a Windows multi-resolution icon (GUI/logo4.ico).

PyInstaller and Inno Setup both require .ico format on Windows. We center the
non-square logo on a transparent square canvas so the icon doesn't get
squashed at small sizes, then bake every standard Windows icon size into a
single .ico file.
"""

from __future__ import annotations

import os
import sys
from PIL import Image


def main() -> int:
    root = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(root, "GUI", "logo4.png")
    dst = os.path.join(root, "GUI", "logo4.ico")

    if not os.path.isfile(src):
        print(f"ERROR: source image not found: {src}", file=sys.stderr)
        return 1

    img = Image.open(src).convert("RGBA")

    side = max(img.size)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    x = (side - img.size[0]) // 2
    y = (side - img.size[1]) // 2
    canvas.paste(img, (x, y), img)

    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    canvas.save(dst, format="ICO", sizes=sizes)

    print(f"Wrote {dst}")
    print(f"  Source : {img.size[0]}x{img.size[1]} (RGBA)")
    print(f"  Padded : {side}x{side}")
    print(f"  Embedded sizes: {', '.join(f'{w}x{h}' for w, h in sizes)}")
    print(f"  File size: {os.path.getsize(dst):,} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
