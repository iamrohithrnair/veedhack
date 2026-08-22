from pathlib import Path

from app.artifacts import copy_file, project_dir, write_json, write_text


def test_writes_local_demo_artifacts(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("app.artifacts.DEMO_DIR", tmp_path)
    folder = project_dir("demo-project")
    json_path = write_json("demo-project", "extracted.json", {"Core_Subject": "Pioneer AI"})
    text_path = write_text("demo-project", "script.txt", "Fools! Fine-tune faster.")
    source = tmp_path / "source.mp3"
    source.write_bytes(b"audio")
    audio_path = copy_file("demo-project", "audio.mp3", source)
    assert folder.is_dir()
    assert json_path.read_text().startswith("{")
    assert "Fine-tune" in text_path.read_text()
    assert audio_path.read_bytes() == b"audio"
