import pandas as pd, numpy as np, json
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter as L
from openpyxl.comments import Comment

from config import OUT as O, DATA as D
df=pd.read_pickle(f'{O}/hourly.pkl'); sweep=pd.read_csv(f'{O}/sweep.csv'); dd=pd.read_csv(f'{O}/daily.csv')
phone=pd.read_csv(f'{O}/phone_model.csv'); pv=json.load(open(f'{D}/pvgis_pvcalc.json')); pv23=json.load(open(f'{D}/pvgis_2023_seriescalc_pv.json'))
TILTS=[0,20,30,41,60]
F='Arial'
BLUE=Font(name=F,color='0000FF'); BLK=Font(name=F); BOLD=Font(name=F,bold=True); GRN=Font(name=F,color='008000')
H=Font(name=F,bold=True,color='000000'); HF=PatternFill(fill_type=None); YEL=PatternFill('solid',fgColor='FFFF00')
TITLE=Font(name=F,bold=True,size=14)
wb=Workbook()

def hdr(ws,row,vals,col=1):
    for i,v in enumerate(vals):
        c=ws.cell(row,col+i,v); c.font=H; c.alignment=Alignment(wrap_text=True,vertical='center'); c.border=Border(top=Side('thin'),bottom=Side('thin'),left=Side('thin'),right=Side('thin'))

# ---------------- README ----------------
ws=wb.active; ws.title='README'
lines=[('Rooftop solar power for İstanbul homes – calculation workbook',TITLE),
('Erbs decomposition, isotropic-sky transposition and a temperature-corrected 5 kWp PV model with PVGIS 5.3 hourly data',BOLD),
('',None),
('Site: İTÜ Ayazağa (Maslak) campus, 41.105° N, 29.025° E, 97 m a.s.l. (change in Inputs if you use the home address – re-download PVGIS data for it).',BLK),
('Data: PVGIS 5.3 hourly radiation (PVGIS-SARAH3 satellite) and ERA5 2-m air temperature / 10-m wind, year 2023 (latest full year), horizon from DEM.',BLK),
('Source: European Commission JRC, PVGIS 5.3 API, https://re.jrc.ec.europa.eu/api/v5_3/seriescalc?lat=41.105&lon=29.025&startyear=2023&endyear=2023&components=1 (downloaded 11 Nov 2026).',BLK),
('PVGIS benchmark: PVcalc (1 kWp, crystalline Si, 14 % system loss, south) for 2005–2023 and seriescalc pvcalculation=1 for 2023, same point.',BLK),
('',None),
('Sheets',BOLD),
('Inputs – all parameters and assumptions (blue = typed input, yellow = key assumption).',BLK),
('Hourly_Model – 8760 PVGIS hours; Erbs split, isotropic-sky plane-of-array irradiance for 0/20/30/41/60°, NOCT cell temperature and 5 kWp AC power. All live formulas.',BLK),
('Monthly_Annual – monthly and annual irradiation and yield (kWh/kWp), capacity factor, comparison with PVGIS.',BLK),
('Tilt_Sweep – annual yield for every tilt 0–90° (same model, run in Python script model.py; values) to find the best tilt.',BLK),
('Daily_CloudyLoss – daily clearness index K_T, sky class and PVGIS daily PV output at 41°; loss on cloudy days.',BLK),
('Economics – EPDK household tariff (with taxes), investment cost and simple payback time.',BLK),
('Phone_Measurements – blank template for new phyphox readings (10:00–15:00, phone tilted 41° to south). Phone_Data – the recordings of 11–12 Nov 2026 and their comparison with the clear-sky model.',BLK),
('',None),
('Colour code: blue text = hard-coded input/data, black = formula, green = link to another sheet, yellow fill = key assumption / cell to fill in.',BLK),
('Note: 9 daytime hours are missing in the PVGIS 2023 file (GHI = 0 and sun height = 0 at midday, e.g. 12 Jun 09:10 UTC). They were kept as zero (≈0.1 % of the year).',BLK),
('Time: PVGIS time stamps are UTC (HH:10 = mid-point of the satellite slot). Local time TRT = UTC + 3 h.',BLK)]
for i,(t,f) in enumerate(lines,1):
    c=ws.cell(i,1,t);
    if f: c.font=f
ws.column_dimensions['A'].width=160

