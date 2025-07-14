#!/usr/bin/env python3
# Standard libraries
import os
import shutil
import threading
import zipfile
import json
import subprocess
import platform
import h5py
# Third-party libraries
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import requests
import re
import math
import subprocess
import tempfile
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP



# Default URLs
UNIVERSITY_URL = "http://192.92.147.107:8142/fit"

FUNCTIONS_JSON_PATH = "functions.json"
# Default functions
MONOEXP = r"Mz(t,Mi[0<1.5],M0[0<1.5],T11[0.0001<5])[-1.2<1.2]=Mi \+ (M0-Mi)*exp(-t/T11)"
BIEXP = r"Mz(t,Mi[0<1.5],M0[0<1.5],T11[0.0001<5],T12[0.0001<5],c[0.5<1])[-1.2<1.2]=Mi \+ c*(M0-Mi)*exp(-t/T11) \+(1-c)*(M0-Mi)*exp(-t/T12)"

# Confirm that JSON file with functions is generated if missing
if not os.path.exists(FUNCTIONS_JSON_PATH):
    default_functions = {
        "functions": {
            "Monoexponential": MONOEXP,
            "Biexponential": BIEXP
        },
        "urls": {
            "University URL": UNIVERSITY_URL
        }
    }
    with open(FUNCTIONS_JSON_PATH, "w") as json_file:
        json.dump(default_functions, json_file, indent=4)
# Function to load functions and URLs from JSON file
def load_functions_and_urls_from_json():
    with open(FUNCTIONS_JSON_PATH, "r") as json_file:
        data = json.load(json_file)
    return data["functions"], data["urls"]
# Load functions and URLs from JSON file
functions, urls = load_functions_and_urls_from_json()


def query(url, file_path, params, download_folder):
    try:
        # Upload the file
        with open(file_path, "rb") as file:
            files = {"file": file}
            response = requests.post(url, files=files, data=params)

        # Check for successful response
        if response.status_code != 200:
            raise Exception(f"File upload failed: {response.status_code}, {response.text}")

        # Validate the content type
        content_type = response.headers.get("Content-Type", "")
        if "application/zip" not in content_type and "application/octet-stream" not in content_type:
            raise Exception(f"The query to {url} did not return a ZIP file.")

        # Extract the ZIP file
        os.makedirs(download_folder, exist_ok=True)
        zip_file_path = os.path.join(download_folder, "downloaded.zip")
        with open(zip_file_path, 'wb') as f:
            f.write(response.content)

        print(f"ZIP file downloaded to: {zip_file_path}")

        with zipfile.ZipFile(zip_file_path, 'r') as zip_file:
            zip_file.extractall(download_folder)

        print(f"ZIP extracted to: {download_folder}")

        # Delete the ZIP file after extraction
        os.remove(zip_file_path)  # Remove the ZIP file
        print(f"ZIP file {zip_file_path} deleted.")

        # Automatically show the fit results after extraction
        show_fit_result()

    except Exception as e:
        result_text.delete(1.0, tk.END)  # Clear any previous content
        result_text.insert(tk.END, f"Error: {e}\n")  # Display the error in result_text
        print(f"Error in query function: {e}")
        
