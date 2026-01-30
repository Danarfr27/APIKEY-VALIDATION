#!/usr/bin/env python3
"""
validasi.py

Validator for API keys stored in `api.txt` (one key per line), tuned
for Google Gemini / Generative Language API keys by default.

Default behaviour: send a GET to Google Generative endpoint (models
list) using a query parameter `?key=` (commonly accepted for Google
API keys). You can override endpoint or auth mode with flags.

Outputs a neat top-to-bottom report and writes debug details to
`validasi_debug.log` in the same folder.

Usage:
    python validasi.py --file api.txt
    # or explicitly against a Gemini endpoint/header:
    python validasi.py --file api.txt --endpoint https://generativelanguage.googleapis.com/v1/models --auth-mode api_key_header --key-name x-goog-api-key
"""

import argparse
import sys
import time
import json
from pathlib import Path

try:
    import requests
except Exception:
    requests = None


def read_keys(path):
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Key file not found: {path}")
    keys = []
    for line in p.read_text(encoding='utf-8').splitlines():
        s = line.strip()
        if not s or s.startswith('#'):
            continue
        keys.append(s)
    return keys


def mask_key(k):
    if len(k) <= 10:
        return k[:2] + '...' + k[-2:]
    return k[:4] + '...' + k[-4:]


def check_key_requests(endpoint, key, auth_mode='bearer', key_name='X-API-Key', timeout=10):
    headers = {}
    params = None
    if auth_mode == 'bearer':
        headers['Authorization'] = f'Bearer {key}'
    elif auth_mode == 'api_key_header':
        headers[key_name] = key
    elif auth_mode == 'query_key':
        params = {'key': key}

    try:
        r = requests.get(endpoint, headers=headers, params=params, timeout=timeout)
        try:
            body = r.json()
            body_text = json.dumps(body)
        except Exception:
            body_text = r.text
        return r.status_code, body_text
    except Exception as e:
        return None, str(e)


def check_key_urllib(endpoint, key, auth_mode='bearer', key_name='X-API-Key', timeout=10):
    # fallback: use urllib (no json parsing convenience)
    from urllib import request, error, parse
    url = endpoint
    headers = {}
    if auth_mode == 'bearer':
        headers['Authorization'] = f'Bearer {key}'
    elif auth_mode == 'api_key_header':
        headers[key_name] = key
    elif auth_mode == 'query_key':
        sep = '&' if '?' in url else '?'
        url = f"{url}{sep}key={parse.quote(key)}"

    req = request.Request(url, headers=headers)
    try:
        with request.urlopen(req, timeout=timeout) as r:
            body = r.read().decode('utf-8', errors='replace')
            return r.getcode(), body
    except error.HTTPError as he:
        try:
            body = he.read().decode('utf-8', errors='replace')
        except Exception:
            body = str(he)
        return he.code, body
    except Exception as e:
        return None, str(e)


def main():
    parser = argparse.ArgumentParser(description='Validate API keys listed in a file')
    parser.add_argument('--file', '-f', default='api.txt', help='path to api.txt')
    parser.add_argument('--endpoint', '-e', default='https://generativelanguage.googleapis.com/v1/models', help='validation endpoint')
    parser.add_argument('--auth-mode', choices=['bearer', 'api_key_header', 'query_key'], default='query_key',
                        help='how to send the API key: bearer (Authorization: Bearer), api_key_header (X-API-Key or custom), or query_key (?key=)')
    parser.add_argument('--key-name', default='x-goog-api-key', help='header name to use when --auth-mode=api_key_header')
    parser.add_argument('--delay', '-d', type=float, default=0.35, help='delay between requests (s)')
    parser.add_argument('--debug-log', default='validasi_debug.log', help='debug log file')
    parser.add_argument('--timeout', type=float, default=10.0, help='request timeout seconds')
    args = parser.parse_args()

    try:
        keys = read_keys(args.file)
    except Exception as e:
        print(f'Error: {e}', file=sys.stderr)
        sys.exit(2)

    if not keys:
        print('No keys found in', args.file)
        sys.exit(0)

    use_requests = requests is not None

    results = []
    debug_lines = []
    for i, key in enumerate(keys, 1):
        masked = mask_key(key)
        print(f'[{i}/{len(keys)}] Checking {masked} ...', flush=True)
        if use_requests:
            status, body = check_key_requests(args.endpoint, key, args.auth_mode, args.key_name, timeout=args.timeout)
        else:
            status, body = check_key_urllib(args.endpoint, key, args.auth_mode, args.key_name, timeout=args.timeout)

        note = ''
        ok = False
        if status is None:
            note = f'Error: {body}'
        else:
            if status == 200:
                ok = True
                note = 'Active'
            elif status in (401, 403):
                note = 'Invalid / Unauthorized'
            else:
                note = f'HTTP {status}'

        results.append({'index': i, 'key': key, 'masked': masked, 'status': status, 'ok': ok, 'note': note})

        # debug info: keep response trimmed
        debug = {
            'index': i,
            'masked': masked,
            'status': status,
            'auth_mode': args.auth_mode,
            'body_preview': (body[:1000] + '...') if isinstance(body, str) and len(body) > 1000 else body
        }
        debug_lines.append(debug)

        time.sleep(args.delay)

    # sort: active first then others (preserve index within groups)
    results_sorted = sorted(results, key=lambda r: (0 if r['ok'] else 1, r['index']))

    print('\nValidation results (top -> bottom):')
    print('---------------------------------------------------------------')
    for r in results_sorted:
        status_text = 'ACTIVE' if r['ok'] else 'INVALID'
        code = str(r['status']) if r['status'] is not None else '-'
        print(f"{r['index']:2d}. {r['masked']:20s} | {status_text:7s} | {code:5s} | {r['note']}")
    print('---------------------------------------------------------------')

    # write debug log
    dbgpath = Path(args.debug_log)
    try:
        with dbgpath.open('w', encoding='utf-8') as fh:
            fh.write('DEBUG VALIDATION LOG\n')
            fh.write(f'Endpoint: {args.endpoint}\n')
            fh.write(f'Requested at: {time.ctime()}\n')
            fh.write('\n')
            json.dump(debug_lines, fh, indent=2, ensure_ascii=False)
            fh.write('\n')
        print(f'Debug log written to: {dbgpath}')
    except Exception as e:
        print('Failed to write debug log:', e, file=sys.stderr)

    # write active keys to file (aktif.txt) in same dir as the key file
    try:
        keyfile_dir = Path(args.file).resolve().parent
        aktif_path = keyfile_dir / 'aktif.txt'
        with aktif_path.open('w', encoding='utf-8') as af:
            for r in results_sorted:
                if r['ok']:
                    af.write(f"{r['key']},\n")
        print(f'Active keys written to: {aktif_path}')
    except Exception as e:
        print('Failed to write aktif.txt:', e, file=sys.stderr)


if __name__ == '__main__':
    main()
