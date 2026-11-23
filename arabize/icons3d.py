"""Layered 3D icon tiles, built as plain SVG so the desktop app and the website draw the same icons.

Each tile is stacked from seven layers, back to front:
  1 shadow on the ground     2 extruded side of the tile   3 tile face (gradient)
  4 gloss on the upper half  5 rim light                   6 extruded glyph (two dark copies, offset down)
  7 glyph face (light gradient)
Only SVG Tiny features are used (no filters), so Qt's SVG renderer draws it exactly like a browser.
Glyph outlines come from Lucide (ISC licence).
"""
from __future__ import annotations

HUES = {
    #          light      mid        dark       side
    "gold":   ("#FFE7B0", "#E7B964", "#A8701F", "#6B4310"),
    "cyan":   ("#B8F6FF", "#41C7E0", "#147C9C", "#0A4A60"),
    "violet": ("#E2CCFF", "#9B6BF2", "#5A2FC0", "#371A7A"),
    "emerald": ("#BFF7DA", "#3FCF8E", "#16875A", "#0B5236"),
    "coral":  ("#FFD0BF", "#FF8466", "#C8462B", "#7E2714"),
    "rose":   ("#FFC9EB", "#F062B8", "#A8287A", "#66124A"),
    "blue":   ("#C8DAFF", "#5C8BFF", "#2A50C8", "#16307E"),
    "slate":  ("#E6E9F5", "#8F98BE", "#4E5679", "#2C3250"),
}

GLYPHS = {
    "pad": '<line x1="6" x2="10" y1="11" y2="11"/><line x1="8" x2="8" y1="9" y2="13"/><line x1="15" x2="15.01" y1="12" y2="12"/><line x1="18" x2="18.01" y1="10" y2="10"/><path d="M17.32 5H6.68a4 4 0 0 0-3.978 3.59c-.006.052-.01.101-.017.152C2.604 9.416 2 14.456 2 16a3 3 0 0 0 3 3c1 0 1.5-.5 2-1l1.414-1.414A2 2 0 0 1 9.828 16h4.344a2 2 0 0 1 1.414.586L17 18c.5.5 1 1 2 1a3 3 0 0 0 3-3c0-1.545-.604-6.584-.685-7.258-.007-.05-.011-.1-.017-.151A4 4 0 0 0 17.32 5z"/>',
    "home": '<path d="M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8"/><path d="M3 10a2 2 0 0 1 .709-1.528l7-5.999a2 2 0 0 1 2.582 0l7 5.999A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    "monitor": '<rect width="20" height="14" x="2" y="3" rx="2"/><line x1="8" x2="16" y1="21" y2="21"/><line x1="12" x2="12" y1="17" y2="21"/>',
    "palette": '<circle cx="13.5" cy="6.5" r=".5"/><circle cx="17.5" cy="10.5" r=".5"/><circle cx="8.5" cy="7.5" r=".5"/><circle cx="6.5" cy="12.5" r=".5"/><path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.926 0 1.648-.746 1.648-1.688 0-.437-.18-.835-.437-1.125-.29-.289-.438-.652-.438-1.125a1.64 1.64 0 0 1 1.668-1.668h1.996c3.051 0 5.555-2.503 5.555-5.554C21.965 6.012 17.461 2 12 2z"/>',
    "lang": '<path d="m5 8 6 6"/><path d="m4 14 6-6 2-3"/><path d="M2 5h12"/><path d="M7 2h1"/><path d="m22 22-5-10-5 10"/><path d="M14 18h6"/>',
    "games": '<line x1="6" x2="10" y1="12" y2="12"/><line x1="8" x2="8" y1="10" y2="14"/><line x1="15" x2="15.01" y1="13" y2="13"/><line x1="18" x2="18.01" y1="11" y2="11"/><rect width="20" height="12" x="2" y="6" rx="2"/>',
    "hist": '<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l4 2"/>',
    "keyboard": '<path d="M10 8h.01"/><path d="M12 12h.01"/><path d="M14 8h.01"/><path d="M16 12h.01"/><path d="M18 8h.01"/><path d="M6 8h.01"/><path d="M7 16h10"/><path d="M8 12h.01"/><rect width="20" height="16" x="2" y="4" rx="2"/>',
    "help": '<circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><path d="M12 17h.01"/>',
    "scan": '<path d="M3 7V5a2 2 0 0 1 2-2h2"/><path d="M17 3h2a2 2 0 0 1 2 2v2"/><path d="M21 17v2a2 2 0 0 1-2 2h-2"/><path d="M7 21H5a2 2 0 0 1-2-2v-2"/><path d="M7 8h8"/><path d="M7 12h10"/><path d="M7 16h6"/>',
    "vr": '<circle cx="6" cy="15" r="4"/><circle cx="18" cy="15" r="4"/><path d="M14 15a2 2 0 0 0-2-2 2 2 0 0 0-2 2"/><path d="M2.5 13 5 7c.7-1.3 1.4-2 3-2"/><path d="M21.5 13 19 7c-.7-1.3-1.5-2-3-2"/>',
    "layers": '<path d="M12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83z"/><path d="m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65"/><path d="m22 12.65-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65"/>',
    "wand": '<path d="m21.64 3.64-1.28-1.28a1.21 1.21 0 0 0-1.72 0L2.36 18.64a1.21 1.21 0 0 0 0 1.72l1.28 1.28a1.2 1.2 0 0 0 1.72 0L21.64 5.36a1.2 1.2 0 0 0 0-1.72"/><path d="m14 7 3 3"/><path d="M5 6v4"/><path d="M19 14v4"/><path d="M10 2v2"/><path d="M7 8H3"/><path d="M21 16h-4"/><path d="M11 3H9"/>',
    "template": '<rect width="18" height="7" x="3" y="3" rx="1"/><rect width="9" height="7" x="3" y="14" rx="1"/><rect width="5" height="7" x="16" y="14" rx="1"/>',
    "type": '<polyline points="4 7 4 4 20 4 20 7"/><line x1="9" x2="15" y1="20" y2="20"/><line x1="12" x2="12" y1="4" y2="20"/>',
    "chat": '<path d="M7.9 20A9 9 0 1 0 4 16.1L2 22Z"/>',
    "flag": '<path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" x2="4" y1="22" y2="15"/>',
    "list": '<path d="M3 12h.01"/><path d="M3 18h.01"/><path d="M3 6h.01"/><path d="M8 12h13"/><path d="M8 18h13"/><path d="M8 6h13"/>',
    "info": '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
    "tv": '<rect width="20" height="15" x="2" y="7" rx="2" ry="2"/><polyline points="17 2 12 7 7 2"/>',
    "download": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" x2="12" y1="15" y2="3"/>',
    "power": '<path d="M12 2v10"/><path d="M18.4 6.6a9 9 0 1 1-12.77.04"/>',
    "zap": '<path d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z"/>',
    "book": '<path d="M12 7v14"/><path d="M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3z"/>',
    "sliders": '<line x1="21" x2="14" y1="4" y2="4"/><line x1="10" x2="3" y1="4" y2="4"/><line x1="21" x2="12" y1="12" y2="12"/><line x1="8" x2="3" y1="12" y2="12"/><line x1="21" x2="16" y1="20" y2="20"/><line x1="12" x2="3" y1="20" y2="20"/><line x1="14" x2="14" y1="2" y2="6"/><line x1="8" x2="8" y1="10" y2="14"/><line x1="16" x2="16" y1="18" y2="22"/>',
    "text": '<path d="M17 6.1H3"/><path d="M21 12.1H3"/><path d="M15.1 18H3"/>',
    "image": '<rect width="18" height="18" x="3" y="3" rx="2" ry="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.086-3.086a2 2 0 0 0-2.828 0L6 21"/>',
}


