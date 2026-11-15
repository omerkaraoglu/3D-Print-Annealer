# R2 — Glass front: manufacturing and sourcing in Turkey (Çerkezköy first)

Research date: 2026-11-15. Scope: printed tempered glass, sheet-metal side without dies, fasteners, the plastic frame at 100–300 pieces, bonding consumables, cost and lead time. Out of scope (other agents): Samsung reference, optical bonding and touch physics, mechanical concept.

**Tags.** Every figure carries one of: **[Q]** quoted/published on the cited page, **[T]** typical practice (trade knowledge, not quoted by a supplier), **[E]** my estimate. Sources are numbered `[Sn]` and listed in §7. Nothing here comes from contact with a supplier: no RFQ was sent, no form was filled.

**Exchange rates used:** 1 USD = **50.34 TRY** (14 Nov 2026 22:00 UTC), 1 EUR = **55.48 TRY** (15 Nov 2026 08:27 UTC), LSEG data via Bing [S70]. Turkish prices move monthly; all TRY figures are dated November 2026.

**Two findings to read first**

1. **SATOZ is not a Turkish company.** satoz.tech identifies SATOZ as Guangdong Shiantong Intelligent Display and Control Co., Ltd., Shenzhen / Dongguan, China [S39]. Özdisan (Istanbul) lists "SATOZ" as the manufacturer of SAT070AT40D21 [S40]. The Turkish link is the distributor, not the maker. SATOZ itself advertises full lamination (optical bonding) and custom cover glass for 7.0–10.4" modules (§5.2). I could not confirm on paper that satoz.tech is the same SATOZ as on Özdisan; the "SAT" prefix and Özdisan's "Üretici Firma: SATOZ" make it likely.
2. **PEM FH-M4 hole size in the v2 frame report is wrong.** `Rev3.0_Frame_Design.md` §1.4 gives the sheet hole as Ø 4.22 +0.08. PEM's own page gives **4.0 mm (+0.08)** for FH-M4 [S49]. 4.22 mm = 0.166", the hole for the inch FH-832 stud. Fix `Rev3.0_FrontSheet_Pattern_v2.dxf` before any sheet is cut (outside my write scope; flagged only).

---

## 1. Printed tempered glass

### 1.1 Suppliers

Status: **verified** = capability stated on a page I opened; **to check** = name verified, the capability that matters here is not.

| # | Supplier | Location | What they state | Thinnest temper / size limits | Small orders? | Status |
|---|---|---|---|---|---|---|
| 1 | **SCHOTT Orim Cam San. ve Tic. A.Ş.** | Çerkezköy OSB, G.O. Paşa Mah. 25 Sok. No 4-5-6 [S1] | Cutting, processing, printing, tempering, gluing, assembly of flat glass for ovens, cooktops, hoods, small appliances, **display glasses** [S1]. 34,000 m², two Turkish sites (Çerkezköy, Bolu) ≈ 700 staff [S2]. Bolu: hob tops, **control panels, multi-printed panels**, coating [S3] | not published | not stated; a white-goods OEM supplier — expect high MOQ [E] | verified (capability) / to check (MOQ) |
| 2 | **Yorglass Endüstriyel Cam** | Çerkezköy plant (press release 5 Oct 2026 [S5]; production-operator ad in Çerkezköy [S6]); own site lists Bolu, Gebze, Eskişehir, Manisa [S7] | Oven panel glass, burner plates, oven doors, fridge shelves; matte, decorative-printed, coloured surfaces [S5] | not published | not stated; OEM supplier [E] | to check (what the Çerkezköy plant does) |
| 3 | **Astro Temperli Cam** | Çerkezköy OSB, G.M.K. Paşa Mah. 16. Sk. No 9 (since 2013), + Edirne [S8] | Horizontal tempering, rodaj, drilling, CNC; architectural + "beyaz eşya camları" (fridge, oven, hood) gallery [S8][S10] | **flat temper 4–19 mm, min 200 × 400 mm** [S9] | glazier-type job shop [E] | verified — **cannot do 185 × 150** (below min size) |
| 4 | **BYC Group** (United Endüstriyel Elmaslar Ltd.) | Köseköy, Kartepe / **Kocaeli** (≈ 200 km from Çerkezköy) [S19] | Thin-glass cutting 0.1–12 mm, laser cutting, **chemical tempering 0.5–19 mm, 10 × 10 to 1200 × 2000 mm**, **thermal tempering 3.2–10 mm, 20 × 20 to 2000 × 1000 mm**, **CNC rodaj ±0.1 mm** (45 × 45 min), waterjet, **serigrafi with organic or ceramic (temper) ink**, AR / AG / anti-fog / anti-finger / EMI coatings [S13–S17]. Made the cover glass of the FATİH smart boards for Vestel; prints "ekran çerçevesi ve logo" [S18] | **3.2 mm thermal; 0.5 mm chemical** [S15][S14] | OEM/ODM, prototype-friendly sizes; MOQ not stated | **verified — best fit** |
| 5 | **Temiz Serigrafi** | Muradiye OSB, Yunusemre / **Manisa** [S22] | "Cam kontrol panelleri": glass touch screens and buttons for white goods, various thicknesses, rodaj / pah kırım / C-edge, printing, integrated circuit prints; clients shown: Arçelik/Beko, Bosch, Siemens, LG, Vestel, Whirlpool [S20][S21] | not stated; tempering not mentioned | not stated | to check (thickness, who tempers, MOQ) |
| 6 | **Saraycam** | Y. Dudullu, Ümraniye / Istanbul [S11] | Tempered glass job shop | **3 mm: min 300 × 400**; 4–19 mm rodaj: min 105 × 350 mm [S11] | yes, job shop | verified — **185 × 150 too small** |
| 7 | **Camglass** | Istanbul + Kırklareli [S12] | Tempered, laminated, bent, ceramic-enamel serigrafi and digital ceramic print, RAL colours; architectural focus [S12] | not published | architectural | to check |
| 8 | **Desiprint** | Y. Dudullu, Ümraniye / Istanbul [S24] | **UV flatbed printing on already-tempered flat glass**, silane primer, ISO 2409 cross-hatch claim; lists appliance control panels, medical windows, lift panels [S24] | n/a (prints only) | UV for small/medium runs [S24] | verified (printing only) |
| 9 | Yıldız Serigrafi | İkitelli OSB, Başakşehir / Istanbul [S25] | Screen + UV + pad printing on bottles, caps, glass; Pantone matching, samples [S25] | n/a | samples offered | to check (flat glass, 2K inks) |
| 10 | Zirve Tezyinat | Kurtpınar OSB, Muratlı / Tekirdağ [S26] | Glassware decoration: 2 × 8-colour + 1 × 6-colour automatic screen lines, decoration kilns [S26] | n/a | high volume (200,000/day) | to check (flat parts) |
| 11 | Ortakçı Cam | İnegöl OSB / Bursa | Directory: serigraph-painted tempered glass, CNC, for white goods and hoods [S27]; own site shows automotive only | not published | — | to check |
| 12 | Çağdaş Cam | Kuyucak / Aydın (white-goods glass) [S28] | Household and commercial white-goods glass | not published | — | to check |
| 13 | "serigrafik" (commercial printer), İtimat Cam (glazier) | Barbaros Cad., Çerkezköy [S31] | map listings only | — | — | to check |
| 14 | Kolhis Global Cam | Trabzon / Istanbul [S29] | B2B listing: hood / cooktop / oven glass, screen printing (self-described) | — | samples "open to discuss" | to check |

