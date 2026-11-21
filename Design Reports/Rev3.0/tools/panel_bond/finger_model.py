"""Panel bond, step 2: force-deflection and stress of the Laird LT17BH0731 SMD contact finger.

The maker's drawing (Datasheets/Laird LT17BH0731 SMD contact finger.pdf, rev A, sheet 1) gives the
geometry but NO force, working range, current or temperature.  This script estimates them with a
geometrically non-linear (co-rotational) planar beam model of the strip centre line:

  strip  BeCu C17200 1/2H, heat treated HV 343 min (note F/H), t = 0.127 +-0.02 (title block), b = 5 +-0.2
  base   5 +-0.2 flat, soldered; right bends R0.87 inner (TYP), left bend R0.65 inner,
         bend angles 166.8 deg (TYP) and 153.6 deg (detail A), free height 7.5 +-0.2, length 6 +-0.45,
         top leg 5 +-0.2 flat with a free end, "contact spring in built-in nom. compression" 6.25.
  E = 131 GPa (C17200, assumed: Materion handbook value), Poisson ignored (beam), plane stress.

The panel back is a rigid, frictionless flat plate that moves down; contact with the top leg is a
penalty contact on every top-leg node.  The base nodes are clamped over the soldered length.
Self-contact between the legs is not modelled; the script reports the height at which two
non-adjacent segments come closer than one strip thickness ("bottoming"), and the model is not
used below that height.

Outputs: out/finger_model.json, out/finger_model.png
Run: python -X utf8 finger_model.py
"""
import json, math, os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out')

E = 131000.0           # MPa, assumed
SY = 965.0             # MPa, 0.2 % yield, assumed lower bound for HV 343 (UTS ~ 3.2 x HV ~ 1100 MPa, YS ~ 0.88 UTS)
B = 5.0                # mm strip width (drawing 5 +-0.2)


def centreline(t=0.127, H=7.5, xr=5.0, ang_r=166.8, ang_l=153.6, Rr_in=0.87, Rl_in=0.65, top=5.0, base=5.0, ds=0.05):
    """Return node list (x, y) along the centre line from the base's left end to the top leg's free end."""
    Rr = Rr_in + t / 2
    Rl = Rl_in + t / 2
    yb = t / 2
    # solve straight length Ls so that the top centre line sits at H - t/2
    rise_r = Rr * (1 - math.cos(math.radians(ang_r)))
    rise_l = 2 * Rl * math.sin(math.radians(ang_l / 2))
    inc = math.radians(180 - ang_r)          # incline of the straight legs to the horizontal
    Ls = ((H - t / 2) - yb - 2 * rise_r - rise_l) / (2 * math.sin(inc))
    pts = []
    x, y, hd = xr - base, yb, 0.0

    def straight(L):
        nonlocal x, y
        n = max(2, int(round(L / ds)))
        for i in range(1, n + 1):
            pts.append((x + math.cos(hd) * L * i / n, y + math.sin(hd) * L * i / n))
        x, y = pts[-1]

    def arc(R, turn_deg):           # +: CCW
        nonlocal x, y, hd
        turn = math.radians(turn_deg)
        n = max(4, int(round(abs(turn) * R / ds)))
        sgn = 1 if turn > 0 else -1
        cx, cy = x - sgn * R * math.sin(hd), y + sgn * R * math.cos(hd)
        a0 = hd - sgn * math.pi / 2
        for i in range(1, n + 1):
            a = a0 + turn * i / n
            pts.append((cx + R * math.cos(a), cy + R * math.sin(a)))
        hd += turn
        x, y = pts[-1]

    pts.append((x, y))
    straight(base)
    i_base_end = len(pts) - 1
    arc(Rr, +ang_r)
    straight(Ls)
    arc(Rl, -ang_l)
    straight(Ls)
    arc(Rr, +ang_r)
    i_top_start = len(pts) - 1
    straight(top)
    return np.array(pts), i_base_end, i_top_start, Ls


