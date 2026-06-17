#!/usr/bin/env python3
"""
Shared non-Qt runtime for the TheTechGuy image editor.
"""

from __future__ import annotations

import importlib.util
import os
import re
import shutil
import sys
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


APP_NAME = "TheTechGuy Image Editor"
WINDOW_TITLE = APP_NAME
APP_DATA_DIRNAME = "TheTechGuyImageEditor"
WINDOWS_APP_ID = "TheTechGuy.ImageEditor"
VC_RUNTIME_REG_KEY = r"SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64"

COLOUR_WORDS = {
    "white",
    "black",
    "red",
    "green",
    "blue",
    "yellow",
    "grey",
    "gray",
    "pink",
    "orange",
    "purple",
    "brown",
    "cyan",
    "magenta",
    "beige",
    "cream",
    "teal",
    "navy",
    "lime",
    "maroon",
    "violet",
    "indigo",
}
BACKGROUND_WORDS = {"background", "backdrop", "bg", "wall", "paper", "screen", "sky"}
PORTRAIT_WORDS = {
    "person",
    "people",
    "man",
    "woman",
    "girl",
    "boy",
    "face",
    "human",
    "portrait",
    "selfie",
    "model",
}
ANIME_WORDS = {"anime", "cartoon", "illustration", "drawing", "manga", "character"}
LOGO_WORDS = {"logo", "badge", "icon", "stamp", "sticker", "mark"}
TEXT_WORDS = {"text", "letters", "wordmark", "typography"}
PRODUCT_WORDS = {"product", "object", "item", "package", "bottle", "box"}
ANIMAL_WORDS = {"animal", "dog", "cat", "bird", "pet"}
VEHICLE_WORDS = {"car", "vehicle", "bike", "motorcycle", "truck"}
SUBJECT_WORDS = (
    PORTRAIT_WORDS
    | ANIME_WORDS
    | LOGO_WORDS
    | TEXT_WORDS
    | PRODUCT_WORDS
    | ANIMAL_WORDS
    | VEHICLE_WORDS
    | {"subject", "foreground", "figure"}
)

AI_MODELS: dict[str, dict[str, str]] = {
    "general": {
        "label": "General",
        "model": "isnet-general-use",
        "phrase": "the general model",
    },
    "people": {
        "label": "People / portraits",
        "model": "u2net_human_seg",
        "phrase": "the portrait model",
    },
    "anime": {
        "label": "Anime / illustrations",
        "model": "isnet-anime",
        "phrase": "the anime model",
    },
    "fast": {
        "label": "Fast",
        "model": "u2netp",
        "phrase": "the fast model",
    },
}

MODEL_FILENAMES = {
    "isnet-general-use": "isnet-general-use.onnx",
    "u2net_human_seg": "u2net_human_seg.onnx",
    "isnet-anime": "isnet-anime.onnx",
    "u2netp": "u2netp.onnx",
}

SESSION_CACHE: dict[str, object] = {}


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def bundle_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", app_root()))


def resource_path(filename: str) -> Path:
    return bundle_root() / "resources" / filename


def user_assets_dir() -> Path:
    local_appdata = os.getenv("LOCALAPPDATA")
    base = Path(local_appdata) if local_appdata else Path.home()
    path = base / APP_DATA_DIRNAME / "resources"
    path.mkdir(parents=True, exist_ok=True)
    return path


def loading_gif_path() -> Path:
    override_path = user_assets_dir() / "loding.gif"
    if override_path.exists():
        return override_path
    return resource_path("loding.gif")


def runtime_icon_path() -> Path:
    candidates = (
        resource_path("build_icon.ico"),
        app_root() / "build_icon.ico",
        resource_path("logo.png"),
    )
    for path in candidates:
        if path.exists():
            return path
    return resource_path("logo.png")


def preferred_loading_gif_output() -> Path:
    project_resources = app_root() / "resources"
    if project_resources.exists() and os.access(project_resources, os.W_OK):
        return project_resources / "loding.gif"
    return user_assets_dir() / "loding.gif"


def installed_models_dir() -> Path:
    return app_root() / "models"


def user_models_dir() -> Path:
    local_appdata = os.getenv("LOCALAPPDATA")
    base = Path(local_appdata) if local_appdata else Path.home()
    path = base / APP_DATA_DIRNAME / "models"
    path.mkdir(parents=True, exist_ok=True)
    return path