**Reading of the market.** Around Çerkezköy the capability exists, but in two shapes that do not fit 100 pieces of 185 × 150 well:
- the two white-goods majors (SCHOTT, Yorglass) do exactly this part, at OEM volumes;
- the local tempering shops (Astro, Saraycam type) run architectural horizontal lines whose **minimum piece size is 105–300 × 350–400 mm** [S9][S11]. A 185 × 150 piece falls between the rollers.

The only page-verified supplier that combines small sizes, ±0.1 mm CNC edging, chemical **and** thermal tempering, serigrafi and display-glass references is **BYC Group in Kocaeli** [S13–S18]. Second choice: Temiz Serigrafi (Manisa), which makes glass control panels for the same OEMs (to check). Third: SCHOTT Çerkezköy for a quote on a prototype lot (to check).

### 1.2 Generic capability picture (Turkey)

| Item | Value | Tag / source |
|---|---|---|
| Thermal tempering, architectural lines | 4 mm min (Astro), 3 mm min with 300 × 400 min size (Saraycam) | [Q] [S9][S11] |
| Thermal tempering, small-part line | 3.2 mm min, 20 × 20 mm min size (BYC) | [Q] [S15] |
| Thermal tempering 2–2.8 mm | needs special thin-glass furnaces (GlastonAir to 2 mm; Lisec AEROFLAT 3–8 mm FT, 2–8 mm HS). None found in Turkey | [Q, search index] [S32] |
| Appliance glass (oven doors, panels) | 3–6 mm soda-lime, thermally tempered, ceramic print fired in the temper | [T] |
| Chemically strengthened (ion exchange) | **available locally: BYC 0.5–19 mm**, CS ≤ 1000 MPa "depending on glass type", 300–450 °C K-salt bath | [Q] [S14] |
| CS glass, imported | SATOZ: aluminosilicate 0.55–2.0 mm (CS ≥ 700 MPa, DOL ≥ 35 µm); soda-lime "ceramic" ≥ 2.0 mm (CS ≥ 500, DOL ≥ 10 µm, curvature 1 ‰) | [Q] [S39] |
| Outline tolerance, Turkish sector norm | **±1 mm** ("sektör tolerans olarak +1 mm veya −1 mm") | [Q] [S16] |
| Outline tolerance, precision CNC | ±0.1 mm (BYC); cover-glass makers ±0.10–0.15 | [Q] [S16]; [Q, search index] |
| Thickness tolerance (float 2–6 mm) | ±0.2 mm | [T] (EN 572-2 class) |
| Flatness, thermally tempered | overall bow ≤ 3 mm/m, local bow ≤ 0.5 mm / 300 mm (EN 12150-1, horizontal) → up to **0.55 mm over 185 mm** | [Q, secondary: TuffX handbook citing EN 12150-1] [S33] |
| Flatness, chemically strengthened | ≈ float flatness; SATOZ quotes 1 ‰ (0.19 mm over 185) for ≥ 2 mm | [Q] [S39] / [T] |
| Edge finishes | rodaj (ground), parlak/mat rodaj (polished/satin), C-rodaj (C-edge), bizote (bevel), pah kırma (arris/chamfer), köşe kırma (dubbed corner, 0.5–2.0 mm per SCHOTT) | [Q] [S4][S20] |
| Corner radius | SCHOTT standard min **R 3 ±0.5** (smaller on request) | [Q, search index] [S4] |
| Holes | SCHOTT hole position ±0.3; dia ±0.5 (≤ 100 mm). Rule: hole Ø ≥ glass thickness | [Q, search index] [S4][S38] |
| Print types | (a) ceramic/enamel ("temper boya"), fired during thermal tempering — permanent, only with thermal temper; (b) organic 2K, screen-printed after tempering or CS, baked e.g. 140 °C / 30 min; (c) UV inkjet/flatbed after tempering with silane primer | [Q] [S17][S35][S24] |
| Organic ink film | 5–12 µm per pass (Marabu GL); mesh 140-31…150-31, 100-40…120-34 for higher opacity; flame pre-treat | [Q] [S35] |
| Black-mask opacity | OD ≥ 4 needs 2–3 organic passes ≈ 15–30 µm total | [T] |
| Print-to-print registration | ≤ 0.3 mm; min line / dot 0.5 mm; > 10 colours possible (SCHOTT) | [Q, search index] [S4] |
| Print-to-outline registration | cover-glass practice ±0.1 mm [S34]; architectural screens up to 3 mm (0.8 mm only if specified) [S36] | [Q] |
| Second colour (logo) | one more screen per colour; white/silver usually need 2 passes for opacity | [T] |
| Screen set-up | 1,500–4,000 TRY per screen (frame, mesh, emulsion, film); 1 per colour per side | [E] |
| Price, China benchmark | 3 mm tempered silk-screened panels: US$ 0.63–0.90 (switch cover, 1–499 pcs tier); US$ 3.90 MOQ 100 (touch cover) | [Q, marketplace snippets] [S37] |
| Price, Turkey, 100–120 × 185 × 150 × 3 mm, black border + logo, C-edge, tempered | **300–1,200 TRY/pc (likely 600)** + 5,000–25,000 TRY set-up (screens, CNC program, first articles) | [E] |
| Lead time, Turkey small lot | artwork approval 1 wk, screens 3–5 days, production 2–4 wk → **3–5 weeks** | [E] |
| Lead time, SCHOTT/Yorglass prototype lot | 8–12 weeks incl. sampling | [E] |

