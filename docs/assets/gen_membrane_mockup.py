"""Mockup: a big membrane box that lets only one ball color in (and the other out),
balls swarm it like an ovule, bounce off the title letters, and a same-color hit on
'monkey' flips which color is allowed in/out (and which color 'monkey' is)."""
import math
import random
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = Path(__file__).resolve().parent
W, H = 1200, 630

# The actual brand colors (--pink / --teal in the site CSS and report.py's HTML
# report template) rather than a gradient-derived tone: a saturated orange-red
# reads well as tiny dots on charcoal, but it drifted away from the real brand
# magenta-pink, which has more presence as a full-bleed gradient hero.
PINK = (250, 10, 108)
TEAL = (20, 194, 196)
WHITE = (255, 251, 245)
CHARCOAL = (24, 24, 26)

FONT_BOLD = "/usr/share/fonts/liberation/LiberationSans-Bold.ttf"

MARGIN = 110
BOX = (MARGIN, MARGIN, W - MARGIN, H - MARGIN)
RADIUS = 28
BOX_WIDTH_FRAC = 0.82  # box width as a fraction of canvas width, any aspect ratio
BOX_ASPECT = (W - 2 * MARGIN) / (H - 2 * MARGIN)  # box keeps this width:height shape
BASE_AREA = W * H  # canvas area the tuned ball count/forces were designed for

N_BALLS = 240
BALL_RADIUS = 4.5
SPEED_RANGE = (0.5, 1.3)
OUTER_PULL = 0.045
INNER_PULL = 0.022
GATE_ATTRACT = 0.020
GATE_REPEL = 0.012
DAMPING = 0.998
MAX_SPEED = 2.5
FLIP_COOLDOWN = 16
BOUNCE_DEFLECT_DEG = 24
MONKEY_HIT_PAD = 2.0


@dataclass
class Ball:
    x: float
    y: float
    vx: float
    vy: float
    r: float
    color: tuple
    inside: bool


@dataclass
class State:
    box_tint: tuple = TEAL
    inbound_color: tuple = PINK
    outbound_color: tuple = TEAL
    monkey_color: tuple = PINK
    last_flip_frame: int = -10_000


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def set_canvas(width, height, density_scale=1.0, max_balls=420):
    """Switch the canvas to a new aspect ratio (square, vertical, ...). The box
    keeps its original shape (just scaled), centered in whatever extra space the
    new aspect ratio leaves; ball count scales with canvas area so density stays
    consistent, with an extra `density_scale` knob for the "heavier" cuts."""
    global W, H, BOX, N_BALLS
    W, H = width, height
    box_w = width * BOX_WIDTH_FRAC
    box_h = box_w / BOX_ASPECT
    mx, my = (width - box_w) / 2, (height - box_h) / 2
    BOX = (mx, my, width - mx, height - my)
    area_ratio = (width * height) / BASE_AREA
    N_BALLS = min(max_balls, round(240 * area_ratio * density_scale))


def make_balls():
    bx0, by0, bx1, by1 = BOX
    balls = []
    for i in range(N_BALLS):
        color = PINK if i % 2 == 0 else TEAL
        r = BALL_RADIUS
        while True:
            x = random.uniform(r, W - r)
            y = random.uniform(r, H - r)
            if not (bx0 < x < bx1 and by0 < y < by1):
                break
        ang = random.uniform(0, 2 * math.pi)
        speed = random.uniform(*SPEED_RANGE)
        balls.append(Ball(x, y, math.cos(ang) * speed, math.sin(ang) * speed, r, color, inside=False))
    return balls


def title_rects(draw: ImageDraw.ImageDraw):
    f_title = ImageFont.truetype(FONT_BOLD, 66)
    havoc, monkey = "havoc-", "monkey"
    w_havoc = draw.textlength(havoc, font=f_title)
    w_monkey = draw.textlength(monkey, font=f_title)
    total_w = w_havoc + w_monkey
    cx, cy = (BOX[0] + BOX[2]) / 2, (BOX[1] + BOX[3]) / 2
    tx = cx - total_w / 2

    bbox_h = draw.textbbox((0, 0), havoc + monkey, font=f_title)
    text_h = bbox_h[3] - bbox_h[1]
    ty = cy - text_h / 2 - bbox_h[1]

    pad = 8
    bbox_havoc = draw.textbbox((tx, ty), havoc, font=f_title)
    bbox_monkey = draw.textbbox((tx + w_havoc, ty), monkey, font=f_title)
    rect_havoc = (bbox_havoc[0] - pad, bbox_havoc[1] - pad, bbox_havoc[2] + pad, bbox_havoc[3] + pad)
    rect_monkey = (bbox_monkey[0] - pad, bbox_monkey[1] - pad, bbox_monkey[2] + pad, bbox_monkey[3] + pad)
    return f_title, (tx, ty), w_havoc, rect_havoc, rect_monkey


