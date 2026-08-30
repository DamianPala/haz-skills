#!/bin/sh
set -eu

OUT_DIR="${1:-/tmp/router-backup}"
BACKUP_FILE="$OUT_DIR/config-backup.tar.gz"
CUSTOM_FILE="$OUT_DIR/custom-files.tar.gz"
CUSTOM_LIST="$OUT_DIR/custom-files.list"
STANDARD_LIST="$OUT_DIR/config-files.list"
SCAN_LIST="$OUT_DIR/scan-files.list"
OWNED_LIST="$OUT_DIR/package-owned.list"
MANIFEST_FILE="$OUT_DIR/manifest.txt"
BUNDLE_FILE="${2:-/tmp/openwrt-backup-bundle.tar.gz}"

# Directories holding only operator-added files; safe to scan without a
# package index.
SAFE_CUSTOM_DIRS="/etc/hotplug.d /etc/profile.d /root/bin /usr/local"

# Directories mixing operator scripts with packaged binaries. Scanned only
# when a package file index is available to subtract the packaged ones.
SYSTEM_CUSTOM_DIRS="/etc/init.d /usr/sbin /usr/bin"

mkdir -p "$OUT_DIR"

section() {
    printf '\n=== %s ===\n' "$1"
}

should_exclude_custom_file() {
    case "$1" in
        *.bak | *.bak.* | *.backup | *.backup.* | *~)
            return 0
            ;;
        *.log | *.log.* | *.old | *.orig | *.swp | *.tmp)
            return 0
            ;;
        */.ash_history | */.viminfo | */.lesshst | */.wget-hsts)
            return 0
            ;;
        */cache/* | */tmp/* | */log/* | */logs/* | */run/* | */lock/*)
            return 0
            ;;
    esac

    return 1
}

is_allowed_custom_path() {
    case "$1" in
        /etc/hotplug.d/* | /etc/profile.d/* | /root/bin/* | /usr/local/* | /etc/rc.local)
            return 0
            ;;
        /etc/init.d/* | /usr/sbin/* | /usr/bin/*)
            return 0
            ;;
    esac

    return 1
}

# Files belonging to installed packages. Whatever remains in the scanned
# directories was put there by the operator.
list_package_owned_files() {
    if command -v apk >/dev/null 2>&1; then
        xargs apk info --who-owns 2>/dev/null < "$SCAN_LIST" |
            sed -n 's/^\(.*\) is owned by .*/\1/p'
    elif command -v opkg >/dev/null 2>&1; then
        cat /usr/lib/opkg/info/*.list 2>/dev/null
    fi
}

add_custom_file() {
    path="$1"
    archive_path="${path#/}"

    [ -f "$path" ] || return 0
    [ -L "$path" ] && return 0
    is_allowed_custom_path "$path" || return 0
    should_exclude_custom_file "$path" && return 0
    grep -Fx "$archive_path" "$STANDARD_LIST" >/dev/null 2>&1 && return 0

    printf '%s\n' "$archive_path" >> "$CUSTOM_LIST"
}

collect_custom_files() {
    : > "$CUSTOM_LIST"
    tar -tzf "$BACKUP_FILE" 2>/dev/null | sort > "$STANDARD_LIST"

    scan_dirs="$SAFE_CUSTOM_DIRS"
    if command -v apk >/dev/null 2>&1 || command -v opkg >/dev/null 2>&1; then
        scan_dirs="$scan_dirs $SYSTEM_CUSTOM_DIRS"
    fi

    : > "$SCAN_LIST"
    for dir in $scan_dirs; do
        [ -d "$dir" ] || continue
        find "$dir" -type f 2>/dev/null >> "$SCAN_LIST"
    done
    if [ -f /etc/rc.local ]; then
        printf '%s\n' /etc/rc.local >> "$SCAN_LIST"
    fi
    sort -u "$SCAN_LIST" -o "$SCAN_LIST"

    list_package_owned_files | sort -u > "$OWNED_LIST"

    # Directory scan is the only way to find operator scripts outside /etc,
    # because apk audit reports nothing beyond /etc even when given a path.
    (grep -Fxv -f "$OWNED_LIST" "$SCAN_LIST" 2>/dev/null || true) |
        while IFS= read -r file; do
            add_custom_file "$file"
        done

    # apk audit adds packaged files the operator has modified, which the
    # ownership subtraction above deliberately skips.
    if command -v apk >/dev/null 2>&1; then
        (apk audit 2>/dev/null || true) |
            awk '$1 ~ /^[AU]$/ { print "/" $2 }' |
            while IFS= read -r file; do
                add_custom_file "$file"
            done
    fi

    sort -u "$CUSTOM_LIST" -o "$CUSTOM_LIST"

    if [ -s "$CUSTOM_LIST" ]; then
        tar -czf "$CUSTOM_FILE" -C / -T "$CUSTOM_LIST"
    else
        tar -czf "$CUSTOM_FILE" -T /dev/null
    fi
}

{
    section "date"
    date -u 2>/dev/null || date 2>/dev/null || true

    section "openwrt_release"
    cat /etc/openwrt_release 2>/dev/null || true

    section "board"
    ubus call system board 2>/dev/null || true

    section "kernel"
    uname -a 2>/dev/null || true

    section "storage"
    df -h 2>/dev/null || true

    section "routes"
    ip route 2>/dev/null || route -n 2>/dev/null || true

    section "package_manager"
    if command -v apk >/dev/null 2>&1; then
        apk --version 2>/dev/null || true
    fi
    if command -v opkg >/dev/null 2>&1; then
        opkg --version 2>/dev/null || true
    fi
} > "$MANIFEST_FILE"

sysupgrade -k -b "$BACKUP_FILE"
collect_custom_files

{
    section "archive_file_list"
    tar -tzf "$BACKUP_FILE" 2>/dev/null || true

    section "sysupgrade_file_list"
    sysupgrade -l 2>/dev/null | sort || true

    section "custom_file_list"
    cat "$CUSTOM_LIST" 2>/dev/null || true

    section "sysupgrade.conf"
    cat /etc/sysupgrade.conf 2>/dev/null || true

    section "apk_audit"
    if command -v apk >/dev/null 2>&1; then
        apk audit 2>/dev/null || true
    fi

    section "apk_list_installed"
    if command -v apk >/dev/null 2>&1; then
        apk list -I 2>/dev/null || true
    fi

    section "apk_world"
    cat /etc/apk/world 2>/dev/null || true

    section "opkg_list_installed"
    if command -v opkg >/dev/null 2>&1; then
        opkg list-installed 2>/dev/null || true
    fi

    section "installed_packages.txt from backup"
    tar -O -zxf "$BACKUP_FILE" etc/backup/installed_packages.txt 2>/dev/null || true

    section "custom_file_candidates_from_apk_audit"
    if command -v apk >/dev/null 2>&1; then
        (apk audit 2>/dev/null || true) |
            awk '$1 ~ /^[AU]$/ && ($2 ~ /^etc\/hotplug\.d\// || $2 ~ /^etc\/profile\.d\// || $2 == "etc/rc.local" || $2 ~ /^root\/bin\// || $2 ~ /^usr\/local\// || $2 ~ /^etc\/init\.d\// || $2 ~ /^usr\/s?bin\//) { print }'
    fi

    section "scanned_files_not_owned_by_packages"
    (grep -Fxv -f "$OWNED_LIST" "$SCAN_LIST" 2>/dev/null || true)
} >> "$MANIFEST_FILE"

tar -czf "$BUNDLE_FILE" -C "$OUT_DIR" config-backup.tar.gz custom-files.tar.gz manifest.txt

printf 'Backup set written to %s\n' "$OUT_DIR"
printf 'Main archive: %s\n' "$BACKUP_FILE"
printf 'Custom archive: %s\n' "$CUSTOM_FILE"
printf 'Manifest: %s\n' "$MANIFEST_FILE"
printf 'Transfer bundle: %s\n' "$BUNDLE_FILE"
