"""Test the proprietary ``overprint`` properties."""
from ..testing_utils import FakeHTML, assert_no_logs


@assert_no_logs
def test_overprint_all():
    pdf = FakeHTML(string='''
      <style>
        @page { size: 100px 100px }
        div { -weasy-overprint: all; background: black; height: 50px }
      </style>
      <div></div>
    ''').write_pdf(uncompressed_pdf=True)
    assert b'/OP true' in pdf
    assert b'/op true' in pdf


@assert_no_logs
def test_overprint_fill_only():
    pdf = FakeHTML(string='''
      <style>
        @page { size: 100px 100px }
        div { overprint: fill; background: black; height: 50px }
      </style>
      <div></div>
    ''').write_pdf(uncompressed_pdf=True)
    assert b'/op true' in pdf
    assert b'/OP true' not in pdf


@assert_no_logs
def test_overprint_mode():
    pdf = FakeHTML(string='''
      <style>
        @page { size: 100px 100px }
        div { -weasy-overprint: all; -weasy-overprint-mode: 1;
              background: black; height: 50px }
      </style>
      <div></div>
    ''').write_pdf(uncompressed_pdf=True)
    assert b'/OPM 1' in pdf


@assert_no_logs
def test_overprint_off():
    pdf = FakeHTML(string='''
      <style>
        @page { size: 100px 100px }
        div { background: black; height: 50px }
      </style>
      <div></div>
    ''').write_pdf(uncompressed_pdf=True)
    assert b'/OP true' not in pdf
    assert b'/op true' not in pdf


@assert_no_logs
def test_overprint_text():
    pdf = FakeHTML(string='''
      <style>
        @page { size: 100px 100px }
        p { -weasy-overprint: all; color: black }
      </style>
      <p>overprinted text</p>
    ''').write_pdf(uncompressed_pdf=True)
    assert b'/op true' in pdf