# ---------------- Inputs ----------------
wi=wb.create_sheet('Inputs'); wi.column_dimensions['A'].width=44; wi.column_dimensions['B'].width=14; wi.column_dimensions['C'].width=90
wi['A1']='Inputs and assumptions'; wi['A1'].font=TITLE
hdr(wi,2,['Parameter','Value','Unit / source'])
inp=[('Latitude',41.105,'° N – İTÜ Maslak (PVGIS point)'),
('Longitude',29.025,'° E'),
('Solar constant I_sc',1361,'W m⁻² (Kopp & Lean 2011; standard value)'),
('Ground albedo ρ',0.20,'– typical urban surface (isotropic model ground term)'),
('NOCT',45,'°C – typical crystalline-Si module datasheet'),
('Power temperature coefficient γ',-0.004,'1/K – typical c-Si (−0.4 %/K)'),
('System losses (inverter, wiring, soiling, mismatch)',0.14,'– same 14 % as the PVGIS default, for a fair comparison'),
('Rated power P_STC',5,'kWp – 5 kWp rooftop system (assignment)'),
('Erbs: sun-height limit for beam (cos Z)',0.0872,'cos(85°): below 5° sun height all irradiance treated as diffuse'),
('Day flag: minimum cos Z',0.0175,'cos(89°)'),
('Tilt 1',0,'° (south-facing, azimuth 180°)'),('Tilt 2',20,'°'),('Tilt 3',30,'°'),('Tilt 4',41,'° (≈ latitude)'),('Tilt 5',60,'°'),
('EPDK active energy, residential low tier',0.494065,'TL/kWh excl. tax – EPDK tariff table valid from 4 Apr 2026, Board Decision 14461 (2 Apr 2026), Resmî Gazete 33214; residential prices unchanged on 1 Oct 2026'),
('EPDK active energy, residential high tier',1.895808,'TL/kWh excl. tax – same table (consumption > 8 kWh/day)'),
('EPDK distribution fee, residential LV',2.4249,'TL/kWh excl. tax – same table'),
('Electricity consumption tax (on energy part)',0.05,'– residential rate'),
('VAT (KDV) residential electricity',0.10,'– reduced rate for households'),
('Investment cost – low',150000,'TL, 5 kW grid-tied, no battery, turnkey (Milliyet Uzmanpara, 2026 market range 150–210 k TL)'),
('Investment cost – central',180000,'TL – mid-point of the range'),
('Investment cost – high',210000,'TL'),
('Illuminance → irradiance factor',110,'lux per W m⁻² for direct sunlight (common rule of thumb: ~110 lux ≈ 1 W m⁻²)')]
names={}
for i,(a,b,c) in enumerate(inp,3):
    wi.cell(i,1,a).font=BLK; cb=wi.cell(i,2,b); cb.font=BLUE; wi.cell(i,3,c).font=BLK
    if a.startswith(('System losses','Ground albedo','Investment cost – central','EPDK')): cb.fill=YEL
    names[a]=f'Inputs!$B${i}'
LAT,LON,ISC,ALB,NOCT,GAM,LOSS,PSTC,CZB,CZD=[names[k] for k in ['Latitude','Longitude','Solar constant I_sc','Ground albedo ρ','NOCT','Power temperature coefficient γ','System losses (inverter, wiring, soiling, mismatch)','Rated power P_STC','Erbs: sun-height limit for beam (cos Z)','Day flag: minimum cos Z']]
TIL=[names[f'Tilt {i}'] for i in range(1,6)]

