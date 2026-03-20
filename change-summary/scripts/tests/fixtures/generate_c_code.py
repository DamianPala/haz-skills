#!/usr/bin/env python3
"""Generate synthetic C code for test fixtures.

Produces realistic-looking embedded C modules with controllable size.
Each function has ~10-15 lines, making diffs meaningful and reviewable.
"""

from __future__ import annotations

import sys


def generate_module(
    module_name: str,
    functions: list[dict[str, str | int]],
    includes: list[str] | None = None,
    static_vars: list[str] | None = None,
) -> tuple[str, str]:
    """Generate a .c and .h file pair.

    Returns (source_content, header_content).
    """
    guard = f"{module_name.upper()}_H"
    includes = includes or []
    static_vars = static_vars or []

    # Header
    h_lines = [f"#pragma once", ""]
    for inc in includes:
        h_lines.append(f'#include "{inc}"')
    if includes:
        h_lines.append("")
    for func in functions:
        h_lines.append(f"{func['ret']} {func['name']}({func['args']});")
    h_lines.append("")

    # Source
    c_lines = [f'#include "{module_name}.h"', ""]
    for inc in includes:
        c_lines.append(f'#include "{inc}"')
    if includes:
        c_lines.append("")
    for var in static_vars:
        c_lines.append(var)
    if static_vars:
        c_lines.append("")

    for func in functions:
        c_lines.append(f"{func['ret']} {func['name']}({func['args']}) {{")
        body = func.get("body", "")
        if body:
            for line in str(body).split("\n"):
                c_lines.append(f"    {line}")
        c_lines.append("}")
        c_lines.append("")

    return "\n".join(c_lines), "\n".join(h_lines)


def sensor_v1() -> tuple[str, str]:
    """Initial sensor module: init + 8-channel read + config."""
    funcs = [
        {"ret": "void", "name": "sensor_init", "args": "void", "body": "\n".join([
            "for (int i = 0; i < MAX_CHANNELS; i++) {",
            "    channels[i].value = 0;",
            "    channels[i].type = SENSOR_NONE;",
            "    channels[i].enabled = 0;",
            "    channels[i].sample_count = 0;",
            "    channels[i].last_read_ms = 0;",
            "}",
            "initialized = 1;",
        ])},
        {"ret": "int", "name": "sensor_read", "args": "int ch", "body": "\n".join([
            "if (!initialized) return SENSOR_ERR_NOT_INIT;",
            "return channels[ch].value;",
        ])},
        {"ret": "int", "name": "sensor_configure", "args": "int ch, SensorType type, int interval_ms", "body": "\n".join([
            "channels[ch].type = type;",
            "channels[ch].enabled = 1;",
            "channels[ch].interval_ms = interval_ms;",
            "channels[ch].sample_count = 0;",
            "return SENSOR_OK;",
        ])},
        {"ret": "int", "name": "sensor_get_status", "args": "int ch", "body": "\n".join([
            "if (!initialized) return SENSOR_ERR_NOT_INIT;",
            "return channels[ch].enabled;",
        ])},
        {"ret": "void", "name": "sensor_poll_all", "args": "void", "body": "\n".join([
            "for (int i = 0; i < MAX_CHANNELS; i++) {",
            "    if (!channels[i].enabled) continue;",
            "    channels[i].value = _hw_read(i);",
            "    channels[i].sample_count++;",
            "    channels[i].last_read_ms = _get_tick_ms();",
            "}",
        ])},
    ]
    for i in range(50):
        funcs.append({
            "ret": "int", "name": f"sensor_filter_{i}", "args": "int raw, int history",
            "body": "\n".join([
                f"int alpha = {10 + i * 3};",
                f"int beta = {100 - (10 + i * 3)};",
                "int filtered = (alpha * raw + beta * history) / 100;",
                f"if (filtered < {i * 10}) filtered = {i * 10};",
                f"if (filtered > {4000 + i * 100}) filtered = {4000 + i * 100};",
                f"int deviation = raw - filtered;",
                f"if (deviation < -{50 + i * 5} || deviation > {50 + i * 5}) {{",
                f"    filtered = (filtered + raw) / 2;",
                f"}}",
                "return filtered;",
            ]),
        })

    static = [
        "#define MAX_CHANNELS 8",
        "#define SENSOR_OK 0",
        "#define SENSOR_ERR_NOT_INIT -1",
        "#define SENSOR_NONE 0",
        "",
        "typedef struct {",
        "    int value;",
        "    int type;",
        "    int enabled;",
        "    int interval_ms;",
        "    int sample_count;",
        "    unsigned long last_read_ms;",
        "} ChannelState;",
        "",
        "static ChannelState channels[MAX_CHANNELS];",
        "static int initialized = 0;",
        "",
        "typedef int SensorType;",
        "extern int _hw_read(int ch);",
        "extern unsigned long _get_tick_ms(void);",
    ]
    return generate_module("sensor", funcs, static_vars=static)


