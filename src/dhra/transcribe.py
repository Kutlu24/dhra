"""Pluggable transcription -- DHRA_BUILD_SPEC.md section 16 ("Transcription:
pluggable; Tesseract baseline, interface designed for HTR engines
(Kraken/Transkribus) since manuscript material is the real target").

Every `Transcriber` returns a `TranscriptionResult` carrying its own
`producer`/`producer_version` -- callers pass these straight into
`DHRARepo.create_representation`, which rejects an unversioned one at
write time (section 4.3).

Phase 1 wires two real, working backends (plain text passthrough, and
PDF text extraction via the system `pdftotext`). Image OCR (Tesseract/
Kraken) is defined behind the same protocol but NOT wired in this
environment -- no OCR binary is installed/verified here. Faking that
integration would violate section 0 rule 4 ("prefer refusing to
guessing"); see OPEN_QUESTIONS.md.
"""

from __future__ import annotations

import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from dhra.models import Quality


@dataclass(frozen=True)
class TranscriptionResult:
    text: str
    producer: str
    producer_version: str
    quality: Quality | None = None


class Transcriber(Protocol):
    def transcribe(self, data: bytes) -> TranscriptionResult: ...


class ManualTranscriber:
    """Text supplied by the researcher (manual_upload / already-transcribed
    text and TEI sources go through the format-specific transcribers
    below, not this one, but this is the honest baseline: a human
    already did the transcription, we are just recording it)."""

    producer_version = "1"

    def transcribe(self, data: bytes) -> TranscriptionResult:
        return TranscriptionResult(
            text=data.decode("utf-8"),
            producer="manual",
            producer_version=self.producer_version,
            quality=Quality(manually_corrected=True),
        )


class PdfToTextTranscriber:
    """Real backend: shells out to the system `pdftotext` (poppler-utils).
    Not an OCR engine -- only extracts embedded text layers; a scanned
    PDF with no text layer will come back empty, which is a truthful
    result, not a failure to paper over."""

    def __init__(self, binary: str = "pdftotext"):
        self.binary = binary
        self._version = self._detect_version()

    def _detect_version(self) -> str:
        proc = subprocess.run([self.binary, "-v"], capture_output=True, text=True)
        first_line = (proc.stdout or proc.stderr).splitlines()[0] if (proc.stdout or proc.stderr) else ""
        return first_line.strip() or "unknown"

    def transcribe(self, data: bytes) -> TranscriptionResult:
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".pdf") as src:
            src.write(data)
            src.flush()
            proc = subprocess.run(
                [self.binary, "-layout", src.name, "-"],
                capture_output=True,
                text=True,
                check=True,
            )
        return TranscriptionResult(
            text=proc.stdout,
            producer="pdftotext",
            producer_version=self._version,
        )


class TeiTranscriber:
    """Extracts plain text from TEI XML (the `text` division), stripping
    markup but not normalising the content itself (I9: normalisation
    never alters displayed text -- this just decodes XML to a string)."""

    producer_version = "stdlib-xml.etree"

    def transcribe(self, data: bytes) -> TranscriptionResult:
        root = ET.fromstring(data)
        texts = []
        for elem in root.iter():
            tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
            if tag == "text":
                texts.append("".join(elem.itertext()))
        text = "\n".join(texts) if texts else "".join(root.itertext())
        return TranscriptionResult(
            text=text.strip(),
            producer="tei_extract",
            producer_version=self.producer_version,
        )