# ---------------- Hourly ----------------
wh=wb.create_sheet('Hourly_Model')
cols=['Time UTC (PVGIS)','Local time (TRT)','Month','Date','Beam horiz. Gb (W/m²) PVGIS','Diffuse horiz. Gd (W/m²) PVGIS','Air T2m (°C) ERA5','Wind 10 m (m/s)',
'Declination δ (rad)','Hour angle ω (rad)','cos Z','Eccentricity E0',
'GHI (W/m²)','G0 horiz. extraterr. (W/m²)','k_t','k_d (Erbs)','DHI Erbs (W/m²)','DNI Erbs (W/m²)']
for b in TILTS: cols+= [f'POA {b}° (W/m²)',f'T_cell {b}° (°C)',f'P_AC {b}° (kW)']
hdr(wh,1,cols)
n=len(df)
B=2*np.pi*(df.doy.values-1)/365
E0=1.00011+0.034221*np.cos(B)+0.00128*np.sin(B)+0.000719*np.cos(2*B)+0.000077*np.sin(2*B)
for i in range(n):
    r=i+2; x=df.iloc[i]
    vals=[x.time_UTC, x.local.to_pydatetime(), int(x.month), x.local.date() if False else x.t.date(),
          float(x.Gb_h_Wm2), float(x.Gd_h_Wm2), float(x.T2m_C), float(x.WS10m_ms),
          float(np.radians(x.decl_deg)), float(np.radians(x.hour_angle_deg)), float(x.cosZ), float(E0[i])]
    for j,v in enumerate(vals,1): wh.cell(r,j,v)
    wh.cell(r,13,f'=E{r}+F{r}')
    wh.cell(r,14,f'=IF(K{r}>0,{ISC}*L{r}*K{r},0)')
    wh.cell(r,15,f'=IF(AND(M{r}>0,K{r}>{CZD}),MIN(MAX(M{r}/N{r},0),1),"")')
    wh.cell(r,16,f'=IF(O{r}="","",IF(O{r}<=0.22,1-0.09*O{r},IF(O{r}<=0.8,0.9511-0.1604*O{r}+4.388*O{r}^2-16.638*O{r}^3+12.336*O{r}^4,0.165)))')
    wh.cell(r,17,f'=IF(OR(O{r}="",K{r}<={CZB}),M{r},P{r}*M{r})')
    wh.cell(r,18,f'=IF(OR(O{r}="",K{r}<={CZB}),0,(M{r}-Q{r})/K{r})')
    for k,tl in enumerate(TIL):
        c0=19+3*k; P_,T_,W_=L(c0),L(c0+1),L(c0+2)
        wh.cell(r,c0,f'=R{r}*MAX(0,SIN(I{r})*SIN(RADIANS({LAT}-{tl}))+COS(I{r})*COS(RADIANS({LAT}-{tl}))*COS(J{r}))+Q{r}*(1+COS(RADIANS({tl})))/2+M{r}*{ALB}*(1-COS(RADIANS({tl})))/2')
        wh.cell(r,c0+1,f'=G{r}+({NOCT}-20)/800*{P_}{r}')
        wh.cell(r,c0+2,f'=MAX(0,{PSTC}*{P_}{r}/1000*(1+{GAM}*({T_}{r}-25))*(1-{LOSS}))')
    for j in range(1,13): wh.cell(r,j).font=BLUE
for j in range(1,len(cols)+1): wh.column_dimensions[L(j)].width=12
wh.column_dimensions['A'].width=15; wh.column_dimensions['B'].width=17
wh.freeze_panes='C2'
for r in range(2,n+2):
    wh.cell(r,2).number_format='yyyy-mm-dd hh:mm'; wh.cell(r,4).number_format='yyyy-mm-dd'
wh['I1'].comment=Comment('Solar geometry from Spencer (1971) series (Iqbal 1983), computed in model.py. Checked against PVGIS sun height: max difference 0.3°.','CY')

# ---------------- Monthly ----------------
wm=wb.create_sheet('Monthly_Annual'); wm['A1']='Monthly irradiation on the panel (kWh/m²) and specific yield (kWh/kWp) – model (Erbs + isotropic + NOCT) vs PVGIS'; wm['A1'].font=TITLE
hdr(wm,3,['Month']+[f'H_POA {b}° (kWh/m²)' for b in TILTS]+[f'Yield {b}° (kWh/kWp)' for b in TILTS]+[f'PVGIS 2023 {b}° (kWh/kWp)' for b in TILTS]+[f'PVGIS 2005–23 {b}° (kWh/kWp)' for b in TILTS])
HR=n+1
for m in range(1,13):
    r=3+m; wm.cell(r,1,m).font=BLK
    for k,b in enumerate(TILTS):
        pc=L(19+3*k); wc=L(21+3*k)
        wm.cell(r,2+k,f"=SUMIFS(Hourly_Model!${pc}$2:${pc}${HR},Hourly_Model!$C$2:$C${HR},$A{r})/1000")
        wm.cell(r,7+k,f"=SUMIFS(Hourly_Model!${wc}$2:${wc}${HR},Hourly_Model!$C$2:$C${HR},$A{r})/{PSTC}")
        c=wm.cell(r,12+k,pv23[str(b)]['E_m'][m-1]); c.font=BLUE
        c=wm.cell(r,17+k,pv[f'a{b}']['mon'][m-1][1]); c.font=BLUE
