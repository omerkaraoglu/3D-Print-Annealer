"""Task 3: current firmware (first-order sigma-delta, one decision per full mains cycle).
Writes sigma_delta_results.json, plot_pst_current.png, plot_pinst_example.png."""
import json
import os
import sys

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import appliance as ap  # noqa: E402
import flickermeter as fl  # noqa: E402

LISTED = [0.02, 0.05, 0.1, 0.2, 0.25, 1 / 3, 0.4, 0.5, 0.6, 2 / 3, 0.75, 0.8, 0.9, 0.95, 0.98]
GRID = [round(x, 3) for x in np.arange(0.005, 0.9951, 0.005)]
OUT = os.path.join(HERE, 'sigma_delta_results.json')
LIM = {'pst': 1.0, 'plt': 0.65, 'd_c_pct': 3.3, 'd_max_pct': 4.0, 'T_max_s': 0.5}


def verdict(r):
    fails = []
    if r['pst'] > LIM['pst']:
        fails.append('P_st')
    if r['pst'] > LIM['plt']:          # constant duty: P_lt = P_st
        fails.append('P_lt')
    if r['d_c_pct'] > LIM['d_c_pct']:
        fails.append('d_c')
    if r['d_max_pct'] > LIM['d_max_pct']:
        fails.append('d_max')
    if r['T_max_s'] > LIM['T_max_s']:
        fails.append('T_max')
    return 'PASS' if not fails else 'FAIL (' + ', '.join(fails) + ')'


def main():
    cases = [('sd1', 1, d) for d in LISTED + GRID]
    res = ap.run_cases(cases, OUT)
    listed = [res[ap.key(('sd1', 1, d))] for d in LISTED]
    grid = sorted([res[ap.key(('sd1', 1, d))] for d in GRID], key=lambda r: r['duty_cmd'])
    for r in listed + grid:
        r['verdict'] = verdict(r)
    worst = max(grid + listed, key=lambda r: r['pst'])
    summary = {
        'limits': LIM,
        'listed': [{k: r[k] for k in ('duty_cmd', 'duty_real', 'pst', 'pinst_max', 'd_max_pct', 'd_c_pct',
                                        'T_max_s', 'changes_per_min', 'peaks_f_hz_amp_pct',
                                        'weighted_peaks_f_hz_amp_pct_wamp', 'verdict')} for r in listed],
        'grid_worst': {k: worst[k] for k in ('duty_cmd', 'pst', 'verdict')},
        'grid_pass_fraction_pst': float(np.mean([r['pst'] <= 1.0 for r in grid])),
        'grid_pass_fraction_plt': float(np.mean([r['pst'] <= 0.65 for r in grid])),
        'grid_duty_ranges_failing_pst': ranges([r['duty_cmd'] for r in grid if r['pst'] > 1.0]),
        'grid_duty_ranges_failing_plt': ranges([r['duty_cmd'] for r in grid if r['pst'] > 0.65]),
    }
    with open(OUT) as f:
        data = json.load(f)
    data['summary'] = summary
    with open(OUT, 'w') as f:
        json.dump(data, f, indent=0)
    print(json.dumps({k: v for k, v in summary.items() if k != 'listed'}, indent=1))
    for r in summary['listed']:
        print(f"{r['duty_cmd']:.4f} Pst {r['pst']:.3f} dmax {r['d_max_pct']:.3f} dc {r['d_c_pct']:.3f} "
              f"cpm {r['changes_per_min']:.0f} peaks {r['weighted_peaks_f_hz_amp_pct_wamp'][:2]} {r['verdict']}")

    # plot P_st vs duty
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.plot([r['duty_cmd'] for r in grid], [r['pst'] for r in grid], '-', color='#1f5fa8', lw=1.2,
            label='current firmware (1st-order sigma-delta, decision every cycle), 0.005 grid')
    ax.plot([r['duty_cmd'] for r in listed], [r['pst'] for r in listed], 'o', color='#1f5fa8', ms=4,
            label='listed duties')
    ax.axhline(1.0, color='#b02020', ls='--', lw=1, label='P_st limit 1.0')
    ax.axhline(0.65, color='#d08000', ls=':', lw=1, label='P_lt limit 0.65 (= P_st at constant duty)')
    ax.set_xlabel('pid_output (duty)')
    ax.set_ylabel('P_st')
    ax.set_xlim(0, 1)
    ax.set_ylim(0, None)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8, loc='upper right')
    ax.set_title('P_st vs duty, 1 kW heater on Zref = 0.40 + j0.25 ohm')
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, 'plot_pst_current.png'), dpi=130)
    plt.close(fig)

    # example P_inst trace at the worst listed duty
    wl = max(listed, key=lambda r: r['pst'])
    fm = fl.Flickermeter(fs=ap.FS)
    on = ap.make_pattern('sd1', 1, wl['duty_cmd'])
    p = fm.pinst(ap.waveform(on))[int(ap.PRE_S * fm.fsd):]
    t = np.arange(p.size) / fm.fsd
    on2 = ap.make_pattern('burst_dither', 1000, 0.5)
    p2 = fm.pinst(ap.waveform(on2))[int(ap.PRE_S * fm.fsd):]
    fig, (ax, ax2) = plt.subplots(2, 1, figsize=(8, 5.6))
    m = t < 3
    ax.plot(t[m], p[m], color='#1f5fa8', lw=0.8)
    ax.set_ylim(0, None)
    ax.set_xlabel('time in observation window (s)')
    ax.set_ylabel('P_inst')
    ax.set_title(f"current firmware, duty {wl['duty_cmd']:.3f}: P_st = {wl['pst']:.2f} (10 Hz/20 Hz modulation, 1200 changes/min)", fontsize=9)
    ax.grid(alpha=0.3)
    m2 = t < 60
    ax2.plot(t[m2], p2[m2], color='#c2410c', lw=0.8)
    ax2.set_ylim(0, None)
    ax2.set_xlabel('time in observation window (s)')
    ax2.set_ylabel('P_inst')
    ax2.set_title(f"recommended 20 s burst frame, duty 0.5: P_st = {fl.pst(p2):.2f} (2 changes per 20 s)", fontsize=9)
    ax2.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, 'plot_pinst_example.png'), dpi=130)
    plt.close(fig)


def ranges(vals, step=0.005):
    vals = sorted(vals)
    out = []
    for v in vals:
        if out and v - out[-1][1] <= step * 1.01:
            out[-1][1] = v
        else:
            out.append([v, v])
    return out


if __name__ == '__main__':
    main()
