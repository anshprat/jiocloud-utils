#!/usr/bin/env python
import jenkins
import subprocess
import time
import sys


def p(s):
    print s
    sys.stdout.flush()

p('Getting list of running jobs')
##
# The regex needs to be in raw string as \ collides w/ python usage
# From https://docs.python.org/2/library/re.html#module-re
#
# Regular expressions use the backslash character ('\') to indicate special
# forms or to allow special characters to be used without invoking their
# special meaning. This collides with Pythons usage of the same character
# for the same purpose in string literals
#
# The solution is to use Pythons raw string notation for regular expression
# patterns
##

cmd = r'nova list --fields name | grep puppet-rjil-gate |sed "s/.*_[a-zA-Z0-9]*-\([a-zA-Z0-9\-]*\).*/\1/" | sort| uniq -c'
proc = subprocess.Popen(cmd, shell=True,
                        stdout=subprocess.PIPE)
stdout, _stderr = proc.communicate()

##
# Because of the uniq -c, it always becomes exit 0 from subprocess
# Hence checking stdout length instead for determining if we have useful output
##
if len(stdout) is 0:
    exit(1)

jobs = {}
job_builds = {'gate':'puppet-rjil-gate',
              'overcloud':'puppet-rjil-gate-overcloud',
              'undercloud':'puppet-rjil-gate-undercloud'
              }
fp = open('running.html', 'w')

for l in stdout.split('\n'):
    l = l.strip()
    if not l:
        continue
    count, job = l.split(' ')
    job_number = '-'.join(job.split('-')[-2:])
    jobs[job_number] = int(count)

jenkins = jenkins.Jenkins(url='http://jiocloud.rustedhalo.com:8080')

now = time.time()
fp.write('''
<table>
  <thead>
    <tr>
        <td colspan="4" align="center"><a href="https://docs.google.com/spreadsheets/d/1V75IDtU8GWH2sX5G0dKQDH6K2RX5RZaoJQX0MoIEW4g/edit#gid=0"><b>Builds Reservation Sheet</b></a></td>
    </tr>
    <tr>
      <th>Build number</th>
      <th>Who triggered it?</th>
      <th>What's it for?</th>
      <th>How many minutes has it been running for?</th>
      <th>How much has it cost us so far?</th>
      <th>Terminate</th>
    </tr>
  </thead>
  <tbody>''')

for job in jobs:
    p('Getting info for job %s' % (job,))
    build = jenkins.get_build_info(job_builds[job.split('-')[-2]], int(job.split('-')[-1]))
    params = dict([(x['name'], x['value']) for x in build['actions'][0]['parameters']])
    running_for = (now-(build['timestamp']/1000))/60
    if "undercloud" in job:
        job_name = "undercloud-"
    else:
        job_name = ""
    if "overcloud" in job:
        job_id_del = job
    else:
        job_id_del = job.split('-')[-1]
    fp.write('''
    <tr>
      <td><a href="%s">%s</a></td>
      <td>%s</td>
      <td>%s</td>
      <td>%s</td>
      <td>$%.2f</td>
      <td><a href="http://jiocloud.rustedhalo.com:8080/job/puppet-rjil-gate-%sdelete/buildWithParameters?jobid=%s">Terminate</a></td>
    </tr>
''' % (build['url'], job, params['ghprbTriggerAuthor'], build['description'], running_for, (running_for/60)*1.17, job_name, job_id_del))

fp.write('''
  </tbody>
</table>''')
fp.close()
