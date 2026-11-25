"""Tests for the calibre wall poster: python3 -m unittest discover -s tests"""
import html, json, os, re, shutil, subprocess, sys, tempfile, unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)
import poster  # noqa: E402
import cartridges  # noqa: E402
from poster import CATALOGUE  # noqa: E402  (the well-sourced calibres)
import build  # noqa: E402
import outline  # noqa: E402

ALL = [s for _, items in CATALOGUE for s in items]
EVERY = {s["name"]: s for _, items in cartridges.CATALOGUE for s in items}  # the whole catalogue, by name


class MergeIdenticalTests(unittest.TestCase):
    def test_identical_measurements_share_one_drawing(self):
        groups = [g["names"] for g in poster.merge_identical(ALL) if len(g["names"]) > 1]
        self.assertEqual(sorted(map(sorted, groups)),
                         sorted([sorted([".308 Winchester", "7.62x51 mm NATO"]), sorted([".38 ACP", ".38 Super"]),
                                 sorted([".223 Remington", "5.56 Commercial", "5.56x45 mm NATO", "5.6 mm GP 90"]),
                                 sorted([".500/450 Magnum Express", ".500/450 Nitro Express"])]))

    def test_no_cartridge_is_lost_or_doubled(self):
        names = [n for g in poster.merge_identical(ALL) for n in g["names"]]
        self.assertEqual(sorted(names), sorted(s["name"] for s in ALL))

    def test_same_groups_as_the_calibre_data(self):
        merged = [g["names"] for g in poster.merge_identical(ALL) if len(g["names"]) > 1]
        shown = {s["name"] for s in ALL}  # a group of the calibre data may be left out as not well sourced
        groups = [[n for n in g if n in shown] for g in outline.identical_groups()]
        self.assertEqual(sorted(map(sorted, merged)), sorted(sorted(g) for g in groups if len(g) > 1))

    def test_similar_but_different_cartridges_stay_apart(self):
        groups = {n: i for i, g in enumerate(poster.merge_identical(ALL)) for n in g["names"]}
        self.assertNotEqual(groups["7.5x55 mm Swiss (GP 11)"], groups["7.62x51 mm NATO"])
        self.assertNotEqual(groups["9x19 mm"], groups["9x21 mm IMI"])

    def test_combined_label_lists_every_name(self):
        poster.LANG = "de"
        lines, extra = poster.label_lines(["7.62x51 mm NATO", ".308 Winchester"])
        self.assertEqual(lines, ["7.62x51 mm NATO", ".308 Winchester"])
        self.assertEqual(extra, ["gleiche Abmessungen"])
        lines, _ = poster.label_lines(["7.5x55 mm Swiss (GP 11)", "9x19 mm"])
        self.assertEqual(lines[0], "7.5x55 mm Swiss", "parenthetical part is dropped in a combined label")


def texts(svg):
    """Every piece of text an SVG prints (a failed check then lists these, not the whole file)."""
    return re.findall(r">([^<>]+)<", re.sub(r"<style>.*?</style>", "", svg))  # without the embedded font


