from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..handler import ActionHandler


def _hex_color(s: str) -> str:
    if not isinstance(s, str):
        raise ValueError("color must be a string")
    v = s.strip()
    if not v.startswith("#"):
        raise ValueError("color must start with #")
    if len(v) != 7:
        raise ValueError("color must be #RRGGBB")
    for c in v[1:]:
        if c.lower() not in "0123456789abcdef":
            raise ValueError("color must be hex")
    return v.lower()


def _preset(theme_id: str) -> Dict[str, Any]:
    presets: Dict[str, Dict[str, Any]] = {
        "standard_corporate_2024": {
            "colors": {
                "primary": "#1f4acc",
                "secondary": "#111827",
                "accent": "#22c55e",
                "background": "#ffffff",
            },
            "fonts": {
                "heading": "Calibri",
                "body": "Calibri",
            },
        }
    }
    if theme_id not in presets:
        raise ValueError("unknown theme_id")
    return presets[theme_id]


class PresentationThemeApplyHandler(ActionHandler):
    def execute(self, params: Dict[str, Any], context: Any) -> Dict[str, Any]:
        self.validate_params(params)

        theme_id = params.get("theme_id")
        if not isinstance(theme_id, str) or not theme_id.strip():
            raise ValueError("theme_id must be a non-empty string")

        preset = _preset(theme_id.strip())
        colors = dict(preset.get("colors") or {})
        fonts = dict(preset.get("fonts") or {})

        custom_colors = params.get("custom_colors")
        if custom_colors is not None:
            if not isinstance(custom_colors, list):
                raise ValueError("custom_colors must be an array")
            if custom_colors:
                colors["primary"] = _hex_color(str(custom_colors[0]))

        font_family = params.get("font_family")
        if font_family is not None:
            if not isinstance(font_family, str) or not font_family.strip():
                raise ValueError("font_family must be a non-empty string")
            fonts["heading"] = font_family.strip()
            fonts["body"] = font_family.strip()

        theme_config = {
            "theme_id": theme_id.strip(),
            "colors": colors,
            "fonts": fonts,
        }
        return {"theme_config": theme_config}
