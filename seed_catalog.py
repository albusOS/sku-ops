"""Seed product families and SKUs for 6 departments via the API."""

import requests

BASE = "http://localhost:8000/api/beta"

# Login
r = requests.post(f"{BASE}/shared/auth/login", json={"email": "admin@supplyyard.com", "password": "SupplyYard2026!"})
r.raise_for_status()
TOKEN = r.json()["token"]
H = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

# Department IDs
DEPS = {
    "ELEC": "763270ed-59f6-4314-9bbc-bc11af08f6a8",
    "HVAC": "84a1e52e-c04a-447d-b791-3c8bf272c117",
    "HDWR": "20d813fe-4d15-4f6f-88c4-2fe590d01175",
    "DOOR": "63aa2bd6-0009-4703-a0e5-1fd405476464",
    "FLOOR": "d7dce12b-bf2c-44d4-b94a-d7d62130f85b",
    "JANIT": "70e4bdfb-7de4-450f-b767-ee81826d56f5",
}

def create_family(name, dept_code, description=""):
    r = requests.post(f"{BASE}/catalog/products", headers=H, json={
        "name": name, "category_id": DEPS[dept_code], "description": description
    })
    r.raise_for_status()
    fid = r.json()["id"]
    print(f"  Family: {name} → {fid}")
    return fid

def create_sku(family_id, dept_code, sku):
    r = requests.post(f"{BASE}/catalog/products/{family_id}/skus", headers=H, json=sku)
    r.raise_for_status()
    code = r.json().get("sku_code", "?")
    print(f"    SKU: {sku['name']} → {code}")
    return code

errors = 0

def safe_sku(family_id, dept_code, sku):
    global errors
    try:
        return create_sku(family_id, dept_code, sku)
    except Exception as e:
        errors += 1
        print(f"    ERROR: {sku['name']}: {e}")
        return None

# ═══════════════════════════════════════════════════════════════════════
# ELECTRICAL
# ═══════════════════════════════════════════════════════════════════════
print("\n═══ ELECTRICAL ═══")

fid = create_family("Outlet", "ELEC", "Standard and GFCI outlets")
for amp, typ, color in [
    ("15A", "Standard", "white"), ("15A", "Standard", "almond"),
    ("20A", "Standard", "white"), ("15A", "GFCI", "white"),
    ("20A", "GFCI", "white"), ("20A", "GFCI", "almond"),
]:
    safe_sku(fid, "ELEC", {
        "name": f"{typ} Outlet {amp} {color.title()}",
        "price": 1.29 if typ == "Standard" else 14.99 if amp == "15A" else 18.99,
        "cost": 0.45 if typ == "Standard" else 7.50 if amp == "15A" else 9.50,
        "category_id": DEPS["ELEC"],
        "base_unit": "each",
        "variant_label": f"{typ} / {amp} / {color}",
        "variant_attrs": {"type": typ, "amperage": amp, "color": color},
    })

fid = create_family("Light Switch", "ELEC", "Toggle and rocker switches")
for gang, typ, color in [
    (1, "Toggle", "white"), (1, "Toggle", "almond"), (1, "Rocker", "white"),
    (2, "Rocker", "white"), (3, "Rocker", "white"), (1, "Dimmer", "white"),
]:
    safe_sku(fid, "ELEC", {
        "name": f"{typ} Switch {gang}-Gang {color.title()}",
        "price": 1.49 if typ == "Toggle" else 3.99 if typ == "Rocker" else 12.99,
        "cost": 0.55 if typ == "Toggle" else 1.50 if typ == "Rocker" else 6.50,
        "category_id": DEPS["ELEC"],
        "base_unit": "each",
        "variant_label": f"{typ} / {gang}-gang / {color}",
        "variant_attrs": {"type": typ, "gang_size": gang, "color": color},
    })

fid = create_family("Breaker", "ELEC", "Circuit breakers")
for amp, poles in [("15A", 1), ("20A", 1), ("30A", 2), ("50A", 2)]:
    safe_sku(fid, "ELEC", {
        "name": f"Breaker {amp} {poles}P",
        "price": 6.99 if poles == 1 else 14.99 if amp == "30A" else 24.99,
        "cost": 3.50 if poles == 1 else 7.50 if amp == "30A" else 12.50,
        "category_id": DEPS["ELEC"],
        "base_unit": "each",
        "variant_label": f"{amp} / {poles}-pole",
        "variant_attrs": {"amperage": amp, "poles": poles},
    })

fid = create_family("Light Fixture", "ELEC", "Ceiling and wall fixtures")
for typ, finish in [
    ("Flush Mount 12in", "white"), ("Flush Mount 12in", "brushed nickel"),
    ("Vanity Bar 24in", "chrome"), ("Vanity Bar 36in", "brushed nickel"),
    ("Utility Shop Light 4ft", "white"),
]:
    prices = {"Flush Mount 12in": (19.99, 10.00), "Vanity Bar 24in": (29.99, 15.00),
              "Vanity Bar 36in": (39.99, 20.00), "Utility Shop Light 4ft": (24.99, 12.50)}
    p, c = prices[typ]
    safe_sku(fid, "ELEC", {
        "name": f"{typ} {finish.title()}",
        "price": p, "cost": c,
        "category_id": DEPS["ELEC"],
        "base_unit": "each",
        "variant_label": f"{typ} / {finish}",
        "variant_attrs": {"type": typ, "finish": finish},
    })

