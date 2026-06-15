# -*- coding: utf-8 -*-
"""
FFmpeg фильтры для каждого стиля эдита.

Стили:
- Hype: быстрые нарезки, зум, тряска, вспышки яркости, неоновый цвет
- Sad: замедление, размытие, обесцвечивание, зернистость
- Chill: плавные переходы, тёплые тона, мягкий зум
- Glitch: RGB-сдвиг, шум, смещение

Добавлена поддержка динамической цветокоррекции на основе ИИ-промпта (color_theme).
"""


def get_style_filters(style: str, segment_index: int = 0, color_theme: str | None = None) -> str:
    """
    Возвращает строку FFmpeg-фильтров для заданного стиля и цветовой гаммы.

    Args:
        style: ключ стиля (hype/sad/chill/glitch)
        segment_index: индекс текущего сегмента (для вариации эффектов)
        color_theme: цветовая тема от ИИ (например, "neon red", "black and white")

    Returns:
        Строка FFmpeg video filter complex
    """
    filters = {
        "hype": _get_hype_filters,
        "sad": _get_sad_filters,
        "chill": _get_chill_filters,
        "glitch": _get_glitch_filters,
    }

    builder = filters.get(style, _get_chill_filters)
    style_filter_str = builder(segment_index)
    
    # Применяем ИИ-цветокоррекцию, если она задана
    color_filter = _get_color_theme_filter(color_theme)
    if color_filter:
        return f"{style_filter_str},{color_filter}"
        
    return style_filter_str


def _get_color_theme_filter(color_theme: str | None) -> str:
    """Генерирует FFmpeg фильтры для кастомной цветовой темы."""
    if not color_theme:
        return ""
        
    theme = color_theme.lower()
    
    if "red" in theme:
        # Усиление красных тонов
        return "colorbalance=rs=0.18:gs=-0.08:bs=-0.08:rm=0.25:gm=-0.05:bm=-0.05"
    elif "blue" in theme:
        # Усиление синих тонов (холодный фильтр)
        return "colorbalance=rs=-0.08:gs=-0.08:bs=0.18:rm=-0.05:gm=-0.05:bm=0.25"
    elif "green" in theme:
        # Зеленая матрица
        return "colorbalance=rs=-0.08:gs=0.18:bs=-0.08:rm=-0.05:gm=0.25:bm=-0.05"
    elif any(x in theme for x in ["black and white", "b&w", "gray", "monochrome"]):
        # Черно-белый стиль с повышенной контрастностью
        return "eq=saturation=0:contrast=1.25:brightness=-0.02"
    elif any(x in theme for x in ["vintage", "retro", "warm", "sepia"]):
        # Теплые винтажные тона + виньетка
        return "colorbalance=rs=0.12:gs=0.04:bs=-0.08,vignette=PI/4.5"
    elif any(x in theme for x in ["dark", "shadow", "grim", "gothic"]):
        # Мрачный стиль: низкая яркость, высокий контраст
        return "eq=contrast=1.35:brightness=-0.09:saturation=1.05"
    elif any(x in theme for x in ["neon", "cyberpunk", "purple", "magenta"]):
        # Киберпанк: сине-фиолетово-розовые оттенки
        return "colorbalance=rs=0.12:gs=-0.1:bs=0.22:rm=0.15:gm=-0.15:bm=0.25"
        
    return ""


