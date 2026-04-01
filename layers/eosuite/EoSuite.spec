# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for EoSuite GUI.
Packages the entire application into a single standalone .exe.
"""
import os

block_cipher = None
ROOT = os.path.dirname(os.path.abspath(SPEC))

a = Analysis(
    [os.path.join(ROOT, 'EoSuite_GUI.py')],
    pathex=[ROOT],
    binaries=[],
    datas=[
        (os.path.join(ROOT, 'assets', 'icon.ico'), 'assets'),
    ],
    hiddenimports=[
        'gui', 'gui.styles', 'gui.toolbar', 'gui.sidebar',
        'gui.home_tab', 'gui.terminal_tab', 'gui.split_manager',
        'gui.main_window', 'gui.apps',
        # Tools
        'gui.apps.ecal', 'gui.apps.etimer', 'gui.apps.enote',
        'gui.apps.eviewer', 'gui.apps.econverter', 'gui.apps.eguard',
        'gui.apps.eweb', 'gui.apps.ezip', 'gui.apps.ecleaner',
        'gui.apps.evpn', 'gui.apps.echat', 'gui.apps.epaint',
        'gui.apps.eplay', 'gui.apps.ebuffer', 'gui.apps.epdf',
        'gui.apps.eftp', 'gui.apps.etunnel', 'gui.apps.evirustower',
        'gui.apps.evnc', 'gui.apps.eclock',
        # Connectivity
        'gui.apps.ssh_client', 'gui.apps.serial_term',
        'gui.apps.session_manager',
        # Games
        'gui.apps.snake', 'gui.apps.tetris', 'gui.apps.minesweeper',
        'gui.apps.dice', 'gui.apps.chess',
        # Third-party
        'pypdf', 'pypdf.generic', 'pypdf._readers',
        'PIL', 'PIL.Image', 'PIL.ImageDraw', 'PIL.ImageFont',
        'PIL.PdfImagePlugin', 'PIL.JpegImagePlugin',
        'PIL.PngImagePlugin', 'PIL.BmpImagePlugin', 'PIL.GifImagePlugin',
        'docx', 'docx.document', 'docx.text', 'docx.text.paragraph',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'numpy', 'scipy', 'pandas',
        'cv2', 'torch', 'tensorflow',
        'IPython', 'notebook', 'jupyter',
        'test', 'unittest', 'pytest',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='EoSuite',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(ROOT, 'assets', 'icon.ico'),
)
