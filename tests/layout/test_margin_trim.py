"""Test the ``margin-trim`` property."""
from ..testing_utils import assert_no_logs, render_pages


def find_boxes(page, tags):
    return {
        box.element_tag: box for box in page.descendants()
        if getattr(box, 'element_tag', '') in tags
        and hasattr(box, 'margin_height')}


@assert_no_logs
def test_margin_trim_block_top():
    # The first child's top margin is trimmed at the container edge.
    def render(decl):
        page, = render_pages(f'''
          <style>
            @page {{ size: 200px 400px; margin: 0 }}
            section {{ margin-trim: {decl}; overflow: hidden }}
            section p {{ margin: 40px 0 }}
          </style>
          <section><p>text</p></section>
        ''')
        return find_boxes(page, ('section', 'p'))

    plain = render('none')
    assert plain['p'].position_y - plain['section'].content_box_y() == 40
    trimmed = render('block')
    assert (
        trimmed['p'].position_y -
        trimmed['section'].content_box_y()) == 0


@assert_no_logs
def test_margin_trim_block_bottom():
    # The last child's bottom margin is trimmed: the container height
    # excludes it.
    def render(decl):
        page, = render_pages(f'''
          <style>
            @page {{ size: 200px 400px; margin: 0 }}
            section {{ margin-trim: {decl}; overflow: hidden }}
            section p {{ margin: 0 0 40px }}
          </style>
          <section><p>text</p></section>
        ''')
        return find_boxes(page, ('section',))

    assert render('none')['section'].margin_height() > (
        render('block')['section'].margin_height())
