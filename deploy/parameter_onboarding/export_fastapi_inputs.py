"""Inspect literal FastAPI Query/File signatures without importing service code.

This optional developer helper produces input-only OpenAPI for provider review.
It never imports the service, executes a route, calls an ML library or infers
output compatibility. Unsupported signatures/constraints fail closed.
"""
import argparse
import ast
import hashlib
import inspect
import json
from pathlib import Path

from fastapi import FastAPI, File, Query, UploadFile

TYPES = {"str": str, "int": int, "float": float, "bool": bool, "UploadFile": UploadFile}
KEYWORDS = {"default", "title", "description", "ge", "le", "gt", "lt", "min_length", "max_length", "pattern", "deprecated"}


def inspect_inputs(source: str, source_reference: str, selected_paths: list[str]):
    app = FastAPI(title="Source input signatures for provider review", description=(
        "Source-derived input signatures only. Runtime availability, parameter approval and output contracts are unverified. "
        "The service module and route bodies were not executed."))
    origins = []
    for function in ast.parse(source).body:
        if not isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in function.decorator_list:
            if not (isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute)
                    and isinstance(decorator.func.value, ast.Name) and decorator.func.value.id == "app"
                    and decorator.func.attr in {"get", "post", "put", "patch", "delete"}):
                continue
            if len(decorator.args) != 1 or not isinstance(decorator.args[0], ast.Constant) or not isinstance(decorator.args[0].value, str):
                raise ValueError("Route paths must be literal strings")
            path = decorator.args[0].value
            if path not in selected_paths:
                continue
            if function.args.posonlyargs or function.args.vararg or function.args.kwarg or function.args.kwonlyargs:
                raise ValueError("This helper supports literal positional-or-keyword Query/File signatures only")
            parameters = []
            defaults = [None] * (len(function.args.args) - len(function.args.defaults)) + function.args.defaults
            for argument, default in zip(function.args.args, defaults, strict=True):
                if not isinstance(argument.annotation, ast.Name) or argument.annotation.id not in TYPES:
                    raise ValueError(f"Unsupported input annotation for {argument.arg}")
                if not (isinstance(default, ast.Call) and isinstance(default.func, ast.Name) and default.func.id in {"Query", "File"}):
                    raise ValueError(f"Input {argument.arg} needs an explicit literal Query/File declaration")
                if len(default.args) > 1 or any(k.arg is None or k.arg not in KEYWORDS for k in default.keywords):
                    raise ValueError(f"Unsupported input declaration for {argument.arg}; obtain the full service OpenAPI instead")
                positional = [ast.literal_eval(value) for value in default.args]
                keywords = {k.arg: ast.literal_eval(k.value) for k in default.keywords}
                factory = Query if default.func.id == "Query" else File
                parameters.append(inspect.Parameter(argument.arg, inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=TYPES[argument.annotation.id], default=factory(*positional, **keywords)))
            def unavailable(**kwargs):
                raise RuntimeError("Interface inspection has no executable service")
            unavailable.__name__ = function.name
            unavailable.__signature__ = inspect.Signature(parameters)
            options = {}
            for keyword in decorator.keywords:
                if keyword.arg == "operation_id":
                    options["operation_id"] = ast.literal_eval(keyword.value)
            app.add_api_route(path, unavailable, methods=[decorator.func.attr.upper()], **options)
            origins.append({"path": path, "method": decorator.func.attr.upper(), "function": function.name, "line": function.lineno})
    missing = set(selected_paths) - {item["path"] for item in origins}
    if missing:
        raise ValueError("Selected paths were not inspected: " + ", ".join(sorted(missing)))
    document = app.openapi()
    document["x-ai-effect-source"] = {"reference": source_reference, "sha256": hashlib.sha256(source.encode()).hexdigest(),
                                      "scope": "source-input-signatures-only", "operations": origins}
    return document


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--source-reference", required=True)
    parser.add_argument("--path", action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    # Preserve original newlines in the recorded source digest.
    source = args.source.read_bytes().decode("utf-8")
    document = inspect_inputs(source, args.source_reference, args.path)
    args.output.write_text(json.dumps(document, indent=2) + "\n")
    print(f"Exported {len(document['x-ai-effect-source']['operations'])} source input signatures; no service code executed")


if __name__ == "__main__":
    main()
