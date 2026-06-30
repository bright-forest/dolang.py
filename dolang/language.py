import math
import copy

functions = {
    "log": math.log,
    "exp": math.exp,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "atan": math.atan,
    "tanh": math.tanh,
    "atanh": math.atanh,
    "min": min,
    "max": max,
    "minimum": min,
    "maximum": max,
    "abs": abs,
}

constants = {
    "pi": math.pi,
}


# this is a stupid implementation
class Language:

    functions = functions
    constants = constants
    objects = []
    object_names = []
    yaml_tags = []
    signatures = []

    def append(self, obj):

        self.objects.append(obj)
        self.object_names.append(obj.__name__)
        self.yaml_tags.append("!" + obj.__name__)

        # try to get signature
        try:
            sig = obj.signature
        except:
            sig = None
        self.signatures.append(sig)

    def isvalid(self, name):

        if name[0] == "!":
            name = name[1:]

        return name in self.object_names

    def get_from_tag(self, tag):
        assert tag[0] == "!"
        i = self.object_names.index(tag[1:])
        obj = self.objects[i]
        return obj

    def get_signature(self, tag):
        i = self.object_names.index(tag[1:])
        obj = self.objects[i]
        try:
            sig = obj.signature
        except:
            sig = None
        return sig


LANG = Language()


def language_element(el):
    LANG.append(el)
    return el


class ModelError(Exception):
    pass


def eval_data(data: "yaml_structure", calibration={}):

    import warnings
    from yaml import MappingNode, SequenceNode, ScalarNode

    from dolang.yaml_nodes import mapping_items, mapping_keys, mapping_get, sequence_values

    d = calibration.copy()
    d.update(functions)

    if isinstance(data, ScalarNode):

        val = data.value
        if isinstance(val, (float, int)):
            return val

        elif isinstance(val, str):
            # could be a string, could be an expression, could depend on other sections
            try:
                val = eval(val.replace("^", "**"), d)
            except Exception as e:
                warnings.warn(f"Impossible to evaluate expression: {val}")
            return val

        else:
            raise Exception("Unknown scalar node type.")

    elif isinstance(data, SequenceNode):

        tag = data.tag
        if tag != "tag:yaml.org,2002:seq" and not LANG.isvalid(tag):
            # unknown object type
            # lc = data.lc
            lc = data.start_mark
            msg = (
                f"Line {lc.line}, column {lc.column}.  Tag '{tag}' is not recognized.'"
            )
            raise ModelError(msg)

        # eval children
        children = [eval_data(ch, calibration) for ch in sequence_values(data)]

        if tag == "tag:yaml.org,2002:seq":
            return children
        else:
            objclass = LANG.get_from_tag(tag)
            return objclass(*children)

    elif isinstance(data, MappingNode):

        if (data.tag != "tag:yaml.org,2002:map") and data.tag == "!Function":
            return eval_function(data, calibration)

        tag = data.tag
        if tag != "tag:yaml.org,2002:map" and not LANG.isvalid(tag):
            # unknown object type
            lc = data.start_mark
            # lc = data.lc
            msg = (
                f"Line {lc.line}, column {lc.column}.  Tag '{tag}' is not recognized.'"
            )
            raise ModelError(msg)

        if tag != "tag:yaml.org,2002:map":
            # check argument names (ignore types for now)
            objclass = LANG.get_from_tag(tag)
            signature = LANG.get_signature(tag)
            sigkeys = [*signature.keys()]
            for a in mapping_keys(data):
                ## TODO account for repeated greek arguments
                if (a not in sigkeys) and (
                    greek_translation.get(a, None) not in sigkeys
                ):
                    lc = data.start_mark
                    sigstring = str.join(
                        ", ", [f"{k}={str(v)}" for k, v in signature.items()]
                    )
                    msg = f"Line {lc.line}, column {lc.column}. Unexpected argument '{a}'. Expected: '{objclass.__name__}({sigstring})'"
                    raise ModelError(msg)
                else:
                    try:
                        sigkeys.remove(a)
                    except:
                        sigkeys.remove(greek_translation[a])
            # remove optional arguments
            for sig in sigkeys:
                sigval = signature[sig]
                if sigval is not None and ("Optional" in sigval):
                    sigkeys.remove(sig)

            if len(sigkeys) > 0:
                sigstring = str.join(
                    ", ", [f"{k}={str(v)}" for k, v in signature.items()]
                )
                lc = data.lc
                msg = f"Line {lc.line}, column {lc.col}. Missing argument(s) '{str.join(', ',sigkeys)}'. Expected: '{objclass.__name__}({sigstring})'"
                raise ModelError(msg)

        # eval children
        children = []
        for key, ch in mapping_items(data):
            evd = eval_data(ch, calibration=calibration)
            if tag != "tag:yaml.org,2002:map":
                exptype = signature.get(key, None)
                if exptype in ["Matrix", "Optional[Matrix]"]:
                    matfun = LANG.get_from_tag("!Matrix")
                    try:
                        evd = matfun(*evd)
                    except:
                        lc = data.lc
                        msg = f"Line {lc.line}, column {lc.col}. Argument '{key}' could not be converted to Matrix"
                        raise ModelError(msg)
                elif exptype in ["Vector", "Optional[Vector]"]:
                    vectfun = LANG.get_from_tag("!Vector")
                    try:
                        evd = vectfun(*evd)
                    except:
                        lc = data.lc
                        msg = f"Line {lc.line}, column {lc.col}. Argument '{key}' could not be converted to Vector"
                        raise ModelError(msg)
            children.append(evd)

        kwargs = {k: v for (k, v) in zip(mapping_keys(data), children)}
        if tag == "tag:yaml.org,2002:map":
            return kwargs
        else:
            objclass = LANG.get_from_tag(tag)
            return objclass(**kwargs)

    else:
        raise Exception("Unknown data structure.")


def eval_function(data, calibration):
    from dolang.yaml_nodes import mapping_get_required, sequence_values

    args = tuple(sequence_values(mapping_get_required(data, "arguments")))
    content = copy.deepcopy(mapping_get_required(data, "value"))

    def fun(x):
        calib = calibration.copy()
        for i, a in enumerate(args):
            calib[a] = x[i]
        res = eval_data(content, calib)
        return res

    return fun


# GREEK TOLERANCE

greek_translation = {
    "Sigma": "Σ",
    "sigma": "σ",
    "rho": "ρ",
    "mu": "μ",
    "alpha": "α",
    "beta": "β",
}


def greekify_dict(arg):
    dd = dict()
    for k in arg:
        if k in greek_translation:
            key = greek_translation[k]
        else:
            key = k
        if key in dd:
            raise Exception(f"key {key} defined twice")
        dd[key] = arg[k]
    return dd


def greek_tolerance(fun):
    def f(*pargs, **args):
        nargs = greekify_dict(args)
        return fun(*pargs, **nargs)

    return f
