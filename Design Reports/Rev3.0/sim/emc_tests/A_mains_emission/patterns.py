"""Heater firing patterns, one boolean per full mains cycle.

current : bit-exact model of AnnealerFirmware.ino.ino SECTION 7 (zcd_isr, lines 765-795): 16-bit increment
          sd_increment = (uint16_t)(p*65535 + 0.5) (line 1946), acc += inc once per full cycle, fire the whole
          cycle when acc >= 65536 (then acc -= 65536); inc == 0 -> no firing, acc reset.
decided : 20 s burst frame with error carry (spec 10 item 5, not implemented): at frame start
          acc += inc*1000; n_on = acc >> 16; acc &= 0xFFFF; fire for cyc < n_on (1000-cycle frame).
"""
import numpy as np


def increment(duty):
    return int(duty * 65535.0 + 0.5)


def current_fw(duty, n, acc0=0):
    inc = increment(duty)
    if inc == 0:
        return np.zeros(n, bool)
    j = np.arange(n + 1, dtype=np.int64)
    tot = acc0 + j * inc
    return np.diff(tot // 65536) > 0


def decided_fw(duty, n, frame=1000, acc0=0):
    inc = increment(duty)
    nf = -(-n // frame)
    out = np.zeros(nf * frame, bool)
    acc = acc0
    for k in range(nf):
        acc += inc * frame
        n_on = acc >> 16
        acc &= 0xFFFF
        out[k * frame:k * frame + n_on] = True
    return out[:n]


PATTERNS = {"current": current_fw, "decided": decided_fw}


if __name__ == "__main__":
    for d in (0.1, 0.5, 1 / 3):
        print(d, current_fw(d, 12).astype(int), decided_fw(d, 3000).mean())
