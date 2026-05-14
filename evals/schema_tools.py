"""JSON-schema helpers for evals (mirrors servers/fastapi/utils/schema_utils subset)."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

# OpenAI structured outputs accept only these string formats (see server schema_utils).
supported_string_formats = [
    "date-time",
    "time",
    "date",
    "duration",
    "email",
    "hostname",
    "ipv4",
    "ipv6",
    "uuid",
]


def has_more_than_n_keys(obj: dict[str, object], n: int) -> bool:
    i = 0
    for _ in obj.keys():
        i += 1
        if i > n:
            return True
    return False


def resolve_ref(*, root: dict[str, object], ref: str) -> object:
    if not ref.startswith("#/"):
        raise ValueError(f"Unexpected $ref format {ref!r}; does not start with #/")

    path = ref[2:].split("/")
    resolved: object = root
    for key in path:
        value = resolved[key]  # type: ignore[index]
        assert isinstance(
            value, dict
        ), f"encountered non-dictionary entry while resolving {ref} - {resolved}"
        resolved = value

    return resolved


def ensure_strict_json_schema(
    json_schema: object,
    *,
    path: tuple[str, ...],
    root: dict[str, object],
) -> dict[str, Any]:
    """Mutate JSON schema for OpenAI `response_format` strict mode (additionalProperties, etc.)."""
    if not isinstance(json_schema, dict):
        raise TypeError(f"Expected {json_schema} to be a dictionary; path={path}")

    defs = json_schema.get("$defs")
    if isinstance(defs, dict):
        for def_name, def_schema in defs.items():
            ensure_strict_json_schema(
                def_schema, path=(*path, "$defs", def_name), root=root
            )

    definitions = json_schema.get("definitions")
    if isinstance(definitions, dict):
        for definition_name, definition_schema in definitions.items():
            ensure_strict_json_schema(
                definition_schema,
                path=(*path, "definitions", definition_name),
                root=root,
            )

    typ = json_schema.get("type")
    is_object_type = typ == "object" or (
        isinstance(typ, list) and "object" in typ
    )
    has_properties = isinstance(json_schema.get("properties"), dict) and bool(
        json_schema.get("properties")
    )
    if is_object_type or has_properties:
        json_schema["additionalProperties"] = False

    properties = json_schema.get("properties")
    if isinstance(properties, dict):
        json_schema["required"] = [prop for prop in properties.keys()]
        json_schema["properties"] = {
            key: ensure_strict_json_schema(
                prop_schema, path=(*path, "properties", key), root=root
            )
            for key, prop_schema in properties.items()
        }

    items = json_schema.get("items")
    if isinstance(items, dict):
        json_schema["items"] = ensure_strict_json_schema(
            items, path=(*path, "items"), root=root
        )
    elif typ == "array":
        prefix_items = json_schema.get("prefixItems")
        if (
            isinstance(prefix_items, list)
            and len(prefix_items) > 0
            and isinstance(prefix_items[0], dict)
        ):
            json_schema["items"] = ensure_strict_json_schema(
                prefix_items[0], path=(*path, "items"), root=root
            )
            json_schema.pop("prefixItems", None)
        else:
            json_schema["items"] = {"type": "string"}

    any_of = json_schema.get("anyOf")
    if isinstance(any_of, list):
        json_schema["anyOf"] = [
            ensure_strict_json_schema(variant, path=(*path, "anyOf", str(i)), root=root)
            for i, variant in enumerate(any_of)
        ]

    all_of = json_schema.get("allOf")
    if isinstance(all_of, list):
        if len(all_of) == 1:
            json_schema.update(
                ensure_strict_json_schema(
                    all_of[0], path=(*path, "allOf", "0"), root=root
                )
            )
            json_schema.pop("allOf")
        else:
            json_schema["allOf"] = [
                ensure_strict_json_schema(
                    entry, path=(*path, "allOf", str(i)), root=root
                )
                for i, entry in enumerate(all_of)
            ]

    if typ == "string":
        fmt = json_schema.get("format")
        if fmt is not None and fmt not in supported_string_formats:
            del json_schema["format"]

    if "default" in json_schema and json_schema.get("default") is None:
        json_schema.pop("default")

    ref = json_schema.get("$ref")
    if ref and has_more_than_n_keys(json_schema, 1):
        assert isinstance(ref, str), f"Received non-string $ref - {ref}"

        resolved = resolve_ref(root=root, ref=ref)
        if not isinstance(resolved, dict):
            raise ValueError(
                f"Expected `$ref: {ref}` to resolve to a dictionary but got {resolved}"
            )

        json_schema.update({**resolved, **json_schema})
        json_schema.pop("$ref")
        return ensure_strict_json_schema(json_schema, path=path, root=root)

    return json_schema


def ensure_array_schemas_have_items(schema: dict) -> dict[str, Any]:
    """Recursively ensure every JSON schema node with type array has an items key."""
    result = deepcopy(schema)

    def _is_array_schema_type(type_value: Any) -> bool:
        if type_value == "array":
            return True
        if isinstance(type_value, list):
            return "array" in type_value
        return False

    def _ensure(node: Any) -> Any:
        if isinstance(node, dict):
            if _is_array_schema_type(node.get("type")) and "items" not in node:
                node["items"] = {"type": "string"}
            for key, value in list(node.items()):
                node[key] = _ensure(value)
        elif isinstance(node, list):
            for idx, value in enumerate(node):
                node[idx] = _ensure(value)
        return node

    return _ensure(result)


def prepare_schema_for_json_schema_response(schema: dict) -> dict[str, Any]:
    """Strict OpenAI JSON schema + array items fixes (used with JSONSchemaResponse)."""
    prepared = deepcopy(schema)
    ensure_strict_json_schema(prepared, path=(), root=prepared)
    return ensure_array_schemas_have_items(prepared)
