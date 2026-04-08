import pytest
from verify import build_full_code

HEADER = "import Mathlib\nimport Aesop\n\nset_option maxHeartbeats 0\n\nopen BigOperators Real Nat Topology Rat\n\n"

FORMAL_STMT = "theorem target (n : ℕ) : n + 0 = n := by\n"


def make_theorem(response, formal_statement=FORMAL_STMT, header=HEADER):
    return {"header": header, "formal_statement": formal_statement, "responses": [response]}


# ---------------------------------------------------------------------------
# Core fix: unrelated theorem in response is replaced by formal_statement
# ---------------------------------------------------------------------------

def test_uses_formal_statement_not_response_declaration():
    """The model proved a different theorem — formal_statement must be used."""
    response = "theorem unrelated (x : ℕ) : x = x := by\n  rfl"
    result = build_full_code(make_theorem(response))
    assert "theorem target" in result
    assert "theorem unrelated" not in result


def test_proof_body_is_preserved():
    """Tactics from the model response are kept unchanged."""
    response = "theorem unrelated (x : ℕ) : x = x := by\n  simp\n  omega"
    result = build_full_code(make_theorem(response))
    assert "simp" in result
    assert "omega" in result


def test_correct_structure():
    """Full code = header + formal_statement + proof body (no duplication of ':= by')."""
    response = "theorem unrelated : True := by\n  trivial"
    result = build_full_code(make_theorem(response))
    assert result == HEADER + FORMAL_STMT + "  trivial"


# ---------------------------------------------------------------------------
# Proof body extraction edge cases
# ---------------------------------------------------------------------------

def test_multiline_proof_body():
    response = "theorem foo : True := by\n  constructor\n  · trivial\n  · trivial"
    result = build_full_code(make_theorem(response))
    assert "constructor" in result
    assert "trivial" in result
    assert result.startswith(HEADER + FORMAL_STMT)


def test_leading_newlines_stripped_from_proof_body():
    """Extra newlines between ':= by' and the first tactic are collapsed."""
    response = "theorem foo : True := by\n\n\n  trivial"
    result = build_full_code(make_theorem(response))
    # formal_stmt already ends with '\n', so there should be no double blank line
    assert "\n\n\n" not in result
    assert "trivial" in result


def test_markdown_lean_tag_stripped():
    """'lean\\n' prefix inserted by cleanup() is removed before processing."""
    response = "lean\ntheorem foo : True := by\n  trivial"
    result = build_full_code(make_theorem(response))
    assert "theorem target" in result
    assert "trivial" in result


def test_by_with_extra_whitespace():
    """':=   by' (extra spaces) is still matched."""
    response = "theorem foo : True :=   by\n  trivial"
    result = build_full_code(make_theorem(response))
    assert "theorem target" in result
    assert "trivial" in result


# ---------------------------------------------------------------------------
# Fallback behaviour
# ---------------------------------------------------------------------------

def test_fallback_when_no_formal_statement():
    """Without a formal_statement the raw response is used as-is."""
    theorem = {"header": HEADER, "responses": ["theorem foo : True := by\n  trivial"]}
    result = build_full_code(theorem)
    assert "theorem foo" in result
    assert result == HEADER + "theorem foo : True := by\n  trivial"


def test_fallback_when_formal_statement_empty():
    """Empty formal_statement string triggers the fallback path."""
    theorem = {"header": HEADER, "formal_statement": "", "responses": ["theorem foo : True := by\n  trivial"]}
    result = build_full_code(theorem)
    assert "theorem foo" in result


def test_fallback_when_no_by_in_response():
    """If the response has no ':= by', we cannot extract a proof body — use raw response."""
    response = "-- this is not a valid proof"
    result = build_full_code(make_theorem(response))
    assert result == HEADER + response


# ---------------------------------------------------------------------------
# Header is always included
# ---------------------------------------------------------------------------

def test_header_always_present():
    response = "theorem foo : True := by\n  trivial"
    result = build_full_code(make_theorem(response))
    assert result.startswith(HEADER)


def test_custom_header():
    custom_header = "import Mathlib\n\n"
    theorem = {"header": custom_header, "formal_statement": FORMAL_STMT, "responses": ["theorem foo : True := by\n  trivial"]}
    result = build_full_code(theorem)
    assert result.startswith(custom_header)
