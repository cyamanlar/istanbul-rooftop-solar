import copy, json, pandas as pd
import docx
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

from config import OUT as O, DATA as D, FIG
S=json.load(open(f'{O}/summary.json')); mon=pd.read_csv(f'{O}/monthly.csv')
pv=json.load(open(f'{D}/pvgis_pvcalc.json')); pv23=json.load(open(f'{D}/pvgis_2023_seriescalc_pv.json'))
ex=pd.read_pickle(f'{O}/extra.pkl'); cl, cnt = ex['cl'], ex['cnt']
seg=pd.read_pickle(f'{O}/seg.pkl')
SEGROWS=[['Day','Time (TRT)','n','Median (klx)','10–90 % (klx)','≈ W m^{−2}','Clear-sky model (W m^{−2})','Measured / clear-sky']]+[[r.day,f"{r.start.strftime('%H:%M:%S')}–{r.end.strftime('%H:%M:%S')}",str(r.n),f"{r['median']/1000:.1f}",f"{r.p10/1000:.1f}–{r.p90/1000:.1f}",f"{r.W_meas:.0f}",f"{r.G41_clear:.0f}",f"{r.ratio:.2f}"] for i,r in seg.iterrows()]
TITLE='Rooftop Solar Power for İstanbul Homes: Hourly Modelling of a 5 kWp System with PVGIS Data'

d=docx.Document()
sec=d.sections[0]; sec.page_width=Cm(21); sec.page_height=Cm(29.7)
for m in ('left_margin','right_margin','top_margin','bottom_margin'): setattr(sec,m,Cm(2.5))
st=d.styles['Normal']; st.font.name='Times New Roman'; st.font.size=Pt(11)
st.element.rPr.rFonts.set(qn('w:eastAsia'),'Times New Roman'); st.paragraph_format.first_line_indent=Cm(1.0)

BLACK=RGBColor(0,0,0)
def para(text='',bold=False,italic=False,size=11,align='both',indent=True,before=2,after=2,keep=False):
    p=d.add_paragraph(); pf=p.paragraph_format; pf.line_spacing=1.0
    pf.alignment={'both':WD_ALIGN_PARAGRAPH.JUSTIFY,'center':WD_ALIGN_PARAGRAPH.CENTER,'left':WD_ALIGN_PARAGRAPH.LEFT}[align]
    pf.space_before=Pt(before); pf.space_after=Pt(after)
    if not indent: pf.first_line_indent=Cm(0)
    if keep: pf.keep_with_next=True
    if text: rich(p,text,bold,italic,size)
    return p
def rich(p,text,bold=False,italic=False,size=11):
    # **bold** and _sub_ and ^sup^ markup
    import re
    for tok in re.split(r'(\*\*.+?\*\*|_\{.+?\}|\^\{.+?\}|\*[^*]+?\*)',text):
        if not tok: continue
        b,i,sub,sup=bold,italic,False,False
        if tok.startswith('**'): rich(p,tok[2:-2],True,italic,size); continue
        elif tok.startswith('_{'): tok=tok[2:-1]; sub=True
        elif tok.startswith('^{'): tok=tok[2:-1]; sup=True
        elif tok.startswith('*') and len(tok)>2: tok=tok[1:-1]; i=True
        r=p.add_run(tok); r.bold=b; r.italic=i; r.font.size=Pt(size); r.font.color.rgb=BLACK; r.font.name='Times New Roman'
        if sub: r.font.subscript=True
        if sup: r.font.superscript=True
    return p
def h(text,level=1):
    return para(text,bold=True,align='left',indent=False,before=8 if level==1 else 4,after=2,keep=True)
def cap(label,text,above=False):
    p=para(align='center',indent=False,before=2 if not above else 8,after=6 if not above else 3,keep=above)
    r=p.add_run(label+' '); r.bold=True; r.italic=True; r.font.size=Pt(11); r.font.color.rgb=BLACK
    rich(p,text,size=11); return p
def img(path,w):
    p=para(align='center',indent=False,before=6,after=0,keep=True); p.add_run().add_picture(path,width=Cm(w)); return p
def borders(t):
    tbl=t._tbl; tblPr=tbl.tblPr
    b=OxmlElement('w:tblBorders')
    for e in ('top','left','bottom','right','insideH','insideV'):
        x=OxmlElement(f'w:{e}'); x.set(qn('w:val'),'single'); x.set(qn('w:sz'),'4'); x.set(qn('w:color'),'000000'); b.append(x)
    tblPr.append(b)
