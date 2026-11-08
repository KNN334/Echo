"""Dispatch and inspect repository Actions using existing credentials, without logging secrets."""
import argparse
import json
import re
import subprocess
import urllib.request


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--repository',default='KNN334/Echo')
    p.add_argument('--workflow',default='camus-dataset.yml')
    p.add_argument('--dispatch',action='store_true')
    p.add_argument('--release',action='store_true')
    a=p.parse_args()
    if not re.fullmatch(r'[\w.-]+/[\w.-]+',a.repository):raise ValueError('invalid repository')
    c=subprocess.run(['git','-c','credential.interactive=never','credential','fill'],
           input='protocol=https\nhost=github.com\n\n',text=True,capture_output=True,check=True)
    values=dict(x.split('=',1) for x in c.stdout.splitlines() if '=' in x)
    token=values.get('password')
    if not token:raise RuntimeError('No credential available')
    def api(path,data=None):
        req=urllib.request.Request('https://api.github.com/repos/'+a.repository+path,
                data=json.dumps(data).encode() if data is not None else None,
                headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json',
                         'Content-Type':'application/json','User-Agent':'Echo-workflow-monitor'})
        with urllib.request.urlopen(req,timeout=60) as r:
            content=r.read()
            return json.loads(content) if content else {}
    if a.dispatch:
        api('/actions/workflows/'+a.workflow+'/dispatches',{'ref':'main'})
        print('Workflow dispatched: '+a.workflow)
    result=api('/actions/workflows/'+a.workflow+'/runs?per_page=3')
    runs=[]
    for r in result['workflow_runs']:
        row={k:r.get(k) for k in ('id','status','conclusion','html_url','head_sha','created_at')}
        jobs=api(f"/actions/runs/{r['id']}/jobs")
        row['jobs']=[{'name':j['name'],'status':j['status'],'conclusion':j['conclusion'],
                      'steps':[{'name':s['name'],'status':s['status'],'conclusion':s['conclusion']} for s in j.get('steps',[])]}
                     for j in jobs['jobs']]
        runs.append(row)
    print(json.dumps(runs,indent=2))
    if a.release:
        release=api('/releases/tags/camus-data-20261108')
        print(json.dumps({'tag':release['tag_name'],'url':release['html_url'],
                          'assets':[{k:x.get(k) for k in ('name','size','browser_download_url')} for x in release['assets']]},indent=2))


if __name__=='__main__':main()