fid = create_family("Bulb", "ELEC", "LED and specialty bulbs")
for bulb_type, watt, lumens in [
    ("A19", "9W", "800lm"), ("A19", "13W", "1100lm"),
    ("BR30", "9W", "650lm"), ("BR30", "11W", "850lm"),
    ("PAR38", "15W", "1200lm"),
]:
    safe_sku(fid, "ELEC", {
        "name": f"LED {bulb_type} {watt} {lumens}",
        "price": 3.99 if "A19" in bulb_type else 5.99 if "BR30" in bulb_type else 8.99,
        "cost": 1.50 if "A19" in bulb_type else 2.50 if "BR30" in bulb_type else 4.50,
        "category_id": DEPS["ELEC"],
        "base_unit": "each",
        "sell_uom": "pack",
        "purchase_uom": "case",
        "purchase_pack_qty": 24,
        "variant_label": f"{bulb_type} / {watt}",
        "variant_attrs": {"bulb_type": bulb_type, "wattage": watt, "lumens": lumens},
    })

fid = create_family("Junction Box", "ELEC")
for typ, size in [("Metal 4x4", "4in"), ("Metal 4x4 Deep", "4in"), ("PVC Single Gang", "1-gang"), ("PVC Double Gang", "2-gang")]:
    safe_sku(fid, "ELEC", {
        "name": f"Junction Box {typ}",
        "price": 1.99 if "PVC" in typ else 3.49,
        "cost": 0.80 if "PVC" in typ else 1.50,
        "category_id": DEPS["ELEC"],
        "base_unit": "each",
        "variant_label": typ,
        "variant_attrs": {"type": typ, "size": size},
    })

fid = create_family("Wire", "ELEC", "Romex and THHN wire")
for gauge, typ, length in [
    ("14/2", "Romex NM-B", "250ft"), ("12/2", "Romex NM-B", "250ft"),
    ("10/2", "Romex NM-B", "100ft"), ("14AWG", "THHN Solid", "500ft"),
    ("12AWG", "THHN Solid", "500ft"),
]:
    prices = {"14/2": (54.99, 32.00), "12/2": (74.99, 44.00), "10/2": (49.99, 28.00),
              "14AWG": (39.99, 22.00), "12AWG": (54.99, 30.00)}
    p, c = prices[gauge]
    safe_sku(fid, "ELEC", {
        "name": f"{typ} {gauge} {length}",
        "price": p, "cost": c,
        "category_id": DEPS["ELEC"],
        "base_unit": "roll",
        "variant_label": f"{gauge} / {length}",
        "variant_attrs": {"gauge": gauge, "type": typ, "length": length},
    })

fid = create_family("Smoke Detector", "ELEC")
for typ in ["Battery 10-Year Sealed", "Hardwired w/ Battery Backup", "Combination Smoke/CO"]:
    p = 24.99 if "Battery" in typ else 29.99 if "Hardwired" in typ else 34.99
    safe_sku(fid, "ELEC", {
        "name": f"Smoke Detector {typ}",
        "price": p, "cost": p * 0.5,
        "category_id": DEPS["ELEC"],
        "base_unit": "each",
        "variant_label": typ,
        "variant_attrs": {"type": typ},
    })

fid = create_family("Carbon Monoxide Detector", "ELEC")
for typ in ["Plug-In Digital Display", "Battery 10-Year"]:
    safe_sku(fid, "ELEC", {
        "name": f"CO Detector {typ}",
        "price": 29.99 if "Plug" in typ else 24.99,
        "cost": 15.00 if "Plug" in typ else 12.50,
        "category_id": DEPS["ELEC"],
        "base_unit": "each",
        "variant_label": typ,
        "variant_attrs": {"type": typ},
    })

fid = create_family("Doorbell", "ELEC")
for typ in ["Wired Chime Kit", "Wireless Kit", "Doorbell Button Only"]:
    safe_sku(fid, "ELEC", {
        "name": f"Doorbell {typ}",
        "price": 19.99 if "Wired" in typ else 29.99 if "Wireless" in typ else 4.99,
        "cost": 10.00 if "Wired" in typ else 15.00 if "Wireless" in typ else 2.00,
        "category_id": DEPS["ELEC"],
        "base_unit": "each",
        "variant_label": typ,
        "variant_attrs": {"type": typ},
    })

fid = create_family("Cover Plate", "ELEC", "Switch and outlet cover plates")
for gang, typ, color in [
    (1, "Toggle", "white"), (1, "Duplex", "white"), (1, "Duplex", "almond"),
    (2, "Toggle", "white"), (1, "Blank", "white"), (1, "Decorator/Rocker", "white"),
]:
    safe_sku(fid, "ELEC", {
        "name": f"Cover Plate {typ} {gang}-Gang {color.title()}",
        "price": 0.79 if gang == 1 else 1.29,
        "cost": 0.25 if gang == 1 else 0.45,
        "category_id": DEPS["ELEC"],
        "base_unit": "each",
        "variant_label": f"{typ} / {gang}-gang / {color}",
        "variant_attrs": {"type": typ, "gang_size": gang, "color": color},
    })

