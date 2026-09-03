import difflib
import re


def compact_text(value):
    return re.sub(r"\s+", "", str(value or ""))


def map_risks_to_rendered_pages(risks, pages, minimum_match=4):
    """Map legacy simulated Word risk pages onto rendered PDF pages."""
    if not isinstance(risks, list) or not isinstance(pages, list):
        return {}

    page_texts = [
        (int(page.get("page")), compact_text(page.get("text")))
        for page in pages
        if isinstance(page, dict)
        and str(page.get("page", "")).isdigit()
        and compact_text(page.get("text"))
    ]
    page_numbers = {page_number for page_number, _text in page_texts}
    result = {}
    for index, risk in enumerate(risks):
        if not isinstance(risk, dict):
            continue
        try:
            original_page = int(risk.get("page"))
        except (TypeError, ValueError, OverflowError):
            original_page = 1

        raw_highlights = risk.get("highlight_words") or []
        if not isinstance(raw_highlights, list):
            raw_highlights = []
        raw_terms = [*raw_highlights, risk.get("quote"), risk.get("keyword")]
        terms = sorted(
            {
                compact_text(term)
                for term in raw_terms
                if len(compact_text(term)) >= minimum_match
            },
            key=len,
            reverse=True,
        )

        mapped_page = original_page if original_page in page_numbers else 1
        for term in terms:
            matches = [
                page_number
                for page_number, page_text in page_texts
                if term in page_text
            ]
            if not matches:
                continue
            mapped_page = original_page if original_page in matches else matches[0]
            break
        result[str(index)] = mapped_page
    return result


def ensure_locatable_highlights(risks, pages, minimum_match=4):
    """Add a source-backed fallback only when every AI highlight misses."""
    if not isinstance(risks, list) or not isinstance(pages, list):
        return risks

    page_map = {
        int(page.get("page")): str(page.get("text") or "")
        for page in pages
        if isinstance(page, dict) and str(page.get("page", "")).isdigit()
    }
    for risk in risks:
        if not isinstance(risk, dict):
            continue
        try:
            page_number = int(risk.get("page"))
        except (TypeError, ValueError, OverflowError):
            continue
        page_raw = page_map.get(page_number, "")
        page_text = compact_text(page_raw)
        if not page_raw:
            continue

        words = risk.get("highlight_words") or []
        if not isinstance(words, list):
            words = []
        words = [str(word).strip() for word in words if str(word).strip()]
        if any(word in page_raw for word in words):
            risk["highlight_words"] = words
            continue

        quote = compact_text(risk.get("quote"))
        if not quote:
            risk["highlight_words"] = words
            continue
        match = difflib.SequenceMatcher(
            None, quote, page_text, autojunk=False
        ).find_longest_match()
        if match.size >= minimum_match:
            common = quote[match.a : match.a + match.size]
            fallback = None
            for length in range(min(len(common), 12), minimum_match - 1, -1):
                fallback = next(
                    (
                        common[start : start + length]
                        for start in range(0, len(common) - length + 1)
                        if common[start : start + length] in page_raw
                    ),
                    None,
                )
                if fallback:
                    break
            if fallback and fallback not in words:
                words.append(fallback)
        risk["highlight_words"] = words
    return risks


def attach_ocr_highlight_boxes(risks, pages, minimum_overlap=2):
    """Attach normalized OCR line boxes that match each risk's source terms."""
    if not isinstance(risks, list) or not isinstance(pages, list):
        return risks
    page_lines = {
        int(page.get("page")): page.get("ocr_lines") or []
        for page in pages
        if isinstance(page, dict)
        and str(page.get("page", "")).isdigit()
        and isinstance(page.get("ocr_lines"), list)
    }
    for risk in risks:
        if not isinstance(risk, dict):
            continue
        risk.pop("ocr_highlight_boxes", None)
        try:
            page_number = int(risk.get("page"))
        except (TypeError, ValueError, OverflowError):
            continue
        lines = page_lines.get(page_number, [])
        if not lines:
            continue
        raw_terms = risk.get("highlight_words") or []
        if not isinstance(raw_terms, list):
            raw_terms = []
        raw_terms = [*raw_terms, risk.get("quote")]
        terms = [compact_text(term) for term in raw_terms if compact_text(term)]
        boxes = []
        for line in lines:
            if not isinstance(line, dict):
                continue
            line_text = compact_text(line.get("text"))
            box = line.get("box")
            if not line_text or not isinstance(box, dict):
                continue
            direct_match = any(
                term in line_text or line_text in term
                for term in terms
                if min(len(term), len(line_text)) >= minimum_overlap
            )
            fuzzy_match = False
            if not direct_match:
                fuzzy_match = any(
                    difflib.SequenceMatcher(
                        None, term, line_text, autojunk=False
                    ).find_longest_match().size
                    >= max(minimum_overlap, min(4, len(term)))
                    for term in terms
                )
            if not direct_match and not fuzzy_match:
                continue
            try:
                normalized_box = {
                    "x": float(box["x"]),
                    "y": float(box["y"]),
                    "width": float(box["width"]),
                    "height": float(box["height"]),
                }
            except (KeyError, TypeError, ValueError):
                continue
            if normalized_box not in boxes:
                boxes.append(normalized_box)
        if boxes:
            risk["ocr_highlight_boxes"] = boxes
    return risks
