# Human Typer (Ubuntu X11)

Types your clipboard at human speed (delays, typos, backspaces).
Uses OS-level X11 key events — no page scripts, no Selenium.

Humanization includes: Gaussian key delays, fluency bursts (fast zone vs
stumble), deferred typo corrections, longer pauses on punctuation/newlines,
longer-word slowdown, same-finger penalties, and light fatigue over long text.

## Layout (modular)

Each piece has one job:


| File                  | Role                                          |
| --------------------- | --------------------------------------------- |
| `typer.py`            | Core: hotkey, countdown, human typing         |
| `run.sh`              | Finds `DISPLAY` / X11, then starts `typer.py` |
| `setup.sh`            | One-time: venv + pip deps                     |
| `human-typer.service` | systemd unit template                         |
| `install-service.sh`  | Install **or update** the user service        |
| `requirements.txt`    | Python deps only                              |
| `.venv/`              | Isolated Python env (not edited by hand)      |




## Why not Docker?

Docker is the wrong tool here. This needs your **real keyboard, clipboard, and X11 display**. Containers isolate those by default, so hotkeys and typing into Chrome become fragile or broken. Use a **systemd user service** instead — it is the normal Linux way to keep a desktop helper running across logins and crashes.

## Setup (once)

```bash
sudo chown -R "$USER:$USER" /home/vk_lx/Desktop/MY_STUFF   # if files are root-owned
cd /home/vk_lx/Desktop/MY_STUFF/human-typer
chmod +x setup.sh install-service.sh run.sh
./setup.sh
./install-service.sh
```



## Daily use

1. Copy text (`Ctrl+C`)
2. Click **outside** the browser
3. Press **F8**
4. During the 3s countdown, click into the browser text box
5. Typing starts

Press **F8** again while typing to stop.

## Updating


| What you changed           | What to run                                              |
| -------------------------- | -------------------------------------------------------- |
| `typer.py` / `run.sh` only | `systemctl --user restart human-typer`                   |
| `human-typer.service`      | `./install-service.sh` (replaces unit + restarts)        |
| deps (`requirements.txt`)  | `./setup.sh` then `systemctl --user restart human-typer` |
| unsure / full refresh      | `./install-service.sh`                                   |


`./install-service.sh` **always overwrites** `~/.config/systemd/user/human-typer.service`, reloads systemd, and **restarts** the service.

### Service broken but manual run works?

Usually **not** an F8 conflict — plain F8 is free on most Ubuntu/GNOME setups. Common causes:

1. Service missing `DISPLAY` / `XAUTHORITY` (fixed in `run.sh`)
2. You still have `python typer.py` open in a terminal (two listeners fight)

```bash
cd ~/Desktop/MY_STUFF/human-typer
chmod +x doctor.sh
./doctor.sh
./install-service.sh
journalctl --user -u human-typer -f
```

## Service commands

```bash
systemctl --user status human-typer      # is it running?
journalctl --user -u human-typer -f     # live logs
systemctl --user restart human-typer    # after you edit typer.py
systemctl --user stop human-typer       # stop for now
systemctl --user disable --now human-typer  # remove from login startup
```

It starts with your desktop session and restarts if it crashes (`Restart=on-failure`).

### Change speed / delay permanently

Defaults are already set in `human-typer.service`:

```ini
Environment="HUMAN_TYPER_ARGS=--delay 2.5 --wpm 58 --mistake-prob 0.02"
```

Quotes are required (without them systemd only keeps `--delay` and the service crash-loops).

Edit that line in the **project** unit if you want different values, then re-apply:

```bash
./install-service.sh
```

Or edit only the installed copy at `~/.config/systemd/user/human-typer.service`, then `daemon-reload` + `restart` (that copy alone will be overwritten next time you run `./install-service.sh`).

## Manual run (without service)

```bash
cd /home/vk_lx/Desktop/MY_STUFF/human-typer
source .venv/bin/activate
python typer.py
```

## Options

| Flag | Default | Meaning |
|------|---------|---------|
| `--hotkey` | `<f8>` | Start/stop hotkey |
| `--delay` | `2.5` | Seconds after hotkey before typing |
| `--wpm` | `58` | Typing speed |
| `--mistake-prob` | `0.02` | Typo chance per letter |
| `--jitter` | `0.04` | Random delay noise |
| `--space-pause` | `0.08` | Extra pause after spaces |

