#!/usr/bin/env python3
"""Build the Components submodule repo with 5 commits.

Each commit mass-modifies existing functions to produce large diffs.
Called by build-submodule-fixtures.sh with REPO_DIR env var.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

REPO_DIR = Path(os.environ["REPO_DIR"])
SRC = REPO_DIR / "src"

sys.path.insert(0, str(Path(__file__).parent))
from generate_c_code import radio_v1, sensor_v1, storage_v1


def _git(*args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=Test", "-c", "user.email=test@test.com", *args],
        cwd=REPO_DIR,
        capture_output=True,
        text=True,
        check=True,
    )


def _commit(msg: str) -> None:
    _git("add", "-A")
    _git("commit", "-m", msg)


def _write(relpath: str, content: str) -> None:
    path = SRC / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# ── v1.0.0: initial framework ──

sensor_src, sensor_hdr = sensor_v1()
radio_src, radio_hdr = radio_v1()
storage_src, storage_hdr = storage_v1()

_write("sensor.c", sensor_src)
_write("sensor.h", sensor_hdr)
_write("radio.c", radio_src)
_write("radio.h", radio_hdr)
_write("storage.c", storage_src)
_write("storage.h", storage_hdr)
_commit("feat: initial framework (sensor, radio, storage)")
_git("tag", "v1.0.0")


# ── Commit 2: fix bounds checking in ALL sensor filter functions ──

src = (SRC / "sensor.c").read_text()

# Add bounds check to sensor_read and sensor_configure
src = src.replace(
    "if (!initialized) return SENSOR_ERR_NOT_INIT;\n    return channels[ch].value;",
    "if (!initialized) return SENSOR_ERR_NOT_INIT;\n"
    "    if (ch < 0 || ch >= MAX_CHANNELS) return SENSOR_ERR_INVALID_CH;\n"
    "    if (!channels[ch].enabled) return SENSOR_ERR_DISABLED;\n"
    "    return channels[ch].value;",
)
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
# Add saturation guard to EVERY sensor_filter function
src = re.sub(
    r"(int sensor_filter_\d+\(int raw, int history\) \{)",
    r"\1\n    if (raw < 0) raw = 0;\n    if (raw > 65535) raw = 65535;\n    if (history < 0) history = 0;",
    src,
)
_write("sensor.c", src)
_commit(
    "fix: add bounds checking to sensor_read and all filter functions\n\n"
    "Adds input validation to sensor_read, sensor_configure, and all 50\n"
    "sensor_filter_* functions. Prevents out-of-bounds channel access,\n"
    "invalid sensor type, and raw value overflow."
)


# ── Commit 3: humidity sensor + update all filters with humidity compensation ──

src = (SRC / "sensor.c").read_text()
hdr = (SRC / "sensor.h").read_text()

humidity_block = """
static float humidity_raw;
static float humidity_offset;

float humidity_read(void) {
    return (humidity_raw + humidity_offset) * 0.01f;
}

void humidity_set_raw(float raw) {
    humidity_raw = raw;
}

void humidity_calibrate(float offset) {
    humidity_offset = offset;
}

