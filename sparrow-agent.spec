# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = ['google.genai', 'google.genai.types', 'openai', 'anthropic', 'rich.console', 'rich.panel', 'rich.prompt', 'rich.progress', 'rich.rule', 'rich.table', 'rich.text', 'rich.markdown', 'requests', 'agent', 'agent.config', 'agent.cli', 'agent.checks', 'agent.checks.permissions', 'agent.checks.ports', 'agent.checks.packages', 'agent.installer', 'agent.installer.extractor', 'agent.installer.properties', 'agent.installer.profiles', 'agent.installer.runner', 'agent.llm', 'agent.llm.base', 'agent.llm.gemini', 'agent.llm.openai_client', 'agent.llm.claude', 'agent.llm.prompts', 'agent.utils', 'agent.utils.network', 'agent.utils.platform_utils']
tmp_ret = collect_all('google.genai')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('google.ai')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('openai')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('anthropic')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('rich')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['C:\\Exception\\Downloads\\AgentSparrow\\.claude\\worktrees\\unruffled-hypatia\\main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='sparrow-agent',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
