"""Test PDF-related code, including metadata, bookmarks and hyperlinks."""

import hashlib
import io
import re
from codecs import BOM_UTF16_BE

import pytest

from weasyprint import Attachment
from weasyprint.document import Document, DocumentMetadata
from weasyprint.text.fonts import FontConfiguration
from weasyprint.urls import path2url

from .testing_utils import FakeHTML, assert_no_logs, capture_logs, resource_path

# Top and right positions in points, rounded to the default float precision of
# 6 digits, a rendered by pydyf
TOP = round(297 * 72 / 25.4, 6)
RIGHT = round(210 * 72 / 25.4, 6)


@assert_no_logs
@pytest.mark.parametrize('zoom', [1, 1.5, 0.5])
def test_page_size_zoom(zoom):
    pdf = FakeHTML(string='<style>@page{size:3in 4in').write_pdf(zoom=zoom)
    width, height = int(216 * zoom), int(288 * zoom)
    assert f'/MediaBox [0 0 {width} {height}]'.encode() in pdf


@assert_no_logs
@pytest.mark.parametrize(('css_mode', 'pdf_mode'), [
    ('multiply', 'Multiply'),
    ('screen', 'Screen'),
    ('color-dodge', 'ColorDodge'),
    ('hard-light', 'HardLight'),
    ('luminosity', 'Luminosity'),
])
def test_mix_blend_mode(css_mode, pdf_mode):
    pdf = FakeHTML(string=(
        f'<div style="mix-blend-mode: {css_mode}">a</div>'
    )).write_pdf(uncompressed_pdf=True)
    assert f'/BM /{pdf_mode}'.encode() in pdf


@assert_no_logs
def test_mix_blend_mode_normal():
    # The default value must not emit any blend mode ExtGState.
    pdf = FakeHTML(string=(
        '<div style="mix-blend-mode: normal">a</div>'
    )).write_pdf(uncompressed_pdf=True)
    assert b'/BM /' not in pdf


@assert_no_logs
def test_background_blend_mode():
    # Two background layers with a blend mode each: the first (topmost) layer
    # uses multiply, the second uses screen. Both /BM operators must be emitted.
    pdf = FakeHTML(string=(
        '<div style="width: 50px; height: 50px;'
        ' background-image: linear-gradient(red, blue),'
        ' linear-gradient(green, yellow);'
        ' background-blend-mode: multiply, screen">a</div>'
    )).write_pdf(uncompressed_pdf=True)
    assert b'/BM /Multiply' in pdf
    assert b'/BM /Screen' in pdf


@assert_no_logs
@pytest.mark.parametrize('prefix', ['', 'repeating-'])
def test_conic_gradient_background(prefix):
    # A conic gradient has no native PDF shading, so it is rasterized and
    # embedded as an image XObject for that box.
    gradient = (
        f'{prefix}conic-gradient(from 45deg at 30% 70%,'
        ' red 0deg, blue 180deg, red 360deg)')
    pdf = FakeHTML(string=(
        '<div style="width: 50px; height: 50px;'
        f' background-image: {gradient}">a</div>'
    )).write_pdf(uncompressed_pdf=True)
    # An image XObject must be emitted for the conic gradient.
    assert b'/Subtype /Image' in pdf
    assert b'/XObject' in pdf

    # The output must differ from a solid background of the same size.
    solid = FakeHTML(string=(
        '<div style="width: 50px; height: 50px;'
        ' background-image: none; background-color: red">a</div>'
    )).write_pdf(uncompressed_pdf=True)
    assert b'/Subtype /Image' not in solid
    assert pdf != solid


@assert_no_logs
def test_conic_gradient_not_used_byte_identical():
    # A document that does not use conic-gradient must be unaffected.
    source = '<div style="width: 50px; height: 50px; background: red">a</div>'
    first = FakeHTML(string=source).write_pdf()
    second = FakeHTML(string=source).write_pdf()
    assert first == second
    assert b'/Subtype /Image' not in first


@assert_no_logs
def test_background_blend_mode_normal():
    # The default value must not emit any blend mode ExtGState.
    pdf = FakeHTML(string=(
        '<div style="width: 50px; height: 50px;'
        ' background-image: linear-gradient(red, blue);'
        ' background-blend-mode: normal">a</div>'
    )).write_pdf(uncompressed_pdf=True)
    assert b'/BM /' not in pdf


@assert_no_logs
def test_box_shadow_sharp():
    # A sharp (blur 0) red drop shadow offset by 3px must emit a red rectangle
    # offset from the box (at margin 8px) behind it.
    pdf = FakeHTML(string=(
        '<div style="width: 50px; height: 50px; background: white; '
        'box-shadow: 3px 3px 0 red"></div>'
    )).write_pdf(uncompressed_pdf=True)
    assert b'1 0 0 rg' in pdf  # Red fill colour.
    # The red shadow rectangle is offset by 3px from the box border box
    # (which sits at the page origin with FakeHTML's zero margins).
    assert b'3 3 50 50 re' in pdf


@assert_no_logs
def test_box_shadow_spread():
    # A spread-only shadow grows the box by the spread radius on each side.
    pdf = FakeHTML(string=(
        '<div style="width: 50px; height: 50px; '
        'box-shadow: 0 0 0 5px lime"></div>'
    )).write_pdf(uncompressed_pdf=True)
    # Box border box at 0 0 50 50, grown by 5px each side -> -5 -5 60 60.
    assert b'-5 -5 60 60 re' in pdf


@assert_no_logs
def test_box_shadow_inset():
    # An inset shadow is clipped inside the padding box and filled with the
    # even-odd rule.
    pdf = FakeHTML(string=(
        '<div style="width: 50px; height: 50px; background: white; '
        'box-shadow: inset 4px 4px 0 black"></div>'
    )).write_pdf(uncompressed_pdf=True)
    assert b'0 0 0 rg' in pdf  # Black fill colour.
    assert b'f*' in pdf  # Even-odd fill used for the inset ring.


