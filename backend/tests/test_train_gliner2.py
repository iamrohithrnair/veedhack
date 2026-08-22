from scripts.seed_corpus import _split_passages
from scripts.train_gliner2 import (
    MARKET_TOPICS,
    entities_from_inference,
    extract_ner_seeds,
    interleaved_topics,
    merge_unique_rows,
    to_ner_jsonl,
    valid_preview_rows,
)


def test_extracts_ner_seeds_from_label_existing_shapes() -> None:
    seeds = extract_ner_seeds(
        {
            "data": [
                {
                    "text": "Pioneer AI trains GLiNER in minutes instead of days.",
                    "entities": [
                        {"text": "Pioneer AI", "label": "Core_Subject"},
                        {"text": "days", "label": "Pain_Point"},
                        {"text": "trains GLiNER in minutes", "label": "Action_Hook"},
                    ],
                },
                {
                    "text": "Manual pipelines waste budget.",
                    "entities": {
                        "Core_Subject": [{"text": "Manual pipelines"}],
                        "Pain_Point": ["waste budget"],
                    },
                },
                {"text": "No entities here", "entities": []},
            ]
        }
    )
    assert seeds[0]["entities"] == [
        ["Pioneer AI", "Core_Subject"],
        ["days", "Pain_Point"],
        ["trains GLiNER in minutes", "Action_Hook"],
    ]
    assert seeds[1]["entities"] == [
        ["Manual pipelines", "Core_Subject"],
        ["waste budget", "Pain_Point"],
    ]
    assert len(seeds) == 2


def test_valid_preview_rows_require_text_and_entities() -> None:
    valid = valid_preview_rows(
        {
            "rows": [
                {"entities": []},
                {"text": "Pioneer AI ships Agent Mode.", "entities": [["Pioneer AI", "Core_Subject"]]},
            ]
        }
    )
    assert len(valid) == 1
    assert valid[0]["text"].startswith("Pioneer AI")


def test_entities_from_inference_use_exact_spans() -> None:
    text = "Pioneer AI lets teams fine-tune GLiNER models in minutes instead of days of manual pipeline work."
    entities = entities_from_inference(
        text,
        {
            "result": {
                "data": {
                    "entities": {
                        "Core_Subject": [
                            {"text": "Pioneer AI", "start": 0, "end": 10},
                            {"text": "not in the sentence", "start": 0, "end": 3},
                        ],
                        "Pain_Point": [{"text": "manual pipeline work", "confidence": 0.6}],
                    }
                }
            }
        },
    )
    assert entities == [
        ["Pioneer AI", "Core_Subject"],
        ["manual pipeline work", "Pain_Point"],
    ]


def test_to_ner_jsonl_matches_pioneer_row_contract() -> None:
    payload = to_ner_jsonl(
        [
            {
                "text": "Ada Lovelace worked in London.",
                "entities": [["Ada Lovelace", "PERSON"]],
            }
        ]
    )
    assert payload == (
        '{"text": "Ada Lovelace worked in London.", '
        '"entities": [["Ada Lovelace", "PERSON"]]}\n'
    )


def test_merge_unique_rows_keeps_first_copy() -> None:
    merged = merge_unique_rows(
        [{"text": "Pioneer AI ships Agent Mode.", "entities": [["Pioneer AI", "Core_Subject"]]}],
        [
            {"text": "Pioneer AI ships Agent Mode.", "entities": []},
            {"text": "Manual pipelines waste weeks.", "entities": [["weeks", "Pain_Point"]]},
        ],
    )
    assert len(merged) == 2
    assert merged[0]["entities"][0][0] == "Pioneer AI"


def test_split_passages_chunks_long_raw_content() -> None:
    long = "Pioneer AI ships Agent Mode. " * 40
    parts = _split_passages(long)
    assert len(parts) > 1
    assert all(len(part) >= 80 for part in parts)


def test_interleaved_topics_cover_three_markets() -> None:
    topics = interleaved_topics()
    assert set(MARKET_TOPICS) == {"b2b_sales", "edtech", "media"}
    assert topics[0] in MARKET_TOPICS["b2b_sales"]
    assert topics[1] in MARKET_TOPICS["edtech"]
    assert topics[2] in MARKET_TOPICS["media"]
    assert len(topics) == sum(len(items) for items in MARKET_TOPICS.values())
