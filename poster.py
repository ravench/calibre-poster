#!/usr/bin/env python3
"""Calibre comparison wall poster ("Kaliber im Vergleich"), drawn from the shared calibre data.

    python3 poster.py OUT_DIR [--size A1|A3|...] [--scale 1.0|0.5] [--lang de|en] [--fit | --swiss]

Writes poster.svg (units = mm) and poster.html (for PDF rendering). build.py makes all
published versions. --fit draws the most-listed calibres that fit the page; --swiss the Swiss
service edition. Cartridges with identical measurements are drawn once with all names.
"""
import os, re, sys, html
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "calibre-data"))
from cartridges import CATALOGUE, SHOT, BALL, MINIE, PELLET  # noqa: E402
from outline import outline  # noqa: E402

SIZES = {"A0": (841, 1189), "A1": (594, 841), "A2": (420, 594), "A3": (297, 420), "A4": (210, 297),
         "B1": (700, 1000), "24x36in": (610, 914), "18x24in": (457, 610), "11x17in": (279, 432), "Letter": (216, 279),
         "A0-hoch": (841, 1250), "A3-quer": (420, 297)}

LANG = "de"
FS = 0.58
SUB_GAP = 12  # title baseline to subtitle baseline, in typography units (mm at A1 size)
TEXT = {
    "de": dict(
        cats={"Luftdruck": "Luftdruck", "Randfeuer": "Randfeuer", "Kurzwaffe": "Kurzwaffen", "Langwaffe": "Langwaffen",
              "SP_Geschoss": "Schwarzpulver · Kugeln & Minié", "SP_Patrone": "Schwarzpulver · Patronen", "Flinte": "Flinte"},
        cont=" (Forts.)", title="Kaliber im Vergleich",
        sub="{n} Patronen und Geschosse · {scale}",
        actual="Originalgrösse (Massstab 1:1)", scaled="Massstab 1:{d}",
        note1="Druck ohne Skalierung (100 %) auf {size}: Patronen in Originalgrösse. ",
        noteK="Druck ohne Skalierung (100 %) auf {size}: Massstab 1:{d}. ",
        note2="Masse gerundet nach CIP/SAAMI, Geschossform schematisch. Keine Ladedaten.",
        lic="© 2026 Simon Giotta · Lizenz CC BY-NC 4.0 · creativecommons.org/licenses/by-nc/4.0",
        same="gleiche Masse",
        swiss_title="Ordonnanzpatronen der Schweizer Armee", swiss_sub="{n} Patronen von 1867 bis heute · {scale}", swiss_cat="Seit 1867",
        names={}),
    "en": dict(
        cats={"Luftdruck": "Airgun", "Randfeuer": "Rimfire", "Kurzwaffe": "Handgun", "Langwaffe": "Rifle",
              "SP_Geschoss": "Black powder · balls & Minié", "SP_Patrone": "Black powder · cartridges", "Flinte": "Shotgun"},
        cont=" (cont.)", title="Calibre Comparison",
        sub="{n} cartridges and projectiles · {scale}",
        actual="Actual size (scale 1:1)", scaled="Scale 1:{d}",
        note1="Print without scaling (100 %) on {size}: cartridges at actual size. ",
        noteK="Print without scaling (100 %) on {size}: scale 1:{d}. ",
        note2="Dimensions rounded per CIP/SAAMI, bullet shapes schematic. Not load data.",
        lic="© 2026 Simon Giotta · Licence CC BY-NC 4.0 · creativecommons.org/licenses/by-nc/4.0",
        same="identical dimensions",
        names={"Rundkugel": "Round Ball", "Browning kurz": "Browning Short", "11,43 mm": "11.43 mm",
               "12,7x99": "12.7x99", "Gewehrpatrone 1890": "Swiss cartridge 1890", "Randfeuer": "rimfire", "Zentralfeuer": "centrefire",
               "Milbank-Amsler-Gewehr": "Milbank-Amsler rifle", "Gewehr 1889": "Rifle 1889", "Pistole": "Pistol",
               "Mehrzweckgewehr": "Multi-purpose gun"},
        swiss_title="Swiss Army Service Cartridges", swiss_sub="{n} cartridges from 1867 to today · {scale}", swiss_cat="Since 1867"),
}


def tr(text):
    for a, b in TEXT[LANG]["names"].items():
        text = text.replace(a, b)
    return text

ORDER = ["Luftdruck", "Randfeuer", "Kurzwaffe", "Langwaffe", "Flinte", "Schwarzpulver"]

