import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import RadioButtons

# ── Star configurations ─────────────────────────────────────────────────────
star_configs = {
    "Low (0.5 M☉)": {
        "color": "#4ecdc4",
        "end": "WD",
        "stages": [
            {"name": "Protostar",       "T": 3500,  "L": 0.5},
            {"name": "Main sequence",   "T": 4500,  "L": 0.08},
            {"name": "Red giant",       "T": 3500,  "L": 40},
            {"name": "White dwarf",     "T": 25000, "L": 0.01},
        ]
    },
    "Medium (1.0 M☉)": {
        "color": "#ffd166",
        "end": "WD",
        "stages": [
            {"name": "Protostar",       "T": 4000,  "L": 2},
            {"name": "Main sequence",   "T": 5800,  "L": 1},
            {"name": "Subgiant",        "T": 4800,  "L": 4},
            {"name": "Red giant",       "T": 3600,  "L": 80},
            {"name": "White dwarf",     "T": 30000, "L": 0.005},
        ]
    },
    "High (15 M☉)": {
        "color": "#a29bfe",
        "end": "SN",
        # NOTE: No "Supernova!" stage here — supernova fires in-place at Red supergiant
        "stages": [
            {"name": "Protostar",                "T": 5000,  "L": 20000},
            {"name": "Main sequence",            "T": 28000, "L": 12000},
            {"name": "Main sequence (core burn)","T": 20000, "L": 18000},
            {"name": "Blue supergiant",          "T": 16000, "L": 90000},
            {"name": "Red supergiant",           "T": 3800,  "L": 300000},
        ]
    },
}

STEPS_PER_SEGMENT = 80
INTERVAL_MS       = 25

# Neutron star final resting position on the HR diagram
NS_T = 600000   # very hot (~1e6 K surface, plotted near axis edge)
NS_L = 0.0002   # very dim


def temp_to_color(T):
    if T > 20000: return "#b8d4ff"
    if T > 10000: return "#ddeeff"
    if T >  7500: return "#fffbe8"
    if T >  6000: return "#fff5cc"
    if T >  5000: return "#ffd580"
    if T >  4000: return "#ff9944"
    return "#ff4422"


def interp_path(stages, steps=STEPS_PER_SEGMENT):
    pts = []
    for i in range(len(stages) - 1):
        a, b = stages[i], stages[i + 1]
        for j in range(steps + 1):
            t = j / steps
            T = np.exp(np.log(a["T"]) * (1 - t) + np.log(b["T"]) * t)
            L = np.exp(np.log(a["L"]) * (1 - t) + np.log(b["L"]) * t)
            name = a["name"] if t < 0.5 else b["name"]
            pts.append((T, L, name))
    return pts


# ── Figure layout ──────────────────────────────────────────────────────────
fig = plt.figure(figsize=(14, 8), facecolor="#0b0c14")
fig.subplots_adjust(left=0.22, right=0.97, top=0.95, bottom=0.10)

ax = fig.add_subplot(111, facecolor="#0b0c14")

ax.set_xscale("log")
ax.set_yscale("log")
ax.set_xlim(60000, 1500)
ax.set_ylim(1e-4, 2e7)
ax.set_xlabel("Temperature (K)", color="#888", fontsize=11)
ax.set_ylabel("Luminosity  (L / L☉)", color="#888", fontsize=11)
ax.tick_params(colors="#555", labelsize=9)
for spine in ax.spines.values():
    spine.set_edgecolor("#333")

ax.set_xticks([40000, 20000, 10000, 6000, 4000, 3000])
ax.set_xticklabels(["40k", "20k", "10k", "6k", "4k", "3k"], color="#555")

# Main-sequence band
ms_T = np.array([2500, 50000])
ms_L = np.array([5e-3, 8e4])
ax.fill_between(ms_T, ms_L * 0.18, ms_L * 5.5,
                color="#1a1a3a", alpha=0.9, zorder=1)
ax.plot(ms_T, ms_L, color="#2a2a5a", lw=1, zorder=2)
ax.text(8000, 8, "MAIN SEQUENCE", color="#334", fontsize=9,
        fontweight="bold", alpha=0.7, rotation=-38, zorder=3)

# Region labels
ax.text(40000, 3e5, "SUPERGIANTS", color="#334", fontsize=8, alpha=0.6)
ax.text(6000,  5e3, "GIANTS",       color="#334", fontsize=8, alpha=0.6)
ax.text(20000, 5e-4, "WHITE\nDWARFS", color="#334", fontsize=8, alpha=0.6)