def table(rows,widths,size=9,first_left=True):
    t=d.add_table(rows=len(rows),cols=len(rows[0])); t.alignment=WD_TABLE_ALIGNMENT.CENTER; borders(t); t.autofit=False
    lay=OxmlElement('w:tblLayout'); lay.set(qn('w:type'),'fixed'); t._tbl.tblPr.append(lay)
    for j,wd_ in enumerate(widths): t.columns[j].width=Cm(wd_)
    for gc,wd_ in zip(t._tbl.tblGrid.findall(qn('w:gridCol')),widths): gc.set(qn('w:w'),str(int(wd_*567)))
    for i,row in enumerate(rows):
        trPr=t.rows[i]._tr.get_or_add_trPr(); cs=OxmlElement('w:cantSplit'); trPr.append(cs)
        for j,v in enumerate(row):
            c=t.cell(i,j); c.width=Cm(widths[j]); p=c.paragraphs[0]
            p.paragraph_format.first_line_indent=Cm(0); p.paragraph_format.space_before=Pt(1); p.paragraph_format.space_after=Pt(1)
            p.alignment=WD_ALIGN_PARAGRAPH.LEFT if (j==0 and first_left) else WD_ALIGN_PARAGRAPH.CENTER
            rich(p,str(v),bold=(i==0),size=size)
            if i<len(rows)-1: p.paragraph_format.keep_with_next=True
    return t
def img2(p1,p2,c1,c2,w=7.6):
    t=d.add_table(rows=2,cols=2); t.alignment=WD_TABLE_ALIGNMENT.CENTER
    for j,(pp,cc) in enumerate(((p1,c1),(p2,c2))):
        a=t.cell(0,j).paragraphs[0]; a.alignment=WD_ALIGN_PARAGRAPH.CENTER; a.paragraph_format.first_line_indent=Cm(0); a.add_run().add_picture(pp,width=Cm(w))
        b=t.cell(1,j).paragraphs[0]; b.alignment=WD_ALIGN_PARAGRAPH.CENTER; b.paragraph_format.first_line_indent=Cm(0)
        r=b.add_run(cc[0]+' '); r.bold=True; r.italic=True; r.font.size=Pt(10); rich(b,cc[1],size=10)
def pagebreak():
    p=d.add_paragraph(); p.add_run().add_break(WD_BREAK.PAGE)

# ---------------- content ----------------
para(TITLE,bold=True,align='center',indent=False,before=0,after=6)
h('ABSTRACT')
para('Rooftop photovoltaic (PV) systems turn the solar part of the energy cycle directly into household electricity. This study estimates the output of a 5 kWp south-facing rooftop system in İstanbul from one year (2023) of hourly PVGIS 5.3 data (SARAH-3 satellite irradiance, ERA5 air temperature) at the İTÜ Ayazağa campus. Global horizontal irradiance was split into beam and diffuse parts with the Erbs model, transposed to panels tilted 0°, 20°, 30°, 41° and 60° with the isotropic-sky model, and converted to AC power with a NOCT cell-temperature correction. The site received 1455 kWh m^{−2} of global irradiance, 51 % of the extraterrestrial value. The modelled annual yield is 1185, 1277, 1284, 1263 and 1158 kWh kWp^{−1} for the five tilts (capacity factor 13.2–14.7 %), within ±2 % of the PVGIS estimate for 20–60°. The best tilt is 28° (PVGIS long-term optimum 32°), lower than the latitude because 71 % of the sunlight falls in the summer half-year. An overcast day produces on average 83 % less than a clear day of the same month, and clouds removed 32 % of the clear-sky potential. With the April 2026 EPDK household tariff (3.24–4.86 TL kWh^{−1} with taxes) and an investment of 150 000–210 000 TL, the simple payback time is 4.8–10.1 years (central case 5.8–8.7 years). Rooftop solar is therefore worth installing on unshaded south-facing roofs in İstanbul.')
p=para(indent=False); rich(p,'Keywords: ',bold=True,italic=True); rich(p,'solar radiation, Erbs model, isotropic sky, photovoltaic yield, İstanbul',italic=True)