int humidity_self_test(void) {
    float old = humidity_raw;
    humidity_set_raw(5000.0f);
    float result = humidity_read();
    humidity_set_raw(old);
    if (result < 49.0f || result > 51.0f) return -1;
    return 0;
}
"""
src += humidity_block

# Add humidity compensation to ALL filter functions
src = re.sub(
    r"(    return filtered;\n\})",
    "    /* humidity compensation */\n"
    "    if (humidity_raw > 0.0f) {\n"
    "        float comp = humidity_raw * 0.001f;\n"
    "        filtered = (int)((float)filtered * (1.0f - comp));\n"
    "    }\n"
    r"\1",
    src,
)

hdr = hdr.rstrip() + "\nfloat humidity_read(void);\nvoid humidity_set_raw(float raw);\n" \
    "void humidity_calibrate(float offset);\nint humidity_self_test(void);\n"

_write("sensor.c", src)
_write("sensor.h", hdr)
_commit("feat: add humidity sensor with compensation in all filters")


# ── Commit 4: wear leveling + update ALL storage check functions ──

src = (SRC / "storage.c").read_text()
hdr = (SRC / "storage.h").read_text()

src = src.replace(
    "sector_write_count[sector]++;",
    "sector_write_count[sector]++;\n"
    "    if (sector_write_count[sector] > WEAR_THRESHOLD) {\n"
    "        _relocate_sector(sector);\n"
    "        sector_status[sector] = SECTOR_BAD;\n"
    "    }",
)
src = src.replace(
    "#define SECTOR_BAD 2",
    "#define SECTOR_BAD 2\n#define WEAR_THRESHOLD 100000",
)
src = src.replace(
    "extern void _flash_erase(uint32_t addr, int len);",
    "extern void _flash_erase(uint32_t addr, int len);\nextern void _relocate_sector(int sector);",
)
# Add wear check to EVERY storage_check_block function
src = re.sub(
    r"(int storage_check_block_\d+\(int sector\) \{)",
    r"\1\n    if (sector_status[sector] == SECTOR_BAD) return STORAGE_ERR_BAD_SECTOR;\n"
    r"    if (sector_write_count[sector] > WEAR_THRESHOLD / 2) {\n"
    r"        /* warn: approaching wear limit */\n    }",
    src,
)
src += """int storage_get_wear_stats(int *min_writes, int *max_writes) {
    *min_writes = sector_write_count[0];
    *max_writes = sector_write_count[0];
    for (int i = 1; i < NUM_SECTORS; i++) {
        if (sector_write_count[i] < *min_writes) *min_writes = sector_write_count[i];
        if (sector_write_count[i] > *max_writes) *max_writes = sector_write_count[i];
    }
    return *max_writes - *min_writes;
}
"""
hdr = hdr.rstrip() + "\nint storage_get_wear_stats(int *min_writes, int *max_writes);\n"

_write("storage.c", src)
_write("storage.h", hdr)
_commit("feat: add wear leveling with per-block wear checks in storage")


# ── Commit 5: DMA + rewrite ALL radio diagnostics with cached reads ──

src = (SRC / "radio.c").read_text()
hdr = (SRC / "radio.h").read_text()

# DMA support in radio_send
src = src.replace(
    "for (int i = 0; i < len; i++) {\n"
    "        _write_fifo(data[i]);\n"
    "    }",
    "if (len > DMA_THRESHOLD) {\n"
    "        _dma_transfer(data, len);\n"
    "    } else {\n"
    "        for (int i = 0; i < len; i++) {\n"
    "            _write_fifo(data[i]);\n"
    "        }\n"
    "    }",
)
src = src.replace(
    "#define RADIO_OK 0",
    "#define RADIO_OK 0\n#define DMA_THRESHOLD 64\nstatic int cached_regs[256];",
)
src = src.replace(
    "extern int _read_reg(int addr);",
    "extern int _read_reg(int addr);\nextern void _dma_transfer(const uint8_t *data, int len);",
)
# Rewrite ALL radio_diagnostic functions to use cached reads
src = src.replace("_read_reg(", "_cached_read_reg(cached_regs, ")
src = src.replace("error_count++;", "error_count++;\n        _invalidate_cache(cached_regs);")

batch_fn = """
static int _cached_read_reg(int *cache, int addr) {
    if (cache[addr] == 0) cache[addr] = _read_reg(addr);
    return cache[addr];
}

static void _invalidate_cache(int *cache) {
    for (int i = 0; i < 256; i++) cache[i] = 0;
}

int radio_run_all_diagnostics(int *results) {
    _invalidate_cache(cached_regs);
    int failures = 0;
    for (int i = 0; i < 50; i++) {
        int reg_a = _cached_read_reg(cached_regs, 0x10 + i);
        int reg_b = _cached_read_reg(cached_regs, 0x80 + i);
        results[i] = (reg_a == (0xA0 + i) && reg_b == (0xB0 + i)) ? 0 : -1;
        if (results[i] != 0) failures++;
    }
    return failures;
}
"""
src += batch_fn
hdr = hdr.rstrip() + "\nint radio_run_all_diagnostics(int *results);\n"

_write("radio.c", src)
_write("radio.h", hdr)
_commit("perf: optimize radio with DMA and cached register diagnostics")
