#!/usr/bin/env python3
# combined_nmr_sdf_app.py
# Combined Tkinter app: Tab 1 = SDF Processor, Tab 2 = NMR Data Processor
# Both original tools preserved but refactored into frames that auto-fit.

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import numpy as np
import re
import os
import math

# -------------------------
# SDF Processor (adapted)
# -------------------------
class SDFProcessorFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        # UI (adapted from original SDFProcessorGUI)
        button_frame = ttk.Frame(self)
        button_frame.pack(pady=6, fill='x', padx=6)

        self.load_button = ttk.Button(button_frame, text="Load SDF File", command=self.load_file)
        self.load_button.pack(side=tk.LEFT, padx=4)

        self.save_button = ttk.Button(button_frame, text="Save Output", command=self.save_file, state=tk.DISABLED)
        self.save_button.pack(side=tk.LEFT, padx=4)

        self.normalize_button = ttk.Button(button_frame, text="Normalize", command=self.normalize_output, state=tk.DISABLED)
        self.normalize_button.pack(side=tk.LEFT, padx=4)

        ttk.Label(button_frame, text="Set Row Range (e.g. 0:349):").pack(side=tk.LEFT, padx=6)
        self.range_entry = ttk.Entry(button_frame, width=12)
        self.range_entry.pack(side=tk.LEFT, padx=4)

        self.debug_var = tk.IntVar()
        self.debug_check = ttk.Checkbutton(button_frame, text="Show Debug Info", variable=self.debug_var)
        self.debug_check.pack(side=tk.LEFT, padx=6)

        # Text widget for output (use ScrolledText inside a frame so it expands)
        text_frame = ttk.Frame(self)
        text_frame.pack(fill='both', expand=True, padx=6, pady=(0,6))
        self.output_text = scrolledtext.ScrolledText(text_frame, wrap=tk.WORD)
        self.output_text.pack(fill='both', expand=True)

        # Tag configuration (uses Text widget's tag_configure)
        self.output_text.tag_config("tag", foreground="green", font=('Arial', 10, 'bold'))
        self.output_text.tag_config("data", foreground="blue", font=('Arial', 10, 'bold'))
        self.output_text.tag_config("warning", foreground="orange")
        self.output_text.tag_config("error", foreground="red")

        # internal state
        self.processed_content = ""
        self.row_range = None

    # ---------- SDF functions (kept logic) ----------
    def load_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("SDF files", "*.sdf"), ("All files", "*.*")])
        if file_path:
            self.output_text.delete(1.0, tk.END)
            self.process_file(file_path)
            self.save_button.config(state=tk.NORMAL)
            self.normalize_button.config(state=tk.NORMAL)

    def save_file(self):
        if not self.processed_content:
            messagebox.showwarning("Warning", "No content to save")
            return
        file_path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text files", "*.txt")])
        if file_path:
            try:
                with open(file_path, 'w') as file:
                    file.write(self.processed_content)
                messagebox.showinfo("Success", "File saved successfully")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file: {str(e)}")

    def normalize_output(self):
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

                min_val = min(data_lines)
                max_val = max(data_lines)
                range_val = max_val - min_val if max_val != min_val else 1
                norm_values = [(val - min_val) / range_val for val in data_lines]

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

            # Display normalized content
            self.output_text.delete(1.0, tk.END)
            for line in normalized_lines:
                if line.startswith("# DATA"):
                    self.output_text.insert(tk.END, line + "\n", "data")
                elif line.startswith("#  TAG"):
                    self.output_text.insert(tk.END, line + "\n", "tag")
                else:
                    self.output_text.insert(tk.END, line + "\n")

            self.processed_content = "\n".join(normalized_lines)

        except Exception as e:
            self.output_text.insert(tk.END, f"ERROR in normalization: {str(e)}\n", "error")

    def process_file(self, file_path):
        try:
            with open(file_path, "r") as file:
                lines = file.readlines()

            range_str = self.range_entry.get().strip()
            if range_str:
                try:
                    start, end = map(int, range_str.split(":"))
                    if start >= 0 and end >= start:
                        self.row_range = (start, end)
                    else:
                        raise ValueError()
                except Exception:
                    self.output_text.insert(tk.END, f"Invalid row range format: '{range_str}'. Ignoring range.\n", "warning")
                    self.row_range = None
            else:
                self.row_range = None

            zones = []
            current_zone = None
            data_lines = []
            zone_params = {}
            global_params = {}
            tau_formulas = []
            current_tau_index = 0
            in_parameter_summary = False
            in_data_section = False
            current_zone_has_data = False

            for raw in lines:
                line = raw.strip()
                if "PARAMETER SUMMARY" in line:
                    if current_zone and current_zone_has_data:
                        zones.append((current_zone, zone_params.copy(), data_lines, current_tau_index))
                    current_zone = None
                    zone_params = {}
                    data_lines = []
                    current_zone_has_data = False
                    in_parameter_summary = True
                    in_data_section = False
                    continue
                elif line.startswith("ZONE"):
                    if current_zone and current_zone_has_data and not in_parameter_summary:
                        zones.append((current_zone, zone_params.copy(), data_lines, current_tau_index))
                    in_parameter_summary = False
                    in_data_section = False
                    current_zone = line
                    zone_params = {}
                    data_lines = []
                    current_zone_has_data = False
                    continue

                if "=" in line:
                    parts = [p.strip() for p in line.split("=", 1)]
                    if len(parts) == 2:
                        param_name, param_value = parts
                        if in_parameter_summary:
                            if param_name in ["NBLK", "BS"]:
                                global_params[param_name] = param_value
                            elif param_name == "TAU":
                                tau_formulas.append(line)
                        elif current_zone:
                            if param_name == "T1MAX":
                                try:
                                    zone_params[param_name] = str(float(param_value) / 1000000)
                                except ValueError:
                                    zone_params[param_name] = param_value
                            elif param_name == "BR":
                                zone_params["dum"] = param_value
                            else:
                                zone_params[param_name] = param_value

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
                zones.append((current_zone, zone_params.copy(), data_lines, current_tau_index))

            if "NBLK" not in global_params or "BS" not in global_params:
                raise ValueError("NBLK or BS parameters not found in any PARAMETER SUMMARY")

            nblk = int(global_params["NBLK"])
            bs = int(float(global_params["BS"]))

            self.processed_content = ""

            for zone_idx, (zone_name, params, data, tau_idx) in enumerate(zones):
                block_means = self.calculate_means(data, nblk, bs)
                tau_values = []
                t1max = float(params.get("T1MAX", 1.0))

                if tau_idx > 0 and tau_idx <= len(tau_formulas):
                    tau_formula = tau_formulas[tau_idx - 1]
                    match = re.match(r"TAU\s*=\s*\[(log|lin):([\d\.]+)\*T1MAX:([\d\.]+)\*T1MAX:(\d+)\]", tau_formula)
                    if match:
                        scale_type = match.group(1)
                        mult1 = float(match.group(2))
                        mult2 = float(match.group(3))
                        n_points = int(match.group(4))
                        tau_values_micro = self.generate_tau_values(scale_type, mult1 * t1max * 1e6, mult2 * t1max * 1e6, n_points)
                        tau_values = (tau_values_micro / 1e6).tolist()

                zone_content = []

                if "dum" in params:
                    try:
                        dum_value = round(float(params['dum']) * 1e6)
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
                        f"{tau_values[i]:<15.6f}" if tau_values and i < len(tau_values) else "N/A".ljust(15),
                        f"{block_means[i]:<15.6f}",
                        "1"
                    ]
                    zone_content.append(" ".join(row) + "\n")

                if zone_idx < len(zones) - 1:
                    zone_content.append("\n")

                # Insert into GUI and store
                self.output_text.insert(tk.END, zone_content[0], "data")
                self.output_text.insert(tk.END, zone_content[1], "tag")
                for line in zone_content[2:]:
                    self.output_text.insert(tk.END, line)

                self.processed_content += "".join(zone_content)

        except Exception as e:
            self.output_text.insert(tk.END, f"ERROR: {str(e)}\n", "error")
            self.processed_content = ""

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
            end_idx = min((i + 1) * bs, len(data_lines))

            if self.row_range:
                range_start, range_end = self.row_range
                block_start = start_idx + range_start
                block_end = min(start_idx + range_end + 1, end_idx)
                if block_start >= end_idx:
                    block_data = []
                else:
                    block_lines = data_lines[block_start:block_end]
                    block_data = [float(line.split()[2]) for line in block_lines if len(line.split()) >= 3]
            else:
                block_lines = data_lines[start_idx:end_idx]
                block_data = [float(line.split()[2]) for line in block_lines if len(line.split()) >= 3]

            block_means.append(np.mean(block_data) if block_data else 0.0)

        return block_means

