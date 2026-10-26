"""Draw text."""

from io import BytesIO
from xml.etree import ElementTree

from PIL import Image

from ..images import RasterImage, SVGImage
from ..logger import LOGGER
from ..matrix import Matrix
from ..text.ffi import FROM_UNITS, TO_UNITS, ffi, pango
from ..text.fonts import get_hb_object_data
from ..text.line_break import get_last_word_end
from .border import draw_line
from .color import get_color


def draw_text(stream, textbox, offset_x, text_overflow, block_ellipsis):
    """Draw a textbox to a pydyf stream."""
    with stream.overprint_state(textbox.style):
        from ..layout.percent import percentage

        # Pango crashes with font-size: 0.
        assert textbox.style['font_size']

        # Don’t draw invisible textboxes.
        if textbox.style['visibility'] != 'visible':
            return

        # Rebuild the Pango layout, needed to draw the text and to get the
        # glyph positions for skipped decoration ink.
        textbox.pango_layout.reactivate(textbox.style)

        # Draw underline and overline.
        text_decoration_values = textbox.style['text_decoration_line']
        text_decoration_color = get_color(textbox.style, 'text_decoration_color')
        if (
                'underline' in text_decoration_values or
                'overline' in text_decoration_values):
            if textbox.style['text_decoration_thickness'] in ('auto', 'from-font'):
                thickness = textbox.pango_layout.underline_thickness
            else:
                thickness = percentage(
                    textbox.style['text_decoration_thickness'], textbox.style,
                    textbox.style['font_size'])
        if 'overline' in text_decoration_values:
            offset_y = (
                textbox.baseline - textbox.pango_layout.ascent + thickness / 2)
            draw_text_decoration(
                stream, textbox, offset_x, offset_y, thickness,
                text_decoration_color, skip_ink=True)
        if 'underline' in text_decoration_values:
            if textbox.style['text_underline_offset'] == 'auto':
                underline_offset = - textbox.pango_layout.underline_position
            else:
                underline_offset = percentage(
                    textbox.style['text_underline_offset'], textbox.style,
                    textbox.style['font_size'])
            offset_y = textbox.baseline + underline_offset + thickness / 2
            draw_text_decoration(
                stream, textbox, offset_x, offset_y, thickness,
                text_decoration_color, skip_ink=True)

        # Draw text.
        x, y = textbox.position_x, textbox.position_y + textbox.baseline

        # Draw text shadows behind the glyphs (the first shadow in the list is
        # painted on top, so paint in reverse order).
        shadows = textbox.style['text_shadow']
        if shadows != 'none':
            for color, offset_x, offset_y, blur in reversed(shadows):
                if color is None or color == 'currentcolor':
                    color = textbox.style['color']
                if color.alpha == 0:
                    continue
                with stream.stacked():
                    stream.set_color(color)
                    if blur > 0:
                        # Approximate the blur by lowering the opacity (sharp edge).
                        stream.set_alpha(max(0.1, color.alpha / (1 + blur)))
                    stream.begin_text()
                    draw_first_line(
                        stream, textbox, text_overflow, block_ellipsis,
                        Matrix(d=-1, e=x + offset_x, f=y + offset_y))
                    stream.end_text()

        stream.set_color(textbox.style['color'])
        stream.begin_text()
        emojis = draw_first_line(
            stream, textbox, text_overflow, block_ellipsis, Matrix(d=-1, e=x, f=y))
        stream.end_text()

        # Draw emojis.
        draw_emojis(stream, textbox.style, x, y, emojis)

        # Draw line through.
        if 'line-through' in text_decoration_values:
            thickness = textbox.pango_layout.strikethrough_thickness
            offset_y = textbox.baseline - textbox.pango_layout.strikethrough_position
            draw_text_decoration(
                stream, textbox, offset_x, offset_y, thickness, text_decoration_color)
        textbox.pango_layout.deactivate()


def draw_emojis(stream, style, x, y, emojis):
    """Draw list of emojis."""
    font_size = style['font_size']
    for image, font, a, d, e, f in emojis:
        with stream.stacked():
            stream.transform(a=a, d=d, e=x + e * font_size, f=y + f)
            image.draw(stream, font_size, font_size, style)


