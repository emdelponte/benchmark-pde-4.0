"""Independent numerical checks of artifacts and grouped held-out fits."""
import hashlib,json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit
from sklearn.metrics import roc_auc_score,brier_score_loss
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'outputs'
x=pd.read_parquet(ROOT/'data/raw/FHBVer2.parquet'); y=(x.S>=10).astype(int).to_numpy()
assert (len(x),len(x.columns),int(y.sum()))==(999,337,273)
assert x.id.is_unique
manifest=pd.read_csv(OUT/'manifest.csv')
for row in manifest.itertuples(): assert hashlib.sha256((ROOT/'data/raw'/row.file).read_bytes()).hexdigest()==row.sha256
for line in (OUT/'independent_snapshot/SHA256SUMS.txt').read_text().splitlines():
    sha,path=line.split(maxsplit=1); assert hashlib.sha256((ROOT/path.strip()).read_bytes()).hexdigest()==sha
p=pd.read_csv(OUT/'predictions.csv',float_precision='round_trip'); perf=pd.read_csv(OUT/'performance.csv',float_precision='round_trip'); co=pd.read_csv(OUT/'coefficients.csv')
checks=[]
for row in perf.itertuples():
    q=p.loc[(p.model==row.model)&(p.strategy==row.strategy)]
    assert not q.id.duplicated().any(); assert q.p.between(0,1).all(); assert len(q)==row.n
    assert np.isclose(brier_score_loss(q.y,q.p),row.brier,atol=1e-12)
    assert np.isclose(roc_auc_score(q.y,q.p),row.auc,atol=1e-12)
    assert row.predictor_parameters<=3
    if row.strategy!='temporal': assert set(q.id)==set(x.id)
    else: assert set(q.id)==set(x.loc[x.year>=2009,'id'])
# Independent BFGS minimization checks every year-held-out probability of primary candidates.
errors=[]
for name,k in [('moisture',2),('moisture_temp',3)]:
    X=np.column_stack([np.ones(len(x)),x['VPD.L635.CHD.1'].to_numpy()/24,(x['T.A.2'].to_numpy()-15)/5])[:,:k]
    q=p.loc[(p.model==name)&(p.strategy=='year')].set_index('id')
    for yr in sorted(x.year.unique()):
        test=(x.year==yr).to_numpy(); train=~test; a=X[train]; yy=y[train]
        def loss(beta):
            eta=a@beta; return np.sum(np.logaddexp(0,eta)-yy*eta)
        def grad(beta): return a.T@(expit(a@beta)-yy)
        opt=minimize(loss,np.zeros(k),jac=grad,method='BFGS',options={'gtol':1e-7,'maxiter':1000})
        delta=np.max(np.abs(expit(X[test]@opt.x)-q.loc[x.loc[test,'id'],'p'].to_numpy()))
        errors.append(delta); assert delta<1e-6,(name,yr,delta,opt.message)
    beta=co.loc[co.model==name,'beta'].to_numpy(); assert len(beta)==k
    assert np.isfinite(beta).all()
assert not json.loads((OUT/'model_warnings.json').read_text())
assert pd.read_csv(OUT/'schema_audit.csv').issues.isna().all()
checks=['All downloaded SHA256s and independent-snapshot hashes match','All 12 performance rows match saved predictions','No duplicate test IDs; 999 predictions per grouped strategy/model','Temporal test IDs match years >=2009','All specifications use <=3 predictor parameters','Independent BFGS reproduces all year-out primary predictions within 1e-6','Final model warning log empty; numerical/schema audit has no flagged columns']
result={'checks':checks,'independent_prediction_max_abs_error':float(max(errors))}
(OUT/'verification.json').write_text(json.dumps(result,indent=2)); print(json.dumps(result,indent=2))
