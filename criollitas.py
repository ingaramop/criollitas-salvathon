import sys
import os
import json
from datetime import datetime

def check_arguments(args):
    """
    Validate and check command-line arguments for the script.
    Args:
        args (list): A list of command-line arguments.
    Raises: 
        Exception: If any validation checks fail, generic exceptions with descriptive error messages are raised.
    """
    if len(args) == 3:
        orchestrator_cfg_json_file1 = args[1]
        time_window_hours = args[2]
        if not os.path.isfile(orchestrator_cfg_json_file1):
            raise Exception(f"Argument 1 ({orchestrator_cfg_json_file1}) is not a valid path to an existing file.")
        elif not (time_window_hours).isnumeric():
            raise Exception(f"Argument 2 ({time_window_hours}) is not an integer.")
    elif len(args) == 4:
        orchestrator_cfg_json_file1 = args[1]
        time_window_hours = args[2]
        optional_orchestrator_cfg_json_file2 = args[3]

        if not os.path.isfile(orchestrator_cfg_json_file1):
            raise Exception(f"Argument 1 ({orchestrator_cfg_json_file1}) is not a valid path to an existing file.")
        elif not (time_window_hours).isnumeric():
            raise Exception(f"Argument 2 ({time_window_hours}) is not an integer.")
        if not os.path.isfile(optional_orchestrator_cfg_json_file2):
            raise Exception(f"Argument 3 ({optional_orchestrator_cfg_json_file2}) is not a valid path to an existing file.")
    else:
        raise Exception("Incorrect amount of params.")

def collect_applications_from_json(orchestrator_cfg_json_file):
    """
    Recursive function to extract all occurrences of "apps" objects, nested in different levels of hierarchy within the object structure.
    Args:
        orchestrator_cfg_json_file (obj) : An object resultant of parsing a Marathon json config file.
    Returns: 
        list: A list with all the "apps" objects found in the input.
    """
    apps_objects = []
    
    if isinstance(orchestrator_cfg_json_file, dict):
        for key, value in orchestrator_cfg_json_file.items():
            if key == "apps" and isinstance(value, list):
                apps_objects.extend(value)
            else:
                apps_objects.extend(collect_applications_from_json(value))
    elif isinstance(orchestrator_cfg_json_file, list):
        for item in orchestrator_cfg_json_file:
            apps_objects.extend(collect_applications_from_json(item))
    return apps_objects

def changed_cfg_in_the_last_hours(date_string, hours):
    """
    Check if a configuration change occurred within the specified time window.
    Args:
        date_string (str): A timestamp in the format "%Y-%m-%dT%H:%M:%S.%fZ" representing the configuration change date.
        hours (int): The time window threshold in hours.
    Returns:
        bool: True if the configuration change occurred within the specified time window, False otherwise.
    """

    current_time = datetime.now()
    date_time = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S.%fZ")
    time_difference = current_time - date_time
    return time_difference.total_seconds() <= hours*60*60 


def find_duplicate_containerPorts(applications_file):
    """
    Find duplicate containerPorts within a list of applications.
    Args:
        applications_file (list): A list of application objects from a Marathon json config file.
    Returns:
        dict: A dictionary mapping duplicate containerPorts to a list of applications using them.
    """
    port_to_applications = {}# Create a dictionary to map containerPorts to lists of applications using them

    for application in applications_file: #iter on all apps
        try:
            for port_mapping in application["container"]["portMappings"]: #iter on application port_mappings
                # if conteiner port has already been initialized in the dictionary, then add a new entry to the existing key
                if port_mapping["containerPort"] in port_to_applications:
                    port_to_applications[port_mapping["containerPort"]].append({"application": application["id"], "hostPort": port_mapping["hostPort"],
                                                    "servicePort": port_mapping["servicePort"]})
                # else, create the new key
                else:
                    port_to_applications[port_mapping["containerPort"]] = [{"application": application["id"], "hostPort": port_mapping["hostPort"],
                                                    "servicePort": port_mapping["servicePort"]}]
        except Exception as e:
            #print(f"ERROR checking ports: {e}") 
            pass  
    
    # Remove those ports that are used by a single application (as we are checking for duplicates)
    port_to_applications = {key: value for key, value in port_to_applications.items() if len(value) > 1}
    return port_to_applications

def compare_application_versions_between_files(applications_file1, applications_file2):
    """
    Compare application image versions between two sets of applications from different files. The format of the images is format: Registry/component:version-date-hour.

    Args:
        applications_file1 (list): A list of applications from the first file.
        applications_file2 (list): A list of applications from the second file.

    Returns:
        list: A list of version differences between the applications from the two files. Each entry in the list is a dictionary with the following keys:
        - "application": Application ID
        - "image_version_file_1": Image version in the first file
        - "image_version_file_2": Image version in the second file
        - "most_recent": The most recent version between the two files
    """
    version_change_list = []
    # iter over all apps in file1
    for app_from_file1 in applications_file1:
        # Use the filter function to find the equivalent application in applications_file2
        filtered_result = list(filter(lambda obj: obj["id"] == app_from_file1["id"], applications_file2))
        # Check if the filtered_objects list is not empty
        if len(filtered_result) == 0:
            continue # If same app id is not found in applications_file2, continue
        app_from_file2 = filtered_result[0]

        application_file1_image = app_from_file1["container"]["docker"]["image"] #format: Registry/component:version-date-hour
        application_file2_image = app_from_file2["container"]["docker"]["image"] #format: Registry/component:version-date-hour

        if application_file1_image == application_file2_image:
            continue # If images are identical, continue

        if application_file1_image.split(":")[0] != application_file2_image.split(":")[0]:
            continue # If "Registry/component" part of the image is not identical, continue

        #At this point, I know the fields version-date-hour are not equal.

        app1_full_version = application_file1_image.split(":")[1] #format: version-date-hour
        app2_full_version = application_file2_image.split(":")[1] #format: version-date-hour

        most_recent = find_most_recent_version(app1_full_version, app2_full_version)

        # Append version comparison to list
        version_change_list.append(({"application": app_from_file1["id"], "image_version_file_1": app_from_file1["container"]["docker"]["image"],
                                    "image_version_file_2": app_from_file2["container"]["docker"]["image"], "most_recent": most_recent}))
    return version_change_list