def solve(t=0.127, H=7.5, h_end=4.2, dh=0.05, kp=2.0e4, ds=0.12):
    X0, ib, it, Ls = centreline(t=t, H=H, ds=ds)
    n = len(X0)
    A = B * t
    I = B * t ** 3 / 12.0
    Wb = B * t ** 2 / 6.0
    el = [(i, i + 1) for i in range(n - 1)]
    L0 = np.array([np.linalg.norm(X0[j] - X0[i]) for i, j in el])
    b0 = np.array([math.atan2(X0[j][1] - X0[i][1], X0[j][0] - X0[i][0]) for i, j in el])
    ndof = 3 * n
    fixed = []
    for k in range(0, ib + 1):            # soldered base: clamp
        fixed += [3 * k, 3 * k + 1, 3 * k + 2]
    free = np.setdiff1d(np.arange(ndof), fixed)
    U = np.zeros(ndof)
    top_nodes = list(range(it, n))

    def assemble(U):
        K = np.zeros((ndof, ndof))
        F = np.zeros(ndof)
        Mmax = 0.0
        Nmax = 0.0
        for e, (i, j) in enumerate(el):
            xi = X0[i] + U[3 * i:3 * i + 2]
            xj = X0[j] + U[3 * j:3 * j + 2]
            d = xj - xi
            L = math.hypot(*d)
            beta = math.atan2(d[1], d[0])
            c, s = d[0] / L, d[1] / L
            # rigid rotation, wrapped
            rr = beta - b0[e]
            rr = (rr + math.pi) % (2 * math.pi) - math.pi
            t1 = U[3 * i + 2] - rr
            t2 = U[3 * j + 2] - rr
            ul = L - L0[e]
            N = E * A / L0[e] * ul
            M1 = E * I / L0[e] * (4 * t1 + 2 * t2)
            M2 = E * I / L0[e] * (2 * t1 + 4 * t2)
            Bm = np.array([[-c, -s, 0, c, s, 0],
                           [-s / L, c / L, 1, s / L, -c / L, 0],
                           [-s / L, c / L, 0, s / L, -c / L, 1]])
            D = np.array([[E * A / L0[e], 0, 0],
                          [0, 4 * E * I / L0[e], 2 * E * I / L0[e]],
                          [0, 2 * E * I / L0[e], 4 * E * I / L0[e]]])
            r = np.array([-c, -s, 0, c, s, 0])
            z = np.array([s, -c, 0, -s, c, 0])
            fl = Bm.T @ np.array([N, M1, M2])
            Ke = Bm.T @ D @ Bm + N / L * np.outer(z, z) + (M1 + M2) / L ** 2 * (np.outer(r, z) + np.outer(z, r))
            idx = [3 * i, 3 * i + 1, 3 * i + 2, 3 * j, 3 * j + 1, 3 * j + 2]
            K[np.ix_(idx, idx)] += Ke
            F[idx] += fl
            Mmax = max(Mmax, abs(M1), abs(M2))
            Nmax = max(Nmax, abs(N))
        return K, F, Mmax, Nmax

    def min_gap(Xc):
        # smallest distance between non-adjacent nodes far apart along the strip (> 1.6 mm of arc length)
        sarc = np.concatenate([[0], np.cumsum(L0)])
        best = 1e9
        for i in range(0, n, 2):
            far = np.where(np.abs(sarc - sarc[i]) > 1.6)[0]
            if len(far):
                dmin = np.min(np.linalg.norm(Xc[far] - Xc[i], axis=1))
                best = min(best, dmin)
        return best

    hist = []
    yp = H - t / 2 + t / 2            # plate = outer top surface
    shapes = {}
    while yp > h_end - 1e-9:
        for it_n in range(60):
            K, F, Mmax, Nmax = assemble(U)
            R = -F.copy()
            Kc = K.copy()
            reac = 0.0
            for k in top_nodes:
                yk = X0[k][1] + U[3 * k + 1] + t / 2      # outer surface of the top leg
                pen = yk - yp
                if pen > 0:
                    R[3 * k + 1] -= kp * pen
                    Kc[3 * k + 1, 3 * k + 1] += kp
                    reac += kp * pen
            Rf = R[free]
            if np.linalg.norm(Rf) < 1e-5 and it_n > 0:
                break
            dU = np.linalg.solve(Kc[np.ix_(free, free)], Rf)
            U[free] += dU
            if np.linalg.norm(dU) < 1e-9:
                break
        Xc = X0 + U.reshape(-1, 3)[:, :2]
        gap = min_gap(Xc)
        sig = Mmax / Wb + Nmax / A
        xs = Xc[:, 0]
        cont = [k for k in top_nodes if (X0[k][1] + U[3 * k + 1] + t / 2) - yp > 1e-6]
        hist.append(dict(h=round(yp, 4), F=round(reac, 5), sigma_max=round(sig, 1), min_gap=round(gap, 4),
                         x_min=round(float(xs.min() - t / 2), 4), x_max=round(float(xs.max() + t / 2), 4),
                         contact_x=[round(float(Xc[k][0]), 3) for k in cont][:1] + [round(float(Xc[k][0]), 3) for k in cont][-1:]))
        for hs in (7.5, 6.8, 6.25, 5.8, 5.4, 5.0, 4.6):
            if abs(yp - hs) < dh / 2 + 1e-9:
                shapes[str(hs)] = Xc.round(4).tolist()
        yp -= dh
    return dict(t=t, H=H, Ls=round(Ls, 4), nodes=n, base_end=int(ib), top_start=int(it), X0=X0.round(4).tolist(),
                hist=hist, shapes=shapes)


