"""Clearly synthetic receipt evidence. Audio uses the existing opt-in TTS adapter."""

import asyncio
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from aquaclean.config import Settings
from aquaclean.infrastructure.llm.provider import GeminiProvider


async def main():
    root = Path("artifacts/semana10/media")
    root.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (1200, 850), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 30)
    text = "AQUA CLEAN · EVIDENCIA SINTÉTICA\nRecepción en mostrador, sin pedido previo\nCliente: Lucía Muestra (sintética)\n2 camisas, lavado por prenda\nObservación: botón flojo en una camisa\nPrendas recibidas y contadas por operador demo\nSin pesaje: servicio por prenda\nNo es inspección final de calidad\nSin datos personales reales ni validez fiscal"
    draw.multiline_text((50, 60), text, font=font, fill="#0f172a", spacing=22)
    image.save(root / "recepcion-sintetica.png")
    image.save(root / "recepcion-sintetica.pdf", "PDF", resolution=120)
    provider = GeminiProvider(Settings())
    try:
        audio = await provider.synthetic_audio(
            "Esta es una evidencia sintética para Aqua Clean. En mostrador recibí dos camisas de Lucía Muestra. Una tiene un botón flojo. Solicita lavado por prenda. No declaro inspección final ni pago bancario."
        )
        with wave.open(str(root / "recepcion-sintetica.wav"), "wb") as stream:
            stream.setnchannels(1)
            stream.setsampwidth(2)
            stream.setframerate(24000)
            stream.writeframes(audio)
        print(
            {
                "synthetic": True,
                "generated_fixture": ["PNG", "PDF", "WAV"],
                "tts_provider": "Gemini",
                "cost_usd": None,
            }
        )
    finally:
        if provider.client:
            await provider.client.aio.aclose()
            provider.client.close()


if __name__ == "__main__":
    asyncio.run(main())
