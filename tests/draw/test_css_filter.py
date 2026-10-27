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


@assert_no_logs
def test_filter_every_source_format(tmp_path):
    # The filter applies whatever the source format: an RGB PNG used to
    # print black (the RGBA result written with the original RGB mode)
    # and a JPEG disappeared (the PNG result declared as DCTDecode).
    import base64
    import io

    images = {}
    for name, mode, format_ in (
            ('rgba', 'RGBA', 'PNG'), ('rgb', 'RGB', 'PNG'),
            ('jpeg', 'RGB', 'JPEG')):
        image_file = io.BytesIO()
        Image.new(mode, (40, 20), (200, 16, 46)).save(
            image_file, format=format_)
        images[name] = base64.b64encode(image_file.getvalue()).decode()

    for name, data in images.items():
        target = tmp_path / f'{name}.png'
        FakeHTML(string=f'''
          <style>@page {{ size: 1in 0.5in; margin: 0; background: #fff }}</style>
          <img src="data:image/png;base64,{data}"
               style="width: 1in; filter: grayscale(1)">
        ''').write_png(str(target))
        pixel = Image.open(target).convert('RGB')
        expected = round(0.2126 * 200 + 0.7152 * 16 + 0.0722 * 46)
        assert pixel.getpixel((50, 20)) == (expected,) * 3, name
