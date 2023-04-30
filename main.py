import argparse
import json
import gzip
import os
import csv
from datetime import datetime
from pathlib import Path
from fastkml import kml, styles
from fastkml.geometry import Point


def read_json_lines(file_path, gzip_compressed):
    data = []
    open_func = gzip.open if gzip_compressed else open
    with open_func(file_path, 'rt', encoding='utf-8') as file:
        for line in file:
            data.append(json.loads(line.strip()))
    return data


def concatenate_files(input_path, gzip_compressed):
    data = []
    if os.path.isdir(input_path):
        for file_name in os.listdir(input_path):
            if file_name.endswith('.dlog.gz' if gzip_compressed else '.dlog'):
                data.extend(read_json_lines(os.path.join(input_path, file_name), gzip_compressed))
    elif os.path.isfile(input_path):
        data = read_json_lines(input_path, gzip_compressed)
    return data


def filter_data(data, from_time, to_time):
    if from_time is None and to_time is None:
        return data
    elif from_time is None:
        return [entry for entry in data if entry['tc'] <= to_time]
    elif to_time is None:
        return [entry for entry in data if from_time <= entry['tc']]
    else:
        return [entry for entry in data if from_time <= entry['tc'] <= to_time]


def export_csv(data, output_file):
    if data:
        keys = data[0].keys()
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=keys)
            writer.writeheader()
            for row in data:
                writer.writerow(row)


def create_placemark(entry, ns):
    latitude = entry.get('latitudeValue', 0.0)
    longitude = entry.get('longitudeValue', 0.0)
    altitude = entry.get('altitudeValue', 0.0)

    point = Point((longitude, latitude, altitude))
    placemark = kml.Placemark(ns, 'pmid-' + entry['tc'], entry['tc'], styleUrl='#pointstyle')
    placemark.geometry = point
    placemark.extended_data = kml.ExtendedData()
    for key, value in entry.items():
        if key not in ['latitudeValue', 'longitudeValue', 'altitudeValue']:
            placemark.extended_data.add_data(kml.Data(name=key, value=value))
    return placemark


def export_kml(data, output_file):
    ns = '{http://www.opengis.net/kml/2.2}'
    doc = kml.Document(ns, 'docid', 'Telemetry Data', 'Telemetry Data Description')

    point_style = styles.Style(id='pointstyle')
    icon_style = styles.IconStyle(scale=0.5,
                                  icon_href='http://maps.google.com/mapfiles/kml/shapes/placemark_circle.png')
    point_style.append_style(icon_style)
    doc.append_style(point_style)

    for entry in data:
        placemark = create_placemark(entry, ns)
        doc.append(placemark)

    k = kml.KML(ns)
    k.append(doc)

    with open(output_file, 'w', encoding='utf-8') as kml_file:
        kml_file.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        kml_file.write(k.to_string(prettyprint=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process telemetry data.')
    parser.add_argument('-d', type=str, help='Input directory or file')
    parser.add_argument('-gzip', action='store_true', help='Read gzip compressed files')
    parser.add_argument('-csv', type=str, help='Output CSV file')
    parser.add_argument('-kml', type=str, help='Output KML file')
    parser.add_argument('-ti', type=str, help='Start time (inclusive)')
    parser.add_argument('-to', type=str, help='End time (inclusive)')
    args = parser.parse_args()

    if not args.d:
        print('Please specify an input directory or file with the -d option.')
        exit(1)

    data = concatenate_files(args.d, args.gzip)
    from_time = args.ti
    to_time = args.to
    filtered_data = filter_data(data, from_time, to_time)

    if args.csv:
        export_csv(filtered_data, args.csv)
        print(f"Exported {len(filtered_data)} entries to {args.csv}")

    if args.kml:
        export_kml(filtered_data, args.kml)
        print(f"Exported {len(filtered_data)} entries to {args.kml}")
