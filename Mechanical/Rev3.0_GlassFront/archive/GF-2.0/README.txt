Rev3.0 glass front - GF-2.0 release set (archived 2026-11-16, before the GF-2.1 rebuild; copies only)

GF-2.0 = equal 18.5 border on all four sides (glass 190.48 x 122.32), FPC tails bent back at the panel edge
behind a bridge (g_bend 3.00: bridge pocket face y 122.00, nose R1.5, land break 0.3 x 45 deg, bottom land
5.99), divider rib x 79.92, floors over the flange plate, S4 / R4 only (S8 and F5-F8 removed).
Fusion document 'Rev3.0 GlassFront' (urn:adsk.wipprod:dm.lineage:XyXacwE-SnqsV-hz5pHg3w), version 18 = GF-2.0
(v15-v17 intermediate). Not committed to git (last commit 76f5b79 = GF-1.1).
Frame STEP sha256 7831768c26066dc08cd968fe16808ef4c9ae2b45bcdbc0f7efd7cb4c79ea82ad.
Master params: GF-2.0 incl. the verification's post_verification_corrections / _addendum (sha256 7439b098...).

Independent verification 2026-11-16: 115 PASS / 1 FAIL / 56 (as reported by the lead). Two open findings:
  1. CTP tail -> bridge nose 0.946 nominal / 0.654 at the RSS panel position / 0.239 at the full worst case
     (panel position 0.31 RSS / 0.60 WC after adding print-to-edge +-0.2); the 0.45 intent is not met at WC.
  2. bead inner edge only 0.80 from the edge of the 0.3 x 45 land break over the bridge (rule bead_pocket_min
     >= 1.0) - the FAIL.
Superseded by GF-2.1 (border 19.0, larger g_bend, wider bottom land) which closes both findings.

