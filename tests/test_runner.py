import pytest

from assignment_agent.models import AgentError
from assignment_agent.runner import check_source, matches, run_c

SOURCE = '#include <stdio.h>\nint main(void) { int a,b; scanf("%d%d", &a, &b); printf("%d\\n", 3780+20*a+5*b); return 0; }\n'


@pytest.mark.parametrize("stdin,expected", [("10\n20\n", "4080\n"), ("0\n0\n", "3780\n"), ("123\n45\n", "6465\n")])
def test_actual_c_calculation(tmp_path, stdin, expected):
    source = tmp_path / "課題 コード.c"
    source.write_text(SOURCE, encoding="utf-8")
    result = run_c(source, stdin, tmp_path / "実行 作業")
    assert result["compile_success"]
    assert result["exit_code"] == 0
    assert result["stdout"] == expected


@pytest.mark.parametrize("source,error", [
    ('#include <stdio.h>\nint main(void) { while(1) {} }', "タイムアウト"),
    ('#include <stdio.h>\nint main(void) { while(1) { puts("xxxxxxxxxxxxxxxxxxxxxx"); } }', "出力上限"),
])
def test_bounded_execution(tmp_path, source, error):
    path = tmp_path / "bad.c"
    path.write_text(source)
    result = run_c(path, "", tmp_path / "work", timeout=0.3 if error == "タイムアウト" else 5)
    assert error in result["error"]
    assert len(result["stdout"]) <= 256 * 1024


def test_compile_failure(tmp_path):
    path = tmp_path / "bad.c"
    path.write_text("int main(void) { invalid syntax; }")
    result = run_c(path, "", tmp_path / "work")
    assert not result["compile_success"]
    assert result["exit_code"] is None


@pytest.mark.parametrize("source", [
    '#include <stdlib.h>\nint main(void) { system("dir"); }',
    '#include <windows.h>\nint main(void) { return 0; }',
    '#include <stdio.h>\nint main(void) { fopen("a", "w"); }',
    '#define X system\nint main(void) { X("dir"); }',
    'int main(void) { __asm__("nop"); }',
])
def test_unsupported_operations(source):
    with pytest.raises(AgentError):
        check_source(source)


def test_exact_output_not_substring():
    assert matches("4080\r\n", "4080\n")
    assert not matches("wrong 4080 value", "4080")
    assert not matches(" 4080", "4080")
    assert not matches("A\nB", "A\n\nB")
