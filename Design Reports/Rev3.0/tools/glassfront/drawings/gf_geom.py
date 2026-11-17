"""Plan geometry of the GlassFront module in the FRONT VIEW (u, v), derived only from the master parameters.

Every quantity is computed from Params; where the master also states the result (strip lengths, land widths,
bead-to-pocket, distances to the cut-out) the value is recomputed and compared in `consistency()`.
"""
import json
import math
import re

from gf_common import Rect, FrontView, Params, stadium_pts, V2_V1PARAMS, V2_SHEET_DXF


def gap_temperatures(P: Params):
    """GF-2.0 verified gap values over temperature from the master gaps notes (corrected 2026-11-16); every number is
    parsed - a changed wording raises instead of silently dropping the values"""
    f = r"(-?[\d.]+)"
    g2 = "gaps"
    out = {
        "g2_20C_sides": P.num(g2, r"sides " + f + r", corner diagonal", name="g2_glass_lip"),
        "g2_20C_corner": P.num(g2, r"corner diagonal " + f, name="g2_glass_lip"),
        "g2_cold_50": P.num(g2, r"-20 C " + f + r" \(50 ppm\) / " + f + r" \(70 ppm\); \+70 C", 1, name="g2_glass_lip"),
        "g2_cold_70": P.num(g2, r"-20 C " + f + r" \(50 ppm\) / " + f + r" \(70 ppm\); \+70 C", 2, name="g2_glass_lip"),
        "g2_hot_50": P.num(g2, r"\+70 C " + f + r" \(50 ppm\) / " + f + r" \(70 ppm\)", 1, name="g2_glass_lip"),
        "g2_hot_70": P.num(g2, r"\+70 C " + f + r" \(50 ppm\) / " + f + r" \(70 ppm\)", 2, name="g2_glass_lip"),
        "g2_touch_wc": P.num(g2, r"glass \+0\.2/side, R nominal " + f + r" / " + f, 1, name="g2_glass_lip"),
        "g1_20C_sides": P.num(g2, r"sides " + f + r", corner diagonal", name="g1_lip_sheet"),
        "g1_20C_corner": P.num(g2, r"corner diagonal " + f, name="g1_lip_sheet"),
        "g1_hot_50": P.num(g2, r"\+50 C sheet " + f + r" \(50 ppm\) / " + f + r" \(70 ppm\)", 1, name="g1_lip_sheet"),
        "g1_hot_70": P.num(g2, r"\+50 C sheet " + f + r" \(50 ppm\) / " + f + r" \(70 ppm\)", 2, name="g1_lip_sheet"),
        "g1_cold_50": P.num(g2, r"-20 C " + f + r" \(50 ppm\) / " + f + r" \(70 ppm\)\. Tolerance", 1,
                            name="g1_lip_sheet"),
        "g1_cold_70": P.num(g2, r"-20 C " + f + r" \(50 ppm\) / " + f + r" \(70 ppm\)\. Tolerance", 2,
                            name="g1_lip_sheet"),
        "g1_touch_wc": P.num(g2, r"\(sides / corner min; negative = the sheet edge touches the lip\): " + f, 1,
                             name="g1_lip_sheet"),
    }
    assert "verified" in P.item(g2, "g2_glass_lip")["note"] and "verified" in P.item(g2, "g1_lip_sheet")["note"]
    return out


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
        # GF-2.0: bend-gap slot (through-opening over the tail span), bridge and divider rib (plan, front view)
        self.slot_bg = R("bend_gap_slot")
        self.bridge = R("bridge")
        self.rib = R("divider_rib")
        self.g_bend = P.d("g_bend")
        self.nose_R = P.d("bend_nose_R")
        self.land_break = P.d("land_break")
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
            ln = math.hypot(au, av)                   # the master axis has 4 decimals (|a| 0.99995 at GF-2.1)
            au, av = au / ln, av / ln
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
        """outline of the land's inner edge = clearance pocket + bend-gap slot (union), front view (GF-2.0: over the
        tail span the land ends at the bridge pocket face); corners of the union drawn sharp (reference)"""
        pk, sl = self.pocket, self.slot_bg
        # front view: the slot is below the pocket (v smaller)
        return [(pk.x0, pk.y1), (pk.x1, pk.y1), (pk.x1, pk.y0), (sl.x1, pk.y0), (sl.x1, sl.y0), (sl.x0, sl.y0),
                (sl.x0, pk.y0), (pk.x0, pk.y0)]

    LAND_KEYS = {"front-view right (abs left)": "abs left (front-view right)",
                 "front-view left (abs right)": "abs right (front-view left)",
                 "top": "top",
                 "bottom over the tail span": "bottom over the tail span (x 38.9 .. 167.7)",
                 "bottom outside the tail span": "bottom outside the tail span"}

    def lands(self):
        """land widths (pocket face -> glass edge) per front-view side; GF-2.0: the bottom has two values, over the
        tail span (to the bridge pocket face) and outside it (to the clearance-pocket wall)"""
        g, pk, sl = self.glass, self.pocket, self.slot_bg
        return {"front-view right (abs left)": g.x1 - pk.x1,
                "front-view left (abs right)": pk.x0 - g.x0,
                "top": g.y1 - pk.y1,
                "bottom over the tail span": sl.y0 - g.y0,
                "bottom outside the tail span": pk.y0 - g.y0}

    def bridge_bead_margins(self):
        """bead inner edge over the bridge: to the land-break edge where the land ends and to the pocket-face plane,
        read from the corrected master pocket note (2026-11-16) and checked against the land / break geometry"""
        note = self.P.item("plan_rectangles", "pocket")["note"]
        m = re.search(r"Where the land ends \(Z_LAND \+ ([\d.]+)\).*?over the bridge: ([\d.]+) to the edge of the "
                      r"([\d.]+) x 45 land break \(([\d.]+) to the pocket-face plane", note)
        assert m, ("master pocket note: bridge margins not found", note)
        z_end, brk, b, face = (float(m.group(i)) for i in (1, 2, 3, 4))
        land_b = self.lands()["bottom over the tail span"]
        b2f = land_b - self.bead_edge - self.bead_w
        assert abs(b - self.land_break) < 1e-9 and abs(round(b2f, 2) - face) < 0.006 and \
            abs(round(b2f - (self.land_break - z_end), 2) - brk) < 0.006, (b2f, face, brk)
        self.P._use("plan_rectangles.pocket.note ~ bridge margins", [z_end, brk, face])
        return {"z_end": z_end, "to_break_edge": brk, "to_face_plane": face, "rule": self.bead_pocket_min}

    def break_edge_notes(self):
        """bead inner edge -> land-break edge as the master land notes state it (addendum 2026-11-16): the MEASURED
        value where the land ends (Z_LAND + z, quoted on the drawings) and the LAND-PLANE value (geometry: bead ->
        face plane minus the break). Each number is compared with the thing it describes; a changed wording or a
        mismatch stops the run."""
        P = self.P
        land_b = self.lands()["bottom over the tail span"]
        b2f = land_b - self.bead_edge - self.bead_w              # bead -> pocket-face plane, at the land
        plane = b2f - self.land_break                            # bead -> break edge on the land plane itself
        it = [x for x in P.raw["lands"] if x["name"] == self.LAND_KEYS["bottom over the tail span"]][0]
        m1 = re.search(r"leaves ([\d.]+) of flat land, bead inner edge ([\d.]+) from the break edge \(measured where "
                       r"the land ends, Z_LAND \+ ([\d.]+); ([\d.]+) on the land plane itself\)", it["note"])
        lb = P.dnote("land_break")
        m2 = re.search(r"bead inner edge ([\d.]+) from the break edge, measured where the land ends at Z_LAND \+ "
                       r"([\d.]+) .*?- ([\d.]+) on the land plane itself - and ([\d.]+) from the pocket-face plane", lb)
        assert m1 and m2, ("master land notes: bead -> break edge wording not found", it["note"], lb)
        flat, meas1, z1, pl1 = (float(m1.group(i)) for i in (1, 2, 3, 4))
        meas2, z2, pl2, face2 = (float(m2.group(i)) for i in (1, 2, 3, 4))
        calc_meas = b2f - (self.land_break - z1)                 # the break face is 45 deg: z deeper = z further
        bm = self.bridge_bead_margins()                          # pocket note: same measured value
        chk = {"flat_land": abs(flat - (land_b - self.land_break)) < 1e-6,
               "measured_lands_note": abs(round(calc_meas, 2) - meas1) < 0.006,
               "measured_land_break_note": abs(round(calc_meas, 2) - meas2) < 0.006,
               "measured_pocket_note": abs(bm["to_break_edge"] - meas1) < 1e-9 and abs(bm["z_end"] - z1) < 1e-9,
               "land_plane_lands_note": abs(round(plane, 2) - pl1) < 0.006,
               "land_plane_land_break_note": abs(round(plane, 2) - pl2) < 0.006,
               "face_plane_land_break_note": abs(round(b2f, 2) - face2) < 0.006,
               "same_probe_level": abs(z1 - z2) < 1e-9}
        P._use("lands[bottom over the tail span].note + land_break.note ~ bead -> break edge",
               {"measured": meas1, "z_end": z1, "land_plane": pl1, "face_plane": face2, "flat_land": flat})
        return {"flat_land": flat, "measured": meas1, "z_end": z1, "land_plane": pl1, "face_plane": face2,
                "calc_measured": round(calc_meas, 4), "calc_land_plane": round(plane, 4), "calc_face_plane":
                round(b2f, 4), "checks": chk, "ok": all(chk.values())}

    def tail_route(self, name):
        """GF-2.0 nominal tail centre line (abs y, Z) from the master tail_route (glass-independent)"""
        tr_ = self.P.get("tail_route")[name]
        return [tuple(p) for p in tr_["centreline_yZ"]], tr_

    def tail_vertical_y(self):
        """abs y of the tails' vertical leg centre line = panel edge + l0 + R_in + t/2 (master driving values)"""
        P = self.P
        return P.val("carried_over_from_v2", "panel_y1") + P.d("tail_straight_l0") + P.d("tail_R_in_min") + \
            P.d("tail_t") / 2.0

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
        """counterbore and tube coring values from the master (frame side); GF-2.0: F1-F4 only"""
        P = self.P
        cb = {k: P.val("fasteners.counterbore", k) for k in ("cb_w", "cb_l", "cb_floor_F1-F4", "cb_r", "cb_draft")}
        co = {k: P.val("fasteners.tube_coring", k) for k in ("core_r_in", "core_r_out", "core_depth",
                                                               "core_floor_r", "core_draft")}
        return cb, co

    def mirror_refs(self):
        """two asymmetric references written as TEXT into every front-view DXF (insert point = transformed abs
        point): the abs-left glass edge (KiCad x0) must land at u > 0, the bottom glass edge (abs y1, the tail-exit
        side) at v < 0"""
        g = self.P.rect("glass")
        ul, vl = self.fv.uv(g.x0, self.fv.yc)
        ub, vb = self.fv.uv(self.fv.xc, g.y1)
        return [("MIRROR-REF abs x %.2f (KiCad left glass edge) = front-view RIGHT" % g.x0, ul, vl),
                ("MIRROR-REF abs y %.2f (bottom glass edge, tail side) = front-view BOTTOM" % g.y1, ub, vb)]

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
        mp = self.LAND_KEYS
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
        b4 = P.pt("borders_all_four")
        bd = P.d("border")
        g, w = self.glass, self.window
        b = {"top": g.y1 - w.y1, "left": w.x0 - g.x0, "right": g.x1 - w.x1, "bottom": w.y0 - g.y0}
        res["borders"] = {"computed": {k: round(v, 4) for k, v in b.items()},
                          "master": {"borders_all_four": b4, "driving border": bd},
                          "ok": abs(b4 - bd) < 1e-9 and all(abs(v - b4) < 1e-6 for v in b.values())}
        # GF-2.0: glass centre = window centre = cut-out centre = fastener-pattern centre
        gc = P.pt("glass_centre")
        cc = self.cut.c
        F = self.F
        fpc = (sum(f["u"] for f in F.values()) / len(F), sum(f["v"] for f in F.values()) / len(F))
        res["centres_coincide"] = {"glass_centre_abs": gc, "window_centre_abs": wc,
                                   "glass_uv": [round(x, 6) for x in g.c], "cut_uv": [round(x, 6) for x in cc],
                                   "fastener_pattern_uv": [round(x, 6) for x in fpc],
                                   "ok": all(abs(a) < 1e-6 for a in (g.c[0], g.c[1], cc[0], cc[1], fpc[0], fpc[1],
                                                                       w.c[0], w.c[1]))}
        # GF-2.0 bottom zone: border budget bezel + g_bend + land = border, bridge face = panel edge + g_bend,
        # land break leaves the flat land stated in the master lands note
        pn = self.panel
        bezel = w.y0 - pn.y0
        land_b = L["bottom over the tail span"]
        be = self.break_edge_notes()          # measured (Z_LAND + 0.01) and land-plane values, each vs its geometry
        flat = land_b - self.land_break
        res["bottom_zone"] = {"bezel_window_to_panel": round(bezel, 4), "g_bend": self.g_bend,
                              "land_over_tail_span": round(land_b, 4), "sum": round(bezel + self.g_bend + land_b, 4),
                              "border": bd, "bridge_face_minus_panel_edge": round(pn.y0 - self.slot_bg.y0, 4),
                              "flat_land_after_break": round(flat, 4), "master_flat_land": be["flat_land"],
                              "bead_to_break_edge_measured": [be["calc_measured"], be["measured"], be["z_end"]],
                              "bead_to_break_edge_land_plane": [be["calc_land_plane"], be["land_plane"]],
                              "bead_to_face_plane": [be["calc_face_plane"], be["face_plane"]],
                              "break_edge_checks": be["checks"],
                              "ok": abs(bezel + self.g_bend + land_b - bd) < 1e-6 and
                              abs(pn.y0 - self.slot_bg.y0 - self.g_bend) < 1e-6 and be["ok"]}
        pin = P.d("print_inset")
        res["window_vs_AA"] = {"inset_each_side": [round(w.x0 - self.aa.x0, 4), round(self.aa.x1 - w.x1, 4),
                                                   round(w.y0 - self.aa.y0, 4), round(self.aa.y1 - w.y1, 4)],
                               "print_inset": pin,
                               "ok": all(abs(x - pin) < 1e-6 for x in (w.x0 - self.aa.x0, self.aa.x1 - w.x1,
                                                                       w.y0 - self.aa.y0, self.aa.y1 - w.y1))}
        return res