Files (sha256, bytes):
  0b1336f8d424f9efd22fdb79c918c7a02c567f062b55dfc44fa5d6544582d7f2  Rev3.0_GlassFront.f3d  8189954
  7831768c26066dc08cd968fe16808ef4c9ae2b45bcdbc0f7efd7cb4c79ea82ad  Rev3.0_GlassFront_Frame.step  1586957
  cc36686a73bd7336c1075bee5e44fa129f8953dafd69b3b82d66b71bf77ce6b3  Rev3.0_GlassFront_Frame.stl  5456484
  dc6d0a7048025d9223bde80706480714f6f9b2117def04ec22c493b2335bcf53  Rev3.0_GlassFront_Glass.step  79682
  62dc26bc0baffbe91c0fe55ae5bc7bdbdc9ef6d871c195371def8f1777005192  Rev3.0_GlassFront_Assembly.step  10617596
  efaa96a476755a192ed355d053c856397ac97e3c6a5e10c82072b4c71badf3b1  Rev3.0_GlassFront_Frame_report.json  45034
  3ff964549bc72324f766b66be7887a54a38cfd2da303adf1347c511598ce39cd  Rev3.0_GlassFront_Assembly_report.json  149141
  025cc5380fb06ccd8c497abdea2aa5d0e09ac513f5648f995b8f0d7edefbbce0  Rev3.0_GlassFront_Frame_report_errata.json  8027
  7439b098325a09f4e31bd242b7db6372c30ae9c2bf0aa7c53e3b7003608b6082  Rev3.0_GlassFront_params.json  167034
  47619d18975df252915e28b6d4d116655f65da9153fb46b895e786ed977b556e  Rev3.0_GlassFront_Design_GF-2.0.md  186708
  9a601fea861c37a6b15ad0a9ba785975f0ea9956c649d36e37f7d944ad287e8a  drawings/GF_Appearance.pdf  2100736
  270079a8282b0bfa18a6c2efc03d8246fc1f4d75187bd9714b48d356acfe02a2  drawings/GF_Appearance.png  2860757
  63c5d106cad57dd42f3fef99e00446550a23dcea3d9a3dafc0de60f3b9a6057f  drawings/GF_BondingAids.dxf  70243
  2e174ede9f6f65732cd4afb0b47c86eafe6990272b2bd9e5aa717ed9302355bf  drawings/GF_BondingAids.pdf  88791
  77bfdaeadc684af35cf8b0558d92c69aa361184e6480f2cb099551f40e157eb2  drawings/GF_BondingAids.png  842388
  4b13c50f0c08e4f23539a987569c51bd753aa5dcb5ad50651638c7fcb52fa1a8  drawings/GF_Frame_Inspection.dxf  1182733
  bf04c22772f01d2a607c5408b4e72061735a0b16a54d797b8481a302e4262f1d  drawings/GF_Frame_Inspection.pdf  220892
  bf1a342c43b4597297b07b1636a819e8cc856c815d432b1dba62a2333cae4ad0  drawings/GF_Frame_Inspection_p1.png  559214
  bc6cc2bdc1e625bb81d8e0dfcb68323b93946a9d53ea6877d610cef240bcadd2  drawings/GF_Frame_Inspection_p2.png  983253
  e37bdd902fddbf48a4354da8de07e859475e13e47a818d914a8ae45e70d3f4ff  drawings/GF_Glass.dxf  49848
  6334b794afddcd898084f8c20c0e6fad64b5a43383d57c8829da656f0389b8ca  drawings/GF_Glass.pdf  79936
  7495c751120c92e0d5a892e42dac511d0946974e98c12ed75bb0c31d04acacc7  drawings/GF_Glass.png  962441
  d2d49324901efbd3216c9382d35076e0c93f3d7bda157766392e151c07fed667  drawings/GF_Glass_Print_1to1.pdf  31489
  d1523aa3f0cebc659ce2f0ac06b08d66d64c1e60c84d52f8e2be1fcb072f408f  drawings/GF_Jig_J1.dxf  50208
  d0d9e32810a675988ea163ca182f32a67a1ee25398d7c133c99e7f0f9f766945  drawings/GF_Jig_J1.pdf  74729
  71492b3c558743b5129b60a68fb994cbdc5ff916f0fd5a18d564ebc6e869c9f2  drawings/GF_Jig_J1.png  610897
  43b1a06518508ca533ae54a8b40c23cce69e80d0c598eef0afe6fc44d3d0e285  drawings/GF_Jig_J2.dxf  50354
  9a71ed70e8b6c095a2552a639375f1f37f6b2806ba93699d9cc9a3eb3befa2c4  drawings/GF_Jig_J2.pdf  94539
  b4bf9a08ecd0cf1d26335b1dab6f4b5a91eabfde69dd4804806340a07d61ee8b  drawings/GF_Jig_J2_p1.png  673683
  cbed5375e190e61efaec06be9724828f30ef312f3248e6145e8dc63c4a4d0930  drawings/GF_Jig_J2_p2.png  614386
  ef10f0092447f094578bf99421f8c8ec4a9bfe0c3addab976dcf998b449285f7  drawings/GF_Sheet_R4.dxf  62528
  237ce9bc5852c4b73b069c2243438e06a8a21666a6544b56cbf95ff8393d17e3  drawings/GF_Sheet_R4.pdf  86623
  7061c26120ff3cadf98deacbadfa1f6ca5db2267e9e929c4f6edb0c0b572741f  drawings/GF_Sheet_R4.png  808775
  c736f7fefd2bc46b4d1c036028119c18b2cfe99dd663fe11f18906ec148b534d  drawings/GF_Sheet_S4.dxf  63977
  de41d5a1674546ec8b196122f28a6d8a3d158754ea6512aecd6fdbc044144cd9  drawings/GF_Sheet_S4.pdf  82655
  a3ebab4a67ba334cd691394c176d0edd441c758aa43acc216e68d137f1fdbc10  drawings/GF_Sheet_S4.png  864138
  09f390c4a726bb6b41fd51847601f116a8ee9c1bd41efd8703e3da4c345dbcec  drawings/GF_TailFoldGauge.dxf  46739
  dcdd28adcf3d93bd8a260e08c2cc196a0365101f3e14993ed36d614af8079d7a  drawings/GF_TailFoldGauge.pdf  61156
  df26cd0de602e15a87f6b70cf7c26ee4042c29beb144d99e0ddb8634bef2d5b5  drawings/GF_TailFoldGauge.png  670411
  d19ea7a26c1aee800e04065dc2a4d46a9747b053b298223b4b49b1c5d3158936  drawings/drawings_report.json  261698
  2c1a6ee0d114877a5558b221372c58d5063b24e932c7a243da25d06f3e9fa915  drawings/previews/GF_BondingAids_dxf.png  91491
  38607f8dffb015d641158ad467005be30cc64dc167a3761e8d56bb82513c8216  drawings/previews/GF_Frame_Inspection_dxf.png  102328
  8e5c9ef67a99cfce8d14ef2564e9d90c54e3cae28a53392d2d8ddcbc211dce14  drawings/previews/GF_Glass_Print_1to1_preview.png  78256
  ebf455f48cf479e3b3d1a52cabef12d383b1f7f14bca9666aefc33eff2e82388  drawings/previews/GF_Glass_dxf.png  85081
  7d500a6eb01d50fe947a4d484f7f0ed5b7d1773d2fcacb4529ced442ba848e2d  drawings/previews/GF_Jig_J1_dxf.png  42024
  d44f01689fbbe179430e4fd83fa92cfc706dda9f82274962a67e230700b8586a  drawings/previews/GF_Jig_J2_dxf.png  43437
  433c51ef73e00a99456e3d5e2947e086454bb791b6aeca81a760506a50056e5e  drawings/previews/GF_Sheet_R4_dxf.png  84190
  19356a884a1e63ecefb1bc26d3ce95c174b6c6ab8d3eb738f104309a941b1f76  drawings/previews/GF_Sheet_S4_dxf.png  86188
  64d77c7a405815351eed8ecb6e504e503999b5499b6975454aeed4595f332701  drawings/previews/GF_TailFoldGauge_dxf.png  47618

