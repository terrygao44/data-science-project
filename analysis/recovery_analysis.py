"""
Who came back to Macau? Post-pandemic recovery of visitor arrivals by source market.

Reproducible analysis pipeline for the project repository `data-science-project`.

Inputs  (data/)  : visitor_arrivals.csv, stay_type.csv
Outputs (images/): 01_recovery_index.png, 02_shortfall_contribution.png,
                   03_scale_vs_recovery.png
Console          : the summary statistics quoted in README.md

Run with:  python analysis/recovery_analysis.py
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # headless: write PNG files, never open a window
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.lines import Line2D

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
IMAGES = ROOT / "images"
IMAGES.mkdir(exist_ok=True)

BASELINE = 100.0  # index value of the pre-pandemic year, 2019

# Colour palette: Okabe-Ito colourblind-safe hues, one per region.
REGION_COLOR = {
    "Greater China": "#0072B2",
    "Southeast Asia": "#009E73",
    "Northeast Asia": "#D55E00",
    "Other markets": "#CC79A7",
    "All other markets": "#999999",  # residual row, deliberately neutral
}
NEUTRAL = "#3d3d3d"
GRAY = "#666666"
LIGHTGRID = "#dcdcdc"

plt.rcParams["font.family"] = ["Segoe UI", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False


# --------------------------------------------------------------------------
# 1. Load and prepare
# --------------------------------------------------------------------------
def load_arrivals():
    """Return (markets, total) DataFrames with an added `index` column."""
    df = pd.read_csv(DATA / "visitor_arrivals.csv")
    total = df[df["region"] == "Total"].copy()
    markets = df[df["region"] != "Total"].copy()

    for frame in (markets, total):
        frame["change"] = frame["y2024"] - frame["y2019"]
        frame["index"] = frame["y2024"] / frame["y2019"] * BASELINE

    # Residual: the official total minus the markets that DSEC breaks out
    # individually. Keeping it explicit makes the change column reconcile
    # exactly to the published total instead of silently dropping 1.3%.
    residual = pd.DataFrame(
        [
            {
                "market": "All other markets",
                "region": "All other markets",
                "y2019": int(total["y2019"].iloc[0] - markets["y2019"].sum()),
                "y2024": int(total["y2024"].iloc[0] - markets["y2024"].sum()),
            }
        ]
    )
    residual["change"] = residual["y2024"] - residual["y2019"]
    residual["index"] = residual["y2024"] / residual["y2019"] * BASELINE

    markets = markets.sort_values("index", ascending=False).reset_index(drop=True)
    return markets, total.reset_index(drop=True), residual


def load_stay_type():
    """Return the same-day / overnight split as shares of each year's total."""
    stay = pd.read_csv(DATA / "stay_type.csv")
    wide = stay.pivot(index="year", columns="stay_type", values="arrivals")
    wide["total"] = wide.sum(axis=1)
    wide["same_day_share"] = wide["same_day"] / wide["total"] * 100
    wide["overnight_share"] = wide["overnight"] / wide["total"] * 100
    wide["same_day_index"] = wide.loc[2024, "same_day"] / wide.loc[2019, "same_day"] * 100
    wide["overnight_index"] = wide.loc[2024, "overnight"] / wide.loc[2019, "overnight"] * 100
    return wide