# ═══════════════════════════════════════════════════════════════════════
# HVAC
# ═══════════════════════════════════════════════════════════════════════
print("\n═══ HVAC ═══")

fid = create_family("Air Filter", "HVAC", "Standard and high-efficiency HVAC filters")
for size, merv in [
    ("16x20x1", "MERV 8"), ("16x25x1", "MERV 8"), ("20x20x1", "MERV 8"),
    ("20x25x1", "MERV 8"), ("16x20x1", "MERV 11"), ("16x25x1", "MERV 11"),
    ("20x25x1", "MERV 13"),
]:
    p = 5.99 if "8" in merv else 9.99 if "11" in merv else 14.99
    safe_sku(fid, "HVAC", {
        "name": f"Air Filter {size} {merv}",
        "price": p, "cost": p * 0.45,
        "category_id": DEPS["HVAC"],
        "base_unit": "each",
        "sell_uom": "each",
        "purchase_uom": "case",
        "purchase_pack_qty": 12,
        "variant_label": f"{size} / {merv}",
        "variant_attrs": {"size": size, "merv_rating": merv},
    })

fid = create_family("Thermostat", "HVAC")
for typ in ["Non-Programmable", "Programmable 5-2 Day", "Programmable 7-Day", "Smart Wi-Fi"]:
    prices = {"Non-Programmable": (19.99, 10.00), "Programmable 5-2 Day": (29.99, 15.00),
              "Programmable 7-Day": (39.99, 20.00), "Smart Wi-Fi": (129.99, 65.00)}
    p, c = prices[typ]
    safe_sku(fid, "HVAC", {
        "name": f"Thermostat {typ}",
        "price": p, "cost": c,
        "category_id": DEPS["HVAC"],
        "base_unit": "each",
        "variant_label": typ,
        "variant_attrs": {"type": typ},
    })

fid = create_family("Vent Cover / Register", "HVAC")
for size, typ in [
    ("4x10", "Floor"), ("4x12", "Floor"), ("6x10", "Floor"),
    ("6x12", "Floor"), ("8x4", "Ceiling"), ("12x6", "Ceiling"),
]:
    safe_sku(fid, "HVAC", {
        "name": f"Register {typ} {size} White",
        "price": 5.99 if typ == "Floor" else 7.99,
        "cost": 2.50 if typ == "Floor" else 3.50,
        "category_id": DEPS["HVAC"],
        "base_unit": "each",
        "variant_label": f"{typ} / {size}",
        "variant_attrs": {"size": size, "type": typ, "color": "white"},
    })

fid = create_family("Capacitor", "HVAC", "Run and start capacitors")
for uf, voltage in [("5 MFD", "370V"), ("10 MFD", "370V"), ("25 MFD", "440V"),
                     ("35 MFD", "440V"), ("45 MFD", "440V")]:
    safe_sku(fid, "HVAC", {
        "name": f"Capacitor {uf} {voltage}",
        "price": 9.99 if "5" in uf or "10" in uf else 14.99,
        "cost": 4.50 if "5" in uf or "10" in uf else 7.00,
        "category_id": DEPS["HVAC"],
        "base_unit": "each",
        "variant_label": f"{uf} / {voltage}",
        "variant_attrs": {"capacitance": uf, "voltage": voltage},
    })

fid = create_family("Contactor", "HVAC")
for amp, poles in [("24V 30A", 1), ("24V 30A", 2), ("24V 40A", 2)]:
    safe_sku(fid, "HVAC", {
        "name": f"Contactor {amp} {poles}P",
        "price": 14.99 if poles == 1 else 19.99,
        "cost": 7.00 if poles == 1 else 10.00,
        "category_id": DEPS["HVAC"],
        "base_unit": "each",
        "variant_label": f"{amp} / {poles}-pole",
        "variant_attrs": {"rating": amp, "poles": poles},
    })

fid = create_family("Condensate Pump", "HVAC")
safe_sku(fid, "HVAC", {
    "name": "Condensate Pump 1/30 HP",
    "price": 49.99, "cost": 25.00,
    "category_id": DEPS["HVAC"],
    "base_unit": "each",
    "variant_label": "1/30 HP",
    "variant_attrs": {"hp": "1/30"},
})

fid = create_family("HVAC Tape / Sealant", "HVAC")
for typ in ["Foil Tape 2.5in x 60yd", "Duct Sealant 1qt", "Mastic Tape 2in x 100ft"]:
    safe_sku(fid, "HVAC", {
        "name": typ,
        "price": 7.99 if "Foil" in typ else 9.99 if "Sealant" in typ else 12.99,
        "cost": 3.50 if "Foil" in typ else 4.50 if "Sealant" in typ else 6.00,
        "category_id": DEPS["HVAC"],
        "base_unit": "each",
        "variant_label": typ,
        "variant_attrs": {"type": typ},
    })

# ═══════════════════════════════════════════════════════════════════════
# HARDWARE
# ═══════════════════════════════════════════════════════════════════════
print("\n═══ HARDWARE ═══")

