#!/usr/bin/env python3
"""CLI controller for WiZ smart lights."""

import argparse
import asyncio
import json
import os
import socket
import sys

from pywizlight import wizlight, PilotBuilder, discovery
from pywizlight.exceptions import WizLightConnectionError

_APP_DIR = os.path.join(os.path.expanduser("~"), ".config", "wiz-cli")
os.makedirs(_APP_DIR, exist_ok=True)
NAMES_FILE = os.path.join(_APP_DIR, "names.json")

SCENES = {
    "ocean": 1, "romance": 2, "sunset": 3, "party": 4,
    "fireplace": 5, "cozy": 6, "forest": 7, "pastel": 8,
    "wakeup": 9, "bedtime": 10, "warm_white": 11, "daylight": 12,
    "cool_white": 13, "nightlight": 14, "focus": 15,
    "relax": 16, "true_colors": 17, "tv_time": 18,
    "plant_growth": 19, "spring": 20, "summer": 21,
    "fall": 22, "deep_dive": 23, "jungle": 24,
    "mojito": 25, "club": 26, "christmas": 27,
    "halloween": 28, "candlelight": 29, "golden_white": 30,
    "pulse": 31, "steampunk": 32,
}


def _get_broadcast():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        parts = ip.split(".")
        parts[3] = "255"
        return ".".join(parts)
    except Exception:
        return "192.168.1.255"


def _load_names():
    if os.path.exists(NAMES_FILE):
        with open(NAMES_FILE) as f:
            return json.load(f)
    return {}


def _save_names(names):
    with open(NAMES_FILE, "w") as f:
        json.dump(names, f, indent=2)


def _resolve_target(target):
    names = _load_names()
    for ip, name in names.items():
        if name.lower() == target.lower():
            return ip
    return target


async def _resolve_targets(target_str):
    """Resolve targets. 'all' uses named bulbs, or discovers if none saved."""
    if target_str.lower() == "all":
        names = _load_names()
        if names:
            return list(names.keys())
        broadcast = _get_broadcast()
        print(f"Discovering bulbs on {broadcast}...")
        found = await discovery.discover_lights(broadcast_space=broadcast)
        if not found:
            print("No bulbs found on network.")
            return []
        return [b.ip for b in found]
    return [_resolve_target(t.strip()) for t in target_str.split("+")]


def _display_name(ip):
    names = _load_names()
    name = names.get(ip)
    return f"{name} ({ip})" if name else ip


async def cmd_discover(args):
    broadcast = args.broadcast or _get_broadcast()
    print(f"Discovering on {broadcast}...")
    found = await discovery.discover_lights(broadcast_space=broadcast)
    if not found:
        print("No bulbs found.")
        return
    for b in found:
        print(f"  {_display_name(b.ip)}")
    print(f"\n{len(found)} bulb(s) found.")


async def _run_on_bulb(ip, action):
    light = wizlight(ip)
    try:
        await action(light, ip)
    except (WizLightConnectionError, Exception) as e:
        print(f"  {_display_name(ip)}: error - {e}", file=sys.stderr)
    finally:
        await light.async_close()


async def cmd_on(args):
    ips = await _resolve_targets(args.target)
    pilot = PilotBuilder(brightness=args.brightness) if args.brightness else PilotBuilder()
    async def _on(light, ip):
        await light.turn_on(pilot)
        print(f"Turned on {_display_name(ip)}")
    await asyncio.gather(*[_run_on_bulb(ip, _on) for ip in ips])


async def cmd_off(args):
    ips = await _resolve_targets(args.target)
    async def _off(light, ip):
        await light.turn_off()
        print(f"Turned off {_display_name(ip)}")
    await asyncio.gather(*[_run_on_bulb(ip, _off) for ip in ips])


async def cmd_color(args):
    ips = await _resolve_targets(args.target)
    r, g, b = args.r, args.g, args.b
    async def _color(light, ip):
        await light.turn_on(PilotBuilder(rgb=(r, g, b)))
        print(f"Set {_display_name(ip)} to RGB({r}, {g}, {b})")
    await asyncio.gather(*[_run_on_bulb(ip, _color) for ip in ips])


async def cmd_brightness(args):
    ips = await _resolve_targets(args.target)
    level = max(1, min(255, args.level))
    async def _brightness(light, ip):
        if args.level == 0:
            await light.turn_off()
            print(f"Turned off {_display_name(ip)}")
        else:
            await light.turn_on(PilotBuilder(brightness=level))
            print(f"Set {_display_name(ip)} brightness to {level}")
    await asyncio.gather(*[_run_on_bulb(ip, _brightness) for ip in ips])