# --------------------------------------------------------------------------
# 2. Figure 1 - the recovery index (diverging lollipop)
# --------------------------------------------------------------------------
def figure_recovery_index(markets, total):
    fig, (ax, axf) = plt.subplots(
        2, 1, figsize=(11.5, 8.6), dpi=150,
        gridspec_kw={"height_ratios": [3.2, 1.0], "hspace": 0.42,
                     "top": 0.86, "bottom": 0.07, "left": 0.17, "right": 0.98},
    )

    ys = list(range(len(markets)))
    total_y = ys[-1] + 1.9

    for y, row in zip(ys, markets.itertuples()):
        colour = REGION_COLOR[row.region]
        ax.plot([BASELINE, row.index], [y, y], color=colour, lw=2.2,
                solid_capstyle="round", zorder=2)
        ax.scatter([row.index], [y], s=100, color=colour, zorder=3)
        offset = 2.6 if row.index >= BASELINE else -2.6
        ax.text(row.index + offset, y, f"{row.index:.1f}%", va="center",
                ha="left" if row.index >= BASELINE else "right",
                fontsize=9.5, color="#333333")

    total_index = float(total["index"].iloc[0])
    ax.plot([BASELINE, total_index], [total_y, total_y], color=NEUTRAL, lw=2.6,
            solid_capstyle="round", zorder=2)
    ax.scatter([total_index], [total_y], s=115, color=NEUTRAL, zorder=3)
    ax.text(total_index - 2.6, total_y, f"{total_index:.1f}%", va="center",
            ha="right", fontsize=10, color=NEUTRAL, fontweight="bold")
    ax.axhline(total_y - 0.95, color="#e3e3e3", lw=1, zorder=1)

    ax.axvline(BASELINE, color="#555555", lw=1.2, ls=(0, (4, 3)), zorder=1)
    ax.text(BASELINE, -0.85, "2019 baseline = 100", ha="center", va="bottom",
            fontsize=9, color=GRAY)

    # Annotate the single most consequential number: the Mainland shortfall
    # is 77% of Macau's total gap even though its index (87.7%) looks mild.
    # The denominator is the *published* total change, not the sum of the
    # markets DSEC breaks out, so this matches the headline gap.
    mainland = markets[markets["market"] == "Mainland China"].iloc[0]
    mainland_y = int(markets.index[markets["market"] == "Mainland China"][0])
    total_change = float(total["change"].iloc[0])
    ax.annotate(
        f"Mainland China: {mainland['change'] / 1e6:.2f}M visitors vs 2019 —\n"
        f"{mainland['change'] / total_change * 100:.0f}% of Macau's total shortfall, "
        f"because it is {mainland['y2024'] / float(total['y2024'].iloc[0]) * 100:.0f}% "
        f"of all arrivals",
        xy=(mainland["index"] - 2, mainland_y), xytext=(36, 1.4),
        fontsize=9.2, color="#333333", ha="left", va="center",
        arrowprops=dict(arrowstyle="-", color="#999999", lw=1, shrinkA=4, shrinkB=4),
    )
    japan = markets[markets["market"] == "Japan"].iloc[0]
    japan_y = int(markets.index[markets["market"] == "Japan"][0])
    ax.text(japan["index"] + 2.5, japan_y + 0.6, "largest relative gap",
            fontsize=9.2, color="#333333", ha="left", va="center")

    ax.set_yticks(ys + [total_y])
    ax.set_yticklabels(list(markets["market"]) + ["Total (all markets)"], fontsize=10.5)
    ax.get_yticklabels()[-1].set_fontweight("bold")
    ax.set_xlim(34, 128)
    ax.set_ylim(total_y + 0.6, -1.45)
    ax.set_xticks([40, 60, 80, 100, 120])
    ax.set_xticklabels(["40%", "60%", "80%", "100%", "120%"], fontsize=10, color="#444444")
    ax.xaxis.set_ticks_position("top")
    ax.xaxis.set_label_position("top")
    ax.set_xlabel("2024 visitor arrivals as a share of 2019 arrivals",
                  fontsize=11, labelpad=6)
    ax.tick_params(axis="both", length=0, pad=4)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_axisbelow(True)
    for xv in (40, 60, 80, 120):
        ax.axvline(xv, color=LIGHTGRID, lw=0.9, zorder=0)

    handles = [Line2D([0], [0], marker="o", color="none", markerfacecolor=c,
                      markersize=9, label=r)
               for r, c in REGION_COLOR.items() if r != "All other markets"]
    ax.legend(handles=handles, loc="lower right", frameon=False, fontsize=9.5,
              handletextpad=0.1, borderaxespad=0.2)

    # ---- facet: composition by stay type ----
    stay = load_stay_type()
    seg = {"same_day": "#BFCDDC", "overnight": "#4477AA"}
    for y, year in ((0.0, 2019), (1.0, 2024)):
        same = stay.loc[year, "same_day_share"]
        axf.barh(y, same, height=0.62, color=seg["same_day"], zorder=2)
        axf.barh(y, 100 - same, left=same, height=0.62, color=seg["overnight"], zorder=2)
        axf.text(same / 2, y, f"Same-day {same:.1f}%", ha="center", va="center",
                 fontsize=9.5, color="#333333", zorder=3)
        axf.text(same + (100 - same) / 2, y, f"Overnight {100 - same:.1f}%",
                 ha="center", va="center", fontsize=9.5, color="white", zorder=3)

    axf.set_yticks([0.0, 1.0])
    axf.set_yticklabels(["2019", "2024"], fontsize=11, fontweight="bold")
    axf.set_xlim(0, 100)
    axf.set_ylim(1.75, -0.55)
    axf.set_xticks([])
    axf.tick_params(length=0)
    for spine in axf.spines.values():
        spine.set_visible(False)
    axf.set_title("Share of arrivals by stay type", loc="left", fontsize=11.5,
                  fontweight="bold", pad=16)
    axf.text(0, 1.62,
             f"Same-day visitors are fully back ({stay.loc[2024, 'same_day_index']:.0f}% "
             f"of 2019), while overnight guests — the ones who stay and spend — are "
             f"still {100 - stay.loc[2024, 'overnight_index']:.0f}% below.",
             fontsize=9.2, color=GRAY, va="center")

    fig.text(0.015, 0.975, "Who came back to Macau?", fontsize=18,
             fontweight="bold", color="#222222", ha="left", va="top")
    fig.text(0.015, 0.945,
             "Visitor arrivals in 2024 as a share of 2019 — only the Philippines, "
             "Indonesia and Singapore exceeded their pre-pandemic counts",
             fontsize=11.3, color="#444444", ha="left", va="top")
    fig.text(0.015, 0.028,
             "Data: Statistics and Census Service (DSEC), Macao SAR — \"Visitor arrivals "
             "for December and the whole year of 2024\" (21 Jan 2025) and 2019 annual "
             "visitor statistics; values rounded to the nearest thousand.",
             fontsize=7.8, color="#777777", ha="left", va="bottom")
    fig.text(0.015, 0.012,
             "Markets shown are those with full-year 2024 figures in DSEC's release; "
             "Europe is not shown because that release does not break it out.",
             fontsize=7.8, color="#777777", ha="left", va="bottom")

    out = IMAGES / "01_recovery_index.png"
    fig.savefig(out, dpi=200, facecolor="white")
    plt.close(fig)
    return out


