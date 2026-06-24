"""Tests for Separation (spot) colors via @color-profile -weasy-separation."""

from ..testing_utils import FakeHTML, assert_no_logs

CSS = (
    '@color-profile --gold { '
    '-weasy-separation: "PANTONE 871 C" device-cmyk(0% 17% 60% 24%) }')


@assert_no_logs
def test_separation_color_space():
    pdf = FakeHTML(string=(
        f'<style>{CSS} p {{ color: color(--gold 0.6) }}</style><p>x</p>'
    )).write_pdf(uncompressed_pdf=True)
    # A Separation color space with the (escaped) ink name and a CMYK alternate.
    assert b'/Separation /PANTONE#20871#20C /DeviceCMYK' in pdf
    # Tint transform from no ink to the full-tint CMYK values.
    assert b'/C1 [0 0.17 0.6 0.24]' in pdf
    # The 0.6 tint is set with a Separation color operator.
    assert b'0.6 scn' in pdf


@assert_no_logs
def test_no_separation_when_unused():
    pdf = FakeHTML(string='<p style="color: red">x</p>').write_pdf(
        uncompressed_pdf=True)
    assert b'/Separation' not in pdf
