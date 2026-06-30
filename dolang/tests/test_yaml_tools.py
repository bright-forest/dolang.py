def test_yaml_extension():

    txt = """
        name: "Model"

        symbols:
            controls: [alpha, beta]
            states: [hei, ho]

        equations:
            arbitrage: |

                β*(c[t+1]/c[t])^(-γ+)*r - 1
                β*(c[t+1]/c[t])^(-γ)*(r_2[t+1]-r_1[t+1])
        
        calibration:
            a: 0.1
            b: 10
    """

    import yaml

    data = yaml.compose(txt)

    from dolang.yaml_nodes import (
        mapping_has,
        mapping_get_required,
        mapping_get,
        mapping_keys,
        sequence_values,
    )

    assert mapping_has(data, "name")
    assert not mapping_has(data, "equation")

    assert mapping_get_required(data, "name").value == "Model"

    symbols = mapping_get_required(data, "symbols")
    controls = mapping_get_required(symbols, "controls")
    assert [e.value for e in sequence_values(controls)] == ["alpha", "beta"]

    assert mapping_keys(symbols) == ["controls", "states"]