# --------------------------------------------------------------------------
# 3. Figure 2 - who caused the shortfall (contribution to the change)
# --------------------------------------------------------------------------
def figure_shortfall(markets, total, residual):
    """Bars of each market's change, plus the running total towards the shortfall.

    Both series share one zero-based axis measured in millions of visitors, so
    the running-total line visibly lands on the published total at the end.
    """
    data = pd.concat([markets, residual], ignore_index=True)
    data = data.sort_values("change", ascending=True).reset_index(drop=True)

    total_change = float(total["change"].iloc[0])
    values = (data["change"] / 1e6).tolist()
    running, acc = [], 0.0
    for v in values:
        acc += v
        running.append(acc)

    fig, ax = plt.subplots(figsize=(11.0, 6.9), dpi=150)
    fig.subplots_adjust(top=0.80, bottom=0.225, left=0.205, right=0.97)

    ys = list(range(len(data)))
    colors = [REGION_COLOR[r] for r in data["region"]]
    ax.barh(ys, values, height=0.62, color=colors, zorder=3,
            label="Change in arrivals, by market")

    for y, v in zip(ys, values):
        ax.text(v - 0.08 if v < 0 else v + 0.08, y, f"{v:+.2f}M", va="center",
                ha="right" if v < 0 else "left", fontsize=9.2, color="#333333",
                zorder=6)

    # Running total: accumulates every loss from the top down and then lets the
    # three growing markets give a little back, ending on the published total.
    ax.plot(running, ys, color="#555555", lw=1.5, marker="o", ms=4.5,
            markerfacecolor="white", markeredgewidth=1.4, zorder=5,
            label="Running total")

    ax.axvline(0, color="#555555", lw=1.1, zorder=4)
    ax.axvline(total_change / 1e6, color="#C0392B", lw=1.3, ls=(0, (4, 3)),
               zorder=4, label=f"Total shortfall ({total_change / 1e6:.2f}M)")

    ax.set_yticks(ys)
    ax.set_yticklabels(list(data["market"]), fontsize=10.5)
    ax.get_yticklabels()[0].set_fontweight("bold")
    ax.set_ylim(len(data) - 0.4, -0.9)
    ax.set_xlim(-5.05, 0.95)
    ax.set_xticks([-4, -3, -2, -1, 0])
    ax.set_xticklabels(["−4M", "−3M", "−2M", "−1M", "0"], fontsize=10,
                       color="#444444")
    ax.set_xlabel("Change in visitor arrivals, 2024 vs 2019 (millions)",
                  fontsize=11, labelpad=8)
    ax.tick_params(length=0, pad=6)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_axisbelow(True)
    for xv in (-4, -3, -2, -1):
        ax.axvline(xv, color=LIGHTGRID, lw=0.9, zorder=0)

    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.145), ncol=3,
              frameon=False, fontsize=9.3, handletextpad=0.6, columnspacing=2.2)

    fig.text(0.015, 0.965, "Where Macau's missing visitors went",
             fontsize=18, fontweight="bold", color="#222222", ha="left", va="top")
    fig.text(0.015, 0.916,
             f"The market is {abs(total_change) / 1e6:.2f}M visitors below 2019. "
             "Reading down the running total shows how few markets build that gap.",
             fontsize=11.3, color="#444444", ha="left", va="top")
    fig.text(0.015, 0.028,
             "Data: DSEC, Macao SAR (2024 full-year release, 21 Jan 2025; 2019 annual "
             "statistics). \"All other markets\" is the residual between the published "
             "total and the markets DSEC breaks out, so the series reconciles exactly.",
             fontsize=7.8, color="#777777", ha="left", va="bottom")

    out = IMAGES / "02_shortfall_contribution.png"
    fig.savefig(out, dpi=200, facecolor="white")
    plt.close(fig)
    return out


