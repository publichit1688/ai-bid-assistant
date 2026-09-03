import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import fitz


DEFAULT_RENDERERS = ("microsoft_word", "wps")
SUPPORTED_RENDERERS = (*DEFAULT_RENDERERS, "libreoffice")


class WordRendererNotConfiguredError(RuntimeError):
    """Raised when no configured Word-compatible rendering engine is available."""


class WordConversionError(RuntimeError):
    """Raised when a Word document cannot be rendered to a valid PDF."""


def get_word_preview_path(source_path):
    source = Path(source_path)
    return source.with_name(f"{source.name}.preview.pdf")


def _registry_app_paths(executable_name):
    if os.name != "nt":
        return []
    try:
        import winreg
    except ImportError:
        return []

    values = []
    key_name = (
        "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\"
        + executable_name
    )
    for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for access in (
            winreg.KEY_READ,
            winreg.KEY_READ | getattr(winreg, "KEY_WOW64_64KEY", 0),
            winreg.KEY_READ | getattr(winreg, "KEY_WOW64_32KEY", 0),
        ):
            try:
                with winreg.OpenKey(root, key_name, 0, access) as key:
                    value, _value_type = winreg.QueryValueEx(key, None)
                    values.append(value)
            except OSError:
                continue
    return values


def _first_existing_path(candidates):
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return Path(candidate).resolve()
    return None


def find_renderer_executable(renderer):
    renderer = str(renderer or "").strip().lower()
    program_files = [
        value
        for value in (
            os.getenv("PROGRAMFILES", "").strip(),
            os.getenv("PROGRAMFILES(X86)", "").strip(),
        )
        if value
    ]

    if renderer == "microsoft_word":
        candidates = [
            os.getenv("MICROSOFT_WORD_PATH", "").strip(),
            *_registry_app_paths("WINWORD.EXE"),
            shutil.which("WINWORD.EXE"),
        ]
        for root in program_files:
            candidates.extend(
                [
                    Path(root) / "Microsoft Office" / "root" / "Office16" / "WINWORD.EXE",
                    Path(root) / "Microsoft Office" / "Office16" / "WINWORD.EXE",
                ]
            )
        return _first_existing_path(candidates)

    if renderer == "wps":
        candidates = [
            os.getenv("WPS_OFFICE_PATH", "").strip(),
            *_registry_app_paths("wps.exe"),
            shutil.which("wps.exe"),
        ]
        search_roots = [
            Path(root) / "Kingsoft" / "WPS Office"
            for root in program_files
        ]
        local_app_data = os.getenv("LOCALAPPDATA", "").strip()
        if local_app_data:
            search_roots.append(Path(local_app_data) / "Kingsoft" / "WPS Office")
        for root in search_roots:
            if root.is_dir():
                candidates.extend(root.rglob("wps.exe"))
        return _first_existing_path(candidates)

    if renderer == "libreoffice":
        candidates = [
            os.getenv("LIBREOFFICE_PATH", "").strip(),
            shutil.which("soffice"),
            shutil.which("soffice.exe"),
        ]
        for root in program_files:
            candidates.append(Path(root) / "LibreOffice" / "program" / "soffice.exe")
        return _first_existing_path(candidates)

    return None


def configured_renderers():
    raw_value = os.getenv("WORD_PREVIEW_RENDERERS", "").strip()
    requested = [
        item.strip().lower()
        for item in raw_value.split(",")
        if item.strip().lower() in SUPPORTED_RENDERERS
    ]
    return tuple(dict.fromkeys(requested)) or DEFAULT_RENDERERS


def inspect_preview_pdf(pdf_path):
    try:
        with fitz.open(pdf_path) as document:
            page_count = document.page_count
    except (OSError, RuntimeError, ValueError) as exc:
        raise WordConversionError("Word 预览 PDF 无法打开或文件已损坏") from exc

    if page_count < 1:
        raise WordConversionError("Word 文档转换后没有可预览页面")
    return page_count


def extract_preview_pdf_pages(pdf_path):
    try:
        with fitz.open(pdf_path) as document:
            return [
                {"page": index + 1, "text": page.get_text()}
                for index, page in enumerate(document)
            ]
    except (OSError, RuntimeError, ValueError) as exc:
        raise WordConversionError("Word 预览 PDF 无法提取分页文字") from exc