@assert_no_logs
def test_box_shadow_none():
    # The default value must not emit any extra fill operators.
    pdf = FakeHTML(string=(
        '<div style="width: 50px; height: 50px; background: white"></div>'
    )).write_pdf(uncompressed_pdf=True)
    # Canvas + the div white background fill, but no shadow fills.
    assert pdf.count(b' rg') == 2


@assert_no_logs
def test_text_shadow_sharp():
    # A sharp (blur 0) red text shadow must draw the glyphs twice: once in the
    # red shadow colour (behind) and once in the black text colour (on top),
    # producing two text-showing blocks.
    pdf = FakeHTML(string=(
        '<p style="color: black; font-size: 20px; '
        'text-shadow: 2px 2px 0 red">Hi</p>'
    )).write_pdf(uncompressed_pdf=True)
    assert b'1 0 0 rg' in pdf  # Red shadow fill colour.
    assert b'0 0 0 rg' in pdf  # Black text fill colour.
    assert pdf.count(b'BT') == 2  # Shadow text block + main text block.


@assert_no_logs
def test_text_shadow_none():
    # The default value must not draw the text twice nor emit a red fill.
    pdf = FakeHTML(string=(
        '<p style="color: black; font-size: 20px">Hi</p>'
    )).write_pdf(uncompressed_pdf=True)
    assert b'1 0 0 rg' not in pdf
    assert pdf.count(b'BT') == 1  # Only the main text block.


@assert_no_logs
def test_bookmarks_1():
    pdf = FakeHTML(string='''
      <h1>a</h1>  #
      <h4>b</h4>  ####
      <h3>c</h3>  ###
      <h2>d</h2>  ##
      <h1>e</h1>  #
    ''').write_pdf()
    # a
    # |_ b
    # |_ c
    # L_ d
    # e
    assert re.findall(b'/Count ([0-9-]*)', pdf)[-1] == b'5'
    assert re.findall(b'/Title \\((.*)\\)', pdf) == [
        b'a', b'b', b'c', b'd', b'e']


@assert_no_logs
def test_bookmarks_2():
    pdf = FakeHTML(string='<body>').write_pdf()
    assert b'Outlines' not in pdf


@assert_no_logs
def test_bookmarks_3():
    pdf = FakeHTML(string='<h1>a nbsp…</h1>').write_pdf()
    assert re.findall(b'/Title <(\\w*)>', pdf) == [
        b'feff006100a0006e0062007300702026']


@assert_no_logs
def test_bookmarks_4():
    pdf = FakeHTML(string='''
      <style>
        h1, h2, h3, span { height: 90pt; margin: 0 0 10pt 0 }
      </style>
      <h1>1</h1>
      <h1>2</h1>
      <h2 style="position: relative; left: 20pt">3</h2>
      <h2>4</h2>
      <h3>5</h3>
      <span style="display: block; page-break-before: always"></span>
      <h2>6</h2>
      <h1>7</h1>
      <h2>8</h2>
      <h3>9</h3>
      <h1>10</h1>
      <h2>11</h2>
    ''').write_pdf()
    # 1
    # 2
    # |_ 3
    # |_ 4
    # |  L_ 5
    # L_ 6
    # 7
    # L_ 8
    #    L_ 9
    # 10
    # L_ 11
    assert re.findall(b'/Title \\((.*)\\)', pdf) == [
        str(i).encode() for i in range(1, 12)]
    counts = re.findall(b'/Count ([0-9-]*)', pdf)
    counts.pop(0)  # Page count
    outlines = counts.pop()
    assert outlines == b'11'
    assert counts == [
        b'0', b'4', b'0', b'1', b'0', b'0', b'2', b'1', b'0', b'1', b'0']


@assert_no_logs
def test_bookmarks_5():
    pdf = FakeHTML(string='''
      <h2>1</h2> level 1
      <h4>2</h4> level 2
      <h2>3</h2> level 1
      <h3>4</h3> level 2
      <h4>5</h4> level 3
    ''').write_pdf()
    # 1
    # L_ 2
    # 3
    # L_ 4
    #    L_ 5
    assert re.findall(b'/Title \\((.*)\\)', pdf) == [
        str(i).encode() for i in range(1, 6)]
    counts = re.findall(b'/Count ([0-9-]*)', pdf)
    counts.pop(0)  # Page count
    outlines = counts.pop()
    assert outlines == b'5'
    assert counts == [b'1', b'0', b'2', b'1', b'0']


@assert_no_logs
def test_bookmarks_6():
    pdf = FakeHTML(string='''
      <h2>1</h2> h2 level 1
      <h4>2</h4> h4 level 2
      <h3>3</h3> h3 level 2
      <h5>4</h5> h5 level 3
      <h1>5</h1> h1 level 1
      <h2>6</h2> h2 level 2
      <h2>7</h2> h2 level 2
      <h4>8</h4> h4 level 3
      <h1>9</h1> h1 level 1
    ''').write_pdf()
    # 1
    # |_ 2
    # L_ 3
    #    L_ 4
    # 5
    # |_ 6
    # L_ 7
    #    L_ 8
    # 9
    assert re.findall(b'/Title \\((.*)\\)', pdf) == [
        str(i).encode() for i in range(1, 10)]
    counts = re.findall(b'/Count ([0-9-]*)', pdf)
    counts.pop(0)  # Page count
    outlines = counts.pop()
    assert outlines == b'9'
    assert counts == [b'3', b'0', b'1', b'0', b'3', b'0', b'1', b'0', b'0']


