"""Layout for floating boxes."""

from math import cos, inf, pi, sin

from ..formatting_structure import boxes
from .min_max import handle_min_max_width
from .percent import resolve_percentages, resolve_position_percentages
from .preferred import shrink_to_fit
from .replaced import inline_replaced_box_width_height
from .table import table_wrapper_width


@handle_min_max_width
def float_width(box, context, containing_block):
    # Check that box.width is auto even if the caller does it too, because
    # the handle_min_max_width decorator can change the value
    if box.width == 'auto':
        box.width = shrink_to_fit(context, box, containing_block.width)


def float_layout(context, box, containing_block, absolute_boxes, fixed_boxes,
                 bottom_space, skip_stack):
    """Set the width and position of floating ``box``."""
    from .block import block_container_layout
    from .flex import flex_layout
    from .grid import grid_layout

    cb_width, cb_height = (containing_block.width, containing_block.height)
    resolve_percentages(box, (cb_width, cb_height))

    # TODO: This is only handled later in blocks.block_container_layout
    # https://www.w3.org/TR/CSS21/visudet.html#normal-block
    if cb_height == 'auto':
        cb_height = containing_block.position_y - containing_block.content_box_y()

    resolve_position_percentages(box, (cb_width, cb_height))

    if box.margin_left == 'auto':
        box.margin_left = 0
    if box.margin_right == 'auto':
        box.margin_right = 0
    if box.margin_top == 'auto':
        box.margin_top = 0
    if box.margin_bottom == 'auto':
        box.margin_bottom = 0

    clearance = get_clearance(context, box, containing_block.style['direction'])
    if clearance is not None:
        box.position_y += clearance

    if isinstance(box, boxes.BlockReplacedBox):
        inline_replaced_box_width_height(box, containing_block)
    elif box.width == 'auto':
        float_width(box, context, containing_block)

    if box.is_table_wrapper:
        table_wrapper_width(context, box, (cb_width, cb_height))

    if isinstance(box, boxes.BlockContainerBox):
        box, resume_at, _, _, _, _ = block_container_layout(
            context, box, bottom_space=bottom_space, skip_stack=skip_stack,
            page_is_empty=True, absolute_boxes=absolute_boxes, fixed_boxes=fixed_boxes,
            adjoining_margins=None, first_letter_style=None, first_line_style=None,
            discard=False, max_lines=None)
    elif isinstance(box, boxes.FlexContainerBox):
        box, resume_at, _, _, _ = flex_layout(
            context, box, bottom_space=bottom_space,
            skip_stack=skip_stack, containing_block=containing_block,
            page_is_empty=True, absolute_boxes=absolute_boxes,
            fixed_boxes=fixed_boxes, discard=False)
    elif isinstance(box, boxes.GridContainerBox):
        box, resume_at, _, _, _ = grid_layout(
            context, box, bottom_space=bottom_space,
            skip_stack=skip_stack, containing_block=containing_block,
            page_is_empty=True, absolute_boxes=absolute_boxes,
            fixed_boxes=fixed_boxes)
    else:
        assert isinstance(box, boxes.BlockReplacedBox)
        resume_at = None

    if box.style['float'] == 'bottom':
        # Bottom page floats are positioned at the bottom of the page by
        # the page layout.
        resume_at = None
        return box, resume_at
    box = find_float_position(context, box, containing_block)

    # shape-outside: attach the wrapping polygon to the float, used by
    # avoid_collisions instead of the border rectangle.
    shape = box.style['shape_outside']
    if shape != 'none':
        points = basic_shape_points(
            shape, box.border_width(), box.border_height())
        if points:
            margin = box.style['shape_margin']
            if getattr(margin, 'unit', None) == '%':
                margin = margin.value * containing_block.width / 100
            elif not isinstance(margin, (int, float)):
                margin = margin.value
            if margin:
                points = expand_polygon(points, margin)
            box.shape_points = points

    context.excluded_shapes.append(box)
    return box, resume_at


def find_float_position(context, box, containing_block):
    """Get the right position of the float ``box``."""
    # See https://www.w3.org/TR/CSS2/visuren.html#float-position

    # Point 4 is already handled as box.position_y is set according to the
    # containing box top position, with collapsing margins handled

    # Points 5 and 6, box.position_y is set to the highest position_y possible
    if context.excluded_shapes:
        highest_y = context.excluded_shapes[-1].position_y
        if box.position_y < highest_y:
            box.translate(0, highest_y - box.position_y)

    # Points 1 and 2
    position_x, position_y, available_width = avoid_collisions(
        context, box, containing_block)

    # Point 9
    # position_y is set now, let's define position_x
    # for float: left elements, it's already done!
    float_right = (
        box.style['float'] == 'right' or
        (box.style['direction'] == 'ltr' and box.style['float'] == 'inline-end') or
        (box.style['direction'] == 'rtl' and box.style['float'] == 'inline-start'))
    if float_right:
        position_x += available_width - box.margin_width()

    box.translate(position_x - box.position_x, position_y - box.position_y)

    return box


