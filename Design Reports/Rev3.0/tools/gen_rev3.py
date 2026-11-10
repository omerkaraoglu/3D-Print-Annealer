"""Generate Rev3.0 KiCad schematic sheets and patch the root sheet.

Usage: python -I gen_rev3.py
Writes:
  <proj>/Rev3_Display.kicad_sch, Rev3_Thermocouple.kicad_sch, Rev3_Power.kicad_sch
  <proj>/3dFilamentDryer.kicad_sch (patched)
  <libdir>/Rev3.kicad_sym  (custom symbols)
"""
import os, sys, uuid, copy, math, re, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexp import parse, find, first, prop, Sym, dump
from kicad_lib import get_symbol, pins as lib_pins

PROJ = r"C:/Users/lenovo/Documents/Projects/3D Printer Filament Dryer/KiCad/3dFilamentDryer"
LIBDIR = r"C:/Users/lenovo/Documents/Projects/3D Printer Filament Dryer/KiCad/ComponentsLibrary/User Created/Rev3"
ROOT_SCH = PROJ + "/3dFilamentDryer.kicad_sch"
ROOT_UUID = "ea3996f2-7d6b-4a86-86ab-4ed62213f41f"
PROJECT = "3dFilamentDryer"
VERSION = 20260306
DATE = "2026-11-09"

OZ = "https://www.ozdisan.com/p/"
URLS = {
    'ADS1115IDGSR': OZ + "analogtan-dijitale-donusturucu-entegreler-adc-225/texas-ads1115idgsr-616336",
    'SSD1963QL9': OZ + "arayuz-kontrolor-entegreleri-227/solomon-ssd1963ql9-353972",
    'MIC2288YD5-TR': OZ + "dc-dc-voltaj-regulatorleri-275/micrel-microchip-mic2288yd5-tr-613161",
    'HLK-10M05': OZ + "ac-dc-donusturuculer-606/hi-link-hlk-10m05-702430",
    'SAT70AT40D21-33KN-CTP-V1': OZ + "tft-paneller-381/satoz-sat70at40d21-33kn-ctp-v1-621995",
    'ESP32-WROOM-32E-N16': "https://www.ozdisan.com/c?search=ESP32-WROOM-32E-N16",
    'TPS562201DDCR': "https://www.ozdisan.com/c?search=TPS562201DDCR",
    'LD1117S12CTR': "https://www.ozdisan.com/c?search=LD1117S12CTR",
    'DS1020-09-40VBT1A': "https://www.ozdisan.com/c?search=DS1020-09-40VBT1A",
    'DS1020-09-06VBT1A': "https://www.ozdisan.com/c?search=DS1020-09-06VBT1A",
    'DG127H-5.08-02P-14-00AH': "https://www.ozdisan.com/c?search=DG127H-5.08-02P-14-00AH",
    'NCP18XH103F03RB': "https://www.ozdisan.com/c?search=NCP18XH103F03RB",
    'CX3225GB10000P0HPQCC': "https://www.ozdisan.com/c?search=CX3225GB10000P0HPQCC",
    'SRI0605B-4R7M': "https://www.ozdisan.com/c?search=SRI0605B-4R7M",
    'PCD0403MT100': "https://www.ozdisan.com/c?search=PCD0403MT100",
    'SS14': "https://www.ozdisan.com/c?search=SS14",
    'PESD5V0S1BA': "https://www.ozdisan.com/c?search=PESD5V0S1BA",
}

def U():
    return str(uuid.uuid4())

def S(x):
    return Sym(x)

def num(v):
    v = round(float(v), 4)
    if v == int(v):
        return S(str(int(v)))
    return S(repr(v))

def font(size=1.27):
    return [S('font'), [S('size'), num(size), num(size)]]

def effects(size=1.27, justify=None, hide=False):
    e = [S('effects'), font(size)]
    if justify:
        e.append([S('justify')] + [S(j) for j in justify.split()])
    if hide:
        e.append([S('hide'), S('yes')])
    return e

def property_(name, value, x, y, rot=0, hide=False, size=1.27, justify=None):
    p = [S('property'), name, value, [S('at'), num(x), num(y), num(rot)]]
    if hide:
        p.append([S('hide'), S('yes')])
    p.append([S('show_name'), S('no')])
    p.append([S('do_not_autoplace'), S('no')])
    p.append(effects(size, justify))
    return p

# ----------------------------------------------------------------------------------
# Custom library symbols
# ----------------------------------------------------------------------------------
def lib_pin(ptype, x, y, angle, length, name, number, hide=False):
    p = [S('pin'), S(ptype), S('line'), [S('at'), num(x), num(y), num(angle)], [S('length'), num(length)]]
    if hide:
        p.append([S('hide'), S('yes')])
    p.append([S('name'), name, effects()])
    p.append([S('number'), number, effects()])
    return p

def make_symbol(name, ref_prefix, left, right, top, bottom, width, height=None, footprint='', description='',
                datasheet='', pin_len=2.54, value=None, keywords='', extra_props=None, tb_pitch=2.54):
    """Create a KiCad symbol definition.
    left/right/top/bottom: list of entries; entry = (numbers, name, type) where numbers is str or list of str
    (lists are stacked: first visible, rest hidden at the same place)."""
    pitch = 2.54
    n_side = max(len(left), len(right))
    n_tb = max(len(top), len(bottom))
    H = height or (n_side + 1) * pitch
    W = max(width, (n_tb + 1) * tb_pitch)
    # body rectangle centred at origin
    x1, x2 = -W / 2, W / 2
    y1, y2 = -H / 2, H / 2
    pins = []
    def add(entries, side):
        n = len(entries)
        for i, (numbers, pname, ptype) in enumerate(entries):
            if isinstance(numbers, str):
                numbers = [numbers]
            if side in ('left', 'right'):
                y = y2 - pitch * (i + 1)
                if side == 'left':
                    x, ang = x1 - pin_len, 0
                else:
                    x, ang = x2 + pin_len, 180
            else:
                x = x1 + tb_pitch * (i + 1) + (W - (n + 1) * tb_pitch) / 2
                x = round(round(x / 1.27) * 1.27, 2)
                if side == 'top':
                    y, ang = y2 + pin_len, 270
                else:
                    y, ang = y1 - pin_len, 90
            for k, nmb in enumerate(numbers):
                # stacked duplicates are hidden *passive* pins (a hidden power_in pin would create an implicit global net)
                pins.append(lib_pin(ptype if k == 0 else 'passive', x, y, ang, pin_len, pname, nmb, hide=(k > 0)))
    add(left, 'left'); add(right, 'right'); add(top, 'top'); add(bottom, 'bottom')
    sym = [S('symbol'), name,
           [S('exclude_from_sim'), S('no')], [S('in_bom'), S('yes')], [S('on_board'), S('yes')],
           [S('in_pos_files'), S('yes')], [S('duplicate_pin_numbers_are_jumpers'), S('no')],
           [S('pin_names'), [S('offset'), num(1.016)]],
           property_('Reference', ref_prefix, x1, y2 + 1.27, 0, justify='left bottom'),
           property_('Value', value or name, x1, y1 - 1.27, 0, justify='left top'),
           property_('Footprint', footprint, 0, 0, 0, hide=True),
           property_('Datasheet', datasheet, 0, 0, 0, hide=True),
           property_('Description', description, 0, 0, 0, hide=True),
           property_('ki_keywords', keywords, 0, 0, 0, hide=True),
           ]
    for k, v in (extra_props or {}).items():
        sym.append(property_(k, v, 0, 0, 0, hide=True))
    gfx = [S('symbol'), f"{name}_0_1",
           [S('rectangle'), [S('start'), num(x1), num(y2)], [S('end'), num(x2), num(y1)],
            [S('stroke'), [S('width'), num(0.254)], [S('type'), S('default')]],
            [S('fill'), [S('type'), S('background')]]]]
    unit = [S('symbol'), f"{name}_1_1"] + pins
    sym.append(gfx); sym.append(unit)
    sym.append([S('embedded_fonts'), S('no')])
    return sym

