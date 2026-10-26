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
