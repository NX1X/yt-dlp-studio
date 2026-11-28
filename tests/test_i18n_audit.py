"""Guard: no new user-visible English text may skip tr().

``scripts/i18n_audit.py`` reads every file in src/ and lists string literals
that reach a widget, a dialog, the Activity log or the status bar without
``tr()``. This test fails when it finds one. Fix it in one of two ways:

1. Add the text to ``src/utils/translations.py`` (English and Hebrew) and use
   ``tr("key")`` in the code. This is the normal fix.
2. If the English text is intentional (a language code, a file name), add a
   comment ``# i18n-ok: <reason>`` on the same line. Keep these rare.

The second half of the guard is tests/test_hebrew_ui_has_no_english.py. It
opens the windows in Hebrew and reads the text the user sees.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("i18n_audit", ROOT / "scripts" / "i18n_audit.py")
i18n_audit = importlib.util.module_from_spec(_spec)
sys.modules["i18n_audit"] = i18n_audit  # dataclasses needs the module registered
_spec.loader.exec_module(i18n_audit)


def audit(source: str, rel: str = "src/ui/example.py"):
    return i18n_audit.audit_source(rel, source)


def test_src_has_no_untranslated_user_text():
    findings = i18n_audit.audit()
    report = "\n".join(f"{f.file}:{f.line} {f.kind}: {f.text!r} (suggested key: {f.key})" for f in findings)
    assert not findings, (
        "User-visible English text without tr(). Add a key to both languages in "
        "src/utils/translations.py, or mark intentional English with '# i18n-ok: reason'.\n" + report
    )


def test_every_intentional_english_mark_has_a_reason():
    """``# i18n-ok`` must say why, so the list stays reviewable."""
    bad = []
    for path in sorted((ROOT / "src").rglob("*.py")):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if "i18n-ok" in line and "i18n-ok:" not in line:
                bad.append(f"{path.relative_to(ROOT)}:{number}")
    assert not bad, f"Add a reason after 'i18n-ok:' at {bad}"


class TestAuditFindsWhatItShould:
    @pytest.mark.parametrize(
        "code",
        [
            'label.setText("Download finished")',
            'self.button.setToolTip("Open the folder")',
            'QPushButton("Download now")',
            'QMessageBox.warning(self, "Careful", "Something went wrong")',
            'self.log_widget.append_info(f"Started: {title}")',
            'show_status(self, "Saved")',
            'combo.addItems(["First choice", "Second choice"])',
            'table.setHorizontalHeaderLabels(["Title", "Status"])',
            'box.setWindowTitle("Update available")',
            'self.error.emit("Download failed")',
            'task.fail("Stopped for no reason")',
        ],
    )
    def test_reports_english_text(self, code):
        assert audit(code), code

    @pytest.mark.parametrize(
        "code",
        [
            'label.setText(tr("label_url"))',
            "label.setText(f\"{tr('label_url')}: {value}\")",
            'logger.info("Download finished")',
            'logger.warning(f"Could not open {path}")',
            'label.setText("MP4")',
            'label.setText("1080p")',
            'label.setText("https://example.com")',
            'label.setText("H.264 / AAC")',
            'label.setText("")',
            'label.setText(f"{value}")',
            "label.setText(name)",
            'label.setText("Download finished")  # i18n-ok: test only',
        ],
    )
    def test_ignores_translated_and_technical_text(self, code):
        assert not audit(code), code

    def test_scoped_functions_report_returned_text(self):
        source = 'def get_quality_description(name):\n    return "Best quality"\n'
        assert audit(source, "src/backend/format_handler.py")

    def test_scoped_functions_allow_translation_keys(self):
        source = 'def get_quality_description(name):\n    return tr("quality_desc_best")\n'
        assert not audit(source, "src/backend/format_handler.py")
