"""Rooftop solar for İstanbul homes.
Erbs decomposition + isotropic-sky transposition + NOCT temperature model, 5 kWp system.
Input: PVGIS 5.3 hourly (SARAH3/ERA5) for 2023 at ITU Maslak (41.105 N, 29.025 E, 97 m)."""
import numpy as np, pandas as pd, json, os
from config import DATA as D, OUT as O

LAT, LON = 41.105, 29.025
TILTS = [0, 20, 30, 41, 60]
ALBEDO = 0.20; NOCT = 45.0; GAMMA = -0.004; LOSS = 0.14; PSTC_KW = 5.0; ISC = 1361.0

df = pd.read_csv(f'{D}/pvgis_hourly_2023_istanbul.csv')
df['t'] = pd.to_datetime(df.time_UTC, format='%Y%m%d:%H%M')
df['GHI'] = df.Gb_h_Wm2 + df.Gd_h_Wm2           # tilt 0 -> no ground-reflected part
df['local'] = df.t + pd.Timedelta(hours=3)          # TRT = UTC+3

# ---------- solar geometry (Spencer 1971 / Iqbal) ----------
def solar(t):
    n = t.dt.dayofyear.values; hr = t.dt.hour.values + t.dt.minute.values/60
    B = 2*np.pi*(n-1)/365
    decl = (0.006918-0.399912*np.cos(B)+0.070257*np.sin(B)-0.006758*np.cos(2*B)
            +0.000907*np.sin(2*B)-0.002697*np.cos(3*B)+0.00148*np.sin(3*B))
    eot = 229.18*(0.000075+0.001868*np.cos(B)-0.032077*np.sin(B)-0.014615*np.cos(2*B)-0.040849*np.sin(2*B))
    tst = hr*60 + eot + 4*LON                         # true solar time, minutes
    w = np.radians(tst/4 - 180)                       # hour angle
    phi = np.radians(LAT)
    cosz = np.sin(phi)*np.sin(decl)+np.cos(phi)*np.cos(decl)*np.cos(w)
    E0 = 1.00011+0.034221*np.cos(B)+0.00128*np.sin(B)+0.000719*np.cos(2*B)+0.000077*np.sin(2*B)
    return n, decl, w, cosz, E0
n, decl, w, cosz, E0 = solar(df.t)
df['doy']=n; df['decl_deg']=np.degrees(decl); df['hour_angle_deg']=np.degrees(w)
df['cosZ']=cosz; df['elev_deg']=np.degrees(np.arcsin(np.clip(cosz,-1,1)))
df['G0h'] = np.where(cosz>0, ISC*E0*cosz, 0)

# ---------- Erbs et al. (1982) ----------
day = (df.GHI>0)&(cosz>0.0175)                       # sun > ~1 deg
kt = np.where(day, np.clip(df.GHI/np.maximum(df.G0h,1e-6),0,1.0), np.nan)
kd = np.where(kt<=0.22, 1-0.09*kt,
     np.where(kt<=0.80, 0.9511-0.1604*kt+4.388*kt**2-16.638*kt**3+12.336*kt**4, 0.165))
df['kt']=kt; df['kd']=kd
df['DHI_erbs'] = np.where(day, kd*df.GHI, df.GHI)
df['BHI_erbs'] = df.GHI-df.DHI_erbs
df['DNI_erbs'] = np.where(day&(cosz>0.0872), df.BHI_erbs/np.maximum(cosz,1e-6), 0)  # guard sun < 5 deg
df.loc[day&(cosz<=0.0872),'DHI_erbs'] = df.GHI[day&(cosz<=0.0872)]; df.loc[day&(cosz<=0.0872),'BHI_erbs']=0

# ---------- isotropic sky (Liu & Jordan), south-facing ----------
def poa(beta):
    b=np.radians(beta); phi=np.radians(LAT)
    costh = (np.sin(decl)*np.sin(phi-b) + np.cos(decl)*np.cos(phi-b)*np.cos(w))   # south-facing, N hemisphere
    beam = df.DNI_erbs*np.clip(costh,0,None)
    diff = df.DHI_erbs*(1+np.cos(b))/2
    refl = df.GHI*ALBEDO*(1-np.cos(b))/2
    return beam+diff+refl, beam, diff, refl
def power(G):
    Tc = df.T2m_C + (NOCT-20)/800*G
    return PSTC_KW*G/1000*(1+GAMMA*(Tc-25))*(1-LOSS), Tc     # kW AC (5 kWp)