fid = create_family("Screws", "HDWR")
for size, head, material in [
    ("#8 x 1-1/4in", "Phillips", "zinc"), ("#8 x 2in", "Phillips", "zinc"),
    ("#8 x 3in", "Phillips", "zinc"), ("#10 x 2in", "Phillips", "zinc"),
    ("#10 x 3in", "Phillips", "zinc"), ("#8 x 1-5/8in", "Phillips", "stainless"),
    ("#8 x 2-1/2in", "Star/Torx", "zinc"),
]:
    safe_sku(fid, "HDWR", {
        "name": f"Screw {head} {size} {material.title()}",
        "price": 8.99 if material == "zinc" else 12.99,
        "cost": 4.00 if material == "zinc" else 6.00,
        "category_id": DEPS["HDWR"],
        "base_unit": "lb",
        "sell_uom": "lb",
        "purchase_uom": "box",
        "purchase_pack_qty": 25,
        "variant_label": f"{size} / {head} / {material}",
        "variant_attrs": {"size": size, "head": head, "material": material},
    })

fid = create_family("Nails", "HDWR")
for typ, size in [
    ("Common", "8d 2-1/2in"), ("Common", "16d 3-1/2in"),
    ("Finish", "6d 2in"), ("Finish", "8d 2-1/2in"),
    ("Roofing", "1-1/4in"),
]:
    safe_sku(fid, "HDWR", {
        "name": f"{typ} Nail {size}",
        "price": 6.99,
        "cost": 3.00,
        "category_id": DEPS["HDWR"],
        "base_unit": "lb",
        "sell_uom": "lb",
        "purchase_uom": "box",
        "purchase_pack_qty": 50,
        "variant_label": f"{typ} / {size}",
        "variant_attrs": {"type": typ, "size": size},
    })

fid = create_family("Anchors", "HDWR")
for typ, rating in [
    ("Drywall Plastic", "50lb"), ("Drywall Self-Drill", "75lb"),
    ("Toggle Bolt 1/4in", "150lb"), ("Concrete Wedge 3/8in", "200lb"),
]:
    safe_sku(fid, "HDWR", {
        "name": f"Anchor {typ} {rating}",
        "price": 4.99 if "Plastic" in typ else 6.99 if "Self" in typ else 8.99,
        "cost": 2.00 if "Plastic" in typ else 3.00 if "Self" in typ else 4.50,
        "category_id": DEPS["HDWR"],
        "base_unit": "pack",
        "variant_label": f"{typ} / {rating}",
        "variant_attrs": {"type": typ, "weight_rating": rating},
    })

fid = create_family("Bolts", "HDWR")
for size, material in [
    ("1/4-20 x 2in", "zinc"), ("5/16-18 x 2in", "zinc"),
    ("3/8-16 x 3in", "zinc"), ("1/4-20 x 2in", "stainless"),
]:
    safe_sku(fid, "HDWR", {
        "name": f"Hex Bolt {size} {material.title()}",
        "price": 0.49 if material == "zinc" else 0.89,
        "cost": 0.18 if material == "zinc" else 0.35,
        "category_id": DEPS["HDWR"],
        "base_unit": "each",
        "variant_label": f"{size} / {material}",
        "variant_attrs": {"size": size, "material": material},
    })

fid = create_family("Washers", "HDWR")
for size, material in [("1/4in", "zinc"), ("5/16in", "zinc"), ("3/8in", "zinc"), ("1/4in", "stainless")]:
    safe_sku(fid, "HDWR", {
        "name": f"Flat Washer {size} {material.title()}",
        "price": 3.99, "cost": 1.50,
        "category_id": DEPS["HDWR"],
        "base_unit": "pack",
        "variant_label": f"{size} / {material}",
        "variant_attrs": {"size": size, "material": material},
    })

fid = create_family("Nuts", "HDWR")
for size, material in [("1/4-20", "zinc"), ("5/16-18", "zinc"), ("3/8-16", "zinc")]:
    safe_sku(fid, "HDWR", {
        "name": f"Hex Nut {size} {material.title()}",
        "price": 2.99, "cost": 1.00,
        "category_id": DEPS["HDWR"],
        "base_unit": "pack",
        "variant_label": f"{size} / {material}",
        "variant_attrs": {"size": size, "material": material},
    })

fid = create_family("Brackets", "HDWR")
for typ, size in [("L-Bracket", "2in"), ("L-Bracket", "4in"), ("Corner Brace", "3in"), ("T-Plate", "6in")]:
    safe_sku(fid, "HDWR", {
        "name": f"{typ} {size} Zinc",
        "price": 1.99 if "2" in size else 2.99 if "3" in size or "4" in size else 4.99,
        "cost": 0.80 if "2" in size else 1.20 if "3" in size or "4" in size else 2.00,
        "category_id": DEPS["HDWR"],
        "base_unit": "each",
        "variant_label": f"{typ} / {size}",
        "variant_attrs": {"type": typ, "size": size, "material": "zinc"},
    })

fid = create_family("Hooks", "HDWR")
for typ in ["Utility Hook Large", "Pegboard Hook 6in", "S-Hook 2in", "Cup Hook Brass"]:
    safe_sku(fid, "HDWR", {
        "name": typ,
        "price": 2.49 if "Utility" in typ else 1.49,
        "cost": 1.00 if "Utility" in typ else 0.50,
        "category_id": DEPS["HDWR"],
        "base_unit": "each" if "Utility" in typ else "pack",
        "variant_label": typ,
        "variant_attrs": {"type": typ},
    })