# -------------------------
# NMR Data Processor (adapted)
# -------------------------
def format_data_dum_sci_hz(freq_khz: float) -> str:
    hz = freq_khz * 1000.0
    if hz <= 0:
        return "0e3"
    exp = int(math.floor(math.log10(hz)))
    mant = hz / (10 ** exp)
    while exp > 6:
        mant *= 10.0
        exp -= 1
    while exp < 3:
        mant /= 10.0
        exp += 1
    mant_str = f"{mant:.4g}"
    return f"{mant_str}e{exp}"

def format_tag_label(freq_khz: float) -> str:
    if freq_khz >= 1000.0:
        mhz = freq_khz / 1000.0
        s = f"{mhz:.4g}"
        return f"{s}MHz"
    else:
        s = f"{freq_khz:.4g}"
        return f"{s}KHz"

def _fmt_g(x: float) -> str:
    return f"{x:.6g}"

class NMRDataProcessorFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)

        # Variables
        self.input_file_path = tk.StringVar()
        self.output_file_path = tk.StringVar(value="processed_nmr_data.txt")
        self.extracted_sample_name = "Unknown"
        self.extracted_temperature = "Unknown"

        # Layout
        main_frame = ttk.Frame(self)
        main_frame.pack(fill='both', expand=True, padx=6, pady=6)

        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(6, weight=1)

        ttk.Label(main_frame, text="FFC-IST Data Processor", font=("Arial", 14, "bold")).grid(row=0, column=0, columnspan=3, pady=(0, 10))

        ttk.Label(main_frame, text="Input File:").grid(row=1, column=0, sticky=tk.W, pady=4)
        ttk.Entry(main_frame, textvariable=self.input_file_path, width=60).grid(row=1, column=1, sticky=(tk.W, tk.E), pady=4, padx=(5,5))
        ttk.Button(main_frame, text="Browse", command=self.browse_input_file).grid(row=1, column=2, pady=4)

        ttk.Label(main_frame, text="Output File:").grid(row=2, column=0, sticky=tk.W, pady=4)
        ttk.Entry(main_frame, textvariable=self.output_file_path, width=60).grid(row=2, column=1, sticky=(tk.W, tk.E), pady=4, padx=(5,5))
        ttk.Button(main_frame, text="Browse", command=self.browse_output_file).grid(row=2, column=2, pady=4)

        ttk.Button(main_frame, text="Process Data", command=self.process_data).grid(row=3, column=0, columnspan=3, pady=10)

        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=4)

        ttk.Label(main_frame, text="Processing Results:").grid(row=5, column=0, sticky=tk.W, pady=(8,4))

        self.results_text = scrolledtext.ScrolledText(main_frame, width=100, height=20, wrap=tk.NONE)
        self.results_text.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=4)
        xscroll = ttk.Scrollbar(main_frame, orient="horizontal", command=self.results_text.xview)
        xscroll.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E))
        self.results_text.configure(xscrollcommand=xscroll.set)

        self.download_btn = ttk.Button(main_frame, text="Download Processed File", command=self.download_file, state=tk.DISABLED)
        self.download_btn.grid(row=8, column=0, columnspan=3, pady=8)

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN).grid(row=9, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(6,0))

    # ---------- NMR functions (kept logic) ----------
    def browse_input_file(self):
        filename = filedialog.askopenfilename(title="Select NMR Data File",
                                              filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if filename:
            self.input_file_path.set(filename)

    def browse_output_file(self):
        filename = filedialog.asksaveasfilename(title="Save Processed Data As",
                                                defaultextension=".txt",
                                                filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if filename:
            self.output_file_path.set(filename)

    def process_data(self):
        if not self.input_file_path.get():
            messagebox.showerror("Error", "Please select an input file")
            return
        if not self.output_file_path.get():
            messagebox.showerror("Error", "Please specify an output file")
            return

        self.progress.start()
        self.status_var.set("Processing data...")
        self.download_btn.config(state=tk.DISABLED)
        self.results_text.configure(state="normal")
        self.results_text.delete(1.0, tk.END)

        try:
            with open(self.input_file_path.get(), 'r', encoding='utf-8') as f:
                lines = f.read().splitlines()

            param_start = None
            endtau_index = None
            for i, line in enumerate(lines):
                s = line.strip()
                if endtau_index is None and s.lower().startswith('endtau'):
                    endtau_index = i
                if param_start is None and s.startswith('Parameters'):
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
                    line = lines[i].strip()
                    if '=' in line and not line.startswith('#'):
                        k, v = line.split('=', 1)
                        params[k.strip()] = v.strip().strip('"')

            file_stem = os.path.splitext(os.path.basename(self.input_file_path.get()))[0]
            self.extracted_sample_name = params.get('sampleName', file_stem if file_stem else 'Unknown')

            first_temp = None
            for s in data_lines:
                s = s.strip()
                if not s or s.lower().startswith('endtau'):
                    continue
                parts = [p.strip() for p in s.split(',')]
                if len(parts) >= 1:
                    try:
                        first_temp = float(parts[0])
                        break
                    except ValueError:
                        continue
            self.extracted_temperature = ("Unknown" if first_temp is None
                                          else (str(int(first_temp)) if float(first_temp).is_integer() else str(first_temp)))

            freq_map = {}
            for s in data_lines:
                s = s.strip()
                if not s:
                    continue
                parts = [p.strip() for p in s.split(',')]
                if len(parts) >= 6:
                    try:
                        freq_khz = float(parts[1])
                        freq_map.setdefault(freq_khz, []).append(parts)
                    except ValueError:
                        continue

            out_lines = []
            for freq_khz in sorted(freq_map.keys()):
                dum = format_data_dum_sci_hz(freq_khz)
                tag_label = format_tag_label(freq_khz)

                out_lines.append(f"# DATA dum={dum}")
                out_lines.append(f"# TAG = {self.extracted_sample_name}_Temp = {self.extracted_temperature}C_{tag_label}_1")

                for parts in freq_map[freq_khz]:
                    try:
                        time_us = float(parts[2])
                    except Exception:
                        continue
                    time_sec = time_us * 1e-6

                    try:
                        val = float(parts[3])
                        val_str = _fmt_g(val)
                    except Exception:
                        val_str = parts[3]

                    line = f"{_fmt_g(time_sec):>12}  {val_str:>12}  {1:>12}"
                    out_lines.append(line)

                out_lines.append("")

            full_output_text = "\n".join(out_lines) + "\n"
            self.results_text.insert(tk.END, full_output_text)
            self.results_text.see(tk.END)
            self.results_text.update_idletasks()

            with open(self.output_file_path.get(), 'w', encoding='utf-8') as f:
                f.write(full_output_text)

            self.download_btn.config(state=tk.NORMAL)
            self.status_var.set(f"Successfully processed {len(freq_map)} frequencies")
            messagebox.showinfo("Success", f"Data processed successfully!\nProcessed {len(freq_map)} different frequencies.")

        except Exception as e:
            self.status_var.set("Error processing data")
            messagebox.showerror("Error", f"Failed to process data:\n{str(e)}")
        finally:
            self.progress.stop()

    def download_file(self):
        output_file = self.output_file_path.get()
        if os.path.exists(output_file):
            try:
                if os.name == 'nt':
                    os.startfile(os.path.dirname(output_file))
                elif os.name == 'posix':
                    import subprocess
                    subprocess.call(['open', os.path.dirname(output_file)])
                else:
                    import subprocess
                    subprocess.call(['xdg-open', os.path.dirname(output_file)])
                self.status_var.set("File location opened")
            except Exception:
                messagebox.showinfo("File Saved", f"File saved to:\n{output_file}")
        else:
            messagebox.showerror("Error", "Processed file not found")

# -------------------------
# Main combined application
# -------------------------
def main():
    root = tk.Tk()
    root.title("Combined NMR & SDF Tools")
    # start window size moderate; user can resize
    root.geometry("1100x720")
    root.minsize(900, 500)

    notebook = ttk.Notebook(root)
    notebook.pack(fill='both', expand=True)

    # SDF tab
    sdf_tab = ttk.Frame(notebook)
    sdf_tab.pack(fill='both', expand=True)
    notebook.add(sdf_tab, text="SDF Processor")

    sdf_frame = SDFProcessorFrame(sdf_tab)
    sdf_frame.pack(fill='both', expand=True)

    # NMR tab
    nmr_tab = ttk.Frame(notebook)
    nmr_tab.pack(fill='both', expand=True)
    notebook.add(nmr_tab, text="FFC-IST Data Processor")

    nmr_frame = NMRDataProcessorFrame(nmr_tab)
    nmr_frame.pack(fill='both', expand=True)

    root.mainloop()

if __name__ == "__main__":
    main()
