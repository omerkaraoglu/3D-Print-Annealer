"""Thin-wire method-of-moments solver (frequency domain), written for the C_rf campaign.

EFIE, mixed-potential form, piecewise-linear (rooftop) basis functions on wire nodes (junctions of any order: k-1 bases
per k-segment node), Galerkin testing, reduced kernel g = exp(-jkR)/R with R = sqrt(d^2 + a^2). Segment-pair integrals with
linear weights (2x2 per pair) by Gauss quadrature: 4 points far, 16 points (4 sub-segments x 4) for near pairs.
Sources: delta-gap voltage at a node (series in the wire), lumped series impedances at nodes, incident plane wave.
Fields: every segment is integrated as Gauss-point Hertzian dipoles with the full near+far field expression.
Validated in c5_cm_radiation.py against the half-wave dipole input impedance and the Hertzian-dipole field.
Limits: thin-wire (a << lambda, a << segment), surfaces as wire grids (equal-area radius), no dielectric, free space or
a perfect ground plane by image theory."""
import math
import numpy as np

C0 = 299792458.0
MU0 = 4e-7 * math.pi
EPS0 = 1 / (MU0 * C0 ** 2)
ETA0 = MU0 * C0
GX4, GW4 = np.polynomial.legendre.leggauss(4)
GX4 = (GX4 + 1) / 2; GW4 = GW4 / 2


