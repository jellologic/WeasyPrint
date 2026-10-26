"""Test the ``initial-letter`` property."""

from ..testing_utils import assert_no_logs, render_pages


def get_boxes(page, tag):
    return [
        box for box in page.descendants()
        if type(box).__name__ == 'BlockBox' and box.element_tag == tag]


@assert_no_logs
def test_initial_letter():
    # A 3-line initial letter is enlarged to the height of three lines and
    # floated; the following lines wrap beside it.
    page, = render_pages('''
      <style>
        @page { size: 200px 200px; margin: 10px }
        body { font-family: weasyprint; font-size: 10px; line-height: 20px }
        p { margin: 0 }
        p::first-letter { initial-letter: 3 }
      </style>
      <p>abc def ghi jkl mno pqr</p>
    ''')
    letter_box, = get_boxes(page, 'p::first-letter')
    assert letter_box.style['float'] == 'left'
    assert letter_box.style['initial_letter'] == (3, 3)
    # The font size spans three 20px lines.
    assert letter_box.style['font_size'] == 60
    assert letter_box.height >= 60

    # The second line of the paragraph is pushed beside the float.
    line_boxes = [
        box for box in page.descendants()
        if type(box).__name__ == 'LineBox' and box.element_tag == 'p']
    assert len(line_boxes) >= 2
    second_line = line_boxes[1]
    assert second_line.position_x > 10


@assert_no_logs
def test_initial_letter_normal():
    page, = render_pages('''
      <style>
        @page { size: 300px 200px; margin: 10px }
        body { font-family: weasyprint; font-size: 10px }
        p { margin: 0 }
        p::first-letter { initial-letter: normal }
      </style>
      <p>abc def ghi jkl mno pqr</p>
    ''')
    assert get_boxes(page, 'p::first-letter') == []
    line_boxes = [
        box for box in page.descendants()
        if type(box).__name__ == 'LineBox' and box.element_tag == 'p']
    assert line_boxes[0].position_x == 10


@assert_no_logs
def test_initial_letter_sink():
    # The sink defaults to the size and is clamped to it.
    page, = render_pages('''
      <style>
        @page { size: 300px 200px; margin: 10px }
        body { font-family: weasyprint; font-size: 10px }
        p { margin: 0 }
        p::first-letter { initial-letter: 3 1 }
        p + p::first-letter { initial-letter: 2 5 }
      </style>
      <p>abc def</p>
      <p>abc def</p>
    ''')
    letter_boxes = get_boxes(page, 'p::first-letter')
    assert len(letter_boxes) == 2
    assert letter_boxes[0].style['initial_letter'] == (3, 1)
    assert letter_boxes[1].style['initial_letter'] == (2, 2)
