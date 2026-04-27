# pyinstaller.spec — PantonicVideo release build (§14.1)
# One-file .exe; no UPX in v1 (PRD D16).
# Runtime path resolution: sys._MEIPASS mirrors the project root layout (§14.2).

block_cipher = None

a = Analysis(
    ["main.py"],
    # contracts lives under contracts/src so importlib.import_module("contracts.*") works
    pathex=[".", "contracts/src"],
    binaries=[],
    datas=[
        # Services — manifest.json + entry-point module per service
        ("services/signal_service",          "services/signal_service"),
        ("services/app_state_service",       "services/app_state_service"),
        ("services/filesystem_service",      "services/filesystem_service"),
        ("services/image_service",           "services/image_service"),
        ("services/injector_service",        "services/injector_service"),
        ("services/logging_service",         "services/logging_service"),
        ("services/plugin_registry_service", "services/plugin_registry_service"),
        ("services/project_service",         "services/project_service"),
        ("services/subtitle_service",        "services/subtitle_service"),
        # Built-in plugins — manifest.json + entry-point module per plugin
        ("plugins/image_cropping",           "plugins/image_cropping"),
        ("plugins/project_launcher",         "plugins/project_launcher"),
        ("plugins/subtitle_text_tool",       "plugins/subtitle_text_tool"),
    ],
    # Dynamically imported via importlib.import_module at runtime — must be explicit
    hiddenimports=[
        # Infracore packages
        "infracore",
        "infracore.app",
        "infracore.bootstrap_components.signal_component.signal",
        "infracore.bootstrap_components.signal_component.handle",
        "infracore.bootstrap_components.filesystem_component.filesystem",
        "infracore.bootstrap_components.logging_component.logging",
        "infracore.bootstrap_components.app_state_component.app_state",
        "infracore.bootstrap_components.plugin_registry_component.plugin_registry",
        "infracore.injector_component.injector",
        "infracore.lifecycle.hooks",
        "infracore.lifecycle.excepthook",
        "infracore.manifest.plugin_manifest",
        "infracore.manifest.service_manifest",
        "infracore.ui_shell.window",
        "infracore.ui_shell.docker_menu",
        "infracore.ui_shell.alert_panel",
        "infracore.version_check",
        # Contracts package
        "contracts",
        "contracts.signals",
        "contracts.filesystem",
        "contracts.logging",
        "contracts.state",
        "contracts.manifest",
        "contracts.plugin_registry",
        "contracts.injector",
        "contracts.project",
        "contracts.image",
        "contracts.subtitle",
        "contracts.exceptions",
        # Service entry-point classes (loaded via importlib.import_module at runtime)
        "services.signal_service.service",
        "services.app_state_service.service",
        "services.filesystem_service.service",
        "services.image_service.service",
        "services.injector_service.service",
        "services.logging_service.service",
        "services.plugin_registry_service.service",
        "services.project_service.service",
        "services.subtitle_service.service",
        # Built-in plugin entry-point classes (loaded via importlib.import_module at runtime)
        "plugins.project_launcher.plugin",
        "plugins.image_cropping.plugin",
        "plugins.subtitle_text_tool.plugin",
        # External dependencies
        "pydantic",
        "PIL",
        "PIL.Image",
        "platformdirs",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
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
    name="PantonicVideo",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,         # UPX not committed in v1 (PRD D16)
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,     # GUI application — no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
