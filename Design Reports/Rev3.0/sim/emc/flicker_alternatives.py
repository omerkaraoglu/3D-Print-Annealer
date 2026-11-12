"""Task 4: alternative full-cycle switching patterns. Writes alternatives_results.json
(per-case cache + per-family summary) and plot_pst_alternatives.png."""
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

LISTED = [0.02, 0.05, 0.1, 0.2, 0.25, 1 / 3, 0.4, 0.5, 0.6, 2 / 3, 0.75, 0.8, 0.9, 0.95, 0.98]
GRID = [round(x, 3) for x in np.arange(0.01, 0.9901, 0.01)]
DUTIES = sorted(set([round(d, 6) for d in LISTED + GRID]))
FAMILIES = ([('sd1', K) for K in (1, 2, 4, 8, 16, 25, 50, 100, 250, 500, 1000)]
            + [('burst', N) for N in (50, 100, 250, 500, 1000, 1500, 3000)]
            + [('burst_dither', N) for N in (250, 500, 1000, 1500)]
            + [('sd2', K) for K in (1, 50)])
OUT = os.path.join(HERE, 'alternatives_results.json')
RECOMMENDED = ('burst_dither', 1000)


def label(fam, par):
    if fam == 'sd1':
        return f'1st-order SD, decision every {par} cycle(s) ({par * 20} ms)' + (' [current firmware]' if par == 1 else '')
    if fam == 'sd2':
        return f'2nd-order SD, decision every {par} cycle(s) ({par * 20} ms)'
    if fam == 'burst':
        return f'burst PWM, period {par} cycles ({par / 50:g} s), on = round(d*N)'
    return f'burst PWM + error carry, period {par} cycles ({par / 50:g} s)'


def duty_step(fam, par):
    if fam in ('sd1', 'sd2'):
        return '1/65536 (mean); burst quantum %d cycle(s)' % par
    if fam == 'burst':
        return f'1/{par} = {100 / par:.3g} %'
    return f'1/65536 (mean); per period 1/{par}'


def main():
    cases = [(f, p, d) for f, p in FAMILIES for d in DUTIES]
    res = ap.run_cases(cases, OUT)
    summ = []
    for f, p in FAMILIES:
        rs = sorted([res[ap.key((f, p, d))] for d in DUTIES], key=lambda r: r['duty_cmd'])
        w = max(rs, key=lambda r: r['pst'])
        sp = [r['longest_on_spacing_s'] for r in rs if r['longest_on_spacing_s'] is not None]
        summ.append({
            'family': f, 'param': p, 'label': label(f, p), 'duty_step': duty_step(f, p),
            'pst_worst': w['pst'], 'duty_at_worst': w['duty_cmd'],
            'pst_median': float(np.median([r['pst'] for r in rs])),
            'all_pass_pst_1.0': all(r['pst'] <= 1.0 for r in rs),
            'all_pass_plt_0.65': all(r['pst'] <= 0.65 for r in rs),
            'all_pass_0.8': all(r['pst'] <= 0.8 for r in rs),
            'd_max_pct_worst': max(r['d_max_pct'] for r in rs),
            'd_c_pct_worst': max(r['d_c_pct'] for r in rs),
            'T_max_s_worst': max(r['T_max_s'] for r in rs),
            'max_changes_per_min': max(r['changes_per_min'] for r in rs),
            'thermal_ripple_pp_pct_worst': {t: max(r['thermal_ripple_pp_pct'][t] for r in rs) for t in ('60', '180', '300')},
            'longest_power_period_s_worst': max(sp) if sp else None,
            'duty_error_worst_pct': 100 * max(abs(r['duty_real'] - r['duty_cmd']) for r in rs),
        })
    with open(OUT) as fh:
        data = json.load(fh)
    data['summary'] = summ
    with open(OUT, 'w') as fh:
        json.dump(data, fh, indent=0)
    for s in summ:
        print(f"{s['label']:<62} worst {s['pst_worst']:.3f} @ {s['duty_at_worst']:.3f}  med {s['pst_median']:.3f}  "
              f"<=0.8 {s['all_pass_0.8']}  dc {s['d_c_pct_worst']:.2f}  cpm {s['max_changes_per_min']:.0f}  "
              f"ripple(60/180/300 s) {s['thermal_ripple_pp_pct_worst']['60']:.2f}/{s['thermal_ripple_pp_pct_worst']['180']:.2f}/"
              f"{s['thermal_ripple_pp_pct_worst']['300']:.2f} %  Tpow {s['longest_power_period_s_worst']}  derr {s['duty_error_worst_pct']:.2f} %")

    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    show = [('sd1', 1, '#1f5fa8', '-'), ('sd1', 50, '#7a7a7a', '-'), ('burst', 500, '#2a9d55', '--'),
            ('sd2', 1, '#9a4fb5', ':'), RECOMMENDED + ('#c2410c', '-')]
    for f, p, c, ls in show:
        rs = sorted([res[ap.key((f, p, d))] for d in DUTIES], key=lambda r: r['duty_cmd'])
        lw = 2.2 if (f, p) == RECOMMENDED else 1.2
        lab = label(f, p) + (' [recommended]' if (f, p) == RECOMMENDED else '')
        ax.plot([r['duty_cmd'] for r in rs], [r['pst'] for r in rs], ls, color=c, lw=lw, label=lab)
    ax.axhline(1.0, color='#b02020', ls='--', lw=1, label='P_st limit 1.0')
    ax.axhline(0.65, color='#d08000', ls=':', lw=1, label='P_lt limit 0.65')
    ax.set_xlabel('duty')
    ax.set_ylabel('P_st')
    ax.set_xlim(0, 1)
    ax.set_ylim(0, None)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=7, loc='upper right')
    ax.set_title('P_st vs duty: current firmware and alternatives (1 kW, Zref)')
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, 'plot_pst_alternatives.png'), dpi=130)
    plt.close(fig)


if __name__ == '__main__':
    main()