h('1. INTRODUCTION')
para('The Sun delivers about 1361 W m^{−2} to the top of the atmosphere (the solar constant). On its way to the ground this flux is reflected by clouds, scattered by molecules and aerosols and absorbed by water vapour and ozone, so that on a global and annual average only about half of the incoming sunlight is absorbed at the surface (global energy budget). What remains arrives as a direct (beam) part from the solar disc and a diffuse part from the whole sky, and the energy received by a surface depends on the cosine of the angle between the surface normal and the Sun (Lambert’s cosine law). These are exactly the processes that decide how much electricity a solar panel can produce.')
para('Türkiye has a high solar resource, and rooftop PV for self-consumption has been allowed for households without a generation licence. İstanbul, at 41° N on the Marmara coast, has clear summers but cloudy, rainy winters dominated by mid-latitude cyclones, so the seasonal cycle of cloudiness strongly modifies the astronomical cycle of insolation. Satellite-based data sets such as PVGIS (Photovoltaic Geographical Information System) of the European Commission Joint Research Centre (JRC) now give hourly irradiance for any address (Huld et al., 2012; JRC, 2026). The aim of this study is to use one year of hourly PVGIS data for İstanbul to (i) split the irradiance into beam and diffuse parts with the Erbs et al. (1982) model, (ii) compute the irradiance on south-facing panels with different tilts with the isotropic-sky model (Liu & Jordan, 1963), (iii) estimate the output of a 5 kWp system with a temperature correction, (iv) quantify the loss on cloudy days, (v) evaluate the simple payback time with the current Energy Market Regulatory Authority (EPDK) household tariff, and (vi) compare the model with satellite clear-day data and with phone light-sensor measurements.')

h('2. STUDY REGION, DATA AND METHOD')
h('2.1 Study Region',2)
para('The calculation point is the İstanbul Technical University (İTÜ) Ayazağa (Maslak) campus at 41.105° N, 29.025° E and 97 m above sea level, on the European side of İstanbul. The climate is transitional between Mediterranean and Black Sea types: summers are warm and mostly clear, while from November to March frequent fronts bring overcast skies and rain. At this latitude the noon sun height ranges from 25.4° at the December solstice to 72.3° at the June solstice, and the day length from about 9 h to 15 h. The PVGIS horizon, computed from a digital elevation model, was included; shading by neighbouring buildings was not.')
h('2.2 Data',2)
para('Hourly data for 1 January–31 December 2023 (the latest complete year, 8760 h) were taken from the PVGIS 5.3 web service (JRC, 2026): beam and diffuse irradiance on a horizontal plane from the PVGIS-SARAH3 satellite record, and 2-m air temperature and 10-m wind speed from the ERA5 reanalysis. Time stamps are in UTC (HH:10); local time (TRT) is UTC + 3 h. Nine daytime hours are missing in the file and were kept as zero (≈0.1 % of the annual energy). Only global horizontal irradiance (*GHI* = beam + diffuse) was used as model input; the PVGIS beam/diffuse split was kept to validate the Erbs model. As benchmarks, the PVGIS PV estimates for a 1 kWp crystalline-silicon system with 14 % system loss were taken for 2023 and for the 2005–2023 average at the same point. The electricity price is the EPDK tariff table valid from 4 April 2026 (EPDK, 2026a), which was not changed for households on 1 October 2026 (EPDK, 2026b), and the investment cost is the 2026 market range for a 5 kW grid-connected home system without battery (Milliyet Uzmanpara, 2026).')
h('2.3 Method',2)
para('**Sun geometry.** The declination δ, the equation of time and the hour angle ω were computed from the day number with the Spencer series (Duffie & Beckman, 2013); the solar zenith angle follows from cos *Z* = sin φ sin δ + cos φ cos δ cos ω. The computed sun height agrees with the PVGIS value within 0.3°. The extraterrestrial irradiance on a horizontal plane is *G*_{0h} = *I*_{sc} *E*_{0} cos *Z*, with *I*_{sc} = 1361 W m^{−2} and the Earth–Sun distance factor *E*_{0}.')
para('**Erbs decomposition.** The hourly clearness index *k*_{t} = *GHI*/*G*_{0h} gives the diffuse fraction (Erbs et al., 1982): *k*_{d} = 1 − 0.09*k*_{t} for *k*_{t} ≤ 0.22; *k*_{d} = 0.9511 − 0.1604*k*_{t} + 4.388*k*_{t}^{2} − 16.638*k*_{t}^{3} + 12.336*k*_{t}^{4} for 0.22 < *k*_{t} ≤ 0.80; *k*_{d} = 0.165 for *k*_{t} > 0.80. Then *DHI* = *k*_{d}*GHI* and the direct normal irradiance *DNI* = (*GHI* − *DHI*)/cos *Z*; with the sun below 5° all irradiance is treated as diffuse.')
para('**Isotropic-sky transposition.** For a south-facing panel of tilt β the plane-of-array irradiance is *G*_{POA} = *DNI* max(cos θ, 0) + *DHI* (1 + cos β)/2 + ρ *GHI* (1 − cos β)/2, where cos θ = sin δ sin(φ − β) + cos δ cos(φ − β) cos ω and ρ = 0.2 is the ground albedo (Liu & Jordan, 1963). β = 0°, 20°, 30°, 41° and 60° were computed, and 0–90° in 1° steps to find the optimum.')
para('**PV output.** The cell temperature is *T*_{c} = *T*_{air} + (NOCT − 20)/800 · *G*_{POA} with NOCT = 45 °C, and the AC power of the 5 kWp system is *P* = 5 kWp · (*G*_{POA}/1000) · [1 − 0.004 (*T*_{c} − 25)] · (1 − 0.14). The specific yield is the energy per kWp and the capacity factor CF = yield / 8760 h. All steps are live formulas in the Excel workbook and were cross-checked with a Python script.')
para('**Cloudy days and economics.** Each day was classed by its daily clearness index *K*_{T} = ΣGHI/ΣG_{0h} as clear (≥ 0.60), partly cloudy or overcast (< 0.30); the loss is measured against the mean PVGIS output of the clear days of the same month. The simple payback time is the investment divided by the annual saving (annual energy × tariff with taxes).')
para('**Phone measurement.** The illuminance was recorded with the phyphox “Light” sensor of a smartphone on two days: on 11 November 2026 between 11:52 and 12:57 TRT in nine short recordings, and on 12 November 2026 in three recordings at about 11:19, 12:26 and 13:31 TRT (17–91 s each, 14 214 samples in total; raw files kept with the workbook). The clock time of every sample was reconstructed from the start/pause time stamps stored in the phyphox files. The median illuminance of each recording was converted to an approximate irradiance with 110 lx per W m^{−2} and compared with the modelled clear-sky irradiance on a 41° south plane at the same time (Haurwitz clear-sky *GHI* → Erbs → isotropic sky). The daily shape of the model was also checked against the two clearest November days of the PVGIS record.')

