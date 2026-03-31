"""
Perch-Tag Verifier — Declarative Constraint Collector

Implements the tag function from spec 10-perch-tagging-rules.md.
Instead of raising errors, this module produces a list of typed
constraint objects that declare what relationships must hold for
equations to be well-typed.

Example output:
    NativeTag(var='k', perch='_arvl', group='prestate')
    IdentityRequired(var='a', perch_from='_arvl', perch_to='_dcsn')
    IdentityVerified(var='a', perch_from='_arvl', perch_to='_dcsn')
    MeasurabilityOK(var='k', var_perch='_arvl', block_perch='_dcsn')
    MeasurabilityViolation(var='c', var_perch='_dcsn', block_perch='_arvl')
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Union

from lark import Tree, Token


# ── Perch ordering ──────────────────────────────────────────────────
# Information order: _arvl ≤ _dcsn ≤ _cntn
# ⊤ (parameters/settings) is compatible with everything.

PERCH_ORDER = {'_arvl': 0, '_dcsn': 1, '_cntn': 2}

PERCH_DISPLAY = {
    '_arvl': '<',
    '_dcsn': '~',
    '_cntn': '>',
}

# Symbol group → native perch
GROUP_TO_PERCH: Dict[str, str] = {
    'prestate': '_arvl',
    'states': '_dcsn',
    'poststates': '_cntn',
    'controls': '_dcsn',
    'rewards': '_dcsn',
    'exogenous': '_dcsn',
}

UNIVERSAL_GROUPS = {'parameters', 'settings'}


def perch_leq(p1: str, p2: str) -> bool:
    """Check p1 ≤ p2 in the information order."""
    # Handle branch-refined continuation perches: _cntn.keep ≤ _cntn
    base1 = p1.split('.')[0] if '.' in p1 else p1
    base2 = p2.split('.')[0] if '.' in p2 else p2
    return PERCH_ORDER.get(base1, -1) <= PERCH_ORDER.get(base2, -1)


def display_perch(p: str) -> str:
    """Human-readable perch display."""
    if '.' in p:
        base, branch = p.split('.', 1)
        return f'{PERCH_DISPLAY.get(base, base)}.{branch}'
    return PERCH_DISPLAY.get(p, p)


# ── Constraint types ───────────────────────────────────────────────

@dataclass(frozen=True)
class TagConstraint:
    """Base for all declarative perch-tag constraints."""
    pass


@dataclass(frozen=True)
class NativeTag(TagConstraint):
    """tag(x) = {p}. Variable x is uniquely declared in group g
    with native perch p. Bare usage is valid (Rule 1)."""
    var: str
    perch: str
    group: str

    def __str__(self):
        return (f'tag({self.var}) = {{{display_perch(self.perch)}}} '
                f'— unique in {self.group}')


@dataclass(frozen=True)
class UniversalTag(TagConstraint):
    """tag(x) = T. Parameter or setting — measurable everywhere (Rule 5)."""
    var: str
    group: str

    def __str__(self):
        return f'tag({self.var}) = T — {self.group}, measurable everywhere'


@dataclass(frozen=True)
class AmbiguousTag(TagConstraint):
    """tag(x) = bot. Variable x appears in multiple groups without
    identity connection. Bare usage is ill-typed; explicit tags required
    everywhere (Rule 2)."""
    var: str
    groups: tuple  # e.g. ('prestate', 'states')
    perches: tuple  # e.g. ('_arvl', '_dcsn')

    def __str__(self):
        gs = ', '.join(self.groups)
        ps = ', '.join(display_perch(p) for p in self.perches)
        return (f'tag({self.var}) = bot — appears in [{gs}] '
                f'at perches [{ps}]. Must use explicit tags.')


@dataclass(frozen=True)
class IdentityRequired(TagConstraint):
    """For bare usage of x to be valid when x is in multiple groups,
    there must be an identity transition x[p_to] = x[p_from]
    in the transition equations (Rule 3 precondition)."""
    var: str
    perch_from: str
    perch_to: str

    def __str__(self):
        return (f'REQUIRED: identity {self.var}[{display_perch(self.perch_to)}] = '
                f'{self.var}[{display_perch(self.perch_from)}] '
                f'in transition equations')


@dataclass(frozen=True)
class IdentityVerified(TagConstraint):
    """Identity transition x[p_to] = x[p_from] found in equations.
    tag(x) = {p_from, p_to} — measurable at both perches (Rule 3)."""
    var: str
    perch_from: str
    perch_to: str

    def __str__(self):
        return (f'VERIFIED: {self.var}[{display_perch(self.perch_to)}] = '
                f'{self.var}[{display_perch(self.perch_from)}] '
                f'— tag({self.var}) = '
                f'{{{display_perch(self.perch_from)}, '
                f'{display_perch(self.perch_to)}}}')


@dataclass(frozen=True)
class IdentityMissing(TagConstraint):
    """Identity transition was required but not found. tag(x) remains bot.
    All uses of x must carry explicit perch tags."""
    var: str
    perch_from: str
    perch_to: str

    def __str__(self):
        return (f'MISSING: no identity {self.var}[{display_perch(self.perch_to)}] = '
                f'{self.var}[{display_perch(self.perch_from)}] found '
                f'— tag({self.var}) = bot, explicit tags required')


@dataclass(frozen=True)
class MeasurabilityOK(TagConstraint):
    """Variable x with tag(x) ni p_var used in block at perch p_block.
    p_var <= p_block. Well-typed."""
    var: str
    var_perch: str
    block_perch: str

    def __str__(self):
        return (f'{self.var}[{display_perch(self.var_perch)}] in block at '
                f'{display_perch(self.block_perch)}: '
                f'{display_perch(self.var_perch)} <= '
                f'{display_perch(self.block_perch)} OK')


@dataclass(frozen=True)
class MeasurabilityViolation(TagConstraint):
    """Variable x with tag(x) ni p_var used in block at perch p_block.
    p_var > p_block. Ill-typed — uses future information."""
    var: str
    var_perch: str
    block_perch: str

    def __str__(self):
        return (f'VIOLATION: {self.var}[{display_perch(self.var_perch)}] in block at '
                f'{display_perch(self.block_perch)}: '
                f'{display_perch(self.var_perch)} > '
                f'{display_perch(self.block_perch)} — future information!')


@dataclass(frozen=True)
class ShiftedVariable(TagConstraint):
    """Variable x declared with native perch p_native used with explicit
    tag x[p_shifted]. Distinct shifted object (Rule 4).
    Does not trigger Rule 2."""
    var: str
    native_perch: str
    shifted_perch: str

    def __str__(self):
        return (f'{self.var}[{display_perch(self.shifted_perch)}] is a shifted '
                f'variable (native: {display_perch(self.native_perch)})')


@dataclass(frozen=True)
class BranchTag(TagConstraint):
    """Variable x declared in branch-keyed poststate.
    tag(x) = {>.branch} — measurable at branch sub-algebra (Rule 1 + branching)."""
    var: str
    branch: str
    perch: str  # e.g. '_cntn.keep'

    def __str__(self):
        return (f'tag({self.var}) = {{{display_perch(self.perch)}}} '
                f'— branch poststate ({self.branch})')


# ── Equation scanning helpers ──────────────────────────────────────

def _extract_variables_from_tree(tree: Tree) -> List[Tuple[str, Optional[str], Optional[str]]]:
    """Walk an AST and extract all variable references as (name, perch, branch).

    For bare symbols (no perch tag), perch is None.
    For bare symbols (no branch), branch is None.
    """
    results = []
    _walk_for_variables(tree, results)
    return results


def _walk_for_variables(node, results):
    """Recursive AST walker."""
    if isinstance(node, Token):
        return
    if not isinstance(node, Tree):
        return

    if node.data == 'variable':
        name = node.children[0].children[0].value
        # Extract perch from date child
        if len(node.children) >= 2:
            date_token = node.children[1].children[0]
            raw = date_token.value
            try:
                int(raw)
                perch = None  # numeric timing, not a perch tag
            except (ValueError, TypeError):
                perch = raw  # perch tag string like '_arvl'
        else:
            perch = None
        # Extract branch label (third child)
        branch = None
        if len(node.children) >= 3 and isinstance(node.children[2], Token):
            branch = node.children[2].value
        results.append((name, perch, branch))

    elif node.data == 'symbol':
        name = node.children[0].value
        results.append((name, None, None))  # bare symbol

    else:
        for child in node.children:
            _walk_for_variables(child, results)


def _find_identity_transitions(equations: Dict[str, Tree]) -> Set[Tuple[str, str, str]]:
    """Scan equation ASTs for identity transitions: x[p2] = x[p1].

    Returns set of (var_name, perch_from, perch_to) tuples.
    """
    identities = set()

    for block_name, tree in equations.items():
        _scan_tree_for_identities(tree, identities)

    return identities


def _scan_tree_for_identities(tree, identities):
    """Find assignment/equality nodes of the form x[p1] = x[p2]."""
    if isinstance(tree, Token):
        return
    if not isinstance(tree, Tree):
        return

    if tree.data in ('assignment', 'equality'):
        lhs = tree.children[0]
        rhs = tree.children[1]

        lhs_var = _extract_single_variable(lhs)
        rhs_var = _extract_single_variable(rhs)

        if (lhs_var is not None and rhs_var is not None
                and lhs_var[0] == rhs_var[0]  # same name
                and lhs_var[1] is not None and rhs_var[1] is not None  # both have perch tags
                and lhs_var[1] != rhs_var[1]):  # different perches
            # Identity: x[p_lhs] = x[p_rhs]
            # Convention: perch_from is the earlier perch
            p1, p2 = lhs_var[1], rhs_var[1]
            if PERCH_ORDER.get(p1, 99) <= PERCH_ORDER.get(p2, 99):
                identities.add((lhs_var[0], p1, p2))
            else:
                identities.add((lhs_var[0], p2, p1))

    for child in tree.children:
        _scan_tree_for_identities(child, identities)


def _extract_single_variable(node) -> Optional[Tuple[str, Optional[str]]]:
    """If node is a single variable or symbol, return (name, perch_or_None)."""
    if isinstance(node, Token):
        return None
    if not isinstance(node, Tree):
        return None

    if node.data == 'variable':
        name = node.children[0].children[0].value
        if len(node.children) >= 2:
            raw = node.children[1].children[0].value
            try:
                int(raw)
                return (name, None)
            except (ValueError, TypeError):
                return (name, raw)
        return (name, None)

    if node.data == 'symbol':
        name = node.children[0].value
        return (name, None)

    return None


# ── Block perch mapping ────────────────────────────────────────────

# Equation block names → the perch at which the block is evaluated
BLOCK_TO_PERCH: Dict[str, str] = {
    'arvl_to_dcsn_transition': '_dcsn',
    'dcsn_to_cntn_transition': '_cntn',
    'rwd_function': '_dcsn',
    'cntn_to_dcsn_mover': '_dcsn',
    'dcsn_to_arvl_mover': '_arvl',
}


# ── Main verifier ──────────────────────────────────────────────────

def compute_tag_constraints(
    symbol_groups: Dict[str, List[str]],
    equations: Optional[Dict[str, Tree]] = None,
    branch_poststates: Optional[Dict[str, List[str]]] = None,
    identity_transitions: bool = False,
) -> List[TagConstraint]:
    """Compute declarative tag constraints for a stage.

    This is the main entry point. It implements the tag function from
    spec 10-perch-tagging-rules.md and returns a list of constraints
    that declare what relationships must hold for the stage to be
    well-typed.

    Args:
        symbol_groups: {group_name: [symbol_names]}
            e.g. {'prestate': ['a', 'h'], 'states': ['a', 'h'],
                   'controls': ['c'], 'parameters': ['R', 'beta']}

        equations: {block_name: parsed_AST}  (optional)
            If provided, the verifier scans for identity transitions
            and checks measurability of each variable usage.

        branch_poststates: {branch_name: [symbol_names]}  (optional)
            e.g. {'keep': ['w_keep', 'h_keep'], 'adjust': ['w_adj']}
            For branching stages where poststates are branch-keyed.

        identity_transitions: bool (default False)
            If True, all variables appearing in both prestate and states
            are treated as identity-connected (Rule 3). This handles the
            ``arvl_to_dcsn_transition: identity`` keyword.

    Returns:
        List of TagConstraint objects — the declarative specification
        of what the tag function produces and what must hold.
    """
    constraints: List[TagConstraint] = []

    # ── Step 1: Build name → groups mapping ────────────────────────
    # For each variable name, record which groups it appears in.
    name_to_groups: Dict[str, List[Tuple[str, str]]] = {}  # name → [(group, perch)]

    for group, names in symbol_groups.items():
        if group in UNIVERSAL_GROUPS:
            for name in names:
                constraints.append(UniversalTag(var=name, group=group))
            continue

        if group == 'poststates' and branch_poststates is not None:
            # When branch_poststates is provided, skip flat poststates —
            # branches are handled below.
            continue

        if group not in GROUP_TO_PERCH:
            # Skip groups we don't know about (values, values_marginal, etc.)
            continue

        perch = GROUP_TO_PERCH[group]
        for name in names:
            bare_name = name.split('[')[0] if '[' in name else name
            name_to_groups.setdefault(bare_name, []).append((group, perch))

    # Handle branch-keyed poststates (separate from the main loop so it
    # works whether or not 'poststates' appears in symbol_groups).
    branch_tagged_names: Set[str] = set()
    if branch_poststates is not None:
        for branch, branch_names in branch_poststates.items():
            branch_perch = f'_cntn.{branch}'
            for name in branch_names:
                constraints.append(BranchTag(
                    var=name, branch=branch, perch=branch_perch))
                name_to_groups.setdefault(name, []).append(
                    (f'poststates.{branch}', branch_perch))
                branch_tagged_names.add(name)

    # ── Step 2: Compute tag(x) for each variable name ──────────────
    # Collect the set of universal names for later measurability checks
    universal_names = set()
    for group in UNIVERSAL_GROUPS:
        if group in symbol_groups:
            universal_names.update(symbol_groups[group])

    # Names that appear in exactly one group → Rule 1 (unique)
    # Names that appear in multiple groups → Rule 2 (ambiguous) or Rule 3 (identity)
    multi_group_vars: Dict[str, List[Tuple[str, str]]] = {}

    for name, group_perch_list in name_to_groups.items():
        # Deduplicate by perch (same name in controls and states both map to _dcsn)
        unique_perches = set(p for _, p in group_perch_list)
        unique_groups = [g for g, _ in group_perch_list]

        if len(unique_perches) == 1:
            # Single perch — Rule 1 even if declared in multiple groups
            # Skip if already covered by a BranchTag
            if name in branch_tagged_names:
                continue
            g, p = group_perch_list[0]
            constraints.append(NativeTag(var=name, perch=p, group=g))
        else:
            # Multiple perches — potential Rule 2 or Rule 3
            multi_group_vars[name] = group_perch_list
            constraints.append(AmbiguousTag(
                var=name,
                groups=tuple(unique_groups),
                perches=tuple(sorted(unique_perches,
                                     key=lambda p: PERCH_ORDER.get(
                                         p.split('.')[0], 99))),
            ))
            # Generate identity requirement constraints
            sorted_perches = sorted(unique_perches,
                                    key=lambda p: PERCH_ORDER.get(
                                        p.split('.')[0], 99))
            for i in range(len(sorted_perches) - 1):
                constraints.append(IdentityRequired(
                    var=name,
                    perch_from=sorted_perches[i],
                    perch_to=sorted_perches[i + 1],
                ))

    # ── Step 3: Scan equations for identities (if provided) ────────
    # When identity_transitions=True, synthesize identity pairs for
    # every variable that appears in both prestate and states.
    identities: Set[Tuple[str, str, str]] = set()

    if identity_transitions:
        pre_names = set(symbol_groups.get('prestate', []))
        state_names = set(symbol_groups.get('states', []))
        for name in pre_names & state_names:
            identities.add((name, '_arvl', '_dcsn'))

    if equations is not None:
        identities |= _find_identity_transitions(equations)

    if identities or equations is not None:
        for name, gp_list in multi_group_vars.items():
            perches = sorted(
                set(p for _, p in gp_list),
                key=lambda p: PERCH_ORDER.get(p.split('.')[0], 99))

            for i in range(len(perches) - 1):
                p_from, p_to = perches[i], perches[i + 1]
                if (name, p_from, p_to) in identities:
                    constraints.append(IdentityVerified(
                        var=name, perch_from=p_from, perch_to=p_to))
                else:
                    constraints.append(IdentityMissing(
                        var=name, perch_from=p_from, perch_to=p_to))

    # ── Step 4: Check measurability of variable usages ─────────────
    if equations is not None:
        # Build effective tag map: name → set of perches
        tag_map = _build_tag_map(name_to_groups, multi_group_vars,
                                 identities, universal_names)

        for block_name, tree in equations.items():
            block_perch = BLOCK_TO_PERCH.get(block_name)
            if block_perch is None:
                continue  # unknown block type

            var_usages = _extract_variables_from_tree(tree)
            for var_name, var_perch_tag, branch in var_usages:
                if var_name in universal_names:
                    continue  # parameters always OK

                # Determine the effective perch of this usage
                if var_perch_tag is not None:
                    # Explicitly tagged: x[_arvl], x[_cntn], etc.
                    effective_perch = var_perch_tag
                    if branch:
                        effective_perch = f'{var_perch_tag}.{branch}'
                elif var_name in tag_map:
                    # Bare usage: use the tag map
                    perch_set = tag_map[var_name]
                    if not perch_set:
                        continue  # bot — already reported
                    # Use the minimal perch in the set
                    effective_perch = min(
                        perch_set,
                        key=lambda p: PERCH_ORDER.get(p.split('.')[0], 99))
                else:
                    continue  # unknown variable (likely a function name)

                # Check measurability: effective_perch ≤ block_perch
                if perch_leq(effective_perch, block_perch):
                    constraints.append(MeasurabilityOK(
                        var=var_name,
                        var_perch=effective_perch,
                        block_perch=block_perch))
                else:
                    constraints.append(MeasurabilityViolation(
                        var=var_name,
                        var_perch=effective_perch,
                        block_perch=block_perch))

        # ── Step 5: Detect shifted variables (Rule 4) ──────────────
        for block_name, tree in equations.items():
            var_usages = _extract_variables_from_tree(tree)
            for var_name, var_perch_tag, branch in var_usages:
                if var_perch_tag is None:
                    continue
                if var_name not in name_to_groups:
                    continue
                gp_list = name_to_groups[var_name]
                if len(set(p for _, p in gp_list)) == 1:
                    native_perch = gp_list[0][1]
                    if var_perch_tag != native_perch:
                        constraints.append(ShiftedVariable(
                            var=var_name,
                            native_perch=native_perch,
                            shifted_perch=var_perch_tag))

    return constraints


def _build_tag_map(
    name_to_groups: Dict[str, List[Tuple[str, str]]],
    multi_group_vars: Dict[str, List[Tuple[str, str]]],
    identities: Set[Tuple[str, str, str]],
    universal_names: Set[str],
) -> Dict[str, Set[str]]:
    """Build effective tag map: name → set of perches.

    For unique names: {native_perch}
    For multi-group names with identity: {perch1, perch2}
    For multi-group names without identity: empty set (bot)
    Parameters/settings: not in map (handled separately)
    """
    tag_map: Dict[str, Set[str]] = {}

    for name, gp_list in name_to_groups.items():
        if name in universal_names:
            continue

        unique_perches = set(p for _, p in gp_list)

        if len(unique_perches) == 1:
            tag_map[name] = unique_perches
        else:
            # Check if all adjacent perch pairs have identities
            sorted_perches = sorted(
                unique_perches,
                key=lambda p: PERCH_ORDER.get(p.split('.')[0], 99))
            all_connected = all(
                (name, sorted_perches[i], sorted_perches[i + 1]) in identities
                for i in range(len(sorted_perches) - 1)
            )
            if all_connected:
                tag_map[name] = unique_perches  # Rule 3: both perches valid
            else:
                tag_map[name] = set()  # bot: must use explicit tags

    return tag_map


# ── Pretty-printing ───────────────────────────────────────────────

def format_constraints(constraints: List[TagConstraint],
                       show_ok: bool = True) -> str:
    """Format a constraint list as a human-readable report.

    Args:
        constraints: Output of compute_tag_constraints.
        show_ok: If False, suppress MeasurabilityOK entries.
    """
    lines = []
    lines.append('=== Tag Verification Report ===\n')

    # Group by type
    tags = [c for c in constraints
            if isinstance(c, (NativeTag, UniversalTag, BranchTag, AmbiguousTag))]
    requirements = [c for c in constraints
                    if isinstance(c, (IdentityRequired, IdentityVerified,
                                     IdentityMissing))]
    checks = [c for c in constraints
              if isinstance(c, (MeasurabilityOK, MeasurabilityViolation))]
    shifted = [c for c in constraints if isinstance(c, ShiftedVariable)]

    if tags:
        lines.append('--- Tag assignments ---')
        for c in tags:
            lines.append(f'  {c}')
        lines.append('')

    if requirements:
        lines.append('--- Identity constraints ---')
        for c in requirements:
            lines.append(f'  {c}')
        lines.append('')

    if shifted:
        lines.append('--- Shifted variables (Rule 4) ---')
        for c in shifted:
            lines.append(f'  {c}')
        lines.append('')

    if checks:
        violations = [c for c in checks if isinstance(c, MeasurabilityViolation)]
        oks = [c for c in checks if isinstance(c, MeasurabilityOK)]

        if violations:
            lines.append('--- Measurability VIOLATIONS ---')
            for c in violations:
                lines.append(f'  {c}')
            lines.append('')

        if show_ok and oks:
            lines.append('--- Measurability checks (OK) ---')
            for c in oks:
                lines.append(f'  {c}')
            lines.append('')

    # Summary
    n_violations = sum(1 for c in constraints
                       if isinstance(c, (MeasurabilityViolation, IdentityMissing)))
    n_verified = sum(1 for c in constraints
                     if isinstance(c, IdentityVerified))
    n_required = sum(1 for c in constraints
                     if isinstance(c, IdentityRequired))

    lines.append(f'Summary: {len(constraints)} constraints, '
                 f'{n_required} identities required, '
                 f'{n_verified} verified, '
                 f'{n_violations} violations')

    return '\n'.join(lines)