class LabelTests(unittest.TestCase):
    def tearDown(self):
        poster.LANG = "de"

    def test_decimal_point_and_one_decimal_in_every_language(self):
        # Swiss German writes 7.5 like English; a whole number keeps its «.0» so the lines read evenly.
        for lang in ("de", "en"):
            printed = texts(poster.build("A3", 1.0, lang, names={"9x19 mm", ".45 ACP", ".50 BMG"})[0])
            for text in ("Ø 9.0 · 29.7 mm", ".45 Auto · 11.43 mm", "12.7x99 mm NATO"):
                self.assertIn(text, printed)
        self.assertEqual(poster.fmt(25), "25.0")
        for k, scale in ((0.5, "1:2"), (0.4, "1:2.5"), (0.3, "1:3.3")):  # no «.0», one decimal at most
            printed = texts(poster.build("A3", k, "de", names={"9x19 mm"})[0])
            self.assertIn(f"1 Patronen · Massstab {scale}", printed)
            self.assertTrue(printed[-2].startswith(f"Druck ohne Skalierung (100 %) auf A3: Massstab {scale}. Ø: "), printed[-2])
            self.assertTrue(printed[-2].endswith(" Abmessungen gerundet nach CIP/SAAMI, Geschossform schematisch. Keine Ladedaten."), printed[-2])

    def test_no_label_prints_a_decimal_comma(self):
        quoted = {"Cart. 7,5 mm cadets", "Cart. 7,5 mm cadetti"}  # the Kadettenpatrone's French and Italian box labels
        for lang in ("de", "en"):
            poster.LANG = lang
            lines = [ln for s in EVERY for part in poster.split_name(s) for ln in part]
            lines += [poster.tr(t) for row in poster.SWISS_SERVICE for t in row[1:3] + row[4:]]
            self.assertEqual({ln for ln in lines if re.search(r"\d,\d", ln)}, quoted, lang)
        for lang, _, _, stem in build.VERSIONS:  # and none of those is on a published poster
            with open(os.path.join(ROOT, lang, stem + ".svg")) as f:
                self.assertEqual([t for t in texts(f.read()) if re.search(r"\d,\d", t)], [], stem)

    def test_the_name_in_brackets_leads_the_aliases(self):
        poster.LANG = "de"
        self.assertEqual(poster.split_name("7.5x53.5 mm Swiss (Patrone Modell 1890)"),
                         (["7.5x53.5 mm", "Swiss"], ["Patrone Modell 1890", "GP 1890 · GP 90/03"]))
        # no doubles where an alias repeats the bracket
        self.assertEqual(poster.split_name("7.65 mm Browning (.32 ACP)")[1], [".32 ACP · .32 Auto"])
        self.assertEqual(poster.split_name("7.5x55 mm Swiss (GP 11)"), (["7.5x55 mm"], ["GP 11", "7.5 mm Swiss"]))
        self.assertEqual(poster.split_name("6.35 mm Browning (.25 ACP)")[1], [".25 ACP"])

    def test_english_leaves_out_the_german_aliases(self):
        poster.LANG = "de"
        self.assertEqual(poster.split_name(".22 LR")[1], [".22 Long Rifle · KK"])
        self.assertEqual(poster.split_name("9 mm PA Blanc")[1], ["9 mm P.A.K.", "9 mm P.A. Knall"])
        self.assertEqual(poster.split_name(".22 Long Blanc")[1], [".22 lang Knall", "Setzkartusche 5.6/16"])
        poster.LANG = "en"
        self.assertEqual(poster.split_name(".22 LR")[1], [".22 Long Rifle"])
        self.assertEqual(poster.split_name("9 mm PA Blanc")[1], ["9 mm P.A.K."])
        self.assertEqual(poster.split_name("9 mm Flobert Bosquette")[1], [])
        # of a «Setzkartusche» the size stays
        self.assertEqual(poster.split_name(".22 SH (5.6/11)")[1], [".22 Blank · 5.6/11"])
        self.assertEqual(poster.split_name(".22 Long Blanc")[1], ["5.6/16"])
        german = re.compile("Knall|Kugel|Setzkartusche|KK")
        self.assertEqual([ln for s in EVERY for ln in poster.split_name(s)[1] if german.search(ln)], [])

    def test_subtitle_names_projectiles_only_where_some_are_drawn(self):
        ball = ".36 Rundkugel (.375)"
        sub = lambda lang, names: texts(poster.build("A3", 1.0, lang, names=names)[0])[1].split(" · ")[0]
        self.assertEqual(sub("de", {"9x19 mm", ball}), "2 Patronen und Geschosse")
        self.assertEqual(sub("en", {"9x19 mm", ball}), "2 cartridges and projectiles")
        self.assertEqual(sub("de", {"9x19 mm"}), "1 Patronen")
        self.assertEqual(sub("en", {"9x19 mm", "12/70"}), "2 cartridges")

    def test_german_section_headers_are_plural(self):
        printed = texts(poster.build("A3", 1.0, "de", names={"9x19 mm", ".308 Winchester", "12/70"})[0])
        for header in ("KURZWAFFEN", "LANGWAFFEN", "FLINTEN"):
            self.assertIn(header, printed)

    def test_the_footer_says_what_the_figures_under_a_cartridge_are(self):
        """«Ø» is the bullet of a cartridge and the case of a shot shell or a blank; the second figure is the overall length."""
        names = LayoutTests.NAMES | {".58 Minié"}  # no case at all: not a blank
        for lang, legend, with_blanks in (
                ("de", "Ø: Geschossdurchmesser (Schrotpatronen: Hülse), dann Gesamtlänge. ", "Ø: Geschossdurchmesser (Schrot- und Knallpatronen: Hülse), dann Gesamtlänge. "),
                ("en", "Ø: bullet diameter (shot shells: hull), then overall length. ", "Ø: bullet diameter (shot shells and blanks: case), then overall length. ")):
            for size in ("A1", "Letter"):
                self.assertIn(legend, texts(poster.build(size, 1.0, lang, names=names)[0])[-2], f"{lang} {size}")
            for blank in (".22 Long Blanc", "9 mm PA Blanc"):  # star-crimped, and closed inside a plain cylinder
                self.assertIn(with_blanks, texts(poster.build("A1", 1.0, lang, names=names | {blank})[0])[-2], f"{lang} {blank}")
        shell = next(s for s in ALL if s["name"] == "12/70")
        self.assertLess(shell["base"], shell["rim"])
        self.assertEqual(poster.dims(dict(shell, outline=outline.outline(shell))), f"Ø {poster.fmt(shell['base'])} · {poster.fmt(shell['oal'])} mm", "the hull, not the rim, and the length as crimped")
        blank = next(s for s in ALL if s["name"] == ".22 Long Blanc")
        self.assertEqual(poster.dims(dict(blank, outline=outline.outline(blank))), f"Ø {poster.fmt(blank['base'])} · {poster.fmt(blank['case'])} mm", "a blank's case")


class BuildTests(unittest.TestCase):
    def test_full_catalogue_builds_and_reports_overflow(self):
        svg, (w, h), over, rows = poster.build("A1", 1.0, "de")
        self.assertTrue(svg.startswith("<svg"))
        self.assertIn(f'width="{w}mm" height="{h}mm"', svg)
        self.assertGreater(over, 0, "the whole catalogue no longer fits one A1 sheet at 1:1")

    def test_every_drawing_is_named_once(self):
        names = set(poster.most_that_fit("A2"))
        svg = poster.build("A2", 1.0, "de", names=names)[0]
        drawings = svg.count("<g transform=")
        self.assertEqual(drawings, len(poster.merge_identical([s for s in ALL if s["name"] in names])))
        n = re.search(r">(\d+) Patronen(?: und Geschosse)? · ", svg)
        self.assertEqual(int(n.group(1)), len(names), "the subtitle counts every cartridge, merged or not")

    def test_english_labels(self):
        svg = poster.build("A3", 1.0, "en", names=set(poster.most_that_fit("A3", "en")))[0]
        self.assertIn("Calibre Comparison", svg)
        self.assertIn("Actual size (scale 1:1)", svg)
        self.assertNotIn("Kaliber im Vergleich", svg)

    def test_licence_credit(self):
        for lang in ("de", "en"):
            self.assertIn("© 2026 Simon Giotta", poster.build("A3", 1.0, lang, names={"9x19 mm"})[0])

    def test_rows_never_run_past_the_right_margin(self):
        for size in ("A1", "A3"):
            svg, (w, _), _, _ = poster.build(size, 1.0, "de", names=set(poster.most_that_fit(size)))
            xs = [float(x) for x in re.findall(r'<g transform="translate\(([-\d.]+) ', svg)]
            self.assertLess(max(xs), w - 10, size)