def available_model_path(model_name: str) -> Path | None:
    filename = MODEL_FILENAMES.get(model_name, f"{model_name}.onnx")
    for root in (installed_models_dir(), user_models_dir()):
        candidate = root / filename
        if candidate.exists():
            return candidate
    return None


def configure_model_home(model_name: str | None = None) -> Path:
    if model_name:
        model_file = available_model_path(model_name)
        model_home = model_file.parent if model_file else user_models_dir()
    else:
        installed_dir = installed_models_dir()
        if installed_dir.exists() and any(installed_dir.glob("*.onnx")):
            model_home = installed_dir
        else:
            model_home = user_models_dir()

    os.environ["U2NET_HOME"] = str(model_home)
    return model_home


def verify_branding_assets() -> dict[str, str]:
    logo_path = resource_path("logo.png")
    gif_path = loading_gif_path()
    if not logo_path.exists():
        raise RuntimeError(f"Missing branding asset: {logo_path}")
    if not gif_path.exists():
        raise RuntimeError(f"Missing loading animation: {gif_path}")
    icon_path = runtime_icon_path()
    return {
        "logo_path": str(logo_path),
        "gif_path": str(gif_path),
        "icon_path": str(icon_path),
    }


def verify_models() -> dict[str, str]:
    missing: list[str] = []
    found: dict[str, str] = {}
    for model_name, filename in MODEL_FILENAMES.items():
        path = available_model_path(model_name)
        if path is None:
            missing.append(filename)
        else:
            found[model_name] = str(path)

    if missing:
        raise RuntimeError(
            "Missing required AI model files: "
            + ", ".join(missing)
            + ". Run prepare_models.py or reinstall the packaged app."
        )
    return found


def ensure_runtime_dependencies(include_ai: bool = True) -> None:
    try:
        import PIL  # noqa: F401
    except ModuleNotFoundError as exc:
        raise RuntimeError(f"Missing required dependency: {exc.name}") from exc

    if include_ai:
        try:
            import onnxruntime  # noqa: F401
            import rembg  # noqa: F401
        except ModuleNotFoundError as exc:
            raise RuntimeError(f"Missing required AI dependency: {exc.name}") from exc


def has_vc_runtime() -> bool:
    if os.name != "nt":
        return True

    try:
        import winreg
    except ModuleNotFoundError:
        return True

    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, VC_RUNTIME_REG_KEY, 0, winreg.KEY_READ | getattr(winreg, "KEY_WOW64_64KEY", 0)) as key:
            installed, _ = winreg.QueryValueEx(key, "Installed")
    except OSError:
        return False

    return bool(installed)


def probe_ai_runtime() -> tuple[bool, dict[str, str], str | None]:
    try:
        if not has_vc_runtime():
            raise RuntimeError(
                "Missing Microsoft Visual C++ x64 runtime. Install the app using TheTechGuy Image Editor Setup.exe."
            )
        missing_dependencies = [
            name
            for name in ("onnxruntime", "rembg", "pymatting")
            if importlib.util.find_spec(name) is None
        ]
        if missing_dependencies:
            raise RuntimeError(
                "Missing required AI dependency: " + ", ".join(sorted(missing_dependencies))
            )
        models = verify_models()
        return True, models, None
    except Exception as exc:
        return False, {}, str(exc)


def warm_default_ai_session() -> str:
    try:
        from rembg import new_session
    except ModuleNotFoundError as exc:
        missing = exc.name or str(exc)
        raise RuntimeError(f"AI mode is missing dependency: {missing}") from exc
    except ImportError as exc:
        raise RuntimeError(f"AI mode failed to load rembg: {exc}") from exc

    configure_model_home("isnet-general-use")
    session = new_session("isnet-general-use")
    SESSION_CACHE["isnet-general-use"] = session
    model_path = available_model_path("isnet-general-use")
    return str(model_path) if model_path else str(configure_model_home("isnet-general-use"))


def run_startup_checks(progress: callable | None = None) -> dict[str, object]:
    def emit(message: str) -> None:
        if progress is not None:
            progress(message)

    emit("Loading interface…")
    assets = verify_branding_assets()

    emit("Checking dependencies…")
    ensure_runtime_dependencies(include_ai=False)

    emit("Loading AI engine…")
    ai_available, models, ai_error = probe_ai_runtime()
    if ai_available:
        emit("Preparing models…")
    else:
        emit("AI engine unavailable. Starting editor…")

    emit(f"Starting {APP_NAME}…")
    return {
        "assets": assets,
        "models": models,
        "ai_available": ai_available,
        "ai_error": ai_error,
        "default_model": str(available_model_path("isnet-general-use") or configure_model_home("isnet-general-use")),
        "model_home": str(configure_model_home()),
    }


