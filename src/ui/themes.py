"""
themes.py — Visual styles, colors, and typography for MaxPlus AI (Gemini Grey & White edition).
"""

# Gemini Grey Palette (Modern Neutral Graphite / Dark Slate)
DARK: dict[str, str] = dict(
    bg="#1e1f20",            # Gemini background (charcoal grey)
    bg2="#282a2c",           # Faint muted surface (composer & cards)
    bg3="#333538",           # Elevated surface / button hover
    bg_user="#282a2c",       # User message card
    bg_ai="#232426",         # Gemini AI message blog card
    bg_btn="#333538",        # Flat button background
    bg_err="#371f23",        # Error card background
    border="#3c4043",        # Subtle Gemini card border
    accent="#8ab4f8",        # Gemini Sparkle Blue
    accent_hover="#a8c7fa",  # Light blue hover
    fg="#e3e3e3",            # Primary readable text
    fg_dim="#9aa0a6",        # Secondary / placeholder text
    user_hdr="#8ab4f8",      # User badge color
    ai_hdr="#8ab4f8",        # Gemini badge color
    err_hdr="#f28b82",       # Soft red error
    img_clr="#fdd663",       # Image indicator amber
    tab_sel="#2d2f31",       # Selected tab
    tab_bg="#18191a",        # Tab bar background
    composer_bg="#282a2c",   # Input box: faint grey, opaque
    code_bg="#161718",       # Code block dark background
    code_fg="#d1d7e0",       # Code text
    quote_fg="#8ab4f8",      # Blockquote highlight
)

# Gemini White Palette (Clean Pure White & Ice Grey)
LIGHT: dict[str, str] = dict(
    bg="#ffffff",            # Pure clean white background
    bg2="#f0f4f9",           # Soft faint surface (Gemini signature light grey)
    bg3="#e1e5ea",           # Elevated / hover surface
    bg_user="#f0f4f9",       # User prompt pill/card
    bg_ai="#ffffff",         # AI message card with clean border
    bg_btn="#e8eaed",        # Flat button background
    bg_err="#fce8e6",        # Soft red error card
    border="#dadce0",        # Google clean border
    accent="#1a73e8",        # Gemini Royal Blue
    accent_hover="#1557b0",  # Deeper blue hover
    fg="#1f1f1f",            # Crisp dark text
    fg_dim="#5f6368",        # Secondary / placeholder text
    user_hdr="#1a73e8",      # User badge color
    ai_hdr="#1a73e8",        # Gemini badge color
    err_hdr="#d93025",       # Error red
    img_clr="#e37400",       # Image indicator amber
    tab_sel="#e8eaed",       # Selected tab
    tab_bg="#f1f3f4",        # Tab bar background
    composer_bg="#f0f4f9",   # Input box: faint soft grey, opaque
    code_bg="#f6f8fa",       # Code block light background
    code_fg="#24292f",       # Code text
    quote_fg="#1a73e8",      # Blockquote highlight
)

# Aliases for clarity
GREY = DARK
WHITE = LIGHT

# Active theme mutable reference
T: dict[str, str] = dict(DARK)

# Typography (Gemini Style)
FONT = ("Segoe UI", 11)
FONT_BOLD = ("Segoe UI", 11, "bold")
FONT_MONO = ("Consolas", 10)
FONT_TINY = ("Segoe UI", 9)
FONT_HDR = ("Segoe UI", 13, "bold")
FONT_TITLE = ("Segoe UI Semibold", 16)

# Blog & Markdown Typography
FONT_H1 = ("Segoe UI Semibold", 14, "bold")
FONT_H2 = ("Segoe UI Semibold", 12, "bold")
FONT_H3 = ("Segoe UI Semibold", 11, "bold")
FONT_CODE_INLINE = ("Consolas", 10)
FONT_QUOTE = ("Segoe UI", 10, "italic")
