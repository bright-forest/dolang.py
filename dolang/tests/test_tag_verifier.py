"""
Tests for the declarative tag verifier (perch-tagging rules).

Each test demonstrates a rule from spec 10-perch-tagging-rules.md
and checks that the verifier produces the correct constraints.
"""

import pytest
from dolang.grammar import parse_string
from dolang.tag_verifier import (
    compute_tag_constraints,
    format_constraints,
    NativeTag,
    UniversalTag,
    AmbiguousTag,
    IdentityRequired,
    IdentityVerified,
    IdentityMissing,
    MeasurabilityOK,
    MeasurabilityViolation,
    ShiftedVariable,
    BranchTag,
)


def _parse_block(text: str):
    """Parse a multi-line equation block."""
    return parse_string(text, start='assignment_block')


def _parse_eq_block(text: str):
    """Parse a multi-line equation block (may contain non-assignment eqs)."""
    return parse_string(text, start='equation_block')


# ── Rule 1: Unique name ──────────────────────────────────────────

class TestRule1Unique:
    """If a variable name appears in exactly one group, tag = {native perch}."""

    def test_unique_names_get_native_tags(self):
        symbols = {
            'prestate': ['k'],
            'states': ['m'],
            'controls': ['c'],
            'poststates': ['a_nxt'],
        }
        constraints = compute_tag_constraints(symbols)

        native_tags = [c for c in constraints if isinstance(c, NativeTag)]
        names = {c.var: c.perch for c in native_tags}

        assert names['k'] == '_arvl'
        assert names['m'] == '_dcsn'
        assert names['c'] == '_dcsn'
        assert names['a_nxt'] == '_cntn'

    def test_no_ambiguity_for_unique(self):
        symbols = {
            'prestate': ['k'],
            'states': ['m'],
            'controls': ['c'],
        }
        constraints = compute_tag_constraints(symbols)
        ambiguous = [c for c in constraints if isinstance(c, AmbiguousTag)]
        assert len(ambiguous) == 0


# ── Rule 2: Reused name ─────────────────────────────────────────

class TestRule2Reused:
    """If a variable name appears in multiple groups at different perches,
    bare usage gives bot; explicit tags required."""

    def test_reused_name_gives_ambiguous(self):
        symbols = {
            'prestate': ['a'],
            'states': ['a'],
        }
        constraints = compute_tag_constraints(symbols)

        ambiguous = [c for c in constraints if isinstance(c, AmbiguousTag)]
        assert len(ambiguous) == 1
        assert ambiguous[0].var == 'a'
        assert '_arvl' in ambiguous[0].perches
        assert '_dcsn' in ambiguous[0].perches

    def test_reused_name_generates_identity_requirement(self):
        symbols = {
            'prestate': ['a'],
            'states': ['a'],
        }
        constraints = compute_tag_constraints(symbols)

        required = [c for c in constraints if isinstance(c, IdentityRequired)]
        assert len(required) == 1
        assert required[0].var == 'a'
        assert required[0].perch_from == '_arvl'
        assert required[0].perch_to == '_dcsn'


# ── Rule 3: Identity exception ──────────────────────────────────

class TestRule3Identity:
    """If x appears in two groups AND an identity transition x[p2] = x[p1]
    exists, then tag(x) = {p1, p2}. Bare usage is valid."""

    def test_identity_verified_when_present(self):
        symbols = {
            'prestate': ['a', 'h'],
            'states': ['a', 'h'],
            'controls': ['c'],
        }
        equations = {
            'arvl_to_dcsn_transition': _parse_block(
                'a[_dcsn] = a[_arvl]\n'
                'h[_dcsn] = h[_arvl]'
            ),
        }
        constraints = compute_tag_constraints(symbols, equations)

        verified = [c for c in constraints if isinstance(c, IdentityVerified)]
        verified_names = {c.var for c in verified}
        assert 'a' in verified_names
        assert 'h' in verified_names

    def test_identity_missing_when_absent(self):
        symbols = {
            'prestate': ['a'],
            'states': ['a'],
        }
        equations = {
            'arvl_to_dcsn_transition': _parse_block(
                'a[_dcsn] = R[_arvl] * a[_arvl] + y[_arvl]'
            ),
        }
        # This is NOT an identity (RHS is an expression, not bare a[_arvl])
        # But our scanner looks for direct identity form x[p1] = x[p2]
        constraints = compute_tag_constraints(symbols, equations)

        missing = [c for c in constraints if isinstance(c, IdentityMissing)]
        assert len(missing) == 1
        assert missing[0].var == 'a'


# ── Rule 4: Shifted variables ──────────────────────────────────

class TestRule4Shifted:
    """A Rule-1 variable with a non-native tag creates a distinct shifted object."""

    def test_shifted_detected(self):
        symbols = {
            'controls': ['c'],
        }
        equations = {
            'cntn_to_dcsn_mover': _parse_eq_block(
                'c[_cntn] = (beta * d_{c}V[_cntn])^(-1)'
            ),
        }
        constraints = compute_tag_constraints(symbols, equations)

        shifted = [c for c in constraints if isinstance(c, ShiftedVariable)]
        assert len(shifted) >= 1
        c_shifted = [s for s in shifted if s.var == 'c']
        assert len(c_shifted) == 1
        assert c_shifted[0].native_perch == '_dcsn'
        assert c_shifted[0].shifted_perch == '_cntn'