async def cmd_scene(args):
    ips = await _resolve_targets(args.target)
    scene_name = args.scene.lower().replace(" ", "_")
    if scene_name not in SCENES:
        print(f"Unknown scene '{args.scene}'. Available:")
        for s in sorted(SCENES):
            print(f"  {s}")
        return
    async def _scene(light, ip):
        await light.turn_on(PilotBuilder(scene=SCENES[scene_name]))
        print(f"Set {_display_name(ip)} to scene: {args.scene}")
    await asyncio.gather(*[_run_on_bulb(ip, _scene) for ip in ips])


async def cmd_state(args):
    ips = await _resolve_targets(args.target)
    async def _state(light, ip):
        state = await light.updateState()
        lines = [f"State of {_display_name(ip)}:"]
        try:
            lines.append(f"  Brightness: {state.get_brightness()}")
        except Exception:
            pass
        try:
            r, g, b = state.get_rgb()
            if r is not None:
                lines.append(f"  Color: RGB({r}, {g}, {b})")
        except Exception:
            pass
        try:
            temp = state.get_colortemp()
            if temp:
                lines.append(f"  Color Temp: {temp}K")
        except Exception:
            pass
        try:
            scene = state.get_scene()
            if scene:
                lines.append(f"  Scene: {scene}")
        except Exception:
            pass
        print("\n".join(lines))
    await asyncio.gather(*[_run_on_bulb(ip, _state) for ip in ips])


async def cmd_rename(args):
    ip = args.ip
    names = _load_names()
    names[ip] = args.name
    _save_names(names)
    print(f"Renamed {ip} → {args.name}")


async def cmd_scenes(_args):
    for name in sorted(SCENES):
        print(f"  {name}")


def main():
    parser = argparse.ArgumentParser(
        prog="wiz",
        description="WiZ Light CLI Controller",
    )
    sub = parser.add_subparsers(dest="command")

    # discover
    p = sub.add_parser("discover", aliases=["d"], help="Discover bulbs on network")
    p.add_argument("-b", "--broadcast", help="Broadcast address")

    # on
    p = sub.add_parser("on", help="Turn on a bulb")
    p.add_argument("target", help="Bulb IP/name (use + for multiple, or 'all')")
    p.add_argument("-B", "--brightness", type=int, help="Brightness (0-255)")

    # off
    p = sub.add_parser("off", help="Turn off a bulb")
    p.add_argument("target", help="Bulb IP/name (use + for multiple, or 'all')")

    # color
    p = sub.add_parser("color", aliases=["c"], help="Set bulb color")
    p.add_argument("target", help="Bulb IP/name (use + for multiple, or 'all')")
    p.add_argument("r", type=int, help="Red (0-255)")
    p.add_argument("g", type=int, help="Green (0-255)")
    p.add_argument("b", type=int, help="Blue (0-255)")

    # brightness
    p = sub.add_parser("brightness", aliases=["br"], help="Set brightness")
    p.add_argument("target", help="Bulb IP/name (use + for multiple, or 'all')")
    p.add_argument("level", type=int, help="Brightness (0-255)")

    # scene
    p = sub.add_parser("scene", aliases=["s"], help="Set a scene")
    p.add_argument("target", help="Bulb IP/name (use + for multiple, or 'all')")
    p.add_argument("scene", help="Scene name (use 'scenes' to list)")

    # state
    p = sub.add_parser("state", help="Get bulb state")
    p.add_argument("target", help="Bulb IP/name (use + for multiple, or 'all')")

    # rename
    p = sub.add_parser("rename", help="Name a bulb")
    p.add_argument("ip", help="Bulb IP")
    p.add_argument("name", help="Friendly name")

    # scenes list
    sub.add_parser("scenes", help="List available scenes")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    cmd_map = {
        "discover": cmd_discover, "d": cmd_discover,
        "on": cmd_on,
        "off": cmd_off,
        "color": cmd_color, "c": cmd_color,
        "brightness": cmd_brightness, "br": cmd_brightness,
        "scene": cmd_scene, "s": cmd_scene,
        "state": cmd_state,
        "rename": cmd_rename,
        "scenes": cmd_scenes,
    }
    try:
        asyncio.run(cmd_map[args.command](args))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