def contains_word(text: str, words: set[str]) -> bool:
    return any(re.search(rf"\b{re.escape(word)}\b", text) for word in words)


def extract_colour(text: str) -> str | None:
    return next((word for word in COLOUR_WORDS if re.search(rf"\b{re.escape(word)}\b", text)), None)


def detect_subject_label(text: str) -> str:
    if contains_word(text, PORTRAIT_WORDS):
        return "person"
    if contains_word(text, ANIME_WORDS):
        return "anime subject"
    if contains_word(text, LOGO_WORDS):
        return "logo"
    if contains_word(text, TEXT_WORDS):
        return "text"
    if contains_word(text, PRODUCT_WORDS):
        return "product"
    if contains_word(text, ANIMAL_WORDS):
        return "animal"
    if contains_word(text, VEHICLE_WORDS):
        return "vehicle"
    return "main subject"


def choose_ai_model(text: str, preferred_key: str) -> dict[str, str]:
    if preferred_key in AI_MODELS and preferred_key != "auto":
        return AI_MODELS[preferred_key]
    if contains_word(text, ANIME_WORDS):
        return AI_MODELS["anime"]
    if contains_word(text, PORTRAIT_WORDS):
        return AI_MODELS["people"]
    if re.search(r"\b(fast|quick|quicker|speed|speedy)\b", text):
        return AI_MODELS["fast"]
    return AI_MODELS["general"]


def parse_instruction(
    text: str,
    engine_choice: str,
    model_choice: str,
    tolerance: int,
    blur: float,
    invert_override: bool = False,
) -> dict[str, object]:
    normalized = text.lower().strip()
    colour = extract_colour(normalized)
    mentions_background = contains_word(normalized, BACKGROUND_WORDS)
    explicit_colour_background = bool(colour and mentions_background)
    subject_label = detect_subject_label(normalized)

    subject_pattern = "|".join(sorted(re.escape(word) for word in SUBJECT_WORDS))
    remove_subject = invert_override or bool(
        re.search(
            rf"\b(remove|delete|cut|erase)\b.{{0,40}}\b({subject_pattern})\b",
            normalized,
        )
    )

    if engine_choice == "colour" or explicit_colour_background:
        recommended_tolerance = 60 if colour in {"white", "black"} else 42
        resolved_tolerance = max(tolerance, recommended_tolerance) if colour else tolerance

        if engine_choice == "ai" and explicit_colour_background:
            reply = f"Detected a {colour} background request, so I will use color mode."
        elif colour:
            reply = f"Removing the {colour} background with color matching."
        else:
            reply = "Removing the flat background with corner color matching."

        return {
            "method": "colour",
            "engine_label": "Color mode",
            "tolerance": resolved_tolerance,
            "blur": blur,
            "detected": colour or "edge-matched background",
            "reply": reply,
            "status": f"Color mode | tolerance {resolved_tolerance} | blur {blur:.1f}",
        }

    model = choose_ai_model(normalized, model_choice)
    model_label = model["label"]
    model_name = model["model"]
    model_phrase = model["phrase"]

    if remove_subject:
        reply = f"Removing the {subject_label} and keeping the background with {model_phrase}."
    else:
        reply = f"Removing the background and keeping the {subject_label} with {model_phrase}."

    return {
        "method": "ai",
        "engine_label": "AI mode",
        "ai_model": model_name,
        "ai_label": model_label,
        "invert": remove_subject,
        "detected": subject_label,
        "reply": reply,
        "status": f"AI mode | {model_label} | {model_name}",
    }


def build_trim_plan(threshold: int, blur: float) -> dict[str, object]:
    return {
        "method": "trim",
        "engine_label": "Quick Trim",
        "threshold": int(threshold),
        "blur": float(blur),
        "reply": "Running Quick Trim with the current threshold and edge softness.",
        "detected": "manual trim",
        "status": f"Quick trim | threshold {int(threshold)} | blur {float(blur):.1f}",
    }


