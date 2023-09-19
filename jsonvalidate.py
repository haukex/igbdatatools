#!/usr/bin/env python3
"""Utility functions to load and validate JSON Schemas.

Author, Copyright, and License
------------------------------
Copyright (c) 2023 Hauke Daempfling (haukex@zero-g.net)
at the Leibniz Institute of Freshwater Ecology and Inland Fisheries (IGB),
Berlin, Germany, https://www.igb-berlin.de/

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see https://www.gnu.org/licenses/
"""
import io
import json
import typing
from warnings import catch_warnings, simplefilter
from igbpyutils.file import Filename
from types import MappingProxyType, NoneType
from pprint import pprint
import jschon
from functools import singledispatch

class FrozenEncoder(json.JSONEncoder):
    """A JSON encoder that handles ``MappingProxyType``s like those returned from ``freeze_json``."""
    def default(self, obj):
        if isinstance(obj, MappingProxyType):
            return dict(**obj)
        return super().default(obj)

@singledispatch
def freeze_json(obj):
    """Utility function that "freezes" a JSON data structure into immutable types."""
    raise TypeError(f"I don't handle {type(obj)}")
@freeze_json.register
def _(obj :str|int|float|bytes|bool|NoneType): return obj
@freeze_json.register
def _(obj :tuple|list): return tuple( freeze_json(o) for o in obj )
@freeze_json.register
def _(obj :dict): return MappingProxyType( { k: freeze_json(v) for k, v in obj.items() } )

@singledispatch
def load_json(file :Filename|io.IOBase|typing.IO|bytes|bytearray):
    """Utility function to load JSON either from a filename, file object, or ``bytes`` object."""
    raise TypeError(f"file must be a filename, file object, or bytes, not {repr(file)}")
@load_json.register
def _(file :Filename):
    with open(file, 'rb') as fh: return json.load(fh)
@load_json.register
def _(file :io.IOBase|typing.IO):
    return json.load(file)
@load_json.register
def _(file :bytes|bytearray):
    return json.load(io.BytesIO(file))

with catch_warnings(category=EncodingWarning):
    simplefilter('ignore', category=EncodingWarning)
    _catalog = jschon.create_catalog('2020-12')
def load_json_schema(file, *, verbose=False) -> jschon.JSONSchema:
    """Loads a JSON Schema and checks that the schema itself is valid, and raises an error if not.

    ``file`` can be either a filename, file object, or ``bytes``.
    Turning on ``verbose`` outputs status messages to STDOUT."""
    schema = jschon.JSONSchema(load_json(file), catalog=_catalog)
    result = schema.validate()
    if result.valid:
        if verbose:  # pragma: no cover
            print(f"Schema {file!r} itself is valid")
    else:
        if verbose:  # pragma: no cover
            pprint(result.output('basic'))
        raise RuntimeError(f"Schema {file!r} is invalid")
    return schema

def validate_json(schema :jschon.JSONSchema, file, *, verbose=False):
    """Validates a JSON file against a schema loaded with :func:`load_json_schema`.

    If the validation fails, returns ``None``, otherwise returns the data structure returned by ``json.load``.

    ``file`` can be either a filename, file object, or ``bytes``.
    Turning on ``verbose`` outputs status messages to STDOUT."""
    thejson = load_json(file)
    result = schema.evaluate(jschon.JSON(thejson))
    if result.valid:
        if verbose:  # pragma: no cover
            print(f"The JSON {file!r} validates against the schema")
        return thejson
    else:
        if verbose:  # pragma: no cover
            print(f"The JSON {file!r} failed to validate!")
            pprint(result.output('basic'))  # can also use "detailed" here
        return None

if __name__ == '__main__':  # pragma: no cover
    import sys
    import argparse
    parser = argparse.ArgumentParser(description='JSON Validator')
    parser.add_argument('-q', '--quiet', help="be quiet", action="store_true")
    parser.add_argument('schema', help="the JSON Schema")
    parser.add_argument('jsons', help="the JSON files to validate", nargs="+")
    args = parser.parse_args()
    schema_ = load_json_schema(args.schema, verbose = not args.quiet)
    allok = True
    for j in args.jsons:
        if validate_json(schema_, j, verbose = not args.quiet) is None:
            allok = False
    sys.exit(0 if allok else 1)
