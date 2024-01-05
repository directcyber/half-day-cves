#!/usr/bin/env python3
import argparse
import requests
import github_api_request_handler as gh
import datetime
import json
import parse
import os
import sys

def run_GQ_query(query, variables=""): 
    req_headers = {"Authorization": f"Bearer {github_token}"}
    request = requests.post('https://api.github.com/graphql', json={'query': query, 'variables': variables}, headers=req_headers)
    if request.status_code == 200:
        return request.json()
    else:
        raise Exception("Query failed to run by returning code of {}. {}".format(request.status_code, query))

def get_nvd_data(days):
	"""
	This function retrieves from nvd the last {days} cves.
	"""
	now = datetime.datetime.utcnow()
	pub_start = now-datetime.timedelta(days)
	pub_end=now+datetime.timedelta(1) # we do this to the future 1 day to get everything until the request

	pub_start_str = pub_start.strftime("%Y-%m-%dT%H:%M:%S")
	pub_end_str = pub_end.strftime("%Y-%m-%dT%H:%M:%S")

	url=f"https://services.nvd.nist.gov/rest/json/cves/2.0/?pubStartDate={pub_start_str}&pubEndDate={pub_end_str}&resultsPerPage=2000"
	print(url)

	try:
		resp = requests.get(url)
		resp_json = resp.json()

		total_results=resp_json['totalResults']

		if total_results > 2000:
			print(f'there are {str(total_results)} results, we scanned only the first 2000')

		return resp_json['vulnerabilities']
	except:
		print('failed to fetch from nvd')
		return None

def get_repo_amount_of_stars(repo):
	resp = gh.get(f"https://api.github.com/repos/{repo}", github_token)
	if resp.status_code != 200:
		print(f"ERROR bad status code {resp.status_code}: {resp.text}", file=sys.stderr)
	resp_json = resp.json()
	return resp_json['stargazers_count']

def filter_url_by_github(reference):
	reference_lower = reference.lower()
	if "github.com" in reference_lower:
		if "/commit/" in reference_lower or "/pull/" in reference_lower or "/issues/" in reference_lower:
			return True

	return False

def get_date_of_latest_tag_of_repo_by_html(org,repo):
	resp=requests.get(f"https://github.com/{org}/{repo}/tags")
	resp_html = resp.text

	tag_search_string=f"relative-time datetime=\""

	index_of_date = resp_html.find(tag_search_string)

	if index_of_date == -1:
		print(f"get_date_of_latest_tag_of_repo({org},{repo}) failed, probably this repository does not have tags!! returned default value")
		return datetime.datetime.strptime("2023-05-12T11:29:06+03:00", '%Y-%m-%dT%H:%M:%S%z')

	index_of_date_end = resp_html.find('"',index_of_date+len(tag_search_string)) # this will give the index of the closing " of the date

	tag_str = resp_html[index_of_date+len(tag_search_string):index_of_date_end] # this will take the value of the date between the "

	return datetime.datetime.strptime(tag_str, '%Y-%m-%dT%H:%M:%S%z')


def commit_has_tag_in_gui(org, repo,commit):
	url=f'https://github.com/{org}/{repo}/branch_commits/{commit}'
	resp=requests.get(url)
	# here we check if there is a tag, any tag
	if "ul class=\"branches-tag-list" in resp.text:
		return True
	return False

# -2 there is not such pull request
# -1 the pull request is still open
def get_merge_date_of_pull(org, repo, pull_number):
	resp = gh.get(f"https://api.github.com/repos/{org}/{repo}/pulls/{pull_number}", github_token)
	if resp.status_code==404:
		return -2

	resp_json = resp.json()
	if resp_json['state']=='open' or resp_json['merged_at'] is None: # right now closed
		return -1

	return datetime.datetime.strptime(resp_json['merged_at'], '%Y-%m-%dT%H:%M:%S%z')


def check_pull_half_day(pull_url):
	format_string="https://github.com/{}/{}/pull/{}"
	parsed=parse.parse(format_string, pull_url.lower())
	org,repo,pull_number=parsed
	pull_number=pull_number.split("/")[0] # if there was a trailing /

	merged_date = get_merge_date_of_pull(org,repo,pull_number)
	if merged_date ==-1 or merged_date ==-2: # this means its open or pull doesnt exist which we will print anyway
		return True
	
	tag_date = get_date_of_latest_tag_of_repo_by_html(org,repo)
	if merged_date > tag_date: # meaning the PR is merged but there was no release yet
		return True

	return False

def get_pull_request_of_commit(org, repo, commit_hash):
	url = f"https://api.github.com/repos/{org}/{repo}/commits/{commit_hash}/pulls"
	resp=gh.get(url, github_token)
	resp_json = resp.json()
	
	# If the response is empty array it is not part of a pr
	if len(resp_json) == 0:
		return None
	
	return resp_json[0]['number']


