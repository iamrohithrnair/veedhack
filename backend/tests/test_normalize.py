import pytest

from app.pioneer.normalize import normalize_inference


def test_normalizes_entity_and_classification_shapes() -> None:
    result = normalize_inference(
        {
            "entities": [
                {"label": "Core_Subject", "text": "creator consistency"},
                {"entity_type": "Pain Point", "value": "no time"},
                {"type": "Action-Hook", "entity": "publish today"},
            ],
            "classification": {"label": "Emotional_Vibe", "prediction": "confident"},
        }
    )
    assert result == {
        "Core_Subject": "creator consistency",
        "Pain_Point": "no time",
        "Emotional_Vibe": "confident",
        "Action_Hook": "publish today",
    }


def test_rejects_incomplete_response() -> None:
    with pytest.raises(ValueError, match="Pain_Point"):
        normalize_inference({"Core_Subject": "video"})


def test_normalizes_live_pioneer_keyed_entity_envelope() -> None:
    result = normalize_inference(
        {
            "result": {
                "data": {
                    "entities": {
                        "Core_Subject": [{"text": "Pioneer AI", "confidence": 0.9}],
                        "Pain_Point": [
                            {"text": "expensive pipelines", "confidence": 0.8},
                            {"text": "days of manual work", "confidence": 0.7},
                        ],
                        "Action_Hook": [{"text": "use Agent Mode", "confidence": 0.85}],
                    },
                    "Emotional_Vibe": {
                        "label": "Theatrical Outrage",
                        "confidence": 0.76,
                    },
                }
            }
        }
    )
    assert result == {
        "Core_Subject": "Pioneer AI",
        "Pain_Point": "expensive pipelines",
        "Emotional_Vibe": "Theatrical Outrage",
        "Action_Hook": "use Agent Mode",
    }


def test_maps_canonical_vibe_label_to_theatrical_display_value() -> None:
    result = normalize_inference(
        {
            "Core_Subject": "Pioneer AI",
            "Pain_Point": "manual tuning",
            "Emotional_Vibe": "outrage",
            "Action_Hook": "automate it",
        }
    )
    assert result["Emotional_Vibe"] == "Theatrical Outrage"
