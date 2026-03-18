<!-- Shared product classification rules. Included by both batch decomposition and agent prompts. -->

CRITICAL DISTINCTION — specifications vs. selling units:

- SPECIFICATIONS are physical attributes that describe WHAT the product IS:
  - "3/8 in. Compression x 1/2 in. FIP x 16 in." → connection sizes and length of a faucet supply line. Sold EACH.
  - "16 in. x 16 in." on a towel → towel dimensions. NOT a selling unit.
  - "12/2" on Romex wire → wire gauge and conductor count. NOT a selling unit.
  - "2x4x8" on lumber → cross-section and length. The "8" IS a pack_qty in feet.
  - "3/4 in." on a pipe fitting → pipe diameter. Sold EACH.

- SELLING UNITS describe HOW the product is bought/sold:
  - "(24-Pack)" → pack of 24, base_unit=pack, pack_qty=24
  - "5 Gal" on paint → base_unit=gallon, pack_qty=5
  - "100ft" on wire/pipe → base_unit=foot, pack_qty=100
  - "80lb" on concrete → base_unit=pound, pack_qty=80
  - "$6.97 / each" → confirms base_unit=each
  - "$9.98 / bag" → confirms base_unit=bag

HOW TO DECIDE base_unit:
1. Look for explicit price-per-unit indicators: "/ each", "/ bag", "/ foot", "/ gallon"
2. If the product has an embedded selling quantity (24-Pack, 5 Gal, 100ft), that determines the unit
3. Apply category rules:
   - Discrete items (fittings, valves, fixtures, detectors, tools): each
   - Multi-packs of discrete items: pack (with pack_qty = count)
   - Linear goods (pipe, wire, cable, lumber, conduit, trim): foot
   - Liquids (paint, stain, primer, sealer): gallon (or quart/pint for smaller)
   - Fasteners (screws, nails, bolts) sold in containers: box
   - Sheet goods (drywall, plywood): sheet or sqft
   - Bulk materials (concrete, mortar, soil): bag or pound
   - Tape, mesh, fabric on a roll: roll
4. When in doubt, "each" is the safest default for discrete items

DEPARTMENT CODES:
PLU=plumbing, ELE=electrical, PNT=paint, LUM=lumber, TOL=tools, HDW=hardware/general, GDN=garden, APP=appliances

Department classification:
- Faucet supply lines, valves, pipe, fittings, drains, toilets → PLU
- Smoke/CO detectors, wire, cable, outlets, switches, breakers → ELE
- Paint, stain, primer, caulk, brushes, rollers, prep/cleanup → PNT
- Lumber, plywood, drywall, studs, trim, moulding, doors → LUM
- Drills, saws, bits, blades, hand tools → TOL
- Screws, nails, bolts, anchors, hinges, brackets, towels, cleaning → HDW
- Garden, plants, soil, hoses → GDN
- Furnaces, ranges, hoods, HVAC → APP

VARIANT IDENTIFICATION:
Products that differ only in one specification are variants of the same family:
- "BrassCraft ... x 16 in. Braided Polymer Faucet Supply Line" and "BrassCraft ... x 20 in." → same family, variant_label is the length
- "Kidde Code One Hardwired..." and "Kidde Code One AA Battery..." → same family, variant is power source

Set variant_label to the distinguishing attribute (e.g. "16 in", "20 in", "Hardwired", "AA Battery").
Set variant_attrs to ALL specification key-value pairs that characterize this specific variant.

NAME CLEANING:
- Remove discount text ("DISCOUNT $4.01 OFF EACH", "PREFERRED PRICING...")
- Remove delivery info ("Delivered by Feb 19 - Feb 23")
- Remove store/location info
- Keep brand, material, type, and key specs in the clean_name
- clean_name should read naturally: "Braided Polymer Faucet Supply Line" not "B1-16A F FAUCET SUPPLY"

ORIGINAL_SKU EXTRACTION:
- Look for model numbers (e.g. "B1-16A F", "900-CUAR", "2142099")
- Look for vendor SKU numbers (e.g. "405140", "1008622056")
- Prefer the vendor's model number over store SKU numbers
- Set to null if no vendor part number is visible

CONFIDENCE:
Rate 0.0 to 1.0 how confident you are in the overall classification:
- 0.9+ : clear product with explicit UOM indicators
- 0.7-0.9 : reasonable inference from category/context
- 0.5-0.7 : ambiguous, multiple interpretations possible
- <0.5 : very unclear, likely needs human review
