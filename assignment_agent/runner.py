"""Bounded local C execution. These guards are not an OS security sandbox."""
import os
import re
import shutil
import signal
import subprocess
import tempfile
import time
from pathlib import Path

from .gemini import app_root
from .models import AgentError

MAX_OUTPUT = 256 * 1024
HEADERS = {"stdio.h", "stdlib.h", "math.h", "string.h", "ctype.h", "limits.h",
           "float.h", "stdbool.h", "stdint.h"}
CALLS = set("main printf scanf puts putchar getchar sscanf snprintf sprintf strlen strcmp strncmp strcpy strncpy strcat strncat memcpy memmove memset abs labs llabs atoi atol strtol strtod atof sqrt pow sin cos tan floor ceil round fabs fmod isdigit isalpha isspace tolower toupper exit".split())


def check_source(source):
    # Strings/comments are masked before checks, so display text does not trip guards.
    pattern = r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\''
    masked = re.sub(pattern, lambda m: "\n" * m.group().count("\n") + " ", source)
    if "\\\n" in source or "??" in masked or "##" in masked:
        raise AgentError("Cコードに対応外のプリプロセッサ記法があります。")
    for line in source.splitlines():
        if line.lstrip().startswith("#"):
            include = re.fullmatch(r'\s*#\s*include\s*<([a-z0-9_.]+)>\s*(?://.*)?', line)
            define = re.fullmatch(r"\s*#\s*define\s+[A-Z][A-Z0-9_]*\s+[-+0-9. ()*/]+", line)
            if not define and (not include or include[1] not in HEADERS):
                raise AgentError("Cコードに対応外のヘッダまたはプリプロセッサ命令があります。")
    if re.search(r"\b(?:asm|__asm__|__asm|__attribute__|__declspec)\b|\(\s*\*", masked):
        raise AgentError("Cコードに対応外の低水準操作があります。")
    definitions = set(re.findall(r"\b(?:int|void|char|float|double|long|short|unsigned)\s+(\w+)\s*\([^;{}]*\)\s*\{", masked))
    calls = set(re.findall(r"\b([a-zA-Z_]\w*)\s*\(", masked))
    unknown = calls - CALLS - definitions - {"if", "for", "while", "switch", "sizeof", "return"}
    if unknown:
        raise AgentError("Cコードに対応外の関数があります：" + ", ".join(sorted(unknown)))


def compiler():
    bundled = app_root() / "runtime" / "w64devkit" / "bin" / "gcc.exe"
    found = str(bundled) if bundled.is_file() else shutil.which("gcc")
    if not found:
        raise AgentError("Cコンパイラがありません。GitHub ReleasesのWindows用ZIPを使用してください。")
    return found


def stop_process(process):
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    if process.poll() is None:
        process.kill()
    process.wait(timeout=10)


def bounded_run(command, cwd, stdin, timeout, env):
    with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err, tempfile.TemporaryFile() as inp:
        inp.write(stdin.encode("utf-8"))
        inp.seek(0)
        kwargs = {"start_new_session": True} if os.name != "nt" else {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
        process = subprocess.Popen(command, cwd=cwd, env=env, stdin=inp, stdout=out, stderr=err, **kwargs)
        reason = ""
        end = time.monotonic() + timeout
        try:
            while process.poll() is None:
                if time.monotonic() >= end:
                    reason = "実行がタイムアウトしました。"
                    break
                if os.fstat(out.fileno()).st_size + os.fstat(err.fileno()).st_size > MAX_OUTPUT:
                    reason = "実行結果が出力上限を超えました。"
                    break
                time.sleep(0.02)
        finally:
            if process.poll() is None:
                stop_process(process)
        if os.fstat(out.fileno()).st_size + os.fstat(err.fileno()).st_size > MAX_OUTPUT:
            reason = "実行結果が出力上限を超えました。"
        out.seek(0)
        err.seek(0)
        return {"exit_code": process.returncode,
                "stdout": out.read(MAX_OUTPUT).decode("utf-8", errors="replace"),
                "stderr": err.read(MAX_OUTPUT).decode("utf-8", errors="replace"),
                "error": reason}


def run_c(source_path, stdin, work, timeout=5):
    source_path = Path(source_path).resolve()
    work = Path(work).resolve()
    work.mkdir(parents=True, exist_ok=True)
    source = source_path.read_text(encoding="utf-8")
    try:
        check_source(source)
    except AgentError as exc:
        return {"compile_success": False, "exit_code": None, "stdout": "", "stderr": str(exc), "error": str(exc)}
    gcc = compiler()
    env = {key: value for key, value in os.environ.items()
           if key.upper() in {"SYSTEMROOT", "WINDIR", "TEMP", "TMP", "TMPDIR", "PATH", "LANG", "LC_ALL"}}
    env["PATH"] = str(Path(gcc).parent) + os.pathsep + env.get("PATH", "")
    binary = work / ("program.exe" if os.name == "nt" else "program")
    try:
        compiled = bounded_run([gcc, "-std=c11", "-Wall", "-Wextra", "-finput-charset=UTF-8",
                                "-fexec-charset=UTF-8", str(source_path), "-o", str(binary), "-lm"],
                               work, "", 30, env)
        if compiled["exit_code"] != 0 or compiled["error"]:
            return {**compiled, "compile_success": False, "exit_code": None}
        result = bounded_run([str(binary)], work, stdin, timeout, env)
        return {**result, "compile_success": True, "compile_stderr": compiled["stderr"]}
    except OSError as exc:
        raise AgentError("Cプログラムを起動できません。コンパイラとZIPの展開を確認してください。") from exc


def matches(stdout, expected):
    # Preserve interior blank lines, spaces and labels; ignore only terminal newline.
    return stdout.replace("\r\n", "\n").rstrip("\n") == expected.replace("\r\n", "\n").rstrip("\n")
