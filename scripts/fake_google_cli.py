"""Offline AI stub used only by the Windows packaging smoke test."""
import json
import sys

PLAN = {"lecture_title": "料金計算 動作確認", "missing_information": [], "assignments": [
    {"id": "task_01", "title": "携帯電話の料金", "page": 1,
     "requirements": "3780 + 20 * minutes + 5 * mails",
     "tests": [{"stdin": "10\n20\n", "expected_stdout": "4080\n"},
               {"stdin": "0\n0\n", "expected_stdout": "3780\n"}]}]}
SOURCE = '#include <stdio.h>\nint main(void) { int a,b; scanf("%d%d", &a, &b); printf("%d\\n", 3780+20*a+5*b); return 0; }\n'

for line in sys.stdin:
    prompt = json.loads(line)["message"]["content"]
    answer = PLAN if "まだ解答コード" in prompt else (
        {"valid": True, "issues": []} if "独立したレビュー" in prompt else
        {"solutions": [{"id": "task_01", "source": SOURCE}]})
    print(json.dumps({"event": "result", "result": {"status": "SUCCESS", "response": json.dumps(answer)}}))
