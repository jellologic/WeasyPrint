"""Test page floats (``float: top`` / ``bottom`` with ``float-reference``)."""
from ..testing_utils import assert_no_logs, capture_logs, render_pages


def find_box(page, tag):
    return next(
        box for box in page.descendants()
        if box.element_tag == tag and hasattr(box, 'margin_height'))


@assert_no_logs
def test_page_float_bottom():
    # A "float: bottom" box is placed at the bottom of the page content
    # area, below the other content.
    page, = render_pages('''
      <style>
        @page { size: 6in 4in; margin: 0.5in }
        body { font-family: weasyprint; font-size: 12pt }
        section { height: 1in; margin: 0 }
        aside { float: bottom; float-reference: page;
                margin: 0; height: 0.5in }
      </style>
      <section>content</section>
      <aside>foot</aside>
    ''')
    aside = find_box(page, 'aside')
    section = find_box(page, 'section')
    content_bottom = page.content_box_y() + page.height
    assert abs(
        aside.position_y + aside.margin_height() - content_bottom) < 1
    assert section.position_y + section.margin_height() <= aside.position_y


@assert_no_logs
def test_page_float_bottom_defer():
    # When there is not enough room at the bottom of the page, the whole
    # float is deferred to the next page.
    page_1, page_2 = render_pages('''
      <style>
        @page { size: 6in 4in; margin: 0.5in }
        body { font-family: weasyprint; font-size: 12pt }
        section { height: 2.8in; margin: 0 }
        aside { float: bottom; float-reference: page;
                margin: 0; height: 0.6in }
      </style>
      <section>content</section>
      <aside>foot</aside>
    ''')
    aside = find_box(page_2, 'aside')
    content_bottom = page_2.content_box_y() + page_2.height
    assert abs(
        aside.position_y + aside.margin_height() - content_bottom) < 1
    assert find_box(page_1, 'section')
    assert not [
        box for box in page_1.descendants()
        if box.element_tag == 'aside']


@assert_no_logs
def test_page_float_top_unsupported():
    # "float: top" is not supported yet: a warning is logged and the box
    # is rendered as a regular float.
    with capture_logs() as logs:
        page, = render_pages('''
      <style>
        @page { size: 6in 4in; margin: 0.5in }
        body { font-family: weasyprint; font-size: 12pt }
        section { height: 1in; margin: 0 }
        header { float: top; float-reference: page;
                 margin: 0; height: 0.5in }
      </style>
      <section>first</section>
      <header>head</header>
      <section>second</section>
    ''')
    assert any('"float: top"' in log for log in logs)
    assert find_box(page, 'header')
    assert find_box(page, 'section')
