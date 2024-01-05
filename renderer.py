#!/usr/bin/env python3

from jinja2 import Environment
import json
import datetime


def get_key(kv_item):
	d = kv_item[1]
	if 'published' in d:
		return d['published']
	else:
		return 0

def render(jsonblob):
	data = json.loads(open(jsonblob, 'r').read())
	data_sorted = {k: v for k, v in sorted(data.items(), key=get_key, reverse=True)} 
	# jinja2 rendering
	environment = Environment()
	template = environment.from_string(open("index.html.j2","r").read())
	html = template.render(data=data_sorted, updated=datetime.datetime.utcnow().isoformat())
	with open('index.html', 'w+') as f:
		f.write(html)
	print('rendered to index.html')

if __name__ == "__main__":
	render('half_day_cves.json')