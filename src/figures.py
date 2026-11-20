import pandas as pd, numpy as np, json, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from config import OUT as O, DATA as D, FIG
df=pd.read_pickle(f'{O}/hourly.pkl'); mon=pd.read_csv(f'{O}/monthly.csv'); sw=pd.read_csv(f'{O}/sweep.csv'); dd=pd.read_csv(f'{O}/daily.csv')
pv=json.load(open(f'{D}/pvgis_pvcalc.json')); pv23=json.load(open(f'{D}/pvgis_2023_seriescalc_pv.json')); ph=pd.read_csv(f'{O}/phone_model.csv')
plt.rcParams.update({'font.size':8.5,'axes.spines.top':False,'axes.spines.right':False,
 'axes.edgecolor':'black','axes.labelcolor':'black','xtick.color':'black','ytick.color':'black','text.color':'black','font.family':'DejaVu Serif','axes.grid':True,'grid.color':'#e6e6e6','grid.linewidth':0.6,'legend.frameon':False})
RAMP=['#86b6ef','#5598e7','#2a78d6','#1c5cab','#0d366b']; GRAY='#444'
TILTS=[0,20,30,41,60]; MON='JFMAMJJASOND'

# Fig 1 monthly yield
fig,ax=plt.subplots(figsize=(6.6,2.7))
for c,b in zip(RAMP,TILTS): ax.plot(range(1,13),mon[f'Y_{b}'],color=c,lw=2,marker='o',ms=3.5,label=f'{b}°')
ax.plot(range(1,13),pv23['41']['E_m'],ls='none',marker='x',color=GRAY,ms=6,label='PVGIS 2023, 41°')
ax.set_xticks(range(1,13)); ax.set_xticklabels(list(MON)); ax.set_ylabel('Specific yield (kWh/kWp per month)')
ax.legend(ncol=6,fontsize=7.5,loc='upper left',bbox_to_anchor=(0,1.16)); ax.set_ylim(0,190)
fig.tight_layout(); fig.savefig(f'{FIG}/fig1_monthly.png',dpi=220); plt.close()

# Fig 2 tilt sweep
fig,ax=plt.subplots(figsize=(3.3,2.6))
ax.plot(sw.tilt,sw.yield_kWh_kWp,color='#2a78d6',lw=2,label='Model (Erbs + isotropic), 2023')
ax.plot(TILTS,[pv23[str(b)]['E_y'] for b in TILTS],'x',color=GRAY,ms=6,label='PVGIS 2023')
ax.plot(TILTS,[pv[f'a{b}']['tot']['E_y'] for b in TILTS],'o',mfc='white',mec=GRAY,ms=5,label='PVGIS 2005–2023')
b=sw.loc[sw.yield_kWh_kWp.idxmax()]; ax.annotate(f'best {int(b.tilt)}°\n{b.yield_kWh_kWp:.0f} kWh/kWp',(b.tilt,b.yield_kWh_kWp),xytext=(45,1060),fontsize=7.5,arrowprops=dict(arrowstyle='-',color='#888',lw=0.7))
ax.set_xlabel('Tilt (°, south)'); ax.set_ylabel('Annual yield (kWh/kWp)'); ax.set_ylim(800,1400); ax.legend(fontsize=6.8,loc='lower left')
fig.tight_layout(); fig.savefig(f'{FIG}/fig2_tilt.png',dpi=220); plt.close()

# Fig 3 Erbs vs PVGIS diffuse
v=df[(df.GHI>0)&(df.elev_deg>5)]
fig,ax=plt.subplots(figsize=(3.3,2.6))
ax.scatter(v.Gd_h_Wm2,v.DHI_erbs,s=2,color='#2a78d6',alpha=0.25,lw=0)
ax.plot([0,500],[0,500],color=GRAY,lw=1); ax.set_xlim(0,500); ax.set_ylim(0,500)
r=np.corrcoef(v.Gd_h_Wm2,v.DHI_erbs)[0,1]; rmse=np.sqrt(((v.DHI_erbs-v.Gd_h_Wm2)**2).mean()); mbe=(v.DHI_erbs-v.Gd_h_Wm2).mean()
ax.text(15,440,f'n = {len(v)} h\nr = {r:.2f}, RMSE = {rmse:.0f} W/m²\nMBE = {mbe:.0f} W/m²',fontsize=7.2)
ax.set_xlabel('PVGIS diffuse horizontal (W/m²)'); ax.set_ylabel('Erbs diffuse horizontal (W/m²)')
fig.tight_layout(); fig.savefig(f'{FIG}/fig3_erbs.png',dpi=220); plt.close()

# Fig 4 daily PV coloured by sky class
fig,ax=plt.subplots(figsize=(6.6,2.3)); t=pd.to_datetime(dd.t)
for cls,c in [('clear','#2a78d6'),('partly cloudy','#eda100'),('overcast','#eb6834')]:
    m=dd.sky==cls; ax.bar(t[m],dd.E_pvgis41[m],width=0.9,color=c,label=f'{cls} ({m.sum()} d)')
ax.set_ylabel('PV output (kWh/kWp/day)'); ax.legend(ncol=3,fontsize=7.5,loc='upper left',bbox_to_anchor=(0,1.15))
ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%b'))
fig.tight_layout(); fig.savefig(f'{FIG}/fig4_daily.png',dpi=220); plt.close()

# Fig 5 phone comparison shape (model + two clear Nov 2023 days)
fig,ax=plt.subplots(figsize=(3.3,2.6)); hrs=np.arange(10,16)
ax.plot(hrs,ph.G41_norm,color='#2a78d6',lw=2,marker='o',ms=4,label='Clear-sky model, 15 Nov')
for d_,c,mk in zip(['2023-11-10','2023-11-07'],['#1c5cab','#86b6ef'],['s','^']):
    s=df[(df.local.dt.strftime('%Y-%m-%d')==d_)&(df.local.dt.hour.between(10,15))]
    ax.plot(s.local.dt.hour,s.POA_41/s.POA_41.max(),color=c,lw=1.3,marker=mk,ms=3.5,ls='--',label=f'PVGIS {d_} (41°)')
ax.set_xlabel('Local time (TRT, h)'); ax.set_ylabel('Normalised irradiance (–)'); ax.set_ylim(0.4,1.05); ax.legend(fontsize=6.8,loc='lower center')
fig.tight_layout(); fig.savefig(f'{FIG}/fig5_phone.png',dpi=220); plt.close()
print('annual G0', df.G0h.sum()/1000, 'KT', df.GHI.sum()/df.G0h.sum())
print('summer vs winter share of GHI', df[df.month.isin([4,5,6,7,8,9])].GHI.sum()/df.GHI.sum())
print('Tcell max 30', df.Tcell_30.max(), 'temp loss', 1-(df.P5kW_30.sum()/(5*df.POA_30/1000*(1-0.14)).sum()))