ra=16; wm.cell(ra,1,'Year').font=BOLD
for j in range(2,22): wm.cell(ra,j,f'=SUM({L(j)}4:{L(j)}15)').font=BOLD
rc=17; wm.cell(rc,1,'Capacity factor').font=BOLD
for j in range(7,22): c=wm.cell(rc,j,f'={L(j)}{ra}/8760'); c.number_format='0.0%'
rd=18; wm.cell(rd,1,'Model vs PVGIS 2023').font=BOLD
for k in range(5): c=wm.cell(rd,7+k,f'={L(7+k)}{ra}/{L(12+k)}{ra}-1'); c.number_format='+0.0%;-0.0%'
re_=19; wm.cell(re_,1,'Model vs PVGIS 2005–23').font=BOLD
for k in range(5): c=wm.cell(re_,7+k,f'={L(7+k)}{ra}/{L(17+k)}{ra}-1'); c.number_format='+0.0%;-0.0%'
rf=20; wm.cell(rf,1,'Annual energy of 5 kWp (kWh)').font=BOLD
for k in range(5): c=wm.cell(rf,7+k,f'={L(7+k)}{ra}*{PSTC}'); c.number_format='#,##0'
wm.cell(22,1,'Best of the five tilts (model):').font=BOLD
wm.cell(22,2,f'=INDEX($G$3:$K$3,MATCH(MAX(G{ra}:K{ra}),G{ra}:K{ra},0))')
wm.cell(23,1,'PVGIS optimum (2005–2023, PVcalc optimalangles):').font=BOLD; wm.cell(23,2,'32° tilt, azimuth 8° (W of S), 1325 kWh/kWp, CF 15.1 %').font=BLUE
wm.cell(24,1,'Best tilt from 1° sweep (model):').font=BOLD; wm.cell(24,2,'=Tilt_Sweep!E3').font=GRN
for r in range(4,21):
    for j in range(2,22):
        if wm.cell(r,j).number_format=='General': wm.cell(r,j).number_format='0.0'
wm.column_dimensions['A'].width=30
for j in range(2,22): wm.column_dimensions[L(j)].width=11
wm.row_dimensions[3].height=45
wm['L2']='PVGIS values: blue = typed from PVGIS 5.3 API output (seriescalc 2023 and PVcalc 2005–2023, 1 kWp, 14 % loss).'; wm['L2'].font=BLUE

# ---------------- Tilt sweep ----------------
wt=wb.create_sheet('Tilt_Sweep'); hdr(wt,1,['Tilt (°)','H_POA (kWh/m²)','Yield (kWh/kWp)'])
for i,x in sweep.iterrows():
    wt.cell(i+2,1,int(x.tilt)).font=BLUE; c=wt.cell(i+2,2,round(x.H_poa_kWh_m2,1)); c.font=BLUE; c=wt.cell(i+2,3,round(x.yield_kWh_kWp,1)); c.font=BLUE
N=len(sweep)+1
wt['E1']='Maximum yield (kWh/kWp)'; wt['E2']=f'=MAX(C2:C{N})'
wt['F1']='Best tilt (°)'; wt['E3']=f'=INDEX(A2:A{N},MATCH(E2,C2:C{N},0))'; wt['D3']='Best tilt (°):'
wt['E4']=f'=E2/C43-1'; wt['D4']='Gain vs 41°:'; wt['E4'].number_format='+0.0%'
wt['D6']='Values from model.py (same equations as Hourly_Model, tilt step 1°).'
for c in 'ABCDE': wt.column_dimensions[c].width=18

