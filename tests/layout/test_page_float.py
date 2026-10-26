"""Test the ``float: top`` / ``float: bottom`` page floats."""
from ..testing_utils import assert_no_logs, render_pages


def find_box(page, tag):
    return next(
        box for box in page.descendants()
        if getattr(box, 'element_tag', '') == tag
        and hasattr(box, 'margin_height'))


def find_p(page, text):
    return next(
        box for box in page.descendants()
        if getattr(box, 'element_tag', '') == 'p'
        and any(
            type(child).__name__ == 'TextBox' and text in child.text
            for child in box.descendants()))


@assert_no_logs
def test_page_float_bottom():
    page, = render_pages('''
      <style>
        @page { size: 200px 200px; margin: 0 }
        body { font-family: weasyprint; font-size: 10pt }
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
    page_1, page_2 = render_pages('''
      <style>
        @page { size: 200px 200px; margin: 0 }
        body { font-family: weasyprint; font-size: 10pt }
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
        if getattr(box, 'element_tag', '') == 'aside']


@assert_no_logs
def test_page_float_top_next_page():
    # A "float: top" box is placed at the top of the next page, above
    # the content that follows it in the document.
    page_1, page_2 = render_pages('''
      <style>
        @page { size: 200px 200px; margin: 0 }
        body { font-family: weasyprint; font-size: 10pt }
        p { margin: 0 }
        div { float: top; float-reference: page; margin: 0; height: 40px }
      </style>
      <p>first</p>
      <div></div>
      <p>second</p>
    ''')
    assert len(pages_list(page_1, page_2)) == 2
    header = find_box(page_2, 'div')
    top = page_2.content_box_y()
    assert abs(header.position_y - top) < 0.01
    second = find_p(page_2, 'second')
    assert abs(second.position_y - (top + 40)) < 0.01
    first = find_p(page_1, 'first')
    assert first.position_y < 100


def pages_list(page_1, page_2):
    return [page_1, page_2]