# ── Animated artists ───────────────────────────────────────────────────────
evo_line,  = ax.plot([], [], lw=1.5, linestyle="--", zorder=4)
active_pt, = ax.plot([], [], "o", ms=9, zorder=6, mec="white", mew=0.8)
stage_text  = ax.text(0.5, 1.02, "", transform=ax.transAxes,
                      ha="center", va="bottom", color="#aaa",
                      fontsize=11, fontweight="bold")
halo,      = ax.plot([], [], "o", ms=22, zorder=5, alpha=0.25)

# Supernova expanding ring — centred at Red supergiant position
sn_circle = mpatches.Circle((1, 1), 0, transform=ax.transData,
                             fill=False, edgecolor="#ffd166",
                             linewidth=2, alpha=0, zorder=7)
ax.add_patch(sn_circle)

# Neutron star marker (hidden until after SN)
ns_pt, = ax.plot([], [], "*", ms=10, color="#00e5ff", zorder=8,
                 mec="white", mew=0.5, label="Neutron star")
ns_label = ax.text(0, 0, "", color="#00e5ff", fontsize=8, zorder=8,
                   ha="left", va="center")

# Flash overlay for the supernova moment
flash_circle = mpatches.Circle((0.5, 0.5), 0.0,
                                color="white", alpha=0,
                                transform=ax.transAxes, zorder=9)
ax.add_patch(flash_circle)

# ── Radio buttons ──────────────────────────────────────────────────────────
rax = plt.axes([0.01, 0.65, 0.18, 0.22], facecolor="#111118")
radio = RadioButtons(
    rax,
    list(star_configs.keys()),
    active=1,
    activecolor="#ffd166",
)
for lbl in radio.labels:
    lbl.set_color("white")
    lbl.set_fontsize(10)

# ── Info box ───────────────────────────────────────────────────────────────
info_ax = fig.add_axes([0.01, 0.10, 0.18, 0.30], facecolor="#0f0f1a")
info_ax.set_xlim(0, 1)
info_ax.set_ylim(0, 1)
info_ax.axis("off")
for sp in info_ax.spines.values():
    sp.set_edgecolor("#333")

info_stage = info_ax.text(0.5, 0.97, "—", ha="center", va="top",
                          color="white", fontsize=11, fontweight="bold",
                          wrap=True)
info_T     = info_ax.text(0.5, 0.78, "T: —", ha="center", color="#aaa", fontsize=9)
info_L     = info_ax.text(0.5, 0.63, "L: —", ha="center", color="#aaa", fontsize=9)

star_disc = mpatches.Circle((0.5, 0.28), 0.18,
                             color="yellow", transform=info_ax.transAxes,
                             zorder=10)
info_ax.add_patch(star_disc)

# Legend
legend_ax = fig.add_axes([0.01, 0.42, 0.18, 0.22], facecolor="#0f0f1a")
legend_ax.set_xlim(0, 1)
legend_ax.set_ylim(0, 1)
legend_ax.axis("off")
for i, (key, cfg) in enumerate(star_configs.items()):
    y = 0.78 - i * 0.30
    legend_ax.plot([0.05, 0.22], [y, y], color=cfg["color"], lw=2, ls="--")
    short = key.split("(")[1].rstrip(")")
    legend_ax.text(0.27, y, short, color="#aaa", fontsize=8, va="center")

# ── State ──────────────────────────────────────────────────────────────────
state = dict(
    path=[], frame=0, color="#ffd166", end="WD",
    # SN states:
    sn_phase="none",   # "none" | "flash" | "ring" | "ns" | "done"
    sn_flash_tick=0,
    sn_r=0,
    sn_T=3800, sn_L=300000,   # position of the supernova (= Red supergiant)
)


def build_path(key):
    cfg = star_configs[key]
    state["path"]    = interp_path(cfg["stages"])
    state["frame"]   = 0
    state["color"]   = cfg["color"]
    state["end"]     = cfg["end"]
    state["sn_phase"] = "none"
    state["sn_flash_tick"] = 0
    state["sn_r"]    = 0
    evo_line.set_data([], [])
    evo_line.set_color(cfg["color"])
    halo.set_color(cfg["color"])
    sn_circle.set_alpha(0)
    sn_circle.set_radius(0)
    flash_circle.set_alpha(0)
    flash_circle.set_radius(0)
    ns_pt.set_data([], [])
    ns_label.set_text("")
    # Store Red supergiant endpoint for SN position
    last = cfg["stages"][-1]
    state["sn_T"] = last["T"]
    state["sn_L"] = last["L"]


