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
from collections.abc import Sized, Iterator, Iterable, Callable
from typing import TypeVar, Generic, Optional
from itertools import tee

def gray_product(*iterables):
    """Like :func:`itertools.product`, but return tuples in an order such that only one
    element in the generated tuple changes from one iteration to the next.

        >>> list(gray_product('AB','CD'))
        [('A', 'C'), ('B', 'C'), ('B', 'D'), ('A', 'D')]

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

_T = TypeVar('_T', covariant=True)
class SizedCallbackIterator(Generic[_T], Sized, Iterator[_T]):
    """Wrapper to add ``len`` support to an iterator.

    For example, this can be used to wrap a generator which has a known output length
    (e.g. if it returns exactly one item per input item), so that it can then
    be used in libraries like ``tqdm``."""
    def __init__(self, it :Iterable[_T], length :int, *, strict :bool=False, callback :Optional[Callable[[int, _T], None]]=None):
        if length<0: raise ValueError("length must be >= 0")
        self.it = iter(it)
        self.length = length
        self._count = 0
        self.strict = strict
        self.callback = callback
    def __len__(self) -> int: return self.length
    def __iter__(self) -> Iterator[_T]: return self
    def __next__(self) -> _T:
        try:
            val :_T = next(self.it)
        except StopIteration as ex:
            if self.strict and self._count != self.length:
                raise ValueError(f"expected iterator to return {self.length} items, but it returned {self._count}") from ex
            raise ex
        else:
            if self.callback:
                self.callback(self._count, val)
            self._count += 1
            return val

def is_unique_everseen(iterable, *, key=None):
    """For each element in the input iterable, return either ``True`` if this
    element is unique, or ``False`` if it is not.

    The implementation is very similar :func:`more_itertools.unique_everseen`
    and is subject to the same performance considerations.
    """
    seen_set = set()
    seen_list = []
    use_key = key is not None
    for element in iterable:
        k = key(element) if use_key else element
        try:
            if k not in seen_set:
                seen_set.add(k)
                yield True
            else:
                yield False
        except TypeError:
            if k not in seen_list:
                seen_list.append(k)
                yield True
            else:
                yield False

def no_duplicates(iterable, *, key=None, name="item"):
    """Raise a ``ValueError`` if there are any duplicate elements in the
    input iterable.

    Remember that if you don't want to use this iterator's return values,
    but only use it for checking a list, you need to force it to execute
    by wrapping the call e.g. in a ``set()`` or ``list()``.
    Alternatively, use ``not all(is_unique_everseen(iterable))``.

    The ``name`` argument is only to customize the error messages.

    :func:`more_itertools.duplicates_everseen` could also be used for this purpose,
    but this function returns the values of the input iterable.

    The implementation is very similar :func:`more_itertools.unique_everseen`
    and is subject to the same performance considerations.
    """
    it1, it2 = tee(iterable)
    for element, unique in zip(it1, is_unique_everseen(it2, key=key), strict=True):
        if not unique: raise ValueError(f"duplicate {name}: {element!r}")
        else: yield element
