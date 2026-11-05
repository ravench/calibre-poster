#!/usr/bin/env python3
"""Builds every published version of the poster into de/ and en/.

    python3 build.py            # SVG files only
    python3 build.py --render   # also PDF and PNG previews (needs Node and Playwright with Chromium)
"""
import os, subprocess, sys, tempfile

import poster

ROOT = os.path.dirname(os.path.abspath(__file__))
# (language, size, edition, file stem, preview suffix). All at 1:1. "fit": the most-listed calibres that
# fit the page (the full catalogue does not fit any single sheet); "swiss": the Swiss service cartridges.
VERSIONS = [(lang, size, "fit", f"{stem}-{size}", suffix)
            for lang, stem, suffix in (("de", "kaliber-poster", "vorschau"), ("en", "calibre-poster", "preview"))
            for size in ("A0", "A1", "A2", "A3")] + [
    ("en", size, "fit", f"calibre-poster-{size}", "preview") for size in ("24x36in", "18x24in", "11x17in", "Letter")] + [
    ("de", "A3-quer", "swiss", "schweizer-armee-A3", "vorschau"),
    ("en", "A3-quer", "swiss", "swiss-army-A3", "preview"),
]
PREVIEW_WIDTH = 1600  # px


def version(lang, size, edition):
    if edition == "swiss":
        return poster.build(size, 1.0, lang, swiss=True)
    return poster.build(size, 1.0, lang, names=set(poster.most_that_fit(size, lang)))


def build(render=False):
    for lang, size, edition, stem, suffix in VERSIONS:
        svg, (w, h), over, _ = version(lang, size, edition)
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
        print(f"{lang}/{stem}: {size}, {edition}")


if __name__ == "__main__":
    build("--render" in sys.argv)