def draw_first_line(stream, textbox, text_overflow, block_ellipsis, matrix):
    """Draw the given ``textbox`` line to the document ``stream``."""
    # Don’t draw lines with only invisible characters.
    if not textbox.text.strip():
        return []

    if textbox.style['font_size'] < 1e-6:  # default float precision used by pydyf
        return []

    pango.pango_layout_set_single_paragraph_mode(textbox.pango_layout.layout, True)

    if text_overflow == 'ellipsis' or block_ellipsis != 'none':
        assert textbox.pango_layout.max_width is not None
        max_width = textbox.pango_layout.max_width
        pango.pango_layout_set_width(
            textbox.pango_layout.layout, int(max_width * TO_UNITS))
        if text_overflow == 'ellipsis':
            pango.pango_layout_set_ellipsize(
                textbox.pango_layout.layout, pango.PANGO_ELLIPSIZE_END)
        else:
            if block_ellipsis == 'auto':
                ellipsis = '…'
            else:
                assert block_ellipsis[0] == 'string'
                ellipsis = block_ellipsis[1]

            # Remove last word if hyphenated.
            new_text = textbox.pango_layout.text
            if new_text.endswith(textbox.style['hyphenate_character']):
                last_word_end = get_last_word_end(
                    new_text[:-len(textbox.style['hyphenate_character'])],
                    textbox.style['lang'])
                if last_word_end:
                    new_text = new_text[:last_word_end]

            textbox.pango_layout.set_text(new_text + ellipsis)

    first_line, index = textbox.pango_layout.get_first_line()

    if block_ellipsis != 'none':
        while index:
            last_word_end = get_last_word_end(
                textbox.pango_layout.text[:-len(ellipsis)],
                textbox.style['lang'])
            if last_word_end is None:
                break
            new_text = textbox.pango_layout.text[:last_word_end]
            textbox.pango_layout.set_text(new_text + ellipsis)
            first_line, index = textbox.pango_layout.get_first_line()

    utf8_text = textbox.pango_layout.text.encode()
    stream.set_text_matrix(*matrix.values)
    previous_pango_font = None
    string = ''
    x_advance = 0
    emojis = []
    run = first_line.runs[0]
    while run != ffi.NULL:
        # Get Pango objects.
        glyph_item = run.data
        run = run.next
        glyph_string = glyph_item.glyphs
        glyphs_info = glyph_string.glyphs
        number_of_glyphs = glyph_string.num_glyphs
        offset = glyph_item.item.offset
        clusters = glyph_string.log_clusters

        # Get positions of the glyphs in the UTF-8 string.
        utf8_positions = [offset + clusters[i] for i in range(number_of_glyphs)]
        if glyph_item.item.analysis.level % 2:
            utf8_positions.insert(0, offset + glyph_item.item.length)  # rtl
        else:
            utf8_positions.append(offset + glyph_item.item.length)  # ltr

        pango_font = glyph_item.item.analysis.font
        if pango_font != previous_pango_font:
            # Add font file content and get font size.
            previous_pango_font = pango_font
            font, font_size = stream.add_font(pango_font)

            # Workaround for https://gitlab.gnome.org/GNOME/pango/-/issues/530.
            # This is also needed by raster emoji fonts, see #2800.
            if pango.pango_version() < 14802 or font.png:
                font_size = textbox.style['font_size']

            # Go through the run glyphs.
            if string:
                stream.show_text(string)
            string = ''
            stream.set_font_size(font.hash, 1 if font.bitmap else font_size)
        string += '<'
        for i in range(number_of_glyphs):
            glyph_info = glyphs_info[i]
            glyph_id = glyph_info.glyph
            width = glyph_info.geometry.width

            # Display zero-width empty glyph.
            if glyph_id == pango.PANGO_GLYPH_EMPTY:
                string += f'>{-width / font_size}<'
                continue

            # Display .notdef and log warning for missing glyphs.
            if glyph_id & pango.PANGO_GLYPH_UNKNOWN_FLAG:
                codepoint = glyph_id - pango.PANGO_GLYPH_UNKNOWN_FLAG
                LOGGER.warning(
                    '.notdef glyph rendered for Unicode string unsupported by fonts: '
                    f'"{chr(codepoint)}" (U+{codepoint:04X})')
                glyph_id = font.get_unused_glyph_id(codepoint)
                font.widths[glyph_id] = round(width * 1000 * FROM_UNITS / font_size)
                if 0 not in font.widths:
                    # "width" is actually Pango’s get_approximate_char_width. Force
                    # .notdef’s to use this width, even if it’s not the right, as we
                    # want to keep Pango’s layout for next glyphs.
                    font.widths[0] = font.widths[glyph_id]

            # Create mapping between glyphs and Unicode codepoints.
            if glyph_id not in font.to_unicode:
                utf8_slice = slice(*sorted(utf8_positions[i:i+2]))
                font.to_unicode[glyph_id] = utf8_text[utf8_slice].decode()

            # Set horizontal and vertical offsets.
            offset = glyph_info.geometry.x_offset / font_size
            rise = glyph_info.geometry.y_offset / 1000
            if rise:
                if string[-1] == '<':
                    string = string[:-1]
                else:
                    string += '>'
                stream.show_text(string)
                stream.set_text_rise(-rise)
                string = ''
                if offset:
                    string = f'{-offset}'
                string += f'<{glyph_id:02x}>' if font.bitmap else f'<{glyph_id:04x}>'
                stream.show_text(string)
                stream.set_text_rise(0)
                string = '<'
            else:
                if offset:
                    string += f'>{-offset}<'
                string += f'{glyph_id:02x}' if font.bitmap else f'{glyph_id:04x}'

            # Get glyph logical widths.
            if glyph_id in font.widths:
                logical_width = font.widths[glyph_id]
            else:
                pango.pango_font_get_glyph_extents(
                    pango_font, glyph_id, stream.ink_rect, stream.logical_rect)
                logical_width = font.widths[glyph_id] = round(
                    stream.logical_rect.width * 1000 * FROM_UNITS / font_size)

            # Set kerning, word spacing, letter spacing.
            kerning = logical_width + offset - width * 1000 * FROM_UNITS / font_size
            if kerning:
                string += f'>{int(kerning)}<'

            # Create list of emojis.
            if font.svg:
                svg_data = get_hb_object_data(font.hb_face, 'svg', glyph_id)
                if svg_data:
                    # Do as explained in specification
                    # https://learn.microsoft.com/typography/opentype/spec/svg
                    tree = ElementTree.fromstring(svg_data)
                    if tree.get('id') != f'glyph{glyph_id}':
                        defs = ElementTree.Element('defs')
                        for child in list(tree):
                            defs.append(child)
                            tree.remove(child)
                        tree.append(defs)
                        ElementTree.SubElement(
                            tree, 'use', attrib={'href': f'#glyph{glyph_id}'})
                    if 'viewBox' not in tree.attrib:
                        tree.attrib['viewBox'] = f'0 0 {font.upem} {font.upem}'
                    image = SVGImage(tree, None, None, None)
                    a = d = 1
                    emojis.append([image, font, a, d, x_advance, 0])
            elif font.png:
                png_data = get_hb_object_data(font.hb_font, 'png', glyph_id)
                if png_data:
                    pillow_image = Image.open(BytesIO(png_data))
                    image_id = f'{font.hash}{glyph_id}'
                    image = RasterImage(pillow_image, image_id, png_data)
                    d = logical_width / 1000
                    a = pillow_image.width / pillow_image.height * d
                    pango.pango_font_get_glyph_extents(
                        pango_font, glyph_id, stream.ink_rect,
                        stream.logical_rect)
                    f = -stream.logical_rect.y
                    f = f * FROM_UNITS / font_size - font_size
                    emojis.append([image, font, a, d, x_advance, f])

            x_advance += (logical_width + offset - kerning) / 1000

        # Close the last glyphs list, remove if empty.
        if string[-1] == '<':
            string = string[:-1]
        else:
            string += '>'

    # Draw text.
    stream.show_text(string)

    return emojis