# ---------------- Daily / cloudy loss ----------------
wd=wb.create_sheet('Daily_CloudyLoss')
hdr(wd,1,['Date','Month','Daily GHI (kWh/m²)','Daily G0 horiz. (kWh/m²)','K_T = GHI/G0','Sky class','PVGIS PV 41° (kWh/kWp/day)','Model PV 41° (kWh/kWp/day)'])
for i,x in dd.iterrows():
    r=i+2
    wd.cell(r,1,pd.to_datetime(x.t).date()).number_format='yyyy-mm-dd'; wd.cell(r,1).font=BLUE
    wd.cell(r,2,f'=MONTH(A{r})')
    wd.cell(r,3,f'=SUMIFS(Hourly_Model!$M$2:$M${HR},Hourly_Model!$D$2:$D${HR},A{r})/1000')
    wd.cell(r,4,f'=SUMIFS(Hourly_Model!$N$2:$N${HR},Hourly_Model!$D$2:$D${HR},A{r})/1000')
    wd.cell(r,5,f'=C{r}/D{r}'); wd.cell(r,5).number_format='0.00'
    wd.cell(r,6,f'=IF(E{r}>=$L$3,"clear",IF(E{r}<$L$4,"overcast","partly cloudy"))')
    wd.cell(r,7,float(x.E_pvgis41)).font=BLUE
    wd.cell(r,8,f'=SUMIFS(Hourly_Model!$AD$2:$AD${HR},Hourly_Model!$D$2:$D${HR},A{r})/{PSTC}')
    for j in (3,4,8): wd.cell(r,j).number_format='0.00'
DR=len(dd)+1
wd['K2']='Thresholds'; wd['K2'].font=BOLD
wd['K3']='Clear if K_T ≥'; wd['L3']=0.60; wd['K4']='Overcast if K_T <'; wd['L4']=0.30
for c in ('L3','L4'): wd[c].font=BLUE; wd[c].fill=YEL
hdr(wd,6,['Month','Clear days','Partly cloudy days','Overcast days','Mean clear-day PV','Mean partly-cloudy PV','Mean overcast PV','Loss partly cloudy','Loss overcast','Clear-sky potential (kWh/kWp)','Actual PVGIS (kWh/kWp)','Lost to clouds'],col=11)
for m in range(1,13):
    r=6+m; R=f'$B$2:$B${DR}'; S=f'$F$2:$F${DR}'; E=f'$G$2:$G${DR}'
    wd.cell(r,11,m)
    wd.cell(r,12,f'=COUNTIFS({R},K{r},{S},"clear")'); wd.cell(r,13,f'=COUNTIFS({R},K{r},{S},"partly cloudy")'); wd.cell(r,14,f'=COUNTIFS({R},K{r},{S},"overcast")')
    wd.cell(r,15,f'=AVERAGEIFS({E},{R},K{r},{S},"clear")')
    wd.cell(r,16,f'=IF(M{r}>0,AVERAGEIFS({E},{R},K{r},{S},"partly cloudy"),"")')
    wd.cell(r,17,f'=IF(N{r}>0,AVERAGEIFS({E},{R},K{r},{S},"overcast"),"")')
    wd.cell(r,18,f'=IF(P{r}="","",1-P{r}/O{r})'); wd.cell(r,19,f'=IF(Q{r}="","",1-Q{r}/O{r})')
    wd.cell(r,20,f'=(L{r}+M{r}+N{r})*O{r}'); wd.cell(r,21,f'=SUMIFS({E},{R},K{r})'); wd.cell(r,22,f'=1-U{r}/T{r}')
    for j in (15,16,17,20,21): wd.cell(r,j).number_format='0.00'
    for j in (18,19,22): wd.cell(r,j).number_format='0.0%'
r=19; wd.cell(r,11,'Year').font=BOLD
for j in (12,13,14,20,21): wd.cell(r,j,f'=SUM({L(j)}7:{L(j)}18)').font=BOLD
wd.cell(r,22,'=1-U19/T19').number_format='0.0%'
wd.cell(r,15,f'=AVERAGEIFS($G$2:$G${DR},$F$2:$F${DR},"clear")'); wd.cell(r,16,f'=AVERAGEIFS($G$2:$G${DR},$F$2:$F${DR},"partly cloudy")'); wd.cell(r,17,f'=AVERAGEIFS($G$2:$G${DR},$F$2:$F${DR},"overcast")')
wd.cell(20,11,'Energy lost on overcast days (kWh/kWp/yr)').font=BOLD
wd.cell(20,17,f'=SUMPRODUCT((L7:L18>=0)*N7:N18*O7:O18)-SUMIFS($G$2:$G${DR},$F$2:$F${DR},"overcast")')
wd.cell(21,11,'Energy lost on partly cloudy days (kWh/kWp/yr)').font=BOLD
wd.cell(21,17,f'=SUMPRODUCT(M7:M18*O7:O18)-SUMIFS($G$2:$G${DR},$F$2:$F${DR},"partly cloudy")')
for c in ('O19','P19','Q19','Q20','Q21'): wd[c].number_format='0.00'
wd.cell(23,11,'Method: each day is classed by its daily clearness index K_T. The loss is measured against the mean PV output of the clear days of the same month (removes the seasonal effect).')
for j in range(1,23): wd.column_dimensions[L(j)].width=13
wd.row_dimensions[6].height=45; wd.row_dimensions[1].height=45