class LayoutTests(unittest.TestCase):
    NAMES = {"9x19 mm", ".308 Winchester", "12/70"}

    def test_tallest_cartridge_stays_clear_of_the_header_rule(self):
        for size in ("A0", "A2", "A3"):
            svg = poster.build(size, 1.0, "de", names=self.NAMES)[0]
            tops = [float(y) for y in re.findall(r'<g transform="translate\([-\d.]+ ([-\d.]+)\)', svg)]
            rules = {float(y) for y in re.findall(r'y1="([\d.]+)" y2="[\d.]+" stroke="#cfc5b3" stroke-width="0.25"', svg)}
            self.assertEqual(len(rules), 1, "one row, its three headers on one line")
            self.assertAlmostEqual(min(tops) - rules.pop(), poster.TIP_GAP, places=1, msg=size)

    def test_a_group_far_shorter_than_its_row_gets_its_header_just_above_itself(self):
        svg = poster.build("A2", 1.0, "de", names={".308 Winchester", ".50 BMG", "12/70"})[0]  # the shell beside the .50 BMG
        tops = [float(y) for y in re.findall(r'<g transform="translate\([-\d.]+ ([-\d.]+)\)', svg)]
        rules = sorted({float(y) for y in re.findall(r'y1="([\d.]+)" y2="[\d.]+" stroke="#cfc5b3" stroke-width="0.25"', svg)})
        self.assertEqual(len(rules), 2, "rifles on the row's line, shotgun on its own")
        self.assertAlmostEqual(min(tops) - rules[0], poster.TIP_GAP, places=1)
        self.assertAlmostEqual(tops[-1] - rules[1], poster.TIP_GAP, places=1)
        self.assertGreater(rules[1] - rules[0], poster.HEADER_DROP)

    def test_header_and_title_spacing_scale_with_the_type(self):
        spacing = lambda size: sorted(set(re.findall(r'letter-spacing="([-\d.]+)"', poster.build(size, 1.0, "de", names=self.NAMES)[0])))
        self.assertEqual(spacing("A0"), ["-0.40", "0.50"])
        self.assertEqual(spacing("A2"), ["-0.32", "0.40"])
        self.assertEqual(spacing("A3"), ["-0.23", "0.29"])

    def test_scale_bar_is_100_mm_and_its_unit_ends_at_the_margin(self):
        for size, margin in (("A0", 26), ("A3", 14), ("Letter", 14)):
            svg, (w, _), _, _ = poster.build(size, 1.0, "en", names=self.NAMES)
            x1, x2 = map(float, re.search(r'<line x1="([\d.]+)" x2="([\d.]+)" y1="[\d.]+" y2="[\d.]+" stroke="#1d1b18" stroke-width="0.35"/>', svg).groups())
            self.assertAlmostEqual(x2 - x1, 100, places=6, msg=size)
            unit = re.search(r'<text x="([\d.]+)" y="[\d.]+" text-anchor="end">mm</text>', svg)
            self.assertEqual(float(unit.group(1)), w - margin, size)
            figures = float(re.search(r'<g font-size="([\d.]+)" fill="[^"]+" text-anchor="middle">', svg).group(1))
            self.assertGreater(w - margin - x2, 3 * figures, "room for half of «100», a gap and «mm» at the size they are set in")

    def test_scale_bar_stays_clear_of_the_title_on_every_published_poster(self):
        for lang, _, _, stem in build.VERSIONS:
            with open(os.path.join(ROOT, lang, stem + ".svg"), encoding="utf-8") as f:
                svg = f.read()
            x, y, size, title = re.search(r'<text x="([\d.]+)" y="([\d.]+)" font-size="([\d.]+)" font-weight="800"[^>]*>([^<]+)<', svg).groups()
            bar_x, bar_y = re.search(r'<line x1="([\d.]+)" x2="[\d.]+" y1="([\d.]+)" y2="[\d.]+" stroke="#1d1b18" stroke-width="0.35"/>', svg).groups()
            title_end = float(x) + len(title) * float(size) * 0.56  # generous: the heavy title runs about 0.52 em a letter
            self.assertTrue(float(bar_y) > float(y) or float(bar_x) > title_end, f"{lang}/{stem}: beside the title or on a line below it")


class RowBreakTests(unittest.TestCase):
    """A section cut by a row break keeps at least two cartridges on either side."""
    row = staticmethod(lambda cats: [{"cat": c} for c in cats])

    def held_back(self, cur, rest):
        return poster.held_back(self.row(cur), self.row(rest))

    def test_a_section_does_not_start_with_one_cartridge_at_the_end_of_a_row(self):
        self.assertEqual(self.held_back("PPPPS", "SSS"), 1, "the lone shell joins the others on the next row")
        self.assertEqual(self.held_back("PPPSS", "SSS"), 0, "two may start a section")

    def test_a_section_does_not_end_with_one_cartridge_on_the_next_row(self):
        self.assertEqual(self.held_back("RPPPP", "PS"), 1, "one goes down to keep the last one company")
        self.assertEqual(self.held_back("PPPPP", "PS"), 1, "also where the section fills the whole row")
        self.assertEqual(self.held_back("RPPPP", "PPS"), 0)
        self.assertEqual(self.held_back("RRRPP", "PS"), 2, "three in all: they stay together on the next row")
        self.assertEqual(self.held_back("RRRRP", "PS"), 1, "and so do two")

    def test_whole_sections_and_single_cartridges_stay_where_they_are(self):
        self.assertEqual(self.held_back("RRRRP", "SSS"), 0, "a section of one, complete")
        self.assertEqual(self.held_back("RRRRR", "SSS"), 0)
        self.assertEqual(self.held_back("P", "PS"), 0, "never empties a row")

    def test_no_published_poster_cuts_off_a_single_cartridge(self):
        drawn, draw = [], poster.cartridge_svg
        poster.cartridge_svg = lambda c, o, x, base, k: (drawn.append((c["cat"], base)), draw(c, o, x, base, k))[1]
        try:
            for lang, size, edition, stem in build.VERSIONS:
                del drawn[:]
                build.version(lang, size, edition)
                rows = [[cat for cat, base in drawn if base == b] for b in sorted({base for _, base in drawn})]
                for row, below in zip(rows, rows[1:]):
                    if row[-1] == below[0]:
                        self.assertGreaterEqual(min(row.count(row[-1]), below.count(below[0])), 2, f"{lang}/{stem}: {row[-1]}")
        finally:
            poster.cartridge_svg = draw