def _get_hype_filters(segment_index: int) -> str:
    """
    Hype-стиль: энергичный, агрессивный.
    - Ускорение (1.2x)
    - Зум и тряска камеры
    - Динамическая вспышка белого (Beat Flash) в первые 0.2 сек
    - Резкость и насыщенность
    """
    zoom_values = [1.05, 1.1, 1.15, 1.08, 1.12]
    zoom = zoom_values[segment_index % len(zoom_values)]

    shake_x = (segment_index % 3) * 2 + 2
    shake_y = ((segment_index + 1) % 3) * 2 + 2

    # Формула вспышки: в начале сегмента (t < 0.2) плавно гаснет яркость с 0.2 до 0.0
    flash_expr = "if(lt(t,0.2), 0.18 * (1.0 - t/0.2), 0)"

    filters = [
        "setpts=PTS/1.2",
        f"scale=iw*{zoom}:ih*{zoom}",
        "crop=iw/{0}:ih/{0}".format(zoom),
        f"crop=iw-{shake_x * 2}:ih-{shake_y * 2}:"
        f"{shake_x}+{shake_x}*sin(n*0.5):"
        f"{shake_y}+{shake_y}*cos(n*0.7)",
        # Контраст, насыщенность и ИИ-вспышка
        f"eq=contrast=1.3:brightness=0.02+{flash_expr}:saturation=1.4",
        "unsharp=5:5:1.5:5:5:0.5",
    ]

    return ",".join(filters)


def _get_sad_filters(segment_index: int) -> str:
    """
    Sad-стиль: меланхоличный, замедленный.
    - Замедление (0.85x) с оптическим блендингом кадров (эффект Twixtor)
    - Лёгкое размытие и виньетирование
    - Зернистость плёнки
    - Мягкая вспышка затемнения (fade-in) в начале сцены
    """
    sat_values = [0.3, 0.4, 0.35, 0.45, 0.25]
    saturation = sat_values[segment_index % len(sat_values)]
    
    # Плавное появление кадра из темноты в начале сцены (0.25 сек)
    fade_expr = "if(lt(t,0.25), -0.15 * (1.0 - t/0.25), 0)"

    filters = [
        "setpts=PTS/0.85",
        # Мягкое замедление с интерполяцией кадров (60 FPS blend)
        "minterpolate=fps=60:mi_mode=blend",
        f"eq=saturation={saturation}:brightness=-0.04+{fade_expr}:contrast=1.15",
        "gblur=sigma=1.2",
        "vignette=PI/4",
        "noise=alls=12:allf=t+u",
    ]

    return ",".join(filters)


def _get_chill_filters(segment_index: int) -> str:
    """
    Chill-стиль: спокойный, расслабляющий.
    - Нормальная скорость
    - Тёплые тона (оранжево-жёлтый оттенок)
    - Мягкий зум
    - Плавный фейд яркости на стыке
    """
    zoom_values = [1.02, 1.03, 1.04, 1.025, 1.035]
    zoom = zoom_values[segment_index % len(zoom_values)]

    filters = [
        f"scale=iw*{zoom}:ih*{zoom}",
        "crop=iw/{0}:ih/{0}".format(zoom),
        "colorbalance=rs=0.1:gs=0.05:bs=-0.1:rm=0.08:gm=0.03:bm=-0.05",
        "eq=brightness=0.04:contrast=1.05:saturation=1.18",
        "gblur=sigma=0.4",
    ]

    return ",".join(filters)


def _get_glitch_filters(segment_index: int) -> str:
    """
    Glitch-стиль: киберпанковый, искажённый.
    - RGB-сдвиг
    - Цифровой шум
    - Световой глитч-флэш на стыке кадров
    - Инверсия цветов на некоторых сегментах
    """
    shift_x = (segment_index % 5 + 1) * 3
    shift_y = ((segment_index + 2) % 5 + 1) * 2
    
    # Вспышка сильного глитч-искажения в первые 0.15 сек бита
    glitch_flash = "if(lt(t,0.15), 0.25 * (1.0 - t/0.15), 0)"

    filters_list = [
        f"rgbashift=rh={shift_x}:rv={shift_y}:bh=-{shift_x}:bv=-{shift_y}",
        "noise=alls=25:allf=t",
        f"eq=contrast=1.4:saturation=1.5:brightness=0.02+{glitch_flash}",
    ]

    if segment_index % 3 == 0:
        filters_list.append("negate")

    filters_list.append("unsharp=7:7:2.0:7:7:0")

    return ",".join(filters_list)
