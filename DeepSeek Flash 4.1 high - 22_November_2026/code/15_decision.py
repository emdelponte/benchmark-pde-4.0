import sys; sys.path.insert(0,'code'); import fhb_env
import numpy as np, pandas as pd, os
import fhb_env as env, fhb_model as fm, fhb_specs as fs
df, flat = fm.load(); v = fs.build_vars(flat); d = fs.design_frame(df, v)
d_cc = d.dropna(subset=['corn']).reset_index(drop=True)
rows=[]
for name in ['M1','M2','M5','M4']:
    data = d_cc if name=='M4' else d
    y = data['y'].values.astype(float); pred=np.full(len(data),np.nan)
    for yr in sorted(data['year'].unique()):
        te=(data['year']==yr).values; tr=~te
        pr,_,_,_ = fs.fit_predict(name, data[tr], data[te])
        pred[te]=pr
    for cut in (0.40,0.50,0.60):
        pos = pred>=cut
        tp=int((pos&(y==1)).sum()); fp=int((pos&(y==0)).sum())
        fn=int((~pos&(y==1)).sum()); tn=int((~pos&(y==0)).sum())
        sens=tp/(tp+fn) if tp+fn else np.nan
        spec=tn/(tn+fp) if tn+fp else np.nan
        ppv=tp/(tp+fp) if tp+fp else np.nan
        npv=tn/(tn+fn) if tn+fn else np.nan
        rows.append(dict(model=name, cutoff=cut, flagged=int(pos.sum()),
                         pct_flagged=round(pos.mean()*100,1), tp=tp,fp=fp,fn=fn,tn=tn,
                         sens=round(sens,3), spec=round(spec,3), ppv=round(ppv,3), npv=round(npv,3)))
    rows.append(dict(model=name, cutoff='range', flagged=np.nan, pct_flagged=np.nan,
                     sens=f"min pred {pred.min():.3f}", spec=f"max pred {pred.max():.3f}"))
t=pd.DataFrame(rows); t.to_csv(os.path.join(env.OUT,'decision_thresholds.csv'),index=False)
print(t.to_string(index=False))
