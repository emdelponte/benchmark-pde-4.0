"""Publication-independent diagnostic plots from saved grouped predictions."""
import os
os.environ.setdefault('MPLCONFIGDIR','/tmp/fhb-matplotlib')
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'outputs'
b=pd.read_csv(OUT/'calibration_bins.csv'); g=pd.read_csv(OUT/'group_performance.csv')
fig,axes=plt.subplots(1,2,figsize=(10,4.4))
for ax,strategy in zip(axes,['year','state']):
    ax.plot([0,1],[0,1],'--',color='gray',lw=1)
    for name,color,label in [('moisture','#31688e','Moisture'),('moisture_temp','#269f72','Moisture + temperature')]:
        z=b.loc[(b.strategy==strategy)&(b.model==name)]
        ax.plot(z.predicted,z.observed,'o-',color=color,label=label)
        for row in z.itertuples():
            offset=8 if name=='moisture' else -13
            if row.observed<.03: offset=8 if name=='moisture' else 18
            ax.annotate(str(int(row.n)),(row.predicted,row.observed),xytext=(4,offset),textcoords='offset points',fontsize=8,color=color)
    ax.set(xlim=(0,1),ylim=(-.03,1.02),xlabel='Mean held-out epidemic probability',ylabel='Observed epidemic proportion',title=f'Leave-one-{strategy}-out')
    ax.legend(loc='upper left',fontsize=8)
fig.suptitle('Calibration by fixed probability bins; labels show observation counts',fontsize=11); fig.tight_layout(); fig.savefig(OUT/'calibration.png',dpi=180); plt.close(fig)
fig,axes=plt.subplots(1,2,figsize=(10,4.4))
for ax,strategy in zip(axes,['year','state']):
    z=g.loc[(g.strategy==strategy)&(g.model=='moisture_temp')]
    ax.plot([0,1],[0,1],'--',color='gray',lw=1)
    ax.scatter(z.mean_prediction,z.prevalence,s=12+z.n*1.2,color='#31688e',alpha=.65)
    for row in z.loc[z.n>=25].itertuples(): ax.annotate(str(row.group),(row.mean_prediction,row.prevalence),xytext=(3,3),textcoords='offset points',fontsize=7)
    ax.set(xlim=(0,1),ylim=(0,1),xlabel='Mean held-out probability in group',ylabel='Observed epidemic prevalence in group',title=f'Held-out {strategy} groups')
fig.suptitle('Two-term model: group calibration; point area increases with group size',fontsize=11); fig.tight_layout(); fig.savefig(OUT/'group_calibration.png',dpi=180); plt.close(fig)
