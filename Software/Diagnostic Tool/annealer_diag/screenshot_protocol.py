"""
Shared parser for the firmware's SHOT / SHOT ALL screenshot stream.

The firmware emits text-framed binary tiles on its serial port. The
wire format is documented in sketch_apr16a.ino near g_shot_active.

Both the standalone screenshot.py script and the diag tool's
ScreenshotView use this module so a change in one place updates both.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterator

BEGIN_RE = re.compile(rb"<<SHOT_BEGIN w=(\d+) h=(\d+) fmt=(\S+) name=(\S+)>>")
TILE_RE  = re.compile(rb"<<SHOT_TILE x=(\d+) y=(\d+) w=(\d+) h=(\d+) bytes=(\d+)>>")
END_RE   = re.compile(rb"<<SHOT_END>>")


@dataclass
class Frame:
    """One completed screenshot, ready for save_png() or display."""
    name: str
    w: int
    h: int
    big_endian: bool
    rgb888: bytes


def rgb565_to_rgb888(buf: bytes, w: int, h: int, big_endian: bool) -> bytes:
    """Convert RGB565 → RGB888 with proper bit-replication on the low bits.

    big_endian=True for LV_COLOR_16_SWAP=1 (panel-native byte order),
    False for the default host little-endian layout.
    """
    out = bytearray(w * h * 3)
    j = 0
    for i in range(w * h):
        b0 = buf[i * 2]
        b1 = buf[i * 2 + 1]
        v = (b0 << 8) | b1 if big_endian else (b1 << 8) | b0
        r5 = (v >> 11) & 0x1F
        g6 = (v >> 5)  & 0x3F
        b5 = v & 0x1F
        out[j]     = (r5 << 3) | (r5 >> 2)
        out[j + 1] = (g6 << 2) | (g6 >> 4)
        out[j + 2] = (b5 << 3) | (b5 >> 2)
        j += 3
    return bytes(out)


def read_line(ser, timeout_s: float) -> bytes | None:
    """Read one LF-terminated line, stripping the trailing CR. None on timeout."""
    deadline = time.monotonic() + timeout_s
    buf = bytearray()
    while time.monotonic() < deadline:
        b = ser.read(1)
        if not b:
            continue
        if b == b"\n":
            if buf and buf[-1:] == b"\r":
                buf.pop()
            return bytes(buf)
        buf += b
    return None


def read_exact(ser, n: int, timeout_s: float) -> bytes | None:
    """Read exactly n bytes within timeout, else None."""
    deadline = time.monotonic() + timeout_s
    out = bytearray()
    while len(out) < n and time.monotonic() < deadline:
        chunk = ser.read(n - len(out))
        if chunk:
            out += chunk
    return bytes(out) if len(out) == n else None


def drain_input(ser, settle_s: float = 0.05) -> None:
    """Discard whatever's currently buffered on the serial port."""
    while ser.in_waiting:
        ser.read(ser.in_waiting)
        time.sleep(settle_s)