# --------------------------------------------------------------------------
# 4. Figure 3 - the trap the index hides: recovery vs. absolute size
# --------------------------------------------------------------------------
def figure_scale(markets, total):
    fig, ax = plt.subplots(figsize=(10.6, 6.8), dpi=150)
    fig.subplots_adjust(top=0.82, bottom=0.12, left=0.09, right=0.97)

    for row in markets.itertuples():
        # Marker area grows with the absolute change, but on a square-root
        # scale: on a linear scale Mainland China would swallow the panel.
        size = 30 + 12 * (abs(row.change) / 1000) ** 0.5
        ax.scatter(row.y2024, row.index, s=size, color=REGION_COLOR[row.region],
                   alpha=0.9, zorder=3, edgecolor="white", linewidth=1.3)

    ax.axhline(BASELINE, color="#555555", lw=1.2, ls=(0, (4, 3)), zorder=1)
    ax.text(1.6e6, BASELINE + 1.6, "2019 level = 100", fontsize=9, color=GRAY)

    total_index = float(total["index"].iloc[0])
    ax.scatter(total["y2024"], total_index, marker="D", s=95, color=NEUTRAL,
               zorder=4, edgecolor="white", linewidth=1.3)

    # Labels are placed with point offsets so that nothing is clipped by the
    # axes. Thailand and Malaysia sit almost on top of each other, so they are
    # pushed to opposite sides of the same height.
    label_side = {
        "Philippines": (10, 3, "left"), "Indonesia": (10, 3, "left"),
        "Singapore": (10, 3, "left"), "Hong Kong SAR": (10, 3, "left"),
        "Taiwan region": (10, 3, "left"), "United States": (10, 3, "left"),
        "Republic of Korea": (10, 3, "left"), "Japan": (10, 3, "left"),
        "India": (10, 3, "left"),
        "Thailand": (10, 9, "left"), "Malaysia": (10, -10, "left"),
        "Mainland China": (-11, 4, "right"),
    }
    for row in markets.itertuples():
        dx, dy, ha = label_side[row.market]
        ax.annotate(row.market, xy=(row.y2024, row.index),
                    xytext=(dx, dy), textcoords="offset points",
                    fontsize=9, color="#333333", ha=ha, va="center", zorder=6)
    ax.annotate("Total", xy=(float(total["y2024"].iloc[0]), total_index),
                xytext=(0, -15), textcoords="offset points", fontsize=9.5,
                color=NEUTRAL, fontweight="bold", ha="center", va="top", zorder=6)

    ax.set_xscale("log")
    ax.set_xlim(9e4, 6.5e7)
    ax.set_ylim(35, 128)
    ax.set_xticks([1e5, 3e5, 1e6, 3e6, 1e7, 3e7])
    ax.set_xticklabels(["100k", "300k", "1M", "3M", "10M", "30M"], fontsize=10,
                       color="#444444")
    ax.set_yticks([40, 60, 80, 100, 120])
    ax.set_yticklabels(["40%", "60%", "80%", "100%", "120%"], fontsize=10,
                       color="#444444")
    ax.set_xlabel("2024 visitor arrivals (log scale) — market size", fontsize=11,
                  labelpad=8)
    ax.set_ylabel("2024 arrivals as a share of 2019", fontsize=11, labelpad=8)
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_axisbelow(True)
    for xv in (3e5, 3e6, 3e7):
        ax.axvline(xv, color=LIGHTGRID, lw=0.9, zorder=0)
    for yv in (60, 80, 120):
        ax.axhline(yv, color=LIGHTGRID, lw=0.9, zorder=0)

    handles = [Line2D([0], [0], marker="o", color="none", markerfacecolor=c,
                      markersize=9, label=r)
               for r, c in REGION_COLOR.items() if r != "All other markets"]
    ax.legend(handles=handles, loc="lower right", frameon=False, fontsize=9.5,
              handletextpad=0.1, borderaxespad=0.3)

    fig.text(0.015, 0.965, "Size versus recovery: two different stories",
             fontsize=18, fontweight="bold", color="#222222", ha="left", va="top")
    fig.text(0.015, 0.917,
             "Larger markers mean a larger absolute change in arrivals, so the "
             "biggest gap is not the lowest percentage.",
             fontsize=11.3, color="#444444", ha="left", va="top")
    fig.text(0.015, 0.025,
             "Data: DSEC, Macao SAR (2024 full-year release, 21 Jan 2025; 2019 annual "
             "statistics). Twelve source markets plus the published total.",
             fontsize=7.8, color="#777777", ha="left", va="bottom")

    out = IMAGES / "03_scale_vs_recovery.png"
    fig.savefig(out, dpi=200, facecolor="white")
    plt.close(fig)
    return out


