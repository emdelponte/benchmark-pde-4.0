"""Structural audit only. Does not derive an undocumented epidemic response or fit models."""
import os
os.environ.setdefault('MPLCONFIGDIR', '/tmp/fhb-matplotlib')
import hashlib, json, platform, re
from pathlib import Path
from html.parser import HTMLParser
import importlib.metadata as im
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import yaml
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT = Path(__file__).resolve().parents[1]
RAW, OUT = ROOT/'data/raw', ROOT/'outputs'
OUT.mkdir(exist_ok=True)
d = pd.read_parquet(RAW/'FHBVer2.parquet')
y = yaml.safe_load((RAW/'FHBVer2DataDict.yaml').read_text())
cols = y['tables'][0]['columns']; dic = {c['name']: c for c in cols}
meta = pd.read_csv(RAW/'VariablesMetaData.csv')
w = [c['name'] for c in cols if c['category']=='weather_derived']
pre = [n for n in w if dic[n]['window_end_day']<0 and not dic[n].get('deprecated',False)]
checks=[]
for n in d:
    c=dic[n]; s=d[n]; non=s.dropna(); issues=[]
    if not np.isclose(s.isna().mean()*100, c['missing_pct'], atol=0.055): issues.append('missing_pct differs')
    if c['type']=='integer' and not np.all(np.equal(non.astype(float)%1,0)): issues.append('noninteger values')
    if c['type']=='factor' and set(non.astype(str)) != set(c.get('levels',[])): issues.append('level mismatch')
    if pd.api.types.is_numeric_dtype(s):
        for key in ['range','valid_range']:
            bounds=c.get(key,{})
            for endpoint,fun in [('min',min),('max',max)]:
                if endpoint in bounds:
                    val=fun(non)
                    if key=='range' and not np.isclose(val,bounds[endpoint],rtol=1e-6,atol=1e-6): issues.append(f'{key}.{endpoint} differs')
                    if key=='valid_range' and ((endpoint=='min' and val<bounds[endpoint]-1e-6) or (endpoint=='max' and val>bounds[endpoint]+1e-6)): issues.append(f'{key}.{endpoint} violated')
    if 'identical_to' in c and not s.equals(d[c['identical_to']]): issues.append('identical_to differs')
    checks.append(dict(name=n,arrow_type=str(pq.read_schema(RAW/'FHBVer2.parquet').field(n).type),documented_type=c['type'],unit=c.get('unit',''),missing=int(s.isna().sum()),observed_min=str(non.astype(str).min() if c['type']=='factor' else non.min()),observed_max=str(non.astype(str).max() if c['type']=='factor' else non.max()),issues='; '.join(issues),category=c['category']))
pd.DataFrame(checks).to_csv(OUT/'schema_audit.csv',index=False)
pd.DataFrame(cols).drop(columns=['same_condition_as','same_window_as'],errors='ignore').to_csv(OUT/'dictionary_flat.csv',index=False)
windows=[]
for n in w:
    c=dic[n]; a=c['window_start_day']; b=c['window_end_day']
    row=dict(name=n,start=a,end=b,period=c['analysis_period'],unit=c.get('unit',''),deprecated=c.get('deprecated',False),available_00UTC=b<0,closed_days=b-a+1)
    if n in set(meta.variable_name):
        m=meta.loc[meta.variable_name==n].iloc[0]; row['csv_win_length']=int(m.win_length); row['csv_length_differs_closed']=int(m.win_length)!=b-a+1
    windows.append(row)
pd.DataFrame(windows).to_csv(OUT/'window_audit.csv',index=False)
cor=d[pre].corr(); cor.to_csv(OUT/'strict_pre_correlations.csv')
pairs=[]
for i,n in enumerate(pre):
    for m in pre[i+1:]: pairs.append(dict(a=n,b=m,r=float(cor.loc[n,m])))
pd.DataFrame(pairs).assign(abs_r=lambda z:z.r.abs()).sort_values('abs_r',ascending=False).to_csv(OUT/'correlation_pairs.csv',index=False)
# These are conservative dependency proxies, never claimed to be actual trial IDs.
d['state_year']=d.state.astype(str)+'_'+d.year.astype(str)
d['state_date']=d.state.astype(str)+'_'+d.fdate.astype(str)
d['weather_profile']=pd.util.hash_pandas_object(d[w],index=False).astype(str)
def group_table(k):
    t=d.groupby(k,observed=True).agg(n=('S','size'),mean_severity=('S','mean'),median_severity=('S','median'),zero_severity=('S',lambda z:(z==0).sum()))
    t.to_csv(OUT/f'by_{k}.csv'); return t
for k in ['year','state','resist','type','state_year','state_date','weather_profile']: group_table(k)
d.groupby(['state','year'],observed=True).size().unstack(fill_value=0).to_csv(OUT/'state_year_counts.csv')
dup_numeric=[]
for i,n in enumerate(w):
    for m in w[i+1:]:
        if d[n].equals(d[m]): dup_numeric.append((n,m))
pd.DataFrame(dup_numeric,columns=['a','b']).to_csv(OUT/'identical_weather_pairs.csv',index=False)
# Record row-level extremes, without removing scientifically possible observations.
z=(d[pre]-d[pre].mean())/d[pre].std()
ext=pd.DataFrame({'id':d.id,'state':d.state,'year':d.year,'S':d.S,'max_abs_z':z.abs().max(axis=1)})
ext.sort_values('max_abs_z',ascending=False).to_csv(OUT/'extreme_rows.csv',index=False)
class TextParser(HTMLParser):
    def __init__(self): super().__init__(); self.parts=[]; self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag in ('script','style'): self.skip+=1
    def handle_endtag(self,tag):
        if tag in ('script','style'): self.skip=max(0,self.skip-1)
    def handle_data(self,data):
        if not self.skip and data.strip(): self.parts.append(data.strip())
