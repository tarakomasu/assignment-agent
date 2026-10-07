import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from .models import AgentError, parse_json


def app_root():
    return Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]


def state_root():
    override = os.environ.get("ASSIGNMENT_AGENT_STATE")
    if override:
        return Path(override).resolve()
    base = Path(os.environ.get("LOCALAPPDATA", str(Path.home() / ".local" / "share")))
    return base / "AssignmentAgent"


def gemini_command():
    root = app_root()
    node = root / "runtime" / "node" / ("node.exe" if os.name == "nt" else "node")
    script = root / "runtime" / "gemini" / "node_modules" / "@google" / "gemini-cli" / "bundle" / "gemini.js"
    if node.is_file() and script.is_file():
        return [str(node), str(script)]
    command = shutil.which("gemini")
    if command and not command.lower().endswith((".cmd", ".bat")):
        return [command]
    # Avoid shell=True and .cmd quoting on Windows, even in development mode.
    if command and shutil.which("node"):
        script = Path(command).parent / "node_modules" / "@google" / "gemini-cli" / "bundle" / "gemini.js"
        if script.is_file():
            return [shutil.which("node"), str(script)]
    raise AgentError("Gemini CLIがありません。GitHub ReleasesのWindows用ZIPを展開して使用してください。")


def gemini_env():
    state = state_root()
    home = state / "home"
    (home / ".gemini").mkdir(parents=True, exist_ok=True)
    # System settings override user/project settings. Keep CLI tools read-only;
    # compilation, execution and document writes are controlled by Python.
    settings = {
        "tools": {"core": ["read_file"], "allowed": ["read_file"]},
        "context": {"fileName": "ASSIGNMENT_CONTEXT_UNUSED.md"},
        "security": {"folderTrust": {"enabled": False},
                     "auth": {"selectedType": "oauth-personal", "enforcedType": "oauth-personal"}},
        "admin": {"mcp": {"enabled": False}, "extensions": {"enabled": False}},
        "experimental": {"enableAgents": False},
        "general": {"enableAutoUpdate": False},
        "telemetry": {"enabled": False},
    }
    system = state / "system-settings.json"
    system.write_text(json.dumps(settings), encoding="utf-8")
    env = os.environ.copy()
    for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GEMINI_SYSTEM_MD", "GEMINI_CLI_SYSTEM_DEFAULTS_PATH"):
        env.pop(name, None)
    env["GEMINI_CLI_HOME"] = str(home)
    env["GEMINI_CLI_SYSTEM_SETTINGS_PATH"] = str(system)
    env["GEMINI_CLI_SURFACE"] = "assignment-agent"
    # node.exe and compiler DLLs must be discoverable in the portable release.
    env["PATH"] = str(app_root() / "runtime" / "node") + os.pathsep + env.get("PATH", "")
    return env


class Gemini:
    def __init__(self, workspace, model=None):
        self.workspace = Path(workspace)
        self.model = model
        self.calls = 0

    def ask(self, prompt):
        self.calls += 1
        # Pass the large plan/code via stdin to stay below Windows' command-line limit.
        command = gemini_command() + ["-p", "標準入力の指示を実行し、JSONだけを返す。最初にread_fileでlecture.pdf全体を読むこと。",
                                     "--output-format", "json", "-e", "none"]
        if self.model:
            command += ["--model", self.model]
        try:
            result = subprocess.run(command, cwd=self.workspace, env=gemini_env(),
                                    input=prompt, capture_output=True,
                                    encoding="utf-8", errors="replace", timeout=600)
        except subprocess.TimeoutExpired as exc:
            raise AgentError("Geminiの応答が10分以内に完了しませんでした。時間をおいて再実行してください。") from exc
        except OSError as exc:
            raise AgentError("Gemini CLIを起動できません。ZIPを再展開してください。") from exc
        # Do not save raw CLI diagnostic output, which may contain account data.
        if result.returncode:
            raise AgentError("Geminiの処理に失敗しました。loginでログインを確認し、利用上限の場合は時間をおいて再実行してください。")
        wrapper = parse_json(result.stdout)
        if wrapper.get("error") or not isinstance(wrapper.get("response"), str):
            raise AgentError("Geminiから解答が返りませんでした。loginまたは利用上限を確認してください。")
        answer = parse_json(wrapper["response"])
        (self.workspace / f"response-{self.calls:02d}.json").write_text(
            json.dumps(answer, ensure_ascii=False, indent=2), encoding="utf-8")
        return answer


def login():
    workspace = state_root() / "login"
    workspace.mkdir(parents=True, exist_ok=True)
    print("ブラウザでGoogleにログインしてください。完了後、Gemini画面で /quit と入力します。", flush=True)
    return subprocess.call(gemini_command() + ["-e", "none"], cwd=workspace, env=gemini_env())