def run_curl():
    def execute_curl():
        start_blinking()
        try:
            # Get user inputs
            symb_size = symb_size_entry.get()
            file_path = file_entry.get()
            function = function_entry.get("1.0", tk.END).strip()
            logx = logx_var.get()
            logy = logy_var.get()
            autox = autox_var.get()
            autoy = autoy_var.get()
            server_url = url_entry.get()
            download_folder = "downloaded"

            # Validate inputs
            if file_path:  # Only validate if a file is selected
                allowed_extensions = ['.hdf5', '.5hdf', '.json', '.sav', '.zip', '.dat', '.sdf']
                file_extension = os.path.splitext(file_path)[1].lower()
                if file_extension not in allowed_extensions:
                    stop_blinking()
                    result_text.delete(1.0, tk.END)
                    result_text.insert(tk.END, "Error: Please select a valid file (.hdf5, .json, .sav, .zip, .dat, .sdf).\n")
                    return
            if not server_url:
                stop_blinking()
                result_text.delete(1.0, tk.END)
                result_text.insert(tk.END, "Error: Server URL is required.\n")
                return

            # Prepare the request payload
            params = {
                "stelar-hdf5": "yes" if is_hdf5_file(file_path) else "no",
                "logx": logx,
                "logy": logy,
                "autox": autox,
                "autoy": autoy,
                "symbsize": symb_size,
                "download": "zip"
            }

            # Add function parameter only if the file is not JSON or SAV
            file_extension = os.path.splitext(file_path)[1].lower()
            if file_extension not in ['.json', '.sav']:
                if not function:
                    stop_blinking()
                    result_text.delete(1.0, tk.END)
                    result_text.insert(tk.END, "Error: Function definition is required for this file type.\n")
                    return
                params["function"] = function  # Add function parameter for non-JSON/SAV files

            # Call the query function
            query(server_url, file_path, params, download_folder)
        finally:
            stop_blinking()

    # Start the fit process in a separate thread to avoid blocking the UI
    threading.Thread(target=execute_curl, daemon=True).start()

def open_folder(download_folder):
    try:
        # Ensure the folder exists
        if not os.path.exists(download_folder):
            result_text.delete(1.0, tk.END)  # Clear previous content
            result_text.insert(tk.END, f"Error: The folder {download_folder} does not exist.\n")
            return

        # For Windows
        if platform.system() == 'Windows':
            os.startfile(download_folder)  # Open the folder

        # For macOS
        elif platform.system() == 'Darwin':
            subprocess.run(['open', download_folder])

        # For Linux
        elif platform.system() == 'Linux':
            subprocess.run(['xdg-open', download_folder])

        else:
            result_text.delete(1.0, tk.END)  # Clear previous content
            result_text.insert(tk.END, "Error: Unsupported OS for opening folders.\n")
    except Exception as e:
        result_text.delete(1.0, tk.END)  # Clear previous content
        result_text.insert(tk.END, f"Error: Failed to open the folder: {e}\n")

def open_downloaded_folder():
    download_folder = "downloaded"
    open_folder(download_folder)

def start_blinking():
    def blink():
        colors = ["black", "white"]  # Alternate between black and white
        index = 0
        while blinking:
            run_button.config(fg=colors[index])
            index = (index + 1) % len(colors)
            run_button.update()
            run_button.after(500)  # Half-second interval

    global blinking
    blinking = True
    threading.Thread(target=blink, daemon=True).start()

def stop_blinking():
    global blinking
    blinking = False
    run_button.config(fg="red")  # Reset to default color

# Ensure the blinking variable is defined
blinking = False

def show_pdf():
    download_folder = "downloaded"
    pdf_file = None

    # Recursively search for All.pdf in the download folder and its subdirectories
    for root, dirs, files in os.walk(download_folder):
        if "All.pdf" in files:
            pdf_file = os.path.join(root, "All.pdf")
            break

    # If found, open it with the default PDF viewer
    if pdf_file:
        try:
            if os.name == 'nt':  # For Windows
                os.startfile(pdf_file)  # Open the file
            elif os.name == 'posix':  # For Linux/macOS
                subprocess.run(['xdg-open', pdf_file])  # Open with default viewer
            else:
                result_text.delete(1.0, tk.END)  # Clear previous content
                result_text.insert(tk.END, "Error: Unsupported OS for opening PDF.\n")
        except Exception as e:
            result_text.delete(1.0, tk.END)  # Clear previous content
            result_text.insert(tk.END, f"Error: Failed to open the PDF: {e}\n")
    else:
        result_text.delete(1.0, tk.END)  # Clear previous content
        result_text.insert(tk.END, "Error: All.pdf not found in the downloaded folder.\n")

def browse_file():
    file_path = filedialog.askopenfilename(
        filetypes=[
            ("All files", "*.*"),
            ("HDF5 files", "*.hdf5"),
            ("JSON files", "*.json"),
            ("SAV files", "*.sav"),
            ("ZIP files", "*.zip"),
            ("DAT files", "*.dat"),
            ("SDF files", "*.sdf")
        ]
    )
    if file_path:
        file_entry.delete(0, tk.END)
        file_entry.insert(0, file_path)