class TypeTests(unittest.TestCase):
    NAMES = LayoutTests.NAMES

    def test_no_line_is_set_smaller_than_five_points_and_no_name_smaller_than_six(self):
        builds = [poster.build(size, 1.0, "en", names=self.NAMES)[0] for size in ("A0", "A2", "A3", "Letter")]
        for svg in builds + [poster.build("A3-quer", 1.0, "de", swiss=True)[0]]:
            sizes = [float(x) for x in re.findall(r'font-size="([\d.]+)"', svg)]
            self.assertGreaterEqual(min(sizes), 1.77, "5 pt is 1.764 mm")
            names = [float(x) for x in re.findall(r'font-size="([\d.]+)" font-weight="600"', svg)]
            self.assertGreaterEqual(min(names), 2.12, "6 pt is 2.117 mm")
        self.assertIn('font-size="2.55" font-weight="600"', builds[0], "the big sheets keep their A1-sized type")
        self.assertIn('font-size="2.12" font-weight="600"', builds[2], "6 pt on A3")

    def test_a_row_ends_under_its_longest_label(self):
        """No row keeps room for label lines it does not have: the space between its lowest
        dimension line and the next header is the same all down the sheet."""
        svg = poster.build("A2", 1.0, "de", names=set(poster.most_that_fit("A2")))[0]
        heads = sorted({float(y) for y in re.findall(r'<text x="[\d.]+" y="([\d.]+)" font-size="[\d.]+" font-weight="700"', svg)})
        dims = [float(y) for y in re.findall(r'<text x="[\d.]+" y="([\d.]+)"[^>]*>Ø ', svg)]
        rows = [(above, below) for above, below in zip(heads, heads[1:]) if any(above < y < below for y in dims)]
        gaps = [below - max(y for y in dims if above < y < below) for above, below in rows]  # a row's own lower header aside
        self.assertGreater(len(gaps), 2)
        self.assertGreater(min(gaps), 8, "and that space keeps the header clear of the labels above it")
        for gap in gaps:
            self.assertAlmostEqual(gap, gaps[0], places=1)

    def test_names_keep_the_room_of_their_own_size_on_every_published_poster(self):
        """Where the type stops shrinking with the sheet, the columns stop too: two names side by
        side stay at least eight times their size apart."""
        for lang, _, _, stem in build.VERSIONS:
            with open(os.path.join(ROOT, lang, stem + ".svg"), encoding="utf-8") as f:
                svg = f.read()
            rows = {}
            for x, y, size in re.findall(r'<text x="([\d.]+)" y="([\d.]+)" text-anchor="middle" font-size="([\d.]+)" font-weight="600"', svg):
                rows.setdefault(y, []).append(float(x))
            steps = [b - a for xs in rows.values() for a, b in zip(sorted(xs), sorted(xs)[1:])]
            self.assertGreater(len(steps), 5, stem)  # the shotgun sheet has eight shells in all
            self.assertGreaterEqual(min(steps), 8 * float(size), f"{lang}/{stem}")

    def footer(self, svg):
        """(x, y, end by a generous estimate, text) of each line under the footer rule."""
        lines = re.findall(r'<text x="([\d.]+)" y="([\d.]+)" font-size="([\d.]+)" fill="#6f675c"(?: text-anchor="end")?>([^<]+)</text>', svg)
        lines = [(float(x), float(y), float(size), html.unescape(text)) for x, y, size, text in lines if "Ø: " in text or "©" in text or "(100" in text]
        return [(x, y, x + len(text) * size * 0.52, text) for x, y, size, text in lines]  # Inter runs up to 0.51 em a letter (German)

    def test_the_footer_note_fits_on_one_line_on_every_published_poster(self):
        for lang, _, _, stem in build.VERSIONS:
            with open(os.path.join(ROOT, lang, stem + ".svg"), encoding="utf-8") as f:
                svg = f.read()
            width = float(re.search(r'viewBox="0 0 ([\d.]+) ', svg).group(1))
            (x, _, end, note), (_, _, _, licence) = self.footer(svg)
            self.assertIn("Ø: ", note)
            self.assertTrue(note.endswith("Keine Ladedaten." if lang == "de" else "Not load data."), note)
            self.assertLess(end, width - x, f"{lang}/{stem}: the note must end inside the margin")
            self.assertIn("CC BY-NC 4.0", licence)

    def test_the_footer_note_takes_two_lines_where_one_is_too_narrow(self):
        """German runs longer: on A4 and Letter (not published in German) the legend starts a second line."""
        for size in ("A4", "Letter"):
            svg, (w, h), _, _ = poster.build(size, 1.0, "de", names=LayoutTests.NAMES | {"9 mm PA Blanc"})
            first, second, licence = self.footer(svg)
            self.assertTrue(first[3].endswith("Patronen in Originalgrösse."), first[3])
            self.assertTrue(second[3].startswith("Ø: Geschossdurchmesser (Schrot- und Knallpatronen: Hülse)"), second[3])
            self.assertTrue(licence[3].startswith("©"))
            for x, y, end, text in (first, second, licence):
                self.assertEqual(x, 14, text)
                self.assertLess(end, w - 14, f"{size}: {text}")
            self.assertEqual(sorted({first[1], second[1], licence[1]}), [first[1], second[1], licence[1]], "one under the other")
            self.assertLess(licence[1], h - 7.5, "the third line still clears the sheet's edge")

    def test_the_licence_goes_below_the_note_where_both_do_not_fit_on_one_line(self):
        def footer(size):
            svg = poster.build(size, 1.0, "en", names=self.NAMES)[0]
            note = re.search(r'<text x="([\d.]+)" y="([\d.]+)" font-size="[\d.]+" fill="#6f675c">Print without', svg)
            licence = re.search(r'<text x="([\d.]+)" y="([\d.]+)" font-size="[\d.]+" fill="#6f675c"( text-anchor="end")?>©', svg)
            return [float(v) for v in note.groups()], [float(v) for v in licence.groups()[:2]], licence.group(3)
        (note_x, note_y), (x, y), end = footer("Letter")
        self.assertEqual((x, end), (note_x, None), "flush left, under the note")
        self.assertGreater(y - note_y, poster.MIN_TEXT)
        self.assertLess(y, poster.SIZES["Letter"][1] - 10, "and still 10 mm inside the sheet")
        (note_x, note_y), (x, y), end = footer("A3")
        self.assertEqual((y, x), (note_y, poster.SIZES["A3"][0] - 14), "side by side where there is room")
        self.assertTrue(end)


