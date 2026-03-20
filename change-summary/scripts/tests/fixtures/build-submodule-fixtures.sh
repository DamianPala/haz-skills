#!/usr/bin/env bash
set -euo pipefail

# Build synthetic git repos for submodule expansion/ignore testing.
# Run once, commit resulting .bundle files.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

git_cfg=(-c user.name=Test -c user.email=test@test.com)

# ─── Components (via Python builder) ─────────────────────────────────────────

COMP_DIR="$WORK_DIR/child-components"
mkdir -p "$COMP_DIR/src"
git -C "$COMP_DIR" init --initial-branch=master
git -C "$COMP_DIR" config user.name Test
git -C "$COMP_DIR" config user.email test@test.com
git -C "$COMP_DIR" config core.hooksPath /dev/null

REPO_DIR="$COMP_DIR" python3 "$SCRIPT_DIR/build_components.py"

COMP_HEAD=$(git -C "$COMP_DIR" rev-parse HEAD)
COMP_V1=$(git -C "$COMP_DIR" rev-parse v1.0.0)
COMP_COUNT=$(git -C "$COMP_DIR" rev-list --count v1.0.0..HEAD)
echo "Components: $COMP_COUNT commits"

# ─── Drivers (large vendor blobs, ignore target) ─────────────────────────────

DRV_DIR="$WORK_DIR/child-drivers"
mkdir -p "$DRV_DIR/STM32F4/src" "$DRV_DIR/STM32F4/inc"
git -C "$DRV_DIR" init --initial-branch=master
git -C "$DRV_DIR" config user.name Test
git -C "$DRV_DIR" config user.email test@test.com
git -C "$DRV_DIR" config core.hooksPath /dev/null

python3 -c "
lines = ['#include \"stm32f4xx_hal.h\"', '']
for periph in ['GPIO', 'SPI', 'I2C', 'UART', 'TIM', 'ADC', 'DMA', 'RCC']:
    lines.append(f'/* ---- {periph} ---- */')
    for f in range(80):
        lines.append(f'HAL_StatusTypeDef HAL_{periph}_Func{f}(void) {{')
        for j in range(8):
            lines.append(f'    volatile uint32_t reg{j} = 0x{f:04X}{j:02X};')
            lines.append(f'    (void)reg{j};')
        lines.append('    return HAL_OK;')
        lines.append('}')
        lines.append('')
with open('$DRV_DIR/STM32F4/src/stm32f4xx_hal.c', 'w') as f:
    f.write('\n'.join(lines))
"

cat > "$DRV_DIR/STM32F4/inc/stm32f4xx_hal.h" << 'EOF'
#pragma once
#include <stdint.h>
typedef enum { HAL_OK = 0, HAL_ERROR, HAL_BUSY, HAL_TIMEOUT } HAL_StatusTypeDef;
EOF

git -C "$DRV_DIR" add -A
git -C "$DRV_DIR" "${git_cfg[@]}" commit -m "feat: initial STM32F4 HAL drivers"
git -C "$DRV_DIR" tag v1.0.0

python3 -c "
lines = ['#include \"stm32f4xx_hal.h\"', '', '/* ---- DAC ---- */']
for f in range(100):
    lines.append(f'HAL_StatusTypeDef HAL_DAC_Func{f}(void) {{')
    for j in range(4):
        lines.append(f'    volatile uint32_t r{j} = 0xDAC{f:04X};')
        lines.append(f'    (void)r{j};')
    lines.append('    return HAL_OK;')
    lines.append('}')
    lines.append('')
with open('$DRV_DIR/STM32F4/src/stm32f4xx_hal_dac.c', 'w') as f:
    f.write('\n'.join(lines))
"
git -C "$DRV_DIR" add -A
git -C "$DRV_DIR" "${git_cfg[@]}" commit -m "feat: add DAC peripheral driver"

python3 -c "
import pathlib
hal = pathlib.Path('$DRV_DIR/STM32F4/src/stm32f4xx_hal.c')
content = hal.read_text()
content = content.replace(
    'HAL_StatusTypeDef HAL_SPI_Func0(void) {',
    'HAL_StatusTypeDef HAL_SPI_Func0(void) {\n    /* Fix: timeout guard */\n    if (__HAL_GET_FLAG(SPI_FLAG_BSY)) return HAL_TIMEOUT;',
)
hal.write_text(content)
"
git -C "$DRV_DIR" add -A
git -C "$DRV_DIR" "${git_cfg[@]}" commit -m "fix: SPI timeout handling"

