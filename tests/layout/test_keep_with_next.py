"""Test the ``-weasy-keep-with-next`` property."""

from ..testing_utils import assert_no_logs, render_pages


def text_boxes(page):
    return [
        box.text for box in page.descendants()
        if type(box).__name__ == 'TextBox']


HTML = '''
  <style>
    @page { size: 200px 100px; margin: 10px }
    body { font-family: weasyprint; font-size: 10px; line-height: 10px }
    div { height: 60px }
    h1 { margin: 0 }
    p { margin: 0; orphans: 1; widows: 1 }
  </style>
  <div></div>
  <h1 style="%s">heading</h1>
  <p>a<br>b<br>c<br>d<br>e<br>f<br>g<br>h</p>
'''

# The paragraph is 8 lines of 10px; the filler leaves exactly one line of
# space after the heading on the first page.


@assert_no_logs
def test_keep_with_next():
    # Without keep-with-next, the heading stays on page 1 with a single
    # line of the paragraph.
    pages = render_pages(HTML % '')
    assert 'heading' in text_boxes(pages[0])


@assert_no_logs
def test_keep_with_next_amount():
    # The heading requires at least 2 lines of the following paragraph:
    # both move to the next page.
    page1, page2 = render_pages(HTML % '-weasy-keep-with-next: 2')[:2]
    # Page 1 only has the (empty) filler.
    assert text_boxes(page1) == []
    # Page 2 has the heading and at least two paragraph lines.
    page2_texts = text_boxes(page2)
    assert 'heading' in page2_texts
    assert len([t for t in page2_texts if t in 'abcdefgh']) >= 2
