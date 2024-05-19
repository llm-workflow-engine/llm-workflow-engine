from typing import Dict, Any

import inspect

import docutils.parsers.rst
import docutils.utils
import docutils.frontend
import docutils.nodes


def type_mapping(dtype):
    """
    Map a Python data type to a corresponding JSON type string.

    Parameters
    ----------
    dtype : type
        The Python data type to map (e.g., float, int, str).

    Returns
    -------
    str
        The corresponding JSON type string (e.g., 'number', 'integer', 'string').
    """
    if dtype == float:
        return "number"
    elif dtype == int:
        return "integer"
    elif dtype == str:
        return "string"
    else:
        return "string"


def merge_argument_attrs_from_doc(attrs, param_name, parsed_doc):
    doc_attrs = parsed_doc.get(param_name)
    description = ""
    if doc_attrs:
        description = doc_attrs.get("description", "")
    attrs["description"] = description
    return attrs


def func_to_openai_tool_spec(name, func):
    argspec = inspect.getfullargspec(func)
    func_doc = inspect.getdoc(func)
    parsed_doc = parse_docstring(func_doc)
    func_description = parsed_doc.get("__description", "")
    params = argspec.annotations
    if "return" in params.keys():
        del params["return"]
    for param_name in argspec.args:
        if param_name == "self":
            continue
        params[param_name] = {"type": type_mapping(argspec.annotations[param_name])}
        params[param_name] = merge_argument_attrs_from_doc(
            params[param_name], param_name, parsed_doc
        )
    len_optional_params = len(argspec.defaults) if argspec.defaults else None
    return {
        "name": name,
        "description": func_description,
        "parameters": {
            "type": "object",
            "properties": params,
            "required": (
                argspec.args[1:-len_optional_params] if len_optional_params else argspec.args[1:]
            ),
        },
    }


# def func_to_json_schema_spec(name, func):
#     argspec = inspect.getfullargspec(func)
#     func_doc = inspect.getdoc(func)
#     parsed_doc = parse_docstring(func_doc)
#     func_description = parsed_doc.get("__description", "")
#     params = argspec.annotations
#     if "return" in params.keys():
#         del params["return"]
#     len_optional_params = len(argspec.defaults) if argspec.defaults else 0
#     required_params = argspec.args[:-len_optional_params] if len_optional_params else argspec.args
#     for param_name in argspec.args:
#         if param_name == "self":
#             continue
#         params[param_name] = {
#             "type": type_mapping(argspec.annotations[param_name]),
#             "title": param_name,
#             "description": param_name,
#         }
#         params[param_name] = merge_argument_attrs_from_doc(
#             params[param_name], param_name, parsed_doc
#         )
#         if param_name in required_params:
#             params[param_name]["required"] = True
#     return {
#         "title": name,
#         "description": func_description,
#         "properties": params,
#     }


def parse_rst(text: str) -> docutils.nodes.document:
    parser = docutils.parsers.rst.Parser()
    settings = docutils.frontend.get_default_settings(docutils.parsers.rst.Parser)
    document = docutils.utils.new_document("<rst-doc>", settings=settings)
    parser.parse(text, document)
    return document


def parse_type(type_str: str) -> Dict[str, Any]:
    type_info = {"optional": False}
    type_parts = type_str.split(",")
    if "optional" in type_parts:
        type_info["optional"] = True
        type_parts.remove("optional")
    type_info["type"] = eval(type_parts[0].strip())
    return type_info


def parse_docstring(docstring: str) -> Dict[str, Dict[str, Any]]:
    document = parse_rst(docstring)
    parsed_elements = {}
    description = []
    description_complete = False
    for elem in document.findall():
        if isinstance(elem, docutils.nodes.paragraph):
            if not description_complete and (
                not elem.parent or not isinstance(elem.parent, docutils.nodes.field_list)
            ):
                description.append(elem.astext())
        elif isinstance(elem, docutils.nodes.field_name):
            description_complete = True
            field_name = elem.astext()
            field_body = elem.parent.children[1].astext()
            if field_name.startswith(("param", "type", "raises", "return", "rtype")):
                try:
                    prefix, arg_name = field_name.split(" ", 1)
                except ValueError:
                    prefix = field_name.strip()
                    arg_name = None
                if arg_name and arg_name not in parsed_elements:
                    parsed_elements[arg_name] = {}
                if prefix == "param":
                    parsed_elements[arg_name]["description"] = field_body
                elif prefix == "type":
                    parsed_elements[arg_name].update(parse_type(field_body))
                elif prefix == "raises":
                    exception_type = arg_name
                    if prefix not in parsed_elements:
                        parsed_elements[prefix] = {}
                    parsed_elements[prefix]["description"] = field_body
                    parsed_elements[prefix]["type"] = eval(exception_type)
                elif prefix == "return":
                    parsed_elements["return"] = {"description": field_body}
                elif prefix == "rtype":
                    parsed_elements["return"].update(parse_type(field_body))
    parsed_elements["__description"] = " ".join(description)
    return parsed_elements