class OrderTests(unittest.TestCase):
    @staticmethod
    def printed(svg):
        """(length, diameter) of every drawing, as printed under it, in poster order. A round ball
        shows only its diameter, which is also its length."""
        return [(float(l or d), float(d)) for d, l in re.findall(r">Ø ([\d.]+)(?: · ([\d.]+))? mm<", svg)]

    def test_each_section_goes_by_length_then_diameter(self):
        sections = [specs for cat, specs in CATALOGUE if cat != "Schwarzpulver"]
        black = dict(CATALOGUE)["Schwarzpulver"]
        sections += [[s for s in black if s["kind"] in (poster.BALL, poster.MINIE)],
                     [s for s in black if s["kind"] not in (poster.BALL, poster.MINIE)]]
        for specs in sections:
            names = {s["name"] for s in specs}
            with self.subTest(first=specs[0]["name"]):
                got = self.printed(poster.build("A0", 1.0, "de", names=names)[0])
                self.assertGreater(len(got), 1)
                self.assertEqual(got, sorted(got))

    def test_equal_length_puts_the_thinner_bullet_first(self):
        svg = poster.build("A3", 1.0, "de", names={"12/70", "16/70", "20/70", "28/70"})[0]
        self.assertEqual(self.printed(svg), [(61.1, 20.6), (62.0, 18.9), (62.1, 17.7), (63.5, 15.8)])
        svg = poster.build("A3", 1.0, "de", names={".308 Winchester", ".30-06 Springfield", "7.5x55 mm Swiss (GP 11)"})[0]
        self.assertEqual(self.printed(svg), sorted(self.printed(svg)))

    def test_length_as_printed_decides_before_the_diameter(self):
        # 84.84 mm is printed as 84.8 mm, so the thinner bullet comes first.
        self.assertLess(poster.section_order({"oal": 84.84, "bullet": 6.7}), poster.section_order({"oal": 84.8, "bullet": 7.8}))