def nearest_point_on_rect(x, y, rect):
    x0, y0, x1, y1 = rect
    return clamp(x, x0, x1), clamp(y, y0, y1)


def nearest_boundary_point(x, y, rect):
    """Closest point on the rect's perimeter, for a point already inside it."""
    x0, y0, x1, y1 = rect
    d_left, d_right, d_top, d_bottom = x - x0, x1 - x, y - y0, y1 - y
    m = min(d_left, d_right, d_top, d_bottom)
    if m == d_left:
        return x0, y
    if m == d_right:
        return x1, y
    if m == d_top:
        return x, y0
    return x, y1


def redirect(b: Ball, max_deg=BOUNCE_DEFLECT_DEG):
    """Rotate the post-bounce velocity by a small random angle so balls don't
    just ping back and forth along the same line."""
    angle = math.radians(random.uniform(-max_deg, max_deg))
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    vx, vy = b.vx, b.vy
    b.vx = vx * cos_a - vy * sin_a
    b.vy = vx * sin_a + vy * cos_a


def reflect_at_point(b: Ball, nx, ny):
    """Push the ball's edge back to nx,ny and reflect its velocity off that contact
    point, like a real bounce. Shared by letter collisions and the box membrane."""
    dx, dy = b.x - nx, b.y - ny
    dist = math.hypot(dx, dy)
    if dist >= b.r or dist == 0:
        return False
    ux, uy = dx / (dist or 1e-6), dy / (dist or 1e-6)
    overlap = b.r - dist
    b.x += ux * overlap
    b.y += uy * overlap
    vn = b.vx * ux + b.vy * uy
    if vn < 0:
        b.vx -= 2 * vn * ux
        b.vy -= 2 * vn * uy
    redirect(b)
    return True


def reflect_off_rect(b: Ball, rect):
    nx, ny = nearest_point_on_rect(b.x, b.y, rect)
    reflect_at_point(b, nx, ny)


