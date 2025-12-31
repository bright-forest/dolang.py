def test_syntax_errors():

    from dolang.grammar import parse_string
    import os
    import yaml

    DIR_PATH, this_filename = os.path.split(__file__)
    DATA_PATH = os.path.join(DIR_PATH, "syntax_errors.yaml")

    txt = open(DATA_PATH, "rt", encoding="utf-8").read()
    data = yaml.compose(txt)

    from dolang.yaml_nodes import mapping_get_required, sequence_values

    equations = mapping_get_required(data, "equations")

    try:
        list_node = mapping_get_required(equations, "list")
        parse_string(sequence_values(list_node)[1], start="equation")
    except Exception as e:
        assert e.line == 13
        assert e.column == 29

    try:
        parse_string(mapping_get_required(equations, "block"), start="equation_block")
    except Exception as e:
        assert e.line == 17
        assert e.column == 29

    try:
        parse_string(mapping_get_required(equations, "block2"), start="equation_block")
    except Exception as e:
        assert e.line == 25
        assert e.column == 29

    try:
        inline_node = mapping_get_required(equations, "inline")
        parse_string(sequence_values(inline_node)[1], start="equation")
    except Exception as e:
        assert e.line == 27
        assert e.column == 26


test_syntax_errors()


def test_variable_definitions_errors():

    from dolang.grammar import parse_string
    from lark.exceptions import UnexpectedCharacters
    import os
    import yaml

    DIR_PATH, this_filename = os.path.split(__file__)
    DATA_PATH = os.path.join(DIR_PATH, "syntax_errors.yaml")

    txt = open(DATA_PATH, "rt", encoding="utf-8").read()
    data = yaml.compose(txt)

    from dolang.yaml_nodes import mapping_get_required

    definitions = mapping_get_required(data, "definitions")
    for v in definitions.value:
        k = v[0]
        v = v[1].value
        if v == "None":
            parse_string(k, start="variable")  # no problem
        else:
            line = int(v[0].value)
            column = int(v[1].value)
            try:
                parse_string(k, start="variable")  # no problem
            except UnexpectedCharacters as e:
                assert e.column == column
                assert e.line == line