def clean_fit_results(fit_results):
    # Replace '| ' with a tab to clean up the data for Excel pasting
    clean_results = fit_results.replace(" | ", "\t")  # Replacing with tab
    return clean_results

def show_fit_result():
    download_folder = "downloaded"
    json_file = None

    # Search for the first JSON file in the subfolders
    for root, dirs, files in os.walk(download_folder):
        for file in files:
            if file.endswith(".json"):  # Check for .json files
                json_file = os.path.join(root, file)  # Get the full path of the file
                break  # Stop after finding the first JSON file
        if json_file:
            break

    if json_file:
        try:
            # Open the found JSON file
            with open(json_file, 'r') as f:
                json_data = json.load(f)

            # Check for the presence of 'fit-results' in the JSON file
            fit_results = json_data.get('fit-results')
            if fit_results:
                # Clean the 'fit-results' string to remove '|' symbols and replace with tab
                cleaned_fit_results = clean_fit_results(fit_results)

                # Parse the cleaned 'fit-results' string (CSV-like data)
                rows = cleaned_fit_results.strip().split("\n")
                header = rows[0].split("\t")  # Split by tab
                data_rows = [row.split("\t") for row in rows[1:]]  # Split data by tab

                # Format the parsed data for display
                display_text = f"Headers:\n{'\t'.join(header)}\n\n"  # Join with tabs
                for row in data_rows:
                    display_text += f"{'\t'.join(row)}\n"  # Join each row with tabs

                # Display the formatted data in the result_text widget
                result_text.delete(1.0, tk.END)  # Clear any previous content
                result_text.insert(tk.END, display_text)
                # Save to a .dat file for Gnuplot
                with open("fit_results.dat", "w") as f:
                    f.write(cleaned_fit_results)
            else:
                # Debugging: Display all keys in the JSON
                all_keys = json_data.keys()
                messagebox.showinfo("Debug Info", f"'fit-results' key not found. Available keys: {list(all_keys)}")
        except Exception as e:
            messagebox.showerror("Error", f"Error reading or parsing the JSON file: {e}")
    else:
        messagebox.showerror("Error", "No JSON file found in the downloaded folder or its subfolders.")

def use_university_url():
    # Set the server URL to the university URL
    url_entry.delete(0, tk.END)
    url_entry.insert(0, UNIVERSITY_URL)

def insert_function(event):
    # Get the selected function name (key) from the dropdown
    selected_function = function_var.get()

    # Load the existing functions from the JSON file
    with open(FUNCTIONS_JSON_PATH, "r") as json_file:
        functions_data = json.load(json_file)

    # Get the full function definition (value) for the selected function
    if selected_function in functions_data["functions"]:
        function_value = functions_data["functions"][selected_function]
        # Update the function definition entry box with the value
        function_entry.delete(0, tk.END)
        function_entry.insert(tk.END, function_value)

def clean_folder():
    folder_to_remove = "downloaded"  # Always delete the "downloaded" folder

    # Clear previous content in the result_text widget
    result_text.delete(1.0, tk.END)
    
    # Remove the folder
    if os.path.exists(folder_to_remove):
        try:
            if os.path.isdir(folder_to_remove):
                shutil.rmtree(folder_to_remove)  # Remove the folder and its contents
                result_text.insert(tk.END, f"Folder {folder_to_remove} has been successfully removed.\n")
            else:
                result_text.insert(tk.END, f"{folder_to_remove} is not a valid folder.\n")
        except Exception as e:
            result_text.insert(tk.END, f"Failed to delete {folder_to_remove}: {e}\n")
    else:
        result_text.insert(tk.END, f"{folder_to_remove} does not exist.\n")


