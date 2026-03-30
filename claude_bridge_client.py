#!/usr/bin/env python3
"""
Claude Bridge Client v2

Connects your local Claude Code instance to the MineAI platform.
Uses priority queue: higher-priority tasks are dispatched first.

Usage:
    python3 claude_bridge_client.py [--token TOKEN] [--url URL] [--name NAME]

Requirements:
    pip install requests
    Claude Code CLI: npm install -g @anthropic-ai/claude-code
"""

import argparse
import json
import os
import platform
import subprocess
import sys
import threading
import time
from datetime import datetime

try:
    import requests
except ImportError:
    print("Error: please install requests first:  pip install requests")
    sys.exit(1)

# ── Injected at download time by the platform ──────────────────
PLATFORM_URL   = '__PLATFORM_URL__'
USER_TOKEN     = '__USER_TOKEN__'
BRIDGE_VERSION = '2.0.0'
CONFIG_PATH    = os.path.expanduser('~/.claude_bridge_config.json')

# ── Runtime state ───────────────────────────────────────────────
_connection_id: str = ''
_active_procs: dict = {}   # session_id → subprocess.Popen
_cancel_flags: dict = {}   # session_id → bool


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _log(msg: str, level: str = 'INFO'):
    ts    = datetime.now().strftime('%H:%M:%S')
    icons = {'INFO': '·', 'OK': '✓', 'WARN': '!', 'ERROR': '✗', 'CLAUDE': '◆', 'QUEUE': '⬆'}
    print(f"  [{ts}] {icons.get(level,'·')} {msg}", flush=True)


def _api(method: str, path: str, **kwargs):
    headers = kwargs.pop('headers', {})
    headers['Authorization'] = f'Token {USER_TOKEN}'
    url = f"{PLATFORM_URL.rstrip('/')}/api/bridge/{path}"
    return requests.request(method, url, headers=headers, timeout=35, **kwargs)


def _post_message(session_id: str, msg_type: str, content: dict, direction: str = 'from_claude'):
    try:
        _api('POST', f'session/{session_id}/message/',
             json={'type': msg_type, 'content': content, 'direction': direction})
    except Exception as e:
        _log(f"Failed to post message: {e}", 'WARN')


def _update_status(session_id: str, status: str, model_info: dict = None,
                   claude_sid: str = None, result_text: str = None):
    payload: dict = {'status': status}
    if model_info:
        payload['model_info'] = model_info
    if claude_sid:
        payload['claude_session_id'] = claude_sid
    if result_text is not None:
        payload['result_text'] = result_text
    try:
        _api('POST', f'session/{session_id}/status/', json=payload)
    except Exception as e:
        _log(f"Failed to update status: {e}", 'WARN')


# ─────────────────────────────────────────────────────────────
# Registration
# ─────────────────────────────────────────────────────────────

def _register() -> bool:
    global _connection_id
    cfg = {}
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH) as f:
                cfg = json.load(f)
        except Exception:
            pass

    saved_cid = cfg.get('connection_id', '')
    resp = _api('POST', 'connect/', json={
        'connection_id': saved_cid,
        'name': platform.node() or 'My Computer',
        'os_info': f"{platform.system()} {platform.release()}",
        'version': BRIDGE_VERSION,
    })
    if not resp.ok:
        _log(f"Registration failed: {resp.text}", 'ERROR')
        return False

    data = resp.json()
    _connection_id = data['connection_id']
    cfg['connection_id'] = _connection_id
    try:
        with open(CONFIG_PATH, 'w') as f:
            json.dump(cfg, f)
    except Exception:
        pass
    _log(f"Connected  id={_connection_id[:8]}…  "
         f"default priority=P{data.get('default_priority', 5)}", 'OK')
    return True


# ─────────────────────────────────────────────────────────────
# Claude Code runner
# ─────────────────────────────────────────────────────────────

def _build_cmd(prompt: str, permission_mode: str, resume_id: str = '') -> list:
    cmd = ['claude', '--output-format', 'stream-json', '--print', prompt]
    if resume_id:
        cmd += ['--resume', resume_id]
    if permission_mode == 'full_auto':
        cmd.append('--dangerously-skip-permissions')
    elif permission_mode == 'read_only':
        cmd += ['--allowedTools', 'Read,Glob,Grep,LS']
    return cmd