def _shape_length(value, reference):
    """Resolve one basic-shape length against a reference size."""
    if getattr(value, 'unit', None) == '%':
        return value.value / 100 * reference
    if isinstance(value, (int, float)):
        return value
    return value.value


def basic_shape_points(shape, width, height):
    """Return the polygon points of a basic shape in box coordinates.

    ``width`` and ``height`` are the reference box sizes.

    """
    type_ = shape[0]
    if type_ == 'polygon':
        _, _fill_rule, points = shape
        return [
            (_shape_length(x, width), _shape_length(y, height))
            for x, y in points]
    if type_ == 'inset':
        _, (top, right, bottom, left) = shape
        top = _shape_length(top, height)
        right = _shape_length(right, width)
        bottom = _shape_length(bottom, height)
        left = _shape_length(left, width)
        return [
            (left, top), (width - right, top),
            (width - right, height - bottom), (left, height - bottom)]
    if type_ in ('circle', 'ellipse'):
        _, radii, (px, py) = shape
        if type_ == 'circle':
            # Validation holds a single bare radius for circles.
            radii = (radii,)
        center_x = _shape_length(px, width)
        center_y = _shape_length(py, height)

        def radius(value, reference, closest, farthest):
            if value == 'closest-side':
                return closest
            if value == 'farthest-side':
                return farthest
            # Percentages resolve against sqrt(width² + height²) / sqrt(2).
            diagonal = (width ** 2 + height ** 2) ** 0.5
            return _shape_length(value, diagonal / 2 ** 0.5)

        if type_ == 'circle':
            rx = ry = radius(
                radii[0], width,
                min(center_x, width - center_x, center_y, height - center_y),
                max(center_x, width - center_x, center_y, height - center_y))
        else:
            rx = radius(
                radii[0], width,
                min(center_x, width - center_x),
                max(center_x, width - center_x))
            ry = radius(
                radii[1], height,
                min(center_y, height - center_y),
                max(center_y, height - center_y))
        return [
            (center_x + rx * cos(2 * pi * i / 32),
             center_y + ry * sin(2 * pi * i / 32))
            for i in range(32)]
    return None


def expand_polygon(points, margin):
    """Offset the polygon edges outward by ``margin``.

    Each new vertex is the intersection of the two offset edges adjacent
    to the original one (miter offset).

    """
    count = len(points)
    # Signed area (positive when the points are clockwise in the y-down
    # coordinate system).
    area = sum(
        points[i][0] * points[(i + 1) % count][1] -
        points[(i + 1) % count][0] * points[i][1]
        for i in range(count))
    flip = -1 if area < 0 else 1

    def offset_edge(a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = (dx ** 2 + dy ** 2) ** 0.5 or 1
        normal = (flip * dy / length, -flip * dx / length)
        return (
            (a[0] + normal[0] * margin, a[1] + normal[1] * margin),
            (dx / length, dy / length))

    offset_edges = [
        offset_edge(points[i], points[(i + 1) % count])
        for i in range(count)]
    new_points = []
    for i in range(count):
        (a1, d1), (a2, d2) = offset_edges[i - 1], offset_edges[i]
        # Intersect the two offset lines: a1 + t·d1 == a2 + u·d2.
        denominator = d1[0] * d2[1] - d1[1] * d2[0]
        if abs(denominator) < 1e-10:
            new_points.append(a2)
            continue
        t = ((a2[0] - a1[0]) * d2[1] - (a2[1] - a1[1]) * d2[0]) / denominator
        new_points.append((a1[0] + t * d1[0], a1[1] + t * d1[1]))
    return new_points


def shape_x_bounds(points, offset_x, offset_y, band_top, band_bottom):
    """Return the ``(min_x, max_x)`` of a polygon within a y band.

    Points are relative to the box origin, offset by the box position;
    the band is absolute.

    """
    band_top -= offset_y
    band_bottom -= offset_y
    minimum = maximum = None
    count = len(points)
    for i in range(count):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % count]
        if y1 == y2:
            if band_top <= y1 <= band_bottom:
                candidates = (x1, x2)
            else:
                continue
        else:
            if y1 > y2:
                x1, y1, x2, y2 = x2, y2, x1, y1
            low = max(y1, band_top)
            high = min(y2, band_bottom)
            if low > high:
                continue
            candidates = (
                x1 + (x2 - x1) * (low - y1) / (y2 - y1),
                x1 + (x2 - x1) * (high - y1) / (y2 - y1))
        for x in candidates:
            if minimum is None or x < minimum:
                minimum = x
            if maximum is None or x > maximum:
                maximum = x
    if minimum is None:
        return None
    return minimum + offset_x, maximum + offset_x


