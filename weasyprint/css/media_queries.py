"""Handle media queries.

https://www.w3.org/TR/mediaqueries-4/

"""

import tinycss2

from ..logger import LOGGER
from .tokens import get_length, get_resolution, remove_whitespace, split_on_comma
from .units import to_pixels

# Media types we understand. Anything else is treated as an unknown media type
# that never matches (per the spec, unknown media types evaluate to false).
KNOWN_MEDIA_TYPES = {'all', 'print', 'screen', 'speech'}

# Media features that take a value and support min-/max- prefixes (range
# features), mapped to the descriptor key they compare against.
_RANGE_FEATURES = {
    'width': 'width',
    'height': 'height',
    'resolution': 'resolution',
    'device-width': 'width',
    'device-height': 'height',
}

# Discrete features mapped to the descriptor key.
_DISCRETE_FEATURES = {
    'orientation': 'orientation',
}


class MediaDescriptor:
    """The evaluation target for media queries.

    For paged output the target is the page area: ``width`` and ``height`` are
    in CSS pixels, ``resolution`` is in dots-per-pixel (dppx).

    """
    def __init__(self, media_type, width, height, resolution):
        self.media_type = media_type
        self.width = width
        self.height = height
        self.resolution = resolution

    @property
    def orientation(self):
        return 'portrait' if self.height >= self.width else 'landscape'

    def get(self, key):
        if key == 'orientation':
            return self.orientation
        return getattr(self, key)


def make_descriptor(media_type, page_size=None, resolution=1):
    """Build a :class:`MediaDescriptor` from a media type.

    :param page_size: ``(width, height)`` in CSS pixels, or ``None`` to use the
        default page size (A4).
    :param resolution: output resolution in dppx (1 dppx == 96 dpi).

    """
    if page_size is None:
        from .computed_values import INITIAL_PAGE_SIZE
        width = to_pixels(INITIAL_PAGE_SIZE[0], None, None)
        height = to_pixels(INITIAL_PAGE_SIZE[1], None, None)
    else:
        width, height = page_size
    return MediaDescriptor(media_type, width, height, resolution)


def _feature_value_pixels(value):
    """Resolve a media-feature length token to CSS pixels, or ``None``."""
    length = get_length(value, negative=False)
    if length is None:
        return None
    return to_pixels(length, None, None)


def _parse_plain_feature(name, value_tokens):
    """Parse ``name: value`` or boolean ``name`` into an evaluator.

    Returns a one-argument callable taking a :class:`MediaDescriptor` and
    returning a bool, or ``None`` if the feature is unknown/invalid.

    """
    name = name.lower()
    prefix = None
    base = name
    if name.startswith('min-'):
        prefix, base = 'min', name[4:]
    elif name.startswith('max-'):
        prefix, base = 'max', name[4:]

    if base in _RANGE_FEATURES:
        key = _RANGE_FEATURES[base]
        is_resolution = base == 'resolution'
        if not value_tokens:
            # Boolean context: true when the feature is non-zero. min-/max-
            # without a value is invalid.
            if prefix is not None:
                return None
            return lambda d: d.get(key) != 0
        if is_resolution:
            target = get_resolution(value_tokens[0])
        else:
            target = _feature_value_pixels(value_tokens[0])
        if target is None or len(value_tokens) != 1:
            return None
        if prefix == 'min':
            return lambda d: d.get(key) >= target
        elif prefix == 'max':
            return lambda d: d.get(key) <= target
        else:
            return lambda d: d.get(key) == target

    if prefix is None and base in _DISCRETE_FEATURES:
        key = _DISCRETE_FEATURES[base]
        if not value_tokens:
            # Boolean context: orientation is always present (truthy).
            return lambda d: True
        if len(value_tokens) != 1 or value_tokens[0].type != 'ident':
            return None
        wanted = value_tokens[0].lower_value
        if base == 'orientation' and wanted not in ('portrait', 'landscape'):
            return None
        return lambda d, key=key, wanted=wanted: d.get(key) == wanted

    return None


def _parse_feature_block(tokens):
    """Parse the contents of a ``(...)`` media-feature block.

    Returns an evaluator callable, or ``None`` on invalid/unsupported input.

    """
    tokens = remove_whitespace(tokens)
    if not tokens:
        return None

    # Plain / boolean syntax: ``name`` or ``name: value``.
    if tokens[0].type == 'ident':
        if len(tokens) == 1:
            return _parse_plain_feature(tokens[0].value, [])
        if (getattr(tokens[1], 'type', None) == 'literal'
                and tokens[1].value == ':'):
            return _parse_plain_feature(tokens[0].value, tokens[2:])

    # Range syntax: ``name <op> value`` / ``value <op> name`` /
    # ``value <op> name <op> value``. Only single-comparator forms are
    # supported here, which covers the common cases.
    parts = _split_on_comparators(tokens)
    if parts is not None:
        return _parse_range(parts)

    return None


def _is_single_comparator_char(token):
    return (getattr(token, 'type', None) == 'literal'
            and token.value in ('<', '>', '='))


def _split_on_comparators(tokens):
    """Split ``tokens`` into operands and operators for the range syntax.

    Returns ``[operand, op, operand]`` or ``[operand, op, operand, op,
    operand]`` (each operand being a token list, each op a string), or ``None``
    if the structure is not a valid range expression.

    """
    operands = []
    operators = []
    current = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if _is_single_comparator_char(token):
            op = token.value
            # tinycss2 tokenises ``>=`` and ``<=`` as two adjacent literals
            # (``>`` ``=`` / ``<`` ``=``); merge them back here. Whitespace has
            # already been removed.
            if op in ('<', '>') and i + 1 < len(tokens):
                following = tokens[i + 1]
                if (getattr(following, 'type', None) == 'literal'
                        and following.value == '='):
                    op += '='
                    i += 1
            operands.append(current)
            operators.append(op)
            current = []
        else:
            current.append(token)
        i += 1
    operands.append(current)

    if len(operators) == 0 or len(operators) > 2:
        return None
    result = []
    for index, operand in enumerate(operands):
        result.append(operand)
        if index < len(operators):
            result.append(operators[index])
    return result