def check_commit_half_day(commit_url):
	try:
		format_string="https://github.com/{}/{}/commit/{}"
		parsed=parse.parse(format_string, commit_url.lower())
		org,repo,commit_number=parsed
		commit_number=commit_number.split("/")[0] # if there was a trailing /
		commit_number=commit_number.replace(".","")

		# if there is a tag in gui meaning there was a release which means False to 0.5 day
		if commit_has_tag_in_gui(org,repo,commit_number):
			return False


		# Now we check if it is part of a PR, because we prefer to check PR for 0.5 day instead of a commit
		pull_number = get_pull_request_of_commit(org,repo,commit_number)
		if pull_number is not None:
			return check_pull_half_day(f"https://github.com/{org}/{repo}/pull/{pull_number}")

		# Here we have a commit without a tag in gui and is not part of a PR.
		# Now we check by latest tag of the repository (which is not hermetic because we dont know when it was pushed to GitHub)
		resp = gh.get(f"https://api.github.com/repos/{org}/{repo}/commits/{commit_number}", github_token)
		resp_json=resp.json()
		commit_date_str=resp_json['commit']['author']['date']

		commit_date = datetime.datetime.strptime(commit_date_str, '%Y-%m-%dT%H:%M:%S%z')
		tag_date = get_date_of_latest_tag_of_repo_by_html(org,repo)

		# If the commit is after the latest tag date we have 0.5 day
		return commit_date > tag_date
	except:
		return False


def check_issue_half_day(issue_url):
	# currently there is no implementation here because even if the issue is closed it does not mean there is a fix
	# maybe in the future check pull requests that resolve the issue, etc.
	return True


def iterate_nvd_cves_for_half_day(lastest_nvd_vulneraiblities, minimum_github_stars):

	results = {} # CVE: {detail dict}

	for cve in lastest_nvd_vulneraiblities:
		cve_has_github_data=False
		cve_has_github_commit=False
		cve_has_github_pull=False
		cve_is_half_day=False
		cve_data=cve['cve']
		cve_id = cve_data['id']
		cve_references = cve_data['references']

		current_year = datetime.datetime.utcnow().year
		# dont analyze cves that do not start with the current year
		if not cve_id.lower().startswith(f'cve-{current_year}'):
			continue

		for reference in cve_references:
			url = reference['url']

			if filter_url_by_github(url):
				cve_has_github_data=True
				
				if '/pull/' in url:
					cve_has_github_pull=True
					github_url = url
					break # we break here because PR is the best case to check about 0.5

				if '/commit/' in url: # no break here, because we want to keep checking maybe /pull/ will be in the future
					cve_has_github_commit=True
					github_url = url

				# we want to enter here only if there wasnt a commit/pull in any other of the references
				# we dont check cve_has_github_pull because it has the break so it wont ever reach here
				elif '/issues/' in url and not cve_has_github_commit: 
					github_url = url

		if cve_has_github_data: # There is github information on at least 1 of the references
			format_string="https://github.com/{}/{}/{}"
			github_url = github_url.lower().replace("www.github.com", "github.com")
			parsed=parse.parse(format_string, github_url)

			if parsed is None:
				print(f'error in {github_url}')
				continue

			org,repo,_ = parsed

			# if the repo has small amount of stars we skip this cve
			if get_repo_amount_of_stars(org+'/'+repo) < minimum_github_stars:
				continue
			
			if cve_has_github_pull:
				cve_is_half_day = check_pull_half_day(github_url)
			elif cve_has_github_commit:
				cve_is_half_day = check_commit_half_day(github_url)
			else: # currently for issue we state 0.5 day automatically
				cve_is_half_day = check_issue_half_day(github_url) 

			if cve_is_half_day:
				results[cve_id] = {"url": github_url}
				print(f'found a possible half_day on {cve_id} with the reference: {github_url}')

	return results

def main():
	global github_token

	results_filename = 'half_day_cves.json'

	parser = argparse.ArgumentParser(description="Scan nvd for potential half day vulnerabilities")

	# parser.add_argument("--github_token","-gh", help="GitHub token to use for the api, no permissions needed.", required=True)

	parser.add_argument("--days", "-d",default=3, type=int, help="How many days ago to scan the nvd for new CVEs. Default is 3.")

	parser.add_argument("--min_stars","-s", default=50, type=int, help="The minimum amount of GitHub stars to scan for half day.")

	# Parse the command-line arguments
	args = parser.parse_args()

	github_token = os.getenv("GITHUB_TOKEN")

	lastest_nvd_vulneraiblities = get_nvd_data(args.days)

	if lastest_nvd_vulneraiblities is not None:
		cve_urls_dict = iterate_nvd_cves_for_half_day(lastest_nvd_vulneraiblities, args.min_stars)
		if os.path.isfile(results_filename):
			with open(results_filename, 'r') as f:
				old_cves = set(json.load(f).keys())
				for cve in cve_urls_dict:
					if cve not in old_cves:
						cve_urls_dict[cve]['new'] = True
					else:
						cve_urls_dict[cve]['new'] = False
		with open(results_filename, 'w') as f:
			json.dump(cve_urls_dict, f)
			print(f"saved output to {results_filename}", file=sys.stderr)


if __name__ == '__main__':
	main()


