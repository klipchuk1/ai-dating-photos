"""
Dating photo style catalog.

Each style carries:
  - prompt         : English generation prompt.
                     Every prompt is prefixed with the identity anchor phrase so
                     InstantID has an explicit text signal to lock the face.
  - description    : Russian UI description shown to the user.
  - negative_prompt: Per-style additions merged on top of NEGATIVE_BASE.

NEGATIVE_BASE is always appended — keeps face quality consistent across all styles.
"""

from typing import TypedDict


# ── Identity anchor ────────────────────────────────────────────────────────────
# Inserted at the start of every prompt.
# Reinforces InstantID's ip_adapter conditioning at the text level.
_ID_ANCHOR = "SAME person, same face, identity preserved,"

# ── Shared negative prompt ─────────────────────────────────────────────────────
NEGATIVE_BASE = (
    "different face, distorted face, blurry, low quality, "
    "deformed features, bad anatomy, extra limbs, cloned face, "
    "watermark, text, logo, cropped, out of frame"
)


# ── Style type ─────────────────────────────────────────────────────────────────

class Style(TypedDict):
    id:              str
    name:            str
    description:     str     # Russian
    prompt:          str     # English — identity anchor already included
    negative_prompt: str     # NEGATIVE_BASE + style-specific additions
    preview_url:     str
    style_strength:  float   # InstantID ip_adapter_scale


# ── Helper to build prompt & negative ─────────────────────────────────────────

def _p(core: str, neg_extra: str = "") -> tuple[str, str]:
    """Return (prompt, negative_prompt) with anchor and base injected."""
    prompt = f"{_ID_ANCHOR} {core}"
    neg    = f"{NEGATIVE_BASE}, {neg_extra}" if neg_extra else NEGATIVE_BASE
    return prompt, neg


# ── Style catalog ──────────────────────────────────────────────────────────────

_urban_prompt, _urban_neg = _p(
    "professional dating photo, urban street background, "
    "casual modern outfit, relaxed confident pose, "
    "soft natural daylight, shallow depth of field, "
    "35mm lens, photorealistic, lifestyle photography",
)

_cafe_prompt, _cafe_neg = _p(
    "lifestyle portrait in a cozy cafe, warm ambient window light, "
    "coffee cup on table, casual relaxed smile, "
    "bokeh interior background, 50mm lens, photorealistic",
)

_business_prompt, _business_neg = _p(
    "confident business professional portrait, modern office or city backdrop, "
    "smart business casual attire, strong assured expression, "
    "clean directional studio light, 85mm lens, editorial quality",
    "tie, suit, overly formal, stiff pose",
)

_fitness_prompt, _fitness_neg = _p(
    "athletic lifestyle photo, gym or outdoor training background, "
    "sportswear, energetic confident pose, dynamic natural light, "
    "sharp detail, photorealistic, fitness magazine quality",
    "overweight, unhealthy, out of shape",
)

_travel_prompt, _travel_neg = _p(
    "travel lifestyle portrait, exotic location backdrop — "
    "mountains, beach, or European street, "
    "casual holiday outfit, natural happy expression, "
    "golden hour light, 35mm lens, photorealistic",
)

_night_prompt, _night_neg = _p(
    "cinematic nighttime dating portrait, city street with neon bokeh, "
    "warm rim light, mysterious yet approachable expression, "
    "85mm f/1.4 lens, photorealistic, atmospheric",
    "dark, underexposed, scary",
)

_luxury_prompt, _luxury_neg = _p(
    "premium luxury lifestyle portrait, upscale hotel terrace or rooftop, "
    "elegant understated outfit, confident relaxed posture, "
    "professional fashion photography, soft golden backlight, "
    "medium format look, photorealistic",
    "cheap, tacky, overly flashy",
)

_friendly_prompt, _friendly_neg = _p(
    "warm friendly portrait, bright natural outdoor light, "
    "genuine open smile, approachable relaxed pose, "
    "clean simple background with soft bokeh, "
    "50mm lens, photorealistic, dating profile quality",
)

_minimal_prompt, _minimal_neg = _p(
    "clean minimal studio portrait, pure white or light grey background, "
    "professional three-point lighting, natural confident expression, "
    "sharp crisp detail, 85mm lens, photorealistic",
    "cluttered background, shadows, vignette",
)

