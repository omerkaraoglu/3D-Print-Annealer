"""Validate flickermeter.py against the IEC 61000-4-15 test points.
Writes validation.json and validation.md (idempotent; cached results reused)."""
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import flickermeter as fl  # noqa: E402

FS = 4000.0
PRE = 30.0      # s pre-roll discarded
TOBS = 600.0    # s observation
RECT = [(1, 2.724), (2, 2.211), (7, 1.459), (39, 0.906), (110, 0.725), (1620, 0.402), (4000, 2.40), (4800, 4.834)]
OUT_JSON = os.path.join(HERE, 'validation.json')

_FM = {}


def _fm(hp):
    if hp not in _FM:
        _FM[hp] = fl.Flickermeter(fs=FS, hp_order=hp)
    return _FM[hp]


def run_rect(args):
    cpm, dvv_pct, hp, phase_deg = args
    fm = _fm(hp)
    t_off = 5.0 + (phase_deg / 360.0) / 50.0
    v = fl.rect_modulated(FS, PRE + TOBS, dvv_pct / 100.0, cpm, t_offset=t_off)
    p = fm.pinst(v)[int(PRE * fm.fsd):]
    return {'kind': 'rect', 'cpm': cpm, 'dvv_pct': dvv_pct, 'hp_order': hp, 'phase_deg': phase_deg,
            'pst_cpf': fl.pst(p, 'cpf'), 'pst_exact': fl.pst(p, 'exact'), 'pinst_max': float(p.max())}


def run_sine(args):
    fmod, dvv_pct, hp = args
    fm = _fm(hp)
    v = fl.sine_modulated(FS, 60.0, dvv_pct / 100.0, fmod)
    p = fm.pinst(v)[int(20 * fm.fsd):]
    return {'kind': 'sine', 'f_hz': fmod, 'dvv_pct': dvv_pct, 'hp_order': hp,
            'pinst_max': float(p.max()), 'pinst_mean': float(p.mean())}


def main():
    t0 = time.time()
    jobs_rect = []
    for hp in (1, 6):
        for cpm, dvv in RECT:
            phases = (0, 45, 90, 135, 180, 225, 270, 315) if cpm >= 1620 else (0,)
            for ph in phases:
                jobs_rect.append((cpm, dvv, hp, ph))
    jobs_sine = [(8.8, 0.250, 1), (8.8, 0.250, 6)]
    with ProcessPoolExecutor(max_workers=max(1, os.cpu_count() - 2)) as ex:
        res_r = list(ex.map(run_rect, jobs_rect))
        res_s = list(ex.map(run_sine, jobs_sine))
    fm = _fm(1)
    out = {'fs_hz': FS, 'decimation': fm.dec, 'pre_roll_s': PRE, 'observation_s': TOBS,
           'calibration_gain': fm.gain, 'rect': res_r, 'sine': res_s,
           'runtime_s': time.time() - t0}
    with open(OUT_JSON, 'w') as f:
        json.dump(out, f, indent=1)
    write_md(out)


def write_md(out):
    lines = ['| changes/min | dV/V (%) | P_st (HP 1st order, phase 0) | dev. | P_st (HP 6th order) | dev. | phase spread (HP 1st order, min..max over 8 carrier phases) |',
             '|---:|---:|---:|---:|---:|---:|---|']
    for cpm, dvv in RECT:
        r1 = [r for r in out['rect'] if r['cpm'] == cpm and r['hp_order'] == 1]
        r6 = [r for r in out['rect'] if r['cpm'] == cpm and r['hp_order'] == 6]
        a = [r for r in r1 if r['phase_deg'] == 0][0]['pst_cpf']
        b = [r for r in r6 if r['phase_deg'] == 0][0]['pst_cpf']
        spread = ''
        if len(r1) > 1:
            v = [r['pst_cpf'] for r in r1]
            spread = f'{min(v):.3f} .. {max(v):.3f}'
        lines.append(f'| {cpm} | {dvv} | {a:.3f} | {100*(a-1):+.1f} % | {b:.3f} | {100*(b-1):+.1f} % | {spread} |')
    lines.append('')
    lines.append('| sinusoidal test | P_inst,max | P_inst,mean |')
    lines.append('|---|---:|---:|')
    for s in out['sine']:
        lines.append(f"| {s['f_hz']} Hz, dV/V {s['dvv_pct']} % p-p, HP order {s['hp_order']} | {s['pinst_max']:.3f} | {s['pinst_mean']:.3f} |")
    with open(os.path.join(HERE, 'validation.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    if os.path.exists(OUT_JSON) and '--force' not in sys.argv:
        with open(OUT_JSON) as f:
            write_md(json.load(f))
    else:
        main()