**Which strengthening for this part.**
- *Thermal tempering at 3 mm*: only on appliance lines or BYC-type small furnaces (3.2 mm min at BYC). Gives the "safety glass" fragmentation, but bow up to ~0.5 mm over the part [S33]. That is hard on a dry OCA lamination; LOCA or thick OCA absorbs it.
- *Chemical strengthening at 2–3 mm*: no size limit, float flatness, organic print after strengthening. Breaks in large shards (no dicing). Available locally (BYC) and from SATOZ.
- *4 mm thermal*: widely available, but 4 mm changes the flush geometry (glass back 3 mm behind the sheet's back face).

### 1.3 What the glass shop needs (drawing / artwork)

- **DXF 1:1 in mm**: outline, corner radii, (no holes), print window and logo as separate layers. Many shops also take STEP.
- **PDF / AI vector artwork**, **mirrored**, marked "2. yüz / iç yüz baskı (ters baskı)" with a view-from-front reference image.
- Colour: black as RAL 9005 or Pantone Black 6 C, **OD ≥ 4 (target), measured at 550 nm**; logo colour as Pantone / RAL. Gloss: matte or satin black.
- Tolerance block: outline ±0.1 (or ±0.2), thickness ±0.2, print-to-edge ±0.2, print-to-print ±0.3, window corner radius, flatness (≤ 0.2 mm over the part if dry OCA is used).
- Edge: C-rodaj parlak, or düz rodaj + 0.3–0.5 × 45° pah both sides; corners R ≥ 3.
- Cosmetic acceptance: viewing distance 300–500 mm, scratch / pinhole / ink-edge (saw-tooth) limits, inside the window vs. under the black.
- Strengthening: "kimyasal temper, CS ≥ 450 MPa, DOL ≥ 10 µm" or "ısıl temper EN 12150-1, kırılma testi".

### 1.4 Turkish search terms and RFQ text

Search terms: `serigrafi baskılı temperli cam`, `ekran camı / kapak camı / ön panel camı`, `dokunmatik panel camı`, `kimyasal temperli cam`, `ince cam kesimi`, `CNC cam rodaj ±0,1`, `C rodaj parlak`, `pah kırma`, `köşe radyus`, `siyah çerçeve baskı`, `organik cam boyası serigrafi`, `seramik (emaye) temper boya`, `AG / AR / AF kaplama cam`, `beyaz eşya cam kontrol paneli`, `numune üretimi cam`.

RFQ (Turkish, ready to paste):

> **Konu: Fiyat teklifi talebi — serigrafi baskılı temperli ekran camı, 100–120 adet**
>
> Merhaba,
> Aşağıdaki cam için fiyat ve termin teklifi rica ediyoruz. Teknik resim (DXF) ve baskı dosyası (PDF, ters/ayna baskı) ektedir.
> - Malzeme: şeffaf float cam (tercihen low-iron / ekstra şeffaf), kalınlık **3 mm** (alternatif 4 mm için de fiyat veriniz).
> - Ölçü: **185 × ___ mm** (125–155 arası, resme göre), köşeler **R3**, delik yok.
> - Kenar: CNC rodaj, **C kenar parlak** (veya düz rodaj + 0,3–0,5 mm pah, iki yüz). Ölçü toleransı **±0,1 mm** (mümkün değilse ulaşabileceğiniz toleransı belirtiniz).
> - Sertleştirme: **kimyasal temper** (CS ≥ 450 MPa) **veya ısıl temper** (EN 12150-1). Hangisini önerirsiniz, düzlemsellik (sehim) değeriniz nedir?
> - Baskı: **iç yüze (2. yüz) serigrafi**, siyah çerçeve (RAL 9005 / Pantone Black 6C), optik yoğunluk **OD ≥ 4**, ayrıca **1 renk logo**. Baskı–kenar toleransı ±0,2 mm, baskı–baskı ±0,3 mm. Organik (2K) veya seramik boya — önerinizi belirtiniz.
> - Opsiyon: dış yüze AG veya AF kaplama fiyatı ayrıca.
> - Adet: **100–120 adet**, önce **5 adet numune**.
> - Lütfen belirtiniz: birim fiyat, elek/kalıp ve CNC programı (tek seferlik) bedeli, numune termini, seri termini, minimum sipariş, ambalaj (ara kâğıt / koruyucu film).
> Teşekkürler.

### 1.5 Design consequences (glass)

1. **Glass thickness is a parameter, 3.0–4.0 mm**, until a quote fixes it. 3.0 mm thermal is not on BYC's list (3.2 mm min) [S15]; 3.0 mm chemical is.
2. **Outline 185 × (125…155), corners R ≥ 3 mm** [S4]. No holes, no notches in the glass.
3. **Outline tolerance: design for ±0.2 mm** (precision CNC) — and never assume the sector's ±1 mm [S16]. Make it a drawing call-out.
4. **Thickness tolerance ±0.2 mm** [T] → flushness must be set by a bonding jig, not by the part stack (§4.5, §5.4).
5. **Flatness**: thermally tempered may bow up to ~0.55 mm over 185 mm [S33]. For dry OCA ask for ≤ 0.2 mm or use chemical strengthening; otherwise use LOCA / thick OCA (other agent).
6. **Print window = active area 154.08 × 85.92 + ≥ 0.5 mm per side** (print-to-edge ±0.2 + display-to-glass alignment ±0.3) → window ≥ 155.1 × 86.9, recommend 0.75 mm per side (155.6 × 87.4) [E]; coordinate with the bonding agent.
7. **Ink step 15–30 µm** at the window edge [S35][T]; the OCA/LOCA choice must bury it.
8. **Min print feature 0.5 mm**, print-to-print ≤ 0.3 mm [S4]; keep logo strokes ≥ 0.5 mm and ≥ 1 mm from the window edge.
9. Print **to the glass edge** (allowed setback 0…0.2 mm), so no clear sliver shows in the gap to the sheet [E].
10. Organic ink limits the glass face temperature to the ink rating (bake 140 °C [S35]); fine for a control-panel face at ≤ 70 °C [T].

---

## 2. Sheet-metal side without dies

### 2.1 Local shops

| Shop | Location | Stated | Source |
|---|---|---|---|
| **Airsan Metal İşleme** | Seymen Mah., Çorlu (serves Çerkezköy OSB) | laser, press brake, sheet-metal centre; white-goods sub-supplier (Arçelik named); **±0.05 mm cutting accuracy, "çapaksız"** claim; 24–48 h for stocked DKP / galvanised | [Q] [S41] |
| **KOZMETAL** | Kapaklı / Tekirdağ | CNC laser, CNC press brake, electrostatic powder coating, robotic + MIG welding, assembly | [Q] [S42] |
| **Tekniksat Metal** | Esenyurt / Istanbul | **CNC turret punch (TP series, 29 stations + 2 index)**: punching, **forming, tapping, wheel tools**; fibre laser (N₂/O₂/air); press brake to 10 mm; powder coating 200 m²/h | [Q] [S43] |
| Famak Makina | Nilüfer / Bursa | Turkish maker of **belt and brush deburring / edge-rounding machines** for laser-cut sheet — i.e. such machines are in Turkish job shops | [Q] [S44] |

Turret punches with standard forming tools are common in Istanbul electrical-panel ("pano") shops [T]; I did not find one advertised in Çerkezköy itself (to check).

### 2.2 Capabilities on 1.0 mm (0.8–1.5) DKP or stainless

| Topic | Value / practice | Tag |
|---|---|---|
| Laser cut accuracy | ±0.05 (claim) [S41]; plan **±0.1 mm** on a cut-out | [Q]/[T] |
| Visible edge | N₂ cutting gives a bright, oxide-free edge; micro-burr on the exit side; perpendicularity per ISO 9013 | [T] |
| Micro-joints | the cut-out slug is held by micro-joints / lead-ins → **specify: pierce and micro-joints in the scrap, none on the visible edge** ("görünür kenarda mikro bağlantı ve delme izi olmayacak") | [T] |
| Deburr / edge rounding | manual (deburring blade, Scotch-Brite) in small shops; brush/belt machines (Famak, Lissmac, Timesavers type) in larger shops → edge break R 0.2–0.5 mm; vibratory finishing only for small parts, not a front panel | [T] [S44] |
| Paint on edges | powder coat 60–80 µm pulls back from sharp edges → deburr before coating | [T] |
| Min bend flange | 1.0 mm on V8: **≥ 5.5 mm** (Durma chart); rule of thumb 70–77 % of V (V6 → 4.2–4.6 mm); WILA ≥ 6 t | [Q, search index] [S45] |
| Inside bend radius | ≈ 1.0–1.5 mm (air bending, V6–V8) | [T] |
| Hole / cut-out to bend line | ≥ 2 t + r ≈ 3–3.5 mm, else distortion | [T] |
| Internal flange round a closed window | not a standard press-brake operation (4-sided internal return needs segmented tooling and corner reliefs; two opposite sides at best) — **check with shop** | [E] |
| Turret-punch standard forms | louvre, **countersink dimple (havşa)**, extruded hole (flanşlı delik) + tapping, half-shear locating bumps, card guides, short offsets, knock-outs | [Q] [S43] / [T] |
| What forms allow here | (a) **countersunk dimple → flush countersunk rivet or screw head** on 1.0 mm sheet; (b) half-shear bumps on the back to locate the frame; (c) extruded M3/M4 threads (open on the front → only where hidden) | [T] |
| What forms do not allow | a long recess / joggle round the glass (that needs a die) | [T] |

### 2.3 Hidden-fastener options on the sheet

| Option | Front appearance | Constraints on 1.0 mm | Cost per point (installed) |
|---|---|---|---|
| **CD (capacitor-discharge) weld stud**, ISO 13918, tip ignition ("kondansatör deşarjlı saplama kaynağı") | none, or a faint witness | Promsis sheet ranges: **M3/M4 0.7–1.4 mm**, M5/M6 0.8–1.4 mm [S47]; Soyer min sheet 1/10 d, ≥ 0.5 mm [S48]; drawn-arc needs t ≥ d/3 (≤ M10) → **CD only** [S48 snippet: Taylor] | stud 1–3 TRY + welding 2–5 TRY [E] |
| PEM FH-M4 clinch stud | **flush Ø 5.9 head visible** on the front | sheet ≥ 1.0 mm, hole **4.0 +0.08**, HRB ≤ 80, edge ≥ 7.2 mm [Q] [S49]; FHS / FH4 for stainless | 5–15 TRY [E] |
| PEM concealed-head CHC/CHA | none | sheet **≥ 1.60 mm** for M4 [Q] [S50] → **not on 1.0 mm** | — |
| Rivet nut ("somun perçin") | flange visible (flush-head needs a countersink 1.0 mm cannot hold) | — | 0.7–5 TRY + setting [Q] [S57] |
| Countersunk blind rivet in a punched dimple | flush Ø ≈ 7–8 disc, paintable / black | needs a countersink-forming tool in the turret | 1–3 TRY + tool if the shop lacks it [E] |
| Bonded fixings (VHB or MS-polymer bonded brackets; bigHead perforated-head bonded studs, Bossard brand) | none | surface prep, cure time; bigHead Turkish distributor not found | to check [S72] |
| No fixing through the front skin: frame clamped by an inner bracket to the oven chassis | none | mechanical concept (other agent) | — |

CD studs — points to settle by test [T]:
- On 1.0 mm mild steel an M3/M4 CD stud usually leaves only a faint ring or slight dimple on the face side. Under 60–80 µm powder coat it is normally invisible. On pre-painted sheet (paint burn) and on brushed stainless (heat tint, dimple catches the light) it can show.
- **Weld before painting.** Cap or mask the threads in the paint shop. Earth contact needs bare metal.
- Stainless sheet: A2 studs. Galvanised: coating ≤ 25 µm for tip ignition (Taylor table, search index [S48]).
- Order a **test coupon** (same sheet, same finish, 3 studs each M3 and M4) before release.

Where to buy: CD studs M3–M8, external/internal thread, steel copper-plated / A2 / Al: **Promsis**, Perpa Şişli, Istanbul [S47]; Star Bağlantı (Ataşehir) also lists weld studs and press-in fasteners [S51]; Onurfix (Ümraniye) weld studs [S54]. PEM has a Turkey sales office in Istanbul (PEM locations page, search index only; page 401 on fetch) [S71].

### 2.4 Design consequences (sheet metal)

1. **Cut-out = glass outline + 0.5 mm per side nominal** (laser ±0.1, glass ±0.1–0.2, frame location ±0.15 → no contact at worst case) [E]; corner radius = glass R + 0.5 (R 3 glass → R 3.5 cut-out).
2. Drawing note: **no pierce points, lead-ins or micro-joints on the visible cut-out edge**; deburr to R 0.2–0.5 before coating.
3. Keep every hole, stud and form **≥ 7.2 mm** (PEM edge rule [S49]) — design to **≥ 8 mm** — from the cut-out edge and from bends; ≥ 3.5 mm from a bend line.
4. **Fixings through the visible ring round the glass: CD weld studs M4 (or M3) on the inner face**, welded before paint, released by a coupon test. PEM FH heads would show as Ø 5.9 discs.
5. If a stud must go through to the front, use a **punched countersink dimple + countersunk fastener** (flush), not a dome head.
6. Correct the PEM FH-M4 hole to **Ø 4.0 +0.08** wherever PEM studs remain [S49].
7. Flanges (if any) ≥ 5.5 mm on 1.0 mm sheet [S45]; no closed-window return flange unless the shop confirms it.
8. Sheet flatness round a large window is ±0.3 mm class [T]. The clamping pattern (studs every ≤ 60 mm, as v2) also flattens the sheet edge at the glass.

---

## 3. Rivets and fasteners, sheet to plastic flange

### 3.1 What is available in Turkey

| Type (Turkish trade name) | Where | Notes |
|---|---|---|
| Standard open dome "pop perçin" Al/St, ISO 15977 | everywhere; 4 × 10 Al ≈ **0.74 TRY/pc** in 1000-packs (Akakçe, Nov 2026) | [Q] [S57] |
| Large flange "geniş başlı / geniş kafa" (LKS, ASMG-LF, LPR) | Micro Perçin (Uzman Alüminyum Perçin, Bornova / İzmir) | [Q] [S52] |
| **Coloured heads** — standard white / black / grey on NKS (dome) and LKS (large flange); other colours ask | Micro Perçin | [Q] [S52] |
| Multigrip (ASMG, SSMG, PSMG) | Micro Perçin; Star Bağlantı | [Q] [S51][S52] |
| Sealed / closed end "arkası kapalı, sızdırmaz" (SAS) | Micro Perçin; Star Bağlantı | [Q] [S51][S52] |
| **Tri-fold / bulb types for plastics**: "papatya (3 wings)" — Star Bağlantı; "ahtapot" (PR/LPR) and "bulb, yarıklı" (BL, EBL) — Micro Perçin | Ataşehir (Istanbul) / İzmir | [Q] [S51][S52] |
| Stainless "inox" rivets | Micro Perçin, Hedef Bağlantı, Onurfix | [Q] [S52][S53][S54] |
| Rivet nuts M4 | 0.72–4.95 TRY/pc by type and pack (Akakçe) | [Q] [S57] |

Reference brand data (for the drawing):
- **ISO 15977 open-end Al/St dome head** [Q] [S55]:
  - Ø 3.2: head dk ≤ 6.7 mm, **height k ≤ 1.3 mm**; grip 3–5 mm at L 8.
  - Ø 4.0: dk ≤ 8.4 mm, **k ≤ 1.7 mm**; grip 2.5–4 at L 8, 4–6 at L 10.
  - Ø 4.8: dk ≤ 10.1 mm, k ≤ 2.0 mm.
- **GESIPA TRI-FOLD Al/Al 4.8 × 16** [Q] [S56]: head Ø 10.1 mm, hole 5.1–5.4 mm, shear 900 N, tensile 1,300 N; marketed for soft and brittle materials and plastics.
- Hole for Ø 4.0: 4.1–4.2 mm [T].

### 3.2 Four visible rivets: 1.0 mm sheet + 2.5–3.0 mm PA6-GF30 flange

- **Grip** = 1.0 + 2.5…3.0 = 3.5–4.0 mm (+ any spacer or gasket in the joint). Fits Ø 3.2 × 8 (grip 3–5) or Ø 4.0 × 8 (2.5–4, at its top end) [S55]; multigrip if the gasket is in the stack.
- **How proud it sits**: dome Ø 4.0 up to 1.7 mm, Ø 3.2 up to 1.3 mm [S55]. Large flange ≈ 1.0–1.3 mm high but Ø ≈ 12 mm [T]. Countersunk in a punched dimple: flush [T].
- **Setting load on the plastic** [E]:
  - A Ø 4 Al/St rivet breaks its mandrel at roughly 2–3 kN [T].
  - A standard dome rivet forms a blind bulb of Ø ≈ 6–6.5 mm, i.e. about 20 mm² of bearing on the Ø 4.1 hole. That is ~100–125 MPa transient on PA6-GF30: crushing / cracking risk, and far above the 15 MPa creep allowance used in v2 (§5.3 of the frame report).
  - A tri-fold (legs ≈ Ø 10–12 mm footprint, ~57 mm²) gives ~35–45 MPa transient and relaxes.
  - So: **tri-fold / bulb Al/Al rivets, or a steel backing washer on the blind side** (only if the back is accessible during setting).
- **Thermal mismatch.** Four rivets clamp the frame rigidly at the corners. PA6-GF30 (30–70 ppm/K) against steel (12 ppm/K) over ΔT 60 K and ~250 mm between diagonal corners: **0.27–0.87 mm** of mismatch [E] from the v2 report's values. Rivets cannot slide, so the flange will bow or creep, or the rivets take the shear. v2 solved this with radial slots under nyloc nuts.
- **Cosmetics.** Black-painted aluminium heads on a black-painted panel blend best. Stainless rivets on brushed stainless. Painted heads can chip at the mandrel break [T].
- **Sealing.** Use sealed (closed-end) rivets if the oven front sees steam [T].

### 3.3 Fastener cost comparison, per oven

| Scheme | Parts | Per oven [E] |
|---|---|---|
| 4 black dome rivets Ø 3.2/4.0 Al/St | 4 × 1–3 TRY | **5–15 TRY** + hand riveter 500–1,500 TRY one-off |
| 4 tri-fold Al/Al, black | 4 × 3–8 TRY | 15–35 TRY |
| 4 countersunk rivets in dimples (flush) | 4 × 1–3 TRY + dimple tool (if missing) 10–25k TRY one-off | 5–15 TRY |
| 10 CD M4 studs + DIN 9021 + nyloc (v2 pattern) | stud + weld 3–8, washer + nut 2–3 | **60–110 TRY** |
| 10 PEM FH-M4 + washer + nut | 7–18 per point | 70–180 TRY |

### 3.4 Design consequences (fasteners)

1. If rivets are used: **Ø 3.2 or Ø 4.0, grip 3.5–4.0 mm** (or multigrip), holes Ø 3.3 / 4.1–4.2, **≥ 8 mm (2 d) from the glass cut-out** and sheet edges [T].
2. Flat, solid flange under each rivet (no ribs, no gasket in the grip). Boss/flange **≥ Ø 14** for a tri-fold footprint.
3. **Tri-fold / bulb Al/Al** or backing washer — not a standard bulb directly on PA6-GF30.
4. **Rivets give no thermal float.** Either accept a corner-only fixation with compliant flanges (mechanical agent to check), or keep **hidden CD studs in radial slots (v2 logic)** — my recommendation.
5. Budget **1.3–1.7 mm head projection** for dome heads, **0 mm** for dimple + countersunk.

---

## 4. The plastic frame at 100–300 pieces

Part: ≈ 200 × 170 × 16 mm, ≈ 55 cm³ (75 g in PA6-GF30), single-cavity, two-plate, no slides (v2 report §1.5, §7).

### 4.1 Routes compared

| Route | Tool / NRE | Piece price (100–300) | Lead | Flame / glow-wire | Tag / source |
|---|---|---|---|---|---|
| **Steel mould** (P20 / 1.2311 / 1.2738) | simple single cavity 80–250k TRY; medium (cores, ejectors) **250–700k TRY** — this part is "medium" → 300–500k TRY ($6–10k) | 60–150 TRY | **8–12+ weeks** | any grade, e.g. Durethan BKV30FN04 (V-0, GWFI 960, GWIT ≥ 775 to confirm) | [Q] [S58][S59] / [E] |
| **Aluminium mould** (7075) | Al prototype tools **40–150k TRY** (generic); MARG small parts US$ 1–2.5k; Al ≈ 2–3× cheaper than steel → this part **100–300k TRY** (likely 175k) | 60–150 TRY | days–few weeks (MARG); **4–6 weeks** for this part | same material as steel. GF30 is abrasive: Al life ~ 1–5k shots [E]; MARG notes GF materials "call for steel" | [Q] [S58][S59] / [E] |
| **MJF PA12** (HP), Istanbul bureaus (T3Dizayn Sultangazi, Başaran Ümraniye, Printly Avcılar, MARM Kadıköy, Xometry TR) | none | **10–30 TRY/g** → 560–1,680 TRY/part (56 g) | 2–6 days | **standard PA12 not FR**; no FR grade listed by the Istanbul bureaus I opened | [Q] [S60][S61] |
| **MJF HP 3D HR PA12 FR** (EU bureaus) | none | ≈ €40–80 → 2,200–4,400 TRY/part | 1–2 weeks + shipping | **UL94 V-0 at 2.5 mm, V-2 at 1.8, HB at 1.0** (HP); **GWFI / GWIT not published** ("reach out to an HP representative") | [Q] [S62] / [E] price |
| **SLS EOS PA 2241 FR** | none | similar to MJF FR | 1–2 weeks | HDT 154 °C @ 0.45 MPa (EOS); V-0 thickness not confirmed; GW not published | [Q, search index] [S63] |
| **FDM FR** (PC-FR, PC/ABS-FR, ULTEM 9085) | none | 3–12 TRY/g generic FDM; FR filaments rarely offered locally | days | V-0 grades exist; layer adhesion, anisotropy, no GW data → **not for a mains-adjacent part** | [Q] [S60] / [T] |
| **CNC from plate** (FR4/G10, PC-FR, PEI) | fixture + CAM 5–15k TRY | 2,500–6,000 TRY/part (15 mm deep ring with 9 bosses, 10 tubes) | 1–3 weeks | FR4 can meet GWFI 960; others to check | [E] |
| Vacuum casting PU (FR resin) | silicone mould 5–30k TRY per ~20 parts | 300–800 TRY | 2–3 weeks | FR PU grades exist; GW unknown | [Q] [S58] / [E] |

**IEC 60335-1 cl. 30.2.3.** The frame sits **1.21 mm** from mains copper (J4.1), inside the 3 mm zone round connections carrying > 0.2 A. So it needs **GWFI ≥ 850 °C and GWIT ≥ 775 °C** on the material, or the **750 °C glow-wire test on the part** (flame ≤ 2 s, else needle-flame on the surroundings) (v2 report §3). No printed FR grade I found publishes GWFI/GWIT [S62][S63]. A printed frame therefore needs a **glow-wire test on the finished part** at a lab: ≈ 5–15k TRY [E].

**Material locally.** FR PA6-GF30 is sold by Istanbul resin distributors. Aydın Plastik (Bayrampaşa) lists flame-retardant PA6; the search index shows "Pimamid V G30 V100 NL — PA6 GF30, UL94 V-0, **halojenli**" (halogenated) [S64]. Halogen-free GWIT-775 grades (Durethan BKV30FN04, Ultramid B3UG4 class) must be confirmed with the distributor. Lot: one 25 kg bag ≈ 250 parts; at €6–9/kg about 8–12.5k TRY [E].

### 4.2 Break-even (likely values) [E]

- **Aluminium tool vs MJF PA12 FR (EU, ~3,330 TRY/part)**: 175,000 / (3,330 − 120) ≈ **55 parts**.
- **Aluminium tool vs MJF PA12 non-FR (~1,120 TRY/part)**: 175,000 / (1,120 − 120) ≈ **175 parts**, and non-FR fails cl. 30 anyway.
- **Steel vs aluminium**: the extra 125–325k TRY buys tool life only. It pays back at thousands of parts per year, not at 300.
- **CNC from plate** loses to the aluminium tool above ≈ 40–70 parts.

### 4.3 Recommendation for the first 100

1. **2–3 MJF PA12 (non-FR) fit samples first**: about 600–1,700 TRY each, 2–6 days, from an Istanbul bureau. Check against the real panel, glass and sheet before cutting the tool.
2. **Aluminium single-cavity tool from the v2 CAD** (gating, ejection and draft already set for a two-plate tool). Hardened steel inserts at the sub-gates and for the slender pilot / slot pins if the toolmaker advises.
3. Mould **300 parts in one run** in a **halogen-free FR PA6-GF30 with GWIT ≥ 775 °C** on the UL card. Lead time **5–7 weeks** to T1.
4. Run the **Moldflow / warp check** the v2 report already asks for. Flatness of the bond / clamp face ≤ 0.3 mm matters even more with glass.
5. Go to steel only when annual volume passes a few thousand.

### 4.4 Design consequences (frame)

1. Keep the frame **two-plate, one pull, no slides**: the aluminium-tool price assumes it.
2. Walls stay **≥ 2.5 mm** wherever the part could ever be printed in PA12 FR (HP V-0 only at 2.5 mm [S62]).
3. Give the glass-bond land a **flat, toolable face ≥ 6–8 mm wide** with an **adhesive gap set by stand-off pips** (§5.4). The jig, not the part, sets glass flushness.
4. Leave **material choice open between PA6-GF30 FR and an unfilled FR grade**. Unfilled is kinder to an aluminium tool but creeps more; re-run v2 §5 if changed.
5. If rivets are used (§3), each rivet seat is a **flat solid pad ≥ Ø 14** with no rib under it.

---

## 5. Bonding consumables and display side

### 5.1 Consumables available in Turkey

| Item | Availability / price (Nov 2026) | Tag / source |
|---|---|---|
| **OCA film sheets** | Phone/tablet-repair channel: tablet-size sheets (e.g. Mitsubishi-branded, 6–12.9" listings; iPad mini OCA ≈ 318 TRY). Thickness and grade rarely stated. Industrial OCA (3M 8146-x, tesa 58xx "cover glass to touch panel") via converters — tesa TR lists the series [S67] | [Q] [S65][S67] |
| OCA 175–250 µm, 7–8", industrial grade | import (China) ≈ $1–3 / sheet at 100 pcs; local repair-grade 150–350 TRY | [E] |
| **LOCA UV resin** | TP-2500F type, 50 ml ≈ 297–301 TRY (Akakçe) → ≈ 5 ml per display ≈ 30 TRY | [Q] [S65] / [E] |
| UV curing | 365/395 nm LED lamp or box 3–15k TRY | [E] |
| Debubbler / small autoclave (OCA route) | repair-grade 15–40k TRY | [E] |
| **3M VHB** | 3M Türkiye product pages (4910, 5952F) [S68]; retail 4910F 19 mm × 33 m **3,875–5,936 TRY**, 12 mm × 33 m 2,375 TRY (Akakçe) | [Q] [S65] |
| VHB grades to stock | **4910/4905 clear** (glass), **5952 black** (plastics, painted metal), **4611 grey** (high temperature) | [T] |
| **Die-cut ("kesim") service** | **Ulus Bant** (Akçaburgaz, Esenyurt / Istanbul): 3M VHB die-cut / kiss-cut, rotary, finger-lift [S66]; **Nordem** (Nilüfer / Bursa): die- and kiss-cut, laser and steel-rule [S66] | [Q] |
| Glass primer | 3M Primer 94 / silane glass primer, one can ≈ 100 units | [T] / [E] |
| **Neutral silicone** | Akfix 900N 310 ml **212–273 TRY**; Selsil 06 300 ml 260 TRY (Akakçe). Somafix: no listing found | [Q] [S65] |
| **MS polymer** | Akfix MS757 290 ml 381 TRY; Soudal Fix All High Tack 290 ml 311 TRY (Akakçe) | [Q] [S65] |
| Sika, Dow (DOWSIL) | via industrial distributors; prices not checked | to check |
| **Formex GK-17** (0.43 mm FR PP) | Turkish-language pages only from Chinese converters (Vantape, GBS); ITW Formex lists UL94 V-0. No Turkish converter verified — ask Ulus Bant / Nordem to cut supplied sheet | [Q] [S69] / to check |

Notes [T]:
- Use **neutral (alkoxy / oxime) silicone, never acetoxy**: acetic acid attacks copper, ink and some coatings.
- MS polymer bonds glass + PA6 well with primer and stays elastic. It also fills ±0.2 mm thickness scatter, which VHB foam does not.

### 5.2 Display houses: cover lens and optical bonding

- **SATOZ** (satoz.tech, Shenzhen / Dongguan) [S39]:
  - Medium-size (7.0–10.4") assemblies with **"Full Lamination, Air Bonding"**, G+G / G+F / G+FF, **"2.5D Cover Glass, All-in-one Black"**, AG / AR / AF, "10 mm thick cover glass", −40…85 °C, "customized according to customer requirements".
  - Cover glass series: aluminosilicate 0.55–2.0 mm (CS ≥ 700 MPa, DOL ≥ 35 µm); soda-lime ≥ 2.0 mm (CS ≥ 500 MPa, DOL ≥ 10 µm, curvature 1 ‰).
  - **No MOQ stated.**
  - In Turkey: Özdisan lists SAT070AT40D21Y0-35100T07 with MOQ 1 / MPQ 76, 0 in stock on 15 Nov 2026 [S40]. A custom lamination would be an Özdisan project request. Lead time 8–12 weeks incl. samples [E]; MOQ probably ≥ several hundred [E] — **to check**.
- **Turkish optical-bonding houses**: none with a public page found. BYC makes cover glass for Vestel smart boards but does not advertise lamination [S18]; Temiz Serigrafi makes glass touch panels for white goods [S20] (bonding not stated). **To check.**

### 5.3 Route B worth pricing in parallel

Buy the panel **with a custom 185 × ~140 × 2–3 mm cover glass, black border + logo, fully laminated by SATOZ**, through Özdisan. That replaces glass sourcing, print set-up, OCA and the lamination jig (≈ $2,700 of the likely roll-up) with a per-unit adder (≈ $10–25 [E]) plus NRE (≈ $300–1,500 [E]). It leaves the glass "made in China, bought in Turkey". It is the lowest-risk optics route if the MOQ fits.

### 5.4 Design consequences (bonding side)

1. **Glass-to-frame bondline ≥ 0.5 mm nominal** (MS polymer / neutral silicone), set by **0.5 mm stand-off pips** on the frame. Absorbs glass ±0.2 + frame ±0.1 + sheet ±0.08 → flush within ±0.1 when bonded in a jig [E].
2. **Bonding jig references the glass front face and the frame's sheet-contact face** (offset = sheet thickness 1.0 mm) on one flat plate. The jig defines flushness.
3. VHB is fine where the bondline is fixed (e.g. frame to sheet back). For glass to frame, prefer an elastic paste adhesive + primer, or VHB 1.1 mm only if the glass is ±0.1 thick.
4. Keep **adhesive ≥ 2 mm away from the print window**; give the print ≥ 3 mm land beyond the bond for squeeze-out.
5. Formex / insulation stays as in v2 (open question 2 of the frame report).

---

## 6. Cost roll-up (100 ovens, 110 glass sets incl. 10 % spares)

All [E] unless noted; build-up in §1–5. TRY at 50.34 TRY/USD (14 Nov 2026).

| Item | Low TRY | Likely TRY | High TRY | Low USD | Likely USD | High USD | Basis |
|---|---:|---:|---:|---:|---:|---:|---|
| Glass, 110 pcs (3 mm, printed, C-edge, strengthened) | 33,000 | 66,000 | 132,000 | 656 | 1,311 | 2,622 | 300 / 600 / 1,200 TRY/pc |
| Print + CNC set-up, first articles (2 screens) | 5,000 | 12,000 | 25,000 | 99 | 238 | 497 | screens 1.5–4k each + programming |
| Frame tool (aluminium, single cavity) | 100,000 | 175,000 | 300,000 | 1,986 | 3,476 | 5,960 | [S58][S59] scaled |
| Frame parts 110 + resin bag + T1 sampling | 11,600 | 26,200 | 52,500 | 230 | 520 | 1,043 | 60 / 120 / 250 TRY/pc |
| Prototypes and tests (3 MJF fit samples; glow-wire on part) | 2,000 | 12,000 | 23,000 | 40 | 238 | 457 | [S60] + lab estimate |
| Fasteners (10 hidden CD M4 + washer + nyloc per oven) | 6,000 | 9,000 | 14,000 | 119 | 179 | 278 | 6 / 9 / 14 TRY per point |
| Adhesives / OCA / primer, 110 sets | 8,800 | 38,000 | 66,000 | 175 | 755 | 1,311 | LOCA+MS / OCA+VHB / industrial OCA + die-cut VHB |
| Sheet-metal delta (precise cut-out, deburr, CNC program) | 3,000 | 7,000 | 15,000 | 60 | 139 | 298 | 20–120 TRY/panel + 1–3k program |
| Jigs and equipment (bonding jig, flush jig, UV lamp, debubbler if OCA) | 15,000 | 40,000 | 90,000 | 298 | 795 | 1,788 | — |
| **Total** | **184,400** | **385,200** | **717,500** | **3,663** | **7,652** | **14,253** | |
| per oven | 1,844 | 3,852 | 7,175 | 37 | 77 | 143 | |
| of which one-off (tool, set-up, T1 sampling, jigs, tests, programs) | 123,000 | 246,000 | 456,000 | 2,443 | 4,887 | 9,058 | |
| recurring per oven (glass + frame part + resin + fasteners + adhesives + sheet delta) | ≈ 614 | ≈ 1,392 | ≈ 2,615 | 12 | 28 | 52 | |

Notes:
- **Excluding the frame tool** (the v2 frame needs a tool anyway; v2 assumed steel), the glass-front-specific spend is **84k / 210k / 418k TRY ($1.7k / $4.2k / $8.3k)**.
- **Rivet variant**: replace the fastener line by 4 black dome or tri-fold rivets → 500–3,500 TRY per 100 ovens + riveter. Saves ≈ $100–250, but loses thermal float (§3.2).
- **Route B (SATOZ lamination via Özdisan)**: glass + set-up + OCA + lamination jig (likely ≈ $2,700) become ≈ $1,300–4,000 for 100 + NRE, MOQ permitting [E].

**Lead-time picture** (from design freeze):

| Track | Weeks | Basis |
|---|---|---|
| MJF fit samples | 0.5–1 | [S61] |
| Glass RFQ → samples (BYC-type) | 3–5 | [E] |
| Glass series after sample approval | 2–4 | [E] |
| Aluminium tool to T1 | 4–6 (+1 for T2) | [S59] / [E] |
| Steel tool (if chosen) | 8–12+ | [Q] [S59] |
| FR PA6-GF30 halogen-free, 1 bag | 1–4 | [E] — to check stock |
| Sheet metal incl. CD studs + powder coat | 1–2 | [S41] / [E] |
| Rivets, studs, VHB, MS polymer, LOCA | days (stock) | [S47][S52][S65] |
| SATOZ custom lamination (route B) | 8–12 | [E] |
| **Critical path** | **≈ 7–8 weeks** to the first complete set (aluminium tool + T1 ≈ 6–7 wk; glass samples run in parallel) | |

---

## 7. Sources

All opened on 2026-11-15 unless marked "search index" (figure seen in the search engine's extract of the page; page not opened or 404 at fetch time).

- [S1] SCHOTT Çerkezköy location: https://www.schott.com/en-ae/about-us/company/regions-and-locations/cerkezkoey
- [S2] SCHOTT, "20 years of flat glass processing in Çerkezköy", 23 Mar 2022: https://www.schott.com/en-us/news-and-media/media-releases/2022/schott-celebrates-20-years-of-flat-glass-processing-in-cerkezkoy-turkey
- [S3] SCHOTT Bolu location: https://www.schott.com/en-ca/about-us/company/regions-and-locations/bolu
- [S4] SCHOTT processed flat glass technical details (search index; 404 at fetch): https://www.schott.com/en-gb/products/processed-flat-glass/technical-details , https://www.schott.com/home-appliance/turkish/products/cutting.html
- [S5] Yorglass press release, ForInvest 5 Oct 2026: https://www.foreks.com/haber/detay/6ac35ec524008d7d4373bdb6/FRKS/tr/yorglass-beyaz-esyada-pisirmeden-sogutmaya-camasirdan-yeni-nesil-yuzeylere-one-stop-partner-yaklasimini-guclendiriyor-05-10-26/
- [S6] Yorglass production-operator ad, Çerkezköy: https://www.eleman.net/is-ilani/uretim-operatoru-i4798285
- [S7] Yorglass website: https://www.yorglass.com
- [S8] Astro Temperli Cam: https://www.astrocam.com.tr and https://www.astrocam.com.tr/kurumsal/uretim-tesislerimiz
- [S9] Astro tempering limits: https://www.astrocam.com.tr/cam-temperleme/
- [S10] Astro white-goods glass: https://www.astrocam.com.tr/beyaz-esya-camlari/
- [S11] Saraycam, tempered glass sizes: https://saraycam.com/temperli-cam-ebatlari-ne-kadar-olmalidir/
- [S12] Camglass: https://www.camglass.com.tr , https://camglass.com.tr/products/screen-printed-glass/ , https://www.camglass.com.tr/serigrafik-baski-rulo-baski
- [S13] BYC Group home: https://www.bycunited.com
- [S14] BYC chemical tempering: http://www.bycunited.com/kimyasal-cam-temperleme.html
- [S15] BYC thermal tempering: https://www.bycunited.com/islem/isil-temperleme/
- [S16] BYC CNC rodaj (±0.1; sector ±1 mm): https://www.bycunited.com/islem/cnc-rodajlama/
- [S17] BYC serigrafi: https://www.bycunited.com/islem/serigrafi/
- [S18] BYC interactive display glass (FATİH / Vestel): https://www.bycunited.com/urun/etkilesimli-ekran/
- [S19] BYC contact: https://www.bycunited.com/iletisim
- [S20] Temiz Serigrafi glass control panels: https://www.temizserigrafi.com/tr/urun/cam-kontrol-panelleri
- [S21] Temiz Serigrafi home: https://www.temizserigrafi.com/tr
- [S22] Temiz Serigrafi contact (Manisa): https://www.temizserigrafi.com/tr/iletisim
- [S24] Desiprint, glass printing: https://www.desiprint.com.tr/blog/cam-uzerine-baski-teknikleri
- [S25] Yıldız Serigrafi: https://www.yildizserigrafi.com.tr
- [S26] Zirve Tezyinat: https://www.zirvecam.com.tr
- [S27] Ortakçı Cam directory entry: https://www.firmasec.com/firma/ryzdk-ortakci-cam ; own site https://www.ortakcicam.com.tr
- [S28] Çağdaş Cam, Ekonomi Gazetesi 2 Sep 2025: https://www.ekonomigazetesi.com/sirket-haberleri/cagdas-cam-yapay-zeka-destekli-yeni-yatirimla-kapasitesini-katliyor-58151
- [S29] Kolhis listing: https://www.b2match.com/e/co-matching2026/opportunities/UGFydGljaXBhdGlvbk9wcG9ydHVuaXR5OjI1NzAzMw==
- [S31] Bing local results, Çerkezköy: https://www.bing.com/search?q=%C3%87erkezk%C3%B6y+temperli+cam+serigrafi
- [S32] Thin tempering (GlastonAir 2 mm; Lisec; TecnoAir) — search index: https://www.glasscanadamag.com/glastonair-trouble-free-thin-tempering-4113/
- [S33] TuffX handbook, EN 12150-1 bow table — search index: https://media.trulypvc.com/pdfs/TuffX-Techincal-Handbook-Issue-16.pdf
- [S34] Fuxinag, black bezel printing (±0.1 mm): https://www.fuxinag.com/news/how-is-the-black-bezel-of-cover-glass-of-a-touchscreen-silkscreen-printed/
- [S35] Marabu Glass Ink GL TDS (film 5–12 µm, 140 °C/30 min, mesh): https://cdn.shopify.com/s/files/1/0068/0244/0276/files/Glass_Ink_GL_Technical_Data_Sheet.pdf
- [S36] Glasswerks TB 005, silkscreen tolerances — search index: https://spinx-dev.s3.amazonaws.com/glasswerks/uploads/2026/05/TB_005_Guidance_On_Silkscreen_Decorative_Glass.pdf
- [S37] Marketplace prices — search index: https://www.alibaba.com/product-introduction/Custom-3mm-Physical-Tempered-Glass-with_1601299436817.html
- [S38] Saida Glass strengthening / hole rule — search index: https://m.saidaglass.com/capabilities/glass-strengthening , https://www.saidaglass.com/news/why-drilling-hole-size-should-same-at-glass-thickness-as-least
- [S39] SATOZ: https://satoz.tech/en/ , https://satoz.tech/en/products/glass/ , https://satoz.tech/en/products/assembly/
- [S40] Özdisan, SAT070AT40D21Y0-35100T07: https://www.ozdisan.com/p/tft-paneller-381/satoz-sat070at40d21y0-35100t07-529958
- [S41] Airsan Metal: https://airsan.com.tr/cerkezkoy-lazer-kesim-sac-isleme
- [S42] KOZMETAL: https://www.kozmetal.com.tr
- [S43] Tekniksat Metal: https://www.tekniksatmetal.com
- [S44] Famak deburring machines: https://famakmakina.com.tr/uygulamalar/capak-alma
- [S45] Durma V-die chart; The Fabricator / Bystronic / WILA flange rules — search index: https://www.durmapress.com/press-brake-v-die-opening-chart-die-size-calculation-guide/
- [S47] Promsis CD studs: https://promsis.com.tr/urun/kondansator_desarjli_saplamalar
- [S48] Soyer BMH 22i manual (min sheet 1/10 d, ≥ 0.5 mm) and Taylor troubleshooting guide (drawn arc 3:1, coating ≤ 25 µm) — search index / opened: https://www.manualslib.com/manual/2078955/Soyer-Bmh-22i.html?page=39 , https://taylor-studwelding.com/stud-welding-troubleshooting-guide
- [S49] PEM FH-M4-8ZI: https://www.pemnet.com/products/product-finder/FH-M4-8ZI/
- [S50] PEM CHA-M4-8 (min sheet 1.60) — search index: https://catalog.pemnet.com/item/concealed-head-studs-types-cfha-cfhc-cha-chc/oncealed-head-studs-types-cha-cfha-chc-cfhc-metric/cha-m4-8
- [S51] Star Bağlantı: https://www.starbaglanti.com
- [S52] Micro Perçin: https://www.percin.com.tr/renkli-percin
- [S53] Hedef Bağlantı: https://www.hedefbaglanti.com.tr
- [S54] Onurfix: https://onurfix.com.tr/cd-kaynak-saplama
- [S55] DIN EN ISO 15977 table: https://fasten.it/en/norms/norm/din_en_iso_15977
- [S56] GESIPA TRI-FOLD 4.8 × 16: https://www.gesipa.com/products/tri-fold-blind-rivets/1433821-tri-fold-blind-rivets-alualu-dome-head-48-x-19/
- [S57] Akakçe rivets / rivet nuts: https://www.akakce.com/arama/?q=pop+per%C3%A7in+4x10+siyah , https://www.akakce.com/arama/?q=somun+per%C3%A7in+m4
- [S58] İmalat Rehberi, mould cost 2026: https://imalatrehberi.com/rehber/enjeksiyon-kalip-maliyeti
- [S59] MARG Mühendislik, mould prices, 1 Sep 2026: http://marg.com.tr/blog/plastik-enjeksiyon-kalip-fiyatlari/
- [S60] MARM Engineering, 3D printing prices 2026: https://marmengineering.com/3d-baski-fiyat/
- [S61] MJF bureaus: https://t3dizayn.com/tr/mjf-baski , https://www.basaran.tech/mjf , https://printly.studio/materials , https://xometry.com.tr
- [S62] HP HR PA 12 FR datasheet (Protolabs copy): https://www.protolabs.com/media/ohwkj0ab/hp-data-sheet-pa12fr.pdf
- [S63] EOS flame-retardant materials — search index: https://www.eos.info/en-us/polymer-solutions/polymer-materials/flame-retardant
- [S64] Aydın Plastik raw materials (Pimamid line — search index): https://aydinplastik.com/urunler/hammadde
- [S65] Akakçe price searches: https://www.akakce.com/arama/?q=akfix+n%C3%B6tr+silikon , https://www.akakce.com/arama/?q=akfix+ms+polimer+290 , https://www.akakce.com/arama/?q=3m+vhb+4910 , https://www.akakce.com/arama/?q=loca+uv+yap%C4%B1%C5%9Ft%C4%B1r%C4%B1c%C4%B1 , https://www.akakce.com/arama/?q=oca+film
- [S66] Ulus Bant: https://ulusbant.com.tr/ozel-kesimli-bantlar ; Nordem: https://www.nordem.com.tr/die-cut-bant
- [S67] tesa OCA (TR): https://www.tesa.com/tr-tr/endustri/urunler/optik-olarak-seffaf-bantlar
- [S68] 3M Türkiye VHB pages (search result): https://www.3m.com.tr
- [S69] Formex GK-17: https://www.vantape.com/tr , https://www.itwformex.com
- [S70] Exchange rates (LSEG via Bing): https://www.bing.com/search?q=dolar+kuru+bug%C3%BCn+USD+TRY
- [S71] PEM locations, Turkey sales office — search index (401 at fetch): https://stageaws.pemnet.com/en-sg/company/locations/
- [S72] bigHead bonded fasteners (Bossard) — search index: https://americas.bossard.com/bonding-fasteners/composite-fasteners/

## 8. Not verified (to check by RFQ)

- Every price for glass, tools, CD welding, jigs and glow-wire testing is an estimate. No supplier was contacted.
- MOQ and small-lot willingness of SCHOTT Çerkezköy, Yorglass Çerkezköy, Temiz Serigrafi, BYC.
- What Yorglass's Çerkezköy plant actually makes: it is absent from its own website.
- BYC: 3.0 mm thermal (page says 3.2 mm min), their print registration, OD and flatness figures.
- SATOZ: MOQ and NRE for custom cover glass + full lamination. I also could not confirm that satoz.tech is the same SATOZ as on Özdisan.
- GWFI / GWIT of any printed FR polymer; a Turkish bureau offering PA12 FR / PA 2241 FR.
- Halogen-free FR PA6-GF30 stock in Turkey (grade, bag lead time).
- CD-stud face-side marking on 1.0 mm painted DKP and brushed stainless: no quantitative source; needs a coupon.
- A turret-punch shop with a countersink-forming tool in Çerkezköy itself (verified only in Esenyurt).
- A Turkish Formex converter; Sika / Dow industrial prices.
- SCHOTT technical-detail figures and the EN 12150-1 bow values come from the search engine's index and a secondary handbook, not from the pages or the standard themselves.
