# -*- mode: python ; coding: utf-8 -*-
# PyInstaller 打包配置：onedir 产物 dist/image-gen-platform/（exe + _internal）。
# 前端 dist 与静态资源作为数据文件打进包，由后端托管；存储默认 SQLite 单文件随包走。
# 构建：venv 下执行  pyinstaller image_gen_platform.spec --noconfirm

a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('frontend/dist', 'frontend/dist'),   # 前端产物（含 index.html/assets），冻结态由 main.py 从 _MEIPASS 解析
    ],
    hiddenimports=[
        # uvicorn 标准 extras 的动态导入点，PyInstaller 静态分析扫不到
        'uvicorn.logging',
        'uvicorn.loops', 'uvicorn.loops.auto',
        'uvicorn.protocols', 'uvicorn.protocols.http', 'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets', 'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan', 'uvicorn.lifespan.on',
        'anyio._backends._asyncio',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='image-gen-platform',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,          # 保留控制台：启动诊断/日志可见
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='image-gen-platform',
)