def at(h, hist, key):
    hs = np.array([r['h'] for r in hist])
    vs = np.array([r[key] for r in hist])
    o = np.argsort(hs)
    return float(np.interp(h, hs[o], vs[o]))


def main():
    os.makedirs(OUT, exist_ok=True)
    cases = {}
    for name, t in (('t_nom_0.127', 0.127), ('t_min_0.107', 0.107), ('t_max_0.147', 0.147)):
        cases[name] = solve(t=t)
        print(name, 'done')
    nom = cases['t_nom_0.127']['hist']
    # bottoming: first height where the legs come closer than 1 thickness (plus 0.02)
    res = {}
    for name, c in cases.items():
        tt = c['t']
        hb = None
        for r in c['hist']:
            if r['min_gap'] < tt + 0.02:
                hb = r['h']
                break
        hy = None
        for r in c['hist']:
            if r['sigma_max'] >= SY:
                hy = r['h']
                break
        res[name] = dict(bottoming_h=hb, yield_h=hy,
                         F_at={str(h): round(at(h, c['hist'], 'F'), 3) for h in (7.3, 6.82, 6.52, 6.25, 5.8, 5.4, 5.08, 5.0, 4.85, 4.6, 4.4)},
                         sigma_at={str(h): round(at(h, c['hist'], 'sigma_max'), 0) for h in (7.3, 6.82, 6.52, 6.25, 5.8, 5.4, 5.08, 5.0, 4.85, 4.6, 4.4)},
                         x_extent={str(h): [round(at(h, c['hist'], 'x_min'), 3), round(at(h, c['hist'], 'x_max'), 3)] for h in (7.5, 6.82, 6.25, 5.8, 5.0, 4.6)})
    json.dump(dict(model=__doc__.strip().splitlines()[0], E_MPa=E, yield_MPa_assumed=SY, width_mm=B,
                   summary=res, cases=cases), open(os.path.join(OUT, 'finger_model.json'), 'w'), indent=0)
    for k, v in res.items():
        print(k, json.dumps(v))
    # plot
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 3, figsize=(15, 4.8))
    for name, c in cases.items():
        h = [r['h'] for r in c['hist']]
        ax[0].plot(h, [r['F'] for r in c['hist']], label=name)
        ax[1].plot(h, [r['sigma_max'] for r in c['hist']], label=name)
    ax[1].axhline(SY, color='r', ls='--', lw=0.8, label='yield (assumed 965 MPa)')
    for a, yl in ((ax[0], 'contact force per finger (N)'), (ax[1], 'max. bending + axial stress (MPa)')):
        a.set_xlabel('working height = PCB pad to panel back (mm)')
        a.set_ylabel(yl)
        a.invert_xaxis()
        a.grid(alpha=0.3)
        a.legend(fontsize=8)
    c = cases['t_nom_0.127']
    X0 = np.array(c['X0'])
    ax[2].plot(X0[:, 0], X0[:, 1], 'k-', lw=1.2, label='free 7.5')
    cols = {'6.25': 'tab:blue', '5.8': 'tab:green', '5.0': 'tab:orange', '4.6': 'tab:red'}
    for hs, col in cols.items():
        if hs in c['shapes']:
            S = np.array(c['shapes'][hs])
            ax[2].plot(S[:, 0], S[:, 1], '-', color=col, lw=1, label=f'h {hs}')
    ax[2].set_aspect('equal')
    ax[2].set_title('centre line, t 0.127 (model)')
    ax[2].legend(fontsize=7, loc='upper right')
    ax[2].grid(alpha=0.3)
    fig.suptitle('Laird LT17BH0731 - co-rotational beam model (estimate; the maker states no force)')
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, 'finger_model.png'), dpi=130)


if __name__ == '__main__':
    main()
