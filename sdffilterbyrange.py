# Import necessary modules
import tkinter as tk  # For GUI
from tkinter import filedialog, messagebox  # For file dialog boxes and pop-up messages
import numpy as np  # For numeric operations like mean, logspace, linspace
import re  # For regular expressions (pattern matching)

# Define the main GUI application class
class SDFProcessorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("SDF File Processor")
        self.root.geometry("1000x600")

        # Create a frame to hold the buttons
        button_frame = tk.Frame(root)
        button_frame.pack(pady=10)

        # Button to load a file
        self.load_button = tk.Button(button_frame, text="Load SDF File", command=self.load_file)
        self.load_button.pack(side=tk.LEFT, padx=5)

        # Button to save output, disabled until a file is loaded
        self.save_button = tk.Button(button_frame, text="Save Output", command=self.save_file, state=tk.DISABLED)
        self.save_button.pack(side=tk.LEFT, padx=5)

        # Button to normalize output
        self.normalize_button = tk.Button(button_frame, text="Normalize", command=self.normalize_output, state=tk.DISABLED)
        self.normalize_button.pack(side=tk.LEFT, padx=5)

        # Row range input field
        tk.Label(button_frame, text="Set Row Range (e.g. 0:349):").pack(side=tk.LEFT, padx=5)
        self.range_entry = tk.Entry(button_frame, width=10)
        self.range_entry.pack(side=tk.LEFT, padx=5)

        # Checkbox to enable debug mode
        self.debug_var = tk.IntVar()
        self.debug_check = tk.Checkbutton(root, text="Show Debug Info", variable=self.debug_var)
        self.debug_check.pack()

        # Text box to show the output
        self.output_text = tk.Text(root, wrap=tk.WORD, width=120, height=30)
        self.output_text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # Configure text colors and styles for tags
        self.output_text.tag_config("tag", foreground="green", font=('Arial', 10, 'bold'))
        self.output_text.tag_config("data", foreground="blue", font=('Arial', 10, 'bold'))
        self.output_text.tag_config("warning", foreground="orange")
        self.output_text.tag_config("error", foreground="red")

        # To hold processed file content
        self.processed_content = ""
        self.row_range = None  # User-defined range like 0:349

    # Function to load a file
    def load_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("SDF files", "*.sdf"), ("All files", "*.*")])
        if file_path:
            self.output_text.delete(1.0, tk.END)
            self.process_file(file_path)
            self.save_button.config(state=tk.NORMAL)
            self.normalize_button.config(state=tk.NORMAL)

    # Function to save processed content to file
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

    # Function to normalize the data
    def normalize_output(self):
        try:
            lines = self.processed_content.splitlines()
            normalized_lines = []
            current_zone = []
            inside_zone = False

            # Helper function to normalize each zone
            def normalize_zone(zone_lines):
                data_lines = []
                for line in zone_lines:
                    if line.startswith("#") or "N/A" in line:
                        continue
                    parts = line.split()
                    if len(parts) >= 2:
                        try:
                            data_lines.append(float(parts[1]))  # Y-values for normalization
                        except ValueError:
                            continue

                if not data_lines:
                    return zone_lines  # No data to normalize

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
                                parts[1] = f"{norm_values[norm_index]:<15.6f}"  # Replace Y-value
                                norm_index += 1
                                norm_zone.append(" ".join(parts))
                            except ValueError:
                                norm_zone.append(line)
                        else:
                            norm_zone.append(line)

                return norm_zone

            # Main normalization loop
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

            # Display and store normalized content
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

    # Process the SDF file
    def process_file(self, file_path):
        try:
            with open(file_path, "r") as file:
                lines = file.readlines()

            # Handle row range input
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

            # Variables to store data while parsing
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

            for line in lines:
                line = line.strip()
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

                # Extract parameters
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

            # Build final content zone by zone
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

                # Insert zone into GUI and store in memory
                self.output_text.insert(tk.END, zone_content[0], "data")
                self.output_text.insert(tk.END, zone_content[1], "tag")
                for line in zone_content[2:]:
                    self.output_text.insert(tk.END, line)

                self.processed_content += "".join(zone_content)

        except Exception as e:
            self.output_text.insert(tk.END, f"ERROR: {str(e)}\n", "error")
            self.processed_content = ""

    # Generate tau values based on scale type
    def generate_tau_values(self, scale_type, start, stop, num_points):
        if scale_type == "log":
            return np.logspace(np.log10(start), np.log10(stop), num=num_points)
        elif scale_type == "lin":
            return np.linspace(start, stop, num=num_points)
        else:
            raise ValueError(f"Unknown scale type: {scale_type}")

    # Calculate average for each block of data
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

# Run the GUI app
if __name__ == "__main__":
    root = tk.Tk()
    app = SDFProcessorGUI(root)
    root.mainloop()