def _process_stream(proc, session_id: str) -> tuple:
    """Read stream-json lines from proc.stdout and relay to platform.
    Returns (claude_session_id, model_info, final_status, result_text)."""
    claude_sid   = ''
    model_info: dict = {}
    final_status = 'completed'
    result_text  = ''

    for raw_line in proc.stdout:
        if _cancel_flags.get(session_id):
            proc.terminate()
            _update_status(session_id, 'cancelled')
            return claude_sid, model_info, 'cancelled', result_text

        line = raw_line.strip()
        if not line:
            continue
        try:
            evt = json.loads(line)
        except json.JSONDecodeError:
            continue

        etype = evt.get('type', '')

        if etype == 'system' and evt.get('subtype') == 'init':
            claude_sid = evt.get('session_id', '')
            model_info = {
                'model': evt.get('model', ''),
                'tools': [t.get('name', t) if isinstance(t, dict) else str(t)
                          for t in evt.get('tools', [])],
            }
            _update_status(session_id, 'running', model_info, claude_sid)
            _post_message(session_id, 'system_init', {
                'claude_session_id': claude_sid,
                'model': model_info.get('model', ''),
                'tools': model_info.get('tools', []),
                'permission_mode': evt.get('permissionMode', ''),
            })
            _log(f"Session init  model={model_info.get('model','?')}", 'CLAUDE')

        elif etype == 'assistant':
            msg = evt.get('message', {})
            for block in msg.get('content', []):
                btype = block.get('type', '')
                if btype == 'text':
                    text = block.get('text', '')
                    if text:
                        _post_message(session_id, 'text', {'text': text})
                        _log(f"{text[:80]}{'…' if len(text)>80 else ''}", 'CLAUDE')
                elif btype == 'tool_use':
                    tool_name  = block.get('name', '')
                    tool_input = block.get('input', {})
                    tool_id    = block.get('id', '')
                    _post_message(session_id, 'tool_use', {
                        'tool_name': tool_name,
                        'tool_input': tool_input,
                        'tool_use_id': tool_id,
                    })
                    _log(f"Tool → {tool_name}", 'INFO')

        elif etype == 'user':
            for block in evt.get('message', {}).get('content', []):
                if block.get('type') == 'tool_result':
                    content = block.get('content', '')
                    if isinstance(content, list):
                        content = '\n'.join(
                            c.get('text', '') for c in content if c.get('type') == 'text'
                        )
                    _post_message(session_id, 'tool_result', {
                        'tool_use_id': block.get('tool_use_id', ''),
                        'content': str(content)[:3000],
                        'is_error': block.get('is_error', False),
                    })

        elif etype == 'result':
            is_error = evt.get('is_error', False)
            cost     = evt.get('total_cost_usd', 0) or 0
            usage    = evt.get('usage', {})
            result_text = evt.get('result', '')
            model_info.update({
                'total_cost_usd':    cost,
                'total_input_tokens':  usage.get('input_tokens', 0),
                'total_output_tokens': usage.get('output_tokens', 0),
            })
            final_status = 'error' if is_error else 'completed'
            _post_message(session_id, 'result', {
                'text': result_text,
                'is_error': is_error,
                'cost_usd': cost,
                'claude_session_id': claude_sid,
            })
            _log(f"{'Failed' if is_error else 'Done'}  cost=${cost:.4f}", 'OK' if not is_error else 'ERROR')

    try:
        err = proc.stderr.read()
        if err and proc.returncode not in (0, None):
            _post_message(session_id, 'error', {'text': err[:1000]})
            final_status = 'error'
    except Exception:
        pass

    proc.wait()
    return claude_sid, model_info, final_status, result_text


def _run_session(session_id: str, working_dir: str, prompt: str,
                 permission_mode: str, priority: int = 5):
    _log(f"[P{priority}] Starting {session_id[:8]}…  dir={working_dir}", 'QUEUE')
    _cancel_flags[session_id] = False

    wd = os.path.expanduser(working_dir)
    if not os.path.isdir(wd):
        _post_message(session_id, 'error', {'text': f"Directory not found: {working_dir}"})
        _update_status(session_id, 'error')
        return

    cmd = _build_cmd(prompt, permission_mode)
    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=wd, text=True, bufsize=1,
        )
        _active_procs[session_id] = proc
        claude_sid, model_info, final_status, result_text = _process_stream(proc, session_id)
        _update_status(session_id, final_status, model_info, claude_sid, result_text)
        _log(f"[P{priority}] Finished {session_id[:8]}  status={final_status}", 'OK')

    except FileNotFoundError:
        msg = ("'claude' command not found.\n"
               "Install: npm install -g @anthropic-ai/claude-code")
        _post_message(session_id, 'error', {'text': msg})
        _update_status(session_id, 'error')
        _log(msg, 'ERROR')
    except Exception as e:
        _post_message(session_id, 'error', {'text': str(e)})
        _update_status(session_id, 'error')
        _log(f"Session error: {e}", 'ERROR')
    finally:
        _active_procs.pop(session_id, None)
        _cancel_flags.pop(session_id, None)


def _run_followup(session_id: str, message: str, claude_sid: str, permission_mode: str):
    """Continue an existing session with a follow-up message."""
    _log(f"Follow-up for {session_id[:8]}…", 'INFO')
    _update_status(session_id, 'running')

    cmd = _build_cmd(message, permission_mode, resume_id=claude_sid)
    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1,
        )
        _active_procs[session_id] = proc
        new_sid, model_info, final_status, result_text = _process_stream(proc, session_id)
        _update_status(session_id, final_status, model_info, new_sid or claude_sid, result_text)
    except Exception as e:
        _post_message(session_id, 'error', {'text': str(e)})
        _update_status(session_id, 'error')
    finally:
        _active_procs.pop(session_id, None)