h('3. ANALYSIS')
h('3.1 Irradiance and Validation of the Erbs Model',2)
para(f'In 2023 the site received **1455 kWh m^{{−2}}** of global horizontal irradiance against 2837 kWh m^{{−2}} at the top of the atmosphere, an annual clearness index of **0.51** – about half of the extraterrestrial radiation reached the ground, as in the global energy budget. 71 % of the annual *GHI* fell in April–September. The Erbs model gives a diffuse fraction of 0.41 against 0.43 in PVGIS; the hourly values correlate well (r = 0.98, RMSE = 23 W m^{{−2}}, bias −9 W m^{{−2}}, Figure 1), but Erbs underestimates the diffuse part at high diffuse irradiance (broken clouds).')
img2(f'{FIG}/fig3_erbs.png',f'{FIG}/fig2_tilt.png',('Figure 1.','Hourly diffuse irradiance: Erbs model against PVGIS (sun > 5°), 2023.'),('Figure 2.','Annual yield against tilt: model (line), PVGIS 2023 (×), PVGIS 2005–2023 (○).'))

h('3.2 Monthly and Annual Yield, Best Tilt and Capacity Factor',2)
rows=[['Tilt','H on panel (kWh m^{−2})','Model yield (kWh kWp^{−1})','Model CF','PVGIS 2023 (kWh kWp^{−1})','Model − PVGIS 2023','PVGIS 2005–23 (kWh kWp^{−1})','PVGIS CF']]
for b in [0,20,30,41,60]:
    a=S['ann'][str(b)]; p23=pv23[str(b)]['E_y']; lt=pv[f'a{b}']['tot']['E_y']
    rows.append([f'{b}°',f"{a['H']:.0f}",f"{a['Y']:.0f}",f"{100*a['CF']:.1f} %",f'{p23:.0f}',f"{100*(a['Y']/p23-1):+.1f} %",f'{lt:.0f}',f'{100*lt/8760:.1f} %'])
