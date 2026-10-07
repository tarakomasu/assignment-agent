"""Exercise a packaged Windows exe without Python, GCC or Node on PATH.

The fake CLI only replaces the remote AI response. Compilation, execution,
screenshots and Word generation are performed by the real packaged executable.
"""
import json
import os
import subprocess
import shutil
import sys
import tempfile
from pathlib import Path

from pypdf import PdfWriter

root = Path(sys.argv[1]).resolve()
fake = Path(sys.argv[2]).resolve()
with tempfile.TemporaryDirectory(prefix="課題 テスト ") as temp:
    temp = Path(temp)
    # The executable and its bundled libraries must also work under Japanese
    # install paths, not just with Japanese input/output paths.
    installed = temp / "デスクトップ" / "課題 アプリ"
    shutil.copytree(root, installed)
    root = installed
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    with (temp / "講義 資料.pdf").open("wb") as stream:
        writer.write(stream)
    env = os.environ.copy()
    # Keep the compiler cache ASCII while the app has a Japanese install path.
    env["ASSIGNMENT_AGENT_STATE"] = str(Path("build/smoke-state").resolve())
    env["ASSIGNMENT_AGENT_AGY"] = str(fake)
    env["PATH"] = str(Path(env["SYSTEMROOT"]) / "System32")
    result = subprocess.run([str(root / "assignment-agent.exe"), "--debug", "run", str(temp / "講義 資料.pdf"),
                 "--output", str(temp / "output"), "--work", str(temp / "work")], env=env)
    if result.returncode:
        for report in (temp / "work").glob("*/artifacts/*/tests.json"):
            print(report.read_text(encoding="utf-8"))
        raise SystemExit(result.returncode)
    docs = list((temp / "output").glob("*/submission.docx"))
    assert len(docs) == 1, "Word output missing"
    assert list((temp / "output").glob("*/*/result*.png")), "Screenshot missing"
    from docx import Document
    document = Document(docs[0])
    assert document.inline_shapes, "Word images missing"
    assert "携帯電話の料金" in "\n".join(p.text for p in document.paragraphs)
    qa = Path("build/visual-smoke")
    qa.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(docs[0], qa / "submission.docx")
    print("Portable release smoke test: PASS")
