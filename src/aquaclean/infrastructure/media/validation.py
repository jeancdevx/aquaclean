import io
import warnings
from pathlib import Path

from PIL import Image
from pypdf import PdfReader

from aquaclean.config import Settings
from aquaclean.domain.errors import DomainError

MIMES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".pdf": "application/pdf",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
}


def validate(data: bytes, filename: str, settings: Settings) -> dict:
    if not data or len(data) > settings.max_upload_mb * 1024 * 1024:
        raise DomainError("Archivo vacío o supera el tamaño permitido.", "invalid_file", 413)
    suffix = Path(filename).suffix.lower()
    expected = MIMES.get(suffix)
    if not expected:
        raise DomainError("Formato permitido: JPG, PNG, WebP, PDF, MP3 o WAV.", "invalid_file", 415)
    info: dict = {"mime": expected, "pages": None, "duration": None}
    try:
        if expected.startswith("image/"):
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                image = Image.open(io.BytesIO(data))
                if image.width * image.height > 25_000_000:
                    raise ValueError("image pixel limit")
                actual = Image.MIME.get(image.format or "")
                image.verify()
            if actual != expected:
                raise ValueError("mime mismatch")
        elif expected == "application/pdf":
            if not data.startswith(b"%PDF-"):
                raise ValueError("not pdf")
            pdf = PdfReader(io.BytesIO(data))
            if pdf.is_encrypted or not 0 < len(pdf.pages) <= settings.max_pdf_pages:
                raise ValueError("pdf encrypted/pages")
            info["pages"] = len(pdf.pages)
        else:
            if suffix == ".wav":
                if not data.startswith(b"RIFF") or data[8:12] != b"WAVE":
                    raise ValueError("not wav")
                from mutagen.wave import WAVE

                audio = WAVE(io.BytesIO(data))
            else:
                from mutagen.mp3 import MP3

                audio = MP3(io.BytesIO(data))
            if not audio.info or not 0 < audio.info.length <= settings.max_audio_seconds:
                raise ValueError("audio duration")
            info["duration"] = audio.info.length
    except Exception as exc:
        raise DomainError(
            "Contenido inválido, tipo incompatible o límite de páginas/duración excedido.",
            "invalid_file",
            415,
        ) from exc
    return info
