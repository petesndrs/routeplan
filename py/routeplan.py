import requests
import csv
import json
import xml.etree.cElementTree as ET

debug = True

query_string = ''
with open('../routes/route1/route1.ll') as csv_file:
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
tree.write("filename.gpx", encoding='utf-8', xml_declaration=True)

print("STEP: GPX file created") 


