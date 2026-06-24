"""Integration tests for Selectors Level 4 features via the forked cssselect2.

These confirm WeasyPrint's cascade actually applies the new selectors
(:dir(), :read-write/:read-only, the '>>' descendant combinator and
'[*|attr]' any-namespace attribute selectors). The selector matching itself
is unit-tested in cssselect2; here we check the end-to-end wiring.
"""

from ..testing_utils import FakeHTML, assert_no_logs

RED = (1, 0, 0, 1)


def _color(html, target_id):
    """Render ``html`` and return the computed ``color`` of element ``id``."""
    document = FakeHTML(string=html).render()

    def walk(box):
        element = getattr(box, 'element', None)
        if element is not None and element.get('id') == target_id:
            return tuple(box.style['color'])
        for child in getattr(box, 'children', ()) or ():
            found = walk(child)
            if found is not None:
                return found

    for page in document.pages:
        found = walk(page._page_box)
        if found is not None:
            return found


@assert_no_logs
def test_descendant_combinator():
    color = _color(
        '<style>div >> span { color: red }</style>'
        '<div><p><span id="t">x</span></p></div>', 't')
    assert color == RED


@assert_no_logs
def test_any_namespace_attribute():
    color = _color(
        '<style>[*|data-x] { color: red }</style>'
        '<p id="t" data-x="1">x</p>', 't')
    assert color == RED


@assert_no_logs
def test_dir_pseudo_class():
    color = _color(
        '<style>span:dir(rtl) { color: red }</style>'
        '<div dir="rtl"><span id="t">x</span></div>', 't')
    assert color == RED


@assert_no_logs
def test_read_write_pseudo_class():
    color = _color(
        '<style>input:read-write { color: red }</style>'
        '<form><input id="t"></form>', 't')
    assert color == RED