def insert_function(event):
    # Get the selected function name from the dropdown
    selected_function = function_var.get()

    # Load the existing functions from the JSON file
    with open(FUNCTIONS_JSON_PATH, "r") as json_file:
        functions_data = json.load(json_file)

    # Get the full function definition for the selected function
    if selected_function in functions_data["functions"]:
        function_definition = functions_data["functions"][selected_function]
        # Update the function definition entry box
        function_entry.delete("1.0", tk.END)
        function_entry.insert("1.0", function_definition)

def is_hdf5_file(file_path):
    try:
        if file_path.endswith(('.hdf5')):
            with h5py.File(file_path, 'r'):
                return True
        return False
    except Exception:
        return False

# Update the URL entry field when an option is selected
def set_url(event):
    # Get the selected URL key from the dropdown
    selected_url = url_var.get()

    # Load the existing URLs from the JSON file
    with open(FUNCTIONS_JSON_PATH, "r") as json_file:
        functions_data = json.load(json_file)

    # Get the full URL for the selected key
    if selected_url in functions_data["urls"]:
        url_value = functions_data["urls"][selected_url]
        # Update the URL entry box
        url_entry.delete(0, tk.END)
        url_entry.insert(tk.END, url_value)  
#__________________________________________________________________________________________________________
def list_functions():
    try:
        # URL for the /list endpoint
        url = "http://192.92.147.107:8142/list"

        # Headers to match the curl request
        headers = {
            "User-Agent": "curl/7.79.1",  # Example User-Agent from curl
            "Accept": "*/*"  # Example Accept header from curl
        }

        # Make the GET request
        response = requests.get(url, headers=headers)

        # Check if the request was successful
        if response.status_code == 200:
            # Clear the result_text widget
            result_text.delete(1.0, tk.END)

            # Insert the raw response into the result_text widget
            result_text.insert(tk.END, "Available Functions:\n\n")
            result_text.insert(tk.END, response.text)  # Display the raw response
        else:
            # Show an error message if the request failed
            result_text.delete(1.0, tk.END)
            result_text.insert(tk.END, f"Error: Failed to fetch functions. Status code: {response.status_code}\n")
    except requests.exceptions.RequestException as e:
        # Show an error message if there was an exception
        result_text.delete(1.0, tk.END)
        result_text.insert(tk.END, f"Error: An error occurred while fetching functions: {e}\n")

# Function to add a new function to the JSON file
def add_function():
    # Get the function definition from the entry box
    function_definition = function_entry.get("1.0", tk.END).strip()


    # Check if the input is empty
    if not function_definition:
        result_text.delete(1.0, tk.END)
        result_text.insert(tk.END, "Error: Function definition is required.\n")
        return

    try:
        # Extract the function name (key) and value
        if ":" in function_definition:
            # If the input contains a colon, split into key and value
            key_value = function_definition.split(":", 1)  # Split on the first colon only
            if len(key_value) == 2:
                function_name = key_value[0].strip()  # Key (function name)
                function_value = key_value[1].strip()  # Value (function definition)
            else:
                # If the input is invalid, treat the entire input as the key and value
                function_name = function_definition.strip()
                function_value = function_definition.strip()
        else:
            # If there is no colon, treat the entire input as the key and value
            function_name = function_definition.strip()
            function_value = function_definition.strip()

        # Load the existing functions from the JSON file
        with open(FUNCTIONS_JSON_PATH, "r") as json_file:
            functions_data = json.load(json_file)

        # Add the new function to the list
        functions_data["functions"][function_name] = function_value

        # Save the updated functions back to the JSON file
        with open(FUNCTIONS_JSON_PATH, "w") as json_file:
            json.dump(functions_data, json_file, indent=4)

        # Update the dropdown menu with only the function names (keys)
        function_combobox["values"] = list(functions_data["functions"].keys())

        # Select the newly added function in the dropdown
        function_var.set(function_name)

        # Update the function definition entry box with the value (function definition)
        function_entry.delete(0, tk.END)
        function_entry.insert(tk.END, function_value)

        # Display a confirmation message
        result_text.delete(1.0, tk.END)
        result_text.insert(tk.END, f"Function '{function_name}' has been added.\n")
    except Exception as e:
        result_text.delete(1.0, tk.END)
        result_text.insert(tk.END, f"Error: Failed to add function. {e}\n")