@assert_no_logs
def test_bookmarks_7():
    # Reference for the next test. zoom=1
    pdf = FakeHTML(string='<h2>a</h2>').write_pdf()

    assert re.findall(b'/Title \\((.*)\\)', pdf) == [b'a']
    dest, = re.findall(b'/Dest \\[(.*)\\]', pdf)
    y = round(float(dest.strip().split()[-2]))

    pdf = FakeHTML(string='<h2>a</h2>').write_pdf(zoom=1.5)
    assert re.findall(b'/Title \\((.*)\\)', pdf) == [b'a']
    dest, = re.findall(b'/Dest \\[(.*)\\]', pdf)
    assert round(float(dest.strip().split()[-2])) == 1.5 * y


@assert_no_logs
def test_bookmarks_8():
    pdf = FakeHTML(string='''
      <h1>a</h1>
      <h2>b</h2>
      <h3>c</h3>
      <h2 style="bookmark-state: closed">d</h2>
      <h3>e</h3>
      <h4>f</h4>
      <h1>g</h1>
    ''').write_pdf()
    # a
    # |_ b
    # |  |_ c
    # |_ d (closed)
    # |  |_ e
    # |     |_ f
    # g
    assert re.findall(b'/Title \\((.*)\\)', pdf) == [
        b'a', b'b', b'c', b'd', b'e', b'f', b'g']
    counts = re.findall(b'/Count ([0-9-]*)', pdf)
    counts.pop(0)  # Page count
    outlines = counts.pop()
    assert outlines == b'5'
    assert counts == [b'3', b'1', b'0', b'-2', b'1', b'0', b'0']


@assert_no_logs
def test_bookmarks_9():
    pdf = FakeHTML(string='''
      <h1 style="bookmark-label: 'h1 on page ' counter(page)">a</h1>
    ''').write_pdf()
    counts = re.findall(b'/Count ([0-9-]*)', pdf)
    outlines = counts.pop()
    assert outlines == b'1'
    assert re.findall(b'/Title \\((.*)\\)', pdf) == [b'h1 on page 1']


@assert_no_logs
def test_bookmarks_10():
    pdf = FakeHTML(string='''
      <style>
      div:before, div:after {
         content: '';
         bookmark-level: 1;
         bookmark-label: 'x';
      }
      </style>
      <div>a</div>
    ''').write_pdf()
    # x
    # x
    counts = re.findall(b'/Count ([0-9-]*)', pdf)
    outlines = counts.pop()
    assert outlines == b'2'
    assert re.findall(b'/Title \\((.*)\\)', pdf) == [b'x', b'x']


@assert_no_logs
def test_bookmarks_11():
    pdf = FakeHTML(string='''
      <div style="display:inline; white-space:pre;
       bookmark-level:1; bookmark-label:'a'">
      a
      a
      a
      </div>
      <div style="bookmark-level:1; bookmark-label:'b'">
        <div>b</div>
        <div style="break-before:always">c</div>
      </div>
    ''').write_pdf()
    # a
    # b
    counts = re.findall(b'/Count ([0-9-]*)', pdf)
    outlines = counts.pop()
    assert outlines == b'2'
    assert re.findall(b'/Title \\((.*)\\)', pdf) == [b'a', b'b']


@assert_no_logs
def test_bookmarks_12():
    pdf = FakeHTML(string='''
      <div style="bookmark-level:1; bookmark-label:contents">a</div>
    ''').write_pdf()
    # a
    counts = re.findall(b'/Count ([0-9-]*)', pdf)
    outlines = counts.pop()
    assert outlines == b'1'
    assert re.findall(b'/Title \\((.*)\\)', pdf) == [b'a']


@assert_no_logs
def test_bookmarks_13():
    pdf = FakeHTML(string='''
      <div style="bookmark-level:1; bookmark-label:contents;
                  text-transform:uppercase">a</div>
    ''').write_pdf()
    # a
    counts = re.findall(b'/Count ([0-9-]*)', pdf)
    outlines = counts.pop()
    assert outlines == b'1'
    assert re.findall(b'/Title \\((.*)\\)', pdf) == [b'a']


@assert_no_logs
def test_bookmarks_14():
    pdf = FakeHTML(string='''
      <h1>a</h1>
      <h1> b c d </h1>
      <h1> e
             f </h1>
      <h1> g <span> h </span> i </h1>
    ''').write_pdf()
    assert re.findall(b'/Count ([0-9-]*)', pdf)[-1] == b'4'
    assert re.findall(b'/Title \\((.*)\\)', pdf) == [
        b'a', b'b c d', b'e f', b'g h i']


@assert_no_logs
def test_bookmarks_15():
    # Regression test for #1815.
    pdf = FakeHTML(string='''
      <style>@page { size: 10pt 10pt }</style>
      <h1>a</h1>
    ''').write_pdf()
    assert re.findall(b'/Count ([0-9-]*)', pdf)[-1] == b'1'
    assert re.findall(b'/Title \\((.*)\\)', pdf) == [b'a']
    assert b'/XYZ 0 10 0' in pdf


@assert_no_logs
def test_viewer_preferences_none():
    # Documents not using the feature must not gain these keys.
    pdf = FakeHTML(string='<body>').write_pdf()
    assert b'/PageLayout' not in pdf
    assert b'/PageMode' not in pdf
    assert b'/ViewerPreferences' not in pdf


@assert_no_logs
def test_viewer_preferences_unchanged():
    # Byte-identical output when the feature is not used.
    html = '<h1>Hello</h1><p>World</p>'
    default = FakeHTML(string=html).write_pdf()
    explicit_none = FakeHTML(string=html).write_pdf(
        pdf_page_layout=None, pdf_page_mode=None, pdf_viewer_preferences=None)
    assert default == explicit_none


@assert_no_logs
def test_pdf_open_action_none():
    # Documents not using the feature must not gain an /OpenAction.
    pdf = FakeHTML(string='<body>').write_pdf()
    assert b'/OpenAction' not in pdf