def capture_frames(
    ser,
    command: str,
    *,
    idle_timeout_s: float = 6.0,
    post_frame_timeout_s: float = 1.5,
    progress: Callable[[str, str], None] | None = None,
) -> Iterator[Frame]:
    """Send a SHOT / SHOT ALL command and yield Frames as they complete.

    The serial port must be owned exclusively by the caller while this
    generator runs — any concurrent reader would steal bytes and break
    the binary tile parser.

    Timeout semantics:
      • Before the first frame ends, any line (including non-protocol
        firmware chatter) resets the idle clock — the firmware may be
        booting / printing connect logs before it gets to SHOT.
      • After the first END marker we wait `post_frame_timeout_s` for
        the next BEGIN, and ONLY protocol markers reset the clock. This
        prevents the firmware's 500 ms telemetry print from keeping the
        generator alive forever once SHOT (or the final screen of
        SHOT ALL) finishes.

    progress: optional callback(kind, detail) for UI updates. kind is
    one of {"sent", "begin", "tile", "end", "log", "warn"}.
    """
    def emit(kind: str, detail: str = "") -> None:
        if progress is not None:
            progress(kind, detail)

    drain_input(ser)
    ser.write((command + "\n").encode("ascii"))
    ser.flush()
    emit("sent", command)

    fb = None
    frame_w = frame_h = 0
    frame_name = ""
    frame_big_endian = False
    seen_any_frame = False
    last_activity = time.monotonic()

    while True:
        active_timeout = post_frame_timeout_s if seen_any_frame else idle_timeout_s
        if time.monotonic() - last_activity > active_timeout:
            return

        line = read_line(ser, timeout_s=1.0)
        if line is None:
            continue

        m = BEGIN_RE.search(line)
        if m:
            frame_w = int(m.group(1))
            frame_h = int(m.group(2))
            fmt = m.group(3).decode()
            frame_name = m.group(4).decode()
            if fmt == "rgb565_le":
                frame_big_endian = False
            elif fmt == "rgb565_be":
                frame_big_endian = True
            else:
                emit("warn", f"unsupported fmt: {fmt}")
                fb = None
                last_activity = time.monotonic()
                continue
            fb = bytearray(frame_w * frame_h * 2)
            emit("begin", f"{frame_name} ({frame_w}x{frame_h}, {fmt})")
            last_activity = time.monotonic()
            continue

        m = TILE_RE.search(line)
        if m and fb is not None:
            tx = int(m.group(1)); ty = int(m.group(2))
            tw = int(m.group(3)); th = int(m.group(4))
            nbytes = int(m.group(5))
            data = read_exact(ser, nbytes, timeout_s=30.0)
            if data is None:
                emit("warn", "timeout reading tile bytes")
                fb = None
                last_activity = time.monotonic()
                continue
            # Consume the trailing CRLF the firmware writes after the binary.
            read_line(ser, timeout_s=2.0)
            for row in range(th):
                src = row * tw * 2
                dst = ((ty + row) * frame_w + tx) * 2
                fb[dst:dst + tw * 2] = data[src:src + tw * 2]
            emit("tile", f"y={ty}+{th}")
            last_activity = time.monotonic()
            continue

        if END_RE.search(line):
            if fb is not None:
                rgb = rgb565_to_rgb888(fb, frame_w, frame_h, frame_big_endian)
                emit("end", frame_name)
                yield Frame(frame_name, frame_w, frame_h, frame_big_endian, rgb)
                fb = None
                seen_any_frame = True
            last_activity = time.monotonic()
            continue

        # Unrelated firmware log output. Forward it for visibility but
        # only treat it as "activity" before the first frame ends — once
        # we've yielded a frame, only protocol markers may extend the
        # wait, otherwise the periodic telemetry would block forever.
        try:
            text = line.decode(errors="replace").strip()
            if text:
                emit("log", text)
        except Exception:
            pass
        if not seen_any_frame:
            last_activity = time.monotonic()


def save_png(frame: Frame, out_dir: Path, scale: int = 4) -> list[Path]:
    """Write the native PNG (and optionally an Nx nearest-neighbor upscale).

    Returns the list of paths written. Requires Pillow.
    """
    from PIL import Image  # local import so callers without Pillow can still
                           # use capture_frames() to drive their own renderers

    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    img = Image.frombytes("RGB", (frame.w, frame.h), frame.rgb888)

    paths: list[Path] = []
    native = out_dir / f"{frame.name}_{stamp}.png"
    img.save(native)
    paths.append(native)

    if scale and scale > 1:
        big = img.resize((frame.w * scale, frame.h * scale), Image.NEAREST)
        big_path = out_dir / f"{frame.name}_{stamp}_{scale}x.png"
        big.save(big_path)
        paths.append(big_path)

    return paths
