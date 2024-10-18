IGB Data Tools
==============

This is a collection of various data processing tools, libraries, and
utilities. Please see the individual files for details.

Requirements: Python 3.11 and the requirements listed in `requirements.txt`.

You can place this directory in your `PYTHONPATH` environment variable,
see the file `notes/Notes.md` for details.

Attention
---------

This repository has evolved into more of an incubator.
For example, `loggerdata.toa5` was released as <https://pypi.org/project/PyTOA5/>
and the former is therefore **deprecated** and will eventually be removed.
While the code here is still tested and works, I plan on splitting more of
those parts that have proven useful out into their own libraries / tools,
and I may not continue development in this repository.

TODOs
-----

- Check and generate documentation with Sphinx
  - Many places that use double-backtick strings could use roles (`:func:` etc.) instead.
  - See <https://www.sphinx-doc.org/en/master/usage/restructuredtext/domains.html#info-field-lists>
- Apply `mypy` more


Author, Copyright, and License
------------------------------

Copyright (c) 2022 Hauke Daempfling <haukex@zero-g.net>
at the Leibniz Institute of Freshwater Ecology and Inland Fisheries (IGB),
Berlin, Germany, <https://www.igb-berlin.de/>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
