import sys
import os
import json
from datetime import datetime


def check_arguments(params):
  if len(params) == 3:
      orchestrator_cfg_json_file1 = params[1]
      time_window_hours = params[2]
      if not os.path.isfile(orchestrator_cfg_json_file1):
          raise Exception(f"Argument 1 ({orchestrator_cfg_json_file1}) is not a valid path to an existing file.")
      elif not (time_window_hours).isnumeric():
          raise Exception(f"Argument 2 ({time_window_hours}) is not an integer.")
  elif len(params) == 4:
      orchestrator_cfg_json_file1 = params[1]
      time_window_hours = params[2]
      optional_orchestrator_cfg_json_file2 = params[3]

      if not os.path.isfile(orchestrator_cfg_json_file1):
          raise Exception(f"Argument 1 ({orchestrator_cfg_json_file1}) is not a valid path to an existing file.")
      elif not (time_window_hours).isnumeric():
          raise Exception(f"Argument 2 ({time_window_hours}) is not an integer.")
      if not os.path.isfile(optional_orchestrator_cfg_json_file2):
          raise Exception(f"Argument 3 ({optional_orchestrator_cfg_json_file2}) is not a valid path to an existing file.")
  else:
      raise Exception("Incorrect amount of params.")


# Function to extract all occurrences of "apps" objects
def collect_applications_from_json(orchestrator_cfg_json_file):
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

# Function to check if a date is within X hours of the current time
def changed_cfg_in_the_last_hours(date_string, hours):
    current_time = datetime.now()
    date_time = datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S.%fZ")
    time_difference = current_time - date_time
    return time_difference.total_seconds() <= hours*60*60 




USAGE_MSG = """USAGE: python criollitas.py <orchestrator_cfg_json_file1> <time_window_hours> <optional_orchestrator_cfg_json_file2>.
WHERE:
  - <orchestrator_cfg_json_file1> is the main container orchestrator config file to be analyzed.
  - <time_window_hours> is the threshold in hours to check back in time for application config changes.
  - <optional_orchestrator_cfg_json_file2> is a secondary and optional container orchestrator config file.
    If it is present, a version comparison will be performed between this file and the main one.
    If it is absent, no analisys will be performed. """

#Check if args are correct, else print error and exit
try:
    check_arguments(sys.argv)
except Exception as e:
    print(f"ERROR: {e}")
    print(USAGE_MSG)
    exit(-1)

#Open and parse the <orchestrator_cfg_json_file1>, else print error and exit
try:
    with open("input.json", 'r') as json_file:
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


print(f"Applications that changed their config in the last {time_window_hours} hours, ordered by change date desc.:")
print("CONFIG_MODIFICATION_DATE <-> APPLICATION NAME")
if len(ordered_applications) == 0:
    print("No apps found matching this criteria.")
for app in ordered_applications:
    print(f'{app["versionInfo"]["lastConfigChangeAt"]} <-> {app["id"]}')

