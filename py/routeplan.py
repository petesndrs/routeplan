import os
import configparser
import fileinput
import requests
import csv
import json
import xml.etree.cElementTree as ET
import semver
from datetime import datetime
import git


def getPathAndFileroot(file):
    '''Function getPathAndFileroot
    '''
    input_abs = os.path.abspath(file)
    print(input_abs)
    input_root = os.path.dirname(input_abs)
    print(input_root)
    input_fileroot, _ = os.path.splitext(input_abs)
    print(input_fileroot)
    return input_root, input_fileroot


def gitBranchAndSha():
    '''Function gitBranchAndSha
    '''
    repo = git.Repo('..')
    branch = repo.active_branch.name
    sha = repo.head.object.hexsha
    short_sha = repo.git.rev_parse(sha, short=7)
    return branch, short_sha

MAJOR = 0
MINOR = 1
PATCH = 0

debug = True

path_routes = '../routes/'
top_html_template = '../docs_templates/edfr.template.html'
top_html_name = '../docs/EDFR.html'

dir_list = next(os.walk(path_routes))[1]
print(dir_list)

all_routes = []
new_route = {}

for dir in dir_list:

    input = path_routes + dir + '/route1.ll'

    print(input)
    input_root, input_fileroot = getPathAndFileroot(input)

    config = configparser.ConfigParser()
    config.read(input_fileroot+'.data')
    print(config.sections())

    new_route['reference'] = config['route']['reference']
    new_route['title'] = config['route']['title']

    query_string = ''
    with open(input) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        line_count = 0
        for row in csv_reader:
            r0=row[0].strip()
            r1=row[1].strip()
            if line_count == 0:
                query_string+=r0+','+r1
            else:
                query_string+='|'+r0+','+r1
            line_count += 1
            if debug:
                print('Latitude {} Longitude {}'.format(r0,r1))
      
        print('Processed {} lines.'.format(line_count))

    if debug:
        print(query_string)

    print('STEP: Read co-ordinates')

    parameters = {'locations': query_string }


    if debug:
        print(requests.certs.where())

    success = False

    while not success:
        try:
            r = requests.get('https://api.open-elevation.com/api/v1/lookup', params=parameters)
            if debug:
                print(r.url)
                print(r.status_code)
            if r.status_code == 200:
                if debug:
                    print(r.text)
                data = json.loads(r.text)
                success = True
        except requests.exceptions.RequestException as ereq:
            if debug:
                print('Ooops exception')
                print(ereq)

    print("STEP: Data retrieved")

    print(data['results'])

    for point in data['results']:
        print('{} {}'.format(point['latitude'], point['longitude']))

    gpx = ET.Element("gpx", version="1.1", creator="Manual")
    rte = ET.SubElement(gpx, "rte")

    for point in data['results']:
        ET.SubElement(rte, "rtept", lat=str(point['latitude']), lon=str(point['longitude']), ele=str(point['elevation']))

    tree = ET.ElementTree(gpx)
    tree.write(input_fileroot+'.gpx', encoding='utf-8', xml_declaration=True)

    print("STEP: GPX file created") 

    all_routes.append(new_route)
    print(all_routes)


outfile = open(top_html_name, 'w')
for line in fileinput.FileInput(top_html_template):
    outfile.write(line)
    if "<!--INSERT-ROUTE-LINKS-HERE-->" in line:
        print(line)
        for route in all_routes:
            outfile.write('<a href=' + route['reference'] + '.html >' + route['reference'] + ': ' + route['title'] + '</a>')
    if "INSERT-DATE-HERE" in line:
        time = str(datetime.utcnow()).split('.')[0]
        outfile.write('    "{}"+\n'.format(time))
    if "INSERT-VERSION-HERE" in line:
        git_branch, git_sha = gitBranchAndSha()
        version = semver.format_version(MAJOR, MINOR, PATCH, git_branch, git_sha)
        print(version)
        outfile.write('    "{}"+\n'.format(version))