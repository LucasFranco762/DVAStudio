# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_data_files

# ── PyQt6 (inclui WebEngine) ──────────────────────────────────────────────────
qt_datas, qt_binaries, qt_hidden = collect_all('PyQt6')

# ── yt-dlp ────────────────────────────────────────────────────────────────────
ytdlp_datas, ytdlp_binaries, ytdlp_hidden = collect_all('yt_dlp')

# ── imageio-ffmpeg (inclui o binário ffmpeg) ──────────────────────────────────
ffmpeg_datas, ffmpeg_binaries, ffmpeg_hidden = collect_all('imageio_ffmpeg')

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=qt_binaries + ytdlp_binaries + ffmpeg_binaries,
    datas=[
        ('Icone.png', '.'),
        ('src/dvaStudio/assets/icon.png', 'src/dvaStudio/assets'),
    ] + qt_datas + ytdlp_datas + ffmpeg_datas,
    hiddenimports=(
        qt_hidden + ytdlp_hidden + ffmpeg_hidden + [
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
