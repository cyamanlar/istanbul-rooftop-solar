"""Download the PVGIS 5.3 inputs used in this project (needs internet).
Writes data/pvgis/*.csv / *.json. The repository already contains the files retrieved on 11 Nov 2026."""
import json, requests, pandas as pd
from config import DATA, LAT, LON
API = 'https://re.jrc.ec.europa.eu/api/v5_3/'
P = dict(lat=LAT, lon=LON, outputformat='json')
s = requests.get(API+'seriescalc', params=dict(P, startyear=2023, endyear=2023, components=1), timeout=120).json()
h = pd.DataFrame(s['outputs']['hourly']).rename(columns={'time':'time_UTC','Gb(i)':'Gb_h_Wm2','Gd(i)':'Gd_h_Wm2','Gr(i)':'Gr_h_Wm2','H_sun':'H_sun_deg','T2m':'T2m_C','WS10m':'WS10m_ms'})
h[['time_UTC','Gb_h_Wm2','Gd_h_Wm2','Gr_h_Wm2','H_sun_deg','T2m_C','WS10m_ms','Int']].to_csv(f'{DATA}/pvgis_hourly_2023_istanbul.csv', index=False)
json.dump(s['inputs'], open(f'{DATA}/pvgis_hourly_2023_inputs.json','w'))
red = lambda o: {'tot': o['outputs']['totals']['fixed'], 'mon': [[m['month'], m['E_m'], m['H(i)_m'], m['SD_m']] for m in o['outputs']['monthly']['fixed']],
                 'slope': o['inputs']['mounting_system']['fixed']['slope'], 'az': o['inputs']['mounting_system']['fixed']['azimuth']}
pv = {f'a{a}': red(requests.get(API+'PVcalc', params=dict(P, peakpower=1, loss=14, angle=a, aspect=0), timeout=120).json()) for a in [0,20,30,41,60]}
pv['opt'] = red(requests.get(API+'PVcalc', params=dict(P, peakpower=1, loss=14, optimalangles=1), timeout=120).json())
json.dump(pv, open(f'{DATA}/pvgis_pvcalc.json','w'))
out, daily41 = {}, None
for a in [0,20,30,41,60]:
    r = pd.DataFrame(requests.get(API+'seriescalc', params=dict(P, startyear=2023, endyear=2023, pvcalculation=1, peakpower=1, loss=14, angle=a, aspect=0), timeout=120).json()['outputs']['hourly'])
    r['m'] = r.time.str[4:6].astype(int); r['d'] = r.time.str[:8]
    out[str(a)] = {'E_m': (r.groupby('m').P.sum()/1000).round(2).tolist(), 'H_m': (r.groupby('m')['G(i)'].sum()/1000).round(2).tolist(), 'E_y': round(r.P.sum()/1000, 1)}
    if a == 41: daily41 = (r.groupby('d').P.sum()/1000).round(3)
json.dump(out, open(f'{DATA}/pvgis_2023_seriescalc_pv.json','w'))
daily41.to_csv(f'{DATA}/pvgis_2023_daily_PV_41deg_kWh_per_kWp.txt', index=False, header=False)
print('PVGIS data written to', DATA)