_cinematic_prompt, _cinematic_neg = _p(
    "cinematic wide-format portrait, dramatic directional light, "
    "moody colour grade — warm teal-orange, "
    "film grain texture, confident composed expression, "
    "anamorphic lens bokeh, photorealistic, movie still quality",
    "overexposed, flat lighting, generic",
)


STYLES: dict[str, Style] = {
    "urban_casual": {
        "id":             "urban_casual",
        "name":           "Urban Casual",
        "description":    "Городская улица, естественный свет, расслабленный образ",
        "prompt":         _urban_prompt,
        "negative_prompt": _urban_neg,
        "preview_url":    "/previews/urban_casual.jpg",
        "style_strength": 0.75,
    },
    "cafe_lifestyle": {
        "id":             "cafe_lifestyle",
        "name":           "Café Lifestyle",
        "description":    "Уютное кафе, тёплый свет, атмосферный lifestyle",
        "prompt":         _cafe_prompt,
        "negative_prompt": _cafe_neg,
        "preview_url":    "/previews/cafe_lifestyle.jpg",
        "style_strength": 0.72,
    },
    "business_alpha": {
        "id":             "business_alpha",
        "name":           "Business Alpha",
        "description":    "Деловой стиль, уверенность, современный офис",
        "prompt":         _business_prompt,
        "negative_prompt": _business_neg,
        "preview_url":    "/previews/business_alpha.jpg",
        "style_strength": 0.70,
    },
    "fitness_athletic": {
        "id":             "fitness_athletic",
        "name":           "Fitness Athletic",
        "description":    "Спортивный образ, энергия, активный стиль жизни",
        "prompt":         _fitness_prompt,
        "negative_prompt": _fitness_neg,
        "preview_url":    "/previews/fitness_athletic.jpg",
        "style_strength": 0.74,
    },
    "travel_vacation": {
        "id":             "travel_vacation",
        "name":           "Travel Vacation",
        "description":    "Путешествие, экзотика, закатный свет на природе",
        "prompt":         _travel_prompt,
        "negative_prompt": _travel_neg,
        "preview_url":    "/previews/travel_vacation.jpg",
        "style_strength": 0.73,
    },
    "night_city": {
        "id":             "night_city",
        "name":           "Night City Dating",
        "description":    "Ночной город, неоновые огни, кинематографичная атмосфера",
        "prompt":         _night_prompt,
        "negative_prompt": _night_neg,
        "preview_url":    "/previews/night_city.jpg",
        "style_strength": 0.78,
    },
    "premium_luxury": {
        "id":             "premium_luxury",
        "name":           "Premium Luxury",
        "description":    "Премиальный образ, роскошный интерьер, высокий класс",
        "prompt":         _luxury_prompt,
        "negative_prompt": _luxury_neg,
        "preview_url":    "/previews/premium_luxury.jpg",
        "style_strength": 0.76,
    },
    "friendly_portrait": {
        "id":             "friendly_portrait",
        "name":           "Friendly Portrait",
        "description":    "Тёплый открытый портрет, искренняя улыбка, простой фон",
        "prompt":         _friendly_prompt,
        "negative_prompt": _friendly_neg,
        "preview_url":    "/previews/friendly_portrait.jpg",
        "style_strength": 0.70,
    },
    "minimal_clean": {
        "id":             "minimal_clean",
        "name":           "Minimal Clean",
        "description":    "Студийный свет, белый фон, чёткость и чистота",
        "prompt":         _minimal_prompt,
        "negative_prompt": _minimal_neg,
        "preview_url":    "/previews/minimal_clean.jpg",
        "style_strength": 0.68,
    },
    "cinematic": {
        "id":             "cinematic",
        "name":           "Cinematic",
        "description":    "Кинематографичный кадр, драматический свет, teal-orange грейдинг",
        "prompt":         _cinematic_prompt,
        "negative_prompt": _cinematic_neg,
        "preview_url":    "/previews/cinematic.jpg",
        "style_strength": 0.77,
    },
}


# ── Public API ─────────────────────────────────────────────────────────────────

def get_styles() -> list[Style]:
    """Return all styles as a list (UI-facing)."""
    return list(STYLES.values())


def get_prompt(style_id: str) -> tuple[str, str]:
    """
    Return (prompt, negative_prompt) for the given style_id.
    Raises KeyError for unknown IDs.
    """
    style = STYLES[style_id]
    return style["prompt"], style["negative_prompt"]
