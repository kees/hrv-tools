#!/usr/bin/env python2
import xlwt, json, sys
from datetime import datetime

style_bold = xlwt.easyxf('font: name Arial, bold on')
style_date = xlwt.easyxf(num_format_str='YYYY-MM-DD')

wb = xlwt.Workbook()
ws = wb.add_sheet('Measurements')

elitehrv = json.load(open(sys.argv[1]))
# Load an optional "events.txt" file containing date-indexed line of
# text to include in the "Events" column:
#   2015-07-10  Upped Crossfit from 2x/week to 3x/week
if len(sys.argv) > 2:
    events = dict(line.strip().split(None, 1) for line in open(sys.argv[2]))
else:
    events = dict()

col = 0
ws.write(0, col, "Date", style_bold); col += 1
ws.write(0, col, "Systolic", style_bold); col += 1
ws.write(0, col, "Diastolic", style_bold); col += 1
ws.write(0, col, "BP", style_bold); col += 1
ws.write(0, col, "Pulse", style_bold); col += 1
ws.write(0, col, "Weight", style_bold); col += 1
ws.write(0, col, "BMI", style_bold); col += 1
ws.write(0, col, "HRV score", style_bold); col += 1
ws.write(0, col, "HRV Pulse", style_bold); col += 1
ws.write(0, col, "Events", style_bold); col += 1

bp_data = []
weight_data = []
row = 1
for entry in elitehrv['readings']:
    date = entry['datetime'].split(' ')[0]
    hrv_hr = entry['hr']
    hrv_score = entry['score']
    notes = entry['notes']
    tags = entry['tags']

    # Extract BP and Weight lines from Notes.
    if notes and '\n' in notes:
        bp, weight = notes.split('\n')[0:2]
        if '/' in weight:
            weight = weight.replace('/','@')
    else:
        bp = notes
        weight = None

    # Extract BMI from weight notes line
    if weight and '@' in weight:
        weight, bmi = weight.split('@')
    else:
        bmi = None

    # Extract HR from BP notes line
    if bp and '@' in bp:
        bp, hr = bp.split('@')
    else:
        print("Warning: reading %s missing BP HR" % (date))
        hr = hrv_hr

    if bp and '/' in bp:
        systolic, diastolic = bp.split('/')

    # Skip notes-less readings
    if not bp:
        continue

    try:
        bp_data.append([ date, int(systolic), int(diastolic), int(hr) ])
    except:
        print(systolic, diastolic, hr)
    if weight:
        weight_data.append([ date, float(weight) ])

    #print(date, bp, hr, weight, bmi, hrv_score, hrv_hr)

    col = 0
    ws.write(row, col, date, style_date); col += 1
    ws.write(row, col, systolic); col += 1
    ws.write(row, col, diastolic); col += 1
    ws.write(row, col, xlwt.Formula('CONCATENATE(%c%d,"/",%c%d)' % (
                                        chr(ord('A') + (col - 2)),
                                        row + 1,
                                        chr(ord('A') + (col - 1)),
                                        row + 1))); col += 1
    ws.write(row, col, hr); col += 1
    ws.write(row, col, weight); col += 1
    ws.write(row, col, bmi); col += 1
    ws.write(row, col, hrv_score); col += 1
    ws.write(row, col, hrv_hr); col += 1
    if date in events:
        ws.write(row, col, events[date]); col += 1
    elif tags:
        ws.write(row, col, tags); col += 1

    row += 1

wb.save('hrv.xls')
sys.exit(0)

from pychart import *

theme.output_format = 'png'
theme.output_file = 'hrv.png'
theme.reinitialize()

can = canvas.default_canvas()
size = (640, 480)
ar = area.T(size = size, y_range = (0, None),
            x_axis = axis.X(format="%s", label="Date"),
            y_axis = axis.Y(format="%d", label="Pressure"))
print(bp_data)
ar.add_plot(line_plot.T(label="Systolic", data=bp_data, ycol=1),
            line_plot.T(label="Diastolic", data=bp_data, ycol=2))
ar.draw()

