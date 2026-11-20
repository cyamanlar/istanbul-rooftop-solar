"""Read phyphox 'Light' recordings, rebuild the clock time of every sample from the
start/pause events and compare recording medians with a clear-sky model on a 41° plane."""
import glob, os, numpy as np, pandas as pd, xml.etree.ElementTree as ET, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
from config import PHYPHOX, OUT, FIG, LAT, LON
ISC = 1361.0; LUX_PER_WM2 = 110.0
plt.rcParams.update({'font.family':'DejaVu Serif','font.size':8.5})

def clear_sky_41(ts):
    """Haurwitz clear-sky GHI -> Erbs split -> isotropic sky on a 41° south plane (W/m²)."""
    t = pd.Series(ts).dt.tz_convert('UTC')
    n = t.dt.dayofyear.values; hr = t.dt.hour.values + t.dt.minute.values/60 + t.dt.second.values/3600
    B = 2*np.pi*(n-1)/365
    dc = (0.006918-0.399912*np.cos(B)+0.070257*np.sin(B)-0.006758*np.cos(2*B)
          +0.000907*np.sin(2*B)-0.002697*np.cos(3*B)+0.00148*np.sin(3*B))
    eot = 229.18*(0.000075+0.001868*np.cos(B)-0.032077*np.sin(B)-0.014615*np.cos(2*B)-0.040849*np.sin(2*B))
    w = np.radians((hr*60+eot+4*LON)/4-180); phi = np.radians(LAT)
    cz = np.sin(phi)*np.sin(dc)+np.cos(phi)*np.cos(dc)*np.cos(w); E0 = 1.00011+0.034221*np.cos(B)
    czp = np.clip(cz, 1e-3, None)
    ghi = np.where(cz > 0, 1098*czp*np.exp(-0.057/czp), 0); k = np.clip(ghi/(ISC*E0*czp), 0, 1)
    kd = np.where(k<=0.22,1-0.09*k,np.where(k<=0.8,0.9511-0.1604*k+4.388*k**2-16.638*k**3+12.336*k**4,0.165))
    dhi = kd*ghi; dni = np.where(cz > 0.0872, (ghi-dhi)/czp, 0); b = np.radians(41)
    ct = np.sin(dc)*np.sin(phi-b)+np.cos(dc)*np.cos(phi-b)*np.cos(w)
    return dni*np.clip(ct,0,None)+dhi*(1+np.cos(b))/2+ghi*0.2*(1-np.cos(b))/2, np.degrees(np.arcsin(cz))

def load(path, segbase):
    root = ET.parse(path).getroot(); c = {x.text.strip(): x.get('init') for x in root.iter('container')}
    lux = np.array([float(v) for v in c['illum'].split(',')]); tt = np.array([float(v) for v in c['illum_time'].split(',')])
    ev = [(float(e.get('experimentTime')), int(e.get('systemTime'))) for e in root.find('events')]
    out = []
    for k in range(0, len(ev), 2):
        a, sys0 = ev[k]; b = ev[k+1][0]; m = (tt >= a) & (tt <= b)
        if m.any():
            clock = pd.to_datetime([(sys0 + (x-a)*1000)/1000 for x in tt[m]], unit='s', utc=True).tz_convert('Europe/Istanbul')
            out.append(pd.DataFrame({'clock': clock, 'lux': lux[m], 'seg': segbase+k}))
    return pd.concat(out)

files = sorted(glob.glob(os.path.join(PHYPHOX, '*.phyphox')))
D = pd.concat([load(f, 100*i) for i, f in enumerate(files)])
D['day'] = D.clock.dt.strftime('%d %b').str.lstrip('0')
D.to_pickle(f'{OUT}/meas.pkl')
g = D.groupby(['day','seg']).agg(start=('clock','min'), end=('clock','max'), n=('lux','size'), median=('lux','median'),
        p10=('lux', lambda s: s.quantile(.1)), p90=('lux', lambda s: s.quantile(.9)), mx=('lux','max')).reset_index()
g = g.sort_values('start').reset_index(drop=True)
G, el = clear_sky_41(g.start + (g.end-g.start)/2)
g['G41_clear'] = G; g['elev'] = el; g['W_meas'] = g['median']/LUX_PER_WM2; g['ratio'] = g['W_meas']/g['G41_clear']
g.to_pickle(f'{OUT}/seg.pkl')
g.drop(columns=['seg']).to_csv(f'{OUT}/phone_recordings_summary.csv', index=False)
print(g[['day','start','n','median','W_meas','G41_clear','ratio']].to_string())

days = list(dict.fromkeys(g.day))
fig, axs = plt.subplots(1, len(days), figsize=(6.8, 2.6), sharey=True, squeeze=False); axs = axs[0]
for ax, day in zip(axs, days):
    d = D[D.day == day]; gg = g[g.day == day]; date = d.clock.iloc[0].strftime('%Y-%m-%d')
    ax.scatter(d.clock.dt.tz_localize(None), d.lux/1000, s=1.5, color='#2a78d6', alpha=0.35, lw=0, label='samples')
    ax.plot((gg.start+(gg.end-gg.start)/2).dt.tz_localize(None), gg['median']/1000, 'o', color='#0d366b', ms=5, label='recording median')
    tt = pd.Series(pd.date_range(f'{date} 10:00', f'{date} 15:00', freq='10min', tz='Europe/Istanbul')); Gm, _ = clear_sky_41(tt)
    ax.plot(tt.dt.tz_localize(None), Gm*LUX_PER_WM2/1000, 'k--', lw=1.3, label='clear-sky model, 41°')
    ax.set_title(f'{day} 2026', fontsize=9); ax.set_ylim(0, 100); ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter('%H'))
    ax.set_xlabel('Local time (TRT, h)'); ax.grid(color='#e6e6e6', lw=0.6)
    for s in ('top','right'): ax.spines[s].set_visible(False)
axs[0].set_ylabel('Illuminance (klx)'); axs[0].legend(fontsize=6.8, frameon=False, loc='center left', bbox_to_anchor=(0, 0.55))
fig.tight_layout(); fig.savefig(f'{FIG}/fig6_phone_meas.png', dpi=220)
