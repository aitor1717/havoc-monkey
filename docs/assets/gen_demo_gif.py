"""Render docs/assets/demo.cast to demo.svg plus animated GIFs for GitHub/HN/LinkedIn."""
import re
import shutil
import subprocess
from pathlib import Path

from PIL import Image

import termtosvg.anim as anim
import termtosvg.asciicast as asciicast
import termtosvg.config as config
import termtosvg.term as term

HERE = Path(__file__).resolve().parent
CAST = HERE / "demo.cast"
FRAMES_DIR = HERE / "_frames"

# Same brand colors as the membrane loop GIFs (gen_membrane_mockup.py), so the
# terminal demo doesn't look like a different product. Maps standard ANSI slots:
# color1/2/3 are also reused for the three window-chrome "traffic light" dots.
CHARCOAL = "#18181A"
PINK = "#FA0A6C"
TEAL = "#14C2C4"
WHITE = "#FFFBF5"

_COLOR_OVERRIDES = {
    "background": CHARCOAL,
    "color0": CHARCOAL,
    "color1": PINK,    # window dot 1
    "color2": TEAL,    # window dot 3, and our bold-green "$" prompt
    "color3": WHITE,   # window dot 2
    "color7": WHITE,
    "color8": TEAL,    # bright black -> UNKNOWN/SKIPPED severity
    "color9": PINK,    # bright red -> CRITICAL/HIGH severity
    "color10": TEAL,   # bright green -> LOW/PASSED severity
    "color11": PINK,   # bright yellow -> MEDIUM severity
    "color15": WHITE,
    "foreground": WHITE,
}


def recolor_template(template: bytes) -> bytes:
    text = template.decode("utf-8")
    for name, hex_color in _COLOR_OVERRIDES.items():
        text = re.sub(
            rf"(\.{name}\s*\{{\s*fill:\s*)#[0-9A-Fa-f]{{6}}(\s*\}})",
            rf"\g<1>{hex_color}\g<2>",
            text,
        )
    return text.encode("utf-8")


TEMPLATE = recolor_template(config.default_templates()["window_frame"])


def build_frames():
    FRAMES_DIR.mkdir(exist_ok=True)
    records = asciicast.read_records(str(CAST))
    geometry, frames = term.timed_frames(records, min_frame_dur=1, max_frame_dur=600, last_frame_dur=4000)
    frames = list(frames)
    anim.render_animation(frames, geometry, str(HERE / "demo.svg"), TEMPLATE)
    anim.render_still_frames(frames, geometry, str(FRAMES_DIR), TEMPLATE)
    durations_ms = [max(20, round(f.duration)) for f in frames]
    return durations_ms


def svgs_to_pngs(scale: float) -> list[Path]:
    svgs = sorted(FRAMES_DIR.glob("termtosvg_*.svg"))
    pngs = []
    for svg in svgs:
        png = svg.with_suffix(".png")
        subprocess.run(
            ["rsvg-convert", "-z", str(scale), "-o", str(png), str(svg)],
            check=True,
        )
        pngs.append(png)
    return pngs


def make_gif(pngs: list[Path], durations_ms: list[int], out_path: Path, canvas=None, bg=(24, 24, 26)):
    frames = [Image.open(p).convert("RGB") for p in pngs]
    if canvas is not None:
        cw, ch = canvas
        composed = []
        for im in frames:
            bgim = Image.new("RGB", (cw, ch), bg)
            scale = min(cw / im.width, ch / im.height)
            new_size = (round(im.width * scale), round(im.height * scale))
            im_resized = im.resize(new_size, Image.LANCZOS)
            x = (cw - new_size[0]) // 2
            y = (ch - new_size[1]) // 2
            bgim.paste(im_resized, (x, y))
            composed.append(bgim)
        frames = composed

    frames[0].save(
        out_path,
        save_all=True,
        append_images=frames[1:],
        duration=durations_ms,
        loop=0,
        optimize=True,
    )
    print(f"wrote {out_path}  {frames[0].size}  {len(frames)} frames")


def main():
    durations_ms = build_frames()

    pngs_wide = svgs_to_pngs(scale=1.0)
    make_gif(pngs_wide, durations_ms, HERE / "demo_github.gif")

    pngs_hires = svgs_to_pngs(scale=1.6)
    pngs_hires = sorted(FRAMES_DIR.glob("termtosvg_*.png"))
    make_gif(pngs_hires, durations_ms, HERE / "demo_linkedin.gif", canvas=(1200, 627))

    shutil.rmtree(FRAMES_DIR)


if __name__ == "__main__":
    main()
