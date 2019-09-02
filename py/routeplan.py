'''routeplan.py
'''
import os
import configparser
import fileinput
import csv
import json
import xml.etree.cElementTree as ET
from datetime import datetime
import requests
import semver
import git

MAJOR = 0
MINOR = 1
PATCH = 0

DEBUG = True

WAYMARKS_CSV = '../waymarks/waymarks.csv'
PATH_ROUTES = '../routes/'
HTML_HEADER = '../docs_templates/edfr.header.html'
TOP_HTML_TEMPLATE = '../docs_templates/edfr.template.html'
ROUTE_HTML_TEMPLATE = '../docs_templates/route.template.html'
TOP_HTML_NAME = '../docs/EDFR.html'
HTML_PATH = '../docs/'


def get_coords(coords_csv):
    '''Function get_coords
    '''
    coords_from_csv = []
    with open(coords_csv) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        line_count = 0
        for row in csv_reader:
            coord_from_csv = {'latitude': row[0].strip(),
                              'longitude': row[1].strip()}
            coords_from_csv.append(coord_from_csv)
            line_count += 1
    print('Processed {} lines.'.format(line_count))
    return coords_from_csv


def get_peaks():
    '''Function get_peaks
    '''
    with open(WAYMARKS_CSV) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        peaks_from_csv = {}
        for csv_row in csv_reader:
            peaks_from_csv[csv_row[0].strip()] = {
                'latitude': csv_row[1].strip(),
                'longitude': csv_row[2].strip(),
                'elevation': csv_row[3].strip()}
        print(peaks_from_csv)
    return peaks_from_csv


def get_path_and_fileroot(file):
    '''Function get_path_and_fileroot
    '''
    input_abs = os.path.abspath(file)
    print(input_abs)
    input_root_path = os.path.dirname(input_abs)
    print(input_root_path)
    return input_root_path


def git_branch_and_sha():
    '''Function git_branch_and_sha
    '''
    repo = git.Repo('..')
    branch = repo.active_branch.name
    sha = repo.head.object.hexsha
    short_sha = repo.git.rev_parse(sha, short=7)
    return branch, short_sha


print('STEP: Read peaks')
PEAKS = get_peaks()

DIR_LIST = next(os.walk(PATH_ROUTES))[1]
print(DIR_LIST)

ALL_ROUTES = []
NEW_ROUTE = {}