# ─────────────────────────────────────────────────────────────
# Command handler
# ─────────────────────────────────────────────────────────────

def _handle_command(cmd: dict):
    ctype = cmd.get('cmd_type')
    sid   = cmd.get('session_id', '')
    data  = cmd.get('data', {})

    if ctype == 'start_session':
        priority = data.get('priority', 5)
        t = threading.Thread(
            target=_run_session,
            args=(sid,
                  data.get('working_dir', '~'),
                  data.get('prompt', ''),
                  data.get('permission_mode', 'default'),
                  priority),
            daemon=True,
        )
        t.start()
        _log(f"[P{priority}] Dispatched {sid[:8]}…", 'OK')

    elif ctype == 'send_message':
        try:
            resp = _api('GET', f"sessions/{sid}/")
            if resp.ok:
                s = resp.json()
                claude_sid = s.get('claude_session_id', '')
                pmode      = s.get('permission_mode', 'default')
                if claude_sid:
                    t = threading.Thread(
                        target=_run_followup,
                        args=(sid, data.get('message', ''), claude_sid, pmode),
                        daemon=True,
                    )
                    t.start()
                else:
                    _log("No claude_session_id yet — cannot resume", 'WARN')
        except Exception as e:
            _log(f"send_message error: {e}", 'ERROR')

    elif ctype == 'cancel_session':
        _cancel_flags[sid] = True
        proc = _active_procs.get(sid)
        if proc:
            proc.terminate()
        _log(f"Cancelled {sid[:8]}…", 'WARN')


# ─────────────────────────────────────────────────────────────
# Priority queue poll loop (v2)
# ─────────────────────────────────────────────────────────────

def _queue_loop():
    _log("Priority queue polling every 2s…  Ctrl+C to stop.", 'INFO')
    print()
    consecutive_errors = 0

    while True:
        try:
            resp = _api('GET', f'queue/{_connection_id}/')
            if resp.ok:
                consecutive_errors = 0
                cmds = resp.json().get('commands', [])
                if cmds:
                    _log(f"Got {len(cmds)} command(s) from queue", 'INFO')
                for cmd in cmds:
                    _handle_command(cmd)
            elif resp.status_code == 401:
                _log("Authentication failed — check your token.", 'ERROR')
                sys.exit(1)
            else:
                _log(f"Queue returned {resp.status_code}", 'WARN')
        except requests.exceptions.ConnectionError:
            consecutive_errors += 1
            _log(f"Connection lost ({consecutive_errors}) — retry in 5s", 'WARN')
            time.sleep(5)
            continue
        except Exception as e:
            _log(f"Queue error: {e}", 'WARN')

        time.sleep(2)


# ─────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Claude Bridge Client v2')
    parser.add_argument('--token', default=USER_TOKEN,   help='Platform auth token')
    parser.add_argument('--url',   default=PLATFORM_URL, help='Platform base URL')
    parser.add_argument('--name',  default=None,         help='Connection display name')
    args = parser.parse_args()

    global USER_TOKEN, PLATFORM_URL
    USER_TOKEN   = args.token
    PLATFORM_URL = args.url.rstrip('/')

    print()
    print('  ╔══════════════════════════════════════════════╗')
    print('  ║   Claude Bridge Client  v' + BRIDGE_VERSION + '              ║')
    print('  ║   Local Claude Code → MineAI Platform        ║')
    print('  ║   Priority Queue · Webhook · Statistics       ║')
    print('  ╚══════════════════════════════════════════════╝')
    print()

    if USER_TOKEN in ('__USER_TOKEN__', ''):
        print('  Error: token not set.')
        print('  Download pre-configured script from the platform, or:')
        print('    python3 claude_bridge_client.py --token YOUR_TOKEN')
        sys.exit(1)

    try:
        r = subprocess.run(['claude', '--version'], capture_output=True, text=True, timeout=5)
        _log(f"Claude Code: {r.stdout.strip() or r.stderr.strip()}", 'OK')
    except FileNotFoundError:
        _log("'claude' not found — install it first:", 'ERROR')
        _log("  npm install -g @anthropic-ai/claude-code", 'INFO')
        sys.exit(1)
    except Exception:
        _log("Could not check claude version — proceeding anyway", 'WARN')

    _log(f"Platform: {PLATFORM_URL}", 'INFO')

    if not _register():
        sys.exit(1)

    try:
        _queue_loop()
    except KeyboardInterrupt:
        print()
        _log("Disconnecting…", 'INFO')
        _log("Goodbye!", 'OK')
        print()


if __name__ == '__main__':
    main()