# ---------------- Economics ----------------
we=wb.create_sheet('Economics'); we['A1']='Simple payback of a 5 kWp rooftop system (30° south roof)'; we['A1'].font=TITLE
we.column_dimensions['A'].width=52;
for c in 'BCDE': we.column_dimensions[c].width=16
rows=[('Price, low tier incl. taxes (TL/kWh)',f'=({names["EPDK active energy, residential low tier"]}*(1+{names["Electricity consumption tax (on energy part)"]})+{names["EPDK distribution fee, residential LV"]})*(1+{names["VAT (KDV) residential electricity"]})'),
('Price, high tier incl. taxes (TL/kWh)',f'=({names["EPDK active energy, residential high tier"]}*(1+{names["Electricity consumption tax (on energy part)"]})+{names["EPDK distribution fee, residential LV"]})*(1+{names["VAT (KDV) residential electricity"]})'),
('Annual energy, 5 kWp at 30° (kWh)','=Monthly_Annual!I20'),
('Annual saving, low tier (TL/yr)','=B5*B3'),('Annual saving, high tier (TL/yr)','=B5*B4')]
for i,(a,f) in enumerate(rows,3):
    we.cell(i,1,a); c=we.cell(i,2,f); c.font=GRN if '!' in f else BLK; c.number_format='#,##0.00' if i<5 else '#,##0'
hdr(we,10,['Simple payback (years) = investment / annual saving','Investment (TL)','Low tier','High tier'])
for i,k in enumerate(['low','central','high']):
    r=11+i; we.cell(r,1,f'Investment – {k}'); we.cell(r,2,f'={names["Investment cost – "+k]}').font=GRN
    we.cell(r,3,f'=B{r}/$B$6'); we.cell(r,4,f'=B{r}/$B$7')
    we.cell(r,2).number_format='#,##0'; we.cell(r,3).number_format='0.0'; we.cell(r,4).number_format='0.0'
notes=['Assumptions: every kWh produced replaces a kWh bought at the tariff (self-consumption or netting); no battery; no degradation, O&M, inverter replacement, discounting or tariff increase.',
'A 5 kWp system makes ≈6,400 kWh/yr, more than an average Turkish household uses (≈3,000–5,000 kWh/yr). Surplus sold to the grid earns less than the retail price, so the real payback is longer for small consumers.',
'Households above the EPDK limit (3,000 kWh/yr from 2027, 4,000 kWh/yr in 2026) pay the higher SKTT price → shorter payback.',
'Tariff source: EPDK electricity tariff tables valid from 4 Apr 2026 (Board Decision 14461; Resmî Gazete 33214), https://www.epdk.gov.tr/Detay/Icerik/3-1327/elektrik-faturalarina-esas-tarife-tablolari ; residential prices unchanged at 1 Oct 2026 and in EPDK decision of 30 Oct 2026 (Bloomberg HT, 30 Oct 2026).',
'Cost source: Milliyet Uzmanpara (2026): 5 kW grid-tied home system without battery 150–210 thousand TL.']
for i,t in enumerate(notes): we.cell(16+i,1,t)