for next_dir in DIR_LIST:

    input_csv = PATH_ROUTES + next_dir + '/latlong.csv'

    print(input_csv)
    input_root = get_path_and_fileroot(input_csv)

    config = configparser.ConfigParser()
    config.read(input_root + '/route.data')
    print(config.sections())

    NEW_ROUTE['reference'] = config['route']['reference']
    NEW_ROUTE['title'] = config['route']['title']

    coords = get_coords(input_csv)

    query_string = ''
    first_line = 1
    for coord in coords:
        if first_line == 1:
            query_string += coord['latitude'] + ',' + coord['longitude']
            first_line = 0
        else:
            query_string += '|' + coord['latitude'] + ',' + coord['longitude']

    if DEBUG:
        print(query_string)

    print('STEP: Read co-ordinates')

    parameters = {'locations': query_string}

    if DEBUG:
        print(requests.certs.where())

    success = False

    while not success:
        try:
            r = requests.get('https://api.open-elevation.com/api/v1/lookup',
                             params=parameters)
            if DEBUG:
                print(r.url)
                print(r.status_code)
            if r.status_code == 200:
                if DEBUG:
                    print(r.text)
                data = json.loads(r.text)
                success = True
        except requests.exceptions.RequestException as ereq:
            if DEBUG:
                print('Ooops exception')
                print(ereq)

    print("STEP: Data retrieved")

    print(data['results'])

    gpx = ET.Element("gpx", version="1.1", creator="Manual")

    # Add waymarks
    wptstart = ET.SubElement(gpx, "wpt",
                             lat=str(data['results'][0]['latitude']),
                             lon=str(data['results'][0]['longitude']))
    ET.SubElement(wptstart, 'name').text = 'Start'

    wptfinish = ET.SubElement(gpx, "wpt",
                              lat=str(data['results'][-1]['latitude']),
                              lon=str(data['results'][-1]['longitude']))
    ET.SubElement(wptfinish, 'name').text = 'Finish'

    for peak in config['route']['peaks'].split(','):
        print(peak.strip())
        wpt = ET.SubElement(gpx, "wpt", lat=PEAKS[peak.strip()]['latitude'],
                            lon=PEAKS[peak.strip()]['longitude'])
        ET.SubElement(wpt, 'name').text = peak.strip()
        ET.SubElement(wpt, 'desc').text = ('Elevation: '
                                           + PEAKS[peak.strip()]['elevation']
                                           + 'm')

    # Add route
    rte = ET.SubElement(gpx, "rte")
    ET.SubElement(rte, 'name').text = NEW_ROUTE['reference']
    ET.SubElement(rte, 'desc').text = NEW_ROUTE['title']

    for point in data['results']:
        ET.SubElement(rte, "rtept", lat=str(point['latitude']),
                      lon=str(point['longitude']), ele=str(point['elevation']))

    tree = ET.ElementTree(gpx)
    tree.write(HTML_PATH + NEW_ROUTE['reference'] + '.gpx',
               encoding='utf-8', xml_declaration=True)

    print("STEP: GPX file created")

    ALL_ROUTES.append(NEW_ROUTE)
    print(ALL_ROUTES)

    routefile = open(HTML_PATH + NEW_ROUTE['reference'] + '.html', 'w')
    for line in fileinput.FileInput(ROUTE_HTML_TEMPLATE):
        routefile.write(line)
        if "<!--INSERT-HEADER-HERE-->" in line:
            print(line)
            with open(HTML_HEADER) as infile:
                routefile.write(infile.read())
        elif "INSERT-DATE-HERE" in line:
            print(line)
            time = str(datetime.utcnow()).split('.')[0]
            routefile.write('    "{}"+\n'.format(time))
        elif "INSERT-TITLE-HERE" in line:
            print(line)
            title = config['route']['reference'] + ": " + config['route']['title']
            routefile.write('    "{}"+\n'.format(title))
        elif "INSERT-MAINBODY-HERE" in line:
            print(line)
            for newline in config['route']['description'].split('\n'):
                 routefile.write('    "{}"+\n'.format(newline))
        elif "INSERT-VERSION-HERE" in line:
            print(line)
            git_branch, git_sha = git_branch_and_sha()
            version = semver.format_version(MAJOR, MINOR,
                                            PATCH, git_branch, git_sha)
            print(version)
            routefile.write('    "{}"+\n'.format(version))
        elif "INSERT-MAP-URL-HERE" in line:
            print(line)
            routefile.write('    "{}"+\n'.format(config['resources']['map']))
        elif "INSERT-INFO-PEAKS-HERE" in line:
            print(line)
            peaks = ""
            for peak in config['route']['peaks'].split(','):
                print(peak.strip())
                peaks += peak + " (" + PEAKS[peak.strip()]['elevation'] + "m), "
            print(peaks)
            routefile.write('    "{}"+\n'.format(peaks[:-2]))
        elif "INSERT-INFO-START-HERE" in line:
            print(line)
            start = config['route']['start']
            routefile.write('    "{}"+\n'.format(start))
        elif "INSERT-INFO-DISTANCE-HERE" in line:
            print(line)
            dist = config['resources']['distance']
            routefile.write('    "{}"+\n'.format(dist))

        elif "INSERT-INFO-GPX-HERE" in line:
            print(line)
            gpx = config['route']['reference'] + '.gpx'
            routefile.write('    "<a href=./{}>{}</a>"+\n'.format(gpx,gpx))

OUTFILE = open(TOP_HTML_NAME, 'w')
for line in fileinput.FileInput(TOP_HTML_TEMPLATE):
    OUTFILE.write(line)
    if "<!--INSERT-HEADER-HERE-->" in line:
        print(line)
        with open(HTML_HEADER) as infile:
            OUTFILE.write(infile.read())
    elif "<!--INSERT-ROUTE-LINKS-HERE-->" in line:
        print(line)
        for route in ALL_ROUTES:
            OUTFILE.write('<a href=' + route['reference'] + '.html >'
                          + route['reference'] + ': ' + route['title']
                          + '</a>')
    elif "INSERT-DATE-HERE" in line:
        print(line)
        time = str(datetime.utcnow()).split('.')[0]
        OUTFILE.write('    "{}"+\n'.format(time))
    elif "INSERT-VERSION-HERE" in line:
        print(line)
        git_branch, git_sha = git_branch_and_sha()
        version = semver.format_version(MAJOR, MINOR,
                                        PATCH, git_branch, git_sha)
        print(version)
        OUTFILE.write('    "{}"+\n'.format(version))