def ssd1963_symbol():
    left = [(str(7 + i), f"D{i}", 'bidirectional') for i in range(5)]           # D0..D4 = 7..11
    left += [('113', 'D8', 'bidirectional')]
    # Build full D map from datasheet LQFP table
    dmap = {0: 7, 1: 8, 2: 9, 3: 10, 4: 11, 5: 116, 6: 115, 7: 114, 8: 113, 9: 112, 10: 111, 11: 107, 12: 106,
            13: 105, 14: 104, 15: 103, 16: 99, 17: 98, 18: 88, 19: 87, 20: 92, 21: 91, 22: 90, 23: 89}
    left = [(str(dmap[i]), f"D{i}", 'bidirectional') for i in range(24)]
    left += [('123', 'CS#', 'input'), ('122', 'D/C#', 'input'), ('120', 'WR#', 'input'), ('121', 'RD#', 'input'),
             ('127', 'RESET#', 'input'), ('128', 'CONF', 'input'), ('50', 'TE', 'output'), ('15', 'CLK', 'input'),
             ('22', 'XTAL_IN', 'input'), ('24', 'XTAL_OUT', 'output')]
    lmap = {23: 28, 22: 29, 21: 30, 20: 31, 17: 35, 16: 59, 15: 60, 14: 61, 13: 62, 12: 63, 11: 67, 10: 68, 9: 69,
            8: 70, 7: 71, 6: 72, 5: 76, 4: 77, 3: 78, 2: 79, 1: 80, 0: 81, 19: 85, 18: 86}
    right = [(str(lmap[i]), f"LDATA{i}", 'output') for i in range(23, -1, -1)]
    right += [('45', 'LSHIFT', 'output'), ('44', 'LLINE', 'output'), ('43', 'LFRAME', 'output'), ('49', 'LDEN', 'output'),
              ('51', 'PWM', 'output'), ('36', 'GPIO0', 'bidirectional'), ('37', 'GPIO1', 'bidirectional'),
              ('38', 'GPIO2', 'bidirectional'), ('39', 'GPIO3', 'bidirectional'), ('52', 'GAMAS0', 'output'),
              ('53', 'GAMAS1', 'output')]
    vddd = [str(n) for n in (1, 6, 14, 21, 25, 32, 40, 46, 56, 64, 73, 82, 93, 102, 110, 119, 126)]
    vddio = [str(n) for n in (4, 12, 16, 95, 97, 100, 108, 117, 124)]
    vddlcd = [str(n) for n in (27, 34, 42, 48, 54, 58, 66, 75, 84)]
    vss = [str(n) for n in (2, 3, 5, 13, 17, 20, 23, 26, 33, 41, 47, 55, 57, 65, 74, 83, 94, 96, 101, 109, 118, 125)]
    top = [(vddd, 'VDDD', 'power_in'), (['18'], 'VDDPLL', 'power_in'), (vddio, 'VDDIO', 'power_in'), (vddlcd, 'VDDLCD', 'power_in')]
    bottom = [(vss, 'VSS', 'power_in'), (['19'], 'VSSPLL', 'power_in')]
    assert sum(len(n) if isinstance(n, list) else 1 for n, _, _ in left + right + top + bottom) == 128
    return make_symbol('SSD1963QL9', 'U', left, right, top, bottom, width=35.56, tb_pitch=7.62,
                       footprint='Package_QFP:LQFP-128_14x14mm_P0.4mm',
                       description='Solomon Systech SSD1963 display controller, 1215 KB frame buffer, 8080/6800 MCU interface, 24-bit RGB TFT output, LQFP-128',
                       datasheet=URLS['SSD1963QL9'], keywords='TFT controller LCD SSD1963',
                       extra_props={'MPN': 'SSD1963QL9', 'Manufacturer': 'Solomon Systech'})

def mic2288_symbol():
    left = [('5', 'VIN', 'power_in'), ('4', 'EN', 'input')]
    right = [('1', 'SW', 'output'), ('3', 'FB', 'input')]
    bottom = [('2', 'GND', 'power_in')]
    return make_symbol('MIC2288YD5', 'U', left, right, [], bottom, width=12.7, height=10.16,
                       footprint='Package_TO_SOT_SMD:TSOT-23-5',
                       description='Microchip MIC2288 1.2 MHz 1.2 A boost regulator, 34 V max, TSOT-23-5',
                       datasheet=URLS['MIC2288YD5-TR'], keywords='boost LED driver',
                       extra_props={'MPN': 'MIC2288YD5-TR', 'Manufacturer': 'Microchip'})

def tft_symbol():
    names = {1: 'VLED-', 2: 'VLED+', 3: 'GND', 4: 'VDD', 29: 'GND', 30: 'PCLK', 31: 'NC', 32: 'HSYNC', 33: 'VSYNC',
             34: 'DE', 35: 'NC', 36: 'GND', 37: 'XR', 38: 'YD', 39: 'XL', 40: 'YU'}
    for i in range(8):
        names[5 + i] = f'R{i}'; names[13 + i] = f'G{i}'; names[21 + i] = f'B{i}'
    types = {1: 'passive', 2: 'passive', 3: 'power_in', 4: 'passive', 29: 'power_in', 36: 'power_in',
             31: 'no_connect', 35: 'no_connect', 37: 'passive', 38: 'passive', 39: 'passive', 40: 'passive'}
    left = [(str(n), names[n], types.get(n, 'input')) for n in range(1, 41)]
    return make_symbol('TFT_SAT070AT40D21_FPC40', 'J', left, [], [], [], width=22.86,
                       footprint='Connector_FFC-FPC:TE_4-1734839-0_1x40-1MP_P0.5mm_Horizontal',
                       description='SATOZ SAT070AT40D21 7" 800x480 TFT, 24-bit RGB, 40-pin 0.5 mm FPC (connector: Connfly DS1020-09-40VBT1A bottom contact, verify contact side)',
                       datasheet=URLS['SAT70AT40D21-33KN-CTP-V1'], keywords='TFT display FPC',
                       extra_props={'MPN': 'DS1020-09-40VBT1A', 'Manufacturer': 'Connfly', 'Panel': 'SAT70AT40D21-33KN-CTP-V1'})

def ctp_symbol():
    left = [('1', 'VDD', 'passive'), ('2', 'GND', 'power_in'), ('3', 'INT', 'bidirectional'),
            ('4', 'SDA', 'bidirectional'), ('5', 'SCL', 'input'), ('6', 'RST', 'input')]
    return make_symbol('CTP_GT911_FPC6', 'J', left, [], [], [], width=17.78,
                       footprint='Connector_FFC-FPC:TE_0-1734839-6_1x06-1MP_P0.5mm_Horizontal',
                       description='Fannal FN070A133 capacitive touch panel (GT911, I2C 0x5D/0x14), 6-pin 0.5 mm FPC (connector: Connfly DS1020-09-06VBT1A bottom contact, verify contact side)',
                       datasheet=URLS['SAT70AT40D21-33KN-CTP-V1'], keywords='touch GT911 FPC',
                       extra_props={'MPN': 'DS1020-09-06VBT1A', 'Manufacturer': 'Connfly'})

CUSTOM = {}
for s in (ssd1963_symbol(), mic2288_symbol(), tft_symbol(), ctp_symbol()):
    CUSTOM[s[1]] = s

def custom_symbol(name):
    s = copy.deepcopy(CUSTOM[name])
    s[1] = 'Rev3:' + name
    return s

# ----------------------------------------------------------------------------------
# Sheet builder
# ----------------------------------------------------------------------------------
def transform(px, py, at, mirror=None):
    sx, sy, rot = at
    x, y = px, py
    if mirror == 'x':
        y = -y
    elif mirror == 'y':
        x = -x
    a = math.radians(rot)
    xr = x * math.cos(a) + y * math.sin(a)
    yr = -x * math.sin(a) + y * math.cos(a)
    return (round(sx + xr, 2), round(sy - yr, 2))