def _resolve_operand(tokens):
    """Resolve a range operand to either ``('feature', key, is_resolution)`` or
    ``('value', resolved)``, or ``None``."""
    tokens = remove_whitespace(tokens)
    if len(tokens) == 1 and tokens[0].type == 'ident':
        name = tokens[0].lower_value
        if name in _RANGE_FEATURES:
            return ('feature', _RANGE_FEATURES[name], name == 'resolution')
        return None
    if len(tokens) == 1:
        # Try resolution first (dimension with resolution unit), then length.
        resolution = get_resolution(tokens[0])
        if resolution is not None:
            return ('value', resolution, True)
        pixels = _feature_value_pixels(tokens[0])
        if pixels is not None:
            return ('value', pixels, False)
    return None


_OPS = {
    '<': lambda a, b: a < b,
    '<=': lambda a, b: a <= b,
    '>': lambda a, b: a > b,
    '>=': lambda a, b: a >= b,
    '=': lambda a, b: a == b,
}


def _parse_range(parts):
    """Build an evaluator from split range parts."""
    operands = [_resolve_operand(parts[i]) for i in range(0, len(parts), 2)]
    operators = [parts[i] for i in range(1, len(parts), 2)]
    if any(operand is None for operand in operands):
        return None

    # Exactly one operand must be the feature name.
    feature_operands = [o for o in operands if o[0] == 'feature']
    if len(feature_operands) != 1:
        return None

    # Value operands must use units compatible with the feature (resolution
    # features compare against resolutions, length features against lengths).
    feature_is_resolution = feature_operands[0][2]
    for operand in operands:
        if operand[0] == 'value' and operand[2] != feature_is_resolution:
            return None

    def evaluator(descriptor):
        resolved = []
        for operand in operands:
            if operand[0] == 'feature':
                resolved.append(descriptor.get(operand[1]))
            else:
                resolved.append(operand[1])
        for index, op in enumerate(operators):
            left = resolved[index]
            right = resolved[index + 1]
            if not _OPS[op](left, right):
                return False
        return True

    return evaluator


def _parse_query(tokens):
    """Parse a single (comma-separated) media query.

    Returns ``(negate, type_or_none, [evaluators])`` or ``None`` on invalid.

    """
    tokens = remove_whitespace(tokens)
    if not tokens:
        # Empty query is equivalent to ``all``.
        return (False, 'all', [])

    negate = False
    media_type = None
    evaluators = []
    index = 0

    # Leading ``not`` / ``only`` followed by a media type.
    if tokens[0].type == 'ident' and tokens[0].lower_value in ('not', 'only'):
        if tokens[0].lower_value == 'not':
            negate = True
        index = 1

    expect_and = False
    while index < len(tokens):
        token = tokens[index]
        if expect_and:
            if token.type == 'ident' and token.lower_value == 'and':
                expect_and = False
                index += 1
                continue
            return None
        if token.type == 'ident':
            name = token.lower_value
            if name in ('and', 'or', 'not', 'only'):
                return None
            if media_type is not None or evaluators:
                # A bare ident after we already have a type/feature is invalid.
                return None
            media_type = name
            expect_and = True
            index += 1
            continue
        if getattr(token, 'type', None) == '() block':
            evaluator = _parse_feature_block(token.content)
            if evaluator is None:
                return None
            evaluators.append(evaluator)
            expect_and = True
            index += 1
            continue
        return None

    if media_type is None and not evaluators:
        return None
    return (negate, media_type, evaluators)


def parse_media_query(tokens):
    """Parse a media query list.

    Returns a list of parsed queries (opaque structures) or ``None`` if the
    whole query list is invalid.

    """
    tokens = remove_whitespace(tokens)
    if not tokens:
        return [(False, 'all', [])]
    queries = []
    for part in split_on_comma(tokens):
        query = _parse_query(part)
        if query is None:
            LOGGER.warning(
                'Expected a media query, got %r', tinycss2.serialize(part))
            return
        queries.append(query)
    return queries


def _evaluate_single(query, descriptor):
    negate, media_type, evaluators = query
    if media_type is not None and media_type not in KNOWN_MEDIA_TYPES:
        result = False
    else:
        type_matches = (
            media_type is None
            or media_type == 'all'
            or media_type == descriptor.media_type)
        result = type_matches and all(
            evaluator(descriptor) for evaluator in evaluators)
    return not result if negate else result


def evaluate_media_query(query_list, target):
    """Return the boolean evaluation of ``query_list`` for the given target.

    :param query_list: either the list of parsed queries returned by
        :func:`parse_media_query`, the legacy list of media-type strings, or a
        list mixing the two (from HTML ``media`` attributes).
    :param target: a :class:`MediaDescriptor`, or a media-type string (legacy
        callers); a string is turned into a default descriptor.

    """
    if isinstance(target, str):
        descriptor = make_descriptor(target)
    else:
        descriptor = target

    for query in query_list:
        if isinstance(query, str):
            # Legacy media-type string (e.g. from an HTML ``media`` attribute).
            if query == 'all' or query == descriptor.media_type:
                return True
        elif _evaluate_single(query, descriptor):
            return True
    return False