def build_mix_plan(
    background_style: str,
    scale_percent: int,
    padding_percent: int,
    shadow_strength: int,
) -> dict[str, object]:
    return {
        "method": "mix",
        "engine_label": "Canvas Compose",
        "background_style": str(background_style),
        "scale_percent": int(scale_percent),
        "padding_percent": int(padding_percent),
        "shadow_strength": int(shadow_strength),
        "reply": f"Building a {background_style} canvas compose preview.",
        "detected": "mixed canvas",
        "status": f"Canvas compose | {background_style} | scale {int(scale_percent)}% | padding {int(padding_percent)}%",
    }


def build_output_path(input_path: str | Path, suffix: str = "_transparent.png") -> Path:
    source = Path(input_path)
    return source.with_name(f"{source.stem}{suffix}")


def get_rembg_session(model_name: str) -> object:
    configure_model_home(model_name)
    session = SESSION_CACHE.get(model_name)
    if session is None:
        try:
            from rembg import new_session
        except ModuleNotFoundError as exc:
            missing = exc.name or str(exc)
            raise RuntimeError(f"AI mode is missing dependency: {missing}") from exc
        except ImportError as exc:
            raise RuntimeError(f"AI mode failed to load rembg: {exc}") from exc
        session = new_session(model_name)
        SESSION_CACHE[model_name] = session
    return session


def refine_alpha_mask(alpha: np.ndarray, blur: float, tighten: int = 0) -> np.ndarray:
    mask = Image.fromarray(alpha.astype(np.uint8))
    if tighten > 0:
        size = min(7, tighten * 2 + 1)
        if size >= 3:
            mask = mask.filter(ImageFilter.MinFilter(size=size))
    if blur >= 1.0:
        mask = mask.filter(ImageFilter.MedianFilter(size=3))
    if blur > 0:
        mask = mask.filter(ImageFilter.GaussianBlur(radius=max(0.4, blur)))

    refined = np.array(mask, dtype=np.uint8)
    refined[refined <= 6] = 0
    refined[refined >= 249] = 255
    return refined


def remove_bg_ai(image: Image.Image, model_name: str, invert: bool) -> Image.Image:
    try:
        from rembg import remove
    except ModuleNotFoundError as exc:
        missing = exc.name or str(exc)
        raise RuntimeError(f"AI mode is missing dependency: {missing}") from exc
    except ImportError as exc:
        raise RuntimeError(f"AI mode failed to load rembg: {exc}") from exc

    result = remove(image.convert("RGBA"), session=get_rembg_session(model_name))
    data = np.array(result)
    data[:, :, 3] = refine_alpha_mask(data[:, :, 3], 0.8, tighten=1)
    if invert:
        data[:, :, 3] = 255 - data[:, :, 3]
    return Image.fromarray(data)


def outer_background_mask(match_mask: np.ndarray) -> np.ndarray:
    height, width = match_mask.shape
    visited = np.zeros((height, width), dtype=bool)
    queue: deque[tuple[int, int]] = deque()

    def add_seed(y: int, x: int) -> None:
        if match_mask[y, x] and not visited[y, x]:
            visited[y, x] = True
            queue.append((y, x))

    for x in range(width):
        add_seed(0, x)
        add_seed(height - 1, x)

    for y in range(height):
        add_seed(y, 0)
        add_seed(y, width - 1)

    while queue:
        y, x = queue.popleft()
        for next_y, next_x in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
            if (
                0 <= next_y < height
                and 0 <= next_x < width
                and match_mask[next_y, next_x]
                and not visited[next_y, next_x]
            ):
                visited[next_y, next_x] = True
                queue.append((next_y, next_x))

    return visited