INK, MUTED, PAPER, RULE = "#1d1b18", "#6f675c", "#f6f1e7", "#cfc5b3"
FONT = "Inter, 'Helvetica Neue', Arial, sans-serif"


def fmt(x):
    d = "," if LANG == "de" else "."
    s = f"{x:.1f}"
    return s[:-2] if s.endswith(".0") else s.replace(".", d)


from cartridges import DISPLAY_ALIASES  # single source, shared with the app
# Poster-only additions as (category, spec). GP 1890 used to be one; it is now in the app catalogue
# (Langwaffe, smokeless) with its paper-patched, steel-capped bullet.
EXTRA = []
MERGED = set()  # names to leave out of the poster

# Swiss service edition: every small-arms cartridge the Swiss army adopted, oldest first.
# The Swiss name is used only where a source gives it (Pist Pat 03/41: de.wikipedia «7,65 x 21 mm Luger»,
# sigforum Pist Pat 41 box; GP 11 / GP 90 / GP 1890 as in the calibre data); otherwise the usual name.
SWISS_SERVICE = [  # (catalogue name, Swiss name, international name, year adopted, weapons); Swiss name only where sourced
    ("18 mm Milbank-Amsler", "18 mm Milbank-Amsler", "", 1867, "Milbank-Amsler-Gewehr"),
    ("10.4x38 mm R Vetterli", "10,4x38 R Vetterli", "", 1867, "Peabody 1867, Vetterli 1869"),
    ("10.4 mm Swiss Ordnance 1872 Rimfire", "10,4 mm Randfeuer", "", 1872, "Revolver 1872"),
    ("10.4 mm Swiss Ordnance 1878", "10,4 mm Zentralfeuer", "", 1878, "Revolver 1872/78"),
    ("7.5 mm Swiss Ordnance 1882", "7,5x23 R", "", 1882, "Revolver 1882"),
    ("7.5x53.5 mm Swiss (GP 1890)", "GP 1890", "7,5x53,5", 1889, "Gewehr 1889"),
    ("7.65 mm Parabellum", "Pist Pat 03", "7,65 mm Parabellum", 1900, "Pistole 1900, 1906, 06/29"),
    ("7.5x55 mm Swiss (GP 11)", "GP 11", "7,5x55", 1911, "K11, K31, Lmg 25, Mg 51, Stgw 57"),
    ("9x19 mm", "Pist Pat 41", "9 mm Parabellum", 1941, "Pistole 49, Pistole 75, Mp 14"),
    ("12/70", "12/70", "", "", "Mehrzweckgewehr"),
    (".50 BMG", ".50 BMG", "12,7x99 NATO", "", "Mg 64, PSG 04"),
    ("5.6 mm GP 90", "GP 90", "5,56x45 NATO", 1990, "Stgw 90, Lmg 05"),
    (".338 Lapua Magnum", ".338 Lapua Magnum", "8,6x70", 2004, "SSGw 04, SSGw 18"),
    ("7.62x51 mm NATO", "7,62x51 NATO", "", 2012, "Zf Stgw 12"),
    ("6.5 mm Creedmoor", "6,5 mm Creedmoor", "", 2020, "Zf Stgw 20")]

SHARE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "listing-share.json")


def ranked():
    """All calibre names, most listed for sale first (listing-share.json); unlisted ones last, obsolete after current."""
    import json
    from cartridges import OBSOLETE
    share = json.load(open(SHARE_FILE))["share"]
    names = [s["name"] for _, v in CATALOGUE for s in v]
    return sorted(names, key=lambda n: (-share.get(n, 0), n in OBSOLETE, n))


def most_that_fit(size, lang="de", pool=None):
    """The longest prefix of the ranking that fits on the page at 1:1."""
    pool = pool or ranked()
    fits = lambda n: build(size, 1.0, lang, names=set(pool[:n]))[2] <= 0
    lo, hi = 0, len(pool)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if fits(mid):
            lo = mid
        else:
            hi = mid - 1
    while lo and not fits(lo):
        lo -= 1
    return pool[:lo]



def wrap(words, limit, sep=" "):
    lines, cur = [], ""
    for w in words:
        if cur and len(cur) + len(sep) + len(w) > limit:
            lines.append(cur); cur = w
        else:
            cur = (cur + sep + w) if cur else w
    return lines + [cur] if cur else lines