def add_url():
    # Get the URL from the entry box
    new_url = url_entry.get().strip()

    # Check if the input is empty
    if not new_url:
        result_text.delete(1.0, tk.END)
        result_text.insert(tk.END, "Error: URL is required.\n")
        return

    try:
        # Generate a key for the new URL (e.g., "Custom URL 1", "Custom URL 2", etc.)
        with open(FUNCTIONS_JSON_PATH, "r") as json_file:
            functions_data = json.load(json_file)

        # Find the next available custom URL key
        custom_url_count = 1
        while f"Custom URL {custom_url_count}" in functions_data["urls"]:
            custom_url_count += 1
        url_key = f"Custom URL {custom_url_count}"

        # Add the new URL to the list
        functions_data["urls"][url_key] = new_url

        # Save the updated URLs back to the JSON file
        with open(FUNCTIONS_JSON_PATH, "w") as json_file:
            json.dump(functions_data, json_file, indent=4)

        # Update the URL dropdown menu with the new key
        url_combobox["values"] = list(functions_data["urls"].keys())

        # Select the newly added URL in the dropdown
        url_var.set(url_key)

        # Display a confirmation message
        result_text.delete(1.0, tk.END)
        result_text.insert(tk.END, f"URL '{url_key}' has been added.\n")
    except Exception as e:
        result_text.delete(1.0, tk.END)
        result_text.insert(tk.END, f"Error: Failed to add URL. {e}\n")




custom_data_file_path = "custom_plot_data.dat"

def create_custom_data_file(instructions):
    global custom_data_file_path
    try:
        formulas = [line.strip() for line in instructions.split('\n') if line.strip()]
        if not formulas:
            messagebox.showerror("Error", "No formulas provided.")
            return

        if not os.path.exists("fit_results.dat"):
            messagebox.showerror("Error", "fit_results.dat not found.")
            return

        with open("fit_results.dat", "r") as f:
            raw_data = f.read().strip()

        if not raw_data:
            messagebox.showerror("Error", "fit_results.dat is empty.")
            return

        # Preprocess formulas: replace $N with vN
        processed_formulas = [
            re.sub(r'\$(\d+)', r'v\1', formula) for formula in formulas
        ]

        evaluated_rows = []

        for line in raw_data.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            cols = [col.strip() for col in line.split(",")]

            safe_dict = {
                'sqrt': math.sqrt,
                'log': math.log,
                'log10': math.log10,
                'exp': math.exp,
                'sin': math.sin,
                'cos': math.cos,
                'tan': math.tan,
                'pi': math.pi,
                'e': math.e
            }

            for i, col in enumerate(cols, start=1):
                try:
                    safe_dict[f'v{i}'] = float(col)
                except:
                    safe_dict[f'v{i}'] = 0.0  # fallback for non-numeric

            row_values = []
            for formula in processed_formulas:
                try:
                    val = eval(formula, {"__builtins__": None}, safe_dict)
                    row_values.append(val)
                except Exception as e:
                    messagebox.showerror("Evaluation Error", f"Error in '{formula}': {e}")
                    return

            evaluated_rows.append(row_values)

        # ✅ Group rows by the first evaluated value (e.g., $5)
        grouped = defaultdict(list)
        for row in evaluated_rows:
            key = row[0]
            grouped[key].append(row)

        # ✅ Average each group row-wise
        averaged_rows = []
        for group in grouped.values():
            count = len(group)
            num_cols = len(group[0])
            avg_row = [
                sum(row[i] for row in group) / count
                for i in range(num_cols)
            ]
            averaged_rows.append(avg_row)

        # ✅ Write output
        output_lines = [" ".join(map(str, row)) for row in averaged_rows]
        with open(custom_data_file_path, 'w') as out:
            out.write("\n".join(output_lines))

        messagebox.showinfo("Success", f"Custom data file created:\n{custom_data_file_path}")

    except Exception as e:
        messagebox.showerror("Error", f"Failed to process file: {e}")



