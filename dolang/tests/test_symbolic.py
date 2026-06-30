import ast
import dolang
from dolang.grammar import str_expression as to_source
from dolang.symbolic import stringify, list_variables, list_symbols
from dolang.grammar import Tree


def test_parsing():
    from dolang.grammar import str_expression, sanitize
    from dolang.symbolic import parse_string

    e = parse_string("s + a(0) + b[t-1] + b[t] + b[t+1]")
    print(e.pretty())

    e = parse_string("chi*n^eta*c^sigma - w(1)")
    print(e.pretty())

    e = parse_string("chi*n^eta*c^sigma - w(1) | 0.01 <= n <= 1.0")
    print(e.pretty())

    e = parse_string("chi*n^eta*c^sigma - w(1) ⟂ 0.01 <= n <= 1.0")
    print(e.pretty())

    e = parse_string("i = exp(z)*k^alpha*n^(1-alpha) - (m)^(-1/sigma)")
    print(e.pretty())
    f = sanitize(e, variables=["m"])
    print(str_expression(f))

    s = "i = exp(z)*k^alpha*n^(1-alpha) - (m)^(-1/sigma)"
    e = parse_string(s)

    s = "i = exp(z)*k^alpha*n^(1-alpha) - (m)^(-1/sigma)"
    # vars = ['z', 'p', 'k', 'n', 'i', 'm', 'V', 'u', 'y', 'c', 'rk', 'w', 'y', 'c']
    # print("HI")
    # v = sanitize(s, variables=vars)
    # print(v)
    e = parse_string(s)
    print(str_expression(e))


def test_parsing_unicode():

    from dolang.symbolic import parse_string

    s = "αα"
    e = parse_string(s)
    print(e)


def test_expectation():
    from dolang.symbolic import parse_string

    s = "𝔼[ (x[t+1] / x[t]) ]"
    e = parse_string(s)
    print(e.pretty())
    from dolang.symbolic import str_expression

    print(str_expression(e))


def test_expectation_bracket_form():
    """Test bracket form: E[...] and 𝔼[...]"""
    from dolang.symbolic import parse_string, str_expression

    # E[...] form
    e = parse_string("E[x]")
    assert e.data == "expectation"
    assert len(e.children) == 1  # just the formula
    s = str_expression(e)
    assert s == "𝔼[x]"

    # 𝔼[...] form
    e = parse_string("𝔼[V[t+1]]")
    assert e.data == "expectation"
    s = str_expression(e)
    assert "𝔼[" in s


def test_expectation_subscript_form():
    """Test new subscript form: E_{y}(...) and E_{y,z}(...)"""
    from dolang.symbolic import parse_string, str_expression

    # Single variable: E_{y}(...)
    e = parse_string("E_{y}(V[t])")
    assert e.data == "expectation"
    assert len(e.children) == 2  # exp_var_list and formula
    # First child should be exp_var_list with ["y"]
    assert e.children[0].data == "exp_var_list"
    assert e.children[0].children[0].value == "y"
    s = str_expression(e)
    assert s == "E_{y}(V[t])"

    # Multiple variables: E_{y,z}(...)
    e = parse_string("E_{y,z}(V[t] + x)")
    assert e.data == "expectation"
    assert len(e.children) == 2
    var_list = e.children[0]
    assert var_list.data == "exp_var_list"
    assert len(var_list.children) == 2
    assert var_list.children[0].value == "y"
    assert var_list.children[1].value == "z"
    s = str_expression(e)
    assert s == "E_{y,z}(V[t] + x)"


def test_expectation_conditional_subscript_form():
    """Test conditional subscript form: E_{y|y_pre}(...)"""
    from dolang.symbolic import parse_string, str_expression

    e = parse_string("E_{y|y_pre}(V[t])")
    assert e.data == "expectation"
    assert len(e.children) == 2

    cond = e.children[0]
    assert cond.data == "cond_exp_var_list"
    assert cond.children[0].data == "exp_var_list"
    assert cond.children[1].data == "exp_var_list"
    assert cond.children[0].children[0].value == "y"
    assert cond.children[1].children[0].value == "y_pre"

    s = str_expression(e)
    assert s == "E_{y|y_pre}(V[t])"