GF-2.0 Fusion renders copied to Mechanical/Rev3.0_GlassFront/renders/GF-2.0/ (sha256, bytes):
  da492ae1adb6eb4242a88572930e4ff0a05ba3c813b280573d7273751ecd496b  renders/GF-2.0/Fusion_Assembly_back_no_PCB.png  144864
  af97629bd49dac3778c21985065a2be9a02e449a26ff0b23763b517e298314cc  renders/GF-2.0/Fusion_Assembly_exploded.png  181890
  bd3b2c4b51ef790e5beb26a5c47a126154550588f0570d65264425f06d11f5ff  renders/GF-2.0/Fusion_Assembly_exploded_back.png  256195
  f12c9e63f072147e498d683d141221a7960da90f4e50fc9ac20065ccf2a62aa3  renders/GF-2.0/Fusion_Assembly_front.png  58471
  f4b01c092cf4da5d2e37e98ecd43ee8b060aad11e4cd2aa245b7e9bae2599782  renders/GF-2.0/Fusion_Assembly_front_R4.png  72534
  050413b4be875ce080f0fd7448d686f56c16ccf3e66dc75766978832d0835a6a  renders/GF-2.0/Fusion_Assembly_front_R4_closeup_F1.png  89222
  c0fe2563f6a0ba13c9e6254c11f98e3519d53e512e715b0fc5c3b0d7ac435022  renders/GF-2.0/Fusion_Assembly_iso_back.png  260623
  ce3136586785a6e5aa32f23da2738fa65b934c7629738bab69281de7ddc8bd51  renders/GF-2.0/Fusion_Assembly_iso_back_no_PCB.png  160996
  921bc13b6f09096703d56df1efe8c5c1c41cd73b5961756256dbcc855beffe75  renders/GF-2.0/Fusion_Assembly_iso_front.png  49124
  cb1c77b56287b436cc3610465e6fc7a33847bcdc575fc248de1c58faa8dd8b37  renders/GF-2.0/Fusion_Assembly_section_bridge_x103.85.png  72958
  f52af151b8b790018d332e0a451a329d4b3ba417b2de7ce6299f4ad7440611a8  renders/GF-2.0/Fusion_Assembly_section_corner_F1_slot_axis.png  73044
  75c27e65f68d4f20cf2b84337a23e15f7eb4cf6ff6d6897371804392e3192e85  renders/GF-2.0/Fusion_Assembly_section_side_edge_y66.83.png  115114
  a0b795b6bad52abd2dee570e4b89bbfd81f4fce134373af7a977e1fb93cdd535  renders/GF-2.0/Fusion_FrameGF_back.png  109961
  51077b3052c6680a8532acbf5497cb65288b271e94edf982b85ebf764db18798  renders/GF-2.0/Fusion_FrameGF_closeup_bridge_tail_pocket_front.png  72143
  653e3811489f9495b81ff93264950f4b57114ecbfbdbecedd93a687451a45e3a  renders/GF-2.0/Fusion_FrameGF_closeup_corner_F1_back_tube_rib.png  162073
  e142675eaf58fce604acbb5f351d1c4ecbd1a95daa5dc67729a0cc978bbc6228  renders/GF-2.0/Fusion_FrameGF_closeup_corner_F1_lip_seat_ring_pad_slot.png  111131
  df497603336ef03d5d53183abfcecb47bdd5423b555a1c27b1ffcfaad8d48a61  renders/GF-2.0/Fusion_FrameGF_closeup_land_pip_P1.png  66795
  2a22c9a098ef51db14f248f179f801d6001d5574c357c88712019af7610571d0  renders/GF-2.0/Fusion_FrameGF_closeup_tail_pocket_back.png  115758
  4e49a17a36f094b2845cdf737b0292a0475348a89e900f878d59dcb1e7366fcd  renders/GF-2.0/Fusion_FrameGF_front.png  48413
  7348ed63401adfd29c3820f47c7220a529510866d378462b797a5abfb550c31a  renders/GF-2.0/Fusion_FrameGF_iso_back.png  151570
  a99c3128b8235a1495eaa2ee39dbddf0ad2ee2b8c4b9a0721512afc1e452dd58  renders/GF-2.0/Fusion_FrameGF_iso_front.png  78595
  0c90664cd4f2ebc37d35ce0c74eabf7b96c75b5689eef37bc6c75e3a65f57088  renders/GF-2.0/Fusion_FrameGF_section_left_edge_y66.83.png  34761
  9fd5b9dfbb7fda6cc60a9afa9f242bc99acf0e626038886c314535c3139320e3  renders/GF-2.0/Fusion_FrameGF_section_right_edge_y60.png  34301
  f4b01c092cf4da5d2e37e98ecd43ee8b060aad11e4cd2aa245b7e9bae2599782  renders/GF-2.0/Fusion_GF20_assembly_front_R4.png  72534
  f12c9e63f072147e498d683d141221a7960da90f4e50fc9ac20065ccf2a62aa3  renders/GF-2.0/Fusion_GF20_assembly_front_S4.png  58471
  1fb382d1a3fa595cc4d3adec22a9c5274a7f81b5d9b952e81c96c2d8a727655b  renders/GF-2.0/Fusion_GF20_back.png  211174
  3d9f062690d9ad4d4cdfcc5fd9cf517623e05d22992e10c9071399cce304f6a6  renders/GF-2.0/Fusion_GF20_bottom_edge_bridge_nose_closeup.png  305024
  5c5d5ffc6453d45049e7ec3daecf6387119c929b3efb28fabed6393febaf407c  renders/GF-2.0/Fusion_GF20_bottom_edge_bridge_tails_back.png  375955
  0f86430532033f43a1e1a81023f839bcada20aeaf8466f5b9d1df9c8a51fd428  renders/GF-2.0/Fusion_GF20_bottom_edge_bridge_tails_front.png  190866
  8c60144194d52072a5d8aa332e4340cdfb5d949b61717a87672a2c9ddcb9579f  renders/GF-2.0/Fusion_GF20_front.png  72166
  11e23b459d8f9f4d307d6fb33599c27f1c28c0885a305dcc4cc4809cf92b9fb5  renders/GF-2.0/Fusion_GF20_section_x103.85_TFT_tail.png  72956
  0e75b0fe771e2e4a5ecb7aaa56c874b0a53bb33fe9b7766ed099cf60a05c7e8e  renders/GF-2.0/Fusion_GF20_section_x150.0_TFT_wide_part.png  74882
  e9b87d765642410b802c43cdfdf1f39ec8ec631fbc2ea0897beba1e3456867ab  renders/GF-2.0/Fusion_GF20_section_x60.0_CTP_tail.png  74846
  296a287657713527bda1d8e5ace99b42c7b52f539e8574a313a74a596b01a272  renders/GF-2.0/Fusion_GF20_section_x79.92_divider_rib.png  62567

archive/GF-1.1/ is unchanged.