fid = create_family("Chains", "HDWR")
for typ, size in [("Zinc Plated", "#2 / 125lb"), ("Zinc Plated", "#3 / 240lb"), ("Stainless", "#2 / 125lb")]:
    safe_sku(fid, "HDWR", {
        "name": f"Chain {typ} {size}",
        "price": 1.99 if "Zinc" in typ else 3.49,
        "cost": 0.90 if "Zinc" in typ else 1.60,
        "category_id": DEPS["HDWR"],
        "base_unit": "ft",
        "sell_uom": "ft",
        "purchase_uom": "roll",
        "purchase_pack_qty": 100,
        "variant_label": f"{typ} / {size}",
        "variant_attrs": {"type": typ, "size": size},
    })

fid = create_family("Fastener Kits", "HDWR")
for typ in ["Screw Assortment 200pc", "Bolt & Nut Kit 150pc", "Drywall Anchor Kit 100pc"]:
    safe_sku(fid, "HDWR", {
        "name": typ,
        "price": 14.99 if "200" in typ else 12.99,
        "cost": 6.00 if "200" in typ else 5.50,
        "category_id": DEPS["HDWR"],
        "base_unit": "kit",
        "variant_label": typ,
        "variant_attrs": {"type": typ},
    })

# ═══════════════════════════════════════════════════════════════════════
# DOORS & LOCKS
# ═══════════════════════════════════════════════════════════════════════
print("\n═══ DOORS & LOCKS ═══")

fid = create_family("Door Slab", "DOOR", "Interior hollow-core and solid-core door slabs")
for core, width in [
    ("Hollow Core", "24in"), ("Hollow Core", "28in"), ("Hollow Core", "30in"),
    ("Hollow Core", "32in"), ("Solid Core", "30in"), ("Solid Core", "32in"),
]:
    p = 39.99 if core == "Hollow Core" else 79.99
    safe_sku(fid, "DOOR", {
        "name": f"Door Slab {core} {width} x 80in",
        "price": p, "cost": p * 0.5,
        "category_id": DEPS["DOOR"],
        "base_unit": "each",
        "variant_label": f"{core} / {width}",
        "variant_attrs": {"core": core, "width": width, "height": "80in"},
    })

fid = create_family("Prehung Door", "DOOR")
for typ, width in [
    ("Interior Hollow", "30in"), ("Interior Hollow", "32in"),
    ("Interior Solid", "30in"), ("Exterior Steel", "36in"),
]:
    prices = {"Interior Hollow": (89.99, 45.00), "Interior Solid": (149.99, 75.00),
              "Exterior Steel": (249.99, 125.00)}
    p, c = prices[typ]
    safe_sku(fid, "DOOR", {
        "name": f"Prehung {typ} {width} x 80in",
        "price": p, "cost": c,
        "category_id": DEPS["DOOR"],
        "base_unit": "each",
        "variant_label": f"{typ} / {width}",
        "variant_attrs": {"type": typ, "width": width},
    })

fid = create_family("Hinges", "DOOR")
for size, finish in [("3.5in", "satin nickel"), ("3.5in", "oil-rubbed bronze"),
                      ("4in", "satin nickel"), ("4in", "oil-rubbed bronze")]:
    safe_sku(fid, "DOOR", {
        "name": f"Door Hinge {size} {finish.title()}",
        "price": 3.99 if size == "3.5in" else 4.99,
        "cost": 1.50 if size == "3.5in" else 2.00,
        "category_id": DEPS["DOOR"],
        "base_unit": "each",
        "sell_uom": "pair",
        "variant_label": f"{size} / {finish}",
        "variant_attrs": {"size": size, "finish": finish},
    })

fid = create_family("Deadbolt", "DOOR")
for typ, finish in [("Single Cylinder", "satin nickel"), ("Single Cylinder", "oil-rubbed bronze"),
                     ("Double Cylinder", "satin nickel")]:
    safe_sku(fid, "DOOR", {
        "name": f"Deadbolt {typ} {finish.title()}",
        "price": 24.99 if "Single" in typ else 34.99,
        "cost": 12.00 if "Single" in typ else 17.00,
        "category_id": DEPS["DOOR"],
        "base_unit": "each",
        "variant_label": f"{typ} / {finish}",
        "variant_attrs": {"type": typ, "finish": finish},
    })

fid = create_family("Knob / Lever", "DOOR")
for typ, finish, grade in [
    ("Passage Knob", "satin nickel", "interior"), ("Privacy Knob", "satin nickel", "interior"),
    ("Entry Lever", "satin nickel", "exterior"), ("Entry Lever", "oil-rubbed bronze", "exterior"),
]:
    safe_sku(fid, "DOOR", {
        "name": f"{typ} {finish.title()} {grade.title()}",
        "price": 12.99 if "Passage" in typ else 14.99 if "Privacy" in typ else 29.99,
        "cost": 6.00 if "Passage" in typ else 7.00 if "Privacy" in typ else 15.00,
        "category_id": DEPS["DOOR"],
        "base_unit": "each",
        "variant_label": f"{typ} / {finish} / {grade}",
        "variant_attrs": {"type": typ, "finish": finish, "grade": grade},
    })

