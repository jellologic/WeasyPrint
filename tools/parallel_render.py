#!/usr/bin/env python
"""Render many documents to PDF in parallel.

WeasyPrint rendering is CPU- and GIL-bound, so threads do not help, but it
scales close to linearly across *processes*. This tool renders a batch of
HTML inputs across a process pool, giving a large throughput win on
multi-core machines (e.g. generating thousands of invoices/reports).

Each worker process builds a single ``FontConfiguration`` once and reuses it
for every document it handles, so the per-process font setup cost is paid
once rather than per document.

Examples
--------
Render every HTML file in a folder to ./out, using all but one core::

    python tools/parallel_render.py invoices/*.html -o out

Use a fixed number of workers and render specific files and a URL::

    python tools/parallel_render.py -j 8 a.html b.html https://example.com

Benchmark serial vs parallel on synthetic documents (no inputs needed)::

    python tools/parallel_render.py --benchmark 160 -j 8

Notes
-----
This is a standalone utility, not part of the importable ``weasyprint``
package. On PyPy, prefer fewer, longer-lived workers (each handling many
documents) so the JIT has time to warm up; with many short-lived workers the
warmup cost is wasted and CPython is usually faster.
"""

import argparse
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse

# One warm FontConfiguration per worker process, created in the initializer.
_FONT_CONFIG = None


def _worker_init():
    global _FONT_CONFIG
    from weasyprint.text.fonts import FontConfiguration
    _FONT_CONFIG = FontConfiguration()


def _is_url(source):
    return urlparse(str(source)).scheme in ('http', 'https', 'ftp')


def _output_path(source, output_dir, index):
    if _is_url(source):
        name = (urlparse(source).path.rsplit('/', 1)[-1] or f'document-{index}')
    else:
        name = Path(source).name
    stem = Path(name).stem or f'document-{index}'
    return Path(output_dir) / f'{stem}.pdf'


def _render_job(args):
    """Render one (source, target) pair. Runs in a worker process."""
    index, source, target = args
    from weasyprint import HTML
    try:
        HTML(source).write_pdf(target, font_config=_FONT_CONFIG)
        return (source, target, os.path.getsize(target), None)
    except Exception as exc:  # keep the batch going if one document fails
        return (source, target, 0, f'{type(exc).__name__}: {exc}')


def run_batch(sources, output_dir, n_workers):
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    jobs = [
        (i, src, str(_output_path(src, output_dir, i)))
        for i, src in enumerate(sources)]

    start = time.perf_counter()
    failures = []
    done = 0
    with ProcessPoolExecutor(
            max_workers=n_workers, initializer=_worker_init) as executor:
        futures = [executor.submit(_render_job, job) for job in jobs]
        for future in as_completed(futures):
            source, target, size, error = future.result()
            done += 1
            if error:
                failures.append((source, error))
                print(f'  [{done}/{len(jobs)}] FAILED {source}: {error}',
                      file=sys.stderr)
            else:
                print(f'  [{done}/{len(jobs)}] {source} -> {target} '
                      f'({size:,} bytes)')
    elapsed = time.perf_counter() - start

    ok = len(jobs) - len(failures)
    print(f'\nRendered {ok}/{len(jobs)} documents in {elapsed:.2f}s '
          f'({ok / elapsed:.1f} docs/s) using {n_workers} workers.')
    if failures:
        print(f'{len(failures)} failed.', file=sys.stderr)
    return not failures


def _benchmark(n_docs, n_workers):
    """Render synthetic table reports serially then in parallel, and compare."""
    template = (
        '<!DOCTYPE html><html><head><meta charset=utf-8><style>'
        'body{{font-family:sans-serif;font-size:11px}}'
        'table{{width:100%;border-collapse:collapse}}'
        'td,th{{border:1px solid #999;padding:3px}} thead{{background:#eee}}'
        '@page{{size:A4;margin:1.5cm}}</style></head><body><h1>Report {n}</h1>'
        '<table><thead><tr><th>#</th><th>Name</th><th>Cat</th><th>Price</th>'
        '</tr></thead><tbody>{rows}</tbody></table></body></html>')

    def doc(n, rows=200):
        body = ''.join(
            f'<tr><td>{i}</td><td>Item {i} report {n}</td>'
            f'<td>Cat {i % 7}</td><td>${i * 3.5:.2f}</td></tr>'
            for i in range(1, rows + 1))
        return template.format(n=n, rows=body)

    docs = [doc(n) for n in range(n_docs)]

    def render_one(html):
        from weasyprint import HTML
        return len(HTML(string=html).write_pdf(font_config=_FONT_CONFIG))

    _worker_init()
    start = time.perf_counter()
    for html in docs:
        render_one(html)
    serial = time.perf_counter() - start

    start = time.perf_counter()
    with ProcessPoolExecutor(
            max_workers=n_workers, initializer=_worker_init) as executor:
        list(executor.map(_bench_job, docs))
    parallel = time.perf_counter() - start

    print(f'docs={n_docs} workers={n_workers}')
    print(f'  serial:   {serial:.2f}s  ({n_docs / serial:.1f} docs/s)')
    print(f'  parallel: {parallel:.2f}s  ({n_docs / parallel:.1f} docs/s)  '
          f'speedup={serial / parallel:.1f}x')


def _bench_job(html):
    from weasyprint import HTML
    return len(HTML(string=html).write_pdf(font_config=_FONT_CONFIG))


def main():
    default_workers = max(1, (os.cpu_count() or 2) - 1)
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        'inputs', nargs='*',
        help='HTML files or URLs to render to PDF')
    parser.add_argument(
        '-o', '--output-dir', default='.',
        help='directory for the generated PDFs (default: current directory)')
    parser.add_argument(
        '-j', '--workers', type=int, default=default_workers,
        help=f'number of worker processes (default: {default_workers})')
    parser.add_argument(
        '--benchmark', type=int, metavar='N',
        help='render N synthetic documents and report serial vs parallel '
             'throughput instead of rendering inputs')
    args = parser.parse_args()

    if args.benchmark is not None:
        _benchmark(args.benchmark, args.workers)
        return

    if not args.inputs:
        parser.error('no inputs given (or use --benchmark N)')

    ok = run_batch(args.inputs, args.output_dir, args.workers)
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
