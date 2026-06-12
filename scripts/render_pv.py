#!/usr/bin/env python3
from __future__ import annotations

import math
import shutil
import subprocess
import textwrap
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "video"
FRAMES = OUT / "frames"
SPRITE = ROOT / "assets" / "zawa-spritesheet.webp"
W, H = 1280, 720
FPS = 24
CELL_W, CELL_H = 192, 208

FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"

PALETTE = {
    "ink": (24, 24, 22),
    "cream": (255, 249, 236),
    "paper": (244, 238, 222),
    "green": (127, 220, 149),
    "blue": (112, 167, 255),
    "amber": (242, 184, 75),
    "red": (224, 91, 82),
    "muted": (102, 105, 108),
    "dark": (31, 33, 31),
}

ROWS = {
    "idle": (0, 6),
    "running-right": (1, 8),
    "running-left": (2, 8),
    "waving": (3, 4),
    "jumping": (4, 5),
    "failed": (5, 8),
    "waiting": (6, 6),
    "running": (7, 6),
    "review": (8, 6),
}

SCENES = [
    {
        "seconds": 9,
        "state": "idle",
        "title": "ZAWA Agent",
        "subtitle": "An anxiety-powered onboarding buddy for Mantle.",
        "caption": "A character-driven guide that keeps beginners safe before they press Confirm.",
        "voice": "Meet ZAWA Agent, an anxiety-powered onboarding buddy for Mantle. It helps beginners stay safe before they press Confirm.",
        "mode": "hero",
    },
    {
        "seconds": 10,
        "state": "failed",
        "title": "The Problem",
        "subtitle": "New users lose money before they understand the basics.",
        "caption": "Wrong network. High gas. Suspicious links. Bad bridges. One click can drain a tiny wallet.",
        "voice": "For new Web3 users, the danger is not only hackers. It is wrong networks, high gas, suspicious links, and bridges they do not understand.",
        "mode": "danger",
    },
    {
        "seconds": 10,
        "state": "running",
        "title": "Step 1: Check The Wallet",
        "subtitle": "ZAWA reads the situation before giving advice.",
        "caption": "Wallet connected. Network checked. Balance and estimated gas compared.",
        "voice": "First, ZAWA checks the wallet, the network, the balance, and the estimated gas fee. No guessing. No rushing.",
        "mode": "console",
    },
    {
        "seconds": 11,
        "state": "waving",
        "title": "Step 2: Stop Risky Actions",
        "subtitle": "When the fee is too high, ZAWA interrupts.",
        "caption": "Wait. If the fee is bigger than the value, the safest move is to stop.",
        "voice": "If the action is too expensive or risky, ZAWA interrupts with a simple warning. Wait. The fee can be more dangerous than the transaction.",
        "mode": "warning",
    },
    {
        "seconds": 10,
        "state": "review",
        "title": "Step 3: Explain The Safest Route",
        "subtitle": "Small practical steps beat reckless trading.",
        "caption": "Use Mantle. Verify the source. Try free or low-cost tasks first.",
        "voice": "Then ZAWA explains the safest next step in plain language. Verify the source, use Mantle, and start with free or low-cost tasks.",
        "mode": "review",
    },
    {
        "seconds": 9,
        "state": "jumping",
        "title": "Step 4: Celebrate Safe Progress",
        "subtitle": "Tiny wins make onboarding memorable.",
        "caption": "The user completes a safe task. ZAWA celebrates the survival win.",
        "voice": "When the user completes a safe action, ZAWA celebrates. A tiny successful step becomes memorable, not confusing.",
        "mode": "success",
    },
    {
        "seconds": 10,
        "state": "waiting",
        "title": "Built For Hackathon UX",
        "subtitle": "Not just a chatbot. A face-acting risk manager.",
        "caption": "ZAWA turns onboarding into a living safety layer for first-time Mantle users.",
        "voice": "This is not just another chatbot. ZAWA is a face-acting risk manager, turning Mantle onboarding into a living safety layer.",
        "mode": "final",
    },
]


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(BOLD if bold else FONT, size)


def rounded(draw: ImageDraw.ImageDraw, box, fill, outline=PALETTE["ink"], width=2):
    draw.rounded_rectangle(box, radius=8, fill=fill, outline=outline, width=width)


def text(draw: ImageDraw.ImageDraw, xy, body: str, size: int, fill, bold=False, max_chars=36, leading=1.18):
    f = font(size, bold)
    lines = []
    for part in body.split("\n"):
        lines.extend(textwrap.wrap(part, max_chars) or [""])
    x, y = xy
    for line in lines:
        draw.text((x, y), line, font=f, fill=fill)
        y += int(size * leading)
    return y