fid = create_family("Strike Plate", "DOOR")
for finish in ["satin nickel", "oil-rubbed bronze"]:
    safe_sku(fid, "DOOR", {
        "name": f"Strike Plate {finish.title()}",
        "price": 2.99, "cost": 1.00,
        "category_id": DEPS["DOOR"],
        "base_unit": "each",
        "variant_label": finish,
        "variant_attrs": {"finish": finish},
    })

fid = create_family("Door Stop", "DOOR")
for typ in ["Wall Mount White", "Hinge Pin Satin Nickel", "Floor Mount Chrome"]:
    safe_sku(fid, "DOOR", {
        "name": f"Door Stop {typ}",
        "price": 2.49 if "Wall" in typ else 3.49,
        "cost": 1.00 if "Wall" in typ else 1.50,
        "category_id": DEPS["DOOR"],
        "base_unit": "each",
        "variant_label": typ,
        "variant_attrs": {"type": typ},
    })

fid = create_family("Door Sweep", "DOOR")
for typ in ["Aluminum 36in", "Vinyl U-Shape 36in"]:
    safe_sku(fid, "DOOR", {
        "name": f"Door Sweep {typ}",
        "price": 9.99 if "Aluminum" in typ else 6.99,
        "cost": 4.50 if "Aluminum" in typ else 3.00,
        "category_id": DEPS["DOOR"],
        "base_unit": "each",
        "variant_label": typ,
        "variant_attrs": {"type": typ},
    })

fid = create_family("Weatherstripping", "DOOR")
for typ in ["V-Strip Bronze 17ft", "Foam Tape 3/8in x 17ft", "Door Bottom Seal 36in"]:
    safe_sku(fid, "DOOR", {
        "name": f"Weatherstripping {typ}",
        "price": 5.99 if "Foam" in typ else 8.99,
        "cost": 2.50 if "Foam" in typ else 4.00,
        "category_id": DEPS["DOOR"],
        "base_unit": "each",
        "variant_label": typ,
        "variant_attrs": {"type": typ},
    })

fid = create_family("Door Closer", "DOOR")
for typ in ["Residential Pneumatic", "Commercial Grade 3", "Storm Door Closer"]:
    safe_sku(fid, "DOOR", {
        "name": f"Door Closer {typ}",
        "price": 19.99 if "Residential" in typ else 49.99 if "Commercial" in typ else 12.99,
        "cost": 10.00 if "Residential" in typ else 25.00 if "Commercial" in typ else 6.00,
        "category_id": DEPS["DOOR"],
        "base_unit": "each",
        "variant_label": typ,
        "variant_attrs": {"type": typ},
    })

# ═══════════════════════════════════════════════════════════════════════
# FLOORING
# ═══════════════════════════════════════════════════════════════════════
print("\n═══ FLOORING ═══")

fid = create_family("LVP / Vinyl Plank", "FLOOR")
for color, thickness, wear in [
    ("Classic Oak", "5mm", "20mil"), ("Weathered Gray", "5mm", "20mil"),
    ("Hickory Natural", "6mm", "22mil"), ("Dark Walnut", "6mm", "22mil"),
    ("Whitewash Pine", "5mm", "12mil"),
]:
    p = 2.49 if thickness == "5mm" and "12" in wear else 2.99 if thickness == "5mm" else 3.49
    safe_sku(fid, "FLOOR", {
        "name": f"LVP {color} {thickness} {wear}",
        "price": p, "cost": p * 0.45,
        "category_id": DEPS["FLOOR"],
        "base_unit": "sqft",
        "sell_uom": "box",
        "purchase_uom": "pallet",
        "purchase_pack_qty": 60,
        "variant_label": f"{color} / {thickness}",
        "variant_attrs": {"color": color, "thickness": thickness, "wear_layer": wear, "box_coverage": "23.6 sqft"},
    })

fid = create_family("Laminate Flooring", "FLOOR")
for color, thickness in [("Honey Oak", "8mm"), ("Gray Ash", "10mm"), ("Espresso", "10mm")]:
    p = 1.79 if thickness == "8mm" else 2.29
    safe_sku(fid, "FLOOR", {
        "name": f"Laminate {color} {thickness}",
        "price": p, "cost": p * 0.45,
        "category_id": DEPS["FLOOR"],
        "base_unit": "sqft",
        "sell_uom": "box",
        "purchase_uom": "pallet",
        "purchase_pack_qty": 60,
        "variant_label": f"{color} / {thickness}",
        "variant_attrs": {"color": color, "thickness": thickness, "box_coverage": "21.3 sqft"},
    })

fid = create_family("Carpet", "FLOOR")
for color, pile in [("Beige", "Plush"), ("Gray", "Plush"), ("Brown", "Berber")]:
    safe_sku(fid, "FLOOR", {
        "name": f"Carpet {pile} {color}",
        "price": 1.49, "cost": 0.65,
        "category_id": DEPS["FLOOR"],
        "base_unit": "sqft",
        "sell_uom": "sqyd",
        "variant_label": f"{color} / {pile}",
        "variant_attrs": {"color": color, "pile": pile},
    })

