#!/usr/bin/env python3
"""Tests for jsonvalidate.

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
import unittest
import pkgutil
import io
from pathlib import Path
import json
from types import MappingProxyType
from jsonvalidate import load_json_schema, validate_json, freeze_json, FrozenEncoder

class TestJsonValidate(unittest.TestCase):

    def test_freeze_json(self):
        j = '''{"hello":"world","foo":[1,2.3,true,false,null]}'''
        d = json.loads(j)
        self.assertEqual( d, {"hello":"world","foo":[1,2.3,True,False,None]} )
        f = freeze_json(d)
        self.assertEqual( f, MappingProxyType({"hello":"world","foo":(1,2.3,True,False,None)}) )
        self.assertEqual( json.dumps(f, cls=FrozenEncoder, separators=(',',':')), j )
        with self.assertRaises(TypeError): freeze_json(f)
        with self.assertRaises(TypeError): json.dumps(io.StringIO("x"), cls=FrozenEncoder)

    def test_load_validate_json_schema(self):
        schema = load_json_schema( pkgutil.get_data('tests', 'test.schema.json') )
        self.assertEqual( validate_json(schema, io.BytesIO(
            b'{"foo":{"Hello":"World"},"bar":[1,2,3]}')),
              {"foo":{"Hello":"World"},"bar":[1,2,3]} )
        self.assertIsNone( validate_json(schema, b'{"foo":{"Hello":"World"},"bar":[1,2,1]}') )
        self.assertIsNone( validate_json(schema, b'{"foo":{"0Hello":"World"},"bar":[1,2,3]}') )
        # also test loading with filename
        self.assertEqual( schema, load_json_schema( Path(__file__).parent/'test.schema.json' ) )
        # errors
        with self.assertRaises(TypeError): load_json_schema( 123 )
        with self.assertRaises(RuntimeError):
            load_json_schema( io.BytesIO(b'{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"foobar"}') )

if __name__ == '__main__':  # pragma: no cover
    unittest.main()
