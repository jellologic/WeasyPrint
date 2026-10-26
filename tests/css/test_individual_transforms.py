"""Test the translate / rotate / scale properties."""
import math

from ..testing_utils import assert_no_logs, parse_all, render_pages


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
def test_translate():
    style = style_for('translate: 10px 5%')
    x, y = style['translate']
    assert (x.value, x.unit) == (10, 'px')
    assert (y.value, y.unit) == (5, '%')


@assert_no_logs
def test_rotate():
    style = style_for('rotate: 45deg')
    assert abs(style['rotate'] - math.pi / 4) < 1e-9


@assert_no_logs
def test_scale():
    style = style_for('scale: 2')
    assert tuple(style['scale']) == (2, 2)


@assert_no_logs
def test_individual_transforms_matrix():
    def determinant(extra):
        pages = render_pages(f'''
          <style>
            @page {{ size: 100px 100px }}
            div {{ width: 20px; height: 20px;
                  transform: translate(0); {extra} }}
          </style>
          <div>x</div>
        ''')
        for child in pages[0].descendants():
            if getattr(child, 'element_tag', '') == 'div':
                matrix = child.transformation_matrix
                if matrix is None:
                    return 1
                return matrix.determinant
        return None

    base = determinant('')
    scaled = determinant('scale: 2')
    assert scaled / base == 4
