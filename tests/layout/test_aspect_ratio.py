"""Test the ``aspect-ratio`` property on block-level boxes."""
from ..testing_utils import assert_no_logs, render_pages


def find_div(page):
    return next(
        box for box in page.descendants()
        if getattr(box, 'element_tag', '') == 'div')


@assert_no_logs
def test_aspect_ratio_height_from_width():
    # width: 200px, height auto, ratio 2/1 -> height 100px
    page, = render_pages('''
      <style>
        @page { size: 400px 400px; margin: 0 }
        div { width: 200px; aspect-ratio: 2 / 1 }
      </style>
      <div></div>
    ''')
    div = find_div(page)
    assert abs(div.width - 200) < 0.01
    assert abs(div.height - 100) < 0.01


@assert_no_logs
def test_aspect_ratio_width_from_height():
    # height: 100px, width auto, ratio 2/1 -> width 200px
    page, = render_pages('''
      <style>
        @page { size: 400px 400px; margin: 0 }
        div { height: 100px; aspect-ratio: 2 / 1 }
      </style>
      <div></div>
    ''')
    div = find_div(page)
    assert abs(div.width - 200) < 0.01
    assert abs(div.height - 100) < 0.01


@assert_no_logs
def test_aspect_ratio_single_number():
    # ratio 0.5 with width 100px -> height 200px
    page, = render_pages('''
      <style>
        @page { size: 400px 400px; margin: 0 }
        div { width: 100px; aspect-ratio: 0.5 }
      </style>
      <div></div>
    ''')
    div = find_div(page)
    assert abs(div.width - 100) < 0.01
    assert abs(div.height - 200) < 0.01


@assert_no_logs
def test_aspect_ratio_replaced_height():
    # aspect-ratio overrides the intrinsic ratio: a 4x4 image with
    # width 40px and ratio 2/1 gets height 20px.
    from ..testing_utils import resource_path
    src = resource_path('pattern.png')
    page, = render_pages(f'''
      <style>
        @page {{ size: 200px 200px; margin: 0 }}
        img {{ display: block; width: 40px; aspect-ratio: 2 / 1 }}
      </style>
      <img src="{src}">
    ''')
    img = next(
        box for box in page.descendants()
        if getattr(box, 'element_tag', '') == 'img')
    assert abs(img.width - 40) < 0.01
    assert abs(img.height - 20) < 0.01
