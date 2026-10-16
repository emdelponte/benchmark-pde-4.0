"""Literature-informed target repair; fixed independently prespecified weather models."""
import os
os.environ.setdefault('MPLCONFIGDIR','/tmp/fhb-matplotlib')
from pathlib import Path
import json, warnings, xml.etree.ElementTree as ET
import numpy as np
import pandas as pd
import yaml
import statsmodels.api as sm
from scipy.special import logit
from scipy.stats import t
from sklearn.metrics import roc_auc_score, brier_score_loss, log_loss
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'outputs'; RAW=ROOT/'data/raw'
assert (ROOT/'analysis_plan.md').exists() and (ROOT/'analysis_plan_revisions.md').exists()
r=ET.parse(ROOT/'data/literature/shah2021.xml')
eq=''.join(r.find(".//disp-formula[@id='pcbi.1008831.e007']").itertext())
assert 'Si≥10' in eq, 'Verify the source equation before deriving target'
d=pd.read_parquet(RAW/'FHBVer2.parquet')
d['y']=(d.S>=10).astype(int)
dic={c['name']:c for c in yaml.safe_load((RAW/'FHBVer2DataDict.yaml').read_text())['tables'][0]['columns']}
w=[n for n,c in dic.items() if c['category']=='weather_derived']
d['profile']=pd.util.hash_pandas_object(d[w],index=False).astype(str)
profile_counts=d.groupby('profile').y.agg(['size','sum']); profile_counts['nonevents']=profile_counts['size']-profile_counts['sum']; profile_counts.to_csv(OUT/'target_profiles.csv')
pre_fit={'events':int(d.y.sum()),'nonevents':int((1-d.y).sum()),'profiles_with_events':int((profile_counts['sum']>0).sum()),'profiles_with_nonevents':int((profile_counts.nonevents>0).sum()),'mixed_profiles':int(((profile_counts['sum']>0)&(profile_counts.nonevents>0)).sum()),'years_with_events':int(d.groupby('year').y.sum().gt(0).sum()),'states_with_events':int(d.groupby('state',observed=True).y.sum().gt(0).sum())}
(OUT/'prefit_target_audit.json').write_text(json.dumps(pre_fit,indent=2))
SPECS={'intercept':[], 'moisture':['VPD.L635.CHD.1'],'moisture_temp':['VPD.L635.CHD.1','T.A.2'],'moisture_temp_quad':['VPD.L635.CHD.1','T.A.2','T.A.2^2'],'temp_earlier':['VPD.L635.CHD.1','T.A.1'],'temp_remote':['VPD.L635.CHD.1','T.A.3']}
failures=[]
def design(frame,name):
    X=pd.DataFrame({'intercept':np.ones(len(frame))},index=frame.index)
    for term in SPECS[name]:
        source=term.replace('^2',''); assert dic[source]['window_end_day']<0
        if source.startswith('VPD'): v=frame[source]/24
        else: v=(frame[source]-15)/5
        X[term]=v**2 if term.endswith('^2') else v
    assert X.shape[1]<=4
    return X.astype(float)
def fit(frame,name,weights=None,cluster=False):
    X=design(frame,name)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always')
        model=sm.GLM(frame.y,X,family=sm.families.Binomial(),freq_weights=weights)
        kw={'cov_type':'cluster','cov_kwds':{'groups':frame.year,'use_correction':True}} if cluster else {}
        out=model.fit(**kw)
        for z in caught: failures.append({'model':name,'message':str(z.message),'context':'cluster' if cluster else 'fit'})
    assert out.converged and np.isfinite(out.params).all(), f'Fit failed: {name}'
    return out
# Calibration-in-large intercept differs from intercept jointly estimated with slope.
def metrics(y,p,calibrate=True,joint=True):
    y=np.asarray(y); p=np.clip(np.asarray(p),1e-8,1-1e-8)
    out={'n':len(y),'events':int(y.sum()),'prevalence':float(y.mean()),'mean_prediction':float(p.mean()),'auc':float(roc_auc_score(y,p)) if len(np.unique(y))==2 else np.nan,'brier':float(brier_score_loss(y,p)),'log_loss':float(log_loss(y,p,labels=[0,1]))}
    if len(np.unique(y))<2 or not calibrate: return out
    lp=logit(p)
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always')
            large=sm.GLM(y,np.ones((len(y),1)),family=sm.families.Binomial(),offset=lp).fit()
            out['calibration_in_large']=float(large.params[0])
            if joint and np.std(lp)>1e-6:
                cal=sm.GLM(y,sm.add_constant(lp),family=sm.families.Binomial()).fit()
                if cal.converged: out.update(calibration_intercept=float(cal.params[0]),calibration_slope=float(cal.params[1]))
            for z in caught: failures.append({'model':'calibration','context':'diagnostic','message':str(z.message)})
    except Exception as e: failures.append({'model':'calibration','context':'diagnostic','message':repr(e)})
    return out
