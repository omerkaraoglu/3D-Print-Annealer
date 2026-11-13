"""Inline diagnostic calls that were run directly through fusion_mcp_execute and that touched the design state
(kept for the record; everything else run inline was readOnly: viewport/document queries, edge censuses,
face/containment probes, close-up screenshots to the scratchpad).

1. Before 05: deleted the half-built sketch 'PCB bosses H1-H9 sketch' left by the first 05 attempt and tested
   origin dimensions on circles in a throw-away sketch (found the equal-coordinate over-constraint; fv2lib._jit).
2. Fillet probes: diag_fillet_probe.PROBES / probe2() with inline selectors (each test fillet deleted again).
3. Timeline inspection before 18:
       f = L.feature('Root fillets R0.5 - shelf back'); f.timelineObject.rollTo(True)
       ... list edges at Z_SHELF_BACK, y 118.3..119.6 ...
       L.des().timeline.moveToEnd()
4. After the failed first 35 run (userParameters unavailable inside a base-feature edit): looked for the
   'Check - socket cylinders (hidden)' occurrence to finish/delete it - nothing had been created.
"""
