import asyncio
import subprocess
import tempfile
import unittest
from pathlib import Path

from app.core import ApiError
from app.domain import ErrorCode
from app.services import (
    AnalysisInput,
    DocDocumentParserService,
    DocumentParseResult,
    DocumentParserService,
    LibreOfficeDocumentConverter,
    PptDocumentParserService,
)


class FakeConvertedDocumentParser:
    def __init__(self, *, expected_suffix: str) -> None:
        self.expected_suffix = expected_suffix
        self.received_path: Path | None = None

    async def parse(self, source: AnalysisInput) -> DocumentParseResult:
        assert source.file_path is not None
        self.received_path = source.file_path
        if source.file_path.suffix != self.expected_suffix:
            raise AssertionError(f"unexpected converted suffix: {source.file_path.suffix}")
        return DocumentParseResult(
            provider="fake-parser",
            version="test",
            slides=(
                {
                    "slideNumber": 1,
                    "sortOrder": 1,
                    "title": "Converted",
                    "body": "Parsed through converted source.",
                    "rawText": "Converted\nParsed through converted source.",
                    "notes": None,
                    "tables": [],
                    "graphs": [],
                    "images": [],
                },
            ),
            warnings=("fake parser warning",),
        )


class LibreOfficeDocumentConversionTest(unittest.TestCase):
    def test_converter_runs_headless_command_and_returns_converted_path(self) -> None:
        captured_commands: list[list[str]] = []

        def fake_runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            captured_commands.append(command)
            output_dir = Path(command[command.index("--outdir") + 1])
            source_path = Path(command[-1])
            target_extension = str(command[command.index("--convert-to") + 1])
            (output_dir / f"{source_path.stem}.{target_extension}").write_bytes(b"converted")
            return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "legacy.ppt"
            source_path.write_bytes(b"legacy")
            output_dir = Path(temp_dir) / "converted"

            converted_path = LibreOfficeDocumentConverter(command_runner=fake_runner).convert(
                source_path,
                output_dir=output_dir,
                target_extension=".pptx",
            )

        self.assertEqual(converted_path.name, "legacy.pptx")
        self.assertEqual(captured_commands[0][0], "libreoffice")
        self.assertIn("--headless", captured_commands[0])
        self.assertEqual(captured_commands[0][captured_commands[0].index("--convert-to") + 1], "pptx")

    def test_converter_reports_missing_libreoffice_as_dependency_error(self) -> None:
        def missing_runner(
            command: list[str],
            **kwargs: object,
        ) -> subprocess.CompletedProcess[str]:
            del command, kwargs
            raise FileNotFoundError("libreoffice")

        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "legacy.doc"
            source_path.write_bytes(b"legacy")
            with self.assertRaises(ApiError) as error_context:
                LibreOfficeDocumentConverter(command_runner=missing_runner).convert(
                    source_path,
                    output_dir=Path(temp_dir) / "converted",
                    target_extension=".docx",
                )

        self.assertEqual(error_context.exception.code, ErrorCode.DEPENDENCY_UNAVAILABLE)

    def test_ppt_parser_converts_to_pptx_before_delegating(self) -> None:
        def fake_runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            output_dir = Path(command[command.index("--outdir") + 1])
            source_path = Path(command[-1])
            (output_dir / f"{source_path.stem}.pptx").write_bytes(b"converted")
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "legacy.ppt"
            source_path.write_bytes(b"legacy")
            fake_parser = FakeConvertedDocumentParser(expected_suffix=".pptx")
            parser = PptDocumentParserService(
                converter=LibreOfficeDocumentConverter(command_runner=fake_runner),
                pptx_parser=fake_parser,
            )

            result = asyncio.run(
                parser.parse(AnalysisInput(resource_id="file-1", file_path=source_path))
            )

        self.assertIsInstance(parser, DocumentParserService)
        self.assertEqual(result.provider, "libreoffice-headless+python-pptx")
        self.assertEqual(result.slides[0]["title"], "Converted")
        self.assertTrue(result.warnings[0].startswith("Converted legacy PPT"))
        self.assertEqual(fake_parser.received_path.name, "legacy.pptx")

    def test_doc_parser_converts_to_docx_before_delegating(self) -> None:
        def fake_runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            output_dir = Path(command[command.index("--outdir") + 1])
            source_path = Path(command[-1])
            (output_dir / f"{source_path.stem}.docx").write_bytes(b"converted")
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "legacy.doc"
            source_path.write_bytes(b"legacy")
            fake_parser = FakeConvertedDocumentParser(expected_suffix=".docx")
            parser = DocDocumentParserService(
                converter=LibreOfficeDocumentConverter(command_runner=fake_runner),
                docx_parser=fake_parser,
            )

            result = asyncio.run(
                parser.parse(AnalysisInput(resource_id="file-1", file_path=source_path))
            )

        self.assertIsInstance(parser, DocumentParserService)
        self.assertEqual(result.provider, "libreoffice-headless+python-docx")
        self.assertEqual(result.slides[0]["title"], "Converted")
        self.assertTrue(result.warnings[0].startswith("Converted legacy DOC"))
        self.assertEqual(fake_parser.received_path.name, "legacy.docx")


if __name__ == "__main__":
    unittest.main()