def edge_samples(rgb: np.ndarray) -> np.ndarray:
    height, width = rgb.shape[:2]
    sample_size = max(2, min(12, height // 6, width // 6))
    return np.concatenate(
        [
            rgb[:sample_size, :, :].reshape(-1, 3),
            rgb[-sample_size:, :, :].reshape(-1, 3),
            rgb[:, :sample_size, :].reshape(-1, 3),
            rgb[:, -sample_size:, :].reshape(-1, 3),
        ]
    )


def dominant_edge_palette(samples: np.ndarray, limit: int = 5) -> np.ndarray:
    quantized = np.clip(np.round(samples / 18.0), 0, 14).astype(np.int16)
    unique, counts = np.unique(quantized, axis=0, return_counts=True)
    order = np.argsort(counts)[::-1][:limit]
    return unique[order].astype(np.float32) * 18.0 + 9.0


def background_distance_map(rgb: np.ndarray, samples: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    palette = dominant_edge_palette(samples)
    background = np.median(samples, axis=0).astype(np.float32)
    palette = np.vstack([palette, background])
    diffs = rgb[:, :, None, :] - palette[None, None, :, :]
    distance = np.sqrt(np.sum(diffs * diffs, axis=3))
    spread = float(np.std(samples, axis=0).mean())
    return np.min(distance, axis=2), background, spread


def remove_bg_colour(image: Image.Image, tolerance: int, blur: float) -> Image.Image:
    data = np.array(image.convert("RGBA"))
    rgb = data[:, :, :3].astype(np.float32)
    samples = edge_samples(rgb)
    distance, background, spread = background_distance_map(rgb, samples)
    luminance = 0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]
    background_luminance = float(0.299 * background[0] + 0.587 * background[1] + 0.114 * background[2])
    chroma = np.max(rgb, axis=2) - np.min(rgb, axis=2)

    tolerance_value = max(12.0, float(tolerance) + spread * 0.7)
    luminance_tolerance = max(16.0, tolerance_value * 0.9)
    light_background = background_luminance >= 170.0

    base_match = distance <= tolerance_value
    tonal_match = (
        np.abs(luminance - background_luminance) <= luminance_tolerance
    ) & (distance <= tolerance_value * 1.5)
    if light_background:
        soft_match = (
            (luminance >= background_luminance - luminance_tolerance * 1.2)
            & (chroma <= 48.0 + tolerance_value * 0.9)
            & (distance <= tolerance_value * 1.8)
        )
        matched = base_match | tonal_match | soft_match
    else:
        matched = base_match | tonal_match

    alpha = np.where(outer_background_mask(matched), 0, 255).astype(np.uint8)
    alpha = refine_alpha_mask(alpha, blur, tighten=1 if light_background else 0)
    data[:, :, 3] = alpha
    return Image.fromarray(data)


def remove_bg_trim(image: Image.Image, threshold: int, blur: float) -> Image.Image:
    data = np.array(image.convert("RGBA"))
    rgb = data[:, :, :3].astype(np.float32)
    background_samples = edge_samples(rgb)
    distance, background, spread = background_distance_map(rgb, background_samples)
    luminance = 0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]
    background_luminance = float(
        0.299 * background[0] + 0.587 * background[1] + 0.114 * background[2]
    )
    chroma = np.max(rgb, axis=2) - np.min(rgb, axis=2)
    alpha_hint = data[:, :, 3].astype(np.float32)

    color_tolerance = max(16.0, threshold * 1.85 + spread * 1.6)
    luminance_tolerance = max(12.0, threshold * 1.55 + spread * 1.2)
    light_background = background_luminance >= 168.0

    base_match = distance <= color_tolerance
    tonal_match = (
        np.abs(luminance - background_luminance) <= luminance_tolerance
    ) & (distance <= color_tolerance * 1.55)

    if light_background:
        soft_light_match = (
            (luminance >= background_luminance - luminance_tolerance * 1.35)
            & (chroma <= 52.0 + threshold * 1.2)
            & (distance <= color_tolerance * 1.8)
        )
        matched = base_match | tonal_match | soft_light_match
    else:
        matched = base_match | tonal_match

    if np.any(alpha_hint < 255):
        matched |= alpha_hint <= 10

    alpha = np.where(outer_background_mask(matched), 0, 255).astype(np.uint8)
    alpha = refine_alpha_mask(alpha, blur, tighten=1 if light_background else 0)

    data[:, :, 3] = alpha
    return Image.fromarray(data)


def gradient_background(
    size: tuple[int, int],
    top_color: tuple[int, int, int],
    bottom_color: tuple[int, int, int],
) -> Image.Image:
    width, height = size
    background = Image.new("RGBA", size)
    draw = ImageDraw.Draw(background)
    for y in range(height):
        blend = y / max(1, height - 1)
        colour = tuple(
            int(top_color[index] * (1.0 - blend) + bottom_color[index] * blend)
            for index in range(3)
        )
        draw.line((0, y, width, y), fill=colour + (255,))
    return background


def mix_background(style: str, size: tuple[int, int]) -> Image.Image:
    style_key = style.lower().strip()
    if style_key == "transparent":
        return Image.new("RGBA", size, (0, 0, 0, 0))
    if style_key == "white":
        return Image.new("RGBA", size, (248, 249, 252, 255))
    if style_key == "dark":
        return Image.new("RGBA", size, (20, 24, 31, 255))
    if style_key == "warm":
        return gradient_background(size, (255, 230, 208), (208, 90, 92))
    return gradient_background(size, (25, 30, 54), (35, 88, 160))


def create_mix_canvas(
    image: Image.Image,
    background_style: str,
    scale_percent: int,
    padding_percent: int,
    shadow_strength: int,
) -> Image.Image:
    source = image.convert("RGBA")
    width, height = source.size
    padding = int(min(width, height) * (padding_percent / 100.0))
    canvas_size = (width + padding * 2, height + padding * 2)
    background = mix_background(background_style, canvas_size)

    target_width = max(32, int(width * (scale_percent / 100.0)))
    target_height = max(32, int(height * (scale_percent / 100.0)))
    subject = source.resize((target_width, target_height), Image.Resampling.LANCZOS)
    offset = (
        (canvas_size[0] - subject.width) // 2,
        (canvas_size[1] - subject.height) // 2,
    )

    if shadow_strength > 0:
        shadow_alpha = subject.getchannel("A").filter(
            ImageFilter.GaussianBlur(radius=max(2.0, shadow_strength / 2.0))
        )
        shadow = Image.new(
            "RGBA",
            subject.size,
            (10, 12, 18, min(180, 40 + shadow_strength * 8)),
        )
        shadow.putalpha(shadow_alpha)
        background.alpha_composite(shadow, (offset[0], offset[1] + max(4, shadow_strength // 2)))

    background.alpha_composite(subject, offset)
    return background


def run_local_processing(
    input_path: str,
    plan: dict[str, object],
    progress: callable | None = None,
) -> Path:
    def emit(message: str) -> None:
        if progress is not None:
            progress(message)

    with Image.open(input_path) as opened:
        image = opened.convert("RGBA")

    method = str(plan["method"])
    if method == "colour":
        tolerance = int(plan["tolerance"])
        blur = float(plan["blur"])
        emit(f"Running color match with tolerance {tolerance} and blur {blur:.1f}…")
        result = remove_bg_colour(image, tolerance, blur)
    elif method == "trim":
        threshold = int(plan["threshold"])
        blur = float(plan["blur"])
        emit(f"Running Quick Trim with threshold {threshold} and softness {blur:.1f}…")
        result = remove_bg_trim(image, threshold, blur)
    else:
        ai_label = str(plan["ai_label"])
        ai_model = str(plan["ai_model"])
        emit(f"Running {ai_label} AI segmentation…")
        result = remove_bg_ai(image, ai_model, bool(plan.get("invert", False)))

    output_path = build_output_path(input_path)
    emit("Saving result…")
    result.save(output_path)
    return output_path


def save_copy(source_path: str, destination_path: str) -> str:
    source = Path(source_path)
    destination = Path(destination_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return str(destination)


def run_local_processing(
    input_path: str,
    plan: dict[str, object],
    progress: callable | None = None,
) -> Path:
    def emit(message: str) -> None:
        if progress is not None:
            progress(message)

    with Image.open(input_path) as opened:
        image = opened.convert("RGBA")

    method = str(plan["method"])
    if method == "colour":
        tolerance = int(plan["tolerance"])
        blur = float(plan["blur"])
        emit(f"Running color match with tolerance {tolerance} and blur {blur:.1f}…")
        result = remove_bg_colour(image, tolerance, blur)
    elif method == "trim":
        threshold = int(plan["threshold"])
        blur = float(plan["blur"])
        emit(f"Running Quick Trim with threshold {threshold} and softness {blur:.1f}…")
        result = remove_bg_trim(image, threshold, blur)
    elif method == "mix":
        background_style = str(plan["background_style"])
        scale_percent = int(plan["scale_percent"])
        padding_percent = int(plan["padding_percent"])
        shadow_strength = int(plan["shadow_strength"])
        emit(f"Building a {background_style} canvas mix…")
        result = create_mix_canvas(image, background_style, scale_percent, padding_percent, shadow_strength)
    else:
        ai_label = str(plan["ai_label"])
        ai_model = str(plan["ai_model"])
        emit(f"Running {ai_label} AI segmentation…")
        result = remove_bg_ai(image, ai_model, bool(plan.get("invert", False)))

    output_path = build_output_path(input_path, "_mix.png" if method == "mix" else "_transparent.png")
    emit("Saving result…")
    result.save(output_path)
    return output_path