def tile_svg(name: str, hue: str = "gold", uid: str = "", size: int | None = None) -> str:
    """A 48x48 3D icon tile. uid keeps gradient ids unique when many tiles share one web page."""
    lt, mid, dk, side = HUES.get(hue, HUES["gold"])
    g = GLYPHS[name]
    u = f"{uid or name}-{hue}"
    dims = f' width="{size}" height="{size}"' if size else ""
    glyph_t = 'transform="translate(10.5 9) scale(1.125)"'
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"{dims} aria-hidden="true">'
        f'<defs>'
        f'<linearGradient id="f{u}" x1="0" y1="0" x2="0.35" y2="1"><stop offset="0" stop-color="{lt}"/>'
        f'<stop offset="0.55" stop-color="{mid}"/><stop offset="1" stop-color="{dk}"/></linearGradient>'
        f'<linearGradient id="s{u}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#FFFFFF" stop-opacity="0.55"/>'
        f'<stop offset="1" stop-color="#FFFFFF" stop-opacity="0"/></linearGradient>'
        f'<linearGradient id="g{u}" gradientUnits="userSpaceOnUse" x1="0" y1="3" x2="0" y2="21"><stop offset="0" stop-color="#FFFFFF"/>'
        f'<stop offset="1" stop-color="{lt}"/></linearGradient>'
        f'</defs>'
        # 1 shadow on the ground
        f'<ellipse cx="24" cy="44.2" rx="16" ry="2.6" fill="#000000" fill-opacity="0.38"/>'
        # 2 extruded side
        f'<rect x="5" y="7.5" width="38" height="35" rx="11" fill="{side}"/>'
        # 3 face
        f'<rect x="5" y="4" width="38" height="35" rx="11" fill="url(#f{u})"/>'
        # 4 gloss
        f'<path d="M16 4.6h16a10.4 10.4 0 0 1 10.4 10.4v1.6C36 19.6 12 19.6 5.6 16.6V15A10.4 10.4 0 0 1 16 4.6z" fill="url(#s{u})"/>'
        # 5 rim light
        f'<rect x="5.6" y="4.6" width="36.8" height="33.8" rx="10.4" fill="none" stroke="#FFFFFF" stroke-opacity="0.45" stroke-width="0.9"/>'
        # 6 extruded glyph
        f'<g fill="none" stroke="{side}" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" stroke-opacity="0.85">'
        f'<g transform="translate(0 1.9)"><g {glyph_t}>{g}</g></g>'
        f'<g transform="translate(0 1.0)"><g {glyph_t}>{g}</g></g></g>'
        # 7 glyph face
        f'<g fill="none" stroke="url(#g{u})" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round">'
        f'<g {glyph_t}>{g}</g></g>'
        f'</svg>'
    )