fid = create_family("Tile", "FLOOR")
for typ, size, color in [
    ("Ceramic", "12x12", "White"), ("Ceramic", "12x12", "Beige"),
    ("Porcelain", "12x24", "Gray"), ("Porcelain", "12x24", "White"),
]:
    p = 1.29 if typ == "Ceramic" else 2.49
    safe_sku(fid, "FLOOR", {
        "name": f"Tile {typ} {size} {color}",
        "price": p, "cost": p * 0.4,
        "category_id": DEPS["FLOOR"],
        "base_unit": "sqft",
        "sell_uom": "box",
        "purchase_uom": "pallet",
        "purchase_pack_qty": 50,
        "variant_label": f"{typ} / {size} / {color}",
        "variant_attrs": {"type": typ, "size": size, "color": color},
    })

fid = create_family("Underlayment", "FLOOR")
for typ in ["Standard Foam 2mm 100sqft", "Premium Foam 3mm 100sqft", "Moisture Barrier 6mil 100sqft"]:
    safe_sku(fid, "FLOOR", {
        "name": f"Underlayment {typ}",
        "price": 24.99 if "Standard" in typ else 39.99 if "Premium" in typ else 19.99,
        "cost": 12.00 if "Standard" in typ else 18.00 if "Premium" in typ else 9.00,
        "category_id": DEPS["FLOOR"],
        "base_unit": "roll",
        "variant_label": typ,
        "variant_attrs": {"type": typ},
    })

fid = create_family("Transition Strip", "FLOOR")
for typ, finish in [("T-Molding", "oak"), ("Reducer", "oak"), ("Threshold", "aluminum")]:
    safe_sku(fid, "FLOOR", {
        "name": f"Transition {typ} 36in {finish.title()}",
        "price": 9.99 if "aluminum" in finish else 12.99,
        "cost": 4.50 if "aluminum" in finish else 6.00,
        "category_id": DEPS["FLOOR"],
        "base_unit": "each",
        "variant_label": f"{typ} / {finish}",
        "variant_attrs": {"type": typ, "finish": finish, "length": "36in"},
    })

fid = create_family("Baseboard / Trim", "FLOOR")
for style, height in [("Colonial", "3-1/4in"), ("Ranch", "2-1/4in"), ("Modern Flat", "3-1/2in")]:
    safe_sku(fid, "FLOOR", {
        "name": f"Baseboard {style} {height} Primed 8ft",
        "price": 4.99 if "2" in height else 6.99,
        "cost": 2.00 if "2" in height else 3.00,
        "category_id": DEPS["FLOOR"],
        "base_unit": "each",
        "variant_label": f"{style} / {height}",
        "variant_attrs": {"style": style, "height": height, "length": "8ft", "material": "MDF primed"},
    })

fid = create_family("Adhesive", "FLOOR")
for typ in ["Vinyl Flooring Adhesive 1gal", "Tile Thinset 25lb", "Carpet Seam Tape 15ft"]:
    safe_sku(fid, "FLOOR", {
        "name": typ,
        "price": 24.99 if "Adhesive" in typ else 12.99 if "Thinset" in typ else 8.99,
        "cost": 12.00 if "Adhesive" in typ else 6.00 if "Thinset" in typ else 4.00,
        "category_id": DEPS["FLOOR"],
        "base_unit": "each",
        "variant_label": typ,
        "variant_attrs": {"type": typ},
    })

# ═══════════════════════════════════════════════════════════════════════
# JANITORIAL / CLEANING
# ═══════════════════════════════════════════════════════════════════════
print("\n═══ JANITORIAL / CLEANING ═══")

fid = create_family("All-Purpose Cleaner", "JANIT")
for size, scent in [("32oz Spray", "Lemon"), ("32oz Spray", "Lavender"), ("1gal Concentrate", "Unscented")]:
    safe_sku(fid, "JANIT", {
        "name": f"All-Purpose Cleaner {size} {scent}",
        "price": 4.99 if "32oz" in size else 12.99,
        "cost": 2.00 if "32oz" in size else 5.50,
        "category_id": DEPS["JANIT"],
        "base_unit": "each",
        "variant_label": f"{size} / {scent}",
        "variant_attrs": {"size": size, "scent": scent},
    })

fid = create_family("Disinfectant", "JANIT")
for size, typ in [("32oz Spray", "Hospital Grade"), ("1gal Concentrate", "Hospital Grade"),
                   ("Wipes 75ct", "Surface")]:
    safe_sku(fid, "JANIT", {
        "name": f"Disinfectant {typ} {size}",
        "price": 5.99 if "32oz" in size else 14.99 if "1gal" in size else 6.99,
        "cost": 2.50 if "32oz" in size else 6.50 if "1gal" in size else 3.00,
        "category_id": DEPS["JANIT"],
        "base_unit": "each",
        "variant_label": f"{typ} / {size}",
        "variant_attrs": {"type": typ, "size": size},
    })

