"""
Tests for the cleanup() and _trim_to_theorem() functions in generate_concurrent.py.

Run with:  python -m pytest test_cleanup.py -v
"""
import pytest
from generate_concurrent import cleanup, _trim_to_theorem

# ---------------------------------------------------------------------------
# A minimal but realistic Lean proof used across many test cases
# ---------------------------------------------------------------------------
PROOF = "theorem foo (n : ℕ) : n + 0 = n := by simp"
LEMMA = "lemma bar (n : ℕ) : 0 + n = n := by simp"


# ---------------------------------------------------------------------------
# _trim_to_theorem
# ---------------------------------------------------------------------------
class TestTrimToTheorem:
    def test_no_preamble(self):
        assert _trim_to_theorem(PROOF) == PROOF

    def test_strips_preamble_before_theorem(self):
        snippet = f"Some explanation here.\n{PROOF}"
        assert _trim_to_theorem(snippet) == PROOF

    def test_works_with_lemma(self):
        snippet = f"Here is the proof:\n{LEMMA}"
        assert _trim_to_theorem(snippet) == LEMMA

    def test_no_theorem_or_lemma_returns_stripped(self):
        snippet = "  just some text  "
        assert _trim_to_theorem(snippet) == "just some text"

    def test_strips_leading_whitespace_after_trim(self):
        snippet = f"preamble\n  {PROOF}"
        assert _trim_to_theorem(snippet) == PROOF


# ---------------------------------------------------------------------------
# Strategy 1: explicit FINAL``` marker
# ---------------------------------------------------------------------------
class TestCleanupFinalMarker:
    def test_basic_final_no_language_tag(self):
        response = f"Here is my proof.\nFINAL```\n{PROOF}\n```"
        assert cleanup(response) == PROOF

    def test_final_with_lean_tag(self):
        response = f"Explanation.\nFINAL```lean\n{PROOF}\n```"
        assert cleanup(response) == PROOF

    def test_final_with_lean4_tag(self):
        response = f"Explanation.\nFINAL```lean4\n{PROOF}\n```"
        assert cleanup(response) == PROOF

    def test_final_case_insensitive(self):
        # The regex is IGNORECASE on the FINAL prefix
        response = f"final```lean\n{PROOF}\n```"
        assert cleanup(response) == PROOF

    def test_final_strips_preamble_before_theorem(self):
        response = f"FINAL```\n-- some comment\n{PROOF}\n```"
        assert cleanup(response) == PROOF

    def test_final_picks_longest_match(self):
        short = "theorem a : True := trivial"
        long_ = PROOF
        # Put the shorter one first so a naive first-match would be wrong
        response = f"FINAL```\n{short}\n```\nFINAL```\n{long_}\n```"
        assert cleanup(response) == long_

    def test_final_trusted_even_without_theorem_keyword(self):
        # FINAL marker is trusted unconditionally (model followed the format)
        response = "FINAL```\nby simp\n```"
        assert cleanup(response) == "by simp"


# ---------------------------------------------------------------------------
# Strategy 2: ```lean / ```lean4 code block (no FINAL prefix)
# ---------------------------------------------------------------------------
class TestCleanupLeanTagBlock:
    def test_lean_tag_block(self):
        response = f"Here is my proof:\n```lean\n{PROOF}\n```"
        assert cleanup(response) == PROOF

    def test_lean4_tag_block(self):
        response = f"Here is my proof:\n```lean4\n{PROOF}\n```"
        assert cleanup(response) == PROOF

    def test_lean_tag_block_strips_preamble(self):
        response = f"```lean\n-- preamble comment\n{PROOF}\n```"
        assert cleanup(response) == PROOF

    def test_lean_tag_block_ignored_without_theorem(self):
        # A ```lean block with no theorem/lemma should not be returned by strategy 2;
        # the function should fall through to later strategies or return the raw response.
        response = "```lean\nby simp\n```"
        # No later strategy will find a theorem either, so raw response is returned
        assert cleanup(response) == response

    def test_lean_tag_picks_longest(self):
        short = "theorem a : True := trivial"
        response = f"```lean\n{short}\n```\n```lean\n{PROOF}\n```"
        assert cleanup(response) == PROOF


# ---------------------------------------------------------------------------
# Strategy 3: any fenced code block containing theorem/lemma
# ---------------------------------------------------------------------------
class TestCleanupAnyCodeBlock:
    def test_plain_code_block_with_theorem(self):
        response = f"```\n{PROOF}\n```"
        assert cleanup(response) == PROOF

    def test_other_language_tag_with_theorem(self):
        # e.g. model tagged it as 'text' but it contains a theorem
        response = f"```text\n{PROOF}\n```"
        assert cleanup(response) == PROOF

    def test_code_block_with_lemma(self):
        response = f"```\n{LEMMA}\n```"
        assert cleanup(response) == LEMMA

    def test_code_block_without_theorem_skipped(self):
        # Block has no theorem/lemma — should fall through to strategy 4 or raw
        response = "```\nsome random code\n```\ntheorem foo : True := trivial"
        assert cleanup(response) == "theorem foo : True := trivial"


# ---------------------------------------------------------------------------
# Strategy 4: bare theorem/lemma keyword in plain text
# ---------------------------------------------------------------------------
class TestCleanupBareTheorem:
    def test_bare_theorem_in_text(self):
        response = f"Let me prove this.\n{PROOF}"
        assert cleanup(response) == PROOF

    def test_bare_lemma_in_text(self):
        response = f"Here:\n{LEMMA}"
        assert cleanup(response) == LEMMA

    def test_bare_theorem_strips_leading_text(self):
        response = f"Some long explanation.\n\n{PROOF}"
        assert cleanup(response) == PROOF


# ---------------------------------------------------------------------------
# Fallback: raw response
# ---------------------------------------------------------------------------
class TestCleanupFallback:
    def test_no_structure_returns_raw(self):
        # No theorem/lemma keyword and no code block — raw response is returned
        response = "I cannot solve this problem."
        assert cleanup(response) == response

    def test_empty_string(self):
        assert cleanup("") == ""


# ---------------------------------------------------------------------------
# Edge / regression cases
# ---------------------------------------------------------------------------
class TestCleanupEdgeCases:
    def test_multiline_proof_body(self):
        proof = (
            "theorem foo (n : ℕ) : n + 0 = n := by\n"
            "  induction n with\n"
            "  | zero => simp\n"
            "  | succ n ih => simp [Nat.succ_add, ih]"
        )
        response = f"FINAL```lean\n{proof}\n```"
        assert cleanup(response) == proof

    def test_final_marker_beats_lean_tag_block(self):
        # If both are present, the FINAL marker (strategy 1) should win
        other = "theorem other : True := trivial"
        response = f"```lean\n{other}\n```\nFINAL```lean\n{PROOF}\n```"
        assert cleanup(response) == PROOF

    def test_whitespace_only_inside_final_block(self):
        # The FINAL marker is trusted; content is all whitespace so _trim_to_theorem
        # finds no theorem keyword and returns an empty string.
        response = "FINAL```\n   \n```"
        assert cleanup(response) == ""

    def test_response_with_multiple_code_blocks_picks_one_with_theorem(self):
        response = (
            "First block has no proof:\n```\nsome output\n```\n"
            f"Second block has the proof:\n```\n{PROOF}\n```"
        )
        assert cleanup(response) == PROOF