# ---------------- Phone ----------------
wp=wb.create_sheet('Phone_Measurements'); wp['A1']='Phone light sensor (phyphox "Light") – phone tilted 41° towards south, every hour 10:00–15:00 local time'; wp['A1'].font=TITLE
wp['A2']='Fill in the yellow cells (date, cloud note, lux). Never point the phone at the Sun. Modelled clear-sky values are for 15 Nov 2026 (Haurwitz clear-sky GHI + Erbs + isotropic, 41°).'
hdr(wp,4,['Day','Date','Local time','Measured illuminance (lux)','Measured normalised (lux / day max)','Measured as W/m² (lux / 110)','Model G41 clear sky (W/m²)','Model normalised','Difference of normalised shape','Sun height (°)','Clouds / notes'])
r=5
for day in (1,2):
    first=r
    for _,x in phone.iterrows():
        wp.cell(r,1,f'Clear day {day}'); c=wp.cell(r,2); c.fill=YEL; c.number_format='yyyy-mm-dd'
        wp.cell(r,3,x.local_time); c=wp.cell(r,4); c.fill=YEL
        wp.cell(r,5,f'=IF(D{r}="","",D{r}/MAX($D${first}:$D${first+5}))'); wp.cell(r,6,f'=IF(D{r}="","",D{r}/{names["Illuminance → irradiance factor"]})')
        wp.cell(r,7,float(x.G41_model_Wm2)).font=BLUE; wp.cell(r,8,f'=G{r}/MAX($G${first}:$G${first+5})')
        wp.cell(r,9,f'=IF(E{r}="","",E{r}-H{r})'); wp.cell(r,10,float(x.elev_deg)).font=BLUE; wp.cell(r,11).fill=YEL
        for j in (5,8,9): wp.cell(r,j).number_format='0.00'
        r+=1
wp.cell(r+1,1,'RMS difference of normalised shapes (both days):').font=BOLD
wp.cell(r+1,5,f'=IF(COUNT(D5:D16)=0,"",SQRT(SUMPRODUCT((I5:I16)^2)/COUNT(I5:I16)))')
wp.cell(r+2,1,'Format example: Date 2026-11-15, Local time 12:00, lux 92000 (direct sun, clean sensor). Phone sensors saturate near 60–100 klx on some models – note it if the value stops rising.')
for j,wdt in zip(range(1,12),[12,12,10,16,16,14,16,12,14,10,24]): wp.column_dimensions[L(j)].width=wdt
wp.row_dimensions[4].height=45

# ---------------- Phone measurements ----------------
import os
if os.path.exists(f'{O}/seg.pkl'):
    seg=pd.read_pickle(f'{O}/seg.pkl'); Dm=pd.read_pickle(f'{O}/meas.pkl')
    wsp=wb.create_sheet('Phone_Data'); bd=Border(*(Side('thin'),)*4)
    wsp['A1']='Phyphox "Light" measurements (raw .phyphox files in data/phyphox)'; wsp['A1'].font=BOLD
    hh=['Rec.','Day','Start (TRT)','End (TRT)','Samples','Median (lx)','P10 (lx)','P90 (lx)','Max (lx)','≈ Irradiance (W/m²) = median/110','Clear-sky model G41 (W/m²)','Measured / clear-sky']
    for j,v in enumerate(hh,1): c=wsp.cell(3,j,v); c.font=H; c.border=bd; c.alignment=Alignment(wrap_text=True)
    for i,r in seg.iterrows():
        R=4+i
        for j,v in enumerate([i+1,r.day,r.start.strftime('%H:%M:%S'),r.end.strftime('%H:%M:%S'),int(r.n),float(r['median']),float(r.p10),float(r.p90),float(r.mx)],1): wsp.cell(R,j,v).font=BLUE
        wsp.cell(R,10,f"=F{R}/{names['Illuminance → irradiance factor']}").number_format='0'
        wsp.cell(R,11,round(float(r.G41_clear),1)).font=BLUE; wsp.cell(R,12,f"=J{R}/K{R}").number_format='0.00'
    st0=4+len(seg)+2; wsp.cell(st0,1,'Raw samples').font=BOLD
    for j,v in enumerate(['Day','Local time (TRT)','Illuminance (lx)'],1): c=wsp.cell(st0+1,j,v); c.font=H; c.border=bd
    for k,(_,r) in enumerate(Dm.sort_values('clock').iterrows()):
        wsp.cell(st0+2+k,1,r.day); wsp.cell(st0+2+k,2,r.clock.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]); wsp.cell(st0+2+k,3,float(r.lux))
    for c_,w_ in zip('ABCDEFGHIJKL',[7,9,11,11,9,11,10,10,10,16,16,12]): wsp.column_dimensions[c_].width=w_
    wsp.row_dimensions[3].height=45
wb.calculation.fullCalcOnLoad=True
wb.save(f'{O}/workbook.xlsx'); print('saved')