def find_most_recent_version(app1_full_version, app2_full_version):
    """
    Compare two full version strings and determine the most recent version.
    Args:
        app1_full_version (str): Full version string from the first application.
        app2_full_version (str): Full version string from the second application.
    Returns:
        str: The result indicating which version is the most recent:
        - "image_version_file_1" if the first application's version is more recent.
        - "image_version_file_2" if the second application's version is more recent.
        - "unknown" if versions cannot be compared or are equal.
    """
    most_recent = "unknown"
    try:   
        # Split version strings into lists of integers
        version1_parts = [int(part) for part in app1_full_version.split("-")[0].strip('v').split('.')] 
        version2_parts = [int(part) for part in app2_full_version.split("-")[0].strip('v').split('.')] 
        # Pad the shorter version with zeros
        while len(version1_parts) < len(version2_parts):
            version1_parts.append(0)
        while len(version2_parts) < len(version1_parts):
            version2_parts.append(0)  
        # Compare each part of the version
        for part1, part2 in zip(version1_parts, version2_parts):
            if part1 < part2:
                return "image_version_file_2"
            elif part1 > part2:
                 return "image_version_file_1"
            
        # If versions are equal, compare the dates
        date1 = int(app1_full_version.split("-")[1])
        date2 = int(app2_full_version.split("-")[1])
        if date1 < date2:
            return "image_version_file_2"
        elif date1 > date2:
            return "image_version_file_1"
        else:
            # If dates are equal, compare the hours
            hour1 = int(app1_full_version.split("-")[2])
            hour2 = int(app2_full_version.split("-")[2])
            if hour1 < hour2:
                return "image_version_file_2"
            if hour1 > hour2:
                return "image_version_file_1"
    except:
        pass
    return "unknown"

USAGE_MSG = """USAGE: python criollitas.py <orchestrator_cfg_json_file1> <time_window_hours> <optional_orchestrator_cfg_json_file2>.
WHERE:
  - <orchestrator_cfg_json_file1> is the main container orchestrator config file to be analyzed.
  - <time_window_hours> is the threshold in hours to check back in time for application config changes.
  - <optional_orchestrator_cfg_json_file2> is a secondary and optional container orchestrator config file.
    If it is present, a version comparison will be performed between this file and the main one.
    If it is absent, no analysis will be performed. """

#Check if args are correct, else print error and exit
try:
    check_arguments(sys.argv)
except Exception as e:
    print(f"ERROR: {e}")
    print(USAGE_MSG)
    exit(-1)

#Open and parse the <orchestrator_cfg_json_file1>, else print error and exit
try:
    with open(sys.argv[1], 'r') as json_file:
        parsed_json = json.load(json_file)
except Exception as e:
    print(f"Unable to parse file {sys.argv[1]}.")
    print(f"ERROR: {e}")
    exit(-1)

#Collect applications info from json
applications_file1 = collect_applications_from_json(parsed_json)
time_window_hours = int(sys.argv[2])

# Filter the list of objects
filtered_applications = [obj for obj in applications_file1 if changed_cfg_in_the_last_hours(obj["versionInfo"]["lastConfigChangeAt"], time_window_hours)]

# Sort the filtered list by date in descending order (latest date first)
ordered_applications = sorted(filtered_applications, key=lambda obj: obj["versionInfo"]["lastConfigChangeAt"], reverse=True)

print(f"Applications that changed their config in the last {time_window_hours} hours, ordered by change date desc:\n".upper())
print("CONFIG_MODIFICATION_DATE <-> APPLICATION NAME")
if len(ordered_applications) == 0:
    print("No apps found matching this criteria.")
for app in ordered_applications:
    print(f'{app["versionInfo"]["lastConfigChangeAt"]} <-> {app["id"]}')


# Perform analysis to find duplicate ports
port_to_applications_dictionary = find_duplicate_containerPorts(applications_file1)

print("\n--------------------------------------------------------------\n")

print("Applications using the same containerPort Report:\n".upper())
# Print the report
for key, value in port_to_applications_dictionary.items():
    print(f"containerPort {key}:")
    for obj in value:
        print(obj)
# Alternative way to print the report in json format        
#json_formatted_str = json.dumps(port_to_applications_dictionary, indent=2)
#print(json_formatted_str)

print("\n--------------------------------------------------------------\n")

if len(sys.argv) == 4: # If there is a secondary file provided, perform version comparison
    print("Version difference analysis between configuration files:\n".upper())

    #Open and parse the <orchestrator_cfg_json_file1>, else print error and exit
    try:
        with open("input.json", 'r') as json_file:
            parsed_json = json.load(json_file)
    except Exception as e:
        print(f"Unable to parse file {sys.argv[3]}. Analysis")
        print(f"ERROR: {e}")
        exit(-1)

    #Collect applications info from json file 2
    with open("input2.json", 'r') as json_file:
        applications_file2 = collect_applications_from_json(json.load(json_file))
    

    version_change_list = compare_application_versions_between_files(applications_file1, applications_file2)

    print (f"applications_file1 = {sys.argv[1]}")
    print (f"applications_file2 = {sys.argv[3]}")
    json_formatted_str = json.dumps(version_change_list, indent=2)
    print(json_formatted_str)