# ── Rule 5: Constants ──────────────────────────────────────────

class TestRule5Constants:
    """Parameters and settings are measurable everywhere (tag = top)."""

    def test_parameters_get_universal_tag(self):
        symbols = {
            'parameters': ['R', 'beta', 'gamma'],
            'settings': ['n_a'],
            'states': ['m'],
        }
        constraints = compute_tag_constraints(symbols)

        universals = [c for c in constraints if isinstance(c, UniversalTag)]
        universal_names = {c.var for c in universals}
        assert 'R' in universal_names
        assert 'beta' in universal_names
        assert 'gamma' in universal_names
        assert 'n_a' in universal_names


# ── Measurability checks ──────────────────────────────────────

class TestMeasurability:
    """Variable at perch p used in block at perch q: p <= q must hold."""

    def test_arrival_var_in_decision_block_ok(self):
        symbols = {
            'prestate': ['k'],
            'states': ['m'],
            'parameters': ['R', 'y'],
        }
        equations = {
            'arvl_to_dcsn_transition': _parse_block(
                'm[_dcsn] = R * k[_arvl] + y'
            ),
        }
        constraints = compute_tag_constraints(symbols, equations)

        ok_checks = [c for c in constraints
                     if isinstance(c, MeasurabilityOK) and c.var == 'k']
        assert len(ok_checks) >= 1

    def test_continuation_var_in_decision_block_violation(self):
        symbols = {
            'poststates': ['a_nxt'],
            'controls': ['c'],
        }
        equations = {
            'rwd_function': _parse_eq_block(
                'a_nxt[_cntn]^(1-gamma)'
            ),
        }
        constraints = compute_tag_constraints(symbols, equations)

        violations = [c for c in constraints
                      if isinstance(c, MeasurabilityViolation)]
        assert len(violations) >= 1
        assert violations[0].var == 'a_nxt'
        assert violations[0].var_perch == '_cntn'
        assert violations[0].block_perch == '_dcsn'


# ── Branching ────────────────────────────────────────────────

class TestBranching:
    """Branch-keyed poststates create branch sub-algebra tags."""

    def test_branch_tags_assigned(self):
        symbols = {
            'states': ['a', 'h'],
            'controls': ['d'],
        }
        branch_poststates = {
            'keep': ['w_keep', 'h_keep'],
            'adjust': ['w_adj'],
        }
        constraints = compute_tag_constraints(
            symbols, branch_poststates=branch_poststates)

        branch_tags = [c for c in constraints if isinstance(c, BranchTag)]
        tag_map = {c.var: c.perch for c in branch_tags}

        assert tag_map['w_keep'] == '_cntn.keep'
        assert tag_map['h_keep'] == '_cntn.keep'
        assert tag_map['w_adj'] == '_cntn.adjust'


# ── Full stage: tenure-choice ────────────────────────────────

class TestTenureChoice:
    """Integration test: the housing tenure-choice stage
    with identity transitions a=a[<], h=h[<]."""

    def test_full_constraint_report(self):
        symbols = {
            'prestate': ['a', 'h'],
            'states': ['a', 'h'],
            'controls': ['d'],
            'parameters': ['R', 'R_H', 'delta'],
        }
        branch_poststates = {
            'keep': ['w_keep', 'h_keep'],
            'adjust': ['w_adj'],
        }
        equations = {
            'arvl_to_dcsn_transition': _parse_block(
                'a[_dcsn] = a[_arvl]\n'
                'h[_dcsn] = h[_arvl]'
            ),
        }

        constraints = compute_tag_constraints(
            symbols, equations, branch_poststates)

        # a and h should be ambiguous (in prestate + states)
        ambiguous = {c.var for c in constraints if isinstance(c, AmbiguousTag)}
        assert 'a' in ambiguous
        assert 'h' in ambiguous

        # Identities should be required and verified
        verified = {c.var for c in constraints if isinstance(c, IdentityVerified)}
        assert 'a' in verified
        assert 'h' in verified

        # No missing identities
        missing = [c for c in constraints if isinstance(c, IdentityMissing)]
        assert len(missing) == 0

        # Parameters should be universal
        universals = {c.var for c in constraints if isinstance(c, UniversalTag)}
        assert 'R' in universals
        assert 'R_H' in universals

        # Branch tags
        branch_tags = {c.var: c.perch
                       for c in constraints if isinstance(c, BranchTag)}
        assert branch_tags['w_keep'] == '_cntn.keep'
        assert branch_tags['w_adj'] == '_cntn.adjust'

        # Print the report for visual inspection
        report = format_constraints(constraints, show_ok=False)
        print('\n' + report)


# ── Format output ────────────────────────────────────────────

class TestFormatting:
    """The constraint report should be human-readable."""

    def test_format_basic(self):
        symbols = {
            'prestate': ['a'],
            'states': ['a'],
            'parameters': ['R'],
        }
        constraints = compute_tag_constraints(symbols)
        report = format_constraints(constraints)

        assert 'Tag Verification Report' in report
        assert 'bot' in report  # a should be ambiguous
        assert 'T' in report  # R should be universal
        assert 'REQUIRED' in report  # identity needed for a