def test_expectation_legacy_form():
    """Test legacy function form: E_y(...) normalizes to expectation node"""
    from dolang.symbolic import parse_string, str_expression

    # E_y(...) should now be an expectation node, not a call
    e = parse_string("E_y(V[t])")
    assert e.data == "expectation"
    # Legacy form has EFUNCTION token + formula
    assert len(e.children) == 2
    s = str_expression(e)
    # Should print in normalized form
    assert s == "E_{y}(V[t])"

    # E_shock(...) with longer name
    e = parse_string("E_shock(dV[t+1])")
    assert e.data == "expectation"
    s = str_expression(e)
    assert s == "E_{shock}(dV[t+1])"


def test_expectation_unicode_subscript():
    """Test unicode subscript form: 𝔼_{y}(...)"""
    from dolang.symbolic import parse_string, str_expression

    e = parse_string("𝔼_{y}(V[t])")
    assert e.data == "expectation"
    s = str_expression(e)
    assert "E_{y}" in s or "𝔼" in s  # depends on printer output


def test_expectation_in_expression():
    """Test expectation within larger expressions"""
    from dolang.symbolic import parse_string, str_expression

    # Expectation in assignment
    e = parse_string("V[t] = E_{y}(V[t+1])")
    s = str_expression(e)
    assert "E_{y}" in s

    # Expectation with arithmetic
    e = parse_string("r * E_{y}(dV[t])")
    s = str_expression(e)
    assert "E_{y}" in s


def test_maximization_subscript_form():
    """Test new subscript form: max_{c}(...) and max_{c,a}(...)"""
    from dolang.symbolic import parse_string, str_expression

    # Single variable: max_{c}(...)
    e = parse_string("max_{c}(c^2 + V[t+1])")
    assert e.data == "maximization"
    assert len(e.children) == 2  # max_var_list and formula
    # First child should be max_var_list with ["c"]
    assert e.children[0].data == "max_var_list"
    assert e.children[0].children[0].value == "c"
    s = str_expression(e)
    assert "max_{c}" in s

    # Multiple variables: max_{c,a}(...)
    e = parse_string("max_{c,a}(c + a + V[t+1])")
    assert e.data == "maximization"
    assert len(e.children) == 2
    var_list = e.children[0]
    assert var_list.data == "max_var_list"
    assert len(var_list.children) == 2
    assert var_list.children[0].value == "c"
    assert var_list.children[1].value == "a"
    s = str_expression(e)
    assert "max_{c,a}" in s


def test_maximization_legacy_form():
    """Test legacy brace form: max_c{...} normalizes to maximization node"""
    from dolang.symbolic import parse_string, str_expression

    # max_c{...} should be a maximization node
    e = parse_string("max_c{c^2 + V[t]}")
    assert e.data == "maximization"
    # Legacy form has MAXIMIZE token + formula
    assert len(e.children) == 2
    s = str_expression(e)
    # Should print in normalized form
    assert "max_{c}" in s

    # max_ab{...} with longer name
    e = parse_string("max_ab{x + y}")
    assert e.data == "maximization"
    s = str_expression(e)
    assert s == "max_{ab}(x + y)"


def test_maximization_in_expression():
    """Test maximization within larger expressions"""
    from dolang.symbolic import parse_string, str_expression

    # Maximization in assignment (Bellman equation)
    e = parse_string("V[t] = max_{c}(c^2 + beta*V[t+1])")
    s = str_expression(e)
    assert "max_{c}" in s

    # Maximization with arithmetic
    e = parse_string("beta * max_{c}(c + r)")
    s = str_expression(e)
    assert "max_{c}" in s


def test_parse_string():
    from dolang.symbolic import parse_string

    e = parse_string("sin(a(1)+b+f(1)+f(4)+a[t+1])")
    assert isinstance(e, Tree)
    s = to_source(e)
    assert s == "sin(a[t+1] + b + f[t+1] + f[t+4] + a[t+1])"


