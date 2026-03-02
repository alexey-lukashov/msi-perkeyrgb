#!/usr/bin/env python

import sys
import argparse
from .protocol_data.msi_keymaps import AVAILABLE_MSI_KEYMAPS
from .config import load_config, load_steady, ConfigError
from .parsing import parse_model, parse_usb_id, parse_preset, UnknownModelError, UnknownIdError, UnknownPresetError
from .msi_keyboard import MSI_Keyboard
from .hidapi_wrapping import HID_Keyboard, HIDLibraryError, HIDNotFoundError, HIDOpenError
from time import sleep

VERSION = "2.2-alc"
DEFAULT_ID = "1038:1122"
ALC_ID = "1038:1161"
DEFAULT_MODEL = "GE63"


def set_alc_color(rgb):
    """Control lightbar/logo (ALC device) using raw HID packets."""
    try:
        alc_id = parse_usb_id(ALC_ID)
        alc = HID_Keyboard(alc_id)
    except Exception:
        print("Lightbar/logo (ALC) not found or no permissions, skipping.")
        return

    regions = [0x2a, 0x0b, 0x18, 0x24]
    for rid in regions:
        pkt = [0x0e, 0x00, rid, 0x00]
        for i in range(42):
            pkt += list(rgb) + [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00, i]
        while len(pkt) < 520:
            pkt.append(0x00)
        pkt += [0x08, 0x39]
        alc.send_feature_report(pkt)
    alc.send_output_report([0x09] + [0x00] * 63)


def main():
    parser = argparse.ArgumentParser(
        description='Tool to control per-key RGB keyboard backlighting on MSI laptops. https://github.com/Askannz/msi-perkeyrgb',
        epilog='Examples:\n'
               '  msi-perkeyrgb -d                     Disable all\n'
               '  msi-perkeyrgb -s ff0000               Red on all\n'
               '  msi-perkeyrgb --kbd -s ffffff          White keyboard only\n'
               '  msi-perkeyrgb --bar -s ff00ff          Magenta lightbar only\n'
               '  msi-perkeyrgb --bar -d                 Disable lightbar only\n',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('-v', '--version', action='store_true', help='Prints version and exits.')
    parser.add_argument('-c', '--config', action='store', metavar='FILEPATH',
                        help='Loads the configuration file located at FILEPATH.')
    parser.add_argument('-d', '--disable', action='store_true', help='Disable RGB lighting.')
    parser.add_argument('--id', action='store', metavar='VENDOR_ID:PRODUCT_ID',
                        help='Override vendor/product id. Hex format (example: 1038:1122)')
    parser.add_argument('--list-presets', action='store_true', help='List available presets for the given laptop model.')
    parser.add_argument('-p', '--preset', action='store', help='Use vendor preset (see --list-presets).')
    parser.add_argument('-m', '--model', action='store',
                        help='Set laptop model (see --list-models). Default: %s' % DEFAULT_MODEL)
    parser.add_argument('--list-models', action='store_true', help='List available laptop models.')
    parser.add_argument('-s', '--steady', action='store', metavar='HEXCOLOR',
                        help='Set a steady html color. ex. 00ff00 for green')
    parser.add_argument('--kbd', action='store_true', help='Target keyboard only')
    parser.add_argument('--bar', action='store_true', help='Target lightbar/logo only')

    args = parser.parse_args()

    # If neither --kbd nor --bar specified, target both
    do_kbd = True
    do_bar = True
    if args.kbd and not args.bar:
        do_kbd = True
        do_bar = False
    elif args.bar and not args.kbd:
        do_kbd = False
        do_bar = True

    if args.version:
        print("Version : %s" % VERSION)
        return

    if args.list_models:
        print("Available laptop models are :")
        for msi_models, _ in AVAILABLE_MSI_KEYMAPS:
            for model in msi_models:
                print(model)
        print("\nIf your laptop is not in this list, use the closest one.")
        return

    # Parse laptop model
    if not args.model:
        msi_model = DEFAULT_MODEL
    else:
        try:
            msi_model = parse_model(args.model)
        except UnknownModelError:
            print("Unknown MSI model : %s" % args.model)
            sys.exit(1)

    # Parse USB vendor/product ID
    if not args.id:
        usb_id = parse_usb_id(DEFAULT_ID)
    else:
        try:
            usb_id = parse_usb_id(args.id)
        except UnknownIdError:
            print("Unknown vendor/product ID : %s" % args.id)
            sys.exit(1)

    # Loading presets
    msi_presets = MSI_Keyboard.get_model_presets(msi_model)

    if args.list_presets:
        if msi_presets == {}:
            print("No presets available for %s." % msi_model)
        else:
            print("Available presets for %s:" % msi_model)
            for preset in msi_presets.keys():
                print("\t- %s" % preset)
        return

    # Loading keymap
    msi_keymap = MSI_Keyboard.get_model_keymap(msi_model)

    # Open keyboard (KLC) if needed
    kb = None
    if do_kbd:
        try:
            kb = MSI_Keyboard(usb_id, msi_keymap, msi_presets)
        except HIDLibraryError as e:
            print("Cannot open HIDAPI library : %s" % str(e))
            sys.exit(1)
        except HIDNotFoundError:
            if do_bar:
                print("Keyboard (KLC) not found, continuing with lightbar only.")
            else:
                print("No MSI keyboard found.")
                sys.exit(1)
        except HIDOpenError:
            if do_bar:
                print("Cannot open keyboard, continuing with lightbar only.")
            else:
                print("Cannot open keyboard. Check permissions on /dev/hidraw*")
                sys.exit(1)

    # Disable
    if args.disable:
        if kb and do_kbd:
            kb.set_color_all([0, 0, 0])
            kb.refresh()
            print("Keyboard: off")
        if do_bar:
            set_alc_color([0, 0, 0])
            print("Lightbar: off")

    # Preset
    elif args.preset:
        try:
            preset = parse_preset(args.preset, msi_presets)
        except UnknownPresetError:
            print("Preset %s not found for model %s." % (args.preset, msi_model))
            sys.exit(1)
        if kb and do_kbd:
            kb.set_preset(preset)
            kb.refresh()
            print("Keyboard: preset %s" % args.preset)
        if do_bar:
            print("Presets are not supported for lightbar.")

    # Config file
    elif args.config:
        try:
            colors_map, warnings = load_config(args.config, msi_keymap)
        except ConfigError as e:
            print("Error reading config file : %s" % str(e))
            sys.exit(1)
        for w in warnings:
            print("Warning :", w)
        if kb and do_kbd:
            kb.set_colors(colors_map)
            kb.refresh()
            print("Keyboard: config applied")
        if do_bar:
            print("Config files are not supported for lightbar.")

    # Steady color
    elif args.steady:
        color_hex = args.steady.lstrip('#')
        try:
            r = int(color_hex[0:2], 16)
            g = int(color_hex[2:4], 16)
            b = int(color_hex[4:6], 16)
        except (ValueError, IndexError):
            print("Invalid color: %s (use hex like ff0000)" % args.steady)
            sys.exit(1)

        if kb and do_kbd:
            try:
                colors_map, warnings = load_steady(color_hex, msi_keymap)
            except ConfigError as e:
                print("Error preparing steady color : %s" % str(e))
                sys.exit(1)
            kb.set_colors(colors_map)
            kb.refresh()
            print("Keyboard: #%s" % color_hex)
        if do_bar:
            set_alc_color([r, g, b])
            print("Lightbar: #%s" % color_hex)

    else:
        print("Nothing to do ! Use -d, -s, -p, or -c.")


if __name__ == '__main__':
    main()