@assert_no_logs
def test_pdf_open_action_unchanged():
    # Byte-identical output when the feature is not used.
    html = '<h1 id=top>Hello</h1><p>World</p>'
    default = FakeHTML(string=html).write_pdf()
    explicit_none = FakeHTML(string=html).write_pdf(pdf_open_action=None)
    assert default == explicit_none


@assert_no_logs
def test_pdf_open_action_anchor():
    pdf = FakeHTML(string='''
      <h1 id=top>Top</h1>
      <p style="page-break-before: always" id=target>Target</p>
    ''').write_pdf(pdf_open_action='target')
    assert b'/OpenAction' in pdf
    assert b'/S /GoTo' in pdf
    assert b'/XYZ' in pdf


@assert_no_logs
def test_pdf_open_action_page_number():
    pdf = FakeHTML(string='''
      <p>One</p>
      <p style="page-break-before: always">Two</p>
    ''').write_pdf(pdf_open_action=2)
    assert b'/OpenAction' in pdf
    assert b'/S /GoTo' in pdf


def test_pdf_open_action_missing_anchor():
    with capture_logs() as logs:
        pdf = FakeHTML(string='<body>Hello').write_pdf(
            pdf_open_action='nope')
    assert b'/OpenAction' not in pdf
    assert len(logs) == 1
    assert 'pdf_open_action' in logs[0]


def test_pdf_open_action_page_out_of_range():
    with capture_logs() as logs:
        pdf = FakeHTML(string='<body>Hello').write_pdf(pdf_open_action=5)
    assert b'/OpenAction' not in pdf
    assert len(logs) == 1
    assert 'out of range' in logs[0]


@assert_no_logs
def test_pdf_page_layout():
    pdf = FakeHTML(string='<body>').write_pdf(pdf_page_layout='two-column-left')
    assert b'/PageLayout /TwoColumnLeft' in pdf


@assert_no_logs
def test_pdf_page_mode():
    pdf = FakeHTML(string='<body>').write_pdf(pdf_page_mode='full-screen')
    assert b'/PageMode /FullScreen' in pdf


@assert_no_logs
def test_pdf_viewer_preferences():
    pdf = FakeHTML(string='<body>').write_pdf(pdf_viewer_preferences={
        'HideToolbar': True,
        'HideMenubar': False,
        'FitWindow': True,
        'NumCopies': 2,
        'Direction': '/R2L',
    })
    assert b'/ViewerPreferences' in pdf
    assert b'/HideToolbar true' in pdf
    assert b'/HideMenubar false' in pdf
    assert b'/FitWindow true' in pdf
    assert b'/NumCopies 2' in pdf
    assert b'/Direction /R2L' in pdf


@assert_no_logs
def test_pdf_viewer_preferences_merge_with_tags():
    # When tagging is enabled, DisplayDocTitle is set; user prefs must merge.
    pdf = FakeHTML(string='<html lang=en><body>Hi').write_pdf(
        pdf_tags=True, pdf_viewer_preferences={'HideToolbar': True})
    assert b'/DisplayDocTitle true' in pdf
    assert b'/HideToolbar true' in pdf


@assert_no_logs
def test_pdf_page_layout_raw_name():
    pdf = FakeHTML(string='<body>').write_pdf(pdf_page_layout='/OneColumn')
    assert b'/PageLayout /OneColumn' in pdf


def test_pdf_page_layout_unknown():
    with capture_logs() as logs:
        pdf = FakeHTML(string='<body>').write_pdf(pdf_page_layout='bogus')
    assert b'/PageLayout' not in pdf
    assert len(logs) == 1
    assert 'pdf_page_layout' in logs[0]


@assert_no_logs
def test_pdf_page_labels_none():
    # Documents not using the feature must not gain a /PageLabels number tree.
    pdf = FakeHTML(string='<body>').write_pdf(uncompressed_pdf=True)
    assert b'/PageLabels' not in pdf


@assert_no_logs
def test_pdf_page_labels_unchanged():
    # Byte-identical output when the feature is not used.
    html = '<style>div{page-break-after:always}</style><div>a</div><div>b</div>'
    a = FakeHTML(string=html).write_pdf()
    b = FakeHTML(string=html).write_pdf()
    assert a == b
    assert b'/PageLabels' not in a


@assert_no_logs
def test_pdf_page_labels_roman():
    # Roman numerals on the first pages, decimal afterwards.
    pdf = FakeHTML(string='''
      <style>
        @page { size: 100px 100px }
        @page :first { -weasy-pdf-page-label: lower-roman }
        div { page-break-after: always }
      </style>
      <div>i</div><div>1</div>
    ''').write_pdf(uncompressed_pdf=True)
    assert b'/PageLabels' in pdf
    # First page uses lower-roman (/r), the rest default decimal (/D).
    assert re.search(
        br'/Nums \[0 <</S /r>> 1 <</S /D>>\]', pdf)


@assert_no_logs
def test_pdf_page_labels_prefix_and_start():
    pdf = FakeHTML(string='''
      <style>
        @page { -weasy-pdf-page-label: decimal "A-" start(5) }
      </style>
      <body>Hello
    ''').write_pdf(uncompressed_pdf=True)
    assert b'/PageLabels' in pdf
    assert b'/S /D' in pdf
    assert b'/P (A-)' in pdf
    assert b'/St 5' in pdf


def test_pdf_page_labels_invalid():
    with capture_logs() as logs:
        pdf = FakeHTML(string='''
          <style>@page { -weasy-pdf-page-label: bogus }</style>
          <body>Hi
        ''').write_pdf(uncompressed_pdf=True)
    assert b'/PageLabels' not in pdf
    assert len(logs) == 1
    assert 'pdf-page-label' in logs[0]


@assert_no_logs
def test_links_none():
    pdf = FakeHTML(string='<body>').write_pdf()
    assert b'Annots' not in pdf


