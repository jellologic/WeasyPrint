"""Test size container queries."""

from ..testing_utils import assert_no_logs, render_pages


def find_card(page, card_id):
    """Return the box of the card with the given id."""
    for box in page.descendants():
        element = getattr(box, 'element', None)
        if element is not None and element.get('id') == card_id:
            return box


HTML = '''
  <style>
    @page { size: 400px 100px; margin: 0 }
    body { margin: 0; font-family: weasyprint; font-size: 10px }
    .slot { container-type: inline-size }
    .half { width: 50%% }
    .quarter { width: 25%% }
    %s
  </style>
  <div class="slot half"><div class="card" id="ca">a</div></div>
  <div class="slot quarter"><div class="card" id="cb">b</div></div>
'''


@assert_no_logs
def test_container_query_min_width():
    # The half-width slot is 200px wide: the rule applies. The
    # quarter-width slot is 100px: it does not.
    page, = render_pages(
        HTML % '@container (min-width: 150px) { .card { border: 2px solid } }')
    assert find_card(page, 'ca').style['border_left_width'] == 2
    assert find_card(page, 'cb').style['border_left_width'] == 0


@assert_no_logs
def test_container_query_max_width():
    page, = render_pages(
        HTML % '@container (max-width: 150px) { .card { border: 2px solid } }')
    assert find_card(page, 'ca').style['border_left_width'] == 0
    assert find_card(page, 'cb').style['border_left_width'] == 2


@assert_no_logs
def test_container_query_named():
    # The rule targets the container named "wide" only, even when another
    # container would satisfy the condition.
    page, = render_pages('''
      <style>
        @page { size: 400px 100px; margin: 0 }
        body { margin: 0; font-family: weasyprint; font-size: 10px }
        .slot { container-type: inline-size }
        .named { container-name: wide }
        .half { width: 50% }
        .quarter { width: 25% }
        @container wide (min-width: 50px) { .card { border: 2px solid } }
      </style>
      <div class="slot half"><div class="card" id="ca">a</div></div>
      <div class="slot named quarter"><div class="card" id="cb">b</div></div>
    ''')
    assert find_card(page, 'ca').style['border_left_width'] == 0
    assert find_card(page, 'cb').style['border_left_width'] == 2


@assert_no_logs
def test_container_query_display():
    # Matched declarations can change the display: the card disappears in
    # the narrow slot.
    page, = render_pages(
        HTML % '@container (max-width: 150px) { .card { display: none } }')
    assert find_card(page, 'ca') is not None
    assert find_card(page, 'cb') is None


@assert_no_logs
def test_container_query_no_container():
    # Without a matching container the rule is not applied.
    page, = render_pages('''
      <style>
        @page { size: 400px 100px; margin: 0 }
        body { margin: 0 }
        @container (min-width: 150px) { .card { border: 2px solid } }
      </style>
      <div><div class="card" id="ca">a</div></div>
    ''')
    assert find_card(page, 'ca').style['border_left_width'] == 0


@assert_no_logs
def test_container_query_range_syntax():
    # MQ-style range syntax: (width >= …), (… <= width) and clamped bands.
    page, = render_pages('''
      <style>
        @page { size: 400px 100px; margin: 0 }
        body { margin: 0; font-family: weasyprint; font-size: 10px }
        .slot { container-type: inline-size }
        .half { width: 50% }
        .quarter { width: 25% }
        @container (width >= 150px) { .a { border: 2px solid } }
        @container (100px < width) { .b { border: 2px solid } }
        @container (100px < width < 150px) { .c { border: 2px solid } }
      </style>
      <div class="slot half">
        <div class="card a" id="ca">a</div>
        <div class="card b" id="cb">b</div>
        <div class="card c" id="cc">c</div>
      </div>
      <div class="slot quarter">
        <div class="card a" id="da">a</div>
        <div class="card b" id="db">b</div>
        <div class="card c" id="dc">c</div>
      </div>
    ''')
    # The half slot is 200px wide, the quarter slot 100px.
    assert find_card(page, 'ca').style['border_left_width'] == 2
    assert find_card(page, 'da').style['border_left_width'] == 0
    assert find_card(page, 'cb').style['border_left_width'] == 2
    assert find_card(page, 'db').style['border_left_width'] == 0
    # The open band excludes both slots (200 >= 150 and 100 <= 100).
    assert find_card(page, 'cc').style['border_left_width'] == 0
    assert find_card(page, 'dc').style['border_left_width'] == 0


@assert_no_logs
def test_container_units():
    # cqw resolves against the nearest container's inline size; elements
    # with no container ancestor resolve to 0.
    page, = render_pages('''
      <style>
        @page { size: 400px 100px; margin: 0 }
        body { margin: 0; font-family: weasyprint; font-size: 10px }
        .half { width: 50%; container-type: inline-size }
        .pad { padding-left: 10cqw }
        #out { padding-left: 2cqw }
      </style>
      <div class="half"><div class="pad" id="in">a</div></div>
      <div class="pad" id="out">b</div>
    ''')
    inside = find_card(page, 'in')
    outside = find_card(page, 'out')
    # 10cqw of the 200px container.
    assert inside.style['padding_left'] == (20, 'px')
    # No container ancestor: falls back to the page content width
    # (2cqw of 400px).
    assert outside.style['padding_left'] == (8, 'px')


