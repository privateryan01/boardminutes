from io import BytesIO
import unittest

from pypdf import PdfWriter

from ccsd_board_watch.pdf_text import extract_pdf_text


class PdfTextTests(unittest.TestCase):
    def test_extract_pdf_text_rejects_too_many_pages(self):
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        writer.add_blank_page(width=72, height=72)
        buffer = BytesIO()
        writer.write(buffer)

        with self.assertRaises(ValueError):
            extract_pdf_text(buffer.getvalue(), max_pages=1)


if __name__ == "__main__":
    unittest.main()
