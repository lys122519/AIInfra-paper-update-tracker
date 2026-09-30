"""Configurable title filters for keeping the tracker focused on AI Infra."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence


def _normalise_words(value: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", value.casefold())


def title_matches_expression(title: str, expression: str) -> bool:
    """Match expression tokens as prefixes of consecutive title tokens.

    Prefix matching supports configured stems such as ``schedul`` while the
    consecutive-token requirement prevents an exclusion like ``federated
    learning`` from matching unrelated words scattered across a title.
    """
    title_words = _normalise_words(title)
    expression_words = _normalise_words(expression)
    if not expression_words or len(expression_words) > len(title_words):
        return False

    width = len(expression_words)
    return any(
        all(
            title_word.startswith(expression_word)
            for title_word, expression_word in zip(window, expression_words)
        )
        for window in (
            title_words[index:index + width]
            for index in range(len(title_words) - width + 1)
        )
    )


def paper_passes_filters(title: str, matched_keyword: str, filters: Mapping | None) -> bool:
    """Return whether a title passes global exclusions and keyword context rules."""
    if not isinstance(filters, Mapping):
        return True

    exclusions = filters.get("exclude_title_keywords", [])
    if isinstance(exclusions, str):
        exclusions = [exclusions]
    if isinstance(exclusions, Sequence) and any(
        isinstance(expression, str) and title_matches_expression(title, expression)
        for expression in exclusions
    ):
        return False

    context_rules = filters.get("require_any_by_keyword", {})
    if not isinstance(context_rules, Mapping):
        return True

    required_expressions = next(
        (
            values
            for keyword, values in context_rules.items()
            if isinstance(keyword, str) and keyword.casefold() == matched_keyword.casefold()
        ),
        None,
    )
    if required_expressions is None:
        return True
    if isinstance(required_expressions, str):
        required_expressions = [required_expressions]
    if not isinstance(required_expressions, Sequence):
        return True

    valid_expressions = [
        value
        for value in required_expressions
        if isinstance(value, str) and value.strip()
    ]
    return not valid_expressions or any(
        title_matches_expression(title, expression) for expression in valid_expressions
    )
