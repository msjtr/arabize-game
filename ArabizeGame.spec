# -*- mode: python ; coding: utf-8 -*-
# Build:  pyinstaller --noconfirm ArabizeGame.spec   ->  dist/ArabizeGame/ArabizeGame.exe
import sys
from PyInstaller.utils.hooks import collect_all, collect_submodules

datas = [("arabize/assets", "arabize/assets")]
binaries, hidden = [], []
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs
for pkg in ("rapidocr_onnxruntime", "openvr"):
    d, b, h = collect_all(pkg)
    datas += d; binaries += b; hidden += h
# onnxruntime: only the runtime itself, not its model-conversion tools (which drag in scipy/pandas/sympy)
binaries += collect_dynamic_libs("onnxruntime")
hidden += collect_submodules("onnxruntime.capi")
if sys.platform == "win32":
    hidden += ["pynput.keyboard._win32", "pynput.mouse._win32"]
    try:
        hidden += collect_submodules("winrt")
    except Exception:
        pass
else:
    hidden += ["pynput.keyboard._xorg", "pynput.mouse._xorg"]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden,
    excludes=["tkinter", "matplotlib", "IPython", "pytest", "scipy", "pandas", "sympy", "cryptography", "lxml",
              "onnxruntime.tools", "onnxruntime.transformers", "onnxruntime.quantization", "torch", "tensorflow",
              "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.Qt3DCore", "PySide6.QtQuick",
              "PySide6.QtQml", "PySide6.QtMultimedia", "PySide6.QtCharts", "PySide6.QtDataVisualization", "PySide6.QtPdf"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="ArabizeGame", console=False,
          icon="arabize/assets/app.ico", upx=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="ArabizeGame")