def on_radio(label):
    build_path(label)


radio.on_clicked(on_radio)
build_path("Medium (1.0 M☉)")


# ── Animation update ────────────────────────────────────────────────────────
def update(_):
    path  = state["path"]
    frame = state["frame"]

    # ── Post-path SN sequence ──────────────────────────────────────────────
    if frame >= len(path):
        if state["end"] != "SN":
            return (evo_line, active_pt, halo, sn_circle,
                    flash_circle, ns_pt, ns_label, stage_text)

        phase = state["sn_phase"]

        # Phase 1: white flash (30 ticks)
        if phase in ("none", "flash"):
            state["sn_phase"] = "flash"
            tick = state["sn_flash_tick"]
            # Grow then shrink a white overlay
            alpha = np.clip(1 - abs(tick - 15) / 15, 0, 1)
            flash_circle.set_radius(1.5)
            flash_circle.set_alpha(alpha * 0.85)
            active_pt.set_data([state["sn_T"]], [state["sn_L"]])
            active_pt.set_color("white")
            halo.set_data([state["sn_T"]], [state["sn_L"]])
            stage_text.set_text("SUPERNOVA!")
            info_stage.set_text("SUPERNOVA!")
            state["sn_flash_tick"] += 1
            if tick >= 30:
                state["sn_phase"] = "ring"
                state["sn_r"] = 0
                flash_circle.set_alpha(0)
            return (evo_line, active_pt, halo, sn_circle,
                    flash_circle, ns_pt, ns_label, stage_text)

        # Phase 2: expanding ring fades out
        if phase == "ring":
            T_sn, L_sn = state["sn_T"], state["sn_L"]
            sn_circle.set_center((T_sn, L_sn))
            state["sn_r"] += state["sn_r"] * 0.10 + 300
            alpha = max(0, 1 - state["sn_r"] / 10000)
            sn_circle.set_radius(state["sn_r"])
            sn_circle.set_alpha(alpha)
            active_pt.set_data([], [])
            halo.set_data([], [])
            if alpha == 0:
                state["sn_phase"] = "ns"
                sn_circle.set_alpha(0)
            return (evo_line, active_pt, halo, sn_circle,
                    flash_circle, ns_pt, ns_label, stage_text)

        # Phase 3: neutron star appears
        if phase == "ns":
            ns_pt.set_data([NS_T], [NS_L])
            ns_label.set_position((NS_T * 0.85, NS_L * 2.5))
            ns_label.set_text("Neutron Star")
            stage_text.set_text("Neutron Star")
            info_stage.set_text("Neutron Star")
            info_T.set_text(f"T: ~{NS_T:,} K")
            info_L.set_text(f"L: {NS_L:.4f} L☉")
            star_disc.set_color("#00e5ff")
            star_disc.set_radius(0.06)
            state["sn_phase"] = "done"
            return (evo_line, active_pt, halo, sn_circle,
                    flash_circle, ns_pt, ns_label, stage_text)

        # Phase done — stay static
        return (evo_line, active_pt, halo, sn_circle,
                flash_circle, ns_pt, ns_label, stage_text)

    # ── Normal path animation ──────────────────────────────────────────────
    T, L, name = path[frame]

    Ts = [p[0] for p in path[:frame + 1]]
    Ls = [p[1] for p in path[:frame + 1]]
    evo_line.set_data(Ts, Ls)

    color = temp_to_color(T)
    active_pt.set_data([T], [L])
    active_pt.set_color(color)
    halo.set_data([T], [L])

    log_L = np.log10(max(L, 1e-4))
    r = np.clip(0.18 + (log_L + 4) * 0.018, 0.10, 0.30)
    star_disc.set_radius(r)
    star_disc.set_color(color)

    info_stage.set_text(name)
    info_T.set_text(f"T: {int(T):,} K")
    L_str = f"{L:.2e}" if L < 0.01 or L > 9999 else f"{L:.1f}"
    info_L.set_text(f"L: {L_str} L☉")

    stage_text.set_text(name)

    state["frame"] += 1
    return (evo_line, active_pt, halo, sn_circle,
            flash_circle, ns_pt, ns_label, stage_text,
            star_disc, info_stage, info_T, info_L)


ani = FuncAnimation(
    fig, update,
    frames=10000,
    interval=INTERVAL_MS,
    blit=False,
)

plt.show()