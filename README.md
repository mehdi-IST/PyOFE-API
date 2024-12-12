# PyOFE-API
PyOFE-API (OneFit-Engine API) is a Python-based graphical user interface (GUI) application that simplifies the process for data fitting, downloading results, and displaying processed outputs. It is particularly tailored for researchers working with .hdf5 files in the context of NMR relaxometry and similar analyses.

Features
    File Upload: 
		Select .hdf5 files for processing.
    Server Connectivity: 
		Choose between university and local server URLs.
    User Defined Function: 
		Input or select pre-defined monoexponential or biexponential functions.
    Automated Downloads: 
		Download and extract result ZIP files directly.
	
Result Visualization
	View extracted parameters from JSON files.
        Automatically locate and open All.pdf files.
Folder Management
	Open or clean up the downloaded results folder.
Responsive UI 
	Utilizes threading for non-blocking operations.
Cross-Platform Support: 
		Compatible with Windows, macOS, and Linux.  

Prerequisites
Before running PyOFE-API, ensure you have the following installed:
Python 3.8+
Required Python libraries:
pip install requests tkinter