@assert_no_logs
def test_links():
    pdf = FakeHTML(string='''
      <style>
        body { margin: 0; font-size: 10pt; line-height: 2 }
        p { display: block; height: 90pt; margin: 0 0 10pt 0 }
        img { width: 30pt; vertical-align: top }
      </style>
      <p><a href="https://weasyprint.org"><img src=pattern.png></a></p>
      <p style="padding: 0 10pt"><a
         href="#lipsum"><img style="border: solid 1pt"
                             src=pattern.png></a></p>
      <p id=hello>Hello, World</p>
      <p id=lipsum>
        <a style="display: block; page-break-before: always; height: 30pt"
           href="#hel%6Co"></a>a
      </p>
    ''', base_url=resource_path('<inline HTML>')).write_pdf()

    uris = re.findall(b'/URI \\((.*)\\)', pdf)
    types = re.findall(b'/S (/\\w*)', pdf)
    subtypes = re.findall(b'/Subtype (/\\w*)', pdf)
    rects = [
        [float(number) for number in match.split()] for match in re.findall(
            b'/Rect \\[([\\d\\.]+ [\\d\\.]+ [\\d\\.]+ [\\d\\.]+)\\]', pdf)]

    # 30pt wide (like the image), 20pt high (like line-height)
    assert uris.pop(0) == b'https://weasyprint.org'
    assert subtypes.pop(0) == b'/Link'
    assert types.pop(0) == b'/URI'
    assert rects.pop(0) == [0, TOP, 30, TOP - 20]

    # The image itself: 30*30pt
    assert uris.pop(0) == b'https://weasyprint.org'
    assert subtypes.pop(0) == b'/Link'
    assert types.pop(0) == b'/URI'
    assert rects.pop(0) == [0, TOP, 30, TOP - 30]

    # 32pt wide (image + 2 * 1pt of border), 20pt high
    assert subtypes.pop(0) == b'/Link'
    assert b'/Dest (lipsum)' in pdf
    link = re.search(
        b'\\(lipsum\\) \\[\\d+ 0 R /XYZ ([\\d\\.]+ [\\d\\.]+ [\\d\\.]+)]',
        pdf).group(1)
    assert [float(number) for number in link.split()] == [0, TOP, 0]
    assert rects.pop(0) == [10, TOP - 100, 10 + 32, TOP - 100 - 20]

    # The image itself: 32*32pt
    assert subtypes.pop(0) == b'/Link'
    assert rects.pop(0) == [10, TOP - 100, 10 + 32, TOP - 100 - 32]

    # 100% wide (block), 30pt high
    assert subtypes.pop(0) == b'/Link'
    assert b'/Dest (hello)' in pdf
    link = re.search(
        b'\\(hello\\) \\[\\d+ 0 R /XYZ ([\\d\\.]+ [\\d\\.]+ [\\d\\.]+)]',
        pdf).group(1)
    assert [float(number) for number in link.split()] == [0, TOP - 200, 0]
    assert rects.pop(0) == [0, TOP, RIGHT, TOP - 30]


@assert_no_logs
def test_sorted_links():
    # Regression test for #1352.
    pdf = FakeHTML(string='''
      <p id="zzz">zzz</p>
      <p id="aaa">aaa</p>
      <a href="#zzz">z</a>
      <a href="#aaa">a</a>
    ''', base_url=resource_path('<inline HTML>')).write_pdf()
    assert b'(zzz) [' in pdf.split(b'(aaa) [')[-1]


@assert_no_logs
def test_relative_links_no_height():
    # 100% wide (block), 0pt high
    pdf = FakeHTML(
        string='<a href="../lipsum" style="display: block"></a>a',
        base_url='https://weasyprint.org/foo/bar/').write_pdf()
    assert b'/S /URI\n/URI (https://weasyprint.org/foo/lipsum)'
    assert f'/Rect [0 {TOP} {RIGHT} {TOP}]'.encode() in pdf


@assert_no_logs
def test_relative_links_missing_base():
    # Relative URI reference without a base URI
    pdf = FakeHTML(
        string='<a href="../lipsum" style="display: block"></a>a',
        base_url=None).write_pdf()
    assert b'/S /URI\n/URI (../lipsum)'
    assert f'/Rect [0 {TOP} {RIGHT} {TOP}]'.encode() in pdf


@assert_no_logs
def test_relative_links_missing_base_link():
    # Relative URI reference without a base URI: not supported for -weasy-link
    with capture_logs() as logs:
        pdf = FakeHTML(
            string='<div style="-weasy-link: url(../lipsum)">',
            base_url=None).write_pdf()
    assert b'/Annots' not in pdf
    assert len(logs) == 1
    assert 'WARNING: Ignored `-weasy-link: url(../lipsum)`' in logs[0]
    assert 'Relative URI reference without a base URI' in logs[0]


@assert_no_logs
def test_relative_links_internal():
    # Internal URI reference without a base URI: OK
    pdf = FakeHTML(
        string='<a href="#lipsum" id="lipsum" style="display: block"></a>a',
        base_url=None).write_pdf()
    assert b'/Dest (lipsum)' in pdf
    link = re.search(
        b'\\(lipsum\\) \\[\\d+ 0 R /XYZ ([\\d\\.]+ [\\d\\.]+ [\\d\\.]+)]',
        pdf).group(1)
    assert [float(number) for number in link.split()] == [0, TOP, 0]
    rect = re.search(
        b'/Rect \\[([\\d\\.]+ [\\d\\.]+ [\\d\\.]+ [\\d\\.]+)\\]',
        pdf).group(1)
    assert [float(number) for number in rect.split()] == [0, TOP, RIGHT, TOP]