res={}
for bt in TILTS:
    G,bm,df_,rf = poa(bt); P,Tc = power(G)
    df[f'POA_{bt}']=G; df[f'Tcell_{bt}']=Tc; df[f'P5kW_{bt}']=P.clip(lower=0)
# fine sweep for the best tilt
sweep=[]
for bt in range(0,91,1):
    G,_,_,_=poa(bt); P,_=power(G); sweep.append((bt,G.sum()/1000,P.clip(lower=0).sum()/PSTC_KW))
sweep=pd.DataFrame(sweep,columns=['tilt','H_poa_kWh_m2','yield_kWh_kWp'])
best = sweep.loc[sweep.yield_kWh_kWp.idxmax()]

# ---------- monthly / annual ----------
df['month']=df.t.dt.month
mon = pd.DataFrame({'month':range(1,13)})
for bt in TILTS:
    g=df.groupby('month')
    mon[f'H_{bt}']=g[f'POA_{bt}'].sum().values/1000
    mon[f'Y_{bt}']=g[f'P5kW_{bt}'].sum().values/PSTC_KW
ann = {bt:{'H':mon[f'H_{bt}'].sum(),'Y':mon[f'Y_{bt}'].sum()} for bt in TILTS}
for bt in TILTS: ann[bt]['CF']=ann[bt]['Y']/8760; ann[bt]['E5']=ann[bt]['Y']*PSTC_KW

pv = json.load(open(f'{D}/pvgis_pvcalc.json')); pv23=json.load(open(f'{D}/pvgis_2023_seriescalc_pv.json'))

# ---------- Erbs vs PVGIS own split (validation) ----------
v = df[day & (df.elev_deg>5)]
rmse_d = np.sqrt(((v.DHI_erbs-v.Gd_h_Wm2)**2).mean()); mbe_d=(v.DHI_erbs-v.Gd_h_Wm2).mean()
ann_frac_diff_erbs = df.DHI_erbs.sum()/df.GHI.sum(); ann_frac_diff_pvgis=df.Gd_h_Wm2.sum()/df.GHI.sum()

# ---------- cloudy-day loss (PVGIS 2023 daily PV, 41 deg) ----------
dd = df.groupby(df.t.dt.date).agg(GHI=('GHI','sum'),G0=('G0h','sum'),Tmax=('T2m_C','max')).reset_index()
dd['KT']=dd.GHI/dd.G0
dd['E_pvgis41']=np.loadtxt(f'{D}/pvgis_2023_daily_PV_41deg_kWh_per_kWp.txt')
dd['E_model41']=df.groupby(df.t.dt.date)['P5kW_41'].sum().values/PSTC_KW
dd['month']=pd.to_datetime(dd.t).dt.month
dd['sky']=np.select([dd.KT>=0.60, dd.KT<0.30],['clear','overcast'],'partly cloudy')
cl = dd.groupby(['month','sky']).E_pvgis41.mean().unstack()
cl['clear_ref']=cl['clear']   # mean of clear days (KT>=0.6) of the month
cl['loss_overcast_%']=100*(1-cl['overcast']/cl['clear_ref'])
cl['loss_partly_%']=100*(1-cl['partly cloudy']/cl['clear_ref'])
cnt = dd.groupby(['month','sky']).size().unstack(fill_value=0)
potential = (dd.groupby('month').size()*cl['clear']).sum()
actual = dd.E_pvgis41.sum(); loss_total=100*(1-actual/potential)
ov = dd[dd.sky=='overcast']; lost_on_overcast = (dd.month.map(cl.clear_ref)[dd.sky=='overcast']-ov.E_pvgis41).sum()
lost_on_partly = (dd.month.map(cl.clear_ref)[dd.sky=='partly cloudy']-dd[dd.sky=='partly cloudy'].E_pvgis41).sum()

# ---------- economics ----------
# EPDK tariff table valid from 4 Apr 2026 (Board decision 14461, RG 33214); residential prices unchanged on 1 Oct 2026.
en_low, en_high, dist = 0.494065, 1.895808, 2.424900     # TL/kWh, tax excluded
BTV, KDV = 0.05, 0.10                                     # energy-consumption tax on energy part; VAT residential
p_low = (en_low*(1+BTV)+dist)*(1+KDV); p_high=(en_high*(1+BTV)+dist)*(1+KDV)
CAPEX = {'low':150000,'mid':180000,'high':210000}
E_best = best.yield_kWh_kWp*PSTC_KW
E41 = ann[30]['E5']   # economics for a 30 deg roof (near-optimal)
econ=[]
for cname,c in CAPEX.items():
    for pname,p in [('low tier',p_low),('high tier',p_high)]:
        econ.append([cname,c,pname,round(p,3),round(E41),round(E41*p),round(c/(E41*p),1)])