rows.append(['Best','–','28°: 1285','14.7 %','30° (of 5)','–','32°, az. 8° W: 1325','15.1 %'])
cap('Table 1.','Annual irradiation on the panel, specific yield and capacity factor (CF): model and PVGIS (1 kWp, 14 % loss) for the same point.',above=True)
table(rows,[1.2,2.0,2.1,1.5,2.1,1.9,2.4,1.5])
para(f'Table 1 and Figure 2 show that the yield curve is flat near its maximum: the model gives the highest annual yield at **28°** (1285 kWh kWp^{{−1}}), PVGIS 2023 at 30° among the five tilts, and the PVGIS 2005–2023 optimum is 32°. All tilts between 20° and 41° are within 2 % of the maximum; the “tilt = latitude” rule (41°) gives 1.7 % less and 60° gives 10 % less. The optimum is lower than the latitude because most of the energy arrives in the clear, high-sun summer half-year and because a flatter panel sees more of the diffuse sky. The model agrees with PVGIS 2023 within ±2 % for 20–60° (+0.7 % at 30°, −0.5 % at 41°); only the flat panel is 5.5 % higher because the model has no reflection (angle-of-incidence) loss, which is largest for low sun on a flat panel. 2023 was about 3 % below the long-term PVGIS mean. At 30°, the 5 kWp system produces **≈ 6420 kWh yr^{{−1}}** (CF = 14.7 %, PVGIS 14.6 % for 2023 and 15.1 % long-term). The temperature correction costs about 6 % of the annual energy; the cell temperature reaches 66 °C on hot July afternoons.',before=6)
mtab=[['Tilt']+list('JFMAMJJASOND')+['Year']]
for b in [0,20,30,41,60]: mtab.append([f'{b}°']+[f'{v:.0f}' for v in mon[f'Y_{b}']]+[f"{mon[f'Y_{b}'].sum():.0f}"])
mtab.append(['PVGIS 41°']+[f'{v:.0f}' for v in pv23['41']['E_m']]+[f"{pv23['41']['E_y']:.0f}"])
cap('Table 2.','Monthly specific yield (kWh kWp^{−1}) of the model and of PVGIS 2023 at 41°.',above=True)
table(mtab,[2.0]+[0.98]*12+[1.25],size=8.5)
img(f'{FIG}/fig1_monthly.png',13.0); cap('Figure 3.','Monthly specific yield for the five tilts; crosses show the PVGIS 2023 output at 41°.')
para('The seasonal pattern follows the cosine law: in December the 60° panel gives 61 kWh kWp^{−1} against 40 for the flat panel, while in July the flat panel gives 179 against 137. July produces almost three times as much as December (Table 2, Figure 3).')

h('3.3 Loss on Cloudy Days',2)
ctab=[['Month']+list('JFMAMJJASOND'),['Clear days']+[str(cnt.loc[m,'clear']) for m in range(1,13)],['Overcast days']+[str(cnt.loc[m,'overcast']) for m in range(1,13)],
['Clear-day PV']+[f"{cl.loc[m,'clear']:.1f}" for m in range(1,13)],['Overcast-day PV']+[('–' if pd.isna(cl.loc[m,'overcast']) else f"{cl.loc[m,'overcast']:.1f}") for m in range(1,13)],
['Loss, overcast']+[('–' if pd.isna(cl.loc[m,'loss_overcast_%']) else f"{cl.loc[m,'loss_overcast_%']:.0f} %") for m in range(1,13)],
['Loss, partly cloudy']+[f"{cl.loc[m,'loss_partly_%']:.0f} %" for m in range(1,13)]]
para('Of the 365 days of 2023, 146 were clear, 137 partly cloudy and 82 overcast (Figure 4). An overcast day gave on average **83 % less** energy than a clear day of the same month (70 % in May–June, 87–89 % in November–February) and a partly cloudy day 26–50 % less (Table 3). If every day had been as clear as the clear days of its month, the panel would have produced 1861 instead of 1269 kWh kWp^{−1}: clouds removed **32 %** of the clear-sky potential, 330 kWh kWp^{−1} on overcast and 263 kWh kWp^{−1} on partly cloudy days. Overcast days are concentrated in November–March (13 in January, 12 in December, none in July), when mid-latitude cyclones and fronts cross the Marmara region.')
cap('Table 3.','Number of days and mean PVGIS daily output at 41° (kWh kWp^{−1} day^{−1}) by sky class, and the loss relative to clear days of the same month.',above=True)
table(ctab,[2.7]+[1.08]*12,size=8.5)
img(f'{FIG}/fig4_daily.png',13.5); cap('Figure 4.','Daily PVGIS PV output at 41° in 2023 by daily clearness index K_{T} (clear ≥ 0.60, overcast < 0.30).')