@assert_no_logs
def test_relative_links_anchors():
    pdf = FakeHTML(
        string='<div style="-weasy-link: url(#lipsum)" id="lipsum"></div>a',
        base_url=None).write_pdf()
    assert b'/Dest (lipsum)' in pdf
    link = re.search(
        b'\\(lipsum\\) \\[\\d+ 0 R /XYZ ([\\d\\.]+ [\\d\\.]+ [\\d\\.]+)]',
        pdf).group(1)
    assert [float(number) for number in link.split()] == [0, TOP, 0]
    rect = re.search(
        b'/Rect \\[([\\d\\.]+ [\\d\\.]+ [\\d\\.]+ [\\d\\.]+)\\]',
        pdf).group(1)
    assert [float(number) for number in rect.split()] == [0, TOP, RIGHT, TOP]


@assert_no_logs
def test_relative_links_different_base():
    pdf = FakeHTML(
        string='<a href="/test/lipsum"></a>a',
        base_url='https://weasyprint.org/foo/bar/').write_pdf()
    assert b'https://weasyprint.org/test/lipsum' in pdf


@assert_no_logs
def test_relative_links_same_base():
    pdf = FakeHTML(
        string='<a id="test" href="/foo/bar/#test"></a>a',
        base_url='https://weasyprint.org/foo/bar/').write_pdf()
    assert b'/Dest (test)' in pdf


@assert_no_logs
def test_missing_links():
    with capture_logs() as logs:
        pdf = FakeHTML(string='''
          <style> a { display: block; height: 15pt } </style>
          <a href="#lipsum"></a>
          <a href="#missing" id="lipsum"></a>
          <a href=""></a>a
        ''', base_url=None).write_pdf()
    assert b'/Dest (lipsum)' in pdf
    assert len(logs) == 1
    link = re.search(
        b'\\(lipsum\\) \\[\\d+ 0 R /XYZ ([\\d\\.]+ [\\d\\.]+ [\\d\\.]+)]',
        pdf).group(1)
    assert [float(number) for number in link.split()] == [0, TOP - 15, 0]
    rect = re.search(
        b'/Rect \\[([\\d\\.]+ [\\d\\.]+ [\\d\\.]+ [\\d\\.]+)\\]',
        pdf).group(1)
    assert [float(number) for number in rect.split()] == [
        0, TOP, RIGHT, TOP - 15]
    assert 'ERROR: No anchor #missing for internal URI reference' in logs[0]


@assert_no_logs
def test_anchor_multiple_pages():
    pdf = FakeHTML(string='''
      <style> a { display: block; break-after: page } </style>
      <div id="lipsum">
        <a href="#lipsum"></a>
        <a href="#lipsum"></a>
        <a href="#lipsum"></a>
      </div>
    ''', base_url=None).write_pdf()
    first_page, = re.findall(b'/Kids \\[(\\d+) 0 R', pdf)
    assert b'/Names [(lipsum) [' + first_page in pdf


@assert_no_logs
def test_embed_gif():
    assert b'/Filter /DCTDecode' not in FakeHTML(
        base_url=resource_path('dummy.html'),
        string='<img src="pattern.gif">').write_pdf()


@assert_no_logs
def test_embed_jpeg():
    # JPEG-encoded image, embedded in PDF:
    assert b'/Filter /DCTDecode' in FakeHTML(
        base_url=resource_path('dummy.html'),
        string='<img src="blue.jpg">').write_pdf()


@assert_no_logs
def test_embed_image_once():
    # Image repeated multiple times, embedded once
    assert FakeHTML(
        base_url=resource_path('dummy.html'),
        string='''
          <img src="blue.jpg">
          <div style="background: url(blue.jpg)"></div>
          <img src="blue.jpg">
          <div style="background: url(blue.jpg) no-repeat"></div>
        ''').write_pdf().count(b'/Filter /DCTDecode') == 1


@assert_no_logs
def test_embed_images_from_pages():
    page1, = FakeHTML(
        base_url=resource_path('dummy.html'),
        string='<img src="blue.jpg">').render().pages
    page2, = FakeHTML(
        base_url=resource_path('dummy.html'),
        string='<img src="not-optimized.jpg">').render().pages
    document = Document(
        (page1, page2), metadata=DocumentMetadata(),
        font_config=FontConfiguration(), color_profiles={},
        url_fetcher=None, output_intent=None).write_pdf()
    assert document.count(b'/Filter /DCTDecode') == 2


@assert_no_logs
def test_document_info():
    pdf = FakeHTML(string='''
      <meta name=author content="I Me &amp; Myself">
      <title>Test document</title>
      <h1>Another title</h1>
      <meta name=generator content="Human after all">
      <meta name=keywords content="html ,\tcss,
                                   pdf,css">
      <meta name=description content="Blah… ">
      <meta name=dcterms.created content=2011-04-21T23:00:00Z>
      <meta name=dcterms.modified content=2013-07-21T23:46+01:00>
    ''').write_pdf()
    assert b'/Author (I Me & Myself)' in pdf
    assert b'/Title (Test document)' in pdf
    assert (
        b'/Creator <feff00480075006d0061006e00a00061'
        b'006600740065007200a00061006c006c>') in pdf
    assert b'/Keywords (html, css, pdf)' in pdf
    assert b'/Subject <feff0042006c0061006820260020>' in pdf
    assert b'/CreationDate (D:20110421230000Z)' in pdf
    assert b"/ModDate (D:20130721234600+01'00)" in pdf