class SelectionTests(unittest.TestCase):
    def test_only_well_sourced_calibres_are_drawn(self):
        shown = {s["name"] for s in ALL}
        self.assertEqual(shown, {n for n, s in EVERY.items() if outline.well_sourced(s)})
        self.assertGreater(len(shown), 500)
        self.assertLess(len(shown), len(EVERY))
        for name in ("9x19 mm", "12/70", "10.4 mm Swiss Ordnance 1878"):  # the last one: a default rim is allowed
            self.assertIn(name, shown)
        left_out = ".56-52 Spencer Necked"  # an estimated shoulder at the default angle
        self.assertNotIn(left_out, shown)
        self.assertNotIn(left_out, poster.ranked())
        svg = poster.build("A3", 1.0, "en", names={"9x19 mm", left_out})[0]  # also when asked for by name
        self.assertIn("1 cartridges · Actual size (scale 1:1)", texts(svg))
        for size in ("A3", "A0"):
            self.assertLessEqual(set(poster.most_that_fit(size)), shown)

    def test_cannon_rounds_stay_off(self):  # a cannon poster may come later; the calibre posters leave them out
        cannon = {s["name"] for cat, items in cartridges.ALL_CATALOGUE if cat == "Kanone" for s in items}
        self.assertGreater(len(cannon), 20)
        self.assertFalse(cannon & {s["name"] for s in ALL})

    def test_ranking_holds_every_calibre_once(self):
        ranked = poster.ranked()
        self.assertEqual(sorted(ranked), sorted(s["name"] for s in ALL))

    def test_most_listed_first(self):
        top = poster.ranked()[:5]
        self.assertIn("9x19 mm", top)
        self.assertIn(".22 LR", top)

    def test_bigger_paper_holds_more(self):
        counts = [len(poster.most_that_fit(size)) for size in ("A3", "A2", "A1", "A0")]
        self.assertEqual(counts, sorted(counts))
        self.assertLess(counts[-1], len(ALL), "not even A0 holds the whole catalogue at 1:1")

    def test_selection_fits_and_the_next_one_does_not(self):
        cat_of = {s["name"]: cat for cat, items in CATALOGUE for s in items}
        for size in ("A3", "A1"):
            names = poster.most_that_fit(size)
            shown_cats = {cat_of[n] for n in names}
            pool = [n for n in poster.ranked() if cat_of[n] in shown_cats]
            self.assertEqual(names, pool[:len(names)], "a prefix of the ranking, less the left-out sections")
            self.assertLessEqual(poster.build(size, 1.0, "de", names=set(names))[2], poster.OVERRUN)
            self.assertGreater(poster.build(size, 1.0, "de", names=set(pool[:len(names) + 1]))[2], poster.OVERRUN)

    def test_the_search_fills_the_page_as_far_as_the_build_allows(self):
        # build.py accepts a last row that runs OVERRUN mm past the content edge; the search stops there too
        # and not 2 mm earlier, which cost A0 a whole row.
        self.addCleanup(setattr, poster, "build", poster.build)
        poster.build = lambda size, k, lang, names: (None, None, len(names) - 8.5, 1)  # 9 names: 0.5 mm over
        pool = [f"calibre {i}" for i in range(30)]
        self.assertEqual(len(poster._prefix_that_fits("A0", "de", pool)), 10, "1.5 mm over still fits, 2.5 mm does not")
        self.assertEqual(poster.OVERRUN, 2.0)

    def test_no_air_gun_and_no_section_of_only_a_few_black_powder(self):
        cat_of = {s["name"]: cat for cat, items in CATALOGUE for s in items}
        air = {name for name, cat in cat_of.items() if cat == "Luftdruck"}
        self.assertTrue(air, "the catalogue has them")
        with open(poster.SHARE_FILE, encoding="utf-8") as f:
            listed = set(json.load(f)["share"])
        self.assertEqual(air & listed, {"4.5 mm Diabolo (.177)", "5.5 mm Diabolo (.22)"}, "the README says two are listed")
        for lang, size, edition, stem in build.VERSIONS:
            if edition != "fit":
                continue
            names = poster.most_that_fit(size, lang)
            with self.subTest(stem=stem):
                self.assertEqual([x for x in names if cat_of[x] in poster.LEFT_OUT], [])
            for cat in poster.SMALL_SECTIONS:
                with self.subTest(stem=stem, cat=cat):
                    n = sum(cat_of[x] == cat for x in names)
                    self.assertTrue(n == 0 or n >= poster.MIN_SECTION, n)
        # also from a pool that ranks every air-gun calibre first
        air_first = sorted(poster.ranked(), key=lambda n: cat_of[n] != "Luftdruck")
        self.assertEqual([x for x in poster.most_that_fit("A3", pool=air_first) if cat_of[x] == "Luftdruck"], [])
        a1 = poster.most_that_fit("A1")
        self.assertGreaterEqual(sum(cat_of[x] == "Schwarzpulver" for x in a1), poster.MIN_SECTION)  # big sheets keep it
        self.assertFalse(any(cat_of[x] == "Schwarzpulver" for x in poster.most_that_fit("A3")))

    def test_every_listed_share_is_a_catalogue_calibre(self):
        import json
        share = json.load(open(poster.SHARE_FILE))["share"]
        self.assertLessEqual(set(share), set(EVERY))


class SwissServiceTests(unittest.TestCase):
    def test_every_service_cartridge_is_in_the_catalogue(self):
        for row in poster.SWISS_SERVICE:
            self.assertIn(row[0], EVERY)

    def test_the_swiss_poster_shows_the_well_sourced_ones(self):
        shown = {s["name"] for s in ALL}
        rows = [row for row in poster.SWISS_SERVICE if row[0] in shown]
        self.assertGreaterEqual(len(rows), 14)
        svg = poster.build("A3-quer", 1.0, "de", swiss=True)[0]
        self.assertIn(f"{len(rows)} Patronen von 1867 bis heute", svg)
        self.assertEqual(svg.count("<g transform="), len(rows))

    def test_oldest_first_and_fits_a3_landscape(self):
        svg, _, over, rows = poster.build("A3-quer", 1.0, "de", swiss=True)
        self.assertLessEqual(over, 0)
        self.assertEqual(rows, 1)
        self.assertLess(svg.index("Milbank-Amsler"), svg.index("Pist Pat 41"))
        self.assertLess(svg.index("Pist Pat 41"), svg.index("Zf Stgw 20"))
        years = [row[3] for row in poster.SWISS_SERVICE]
        self.assertTrue(all(isinstance(year, int) for year in years), "every round has its year")
        self.assertEqual(years, sorted(years), "and stands in that order")
        printed = texts(svg)
        for year in ("1964", "1991"):  # the .50 BMG (Mg 64) and the 12/70 (Mzgw 91)
            self.assertIn(year, printed)
        self.assertLess(printed.index(".50 BMG"), printed.index("GP 90"))
        self.assertLess(printed.index("GP 90"), printed.index("12/70"))

    def test_weapons_break_between_weapons(self):
        de = texts(poster.build("A3-quer", 1.0, "de", swiss=True)[0])
        for row in poster.SWISS_SERVICE:
            for weapon in row[4].split(", "):  # never «Pistole» on one line and «75» on the next
                self.assertTrue(any(weapon in t.rstrip(",").split(", ") for t in de), weapon)

    def test_no_section_header_repeats_the_subtitle(self):
        for lang in ("de", "en"):
            svg = poster.build("A3-quer", 1.0, lang, swiss=True)[0]
            self.assertNotIn('font-weight="700"', svg, "no header text and no count")
            self.assertEqual(svg.count(f'stroke="{poster.RULE}"'), 1, "only the footer rule, no header rule")
            self.assertEqual(sum("1867 " in t for t in texts(svg)[:3]), 1, "the subtitle still says it")

    def test_english_names_are_capitalised_alike(self):
        en = texts(poster.build("A3-quer", 1.0, "en", swiss=True)[0])
        for text in ("Rimfire", "Centrefire", "Milbank-Amsler Rifle", "Rifle 1889", "Cadet Rifle 1897", "Pistol 75, Mp 14"):
            self.assertIn(text, en)

    def test_swiss_names_lead_and_numbers_use_points(self):
        de = poster.build("A3-quer", 1.0, "de", swiss=True)[0]
        en = poster.build("A3-quer", 1.0, "en", swiss=True)[0]
        for name in ("Pist Pat 03", "Pist Pat 41", "GP 11", "GP 90", "Kadettenpatrone"):
            self.assertIn(f">{name}<", de)
        self.assertIn(">Modell 1890<", de)  # the 1890 round under its own name: «Patrone» / «Modell 1890»
        self.assertNotIn("GP 1890", de)  # a later collectors' name
        self.assertIn("Ordonnanzpatronen der Schweizer Armee", de)
        self.assertIn("Swiss Army Service Cartridges", en)
        for svg in (de, en):
            self.assertIn("10.4 mm", svg)
            self.assertNotIn("10,4 mm", svg)


