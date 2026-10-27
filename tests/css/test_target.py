"""Test the CSS cross references using target-*() functions."""

import re

from ..testing_utils import assert_no_logs, render_pages


@assert_no_logs
def test_target_counter():
    page, = render_pages('''
      <style>
        div:first-child { counter-reset: div }
        div { counter-increment: div }
        #id1::before { content: target-counter('#id4', div) }
        #id2::before { content: 'test ' target-counter('#id1', div) }
        #id3::before { content: target-counter(url(#id4), div, lower-roman) }
        #id4::before { content: target-counter('#id3', div) }
      </style>
      <body>
        <div id="id1"></div>
        <div id="id2"></div>
        <div id="id3"></div>
        <div id="id4"></div>
    ''')
    html, = page.children
    body, = html.children
    div1, div2, div3, div4 = body.children
    before = div1.children[0].children[0].children[0]
    assert before.text == '4'
    before = div2.children[0].children[0].children[0]
    assert before.text == 'test 1'
    before = div3.children[0].children[0].children[0]
    assert before.text == 'iv'
    before = div4.children[0].children[0].children[0]
    assert before.text == '3'


@assert_no_logs
def test_target_counter_attr():
    page, = render_pages('''
      <style>
        div:first-child { counter-reset: div }
        div { counter-increment: div }
        div::before { content: target-counter(attr(data-count), div) }
        #id2::before { content: target-counter(attr(data-count url), div) }
        #id4::before {
          content: target-counter(attr(data-count), div, lower-alpha) }
      </style>
      <body>
        <div id="id1" data-count="#id4"></div>
        <div id="id2" data-count="#id1"></div>
        <div id="id3" data-count="#id2"></div>
        <div id="id4" data-count="#id3"></div>
    ''')
    html, = page.children
    body, = html.children
    div1, div2, div3, div4 = body.children
    before = div1.children[0].children[0].children[0]
    assert before.text == '4'
    before = div2.children[0].children[0].children[0]
    assert before.text == '1'
    before = div3.children[0].children[0].children[0]
    assert before.text == '2'
    before = div4.children[0].children[0].children[0]
    assert before.text == 'c'


@assert_no_logs
def test_target_counters():
    page, = render_pages('''
      <style>
        div:first-child { counter-reset: div }
        div { counter-increment: div }
        #id1-2::before { content: target-counters('#id4-2', div, '.') }
        #id2-1::before { content: target-counters(url(#id3), div, '++') }
        #id3::before {
          content: target-counters('#id2-1', div, '.', lower-alpha) }
        #id4-2::before {
          content: target-counters(attr(data-count, url), div, '') }
      </style>
      <body>
        <div id="id1"><div></div><div id="id1-2"></div></div>
        <div id="id2"><div id="id2-1"></div><div></div></div>
        <div id="id3"></div>
        <div id="id4">
          <div></div><div id="id4-2" data-count="#id1-2"></div>
        </div>
    ''')
    html, = page.children
    body, = html.children
    div1, div2, div3, div4 = body.children
    before = div1.children[1].children[0].children[0].children[0]
    assert before.text == '4.2'
    before = div2.children[0].children[0].children[0].children[0]
    assert before.text == '3'
    before = div3.children[0].children[0].children[0]
    assert before.text == 'b.a'
    before = div4.children[1].children[0].children[0].children[0]
    assert before.text == '12'


@assert_no_logs
def test_target_text():
    page, = render_pages('''
      <style>
        a { display: block; color: red }
        div:first-child { counter-reset: div }
        div { counter-increment: div }
        #id2::before { content: 'wow' }
        #link1::before { content: 'test ' target-text('#id4') }
        #link2::before { content: target-text(attr(data-count, url), before) }
        #link3::before { content: target-text('#id3', after) }
        #link4::before { content: target-text(url(#id1), first-letter) }
      </style>
      <body>
        <a id="link1"></a>
        <div id="id1">1 Chapter 1</div>
        <a id="link2" data-count="#id2"></a>
        <div id="id2">2 Chapter 2</div>
        <div id="id3">3 Chapter 3</div>
        <a id="link3"></a>
        <div id="id4">4 Chapter 4</div>
        <a id="link4"></a>
    ''')
    html, = page.children
    body, = html.children
    a1, div1, a2, div2, div3, a3, div4, a4 = body.children
    before = a1.children[0].children[0].children[0]
    assert before.text == 'test 4 Chapter 4'
    before = a2.children[0].children[0].children[0]
    assert before.text == 'wow'
    assert len(a3.children[0].children[0].children) == 0
    before = a4.children[0].children[0].children[0]
    assert before.text == '1'


@assert_no_logs
def test_target_text_whitespace_around_target():
    # Regression test for #1875.
    page, = render_pages('''
      <style>
        a::before { content: target-text(attr(href)) }
      </style>
      <p>before <a href="#ref"></a> after</p>
      <h2 id="ref">text</h2>
    ''')
    html, = page.children
    body, = html.children
    p, h2 = body.children
    line, = p.children
    before, a, after = line.children
    assert before.text == 'before '
    assert after.text == ' after'
    assert a.children[0].children[0].text == 'text'