def plot_gnuplot():
    user_input = gnuplot_input.get("1.0", tk.END).strip()
    if not user_input:
        messagebox.showerror("Error", "Please enter Gnuplot instructions.")
        return

    # Replace $data with the actual file path
    script_content = user_input.replace("$data", custom_data_file_path)

    try:
        # Write Gnuplot script to a temp file
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".gp") as f:
            f.write(script_content)
            script_path = f.name

        # Run the script using Gnuplot
        subprocess.run(["gnuplot", "-p", script_path])
    except Exception as e:
        messagebox.showerror("Error", f"Gnuplot failed: {e}")









#---------------------------#----------------------------------#---------------------------#-----------------------------#

# Load JSON once before creating GUI
with open(FUNCTIONS_JSON_PATH, "r") as json_file:
    functions_data = json.load(json_file)

functions = functions_data["functions"]
urls = functions_data["urls"]


# Create the main application window
root = tk.Tk()
root.title("OneFit Interface")
root.geometry("1100x580")

# Styling
style = ttk.Style()
style.configure("TLabel", font=("Arial", 10))
style.configure("TEntry", font=("Arial", 10))
style.configure("TCombobox", font=("Arial", 10))

# Allow root's column 0 to expand
root.columnconfigure(0, weight=1)

# ----------- File selection - full width layout -----------
file_frame = tk.Frame(root)
file_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(5,0))

# Configure frame columns
file_frame.columnconfigure(0, weight=0)
file_frame.columnconfigure(1, weight=1)  # Entry expands
file_frame.columnconfigure(2, weight=0)

tk.Label(file_frame, text="Select File:", font=("Arial", 11)).grid(row=0, column=0, padx=(0, 5), sticky="w")
file_entry = ttk.Entry(file_frame)
file_entry.grid(row=0, column=1, padx=2, sticky="ew")
browse_button = tk.Button(file_frame, text="Browse", fg="red", bg="white", font=("Arial", 8), command=browse_file)
browse_button.grid(row=0, column=2, padx=(5, 0), sticky="e")
#--------------------------------------------------------------------------------------------------------------

# --- Server URL 3rd_Frame with Add URL button in one line ---
server_url_frame = tk.Frame(root)
server_url_frame.grid(row=3, column=0, columnspan=4, sticky="ew", pady=(5,0))

# Configure columns for layout
server_url_frame.columnconfigure(1, weight=0)  # Combobox small
server_url_frame.columnconfigure(3, weight=1)  # Entry expands but limited width
server_url_frame.columnconfigure(4, weight=0)  # Button fixed size

# Select URL Label + Combobox (small width)
tk.Label(server_url_frame, text="Select URL:", font=("Arial", 11)).grid(row=0, column=0, padx=2, pady=5, sticky="e")
url_var = tk.StringVar()
url_combobox = ttk.Combobox(server_url_frame, textvariable=url_var, 
                            values=list(functions_data["urls"].keys()), state="readonly", width=20)
url_combobox.grid(row=0, column=1, padx=2, pady=5, sticky="w")
url_combobox.bind("<<ComboboxSelected>>", set_url)

# OneFit-Engine URL Label + Entry (smaller width)
tk.Label(server_url_frame, text="OneFit-Engine URL:", font=("Arial", 11)).grid(row=0, column=2, padx=10, pady=5, sticky="e")
url_entry = ttk.Entry(server_url_frame, width=40)  # Reduced width
url_entry.grid(row=0, column=3, padx=2, pady=5, sticky="we")
url_entry.insert(0, urls[list(urls.keys())[0]])

# Add URL Button (placed at end of the line)
add_url_button = ttk.Button(server_url_frame, text="Add URL", command=add_url, style="TButton")
add_url_button.grid(row=0, column=4, padx=(10, 2), pady=5, sticky="w")

#--------------------------------------------------------------------------------------------------------------


# --- Combined Function + Options Frame (Two Rows) ---
combined_frame = tk.Frame(root)
combined_frame.grid(row=4, column=0, columnspan=4, sticky="ew", pady=(5,0))
combined_frame.columnconfigure(0, weight=1)

