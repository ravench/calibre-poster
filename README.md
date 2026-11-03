# Calibre poster

«Kaliber im Vergleich» / «Calibre Comparison»: a wall poster with every cartridge of the
[shared calibre data](https://github.com/ravench/calibre-data), from the diabolo pellet to
the .50 BMG, sorted by group, bullet diameter and length.

| | German | English |
|---|---|---|
| A1, scale 1:1 | [PDF](de/kaliber-poster-A1.pdf) · [SVG](de/kaliber-poster-A1.svg) · [preview](de/kaliber-poster-A1-vorschau.png) | [PDF](en/calibre-poster-A1.pdf) · [SVG](en/calibre-poster-A1.svg) · [preview](en/calibre-poster-A1-preview.png) |
| A3, scale 1:2 | [PDF](de/kaliber-poster-A3.pdf) · [SVG](de/kaliber-poster-A3.svg) · [preview](de/kaliber-poster-A3-vorschau.png) | [PDF](en/calibre-poster-A3.pdf) · [SVG](en/calibre-poster-A3.svg) · [preview](en/calibre-poster-A3-preview.png) |

Print without scaling (100 %). On A1 the cartridges are shown at actual size; the scale bar at
the top right lets you check. Cartridges with identical measurements (.308 Win / 7.62 NATO,
.223 Rem / 5.56 NATO / GP 90) are drawn once with all their names. Dimensions are rounded
per CIP/SAAMI and bullet shapes are schematic; this is not load data.

## Building

```sh
git submodule update --init          # the calibre data in calibre-data/
python3 build.py                     # all SVG versions
python3 build.py --render            # also PDF and PNG previews (Node + Playwright with Chromium)
python3 -m unittest discover -s tests
```

`poster.py` draws one version (`python3 poster.py OUT_DIR --size A1 --scale 1 --lang de`).
To use newer calibre data, update the submodule (`git -C calibre-data pull origin main`),
run `python3 build.py --render` and commit both. CI fails when the committed SVGs are out of
date.

## Licence

- The poster (`de/`, `en/`): [CC BY-NC 4.0](LICENSE-POSTER.md),
  © 2026 Simon Giotta. Share, print and adapt it with credit, not commercially.
- The code (`poster.py`, `build.py`, `render.js`, `tests/`): [PolyForm Noncommercial 1.0.0](LICENSE.md). Contributions need the
  [Contributor License Agreement](CLA.md).