if (RAW/'FHBVer2Codebook.html').exists():
    p=TextParser(); p.feed((RAW/'FHBVer2Codebook.html').read_text()); text='\n'.join(p.parts); (OUT/'codebook_text.txt').write_text(text)
    (OUT/'codebook_outcome_search.txt').write_text('\n'.join(line for line in text.splitlines() if re.search(r'epidem|binary|severity|index|threshold',line,re.I)))
record=json.loads((RAW/'record.json').read_text()); manifest=[]
for f in record['files']:
    p=RAW/f['key']
    if p.exists():
        checksum='md5:'+hashlib.md5(p.read_bytes()).hexdigest(); assert checksum==f['checksum'],p
        manifest.append(dict(file=p.name,bytes=p.stat().st_size,md5=checksum,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),source=f['links']['self']))
pd.DataFrame(manifest).to_csv(OUT/'manifest.csv',index=False)
# Cross-format check adds evidence that the response was not lost in conversion.
csv=pd.read_csv(RAW/'FHBVer2.csv')
nums=[n for n in w+['id','year','corn','S']]
csv_equal=all(np.allclose(d[n].astype(float),csv[n].astype(float),equal_nan=True,rtol=1e-10,atol=1e-10) for n in nums)
summary=dict(rows=len(d),columns=len(dic),weather_columns=len(w),responses=[c for c in cols if c['category']=='response'],schema_missing_in_yaml=sorted(set(d.columns[:337])-set(dic)),schema_missing_in_parquet=sorted(set(dic)-set(d.columns[:337])),year_min=int(d.year.min()),year_max=int(d.year.max()),years=int(d.year.nunique()),states=int(d.state.nunique()),missing=d.iloc[:,:337].isna().sum()[lambda a:a>0].to_dict(),S=d.S.describe().to_dict(),S_zero=int((d.S==0).sum()),weather_profiles=int(d.weather_profile.nunique()),state_years=int(d.state_year.nunique()),state_dates=int(d.state_date.nunique()),weather_profile_max_size=int(d.weather_profile.value_counts().max()),profile_singletons=int((d.weather_profile.value_counts()==1).sum()),profiles_with_multiple_rows=int((d.weather_profile.value_counts()>1).sum()),duplicate_rows_excluding_id=int(d.iloc[:,:337].drop(columns='id').duplicated().sum()),weather_effective_size_proxy=float(len(d)**2/(d.weather_profile.value_counts()**2).sum()),period_counts=pd.Series([dic[n]['analysis_period'] for n in w]).value_counts().to_dict(),pre_day0=sum(dic[n]['analysis_period']=='pre' and dic[n]['window_end_day']==0 for n in w),strict_pre=pre,metadata_only=sorted(set(meta.variable_name)-set(w)),weather_missing_csv_metadata=sorted(set(w)-set(meta.variable_name)),csv_numeric_equal=csv_equal,identical_weather_pairs=dup_numeric,schema_issue_columns=[r for r in checks if r['issues']],versions={p:im.version(p) for p in ['pandas','pyarrow','PyYAML','numpy','scipy','statsmodels','scikit-learn','matplotlib']},python=platform.python_version(),system=platform.platform())
(OUT/'audit_summary.json').write_text(json.dumps(summary,indent=2))
fig,ax=plt.subplots(1,2,figsize=(10,4)); ax[0].hist(d.S,bins=30,color='#31688e'); ax[0].set(xlabel='FHB index (%)',ylabel='Rows',title='Continuous outcome; no documented binary label'); counts=d.year.value_counts().sort_index(); ax[1].bar(counts.index,counts.values,color='#35b779'); ax[1].set(xlabel='Assessment year',ylabel='Rows',title='Uneven temporal representation'); fig.tight_layout(); fig.savefig(OUT/'severity_and_year.png',dpi=180); plt.close(fig)
fig,ax=plt.subplots(figsize=(8,5)); d.state.value_counts().sort_values().plot.barh(ax=ax,color='#31688e'); ax.set(xlabel='Rows',ylabel='State',title='Geographic representation'); fig.tight_layout(); fig.savefig(OUT/'states.png',dpi=180); plt.close(fig)
fig,ax=plt.subplots(figsize=(10,9)); imshow=ax.imshow(cor,vmin=-1,vmax=1,cmap='RdBu_r'); ax.set_xticks(range(len(pre)),pre,rotation=90,fontsize=6); ax.set_yticks(range(len(pre)),pre,fontsize=6); fig.colorbar(imshow,ax=ax,label='Pearson correlation'); ax.set_title('Strictly pre-anthesis predictors (outcome-blind audit)'); fig.tight_layout(); fig.savefig(OUT/'correlations.png',dpi=180); plt.close(fig)
print(json.dumps({k:v for k,v in summary.items() if k not in ['responses','strict_pre','identical_weather_pairs','schema_issue_columns']},indent=2))
print('Issues:',summary['schema_issue_columns'])
print('Top correlations:',pd.read_csv(OUT/'correlation_pairs.csv').head(10).to_string(index=False))