def step(balls, state: State, frame_idx):
    bx0, by0, bx1, by1 = BOX

    for b in balls:
        if b.inside:
            tx, ty = (bx0 + bx1) / 2, (by0 + by1) / 2
            pull = INNER_PULL
        else:
            tx, ty = nearest_point_on_rect(b.x, b.y, BOX)
            pull = OUTER_PULL
        dx, dy = tx - b.x, ty - b.y
        dist = math.hypot(dx, dy) or 1e-6
        b.vx += pull * dx / dist
        b.vy += pull * dy / dist

        # Gate bias: balls that *can* cross lean toward doing so; balls that
        # can't are gently held back, as if the title text were quietly
        # pulling or pushing them depending on which color it currently favors.
        if b.inside and b.color == state.outbound_color:
            gx, gy = nearest_boundary_point(b.x, b.y, BOX)  # can leave: drift toward the exit
            gate = GATE_ATTRACT
        elif b.inside:
            gx, gy = (bx0 + bx1) / 2, (by0 + by1) / 2  # trapped: drift back toward center/text
            gate = GATE_REPEL
        elif b.color == state.inbound_color:
            gx, gy = nearest_point_on_rect(b.x, b.y, BOX)  # can enter: drift toward the box
            gate = GATE_ATTRACT
        else:
            gx, gy = nearest_point_on_rect(b.x, b.y, BOX)  # can't enter: drift away from it
            gate = -GATE_REPEL
        gdx, gdy = gx - b.x, gy - b.y
        gdist = math.hypot(gdx, gdy) or 1e-6
        b.vx += gate * gdx / gdist
        b.vy += gate * gdy / gdist

        b.vx *= DAMPING
        b.vy *= DAMPING
        speed = math.hypot(b.vx, b.vy)
        if speed > MAX_SPEED:
            b.vx *= MAX_SPEED / speed
            b.vy *= MAX_SPEED / speed
        b.x += b.vx
        b.y += b.vy

    for b in balls:
        if not b.inside:
            bounced = False
            if b.x - b.r < 0:
                b.x = b.r
                b.vx *= -1
                bounced = True
            if b.x + b.r > W:
                b.x = W - b.r
                b.vx *= -1
                bounced = True
            if b.y - b.r < 0:
                b.y = b.r
                b.vy *= -1
                bounced = True
            if b.y + b.r > H:
                b.y = H - b.r
                b.vy *= -1
                bounced = True
            if bounced:
                redirect(b)

    for b in balls:
        # Block disallowed crossings right at the circle's edge, same bounce
        # physics as any other collision. Allowed colors are simply never
        # touched here, so they glide through at their own natural speed.
        if b.inside:
            nx, ny = nearest_boundary_point(b.x, b.y, BOX)
            allowed = state.outbound_color
        else:
            nx, ny = nearest_point_on_rect(b.x, b.y, BOX)
            allowed = state.inbound_color
        if b.color == allowed:
            continue
        dx, dy = b.x - nx, b.y - ny
        dist = math.hypot(dx, dy)
        if dist == 0 or dist >= b.r:
            continue
        # Only a genuine crossing attempt if the ball is actually heading through
        # the wall (not just freshly arrived and still drifting deeper inward).
        vn = b.vx * (dx / dist) + b.vy * (dy / dist)
        if vn >= 0:
            continue
        reflect_at_point(b, nx, ny)

    for b in balls:
        # Bookkeeping only: flip `inside` once the center has actually crossed
        # the line. No repositioning, so allowed colors slide through smoothly
        # instead of jumping to a fixed offset.
        now_inside = bx0 < b.x < bx1 and by0 < b.y < by1
        if now_inside != b.inside:
            b.inside = now_inside

    n = len(balls)
    for i in range(n):
        a = balls[i]
        for j in range(i + 1, n):
            c = balls[j]
            if a.inside != c.inside:
                continue
            dx, dy = c.x - a.x, c.y - a.y
            dist = math.hypot(dx, dy) or 1e-6
            min_d = a.r + c.r
            if dist < min_d:
                nx, ny = dx / dist, dy / dist
                overlap = (min_d - dist) / 2
                a.x -= nx * overlap
                a.y -= ny * overlap
                c.x += nx * overlap
                c.y += ny * overlap
                a.vx, c.vx = c.vx, a.vx
                a.vy, c.vy = c.vy, a.vy


def resolve_letters(balls, rect_havoc, rect_monkey, state: State, frame_idx):
    for b in balls:
        if not b.inside:
            continue
        reflect_off_rect(b, rect_havoc)
        before = (b.x, b.y)
        rx0, ry0, rx1, ry1 = rect_monkey
        nx, ny = nearest_point_on_rect(b.x, b.y, rect_monkey)
        dist = math.hypot(b.x - nx, b.y - ny)
        hit = dist < b.r + MONKEY_HIT_PAD
        reflect_off_rect(b, rect_monkey)
        if hit and b.color == state.monkey_color and frame_idx - state.last_flip_frame > FLIP_COOLDOWN:
            state.box_tint = TEAL if state.box_tint == PINK else PINK
            state.outbound_color = state.box_tint
            state.inbound_color = PINK if state.box_tint == TEAL else TEAL
            state.monkey_color = TEAL if state.monkey_color == PINK else PINK
            state.last_flip_frame = frame_idx


def render(balls, state: State, rect_havoc, rect_monkey, title_pos, f_title, w_havoc):
    base = Image.new("RGBA", (W, H), (*CHARCOAL, 255))

    box_glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(box_glow)
    gdraw.rounded_rectangle(BOX, radius=RADIUS, outline=(*state.box_tint, 90), width=10)
    box_glow = box_glow.filter(ImageFilter.GaussianBlur(10))
    base.alpha_composite(box_glow)

    ball_glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bgdraw = ImageDraw.Draw(ball_glow)
    for b in balls:
        bgdraw.ellipse([b.x - b.r * 1.6, b.y - b.r * 1.6, b.x + b.r * 1.6, b.y + b.r * 1.6], fill=(*b.color, 45))
    ball_glow = ball_glow.filter(ImageFilter.GaussianBlur(2))
    base.alpha_composite(ball_glow)

    ball_flat = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    bfdraw = ImageDraw.Draw(ball_flat)
    for b in balls:
        bfdraw.ellipse([b.x - b.r, b.y - b.r, b.x + b.r, b.y + b.r], fill=(*b.color, 255))
    base.alpha_composite(ball_flat)

    box_stroke = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(box_stroke)
    sdraw.rounded_rectangle(BOX, radius=RADIUS, outline=(*state.box_tint, 235), width=3)
    base.alpha_composite(box_stroke)

    tx, ty = title_pos

    monkey_glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    mgdraw = ImageDraw.Draw(monkey_glow)
    mgdraw.text((tx + w_havoc, ty), "monkey", font=f_title, fill=(*state.monkey_color, 160))
    monkey_glow = monkey_glow.filter(ImageFilter.GaussianBlur(4))
    base.alpha_composite(monkey_glow)

    draw = ImageDraw.Draw(base)
    draw.text((tx, ty), "havoc-", font=f_title, fill=(*WHITE, 255))
    draw.text((tx + w_havoc, ty), "monkey", font=f_title, fill=(*state.monkey_color, 255))

    return base.convert("RGB")


