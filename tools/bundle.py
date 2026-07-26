#!/usr/bin/env python3
"""Read and write the islands inside index.html.

index.html is not hand-editable: it is a self-contained bundle whose real
contents live base64'd and gzipped inside <script type="__bundler/*"> islands.
Editing the app means unpacking the template, changing that, and packing it
back. This module is the only thing that should ever rewrite index.html.

    python3 tools/bundle.py unpack          # -> build/template.html (+ assets)
    python3 tools/bundle.py pack            # build/template.html -> index.html
    python3 tools/bundle.py assets          # list what is in the manifest

The islands:
    manifest       uuid -> {mime, compressed, base64 data}
    template       the JSON-encoded HTML the loader swaps the document for
    ext_resources  CDN url -> uuid, resolved into window.__resources at boot
    page_order     nested-page uuids

An asset is live if its uuid appears in EITHER the template OR ext_resources.
React and ReactDOM are named only in ext_resources — prune against the template
alone and the app boots to a blank screen reaching for unpkg.com.
"""
import base64
import gzip
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, 'index.html')
BUILD = os.path.join(ROOT, 'build')
TEMPLATE = os.path.join(BUILD, 'template.html')
CLOSE = '\n  </script>'


def _bounds(doc, kind):
    opener = '<script type="__bundler/%s">\n' % kind
    start = doc.index(opener) + len(opener)
    return start, doc.index(CLOSE, start)


def read_island(doc, kind):
    a, b = _bounds(doc, kind)
    return doc[a:b]


def write_island(doc, kind, text):
    a, b = _bounds(doc, kind)
    return doc[:a] + text + doc[b:]


def load():
    return open(INDEX, encoding='utf-8').read()


def unpack():
    doc = load()
    os.makedirs(BUILD, exist_ok=True)
    template = json.loads(read_island(doc, 'template'))
    open(TEMPLATE, 'w', encoding='utf-8').write(template)
    print('template -> %s  (%d lines)' % (TEMPLATE, template.count('\n') + 1))

    manifest = json.loads(read_island(doc, 'manifest'))
    assets = os.path.join(BUILD, 'assets')
    os.makedirs(assets, exist_ok=True)
    for uuid, entry in manifest.items():
        raw = base64.b64decode(entry['data'])
        if entry.get('compressed'):
            raw = gzip.decompress(raw)
        ext = {'image/png': 'png', 'font/woff2': 'woff2'}.get(entry['mime'], 'js')
        open(os.path.join(assets, uuid + '.' + ext), 'wb').write(raw)
    print('%d assets -> %s' % (len(manifest), assets))


def pack():
    doc = load()
    template = open(TEMPLATE, encoding='utf-8').read()
    # The island lives inside a <script>, so an unescaped "</" would close the
    # tag early. The original bundler escapes the slash; match it.
    encoded = json.dumps(template, ensure_ascii=False).replace('</', '<\\u002F')
    assert '</script' not in encoded.lower(), 'template would break out of its tag'
    assert json.loads(encoded) == template, 'round-trip mismatch'

    before = len(doc)
    doc = write_island(doc, 'template', encoded)

    # every uuid still referenced must survive
    manifest = json.loads(read_island(doc, 'manifest'))
    ext = json.loads(read_island(doc, 'ext_resources'))
    live = {e['uuid'] for e in ext} | {u for u in manifest if u in template}
    for e in ext:
        assert e['uuid'] in manifest, 'ext_resources lost %s' % e['id']
    dead = [u for u in manifest if u not in live]
    if dead:
        print('note: %d asset(s) unreferenced (not pruned): %s'
              % (len(dead), ', '.join(u[:8] for u in dead)))

    open(INDEX, 'w', encoding='utf-8').write(doc)
    print('index.html  %.2f MB -> %.2f MB' % (before / 1048576, len(doc) / 1048576))


def assets():
    manifest = json.loads(read_island(load(), 'manifest'))
    total = sum(len(v['data']) for v in manifest.values())
    for uuid, v in sorted(manifest.items(), key=lambda kv: -len(kv[1]['data'])):
        print('  %-38s %-24s %8.1f KB  %4.1f%%'
              % (uuid, v['mime'], len(v['data']) / 1024, 100 * len(v['data']) / total))
    print('  %d assets, %.2f MB of base64' % (len(manifest), total / 1048576))


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'unpack'
    {'unpack': unpack, 'pack': pack, 'assets': assets}[cmd]()
