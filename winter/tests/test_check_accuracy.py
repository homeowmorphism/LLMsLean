"""
Tests for check_accuracy_all() in verify.py.

verify_single_result() and verify_parallel() require a live Lean server and
are not tested here. check_accuracy_all() is pure computation and fully
unit-testable.

Two modes, determined by whether "pass" appears in the filename:
  - Amend mode  ("pass" NOT in filename): returns per-round accuracy percentages.
  - Pass@k mode ("pass"     in filename): returns unbiased pass@k estimates (0–1).

Run with:  python -m pytest tests/ -v
"""
import math
import pytest
import jsonlines as jsl
from verify import check_accuracy_all


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def write_jsonl(path, records):
    with jsl.open(str(path), mode="w") as w:
        w.write_all(records)


def amend_path(tmp_path, name="results_amend@4.jsonl"):
    """Return a tmp path whose name does NOT contain 'pass' (amend mode)."""
    return tmp_path / name


def pass_path(tmp_path, name="results_pass@4.jsonl"):
    """Return a tmp path whose name DOES contain 'pass' (pass@k mode)."""
    return tmp_path / name


# ---------------------------------------------------------------------------
# Amend mode — accuracy percentage per round
# ---------------------------------------------------------------------------

class TestAmendMode:
    def test_single_theorem_all_pass(self, tmp_path):
        p = amend_path(tmp_path)
        write_jsonl(p, [{"verification": ["Pass", "Pass", "Pass"]}])
        assert check_accuracy_all(str(p)) == [100.0, 100.0, 100.0]

    def test_single_theorem_all_fail(self, tmp_path):
        p = amend_path(tmp_path)
        write_jsonl(p, [{"verification": ["Fail: error", "Fail: error"]}])
        assert check_accuracy_all(str(p)) == [0.0, 0.0]

    def test_two_theorems_half_pass_each_round(self, tmp_path):
        p = amend_path(tmp_path)
        write_jsonl(p, [
            {"verification": ["Pass", "Pass"]},
            {"verification": ["Fail: error", "Fail: error"]},
        ])
        assert check_accuracy_all(str(p)) == [50.0, 50.0]

    def test_accuracy_improves_across_rounds(self, tmp_path):
        # Theorem 1 passes in round 0; theorem 2 only passes in round 1
        p = amend_path(tmp_path)
        write_jsonl(p, [
            {"verification": ["Pass", "Pass"]},
            {"verification": ["Fail: error", "Pass"]},
        ])
        result = check_accuracy_all(str(p))
        assert result == [50.0, 100.0]

    def test_missing_verification_reduces_denominator(self, tmp_path):
        # Theorem without 'verification' is excluded from the denominator.
        # 1 theorem passes out of 2 that have verification entries (not 3 total).
        p = amend_path(tmp_path)
        write_jsonl(p, [
            {"verification": ["Pass"]},
            {"verification": ["Fail: error"]},
            {"formal_statement": "no verification key"},  # excluded
        ])
        result = check_accuracy_all(str(p))
        assert result == [50.0]

    def test_num_rounds_taken_from_first_verified_theorem(self, tmp_path):
        # num[] is sized from the first theorem that has a verification key.
        # Extra rounds in later theorems are silently ignored.
        p = amend_path(tmp_path)
        write_jsonl(p, [
            {"verification": ["Pass", "Pass"]},        # first: 2 rounds → sets size
            {"verification": ["Fail", "Pass", "Pass"]},  # extra round ignored
        ])
        result = check_accuracy_all(str(p))
        assert len(result) == 2

    def test_pass_substring_in_fail_string_not_counted(self, tmp_path):
        # "Fail: ..." should never contain "Pass", but guard against it
        p = amend_path(tmp_path)
        write_jsonl(p, [{"verification": ["Fail: type mismatch"]}])
        assert check_accuracy_all(str(p)) == [0.0]

    def test_four_theorems_three_pass(self, tmp_path):
        p = amend_path(tmp_path)
        write_jsonl(p, [
            {"verification": ["Pass"]},
            {"verification": ["Pass"]},
            {"verification": ["Pass"]},
            {"verification": ["Fail: error"]},
        ])
        assert check_accuracy_all(str(p)) == [75.0]


# ---------------------------------------------------------------------------
# Pass@k mode — unbiased pass@k estimator
# ---------------------------------------------------------------------------
#
# Formula: pass@k = (1/T) * sum_t [ 1 - C(n - c_t, k) / C(n, k) ]
#   n   = number of samples per theorem (same for all)
#   c_t = number of "Pass" entries for theorem t
#   T   = total number of theorems