def test_remove_timing():
    from dolang.symbolic import parse_string, remove_timing

    e = parse_string("sin(a(1)+b+f(1)+f(4)+a[t+1])")
    assert isinstance(e, Tree)
    s = to_source(e)
    rr = remove_timing(s)
    assert rr == "sin(a + b + f + f + a)"


def test_multiline():
    from dolang.symbolic import parse_string

    e = parse_string(
        "a ⟂ x <= y <= exp(z)\nb ⟂ x <= y <= z", start="complementarity_block"
    )
    assert len(e.children) == 2


def test_predicate():
    from dolang.symbolic import parse_string, str_expression

    e = parse_string("a[t] <= (x[t]+b)")
    print(e.pretty())
    print(str_expression(e))
    e = parse_string("∀t, a[t] <= (x[t]+b)")
    print(e.pretty())
    print(str_expression(e))


def test_subperiod():
    from dolang.symbolic import parse_string, str_expression

    e = parse_string("a[t$1] = a[t+1]")
    print(e.pretty())
    print(str_expression(e))
    e = parse_string("a[t$consumption] = a[t+1]")
    print(e.pretty())
    print(str_expression(e))
    from lark.lark import Lark


# def test_list_symbols_debug():
#     from dolang.symbolic import parse_string
#     e = parse_string('sin(a(1)+b+f(1)+f(4)+a(1)+a+a[t+1]+cos(0)')
#     l = ListSymbols(known_functions=['sin', 'f'])
#     l.visit(e)
#     # note that cos is recognized as variable
#     assert (l.variables == [(('a', 1), 4), (('a', 1), 22), (('cos', 0), 37)])
#     assert (l.constants == [('b', 9), ('a', 27)])
#     assert (l.functions == [('sin', 0), ('f', 11), ('f', 16)])
#     assert (l.problems == [['a', 0, 29, 'incorrect subscript']])


def test_list_symbols():
    from dolang.symbolic import parse_string

    e = parse_string("sin(a(1)+b+f(1)+f(4)+a(1))+cos(0)")
    ll = list_symbols(e)
    print(ll.variables)
    print(ll.parameters)
    # cos is recognized as a usual function
    assert ll.variables == [("a", 1), ("f", 1), ("f", 4)]
    assert ll.parameters == ["b"]


def test_list_variables():
    from dolang.symbolic import parse_string

    e = parse_string("sin(a(1)+b+f(1)+f(4)+sin(a)+k*cos(a(0)))")
    list_variables(e)
    assert list_variables(e) == [("a", 1), ("f", 1), ("f", 4), ("a", 0)]


def test_sanitize():

    from dolang.symbolic import sanitize, parse_string

    s = "sin(a(1)+b+a+f(-1)+f(4)+a(1))"

    expected = "sin(a[t+1] + b + a[t] + f[t-1] + f[t+4] + a[t+1])"
    assert sanitize(s, variables=["a", "f"]) == expected

    # # we also deal with = signs, and convert to python exponents
    # assert (sanitize("a(1) = a^3 + b") == "a(1) == (a) ** (3) + b")


def test_stringify():

    from dolang.symbolic import parse_string

    s = "sin(a(1) + b + a(0) + f(-1) + f(4) + a(1))"
    enes = stringify(s)
    assert enes == "sin(a__1_ + b_ + a__0_ + f_m1_ + f__4_ + a__1_)"


def test_time_shift():

    from dolang.symbolic import time_shift, stringify_parameter

    e = "sin(a(1) + b + a(0) + f(-1) + f(4) + a(1))"

    enes = stringify(time_shift(e, +1))
    assert (enes) == "sin(a__2_ + b_ + a__1_ + f__0_ + f__5_ + a__2_)"


# =====================================================================
# spec_0.1l — chained subscript V[perch][branch_label]
# =====================================================================

