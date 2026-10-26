"""Live local Uvicorn tamper/restart check against the disposable P7 clone."""
import argparse
from contextlib import closing
from hashlib import sha256
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
import requests


QUESTION = "What were P&G's net sales for the three months ended September 30, 2026?"


def launch(root, port, token):
    env = dict(os.environ, TOPIC3_RESEARCH_ROOT=str(root), TOPIC3_RESEARCH_API_TOKEN=token,
               TOPIC3_RESEARCH_MODE='real_frozen')
    process = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app.research_api:app',
                                '--host', '127.0.0.1', '--port', str(port), '--log-level', 'error'],
                               env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    url = f'http://127.0.0.1:{port}'
    for _ in range(100):
        if process.poll() is not None:
            raise RuntimeError('P7_UVICORN_EXITED')
        try:
            if requests.get(url + '/research/v1/health', timeout=.25).status_code == 200:
                return process, url
        except requests.RequestException:
            pass
        time.sleep(.1)
    process.terminate();process.wait(timeout=5)
    raise RuntimeError('P7_UVICORN_NOT_READY')


def stop(process):
    process.terminate()
    try:process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill();process.wait(timeout=5)


def request(url, token):
    response = requests.post(url + '/research/v1/query',
        headers={'Authorization': 'Bearer ' + token},
        json={'question': QUESTION, 'workflow': 'automatic_real', 'arm': 'B'}, timeout=30)
    body = response.json()
    return {'http_status': response.status_code, 'answer_status': body.get('answer', {}).get('status'),
            'values': body.get('answer', {}).get('result_values', []), 'detail': body.get('detail')}


def run(root):
    root = root.resolve(strict=True)
    if 'p7-isolated-review' not in root.name:
        raise ValueError('P7_CLONE_REQUIRED')
    with closing(socket.socket()) as s:
        s.bind(('127.0.0.1', 0));port = s.getsockname()[1]
    token = secrets.token_urlsafe(32)
    raw = next((root / 'raw').rglob('pg-20260930.htm'))
    original = raw.read_bytes()
    if sha256(original).hexdigest() != '30904fac63dc81fec0a524c812bea5109521b9b8063f34adf13f3f50bd2a4b53':
        raise ValueError('P7_CLONE_RAW_SOURCE_NOT_CONTROL')
    process, url = launch(root, port, token)
    try:
        control = request(url, token)
        if control['values'] != ['23276000000']:
            raise AssertionError('P7_HTTP_CONTROL_FAILED')
        try:
            raw.write_bytes(original + b' ')
            tampered = request(url, token)
        finally:
            raw.write_bytes(original)
        restored = request(url, token)
        if tampered['http_status'] != 409 or tampered['values'] or restored != control:
            raise AssertionError('P7_HTTP_TAMPER_REFUSAL_FAILED')
    finally:
        stop(process)
    process, url = launch(root, port, token)
    try:
        restarted = request(url, token)
        unauth = requests.post(url + '/research/v1/query',
            json={'question': QUESTION, 'workflow': 'automatic_real'}, timeout=5).status_code
        if restarted != control or unauth != 401:
            raise AssertionError('P7_RESTART_OR_AUTH_FAILED')
    finally:
        stop(process)
    return {'schema_version': 'topic3-p7-http-tamper/v1', 'clone_only': True,
            'control': control, 'tampered_raw': tampered, 'restored': restored,
            'restarted': restarted, 'unauthorized_http': unauth, 'token_recorded': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = run(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'tampered_http': result['tampered_raw']['http_status'],
                      'restart_status': result['restarted']['answer_status'],
                      'unauthorized_http': result['unauthorized_http']}))