class TestPassKMode:
    def test_all_pass_returns_ones(self, tmp_path):
        p = pass_path(tmp_path)
        write_jsonl(p, [
            {"verification": ["Pass", "Pass", "Pass"]},
            {"verification": ["Pass", "Pass", "Pass"]},
        ])
        result = check_accuracy_all(str(p))
        assert len(result) == 3
        assert all(math.isclose(v, 1.0) for v in result)

    def test_none_pass_returns_zeros(self, tmp_path):
        p = pass_path(tmp_path)
        write_jsonl(p, [
            {"verification": ["Fail: e", "Fail: e", "Fail: e"]},
            {"verification": ["Fail: e", "Fail: e", "Fail: e"]},
        ])
        result = check_accuracy_all(str(p))
        assert all(math.isclose(v, 0.0) for v in result)

    def test_known_values_n2_c1(self, tmp_path):
        # n=2, c=1 for a single theorem:
        #   pass@1 = 1 - C(1,1)/C(2,1) = 1 - 1/2 = 0.5
        #   pass@2 = 1 - C(1,2)/C(2,2) = 1 - 0/1 = 1.0
        p = pass_path(tmp_path)
        write_jsonl(p, [{"verification": ["Pass", "Fail: e"]}])
        result = check_accuracy_all(str(p))
        assert len(result) == 2
        assert math.isclose(result[0], 0.5)
        assert math.isclose(result[1], 1.0)

    def test_known_values_n3_c1(self, tmp_path):
        # n=3, c=1:
        #   pass@1 = 1 - C(2,1)/C(3,1) = 1 - 2/3 = 1/3
        #   pass@2 = 1 - C(2,2)/C(3,2) = 1 - 1/3 = 2/3
        #   pass@3 = 1 - C(2,3)/C(3,3) = 1 - 0/1 = 1.0
        p = pass_path(tmp_path)
        write_jsonl(p, [{"verification": ["Pass", "Fail: e", "Fail: e"]}])
        result = check_accuracy_all(str(p))
        assert len(result) == 3
        assert math.isclose(result[0], 1/3)
        assert math.isclose(result[1], 2/3)
        assert math.isclose(result[2], 1.0)

    def test_known_values_n4_c2(self, tmp_path):
        # n=4, c=2:
        #   pass@1 = 1 - C(2,1)/C(4,1) = 1 - 2/4 = 0.5
        #   pass@2 = 1 - C(2,2)/C(4,2) = 1 - 1/6 = 5/6
        #   pass@3 = 1 - C(2,3)/C(4,3) = 1 - 0/4 = 1.0
        #   pass@4 = 1 - C(2,4)/C(4,4) = 1 - 0/1 = 1.0
        p = pass_path(tmp_path)
        write_jsonl(p, [{"verification": ["Pass", "Pass", "Fail: e", "Fail: e"]}])
        result = check_accuracy_all(str(p))
        assert len(result) == 4
        assert math.isclose(result[0], 0.5)
        assert math.isclose(result[1], 5/6)
        assert math.isclose(result[2], 1.0)
        assert math.isclose(result[3], 1.0)

    def test_multiple_theorems_averaged(self, tmp_path):
        # Two theorems: one with c=2 (all pass, n=2), one with c=0 (none pass, n=2)
        #   theorem 1: pass@1 = 1.0,  pass@2 = 1.0
        #   theorem 2: pass@1 = 0.0,  pass@2 = 0.0
        #   average:   pass@1 = 0.5,  pass@2 = 0.5
        p = pass_path(tmp_path)
        write_jsonl(p, [
            {"verification": ["Pass", "Pass"]},
            {"verification": ["Fail: e", "Fail: e"]},
        ])
        result = check_accuracy_all(str(p))
        assert len(result) == 2
        assert math.isclose(result[0], 0.5)
        assert math.isclose(result[1], 0.5)

    def test_result_length_equals_n(self, tmp_path):
        p = pass_path(tmp_path)
        write_jsonl(p, [{"verification": ["Pass"] * 8}])
        result = check_accuracy_all(str(p))
        assert len(result) == 8

    def test_pass_at_k_is_nondecreasing(self, tmp_path):
        # More samples means at least as likely to find a solution
        p = pass_path(tmp_path)
        write_jsonl(p, [
            {"verification": ["Pass", "Fail: e", "Pass", "Fail: e"]},
            {"verification": ["Fail: e", "Pass", "Fail: e", "Pass"]},
        ])
        result = check_accuracy_all(str(p))
        for i in range(len(result) - 1):
            assert result[i] <= result[i + 1] + 1e-9
