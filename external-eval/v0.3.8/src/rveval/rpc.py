"""Bounded newline-JSON RPC v2. Persistent worker; no implicit retries.

Not a sandbox. Use a network/FS-isolated worker for untrusted benchmark code.
"""
from __future__ import annotations
import os
import math
import selectors
import shlex
import signal
import subprocess
import sys
import time
from pathlib import Path
from .canonical import canonical_bytes, loads
from .guardrails import ProtocolError, UnsupportedError, IntegrityError

PROTOCOL="rveval.rpc.v2"

class JsonProcess:
    def __init__(self, config, base_dir):
        if os.name != "posix":
            raise UnsupportedError("PIPE_SELECTOR_RPC_REQUIRES_POSIX")
        raw=config["command"]
        self.command=raw if type(raw) is list else shlex.split(raw)
        if not self.command or any(type(arg) is not str or not arg for arg in self.command):
            raise ValueError("RPC_COMMAND_INVALID")
        self.command=[sys.executable if arg=="{python}" else arg for arg in self.command]
        self.cwd=(Path(base_dir)/config.get("cwd", ".")).resolve()
        self.timeout=float(config.get("timeout_seconds", 120))
        self.max_bytes=int(config.get("max_message_bytes", 8 * 1024 * 1024))
        if not math.isfinite(self.timeout) or self.timeout<=0 or self.max_bytes<128: raise ValueError("RPC_LIMITS_INVALID")
        self.env={k:os.environ[k] for k in ("PATH","SYSTEMROOT","LANG","LC_ALL","PYTHONPATH") if k in os.environ}
        for key in config.get("env_allowlist", []):
            if key not in os.environ: raise ValueError("REQUIRED_ENV_UNAVAILABLE:"+key)
            self.env[key]=os.environ[key]
        self.process=None; self.buffer=b""; self.sequence=0; self.closed=False
    def _start(self):
        self.process=subprocess.Popen(self.command, cwd=self.cwd, env=self.env,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            bufsize=0, start_new_session=(os.name=="posix"))
    def _line(self, deadline):
        assert self.process and self.process.stdout
        with selectors.DefaultSelector() as sel:
            sel.register(self.process.stdout, selectors.EVENT_READ)
            while b"\n" not in self.buffer:
                remaining=deadline-time.monotonic()
                if remaining<=0 or not sel.select(remaining): raise TimeoutError("RPC_RESPONSE_TIMEOUT")
                block=os.read(self.process.stdout.fileno(), 65536)
                if not block: raise ProtocolError("RPC_EOF_BEFORE_RESPONSE")
                self.buffer+=block
                if len(self.buffer)>self.max_bytes: raise ProtocolError("RPC_RESPONSE_TOO_LARGE")
        line,self.buffer=self.buffer.split(b"\n",1)
        return line
    def call(self, op, **payload):
        if self.closed:
            raise ProtocolError("RPC_CHANNEL_CLOSED_NO_RESTART")
        rid=str(self.sequence); self.sequence+=1
        request={"protocol":PROTOCOL,"request_id":rid,"op":op,"payload":payload}
        encoded=canonical_bytes(request)+b"\n"
        if len(encoded)>self.max_bytes: raise ProtocolError("RPC_REQUEST_TOO_LARGE")
        deadline=time.monotonic()+self.timeout
        try:
            if self.process is None: self._start()
            assert self.process and self.process.stdin
            # Nonblocking write bounds timeout even if the worker stops reading stdin.
            fd=self.process.stdin.fileno(); os.set_blocking(fd,False)
            view=memoryview(encoded)
            with selectors.DefaultSelector() as sel:
                sel.register(fd,selectors.EVENT_WRITE)
                while view:
                    remaining=deadline-time.monotonic()
                    if remaining<=0 or not sel.select(remaining): raise TimeoutError("RPC_REQUEST_TIMEOUT")
                    try: n=os.write(fd,view)
                    except BlockingIOError: continue
                    view=view[n:]
            value=loads(self._line(deadline))
            if type(value) is not dict or value.get("protocol")!=PROTOCOL or value.get("request_id")!=rid:
                raise ProtocolError("RPC_CORRELATION_MISMATCH")
            if value.get("ok") is False:
                error=value.get("error",{})
                if error.get("category")=="UNSUPPORTED": raise UnsupportedError(error.get("code","RPC_UNSUPPORTED"))
                if error.get("category")=="INTEGRITY_ERROR": raise IntegrityError(error.get("code","RPC_INTEGRITY"))
                raise ProtocolError("RPC_REMOTE_ERROR")
            if value.get("ok") is not True or type(value.get("result")) is not dict:
                raise ProtocolError("RPC_RESULT_SHAPE_INVALID")
            return value["result"]
        except BaseException:
            self.close(); raise
    def close(self):
        self.closed=True
        p=self.process
        if p is not None:
            from .process_control import terminate_group
            terminate_group(p, graceful=True, grace_seconds=0.5)
            for stream in (p.stdin,p.stdout):
                if stream: stream.close()
        self.process=None; self.buffer=b""


def serve(handler):
    """Reference worker loop; stdout is protocol-only, diagnostics go to stderr."""
    for raw in sys.stdin.buffer:
        rid=None
        try:
            req=loads(raw); rid=req["request_id"]
            if req.get("protocol")!=PROTOCOL: raise ProtocolError("RPC_VERSION_UNSUPPORTED")
            result=handler(req["op"],req["payload"])
            if type(result) is not dict: raise ProtocolError("RPC_HANDLER_RESULT_INVALID")
            response={"protocol":PROTOCOL,"request_id":rid,"ok":True,"result":result}
        except Exception as exc:
            category="UNSUPPORTED" if isinstance(exc,UnsupportedError) else "INTEGRITY_ERROR" if isinstance(exc,IntegrityError) else "INFRASTRUCTURE_ERROR"
            response={"protocol":PROTOCOL,"request_id":rid,"ok":False,
                      "error":{"category":category,"code":type(exc).__name__}}
        sys.stdout.buffer.write(canonical_bytes(response)+b"\n");sys.stdout.buffer.flush()