# === First Line (Full width layout) ===
top_line_frame = tk.Frame(combined_frame)
top_line_frame.grid(row=0, column=0, sticky="ew")
top_line_frame.columnconfigure(0, weight=1)
top_line_frame.columnconfigure(1, weight=0)

# Left and middle options grouped
left_mid_frame = tk.Frame(top_line_frame)
left_mid_frame.grid(row=0, column=0, sticky="w")

tk.Label(left_mid_frame, text="Select Function:", font=("Arial", 11)).pack(side="left", padx=5)

function_var = tk.StringVar()
function_combobox = ttk.Combobox(left_mid_frame, textvariable=function_var,
                                 values=list(functions_data["functions"].keys()),
                                 state="readonly", width=25)
function_combobox.pack(side="left", padx=5)
function_combobox.bind("<<ComboboxSelected>>", insert_function)

# Options
def add_option(label_text, var):
    tk.Label(left_mid_frame, text=label_text, font=("Arial", 11)).pack(side="left", padx=(10, 2))
    ttk.Combobox(left_mid_frame, textvariable=var, values=["yes", "no"],
                 state="readonly", width=5).pack(side="left", padx=2)

logx_var = tk.StringVar(value="yes")
logy_var = tk.StringVar(value="yes")
autox_var = tk.StringVar(value="yes")
autoy_var = tk.StringVar(value="yes")

add_option("Logx:", logx_var)
add_option("Logy:", logy_var)
add_option("Autox:", autox_var)
add_option("Autoy:", autoy_var)

# SymbSize
tk.Label(left_mid_frame, text="SymbSize:", font=("Arial", 11)).pack(side="left", padx=(10, 2))
symb_size_entry = ttk.Entry(left_mid_frame, width=5)
symb_size_entry.pack(side="left", padx=2)
symb_size_entry.insert(0, "1.0")

# === Second Line: Function Entry (Label + Entry in one frame, Buttons in another frame) ===

# Frame 1: Label + Entry Box
function_entry_frame = tk.Frame(combined_frame)
function_entry_frame.grid(row=1, column=0, sticky="w", padx=5, pady=2)

tk.Label(function_entry_frame, text="Function:", font=("Arial", 11)).grid(row=0, column=0, padx=5, pady=2, sticky="nw")

function_entry = tk.Text(function_entry_frame, height=3, width=128, wrap=tk.WORD, font=("Arial", 10))
function_entry.grid(row=0, column=1, padx=5, pady=2, sticky="w")

# Frame 2: Buttons stacked vertically
function_button_frame = tk.Frame(combined_frame)
function_button_frame.grid(row=1, column=1, sticky="nw", padx=(0, 10))  # Align right side of entry box

add_function_button = ttk.Button(function_button_frame, text="Add Function", command=add_function)
add_function_button.pack(side="top", pady=(0, 2))

list_functions_button = ttk.Button(function_button_frame, text="List Functions", command=list_functions)
list_functions_button.pack(side="top", pady=(0, 2))


# === Result Message Area + Buttons in One Line ===
buttons_message_frame = tk.Frame(root)
buttons_message_frame.grid(row=5, column=0, columnspan=4, sticky="ew", padx=10, pady=10)
buttons_message_frame.columnconfigure(0, weight=1)  # Text expands
buttons_message_frame.columnconfigure(1, weight=0)


# ====== Message Text Area (Left) ======
result_frame = tk.Frame(buttons_message_frame)
result_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
result_frame.grid_rowconfigure(0, weight=1)
result_frame.grid_columnconfigure(0, weight=1)

result_text = tk.Text(result_frame, height=9, wrap=tk.NONE, font=("Arial", 10))
result_text.grid(row=0, column=0, sticky="nsew")

v_scrollbar = tk.Scrollbar(result_frame, orient=tk.VERTICAL, command=result_text.yview, width=15)
v_scrollbar.grid(row=0, column=1, sticky="ns")

