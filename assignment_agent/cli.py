import argparse
import sys
from pathlib import Path

from .gemini import app_root, gemini_command, login
from .models import AgentError
from .runner import compiler


def main(argv=None):
    # Windows redirected consoles can default to a legacy code page. Keep both
    # user messages and CI output readable without UnicodeEncodeError.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="講義PDFから今回のC言語課題を検証し、Wordを作成します。")
    parser.add_argument("--debug", action="store_true", help="開発用のエラー詳細を表示")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("login", help="初回のGoogleログイン")
    doctor_parser = commands.add_parser("doctor", help="同梱ツールの確認")
    doctor_parser.add_argument("--install-google-cli", action="store_true", help="Google公式CLIの取得も確認")
    profile_parser = commands.add_parser("profile", help="提出者の氏名と学籍番号を設定")
    profile_parser.add_argument("--name", required=True)
    profile_parser.add_argument("--student-id", required=True)
    run_parser = commands.add_parser("run", help="PDFの今回の課題をすべて処理")
    run_parser.add_argument("pdf", nargs="?", help="PDFのパス。省略時はinput内のPDF1件を使用")
    run_parser.add_argument("--output", type=Path, default=app_root() / "output")
    run_parser.add_argument("--work", type=Path, default=app_root() / "work")
    run_parser.add_argument("--model", help="Geminiのモデル名（通常は指定不要）")
    args = parser.parse_args(argv)
    try:
        if args.command == "login":
            return login()
        if args.command == "profile":
            from .profile import save_profile
            save_profile(args.name, args.student_id)
            print("提出者情報を保存しました。次回作成するWordに記載します。")
            return 0
        if args.command == "doctor":
            if args.install_google_cli:
                from .gemini import install_google_cli
                import subprocess
                command = install_google_cli()
                subprocess.run(command + ["--version"], check=True)
            try:
                print("Google CLI:", " ".join(gemini_command()))
            except AgentError:
                print("Google CLI: 初回loginでGoogle公式から取得します")
            print("Cコンパイラ:", compiler())
            from playwright.sync_api import sync_playwright
            import os
            browsers = app_root() / "runtime" / "browsers"
            if browsers.is_dir():
                os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(browsers)
            with sync_playwright() as p:
                browser = p.chromium.launch()
                browser.close()
            print("画像生成ブラウザ: OK")
            return 0
        if args.pdf:
            pdf = Path(args.pdf)
        else:
            files = sorted(p for p in (app_root() / "input").glob("*") if p.suffix.lower() == ".pdf")
            if len(files) != 1:
                raise AgentError("inputにPDFを1つ置くか、runの後にPDFのパスを指定してください。")
            pdf = files[0]
        from .pipeline import run
        from .profile import load_profile
        result = run(pdf, args.output, args.work, args.model, progress=lambda x: print(x, flush=True), profile=load_profile())
        print(f"\n作成しました：{result}\nWordを開いてコード・実行結果・提出条件を確認してください。")
        return 0
    except KeyboardInterrupt:
        print("\n処理を中止しました。", file=sys.stderr)
        return 130
    except AgentError as exc:
        print(f"\nエラー：{exc}", file=sys.stderr)
        return 1
    except Exception:
        if args.debug:
            import traceback
            traceback.print_exc()
        print("\n処理に失敗しました。空き容量・ZIPの展開・ネット接続を確認してください。", file=sys.stderr)
        return 1
