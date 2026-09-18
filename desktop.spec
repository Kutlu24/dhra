# PyInstaller spec for the DHRA desktop launcher -- see src/dhra/desktop.py
# for what this actually does and doesn't solve (no bundled poppler/
# tesseract, no native window, unsigned builds show an OS warning).
#
# Build: pyinstaller desktop.spec
# Output: dist/dhra-desktop(.exe on Windows)
#
# Run on each target OS separately -- PyInstaller does not cross-compile.
# .github/workflows/desktop-build.yml runs this on windows-latest,
# macos-latest, and ubuntu-latest to produce all three real artifacts.

block_cipher = None

a = Analysis(
    ["src/dhra/desktop.py"],
    pathex=["src"],
    binaries=[],
    datas=[
        ("src/dhra/web/templates", "dhra/web/templates"),
        ("src/dhra/web/static", "dhra/web/static"),
    ],
    hiddenimports=["dhra.desktop"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="dhra-desktop",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # keep the terminal window -- it's the only status/stop UI there is right now
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # No icon set: PyInstaller needs a platform-native format (.ico on
    # Windows, .icns on macOS) -- the logo only exists as SVG right now.
    # Converting it is a small, separate follow-up, not done here.
    icon=None,
)