DRV_HEAD=$(git -C "$DRV_DIR" rev-parse HEAD)
DRV_V1=$(git -C "$DRV_DIR" rev-parse v1.0.0)

# ─── Parent repo ─────────────────────────────────────────────────────────────

PARENT_DIR="$WORK_DIR/parent"
mkdir -p "$PARENT_DIR/src"
git -C "$PARENT_DIR" init --initial-branch=master
git -C "$PARENT_DIR" config user.name Test
git -C "$PARENT_DIR" config user.email test@test.com
git -C "$PARENT_DIR" config core.hooksPath /dev/null

cat > "$PARENT_DIR/src/main.c" << 'EOF'
int main(void) { return 0; }
EOF
echo "# DR203 Recorder Firmware" > "$PARENT_DIR/README.md"
git -C "$PARENT_DIR" add -A
git -C "$PARENT_DIR" "${git_cfg[@]}" commit -m "feat: initial app"
git -C "$PARENT_DIR" tag v1.0.0

# v1.1.0: add submodules pinned to v1.0.0
git -C "$PARENT_DIR" -c protocol.file.allow=always submodule add "$COMP_DIR" Components
git -C "$PARENT_DIR" -C Components checkout "$COMP_V1"
git -C "$PARENT_DIR" add Components
git -C "$PARENT_DIR" "${git_cfg[@]}" commit -m "chore: add Components submodule"

git -C "$PARENT_DIR" -c protocol.file.allow=always submodule add "$DRV_DIR" drivers/STM32F4
git -C "$PARENT_DIR" -C drivers/STM32F4 checkout "$DRV_V1"
git -C "$PARENT_DIR" add drivers/STM32F4
git -C "$PARENT_DIR" "${git_cfg[@]}" commit -m "chore: add STM32F4 drivers submodule"
git -C "$PARENT_DIR" tag v1.1.0

# v2.0.0: update both submodules + parent changes + config
git -C "$PARENT_DIR" -C Components checkout "$COMP_HEAD"
git -C "$PARENT_DIR" add Components
git -C "$PARENT_DIR" -C drivers/STM32F4 checkout "$DRV_HEAD"
git -C "$PARENT_DIR" add drivers/STM32F4

cat > "$PARENT_DIR/src/main.c" << 'EOF'
#include "sensor.h"
#include "radio.h"
#include "storage.h"

int main(void) {
    sensor_init();
    storage_init();
    RadioConfig cfg = { .default_channel = 10, .tx_power_dbm = 0 };
    radio_init(&cfg);
    float h = humidity_read();
    (void)h;
    return 0;
}
EOF
git -C "$PARENT_DIR" add src/main.c

cat > "$PARENT_DIR/AGENTS.md" << 'EOF'
# Project Agents

## change-summary

```yaml
submodules:
  ignore:
    - drivers/STM32F4
  expand:
    - Components
```

## General

Embedded firmware project for the DR203 data recorder.
EOF
git -C "$PARENT_DIR" add AGENTS.md

git -C "$PARENT_DIR" "${git_cfg[@]}" commit -m "feat: integrate humidity, DMA radio, and wear-leveled storage"
git -C "$PARENT_DIR" tag v2.0.0

# ─── Bundle + Report ─────────────────────────────────────────────────────────

echo ""
git -C "$COMP_DIR" bundle create "$SCRIPT_DIR/child-components.bundle" --all
git -C "$DRV_DIR" bundle create "$SCRIPT_DIR/child-drivers.bundle" --all
git -C "$PARENT_DIR" bundle create "$SCRIPT_DIR/parent.bundle" --all

echo "=== Bundle sizes ==="
ls -lh "$SCRIPT_DIR"/*.bundle

echo ""
echo "=== Per-commit diff sizes in Components ==="
cd "$COMP_DIR"
for hash in $(git rev-list --reverse v1.0.0..HEAD); do
    msg=$(git log --format="%s" -1 "$hash")
    diff_chars=$(git diff-tree -p "$hash" | wc -c)
    diff_tokens=$((diff_chars / 4))
    echo "  $msg: ~${diff_tokens} tokens"
done
total_chars=$(git diff v1.0.0..HEAD | wc -c)
total_tokens=$((total_chars / 4))
echo "  TOTAL (aggregate): ~${total_tokens} tokens"
