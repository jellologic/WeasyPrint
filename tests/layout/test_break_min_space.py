"""Test the non-standard ``break-before-min-space`` property."""
from ..testing_utils import assert_no_logs, render_pages


def find_box(page, tag):
    return next(
        box for box in page.descendants()
        if box.element_tag == tag and hasattr(box, 'margin_height'))


@assert_no_logs
def test_break_before_min_space():
    # A block that is split and starts too close to the bottom of the
    # page moves entirely to the next page.
    pages = render_pages('''
      <style>
        @page { size: 4in 4in; margin: 0.5in }
        body { font-family: weasyprint; font-size: 12pt }
        .lead { height: 2.4in; margin: 0 }
        section { break-before-min-space: 50%; height: 1in; margin: 0 }
      </style>
      <div class="lead"></div>
      <section>content</section>
    ''')
    page_1, page_2 = pages[0], pages[1]
    assert find_box(page_1, 'div')
    assert not [
        box for box in page_1.descendants()
        if box.element_tag == 'section']
    section = find_box(page_2, 'section')
    assert abs(section.margin_height() - 96) < 1  # whole 1in section


@assert_no_logs
def test_break_before_min_space_fits():
    # The block is not moved when it fits completely in the remaining
    # space, even when it is smaller than the threshold.
    pages = render_pages('''
      <style>
        @page { size: 4in 4in; margin: 0.5in }
        body { font-family: weasyprint; font-size: 12pt }
        .lead { height: 2.2in; margin: 0 }
        section { break-before-min-space: 50%; height: 0.5in; margin: 0 }
      </style>
      <div class="lead"></div>
      <section>content</section>
    ''')
    section = find_box(pages[0], 'section')
    assert abs(section.margin_height() - 48) < 1


@assert_no_logs
def test_break_before_min_space_auto():
    # Without the property, the block is split as usual between its
    # children.
    pages = render_pages('''
      <style>
        @page { size: 4in 4in; margin: 0.5in }
        body { font-family: weasyprint; font-size: 12pt }
        .lead { height: 2.4in; margin: 0 }
        section { margin: 0 }
        section div { height: 0.5in; margin: 0 }
      </style>
      <div class="lead"></div>
      <section><div>a</div><div>b</div></section>
    ''')
    assert find_box(pages[0], 'section')
    assert 'a' in [
        child.text for child in pages[0].descendants()
        if type(child).__name__ == 'TextBox']
