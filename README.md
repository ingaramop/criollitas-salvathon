# criollitas.py

## Overview
`criollitas.py` is a Python script designed to analyze Marathon JSON configuration files and provide insights into changes, port conflicts, and container image version comparisons within those configurations.

`input.json` and `input2.json` are samples of Marathon JSON configuration files.

## Features

1. **Configuration Change List**:
   - Lists every application that has changed its configuration during the last X hours.
   - The output will be in the format: `{CONFIG_MODIFICATION_DATE <-> APPLICATION NAME}`.
   - The list is ordered by `CONFIG_MODIFICATION_DATE` in descending order.

2. **Duplicate Port Report**:
   - Generates a report of applications using the same `containerPort`.

3. **Container Image Version Comparison** (Optional):
   - If a second Marathon JSON configuration file is provided, the script performs a comparison between the two files' applications to determine the newest container image versions.

## Usage

1- Requierement: Make sure you have Python3 installed on your system.
2- Get the code:
```bash
git clone https://github.com/ingaramop/criollitas-salvathon.git
```
2- Step into the project directory:
```bash
cd criollitas-salvathon
```
3- Execute the script:
```bash
python criollitas.py <orchestrator_cfg_json_file1> <time_window_hours> <optional_orchestrator_cfg_json_file2>
```
**Where:**
  - `<orchestrator_cfg_json_file1>` is the main container orchestrator config file to be analyzed.
  - `<time_window_hours>` is the threshold in hours to check back in time for application config changes.
  - `<optional_orchestrator_cfg_json_file2>` is a secondary and optional container orchestrator config file.
    - If present, a version comparison will be performed between this file and the main one.
    - If absent, no analysis will be performed.

**Example1.** Analyze input.json with a time window of 2000 hours:
```bash
python criollitas.py input.json 20000
```
**Example2.** Analyze input.json with a time window of 3000 hours and compare it with input2.json:
```bash
python criollitas.py input.json 30000 input2.json
```