def test_chained_subscript_parse():
    """V[_cntn][work] parses → AST with 3 children (name, date, branch label)."""
    from dolang.symbolic import parse_string
    from lark.lexer import Token as LToken

    e = parse_string("V[_cntn][work]")
    assert e.data == "variable"
    assert len(e.children) == 3
    assert e.children[0].children[0].value == "V"      # name
    assert e.children[1].children[0].value == "_cntn"   # date (perch tag)
    assert isinstance(e.children[2], LToken)
    assert e.children[2].value == "work"                # branch label


def test_chained_subscript_roundtrip():
    """Round-trip: str_expression(parse_string(...)) preserves chained subscript."""
    from dolang.symbolic import parse_string, str_expression

    assert str_expression(parse_string("V[_cntn][work]")) == "V[_cntn][work]"
    assert str_expression(parse_string("V[_cntn][retire]")) == "V[_cntn][retire]"


def test_chained_subscript_glyph():
    """Glyph tags normalize correctly with branch label: V[>][work] → V[_cntn][work]."""
    from dolang.symbolic import parse_string, str_expression

    assert str_expression(parse_string("V[>][work]")) == "V[_cntn][work]"
    assert str_expression(parse_string("V[<][x]")) == "V[_arvl][x]"


def test_chained_subscript_variables_lister():
    """VariablesLister includes branch label as third tuple element."""
    from dolang.symbolic import parse_string
    from dolang.grammar import VariablesLister

    e = parse_string("V[_cntn][work] + V[_cntn][retire] + x[_dcsn]")
    vl = VariablesLister()
    vl.visit(e)
    assert ("V", "_cntn", "work") in vl.result.variables
    assert ("V", "_cntn", "retire") in vl.result.variables
    assert ("x", "_dcsn") in vl.result.variables


def test_chained_subscript_time_shift():
    """TimeShifter preserves branch labels on time-shifted variables."""
    from dolang.symbolic import parse_string, str_expression, time_shift

    # Perch tags are not time-shifted, branch label preserved
    e = parse_string("V[_cntn][work]")
    shifted = time_shift(e, 1)
    assert str_expression(shifted) == "V[_cntn][work]"


def test_no_branch_label_regression():
    """Variables without branch labels still work (regression)."""
    from dolang.symbolic import parse_string, str_expression

    assert str_expression(parse_string("V[_cntn]")) == "V[_cntn]"
    assert str_expression(parse_string("x[t+1]")) == "x[t+1]"
    assert str_expression(parse_string("a[t]")) == "a[t]"


# =====================================================================
# spec_0.1l — AGGREGATE binder
# =====================================================================

def test_aggregate_parse():
    """AGGREGATE_d(expr; params) parses → aggregate_call node."""
    from dolang.symbolic import parse_string

    e = parse_string("AGGREGATE_d(V[_cntn]; sigma)")
    assert e.data == "aggregate_call"
    assert e.children[0].value == "AGGREGATE_d"
    assert len(e.children) == 3  # head, arg1, arg2


def test_aggregate_roundtrip():
    """Round-trip for AGGREGATE binder."""
    from dolang.symbolic import parse_string, str_expression

    assert str_expression(parse_string("AGGREGATE_d(V[_cntn]; sigma)")) == \
        "AGGREGATE_d(V[_cntn]; sigma)"


def test_aggregate_with_branch_label():
    """AGGREGATE works with chained subscripts."""
    from dolang.symbolic import parse_string, str_expression

    s = "AGGREGATE_d(V[_cntn][work] - delta; V[_cntn][retire])"
    result = str_expression(parse_string(s))
    assert "AGGREGATE_d" in result
    assert "V[_cntn][work]" in result


# =====================================================================
# spec_0.1l — multi-alternative maximization
# =====================================================================

def test_maximization_multi_alternative():
    """max_{d}(expr1, expr2) parses with multiple alternatives."""
    from dolang.symbolic import parse_string, str_expression

    e = parse_string("max_{d}(V[_cntn][work] - delta, V[_cntn][retire])")
    assert e.data == "maximization"
    s = str_expression(e)
    assert "max_{d}" in s
    assert "V[_cntn][work]" in s
    assert "V[_cntn][retire]" in s
