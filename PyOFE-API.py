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


# Default URLs
UNIVERSITY_URL = "http://onefite-t.vps.tecnico.ulisboa.pt:8142/fit"
LOCAL_URL = "http://localhost:8142/fit/muhammad"

FUNCTIONS_JSON_PATH = "functions.json"
# Default functions
MONOEXP = r"Mz(t,Mi[0<1.5],M0[0<1.5],T11[0.0001<5])[-1.2<1.2]=Mi \+ (M0-Mi)*exp(-t/T11)"
BIEXP = r"Mz(t,Mi[0<1.5],M0[0<1.5],T11[0.0001<5],T12[0.0001<5],c=1[0.5<1])[-1.2<1.2]=Mi \+ c*(M0-Mi)*exp(-t/T11) \+(1-c)*(M0-Mi)*exp(-t/T12)"

# Confirm that JSON file with functions is generated if missing
if not os.path.exists(FUNCTIONS_JSON_PATH):
    default_functions = {
        "functions": {
            "Monoexponential": MONOEXP,
            "Biexponential": BIEXP
        }
    }
    with open(FUNCTIONS_JSON_PATH, "w") as json_file:
        json.dump(default_functions, json_file, indent=4)
# Function to load functions from JSON file
def load_functions_from_json():
    with open(FUNCTIONS_JSON_PATH, "r") as json_file:
        data = json.load(json_file)
    return data["functions"]
# Load functions from JSON file
functions = load_functions_from_json()



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

    # Get user inputs
    file_path = file_entry.get()
    function = function_entry.get()
    logx = logx_var.get()
    autox = autox_var.get()
    server_url = url_entry.get()
    download_folder = "downloaded"

    # Validate inputs
    if not os.path.isfile(file_path):
        stop_blinking()
        result_text.delete(1.0, tk.END)
        result_text.insert(tk.END, "Error: Please select a valid .hdf5 file.\n")
        return
    if not server_url:
        stop_blinking()
        result_text.delete(1.0, tk.END)
        result_text.insert(tk.END, "Error: Server URL is required.\n")
        return
    if not function:
        stop_blinking()
        result_text.delete(1.0, tk.END)
        result_text.insert(tk.END, "Error: Function definition is required.\n")
        return

    # Prepare the request payload with automatic stelar-hdf5 detection
    params = {
        "stelar-hdf5": "yes" if is_hdf5_file(file_path) else "no",
        "function": function,
        "logx": logx,
        "autox": autox,
        "download": "zip"
    }

    # Call the query function
    try:
        query(server_url, file_path, params, download_folder)
        stop_blinking()
    except Exception as e:
        stop_blinking()
        result_text.delete(1.0, tk.END)
        result_text.insert(tk.END, f"Error: {e}\n")


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
    file_path = filedialog.askopenfilename(filetypes=[("HDF5 files", "*.hdf5"), ("All files", "*.*")])
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

def use_local_url():
    # Set the server URL to the local URL
    url_entry.delete(0, tk.END)
    url_entry.insert(0, LOCAL_URL)

def insert_function(event):
    selected_function = function_var.get()
    if selected_function == "Monoexponential":
        function_entry.delete(0, tk.END)
        function_entry.insert(tk.END, MONOEXP)
    elif selected_function == "Biexponential":
        function_entry.delete(0, tk.END)
        function_entry.insert(tk.END, BIEXP)

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
    selected_function = function_var.get()
    if selected_function in functions:
        function_entry.delete(0, tk.END)
        function_entry.insert(tk.END, functions[selected_function])

def is_hdf5_file(file_path):
    try:
        with h5py.File(file_path, 'r'):
            return True
    except Exception:
        return False

# Create the main application window
root = tk.Tk()
root.title("OneFit Interface")
root.geometry("1150x600")

# Styling
style = ttk.Style()
style.configure("TLabel", font=("Arial", 10))
style.configure("TEntry", font=("Arial", 10))
style.configure("TCombobox", font=("Arial", 10))

# File selection
tk.Label(root, text="Select File (.hdf5):", font=("Arial", 11)).grid(row=0, column=0, padx=2, pady=5, sticky="e")
file_entry = ttk.Entry(root, width=40)
file_entry.grid(row=0, column=1, padx=2, pady=5, sticky="ew")
browse_button = tk.Button(root, text="Browse", command=browse_file, fg="red", bg="white", font=("Arial", 8))
browse_button.grid(row=0, column=2, padx=2, pady=5, sticky="w")

#Logx, and Autox options
options_frame = tk.Frame(root)
options_frame.grid(row=1, column=0, columnspan=6, pady=10, sticky="ew")

tk.Label(options_frame, text="Logx:", font=("Arial", 11)).grid(row=0, column=0, padx=10, sticky="e")
logx_var = tk.StringVar(value="yes")
logx_dropdown = ttk.Combobox(options_frame, textvariable=logx_var, values=["yes", "no"], state="readonly", width=10)
logx_dropdown.grid(row=0, column=1, padx=5, sticky="w")

