"""Functions to help clean & normalize business names.

See http://www.unicode.org/reports/tr15/#Normalization_Forms_Table for details
on Unicode normalization and the NFKD normalization used here.

Basic usage:

>> terms = get_terms()
>> clean_name("Daddy & Sons, Ltd.", terms)
Daddy & Sons

"""

import functools
import operator
from collections import OrderedDict
import re
import unicodedata
from .termdata import terms_by_type, terms_by_country


tail_removal_rexp = re.compile(r"[^\.\w]+$", flags=re.UNICODE)


def get_terms():
    ts = functools.reduce(operator.iconcat, terms_by_type.values(), [])
    cs = functools.reduce(operator.iconcat, terms_by_country.values(), [])
    return set(ts + cs)

def normalize_terms(terms):
    "retrieve all unique terms from termdata definitions"
    return (unicodedata.normalize("NFKD", t.casefold()) for t in terms)

def deconstruct_terms(terms):
    "get terms split by whitespace & sorted by # of parts"
    return set(tuple(t.split()) for t in terms)

def sizesort_deconstructed_terms(dterms):
    return sorted(dterms, key=len, reverse=True)

def strip_tail(name):
    "Get rid of all trailing non-letter symbols except the dot"
    match = re.search(tail_removal_rexp, name)
    if match is not None:
        name = name[: match.span()[0]]
    return name


def splices(s, size):
    "return a list of all in-order string part splices of given size"
    sp = s.split()
    spc = len(sp)
    return [sp[i:i+size] for i in range(0, spc-size+1)]


def normalized(text):
    "caseless Unicode normalization"
    return unicodedata.normalize("NFKD", text.casefold())


def find_suffix(name, spterms):
    "check if last part of name matches any single-part term"
    idx = spterms.find(name[-1])
    if idx != -1:
        return spterms[idx]

def find_prefix(name, spterms):
    "check if first part of name matches any simgle-part term"
    idx = spterms.find(name[0])
    if idx != -1:
        return spterms[idx]

def find_inside(name, terms):
    "give sorted terms, longest first"

    for term in terms:
        try:
            idx = name.index(term)
        except ValueError:
            pass
        else:
            return idx, term

"""

Optimized term checking sequence:

1.a check for multipart term prefixes and suffixes
1.b check for single-part prefixes, suffixes and terms in side name
2. check for multipart -part

Check for multipart prefiterms first (ones that have a whitespace or more in them)


2. First check multipart prefixes and suffixes.
"""



def basename_partcmp(name, terms, suffix=True, prefix=False, middle=False):
    "input: list of deconstructed terms"

    # normalize name
    name = normalized(strip_tail(name))

    # deconstruct it
    nparts = name.split()

    # get multi-part & single-part terms
    mpterms, spterms = terms
    #mpterms = set(t for t in terms if len(t) > 1)
    #spterms = tuple(t[0] for t in terms.difference(mpterms))

    # check multipart prefixes & suffixes
    if prefix and nparts:
        for mpterms in terms:
            pass

    if prefix:
        term = find_prefix(name, mpterms)

    if suffix:
        term = find_suffix(name, mpterms)

    if middle:
        term = find_inside(name, mpterms)

    # return name without suffixed/prefixed/middle type term(s)
    for term, nterm in ((t, normalized(t)) for t in terms):
        pass


def suffixes(n, terms):

    def find_suffix(n, terms):
        for t in terms:
            if n.endswith(t):
                return True
        return False

    suffixes = []
    found = find_suffix(n, terms)
    while found:
        suffixes.append(found)
        found = find_suffix(n, terms)
    return suffixes


def remove_prefixes(n, nn, terms):

    def removed(n, terms):
        for t in terms:
            if n.startswith(t):
                return n[len(t):]
        return False

    result = removed(n, terms)
    while result:
        result = removed(n, terms)
    return result



def basename_listcmp(name, terms, suffix=True, prefix=False, middle=False):
    "return cleaned base version of the business name"

    name = strip_tail(name)
    nparts = name.split()
    nname = normalized(name)
    nnparts = nname.split()
    nnsize = len(nnparts)

    if suffix:
        for termsize, termparts in terms:
            if nnparts[-termsize:] == termparts:
                del nnparts[-termsize:]
                del nparts[-termsize:]

    if prefix:
        for termsize, termparts in terms:
            if nnparts[:termsize] == termparts:
                del nnparts[:termsize]
                del nparts[:termsize]

    if middle:
        sizediff = nnsize - termsize
        if sizediff > 1:
            for i in range(1, sizediff):
                if nnparts[i:nnsize] == ntermparts:
                    del nnparts[i:nnsize]
                    del nparts[i:nnsize]

    return strip_tail(" ".join(nparts))



def basename(*args, **kwargs):
    return basename_strcmp(*args, **kwargs)