class Sheet:
    def __init__(self, filename, sheet_uuid, title, page):
        self.filename = filename
        self.uuid = sheet_uuid
        self.title = title
        self.page = page
        self.libsyms = {}
        self.items = []
        self.pinpos = {}     # (ref, number) -> (x, y, dx, dy)  stub direction unit vector
        self.refs = {}
        self.pwr_n = 0

    def add_lib(self, libsym):
        name = libsym[1]
        if name not in self.libsyms:
            self.libsyms[name] = libsym
        return self.libsyms[name]

    def place(self, lib, ref, x, y, rot=0, mirror=None, value=None, footprint=None, fields=None, hide_value=False):
        """lib: ('Device','R') for a standard lib symbol, or 'Rev3:NAME' for a custom one."""
        if isinstance(lib, tuple):
            ls = get_symbol(*lib)
        else:
            ls = custom_symbol(lib.split(':', 1)[1])
        ls = self.add_lib(ls)
        lib_id = ls[1]
        x = round(round(x / 1.27) * 1.27, 2)      # snap to the 50 mil connection grid
        y = round(round(y / 1.27) * 1.27, 2)
        at = (x, y, rot)
        sym = [S('symbol'), [S('lib_id'), lib_id], [S('at'), num(x), num(y), num(rot)]]
        if mirror:
            sym.append([S('mirror'), S(mirror)])
        sym += [[S('unit'), num(1)], [S('body_style'), num(1)], [S('exclude_from_sim'), S('no')], [S('in_bom'), S('yes')],
                [S('on_board'), S('yes')], [S('in_pos_files'), S('yes')], [S('dnp'), S('no')],
                [S('fields_autoplaced'), S('yes')], [S('uuid'), U()]]
        # properties: start from lib defaults
        libprops = {p[1]: p for p in find(ls, 'property')}
        fp = footprint if footprint is not None else (libprops.get('Footprint', [None, None, ''])[2])
        ds = (fields or {}).get('Datasheet', libprops.get('Datasheet', [None, None, ''])[2])
        desc = (fields or {}).get('Description', libprops.get('Description', [None, None, ''])[2])
        val = value if value is not None else libprops.get('Value', [None, None, lib_id])[2]
        sym.append(property_('Reference', ref, x + 2.54, y - 2.54, 0, hide=ref.startswith('#'), justify='left'))
        sym.append(property_('Value', val, x + 2.54, y, 0, hide=hide_value, justify='left'))
        sym.append(property_('Footprint', fp, x, y, 0, hide=True))
        sym.append(property_('Datasheet', ds, x, y, 0, hide=True))
        sym.append(property_('Description', desc, x, y, 0, hide=True))
        extra = {k: v[2] for k, v in libprops.items() if k in ('MPN', 'Manufacturer', 'Panel')}
        extra.update({k: v for k, v in (fields or {}).items() if k not in ('Datasheet', 'Description')})
        for k, v in extra.items():
            sym.append(property_(k, v, x, y, 0, hide=True))
        for p in lib_pins(ls):
            sym.append([S('pin'), p['number'], [S('uuid'), U()]])
        sym.append([S('instances'), [S('project'), PROJECT, [S('path'), f"/{ROOT_UUID}/{self.uuid}",
                                                              [S('reference'), ref], [S('unit'), num(1)]]]])
        self.items.append(sym)
        dirs = {0: (-1, 0), 180: (1, 0), 90: (0, -1), 270: (0, 1)}
        for p in lib_pins(ls):
            pt = transform(p['x'], p['y'], at, mirror)
            dx, dy = dirs[int(p['angle']) % 360]
            pe = transform(p['x'] + dx, p['y'] + dy, at, mirror)
            ux, uy = round(pe[0] - pt[0], 2), round(pe[1] - pt[1], 2)
            self.pinpos[(ref, p['number'])] = (pt[0], pt[1], ux, uy, p['name'])
        self.refs[ref] = sym
        return sym

    def pin(self, ref, number):
        return self.pinpos[(ref, str(number))]

    def wire(self, a, b):
        self.items.append([S('wire'), [S('pts'), [S('xy'), num(a[0]), num(a[1])], [S('xy'), num(b[0]), num(b[1])]],
                           [S('stroke'), [S('width'), num(0)], [S('type'), S('default')]], [S('uuid'), U()]])

    def junction(self, p):
        self.items.append([S('junction'), [S('at'), num(p[0]), num(p[1])], [S('diameter'), num(0)],
                           [S('color'), num(0), num(0), num(0), num(0)], [S('uuid'), U()]])

    def label(self, name, p, ux, uy, glob=False, shape='bidirectional'):
        if ux > 0: rot, just = 0, 'left bottom'
        elif ux < 0: rot, just = 180, 'right bottom'
        elif uy < 0: rot, just = 90, 'left bottom'
        else: rot, just = 270, 'right bottom'
        if glob:
            just = 'left' if rot in (0, 90) else 'right'
            self.items.append([S('global_label'), name, [S('shape'), S(shape)], [S('at'), num(p[0]), num(p[1]), num(rot)],
                               [S('fields_autoplaced'), S('yes')], effects(1.27, just), [S('uuid'), U()],
                               [S('property'), 'Intersheetrefs', '${INTERSHEET_REFS}', [S('at'), num(p[0]), num(p[1]), num(0)],
                                [S('hide'), S('yes')], [S('show_name'), S('no')], [S('do_not_autoplace'), S('no')], effects(1.27, just)]])
        else:
            self.items.append([S('label'), name, [S('at'), num(p[0]), num(p[1]), num(rot)], effects(1.27, just), [S('uuid'), U()]])

    def no_connect(self, ref, number):
        x, y, ux, uy, _ = self.pin(ref, number)
        self.items.append([S('no_connect'), [S('at'), num(x), num(y)], [S('uuid'), U()]])

    def power(self, name, p, ux, uy):
        """Place a power symbol whose pin sits at p; ux/uy give the free direction."""
        self.pwr_n += 1
        ref = f"#PWR3{self.page:02d}{self.pwr_n:02d}"
        rot = 0
        if name == 'GND':
            # GND body hangs below its pin -> free direction must be down
            rot = {(0, 1): 0, (1, 0): 270, (-1, 0): 90, (0, -1): 180}[(int(ux), int(uy))]
        else:
            rot = {(0, -1): 0, (1, 0): 90, (-1, 0): 270, (0, 1): 180}[(int(ux), int(uy))]
        self.place(('power', name), ref, p[0], p[1], rot, value=name)

    def net(self, ref, number, name, kind='label', stub=2.54, shape='bidirectional'):
        """Connect pin to a net by a stub wire ending in a local/global label or power symbol."""
        x, y, ux, uy, pname = self.pin(ref, number)
        end = (round(x + ux * stub, 2), round(y + uy * stub, 2))
        if stub > 0:
            self.wire((x, y), end)
        if kind == 'label':
            self.label(name, end, ux, uy)
        elif kind == 'global':
            self.label(name, end, ux, uy, glob=True, shape=shape)
        elif kind == 'power':
            # side pins get a rotated power symbol at the stub end (a vertical jog would land on the
            # neighbouring pin's stub and short the nets)
            self.power(name, end, ux, uy)
        return end

    def text(self, s, x, y, size=1.27):
        self.items.append([S('text'), s, [S('exclude_from_sim'), S('no')], [S('at'), num(x), num(y), num(0)],
                           effects(size, 'left top'), [S('uuid'), U()]])

    def serialize(self):
        root = [S('kicad_sch'), [S('version'), num(VERSION)], [S('generator'), 'eeschema'], [S('generator_version'), '10.0'],
                [S('uuid'), self.uuid], [S('paper'), 'A3'],
                [S('title_block'), [S('title'), self.title], [S('date'), DATE], [S('rev'), '3.0'], [S('company'), 'READARK'],
                 [S('comment'), num(1), 'M. Ömer Karaoğlu']],
                [S('lib_symbols')] + list(self.libsyms.values())]
        root += self.items
        root.append([S('embedded_fonts'), S('no')])
        return dump(root) + '\n'

    def write(self):
        with open(os.path.join(PROJ, self.filename), 'w', encoding='utf-8') as f:
            f.write(self.serialize())

# convenience for passives --------------------------------------------------------
R0402 = 'Resistor_SMD:R_0402_1005Metric'
R0603 = 'Resistor_SMD:R_0603_1608Metric'
R0805 = 'Resistor_SMD:R_0805_2012Metric'
C0402 = 'Capacitor_SMD:C_0402_1005Metric'
C0603 = 'Capacitor_SMD:C_0603_1608Metric'
C0805 = 'Capacitor_SMD:C_0805_2012Metric'

def two_pin(sh, lib, ref, x, y, value, fp, top, bottom, rot=0, fields=None, topkind='label', botkind='label', stub=2.54):
    """Vertical 2-pin part (R/C/L/NTC: pin1 at top, pin2 at bottom with rot=0). top/bottom: net names.
    kinds: 'label' | 'global' | 'power' | 'nc'."""
    sh.place(lib, ref, x, y, rot, value=value, footprint=fp, fields=fields)
    for n, nm, kind in (('1', top, topkind), ('2', bottom, botkind)):
        if kind == 'nc':
            sh.no_connect(ref, n)
        else:
            sh.net(ref, n, nm, kind, stub)

# ----------------------------------------------------------------------------------
# Sheet: Power (5 V -> 3.3 V buck, 3.3 V -> 1.2 V LDO)
# ----------------------------------------------------------------------------------
def build_power():
    sh = Sheet('Rev3_Power.kicad_sch', '3a0f6c2e-0001-4c3e-9b1e-000000000003', 'Rev3.0 Power: 5V->3V3 buck, 3V3->1V2 LDO', 4)
    sh.text("5 V rail comes from PS1 (HLK-10M05, 5 V / 2 A) on the root sheet.\n"
            "U30 TPS562201: 5 V -> 3.3 V synchronous buck, 580 kHz, 2 A. Vout = 0.768 V x (1 + R330/R331) = 3.32 V.\n"
            "U31 LD1117S12: 3.3 V -> 1.2 V LDO for the SSD1963 core/PLL (VDDD, VDDPLL).\n"
            "Layout: C330/C331 at U30 VIN pin, C332 (VBST) next to the IC, L30/C333/C334 loop tight, FB divider close to VFB, no copper under L30 on inner layers.",
            20, 20, 1.6)
    # Buck
    u = 'U30'
    sh.place(('Regulator_Switching', 'TPS562200'), u, 90, 70, 0, value='TPS562201DDCR',
             footprint='Package_TO_SOT_SMD:TSOT-23-6',
             fields={'MPN': 'TPS562201DDCR', 'Manufacturer': 'Texas Instruments', 'Datasheet': URLS['TPS562201DDCR'],
                     'Description': '4.5-17 V input, 2 A synchronous step-down converter, 580 kHz, TSOT23-6, -40..+125 C'})
    sh.net(u, '3', '+5V', 'power', 5.08)          # VIN
    sh.net(u, '5', '+5V', 'power', 5.08)          # EN tied to VIN (EN abs max 6.5 V)
    sh.net(u, '1', 'GND', 'power', 2.54)          # GND
    sh.net(u, '2', 'BUCK_SW', 'label', 5.08)      # SW
    sh.net(u, '6', 'BUCK_BST', 'label', 5.08)     # VBST
    sh.net(u, '4', 'BUCK_FB', 'label', 5.08)      # VFB
    two_pin(sh, ('Device', 'C'), 'C330', 50, 70, '10uF 10V X5R', C0805, '+5V', 'GND', topkind='power', botkind='power')
    two_pin(sh, ('Device', 'C'), 'C331', 60, 70, '10uF 10V X5R', C0805, '+5V', 'GND', topkind='power', botkind='power')
    two_pin(sh, ('Device', 'C'), 'C332', 120, 60, '100nF 25V X7R', C0402, 'BUCK_BST', 'BUCK_SW')
    two_pin(sh, ('Device', 'L'), 'L30', 135, 70, '4.7uH 4A', 'Inductor_SMD:L_Bourns_SRN6045TA', 'BUCK_SW', '+3V3',
            botkind='power', fields={'MPN': 'SRI0605B-4R7M', 'Manufacturer': 'Core Master', 'Datasheet': URLS['SRI0605B-4R7M'],
                                     'Description': 'Shielded power inductor 4.7 uH 4 A 70 mOhm 6.6x6.2x5 mm (footprint placeholder: verify against SRI0605B drawing)'})
    two_pin(sh, ('Device', 'R'), 'R330', 150, 62, '33.2k 1%', R0402, '+3V3', 'BUCK_FB', topkind='power')
    two_pin(sh, ('Device', 'R'), 'R331', 150, 78, '10k 1%', R0402, 'BUCK_FB', 'GND', botkind='power')
    two_pin(sh, ('Device', 'C'), 'C333', 165, 70, '22uF 10V X5R', C0805, '+3V3', 'GND', topkind='power', botkind='power')
    two_pin(sh, ('Device', 'C'), 'C334', 175, 70, '22uF 10V X5R', C0805, '+3V3', 'GND', topkind='power', botkind='power')
    # LDO
    u = 'U31'
    sh.place(('Regulator_Linear', 'LD1117S12TR_SOT223'), u, 90, 120, 0, value='LD1117S12CTR',
             footprint='Package_TO_SOT_SMD:SOT-223-3_TabPin2',
             fields={'MPN': 'LD1117S12CTR', 'Manufacturer': 'STMicroelectronics', 'Datasheet': URLS['LD1117S12CTR'],
                     'Description': '1.2 V 800 mA LDO, SOT-223, -40..+125 C, SSD1963 core supply'})
    sh.net(u, '3', '+3V3', 'power', 5.08)
    sh.net(u, '2', '+1V2', 'power', 5.08)
    sh.net(u, '1', 'GND', 'power', 2.54)
    two_pin(sh, ('Device', 'C'), 'C335', 60, 120, '1uF 16V X7R', C0603, '+3V3', 'GND', topkind='power', botkind='power')
    two_pin(sh, ('Device', 'C'), 'C336', 120, 120, '10uF 6.3V X5R', C0805, '+1V2', 'GND', topkind='power', botkind='power')
    two_pin(sh, ('Device', 'C'), 'C337', 130, 120, '1uF 6.3V X7R', C0603, '+1V2', 'GND', topkind='power', botkind='power')
    # power flags: +3V3 and +1V2 are driven by power_out pins (U30 SW is 'output' type; L30 is passive) -> add PWR_FLAG on +3V3
    sh.place(('power', 'PWR_FLAG'), '#FLG301', 200, 60, 0, value='PWR_FLAG')
    sh.net('#FLG301', '1', '+3V3', 'power', 2.54)
    sh.text("Power budget (Rev3.0): 5 V rail 5.5 W peak (backlight 1.6 W, ESP32 Wi-Fi 1.2 W, SSD1963+panel 0.5 W, relay 0.4 W, fan up to 1.5 W).\n"
            "3V3 rail: ~0.9 A peak -> buck loss ~0.3 W. 1V2 rail: ~60 mA -> LDO loss 0.13 W.", 20, 150, 1.6)
    return sh

