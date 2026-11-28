"""Static audit for user-visible English text that does not go through tr().

It parses every Python file under src/ with ``ast`` and lists string literals
that reach the user without ``tr()``: Qt widget text, tooltips, titles,
message boxes, combo items, table headers, Activity log lines, status bar
messages, tray notifications and error dialog text.

Not reported:
  * ``logger.*`` calls (the log file stays English).
  * Technical text that reads the same in every language (URLs, file
    extensions, codec names, resolutions, "MP4" alone, ...).
  * Lines marked ``# i18n-ok: <reason>`` (intentional English, reviewed).

Usage:
    python scripts/i18n_audit.py             # markdown table
    python scripts/i18n_audit.py --summary   # counts by file
    python scripts/i18n_audit.py --json
    python scripts/i18n_audit.py --check     # exit 1 if anything is found
    python scripts/i18n_audit.py --root PATH # audit another copy of src/
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"

ALLOW_MARK = "i18n-ok"

# Method name -> positional argument indexes that hold user-visible text
# (None = every positional argument).
METHOD_SINKS: dict[str, tuple[int, ...] | None] = {
    "setText": (0,),
    "setToolTip": (0,),
    "setPlaceholderText": (0,),
    "setWindowTitle": (0,),
    "setStatusTip": (0,),
    "setWhatsThis": (0,),
    "setTitle": (0,),
    "setLabelText": (0,),
    "setInformativeText": (0,),
    "setDetailedText": (0,),
    "setPlainText": (0,),
    "setHtml": (0,),
    "setMarkdown": (0,),
    "setHorizontalHeaderLabels": (0,),
    "setVerticalHeaderLabels": (0,),
    "setHeaderLabels": (0,),
    "setAccessibleName": (0,),
    "setAccessibleDescription": (0,),
    "setSuffix": (0,),
    "setPrefix": (0,),
    "setSpecialValueText": (0,),
    "setFormat": (0,),
    "setButtonText": (1,),
    "setItemText": (1,),
    "setTabText": (1,),
    "setTabToolTip": (1,),
    "addItem": (0,),
    "addItems": (0,),
    "insertItem": (1,),
    "insertItems": (1,),
    "addTab": (1, 2),
    "addAction": (0,),
    "addMenu": (0,),
    "addRow": None,
    "showMessage": (0,),
    "show_status": (1,),
    "show_tray_message": (0,),
    "set_tray_tooltip": (0,),
    "notify_custom": (0, 1),
    "notify_download_complete": (0,),
    "notify_download_error": (0, 1),
    "append_log": (0,),
    "append_error": (0,),
    "append_success": (0,),
    "append_info": (0,),
    "append_warning": (0,),
    "fail": (0,),
    "append": None,  # only for log-like receivers, see LOG_RECEIVERS
}

# QMessageBox.information(parent, title, text) and friends.
STATIC_DIALOGS: dict[str, tuple[int, ...]] = {
    "QMessageBox.information": (1, 2),
    "QMessageBox.warning": (1, 2),
    "QMessageBox.critical": (1, 2),
    "QMessageBox.question": (1, 2),
    "QMessageBox.about": (1, 2),
    "QInputDialog.getText": (1, 2),
    "QInputDialog.getInt": (1, 2),
    "QFileDialog.getExistingDirectory": (1,),
    "QFileDialog.getOpenFileName": (1, 3),
    "QFileDialog.getOpenFileNames": (1, 3),
    "QFileDialog.getSaveFileName": (1, 3),
}

# Constructors whose first text argument is shown to the user.
CONSTRUCTOR_SINKS: dict[str, tuple[int, ...]] = {
    "QLabel": (0,),
    "QPushButton": (0,),
    "QToolButton": (0,),
    "QCheckBox": (0,),
    "QRadioButton": (0,),
    "QGroupBox": (0,),
    "QAction": (0,),
    "QMenu": (0,),
    "QTableWidgetItem": (0,),
    "QListWidgetItem": (0,),
    "QTreeWidgetItem": (0,),
    "QProgressDialog": (0, 1),
}

# Receivers for ``.append(...)`` that are the Activity log.
LOG_RECEIVERS = {"log_widget", "log_text", "log_view", "activity_log"}

# Signal names whose ``emit(...)`` text ends up in front of the user.
EMIT_RECEIVERS = {"error", "failed", "status", "message"}

# Functions that hand plain data to the user (error texts, descriptions,
# fallback names) instead of calling a widget. Inside them every string
# literal counts, except docstrings, lookups, comparisons and logger calls.
DATA_SCOPES: dict[str, set[str]] = {
    "src/utils/error_handler.py": {"get_error_info"},
    "src/backend/format_handler.py": {"get_quality_description"},
    "src/backend/update_checker.py": {"format_release_notes"},
    "src/backend/yt_dlp_wrapper.py": {"_get_language_name"},
    "src/backend/history_manager.py": {"add_download"},
    "src/backend/playlist_fetcher.py": {"fetch_playlist_info", "get_playlist_info", "get_duration_formatted"},
    "src/models/video_info.py": {"from_dict", "get_duration_formatted"},
    "src/ui/log_widget.py": {"_line_html"},
}

# Technical words that read the same in Hebrew. A literal made only of
# these (plus digits and punctuation) is not reported.
TECHNICAL_WORDS = {
    "yt",
    "dlp",
    "yt-dlp",
    "ytdlp",
    "studio",
    "youtube",
    "ffmpeg",
    "ffprobe",
    "deno",
    "github",
    "mp3",
    "mp4",
    "m4a",
    "mkv",
    "webm",
    "flac",
    "wav",
    "opus",
    "ogg",
    "vorbis",
    "aac",
    "jpg",
    "jpeg",
    "png",
    "webp",
    "gif",
    "srt",
    "vtt",
    "ass",
    "json",
    "url",
    "urls",
    "html",
    "css",
    "kb",
    "mb",
    "gb",
    "tb",
    "kbps",
    "mbps",
    "fps",
    "hz",
    "khz",
    "hd",
    "sd",
    "uhd",
    "hdr",
    "av1",
    "vp9",
    "vp8",
    "avc",
    "hevc",
    "nx1x",
    "nxtools",
    "ctrl",
    "alt",
    "shift",
    "del",
    "esc",
    "enter",
    "ok",
}

_PLACEHOLDER = "\x00"
_WORD_RE = re.compile(r"[A-Za-z][A-Za-z0-9'+\-]*")
_TAG_RE = re.compile(r"<[^>]*(?:>|$)")
# A translation key such as "quality_desc_best": an identifier, not text.
_KEY_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_ENTITY_RE = re.compile(r"&[a-z]+;|&#\d+;")


@dataclass(frozen=True)
class Finding:
    file: str
    line: int
    kind: str
    text: str
    key: str


def _literal_text(node: ast.AST) -> str | None:
    """Return the English text of an untranslated literal expression.

    Dynamic parts are written as NUL. Any call (``tr()``, ``str()``) returns
    None, except ``"...".format(...)``.
    """
    if isinstance(node, ast.Constant):
        return node.value if isinstance(node.value, str) else None
    if isinstance(node, ast.JoinedStr):
        return "".join(str(v.value) if isinstance(v, ast.Constant) else _PLACEHOLDER for v in node.values)
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Mod)):
        left, right = _literal_text(node.left), _literal_text(node.right)
        if left is None and right is None:
            return None
        return (left if left is not None else _PLACEHOLDER) + (right if right is not None else _PLACEHOLDER)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "format":
        return _literal_text(node.func.value)
    return None


def _literals(node: ast.AST) -> list[tuple[ast.AST, str]]:
    """Every untranslated literal inside a text argument (lists, ternaries)."""
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        found: list[tuple[ast.AST, str]] = []
        for element in node.elts:
            found.extend(_literals(element))
        return found
    if isinstance(node, ast.IfExp):
        return _literals(node.body) + _literals(node.orelse)
    text = _literal_text(node)
    return [(node, text)] if text is not None else []


def is_technical(text: str) -> bool:
    """True when the text needs no translation (URL, codec, resolution...)."""
    if _KEY_RE.match(text):
        return True
    stripped = _ENTITY_RE.sub(" ", _TAG_RE.sub(" ", text.replace(_PLACEHOLDER, " ")))
    if re.match(r"^\s*(https?://|www\.)", stripped):
        return True
    for word in _WORD_RE.findall(stripped):
        lowered = word.lower().strip("-'+")
        # One letter is a unit or a shortcut key ("x", "B", "s").
        if len(lowered) <= 1 or lowered in TECHNICAL_WORDS:
            continue
        return False
    return True


def _slug(text: str) -> str:
    words = [w.lower() for w in _WORD_RE.findall(text.replace(_PLACEHOLDER, " "))]
    return "_".join(words[:4]) or "text"


_KIND_PREFIX = {
    "setToolTip": "tooltip",
    "setPlaceholderText": "placeholder",
    "setWindowTitle": "dialog",
    "QCheckBox": "checkbox",
    "QPushButton": "button",
    "QGroupBox": "group",
    "setTitle": "group",
    "QLabel": "label",
    "setText": "label",
    "show_status": "status",
    "append_log": "log",
    "append_info": "log",
    "append_error": "log",
    "append_success": "log",
    "append_warning": "log",
    "append": "log",
    "addItem": "item",
    "addItems": "item",
}


def _kind(name: str) -> str:
    if name.startswith(("QMessageBox.", "QInputDialog.")):
        return "dialog"
    return _KIND_PREFIX.get(name, "text")


def _call_name(func: ast.AST) -> str:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        if isinstance(func.value, ast.Name):
            return f"{func.value.id}.{func.attr}"
        return func.attr
    return ""


def _receiver_name(func: ast.Attribute) -> str:
    value = func.value
    if isinstance(value, ast.Attribute):
        return value.attr
    return value.id if isinstance(value, ast.Name) else ""


def _docstring_ids(tree: ast.AST) -> set[int]:
    ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                ids.add(id(body[0].value))
    return ids


class _Visitor(ast.NodeVisitor):
    def __init__(self, rel: str, lines: list[str]):
        self.rel = rel
        self.lines = lines
        self.findings: list[Finding] = []

    def _allowed(self, node: ast.AST) -> bool:
        first = getattr(node, "lineno", 0)
        last = getattr(node, "end_lineno", first) or first
        return any(ALLOW_MARK in self.lines[i - 1] for i in range(first, last + 1) if 0 < i <= len(self.lines))

    def report(self, node: ast.AST, kind: str, text: str) -> None:
        if is_technical(text) or self._allowed(node):
            return
        shown = text.replace(_PLACEHOLDER, "{}").replace("\n", "\\n")
        key = f"{_kind(kind)}_{_slug(text)}"
        self.findings.append(Finding(self.rel, getattr(node, "lineno", 0), kind, shown, key))

    def _check_args(self, call: ast.Call, name: str, indexes: tuple[int, ...] | None) -> None:
        args = call.args
        selected = args if indexes is None else [args[i] for i in indexes if i < len(args)]
        for arg in selected:
            for node, text in _literals(arg):
                self.report(node, name, text)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if node.name in DATA_SCOPES.get(self.rel, set()):
            skip = _skip_ids(node)
            for child in ast.walk(node):
                if isinstance(child, ast.Constant) and isinstance(child.value, str) and id(child) not in skip:
                    self.report(child, f"{node.name}()", child.value)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        name = _call_name(node.func)
        is_attr = isinstance(node.func, ast.Attribute)
        short = node.func.attr if is_attr else name
        receiver = _receiver_name(node.func) if is_attr else ""
        if short == "tr":
            return  # translated: do not look inside
        if receiver in {"logger", "logging"}:
            return  # the log file stays English
        if name in STATIC_DIALOGS:
            self._check_args(node, name, STATIC_DIALOGS[name])
        elif name in CONSTRUCTOR_SINKS:
            self._check_args(node, name, CONSTRUCTOR_SINKS[name])
        elif is_attr and short == "emit":
            if receiver in EMIT_RECEIVERS:
                self._check_args(node, f"{receiver}.emit", None)
        elif short in METHOD_SINKS and (is_attr or short == "show_status"):
            if short != "append" or receiver in LOG_RECEIVERS:
                self._check_args(node, short, METHOD_SINKS[short])
        self.generic_visit(node)


def _skip_ids(scope: ast.AST) -> set[int]:
    """Ids of the literals in ``scope`` that are not text for the user."""
    skip = set(_docstring_ids(scope))

    def skip_all(node: ast.AST) -> None:
        skip.update(id(n) for n in ast.walk(node) if isinstance(n, ast.Constant))

    for node in ast.walk(scope):
        if isinstance(node, ast.Call):
            short = node.func.attr if isinstance(node.func, ast.Attribute) else _call_name(node.func)
            receiver = _receiver_name(node.func) if isinstance(node.func, ast.Attribute) else ""
            if short == "tr" or receiver in {"logger", "logging"}:
                skip_all(node)
            elif short in {"lower", "startswith", "endswith", "get", "split", "replace", "join", "getattr"}:
                for arg in node.args:
                    skip_all(arg)
        elif isinstance(node, (ast.Compare, ast.Raise, ast.Assert)):
            skip_all(node)
        elif isinstance(node, ast.Dict):
            for key in node.keys:
                if key is not None:
                    skip_all(key)
    return skip


def audit_source(rel: str, source: str) -> list[Finding]:
    """Audit one file's source text. ``rel`` is the path shown in findings."""
    tree = ast.parse(source, filename=rel)
    lines = source.splitlines()
    visitor = _Visitor(rel, lines)
    visitor.visit(tree)
    return visitor.findings


