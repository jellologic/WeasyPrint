"""Test the ``-weasy-continued-content`` property."""

from ..testing_utils import assert_no_logs, render_pages


def text_boxes(page):
    return [
        box.text for box in page.descendants()
        if type(box).__name__ == 'TextBox']


HTML = '''
  <style>
    @page { size: 200px 100px; margin: 10px }
    body { font-family: weasyprint; font-size: 10px; line-height: 10px }
    p { margin: 0; orphans: 2; widows: 2 }
    section { %s }
  </style>
  <section>
    <p>%s</p>
  </section>
'''

PARAGRAPH = '<br>'.join('abcdefghijklm')


@assert_no_logs
def test_continued_content():
    # Continuation fragments start with the marker line.
    pages = render_pages(HTML % ('-weasy-continued-content: "(continued)"',
                                 PARAGRAPH))
    # The first page starts with the content, not the marker.
    assert text_boxes(pages[0])[0] == 'a'
    for page in pages[1:]:
        assert text_boxes(page)[0] == '(continued)'


@assert_no_logs
def test_no_continued_content():
    # Without the property, continuation fragments have no marker.
    pages = render_pages(HTML % ('', PARAGRAPH))
    assert text_boxes(pages[0])[0] == 'a'
    for page in pages[1:]:
        assert text_boxes(page)[0] != '(continued)'