h('3.4 Simple Payback Time',2)
para('In the EPDK tariff table valid from 4 April 2026, the single-time residential low-voltage tariff consists of 0.4941 TL kWh^{−1} (low tier, ≤ 8 kWh day^{−1}) or 1.8958 TL kWh^{−1} (high tier) active energy and a 2.4249 TL kWh^{−1} distribution fee. With the 5 % electricity consumption tax on the energy part and 10 % VAT, the household price is **3.24 TL kWh^{−1}** (low tier) and **4.86 TL kWh^{−1}** (high tier). A 5 kW grid-connected home system without battery costs 150 000–210 000 TL in 2026.')
cap('Table 4.','Annual saving and simple payback time of a 5 kWp system at 30° (6420 kWh yr^{−1}).',above=True)
table([['','Low tier','High tier'],['Price incl. taxes (TL kWh^{−1})','3.24','4.86'],['Annual saving (TL yr^{−1})','20 789','31 183'],['Payback, investment 150 000 TL (yr)','7.2','4.8'],['Payback, investment 180 000 TL (yr)','8.7','5.8'],['Payback, investment 210 000 TL (yr)','10.1','6.7']],[6.5,3,3])
para('In the central case the system pays back in **about 9 years at the low tier and about 6 years at the high tier**, against a module lifetime of 25–30 years. The simple payback assumes that each kWh produced replaces a purchased kWh and ignores degradation (≈0.5 % yr^{−1}), maintenance, an inverter replacement, financing and future tariff increases. Since 6420 kWh exceeds a typical household consumption of 3000–5000 kWh yr^{−1}, surplus sold to the grid earns less than the retail price, so the payback is longer for small consumers and shorter for households above the EPDK limit of 3000 kWh yr^{−1} from 2027.',before=6)

h('3.5 Daily Shape and Phone Measurements',2)
img(f'{FIG}/fig5_phone.png',7.0); cap('Figure 5.','Normalised irradiance on a 41° south plane, 10:00–15:00 TRT: clear-sky model for 15 November and two clear November days of PVGIS 2023.')
para('The modelled clear-sky shape on the 41° plane rises from 65 % of the peak at 10:00 to a maximum near 12:50 TRT (solar noon at 29° E in mid-November) and falls to 79 % at 15:00 (Figure 5). As an independent check of this shape, the two clearest November days of 2023 in the PVGIS satellite record (7 and 10 November, daily *K*_{T} = 0.63 and 0.64) were transposed to the same 41° plane. They show the same morning rise and the same timing of the maximum (12:10–13:10 TRT) as the model; between 10:00 and 12:00 the normalised values differ by at most 0.06, while after 13:00 the satellite values fall faster (0.70–0.71 instead of 0.79 at 15:00; largest difference −0.13 at 14:00), which is consistent with afternoon haze over the city and with the HH:10 satellite time stamp.')
para('**Phone measurements of 11 and 12 November 2026.** Table 5 and Figure 6 summarise the twelve recordings. On 11 November the recording medians were 6–35 klx (about 57–320 W m^{−2}) between 11:52 and 12:57, and on 12 November 10.2 klx at 11:19, 2.7 klx at 12:26 and 4.0 klx at 13:31 (about 25–92 W m^{−2}). The clear-sky model for the same minutes gives 756–840 W m^{−2} (83–92 klx) on the 41° plane, so the ratio measured / clear-sky was only 0.07–0.38 on 11 November and 0.03–0.12 on 12 November. Both days were cloudy, in agreement with the İBB AKOM forecast of partly to mostly cloudy skies (İBB AKOM, 2026): the sensor received mainly diffuse light, and on 12 November the illuminance even fell towards noon instead of rising, because thicker cloud passed over. Within single recordings on 11 November the illuminance jumped by a factor of 3–10 (e.g. 5.2 → 52.8 klx at 12:43–12:45), showing short sunny breaks between clouds. These ratios match the PVGIS result that an overcast November day gives only about 10–15 % of a clear day (Table 3).')
cap('Table 5.','Phyphox illuminance recordings on 11 and 12 November 2026 compared with the clear-sky model on a 41° south plane.',above=True)
table(SEGROWS,[1.3,3.2,1.1,1.5,1.9,1.4,2.2,1.9],size=8.5)
img(f'{FIG}/fig6_phone_meas.png',14.5); cap('Figure 6.','Phyphox illuminance on 11 and 12 November 2026 (all samples and recording medians) and the clear-sky model on a 41° plane converted with 110 lx per W m^{−2}.')
para('**Limitations of the measurement.** The protocol asked for hourly readings from 10:00 to 15:00 on two clear days. The two days available (11 and 12 November) were cloudy, and the readings cover about 11:19–13:31 only, so they test the order of magnitude and the effect of clouds rather than the clear-sky daily shape; the clear-sky shape is checked with the PVGIS clear days above. A clear day with readings from 10:00 to 15:00 would complete the comparison.')
h('3.6 Sources of Error',2)
para('The Erbs model is an empirical global fit (bias −9 W m^{−2} for diffuse here); the isotropic model ignores circumsolar and horizon brightening and slightly underestimates the tilted irradiance on clear days; reflection, spectral and low-light losses were not modelled; the NOCT model ignores wind cooling; only one year (2023, ≈3 % below the long-term mean) was used; the satellite irradiance has an hourly uncertainty of about 5 % and nine missing hours; the point is the campus, not a specific roof with local shading; the payback uses a fixed tariff and a market cost range. The phone measurements cover two cloudy days around noon only; the sensor is uncalibrated and the tilt was held by hand.')

