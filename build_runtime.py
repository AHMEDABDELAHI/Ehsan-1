"""Build public runtime dependencies only. No company data or application source."""
import hashlib, json, os, pathlib, subprocess, sys, urllib.request, zipfile
R=pathlib.Path('output').resolve(); P=R/'runtime'/'python'; P.mkdir(parents=True,exist_ok=True)
url='https://www.python.org/ftp/python/3.13.15/python-3.13.15-embed-amd64.zip'
expected='d1f04d990aee1253d8569e8e5104e30fa9f5fa830899f14843448872d936a2cf'
raw=urllib.request.urlopen(url,timeout=90).read()
assert hashlib.sha256(raw).hexdigest()==expected,'Python download hash mismatch'
pathlib.Path('python_embed.zip').write_bytes(raw)
with zipfile.ZipFile('python_embed.zip') as z:z.extractall(P)
(P/'python313._pth').write_text('python313.zip\n.\nLib/site-packages\n../../app\nimport site\n',encoding='ascii')
deps=['fastapi==0.128.2','uvicorn==0.48.0','python-multipart==0.0.29','openpyxl==3.1.5','defusedxml==0.7.1','httpx==0.28.1','playwright==1.57.0','python-calamine==0.6.1','pydantic==2.13.4','starlette==0.50.0']
subprocess.run([sys.executable,'-m','pip','install','--disable-pip-version-check','--only-binary=:all:','--target',str(P/'Lib/site-packages'),*deps],check=True)
env=dict(os.environ);env['PLAYWRIGHT_BROWSERS_PATH']=str(R/'runtime'/'browsers')
exe=str(P/'python.exe')
subprocess.run([exe,'-m','playwright','install','--no-shell','chromium'],env=env,check=True)
smoke='''import io,json,os,pathlib,platform,sqlite3,ssl,sys,tempfile
import fastapi,uvicorn,multipart,openpyxl,defusedxml,httpx,pydantic,python_calamine
from importlib.metadata import version
from fastapi.testclient import TestClient
from playwright.sync_api import sync_playwright
root=pathlib.Path(sys.argv[1]); result={'platform':platform.platform(),'python':sys.version,'isolation':sys.flags.isolated,'checks':[]}
assert sys.flags.isolated==1
conn=sqlite3.connect(':memory:');assert conn.execute('pragma integrity_check').fetchone()[0]=='ok';conn.close();result['checks'].append('SQLite integrity')
a=fastapi.FastAPI()
@a.get('/health')
def health():return {'ok':True}
assert TestClient(a).get('/health').json()['ok'];result['checks'].append('FastAPI local request')
w=openpyxl.Workbook();w.active.append(['account','debit','credit']);w.active.append(['412100',125,0]);stream=io.BytesIO();w.save(stream)
assert openpyxl.load_workbook(io.BytesIO(stream.getvalue())).active['B2'].value==125
cw=python_calamine.CalamineWorkbook.from_filelike(io.BytesIO(stream.getvalue()));assert cw.get_sheet_by_index(0).to_python()[1][1]==125
result['checks'].append('XLSX two readers')
with sync_playwright() as p:
 b=p.chromium.launch(executable_path=p.chromium.executable_path,headless=True);c=b.new_context();c.route('**/*',lambda r:r.abort());page=c.new_page();page.set_content('<html lang="ar" dir="rtl"><meta charset="utf-8"><h1>اختبار طباعة محلي</h1><table><tr><td>المبلغ</td><td>125.00</td></tr></table></html>');pdf=page.pdf();assert pdf.startswith(b'%PDF-') and len(pdf)>1000;b.close()
result['checks'].append('Bundled Chromium PDF with all page network requests blocked')
result['versions']={x:version(x) for x in ['fastapi','uvicorn','python-multipart','openpyxl','defusedxml','httpx','playwright','python-calamine','pydantic','starlette']}
result['limitations']=['Dependency smoke test on Windows Server 2022 runner, not complete AquaFin app UAT or father device.','OS network not disabled; application page routes blocked in PDF smoke.']
(root/'runtime_native_smoke.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps(result,ensure_ascii=True))
'''
pathlib.Path('runtime_smoke.py').write_text(smoke,encoding='utf-8')
subprocess.run([exe,str(pathlib.Path('runtime_smoke.py').resolve()),str(R)],env=env,check=True)
for f in list(R.rglob('*.pyc')):f.unlink()
files={str(f.relative_to(R)).replace('\\','/'):{'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size} for f in R.rglob('*') if f.is_file()}
(R/'runtime_manifest.json').write_text(json.dumps({'purpose':'Redistributable components only; no company data','python_url':url,'python_sha256':expected,'requirements':deps,'files':files},indent=2),encoding='utf-8')
print('COMPONENT RUNTIME READY',len(files),sum(x['bytes'] for x in files.values()))