def get_clearance(context, box, direction, collapsed_margin=0):
    """Return None if there is no clearance, otherwise the clearance value."""

    def clear(clear_value, float_value):
        """Closure returning whether clear and float values match."""
        if clear_value == 'inline-start':
            clear_value = 'left' if direction == 'ltr' else 'right'
        if clear_value == 'inline-end':
            clear_value = 'left' if direction == 'rtl' else 'right'
        if float_value == 'inline-start':
            float_value = 'left' if direction == 'ltr' else 'right'
        if float_value == 'inline-end':
            float_value = 'left' if direction == 'rtl' else 'right'
        return clear_value in (float_value, 'both')

    # Box should be after shape that’s broken on this page.
    for broken_shape in context.broken_out_of_flow:
        if broken_shape.is_floated():
            if clear(box.style['clear'], broken_shape.style['float']):
                return inf
    # Hypothetical position is the position of the top border edge
    clearance = None
    hypothetical_position = box.position_y + collapsed_margin
    for excluded_shape in context.excluded_shapes:
        if clear(box.style['clear'], excluded_shape.style['float']):
            y, h = excluded_shape.position_y, excluded_shape.margin_height()
            if hypothetical_position < y + h:
                clearance = max((clearance or 0), y + h - hypothetical_position)
    return clearance


def avoid_collisions(context, box, containing_block, outer=True):
    excluded_shapes = context.excluded_shapes
    position_y = box.position_y if outer else box.border_box_y()

    box_width = box.margin_width() if outer else box.border_width()
    box_height = box.margin_height() if outer else box.border_height()

    if box.border_height() == 0 and box.is_floated():
        return 0, 0, containing_block.width

    left_keywords = ['left']
    right_keywords = ['right']
    if containing_block.style['direction'] == 'ltr':
        left_keywords.append('inline-start')
        right_keywords.append('inline-end')
    else:
        left_keywords.append('inline-end')
        right_keywords.append('inline-start')

    while True:
        colliding_shapes = []
        for shape in excluded_shapes:
            # Assign locals to avoid slow attribute lookups.
            shape_position_y = shape.position_y
            shape_margin_height = shape.margin_height()
            if ((shape_position_y < position_y <
                 shape_position_y + shape_margin_height) or
                (shape_position_y < position_y + box_height <
                 shape_position_y + shape_margin_height) or
                (shape_position_y >= position_y and
                 shape_position_y + shape_margin_height <=
                 position_y + box_height)):
                colliding_shapes.append(shape)
        left_bounds = []
        right_bounds = []
        for shape in colliding_shapes:
            # shape-outside: use the shape polygon’s extent in the band.
            points = getattr(shape, 'shape_points', None)
            if points is not None:
                bounds = shape_x_bounds(
                    points, shape.position_x, shape.position_y,
                    position_y, position_y + box_height)
                if bounds is None:
                    continue
                if shape.style['float'] in left_keywords:
                    left_bounds.append(bounds[1])
                elif shape.style['float'] in right_keywords:
                    right_bounds.append(bounds[0])
                continue
            if shape.style['float'] in left_keywords:
                left_bounds.append(shape.position_x + shape.margin_width())
            elif shape.style['float'] in right_keywords:
                right_bounds.append(shape.position_x)

        # Set the default maximum bounds
        max_left_bound = containing_block.content_box_x()
        max_right_bound = max_left_bound + containing_block.width

        if not outer:
            max_left_bound += box.margin_left
            max_right_bound -= box.margin_right

        # Set the real maximum bounds according to sibling float elements
        if left_bounds or right_bounds:
            if left_bounds:
                max_left_bound = max(max(left_bounds), max_left_bound)
            if right_bounds:
                max_right_bound = min(min(right_bounds), max_right_bound)

            # Points 3, 7 and 8
            if box_width > max_right_bound - max_left_bound:
                # The box does not fit here
                new_position_y = min(
                    shape.position_y + shape.margin_height()
                    for shape in colliding_shapes)
                if new_position_y > position_y:
                    # We can find a solution with a higher position_y
                    position_y = new_position_y
                    continue
                # No solution, we must put the box here
        break

    # See https://www.w3.org/TR/CSS21/visuren.html#floats
    # Boxes that can’t collide with floats are:
    # - floats
    # - line boxes
    # - table wrappers
    # - block-level replaced box
    # - element establishing new formatting contexts
    assert (
        box.is_floated() or
        isinstance(box, boxes.LineBox) or
        box.is_table_wrapper or
        isinstance(box, boxes.BlockReplacedBox) or
        box.establishes_formatting_context())

    # The x-position of the box depends on its type.
    position_x = max_left_bound
    if box.style['float'] == 'none':
        if containing_block.style['direction'] == 'rtl':
            if isinstance(box, boxes.LineBox):
                # The position of the line is the position of the cursor, at
                # the right bound.
                position_x = max_right_bound
            elif box.is_table_wrapper:
                # The position of the right border of the table is at the right
                # bound.
                position_x = max_right_bound - box_width
            else:
                # The position of the right border of the replaced box or
                # formatting context is at the right bound.
                assert (
                    isinstance(box, boxes.BlockReplacedBox) or
                    box.establishes_formatting_context())
                position_x = max_right_bound - box_width

    available_width = max_right_bound - max_left_bound

    if not outer:
        position_x -= box.margin_left
        position_y -= box.margin_top

    return position_x, position_y, available_width
