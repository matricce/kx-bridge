# PyInstaller-Spec für kx-bridge — plattformneutral (Linux + Windows via PyBuilder).
# Wird relativ zum Repo-Root ausgeführt (`pyinstaller kx-bridge.spec`), wo
# kobrax_moonraker_bridge.py und web/ flach liegen (Release-Repo-Layout).
#
# Bindet das Web-Theme-System (web/themes/<name>/ + web/DOC/) ins Onefile-Binary
# ein → zur Laufzeit über sys._MEIPASS lesbar (_WEB_BASE in der Bridge).
from PyInstaller.utils.hooks import collect_all

datas = [("web", "web"), ("data", "static")]  # bridge/data/ → static/ im _MEIPASS
binaries = []
hiddenimports = []

# pycryptodome vollständig einsammeln (Krypto für die Drucker-Auth)
_d, _b, _h = collect_all("pycryptodome")
datas += _d
binaries += _b
hiddenimports += _h

a = Analysis(
    ["kobrax_moonraker_bridge.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="kx-bridge",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    onefile=True,
)
