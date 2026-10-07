import json
import re
from dataclasses import asdict, dataclass


class AgentError(Exception):
    """An actionable error which can be shown to a nontechnical user."""


def parse_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        value = json.loads(text)
    except (ValueError, TypeError) as exc:
        raise AgentError("Geminiの応答を読み取れませんでした。もう一度実行してください。") from exc
    if not isinstance(value, dict):
        raise AgentError("Geminiの応答形式が正しくありません。")
    return value


def required_text(obj, key, maximum=30000, allow_empty=False):
    value = obj.get(key)
    if not isinstance(value, str) or len(value) > maximum or (not allow_empty and not value.strip()):
        raise AgentError(f"Geminiの応答に有効な {key} がありません。")
    return value


@dataclass
class TestCase:
    stdin: str
    expected_stdout: str


@dataclass
class Assignment:
    id: str
    title: str
    page: int
    requirements: str
    tests: list[TestCase]
    source: str = ""

    def data(self):
        return asdict(self)


def parse_plan(value, page_count):
    missing = value.get("missing_information")
    if not isinstance(missing, list) or any(not isinstance(x, str) for x in missing):
        raise AgentError("Geminiの不足情報の応答形式が正しくありません。")
    if missing:
        raise AgentError("課題を解くための情報が不足しています：\n" + "\n".join(missing))
    title = required_text(value, "lecture_title", 200)
    items = value.get("assignments")
    if not isinstance(items, list) or not 1 <= len(items) <= 30:
        raise AgentError("今回の課題を特定できませんでした（課題数は1〜30件に対応）。")
    assignments = []
    ids = set()
    for item in items:
        if not isinstance(item, dict):
            raise AgentError("課題の形式が正しくありません。")
        task_id = required_text(item, "id", 40)
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,39}", task_id) or task_id in ids:
            raise AgentError("課題IDが重複しているか、使用できない文字を含みます。")
        ids.add(task_id)
        page = item.get("page")
        if type(page) is not int or not 1 <= page <= page_count:
            raise AgentError("課題の参照ページがPDFの範囲外です。")
        tests = item.get("tests")
        if not isinstance(tests, list) or not 1 <= len(tests) <= 10:
            raise AgentError("課題ごとに1〜10件の検証用入力が必要です。")
        cases = []
        for test in tests:
            if not isinstance(test, dict):
                raise AgentError("テストデータの形式が正しくありません。")
            cases.append(TestCase(required_text(test, "stdin", 10000, True),
                                  required_text(test, "expected_stdout", 10000)))
        assignments.append(Assignment(task_id, required_text(item, "title", 200), page,
                                      required_text(item, "requirements"), cases))
    return title, assignments


def parse_sources(value, assignments):
    items = value.get("solutions")
    if not isinstance(items, list) or len(items) != len(assignments):
        raise AgentError("すべての課題のCコードが生成されませんでした。")
    sources = {}
    for item in items:
        if not isinstance(item, dict):
            raise AgentError("Cコードの応答形式が正しくありません。")
        task_id = required_text(item, "id", 40)
        if task_id in sources:
            raise AgentError("Cコードの課題IDが重複しています。")
        sources[task_id] = required_text(item, "source")
    if set(sources) != {a.id for a in assignments}:
        raise AgentError("課題とCコードの対応が正しくありません。")
    for assignment in assignments:
        assignment.source = sources[assignment.id]
