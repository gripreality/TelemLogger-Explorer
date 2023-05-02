import argparse
import json
import gzip
import os
import csv
from datetime import datetime
from fastkml import kml, styles
from fastkml.geometry import LineString, Point
from pathlib import Path
import glob
import tkinter as tk
from tkinter import filedialog, messagebox

def find_dlog_files(folder_path):
    """
    Returns a list of all *.dlog files in the given folder path.
    """
    dlog_files = glob.glob(folder_path + '/*.dlog')
    return dlog_files

def unzip_files(folder_path):
    """
    Given a folder path, unzips all *.gz files in the folder to a folder with the name of the first file in the folder
    without the extension.
    """
    # Get a list of all *.gz files in the folder
    gz_files = [file for file in os.listdir(folder_path) if file.endswith('.gz')]

    # Create the output folder with the name of the first file in the folder (without the extension)
    output_folder = Path(folder_path) / Path(gz_files[0]).stem.replace('.dlog', '')
    output_folder.mkdir(parents=True, exist_ok=True)

    # Unzip each file to the output folder
    for gz_file in gz_files:
        input_file = Path(folder_path) / gz_file
        output_file = output_folder / Path(gz_file).stem

        with gzip.open(input_file, 'rb') as f_in, open(output_file, 'wb') as f_out:
            f_out.write(f_in.read())

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

class Application(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.pack()
        self.create_widgets()

    def create_widgets(self):
        self.select_folder_button = tk.Button(self, text="Select Folder", command=self.select_folder)
        self.select_folder_button.pack(side="left")

        self.unzip_files_button = tk.Button(self, text="Unzip Files", command=self.unzip_files)
        self.unzip_files_button.pack(side="left")

        self.refresh_data_button = tk.Button(self, text="Refresh Data", command=self.refresh_data)
        self.refresh_data_button.pack(side="left")

        self.export_csv_button = tk.Button(self, text="Export CSV", command=self.export_csv)
        self.export_csv_button.pack(side="left")

        self.export_kml_button = tk.Button(self, text="Export KML", command=self.export_kml)
        self.export_kml_button.pack(side="left")

        self.from_time_label = tk.Label(self, text="From Timecode:")
        self.from_time_label.pack(side="left")
        self.from_time_entry = tk.Entry(self)
        self.from_time_entry.pack(side="left")

        self.to_time_label = tk.Label(self, text="To Timecode:")
        self.to_time_label.pack(side="left")
        self.to_time_entry = tk.Entry(self)
        self.to_time_entry.pack(side="left")

        self.tc_info_label = tk.Label(self, text="")
        self.tc_info_label.pack(side="left")

        self.quit_button = tk.Button(self, text="Quit", fg="red", command=self.master.destroy)
        self.quit_button.pack(side="right")

    def select_folder(self):
        folder_path = filedialog.askdirectory()
        if folder_path:
            self.folder_path = folder_path
            messagebox.showinfo("Folder Selected", f"Selected folder: {self.folder_path}")

    def unzip_files(self):
        if not hasattr(self, 'folder_path'):
            messagebox.showwarning("Folder Not Selected", "Please select a folder first.")
            return

        unzip_files(self.folder_path)
        messagebox.showinfo("Files Unzipped", f"Files unzipped to: {self.folder_path}")

    def refresh_data(self):
        if not hasattr(self, 'folder_path'):
            messagebox.showwarning("Folder Not Selected", "Please select a folder first.")
            return

        dlog_files_list = find_dlog_files(self.folder_path)
        combined_json = combine_json_files(dlog_files_list)

        # Display first and last timecodes if "tc" exists in the dataset
        timecodes = [entry['tc'] for entry in combined_json if 'tc' in entry]
        if timecodes:
            self.tc_info_label.config(text=f"First TC: {timecodes[0]}, Last TC: {timecodes[-1]}")
        else:
            self.tc_info_label.config(text="No timecode data in dataset")

        messagebox.showinfo("Data Refreshed", "Dataset refreshed.")


    def export_csv(self):
        if not hasattr(self, 'folder_path'):
            messagebox.showwarning("Folder Not Selected", "Please select a folder first.")
            return

        dlog_files_list = find_dlog_files(self.folder_path)
        combined_json = combine_json_files(dlog_files_list)

        csv_file = filedialog.asksaveasfilename(defaultextension=".csv")
        if csv_file:
            from_time = self.from_time_entry.get()
            to_time = self.to_time_entry.get()
            filtered_data = filter_data(combined_json, from_time, to_time)
            write_json_to_csv(filtered_data, csv_file, downsample=0)
            messagebox.showinfo("CSV Exported", f"CSV file exported to: {csv_file}")

    def export_kml(self):
        if not hasattr(self, 'folder_path'):
            messagebox.showwarning("Folder Not Selected", "Please select a folder first.")
            return

        dlog_files_list = find_dlog_files(self.folder_path)
        combined_json = combine_json_files(dlog_files_list)

        kml_file = filedialog.asksaveasfilename(defaultextension=".kml")
        if kml_file:
            from_time = self.from_time_entry.get()
            to_time = self.to_time_entry.get()
            filtered_data = filter_data(combined_json, from_time, to_time)
            downsample = int(input("Enter a downsample factor for the KML output: "))
            placemark_downsample = int(input("Enter a downsample factor for the Placemark objects in the KML output: "))
            add_placemarks = messagebox.askyesno("Add Placemarks",
                                                 "Would you like to add Placemark objects to the KML output?")
            export_kml(filtered_data, kml_file, downsample=downsample, add_placemarks=add_placemarks,
                       placemark_downsample=placemark_downsample)
            messagebox.showinfo("KML Exported", f"KML file exported to: {kml_file}")

    def filter_data(self, data):
        from_time = self.from_time_entry.get()
        to_time = self.to_time_entry.get()
        return filter_data(data, from_time, to_time)


root = tk.Tk()
app = Application(master=root)
app.mainloop()

#unzip_files("compData")

#dlog_files_list = find_dlog_files("tcData")
#combined_json = combine_json_files(dlog_files_list)

#json_data = combined_json  # your combined JSON data here
#output = json_data

#export_kml(output, "driveData.kml", downsample=10, add_placemarks=True, placemark_downsample=30)

#csv_file = 'output.csv'  # path to the CSV file you want to create
#write_json_to_csv(json_data, csv_file, downsample=0) # Write the CSV