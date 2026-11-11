#!/usr/bin/env python3
"""Probe native setup-window visibility and accessibility on a disposable CI runner."""
import json
import os
from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile
import time

if sys.platform != 'darwin' or os.environ.get('GITHUB_ACTIONS') != 'true' or os.environ.get('RUNNER_ENVIRONMENT') != 'github-hosted':
    raise SystemExit('A disposable GitHub-hosted macOS runner is required')
root = Path(__file__).resolve().parents[1]
app = root / 'browser-extension/build/safari-development-derived/Build/Products/Release/Super-SAG Web Clipper.app'
info = plistlib.loads((app / 'Contents/Info.plist').read_bytes())
binary = app / 'Contents/MacOS' / info['CFBundleExecutable']
swift = r'''
import Foundation
import CoreGraphics
let target = Int32(CommandLine.arguments[1])!
let windows = CGWindowListCopyWindowInfo([.optionOnScreenOnly, .excludeDesktopElements], kCGNullWindowID) as? [[String: Any]] ?? []
let owned = windows.filter { window in
    (window[kCGWindowOwnerPID as String] as? NSNumber)?.int32Value == target &&
    (window[kCGWindowLayer as String] as? NSNumber)?.intValue == 0
}
print(owned.count)
'''
with tempfile.TemporaryDirectory(prefix='super-sag-gui-probe-', dir=os.environ['RUNNER_TEMP']) as temporary:
    temporary = Path(temporary)
    swift_source = temporary / 'windows.swift'
    swift_source.write_text(swift)
    probe = temporary / 'windows'
    subprocess.run(['swiftc', str(swift_source), '-o', str(probe)], check=True)
    process = subprocess.Popen([str(binary)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    result = {'scope': 'Safari development setup app; not the desktop app or Safari enablement', 'pid_started': process.pid}
    try:
        deadline = time.monotonic() + 30
        count = 0
        while process.poll() is None and time.monotonic() < deadline:
            window_probe = subprocess.run([str(probe), str(process.pid)], text=True, capture_output=True, timeout=15)
            result['window_probe_exit'] = window_probe.returncode
            if window_probe.returncode == 0 and window_probe.stdout.strip().isdigit():
                count = int(window_probe.stdout.strip())
            if count:
                break
            time.sleep(1)
        result['process_alive'] = process.poll() is None
        result['visible_window_count'] = count
        if process.poll() is None and count:
            statement = f'tell application "System Events" to tell (first application process whose unix id is {process.pid}) to perform action "AXRaise" of window 1'
            try:
                accessibility = subprocess.run(['osascript', '-e', statement], text=True, capture_output=True, timeout=15)
                result['accessibility_raise_exit'] = accessibility.returncode
                result['accessibility_error'] = accessibility.stderr.strip()[:500]
            except subprocess.TimeoutExpired:
                result['accessibility_error'] = 'Timed out; UI automation may require interactive permissions'
        print(json.dumps(result, indent=2))
        if not result['process_alive'] or count < 1 or result.get('accessibility_raise_exit') != 0:
            raise RuntimeError('The native setup window was not visible and accessible to System Events')
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