summaries=[]; group_metrics=[]; predictions=[]; coefficients=[]; delete_coefs=[]; influence=[]
for name in SPECS:
    ordinary=fit(d,name); robust=fit(d,name,cluster=True); ci=t.ppf(.975,d.year.nunique()-1)
    for term,coef,se in zip(robust.params.index,robust.params,robust.bse):
        coefficients.append(dict(model=name,term=term,beta=coef,se_cluster_year=se,lower=coef-ci*se,upper=coef+ci*se,odds_ratio=np.exp(coef),OR_lower=np.exp(coef-ci*se),OR_upper=np.exp(coef+ci*se)))
    inf=ordinary.get_influence().cooks_distance[0]
    for i in np.argsort(inf)[-10:]: influence.append(dict(model=name,id=int(d.iloc[i].id),cook=float(inf[i]),year=int(d.iloc[i].year),state=str(d.iloc[i].state)))
    for strategy in ['year','state','temporal']:
        if strategy!='year' and name not in ['intercept','moisture','moisture_temp']: continue
        p=pd.Series(np.nan,index=d.index)
        groups=sorted(d[strategy].unique()) if strategy!='temporal' else ['2009-2015']
        for g in groups:
            test=(d[strategy]==g) if strategy!='temporal' else (d.year>=2009)
            train=~test
            model=fit(d.loc[train],name); pred=model.predict(design(d.loc[test],name)); p.loc[test]=pred
            mm=metrics(d.loc[test].y,pred,calibrate=False)
            # Small-group calibration intentionally excluded; only pooled diagnostics.
            group_metrics.append(dict(model=name,strategy=strategy,group=str(g),train_n=int(train.sum()),train_events=int(d.loc[train].y.sum()),**{k:v for k,v in mm.items() if not k.startswith('calibration')}))
            if strategy=='year':
                for term,coef in model.params.items(): delete_coefs.append(dict(model=name,omitted_year=int(g),term=term,beta=coef))
        keep=p.notna(); summaries.append(dict(model=name,strategy=strategy,predictor_parameters=len(SPECS[name]),**metrics(d.loc[keep].y,p.loc[keep],joint=name!="intercept")))
        for i in d.index[keep]: predictions.append(dict(id=int(d.loc[i,'id']),year=int(d.loc[i,'year']),state=str(d.loc[i,'state']),resist=str(d.loc[i,'resist']),profile=str(d.loc[i,'profile']),y=int(d.loc[i,'y']),model=name,strategy=strategy,p=float(p.loc[i])))
pred=pd.DataFrame(predictions); pred.to_csv(OUT/'predictions.csv',index=False)
pd.DataFrame(summaries).to_csv(OUT/'performance.csv',index=False); pd.DataFrame(group_metrics).to_csv(OUT/'group_performance.csv',index=False)
pd.DataFrame(coefficients).to_csv(OUT/'coefficients.csv',index=False); pd.DataFrame(delete_coefs).to_csv(OUT/'year_deletion_coefficients.csv',index=False); pd.DataFrame(influence).to_csv(OUT/'top_influence.csv',index=False)
# Prespecified sensitivities, each refit entirely within held-out-year training data.
sens=[]
for name in ['moisture','moisture_temp']:
    for variant in ['remove_duplicates','profile_weighted']:
        frame=d.loc[~d[list(dic)].drop(columns='id').duplicated()].copy() if variant=='remove_duplicates' else d.copy()
        pp=pd.Series(np.nan,index=frame.index)
        for yr in sorted(frame.year.unique()):
            test=frame.year==yr; tr=frame.loc[~test]
            weights=None
            if variant=='profile_weighted':
                sizes=tr.profile.map(tr.profile.value_counts()); weights=1/sizes; weights=weights/weights.mean()
            ff=fit(tr,name,weights=weights); pp.loc[test]=ff.predict(design(frame.loc[test],name))
        sens.append(dict(model=name,variant=variant,**metrics(frame.y,pp)))
