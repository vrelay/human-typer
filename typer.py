#!/usr/bin/env python3
"""
Clipboard human typer for X11.

Workflow:
  1. Copy text (Ctrl+C)
  2. Click OUTSIDE the browser (desktop / another window)
  3. Press hotkey (default: F8)
  4. During the countdown, click into the browser text box
  5. Typing starts after the gap — site never sees the hotkey
"""

from __future__ import annotations

import argparse
import random
import sys
import threading
import time

import pyperclip
from pynput import keyboard
from pynput.keyboard import Controller, Key, GlobalHotKeys

# Neighbor keys on QWERTY (for realistic typos)
NEIGHBORS = {
    "a": "sqwz",
    "b": "vghn",
    "c": "xdfv",
    "d": "erfcxs",
    "e": "rdsw",
    "f": "rtgvcd",
    "g": "tyhbvf",
    "h": "yujnbg",
    "i": "uojk",
    "j": "uiknmh",
    "k": "iolmj",
    "l": "opk",
    "m": "njk",
    "n": "bhjm",
    "o": "iplk",
    "p": "ol",
    "q": "wa",
    "r": "edft",
    "s": "weadzx",
    "t": "rfgy",
    "u": "yhji",
    "v": "cfgb",
    "w": "qeas",
    "x": "zsdc",
    "y": "tghu",
    "z": "asx",
}

kb = Controller()
state_lock = threading.Lock()
typing_active = False
stop_requested = False

# Same-finger pairs (rough QWERTY left/right finger collisions) — slight slowdown
SAME_FINGER = {
    "qaz", "wsx", "edc", "rfvtgb", "yhnujm", "ik", "ol", "p",
}


def wpm_to_delay(wpm: float) -> float:
    # ~5 chars per word
    return 60.0 / (wpm * 5.0)


def gauss_sleep(mean: float, sigma: float, minimum: float = 0.012) -> None:
    """Gaussian pause — more natural than flat uniform jitter."""
    time.sleep(max(minimum, random.gauss(mean, max(0.004, sigma))))


def human_delay(base: float, jitter: float, extra: float = 0.0) -> None:
    # jitter used as sigma; keep name for CLI compatibility
    gauss_sleep(base + extra, jitter * 1.1)


def type_char(ch: str) -> None:
    if ch == "\n":
        kb.press(Key.enter)
        kb.release(Key.enter)
    elif ch == "\t":
        kb.press(Key.tab)
        kb.release(Key.tab)
    else:
        kb.type(ch)


def backspace_n(n: int, base: float, jitter: float) -> None:
    for _ in range(n):
        if stop_requested:
            return
        kb.press(Key.backspace)
        kb.release(Key.backspace)
        human_delay(base * 0.65, jitter * 0.5)


def maybe_typo(ch: str) -> str | None:
    low = ch.lower()
    if low not in NEIGHBORS:
        return None
    wrong = random.choice(NEIGHBORS[low])
    return wrong.upper() if ch.isupper() else wrong


def same_finger(a: str, b: str) -> bool:
    a, b = a.lower(), b.lower()
    if not a.isalpha() or not b.isalpha() or a == b:
        return a == b and a.isalpha()
    for group in SAME_FINGER:
        if a in group and b in group:
            return True
    return False


def word_len_at(text: str, i: int) -> int:
    """Length of the alphanumeric run containing index i."""
    if i < 0 or i >= len(text) or not text[i].isalnum():
        return 0
    start = i
    while start > 0 and text[start - 1].isalnum():
        start -= 1
    end = i
    while end + 1 < len(text) and text[end + 1].isalnum():
        end += 1
    return end - start + 1


