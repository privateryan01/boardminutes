import unittest

from ccsd_board_watch.matcher import find_school_personnel_matches
from ccsd_board_watch.models import Attachment, Meeting, School


class MatcherTests(unittest.TestCase):
    def test_matches_school_and_person_from_separation_row(self):
        text = """
        INFORMATION ON LICENSED PERSONNEL SEPARATIONS
        Name School and Assignment Date Date Reason
        Danielle Belen Wallin ES 07/26/23 05/27/26 Relocation
        Third Grade
        """
        attachment = Attachment("8.04", "Licensed Personnel Separations.", "Info 8.04.pdf", "doc", "https://example.test/doc", "separation")
        meeting = Meeting(1678, "Regular Board Meeting - May 14 2026", "May 14, 2026", "https://example.test/meeting")
        school = School("wallin_es", "Henderson", "Wallin ES", ("Wallin ES", "Wallin"), "henderson cluster.png")

        findings = find_school_personnel_matches(text, attachment, meeting, [school])

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].school_name, "Wallin ES")
        self.assertEqual(findings[0].person_name, "Danielle Belen")
        self.assertEqual(findings[0].reason, "Relocation")
        self.assertEqual(findings[0].effective_date, "05/27/26")

    def test_matches_school_from_previous_promotion_name_line(self):
        text = """
        PROMOTIONS:
        Name From To Effective Date
        April L. McCartney Assistant Principal Coordinator IV April 27, 2026
        Gunderson MS Multi-Tiered System of Supports
        """
        attachment = Attachment("8.02", "Unified Personnel Promotions and Transfers/Reassignments.", "Info 8.02.pdf", "doc", "https://example.test/doc", "promotion_transfer")
        meeting = Meeting(1678, "Regular Board Meeting - May 14 2026", "May 14, 2026", "https://example.test/meeting")
        school = School("gunderson_ms", "Southwest Vegas", "Gunderson MS", ("Gunderson MS", "Gunderson"), "southwest vegas cluster.png")

        findings = find_school_personnel_matches(text, attachment, meeting, [school])

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].school_name, "Gunderson MS")
        self.assertEqual(findings[0].person_name, "April L. McCartney")
        self.assertEqual(findings[0].confidence, "high")

    def test_matches_school_and_person_from_new_hire_row(self):
        text = """
        CLARK COUNTY SCHOOL DISTRICT
        LICENSED PERSONNEL EMPLOYMENT
        LAST NAME FIRST NAME WORK LOCATION ASSIGNMENT EFFECTIVE SALARY START DATE
        PEDROZA MARLENE WALLIN ES GRADE 2 6,363.27$ 05/01/2026
        NUMBER OF CONTRACTS: 1
        """
        attachment = Attachment("3.08", "Licensed Personnel Employment.", "Info 3.08.pdf", "doc", "https://example.test/doc", "new_hire")
        meeting = Meeting(1678, "Regular Board Meeting - May 14 2026", "May 14, 2026", "https://example.test/meeting")
        school = School("wallin_es", "Henderson", "Wallin ES", ("Wallin ES", "Wallin"), "henderson cluster.png")

        findings = find_school_personnel_matches(text, attachment, meeting, [school])

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].school_name, "Wallin ES")
        self.assertEqual(findings[0].movement_type, "new_hire")
        self.assertEqual(findings[0].person_name, "PEDROZA MARLENE")
        self.assertEqual(findings[0].effective_date, "05/01/2026")
        self.assertEqual(findings[0].confidence, "high")

    def test_uses_previous_line_date_for_promotion_transfer_school_line(self):
        text = """
        TRANSFERS/REASSIGNMENTS:
        Hannibal A. Nisperos Assistant Principal Assistant Principal   April 16, 2026
        Blackhurst ES  Derfelt ES
        Guillermo E. Vivas Assistant Principal Dean of Students  July 29, 2026
        """
        attachment = Attachment("8.06", "Unified Personnel Promotions and Transfers/Reassignments.", "Info 8.06.pdf", "doc", "https://example.test/doc", "promotion_transfer")
        meeting = Meeting(1671, "Regular Board Meeting - Apr 23 2026", "April 23, 2026", "https://example.test/meeting")
        school = School("blackhurst_es", "Southwest Vegas", "Blackhurst ES", ("Blackhurst ES", "Blackhurst"), "southwest vegas cluster.png")

        findings = find_school_personnel_matches(text, attachment, meeting, [school])

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].person_name, "Hannibal A. Nisperos")
        self.assertEqual(findings[0].effective_date, "April 16, 2026")