pd.DataFrame(sens).to_csv(OUT/'sensitivity_performance.csv',index=False)
# Fixed-prediction year-block bootstrap, paired differences; no feature/model refitting.
wide=pred.loc[pred.strategy=='year'].pivot(index='id',columns='model',values='p').loc[d.id]
y=d.y.to_numpy(); rng=np.random.default_rng(20261010); years=d.year.to_numpy(); levels=np.unique(years); groups=[np.flatnonzero(years==yr) for yr in levels]; draws={n:[] for n in SPECS}; differences=[]
for b in range(1000):
    idx=np.concatenate([groups[j] for j in rng.integers(0,len(groups),len(groups))])
    if np.unique(y[idx]).size<2: continue
    for name in SPECS:
        pp=wide[name].to_numpy()[idx]; draws[name].append([roc_auc_score(y[idx],pp),np.mean((y[idx]-pp)**2)])
    differences.append(np.mean((y[idx]-wide.moisture_temp.to_numpy()[idx])**2-(y[idx]-wide.moisture.to_numpy()[idx])**2))
boot=[]
for name,v in draws.items():
    a=np.array(v)
    for j,metric in enumerate(['auc','brier']): boot.append(dict(model=name,metric=metric,lower=np.quantile(a[:,j],.025),upper=np.quantile(a[:,j],.975),resamples=len(a)))
boot.append(dict(model='moisture_temp minus moisture',metric='paired_brier_difference',lower=np.quantile(differences,.025),upper=np.quantile(differences,.975),resamples=len(differences)))
pd.DataFrame(boot).to_csv(OUT/'bootstrap_intervals.csv',index=False)
# Group-balanced diagnostic scoring uses actual weather profiles only at evaluation.
group_bal=[]
for name in SPECS:
    weights=1/d.profile.map(d.profile.value_counts()); pp=wide[name].to_numpy()
    group_bal.append(dict(model=name,profile_balanced_brier=float(np.average((y-pp)**2,weights=weights)),profile_balanced_auc=float(roc_auc_score(y,pp,sample_weight=weights))))
pd.DataFrame(group_bal).to_csv(OUT/'profile_balanced_metrics.csv',index=False)
sub=[]
for name in ['moisture','moisture_temp']:
    for cls in d.resist.cat.categories:
        q=pred.loc[(pred.strategy=='year')&(pred.model==name)&(pred.resist==cls)]; sub.append(dict(model=name,resist=cls,**metrics(q.y,q.p)))
pd.DataFrame(sub).to_csv(OUT/'resistance_performance.csv',index=False)
bins=[]; fig,axes=plt.subplots(1,2,figsize=(10,4))
for ax,strategy in zip(axes,['year','state']):
    ax.plot([0,1],[0,1],'--',color='gray',lw=1)
    for name,col in [('moisture','#31688e'),('moisture_temp','#35b779')]:
        q=pred.loc[(pred.strategy==strategy)&(pred.model==name)].copy(); q['bin']=pd.cut(q.p,bins=np.linspace(0,1,6),include_lowest=True)
        z=q.groupby('bin',observed=True).agg(n=('y','size'),observed=('y','mean'),predicted=('p','mean'))
        ax.plot(z.predicted,z.observed,'o-',label=name,color=col)
        for _,row in z.iterrows(): ax.annotate(str(int(row.n)),(row.predicted,row.observed),fontsize=7)
        for k,row in z.iterrows(): bins.append(dict(model=name,strategy=strategy,bin=str(k),**row.to_dict()))
    ax.set(xlim=(0,1),ylim=(0,1),xlabel='Mean held-out probability',ylabel='Observed epidemic frequency',title=f'Leave-one-{strategy}-out; labels = bin n'); ax.legend(fontsize=8)
fig.tight_layout(); fig.savefig(OUT/'calibration.png',dpi=180); plt.close(fig); pd.DataFrame(bins).to_csv(OUT/'calibration_bins.csv',index=False)
(OUT/'model_warnings.json').write_text(json.dumps(failures,indent=2))
(OUT/'fitted_model.json').write_text(json.dumps({'target':'S >= 10 percent','phase':'literature-informed continuation','models':{name:{'terms':SPECS[name],'coefficients':fit(d,name).params.to_dict()} for name in ['moisture','moisture_temp']},'scaling':{'VPD.L635.CHD.1':'hours / 24','T.A.2':'(degC - 15) / 5'},'timing':'all source windows end strictly before day 0; YAML closed intervals'},indent=2))
print(pd.DataFrame(summaries).to_string(index=False)); print('Prefit:',pre_fit); print('Warning count:',len(failures)); print(pd.DataFrame(boot).to_string(index=False)); print(pd.DataFrame(sens).to_string(index=False))
