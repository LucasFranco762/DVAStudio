"""Configuração do compositor antes da inicialização do WebEngine."""
import os


def configure_webengine() -> None:
    if os.name != "nt":
        return
    flags = os.environ.get("QTWEBENGINE_CHROMIUM_FLAGS", "")
    # O compartilhamento de texturas D3D/Skia pode perder o contexto no Windows
    # e deixar o view preto. A composição por software evita esse caminho.
    if "--disable-gpu" not in flags.split():
        os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = (flags + " --disable-gpu").strip()
