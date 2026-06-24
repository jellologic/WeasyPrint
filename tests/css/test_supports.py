"""Test the CSS @supports at-rule."""

import pytest

from ..testing_utils import assert_no_logs, render_pages


def _div_width(style):
    page, = render_pages('''
      <style>
        div { width: 50px }
        %s
      </style>
      <div>abc</div>
    ''' % style)
    html, = page.children
    body, = html.children
    div, = body.children
    return div.width


@assert_no_logs
@pytest.mark.parametrize('style', [
    # Supported declaration applies.
    '@supports (color: red) { div { width: 100px } }',
    # Whitespace variations.
    '@supports(color:red){ div { width: 100px } }',
    # not on an unsupported declaration applies.
    '@supports not (foo: bar) { div { width: 100px } }',
    # and where both branches are supported.
    '@supports (color: red) and (display: block) { div { width: 100px } }',
    # or where one branch is supported.
    '@supports (foo: bar) or (color: red) { div { width: 100px } }',
    '@supports (color: red) or (foo: bar) { div { width: 100px } }',
    # selector() with a compilable selector.
    '@supports selector(a > b) { div { width: 100px } }',
    # Nested parenthesized condition.
    '@supports ((foo: bar) or (color: red)) and (display: block)'
    ' { div { width: 100px } }',
])
def test_supports_applies(style):
    assert _div_width(style) == 100


@assert_no_logs
@pytest.mark.parametrize('style', [
    # Unknown property is unsupported.
    '@supports (foo: bar) { div { width: 100px } }',
    # Known property with invalid value is unsupported.
    '@supports (color: notacolor) { div { width: 100px } }',
    # not on a supported declaration skips.
    '@supports not (color: red) { div { width: 100px } }',
    # and where one branch is unsupported.
    '@supports (color: red) and (foo: bar) { div { width: 100px } }',
    # or where both branches are unsupported.
    '@supports (foo: bar) or (baz: qux) { div { width: 100px } }',
    # Unknown function condition is unsupported.
    '@supports font-tech(color-COLRv1) { div { width: 100px } }',
    # selector() with an invalid selector is unsupported.
    '@supports selector(a >>> b) { div { width: 100px } }',
])
def test_supports_skips(style):
    assert _div_width(style) == 50