def type_human(
    text: str,
    wpm: float,
    mistake_prob: float,
    jitter: float,
    space_pause: float,
) -> None:
    global typing_active, stop_requested
    base = wpm_to_delay(wpm)

    with state_lock:
        typing_active = True
        stop_requested = False

    print("\n>>> Typing started. Press the same hotkey again to STOP.\n", flush=True)

    # Fluency bursts: "in the zone" vs "stumbling"
    in_zone = random.random() < 0.65
    chars_left_in_state = random.randint(14, 42)
    prev = ""

    i = 0
    while i < len(text):
        if stop_requested:
            print("\n>>> Stopped by hotkey.\n", flush=True)
            break

        # Switch fluency state periodically
        chars_left_in_state -= 1
        if chars_left_in_state <= 0:
            in_zone = not in_zone
            chars_left_in_state = (
                random.randint(18, 55) if in_zone else random.randint(8, 22)
            )

        speed_mul = 0.82 if in_zone else 1.28
        # Slight fatigue over long pastes
        fatigue = 1.0 + min(0.18, i / max(1, len(text)) * 0.18)
        # Harder / longer words are a bit slower
        wl = word_len_at(text, i)
        hard_mul = 1.0 + (0.08 if wl >= 8 else 0.0) + (0.06 if wl >= 12 else 0.0)

        ch = text[i]
        local_base = base * speed_mul * fatigue * hard_mul
        local_jitter = jitter * (0.85 if in_zone else 1.35)

        # --- typo paths ---
        did_special = False
        if ch.isalpha() and random.random() < mistake_prob:
            wrong = maybe_typo(ch)
            if wrong:
                # Deferred correction: keep typing a bit, then fix (more human)
                if random.random() < 0.55:
                    type_char(wrong)
                    human_delay(local_base, local_jitter, extra=random.uniform(0.05, 0.15))
                    ahead = 0
                    max_ahead = random.randint(1, 3)
                    while (
                        ahead < max_ahead
                        and i + 1 + ahead < len(text)
                        and text[i + 1 + ahead].isalnum()
                    ):
                        type_char(text[i + 1 + ahead])
                        human_delay(local_base, local_jitter)
                        ahead += 1
                    # "oops" pause
                    gauss_sleep(random.uniform(0.28, 0.65), 0.08)
                    backspace_n(1 + ahead, local_base, local_jitter)
                    gauss_sleep(random.uniform(0.08, 0.2), 0.03)
                    # retype correct slice
                    for k in range(0, ahead + 1):
                        if stop_requested:
                            break
                        type_char(text[i + k])
                        extra = 0.0
                        if text[i + k] == " ":
                            extra = space_pause
                        human_delay(local_base, local_jitter, extra=extra)
                    prev = text[i + ahead] if ahead >= 0 else ch
                    i += ahead + 1
                    did_special = True
                else:
                    # Immediate fix (sometimes +1 extra wrong char)
                    type_char(wrong)
                    human_delay(local_base, local_jitter, extra=random.uniform(0.08, 0.25))
                    extra_wrong = 0
                    if (
                        random.random() < 0.35
                        and i + 1 < len(text)
                        and text[i + 1].isalpha()
                    ):
                        w2 = maybe_typo(text[i + 1])
                        if w2:
                            type_char(w2)
                            extra_wrong = 1
                            human_delay(
                                local_base, local_jitter, extra=random.uniform(0.12, 0.35)
                            )
                    backspace_n(1 + extra_wrong, local_base, local_jitter)
                    human_delay(local_base, local_jitter, extra=random.uniform(0.05, 0.15))

        if did_special:
            continue

        type_char(ch)

        extra = 0.0
        if ch == " ":
            extra += space_pause + random.uniform(0.0, 0.06)
        elif ch in ".,!?;:":
            extra += random.uniform(0.18, 0.55)
        elif ch == "\n":
            extra += random.uniform(0.35, 0.95)
        elif ch.isupper():
            extra += random.uniform(0.02, 0.08)

        # Same finger / double letter motor slowdown
        if prev and same_finger(prev, ch):
            extra += random.uniform(0.025, 0.07)

        # Occasional thinking pause (more often when stumbling)
        think_p = 0.012 if in_zone else 0.04
        if random.random() < think_p:
            extra += random.uniform(0.4, 1.1)

        human_delay(local_base, local_jitter, extra=extra)
        prev = ch
        i += 1

    with state_lock:
        typing_active = False
        stop_requested = False
    print(
        "\n>>> Done. Waiting for next hotkey (Ctrl+C in this terminal to quit).\n",
        flush=True,
    )


def countdown(seconds: float) -> None:
    whole = int(seconds)
    frac = seconds - whole
    for left in range(whole, 0, -1):
        print(f"  Focus the text box now... {left}", flush=True)
        time.sleep(1)
    if frac > 0:
        time.sleep(frac)
    print("  Go!\n", flush=True)


def run_once(args: argparse.Namespace) -> None:
    text = pyperclip.paste()
    if not text or not text.strip():
        print("Clipboard is empty. Copy text first, then press the hotkey.")
        return

    preview = text.replace("\n", "\\n")
    if len(preview) > 80:
        preview = preview[:77] + "..."
    print(f"\nClipboard ready ({len(text)} chars): {preview}")
    print(f"Countdown: {args.delay:.1f}s — click into the browser field now.")
    countdown(args.delay)
    type_human(
        text=text,
        wpm=args.wpm,
        mistake_prob=args.mistake_prob,
        jitter=args.jitter,
        space_pause=args.space_pause,
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Human-like clipboard typer (X11)")
    p.add_argument(
        "--hotkey",
        default="<f8>",
        help='pynput hotkey, default <f8>. Examples: <f8>, <ctrl>+<shift>+v',
    )
    p.add_argument(
        "--delay",
        type=float,
        default=2.5,
        help="Seconds after hotkey before typing starts (default: 2.5)",
    )
    p.add_argument("--wpm", type=float, default=58.0, help="Typing speed (default: 58)")
    p.add_argument(
        "--mistake-prob",
        type=float,
        default=0.02,
        help="Chance of a typo per letter (default: 0.02)",
    )
    p.add_argument(
        "--jitter",
        type=float,
        default=0.04,
        help="Random delay jitter in seconds (default: 0.04)",
    )
    p.add_argument(
        "--space-pause",
        type=float,
        default=0.08,
        help="Extra pause after spaces (default: 0.08)",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    def on_hotkey() -> None:
        global typing_active, stop_requested
        with state_lock:
            if typing_active:
                stop_requested = True
                print("Stop requested...")
                return
        # run in background so hotkey listener stays alive
        threading.Thread(target=run_once, args=(args,), daemon=True).start()

    mapping = {args.hotkey: on_hotkey}

    print("Human Typer ready (X11)")
    print(f"  Hotkey : {args.hotkey}")
    print(f"  Delay  : {args.delay}s after hotkey")
    print(f"  Speed  : {args.wpm} WPM")
    print()
    print("Steps:")
    print("  1. Copy your text")
    print("  2. Click OUTSIDE the browser (so the site does not see the hotkey)")
    print(f"  3. Press {args.hotkey}")
    print("  4. During the countdown, click into the browser text box")
    print("  5. Typing starts automatically")
    print()
    print("Press Ctrl+C here to quit.\n")

    try:
        with GlobalHotKeys(mapping) as h:
            h.join()
    except KeyboardInterrupt:
        print("\nBye.")
        sys.exit(0)


if __name__ == "__main__":
    main()
