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

    def test_combines_transfer_between_two_watched_schools(self):
        text = """
        TRANSFERS/REASSIGNMENTS:
        April 20, 2026
        Shawana F. King Assistant Principal Assistant Principal   TBD
        Martin MS Rundle ES
        RoAnn Triana
        May 14, 2026
        """
        attachment = Attachment("8.02", "Unified Personnel Promotions and Transfers/Reassignments.", "Info 8.02.pdf", "doc", "https://example.test/doc", "promotion_transfer")
        meeting = Meeting(1678, "Regular Board Meeting - May 14 2026", "May 14, 2026", "https://example.test/meeting")
        schools = [
            School("martin_ms", "Cluster 5", "Martin MS", ("Martin MS", "Martin"), "clusters 1-10.png"),
            School("rundle_es", "Cluster 4", "Rundle ES", ("Rundle ES", "Rundle"), "clusters 1-10.png"),
        ]

        findings = find_school_personnel_matches(text, attachment, meeting, schools)

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].person_name, "Shawana F. King")
        self.assertEqual(findings[0].school_name, "Martin MS -> Rundle ES")
        self.assertEqual(findings[0].cluster, "Cluster 5 -> Cluster 4")
        self.assertEqual(findings[0].school_ids, ["martin_ms", "rundle_es"])
        self.assertEqual(findings[0].clusters, ["Cluster 5", "Cluster 4"])
        self.assertEqual(findings[0].from_school_name, "Martin MS")
        self.assertEqual(findings[0].to_school_name, "Rundle ES")
        self.assertEqual(findings[0].effective_date, "TBD")

    def test_ignores_new_hire_resume_company_location_matches(self):
        text = """
        Experience:
        The MIDAS Consulting Group LLC
        Las Vegas, NV (2021-present)
        Senior Vice President, Client Development
        Catapult Fundraising, Inc.
        Las Vegas, NV (2022-2024)
        Roseman University of Health Services
        Las Vegas, NV (2019-2021)
        """
        attachment = Attachment("3.07", "Approval to Employ Licensed Personnel.", "Info 3.07.pdf", "doc", "https://example.test/doc", "new_hire")
        meeting = Meeting(1678, "Regular Board Meeting - May 14 2026", "May 14, 2026", "https://example.test/meeting")
        school = School("las_vegas_hs", "Cluster 6", "Las Vegas HS", ("Las Vegas HS", "Las Vegas"), "clusters 1-10.png")

        findings = find_school_personnel_matches(text, attachment, meeting, [school])

        self.assertEqual(findings, [])

    def test_matches_wrapped_last_name_without_borrowing_previous_row(self):
        text = """
        Name School and Assignment Date Date Reason
        Shawn Drinkard Ronzone ES 07/31/24 05/27/26 Accepted Position
        Physical Education in Other District
        Michaelene  Lowman ES 08/15/07 05/27/26 Retirement
        Duncan-Holstein Second Grade
        """
        attachment = Attachment("8.04", "Licensed Personnel Separations.", "Info 8.04.pdf", "doc", "https://example.test/doc", "separation")
        meeting = Meeting(1678, "Regular Board Meeting - May 14 2026", "May 14, 2026", "https://example.test/meeting")
        school = School("lowman_es", "Cluster 21", "Lowman ES", ("Lowman ES", "Lowman"), "clusters 21-30.png")

        findings = find_school_personnel_matches(text, attachment, meeting, [school])

        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0].person_name, "Michaelene Duncan-Holstein")
        self.assertEqual(findings[0].reason, "Retirement")

    def test_ignores_staffing_report_attachments(self):
        text = """
        SUPPORT PROFESSIONAL AND SCHOOL POLICE STAFFING REPORT
        Wallin ES Custodian Vacancy
        """
        attachment = Attachment("8.05", "Support Professional and School Police Staffing Report.", "Info 8.05.pdf", "doc", "https://example.test/doc", "staffing_report")
        meeting = Meeting(1678, "Regular Board Meeting - May 14 2026", "May 14, 2026", "https://example.test/meeting")
        school = School("wallin_es", "Cluster 11", "Wallin ES", ("Wallin ES", "Wallin"), "clusters 11-20.png")

        findings = find_school_personnel_matches(text, attachment, meeting, [school])

        self.assertEqual(findings, [])
