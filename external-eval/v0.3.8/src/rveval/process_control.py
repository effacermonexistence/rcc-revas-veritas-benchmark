"""Bounded lifecycle for trusted native processes; not an OS security sandbox.

POSIX children get separate groups. Cancellation is relayed through each managed
coordinator before a final group kill. Native code must not daemonize, change
sessions, replace the coordinator handlers or launch untracked remote work.
Windows fallback controls only the direct child; no Windows tree claim is made.
"""
from contextlib import contextmanager
import os
import signal
import subprocess
import threading
import psutil


def terminate_group(process, *, graceful=False, grace_seconds=1.0):
    """Cancel, kill remaining inherited descendants, and reap the group leader."""
    # Capture child process identities BEFORE the leader can exit/reparent them.
    # psutil Process.kill checks PID reuse. No cleanup claim covers remote work
    # or children deliberately detached before this snapshot.
    descendants = []
    try:
        descendants = psutil.Process(process.pid).children(recursive=True)
    except psutil.NoSuchProcess:
        pass
    def send(sig):
        try:
            if os.name == 'posix':
                os.killpg(process.pid, sig)
            elif process.poll() is None:
                process.kill()
        except ProcessLookupError:
            pass
    if graceful and process.poll() is None:
        send(signal.SIGTERM)
        try:
            process.wait(timeout=grace_seconds)
        except subprocess.TimeoutExpired:
            pass
    send(signal.SIGKILL if os.name == 'posix' else signal.SIGTERM)
    for child in reversed(descendants):
        try:
            child.kill()
        except psutil.NoSuchProcess:
            pass
    process.wait()
    # Child process identity is retained across leader exit. A zombie has no
    # executable work left; reaping grandchildren belongs to their OS parent.
    _, alive = psutil.wait_procs(descendants, timeout=1.0)
    executing = []
    for child in alive:
        try:
            if child.status() != psutil.STATUS_ZOMBIE:
                executing.append(child.pid)
        except psutil.NoSuchProcess:
            pass
    if executing:
        raise RuntimeError('PROCESS_CLEANUP_INCOMPLETE')


@contextmanager
def managed_process(command, **kwargs):
    """Parent cancellation cannot abandon a separately grouped managed child.

    Main-thread SIGTERM/SIGINT handlers are installed before spawning. A signal
    arriving during Popen is recorded and replayed after the child is registered.
    Previous handlers are restored on every exit. Background-thread use still
    performs ordinary finalization but does not replace process-wide handlers.
    """
    active = {'process': None, 'pending': None, 'closing': False}
    previous = {}
    def cancelled(signum, frame):
        if active['closing']:
            return
        process = active['process']
        if process is None:
            active['pending'] = signum
            return
        active['closing'] = True
        terminate_group(process, graceful=True)
        raise SystemExit(128 + signum)
    if threading.current_thread() is threading.main_thread():
        for sig in (signal.SIGTERM, signal.SIGINT):
            previous[sig] = signal.getsignal(sig)
            signal.signal(sig, cancelled)
    try:
        process = subprocess.Popen(command, start_new_session=os.name == 'posix', **kwargs)
        active['process'] = process
        if active['pending'] is not None:
            cancelled(active['pending'], None)
        yield process
    finally:
        try:
            if active['process'] is not None:
                terminate_group(active['process'])
        finally:
            for sig, handler in previous.items():
                signal.signal(sig, handler)
