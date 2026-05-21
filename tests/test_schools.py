import csv
from pathlib import Path
import tempfile
import unittest

from ccsd_board_watch.models import School
from ccsd_board_watch.schools import cluster_sort_key, load_schools, save_schools, school_id_from_name


class SchoolConfigTests(unittest.TestCase):
    def test_school_id_from_name_is_unique(self):
        self.assertEqual(school_id_from_name("Wallin ES", {"wallin_es"}), "wallin_es_2")

    def test_cluster_sort_key_sorts_numbered_clusters_numerically(self):
        clusters = ["Cluster 10", "Cluster 2", "Cluster 1", "Henderson"]

        self.assertEqual(sorted(clusters, key=cluster_sort_key), ["Cluster 1", "Cluster 2", "Cluster 10", "Henderson"])

    def test_default_school_file_has_explicit_aliases(self):
        with Path("data/schools.csv").open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))

        self.assertEqual(319, len(rows))
        self.assertFalse([row["school_id"] for row in rows if not row["aliases"].strip()])

    def test_default_school_file_includes_screenshot_style_aliases(self):
        schools = {school.school_id: school for school in load_schools(Path("data/schools.csv"))}

        self.assertIn("Harris, G", schools["harris_g_es"].aliases)
        self.assertIn("Miller, S", schools["miller_s_es"].aliases)
        self.assertIn("H.M. Brown", schools["h_m_brown_es"].aliases)
        self.assertIn("Chaparral High School", schools["chaparral_hs"].aliases)

    def test_save_and_load_schools_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "schools.csv"
            schools = [
                School(
                    school_id="wallin_es",
                    cluster="Henderson",
                    display_name="Wallin ES",
                    aliases=("Wallin ES", "Wallin Elementary School"),
                    source_image="manual",
                )
            ]

            save_schools(path, schools)

            self.assertEqual(load_schools(path), schools)