class Wires:
    def __init__(self, tol=1e-6):
        self.nodes = []          # xyz
        self.segs = []           # (n0, n1, radius, tag)
        self.tol = tol
        self.loads = {}          # node index -> list of (callable f->Z, seg_a, seg_b)

    def node(self, p):
        p = np.asarray(p, float)
        for i, q in enumerate(self.nodes):
            if np.linalg.norm(q - p) < self.tol:
                return i
        self.nodes.append(p)
        return len(self.nodes) - 1

    def line(self, p0, p1, nseg, a, tag=""):
        p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
        ids = [self.node(p0 + (p1 - p0) * k / nseg) for k in range(nseg + 1)]
        for k in range(nseg):
            self.segs.append((ids[k], ids[k + 1], a, tag))
        return ids

    def polyline(self, pts, seglen, a, tag=""):
        ids = []
        for p0, p1 in zip(pts[:-1], pts[1:]):
            n = max(1, int(math.ceil(np.linalg.norm(np.subtract(p1, p0)) / seglen)))
            ids += self.line(p0, p1, n, a, tag)
        return ids

    def finalize(self):
        P = np.array(self.nodes)
        S = np.array([(s[0], s[1]) for s in self.segs])
        self.P, self.S = P, S
        self.a = np.array([s[2] for s in self.segs])
        self.tags = [s[3] for s in self.segs]
        r0, r1 = P[S[:, 0]], P[S[:, 1]]
        self.len = np.linalg.norm(r1 - r0, axis=1)
        self.t = (r1 - r0) / self.len[:, None]
        self.r0, self.r1 = r0, r1
        self.mid = (r0 + r1) / 2
        # basis functions
        att = {}
        for si, (n0, n1) in enumerate(S):
            att.setdefault(n0, []).append((si, 0))      # segment si has node n0 at its u=0 end
            att.setdefault(n1, []).append((si, 1))
        parts = []   # (basis, seg, shape_idx, sigma, div)
        self.bnode = []
        nb = 0
        for nd, lst in att.items():
            if len(lst) < 2:
                continue
            sA, endA = lst[0]
            for sB, endB in lst[1:]:
                # part A: current flows INTO the node along segment A
                shapeA = endA                      # junction at u=1 -> phi_1 (u), at u=0 -> phi_0 (1-u)
                sigA = 1.0 if endA == 1 else -1.0
                parts.append((nb, sA, shapeA, sigA, 1.0 / self.len[sA]))
                # part B: current flows OUT of the node along segment B
                shapeB = endB
                sigB = 1.0 if endB == 0 else -1.0
                parts.append((nb, sB, shapeB, sigB, -1.0 / self.len[sB]))
                self.bnode.append((nd, sA, sB))
                nb += 1
        self.nb = nb
        pr = np.array(parts)
        self.pb, self.ps = pr[:, 0].astype(int), pr[:, 1].astype(int)
        self.pa, self.psig, self.pdiv = pr[:, 2].astype(int), pr[:, 3], pr[:, 4]
        self._pairs_near = None
        return self

    def basis_at(self, node_idx, seg_a=None):
        """index of a basis function at a node (first one, or the one whose part A is seg_a)."""
        for b, (nd, sA, sB) in enumerate(self.bnode):
            if nd == node_idx and (seg_a is None or sA == seg_a):
                return b
        raise KeyError(node_idx)

    def nearest_node(self, p):
        return int(np.argmin(np.linalg.norm(self.P - np.asarray(p), axis=1)))

    # ------------------------------------------------------------------------------------------------------------
    def _integrals(self, k):
        """I[s, s', a, b] = int_s int_s' phi_a(u) phi_b(u') g dl dl'   (complex), shape (ns, ns, 2, 2)."""
        ns = len(self.len)
        # far: 4-point Gauss
        u = GX4
        Q = self.r0[:, None, :] + u[None, :, None] * (self.r1 - self.r0)[:, None, :]      # (ns, 4, 3)
        W = GW4[None, :] * self.len[:, None]                                                   # (ns, 4)
        phi = np.stack([1 - u, u])                                                             # (2, 4)
        Qf = Q.reshape(-1, 3)
        d2 = ((Qf[:, None, :] - Qf[None, :, :]) ** 2).sum(-1)
        aa = np.repeat(self.a, 4)
        R = np.sqrt(d2 + (aa[:, None] ** 2 + aa[None, :] ** 2) / 2)
        g = np.exp(-1j * k * R) / R
        g = g.reshape(ns, 4, ns, 4)
        Wp = W[:, None, :] * phi[None, :, :]                                                   # (ns, 2, 4)
        I = np.einsum("iaq,iqjr,jbr->ijab", Wp, g, Wp, optimize=True)
        # near pairs: refine with 4 sub-segments x 4 Gauss points
        if self._pairs_near is None:
            dm = np.linalg.norm(self.mid[:, None, :] - self.mid[None, :, :], axis=-1)
            lim = 1.6 * np.maximum(self.len[:, None], self.len[None, :])
            self._pairs_near = np.argwhere(dm < lim)
        u16 = (np.repeat(np.arange(4), 4) + np.tile(GX4, 4)) / 4
        w16 = np.tile(GW4, 4) / 4
        phi16 = np.stack([1 - u16, u16])
        for i, j in self._pairs_near:
            qi = self.r0[i] + u16[:, None] * (self.r1[i] - self.r0[i])
            qj = self.r0[j] + u16[:, None] * (self.r1[j] - self.r0[j])
            Rr = np.sqrt(((qi[:, None, :] - qj[None, :, :]) ** 2).sum(-1) + (self.a[i] ** 2 + self.a[j] ** 2) / 2)
            gg = np.exp(-1j * k * Rr) / Rr
            wi = w16 * self.len[i]; wj = w16 * self.len[j]
            I[i, j] = np.einsum("aq,qr,br->ab", phi16 * wi, gg, phi16 * wj)
        return I

    def Z(self, f):
        w = 2 * math.pi * f
        k = w / C0
        I = self._integrals(k)
        sp, sa = self.ps, self.pa
        tdot = self.t[sp] @ self.t[sp].T
        Ia = I[sp[:, None], sp[None, :], sa[:, None], sa[None, :]]
        Itot = I.sum(axis=(2, 3))[sp[:, None], sp[None, :]]
        Zp = (1j * w * MU0 / (4 * math.pi)) * (self.psig[:, None] * self.psig[None, :]) * tdot * Ia \
            + (1 / (1j * w * EPS0 * 4 * math.pi)) * (self.pdiv[:, None] * self.pdiv[None, :]) * Itot
        Z = np.zeros((self.nb, self.nb), complex)
        np.add.at(Z, (self.pb[:, None], self.pb[None, :]), Zp)
        return Z

    def plane_wave_V(self, f, E0, pol, kdir):
        """V_m = int f_m . E_inc dl, E_inc = E0 * pol * exp(-j k kdir.r)."""
        k = 2 * math.pi * f / C0
        u = GX4
        V = np.zeros(self.nb, complex)
        for b_, s, a_, sig in zip(self.pb, self.ps, self.pa, self.psig):
            q = self.r0[s] + u[:, None] * (self.r1[s] - self.r0[s])
            ph = (1 - u) if a_ == 0 else u
            e = E0 * np.exp(-1j * k * (q @ kdir))
            V[b_] += sig * (self.t[s] @ pol) * np.sum(GW4 * self.len[s] * ph * e)
        return V

    def seg_currents(self, Ib):
        """current at both ends of every segment (along t_s): c[s,0] at u=0, c[s,1] at u=1."""
        c = np.zeros((len(self.len), 2), complex)
        for b_, s, a_, sig in zip(self.pb, self.ps, self.pa, self.psig):
            c[s, a_] += sig * Ib[b_]
        return c

    def fields(self, Ib, f, obs, image_z=None):
        """E field (complex, V/m) at obs points (M,3). image_z: perfect ground plane at y = image_z (vertical axis y)."""
        w = 2 * math.pi * f
        k = w / C0
        c = self.seg_currents(Ib)
        u = GX4
        src, mom = [], []
        for s in range(len(self.len)):
            q = self.r0[s] + u[:, None] * (self.r1[s] - self.r0[s])
            Iq = c[s, 0] * (1 - u) + c[s, 1] * u
            src.append(q)
            mom.append((Iq * GW4 * self.len[s])[:, None] * self.t[s][None, :])
        src = np.vstack(src); mom = np.vstack(mom)
        if image_z is not None:            # image of a current element over PEC (plane normal y): horizontal comps reversed
            isrc = src.copy(); isrc[:, 1] = 2 * image_z - src[:, 1]
            imom = mom.copy(); imom[:, 0] *= -1; imom[:, 2] *= -1
            src = np.vstack([src, isrc]); mom = np.vstack([mom, imom])
        E = np.zeros((len(obs), 3), complex)
        for i0 in range(0, len(src), 2000):
            s_ = src[i0:i0 + 2000]; m_ = mom[i0:i0 + 2000]
            Rv = obs[:, None, :] - s_[None, :, :]
            R = np.linalg.norm(Rv, axis=-1)
            Rh = Rv / R[..., None]
            pe = m_ / (1j * w)                                       # electric dipole moment (C*m)
            rd = (Rh * pe[None]).sum(-1)
            t1 = np.cross(np.cross(Rh, pe[None]), Rh) * (k ** 2 / R)[..., None]
            t2 = (3 * Rh * rd[..., None] - pe[None]) * ((1 / R ** 3 + 1j * k / R ** 2))[..., None]
            E += ((t1 + t2) * (np.exp(-1j * k * R) / (4 * math.pi * EPS0))[..., None]).sum(1)
        return E
