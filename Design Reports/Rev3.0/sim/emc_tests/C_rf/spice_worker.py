"""Run one ngspice netlist in a fresh process (PySpice's shared-library session slows down and grows when reused for many
transients) and save the vectors (time, every V-source branch current, every node voltage) to an .npz.
If ngspice reports an error (e.g. 'timestep too small' on the ideal L / T-line mix) the run is repeated with
gear integration and relaxed tolerances, then with a 10 ps step; the variant used is stored as 'variant'.
usage: python spice_worker.py <netlist.cir> <out.npz>"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
import ngspice_helper

net = open(sys.argv[1], encoding="utf-8").read()
variants = [net,
            net.replace(".tran", ".options method=gear reltol=0.003 abstol=1e-10 vntol=1e-5\n.tran", 1),
            net.replace(".tran 20p", ".tran 10p").replace(" 0 20p", " 0 10p").replace(".tran", ".options method=gear reltol=0.003\n.tran", 1)]
for k, n in enumerate(variants):
    try:
        v = ngspice_helper.run_netlist(n)
        break
    except Exception:
        if k == len(variants) - 1:
            raise
out = {key.replace("#", "_").replace("(", "_").replace(")", "_"): np.asarray(a) for key, a in v.items()}
out["variant"] = np.array(k)
np.savez(sys.argv[2], **out)
