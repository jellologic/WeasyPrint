"""Test extra PDF form field attributes."""

from .testing_utils import FakeHTML, assert_no_logs


def render_form(html):
    return FakeHTML(
        string='''
          <style>
            @page { size: 6in 4in; margin: 0.5in }
            body { font-size: 10pt }
          </style>
        ''' + html).write_pdf(pdf_forms=True, uncompressed_pdf=True)


@assert_no_logs
def test_form_tooltip():
    pdf = render_form(
        '<input name="a" title="Submitted by">'
        '<input name="b" aria-label="Catalog number">')
    assert b'(Submitted by)' in pdf
    assert b'(Catalog number)' in pdf


@assert_no_logs
def test_form_readonly_required():
    pdf = render_form(
        '<textarea name="a" readonly maxlength="10"></textarea>'
        '<input name="b" required>')
    # textarea: multiline bit (1 << 12) + readonly bit (1)
    assert b'/Ff 4097' in pdf
    # required-only text field: bit 2
    assert b'/Ff 2' in pdf


@assert_no_logs
def test_form_alignment():
    pdf = render_form(
        '<input name="a" style="text-align: right">'
        '<input name="b" style="text-align: center">'
        '<input name="c">')
    assert b'/Q 2' in pdf
    assert b'/Q 1' in pdf
    assert b'/Q 0' not in pdf


@assert_no_logs
def test_form_comb():
    pdf = render_form(
        '<input name="a" maxlength="8" style="comb: true">'
        '<input name="b" maxlength="8">')
    # comb bit (1 << 24) on the field with the property
    assert b'/Ff 16777216' in pdf


@assert_no_logs
def test_form_date():
    pdf = render_form('<input name="a" type="date">')
    assert b'/AA' in pdf
    assert b'/JavaScript' in pdf
    assert b'AFDate_FormatEx' in pdf
    assert b'AFDate_KeystrokeEx' in pdf


@assert_no_logs
def test_form_radio_group_tooltip():
    pdf = render_form(
        '<input type="radio" name="r" title="Choose one">')
    assert b'(Choose one)' in pdf
