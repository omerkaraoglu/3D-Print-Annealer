"""Behavioural model of the current firmware's ZCD ISR (AnnealerFirmware.ino.ino, SECTION 7, lines 765-795)
under EFT bursts (spurious falling edges at /ZCD), and of the proposed debounce (P-E2).

ISR as written: every falling edge -> on even edges (sd_half_idx == 0) a sigma-delta decision; sd_half_idx ^= 1;
if sd_fire_cycle: delayMicroseconds(230); TRIG high 150 us; TRIG low.  The ISR blocks ~380 us when firing;
an edge arriving while the ISR runs is latched by the GPIO interrupt status bit and serviced once afterwards
(several edges collapse into one).  Mains 50 Hz, real edges ~225 us before each zero crossing (ASM, H11AA1 window).
Triac: fires when TRIG is high and |v| is enough to latch (ASM > 10 V); conducts until the next current zero.
Burst: 75 edges at 5 kHz every 300 ms (NRS), every burst edge assumed to produce a false edge (worst case).
Outputs: heater energy vs the commanded duty, number of non-zero-phase turn-ons, firing while commanded off.
"""
import numpy as np
import common as cm

F = 50.0
T = 1 / F


def simulate(duty, burst=True, debounce_us=0.0, seconds=6.0, seed=1):
    rng = np.random.default_rng(seed)
    inc = int(round(duty * 65536)) if duty > 0 else 0
    edges = [(k * T / 2 - 225e-6, 'real') for k in range(1, int(seconds * 2 * F))]
    if burst:
        t0 = 0.0137
        while t0 < seconds:
            ph = rng.uniform(0, 200e-6)
            edges += [(t0 + ph + j * 200e-6, 'eft') for j in range(75)]
            t0 += 0.300
    edges.sort()
    acc = 0; half = 0; fire = False; busy_until = -1; pending = False; last_acc = -1.0
    fires = []          # (time of TRIG rising, source)
    for t, src in edges:
        if t < busy_until:
            pending = True; continue
        if debounce_us and src == 'eft':
            # P-E2: level-qualified edge -- the ISR (or a 50 us one-shot) re-reads /ZCD and accepts the edge only
            # if the pin is still low 50 us later.  A real ZCD low window lasts ~450 us; the EFT-induced pulses at
            # the ZCD node last < 1 us (sim_eft.py, 'ZC_false_pulse_width_ns'), so every EFT edge is rejected.
            continue
        last_acc = t
        if half == 0:
            if inc == 0:
                fire = False; acc = 0
            else:
                acc += inc; fire = acc >= 65536
                if fire: acc -= 65536
        half ^= 1
        if fire:
            fires.append((t + 230e-6, src)); busy_until = t + 380e-6
    # heater conduction: a fire at time tf turns the triac on (if |v| >~ 10 V or it is already the start of a half
    # cycle) until the next zero crossing
    on = np.zeros(int(seconds * 2 * F) + 2)       # per half-cycle conducted fraction
    nonzero = 0
    for tf, src in fires:
        k = int(np.floor(tf / (T / 2)))
        ph = (tf - k * T / 2) / (T / 2)            # 0..1 within the half cycle
        v = 325 * np.sin(np.pi * ph)
        if v < 10 and ph > 0.5:
            continue                               # too close to the end: does not latch
        frac = 1.0 - ph if ph > 0.05 else 1.0
        if ph > 0.05 and on[k] == 0:
            nonzero += 1
        on[k] = max(on[k], frac)
    # energy (resistive heater, sin^2 weighting)
    e = 0.0
    for k, fr in enumerate(on):
        if fr <= 0: continue
        ph0 = 1 - fr
        e += (fr - (np.sin(2 * np.pi * 1.0) - np.sin(2 * np.pi * ph0)) / (2 * np.pi)) if fr < 1 else 1.0
    power = e / (seconds * 2 * F)
    return {'duty_cmd': duty, 'power_frac': power, 'error_pct_of_full': (power - duty) * 100,
            'nonzero_phase_turn_ons': nonzero, 'fires': len(fires),
            'fires_from_eft_edges': sum(1 for f in fires if f[1] == 'eft')}


def main():
    out = {'current_firmware': {}, 'P_E2_level_qualified_50us': {}}
    for d in (0.0, 0.2, 0.5, 0.8, 1.0):
        out['current_firmware'][f'{d}'] = {'no_burst': simulate(d, burst=False), 'burst': simulate(d)}
        out['P_E2_level_qualified_50us'][f'{d}'] = {'burst': simulate(d, debounce_us=50)}
    out['notes'] = ('duty 0 -> no firing at all with or without bursts (inc == 0 forces sd_fire_cycle false); '
                    'bursts only redistribute and add firings while the controller is heating. The PID loop '
                    'corrects the power error within its thermal time constant; criterion B allows degradation during '
                    'the test. P-E2: accept a falling edge only if /ZCD is still low 50 us later (level qualification); a window gate (9-11 ms) was also modelled and is worse because 5 kHz burst edges fall inside any window.')
    cm.save_results('eft_firmware', out)
    for k, v in out.items():
        print(k, v)


if __name__ == '__main__':
    main()