# --------------------------------------------------------------------------
# 5. Summary statistics quoted in README.md
# --------------------------------------------------------------------------
def report(markets, total, residual):
    stay = load_stay_type()
    total19 = float(total["y2019"].iloc[0])
    total24 = float(total["y2024"].iloc[0])
    shortfall = total19 - total24

    print("=" * 68)
    print("Macau visitor arrivals: 2019 vs 2024")
    print("=" * 68)
    print(f"Arrivals 2019 : {total19:,.0f}")
    print(f"Arrivals 2024 : {total24:,.0f}  ({total24 / total19 * 100:.1f}% of 2019)")
    print(f"Total shortfall: {shortfall:,.0f}")
    print(f"Markets broken out cover {float(markets['y2024'].sum()) / total24 * 100:.1f}% "
          f"of 2024 arrivals")
    print(f"Residual ('all other markets') change: {float(residual['change'].iloc[0]):,.0f}")
    print("-" * 68)
    print("Recovery index by market (2024 as % of 2019)")
    for row in markets.itertuples():
        print(f"  {row.market:<20} {row.index:6.1f}%   {row.change / 1e6:+7.2f}M")
    print("-" * 68)
    above = markets[markets["index"] >= BASELINE]
    print(f"Markets above the 2019 baseline: {len(above)} "
          f"({', '.join(above['market'])})")
    mainland = markets.loc[markets["market"] == "Mainland China"].iloc[0]
    print(f"Mainland China share of arrivals 2024: "
          f"{mainland['y2024'] / total24 * 100:.1f}%")
    print(f"Mainland China share of the shortfall: "
          f"{mainland['change'] / (total24 - total19) * 100:.1f}%")
    print("-" * 68)
    print("Stay type")
    for year in (2019, 2024):
        print(f"  {year}: same-day {stay.loc[year, 'same_day_share']:.1f}%  "
              f"overnight {stay.loc[year, 'overnight_share']:.1f}%")
    print(f"  Same-day visitors 2024 vs 2019: {stay.loc[2024, 'same_day_index']:.1f}%")
    print(f"  Overnight guests 2024 vs 2019: {stay.loc[2024, 'overnight_index']:.1f}%")
    print("=" * 68)


def main():
    markets, total, residual = load_arrivals()
    report(markets, total, residual)
    for path in (figure_recovery_index(markets, total),
                 figure_shortfall(markets, total, residual),
                 figure_scale(markets, total)):
        print("saved:", path.relative_to(ROOT))


if __name__ == "__main__":
    main()
