# wiz-cli

Control WiZ smart lights from the terminal. Discover bulbs, set colors, brightness, scenes, and more.

## Install

```bash
brew install ifesal/tools/wiz-cli
```

Or with pip:

```bash
pip install wiz-cli
```

## Usage

```bash
wiz discover                        # Find bulbs on your network
wiz rename 192.168.1.50 bedroom     # Name a bulb
wiz on bedroom                      # Turn on
wiz off bedroom                     # Turn off
wiz color bedroom 255 0 100         # Set RGB color
wiz brightness bedroom 128          # Set brightness (0-255)
wiz scene bedroom sunset            # Set a scene
wiz state bedroom                   # Get current state
wiz scenes                          # List all scenes
wiz on all                          # Turn on all named bulbs
wiz color desk+lamp 0 255 0         # Multiple bulbs with +
```

## Bulb Names

Bulb names are stored in `~/.config/wiz-cli/names.json`. Use `wiz rename <ip> <name>` to assign names.
