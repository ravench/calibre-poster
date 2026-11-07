"""Tests for the calibre wall poster: python3 -m unittest discover -s tests"""
import os, re, subprocess, sys, unittest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)
import poster  # noqa: E402
from cartridges import CATALOGUE  # noqa: E402
import build  # noqa: E402
import outline  # noqa: E402

ALL = [s for _, items in CATALOGUE for s in items]


class MergeIdenticalTests(unittest.TestCase):
    def test_identical_measurements_share_one_drawing(self):
        groups = [g["names"] for g in poster.merge_identical(ALL) if len(g["names"]) > 1]
        self.assertEqual(sorted(map(sorted, groups)),
                         sorted([sorted([".308 Winchester", "7.62x51 mm NATO"]),
                                 sorted([".223 Remington", "5.56x45 mm NATO", "5.6 mm GP 90"]),
                                 sorted([".45 ACP", ".45 Super"])]))

    def test_no_cartridge_is_lost_or_doubled(self):
        names = [n for g in poster.merge_identical(ALL) for n in g["names"]]
        self.assertEqual(sorted(names), sorted(s["name"] for s in ALL))

    def test_same_groups_as_the_calibre_data(self):
        merged = [g["names"] for g in poster.merge_identical(ALL) if len(g["names"]) > 1]
        self.assertEqual(sorted(map(sorted, merged)), sorted(map(sorted, outline.identical_groups())))

    def test_similar_but_different_cartridges_stay_apart(self):
        groups = {n: i for i, g in enumerate(poster.merge_identical(ALL)) for n in g["names"]}
        self.assertNotEqual(groups["7.5x55 mm Swiss (GP 11)"], groups["7.5x53.5 mm Swiss (GP 1890)"])
        self.assertNotEqual(groups["9x19 mm"], groups["9x21 mm IMI"])

    def test_combined_label_lists_every_name(self):
        poster.LANG = "de"
        lines, extra = poster.label_lines(["7.62x51 mm NATO", ".308 Winchester"])
        self.assertEqual(lines, ["7.62x51 mm NATO", ".308 Winchester"])
        self.assertEqual(extra, ["gleiche Masse"])
        lines, _ = poster.label_lines(["7.5x55 mm Swiss (GP 11)", "9x19 mm"])
        self.assertEqual(lines[0], "7.5x55 mm Swiss", "parenthetical part is dropped in a combined label")


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
        n = re.search(r"(\d+) Patronen und Geschosse", svg)
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
        """(length, diameter) of every drawing, as printed under it, in poster order."""
        num = lambda t: float(t.replace(",", "."))
        return [(num(l), num(d)) for d, l in re.findall(r">Ø ([\d,.]+) · ([\d,.]+) mm<", svg)]

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
        self.assertEqual(self.printed(svg), [(64.0, 16.0), (64.0, 17.6), (64.0, 18.9), (64.0, 20.6)])

    def test_length_as_printed_decides_before_the_diameter(self):
        # 84.84 mm is printed as 84.8 mm, so the thinner bullet comes first.
        self.assertLess(poster.section_order({"oal": 84.84, "bullet": 6.7}), poster.section_order({"oal": 84.8, "bullet": 7.8}))


class SelectionTests(unittest.TestCase):
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

    def test_selection_fits_and_one_more_does_not(self):
        ranked = poster.ranked()
        for size in ("A3", "A1"):
            n = len(poster.most_that_fit(size))
            self.assertLessEqual(poster.build(size, 1.0, "de", names=set(ranked[:n]))[2], 0)
            self.assertGreater(poster.build(size, 1.0, "de", names=set(ranked[:n + 1]))[2], 0)

    def test_every_listed_share_is_a_catalogue_calibre(self):
        import json
        share = json.load(open(poster.SHARE_FILE))["share"]
        self.assertLessEqual(set(share), {s["name"] for s in ALL})


class SwissServiceTests(unittest.TestCase):
    def test_every_service_cartridge_is_in_the_catalogue(self):
        names = {s["name"] for s in ALL}
        for row in poster.SWISS_SERVICE:
            self.assertIn(row[0], names)

    def test_oldest_first_and_fits_a3_landscape(self):
        svg, _, over, rows = poster.build("A3-quer", 1.0, "de", swiss=True)
        self.assertLessEqual(over, 0)
        self.assertEqual(rows, 1)
        self.assertLess(svg.index("Milbank-Amsler"), svg.index("Pist Pat 41"))
        self.assertLess(svg.index("Pist Pat 41"), svg.index("Zf Stgw 20"))

    def test_swiss_names_lead_and_english_uses_points(self):
        de = poster.build("A3-quer", 1.0, "de", swiss=True)[0]
        en = poster.build("A3-quer", 1.0, "en", swiss=True)[0]
        for name in ("Pist Pat 03", "Pist Pat 41", "GP 11", "GP 90", "GP 1890"):
            self.assertIn(f">{name}<", de)
        self.assertIn("Ordonnanzpatronen der Schweizer Armee", de)
        self.assertIn("Swiss Army Service Cartridges", en)
        self.assertIn("10.4 mm", en)
        self.assertNotIn("10,4 mm", en)


class MaterialTests(unittest.TestCase):
    def test_materials_get_their_own_fill(self):
        spec = {s["name"]: s for s in ALL}
        def svg(name):
            s = spec[name]
            return poster.cartridge_svg(s, outline.outline(s), 0, 0, 1.0)
        self.assertIn("url(#steel)", svg("7.62x39 mm"))      # steel case
        self.assertIn("url(#lead)", svg(".22 LR"))           # lead bullet
        self.assertIn("url(#paper)", svg("7.5x53.5 mm Swiss (GP 1890)"))


class PublishedFilesTests(unittest.TestCase):
    def test_published_svgs_are_up_to_date(self):
        for lang, size, edition, stem, _ in build.VERSIONS:
            with self.subTest(stem):
                with open(os.path.join(ROOT, lang, stem + ".svg")) as f:
                    self.assertEqual(f.read(), build.version(lang, size, edition)[0], "run python3 build.py --render")

    def test_every_version_has_pdf_and_preview(self):
        for lang, _, _, stem, suffix in build.VERSIONS:
            for name in (stem + ".pdf", f"{stem}-{suffix}.png"):
                self.assertTrue(os.path.isfile(os.path.join(ROOT, lang, name)), f"{lang}/{name}")

    def test_every_binary_goes_through_git_lfs(self):
        git = lambda *args: subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=True).stdout
        files = git("ls-files", "*.png", "*.pdf").decode().split()
        self.assertTrue(files)
        for name in files:
            with self.subTest(name):
                self.assertTrue(git("show", ":" + name).startswith(b"version https://git-lfs.github.com/spec/v1"))


if __name__ == "__main__":
    unittest.main()
