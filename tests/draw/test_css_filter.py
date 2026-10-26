"""Test the CSS ``filter`` property on replaced elements."""
from PIL import Image

from weasyprint.images import apply_css_filter

from ..testing_utils import FakeHTML, assert_no_logs, resource_path


def test_filter_grayscale_math():
    image = Image.new('RGB', (2, 2), (200, 100, 50))
    filtered = apply_css_filter(image, (('grayscale', 1),)).convert('RGB')
    expected = round(0.2126 * 200 + 0.7152 * 100 + 0.0722 * 50)
    assert set(filtered.getdata()) == {(expected, expected, expected)}


def test_filter_invert_math():
    image = Image.new('RGB', (2, 2), (200, 100, 50))
    filtered = apply_css_filter(image, (('invert', 1),)).convert('RGB')
    assert set(filtered.getdata()) == {(55, 155, 205)}


def test_filter_brightness_math():
    image = Image.new('RGB', (2, 2), (200, 100, 50))
    filtered = apply_css_filter(image, (('brightness', 0.5),)).convert('RGB')
    assert set(filtered.getdata()) == {(100, 50, 25)}


def test_filter_opacity_math():
    image = Image.new('RGBA', (2, 2), (200, 100, 50, 255))
    filtered = apply_css_filter(image, (('opacity', 0.5),))
    assert set(filtered.getchannel('A').getdata()) == {128}


def test_filter_pixels_unchanged_without_filter():
    image = Image.new('RGB', (2, 2), (200, 100, 50))
    assert list(
        apply_css_filter(image, ()).convert('RGB').getdata()) == list(
        image.getdata())


@assert_no_logs
def test_filter_validation():
    document = FakeHTML(
        string='''
      <style>
        img { filter: grayscale(1) invert(.5) }
        #b { filter: none }
      </style>
      <img src="pattern.png" id="a">
      <img src="pattern.png" id="b">
    ''',
        base_url=resource_path('pattern.png')).render()
    from weasyprint.formatting_structure import boxes
    styles = [
        box.style['filter'] for box in document.pages[0]._page_box.descendants()
        if isinstance(box, boxes.ReplacedBox)]
    assert [tuple(pair) for pair in styles[0]] == [
        ('grayscale', 1), ('invert', 0.5)]
    assert styles[1] == 'none'


@assert_no_logs
def test_filter_renders_differently(assert_different_renderings):
    # The same document with and without a filter renders differently.
    src = resource_path('pattern.png')
    html = f'''
      <style>
        @page {{ size: 8px }}
        body {{ margin: 2px 0 0 2px; font-size: 0 }}
        img {{ filter: invert(1) }}
      </style>
      <div><img src="{src}"></div>
    '''
    html_no_filter = html.replace(' filter: invert(1)', '')
    assert_different_renderings(
        html, html_no_filter)
