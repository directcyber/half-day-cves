# CVE Half-Day Watcher dashboard

This is a fork of Aqua-Nautilus/CVE-Half-Day-Watcher that runs periodically and caches the results in JSON for programmatic access, as well as generates a web dashboard via Github Pages.

## Overview

CVE Half-Day Watcher is a security tool designed to highlight the risk of early exposure of Common Vulnerabilities and Exposures (CVEs) in the public domain. It leverages the National Vulnerability Database (NVD) API to identify recently published CVEs with GitHub references before an official patch is released. By doing so, CVE Half-Day Watcher aims to underscore the window of opportunity for attackers to "harvest" this information and develop exploits.
This tool is a proof of concept, ready to be built upon and extended.

## What is a "Half-Day" Vulnerability?
*  A vulnerability that is known to the party or parties responsible for patching or fixing it. 
Alarmingly, this vulnerability is exposed on some public platforms such as GitHub commit/PR/issue, NVD, etc. 
A patch may have been created in the open-source, but the official release is not yet available.

* What is the risk? These kinds of vulnerabilities may be exposed on public platforms (such as NVD, GitHub, etc.), making it possible for attackers to harvest them, locate the vulnerable code, and even write an exploit.
An example: imagine a case where there is an open issue on GitHub about “unwanted” behavior, and a commit that fixes the vulnerable code exists and refers to the issue, but the latest release on the GitHub project does not include the commit that resolves the issue.

![Log4Shell_Timeline.png](/misc/Log4Shell_Timeline.png)
More information can be found on our [blog](https://blog.aquasec.com/50-shades-of-vulnerabilities-uncovering-flaws-in-open-source-vulnerability-disclosures)

## How It Works

CVE Half-Day Watcher scans the NVD for newly pushed CVEs and checks for any GitHub references such as commits, pull requests (PRs), or issues linked to these CVEs.
It then verifies if the commit/PR has been included in a release on GitHub (currently for issue it skips this check). If a release including the fix is not available, it flags the CVE to indicate a possible "half-day" vulnerability scenario, where the vulnerability is known but not yet patched.

## Installation

Before you begin, ensure you have Python installed on your system. Then, clone the repository and install the dependencies:

```bash
git clone https://github.com/Aqua-Nautilus/CVE-Half-Day-Watcher.git
cd CVE-Half-Day-Watcher
pip install -r requirements.txt
```

## Usage
To use CVE Half-Day Watcher, you will need a GitHub token (without permissions).

```bash
export GITHUB_TOKEN=your_github_token
python scan_nvd.py [--days DAYS] [--min_stars MIN_STARS]
```

* --days: The number of days to look back for CVEs (optional - default is 3).
* --min_stars: The minimum number of stars a repository should have to be considered (optional - default is 50).

An example of the results from November 2, 2023.
![5_half_day_2_x2.png](/misc/5_half_day_2_x2.png)

