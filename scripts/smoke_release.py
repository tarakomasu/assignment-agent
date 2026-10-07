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
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)
    with (temp / "講義 資料.pdf").open("wb") as stream:
        writer.write(stream)
    env = os.environ.copy()
    env["ASSIGNMENT_AGENT_STATE"] = str(temp / "state")
    env["ASSIGNMENT_AGENT_AGY"] = str(fake)
    env["PATH"] = str(Path(env["SYSTEMROOT"]) / "System32")
    result = subprocess.run([str(root / "assignment-agent.exe"), "--debug", "run", str(temp / "講義 資料.pdf"),
                 "--output", str(temp / "output"), "--work", str(temp / "work")], env=env)
    if result.returncode:
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