fid = create_family("Degreaser", "JANIT")
for size, strength in [("32oz Spray", "Standard"), ("1gal", "Industrial")]:
    safe_sku(fid, "JANIT", {
        "name": f"Degreaser {strength} {size}",
        "price": 5.99 if "32oz" in size else 16.99,
        "cost": 2.50 if "32oz" in size else 7.50,
        "category_id": DEPS["JANIT"],
        "base_unit": "each",
        "variant_label": f"{strength} / {size}",
        "variant_attrs": {"strength": strength, "size": size},
    })

fid = create_family("Glass Cleaner", "JANIT")
for size in ["32oz Spray", "1gal Refill"]:
    safe_sku(fid, "JANIT", {
        "name": f"Glass Cleaner {size}",
        "price": 3.99 if "32oz" in size else 9.99,
        "cost": 1.50 if "32oz" in size else 4.00,
        "category_id": DEPS["JANIT"],
        "base_unit": "each",
        "variant_label": size,
        "variant_attrs": {"size": size},
    })

fid = create_family("Mop", "JANIT")
for typ in ["Wet Mop Cotton 24oz", "Wet Mop Microfiber", "Dust Mop 36in"]:
    safe_sku(fid, "JANIT", {
        "name": typ,
        "price": 9.99 if "Cotton" in typ else 14.99 if "Microfiber" in typ else 19.99,
        "cost": 4.50 if "Cotton" in typ else 7.00 if "Microfiber" in typ else 9.50,
        "category_id": DEPS["JANIT"],
        "base_unit": "each",
        "variant_label": typ,
        "variant_attrs": {"type": typ},
    })

fid = create_family("Broom", "JANIT")
for typ in ["Push Broom 24in", "Angle Broom Indoor", "Corn Broom Heavy Duty"]:
    safe_sku(fid, "JANIT", {
        "name": typ,
        "price": 14.99 if "Push" in typ else 8.99,
        "cost": 7.00 if "Push" in typ else 4.00,
        "category_id": DEPS["JANIT"],
        "base_unit": "each",
        "variant_label": typ,
        "variant_attrs": {"type": typ},
    })

fid = create_family("Trash Bags", "JANIT")
for size, strength in [("13gal Kitchen", "Standard 50ct"), ("33gal", "Standard 40ct"),
                        ("55gal Contractor", "Heavy Duty 20ct")]:
    safe_sku(fid, "JANIT", {
        "name": f"Trash Bags {size} {strength}",
        "price": 9.99 if "13" in size else 12.99 if "33" in size else 14.99,
        "cost": 4.50 if "13" in size else 5.50 if "33" in size else 6.50,
        "category_id": DEPS["JANIT"],
        "base_unit": "box",
        "variant_label": f"{size} / {strength}",
        "variant_attrs": {"size": size, "strength": strength},
    })

fid = create_family("Paper Towels", "JANIT")
for typ in ["Standard Roll 6-Pack", "Jumbo Roll 6-Pack", "Center-Pull 6-Pack"]:
    safe_sku(fid, "JANIT", {
        "name": f"Paper Towels {typ}",
        "price": 8.99 if "Standard" in typ else 12.99 if "Jumbo" in typ else 24.99,
        "cost": 4.00 if "Standard" in typ else 6.00 if "Jumbo" in typ else 11.00,
        "category_id": DEPS["JANIT"],
        "base_unit": "pack",
        "variant_label": typ,
        "variant_attrs": {"type": typ},
    })

fid = create_family("Toilet Paper", "JANIT")
for typ in ["Standard 2-Ply 12-Pack", "Jumbo Roll Commercial 8-Pack"]:
    safe_sku(fid, "JANIT", {
        "name": f"Toilet Paper {typ}",
        "price": 9.99 if "Standard" in typ else 19.99,
        "cost": 4.50 if "Standard" in typ else 9.00,
        "category_id": DEPS["JANIT"],
        "base_unit": "pack",
        "variant_label": typ,
        "variant_attrs": {"type": typ},
    })

fid = create_family("Sponges", "JANIT")
for typ in ["Cellulose 6-Pack", "Heavy Duty Scrub 3-Pack"]:
    safe_sku(fid, "JANIT", {
        "name": f"Sponges {typ}",
        "price": 4.99 if "Cellulose" in typ else 5.99,
        "cost": 2.00 if "Cellulose" in typ else 2.50,
        "category_id": DEPS["JANIT"],
        "base_unit": "pack",
        "variant_label": typ,
        "variant_attrs": {"type": typ},
    })

fid = create_family("Gloves", "JANIT")
for typ, size in [("Nitrile Disposable", "M 100ct"), ("Nitrile Disposable", "L 100ct"),
                   ("Nitrile Disposable", "XL 100ct"), ("Rubber Reusable", "L")]:
    safe_sku(fid, "JANIT", {
        "name": f"Gloves {typ} {size}",
        "price": 12.99 if "Disposable" in typ else 4.99,
        "cost": 5.50 if "Disposable" in typ else 2.00,
        "category_id": DEPS["JANIT"],
        "base_unit": "box" if "Disposable" in typ else "pair",
        "variant_label": f"{typ} / {size}",
        "variant_attrs": {"type": typ, "size": size},
    })

# ═══════════════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════════════
print(f"\n{'═'*50}")
print(f"Done. Errors: {errors}")
