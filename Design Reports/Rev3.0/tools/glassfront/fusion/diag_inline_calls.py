"""Inline calls that were run directly through fusion_mcp_execute (not through a numbered file), kept for the record.
Read-only queries (data folder listing, timeline / log peeks, screenshots, document state) are not listed.

1. After 02 (snap check, design changed and restored): glass_t set to 1.1, 2.0, 4.0, 3.0 in turn and the levels
   Z_GLASS_FRONT .. Z_TUBE_TOP, snap_keep read back. Result = master table (1.1: flange back -7.92, snap_keep 0).
       ups.itemByName('glass_t').expression = g ; L.P(...)
2. Peek screenshots after 07 (read-only): L.shot(...) of F1 and F8 from the back into the scratchpad.
3. Deleted the first rule fillet (10x) again:
       L.feature('Root fillets R0.5 - tubes, tube ribs, step wall to flange back (rule)').deleteMe()
4. Milestone save after 13 = exactly the body of 14_save_fillets_slots.py (document version 3).
5. Section-analysis probe before 26: root XZ plane normal = +Y; sectionAnalyses.createInput(xZ plane, -8.2085)
   -> transform translation (0, -8.2085, 0); analysis deleted again.
6. Layout grid (UI preference, not the design): 'ViewLayoutGridOnCommand' list control, item 'Grid Off' selected
   (now part of 26_renders.grid_off).
"""