@assert_no_logs
def test_container_style_query():
    # Style queries match the container's custom-property declarations.
    page, = render_pages('''
      <style>
        @page { size: 400px 100px; margin: 0 }
        body { margin: 0; font-family: weasyprint; font-size: 10px }
        .c { --theme: dark }
        .c2 { --theme: light }
        @container style(--theme: dark) { .card { border: 2px solid } }
      </style>
      <div class="c"><div class="card" id="ca">a</div></div>
      <div class="c2"><div class="card" id="cb">b</div></div>
    ''')
    dark = find_card(page, 'ca')
    light = find_card(page, 'cb')
    assert dark.style['border_left_width'] == 2
    assert light.style['border_left_width'] == 0


@assert_no_logs
def test_container_query_height_units():
    # cqh resolves against the page area height (inline-size containers
    # don't expose a queryable block size).
    page, = render_pages('''
      <style>
        @page { size: 400px 100px; margin: 0 }
        body { margin: 0; font-family: weasyprint; font-size: 10px }
        .half { width: 50%; container-type: inline-size }
        .pad { padding-top: 10cqh }
      </style>
      <div class="half"><div class="pad" id="in">a</div></div>
    ''')
    inside = find_card(page, 'in')
    # 10cqh of the 100px page area height.
    assert inside.style['padding_top'] == (10, 'px')


@assert_no_logs
def test_container_style_query_computed():
    # Style queries on computed properties: display: flex matches the
    # flex container, not the block one.
    page, = render_pages('''
      <style>
        @page { size: 400px 100px; margin: 0 }
        body { margin: 0; font-family: weasyprint; font-size: 10px }
        .flex { display: flex; container-type: inline-size }
        .block { display: block; container-type: inline-size }
        @container style(display: flex) { .card { border: 2px solid } }
      </style>
      <div class="flex"><div class="card" id="ca">a</div></div>
      <div class="block"><div class="card" id="cb">b</div></div>
    ''')
    flex = find_card(page, 'ca')
    block = find_card(page, 'cb')
    assert flex.style['border_left_width'] == 2
    assert block.style['border_left_width'] == 0


@assert_no_logs
def test_container_query_cqh_size_container():
    # cqh resolves against a size container's block height.
    page, = render_pages('''
      <style>
        @page { size: 400px 100px; margin: 0 }
        body { margin: 0; font-family: weasyprint; font-size: 10px }
        .box { height: 100px; container-type: size }
        .pad { padding-top: 10cqh }
      </style>
      <div class="box"><div class="pad" id="in">a</div></div>
    ''')
    inside = find_card(page, 'in')
    # 10cqh of the 100px size container.
    assert inside.style['padding_top'] == (10, 'px')


@assert_no_logs
def test_container_style_query_container_excluded():
    # Style queries do not match the queried container itself: the rule
    # targets the container's own class but applies only to descendants.
    page, = render_pages('''
      <style>
        @page { size: 400px 100px; margin: 0 }
        body { margin: 0; font-family: weasyprint; font-size: 10px }
        .c { --theme: dark; container-type: inline-size }
        @container style(--theme: dark) { .c { border: 2px solid } }
      </style>
      <div class="c">x</div>
    ''')
    html, = page.children
    body, = html.children
    container, = body.children
    assert container.style['border_left_width'] == 0


@assert_no_logs
def test_container_shorthand():
    # The container shorthand sets both the name and the type.
    page, = render_pages('''
      <style>
        @page { size: 400px 100px; margin: 0 }
        body { margin: 0; font-family: weasyprint; font-size: 10px }
        .slot { container: wide / inline-size }
        .narrow { container: narrow / inline-size }
        .half { width: 50% }
        .quarter { width: 25% }
        @container wide (min-width: 50px) { .card { border: 2px solid } }
      </style>
      <div class="slot half"><div class="card" id="ca">a</div></div>
      <div class="slot narrow quarter"><div class="card" id="cb">b</div></div>
    ''')
    # The rule targets the container named "wide": the quarter slot
    # satisfies the width but has no matching name.
    assert find_card(page, 'ca').style['border_left_width'] == 2
    assert find_card(page, 'cb').style['border_left_width'] == 0


