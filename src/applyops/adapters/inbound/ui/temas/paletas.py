"""Paletas de los temas: cuatro copiadas de Jaime (`theme.py`, `skins_op.py`,
`skins_equipo.py`) y la Cian del portafolio (`Portafolio-Frontend-React/src/themes/palettes.js`).

Mismo set de 15 tokens que en Jaime, para que la piel portada funcione sin
cambios. Las etiquetas siguen el formato único del selector de Jaime:
«<emoji> <Nombre> · <color> · <Personaje>».

Refactor: Nicolás Cano Leal / Fecha: 2026-11-25
"""

from __future__ import annotations

TOKENS = (
    "bg", "surface", "surface2", "sidebar", "border", "accent", "accent2", "text",
    "text_dim", "text_mute", "success", "warning", "error", "console_bg", "console_txt",
)  # fmt: skip

PALETAS: dict[str, dict[str, str]] = {
    # Mugiwara: negro de casco, dorado del sombrero de paja, rojo de la cinta.
    "mugiwara": {
        "bg": "#0A0806", "surface": "#171310", "surface2": "#241C14",
        "sidebar": "#0B0907", "border": "#4A3A1E", "accent": "#F5C542",
        "accent2": "#E2382D", "text": "#F4F0E6", "text_dim": "#C3B698",
        "text_mute": "#8A7D66", "success": "#3FD07E", "warning": "#F5A524",
        "error": "#E2382D", "console_bg": "#080604", "console_txt": "#E0D3B0",
    },
    # Gear 5: el blanco de Nika, el rojo del sombrero y el dorado de la libertad.
    "luffy_g5": {
        "bg": "#120A0A", "surface": "#1E1212", "surface2": "#2B1A18",
        "sidebar": "#0E0808", "border": "#4A2320", "accent": "#F5F0E6",
        "accent2": "#E23B2E", "text": "#F7F2EA", "text_dim": "#C9B7AE",
        "text_mute": "#8C766E", "success": "#3FD07E", "warning": "#F5C542",
        "error": "#E23B2E", "console_bg": "#0A0606", "console_txt": "#EDE2D6",
    },
    # Zoro: el verde de su pelo y su haramaki.
    "esmeralda": {
        "bg": "#0A1410", "surface": "#10201A", "surface2": "#163026",
        "sidebar": "#081210", "border": "#21402F", "accent": "#10B981",
        "accent2": "#34D399", "text": "#E6F2EC", "text_dim": "#93B5A5",
        "text_mute": "#6B8578", "success": "#34D399", "warning": "#F5B942",
        "error": "#F87171", "console_bg": "#06110D", "console_txt": "#C6E0D3",
    },
    # Shingeki: el verde de los ojos del titán y el ámbar del rayo, sobre un negro
    # verdoso (el vapor). Subido de contraste en Jaime tras verlo en pantalla.
    "eren": {
        "bg": "#0A0F0C", "surface": "#131C18", "surface2": "#1F2C26",
        "sidebar": "#070C0A", "border": "#38503F", "accent": "#4FF0B0",
        "accent2": "#F2AE33", "text": "#F0F8F3", "text_dim": "#B3CCC0",
        "text_mute": "#83A395", "success": "#4FF0B0", "warning": "#F2AE33",
        "error": "#E8564A", "console_bg": "#060B08", "console_txt": "#D6EBDF",
    },
    # Cian: el tema por defecto del portafolio (fondo azul noche, acento cian e índigo).
    # Valores de `palettes.js`; sidebar, text_mute y consola derivados (el portafolio no los tiene).
    "cian": {
        "bg": "#070B14", "surface": "#0D1424", "surface2": "#121B31",
        "sidebar": "#060912", "border": "#1F2B47", "accent": "#22D3EE",
        "accent2": "#818CF8", "text": "#E6EDF7", "text_dim": "#8B9BB8",
        "text_mute": "#5F6F8C", "success": "#34D399", "warning": "#FBBF24",
        "error": "#F87171", "console_bg": "#050811", "console_txt": "#C7D2FE",
    },
}  # fmt: skip

ETIQUETAS: dict[str, str] = {
    "mugiwara": "🏴‍☠️ Mugiwara · dorado · Luffy",
    "luffy_g5": "🌞 Gear 5 · blanco · Luffy",
    "esmeralda": "⚔️ Esmeralda · verde · Zoro",
    "eren": "⚡ Shingeki · verde titán · Eren",
    "cian": "💠 Cian · cian e índigo · Portafolio",
}

TEMA_POR_DEFECTO = "eren"
