# Calibre poster

«Kaliber im Vergleich» / «Calibre Comparison»: wall posters of the cartridges in the
[shared calibre data](https://github.com/ravench/calibre-data), every one at actual size (1:1),
sorted by group, then by length and, at equal length, by bullet diameter.

The catalogue (411 calibres) no longer fits on one sheet at 1:1, so each size shows the calibres
listed for sale most often that fit on it ([listing-share.json](listing-share.json): share of listings on the big gun
marketplaces, counted 2026-11-04).

| | German | English |
|---|---|---|
| A0, about 285 calibres | [PDF](de/kaliber-poster-A0.pdf) · [SVG](de/kaliber-poster-A0.svg) · [preview](de/kaliber-poster-A0-vorschau.png) | [PDF](en/calibre-poster-A0.pdf) · [SVG](en/calibre-poster-A0.svg) · [preview](en/calibre-poster-A0-preview.png) |
| A1, about 130 | [PDF](de/kaliber-poster-A1.pdf) · [SVG](de/kaliber-poster-A1.svg) · [preview](de/kaliber-poster-A1-vorschau.png) | [PDF](en/calibre-poster-A1.pdf) · [SVG](en/calibre-poster-A1.svg) · [preview](en/calibre-poster-A1-preview.png) |
| A2, about 75 | [PDF](de/kaliber-poster-A2.pdf) · [SVG](de/kaliber-poster-A2.svg) · [preview](de/kaliber-poster-A2-vorschau.png) | [PDF](en/calibre-poster-A2.pdf) · [SVG](en/calibre-poster-A2.svg) · [preview](en/calibre-poster-A2-preview.png) |
| A3, about 50 | [PDF](de/kaliber-poster-A3.pdf) · [SVG](de/kaliber-poster-A3.svg) · [preview](de/kaliber-poster-A3-vorschau.png) | [PDF](en/calibre-poster-A3.pdf) · [SVG](en/calibre-poster-A3.svg) · [preview](en/calibre-poster-A3-preview.png) |
| US sizes: 24 × 36 in, 18 × 24 in, 11 × 17 in, Letter (about 155, 95, 55, 22) | | [24x36in](en/calibre-poster-24x36in.pdf) · [18x24in](en/calibre-poster-18x24in.pdf) · [11x17in](en/calibre-poster-11x17in.pdf) · [Letter](en/calibre-poster-Letter.pdf) |
| Swiss service cartridges since 1867, A3 landscape | [PDF](de/schweizer-armee-A3.pdf) · [SVG](de/schweizer-armee-A3.svg) · [preview](de/schweizer-armee-A3-vorschau.png) | [PDF](en/swiss-army-A3.pdf) · [SVG](en/swiss-army-A3.svg) · [preview](en/swiss-army-A3-preview.png) |

Print without scaling (100 %); the scale bar at the top lets you check. Cartridges with identical
measurements (.308 Win / 7.62 NATO, .223 Rem / 5.56 NATO / GP 90) are drawn once
with all their names. Bullet and case materials (lead, soft point, polymer tip, steel, nickel and copper
cases) come from the calibre data. Dimensions are rounded per CIP/SAAMI and bullet shapes are schematic;
this is not load data. The Swiss poster uses a Swiss designation (Pist Pat 03, Pist Pat 41, GP 1890,
GP 11, GP 90) only where a source gives one.

## Building

```sh
git lfs install                      # the PDFs and PNG previews are stored with Git LFS
git submodule update --init          # the calibre data in calibre-data/
python3 build.py                     # all SVG versions
python3 build.py --render            # also PDF and PNG previews (Node + Playwright with Chromium)
python3 -m unittest discover -s tests
```

Python 3.11 or newer reads the calibre data (one TOML file per calibre).
`poster.py` draws one version (`python3 poster.py OUT_DIR --size A1 --lang de --fit`, or `--swiss`); `build.py` lists the published ones.
To use newer calibre data, update the submodule (`git -C calibre-data pull origin main`),
run `python3 build.py --render` and commit both. CI fails when the committed SVGs are out of
date.

## Licence

- The poster (`de/`, `en/`): [CC BY-NC 4.0](LICENSE-POSTER.md),
  © 2026 Simon Giotta. Share, print and adapt it with credit, not commercially.
- The code (`poster.py`, `build.py`, `render.js`, `tests/`): [PolyForm Noncommercial 1.0.0](LICENSE.md). Contributions need the
  [Contributor License Agreement](CLA.md).