def split_name(name):
    """Main name lines + alias lines (parenthetical part or DISPLAY_ALIASES)."""
    main, aliases = name, []
    if " (" in name:
        main, paren = name.split(" (", 1)
        aliases = [paren.rstrip(")")]
    if name in DISPLAY_ALIASES:
        if main.startswith("7.5x55"):
            main = "7.5x55 mm"
        aliases = DISPLAY_ALIASES[name]
    return wrap(tr(main).split(" "), 13), wrap([tr(a) for a in aliases], 19, " · ")


def short_name(name):
    """Main name without the parenthetical part, for a combined label."""
    return tr(name.split(" (", 1)[0])


def merge_identical(specs):
    """Specs grouped by identical outline (e.g. .308 Win / 7.62 NATO): one drawing per group,
    in the order of each group's first spec."""
    groups = []
    for s in specs:
        o = outline(s)
        shape = {k: v for k, v in o.items() if k in ("width", "height", "case", "head", "bullet")}
        for g in groups:
            if g["kind"] == s["kind"] and g["shape"] == shape:
                g["names"].append(s["name"])
                break
        else:
            groups.append({"spec": s, "kind": s["kind"], "outline": o, "shape": shape, "names": [s["name"]]})
    return groups


def label_lines(names):
    """Name lines + muted lines for one drawing; several names when the measurements are identical."""
    if len(names) == 1:
        return split_name(names[0])
    return [short_name(n) for n in names], [TEXT[LANG]["same"]]


def defs():
    def lg(id, stops):
        s = "".join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in stops)
        return f'<linearGradient id="{id}" x1="0" x2="1" y1="0" y2="0">{s}</linearGradient>'
    return "<defs>" + "".join([
        lg("brass", [(0, "#a8802f"), (0.35, "#f3dc94"), (0.55, "#e2bf63"), (1, "#9c752a")]),
        lg("copper", [(0, "#7c4019"), (0.35, "#e0a06a"), (0.55, "#c07438"), (1, "#713a17")]),
        lg("lead", [(0, "#55585c"), (0.38, "#c9cdd1"), (0.58, "#9a9fa5"), (1, "#4c4f53")]),
        lg("steel", [(0, "#5f656b"), (0.38, "#e1e5e8"), (0.58, "#aeb4ba"), (1, "#565b60")]),
        lg("paper", [(0, "#cfc8b8"), (0.38, "#fffdf7"), (0.58, "#f1ebdd"), (1, "#c6bfae")]),
        lg("nickel", [(0, "#7d8084"), (0.38, "#f2f3f4"), (0.58, "#c9ccd0"), (1, "#74777b")]),
        lg("polymer", [(0, "#8a1c1c"), (0.38, "#e8584a"), (0.58, "#c73a2e"), (1, "#7a1818")]),
        lg("hull", [(0, "#7d1d17"), (0.38, "#d9574a"), (0.58, "#b7352b"), (1, "#701a14")]),
    ]) + "</defs>"


def cartridge_svg(c, o, x, base_y, k):
    """Place outline o (mm) with its bottom-centre at (x, base_y), scaled by k."""
    w, h = o["width"], o["height"]
    tx, ty = x - w / 2 * k, base_y - h * k
    stroke = 'stroke="#3a2c18" stroke-width="{:.3f}" stroke-linejoin="round"'.format(0.14 / k)
    lead = c["kind"] in (BALL, MINIE, PELLET)
    parts = []
    case_fill = {"copper": "copper", "steel": "steel", "nickel": "nickel", "paper": "paper"}.get(o.get("caseMaterial"), "brass")
    if "case" in o:
        parts.append(f'<path d="{o["case"]}" fill="url(#{"hull" if c["kind"] == SHOT else case_fill})" {stroke}/>')
    if "head" in o:
        parts.append(f'<path d="{o["head"]}" fill="url(#{"steel" if o.get("headMaterial") == "steel" else "brass"})" {stroke}/>')
    if "bullet" in o:
        bm = o.get("bulletMaterial")
        metal = "steel" if bm == "steel" else ("lead" if lead or bm == "lead" else "copper")
        parts.append(f'<path d="{o["bullet"]}" fill="url(#{metal})" {stroke}/>')
    if "tip" in o:  # soft point (lead) or polymer tip
        parts.append(f'<path d="{o["tip"]}" fill="url(#{"polymer" if o.get("tipMaterial") == "polymer" else "lead"})" {stroke}/>')
    if "patch" in o:  # paper patch around a lead bullet (GP 1890, Gras, Martini-Henry)
        parts.append(f'<path d="{o["patch"]}" fill="url(#paper)" {stroke}/>')
    return f'<g transform="translate({tx:.3f} {ty:.3f}) scale({k})">{"".join(parts)}</g>'


