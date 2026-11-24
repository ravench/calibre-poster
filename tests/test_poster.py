"""Tests for the calibre wall poster: python3 -m unittest discover -s tests"""
import os, re, subprocess, sys, unittest

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
    return re.findall(r">([^<>]+)<", svg)


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
            self.assertIn(f"Druck ohne Skalierung (100 %) auf A3: Massstab {scale}. Abmessungen gerundet nach CIP/SAAMI, "
                          "Geschossform schematisch. Keine Ladedaten.", printed)

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
            self.assertLessEqual(poster.build(size, 1.0, "de", names=set(names))[2], 0)
            self.assertGreater(poster.build(size, 1.0, "de", names=set(pool[:len(names) + 1]))[2], 0)

    def test_no_section_of_only_a_few_airgun_or_black_powder(self):
        cat_of = {s["name"]: cat for cat, items in CATALOGUE for s in items}
        for lang, size, edition, stem in build.VERSIONS:
            if edition != "fit":
                continue
            names = poster.most_that_fit(size, lang)
            for cat in poster.SMALL_SECTIONS:
                with self.subTest(stem=stem, cat=cat):
                    n = sum(cat_of[x] == cat for x in names)
                    self.assertTrue(n == 0 or n >= poster.MIN_SECTION, n)
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