def main(n_frames=140, frame_ms=50, out_name="mockup_membrane.gif", webp_out_name=None, seed=11,
         settle_frames=10, palette_colors=28, canvas=None, density_scale=1.0, max_balls=420,
         **overrides):
    for k, v in overrides.items():
        globals()[k] = v
    if canvas is not None:
        set_canvas(*canvas, density_scale=density_scale, max_balls=max_balls)
    random.seed(seed)
    balls = make_balls()
    state = State()

    probe = Image.new("RGB", (10, 10))
    pdraw = ImageDraw.Draw(probe)
    f_title, title_pos, w_havoc, rect_havoc, rect_monkey = title_rects(pdraw)

    for f in range(settle_frames):
        step(balls, state, -settle_frames + f)
        resolve_letters(balls, rect_havoc, rect_monkey, state, -settle_frames + f)

    raw_frames = []
    flip_count = 0
    for f in range(n_frames):
        step(balls, state, f)
        before = state.last_flip_frame
        resolve_letters(balls, rect_havoc, rect_monkey, state, f)
        if state.last_flip_frame != before:
            flip_count += 1
        raw_frames.append(render(balls, state, rect_havoc, rect_monkey, title_pos, f_title, w_havoc))

    # Quantize every frame to one shared palette instead of independent per-frame
    # adaptive palettes: keeps color indices stable across frames so the GIF's
    # LZW/frame-diffing compresses far better (~2x smaller in practice).
    #
    # The palette is built from a busy real frame (for natural gradient/glow
    # coverage) *plus* a swatch of our known key colors stitched below it, so rare-
    # but-important colors can't get starved of a slot: pure white text once had
    # so little pixel area in the sampled frame that the adaptive quantizer gave it
    # no slot at all and silently snapped it to the nearest survivor, teal.
    sample = raw_frames[len(raw_frames) // 2]
    swatch = Image.new("RGB", (sample.width, 140), CHARCOAL)
    sw_draw = ImageDraw.Draw(swatch)
    key_colors = [WHITE, PINK, TEAL]
    key_colors += [tuple((a + b) // 2 for a, b in zip(c, CHARCOAL)) for c in (WHITE, PINK, TEAL)]
    band_w = sample.width // len(key_colors)
    for i, c in enumerate(key_colors):
        sw_draw.rectangle([i * band_w, 0, (i + 1) * band_w, 140], fill=c)
    combined = Image.new("RGB", (sample.width, sample.height + swatch.height))
    combined.paste(sample, (0, 0))
    combined.paste(swatch, (0, sample.height))
    pal_img = combined.convert("P", palette=Image.ADAPTIVE, colors=palette_colors)
    frames = [img.quantize(palette=pal_img, dither=Image.Dither.NONE) for img in raw_frames]

    out = HERE / out_name
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=frame_ms, loop=0, optimize=True)
    print(f"wrote {out}  {len(frames)} frames  flips={flip_count}")

    if webp_out_name:
        # Skip the 256-color GIF palette entirely: libwebp's own lossy
        # compression handles the gradient glows natively, so this comes out
        # both higher-fidelity and a fraction of the GIF's size, which is what
        # actually fixes mobile choppiness (less to decode every loop).
        webp_out = HERE / webp_out_name
        raw_frames[0].save(
            webp_out, save_all=True, append_images=raw_frames[1:],
            duration=frame_ms, loop=0, quality=82, method=6, minimize_size=True,
        )
        print(f"wrote {webp_out}  {len(raw_frames)} frames  {webp_out.stat().st_size} bytes")

    return frames


if __name__ == "__main__":
    import sys
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 260
    main(n_frames=n)
