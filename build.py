#!/usr/bin/env python3
"""Builds every published version of the poster into de/ and en/.

    python3 build.py            # SVG files only
    python3 build.py --render   # also PDFs (needs Node and Playwright with Chromium)
"""
import os, subprocess, sys, tempfile

import poster

ROOT = os.path.dirname(os.path.abspath(__file__))
# (language, size, edition, file stem). All at 1:1. "fit": the most-listed calibres that
# fit the page (the full catalogue does not fit any single sheet); "swiss": the Swiss service cartridges;
# "cat:<category>": every calibre of one category, on the smallest sheet that holds it (poster.smallest_sheet).
VERSIONS = [(lang, size, "fit", f"{stem}-{size}")
            for lang, stem in (("de", "kaliber-poster"), ("en", "calibre-poster"))
            for size in ("A0", "A1", "A2", "A3")] + [
    ("en", size, "fit", f"calibre-poster-{size}") for size in ("24x36in", "18x24in", "11x17in", "Letter")] + [
    ("de", "A3-quer", "swiss", "schweizer-armee-A3"),
    ("en", "A3-quer", "swiss", "swiss-army-A3"),
]


def category_versions():
    out = []
    for cat, t in poster.CATEGORY_TITLES.items():
        for lang, stem, sheets in (("de", "kaliber-poster", poster.METRIC_SHEETS), ("en", "calibre-poster", poster.METRIC_SHEETS),
                                   ("en", "calibre-poster", poster.US_SHEETS)):
            size = poster.smallest_sheet(cat, lang, sheets)
            if size:
                out.append((lang, size, "cat:" + cat, f"{stem}-{t['stem_' + lang]}-{size.split('-')[0]}"))
    return out


VERSIONS += category_versions()


def version(lang, size, edition):
    title = None
    if edition.startswith("cat:"):
        cat = edition[4:]
        names, title = poster.category_names(cat), poster.CATEGORY_TITLES[cat][lang]
    else:
        names = None if edition == "swiss" else set(poster.most_that_fit(size, lang))
    built = poster.build(size, 1.0, lang, names=names, swiss=edition == "swiss" or None, title=title)
    assert built[2] <= poster.OVERRUN, f"{lang} {size} {edition}: content runs {built[2]:.1f} mm into the footer"
    return built


def build(render=False):
    for lang, size, edition, stem in VERSIONS:
        svg, (w, h), _, _ = version(lang, size, edition)
        out = os.path.join(ROOT, lang)
        os.makedirs(out, exist_ok=True)
        with open(os.path.join(out, stem + ".svg"), "w") as f:
            f.write(svg)
        if render:
            with tempfile.TemporaryDirectory() as tmp:
                page = os.path.join(tmp, "poster.html")
                with open(page, "w") as f:
                    f.write(poster.page_html(svg))
                subprocess.run(["node", os.path.join(ROOT, "render.js"), page, os.path.join(out, stem + ".pdf"),
                                str(w), str(h)], check=True)
        print(f"{lang}/{stem}: {size}, {edition}")


if __name__ == "__main__":
    build("--render" in sys.argv)