@assert_no_logs
def test_embedded_files_attachments(tmp_path):
    absolute_tmp_path = tmp_path / 'some_file.txt'
    absolute_data = b'12345678'
    absolute_tmp_path.write_bytes(absolute_data)
    absolute_url = path2url(absolute_tmp_path)
    assert absolute_url.startswith('file://')

    relative_tmp_path = tmp_path / 'äöü.txt'
    relative_data = b'abcdefgh'
    relative_tmp_path.write_bytes(relative_data)

    pdf = FakeHTML(
        string=f'''
          <title>Test document</title>
          <meta charset="utf-8">
          <link
            rel="attachment"
            title="some file attachment äöü"
            href="data:,hi%20there">
          <link rel="attachment" href="{absolute_url}">
          <link rel="attachment" href="{relative_tmp_path.name}">
          <h1>Heading 1</h1>
          <h2>Heading 2</h2>
        ''',
        base_url=tmp_path,
    ).write_pdf(
        attachments=[
            Attachment('data:,oob attachment', description='Hello'),
            'data:,raw URL',
            io.BytesIO(b'file like obj')
        ]
    )
    assert f'<{hashlib.md5(b"hi there").hexdigest()}>'.encode() in pdf
    assert b'/F (attachment.bin)' in pdf
    assert b'/UF (attachment.bin)' in pdf
    name = BOM_UTF16_BE + 'some file attachment äöü'.encode('utf-16-be')
    assert b'/Desc <' + name.hex().encode() + b'>' in pdf

    assert hashlib.md5(absolute_data).hexdigest().encode() in pdf
    assert absolute_tmp_path.name.encode() in pdf

    assert hashlib.md5(relative_data).hexdigest().encode() in pdf
    name = BOM_UTF16_BE + 'some file attachment äöü'.encode('utf-16-be')
    assert b'/Desc <' + name.hex().encode() + b'>' in pdf

    assert hashlib.md5(b'oob attachment').hexdigest().encode() in pdf
    assert b'/Desc (Hello)' in pdf
    assert hashlib.md5(b'raw URL').hexdigest().encode() in pdf
    assert hashlib.md5(b'file like obj').hexdigest().encode() in pdf

    assert b'/EmbeddedFiles' in pdf
    assert b'/Outlines' in pdf


@assert_no_logs
def test_attachments_data():
    pdf = FakeHTML(string='''
      <title>Test document 2</title>
      <meta charset="utf-8">
      <link rel="attachment" href="data:,some data">
    ''').write_pdf()
    md5 = f'<{hashlib.md5(b"some data").hexdigest()}>'.encode()
    assert md5 in pdf
    assert b'EmbeddedFiles' in pdf


@assert_no_logs
def test_attachments_data_with_anchor():
    pdf = FakeHTML(string='''
      <title>Test document 2</title>
      <meta charset="utf-8">
      <link rel="attachment" href="data:,some data">
      <h1 id="title">Title</h1>
      <a href="#title">example</a>
    ''').write_pdf()
    md5 = f'<{hashlib.md5(b"some data").hexdigest()}>'.encode()
    assert md5 in pdf
    assert b'EmbeddedFiles' in pdf


@assert_no_logs
def test_attachments_no_href():
    with capture_logs() as logs:
        pdf = FakeHTML(string='''
          <title>Test document 2</title>
          <meta charset="utf-8">
          <link rel="attachment">
        ''').write_pdf()
    assert b'Names' not in pdf
    assert b'Outlines' not in pdf
    assert len(logs) == 1
    assert 'Missing href' in logs[0]


@assert_no_logs
def test_attachments_none():
    pdf = FakeHTML(string='''
      <title>Test document 3</title>
      <meta charset="utf-8">
      <h1>Heading</h1>
    ''').write_pdf()
    assert b'Names' not in pdf
    assert b'Outlines' in pdf


@assert_no_logs
def test_attachments_none_empty():
    pdf = FakeHTML(string='''
      <title>Test document 3</title>
      <meta charset="utf-8">
    ''').write_pdf()
    assert b'Names' not in pdf
    assert b'Outlines' not in pdf


@assert_no_logs
def test_annotations():
    pdf = FakeHTML(string='''
      <title>Test document</title>
      <meta charset="utf-8">
      <a
        rel="attachment"
        href="data:,some data"
        download>A link that lets you download an attachment</a>
    ''').write_pdf()

    assert hashlib.md5(b'some data').hexdigest().encode() in pdf
    assert b'/FileAttachment' in pdf
    assert b'/EmbeddedFiles' not in pdf


@pytest.mark.parametrize(('style', 'media', 'bleed', 'trim'), [
    ('bleed: 30pt; size: 10pt',
     [-30, -30, 40, 40],
     [-10, -10, 20, 20],
     [0, 0, 10, 10]),
    ('bleed: 15pt 3pt 6pt 18pt; size: 12pt 15pt',
     [-18, -15, 15, 21],
     [-10, -10, 15, 21],
     [0, 0, 12, 15]),
])
@assert_no_logs
def test_bleed(style, media, bleed, trim):
    pdf = FakeHTML(string='''
      <title>Test document</title>
      <style>@page { %s }</style>
      <body>test
    ''' % style).write_pdf()
    assert f'/MediaBox {str(media).replace(",", "")}'.encode() in pdf
    assert f'/BleedBox {str(bleed).replace(",", "")}'.encode() in pdf
    assert f'/TrimBox {str(trim).replace(",", "")}'.encode() in pdf


@assert_no_logs
def test_default_rdf_metadata():
    pdf_document = FakeHTML(string='<body>test</body>').render()

    pdf_document.metadata.title = None

    pdf_bytes = pdf_document.write_pdf(
        pdf_variant='pdf/a-3b', pdf_identifier=b'example-bytes', uncompressed_pdf=True)
    assert b'<rdf:RDF xmlns:pdf="http://ns.adobe.com/pdf/1.3/"' in pdf_bytes


@assert_no_logs
def test_custom_rdf_metadata():
    def generate_rdf_metadata(*args, **kwargs):
        return b'TEST_METADATA'

    pdf_document = FakeHTML(string='<body>test</body>').render()

    pdf_document.metadata.title = None
    pdf_document.metadata.generate_rdf_metadata = generate_rdf_metadata

    pdf_bytes = pdf_document.write_pdf(
        pdf_variant='pdf/a-3b', pdf_identifier=b'example-bytes', uncompressed_pdf=True)
    assert b'TEST_METADATA' in pdf_bytes