h('4. CONCLUSION')
para('One year of hourly PVGIS data for İstanbul shows that about half of the extraterrestrial solar radiation reaches the ground and that 41–43 % of it is diffuse. A 5 kWp south-facing rooftop system produces about 1280 kWh per kWp and year (≈ 6400 kWh, capacity factor ≈ 15 %), and the simple Erbs + isotropic-sky + temperature model reproduces the PVGIS result within ±2 % for usual roof tilts. The best tilt is 28–32°, clearly below the latitude rule of 41°, because the clear summer months dominate the annual sum and a flatter panel collects more diffuse light. Clouds remove about one-third of the clear-sky potential, and an overcast winter day gives only 10–15 % of a clear day. With the current EPDK household tariff the investment pays back in about 6–9 years, well within the lifetime of the panels, so rooftop solar is worthwhile for unshaded south-facing roofs in İstanbul, especially for households with high daytime consumption.')
h('ACKNOWLEDGMENTS')
para('I thank the European Commission Joint Research Centre for the free PVGIS data service.')
h('REFERENCES')
refs=['Duffie, J. A., & Beckman, W. A. (2013). Solar engineering of thermal processes (4th ed.). Wiley.',
'EPDK (Enerji Piyasası Düzenleme Kurumu) (2026a). Elektrik faturalarına esas tarife tabloları, 4 Nisan 2026 (Kurul Kararı 14461; Resmî Gazete 33214). Erişim tarihi: 11.11.2026 https://www.epdk.gov.tr/Detay/Icerik/3-1327/elektrik-faturalarina-esas-tarife-tablolari',
'EPDK (Enerji Piyasası Düzenleme Kurumu) (2026b). 2027 yılı son kaynak tedarik tarifesi limiti kararı, 30.10.2026 (reported by Bloomberg HT, 30.10.2026). Erişim tarihi: 11.11.2026 https://www.bloomberght.com/epdk-son-kaynak-tedarik-tarifesinde-limiti-dusurdu-3792931',
'Erbs, D. G., Klein, S. A., & Duffie, J. A. (1982). Estimation of the diffuse radiation fraction for hourly, daily and monthly-average global radiation. Solar Energy, 28(4), 293–302.',
'Huld, T., Müller, R., & Gambardella, A. (2012). A new solar radiation database for estimating PV performance in Europe and Africa. Solar Energy, 86(6), 1803–1815.',
'JRC (European Commission Joint Research Centre) (2026). Photovoltaic Geographical Information System (PVGIS) 5.3. Erişim tarihi: 11.11.2026 https://re.jrc.ec.europa.eu/pvg_tools/en/',
'İBB AKOM (İstanbul Büyükşehir Belediyesi Afet Koordinasyon Merkezi) (2026). İstanbul haftalık hava tahmini, 8–13 Kasım 2026 (7 Kasım 2026). Reported by Politikam. Erişim tarihi: 11.11.2026 https://www.politikam.com/akom-sibirya-soguklari-istanbul-kasim-2026-yagmur-hava-durumu-1',
'Liu, B. Y. H., & Jordan, R. C. (1963). The long-term average performance of flat-plate solar-energy collectors. Solar Energy, 7(2), 53–74.',
'Milliyet Uzmanpara (2026). Elektrik faturasını düşürmek isteyenler dikkat! Güneş paneli kurmanın maliyeti ne kadar? Erişim tarihi: 11.11.2026 https://uzmanpara.milliyet.com.tr/uzmanpara/elektrik-faturasini-dusurmek-isteyenler-dikkat-gunes-paneli-kurmanin-maliyeti-ne-kadar-7696820']
for r_ in refs:
    p=para(r_,size=10,align='left',indent=False,before=0,after=3); p.paragraph_format.left_indent=Cm(0.75); p.paragraph_format.first_line_indent=Cm(-0.75)

