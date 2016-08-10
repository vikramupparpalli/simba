#!/usr/bin/env python

import sys
import time
import struct
import re
import zlib
import argparse
import os

from ConfigParser import ConfigParser
from collections import OrderedDict


MAJOR=1
MINOR=0

SETTINGS_H_FILENAME = "settings.h"
SETTINGS_C_FILENAME = "settings.c"
SETTINGS_BIN_LITTLE_FILENAME = "settings.little-endian.bin"
SETTINGS_BIN_BIG_FILENAME = "settings.big-endian.bin"

HEADER_FMT = """/**
 * @file {filename}
 * @version 6.0.0
 *
 * @section License
 * Copyright (C) 2014-2016, Erik Moqvist
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2.1 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * This file is part of the Simba project.
 */

/**
 * This file was generated by settings.py {major}.{minor} {date}.
 */

#ifndef __SETTINGS_H__
#define __SETTINGS_H__

#include "simba.h"

{addresses}

{sizes}

{types}

{values}

#endif
"""

SOURCE_FMT = """/**
 * @file {filename}
 * @version 6.0.0
 *
 * @section License
 * Copyright (C) 2014-2016, Erik Moqvist
 *
 * This library is free software; you can redistribute it and/or
 * modify it under the terms of the GNU Lesser General Public
 * License as published by the Free Software Foundation; either
 * version 2.1 of the License, or (at your option) any later version.
 *
 * This library is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * Lesser General Public License for more details.
 *
 * This file is part of the Simba project.
 */

/**
 * This file was generated by settings.py {major}.{minor} {date}.
 */

#include "simba.h"

{settings_names}

const FAR struct setting_t settings[]
__attribute__ ((weak)) = {{
{settings_array}
    {{ NULL, 0, 0, 0 }}
}};

#if defined(ARCH_AVR)

uint8_t settings_area[CONFIG_SETTINGS_AREA_SIZE]
__attribute__ ((section (".eeprom"), weak)) = {{
{content_little}
}};

const FAR uint8_t settings_default_area[]
__attribute__ ((weak)) = {{
{content_little}
}};

#elif defined(ARCH_ARM)

uint8_t settings_area[2][CONFIG_SETTINGS_AREA_SIZE]
__attribute__ ((section (".settings"), weak)) = {{
    {{
    {content_little}
    }},
    {{
    {content_little}
    }}
}};

uint8_t settings_default_area[CONFIG_SETTINGS_AREA_SIZE]
__attribute__ ((section (".settings"), weak)) = {{
    {content_little}
}};

#else

const uint8_t settings_default_area[CONFIG_SETTINGS_AREA_SIZE]
__attribute__ ((weak)) = {{
{content_little}
}};

#endif
"""

re_integer = re.compile(r"(?P<sign>)int(?P<bits>\d+)_t")


def parse_settings_file(filename):
    settings_parser = ConfigParser()
    settings_parser.read(filename)

    addresses = []
    sizes = []
    values = []
    types = []

    for item in settings_parser.items("addresses"):
        addresses.append((item[0], int(item[1], 0)))

    for item in settings_parser.items("sizes"):
        sizes.append((item[0], int(item[1], 0)))

    for item in settings_parser.items("types"):
        types.append((item[0], item[1]))

    for item in settings_parser.items("values"):
        values.append((item[0], item[1]))

    addresses.sort(key=lambda item: item[1])

    return addresses, sizes, types, values


def create_settings_dict(addresses, sizes, types, values):
    settings = OrderedDict()

    for name, address in addresses:
        settings[name] = {"address": address}

    for name, size in sizes:
        if name not in settings:
            sys.stderr.write("{}: no address for setting\n".format(name))
            sys.exit(1)
        settings[name]["size"] = size

    for name, type in types:
        if name not in settings:
            sys.stderr.write("{}: no address for setting\n".format(name))
            sys.exit(1)
        settings[name]["type"] = type

    for name, value in values:
        if name not in settings:
            sys.stderr.write("{}: no address for setting\n".format(name))
            sys.exit(1)
        settings[name]["value"] = value

    return settings