def audit(root: Path = SRC) -> list[Finding]:
    """Audit every .py file under ``root``."""
    findings: list[Finding] = []
    for path in sorted(root.rglob("*.py")):
        rel = path.relative_to(root.parent).as_posix()
        if rel == "src/utils/translations.py":
            continue
        findings.extend(audit_source(rel, path.read_text(encoding="utf-8")))
    return sorted(set(findings), key=lambda f: (f.file, f.line, f.text))


def _markdown(findings: list[Finding]) -> str:
    rows = ["| File | Line | Sink | English text | Suggested key |", "|---|---|---|---|---|"]
    for f in findings:
        text = f.text.replace("|", "\\|")
        rows.append(f"| {f.file} | {f.line} | {f.kind} | {text} | `{f.key}` |")
    return "\n".join(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n", maxsplit=1)[0])
    parser.add_argument("--summary", action="store_true", help="counts by file")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--check", action="store_true", help="exit 1 if anything is found")
    parser.add_argument("--root", type=Path, default=SRC, help="folder to audit (default: src/)")
    args = parser.parse_args(argv)

    findings = audit(args.root)
    if args.json:
        print(json.dumps([asdict(f) for f in findings], ensure_ascii=False, indent=2))
    elif args.summary:
        counts = Counter(f.file for f in findings)
        for file, count in sorted(counts.items()):
            print(f"{count:4d}  {file}")
        print(f"{len(findings):4d}  total")
    else:
        print(_markdown(findings))
        print(f"\n{len(findings)} untranslated literal(s)")
    return 1 if args.check and findings else 0


if __name__ == "__main__":
    sys.exit(main())