h_scrollbar = tk.Scrollbar(result_frame, orient=tk.HORIZONTAL, command=result_text.xview, width=15)
h_scrollbar.grid(row=1, column=0, sticky="ew")

result_text.config(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

# ====== Buttons (Right side, stacked) ======
buttons_frame = tk.Frame(buttons_message_frame)
buttons_frame.grid(row=0, column=1, sticky="n")

button_style = {
    'font': ("Arial", 9),
    'width': 10,
    'height': 1,
    'fg': "black",
}

run_button = tk.Button(buttons_frame, text="Fit", command=run_curl, bg="white", **button_style)
run_button.pack(pady=5)

show_pdf_button = tk.Button(buttons_frame, text="Show PDF", command=show_pdf, bg="white", **button_style)
show_pdf_button.pack(pady=5)

open_folder_button = tk.Button(buttons_frame, text="Open Folder", command=open_downloaded_folder, bg="white", **button_style)
open_folder_button.pack(pady=5)

clean_button = tk.Button(buttons_frame, text="Clean", command=clean_folder, bg="white", **button_style)
clean_button.pack(pady=5)



# === Combined Frame for Create Gnuplot Data + Gnuplot Plotting ===
gnuplot_combined_frame = tk.Frame(root)
gnuplot_combined_frame.grid(row=9, column=0, columnspan=4, sticky="we", padx=10, pady=5)
gnuplot_combined_frame.columnconfigure(0, weight=1)  # Left 1/4
gnuplot_combined_frame.columnconfigure(1, weight=3)  # Right 3/4

# === Create Gnuplot Data Section (Left 1/4) ===
process_frame = tk.Frame(gnuplot_combined_frame, padx=5, pady=5, bd=1, relief="groove")
process_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
process_frame.columnconfigure(0, weight=1)

title_button = tk.Button(
    process_frame, text="FILTER RESULTS",
    font=("Arial", 9, "bold"),
    fg="black", bg="white",
    relief="flat", bd=0,
    activebackground="white", activeforeground="blue",
    cursor="hand2",
    command=lambda: create_custom_data_file(process_text.get("1.0", tk.END))
)
title_button.grid(row=0, column=0, pady=(0, 2), sticky="n")

tk.Label(process_frame, text="Enter column formulas (use $1, $2,...):", font=("Arial", 9)).grid(
    row=1, column=0, sticky="w", padx=5, pady=(2, 0)
)

process_text = tk.Text(process_frame, height=4, width=30, font=("Arial", 9))
process_text.insert(tk.END, "$5\n$10\n$11*sqrt($3)\n1/$10\n$11*sqrt($3/($10*$10))")
process_text.grid(row=2, column=0, padx=5, pady=5, sticky="we")

# === Gnuplot Plotting Section (Right 3/4) ===
plot_frame = tk.Frame(gnuplot_combined_frame, padx=5, pady=5, bd=1, relief="groove")
plot_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
plot_frame.columnconfigure(0, weight=1)

plot_title_button = tk.Button(
    plot_frame, text="GNUPLOT PLOTTING",
    font=("Arial", 9, "bold"),
    fg="black", bg="white",
    relief="flat", bd=0,
    activebackground="white", activeforeground="blue",
    cursor="hand2",
    command=plot_gnuplot
)
plot_title_button.grid(row=0, column=0, pady=(0, 2), sticky="n")

tk.Label(plot_frame, text="Enter Gnuplot instructions (use $data for filename):", font=("Arial", 9)).grid(
    row=1, column=0, sticky="w", padx=5, pady=(0, 5)
)

gnuplot_input = tk.Text(plot_frame, height=8, width=60, font=("Courier", 10))
gnuplot_input.insert(tk.END,
"""set logscale xy
set xrange [1e3:1e9]
set yrange [0.1:10]
plot '$data' using 1:2:3 with yerrorlines pt 2 title 'T1', \\
     '$data' using 1:4:5 with yerrorlines pt 6 title 'R1'
""")
gnuplot_input.grid(row=2, column=0, sticky="we", padx=5, pady=5)




# Start the Tkinter event loop
root.mainloop()