@assert_no_logs
def test_container_shorthand_bare_type():
    # A bare type keyword in the shorthand names no container.
    page, = render_pages('''
      <style>
        @page { size: 400px 100px; margin: 0 }
        body { margin: 0; font-family: weasyprint; font-size: 10px }
        .slot { container: inline-size }
        .half { width: 50% }
        .quarter { width: 25% }
        @container (min-width: 150px) { .card { border: 2px solid } }
      </style>
      <div class="slot half"><div class="card" id="ca">a</div></div>
      <div class="slot quarter"><div class="card" id="cb">b</div></div>
    ''')
    assert find_card(page, 'ca').style['border_left_width'] == 2
    assert find_card(page, 'cb').style['border_left_width'] == 0


@assert_no_logs
def test_container_query_pt_lengths():
    # Lengths in the query are converted: 300pt is 400px, so a 255pt
    # (340px) container matches both bounds.
    for query in ('(width < 400px)', '(max-width: 400px)',
                  '(width < 300pt)', '(min-width: 100px)'):
        page, = render_pages('''
          <style>
            @page { size: 600px 100px; margin: 0 }
            body { margin: 0 }
            .slot { width: 255pt; container-type: inline-size }
            .card { color: black }
            @container %s { .card { color: red } }
          </style>
          <div class="slot"><p class="card">x</p></div>
        ''' % query)
        card = next(
            box for box in page.descendants()
            if getattr(box, 'element_tag', '') == 'p')
        assert card.style['color'] == (1, 0, 0, 1), query


@assert_no_logs
def test_container_query_inherited_properties():
    # Inherited declarations (color) from a matching container rule apply
    # like non-inherited ones (border-left), overriding a base rule of
    # the same specificity.
    page, = render_pages('''
      <style>
        @page { size: 600px 100px; margin: 0 }
        body { margin: 0 }
        .slot { width: 255pt; container-type: inline-size }
        .card { color: black }
        @container (width < 400px) {
          .card { color: red; border-left: 2px solid }
        }
      </style>
      <div class="slot"><p class="card" id="target">x</p></div>
    ''')
    card = next(
        box for box in page.descendants()
        if getattr(box, 'element_tag', '') == 'p')
    assert card.style['color'] == (1, 0, 0, 1)
    assert card.style['border_left_width'] == 2


@assert_no_logs
def test_container_query_grid_item():
    # A container that is a grid item is sized by its tracks: span 6 of
    # 12 in a 525pt grid is 350px wide.
    def page_for(grid_extra=''):
        pages = render_pages('''
          <style>
            @page { size: 600px 100px; margin: 0 }
            body { margin: 0 }
            .grid { display: grid; grid-template-columns: repeat(12, 1fr);
                    width: 525pt %s }
            .slot { container-type: inline-size }
            .card { color: black }
            @container (width < 400px) { .card { color: red } }
          </style>
          <div class="grid">
            <div class="slot" style="grid-column: span 6">
              <p class="card">x</p>
            </div>
          </div>
        ''' % grid_extra)
        return next(
            box for box in pages[0].descendants()
            if getattr(box, 'element_tag', '') == 'p')

    assert page_for().style['color'] == (1, 0, 0, 1)
    # Narrower bound: the 350px item does not match.
    pages = render_pages('''
      <style>
        @page { size: 600px 100px; margin: 0 }
        body { margin: 0 }
        .grid { display: grid; grid-template-columns: repeat(12, 1fr);
                width: 525pt }
        .slot { container-type: inline-size }
        .card { color: black }
        @container (width < 300px) { .card { color: red } }
      </style>
      <div class="grid">
        <div class="slot" style="grid-column: span 6"><p class="card">x</p></div>
      </div>
    ''')
    card = next(
        box for box in pages[0].descendants()
        if getattr(box, 'element_tag', '') == 'p')
    assert card.style['color'] == (0, 0, 0, 1)


@assert_no_logs
def test_container_query_definite_track():
    # A container in a definite 255pt track is 340px wide.
    page, = render_pages('''
      <style>
        @page { size: 600px 100px; margin: 0 }
        body { margin: 0 }
        .grid { display: grid; grid-template-columns: 255pt;
                width: 525pt }
        .slot { container-type: inline-size }
        .card { color: black }
        @container (width < 400px) { .card { color: red } }
      </style>
      <div class="grid">
        <div class="slot"><p class="card">x</p></div>
      </div>
    ''')
    card = next(
        box for box in page.descendants()
        if getattr(box, 'element_tag', '') == 'p')
    assert card.style['color'] == (1, 0, 0, 1)


@assert_no_logs
def test_container_query_flex_item():
    # A flex item with a definite width is determinable.
    page, = render_pages('''
      <style>
        @page { size: 600px 100px; margin: 0 }
        body { margin: 0 }
        .row { display: flex; width: 600px }
        .slot { width: 255pt; container-type: inline-size }
        .card { color: black }
        @container (width < 400px) { .card { color: red } }
      </style>
      <div class="row">
        <div class="slot"><p class="card">x</p></div>
      </div>
    ''')
    card = next(
        box for box in page.descendants()
        if getattr(box, 'element_tag', '') == 'p')
    assert card.style['color'] == (1, 0, 0, 1)