# ----------------------------------------------------------------------------------
# Sheet: Thermocouple (ADS1115 front end)
# ----------------------------------------------------------------------------------
def build_thermo():
    sh = Sheet('Rev3_Thermocouple.kicad_sch', '3a0f6c2e-0001-4c3e-9b1e-000000000002', 'Rev3.0 Thermocouple front end (K-type, ADS1115)', 3)
    sh.text("K-type thermocouple on J20 (DEGSON DG127H-5.08-02P screw terminal). Differential RC filter (R220/R221 1k, C220 100n diff, C221/C222 10n CM):\n"
            "fc(diff) = 1/(2*pi*2k*100n) = 0.8 kHz, fc(CM) = 16 kHz. R222/R223 10M (terminal side of R220/R221, so their bias current does not flow through the 1k) pull the inputs to the rails when the\n"
            "thermocouple is open (ADS1115 reads full scale -> firmware reports NAN). D220/D221 PESD5V0S1BA clamp ESD/EFT from the probe wiring.\n"
            "ADS1115: AIN0-AIN1 differential, PGA +/-256 mV (7.8 uV/LSB = 0.19 C for K), 16 SPS; ADDR=GND -> 0x48; ALERT/RDY -> ADC_RDY (IO35).\n"
            "Cold junction: TH220 10k NTC (Murata NCP18XH103, B=3380 K) placed touching J20; ratiometric against R226/R227 half-supply on AIN3.\n"
            "Layout: route TC_P/TC_N as a tightly coupled pair, keep away from the triac/heater wiring and the LCD bus; single-point ground at U20.",
            20, 20, 1.6)
    sh.place(('Connector', 'Screw_Terminal_01x02'), 'J20', 40, 80, 0, value='K-type TC', mirror='y',
             footprint='TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal',
             fields={'MPN': 'DG127H-5.08-02P-14-00AH', 'Manufacturer': 'DEGSON', 'Datasheet': URLS['DG127H-5.08-02P-14-00AH'],
                     'Description': 'PCB screw terminal block 2-pin 5.08 mm, 12 A 300 V, 26-14 AWG'})
    sh.net('J20', '1', 'TC_P', 'label', 5.08)
    sh.net('J20', '2', 'TC_N', 'label', 5.08)
    for ref, net, x in (('D220', 'TC_P', 60), ('D221', 'TC_N', 70)):
        sh.place(('Device', 'D_TVS'), ref, x, 100, 90, value='PESD5V0S1BA', footprint='Diode_SMD:D_SOD-323',
                 fields={'MPN': 'PESD5V0S1BA,115', 'Manufacturer': 'Nexperia', 'Datasheet': URLS['PESD5V0S1BA'],
                         'Description': 'Bidirectional ESD/TVS diode 5 V 130 W SOD-323'})
        sh.net(ref, '1', net, 'label', 2.54)
        sh.net(ref, '2', 'GND', 'power', 2.54)
    two_pin(sh, ('Device', 'R'), 'R220', 85, 72, '1k 0.1%', R0603, 'TC_P', 'TCF_P', rot=90)
    two_pin(sh, ('Device', 'R'), 'R221', 85, 88, '1k 0.1%', R0603, 'TC_N', 'TCF_N', rot=90)
    two_pin(sh, ('Device', 'C'), 'C220', 100, 80, '100nF 50V X7R', C0603, 'TCF_P', 'TCF_N')
    two_pin(sh, ('Device', 'C'), 'C221', 110, 65, '10nF 50V C0G 1%', C0603, 'TCF_P', 'GND', botkind='power')
    two_pin(sh, ('Device', 'C'), 'C222', 110, 95, '10nF 50V C0G 1%', C0603, 'TCF_N', 'GND', botkind='power')
    two_pin(sh, ('Device', 'R'), 'R222', 70, 60, '10M', R0603, '+3V3', 'TC_P', topkind='power')
    two_pin(sh, ('Device', 'R'), 'R223', 70, 100, '10M', R0603, 'TC_N', 'GND', botkind='power')
    # ADC
    u = 'U20'
    sh.place(('Analog_ADC', 'ADS1115IDGS'), u, 160, 80, 0, value='ADS1115IDGSR',
             fields={'MPN': 'ADS1115IDGSR', 'Manufacturer': 'Texas Instruments', 'Datasheet': URLS['ADS1115IDGSR'],
                     'Description': '16-bit delta-sigma ADC, 4 ch, PGA, I2C, 860 SPS, VSSOP-10, -40..+125 C'})
    sh.net(u, '4', 'TCF_P', 'label', 5.08)
    sh.net(u, '5', 'TCF_N', 'label', 5.08)
    sh.net(u, '6', 'NTC_MID', 'label', 5.08)
    sh.net(u, '7', 'VREF_HALF', 'label', 5.08)
    sh.net(u, '8', '+3V3', 'power', 2.54)
    sh.net(u, '3', 'GND', 'power', 2.54)
    sh.net(u, '1', 'GND', 'power', 5.08)        # ADDR -> 0x48
    sh.net(u, '2', 'ADC_RDY', 'global', 7.62, shape='output')
    sh.net(u, '9', 'I2C_SDA', 'global', 7.62)
    sh.net(u, '10', 'I2C_SCL', 'global', 7.62, shape='input')
    two_pin(sh, ('Device', 'R'), 'R224', 190, 62, '10k', R0402, '+3V3', 'ADC_RDY', topkind='power', botkind='global')
    two_pin(sh, ('Device', 'C'), 'C223', 140, 55, '100nF 16V X7R', C0402, '+3V3', 'GND', topkind='power', botkind='power')
    two_pin(sh, ('Device', 'C'), 'C224', 150, 55, '1uF 16V X7R', C0603, '+3V3', 'GND', topkind='power', botkind='power')
    # CJC NTC + reference
    two_pin(sh, ('Device', 'Thermistor_NTC'), 'TH220', 60, 130, '10k NTC B3380', R0603, '+3V3', 'NTC_MID', topkind='power',
            fields={'MPN': 'NCP18XH103F03RB', 'Manufacturer': 'Murata', 'Datasheet': URLS['NCP18XH103F03RB'],
                    'Description': 'NTC thermistor 10k 1% B25/50=3380K 0603 - cold junction sensor, place touching J20'})
    two_pin(sh, ('Device', 'R'), 'R225', 60, 150, '10k 0.1%', R0603, 'NTC_MID', 'GND', botkind='power')
    two_pin(sh, ('Device', 'C'), 'C225', 75, 150, '100nF 16V X7R', C0402, 'NTC_MID', 'GND', botkind='power')
    two_pin(sh, ('Device', 'R'), 'R226', 100, 130, '10k 0.1%', R0603, '+3V3', 'VREF_HALF', topkind='power')
    two_pin(sh, ('Device', 'R'), 'R227', 100, 150, '10k 0.1%', R0603, 'VREF_HALF', 'GND', botkind='power')
    two_pin(sh, ('Device', 'C'), 'C226', 115, 150, '100nF 16V X7R', C0402, 'VREF_HALF', 'GND', botkind='power')
    return sh

