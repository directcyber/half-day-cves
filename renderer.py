#!/usr/bin/env python3

from jinja2 import Environment, FileSystemLoader
import json
import datetime


def render(jsonblob):
	data = json.loads(open(jsonblob, 'r').read())
	# jinja2 rendering
	environment = Environment()
	template = environment.from_string(open("index.html.j2","r").read())
	html = template.render(data=data, updated=datetime.datetime.utcnow().isoformat())
	with open('index.html', 'w+') as f:
		f.write(html)
	print('rendered to index.html')

if __name__ == "__main__":
	render('half_day_cves.json')