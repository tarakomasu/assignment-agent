"""Exercise a packaged Windows exe without Python, GCC or Node on PATH.

The fake CLI only replaces the remote AI response. Compilation, execution,
screenshots and Word generation are performed by the real packaged executable.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from pypdf import PdfWriter

root = Path(sys.argv[1]).resolve()
script = root / "runtime/gemini/node_modules/@google/gemini-cli/bundle/gemini.js"
original = script.read_bytes()
plan = {"lecture_title": "料金計算 動作確認", "missing_information": [], "assignments": [
    {"id": "task_01", "title": "携帯電話の料金", "page": 1,
     "requirements": "3780 + 20 * minutes + 5 * mails",
     "tests": [{"stdin": "10\n20\n", "expected_stdout": "4080\n"},
               {"stdin": "0\n0\n", "expected_stdout": "3780\n"}]}]}
source = '#include <stdio.h>\nint main(void) { int a,b; scanf("%d%d", &a, &b); printf("%d\\n", 3780+20*a+5*b); return 0; }\n'
fake = """import fs from 'node:fs'; const p=fs.readFileSync(0,'utf8');
const answer=p.includes('まだ解答コード')?PLAN:
p.includes('独立したレビュー')?{valid:true,issues:[]}:
{solutions:[{id:'task_01',source:SOURCE}]};
console.log(JSON.stringify({response:JSON.stringify(answer)}));
""".replace("PLAN", json.dumps(plan, ensure_ascii=False)).replace("SOURCE", json.dumps(source))
try:
    script.write_text(fake, encoding="utf-8")
    with tempfile.TemporaryDirectory(prefix="課題 テスト ") as temp:
        temp = Path(temp)
        writer = PdfWriter()
        writer.add_blank_page(width=300, height=300)
        with (temp / "講義 資料.pdf").open("wb") as stream:
            writer.write(stream)
        env = os.environ.copy()
        env["ASSIGNMENT_AGENT_STATE"] = str(temp / "state")
        env["PATH"] = str(Path(env["SYSTEMROOT"]) / "System32")
        result = subprocess.run([str(root / "assignment-agent.exe"), "run", str(temp / "講義 資料.pdf"),
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
        print("Portable release smoke test: PASS")
finally:
    script.write_bytes(original)
