import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import dimension_labels as dl


def test_default_labels_when_no_file(tmp_path, monkeypatch):
    monkeypatch.setattr(dl, "LABELS_FILE", tmp_path / "labels.json")
    labels = dl.load_dimension_labels()
    assert labels == dl.DEFAULT_LABELS


def test_save_and_load_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(dl, "LABELS_FILE", tmp_path / "labels.json")
    custom = {"cabinet": "Корабль", "season": "Калибр", "item": "Паллета"}
    dl.save_dimension_labels(custom)
    loaded = dl.load_dimension_labels()
    assert loaded == custom


def test_partial_saved_file_fills_missing_from_defaults(tmp_path, monkeypatch):
    labels_file = tmp_path / "labels.json"
    monkeypatch.setattr(dl, "LABELS_FILE", labels_file)
    import json
    with open(labels_file, "w", encoding="utf-8") as f:
        json.dump({"cabinet": "Корабль"}, f)
    loaded = dl.load_dimension_labels()
    assert loaded["cabinet"] == "Корабль"
    assert loaded["season"] == dl.DEFAULT_LABELS["season"]
    assert loaded["item"] == dl.DEFAULT_LABELS["item"]


def test_preset_save_load_delete_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(dl, "LABEL_PRESETS_FILE", tmp_path / "presets.json")
    labels = {"cabinet": "Корабль", "season": "Калибр", "item": "Паллета"}
    dl.save_label_preset("Морской", labels)

    assert "Морской" in dl.list_label_preset_names()
    loaded = dl.load_label_presets()
    assert loaded["Морской"] == labels

    dl.delete_label_preset("Морской")
    assert "Морской" not in dl.list_label_preset_names()


def test_list_presets_empty_when_no_file(tmp_path, monkeypatch):
    monkeypatch.setattr(dl, "LABEL_PRESETS_FILE", tmp_path / "no_such_presets.json")
    assert dl.list_label_preset_names() == []
