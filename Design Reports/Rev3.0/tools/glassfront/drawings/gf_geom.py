"""Plan geometry of the GlassFront module in the FRONT VIEW (u, v), derived only from the master parameters.

Every quantity is computed from Params; where the master also states the result (strip lengths, land widths,
bead-to-pocket, distances to the cut-out) the value is recomputed and compared in `consistency()`.
"""
import json
import math

from gf_common import Rect, FrontView, Params, stadium_pts, V2_V1PARAMS, V2_SHEET_DXF


class Geom:
    def __init__(self, P: Params):
        self.P = P
        fv = self.fv = FrontView(P)
        R = lambda name: fv.rect(P.rect(name), name)
        self.glass = R("glass")
        self.window = R("print_window")
        self.aa = R("AA")
        self.va = R("VA_CTP")
        self.lip_in = R("lip_in")
        self.lip_out = R("lip_out")
        self.seat_out = R("seat_ring_out")
        self.cut = R("cut")
        self.tape_in = R("tape_in")
        self.tape_out = R("tape_out")
        self.fl_line = R("fastener_line")
        self.flange = R("flange")
        self.pocket = R("pocket")
        self.tail_pocket = R("tail_pocket")
        co = {c["name"]: c["value"] for c in P.raw["carried_over_from_v2"]}
        for k in ("panel_x0", "panel_x1", "panel_y0", "panel_y1"):
            P._use("carried_over_from_v2." + k, co[k])
        self.panel = fv.rect(Rect(co["panel_x0"], co["panel_x1"], co["panel_y0"], co["panel_y1"], 0.0, "panel"))
        # drives
        self.g1 = P.d("g1")
        self.g2 = P.d("g2")
        self.lip_w = P.d("lip_w")
        self.seat_w = P.d("seat_ring_w")
        self.bead_w = P.d("bead_w")
        self.bead_edge = P.d("bead_edge")
        self.bead_pocket_min = P.d("bead_pocket_min")
        self.tape_w = P.d("tape_w")
        self.tape_margin = P.d("tape_margin")
        self.pad_d = P.d("pad_d")
        self.slot_w = P.d("slot_w")
        self.slot_l = P.d("slot_l")
        self.pip_d = P.d("pip_d")
        self.fast_off = P.d("fast_off")
        # bead band (glass-relative)
        self.bead_out = self.glass.offset(-self.bead_edge, "bead_outer")
        self.bead_inn = self.glass.offset(-(self.bead_edge + self.bead_w), "bead_inner")
        self.bead_cl = self.glass.offset(-(self.bead_edge + self.bead_w / 2.0), "bead_centre_line")
        # logo zone
        lc = P.val("logo_zone", "logo_centre")
        lw_, lh_ = P.val("logo_zone", "logo_w"), P.val("logo_zone", "logo_h")
        cu, cv = fv.uv(*lc)
        self.logo = Rect(cu - lw_ / 2, cu + lw_ / 2, cv - lh_ / 2, cv + lh_ / 2, 0.0, "logo_zone")
        # fasteners
        self.F = {}
        for nme in P.fast_names():
            f = P.fast(nme)
            u, v = fv.uv(f["x_abs"], f["y_abs_down"])
            au, av = fv.vec(*f["slot_axis"])
            self.F[nme] = dict(u=u, v=v, au=au, av=av, deg_abs=f["slot_axis_deg"], used_by=f["used_by"],
                               pad="pad" in f["front_pad"] and "none" not in f["front_pad"],
                               u_master=f["front_view_u"], v_master=f["front_view_v"],
                               d_cut_master=f["d_cut_out_edge"])
        # pips
        self.pips = {}
        for it in P.raw["pips"]:
            if it["name"].startswith("pip") and isinstance(it["value"], list):
                P._use("pips." + it["name"], it["value"])
                self.pips[it["name"]] = fv.uv(*it["value"])
        # tape strips (straight, ending tape_margin before the corner pads)
        F1, F2, F4 = self.F["F1"], self.F["F2"], self.F["F4"]
        rp = self.pad_d / 2.0
        L_tb = abs(F1["u"] - F2["u"]) - 2 * (rp + self.tape_margin)
        L_sd = abs(F1["v"] - F4["v"]) - 2 * (rp + self.tape_margin)
        self.strip_len = {"top_bottom": L_tb, "sides": L_sd}
        ti, to = self.tape_in, self.tape_out
        self.strips = {
            "top": Rect(-L_tb / 2, L_tb / 2, ti.y1, to.y1, 0, "strip_top"),
            "bottom": Rect(-L_tb / 2, L_tb / 2, to.y0, ti.y0, 0, "strip_bottom"),
            "right": Rect(ti.x1, to.x1, -L_sd / 2, L_sd / 2, 0, "strip_right"),     # front-view right
            "left": Rect(to.x0, ti.x0, -L_sd / 2, L_sd / 2, 0, "strip_left"),
        }
        self.dabs = self._dab_regions()
        # land inner boundary (pocket + tail pocket) for the frame-front plan
        self.land_inner = self._land_inner()

    # ------------------------------------------------------------------ helpers
    def slot(self, name):
        f = self.F[name]
        return stadium_pts(f["u"], f["v"], f["au"], f["av"], self.slot_l, self.slot_w)

    def _dab_regions(self):
        """the 8 corner gaps between a strip end and the corner pad, across the tape band (bulge polylines)"""
        rp = self.pad_d / 2.0
        out = {}
        for cn in ("F1", "F2", "F3", "F4"):
            f = self.F[cn]
            cu, cv = f["u"], f["v"]
            su, sv = (1 if cu > 0 else -1), (1 if cv > 0 else -1)
            # horizontal strip (top or bottom) end: x = end_u, band in v between tape_in and tape_out edges
            band_v = [self.tape_in.y1, self.tape_out.y1] if sv > 0 else [self.tape_out.y0, self.tape_in.y0]
            end_u = su * (self.strip_len["top_bottom"] / 2.0)
            out[cn + "_h"] = self._gap_region(cu, cv, rp, end_u, band_v, horizontal=True)
            band_u = [self.tape_in.x1, self.tape_out.x1] if su > 0 else [self.tape_out.x0, self.tape_in.x0]
            end_v = sv * (self.strip_len["sides"] / 2.0)
            out[cn + "_v"] = self._gap_region(cu, cv, rp, end_v, band_u, horizontal=False)
        return out

    @staticmethod
    def _gap_region(cu, cv, rp, end, band, horizontal):
        """closed outline between the straight strip end (line at `end`) and the pad circle, across `band`"""
        pts = []
        if horizontal:
            # line u = end, band v0..v1; pad circle reaches u = cu +- sqrt(rp^2 - (v - cv)^2) towards the strip
            s = 1 if end < cu else -1          # strip lies on the side of the centre the end faces
            v0, v1 = band
            k = 24
            for i in range(k + 1):
                v = v0 + (v1 - v0) * i / k
                dv = v - cv
                du = math.sqrt(max(rp * rp - dv * dv, 0.0))
                pts.append((cu - s * du, v))
            pts += [(end, v1), (end, v0)]
        else:
            s = 1 if end < cv else -1
            u0, u1 = band
            k = 24
            for i in range(k + 1):
                u = u0 + (u1 - u0) * i / k
                du = u - cu
                dv = math.sqrt(max(rp * rp - du * du, 0.0))
                pts.append((u, cv - s * dv))
            pts += [(u1, end), (u0, end)]
        return pts

    def _land_inner(self):
        """outline of pocket + tail pocket (union), front view; corners of the union drawn sharp (reference)"""
        pk, tp = self.pocket, self.tail_pocket
        # front view: tail pocket is below the pocket (v smaller)
        return [(pk.x0, pk.y1), (pk.x1, pk.y1), (pk.x1, pk.y0), (tp.x1, pk.y0), (tp.x1, tp.y0), (tp.x0, tp.y0),
                (tp.x0, pk.y0), (pk.x0, pk.y0)]

    def lands(self):
        """land widths (pocket face -> glass edge) per front-view side"""
        g, pk, tp = self.glass, self.pocket, self.tail_pocket
        return {"front-view right (abs left)": g.x1 - pk.x1,
                "front-view left (abs right)": pk.x0 - g.x0,
                "top": g.y1 - pk.y1,
                "bottom (over the tail-pocket beam)": tp.y0 - g.y0}

    def formex(self):
        """Formex sheet from the master (plan_rectangles 'formex', carried over from v2; GF-1.1 round 3),
        in the front view; the inset to the panel outline is derived and must be the same on all four sides"""
        it = self.P._rect["formex"]
        r = self.fv.rect(self.P.rect("formex"), "formex")
        pn = self.panel
        ins = [pn.x1 - r.x1, r.x0 - pn.x0, pn.y1 - r.y1, r.y0 - pn.y0]
        assert max(ins) - min(ins) < 1e-6, ("formex inset not uniform", ins)
        return r, {"inset": ins[0], "R": r.R, "z": it.get("z"), "status": it.get("status"),
                   "source": "params plan_rectangles.formex"}

    def v2_window(self):
        """v2 sheet window from Rev3.0_FrontSheet_Pattern_v2.dxf (read-only), returned in THIS front view"""
        import ezdxf
        doc = ezdxf.readfile(V2_SHEET_DXF)
        for e in doc.modelspace():
            if e.dxftype() == "LWPOLYLINE" and e.dxf.layer == "CUTOUT":
                pts = [(p[0], p[1]) for p in e.get_points("xy")]
                bul = [p[2] for p in e.get_points("xyb")]
        us, vs = [p[0] for p in pts], [p[1] for p in pts]
        w, h = max(us) - min(us), max(vs) - min(vs)
        # v2 datum = v2 window centre = VA centre (abs); express it in this front view
        cu, cv = self.va.c
        b = [abs(x) for x in bul if abs(x) > 1e-9]
        R = None
        if b:
            # 90 deg corner arcs: radius from the polyline vertices (chord / sqrt 2)
            for i in range(len(pts)):
                if abs(bul[i]) > 1e-9:
                    j = (i + 1) % len(pts)
                    R = math.hypot(pts[j][0] - pts[i][0], pts[j][1] - pts[i][1]) / math.sqrt(2)
                    break
        return {"w": w, "h": h, "R": R, "centre_uv_from_VA": (cu, cv),
                "dxf_centre_offset": ((max(us) + min(us)) / 2, (max(vs) + min(vs)) / 2)}

    @staticmethod
    def corner_gap(inner: Rect, outer: Rect):
        """gap along the 45 deg corner diagonal between two rounded rectangles (corners need not be concentric)"""
        pts = inner.boundary(n_arc=360, step=0.05)
        d = -outer.sdf(pts[:, 0], pts[:, 1])
        return float(d.max())

    def fastener_cuts(self):
        """GF-1.1 counterbore and tube coring values from the master (frame side)"""
        P = self.P
        cb = {k: P.val("fasteners.counterbore", k) for k in ("cb_w", "cb_l", "cb_floor_F1-F4", "cb_floor_F5-F8",
                                                               "cb_r", "cb_draft")}
        co = {k: P.val("fasteners.tube_coring", k) for k in ("core_r_in", "core_r_out", "core_depth",
                                                               "core_floor_r", "core_draft")}
        return cb, co

    def mirror_refs(self):
        """two asymmetric references written as TEXT into every front-view DXF (insert point = transformed abs
        point): the abs-left glass edge (KiCad x0) must land at u > 0, the chin edge (abs y1) at v < 0"""
        g = self.P.rect("glass")
        ul, vl = self.fv.uv(g.x0, self.fv.yc)
        ub, vb = self.fv.uv(self.fv.xc, g.y1)
        return [("MIRROR-REF abs x %.2f (KiCad left glass edge) = front-view RIGHT" % g.x0, ul, vl),
                ("MIRROR-REF abs y %.2f (chin edge) = front-view BOTTOM" % g.y1, ub, vb)]

    # ------------------------------------------------------------------ consistency with the master's own results
    def consistency(self):
        P = self.P
        res = {}
        sl = P.val("tape_and_gasket", "strip_lengths")
        res["strip_lengths"] = {"computed": {k: round(v, 3) for k, v in self.strip_len.items()}, "master": sl,
                                "ok": all(abs(self.strip_len[k] - sl[k]) < 1e-6 for k in sl)}
        lands_m = {it["name"]: (it["value"], it["bead_to_pocket"]) for it in P.raw["lands"]}
        P._use("lands", lands_m)
        L = self.lands()
        mp = {"front-view right (abs left)": "abs left (front-view right)",
              "front-view left (abs right)": "abs right (front-view left)",
              "top": "top", "bottom (over the tail-pocket beam)": "bottom (over the tail-pocket bottom beam)"}
        rows = {}
        okall = True
        for k, v in L.items():
            mv, mb = lands_m[mp[k]]
            b2p = v - self.bead_edge - self.bead_w
            ok = abs(v - mv) < 1e-6 and abs(b2p - mb) < 1e-6 and b2p >= self.bead_pocket_min - 1e-9
            okall &= ok
            rows[k] = {"land": round(v, 3), "master": mv, "bead_to_pocket": round(b2p, 3), "master_b2p": mb,
                       ">= bead_pocket_min": b2p >= self.bead_pocket_min - 1e-9, "ok": ok}
        res["lands"] = {"rows": rows, "ok": okall}
        fs = {}
        okf = True
        for k, f in self.F.items():
            d = float(self.cut.sdf(f["u"], f["v"]))
            ok = abs(f["u"] - f["u_master"]) < 1e-6 and abs(f["v"] - f["v_master"]) < 1e-6
            okf &= ok
            fs[k] = {"u": round(f["u"], 4), "v": round(f["v"], 4), "d_cut_edge": round(d, 4),
                     "master_d_cut": f["d_cut_master"], "master_d_cut_stale": abs(d - f["d_cut_master"]) > 1e-3,
                     "ok": ok}
        res["fasteners_uv_and_cut_distance"] = {"rows": fs, "ok": okf}
        pp = {}
        okp = True
        for k, (u, v) in self.pips.items():
            d = float(self.bead_cl.sdf(u, v))
            okp &= abs(d) < 1e-6
            pp[k] = {"u": round(u, 4), "v": round(v, 4), "dist_to_bead_centre_line": round(d, 6)}
        res["pips_on_bead_centre_line"] = {"rows": pp, "ok": okp}
        wc = P.pt("window_centre")
        wcu = self.fv.uv(*wc)
        res["window_centre"] = {"from_rect": [round(x, 4) for x in self.window.c], "master_point_uv": wcu,
                                "ok": abs(self.window.c[0] - wcu[0]) < 1e-6 and abs(self.window.c[1] - wcu[1]) < 1e-6}
        chin = P.pt("chin_border")
        btlr = P.pt("borders_top_left_right")
        g, w = self.glass, self.window
        b = {"top": g.y1 - w.y1, "left": w.x0 - g.x0, "right": g.x1 - w.x1, "bottom (chin)": w.y0 - g.y0}
        res["borders"] = {"computed": {k: round(v, 4) for k, v in b.items()}, "master": {"t/l/r": btlr, "chin": chin},
                          "ok": all(abs(b[k] - btlr) < 1e-6 for k in ("top", "left", "right")) and
                          abs(b["bottom (chin)"] - chin) < 1e-6}
        pin = P.d("print_inset")
        res["window_vs_AA"] = {"inset_each_side": [round(w.x0 - self.aa.x0, 4), round(self.aa.x1 - w.x1, 4),
                                                   round(w.y0 - self.aa.y0, 4), round(self.aa.y1 - w.y1, 4)],
                               "print_inset": pin,
                               "ok": all(abs(x - pin) < 1e-6 for x in (w.x0 - self.aa.x0, self.aa.x1 - w.x1,
                                                                       w.y0 - self.aa.y0, self.aa.y1 - w.y1))}
        return res
