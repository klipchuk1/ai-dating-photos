"""
Catalog of photo styles for dating.
Each style has a carefully tuned prompt that preserves identity.
The face is controlled by InstantID — prompt drives only environment/lighting/mood.
"""

STYLES: dict = {
    "outdoor_golden": {
        "id": "outdoor_golden",
        "name": "Золотой час",
        "description": "Улица, теплый закатный свет, живые цвета",
        "preview_url": "/previews/outdoor_golden.jpg",
        "prompt": (
            "professional dating photo, warm golden hour sunlight, "
            "outdoor urban background, shallow depth of field, "
            "natural bokeh, candid smile, high-end photography, "
            "35mm lens, sharp focus on face, warm tones"
        ),
        "negative_prompt": (
            "deformed face, distorted features, bad anatomy, "
            "ugly, blurry face, multiple people, cartoon, anime, "
            "painted, illustration, low quality, watermark"
        ),
        "style_strength": 0.75,
    },
    "cafe_vibes": {
        "id": "cafe_vibes",
        "name": "Кофе в кафе",
        "description": "Уютная кофейня, мягкий свет, lifestyle",
        "preview_url": "/previews/cafe_vibes.jpg",
        "prompt": (
            "professional lifestyle photo, cozy cafe interior, "
            "soft window light, coffee cup, warm ambient lighting, "
            "casual relaxed pose, photorealistic, 50mm portrait lens, "
            "shallow dof, natural skin texture"
        ),
        "negative_prompt": (
            "deformed face, blurry face, cartoon, anime, "
            "illustration, bad anatomy, multiple people, watermark"
        ),
        "style_strength": 0.72,
    },
    "city_night": {
        "id": "city_night",
        "name": "Ночной город",
        "description": "Ночные огни, боке, атмосфера",
        "preview_url": "/previews/city_night.jpg",
        "prompt": (
            "professional portrait photo, nighttime city street, "
            "bokeh city lights background, neon reflections, "
            "dramatic yet flattering lighting, confident pose, "
            "85mm portrait lens, photorealistic, cinematic"
        ),
        "negative_prompt": (
            "deformed, distorted face, blurry, cartoon, multiple people, "
            "overexposed, flat lighting, watermark, text"
        ),
        "style_strength": 0.78,
    },
    "nature_fresh": {
        "id": "nature_fresh",
        "name": "На природе",
        "description": "Парк, зелень, естественный свет",
        "preview_url": "/previews/nature_fresh.jpg",
        "prompt": (
            "professional outdoor portrait, lush green park, "
            "dappled sunlight through trees, fresh natural look, "
            "casual but polished, photorealistic, 35mm lens, "
            "vibrant greens, candid moment"
        ),
        "negative_prompt": (
            "deformed face, blurry, cartoon, illustration, "
            "multiple people, bad anatomy, watermark, oversaturated"
        ),
        "style_strength": 0.73,
    },
    "rooftop_view": {
        "id": "rooftop_view",
        "name": "Крыша города",
        "description": "Крыша, горизонт, premium feeling",
        "preview_url": "/previews/rooftop_view.jpg",
        "prompt": (
            "premium lifestyle photo, rooftop terrace, "
            "city skyline background, daytime, confident pose, "
            "editorial quality, 50mm lens, sharp details, "
            "aspirational mood, photorealistic"
        ),
        "negative_prompt": (
            "deformed face, blurry, cartoon, multiple people, "
            "bad anatomy, watermark, low quality"
        ),
        "style_strength": 0.76,
    },
    "studio_clean": {
        "id": "studio_clean",
        "name": "Студия",
        "description": "Белый фон, профессиональный свет, чистота",
        "preview_url": "/previews/studio_clean.jpg",
        "prompt": (
            "professional studio portrait, clean white background, "
            "professional three-point lighting, sharp and clear, "
            "high-fashion magazine quality, 85mm lens, "
            "natural confident expression, photorealistic"
        ),
        "negative_prompt": (
            "deformed face, blurry face, cartoon, multiple people, "
            "bad anatomy, watermark, shadows, low quality"
        ),
        "style_strength": 0.70,
    },
    "beach_summer": {
        "id": "beach_summer",
        "name": "Пляж",
        "description": "Море, лето, солнце и свобода",
        "preview_url": "/previews/beach_summer.jpg",
        "prompt": (
            "candid beach portrait, sunny day, ocean background, "
            "warm summer light, relaxed happy expression, "
            "lifestyle photography, 35mm lens, photorealistic, "
            "natural skin, holiday mood"
        ),
        "negative_prompt": (
            "deformed face, distorted, cartoon, anime, multiple people, "
            "bad anatomy, watermark, blurry face"
        ),
        "style_strength": 0.74,
    },
    "business_casual": {
        "id": "business_casual",
        "name": "Деловой стиль",
        "description": "Smart casual, уверенность, взрослый взгляд",
        "preview_url": "/previews/business_casual.jpg",
        "prompt": (
            "professional business casual portrait, modern office "
            "or city background, confident relaxed pose, "
            "clean polished look, 50mm lens, soft directional light, "
            "photorealistic, LinkedIn-quality but warm"
        ),
        "negative_prompt": (
            "deformed face, blurry, cartoon, multiple people, "
            "bad anatomy, watermark, overly formal, stiff"
        ),
        "style_strength": 0.71,
    },
}