class MaterialTests(unittest.TestCase):
    def test_materials_get_their_own_fill(self):
        spec = EVERY
        def svg(name):
            s = spec[name]
            return poster.cartridge_svg(s, outline.outline(s), 0, 0, 1.0)
        self.assertIn("url(#lacquered)", svg("7.62x39 mm"))  # lacquered steel case, as in the apps
        self.assertIn("url(#lead)", svg(".22 LR"))           # lead bullet
        self.assertIn("url(#paper)", svg("7.5x53.5 mm Swiss (Patrone Modell 1890)"))
        self.assertIn("url(#nickel)", svg("7.5x55 mm Swiss (GP 11)"))  # a silver jacket
        self.assertNotIn("url(#copper)", svg("7.5x55 mm Swiss (GP 11)"))
        self.assertIn("url(#plastic)", svg("6 mm Airsoft-BB"))        # white plastic
        self.assertIn("url(#lead)", svg("4.5 mm Diabolo (.177)"))

    def test_material_colours_match_the_apps(self):
        # Kaliberfinder CartridgeView: brass, copper, lead, steel, lacqueredSteel, nickel, polymer, shotShell
        self.assertEqual(poster.MATERIALS["lacquered"], (0.42, 0.42, 0.33))
        self.assertEqual(poster.MATERIALS["brass"], (0.89, 0.76, 0.44))
        self.assertEqual(poster.MATERIALS["hull"], (0.75, 0.22, 0.17))
        d = poster.defs()
        for name in poster.MATERIALS:
            self.assertIn(f'id="{name}"', d)
        self.assertIn('stop-color="#e3c270"', d)  # brass at its own colour in the middle of the gradient


class UsSheetTests(unittest.TestCase):
    NAMES = LayoutTests.NAMES

    def test_us_sheets_have_their_exact_size_in_inches(self):
        for size, (w, h) in {"24x36in": (24, 36), "18x24in": (18, 24), "11x17in": (11, 17), "Letter": (8.5, 11)}.items():
            self.assertEqual(poster.SIZES[size], (round(w * 25.4, 1), round(h * 25.4, 1)), size)
            svg = poster.build(size, 1.0, "en", names=self.NAMES)[0]
            self.assertEqual(re.findall(r"\d+\.\d{5,}", re.sub(r"<style>.*?</style>", "", svg)), [], f"{size}: no float noise from the odd widths")
        self.assertIn('width="609.6mm" height="914.4mm" viewBox="0 0 609.6 914.4"', poster.build("24x36in", 1.0, "en", names=self.NAMES)[0])

    def test_us_sheets_use_us_spelling_and_name_their_size_in_inches(self):
        us = texts(poster.build("11x17in", 1.0, "en", names=self.NAMES)[0])
        self.assertEqual(us[0], "Caliber Comparison")
        self.assertTrue(us[-2].startswith("Print without scaling (100%) on 11 × 17 in: "), us[-2])
        self.assertIn("License CC BY-NC 4.0", us[-1])
        self.assertTrue(texts(poster.build("Letter", 1.0, "en", names=self.NAMES)[0])[-2].startswith("Print without scaling (100%) on Letter: "))
        half = texts(poster.build("Letter", 0.5, "en", names=self.NAMES)[0])
        self.assertTrue(half[-2].startswith("Print without scaling (100%) on Letter: scale 1:2. "), half[-2])

    def test_other_sheets_keep_their_spelling(self):
        a3 = texts(poster.build("A3", 1.0, "en", names=self.NAMES)[0])
        self.assertEqual(a3[0], "Calibre Comparison")
        self.assertTrue(a3[-2].startswith("Print without scaling (100 %) on A3: "))
        self.assertIn("Licence CC BY-NC 4.0", a3[-1])
        self.assertEqual(texts(poster.build("Letter", 1.0, "de", names=self.NAMES)[0])[0], "Kaliber im Vergleich")
        swiss = texts(poster.build("Letter", 1.0, "en", swiss=True)[0])
        self.assertIn("10.4 mm Centrefire", " ".join(swiss), "the Swiss edition has British names")
        self.assertIn("Licence CC BY-NC 4.0", swiss[-1], "so it keeps British spelling on a US sheet too")