def get_preview_renderer(pdf_path):
    try:
        with fitz.open(pdf_path) as document:
            metadata = document.metadata or {}
    except (OSError, RuntimeError, ValueError):
        return "unknown"
    signature = " ".join(
        str(metadata.get(key) or "")
        for key in ("producer", "creator")
    ).lower()
    if "microsoft" in signature or " word" in signature:
        return "microsoft_word"
    if "wps" in signature or "kingsoft" in signature:
        return "wps"
    if "libreoffice" in signature:
        return "libreoffice"
    return "unknown"


def _common_subprocess_options(timeout_seconds):
    return {
        "capture_output": True,
        "text": True,
        "timeout": timeout_seconds,
        "check": False,
        "creationflags": (
            subprocess.CREATE_NO_WINDOW
            if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW")
            else 0
        ),
    }


def _run_office_automation(renderer, source, target, timeout_seconds):
    backend_root = Path(__file__).resolve().parents[2]
    script_path = backend_root / "scripts" / "render_word_preview.ps1"
    powershell = shutil.which("powershell.exe") or shutil.which("powershell")
    if not powershell or not script_path.is_file():
        raise WordConversionError("Word/WPS 版式转换脚本不可用")

    command = [
        str(powershell),
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script_path),
        "-Engine",
        renderer,
        "-SourcePath",
        str(source),
        "-TargetPath",
        str(target),
    ]
    completed = subprocess.run(
        command,
        **_common_subprocess_options(timeout_seconds),
    )
    if completed.returncode != 0 or not target.is_file():
        raise WordConversionError(f"{renderer} 无法将文档转换为 PDF")


def _run_libreoffice(source, target, temporary_root, timeout_seconds):
    executable = find_renderer_executable("libreoffice")
    if not executable:
        raise WordConversionError("LibreOffice 不可用")
    output_directory = temporary_root / "libreoffice-output"
    profile_directory = temporary_root / "libreoffice-profile"
    output_directory.mkdir()
    profile_directory.mkdir()
    command = [
        str(executable),
        f"-env:UserInstallation={profile_directory.as_uri()}",
        "--headless",
        "--nologo",
        "--nodefault",
        "--nofirststartwizard",
        "--convert-to",
        "pdf:writer_pdf_Export",
        "--outdir",
        str(output_directory),
        str(source),
    ]
    completed = subprocess.run(
        command,
        **_common_subprocess_options(timeout_seconds),
    )
    converted_files = list(output_directory.glob("*.pdf"))
    if completed.returncode != 0 or len(converted_files) != 1:
        raise WordConversionError("LibreOffice 无法将文档转换为 PDF")
    os.replace(converted_files[0], target)


def ensure_word_preview_pdf(source_path, target_path=None, timeout_seconds=120):
    source = Path(source_path).resolve()
    if source.suffix.lower() not in {".doc", ".docx"}:
        raise WordConversionError("仅支持将 DOC、DOCX 文件转换为预览 PDF")
    if not source.is_file():
        raise WordConversionError("Word 源文件不存在")

    target = Path(target_path or get_word_preview_path(source)).resolve()
    if target.is_file() and target.stat().st_mtime_ns >= source.stat().st_mtime_ns:
        inspect_preview_pdf(target)
        return target

    available_renderers = [
        renderer
        for renderer in configured_renderers()
        if find_renderer_executable(renderer)
    ]
    if not available_renderers:
        raise WordRendererNotConfiguredError(
            "未检测到 Microsoft Word 或 WPS Office，请先安装至少一个版式渲染引擎。"
        )

    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(
            prefix=".word-preview-",
            dir=target.parent,
        ) as temporary_directory:
            temporary_root = Path(temporary_directory)
            for renderer in available_renderers:
                rendered_path = temporary_root / f"{renderer}.pdf"
                try:
                    if renderer == "libreoffice":
                        _run_libreoffice(
                            source,
                            rendered_path,
                            temporary_root,
                            timeout_seconds,
                        )
                    else:
                        _run_office_automation(
                            renderer,
                            source,
                            rendered_path,
                            timeout_seconds,
                        )
                    inspect_preview_pdf(rendered_path)
                    os.replace(rendered_path, target)
                    return target
                except (WordConversionError, subprocess.TimeoutExpired):
                    rendered_path.unlink(missing_ok=True)
                    continue
    except OSError as exc:
        raise WordConversionError("Word 预览 PDF 写入失败") from exc

    raise WordConversionError(
        "Microsoft Word 和 WPS Office 均未能完成转换，请确认软件已激活且文件未加密。"
    )