@assert_no_logs
def test_target_float():
    page, = render_pages('''
      <style>
        a::after {
          content: target-counter('#h', page);
          float: right;
        }
      </style>
      <div><a id="span">link</a></div>
      <h1 id="h">abc</h1>
    ''')
    html, = page.children
    body, = html.children
    div, h1 = body.children
    line, = div.children
    inline, = line.children
    text_box, after = inline.children
    assert text_box.text == 'link'
    assert after.children[0].children[0].text == '1'


@assert_no_logs
def test_target_absolute():
    page, = render_pages('''
      <style>
        a::after {
          content: target-counter('#h', page);
        }
        div {
          position: absolute;
        }
      </style>
      <div><a id="span">link</a></div>
      <h1 id="h">abc</h1>
    ''')
    html, = page.children
    body, = html.children
    div, h1 = body.children
    line, = div.children
    inline, = line.children
    text_box, after = inline.children
    assert text_box.text == 'link'
    assert after.children[0].text == '1'


@assert_no_logs
def test_target_absolute_non_root():
    page, = render_pages('''
      <style>
        a::after {
          content: target-counter('#h', page);
        }
        section {
          position: relative;
        }
        div {
          position: absolute;
        }
      </style>
      <section><div><a id="span">link</a></div></section>
      <h1 id="h">abc</h1>
    ''')
    html, = page.children
    body, = html.children
    section, h1 = body.children
    div, = section.children
    line, = div.children
    inline, = line.children
    text_box, after = inline.children
    assert text_box.text == 'link'
    assert after.children[0].text == '1'


@assert_no_logs
def test_target_counter_last_and_page_range():
    # -weasy-target-counter-last gives the page counter of the target’s
    # last fragment; -weasy-target-page-range collapses equal ends.
    pages = render_pages('''
      <style>
        @page { size: 200px 100px; margin: 10px }
        body { margin: 0; font-family: weasyprint; font-size: 10px }
        section { break-before: page }
        #toc a::after {
          content: ' ' -weasy-target-page-range(attr(href), '–') }
        #toc2 a::after {
          content: ' ' -weasy-target-counter-last(attr(href), page) }
      </style>
      <div id="toc">
        <a href="#short">short</a>
        <a href="#long">long</a>
      </div>
      <div id="toc2"><a href="#long">last</a></div>
      <section id="short"><p>abc</p></section>
      <section id="long"><p>def</p><div style="height: 150px"></div></section>
    ''')
    # Page 1 has the table of contents, the short section is on page 2
    # and the long section spans pages 3 and 4.
    assert len(pages) == 4
    texts = ' '.join(
        box.text for box in pages[0].descendants()
        if type(box).__name__ == 'TextBox')
    assert re.search(r'short\s+2', texts)
    assert re.search(r'long\s+3–4', texts)
    assert re.search(r'last\s+4', texts)


@assert_no_logs
def test_target_page_range_remade_first_page():
    # A reference whose target-counter sits on the target’s first page
    # makes that page be laid out again. The range must keep the last
    # page cached for the target’s later fragments.
    def assert_range_matches_span(pages):
        texts = ' '.join(
            box.text for box in pages[0].descendants()
            if type(box).__name__ == 'TextBox')
        section_pages = [
            i for i, page in enumerate(pages, 1)
            if any(getattr(box, 'element_tag', '') == 'section'
                   for box in page.descendants())]
        first, last = section_pages[0], section_pages[-1]
        if first == last:
            expected = r'long\s+%d' % first
        else:
            expected = r'long\s+%d–%d' % (first, last)
        assert re.search(expected, texts)

    markup = '''
      <div id="toc"><a href="#long">long</a></div>
      <section id="long">
        <p><a class="pg" href="#x">see</a></p>
        <p>def</p><div style="height: 150px"></div>
        <p id="x">x</p>
      </section>
    '''

    # The reference forwards from the target’s first page (page 2).
    pages = render_pages('''
      <style>
        @page { size: 200px 100px; margin: 10px }
        body { margin: 0; font-family: weasyprint; font-size: 10px }
        p { margin: 0 }
        section { break-before: page }
        #toc a::after {
          content: ' ' -weasy-target-page-range(attr(href), '–') }
        a.pg::after { content: ' p. ' target-counter(attr(href), page) }
      </style>
    ''' + markup)
    assert_range_matches_span(pages)

    # Same with the target starting on the referencing element’s own
    # page: that page is always laid out again to resolve the reference.
    pages = render_pages('''
      <style>
        @page { size: 200px 100px; margin: 10px }
        body { margin: 0; font-family: weasyprint; font-size: 10px }
        p { margin: 0 }
        #toc a::after {
          content: ' ' -weasy-target-page-range(attr(href), '–') }
        a.pg::after { content: ' p. ' target-counter(attr(href), page) }
      </style>
    ''' + markup)
    assert_range_matches_span(pages)