# ----------------------------------------------------------------------------------
# Sheet: Display (SSD1963 + TFT + backlight + touch)
# ----------------------------------------------------------------------------------
def build_display():
    sh = Sheet('Rev3_Display.kicad_sch', '3a0f6c2e-0001-4c3e-9b1e-000000000001', 'Rev3.0 Display: SSD1963 controller, 7" RGB TFT, backlight, GT911 touch', 2)
    sh.text("U10 SSD1963QL9 drives the 7\" 800x480 panel (24-bit RGB, 33.3 MHz PCLK) from a 1215 KB frame buffer; the ESP32 writes it over an\n"
            "8-bit 8080 bus (D0-D7, WR#, D/C#, CS#, RESET#). CONF=1 -> 8080 mode. RD# pulled up (no reads). CLK tied to GND, 10 MHz crystal on XTAL.\n"
            "R110-R121 33 ohm series terminations: PLACE AT THE ESP32 END of each line, bus length < 80 mm over a solid ground plane.\n"
            "D8-D23, TE, GPIO0-3, GAMAS left open as the datasheet requires. VDDD/VDDPLL = 1.2 V, VDDIO/VDDLCD = 3.3 V, one 100 nF per 2-3 supply pins.\n"
            "Backlight: U11 MIC2288 boost 5 V -> 9.6 V, Iled = 1.24 V / (R122||R123 = 9 ohm) = 138 mA, PWM dimming from SSD1963 PWM pin into EN.\n"
            "D114 15 V zener clamps the output if the LED string is open. Touch: GT911 on J11, I2C 400 kHz, INT=IO32, RST shared with LCD_RST.",
            20, 20, 1.6)
    u = 'U10'
    sh.place('Rev3:SSD1963QL9', u, 190, 150, 0)
    # MCU side
    for i in range(8):
        dmap = {0: 7, 1: 8, 2: 9, 3: 10, 4: 11, 5: 116, 6: 115, 7: 114}
        sh.net(u, str(dmap[i]), f'SSD_D{i}', 'label', 5.08)
    for n in (113, 112, 111, 107, 106, 105, 104, 103, 99, 98, 88, 87, 92, 91, 90, 89):   # D8..D23
        sh.no_connect(u, str(n))
    sh.net(u, '123', 'SSD_CS', 'label', 5.08)
    sh.net(u, '122', 'SSD_DC', 'label', 5.08)
    sh.net(u, '120', 'SSD_WR', 'label', 5.08)
    sh.net(u, '121', 'SSD_RD', 'label', 5.08)
    sh.net(u, '127', 'SSD_RST', 'label', 5.08)
    sh.net(u, '128', '+3V3', 'power', 5.08)       # CONF = 1 -> 8080
    sh.no_connect(u, '50')                        # TE
    sh.net(u, '15', 'GND', 'power', 5.08)         # CLK unused -> VSS
    sh.net(u, '22', 'XTAL_IN', 'label', 5.08)
    sh.net(u, '24', 'XTAL_OUT', 'label', 5.08)
    # LCD side
    lmap = {23: 28, 22: 29, 21: 30, 20: 31, 17: 35, 16: 59, 15: 60, 14: 61, 13: 62, 12: 63, 11: 67, 10: 68, 9: 69,
            8: 70, 7: 71, 6: 72, 5: 76, 4: 77, 3: 78, 2: 79, 1: 80, 0: 81, 19: 85, 18: 86}
    for i in range(24):
        col = 'RGB'[2 - i // 8]       # LDATA0-7 = B, 8-15 = G, 16-23 = R
        sh.net(u, str(lmap[i]), f'{col}{i % 8}', 'label', 5.08)
    sh.net(u, '45', 'PCLK', 'label', 5.08)
    sh.net(u, '44', 'HSYNC', 'label', 5.08)
    sh.net(u, '43', 'VSYNC', 'label', 5.08)
    sh.net(u, '49', 'DE', 'label', 5.08)
    sh.net(u, '51', 'BL_PWM', 'label', 5.08)
    for n in ('36', '37', '38', '39', '52', '53'):
        sh.no_connect(u, n)
    # power pins (stacked: connect visible ones)
    sh.net(u, '1', '+1V2', 'power', 2.54)      # VDDD
    sh.net(u, '18', '+1V2', 'power', 2.54)     # VDDPLL
    sh.net(u, '4', '+3V3', 'power', 2.54)      # VDDIO
    sh.net(u, '27', '+3V3', 'power', 2.54)     # VDDLCD
    sh.net(u, '2', 'GND', 'power', 2.54)       # VSS
    sh.net(u, '19', 'GND', 'power', 2.54)      # VSSPLL
    # series terminations (MCU end)
    nets = [(f'LCD_D{i}', f'SSD_D{i}') for i in range(8)] + [('LCD_CS', 'SSD_CS'), ('LCD_DC', 'SSD_DC'), ('LCD_WR', 'SSD_WR'), ('LCD_RST', 'SSD_RST')]
    for k, (g, l) in enumerate(nets):
        ref = f'R{110 + k}'
        x = 60 + (k % 6) * 15
        y = 70 + (k // 6) * 30
        two_pin(sh, ('Device', 'R'), ref, x, y, '33R', R0402, g, l, topkind='global', stub=3.81)
    two_pin(sh, ('Device', 'R'), 'R124', 150, 70, '10k', R0402, '+3V3', 'SSD_RD', topkind='power')
    # crystal
    sh.place(('Device', 'Crystal_GND24'), 'Y10', 100, 130, 0, value='10MHz', footprint='Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm',
             fields={'MPN': 'CX3225GB10000P0HPQCC', 'Manufacturer': 'Kyocera AVX', 'Datasheet': URLS['CX3225GB10000P0HPQCC'],
                     'Description': 'Crystal 10 MHz 18 pF 3225 4-pad, +/-20 ppm'})
    sh.net('Y10', '1', 'XTAL_IN', 'label', 3.81)
    sh.net('Y10', '3', 'XTAL_OUT', 'label', 3.81)
    sh.net('Y10', '2', 'GND', 'power', 2.54)
    two_pin(sh, ('Device', 'C'), 'C110', 85, 145, '27pF C0G', C0402, 'XTAL_IN', 'GND', botkind='power')
    two_pin(sh, ('Device', 'C'), 'C111', 115, 145, '27pF C0G', C0402, 'XTAL_OUT', 'GND', botkind='power')
    # decoupling
    x = 60
    for ref, val, fp, net in (('C112', '100nF 16V X7R', C0402, '+3V3'), ('C113', '100nF 16V X7R', C0402, '+3V3'),
                              ('C114', '100nF 16V X7R', C0402, '+3V3'), ('C115', '100nF 16V X7R', C0402, '+3V3'),
                              ('C116', '10uF 6.3V X5R', C0805, '+3V3'),
                              ('C117', '100nF 16V X7R', C0402, '+1V2'), ('C118', '100nF 16V X7R', C0402, '+1V2'),
                              ('C119', '100nF 16V X7R', C0402, '+1V2'), ('C120', '1uF 6.3V X7R', C0603, '+1V2'),
                              ('C121', '1uF 6.3V X7R', C0603, '+1V2')):
        two_pin(sh, ('Device', 'C'), ref, x, 185, val, fp, net, 'GND', topkind='power', botkind='power')
        x += 10
    sh.text("C112-C116: VDDIO/VDDLCD (3V3) decoupling, one per 2-3 pins, C117-C121: VDDD/VDDPLL (1V2) decoupling; C121 at VDDPLL pin 18.", 60, 200, 1.27)
    # TFT connector
    j = 'J10'
    sh.place('Rev3:TFT_SAT070AT40D21_FPC40', j, 300, 120, 0, mirror='y')
    for i in range(8):
        sh.net(j, str(5 + i), f'R{i}', 'label', 5.08)
        sh.net(j, str(13 + i), f'G{i}', 'label', 5.08)
        sh.net(j, str(21 + i), f'B{i}', 'label', 5.08)
    sh.net(j, '30', 'PCLK', 'label', 5.08)
    sh.net(j, '32', 'HSYNC', 'label', 5.08)
    sh.net(j, '33', 'VSYNC', 'label', 5.08)
    sh.net(j, '34', 'DE', 'label', 5.08)
    sh.net(j, '1', 'VLED_N', 'label', 5.08)
    sh.net(j, '2', 'VLED_P', 'label', 5.08)
    sh.net(j, '4', 'TFT_VDD', 'label', 5.08)
    for n in ('3', '29', '36'):
        sh.net(j, n, 'GND', 'power', 5.08)
    for n in ('31', '35', '37', '38', '39', '40'):
        sh.no_connect(j, n)
    # panel supply: ferrite bead-less, just caps (10uF + 100nF) + 0R link from 3V3 so the panel can be isolated for debugging
    two_pin(sh, ('Device', 'R'), 'R125', 330, 60, '0R', R0805, '+3V3', 'TFT_VDD', topkind='power')
    two_pin(sh, ('Device', 'C'), 'C122', 345, 70, '10uF 6.3V X5R', C0805, 'TFT_VDD', 'GND', botkind='power')
    two_pin(sh, ('Device', 'C'), 'C123', 355, 70, '100nF 16V X7R', C0402, 'TFT_VDD', 'GND', botkind='power')
    # Backlight boost
    u = 'U11'
    sh.place('Rev3:MIC2288YD5', u, 300, 215, 0)
    sh.net(u, '5', 'BL_VIN', 'label', 5.08)
    sh.net(u, '4', 'BL_EN', 'label', 5.08)
    sh.net(u, '1', 'BL_SW', 'label', 5.08)
    sh.net(u, '3', 'BL_FB', 'label', 5.08)
    sh.net(u, '2', 'GND', 'power', 2.54)
    two_pin(sh, ('Device', 'C'), 'C124', 270, 215, '10uF 10V X5R', C0805, 'BL_VIN', 'GND', botkind='power')
    two_pin(sh, ('Device', 'C'), 'C127', 255, 215, '10uF 10V X5R', C0805, '+5V', 'GND', topkind='power', botkind='power')
    two_pin(sh, ('Device', 'L'), 'L12', 262, 195, '2.2uH 1A', 'Inductor_SMD:L_Taiyo-Yuden_NR-40xx', '+5V', 'BL_VIN', rot=90, topkind='power',
            fields={'Description': 'Pi-filter inductor 2.2 uH >=1 A SMD 4x4 mm (e.g. Viking PCD0403 / Core Master FPI0403S series, pick in-stock value at Ozdisan)'})
    two_pin(sh, ('Device', 'R'), 'R132', 285, 200, '0.5R 0.25W', 'Resistor_SMD:R_1206_3216Metric', 'BL_VIN', 'BL_DAMP')
    two_pin(sh, ('Device', 'C_Polarized'), 'C128', 285, 222, '47uF 10V', 'Capacitor_SMD:CP_Elec_5x5.4', 'BL_DAMP', 'GND', botkind='power',
            fields={'Description': 'Pi-filter damper 47 uF electrolytic/tantalum (Koshin or similar), in series with R132 0.5R'})
    two_pin(sh, ('Device', 'L'), 'L11', 330, 200, '10uH 1A', 'Inductor_SMD:L_Taiyo-Yuden_NR-40xx', 'BL_VIN', 'BL_SW',
            fields={'MPN': 'PCD0403MT100', 'Manufacturer': 'Viking', 'Datasheet': URLS['PCD0403MT100'],
                    'Description': 'Power inductor 10 uH 1.04 A 182 mOhm 4.5x4x3.2 mm (footprint placeholder: verify against PCD0403 drawing)'})
    sh.place(('Device', 'D_Schottky'), 'D111', 345, 215, 0, value='SS14', footprint='Diode_SMD:D_SMA',
             fields={'MPN': 'SS14', 'Manufacturer': 'ON Semiconductor / Panjit', 'Datasheet': URLS['SS14'],
                     'Description': 'Schottky rectifier 1 A 40 V SMA'})
    sh.net('D111', '2', 'BL_SW', 'label', 3.81)     # anode
    sh.net('D111', '1', 'VLED_P', 'label', 3.81)    # cathode
    two_pin(sh, ('Device', 'C'), 'C125', 365, 230, '4.7uF 25V X7R', C0805, 'VLED_P', 'GND', botkind='power')
    sh.place(('Device', 'D_Zener'), 'D114', 375, 215, 90, value='15V 500mW', footprint='Diode_SMD:D_SOD-123',
             fields={'Description': 'Zener 15 V 500 mW SOD-123 (open-LED clamp), e.g. MMSZ5245B / BZT52C15'})
    sh.net('D114', '1', 'VLED_P', 'label', 2.54)
    sh.net('D114', '2', 'GND', 'power', 2.54)
    two_pin(sh, ('Device', 'R'), 'R122', 390, 230, '18R 0.125W', R0805, 'VLED_N', 'GND', botkind='power')
    two_pin(sh, ('Device', 'R'), 'R123', 400, 230, '18R 0.125W', R0805, 'VLED_N', 'GND', botkind='power')
    two_pin(sh, ('Device', 'R'), 'R126', 285, 240, '0R', R0402, 'BL_FB', 'VLED_N')
    two_pin(sh, ('Device', 'R'), 'R127', 270, 240, '100k', R0402, 'BL_EN', 'GND', botkind='power')
    two_pin(sh, ('Device', 'R'), 'R128', 255, 240, '0R', R0402, 'BL_PWM', 'BL_EN')
    sh.text("Backlight: VLED+ = 9.6 V typ (8.7-10.5 V), 3 LEDs in series x 7 strings. FB = 1.24 V across R122||R123 -> 138 mA.\n"
            "Boost input pi-filter C127 10u | L12 2.2u | C124 10u with R132/C128 (0.5R + 47u) damper keeps the 1.2 MHz ripple off the 5 V rail (see EMI report).", 250, 260, 1.27)
    # Touch connector (lower-left block)
    j = 'J11'
    sh.place('Rev3:CTP_GT911_FPC6', j, 80, 245, 0, mirror='y')
    sh.net(j, '1', 'TP_VDD', 'label', 5.08)
    sh.net(j, '2', 'GND', 'power', 5.08)
    sh.net(j, '3', 'TP_INT', 'global', 7.62)
    sh.net(j, '4', 'I2C_SDA', 'global', 7.62)
    sh.net(j, '5', 'I2C_SCL', 'global', 7.62, shape='input')
    sh.net(j, '6', 'LCD_RST', 'global', 7.62, shape='input')
    two_pin(sh, ('Device', 'R'), 'R129', 130, 235, '0R', R0805, '+3V3', 'TP_VDD', topkind='power')
    two_pin(sh, ('Device', 'C'), 'C126', 145, 245, '100nF 16V X7R', C0402, 'TP_VDD', 'GND', botkind='power')
    two_pin(sh, ('Device', 'R'), 'R130', 170, 235, '2.2k', R0402, '+3V3', 'I2C_SDA', topkind='power', botkind='global')
    two_pin(sh, ('Device', 'R'), 'R131', 185, 235, '2.2k', R0402, '+3V3', 'I2C_SCL', topkind='power', botkind='global')
    for ref, net, x in (('D112', 'I2C_SDA', 170), ('D113', 'I2C_SCL', 185)):
        sh.place(('Device', 'D_TVS'), ref, x, 262, 90, value='PESD5V0S1BA', footprint='Diode_SMD:D_SOD-323',
                 fields={'MPN': 'PESD5V0S1BA,115', 'Manufacturer': 'Nexperia', 'Datasheet': URLS['PESD5V0S1BA'],
                         'Description': 'Bidirectional ESD/TVS diode 5 V 130 W SOD-323'})
        sh.net(ref, '1', net, 'global', 2.54)
        sh.net(ref, '2', 'GND', 'power', 2.54)
    sh.text("Touch (GT911 on J11): I2C 400 kHz, R130/R131 2.2k are the ONLY pull-ups on the bus (ADS1115 shares it). INT=IO32 (driven low at reset -> addr 0x5D), RST = LCD_RST.", 60, 275, 1.27)
    return sh

# ----------------------------------------------------------------------------------
# Sheet: Mains input EMC filter (series 120 uH choke + 1 uF X2), inserted after fuse F1
# ----------------------------------------------------------------------------------
def build_filter():
    sh = Sheet('Rev3_InputFilter.kicad_sch', '3a0f6c2e-0001-4c3e-9b1e-000000000004', 'Rev3.0 Mains input EMC filter (PSU branch)', 5)
    sh.text("Differential-mode LC stage on the PSU branch, inserted between fuse F1 (1 A slow blow) and the existing RV1 / C1 (X2) / L1 (CM choke) / PS1 chain:\n"
            "LINE_FUSED -> L40 120 uH (IND-120UH-THT, radial D22.5 mm, P9 mm) -> LINE_FILT; C40 1 uF 275 VAC X2 (Faratronic C42P2105KBSC400, P27.5 mm) from LINE_FILT to NEUT.\n"
            "With C1 (100 nF X2) the stage is a pi-filter: fc = 1/(2*pi*sqrt(120u*1u)) = 14.5 kHz, ~40 dB/dec above it; attenuates the HLK-10M05 switching\n"
            "fundamental (~65 kHz) by ~26 dB and its harmonics more. Carries only the PSU current (<100 mA), not the heater or fan current.\n"
            "Layout: keep L40 away from the thermocouple input and the LCD bus (unshielded choke); C40 bleeder is R6/R7 (2x33k) already on the root sheet.",
            20, 20, 1.6)
    sh.place(('Device', 'L'), 'L40', 80, 70, 90, value='120uH', footprint='Rev3:L_Radial_D22.5mm_P9.00mm',
             fields={'MPN': 'IND-120UH-THT', 'Manufacturer': 'OEM (ozdisan)', 'Datasheet': 'https://www.ozdisan.com/p/sabit-induktorler-468/oem-ind-120uh-tht-954101',
                     'Description': 'Inductor fixed radial 120 uH, wire wound, unshielded, D22.5 x 8.25 mm, pitch 9 mm, THT'})
    sh.net('L40', '1', 'LINE_FUSED', 'global', 7.62, shape='passive')
    sh.net('L40', '2', 'LINE_FILT', 'global', 7.62, shape='passive')
    sh.place(('Device', 'C'), 'C40', 110, 85, 0, value='1uF 275VAC X2', footprint='Rev3:C_Rect_L32.0mm_W9.0mm_P27.50mm_X2',
             fields={'MPN': 'C42P2105KBSC400', 'Manufacturer': 'Faratronic', 'Datasheet': 'https://www.ozdisan.com/p/film-kapasitorler-179/faratronic-c42p2105kbsc400-466649',
                     'Description': 'Film capacitor X2 MKP 1 uF 275 VAC +/-10%, 32x18x9 mm, pitch 27.5 mm, -40..+125 C'})
    sh.net('C40', '1', 'LINE_FILT', 'global', 5.08, shape='passive')
    sh.net('C40', '2', 'NEUT', 'power', 2.54)
    return sh

def write_custom_footprints():
    fpdir = os.path.join(LIBDIR, 'Rev3.pretty')
    os.makedirs(fpdir, exist_ok=True)
    def fp_text(kind, txt, x, y, layer):
        return [S('fp_text'), S(kind), txt, [S('at'), num(x), num(y)], [S('layer'), layer], [S('uuid'), U()],
                [S('effects'), [S('font'), [S('size'), num(1), num(1)], [S('thickness'), num(0.15)]]]]
    def pad(n, x, y, size, drill, shape='circle'):
        return [S('pad'), n, S('thru_hole'), S(shape), [S('at'), num(x), num(y)], [S('size'), num(size), num(size)],
                [S('drill'), num(drill)], [S('layers'), '*.Cu', '*.Mask'], [S('uuid'), U()]]
    def circle(r, layer, w):
        return [S('fp_circle'), [S('center'), num(0), num(0)], [S('end'), num(r), num(0)],
                [S('stroke'), [S('width'), num(w)], [S('type'), S('solid')]], [S('fill'), S('none')], [S('layer'), layer], [S('uuid'), U()]]
    def rect(x1, y1, x2, y2, layer, w):
        return [S('fp_rect'), [S('start'), num(x1), num(y1)], [S('end'), num(x2), num(y2)],
                [S('stroke'), [S('width'), num(w)], [S('type'), S('solid')]], [S('fill'), S('none')], [S('layer'), layer], [S('uuid'), U()]]
    def header(name, descr, tags):
        return [S('footprint'), name, [S('version'), num(20240108)], [S('generator'), 'pcbnew'], [S('generator_version'), '8.0'],
                [S('layer'), 'F.Cu'], [S('descr'), descr], [S('tags'), tags], [S('attr'), S('through_hole')]]
    # L40: radial inductor D22.5 mm, pitch 9 mm
    L = header('L_Radial_D22.5mm_P9.00mm', 'Radial inductor D22.5 mm, pitch 9.00 mm (ozdisan IND-120UH-THT); pad/drill sized for 0.8 mm leads',
               'inductor radial choke')
    L += [fp_text('reference', 'REF**', 0, -13.5, 'F.SilkS'), fp_text('value', 'VAL**', 0, 13.5, 'F.Fab'),
          circle(11.25, 'F.SilkS', 0.12), circle(11.25, 'F.Fab', 0.1), circle(11.75, 'F.CrtYd', 0.05),
          pad('1', -4.5, 0, 2.2, 1.2, 'rect'), pad('2', 4.5, 0, 2.2, 1.2)]
    with open(os.path.join(fpdir, 'L_Radial_D22.5mm_P9.00mm.kicad_mod'), 'w', encoding='utf-8') as f:
        f.write(dump(L) + '\n')
    # C40: X2 film box 32 x 9 mm (height 18), pitch 27.5 mm
    C = header('C_Rect_L32.0mm_W9.0mm_P27.50mm_X2', 'Film capacitor box 32 x 9 mm (H 18 mm), pitch 27.5 mm (Faratronic C42P2105KBSC400)',
               'capacitor film X2 MKP')
    C += [fp_text('reference', 'REF**', 0, -6.5, 'F.SilkS'), fp_text('value', 'VAL**', 0, 6.5, 'F.Fab'),
          rect(-16, -4.5, 16, 4.5, 'F.SilkS', 0.12), rect(-16, -4.5, 16, 4.5, 'F.Fab', 0.1), rect(-16.5, -5, 16.5, 5, 'F.CrtYd', 0.05),
          pad('1', -13.75, 0, 2.4, 1.3, 'rect'), pad('2', 13.75, 0, 2.4, 1.3)]
    with open(os.path.join(fpdir, 'C_Rect_L32.0mm_W9.0mm_P27.50mm_X2.kicad_mod'), 'w', encoding='utf-8') as f:
        f.write(dump(C) + '\n')
    # register in the project fp-lib-table
    tbl = os.path.join(PROJ, 'fp-lib-table')
    t = open(tbl, encoding='utf-8').read()
    if '(name "Rev3")' not in t:
        line = '\t(lib (name "Rev3") (type "KiCad") (uri "${KIPRJMOD}/../ComponentsLibrary/User Created/Rev3/Rev3.pretty") (options "") (descr "Rev3.0 custom footprints"))\n'
        t = t.rstrip()
        assert t.endswith(')')
        t = t[:-1] + line + ')\n'
        open(tbl, 'w', encoding='utf-8').write(t)

# ----------------------------------------------------------------------------------
# Root sheet patch
# ----------------------------------------------------------------------------------
def r2(v):
    return round(float(v), 2)

def patch_root(sheets):
    text = open(ROOT_SCH, encoding='utf-8').read()
    root = parse(text)
    libs = {s[1]: s for s in find(first(root, 'lib_symbols'), 'symbol')}
    syms = find(root, 'symbol')
    byref = {prop(s, 'Reference'): s for s in syms}

    # --- connectivity (union-find over wire endpoints) ---
    parent = {}
    def fp(a):
        while parent.setdefault(a, a) != a:
            parent[a] = parent[parent[a]]; a = parent[a]
        return a
    def union(a, b):
        parent[fp(a)] = fp(b)
    wires = find(root, 'wire')
    wseg = []
    for w in wires:
        xy = find(first(w, 'pts'), 'xy')
        a = (r2(xy[0][1]), r2(xy[0][2])); b = (r2(xy[1][1]), r2(xy[1][2]))
        wseg.append((w, a, b)); union(a, b)
    def on_seg(p, a, b):
        (x, y), (x1, y1), (x2, y2) = p, a, b
        if abs((x2 - x1) * (y - y1) - (y2 - y1) * (x - x1)) > 0.05: return False
        return min(x1, x2) - 0.05 <= x <= max(x1, x2) + 0.05 and min(y1, y2) - 0.05 <= y <= max(y1, y2) + 0.05
    def attach(p):
        for w, a, b in wseg:
            if on_seg(p, a, b):
                union(p, a)
    for j in find(root, 'junction'):
        at = first(j, 'at'); attach((r2(at[1]), r2(at[2])))
    lbl_pts = {}
    for l in find(root, 'label'):
        at = first(l, 'at'); p = (r2(at[1]), r2(at[2])); attach(p); lbl_pts[id(l)] = p
    from netlist_sch import lib_pins as lp, transform as tr
    sympins = {}   # ref -> {number: point}
    for s in syms:
        ref = prop(s, 'Reference'); lib = libs[first(s, 'lib_id')[1]]
        d = {}
        for (name, number, px, py, ang, ln) in lp(lib):
            p = tr(px, py, s); attach(p); d[number] = (p, name)
        sympins[ref] = d

    # --- what to remove ---
    # J1/J5 and the old ESP32 SPI stubs: delete whole connectivity components (they contain only those parts).
    # U2 (TLV1117) and C3: delete symbols + wires touching their VI/VO pins only, then prune dangling wires,
    # because their GND/+5V nodes are shared with PS1/C2 which must stay.
    remove_refs = {'J1', 'J5', 'U2', 'C3', '#PWR08'}
    kill_pts = set()
    for ref in ('J1', 'J5'):
        for number, (p, name) in sympins[ref].items():
            kill_pts.add(fp(p))
    touch_pts = {sympins['U2']['2'][0], sympins['U2']['3'][0], sympins['C3']['1'][0], sympins['C3']['2'][0]}
    u3_free = {'IO18', 'IO19', 'IO23', 'IO26', 'IO4', 'IO14', 'IO16', 'IO21'}
    for number, (p, name) in sympins['U3'].items():
        if name in u3_free:
            kill_pts.add(fp(p))
    # power symbols that sit in a killed component
    for s in syms:
        ref = prop(s, 'Reference')
        if ref.startswith('#PWR'):
            for number, (p, name) in sympins[ref].items():
                if fp(p) in kill_pts:
                    remove_refs.add(ref)
    removed = []
    def keep(item):
        if not isinstance(item, list):
            return True
        k = item[0]
        if k == 'symbol' and prop(item, 'Reference') in remove_refs:
            removed.append(('symbol', prop(item, 'Reference'))); return False
        if k == 'wire':
            xy = find(first(item, 'pts'), 'xy'); a = (r2(xy[0][1]), r2(xy[0][2])); b = (r2(xy[1][1]), r2(xy[1][2]))
            if fp(a) in kill_pts or a in touch_pts or b in touch_pts:
                removed.append(('wire', a)); return False
        if k == 'junction':
            at = first(item, 'at'); p = (r2(at[1]), r2(at[2]))
            if fp(p) in kill_pts:
                removed.append(('junction', p)); return False
        if k == 'label':
            if fp(lbl_pts[id(item)]) in kill_pts:
                removed.append(('label', item[1])); return False
        if k == 'text' and item[1] in ('Thermocouple', 'Touch Display', 'CS', 'SCK', 'SO'):
            removed.append(('text', item[1])); return False
        if k == 'rectangle':
            st = first(item, 'start'); en = first(item, 'end')
            x1, y1, x2, y2 = sorted([r2(st[1]), r2(en[1])]) + sorted([r2(st[2]), r2(en[2])])
            for ref in ('J1', 'J5'):
                sx, sy = float(first(byref[ref], 'at')[1]), float(first(byref[ref], 'at')[2])
                if x1 <= sx <= x2 and y1 <= sy <= y2 and (x2 - x1) * (y2 - y1) < 10000:
                    removed.append(('rectangle', (x1, y1, x2, y2))); return False
        return True
    root[:] = [it for it in root if keep(it)]
    print('removed:', removed)
    # --- prune dangling wires / junctions left behind ---
    kept_refs = {prop(s, 'Reference') for s in find(root, 'symbol')}
    anchor_pts = set()
    for ref in kept_refs:
        for number, (p, name) in sympins[ref].items():
            anchor_pts.add(p)
    for l in find(root, 'label') + find(root, 'global_label'):
        at = first(l, 'at'); anchor_pts.add((r2(at[1]), r2(at[2])))
    def segs():
        out = []
        for w in find(root, 'wire'):
            xy = find(first(w, 'pts'), 'xy')
            out.append((w, (r2(xy[0][1]), r2(xy[0][2])), (r2(xy[1][1]), r2(xy[1][2]))))
        return out
    while True:
        ss = segs()
        drop = []
        for w, a, b in ss:
            for p in (a, b):
                ok = p in anchor_pts or any(on_seg(p, a2, b2) for w2, a2, b2 in ss if w2 is not w)
                if not ok:
                    drop.append(w); break
        if not drop:
            break
        for w in drop:
            root.remove(w)
            removed.append(('dangling-wire', w))
    ss = segs()
    for j in find(root, 'junction'):
        at = first(j, 'at'); p = (r2(at[1]), r2(at[2]))
        if not any(on_seg(p, a, b) for w, a, b in ss):
            root.remove(j); removed.append(('junction', p))
    print('pruned:', [x for x in removed if x[0] in ('dangling-wire', 'junction')])
    sym_pos = [(float(first(s, 'at')[1]), float(first(s, 'at')[2])) for s in find(root, 'symbol') if not prop(s, 'Reference').startswith('#')]
    for rc in list(find(root, 'rectangle')):
        st = first(rc, 'start'); en = first(rc, 'end')
        x1, x2 = sorted([float(st[1]), float(en[1])]); y1, y2 = sorted([float(st[2]), float(en[2])])
        if not any(x1 <= sx <= x2 and y1 <= sy <= y2 for sx, sy in sym_pos):
            root.remove(rc); removed.append(('empty-rectangle', (x1, y1, x2, y2)))

    # --- modify PS1 (HLK-PM01 -> HLK-10M05), U3 value ---
    ps1 = byref['PS1']
    first(ps1, 'lib_id')[1] = 'Converter_ACDC:HLK-10M05'
    for p in find(ps1, 'property'):
        if p[1] == 'Value': p[2] = 'HLK-10M05'
        if p[1] == 'Footprint': p[2] = 'Converter_ACDC:Converter_ACDC_Hi-Link_HLK-10Mxx'
        if p[1] == 'Datasheet': p[2] = URLS['HLK-10M05']
        if p[1] == 'Description': p[2] = 'AC/DC module 90-245 VAC -> 5 VDC 2 A (10 W), 3 kV isolation, Hi-Link HLK-10M05'
    def add_prop(sym, name, value):
        idx = max(i for i, it in enumerate(sym) if isinstance(it, list) and it[0] == 'property')
        sym.insert(idx + 1, property_(name, value, float(first(sym, 'at')[1]), float(first(sym, 'at')[2]), 0, hide=True))
    add_prop(ps1, 'MPN', 'HLK-10M05')
    add_prop(ps1, 'Manufacturer', 'Hi-Link')
    libsyms = first(root, 'lib_symbols')
    libsyms.append(get_symbol('Converter_ACDC', 'HLK-10M05'))
    u3 = byref['U3']
    for p in find(u3, 'property'):
        if p[1] == 'Value': p[2] = 'ESP32-WROOM-32E-N16'
        if p[1] == 'Datasheet': p[2] = URLS['ESP32-WROOM-32E-N16']
    add_prop(u3, 'MPN', 'ESP32-WROOM-32E-N16')
    # title block
    tb = first(root, 'title_block')
    for item in tb:
        if isinstance(item, list) and item[0] == 'rev': item[1] = '3.0'
        if isinstance(item, list) and item[0] == 'date': item[1] = DATE

    # --- new ESP32 stubs + global labels ---
    tmp = Sheet('root', ROOT_UUID, '', 1)
    # --- break the LINE wire after fuse F1 for the new input filter sheet ---
    f1p = sympins['F1']['1'][0]
    cut = None
    for w, a, b in wseg:
        if a == f1p or b == f1p:
            cut = (w, b if a == f1p else a)
    assert cut, 'F1 pin 1 wire not found'
    root.remove(cut[0])
    stub = (r2(f1p[0] + 3.81), f1p[1])
    tmp.wire(f1p, stub)
    tmp.label('LINE_FUSED', stub, 1, 0, glob=True, shape='passive')
    tmp.label('LINE_FILT', cut[1], 0, -1, glob=True, shape='passive')
    print('cut F1 wire to', cut[1])
    newmap = {'IO16': 'LCD_D0', 'IO17': 'LCD_D1', 'IO18': 'LCD_D2', 'IO19': 'LCD_D3', 'IO21': 'LCD_D4', 'IO22': 'LCD_D5',
              'IO23': 'LCD_D6', 'IO25': 'LCD_D7', 'IO26': 'LCD_WR', 'IO27': 'LCD_DC', 'IO5': 'LCD_CS', 'IO14': 'LCD_RST',
              'IO4': 'I2C_SDA', 'IO15': 'I2C_SCL', 'IO32': 'TP_INT', 'IO35': 'ADC_RDY'}
    ncs = {'IO2', 'IO12', 'SENSOR_VP', 'SENSOR_VN', 'SHD/SD2', 'SWP/SD3', 'SCS/CMD', 'SCK/CLK', 'SDO/SD0', 'SDI/SD1'}
    # PWR_FLAGs on the mains nets so ERC sees LINE/NEUT (J3) and PS1 AC/L, AC/N as driven
    for k, (ref, number) in enumerate((('J3', '1'), ('J3', '2'), ('PS1', '1'), ('PS1', '2'))):
        p = sympins[ref][number][0]
        tmp.place(('power', 'PWR_FLAG'), f'#FLG00{k + 1}', p[0], p[1], 180 if number == '2' else 0, value='PWR_FLAG')
    for ref, number in (('U1', '6'), ('K1', '4')):       # intentionally unused pins (4N28 base, relay NC contact)
        p = sympins[ref][number][0]
        tmp.items.append([S('no_connect'), [S('at'), num(p[0]), num(p[1])], [S('uuid'), U()]])
    for number, (p, name) in sympins['U3'].items():
        if name in newmap:
            end = (r2(p[0] + 7.62), p[1])
            tmp.wire(p, end)
            shape = 'input' if name in ('IO35',) else ('bidirectional' if name in ('IO4', 'IO32') else 'output')
            tmp.label(newmap[name], end, 1, 0, glob=True, shape=shape)
        elif name in ncs:
            tmp.items.append([S('no_connect'), [S('at'), num(p[0]), num(p[1])], [S('uuid'), U()]])
    # --- sheet symbols ---
    x0 = 232
    for k, sh in enumerate(sheets):
        x = round(round((x0 + k * 45) / 1.27) * 1.27, 2); y = 215.9; w = 38.1; h = 20.32
        tmp.items.append([S('sheet'), [S('at'), num(x), num(y)], [S('size'), num(w), num(h)], [S('exclude_from_sim'), S('no')],
                          [S('in_bom'), S('yes')], [S('on_board'), S('yes')], [S('dnp'), S('no')], [S('fields_autoplaced'), S('yes')],
                          [S('stroke'), [S('width'), num(0.1524)], [S('type'), S('solid')]],
                          [S('fill'), [S('color'), num(0), num(0), num(0), num(0)]], [S('uuid'), sh.uuid],
                          [S('property'), 'Sheetname', sh.title.split(':')[0].replace('Rev3.0 ', ''), [S('at'), num(x), num(y - 0.7), num(0)],
                           [S('show_name'), S('no')], [S('do_not_autoplace'), S('no')], effects(1.27, 'left bottom')],
                          [S('property'), 'Sheetfile', sh.filename, [S('at'), num(x), num(y + h + 0.6), num(0)],
                           [S('show_name'), S('no')], [S('do_not_autoplace'), S('no')], effects(1.27, 'left top')],
                          [S('instances'), [S('project'), PROJECT, [S('path'), f"/{ROOT_UUID}", [S('page'), str(sh.page)]]]]])
    tmp.text("Rev3.0 (2026-11): 7\" RGB TFT via SSD1963 (sheet Display), K-type thermocouple on ADS1115\n"
             "(sheet Thermocouple), 5V->3V3 buck + 1V2 LDO (sheet Power), mains LC filter after F1 (sheet InputFilter).\n"
             "PS1 upgraded to HLK-10M05 (10 W). MAX6675 module and ILI9341 header removed.\n"
             "ESP32 GPIO map: LCD D0-D7 = IO16,17,18,19,21,22,23,25; WR=IO26 DC=IO27 CS=IO5 RST=IO14;\n"
             "I2C SDA=IO4 SCL=IO15; TP_INT=IO32; ADC_RDY=IO35; TRIG=IO33 ZCD=IO34 FAN=IO13.",
             232, 243, 1.6)
    # insert before sheet_instances
    idx = next(i for i, it in enumerate(root) if isinstance(it, list) and it[0] == 'sheet_instances')
    root[idx:idx] = tmp.items
    # merge any lib symbols the tmp sheet used (power symbols already present; global labels need none)
    for name, ls in tmp.libsyms.items():
        if name not in libs:
            libsyms.append(ls)
    out = dump(root) + '\n'
    with open(ROOT_SCH, 'w', encoding='utf-8') as f:
        f.write(out)
    print('root written; U3 new nets:', newmap)

def write_custom_lib():
    os.makedirs(LIBDIR, exist_ok=True)
    lib = [S('kicad_symbol_lib'), [S('version'), num(20241209)], [S('generator'), 'kicad_symbol_editor'], [S('generator_version'), '9.0']]
    for s in CUSTOM.values():
        lib.append(copy.deepcopy(s))
    with open(os.path.join(LIBDIR, 'Rev3.kicad_sym'), 'w', encoding='utf-8') as f:
        f.write(dump(lib) + '\n')
    # project sym-lib-table
    tbl = os.path.join(PROJ, 'sym-lib-table')
    entries = [f'  (lib (name "Rev3") (type "KiCad") (uri "${{KIPRJMOD}}/../ComponentsLibrary/User Created/Rev3/Rev3.kicad_sym") (options "") (descr "Rev3.0 custom symbols"))']
    with open(tbl, 'w', encoding='utf-8') as f:
        f.write('(sym_lib_table\n  (version 7)\n' + '\n'.join(entries) + '\n)\n')

if __name__ == '__main__':
    if os.path.exists(ROOT_SCH + '.rev2.bak'):
        shutil.copy(ROOT_SCH + '.rev2.bak', ROOT_SCH)      # always start from the Rev2.1 root
    else:
        shutil.copy(ROOT_SCH, ROOT_SCH + '.rev2.bak')
    disp = build_display(); th = build_thermo(); pw = build_power(); fl = build_filter()
    for sh in (disp, th, pw, fl):
        sh.write()
        print('wrote', sh.filename, 'items', len(sh.items))
    patch_root([disp, th, pw, fl])
    write_custom_lib()
    write_custom_footprints()
