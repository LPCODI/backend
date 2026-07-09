import asyncio
import tempfile
import unittest
from pathlib import Path

from app.core import ApiError
from app.domain import ErrorCode
from app.services import AnalysisInput, PdfDocumentParserService
from app.services.interfaces import DocumentParserService

try:
    import fitz
except ImportError:  # pragma: no cover - exercised only when document extra is absent.
    fitz = None


@unittest.skipIf(fitz is None, "PyMuPDF is not installed")
class PdfDocumentParserTest(unittest.TestCase):
    def test_pdf_parser_extracts_page_text_and_images(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "demo.pdf"
            image_path = Path(temp_dir) / "pixel.png"
            image_path.write_bytes(
                bytes.fromhex(
                    "89504e470d0a1a0a0000000d4948445200000001000000010804000000b51c0c02"
                    "0000000b4944415478da63fcff1f0003030200efbfa7db0000000049454e44ae426082"
                )
            )
            document = fitz.open()
            page = document.new_page(width=640, height=480)
            page.insert_text((72, 72), "Problem Definition", fontsize=18)
            page.insert_text((72, 110), "Users need structured practice.", fontsize=12)
            page.insert_image(fitz.Rect(72, 150, 120, 198), filename=str(image_path))
            document.save(pdf_path)
            document.close()

            result = asyncio.run(
                PdfDocumentParserService().parse(
                    AnalysisInput(resource_id="file-1", file_path=pdf_path),
                )
            )

        self.assertIsInstance(PdfDocumentParserService(), DocumentParserService)
        self.assertEqual(result.provider, "pymupdf")
        self.assertEqual(len(result.slides), 1)
        parsed_slide = result.slides[0]
        self.assertEqual(parsed_slide["slideNumber"], 1)
        self.assertEqual(parsed_slide["sortOrder"], 1)
        self.assertEqual(parsed_slide["title"], "Problem Definition")
        self.assertIn("Users need structured practice.", parsed_slide["body"])
        self.assertIn("Problem Definition", parsed_slide["rawText"])
        self.assertEqual(parsed_slide["notes"], None)
        self.assertEqual(parsed_slide["tables"], [])
        self.assertEqual(parsed_slide["graphs"], [])
        self.assertEqual(parsed_slide["images"][0]["extension"], "png")

    def test_pdf_parser_rejects_non_pdf_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "demo.pptx"
            source_path.write_bytes(b"not a pdf")

            with self.assertRaises(ApiError) as error_context:
                asyncio.run(
                    PdfDocumentParserService().parse(
                        AnalysisInput(resource_id="file-1", file_path=source_path),
                    )
                )

        self.assertEqual(error_context.exception.code, ErrorCode.PRESENTATION_FILE_UNSUPPORTED_TYPE)

    def test_pdf_parser_rejects_missing_pdf_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            missing_path = Path(temp_dir) / "missing.pdf"

            with self.assertRaises(ApiError) as error_context:
                asyncio.run(
                    PdfDocumentParserService().parse(
                        AnalysisInput(resource_id="file-1", file_path=missing_path),
                    )
                )

        self.assertEqual(error_context.exception.code, ErrorCode.PRESENTATION_FILE_NOT_FOUND)


if __name__ == "__main__":
    unittest.main()