@assert_no_logs
def test_font_descent_ascent():
    pdf = FakeHTML(string='''
      <html style="font-family: weasyprint">abc
    ''').write_pdf()
    assert b'/Descent -200' in pdf
    assert b'/Ascent 800' in pdf


@assert_no_logs
def test_pdf_tags_inline_table():
    # Regression test for #2601.
    FakeHTML(string='''
      <html lang="en"><table style="display: inline"><td>abc
    ''').write_pdf(pdf_tags=True)


@assert_no_logs
def test_pdf_ua_2_namespace_type():
    # Regression test for #2786.
    pdf = FakeHTML(string='<html lang="en"><body>abc').write_pdf(
        pdf_variant='pdf/ua-2', uncompressed_pdf=True)
    assert b'/Type /Namespace' in pdf


@assert_no_logs
def test_clip_path_inset():
    # clip-path: inset(10px) clips the box to a rectangle inset by 10px on each
    # side. FakeHTML has zero margins so the border box sits at the page origin.
    pdf = FakeHTML(string=(
        '<div style="width: 100px; height: 100px; background: red; '
        'clip-path: inset(10px)"></div>'
    )).write_pdf(uncompressed_pdf=True)
    # Border box 0 0 100 100 inset by 10px -> 10 10 80 80, then clipped (W n).
    assert b'10 10 80 80 re' in pdf
    assert b'W\nn' in pdf


@assert_no_logs
def test_clip_path_inset_four_values():
    pdf = FakeHTML(string=(
        '<div style="width: 100px; height: 100px; background: red; '
        'clip-path: inset(10px 20px 30px 40px)"></div>'
    )).write_pdf(uncompressed_pdf=True)
    # top=10 right=20 bottom=30 left=40 -> x=40 y=10 w=40 h=60.
    assert b'40 10 40 60 re' in pdf


@assert_no_logs
def test_clip_path_polygon():
    pdf = FakeHTML(string=(
        '<div style="width: 100px; height: 100px; background: red; '
        'clip-path: polygon(0 0, 100px 0, 50px 100px)"></div>'
    )).write_pdf(uncompressed_pdf=True)
    # A triangle path is emitted and used as a clip.
    assert b'0 0 m' in pdf
    assert b'100 0 l' in pdf
    assert b'50 100 l' in pdf


@assert_no_logs
def test_clip_path_polygon_evenodd():
    pdf = FakeHTML(string=(
        '<div style="width: 100px; height: 100px; background: red; '
        'clip-path: polygon(evenodd, 0 0, 100px 0, 50px 100px)"></div>'
    )).write_pdf(uncompressed_pdf=True)
    # The even-odd clip operator must be used.
    assert b'W*' in pdf


@assert_no_logs
def test_clip_path_circle():
    pdf = FakeHTML(string=(
        '<div style="width: 100px; height: 100px; background: red; '
        'clip-path: circle(40px)"></div>'
    )).write_pdf(uncompressed_pdf=True)
    # The ellipse path starts at the right-most point (cx + r, cy) = (90, 50)
    # for a circle centred at the box centre (50, 50) with radius 40, and is
    # built from Bézier curves.
    assert b'90 50 m' in pdf
    assert b' c\n' in pdf


@assert_no_logs
def test_clip_path_none():
    # The default value must not emit any extra clipping path.
    pdf = FakeHTML(string=(
        '<div style="width: 100px; height: 100px; background: red; '
        'clip-path: none"></div>'
    )).write_pdf(uncompressed_pdf=True)
    assert b'10 10 80 80 re' not in pdf


@assert_no_logs
def test_layer_optional_content_group():
    # An element with -weasy-layer is assigned to a named PDF optional content
    # group (layer) and its drawing is wrapped in /OC ... BDC ... EMC.
    pdf = FakeHTML(string=(
        '<div style="-weasy-layer: foo">layered</div>'
    )).write_pdf(uncompressed_pdf=True)
    # The catalog gets an /OCProperties dictionary listing the OCG.
    assert b'/OCProperties' in pdf
    # An OCG dictionary named 'foo' is emitted.
    assert b'/Type /OCG' in pdf
    assert b'/Name (foo)' in pdf
    # The content is wrapped in an optional-content marked-content block.
    assert re.search(rb'/OC /oc\d+ BDC', pdf)
    assert b'EMC' in pdf
    # The page resources reference the OCG under /Properties.
    assert b'/Properties' in pdf


@assert_no_logs
def test_layer_shared_and_distinct():
    # Elements sharing a name belong to one OCG; distinct names get distinct
    # OCGs.
    pdf = FakeHTML(string=(
        '<div style="-weasy-layer: foo">A</div>'
        '<div style="-weasy-layer: bar">B</div>'
        '<div style="-weasy-layer: foo">C</div>'
    )).write_pdf(uncompressed_pdf=True)
    # Exactly one OCG dict per distinct name.
    assert pdf.count(b'/Name (foo)') == 1
    assert pdf.count(b'/Name (bar)') == 1
    # Three marked-content blocks (one per element), the two 'foo' elements
    # sharing the same property key.
    blocks = re.findall(rb'/OC /(oc\d+) BDC', pdf)
    assert len(blocks) == 3
    assert blocks[0] == blocks[2]
    assert blocks[0] != blocks[1]


@assert_no_logs
def test_layer_not_used_byte_identical():
    # A document that never uses -weasy-layer must be unaffected: no
    # /OCProperties, and identical bytes across runs.
    source = '<div style="width: 50px; height: 50px; background: red">a</div>'
    first = FakeHTML(string=source).write_pdf()
    second = FakeHTML(string=source).write_pdf()
    assert first == second
    assert b'/OCProperties' not in first
    assert b'/OCG' not in first