# ---------------- Appendix: homeowner note ----------------
pagebreak()
para('APPENDIX A. IS ROOFTOP SOLAR WORTH IT IN İSTANBUL? A ONE-PAGE NOTE TO A HOMEOWNER',bold=True,align='left',indent=False,before=0,after=6)
note=['**Short answer: yes.** For a home with a free, unshaded roof facing roughly south, a 5 kWp system pays for itself in about 6–9 years and then produces almost free electricity for another 15–20 years.',
'**How much electricity?** In İstanbul a 5 kWp system (about 10 modern panels, 25–30 m^{2} of roof) facing south and tilted about 30° produces about **6400 kWh per year**, or 1280 kWh for each kWp installed. This is more than an average Turkish household uses in a year (3000–5000 kWh). The capacity factor is about 15 %: on average over day and night the panels deliver 15 % of their rated power, which is normal at this latitude.',
'**Which angle and direction?** Face the panels south; south-east to south-west loses only a few percent. The best tilt in İstanbul is **28–32°**, not 41°, because most of our sunshine comes in the clear summer half-year. A normal pitched roof (25–35°) is therefore almost ideal. Avoid shade from chimneys, water tanks, neighbouring buildings and trees: a small shadow can cut the output of a whole string of panels.',
'**Seasons and clouds.** July gives about three times as much electricity as December. An overcast winter day gives only about one-tenth of a clear day, and in 2023 clouds removed about one-third of what an always-clear sky would have given. Judge the system by its yearly total; the grid supplies you when the sun does not.',
'**Money.** A 5 kW grid-connected system without a battery costs about 150 000–210 000 TL (2026). At today’s EPDK household tariff it saves about 21 000 TL a year at the low-tier price (3.24 TL kWh^{−1}) and about 31 000 TL at the high-tier price (4.86 TL kWh^{−1}). The simple payback is 7.2–10.1 years at the low tier and 4.8–6.7 years at the high tier. It is shortest for households with high daytime use (air conditioning, heat pump, electric car, home office) and for those above the EPDK limit (3000 kWh per year from 2027); it is longest for small consumers who would export most of the energy, because surplus sold to the grid earns less than the retail price. Size the system to your own consumption – check your last 12 bills first.',
'**Practical checklist.** (1) Have the roof’s structure checked and, for apartment buildings, get the approval of the building management; (2) apply to the distribution company (BEDAŞ on the European side, AYEDAŞ on the Anatolian side) for an unlicensed self-consumption connection; (3) compare at least three offers in TL per kWp and ask for module and inverter warranties; (4) clean the panels once or twice a year, because dust and pollen reduce output; (5) a battery is not needed for the payback – add it only if you want backup power.',
'**Bottom line.** A 30° south roof in İstanbul receives about 1590 kWh of sunlight per square metre each year. A rooftop PV system returns its cost in roughly one-third of its lifetime. It is worth it.']
for t_ in note: para(t_,indent=False,after=5)

for sec in d.sections:
    for hf in (sec.footer,):
        p=hf.paragraphs[0]; p.alignment=WD_ALIGN_PARAGRAPH.CENTER
        fld=OxmlElement('w:fldSimple'); fld.set(qn('w:instr'),'PAGE'); r=OxmlElement('w:r'); t=OxmlElement('w:t'); t.text='1'; r.append(t); fld.append(r); p._p.append(fld)
d.core_properties.author=''; d.core_properties.title=TITLE
d.save(f'{O}/report.docx'); print('ok')
