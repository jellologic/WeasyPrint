"""Test ``vector-effect: non-scaling-stroke`` in SVG images."""
import re

from ...testing_utils import FakeHTML, assert_no_logs


def stroke_widths(body):
    html = f'''
      <style>@page {{ size: 100px 100px; margin: 0 }}</style>
      <svg width="{body[0]}" viewBox="0 0 100 100">
        <line x1="0" y1="50" x2="100" y2="50"
              stroke="black" stroke-width="1" {body[1]}/>
      </svg>
    '''
    pdf = FakeHTML(string=html).write_pdf(uncompressed_pdf=True)
    return [float(value) for value in re.findall(rb'([0-9.]+) w\n', pdf)]


@assert_no_logs
def test_non_scaling_stroke():
    # A stroke in a half-size SVG with non-scaling-stroke is emitted with
    # a doubled line width, so that it prints at the specified weight.
    full = stroke_widths((100, ''))
    half = stroke_widths((50, 'vector-effect="non-scaling-stroke"'))
    assert 1 in full
    assert 2 in half
