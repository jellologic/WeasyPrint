"""Test ``-weasy-continued-content`` on tables."""

from ..testing_utils import assert_no_logs, render_pages


def text_boxes(page):
    return [
        box.text for box in page.descendants()
        if type(box).__name__ == 'TextBox']


HTML = '''
  <style>
    @page { size: 200px 80px; margin: 10px }
    body { margin: 0; font-size: 0 }
    table { border-collapse: separate; border-spacing: 0; width: 100%%;
            %s }
    td, th { height: 10px; padding: 0; font-size: 10px; line-height: 10px }
  </style>
  <table>
    <thead><tr><th>Canopy</th><th>Height</th></tr></thead>
    <tbody>%s</tbody>
  </table>
'''

ROWS = ''.join(
    f'<tr><td>r{i}a</td><td>r{i}b</td></tr>' for i in range(10))


@assert_no_logs
def test_table_continued_content():
    # The repeated thead on continuation pages carries the marker row.
    pages = render_pages(HTML % ('-weasy-continued-content: "(continued)"',
                                 ROWS))
    texts_1 = text_boxes(pages[0])
    assert 'Canopy' in texts_1
    assert '(continued)' not in texts_1
    for page in pages[1:]:
        texts = text_boxes(page)
        assert 'Canopy' in texts
        assert '(continued)' in texts


@assert_no_logs
def test_table_no_continued_content():
    pages = render_pages(HTML % ('', ROWS))
    assert 'Canopy' in text_boxes(pages[0])
    assert len(pages) > 1
    for page in pages[1:]:
        assert '(continued)' not in text_boxes(page)
