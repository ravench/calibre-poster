#!/usr/bin/env python3
"""Builds every published version of the poster into de/ and en/.

    python3 build.py            # SVG files only
    python3 build.py --render   # also PDF and PNG previews (needs Node and Playwright with Chromium)
"""
import os, subprocess, sys, tempfile

import poster

ROOT = os.path.dirname(os.path.abspath(__file__))
# (language, size, scale, file stem, preview suffix)
VERSIONS = [
    ("de", "A1", 1.0, "kaliber-poster-A1", "vorschau"),
    ("de", "A3", 0.5, "kaliber-poster-A3", "vorschau"),
    ("en", "A1", 1.0, "calibre-poster-A1", "preview"),
    ("en", "A3", 0.5, "calibre-poster-A3", "preview"),
]
PREVIEW_WIDTH = 1600  # px


def build(render=False):
    for lang, size, k, stem, suffix in VERSIONS:
        svg, (w, h), over, _ = poster.build(size, k, lang)
        assert over <= 2.0, f"{stem}: content runs {over:.1f} mm into the footer"
        out = os.path.join(ROOT, lang)
        os.makedirs(out, exist_ok=True)
        with open(os.path.join(out, stem + ".svg"), "w") as f:
            f.write(svg)
        if render:
            with tempfile.TemporaryDirectory() as tmp:
                page = os.path.join(tmp, "poster.html")
                with open(page, "w") as f:
                    f.write(f"<!doctype html><meta charset=utf-8><style>@page{{size:{w}mm {h}mm;margin:0}}"
                            f"html,body{{margin:0}}svg{{display:block}}</style>{svg}")
                scale = PREVIEW_WIDTH / (w * 96 / 25.4)
                subprocess.run(["node", os.path.join(ROOT, "render.js"), page,
                                os.path.join(out, f"{stem}-{suffix}.png"), os.path.join(out, stem + ".pdf"),
                                str(w), str(h), f"{scale:.4f}"], check=True)
        print(f"{lang}/{stem}: {size} 1:{1 / k:g}")


if __name__ == "__main__":
    build("--render" in sys.argv)