def sensor_v2_fix() -> tuple[str, str]:
    """Fix: add bounds checking to sensor_read and sensor_configure."""
    src, hdr = sensor_v1()
    # Add bounds check to sensor_read
    src = src.replace(
        "if (!initialized) return SENSOR_ERR_NOT_INIT;\n    return channels[ch].value;",
        "if (!initialized) return SENSOR_ERR_NOT_INIT;\n"
        "    if (ch < 0 || ch >= MAX_CHANNELS) return SENSOR_ERR_INVALID_CH;\n"
        "    if (!channels[ch].enabled) return SENSOR_ERR_DISABLED;\n"
        "    return channels[ch].value;",
    )
    # Add bounds check to sensor_configure
    src = src.replace(
        "channels[ch].type = type;",
        "if (ch < 0 || ch >= MAX_CHANNELS) return SENSOR_ERR_INVALID_CH;\n"
        "    if (type < 0) return SENSOR_ERR_INVALID_TYPE;\n"
        "    channels[ch].type = type;",
    )
    src = src.replace(
        "#define SENSOR_ERR_NOT_INIT -1",
        "#define SENSOR_ERR_NOT_INIT -1\n#define SENSOR_ERR_INVALID_CH -2\n"
        "#define SENSOR_ERR_DISABLED -3\n#define SENSOR_ERR_INVALID_TYPE -4",
    )
    return src, hdr


def radio_v1() -> tuple[str, str]:
    """Initial radio module: packet TX/RX, channel management."""
    funcs = [
        {"ret": "void", "name": "radio_init", "args": "RadioConfig *cfg", "body": "\n".join([
            "current_channel = cfg->default_channel;",
            "tx_power = cfg->tx_power_dbm;",
            "rx_enabled = 0;",
            "packet_count = 0;",
            "error_count = 0;",
            "for (int i = 0; i < RX_BUFFER_SIZE; i++) {",
            "    rx_buffer[i] = 0;",
            "}",
        ])},
        {"ret": "int", "name": "radio_send", "args": "const uint8_t *data, int len", "body": "\n".join([
            "if (len > MAX_PACKET_SIZE) return RADIO_ERR_TOO_LONG;",
            "if (!_is_channel_clear()) return RADIO_ERR_BUSY;",
            "_set_tx_mode();",
            "for (int i = 0; i < len; i++) {",
            "    _write_fifo(data[i]);",
            "}",
            "_trigger_tx();",
            "packet_count++;",
            "return RADIO_OK;",
        ])},
        {"ret": "int", "name": "radio_receive", "args": "uint8_t *buf, int max_len", "body": "\n".join([
            "if (!rx_enabled) return RADIO_ERR_NOT_ENABLED;",
            "int available = _get_rx_count();",
            "if (available == 0) return 0;",
            "int to_read = available < max_len ? available : max_len;",
            "for (int i = 0; i < to_read; i++) {",
            "    buf[i] = _read_fifo();",
            "}",
            "return to_read;",
        ])},
        {"ret": "int", "name": "radio_set_channel", "args": "int channel", "body": "\n".join([
            "if (channel < 0 || channel > MAX_RADIO_CHANNEL) return RADIO_ERR_INVALID;",
            "current_channel = channel;",
            "_configure_frequency(channel);",
            "return RADIO_OK;",
        ])},
    ]
    for i in range(50):
        funcs.append({
            "ret": "int", "name": f"radio_diagnostic_{i}", "args": "void",
            "body": "\n".join([
                f"int reg_a = _read_reg(0x{0x10 + i:02X});",
                f"int reg_b = _read_reg(0x{0x80 + i:02X});",
                f"int expected_a = 0x{0xA0 + i:02X};",
                f"int expected_b = 0x{0xB0 + i:02X};",
                "if (reg_a != expected_a) {",
                "    error_count++;",
                f"    return RADIO_DIAG_FAIL_{i};",
                "}",
                "if (reg_b != expected_b) {",
                "    error_count++;",
                f"    return -(RADIO_DIAG_FAIL_{i} + 100);",
                "}",
                "return RADIO_OK;",
            ]),
        })

    static = [
        "#include <stdint.h>",
        "",
        "#define MAX_PACKET_SIZE 256",
        "#define RX_BUFFER_SIZE 512",
        "#define MAX_RADIO_CHANNEL 125",
        "#define RADIO_OK 0",
        "#define RADIO_ERR_TOO_LONG -1",
        "#define RADIO_ERR_BUSY -2",
        "#define RADIO_ERR_NOT_ENABLED -3",
        "#define RADIO_ERR_INVALID -4",
        *[f"#define RADIO_DIAG_FAIL_{i} -{10+i}" for i in range(50)],
        "",
        "typedef struct { int default_channel; int tx_power_dbm; } RadioConfig;",
        "",
        "static int current_channel;",
        "static int tx_power;",
        "static int rx_enabled;",
        "static int packet_count;",
        "static int error_count;",
        "static uint8_t rx_buffer[RX_BUFFER_SIZE];",
        "",
        "extern int _is_channel_clear(void);",
        "extern void _set_tx_mode(void);",
        "extern void _write_fifo(uint8_t b);",
        "extern void _trigger_tx(void);",
        "extern int _get_rx_count(void);",
        "extern uint8_t _read_fifo(void);",
        "extern void _configure_frequency(int ch);",
        "extern int _read_reg(int addr);",
    ]
    return generate_module("radio", funcs, static_vars=static)


