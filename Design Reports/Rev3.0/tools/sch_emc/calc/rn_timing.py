"""RGB/PCLK timing with RN1-RN7 = 33/100/150/220 Ohm at 33.3 MHz (agentHW 2026-11-21).
Edges at the panel input: C_rf c4b_spice_proposals.py (results.json spice_chain.proposal_SI_check): PCLK 10-90 % 1.08 / 1.62 / 3.32 / 5.38 ns.
Skew terms (same R on data and clock, so the common RC delay cancels):
  flight-time difference: RGB 86.7-107.9 mm, PCLK 107.6 mm (C_rf report 8) at 5.97 ps/mm (eeff 3.2186, results.json assumptions) -> |dL| <= 20.9 mm
  RC-delay difference: line C 0.1048 pF/mm (Z 57.3 Ohm, 5.97 ps/mm) x dL + panel Cin spread (5 pF, 3..10 pF assumed in C; same chip
  on every input -> +-1 pF taken as the spread between two inputs), delay ~ 0.69 * R * dC
  threshold uncertainty: panel VIH 0.7 VDD / VIL 0.3 VDD (SAT070AT40D21 DS p.6) -> 0.5 x (0.4/0.8) x t(10-90) per side
  SSD1963 output skew between LSHIFT and LDATA: not published (SSD1963 DS Rev1.1 p.85 gives the waveform only) -> 1 ns ASSUMED
Window: data launched on one LSHIFT edge, sampled on the opposite edge -> 15.0 ns for set-up and 15.0 ns for hold.
Panel set-up/hold: not given in the SAT070AT40D21 datasheet (p.10 lists DCLK 33.3/50 MHz and porches only)."""
T = 1 / 33.3e6 * 1e9
half = T / 2
edges = {33: 1.08, 100: 1.62, 150: 3.32, 220: 5.38}
dL = 107.9 - 86.7
for R, tr in edges.items():
    flight = dL * 5.97e-3
    dC = 0.1048 * dL + 1.0                     # pF
    rc = 0.69 * R * dC * 1e-3                  # ns
    thr = 0.5 * 0.4 / 0.8 * tr                 # ns, per side
    skew = flight + rc + 1.0
    avail = half - skew - thr
    print("R %3d: edge %.2f ns, skew %.2f ns (flight %.2f, RC %.2f, SSD 1.0), threshold %.2f ns -> set-up/hold budget %.1f ns each (of %.1f)" % (R, tr, skew, flight, rc, thr, avail, half))
