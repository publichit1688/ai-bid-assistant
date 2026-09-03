from app.services.risk_location import (
    attach_ocr_highlight_boxes,
    ensure_locatable_highlights,
    map_risks_to_rendered_pages,
)


def test_legacy_word_risk_is_mapped_to_rendered_page_by_quote():
    risks = [
        {
            "page": 1,
            "quote": "投标保证金必须按时提交",
            "highlight_words": ["投标保证金"],
        }
    ]
    pages = [
        {"page": 1, "text": "第一章 总则"},
        {"page": 2, "text": "投标 保证金必须按时提交，否则不予受理。"},
    ]

    assert map_risks_to_rendered_pages(risks, pages) == {"0": 2}


def test_rendered_page_mapping_keeps_original_page_when_term_is_repeated():
    risks = [{"page": 2, "highlight_words": ["资格审查要求"]}]
    pages = [
        {"page": 1, "text": "资格审查要求"},
        {"page": 2, "text": "资格审查要求"},
    ]

    assert map_risks_to_rendered_pages(risks, pages) == {"0": 2}


def test_existing_matching_highlight_is_preserved():
    risks = [{"page": 2, "quote": "资格审查要求", "highlight_words": ["资格审查"]}]
    pages = [{"page": 2, "text": "本页包含资格审查要求。"}]

    ensure_locatable_highlights(risks, pages)

    assert risks[0]["highlight_words"] == ["资格审查"]


def test_quote_backfills_highlight_only_from_matching_page_text():
    risks = [{"page": 1, "quote": "投标保证金必须按时提交", "highlight_words": ["无效词"]}]
    pages = [{"page": 1, "text": "投标 保证金必须按时提交，否则不予受理。"}]

    ensure_locatable_highlights(risks, pages)

    assert len(risks[0]["highlight_words"]) == 2
    assert risks[0]["highlight_words"][-1] in "投标保证金必须按时提交"


def test_short_or_wrong_page_overlap_does_not_create_false_highlight():
    risks = [{"page": 1, "quote": "资格要求", "highlight_words": ["无效词"]}]
    pages = [
        {"page": 1, "text": "本页只有资格两个字。"},
        {"page": 2, "text": "完整资格要求位于另一页。"},
    ]

    ensure_locatable_highlights(risks, pages, minimum_match=4)

    assert risks[0]["highlight_words"] == ["无效词"]


def test_ocr_boxes_are_attached_only_from_matching_risk_page_lines():
    risks = [
        {
            "page": 2,
            "quote": "投标保证金必须按时提交",
            "highlight_words": ["投标保证金"],
        }
    ]
    pages = [
        {
            "page": 2,
            "text": "投标保证金必须按时提交",
            "ocr_lines": [
                {
                    "text": "投标保证金必须按时提交",
                    "box": {"x": 0.1, "y": 0.2, "width": 0.5, "height": 0.04},
                },
                {
                    "text": "其他无关内容",
                    "box": {"x": 0.1, "y": 0.3, "width": 0.3, "height": 0.04},
                },
            ],
        },
        {
            "page": 3,
            "text": "投标保证金出现在错误页",
            "ocr_lines": [
                {
                    "text": "投标保证金",
                    "box": {"x": 0.1, "y": 0.4, "width": 0.3, "height": 0.04},
                }
            ],
        },
    ]

    attach_ocr_highlight_boxes(risks, pages)

    assert risks[0]["ocr_highlight_boxes"] == [
        {"x": 0.1, "y": 0.2, "width": 0.5, "height": 0.04}
    ]