def section_order(spec):
    """Order inside a section: shortest first, the thinner bullet first where the printed lengths match."""
    return (round(spec["oal"], 1), spec["bullet"])  # length as printed (0.1 mm)


def dims(c):
    o = c["outline"]
    if c["kind"] in (BALL,):
        return f"Ø {fmt(o['width'])} mm"
    return f"Ø {fmt(c['bullet'])} · {fmt(o['height'])} mm"


def build(size="A1", k=1.0, lang="de", names=None, swiss=None, title=None):
    """names: set of calibre names to draw (None = all). swiss: [(name, year, weapons)] for the Swiss service edition."""
    global LANG
    LANG = lang
    L = TEXT[lang]
    W, H = SIZES[size]
    small = W < 400
    # typography: small paper keeps text legible; big paper keeps A1-sized text so it holds more cartridges
    f = FS if small else min(1.0, max(0.8, W / 594))
    if swiss is True:
        swiss = SWISS_SERVICE
    if swiss:
        names = {s[0] for s in swiss}
        SW = {s[0]: s for s in swiss}
    M = 14 if small else 26 * f
    items = []
    by_cat = {k: list(v) for k, v in CATALOGUE}
    # Poster-only additions not (yet) in the app catalogue.
    for cat, spec in EXTRA:
        if all(x["name"] != spec["name"] for x in by_cat[cat]):
            by_cat[cat].append(spec)
    for cat in ORDER:
        specs = sorted([s for s in by_cat[cat] if s["name"] not in MERGED and (names is None or s["name"] in names)],
                       key=section_order)
        # Cartridges with identical measurements are drawn once, with all their names.
        for g in merge_identical(specs):
            s = g["spec"]
            sub = cat if cat != "Schwarzpulver" else ("SP_Geschoss" if s["kind"] in (BALL, MINIE) else "SP_Patrone")
            if swiss:
                sub = "CH"
            items.append({"cat": sub, "name": s["name"], "names": g["names"], "kind": s["kind"], "bullet": s["bullet"],
                          "oal": s["oal"], "outline": g["outline"]})
    if swiss:
        items.sort(key=lambda it: [s[0] for s in swiss].index(it["name"]))
        L = dict(L, cats=dict(L["cats"], CH=L["swiss_cat"]))

    fs_name, fs_sub, fs_dim = 2.55 * f, 2.05 * f, 1.85 * f
    lh = fs_name * 1.18
    label_h = 3 * lh + 2 * fs_sub * 1.2 + fs_dim * 1.6 + 2 * f
    if swiss:
        label_h += 4 * fs_sub * 1.2
    head_h = 9 * f
    gap_cat = 9 * f
    content_w = W - 2 * M

    def cell_w(it):
        w = max((21 if small else 24.5) * f, it["outline"]["width"] * k + 6 * f)
        if len(it["names"]) > 1:  # combined label: room for the longest name on one line
            w = max(w, max(len(n) for n in label_lines(it["names"])[0]) * fs_name * 0.56 + 2 * f)
        return w

    # Rows: flow the categories in order and break when a row is full.
    FLOW = ["Luftdruck", "Randfeuer", "Kurzwaffe", "Langwaffe", "SP_Geschoss", "SP_Patrone", "Flinte", "CH"]
    items.sort(key=lambda it: FLOW.index(it["cat"]))  # stable: keeps the order inside each category
    rows, cur, used = [], [], 0
    for it in items:
        gap = gap_cat if cur and cur[-1]["cat"] != it["cat"] else 0
        if cur and used + gap + cell_w(it) > content_w:
            rows.append(cur); cur, used, gap = [], 0, 0
        cur.append(it); used += gap + cell_w(it)
    if cur:
        rows.append(cur)
    for row in rows:
        for it in row:
            it["extra"] = 0
        i = 0
        while i < len(row):
            j = i
            while j + 1 < len(row) and row[j + 1]["cat"] == row[i]["cat"]:
                j += 1
            n = sum(len(x["names"]) for x in items if x["cat"] == row[i]["cat"])
            label_w = (len(L["cats"][row[i]["cat"]]) + len(str(n)) + 3) * 3.3 * f * 0.78 + 2
            run_w = sum(cell_w(x) for x in row[i:j + 1])
            row[j]["extra"] = max(0, label_w - run_w)
            i = j + 1
    for row in rows:
        for i, it in enumerate(row):
            it["gap_before"] = gap_cat if i and row[i - 1]["cat"] != it["cat"] else 0
        used = sum(cell_w(it) + it["extra"] + it["gap_before"] for it in row)
        # centre-justify: spread leftover width evenly across cells
        pad = (content_w - used) / len(row) if row is not rows[-1] or len(row) > 10 else 0
        for it in row:
            it["pad"] = pad

    out = []
    title_y = M + 22 * f
    T1 = title or (L["swiss_title"] if swiss else L["title"])
    out.append(f'<text x="{M}" y="{title_y:.2f}" font-size="{19 * f:.2f}" font-weight="800" letter-spacing="-0.4" fill="{INK}">{html.escape(T1)}</text>')
    out.append(f'<text x="{M}" y="{title_y + SUB_GAP * f:.2f}" font-size="{5 * f:.2f}" fill="{MUTED}">{html.escape((L["swiss_sub"] if swiss else L["sub"]).format(n=sum(len(it["names"]) for it in items), scale=L["actual"] if abs(k - 1) < 1e-6 else L["scaled"].format(d=fmt(1 / k))))}</text>')
    # scale bar 0-100 mm (true size on print)
    bx, by = W - M - 100 * k, title_y - 3 * f
    if M + len(T1) * 19 * f * 0.56 > bx - 6 * f:  # long title: scale bar moves down beside the subtitle
        sub_w = M + 60 * 5 * f * 0.5  # subtitle is about 60 characters
        by = title_y + (SUB_GAP if sub_w < bx - 4 * f else SUB_GAP + 6) * f
    out.append(f'<g font-size="{2.2 * f:.2f}" fill="{MUTED}" text-anchor="middle">')
    out.append(f'<line x1="{bx}" x2="{bx + 100 * k}" y1="{by}" y2="{by}" stroke="{INK}" stroke-width="0.35"/>')
    for mm in range(0, 101):
        t = 4 if mm % 10 == 0 else (2.6 if mm % 5 == 0 else 1.5)
        x = bx + mm * k
        out.append(f'<line x1="{x:.3f}" x2="{x:.3f}" y1="{by}" y2="{by - t * f:.3f}" stroke="{INK}" stroke-width="{0.3 if mm % 10 == 0 else 0.18}"/>')
        if mm % 10 == 0:
            out.append(f'<text x="{x:.3f}" y="{by + 3.4 * f:.3f}">{mm}</text>')
    out.append(f'<text x="{bx + 100 * k + 2 * f:.2f}" y="{by + 3.4 * f:.3f}" text-anchor="start">mm</text></g>')

    y = title_y + 22 * f
    row_layouts = []
    for row in rows:
        starts = any(i == 0 or it["cat"] != row[i - 1]["cat"] for i, it in enumerate(row)) or True
        tallest = max(it["outline"]["height"] for it in row) * k
        row_layouts.append((row, tallest))
    total = sum(head_h + t + label_h + 6 * f for _, t in row_layouts)
    avail = H - M - 16 * f - y
    spare = max(0, avail - total) / max(1, len(rows))

    for row, tallest in row_layouts:
        y += head_h + spare / 2
        base = y + tallest
        x = M
        groups = []  # (cat, x0, x1, first_in_cat)
        for i, it in enumerate(row):
            x += it["gap_before"]
            cw = cell_w(it) + it["pad"] + it["extra"]
            cx = x + cw / 2
            if not groups or groups[-1][0] != it["cat"]:
                groups.append([it["cat"], x, x + cw])
            else:
                groups[-1][2] = x + cw
            out.append(cartridge_svg(it, it["outline"], cx, base, k))
            lines, extra = label_lines(it["names"])
            if swiss:
                _, disp, intl, yr, wp = SW[it["name"]]
                if LANG == "en":
                    disp, intl, wp = (tr(re.sub(r"(\d),(\d)", r"\1.\2", t)) for t in (disp, intl, wp))
                lines = wrap(disp.split(" "), 13)
                extra = (wrap(intl.split(" "), 19) if intl else []) + ([str(yr)] if yr else []) + wrap(wp.split(" "), 19)
            ty = base + 4.3 * f
            t = [f'<text x="{cx:.2f}" y="{ty:.2f}" text-anchor="middle" font-size="{fs_name:.2f}" font-weight="600" fill="{INK}">']
            for j, ln in enumerate(lines):
                t.append(f'<tspan x="{cx:.2f}" dy="{0 if j == 0 else lh:.2f}">{html.escape(ln)}</tspan>')
            t.append("</text>")
            ny = ty + lh * (len(lines) - 1)
            for aj, al in enumerate(extra):
                ny += lh * 0.95 if aj == 0 else fs_sub * 1.2
                t.append(f'<text x="{cx:.2f}" y="{ny:.2f}" text-anchor="middle" font-size="{fs_sub:.2f}" fill="{MUTED}">{html.escape(al)}</text>')
            t.append(f'<text x="{cx:.2f}" y="{ny + fs_dim * 1.45:.2f}" text-anchor="middle" font-size="{fs_dim:.2f}" fill="{MUTED}" font-variant-numeric="tabular-nums">{html.escape(dims(it))}</text>')
            out.extend(t)
            x += cw
        # category headers + baselines
        for cat, x0, x1 in groups:
            first = next(it for it in items if it["cat"] == cat)
            is_start = row[[it["cat"] for it in row].index(cat)] is first
            n = sum(len(it["names"]) for it in items if it["cat"] == cat)
            label = L["cats"][cat] + ("" if is_start else L["cont"])
            hy = base - tallest - 3.2 * f
            out.append(f'<text x="{x0 + 1:.2f}" y="{hy:.2f}" font-size="{3.3 * f:.2f}" font-weight="700" letter-spacing="0.5" fill="{INK}">{html.escape(label.upper())}'
                       + (f'<tspan fill="{MUTED}" font-weight="400"> · {n}</tspan>' if is_start else "") + '</text>')
            out.append(f'<line x1="{x0 + 1:.2f}" x2="{x1 - 1:.2f}" y1="{hy + 1.6 * f:.2f}" y2="{hy + 1.6 * f:.2f}" stroke="{RULE}" stroke-width="0.25"/>')
            out.append(f'<line x1="{x0 + 1:.2f}" x2="{x1 - 1:.2f}" y1="{base:.2f}" y2="{base:.2f}" stroke="{INK}" stroke-width="0.3"/>')
        y = base + label_h + 6 * f + spare / 2

    fy = H - M + 2 * f
    out.append(f'<line x1="{M}" x2="{W - M}" y1="{fy - 6 * f:.2f}" y2="{fy - 6 * f:.2f}" stroke="{RULE}" stroke-width="0.3"/>')
    note = (L["note1"] if abs(k - 1) < 1e-6 else L["noteK"]).format(size=size.split("-")[0], d=fmt(1 / k)) + L["note2"]
    out.append(f'<text x="{M}" y="{fy:.2f}" font-size="{2.4 * f:.2f}" fill="{MUTED}">{html.escape(note)}</text>')
    out.append(f'<text x="{W - M}" y="{fy:.2f}" font-size="{2.4 * f:.2f}" fill="{MUTED}" text-anchor="end">{html.escape(L["lic"])}</text>')

    over = y - (H - M - 10 * f)
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{H}mm" viewBox="0 0 {W} {H}" '
           f'font-family="{FONT}">{defs()}<rect width="{W}" height="{H}" fill="{PAPER}"/>' + "".join(out) + "</svg>")
    return svg, (W, H), over, len(rows)


if __name__ == "__main__":
    out_dir = sys.argv[1]
    size = sys.argv[sys.argv.index("--size") + 1] if "--size" in sys.argv else "A1"
    k = float(sys.argv[sys.argv.index("--scale") + 1]) if "--scale" in sys.argv else 1.0
    lang = sys.argv[sys.argv.index("--lang") + 1] if "--lang" in sys.argv else "de"
    names = set(most_that_fit(size, lang)) if "--fit" in sys.argv else None
    svg, (W, H), over, nrows = build(size, k, lang, names=names, swiss="--swiss" in sys.argv or None)
    os.makedirs(out_dir, exist_ok=True)
    open(os.path.join(out_dir, "poster.svg"), "w").write(svg)
    open(os.path.join(out_dir, "poster.html"), "w").write(
        f"<!doctype html><meta charset=utf-8><style>@page{{size:{W}mm {H}mm;margin:0}}html,body{{margin:0}}svg{{display:block}}</style>{svg}")
    print(f"{size} scale {k}: {nrows} rows, overflow {over:.1f} mm")