econ=pd.DataFrame(econ,columns=['capex_case','capex_TL','tariff','price_TL_kWh','E_yr_kWh','saving_TL_yr','payback_yr'])

# ---------- phone comparison: modelled clear-day shape, 10-15 local, 41 deg ----------
def clear_shape(date):
    hrs = np.arange(10,16)
    t = pd.Series(pd.to_datetime([f'{date} {h:02d}:00' for h in hrs]) - pd.Timedelta(hours=3))
    n_,dc,ww,cz,e0 = solar(t)
    ghi = 1098*cz*np.exp(-0.057/cz)               # Haurwitz clear-sky
    g0 = ISC*e0*cz; k=np.clip(ghi/g0,0,1)
    kd_ = np.where(k<=0.22,1-0.09*k,np.where(k<=0.8,0.9511-0.1604*k+4.388*k**2-16.638*k**3+12.336*k**4,0.165))
    dhi=kd_*ghi; dni=(ghi-dhi)/cz
    b=np.radians(41); phi=np.radians(LAT)
    ct=np.sin(dc)*np.sin(phi-b)+np.cos(dc)*np.cos(phi-b)*np.cos(ww)
    G = dni*np.clip(ct,0,None)+dhi*(1+np.cos(b))/2+ghi*ALBEDO*(1-np.cos(b))/2
    return pd.DataFrame({'local_time':[f'{h}:00' for h in hrs],'G41_model_Wm2':G.round(0),'G41_norm':(G/G.max()).round(3),
                         'elev_deg':np.degrees(np.arcsin(cz)).round(1)})
phone = clear_shape('2026-11-15')
# real clear November days of 2023 in PVGIS data (shape check)
nov = dd[(dd.month==11)].nlargest(2,'KT')
nov_shapes={}
for d_ in nov.t:
    s=df[(df.local.dt.date==d_)&(df.local.dt.hour.between(10,15))][['local','POA_41']]
    nov_shapes[str(d_)]=s

# ---------- save ----------
df.to_pickle(f'{O}/hourly.pkl'); mon.to_csv(f'{O}/monthly.csv',index=False); sweep.to_csv(f'{O}/sweep.csv',index=False)
dd.to_csv(f'{O}/daily.csv',index=False); econ.to_csv(f'{O}/econ.csv',index=False); phone.to_csv(f'{O}/phone_model.csv',index=False)
summary=dict(ann=ann,best=best.to_dict(),rmse_d=rmse_d,mbe_d=mbe_d,fd_erbs=ann_frac_diff_erbs,fd_pvgis=ann_frac_diff_pvgis,
             loss_total=loss_total,lost_ov=lost_on_overcast,lost_pc=lost_on_partly,actual=actual,potential=potential,
             p_low=p_low,p_high=p_high,E41=E41,E_best=E_best,ndays=dd.sky.value_counts().to_dict(),
             cl=cl.round(2).to_dict(),nov_days=[str(x) for x in nov.t], nov_KT=nov.KT.round(3).tolist(),
             GHI_ann=df.GHI.sum()/1000, Tmean=df.T2m_C.mean())
json.dump(summary,open(f'{O}/summary.json','w'),indent=1,default=float)
pd.to_pickle(dict(cl=cl,cnt=cnt,nov_shapes=nov_shapes),f'{O}/extra.pkl')

print('GHI annual kWh/m2', round(df.GHI.sum()/1000,1), ' mean T', round(df.T2m_C.mean(),1))
print('elev check vs PVGIS H_sun: max abs diff', round((df.elev_deg.clip(lower=0)-df.H_sun_deg).abs().max(),2))
print('diffuse fraction erbs/pvgis', round(ann_frac_diff_erbs,3), round(ann_frac_diff_pvgis,3), 'RMSE',round(rmse_d,1),'MBE',round(mbe_d,1))
for bt in TILTS: print(bt, {k:round(v,3) for k,v in ann[bt].items()}, 'PVGIS 2023', pv23[str(bt)]['E_y'], 'PVGIS LT', pv[f'a{bt}']['tot']['E_y'])
print('best', best.to_dict())
print(mon.round(1).to_string())
print(cl.round(2).to_string()); print(cnt)
print('loss total %',round(loss_total,1),'lost overcast',round(lost_on_overcast,1),'partly',round(lost_on_partly,1),'actual',round(actual,1))
print('prices',round(p_low,3),round(p_high,3)); print(econ.to_string())
print(phone.to_string()); print(nov[['t','KT','E_pvgis41']])
