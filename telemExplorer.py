import argparse
import json
import gzip
import os
import csv
from datetime import datetime
from pathlib import Path
from fastkml import kml, styles
from fastkml.geometry import LineString, Point

import glob

def find_dlog_files(folder_path):
    """
    Returns a list of all *.dlog files in the given folder path.
    """
    dlog_files = glob.glob(folder_path + '/*.dlog')
    return dlog_files

def combine_json_files(file_list):
    """
    Reads each file in file_list, combines the non-empty JSON objects into a single array, and returns the resulting array.
    """
    combined_json = []
    for file_path in file_list:
        with open(file_path, 'r') as f:
            json_data = json.load(f)
            non_empty_json = [j for j in json_data if j]  # remove empty JSON objects
            combined_json.extend(non_empty_json)
    return combined_json


def write_json_to_csv(json_data, csv_file, downsample=0, keys_to_include=None):
    """
    Writes the given JSON data to the specified CSV file.
    """
    with open(csv_file, 'w', newline='') as f:
        writer = csv.writer(f)

        if keys_to_include is None:
            # If keys_to_include is not provided, use all keys from the first JSON object
            keys_to_include = json_data[0].keys()

        # Write header row
        writer.writerow(keys_to_include)

        # Write each JSON object as a row in the CSV file, applying the downsample factor
        for index, json_obj in enumerate(json_data):
            if index % (downsample + 1) == 0:
                row = [json_obj.get(key, '') for key in keys_to_include]
                writer.writerow(row)

def timecode_to_milliseconds(timecode):
    hours, minutes, seconds, frames = [int(part) for part in timecode.split(':')]
    milliseconds = (hours * 3600 + minutes * 60 + seconds) * 1000 + frames * (1000 / 30)
    return int(milliseconds)


def filter_data(data, from_time, to_time):
    from_time_ms = timecode_to_milliseconds(from_time) if from_time else None
    to_time_ms = timecode_to_milliseconds(to_time) if to_time else None

    filtered_data = []
    for entry in data:
        tc_ms = timecode_to_milliseconds(entry['tc'])
        if (from_time_ms is None or from_time_ms <= tc_ms) and (to_time_ms is None or tc_ms <= to_time_ms):
            filtered_data.append(entry)

    return filtered_data


def create_placemark(entry, ns):
    placemark = kml.Placemark(ns)
    placemark.name = entry['tc']
    description = f"Timecode: {entry['tc']}\n"
    for key, value in entry.items():
        if key != 'tc':
            description += f"{key}: {value}\n"
    placemark.description = description.strip()
    placemark.geometry = Point(entry['longitudeValue'], entry['latitudeValue'], entry['altitudeValue'])

    placemark.extended_data = kml.ExtendedData()
    for key, value in entry.items():
        if key not in ('latitudeValue', 'longitudeValue', 'altitudeValue', 'tc'):
            placemark.extended_data.elements.append(kml.Data(name=key, value=str(value)))

    return placemark


def export_kml(data, filename, downsample=0, add_placemarks=True, placemark_downsample=0):
    ns = '{http://www.opengis.net/kml/2.2}'

    k = kml.KML(ns)
    doc = kml.Document(ns)
    k.append(doc)

    line_string_coordinates = []
    for index, entry in enumerate(data):
        if index % (downsample + 1) == 0:
            if add_placemarks and index % (placemark_downsample + 1) == 0:
                placemark = create_placemark(entry, ns)
                doc.append(placemark)

            # Add coordinates to the line_string_coordinates list
            line_string_coordinates.append((entry['longitudeValue'], entry['latitudeValue'], entry['altitudeValue']))

    # Create a LineString with the collected coordinates
    line_string = LineString(line_string_coordinates)

    # Create a Placemark and set its geometry attribute
    line_placemark = kml.Placemark(ns)
    line_placemark.geometry = line_string
    doc.append(line_placemark)

    with open(filename, 'w') as kml_file:
        kml_file.write(k.to_string(prettyprint=True))


dlog_files_list = find_dlog_files("tcData")
combined_json = combine_json_files(dlog_files_list)

json_data = combined_json  # your combined JSON data here
output = json_data

#export_kml(output, "driveData.kml", downsample=10, add_placemarks=True, placemark_downsample=30)

csv_file = 'output.csv'  # path to the CSV file you want to create
write_json_to_csv(json_data, csv_file, downsample=0) # Write the CSV