def sprite_frame(sheet: Image.Image, state: str, tick: int) -> Image.Image:
    row, frames = ROWS[state]
    idx = tick % frames
    crop = sheet.crop((idx * CELL_W, row * CELL_H, (idx + 1) * CELL_W, (row + 1) * CELL_H))
    return crop.resize((CELL_W * 2, CELL_H * 2), Image.Resampling.NEAREST)


def draw_ui_card(draw: ImageDraw.ImageDraw, scene: dict):
    rounded(draw, (735, 116, 1168, 548), PALETTE["cream"])
    text(draw, (766, 148), "Risk Console", 28, PALETTE["ink"], True)
    checks = [
        ("Wallet", "Connected", "pass"),
        ("Network", "Mantle", "pass"),
        ("Gas", "Too expensive" if scene["mode"] in {"danger", "warning"} else "Acceptable", "fail" if scene["mode"] in {"danger", "warning"} else "pass"),
        ("Action", "Verify source" if scene["mode"] == "danger" else "Low-cost route", "fail" if scene["mode"] == "danger" else "pass"),
    ]
    y = 205
    for label, value, kind in checks:
        color = {"pass": PALETTE["green"], "fail": PALETTE["red"], "warn": PALETTE["amber"]}[kind]
        draw.rectangle((766, y, 782, y + 16), fill=color, outline=PALETTE["ink"], width=2)
        draw.text((796, y - 4), label, font=font(18, True), fill=PALETTE["ink"])
        draw.text((930, y - 4), value, font=font(18), fill=PALETTE["muted"])
        y += 58
    risk = "82" if scene["mode"] in {"danger", "warning"} else "18"
    rounded(draw, (956, 430, 1108, 508), PALETTE["red"] if risk == "82" else PALETTE["green"])
    draw.text((1002, 442), risk, font=font(38, True), fill=PALETTE["ink"])
    draw.text((1000, 486), "RISK", font=font(12, True), fill=PALETTE["ink"])


def draw_frame(sheet: Image.Image, scene: dict, tick: int, subtitle: str) -> Image.Image:
    img = Image.new("RGB", (W, H), PALETTE["paper"])
    draw = ImageDraw.Draw(img)

    for x in range(0, W, 32):
        draw.line((x, 0, x, H), fill=(229, 221, 203), width=1)
    for y in range(0, H, 32):
        draw.line((0, y, W, y), fill=(229, 221, 203), width=1)

    draw.rectangle((0, 0, W, H), outline=PALETTE["ink"], width=8)
    draw.rectangle((36, 36, 684, 604), fill=PALETTE["dark"], outline=PALETTE["ink"], width=3)
    draw.text((68, 66), scene["title"], font=font(46, True), fill=PALETTE["cream"])
    text(draw, (70, 128), scene["subtitle"], 24, (188, 203, 178), False, 30)

    zawa = sprite_frame(sheet, scene["state"], tick)
    img.paste(zawa, (188, 176), zawa)

    dialogue_fill = {
        "danger": PALETTE["red"],
        "warning": PALETTE["amber"],
        "success": PALETTE["green"],
    }.get(scene["mode"], PALETTE["cream"])
    rounded(draw, (74, 512, 646, 580), dialogue_fill)
    text(draw, (96, 529), scene["caption"], 22, PALETTE["ink"], True, 46)

    if scene["mode"] == "hero":
        rounded(draw, (735, 116, 1168, 548), PALETTE["cream"])
        text(draw, (770, 152), "What it does", 30, PALETTE["ink"], True)
        bullets = ["Checks wallet status", "Checks Mantle network", "Compares gas with balance", "Warns before risky clicks"]
        y = 220
        for b in bullets:
            draw.rectangle((770, y + 4, 786, y + 20), fill=PALETTE["green"], outline=PALETTE["ink"], width=2)
            draw.text((806, y), b, font=font(22, True), fill=PALETTE["ink"])
            y += 58
    elif scene["mode"] == "final":
        rounded(draw, (735, 116, 1168, 548), PALETTE["cream"])
        text(draw, (770, 150), "Hackathon Pitch", 30, PALETTE["ink"], True)
        text(draw, (770, 214), "A memorable safety layer for first-time Mantle users, powered by an emotional AI companion.", 28, PALETTE["ink"], True, 26)
        rounded(draw, (770, 422, 1100, 492), PALETTE["green"])
        draw.text((810, 440), "ZAWA Agent", font=font(28, True), fill=PALETTE["ink"])
    else:
        draw_ui_card(draw, scene)

    draw.rectangle((0, 622, W, H), fill=(20, 20, 19))
    text(draw, (72, 642), subtitle, 22, PALETTE["cream"], True, 96)
    return img


def wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as f:
        return f.getnframes() / f.getframerate()


def concat_wavs(paths: list[Path], output: Path, pause_seconds: float = 0.35) -> None:
    params = None
    chunks = []
    for path in paths:
        with wave.open(str(path), "rb") as f:
            if params is None:
                params = f.getparams()
            elif f.getparams()[:3] != params[:3]:
                raise SystemExit(f"wav params differ: {path}")
            chunks.append(f.readframes(f.getnframes()))

    if params is None:
        raise SystemExit("no wav files to concatenate")

    silence_frames = int(params.framerate * pause_seconds)
    silence = b"\x00" * silence_frames * params.nchannels * params.sampwidth
    with wave.open(str(output), "wb") as out:
        out.setparams(params)
        for chunk in chunks:
            out.writeframes(chunk)
            out.writeframes(silence)


def main() -> None:
    OUT.mkdir(exist_ok=True)
    if FRAMES.exists():
        shutil.rmtree(FRAMES)
    FRAMES.mkdir(exist_ok=True)
    script_path = OUT / "zawa-pv-script.txt"
    script_path.write_text("\n\n".join(scene["voice"] for scene in SCENES) + "\n", encoding="utf-8")

    scene_wavs = []
    durations = []
    for idx, scene in enumerate(SCENES, start=1):
        voice_txt = OUT / f"voice-{idx:02d}.txt"
        voice_aiff = OUT / f"voice-{idx:02d}.aiff"
        voice_wav = OUT / f"voice-{idx:02d}.wav"
        voice_txt.write_text(scene["voice"], encoding="utf-8")
        subprocess.run(["say", "-v", "Samantha", "-r", "168", "-o", str(voice_aiff), "-f", str(voice_txt)], check=True)
        subprocess.run(
            ["/opt/homebrew/bin/ffmpeg", "-y", "-i", str(voice_aiff), "-ar", "48000", "-ac", "2", str(voice_wav)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        scene_wavs.append(voice_wav)
        durations.append(wav_duration(voice_wav) + 0.6)

    voice_wav = OUT / "zawa-pv-voice.wav"
    concat_wavs(scene_wavs, voice_wav)
    total_seconds = sum(durations)
    if total_seconds > 89:
        raise SystemExit(f"video would be {total_seconds:.1f}s; shorten script")

    sheet = Image.open(SPRITE).convert("RGBA")
    srt_lines = []
    frame_index = 0
    elapsed = 0.0
    for i, (scene, seconds) in enumerate(zip(SCENES, durations), start=1):
        start = elapsed
        end = elapsed + seconds
        srt_lines.append(f"{i}\n{stamp(start)} --> {stamp(end)}\n{scene['voice']}\n")
        frames = math.ceil(seconds * FPS)
        for local in range(frames):
            tick = local // max(1, FPS // 8)
            img = draw_frame(sheet, scene, tick, scene["voice"])
            img.save(FRAMES / f"frame_{frame_index:05d}.png")
            frame_index += 1
        elapsed = end

    srt_path = OUT / "zawa-pv-subtitles.srt"
    srt_path.write_text("\n".join(srt_lines), encoding="utf-8")

    silent = OUT / "zawa-pv-silent.mp4"
    final = OUT / "zawa-agent-pv.mp4"
    subprocess.run(
        [
            "/opt/homebrew/bin/ffmpeg",
            "-y",
            "-framerate",
            str(FPS),
            "-i",
            str(FRAMES / "frame_%05d.png"),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-r",
            str(FPS),
            str(silent),
        ],
        check=True,
    )
    subprocess.run(
        [
            "/opt/homebrew/bin/ffmpeg",
            "-y",
            "-i",
            str(silent),
            "-i",
            str(voice_wav),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            str(final),
        ],
        check=True,
    )
    print(final)
    print(f"duration_seconds={total_seconds:.2f}")


def stamp(seconds: float) -> str:
    ms = int(round((seconds - int(seconds)) * 1000))
    whole = int(seconds)
    h = whole // 3600
    m = (whole % 3600) // 60
    s = whole % 60
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


if __name__ == "__main__":
    main()