def create_binary_content(settings, settings_size, endianess):
    endianess_prefix = ">" if endianess == "big" else "<"

    # create the setting file content
    content = ""

    for _, item in settings.items():
        # add padding between previous setting and this one
        content += "\xff" * (item["address"] - len(content))
        # add the value
        if item["type"] == "string_t":
            if item["size"] <= len(item["value"]):
                sys.stderr.write("{}: value does not fit in size {}\n".format(
                    item["value"],
                    item["size"]))
                sys.exit(1)
            content += item["value"]
            # null termination
            content += "\x00"
        elif re_integer.match(item["type"]):
            bits_to_fmt = {
                8: "b",
                16: "h",
                32: "i"
            }
            mo = re_integer.match(item["type"])
            sign = mo.group("sign")
            bits = int(mo.group("bits"))
            if bits not in [8, 16, 32]:
                sys.stderr.write("{}: bad type\n".format(item["type"]))
                sys.exit(1)
            if bits / 8 != item["size"]:
                sys.stderr.write("{}: bad length of {}\n".format(item["size"],
                                                                 item["type"]))
                sys.exit(1)
            fmt = bits_to_fmt[bits]
            if sign == "u":
                fmt.upper()
            content += struct.pack(endianess_prefix + fmt, int(item["value"], 0))
        else:
            sys.stderr.write("{}: bad type\n".format(item["type"]))
            sys.exit(1)

    if len(content) > settings_size:
        fmt = "Settings area of size {} does not fit in memory of size {}.\n"
        sys.stderr.write(fmt.format(len(content), settings_size))
        sys.exit(1)

    # pad the rest of the area and calculate a crc32
    content += '\xff' * (settings_size - 4 - len(content))
    crc = (zlib.crc32(content) & 0xffffffff)
    content += struct.pack(endianess_prefix + 'I', crc)

    return content


def create_header_file(outdir,
                       settings):

    addresses = []
    sizes = []
    types = []
    values = []

    for name, item in settings.items():
        addresses.append("#define SETTING_{name}_ADDR {value}"
                         .format(name=name.upper(), value=item["address"]))
        sizes.append("#define SETTING_{name}_SIZE {value}"
                     .format(name=name.upper(), value=item["size"]))
        types.append("#define SETTING_{name}_TYPE setting_type_{value}_t"
                     .format(name=name.upper(), value=item["type"]))
        values.append("#define SETTING_{name}_VALUE {value}"
                      .format(name=name.upper(), value=item["value"]))

    now = time.strftime("%Y-%m-%d %H:%M %Z")

    # write to settings header file
    with open(os.path.join(outdir, SETTINGS_H_FILENAME), "w") as fout:
        fout.write(HEADER_FMT.format(filename=SETTINGS_H_FILENAME,
                                     date=now,
                                     major=MAJOR,
                                     minor=MINOR,
                                     addresses="\n".join(addresses),
                                     sizes="\n".join(sizes),
                                     types="\n".join(types),
                                     values="\n".join(values)))


def create_binary_file(outdir,
                       content_little,
                       content_big):
    """Write the content to the setting file.

    """

    with open(os.path.join(outdir, SETTINGS_BIN_LITTLE_FILENAME), "wb") as fout:
        fout.write(content_little)

    with open(os.path.join(outdir, SETTINGS_BIN_BIG_FILENAME), "wb") as fout:
        fout.write(content_big)


def create_source_file(outdir,
                       settings_size,
                       content_little,
                       content_big,
                       settings):
    now = time.strftime("%Y-%m-%d %H:%M %Z")

    settings_names = []
    settings_array = []

    for name, item in settings.items():
        settings_names.append(
            "static const FAR char {name}_name[] = \"{name}\";".format(name=name))
        settings_array.append(
            "    {{ .name_p = {name}_name, .type = setting_type_{type}, "
            ".address = {address}, "
            ".size = {size} }},".format(name=name,
                                        type=item["type"],
                                        address=item["address"],
                                        size=item["size"]))

    content_little_bytes = ['{:#04x}'.format(ord(byte))
                            for byte in content_little]
    content_big_bytes = ['{:#04x}'.format(ord(byte))
                         for byte in content_big]

    content_little_string = ',\n'.join(
        ['    ' + ', '.join(content_little_bytes[i:i+8])
         for i in range(0, len(content_little_bytes), 8)])

    content_big_string = ',\n'.join(
        ['    ' + ', '.join(content_big_bytes[i:i+8])
         for i in range(0, len(content_big_bytes), 8)])

    # write to setting source file
    with open(os.path.join(outdir, SETTINGS_C_FILENAME), "w") as fout:
        fout.write(SOURCE_FMT.format(filename=SETTINGS_C_FILENAME,
                                     date=now,
                                     major=MAJOR,
                                     minor=MINOR,
                                     settings_names='\n'.join(settings_names),
                                     settings_array='\n'.join(settings_array),
                                     content_little=content_little_string,
                                     content_big=content_big_string))


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--output-directory", default=".")
    parser.add_argument("--settings-size", type=int, default=256)
    parser.add_argument("settings")

    args = parser.parse_args()

    items = parse_settings_file(args.settings)
    settings = create_settings_dict(*items)

    content_little = create_binary_content(settings,
                                           args.settings_size,
                                           "little")

    content_big = create_binary_content(settings,
                                        args.settings_size,
                                        "big")

    create_header_file(args.output_directory,
                       settings)
    create_binary_file(args.output_directory,
                       content_little,
                       content_big)
    create_source_file(args.output_directory,
                       args.settings_size,
                       content_little,
                       content_big,
                       settings)

if __name__ == "__main__":
    main()
