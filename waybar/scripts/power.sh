#!/bin/sh
# Privileged session actions behind the waybar power menu.
#
# Alpine + OpenRC has no polkit agent here, so `reboot` / `poweroff` cannot be
# run from a GUI.  We try a passwordless `doas` first and otherwise open a
# terminal that asks for the root password.  For a one-click experience add:
#
#   echo 'permit persist :wheel' | doas tee /etc/doas.d/waybar
#
# and drop the terminal fallback in scripts/power.sh accordingly.

notify() {
    notify-send -a "waybar" -u "${2:-normal}" "Session" "$1" 2>/dev/null
}

ask_in_terminal() {
    terminal="${TERMINAL:-kitty}"
    if ! command -v "$terminal" >/dev/null 2>&1; then
        notify "No terminal available to ask for authentication" "critical"
        return 1
    fi
    prompt="doas $1; printf '\\n[press enter to close] '; read _"
    "$terminal" --title "Authentication required" -e sh -c "$prompt"
}

run_root() {
    if [ "$(id -u)" = "0" ]; then
        "$@"
    elif doas -n "$@" 2>/dev/null; then
        :
    else
        ask_in_terminal "$*"
    fi
}

suspend_backend() {
    for candidate in zzz apc pm-suspend "systemctl suspend"; do
        # shellcheck disable=SC2086
        if command -v ${candidate%% *} >/dev/null 2>&1; then
            printf '%s' "$candidate"
            return 0
        fi
    done
    return 1
}

# The same power menu is used by the Hyprland and the sway bar configs, so pick
# whichever compositor is actually running. SWAYSOCK is exported by sway; the
# Hyprland var is the documented one for hyprctl.
logout_session() {
    if [ -n "${SWAYSOCK:-}" ]; then
        swaymsg exit
    elif [ -n "${HYPRLAND_INSTANCE_SIGNATURE:-}" ]; then
        hyprctl dispatch exit
    else
        notify "No supported compositor session found" "critical"
        return 1
    fi
}

case "${1:-}" in
    logout)
        logout_session
        ;;
    suspend)
        if backend=$(suspend_backend); then
            # shellcheck disable=SC2086
            run_root $backend
        else
            notify "Suspend is unavailable: install pm-utils or acpid-utils" "critical"
        fi
        ;;
    reboot | poweroff)
        run_root "$1"
        ;;
    *)
        notify "Unknown power action: ${1:-none}" "critical"
        ;;
esac
