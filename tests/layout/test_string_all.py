"""Test the non-standard ``string(name, all)`` running heads."""
from weasyprint.formatting_structure import boxes

from ..testing_utils import assert_no_logs, render_pages


def page_text(page):
    return ' '.join(
        child.text.strip() for child in page.descendants()
        if isinstance(child, boxes.TextBox) and child.text.strip())


@assert_no_logs
def test_string_all():
    # string(name, all, separator) joins the value carried from the
    # previous pages with every value assigned on the page.
    pages = render_pages('''
      <style>
        body { font-family: weasyprint; font-size: 12pt }
        h1 { string-set: section content(); margin: 0 }
        section { page-break-before: always }
        @page { @top-left { content: string(section, all, " · ") } }
      </style>
      <h1>Alpha</h1>
      <section></section>
      <h1>Beta</h1>
      <h1>Gamma</h1>
    ''')
    assert len(pages) >= 2
    assert 'Alpha' in page_text(pages[0])
    assert 'Alpha · Beta · Gamma' in page_text(pages[1])


@assert_no_logs
def test_string_all_default_separator():
    # Without a separator argument, values are joined with a space.
    pages = render_pages('''
      <style>
        body { font-family: weasyprint; font-size: 12pt }
        h1 { string-set: section content(); margin: 0 }
        @page { @top-left { content: string(section, all) } }
      </style>
      <h1>Alpha</h1>
      <h1>Beta</h1>
    ''')
    assert 'Alpha Beta' in page_text(pages[0])
