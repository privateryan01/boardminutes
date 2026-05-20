from pathlib import Path
import tempfile
import unittest

from ccsd_board_watch.models import School
from ccsd_board_watch.schools import load_schools, save_schools, school_id_from_name


class SchoolConfigTests(unittest.TestCase):
    def test_school_id_from_name_is_unique(self):
        self.assertEqual(school_id_from_name("Wallin ES", {"wallin_es"}), "wallin_es_2")

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
