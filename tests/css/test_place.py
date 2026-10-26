"""Test the place-items / place-content / place-self shorthands."""
from ..testing_utils import assert_no_logs, parse_all


def style_for(declaration):
    box = parse_all(f'''
      <style>
        div {{ {declaration} }}
      </style>
      <div></div>
    ''')
    for child in box.descendants():
        if getattr(child, 'element_tag', '') == 'div':
            return child.style
    raise AssertionError('div not found')


@assert_no_logs
def test_place_items_one_value():
    style = style_for('place-items: center')
    assert tuple(style['align_items']) == ('center',)
    assert tuple(style['justify_items']) == ('center',)


@assert_no_logs
def test_place_items_two_values():
    style = style_for('place-items: start end')
    assert tuple(style['align_items']) == ('start',)
    assert tuple(style['justify_items']) == ('end',)


@assert_no_logs
def test_place_content_one_value():
    style = style_for('place-content: center')
    assert tuple(style['align_content']) == ('center',)
    assert tuple(style['justify_content']) == ('center',)


@assert_no_logs
def test_place_content_two_values():
    style = style_for('place-content: safe center end')
    assert tuple(style['align_content']) == ('safe', 'center')
    assert tuple(style['justify_content']) == ('end',)


@assert_no_logs
def test_place_self_two_values():
    style = style_for('place-self: start end')
    assert tuple(style['align_self']) == ('start',)
    assert tuple(style['justify_self']) == ('end',)
