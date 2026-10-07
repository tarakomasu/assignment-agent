from assignment_agent.cli import main


def test_unexpected_zero_exit_is_failure(monkeypatch, capsys, tmp_path):
    from assignment_agent import pipeline, profile

    def exit_early(*args, **kwargs):
        raise SystemExit(0)

    monkeypatch.setattr(pipeline, "run", exit_early)
    monkeypatch.setattr(profile, "load_profile", lambda: {})
    assert main(["--debug", "run", str(tmp_path / "lecture.pdf")]) == 1
    captured = capsys.readouterr()
    assert "課題処理を開始" in captured.out
    assert "途中で終了" in captured.err
    assert "SystemExit: 0" in captured.err
    assert "作成しました" not in captured.out