def text_decoration_segments(textbox, offset_y, thickness):
    """Return ``(start, width)`` pixel segments of the decoration to draw.

    With ``text-decoration-skip-ink`` set to ``auto``, the ranges where
    glyph ink would intersect the decoration band are skipped.

    """
    if textbox.style['text_decoration_skip_ink'] == 'none':
        return [(textbox.position_x, textbox.width)]
    first_line, _ = textbox.pango_layout.get_first_line()
    # The decoration band, in Pango units below the baseline.
    band_top = (
        (offset_y - textbox.baseline) * TO_UNITS - thickness * TO_UNITS / 2)
    skips = []
    x_advance = 0
    run = first_line.runs[0]
    while run != ffi.NULL:
        glyph_item = run.data
        run = run.next
        glyph_string = glyph_item.glyphs
        glyphs_info = glyph_string.glyphs
        pango_font = glyph_item.item.analysis.font
        for i in range(glyph_string.num_glyphs):
            glyph_info = glyphs_info[i]
            start = x_advance + glyph_info.geometry.x_offset
            x_advance += glyph_info.geometry.width
            glyph = glyph_info.glyph
            if not glyph or glyph & 0x10000000:  # empty or unknown glyph
                continue
            ink = ffi.new('PangoRectangle *')
            pango.pango_font_get_glyph_extents(pango_font, glyph, ink, ffi.NULL)
            if ink.y + ink.height > band_top:
                # The glyph ink reaches into the decoration band.
                skips.append((start + ink.x, ink.width))
    skips.sort()
    merged = []
    for start, width in skips:
        if merged and start <= merged[-1][0] + merged[-1][1]:
            end = max(merged[-1][0] + merged[-1][1], start + width)
            merged[-1] = (merged[-1][0], end - merged[-1][0])
        else:
            merged.append((start, width))
    segments = []
    position = 0
    for start, width in merged:
        start, width = start * FROM_UNITS, width * FROM_UNITS
        if start > position:
            segments.append((position, start - position))
        position = start + width
    if position < textbox.width:
        segments.append((position, textbox.width - position))
    return [
        (textbox.position_x + start, width)
        for start, width in segments]


def draw_text_decoration(stream, textbox, offset_x, offset_y, thickness, color,
                         skip_ink=False):
    """Draw text-decoration of ``textbox`` to a ``pdf.stream.Stream``."""
    if skip_ink:
        segments = text_decoration_segments(textbox, offset_y, thickness)
    else:
        segments = [(textbox.position_x, textbox.width)]
    for segment_x, segment_width in segments:
        if segment_width <= 0:
            continue
        draw_line(
            stream, segment_x, textbox.position_y + offset_y,
            segment_x + segment_width, textbox.position_y + offset_y,
            thickness, textbox.style['text_decoration_style'], color, offset_x)
