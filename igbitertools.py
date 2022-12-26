#!python3
"""A few useful iterators.

Author, Copyright, and License
------------------------------
Copyright (c) 2022 Hauke Daempfling (haukex@zero-g.net)
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

def gray_product(*iterables):
    """Like :func:`itertools.product`, but return tuples in an order such that only one
    element in the generated tuple changes from one iteration to the next.

        >>> list(gray_product('AB','CD'))
        [('A', 'C'), ('B', 'C'), ('B', 'D'), ('A', 'D')]

    Note that it is also true that only one element changes from the last to the first item of
    the sequence, so it can be looped.

    This is known under several names: "n-ary", "non-Boolean", "non-binary", or "mixed-radix" Gray code.

    All input iterables are consumed by this function before the first output item can be generated.
    Each iterable must have at least two items, or a ``ValueError`` is raised.

    Reference: Knuth's "The Art of Computer Programming", Pre-Fascicle 2A,
    "A Draft of Section 7.2.1.1: Generating all n-Tuples", Page 20,
    Algorithm H, available at
    https://www-cs-faculty.stanford.edu/~knuth/fasc2a.ps.gz
    """
    m = tuple(tuple(x) for x in iterables)
    for x in m:
        if len(x) < 2:
            raise ValueError("each iterable must have two or more items")
    a = [0] * len(m)
    f = list(range(len(m) + 1))
    o = [1] * len(m)
    while True:
        yield tuple(m[i][a[i]] for i in range(len(m)))
        j = f[0]
        f[0] = 0
        if j == len(m):
            break
        a[j] = a[j] + o[j]
        if a[j] == 0 or a[j] == len(m[j])-1:
            o[j] = -o[j]
            f[j] = f[j+1]
            f[j+1] = j+1

def no_duplicates(iterable, *, key=None, name="item"):
    """Raise a ``ValueError`` if there are any duplicate elements in the
    input iterable.

    Remember that if you don't want to use this iterator's return values,
    but only use it for checking a list, you need to force it to execute
    by wrapping the call e.g. in a ``set()`` or ``list()``.

    The ``name`` argument is only to customize the error messages.

    :func:`more_itertools.duplicates_everseen` could also be used for this purpose,
    but this function returns the values of the input iterable.
    The implementation is very similar to :func:`more_itertools.unique_everseen`.
    """
    seenset = set()
    seenlist = []
    use_key = key is not None
    for element in iterable:
        k = key(element) if use_key else element
        try:
            if k in seenset:
                raise ValueError(f"duplicate {name}: {element!r}")
            seenset.add(k)
            yield element
        except TypeError:
            if k in seenlist:
                raise ValueError(f"duplicate {name}: {element!r}")
            seenlist.append(k)
            yield element