tk.Label(options_frame, text="Autox:", font=("Arial", 11)).grid(row=0, column=2, padx=10, sticky="e")
autox_var = tk.StringVar(value="yes")
autox_dropdown = ttk.Combobox(options_frame, textvariable=autox_var, values=["yes", "no"], state="readonly", width=10)
autox_dropdown.grid(row=0, column=3, padx=5, sticky="w")

# Function definition
tk.Label(root, text="Function:", font=("Arial", 11)).grid(row=2, column=0, padx=2, pady=2, sticky="e")
function_entry = ttk.Entry(root, width=120)
function_entry.grid(row=2, column=1, padx=2, pady=2, sticky="w")

# Function dropdown
tk.Label(root, text="Select Function:", font=("Arial", 11)).grid(row=2, column=2, padx=2, pady=2, sticky="e")
# Load functions from JSON file
with open(FUNCTIONS_JSON_PATH, "r") as json_file:
    functions_data = json.load(json_file)  # Load all functions from the JSON

function_var = tk.StringVar()
function_combobox = ttk.Combobox(root, textvariable=function_var, values=list(functions_data["functions"].keys()), state="readonly", width=20)
function_combobox.grid(row=2, column=3, padx=2, pady=2, sticky="w")
function_combobox.bind("<<ComboboxSelected>>", insert_function)

# Server URL
tk.Label(root, text="OneFit-Engine URL:", font=("Arial", 11)).grid(row=3, column=0, padx=2, pady=5, sticky="e")
url_entry = ttk.Entry(root, width=45)
url_entry.grid(row=3, column=1, padx=2, pady=5, sticky="w")

# Dropdown-style button for selecting URL
tk.Label(root, text="Select URL:", font=("Arial", 11)).grid(row=3, column=2, padx=2, pady=5, sticky="e")
url_var = tk.StringVar(value="Select URL")
url_dropdown = ttk.Combobox(root, textvariable=url_var, values=["University URL", "Local URL"], state="readonly", width=15)
url_dropdown.grid(row=3, column=3, padx=2, pady=5, sticky="w")

#__________________________________________________________________________________________________________
# Update the URL entry field when an option is selected
def set_url(event):
    selected_url = url_var.get()  # Get selected URL from dropdown
    if selected_url == "University URL":
        url_entry.delete(0, tk.END)  # Clear the entry field
        url_entry.insert(0, UNIVERSITY_URL)  # Insert University URL
    elif selected_url == "Local URL":
        url_entry.delete(0, tk.END)  # Clear the entry field
        url_entry.insert(0, LOCAL_URL)  # Insert Local URL

# Server URL Label and Entry
tk.Label(root, text="OneFit-Engine URL:", font=("Arial", 11)).grid(row=3, column=0, padx=2, pady=5, sticky="e")
url_entry = ttk.Entry(root, width=45)
url_entry.grid(row=3, column=1, padx=2, pady=5, sticky="w")

# Set default value for url_var to "University URL" to ensure it’s selected initially
url_var = tk.StringVar(value="University URL")  # Default value is "University URL"

# Set the default value in the URL entry field
url_entry.insert(0, UNIVERSITY_URL)

# Dropdown-style button for selecting URL
tk.Label(root, text="Select URL:", font=("Arial", 11)).grid(row=3, column=2, padx=2, pady=5, sticky="e")

url_dropdown = ttk.Combobox(root, textvariable=url_var, values=["University URL", "Local URL"], state="readonly", width=15)
url_dropdown.grid(row=3, column=3, padx=2, pady=5, sticky="w")

# Bind the selection event to update the URL entry field
url_dropdown.bind("<<ComboboxSelected>>", set_url)
#________________________________________________________________________________________________________

# Define a consistent button style for all buttons
button_style = {
    'font': ("Arial", 9),
    'width': 10,
    'height': 1,
    'fg': "white",
    'bg': "blue",
}

# Run button
run_button = tk.Button(root, text="Fit", command=run_curl, fg="red", bg="white", font=("Arial", 10, "bold"), width=8, height=1)
run_button.place(x=250, y=550)  # Adjust x and y values for balanced positioning

# Show PDF button
show_pdf_button = tk.Button(root, text="Show PDF", command=show_pdf, fg="green", bg="white", font=("Arial", 10), width=8, height=1)
show_pdf_button.place(x=400, y=550)  # Adjust x and y values for balanced positioning

# Open Downloaded Folder button
open_folder_button = tk.Button(root, text="Open Folder", command=open_downloaded_folder, **button_style)
open_folder_button.place(x=550, y=550)  # Adjust x and y values for balanced positioning

# Clean button
clean_button = tk.Button(root, text="Clean", command=clean_folder, **button_style)
clean_button.place(x=700, y=550)  # Adjust x and y values for balanced positioning

# Create a Text widget to display the fit_result
result_text = tk.Text(root, height=28, width=180, wrap=tk.WORD, font=("Arial", 8))
result_text.grid(row=6, column=0, columnspan=5, padx=10, pady=10)

# Start the Tkinter event loop
root.mainloop()

