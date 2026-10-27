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


@assert_no_logs
def test_row_widows_column_break_with_avoid():
    # Row widows hold at a column break even when the rows carry
    # break-inside: avoid: an avoid removes break opportunities, it
    # never re-allows one that widows forbids.
    rows = ''.join(f'<tr><td>row{index}</td></tr>' for index in range(8))
    page, = render_pages('''
      <style>
        @page { size: 400px 500px; margin: 10px }
        body { margin: 0; font-size: 10px; line-height: 15px }
        td { height: 15px; padding: 0 }
        .flow { columns: 2; column-gap: 15px }
        table { border-collapse: collapse; width: 100%%;
                -weasy-row-orphans: 3; -weasy-row-widows: 3 }
        tr { break-inside: avoid }
      </style>
      <div class="flow">
        <table><tbody><tr><td>head</td></tr>%s</tbody></table>
      </div>
    ''' % rows)
    # Body rows per column, counted by their cell text.
    columns = {}
    for box in page.descendants():
        if (type(box).__name__ == 'TextBox' and
                box.text.startswith('row')):
            column = 0 if box.position_x < 195 else 1
            columns.setdefault(column, 0)
            columns[column] += 1
    # The last column keeps at least -weasy-row-widows body rows
    # (without the avoid rules the balance leaves 2).
    assert columns[0] + columns[1] == 8
    assert 3 <= columns[0] <= 5
    assert columns[1] >= 3