def storage_v1() -> tuple[str, str]:
    """Initial storage module: flash read/write/erase."""
    funcs = [
        {"ret": "int", "name": "storage_init", "args": "void", "body": "\n".join([
            "write_ptr = 0;",
            "read_ptr = 0;",
            "erase_count = 0;",
            "for (int s = 0; s < NUM_SECTORS; s++) {",
            "    sector_status[s] = SECTOR_CLEAN;",
            "    sector_write_count[s] = 0;",
            "}",
            "return STORAGE_OK;",
        ])},
        {"ret": "int", "name": "storage_write", "args": "uint32_t addr, const uint8_t *data, int len", "body": "\n".join([
            "int sector = addr / SECTOR_SIZE;",
            "if (sector >= NUM_SECTORS) return STORAGE_ERR_BOUNDS;",
            "if (sector_status[sector] == SECTOR_BAD) return STORAGE_ERR_BAD_SECTOR;",
            "for (int i = 0; i < len; i++) {",
            "    _flash_write_byte(addr + i, data[i]);",
            "}",
            "sector_write_count[sector]++;",
            "write_ptr = addr + len;",
            "return len;",
        ])},
        {"ret": "int", "name": "storage_read", "args": "uint32_t addr, uint8_t *buf, int len", "body": "\n".join([
            "int sector = addr / SECTOR_SIZE;",
            "if (sector >= NUM_SECTORS) return STORAGE_ERR_BOUNDS;",
            "for (int i = 0; i < len; i++) {",
            "    buf[i] = _flash_read_byte(addr + i);",
            "}",
            "read_ptr = addr + len;",
            "return len;",
        ])},
        {"ret": "int", "name": "storage_erase_sector", "args": "int sector", "body": "\n".join([
            "if (sector < 0 || sector >= NUM_SECTORS) return STORAGE_ERR_BOUNDS;",
            "_flash_erase(sector * SECTOR_SIZE, SECTOR_SIZE);",
            "sector_status[sector] = SECTOR_CLEAN;",
            "erase_count++;",
            "return STORAGE_OK;",
        ])},
    ]
    for i in range(40):
        funcs.append({
            "ret": "int", "name": f"storage_check_block_{i}", "args": "int sector",
            "body": "\n".join([
                f"uint32_t base = sector * SECTOR_SIZE + {i} * BLOCK_SIZE;",
                f"uint32_t pattern = 0x{0xFF - (i % 256):02X}{(i * 7) % 256:02X};",
                "for (int j = 0; j < BLOCK_SIZE; j++) {",
                "    uint8_t val = _flash_read_byte(base + j);",
                f"    if (val != (pattern & 0xFF)) return STORAGE_ERR_CORRUPT;",
                f"    pattern = (pattern >> 1) | (pattern << 31);",
                "}",
                "return STORAGE_OK;",
            ]),
        })

    static = [
        "#include <stdint.h>",
        "",
        "#define NUM_SECTORS 64",
        "#define SECTOR_SIZE 4096",
        "#define BLOCK_SIZE 256",
        "#define STORAGE_OK 0",
        "#define STORAGE_ERR_BOUNDS -1",
        "#define STORAGE_ERR_BAD_SECTOR -2",
        "#define STORAGE_ERR_CORRUPT -3",
        "#define SECTOR_CLEAN 0",
        "#define SECTOR_DIRTY 1",
        "#define SECTOR_BAD 2",
        "",
        "static uint32_t write_ptr;",
        "static uint32_t read_ptr;",
        "static int erase_count;",
        "static int sector_status[NUM_SECTORS];",
        "static int sector_write_count[NUM_SECTORS];",
        "",
        "extern void _flash_write_byte(uint32_t addr, uint8_t val);",
        "extern uint8_t _flash_read_byte(uint32_t addr);",
        "extern void _flash_erase(uint32_t addr, int len);",
    ]
    return generate_module("storage", funcs, static_vars=static)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    if cmd == "sensor_v1":
        src, hdr = sensor_v1()
        print(f"=== sensor.c ({len(src)} bytes) ===")
        print(src)
        print(f"=== sensor.h ({len(hdr)} bytes) ===")
        print(hdr)
    elif cmd == "sensor_v2":
        src, hdr = sensor_v2_fix()
        print(f"=== sensor.c ({len(src)} bytes) ===")
        print(src)
    elif cmd == "radio_v1":
        src, hdr = radio_v1()
        print(f"=== radio.c ({len(src)} bytes) ===")
        print(src)
    elif cmd == "storage_v1":
        src, hdr = storage_v1()
        print(f"=== storage.c ({len(src)} bytes) ===")
        print(src)
    else:
        for name, fn in [("sensor_v1", sensor_v1), ("radio_v1", radio_v1), ("storage_v1", storage_v1)]:
            src, hdr = fn()
            print(f"{name}: {len(src)} bytes source, {len(hdr)} bytes header")
