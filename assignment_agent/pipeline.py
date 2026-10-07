import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path

from pypdf import PdfReader

from . import prompts
from .artifacts import make_docx, render_result
from .gemini import Gemini
from .models import AgentError, parse_plan, parse_sources
from .runner import matches, run_c


def dump(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def pdf_pages(pdf):
    if not pdf.is_file() or pdf.suffix.lower() != ".pdf":
        raise AgentError("PDFが見つかりません。指定したファイル名を確認してください。")
    if pdf.stat().st_size > 20 * 1024 * 1024:
        raise AgentError("PDFは20MB以下にしてください。")
    try:
        reader = PdfReader(pdf)
        if reader.is_encrypted:
            raise AgentError("パスワード付きPDFには対応していません。")
        count = len(reader.pages)
    except AgentError:
        raise
    except Exception as exc:
        raise AgentError("PDFを読み込めません。ファイルが壊れていないか確認してください。") from exc
    if not 1 <= count <= 100:
        raise AgentError("PDFは1〜100ページに対応しています。")
    return count


def execute_tests(assignments, stage, workspace):
    reports = {}
    failed = False
    for task in assignments:
        folder = stage / task.id
        folder.mkdir(exist_ok=True)
        source = folder / "solution.c"
        source.write_text(task.source, encoding="utf-8")
        cases = []
        for i, test in enumerate(task.tests):
            result = run_c(source, test.stdin, workspace / task.id / str(i))
            result.update(stdin=test.stdin, expected_stdout=test.expected_stdout)
            result["passed"] = bool(result["compile_success"] and result["exit_code"] == 0
                                    and not result["error"] and matches(result["stdout"], test.expected_stdout))
            failed |= not result["passed"]
            cases.append(result)
        reports[task.id] = cases
        dump(folder / "tests.json", cases)
    return reports, failed


def review_result(value):
    valid, issues = value.get("valid"), value.get("issues")
    if type(valid) is not bool or not isinstance(issues, list) or any(not isinstance(x, str) for x in issues):
        raise AgentError("Geminiの仕様検証の応答形式が正しくありません。")
    if valid and issues:
        raise AgentError("Geminiの仕様検証に矛盾があります。")
    if not valid and not issues:
        raise AgentError("Geminiの仕様検証が失敗しましたが、理由がありません。")
    return valid, issues


def run(pdf, output_root, work_root, model=None, ai_factory=Gemini, progress=print):
    pdf = Path(pdf).resolve()
    page_count = pdf_pages(pdf)
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
    workspace = Path(work_root).resolve() / run_id
    workspace.mkdir(parents=True)
    stage = workspace / "artifacts"
    stage.mkdir()
    shutil.copyfile(pdf, workspace / "lecture.pdf")
    ai = ai_factory(workspace, model=model)
    try:
        progress("1/5 PDF全体を読み、今回の課題とテストを特定しています…")
        plan = ai.ask(prompts.DISCOVER)
        title, assignments = parse_plan(plan, page_count)
        dump(stage / "assignment.json", plan)
        progress(f"今回の課題：{len(assignments)}件")
        for task in assignments:
            progress(f"  PDF {task.page}ページ：{task.title}")
        progress("2/5 講義内容に沿ったCコードを生成しています…")
        parse_sources(ai.ask(prompts.GENERATE + json.dumps(plan, ensure_ascii=False)), assignments)
        for attempt in range(3):
            progress(f"3/5 Cコードをコンパイル・実行・検証しています（{attempt + 1}/3）…")
            reports, failed = execute_tests(assignments, stage, workspace)
            payload = json.dumps({"plan": plan, "solutions": [a.data() for a in assignments],
                                  "actual_results": reports}, ensure_ascii=False)
            if not failed:
                progress("4/5 PDFの仕様と全課題の解答を照合しています…")
                valid, issues = review_result(ai.ask(prompts.REVIEW + payload))
                dump(stage / "review.json", {"valid": valid, "issues": issues})
                if valid:
                    break
            else:
                issues = ["コンパイル・実行または期待stdoutとの完全一致に失敗。actual_resultsを確認。"]
            if attempt == 2:
                raise AgentError("3回の検証で問題を解決できませんでした。Wordは作成しません。\n" + "\n".join(issues))
            progress("検証で問題が見つかりました。コードを修正しています…")
            parse_sources(ai.ask(prompts.REPAIR + payload + "\n指摘：" + json.dumps(issues, ensure_ascii=False)), assignments)
        progress("5/5 実行結果画像とWordを作成しています…")
        images = {a.id: render_result(a.source, reports[a.id], stage / a.id) for a in assignments}
        make_docx(title, assignments, images, stage / "submission.docx")
        dump(stage / "manifest.json", {"pdf_filename": pdf.name, "page_count": page_count,
                                       "assignments": len(assignments), "status": "verified"})
        output = Path(output_root).resolve() / run_id
        output.parent.mkdir(parents=True, exist_ok=True)
        # Only publish a fresh complete run. Failed runs cannot leave a stale Word.
        pending = output.parent / (".pending-" + run_id)
        try:
            shutil.copytree(stage, pending)
            pending.rename(output)
        except Exception:
            shutil.rmtree(pending, ignore_errors=True)
            raise
        return output / "submission.docx"
    except Exception as exc:
        dump(workspace / "failure.json", {"error": str(exc), "status": "failed"})
        raise
