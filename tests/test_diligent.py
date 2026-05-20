import unittest

from ccsd_board_watch.diligent import extract_personnel_attachments


class DiligentTests(unittest.TestCase):
    def test_extract_personnel_attachment_from_agenda_html(self):
        html = """
        <table><tr><td>8.02</td><td><h3>Unified Personnel Promotions and Transfers/Reassignments.</h3>
        <p>[Contact Person: RoAnn Triana]</p></td></tr>
        <tr><td></td><td><h4><a href="/document/abc-123">05.14.26 Info. 8.02.pdf</a></h4></td></tr></table>
        """

        attachments = extract_personnel_attachments(html, "https://example.test")

        self.assertEqual(len(attachments), 1)
        self.assertEqual(attachments[0].item_number, "8.02")
        self.assertEqual(attachments[0].movement_type, "promotion_transfer")
        self.assertEqual(attachments[0].document_url, "https://example.test/document/abc-123")

    def test_extracts_personnel_employment_as_new_hire(self):
        html = """
        <table><tr><td>3.08</td><td><h3>Licensed Personnel Employment.</h3>
        <p>Discussion and possible action on approval to employ licensed personnel, as listed.</p></td></tr>
        <tr><td></td><td><h4><a href="/document/hire-123">05.14.26 Ref. 3.08.pdf</a></h4></td></tr></table>
        """

        attachments = extract_personnel_attachments(html, "https://example.test")

        self.assertEqual(len(attachments), 1)
        self.assertEqual(attachments[0].item_number, "3.08")
        self.assertEqual(attachments[0].movement_type, "new_hire")

    def test_extracts_imported_agenda_item_context(self):
        html = """
        <div class="container item agendaorder">
          <dl><dt>Subject</dt><dd>2.13 Licensed Personnel Employment.</dd></dl>
          <dl><dt>Meeting</dt><dd>Jun 12, 2025 - Agenda, Regular Board Meeting</dd></dl>
          <div class="itembody"><p>[Contact Person: RoAnn Triana] (Ref. 2.13)</p></div>
          <div class="public-file print-file"><a href="/document/hire-old">06.12.25 Ref. 2.13.pdf</a></div>
        </div>
        """

        attachments = extract_personnel_attachments(html, "https://example.test")

        self.assertEqual(len(attachments), 1)
        self.assertEqual(attachments[0].item_number, "2.13")
        self.assertEqual(attachments[0].movement_type, "new_hire")

    def test_ignores_governance_policy_employment_language(self):
        html = """
        <table><tr><td>4.13</td><td><h3>Adoption of Governance Policies GP-10: Employment and Duties of Superintendent Performance.</h3></td></tr>
        <tr><td></td><td><h4><a href="/document/policy">05.07.26 Ref. 4.13.pdf</a></h4></td></tr></table>
        """

        attachments = extract_personnel_attachments(html, "https://example.test")

        self.assertEqual(attachments, [])
