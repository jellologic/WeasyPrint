"""Test the ``-weasy-row-orphans`` and ``-weasy-row-widows`` properties."""

from weasyprint.formatting_structure import boxes

from ..testing_utils import assert_no_logs, render_pages


def table_rows(page):
    return [
        box for box in page.descendants()
        if isinstance(box, boxes.TableRowBox)]


ROWS = ''.join(f'<tr><td>{i}</td></tr>' for i in range(6))
TWO_GROUPS = (
    '<tbody>' + ''.join(f'<tr><td>{i}</td></tr>' for i in range(4)) +
    '</tbody><tbody>' +
    ''.join(f'<tr><td>{i}</td></tr>' for i in range(4, 8)) + '</tbody>')

STYLE = '''
  @page { size: 200px %dpx; margin: 10px }
  body { margin: 0 }
  table { border-collapse: separate; border-spacing: 0; width: 100%%;
          %s }
  td { height: 10px; padding: 0; font-size: 0; line-height: 0 }
'''


@assert_no_logs
def test_row_widows():
    # Five rows fit on the first page but the sixth overflows: moving a
    # row to the next page leaves two rows there instead of one.
    pages = render_pages(
        '<style>' + STYLE % (70, '-weasy-row-widows: 2') + '</style>'
        f'<table>{ROWS}</table>')
    assert len(table_rows(pages[0])) == 4
    assert len(table_rows(pages[1])) == 2


@assert_no_logs
def test_no_row_widows():
    # Default: the break leaves five rows on the first page and one on
    # the second.
    pages = render_pages(
        '<style>' + STYLE % (70, '') + '</style>'
        f'<table>{ROWS}</table>')
    assert len(table_rows(pages[0])) == 5
    assert len(table_rows(pages[1])) == 1


@assert_no_logs
def test_row_orphans():
    # Five rows fit on the first page: the second row group starts there
    # but would leave a single row on this page, so the whole group moves
    # to the next page.
    pages = render_pages(
        '<style>' + STYLE % (75, '-weasy-row-orphans: 2') + '</style>'
        f'<table>{TWO_GROUPS}</table>')
    assert len(table_rows(pages[0])) == 4
    assert len(table_rows(pages[1])) == 4


@assert_no_logs
def test_no_row_orphans():
    # Default: the second row group starts on the first page.
    pages = render_pages(
        '<style>' + STYLE % (75, '') + '</style>'
        f'<table>{TWO_GROUPS}</table>')
    assert len(table_rows(pages[0])) == 5
    assert len(table_rows(pages[1])) == 3