class OutputTests(unittest.TestCase):
    def test_every_poster_carries_the_font_in_the_weights_it_uses(self):
        for svg in (poster.build("A3", 1.0, "de", names=LayoutTests.NAMES)[0], poster.build("A3-quer", 1.0, "en", swiss=True)[0]):
            style = re.search(r"<style>(.*?)</style>", svg).group(1)
            faces = set(re.findall(r"@font-face\{font-family:Inter;font-weight:(\d+);src:url\(data:font/woff2;base64,", style))
            used = set(re.findall(r'font-weight="(\d+)"', svg)) | {"400"}  # text without a weight is regular
            self.assertLessEqual(used, faces, "a face for every weight the poster uses")
            self.assertTrue(re.search(r'font-family="Inter,', svg), "and the text asks for it first")

    def test_no_attribute_that_browsers_ignore(self):
        self.assertNotIn("font-variant-numeric", poster.build("A3", 1.0, "de", names=LayoutTests.NAMES)[0])

    def test_the_printed_page_is_paper_under_the_poster(self):
        self.assertIn("html,body{margin:0;background:" + poster.PAPER + "}", poster.page_html("<svg/>"))

    def test_the_command_line_writes_the_page_that_render_js_prints(self):
        with tempfile.TemporaryDirectory() as out:
            subprocess.run([sys.executable, os.path.join(ROOT, "poster.py"), out, "--size", "A3-quer", "--swiss"], check=True, capture_output=True)
            with open(os.path.join(out, "poster.svg")) as f, open(os.path.join(out, "poster.html")) as g:
                svg, page = f.read(), g.read()
        self.assertEqual(svg, poster.build("A3-quer", 1.0, "de", swiss=True)[0])
        self.assertEqual(page, poster.page_html(svg), "no page size of its own: render.js sets it")

    def test_every_character_on_the_published_posters_is_in_the_embedded_font(self):
        """fonts/inter-latin.css is Inter's Latin subset: all of Latin-1 and little else. A name
        with «⅜» (two Nitro Express calibres far down the ranking) would be set in another font."""
        for lang, _, _, stem in build.VERSIONS:
            with open(os.path.join(ROOT, lang, stem + ".svg"), encoding="utf-8") as f:
                printed = set(html.unescape("".join(texts(f.read()))))
            self.assertEqual(sorted(c for c in printed if not (" " <= c <= "~" or "\xa0" <= c <= "ÿ")), [], f"{lang}/{stem}")

    PAGE = "2 0 obj\n<</Type /Page\n/MediaBox [0 0 844.8 1193.52]\n/Parent 3 0 R>>\nendobj\n"
    TAIL = "xref\n0 1\n0000000000 65535 f \ntrailer\n<</Size 4\n/Root 1 0 R>>\nstartxref\n84\n%%EOF\n"

    @unittest.skipUnless(shutil.which("node"), "render.js needs Node")
    def test_the_pdf_page_gets_the_size_of_the_sheet(self):
        """Chromium prints a slightly larger page; render.js cuts it to the sheet, measured from the top left."""
        pdf = "%PDF-1.4\n" + self.PAGE + self.TAIL
        self.assertEqual(pdf.index("xref"), 84)
        script = "process.stdout.write(require('./render.js').trim(Buffer.from(process.argv[1], 'latin1'), 297, 420))"
        out = subprocess.run(["node", "-e", script, pdf], cwd=ROOT, capture_output=True, check=True).stdout.decode("latin1")
        self.assertTrue(out.startswith(pdf), "an incremental update: what Chromium wrote stays as it is")
        update = out[len(pdf):]
        self.assertIn("/MediaBox [0 2.969 841.890 1193.52]", update, "A3 is 841.890 x 1190.551 pt, hanging from the top edge")
        at = int(re.search(r"xref\n2 1\n(\d{10}) 00000 n \n", update).group(1))
        self.assertTrue(out[at:].startswith("2 0 obj\n<</Type /Page\n"), "the new cross-reference entry points at the new page object")
        self.assertIn("/Root 1 0 R\n/Prev 84>>", update)
        self.assertTrue(out[int(re.search(r"startxref\n(\d+)\n%%EOF\n$", out).group(1)):].startswith("xref\n2 1\n"))

    @unittest.skipUnless(shutil.which("node"), "render.js needs Node")
    def test_a_pdf_it_does_not_understand_is_refused(self):
        """Two pages, a page that was trimmed before, no page at all: an error that says so, no half-trimmed file."""
        one = "%PDF-1.4\n" + self.PAGE + self.TAIL
        script = ("const { trim } = require('./render.js'), pdf = text => Buffer.from(text, 'latin1');"
                  "for (const bad of [process.argv[1], process.argv[2], trim(pdf(process.argv[3]), 297, 420).toString('latin1')])"
                  "  try { trim(pdf(bad), 297, 420); console.log('trimmed'); } catch (e) { console.log(e.message); }")
        two = "%PDF-1.4\n" + self.PAGE + self.PAGE.replace("2 0 obj", "5 0 obj") + self.TAIL
        out = subprocess.run(["node", "-e", script, two, "%PDF-1.4\n" + self.TAIL, one], cwd=ROOT, capture_output=True, check=True).stdout.decode()
        self.assertEqual(out.splitlines(), ["render.js: not a one-page PDF as Chromium writes it (or one that was trimmed before)"] * 3)


class PublishedFilesTests(unittest.TestCase):
    def test_published_svgs_are_up_to_date(self):
        for lang, size, edition, stem in build.VERSIONS:
            with self.subTest(stem):
                with open(os.path.join(ROOT, lang, stem + ".svg")) as f:
                    self.assertEqual(f.read(), build.version(lang, size, edition)[0], "run python3 build.py --render")

    def test_every_version_has_a_pdf_and_no_png(self):
        for lang, _, _, stem in build.VERSIONS:
            self.assertTrue(os.path.isfile(os.path.join(ROOT, lang, stem + ".pdf")), f"{lang}/{stem}.pdf")
        self.assertEqual([n for d in ("de", "en") for n in os.listdir(os.path.join(ROOT, d)) if n.endswith(".png")], [])

    def test_the_readme_links_every_version_as_pdf_and_svg(self):
        with open(os.path.join(ROOT, "README.md")) as f:
            links = set(re.findall(r"\]\(((?:de|en)/[^)]+)\)", f.read()))
        for path in links:
            self.assertTrue(os.path.isfile(os.path.join(ROOT, path)), path)
        for lang, _, _, stem in build.VERSIONS:
            for ext in (".pdf", ".svg"):
                self.assertIn(f"{lang}/{stem}{ext}", links)

    def test_every_binary_goes_through_git_lfs(self):
        git = lambda *args: subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=True).stdout
        files = git("ls-files", "*.pdf").decode().split()
        self.assertTrue(files)
        for name in files:
            with self.subTest(name):
                self.assertTrue(git("show", ":" + name).startswith(b"version https://git-lfs.github.com/spec/v1"))


if __name__ == "__main__":
    unittest.main()
