# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

runtime = Path(os.environ.get('DVASTUDIO_BUILD_RUNTIME', 'build/runtime')).resolve()
for binary in ('node.exe', 'ffmpeg.exe'):
    if not (runtime / binary).is_file():
        raise RuntimeError('Use python Gerar_executavel.py para preparar os componentes da distribuição.')

# ── PyQt6 (inclui WebEngine) ──────────────────────────────────────────────────
qt_datas, qt_binaries, qt_hidden = collect_all('PyQt6')

# ── yt-dlp ────────────────────────────────────────────────────────────────────
ytdlp_datas, ytdlp_binaries, ytdlp_hidden = collect_all('yt_dlp')
ejs_datas, ejs_binaries, ejs_hidden = collect_all('yt_dlp_ejs')

# ── imageio-ffmpeg (inclui o binário ffmpeg) ──────────────────────────────────
ffmpeg_datas, ffmpeg_binaries, ffmpeg_hidden = collect_all('imageio_ffmpeg')

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=qt_binaries + ytdlp_binaries + ejs_binaries + ffmpeg_binaries + [
        (str(runtime / 'node.exe'), 'runtime'),
        (str(runtime / 'ffmpeg.exe'), 'runtime'),
    ],
    datas=[
        ('Icone.png', '.'),
        ('Icone.ico', '.'),
        ('src/dvaStudio/assets/icon.png', 'src/dvaStudio/assets'),
    ] + [(str(p), 'runtime') for p in runtime.glob('*LICENSE.txt')] + qt_datas + ytdlp_datas + ejs_datas + ffmpeg_datas,
    hiddenimports=(
        qt_hidden + ytdlp_hidden + ejs_hidden + ffmpeg_hidden + [
            # yt-dlp extractors e postprocessors
            'yt_dlp.extractor._extractors',
            'yt_dlp.extractor.youtube',
            'yt_dlp.postprocessor.ffmpeg',
            'yt_dlp.postprocessor.embedthumbnail',
            # imageio-ffmpeg
            'imageio_ffmpeg',
            'imageio_ffmpeg._utils',
            # PyQt6 WebEngine
            'PyQt6.QtWebEngineWidgets',
            'PyQt6.QtWebEngineCore',
            'PyQt6.QtWebChannel',
            # Stdlib usado pelo downloader
            'shutil',
        ]
    ),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'scipy'],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,       # onedir: binários ficam fora do .exe
    contents_directory='.',      # dependências ao lado do executável
    name='DVAStudio',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,                   # UPX pode quebrar DLLs Qt — desativado
    console=False,               # sem janela de console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='Icone.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='DVAStudio',
)
