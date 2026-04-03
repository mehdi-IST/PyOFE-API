#!/usr/bin/env python3
"""
NMR Lab Suite  —  Professional Edition
=======================================
Tab 1 : SDF Processor
Tab 2 : FFC-IST Data Processor

All original processing logic preserved.
UI completely redesigned: dark scientific-instrument theme.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import numpy as np
import re, os, math, time, threading


# ═══════════════════════════════════════════════════════════════════
#  DESIGN TOKENS  — single source of truth for every colour / font
# ═══════════════════════════════════════════════════════════════════
C = {
    "bg"       : "#12151c",   # root background
    "panel"    : "#1a1e28",   # tab / panel background
    "card"     : "#222738",   # inner cards
    "card2"    : "#1e2230",   # alternate card shade
    "border"   : "#2e3450",   # subtle borders
    "accent"   : "#3dd9b3",   # teal accent
    "accent2"  : "#5b8dee",   # blue accent
    "accent3"  : "#f0883e",   # orange accent  (warnings/highlights)
    "text"     : "#e4e8f4",   # primary text
    "muted"    : "#6b7699",   # secondary / label text
    "success"  : "#4cd98a",   # green
    "warning"  : "#f0c040",   # yellow
    "error"    : "#f07070",   # red
    "data_fg"  : "#a8d8ff",   # data value foreground
    "tag_fg"   : "#3dd9b3",   # TAG line
    "header_bg": "#0f121a",   # column-header rows
    "sel_bg"   : "#2e3e6e",   # listbox selection
    "btn"      : "#253060",   # button normal
    "btn_ho"   : "#3040a0",   # button hover
    "btn_act"  : "#3dd9b3",   # action button
    "btn_act_fg":"#0d1520",
    "entry_bg" : "#1a1e2e",   # entry widget background
    "entry_bd" : "#3040a0",   # entry border
}

FONT_MONO  = ("Consolas", 10)
FONT_MONO_S= ("Consolas", 9)
FONT_LABEL = ("Segoe UI", 9)
FONT_BOLD  = ("Segoe UI", 9, "bold")
FONT_TITLE = ("Segoe UI", 12, "bold")
FONT_SMALL = ("Segoe UI", 8)


# ═══════════════════════════════════════════════════════════════════
#  CUSTOM WIDGET HELPERS
# ═══════════════════════════════════════════════════════════════════

def styled_button(parent, text, command, kind="normal", width=None, **kw):
    """Returns a tk.Button with hover effect."""
    bg  = C["btn_act"] if kind == "action" else C["btn"]
    fg  = C["btn_act_fg"] if kind == "action" else C["text"]
    hbg = "#50ead0"    if kind == "action" else C["btn_ho"]

    cfg = dict(text=text, command=command,
               bg=bg, fg=fg,
               activebackground=hbg, activeforeground=fg,
               font=FONT_BOLD, relief="flat",
               cursor="hand2", padx=14, pady=6,
               bd=0, highlightthickness=0)
    if width:
        cfg["width"] = width
    cfg.update(kw)
    btn = tk.Button(parent, **cfg)

    def on_enter(_):  btn.config(bg=hbg)
    def on_leave(_):  btn.config(bg=bg)
    btn.bind("<Enter>", on_enter)
    btn.bind("<Leave>", on_leave)
    return btn


def labeled_entry(parent, label_text, var, width=18, **kw):
    """Label + Entry pair packed side-by-side."""
    tk.Label(parent, text=label_text,
             bg=C["card"], fg=C["muted"],
             font=FONT_LABEL).pack(side="left", padx=(10, 3))
    e = tk.Entry(parent, textvariable=var, width=width,
                 bg=C["entry_bg"], fg=C["data_fg"],
                 insertbackground=C["accent"],
                 relief="flat", font=FONT_MONO_S,
                 highlightthickness=1,
                 highlightbackground=C["border"],
                 highlightcolor=C["accent"])
    e.pack(side="left", padx=(0, 8))
    return e


def section_label(parent, text):
    """Thin accent-bar + section title."""
    f = tk.Frame(parent, bg=C["panel"])
    f.pack(fill="x", padx=12, pady=(10, 4))
    tk.Frame(f, bg=C["accent"], width=3).pack(side="left", fill="y")
    tk.Label(f, text=f"  {text}",
             bg=C["panel"], fg=C["accent"],
             font=FONT_BOLD).pack(side="left")
    return f


def card_frame(parent, **kw):
    f = tk.Frame(parent, bg=C["card"],
                 highlightthickness=1,
                 highlightbackground=C["border"])
    f.pack(fill="x", padx=12, pady=4, **kw)
    return f


def separator(parent):
    tk.Frame(parent, bg=C["border"], height=1).pack(fill="x", padx=12, pady=6)


class StatusBar(tk.Frame):
    """Bottom status strip with icon + message + optional right info."""
    def __init__(self, parent, **kw):
        super().__init__(parent, bg=C["header_bg"], pady=4, **kw)
        self._icon = tk.Label(self, text="●", bg=C["header_bg"],
                              fg=C["muted"], font=("Segoe UI", 9))
        self._icon.pack(side="left", padx=(10, 4))
        self._msg = tk.Label(self, text="Ready", bg=C["header_bg"],
                             fg=C["muted"], font=FONT_LABEL, anchor="w")
        self._msg.pack(side="left", fill="x", expand=True)
        self._right = tk.Label(self, text="", bg=C["header_bg"],
                               fg=C["muted"], font=FONT_SMALL)
        self._right.pack(side="right", padx=12)

    def set(self, msg, kind="info", right=""):
        colours = {"info": C["muted"], "ok": C["success"],
                   "warn": C["warning"], "error": C["error"],
                   "busy": C["accent"]}
        icons   = {"info": "○", "ok": "✔", "warn": "⚠",
                   "error": "✖", "busy": "◌"}
        col = colours.get(kind, C["muted"])
        self._icon.config(text=icons.get(kind, "●"), fg=col)
        self._msg.config(text=msg, fg=col)
        self._right.config(text=right)


class DataText(tk.Frame):
    """Monospaced scrollable text widget styled for data display."""
    def __init__(self, parent, **kw):
        super().__init__(parent, bg=C["card"], **kw)
        self._txt = scrolledtext.ScrolledText(
            self, font=FONT_MONO,
            bg=C["card"], fg=C["text"],
            insertbackground=C["accent"],
            selectbackground=C["sel_bg"],
            relief="flat", bd=0,
            wrap=tk.NONE,
            padx=10, pady=8
        )
        self._txt.pack(fill="both", expand=True)
        # horizontal scroll
        xscr = tk.Scrollbar(self, orient="horizontal",
                            command=self._txt.xview,
                            bg=C["card"], troughcolor=C["bg"])
        xscr.pack(fill="x")
        self._txt.configure(xscrollcommand=xscr.set)

        # colour tags
        self._txt.tag_config("tag_line",  foreground=C["tag_fg"],
                              font=("Consolas", 10, "bold"))
        self._txt.tag_config("data_line", foreground=C["accent2"],
                              font=("Consolas", 10, "bold"))
        self._txt.tag_config("comment",   foreground=C["muted"])
        self._txt.tag_config("value",     foreground=C["data_fg"])
        self._txt.tag_config("warning",   foreground=C["warning"])
        self._txt.tag_config("error",     foreground=C["error"])
        self._txt.tag_config("row_hi",    background=C["card2"])

    def widget(self):   return self._txt
    def clear(self):    self._txt.delete("1.0", tk.END)
    def insert(self, text, tag=""):
        self._txt.insert(tk.END, text, tag)
    def set_state(self, state):
        self._txt.configure(state=state)


# ═══════════════════════════════════════════════════════════════════
#  TAB 1  —  SDF PROCESSOR
# ═══════════════════════════════════════════════════════════════════
class SDFProcessorTab(tk.Frame):

    def __init__(self, parent):
        super().__init__(parent, bg=C["panel"])
        self.processed_content = ""
        self.row_range = None
        self._file_path = ""
        self._build()

    # ── BUILD UI ────────────────────────────────────────────────────
    def _build(self):
        # ── top controls ──
        top = tk.Frame(self, bg=C["panel"])
        top.pack(fill="x", padx=0, pady=0)

        # file row
        section_label(top, "INPUT FILE")
        file_card = card_frame(top)
        file_card.pack(fill="x", padx=12, pady=4)

        self._path_var = tk.StringVar()
        self._path_entry = tk.Entry(
            file_card, textvariable=self._path_var,
            bg=C["entry_bg"], fg=C["data_fg"],
            insertbackground=C["accent"],
            relief="flat", font=FONT_MONO_S, width=60,
            highlightthickness=1,
            highlightbackground=C["border"],
            highlightcolor=C["accent"],
            state="readonly"
        )
        self._path_entry.pack(side="left", padx=10, pady=8, fill="x", expand=True)
        styled_button(file_card, "Browse…", self.load_file,
                      kind="action").pack(side="left", padx=8, pady=8)

        # options row
        section_label(top, "OPTIONS")
        opt_card = card_frame(top)
        opt_card.pack(fill="x", padx=12, pady=4)

        tk.Label(opt_card, text="Row Range (e.g. 0:349):",
                 bg=C["card"], fg=C["muted"],
                 font=FONT_LABEL).pack(side="left", padx=(10, 4), pady=8)

        self._range_var = tk.StringVar()
        tk.Entry(opt_card, textvariable=self._range_var, width=12,
                 bg=C["entry_bg"], fg=C["data_fg"],
                 insertbackground=C["accent"],
                 relief="flat", font=FONT_MONO_S,
                 highlightthickness=1,
                 highlightbackground=C["border"],
                 highlightcolor=C["accent"]
                 ).pack(side="left", padx=(0, 20), pady=8)

        self._debug_var = tk.IntVar()
        db = tk.Checkbutton(opt_card, text="Show Debug Info",
                            variable=self._debug_var,
                            bg=C["card"], fg=C["muted"],
                            selectcolor=C["entry_bg"],
                            activebackground=C["card"],
                            activeforeground=C["text"],
                            font=FONT_LABEL)
        db.pack(side="left", padx=8)

        # action buttons
        section_label(top, "ACTIONS")
        act_card = card_frame(top)
        act_card.pack(fill="x", padx=12, pady=4)

        styled_button(act_card, "⟳  Process File",
                      self._process_current,
                      kind="action").pack(side="left", padx=8, pady=8)
        styled_button(act_card, "⇗  Normalize",
                      self.normalize_output).pack(side="left", padx=4, pady=8)
        styled_button(act_card, "💾  Save Output",
                      self.save_file).pack(side="left", padx=4, pady=8)
        styled_button(act_card, "✕  Clear",
                      self._clear).pack(side="left", padx=4, pady=8)

        # stats strip
        self._stats_frame = tk.Frame(top, bg=C["panel"])
        self._stats_frame.pack(fill="x", padx=12, pady=(2, 0))
        self._stat_zones  = self._stat_label("Zones: —")
        self._stat_blocks = self._stat_label("NBLK: —")
        self._stat_bs     = self._stat_label("BS: —")
        self._stat_file   = self._stat_label("File: —")

        separator(self)

        # ── output area ──
        section_label(self, "OUTPUT")
        self._data_view = DataText(self)
        self._data_view.pack(fill="both", expand=True, padx=12, pady=(0, 6))

        # status bar
        self._status = StatusBar(self)
        self._status.pack(fill="x", side="bottom")

    def _stat_label(self, text):
        lbl = tk.Label(self._stats_frame, text=text,
                       bg=C["panel"], fg=C["muted"], font=FONT_SMALL)
        lbl.pack(side="left", padx=10)
        return lbl

    def _update_stats(self, zones=None, nblk=None, bs=None, fname=None):
        if zones  is not None: self._stat_zones.config( text=f"Zones: {zones}")
        if nblk   is not None: self._stat_blocks.config(text=f"NBLK: {nblk}")
        if bs     is not None: self._stat_bs.config(    text=f"BS: {bs}")
        if fname  is not None: self._stat_file.config(  text=f"File: {fname}")

    # ── FILE LOADING ────────────────────────────────────────────────
    def load_file(self):
        fp = filedialog.askopenfilename(
            filetypes=[("SDF files", "*.sdf"), ("All files", "*.*")])
        if fp:
            self._file_path = fp
            self._path_var.set(fp)
            self._data_view.clear()
            self.process_file(fp)

    def _process_current(self):
        if self._file_path:
            self._data_view.clear()
            self.process_file(self._file_path)
        else:
            messagebox.showinfo("No File", "Load an SDF file first.")

    def _clear(self):
        self._data_view.clear()
        self.processed_content = ""
        self._path_var.set("")
        self._file_path = ""
        self._status.set("Cleared.", "info")

    # ── SAVE ────────────────────────────────────────────────────────
    def save_file(self):
        if not self.processed_content:
            messagebox.showwarning("Nothing to Save", "Process a file first.")
            return
        fp = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if fp:
            try:
                with open(fp, "w") as f:
                    f.write(self.processed_content)
                self._status.set(f"Saved → {fp}", "ok")
                messagebox.showinfo("Saved", f"Output saved to:\n{fp}")
            except Exception as e:
                messagebox.showerror("Save Error", str(e))

    # ── NORMALIZE  (original logic unchanged) ───────────────────────
    def normalize_output(self):
        if not self.processed_content:
            messagebox.showwarning("Nothing to Normalize", "Process a file first.")
            return
        try:
            lines = self.processed_content.splitlines()
            normalized_lines = []
            current_zone = []
            inside_zone = False

            def normalize_zone(zone_lines):
                data_lines = []
                for line in zone_lines:
                    if line.startswith("#") or "N/A" in line:
                        continue
                    parts = line.split()
                    if len(parts) >= 2:
                        try:
                            data_lines.append(float(parts[1]))
                        except ValueError:
                            continue
                if not data_lines:
                    return zone_lines
                min_val  = min(data_lines)
                max_val  = max(data_lines)
                range_val = max_val - min_val if max_val != min_val else 1
                norm_values = [(v - min_val) / range_val for v in data_lines]
                norm_zone = []
                norm_index = 0
                for line in zone_lines:
                    if line.startswith("#") or "N/A" in line:
                        norm_zone.append(line)
                    else:
                        parts = line.split()
                        if len(parts) >= 2:
                            try:
                                float(parts[1])
                                parts[1] = f"{norm_values[norm_index]:<15.6f}"
                                norm_index += 1
                                norm_zone.append(" ".join(parts))
                            except ValueError:
                                norm_zone.append(line)
                        else:
                            norm_zone.append(line)
                return norm_zone

            for line in lines:
                if line.startswith("# DATA"):
                    if current_zone:
                        normalized_lines.extend(normalize_zone(current_zone))
                        normalized_lines.append("")
                    current_zone = [line]
                    inside_zone = True
                elif inside_zone and line.strip() == "":
                    current_zone.append(line)
                    normalized_lines.extend(normalize_zone(current_zone))
                    current_zone = []
                    inside_zone = False
                else:
                    current_zone.append(line)

            if current_zone:
                normalized_lines.extend(normalize_zone(current_zone))

            self._data_view.clear()
            for line in normalized_lines:
                if line.startswith("# DATA"):
                    self._data_view.insert(line + "\n", "data_line")
                elif line.startswith("#  TAG") or line.startswith("# TAG"):
                    self._data_view.insert(line + "\n", "tag_line")
                elif line.startswith("#"):
                    self._data_view.insert(line + "\n", "comment")
                else:
                    self._data_view.insert(line + "\n", "value")

            self.processed_content = "\n".join(normalized_lines)
            self._status.set("Normalization applied.", "ok")

        except Exception as e:
            self._data_view.insert(f"ERROR in normalization: {e}\n", "error")
            self._status.set(f"Normalization error: {e}", "error")

    # ── PROCESS FILE  (original logic unchanged) ────────────────────
    def process_file(self, file_path):
        self._status.set("Loading file…", "busy")
        self.update_idletasks()
        t0 = time.time()
        try:
            with open(file_path, "r") as fh:
                lines = fh.readlines()

            range_str = self._range_var.get().strip()
            if range_str:
                try:
                    start, end = map(int, range_str.split(":"))
                    if start >= 0 and end >= start:
                        self.row_range = (start, end)
                    else:
                        raise ValueError()
                except Exception:
                    self._data_view.insert(
                        f"⚠  Invalid row range '{range_str}'. Ignored.\n", "warning")
                    self.row_range = None
            else:
                self.row_range = None

            zones               = []
            current_zone        = None
            data_lines          = []
            zone_params         = {}
            global_params       = {}
            tau_formulas        = []
            current_tau_index   = 0
            in_parameter_summary= False
            in_data_section     = False
            current_zone_has_data = False

            for raw in lines:
                line = raw.strip()
                if "PARAMETER SUMMARY" in line:
                    if current_zone and current_zone_has_data:
                        zones.append((current_zone, zone_params.copy(),
                                      data_lines, current_tau_index))
                    current_zone = None
                    zone_params  = {}
                    data_lines   = []
                    current_zone_has_data = False
                    in_parameter_summary  = True
                    in_data_section       = False
                    continue

                elif line.startswith("ZONE"):
                    if current_zone and current_zone_has_data and not in_parameter_summary:
                        zones.append((current_zone, zone_params.copy(),
                                      data_lines, current_tau_index))
                    in_parameter_summary = False
                    in_data_section      = False
                    current_zone         = line
                    zone_params          = {}
                    data_lines           = []
                    current_zone_has_data = False
                    continue

                if "=" in line:
                    parts = [p.strip() for p in line.split("=", 1)]
                    if len(parts) == 2:
                        pname, pval = parts
                        if in_parameter_summary:
                            if pname in ("NBLK", "BS"):
                                global_params[pname] = pval
                            elif pname == "TAU":
                                tau_formulas.append(line)
                        elif current_zone:
                            if pname == "T1MAX":
                                try:
                                    zone_params[pname] = str(float(pval) / 1000000)
                                except ValueError:
                                    zone_params[pname] = pval
                            elif pname == "BR":
                                zone_params["dum"] = pval
                            else:
                                zone_params[pname] = pval

                if line == "DATA" and current_zone:
                    in_data_section = True
                    if tau_formulas and current_tau_index < len(tau_formulas):
                        current_tau_index += 1
                    continue

                if in_data_section and current_zone:
                    parts = line.split()
                    if len(parts) >= 3:
                        try:
                            float(parts[2])
                            data_lines.append(line)
                            current_zone_has_data = True
                        except ValueError:
                            continue

            if current_zone and current_zone_has_data:
                zones.append((current_zone, zone_params.copy(),
                              data_lines, current_tau_index))

            if "NBLK" not in global_params or "BS" not in global_params:
                raise ValueError("NBLK or BS not found in PARAMETER SUMMARY.")

            nblk = int(global_params["NBLK"])
            bs   = int(float(global_params["BS"]))

            self._update_stats(
                zones=len(zones), nblk=nblk, bs=bs,
                fname=os.path.basename(file_path)
            )

            self.processed_content = ""

            for zone_idx, (zone_name, params, data, tau_idx) in enumerate(zones):
                block_means = self.calculate_means(data, nblk, bs)
                tau_values  = []
                t1max = float(params.get("T1MAX", 1.0))

                if tau_idx > 0 and tau_idx <= len(tau_formulas):
                    tau_formula = tau_formulas[tau_idx - 1]
                    match = re.match(
                        r"TAU\s*=\s*\[(log|lin):([\d\.]+)\*T1MAX:([\d\.]+)\*T1MAX:(\d+)\]",
                        tau_formula)
                    if match:
                        scale_type = match.group(1)
                        mult1      = float(match.group(2))
                        mult2      = float(match.group(3))
                        n_points   = int(match.group(4))
                        tau_values_micro = self.generate_tau_values(
                            scale_type, mult1 * t1max * 1e6,
                            mult2 * t1max * 1e6, n_points)
                        tau_values = (tau_values_micro / 1e6).tolist()

                zone_content = []
                if "dum" in params:
                    try:
                        dum_value = round(float(params["dum"]) * 1e6)
                        zone_content.append(f"# DATA dum = {dum_value} \n")
                    except ValueError:
                        zone_content.append(f"# DATA dum = {params['dum']} \n")
                else:
                    zone_content.append("# DATA\n")

                zone_content.append(f"#  TAG = Zone{zone_idx + 1}\n")
                zone_content.append(f"# T1MAX = {t1max}\n")
                if tau_idx > 0 and tau_idx <= len(tau_formulas):
                    zone_content.append(f"# {tau_formulas[tau_idx - 1]}\n")

                for i in range(len(block_means)):
                    row = [
                        f"{tau_values[i]:<15.6f}" if (tau_values and i < len(tau_values))
                        else "N/A".ljust(15),
                        f"{block_means[i]:<15.6f}",
                        "1"
                    ]
                    zone_content.append(" ".join(row) + "\n")

                if zone_idx < len(zones) - 1:
                    zone_content.append("\n")

                # render with tags
                self._data_view.insert(zone_content[0], "data_line")
                self._data_view.insert(zone_content[1], "tag_line")
                for ln in zone_content[2:]:
                    if ln.startswith("#"):
                        self._data_view.insert(ln, "comment")
                    elif ln.strip() == "":
                        self._data_view.insert(ln)
                    else:
                        self._data_view.insert(ln, "value")

                self.processed_content += "".join(zone_content)

            elapsed = time.time() - t0
            self._status.set(
                f"Processed {len(zones)} zones  ·  NBLK={nblk}  BS={bs}",
                "ok",
                right=f"{elapsed:.2f}s"
            )

        except Exception as e:
            self._data_view.insert(f"ERROR: {e}\n", "error")
            self.processed_content = ""
            self._status.set(f"Error: {e}", "error")

    # ── ORIGINAL LOGIC  (unchanged) ─────────────────────────────────
    def generate_tau_values(self, scale_type, start, stop, num_points):
        if scale_type == "log":
            return np.logspace(np.log10(start), np.log10(stop), num=num_points)
        elif scale_type == "lin":
            return np.linspace(start, stop, num=num_points)
        else:
            raise ValueError(f"Unknown scale type: {scale_type}")

    def calculate_means(self, data_lines, nblk, bs):
        block_means = []
        for i in range(nblk):
            start_idx = i * bs
            end_idx   = min((i + 1) * bs, len(data_lines))

            if self.row_range:
                rs, re = self.row_range
                block_start = start_idx + rs
                block_end   = min(start_idx + re + 1, end_idx)
                if block_start >= end_idx:
                    block_data = []
                else:
                    block_lines = data_lines[block_start:block_end]
                    block_data  = [float(l.split()[2])
                                   for l in block_lines if len(l.split()) >= 3]
            else:
                block_lines = data_lines[start_idx:end_idx]
                block_data  = [float(l.split()[2])
                               for l in block_lines if len(l.split()) >= 3]

            block_means.append(np.mean(block_data) if block_data else 0.0)
        return block_means


# ═══════════════════════════════════════════════════════════════════
#  TAB 2  —  FFC-IST DATA PROCESSOR
# ═══════════════════════════════════════════════════════════════════

def format_data_dum_sci_hz(freq_khz: float) -> str:
    hz = freq_khz * 1000.0
    if hz <= 0:
        return "0e3"
    exp  = int(math.floor(math.log10(hz)))
    mant = hz / (10 ** exp)
    while exp > 6:
        mant *= 10.0;  exp -= 1
    while exp < 3:
        mant /= 10.0;  exp += 1
    return f"{mant:.4g}e{exp}"


def format_tag_label(freq_khz: float) -> str:
    if freq_khz >= 1000.0:
        return f"{freq_khz / 1000:.4g}MHz"
    return f"{freq_khz:.4g}KHz"


def _fmt_g(x: float) -> str:
    return f"{x:.6g}"


class NMRDataProcessorTab(tk.Frame):

    def __init__(self, parent):
        super().__init__(parent, bg=C["panel"])
        self.extracted_sample_name = "Unknown"
        self.extracted_temperature = "Unknown"
        self._output_path = ""
        self._build()

    # ── BUILD UI ────────────────────────────────────────────────────
    def _build(self):
        # ── input file ──
        section_label(self, "INPUT FILE")
        in_card = card_frame(self)
        in_card.pack(fill="x", padx=12, pady=4)

        self._in_var = tk.StringVar()
        tk.Entry(in_card, textvariable=self._in_var,
                 bg=C["entry_bg"], fg=C["data_fg"],
                 insertbackground=C["accent"],
                 relief="flat", font=FONT_MONO_S,
                 state="readonly", width=58,
                 highlightthickness=1,
                 highlightbackground=C["border"],
                 highlightcolor=C["accent"]
                 ).pack(side="left", padx=10, pady=8, fill="x", expand=True)
        styled_button(in_card, "Browse…",
                      self.browse_input_file,
                      kind="action").pack(side="left", padx=8, pady=8)

        # ── output file ──
        section_label(self, "OUTPUT FILE")
        out_card = card_frame(self)
        out_card.pack(fill="x", padx=12, pady=4)

        self._out_var = tk.StringVar(value="processed_nmr_data.txt")
        tk.Entry(out_card, textvariable=self._out_var,
                 bg=C["entry_bg"], fg=C["data_fg"],
                 insertbackground=C["accent"],
                 relief="flat", font=FONT_MONO_S, width=58,
                 highlightthickness=1,
                 highlightbackground=C["border"],
                 highlightcolor=C["accent"]
                 ).pack(side="left", padx=10, pady=8, fill="x", expand=True)
        styled_button(out_card, "Browse…",
                      self.browse_output_file).pack(side="left", padx=8, pady=8)

        # ── metadata strip ──
        section_label(self, "DETECTED METADATA")
        meta_card = card_frame(self)
        meta_card.pack(fill="x", padx=12, pady=4)

        self._meta_sample = tk.Label(meta_card, text="Sample: —",
                                      bg=C["card"], fg=C["muted"], font=FONT_LABEL)
        self._meta_sample.pack(side="left", padx=14, pady=6)
        tk.Frame(meta_card, bg=C["border"], width=1
                 ).pack(side="left", fill="y", pady=4)
        self._meta_temp = tk.Label(meta_card, text="Temperature: —",
                                    bg=C["card"], fg=C["muted"], font=FONT_LABEL)
        self._meta_temp.pack(side="left", padx=14, pady=6)
        tk.Frame(meta_card, bg=C["border"], width=1
                 ).pack(side="left", fill="y", pady=4)
        self._meta_freq = tk.Label(meta_card, text="Frequencies: —",
                                    bg=C["card"], fg=C["muted"], font=FONT_LABEL)
        self._meta_freq.pack(side="left", padx=14, pady=6)

        # ── actions ──
        section_label(self, "ACTIONS")
        act_card = card_frame(self)
        act_card.pack(fill="x", padx=12, pady=4)

        styled_button(act_card, "⟳  Process Data",
                      self.process_data, kind="action").pack(side="left", padx=8, pady=8)
        styled_button(act_card, "📂  Open Output Folder",
                      self.download_file).pack(side="left", padx=4, pady=8)
        styled_button(act_card, "✕  Clear",
                      self._clear).pack(side="left", padx=4, pady=8)

        # progress bar
        self._progress = ttk.Progressbar(self, mode="indeterminate", length=200)
        style = ttk.Style()
        style.theme_use("default")
        style.configure("dark.Horizontal.TProgressbar",
                        troughcolor=C["card"], background=C["accent"],
                        bordercolor=C["border"], lightcolor=C["accent"],
                        darkcolor=C["accent2"])
        self._progress.configure(style="dark.Horizontal.TProgressbar")
        self._progress.pack(fill="x", padx=12, pady=(2, 0))

        separator(self)

        # ── results ──
        section_label(self, "PROCESSING RESULTS")
        self._data_view = DataText(self)
        self._data_view.pack(fill="both", expand=True, padx=12, pady=(0, 6))

        # status
        self._status = StatusBar(self)
        self._status.pack(fill="x", side="bottom")

    def _clear(self):
        self._data_view.clear()
        self._in_var.set("")
        self._meta_sample.config(text="Sample: —")
        self._meta_temp.config(text="Temperature: —")
        self._meta_freq.config(text="Frequencies: —")
        self._status.set("Cleared.", "info")

    # ── BROWSE ──────────────────────────────────────────────────────
    def browse_input_file(self):
        fn = filedialog.askopenfilename(
            title="Select NMR Data File",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if fn:
            self._in_var.set(fn)

    def browse_output_file(self):
        fn = filedialog.asksaveasfilename(
            title="Save Processed Data As",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if fn:
            self._out_var.set(fn)

    # ── PROCESS DATA  (original logic unchanged) ────────────────────
    def process_data(self):
        if not self._in_var.get():
            messagebox.showerror("Error", "Select an input file.")
            return
        if not self._out_var.get():
            messagebox.showerror("Error", "Specify an output file.")
            return

        self._progress.start(12)
        self._status.set("Processing…", "busy")
        self._data_view.clear()
        self.update_idletasks()
        t0 = time.time()

        try:
            with open(self._in_var.get(), "r", encoding="utf-8") as f:
                lines = f.read().splitlines()

            param_start  = None
            endtau_index = None
            for i, line in enumerate(lines):
                s = line.strip()
                if endtau_index is None and s.lower().startswith("endtau"):
                    endtau_index = i
                if param_start is None and s.startswith("Parameters"):
                    param_start = i
                if endtau_index is not None and param_start is not None:
                    break

            if endtau_index is not None:
                data_lines = lines[:endtau_index]
            elif param_start is not None:
                data_lines = lines[:param_start]
            else:
                data_lines = lines

            params = {}
            if param_start is not None:
                for i in range(param_start, len(lines)):
                    ln = lines[i].strip()
                    if "=" in ln and not ln.startswith("#"):
                        k, v = ln.split("=", 1)
                        params[k.strip()] = v.strip().strip('"')

            file_stem = os.path.splitext(
                os.path.basename(self._in_var.get()))[0]
            self.extracted_sample_name = params.get(
                "sampleName", file_stem if file_stem else "Unknown")

            first_temp = None
            for s in data_lines:
                s = s.strip()
                if not s or s.lower().startswith("endtau"):
                    continue
                parts = [p.strip() for p in s.split(",")]
                if parts:
                    try:
                        first_temp = float(parts[0])
                        break
                    except ValueError:
                        continue
            self.extracted_temperature = (
                "Unknown" if first_temp is None
                else (str(int(first_temp))
                      if float(first_temp).is_integer()
                      else str(first_temp)))

            freq_map = {}
            for s in data_lines:
                s = s.strip()
                if not s:
                    continue
                parts = [p.strip() for p in s.split(",")]
                if len(parts) >= 6:
                    try:
                        freq_khz = float(parts[1])
                        freq_map.setdefault(freq_khz, []).append(parts)
                    except ValueError:
                        continue

            # update metadata strip
            self._meta_sample.config(
                text=f"Sample: {self.extracted_sample_name}",
                fg=C["accent"])
            self._meta_temp.config(
                text=f"Temperature: {self.extracted_temperature} °C",
                fg=C["accent"])
            self._meta_freq.config(
                text=f"Frequencies: {len(freq_map)}",
                fg=C["accent"])

            out_lines = []
            for freq_khz in sorted(freq_map.keys()):
                dum       = format_data_dum_sci_hz(freq_khz)
                tag_label = format_tag_label(freq_khz)

                out_lines.append(f"# DATA dum={dum}")
                out_lines.append(
                    f"# TAG = {self.extracted_sample_name}"
                    f"_Temp = {self.extracted_temperature}C_{tag_label}_1")

                for parts in freq_map[freq_khz]:
                    try:
                        time_us = float(parts[2])
                    except Exception:
                        continue
                    time_sec = time_us * 1e-6
                    try:
                        val     = float(parts[3])
                        val_str = _fmt_g(val)
                    except Exception:
                        val_str = parts[3]
                    out_lines.append(
                        f"{_fmt_g(time_sec):>12}  {val_str:>12}  {1:>12}")

                out_lines.append("")

            full_text = "\n".join(out_lines) + "\n"

            # render coloured output
            for ln in full_text.splitlines():
                if ln.startswith("# DATA"):
                    self._data_view.insert(ln + "\n", "data_line")
                elif ln.startswith("# TAG") or ln.startswith("#  TAG"):
                    self._data_view.insert(ln + "\n", "tag_line")
                elif ln.startswith("#"):
                    self._data_view.insert(ln + "\n", "comment")
                elif ln.strip() == "":
                    self._data_view.insert("\n")
                else:
                    self._data_view.insert(ln + "\n", "value")

            with open(self._out_var.get(), "w", encoding="utf-8") as f:
                f.write(full_text)

            self._output_path = self._out_var.get()
            elapsed = time.time() - t0
            self._status.set(
                f"Processed {len(freq_map)} frequencies  ·  "
                f"Sample: {self.extracted_sample_name}",
                "ok",
                right=f"{elapsed:.2f}s"
            )
            messagebox.showinfo(
                "Success",
                f"Processed {len(freq_map)} frequencies.\n"
                f"Sample : {self.extracted_sample_name}\n"
                f"Temp   : {self.extracted_temperature} °C\n"
                f"Saved  : {self._out_var.get()}"
            )

        except Exception as e:
            self._status.set(f"Error: {e}", "error")
            messagebox.showerror("Processing Error", str(e))
        finally:
            self._progress.stop()

    # ── OPEN FOLDER  (original logic) ───────────────────────────────
    def download_file(self):
        fp = self._out_var.get()
        if not fp or not os.path.exists(fp):
            messagebox.showinfo("Not Found", "No output file yet.")
            return
        try:
            folder = os.path.dirname(fp)
            if os.name == "nt":
                os.startfile(folder)
            elif os.name == "posix":
                import subprocess
                subprocess.call(["open" if "darwin" in __import__("sys").platform
                                 else "xdg-open", folder])
            self._status.set("Output folder opened.", "ok")
        except Exception:
            messagebox.showinfo("Saved", f"File is at:\n{fp}")


# ═══════════════════════════════════════════════════════════════════
#  HEADER BANNER  (top of the window)
# ═══════════════════════════════════════════════════════════════════
class HeaderBanner(tk.Frame):
    def __init__(self, parent, **kw):
        super().__init__(parent, bg=C["header_bg"], pady=0, **kw)

        # left accent bar
        tk.Frame(self, bg=C["accent"], width=4).pack(side="left", fill="y")

        left = tk.Frame(self, bg=C["header_bg"])
        left.pack(side="left", padx=16, pady=10)

        tk.Label(left, text="NMR LAB SUITE",
                 bg=C["header_bg"], fg=C["text"],
                 font=("Consolas", 16, "bold")).pack(anchor="w")
        tk.Label(left, text="SDF Processor  ·  FFC-IST Data Processor",
                 bg=C["header_bg"], fg=C["muted"],
                 font=("Segoe UI", 9)).pack(anchor="w")

        # right: version badge
        right = tk.Frame(self, bg=C["header_bg"])
        right.pack(side="right", padx=16)
        badge = tk.Frame(right, bg=C["accent2"], padx=8, pady=3)
        badge.pack()
        tk.Label(badge, text="v2.0  PROFESSIONAL",
                 bg=C["accent2"], fg="white",
                 font=("Consolas", 8, "bold")).pack()


# ═══════════════════════════════════════════════════════════════════
#  CUSTOM NOTEBOOK  (styled tab strip)
# ═══════════════════════════════════════════════════════════════════
class StyledNotebook(tk.Frame):
    """Hand-drawn tab strip + content area (no ttk.Notebook)."""

    def __init__(self, parent, **kw):
        super().__init__(parent, bg=C["bg"], **kw)
        self._tabs      = []   # list of (button, frame)
        self._active    = -1

        self._tab_bar = tk.Frame(self, bg=C["header_bg"], pady=0)
        self._tab_bar.pack(fill="x")

        tk.Frame(self._tab_bar, bg=C["border"], height=1
                 ).pack(side="bottom", fill="x")

        self._content = tk.Frame(self, bg=C["panel"])
        self._content.pack(fill="both", expand=True)

    def add(self, frame, label: str):
        idx = len(self._tabs)
        btn = tk.Button(
            self._tab_bar, text=label,
            bg=C["header_bg"], fg=C["muted"],
            activebackground=C["panel"],
            activeforeground=C["text"],
            font=FONT_BOLD, relief="flat",
            bd=0, padx=22, pady=10,
            cursor="hand2",
            command=lambda i=idx: self.select(i)
        )
        btn.pack(side="left")

        frame.place(in_=self._content, x=0, y=0, relwidth=1, relheight=1)
        self._tabs.append((btn, frame))

        if idx == 0:
            self.select(0)

    def select(self, idx: int):
        for i, (btn, frm) in enumerate(self._tabs):
            if i == idx:
                btn.config(bg=C["panel"], fg=C["accent"],
                           font=("Segoe UI", 9, "bold"))
                # accent underline
                btn.config(relief="flat", bd=0,
                           highlightthickness=2,
                           highlightbackground=C["accent"],
                           highlightcolor=C["accent"])
                frm.lift()
            else:
                btn.config(bg=C["header_bg"], fg=C["muted"],
                           font=FONT_BOLD,
                           highlightthickness=0)
        self._active = idx


# ═══════════════════════════════════════════════════════════════════
#  MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════
def main():
    root = tk.Tk()
    root.title("NMR Lab Filter — Professional")
    root.geometry("1160x780")
    root.minsize(960, 620)
    root.configure(bg=C["bg"])

    # ── header ──
    HeaderBanner(root).pack(fill="x")

    # thin separator
    tk.Frame(root, bg=C["accent"], height=2).pack(fill="x")

    # ── notebook ──
    nb = StyledNotebook(root)
    nb.pack(fill="both", expand=True)

    sdf_tab = SDFProcessorTab(nb)
    nmr_tab = NMRDataProcessorTab(nb)

    nb.add(sdf_tab, "  📐  SDF Processor  ")
    nb.add(nmr_tab, "  📊  FFC-IST Data Processor  ")

    # ── keyboard shortcuts ──
    root.bind("<Control-o>", lambda _: sdf_tab.load_file())
    root.bind("<Control-s>", lambda _: sdf_tab.save_file())
    root.bind("<Control-n>", lambda _: sdf_tab.normalize_output())
    root.bind("<F5>",        lambda _: sdf_tab._process_current())

    root.mainloop()


if __name__ == "__main__":
    main()
