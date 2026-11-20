import docx, re
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
d=docx.Document()
s=d.sections[0]; s.page_width=Cm(21); s.page_height=Cm(29.7)
for m in ('left_margin','right_margin'): setattr(s,m,Cm(2.3))
s.top_margin=Cm(1.8); s.bottom_margin=Cm(1.6)
st=d.styles['Normal']; st.font.name='Times New Roman'; st.font.size=Pt(11); st.font.color.rgb=RGBColor(0,0,0)
st.element.rPr.rFonts.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}eastAsia','Times New Roman')
def P(t='',align='both',bold=False,after=4,before=0,size=11,italic=False,indent=None):
    p=d.add_paragraph(); pf=p.paragraph_format; pf.space_after=Pt(after); pf.space_before=Pt(before); pf.line_spacing=1.0
    pf.alignment={'both':WD_ALIGN_PARAGRAPH.JUSTIFY,'left':WD_ALIGN_PARAGRAPH.LEFT,'right':WD_ALIGN_PARAGRAPH.RIGHT,'center':WD_ALIGN_PARAGRAPH.CENTER}[align]
    if indent is not None: pf.left_indent=Cm(indent); pf.first_line_indent=Cm(-0.5)
    for tok in re.split(r'(\*\*.+?\*\*)',t):
        if not tok: continue
        b=bold
        if tok.startswith('**'): tok=tok[2:-2]; b=True
        r=p.add_run(tok); r.bold=b; r.italic=italic; r.font.size=Pt(size); r.font.color.rgb=RGBColor(0,0,0)
    return p
P('[Sender name and address]',align='left',after=8)
P('11 November 2026',align='right',after=8)
P('To the Governorship of İstanbul (T.C. İstanbul Valiliği)',align='left',bold=True,after=0)
P('Vilayet Konağı, Cağaloğlu, Fatih / İstanbul',align='left',after=8)
P('**Subject:** Recommendation to expand rooftop solar power on public buildings and homes in İstanbul',align='left',after=8)
P('Dear Governor,',align='left',after=6)
P('I recently studied the rooftop solar potential of İstanbul. I used one year (2023) of hourly satellite irradiance and temperature data from the European Commission’s PVGIS service for the İTÜ Maslak campus and modelled a 5 kWp rooftop photovoltaic (PV) system. I would like to share the main results and recommend that the Governorship support rooftop solar in the city.')
P('**Main findings.** (1) A south-facing roof in İstanbul receives about 1 455 kWh of sunlight per square metre per year on a horizontal surface and about 1 590 kWh on a 30° roof. (2) A 5 kWp system produces about 6 400 kWh per year (about 1 280 kWh per kWp, capacity factor 15 %), confirmed within ±2 % by the official PVGIS estimate. (3) The best tilt is 28–32°, so most ordinary pitched roofs, and flat roofs with simple frames, are suitable. (4) Output is highest from April to September, when air-conditioning demand peaks; cloudy winter days reduce output, removing about one-third of the clear-sky potential over the year. (5) At the current EPDK household tariff (3.24–4.86 TL/kWh including taxes) and a 2026 cost of 150 000–210 000 TL, a home system pays back in about 6–9 years, while panels last 25–30 years.')
P('**Recommendations.** I respectfully recommend that the Governorship:',after=3)
recs=['**Lead with public buildings.** Install rooftop PV on schools, hospitals, district governorships and other public buildings, in coordination with the Provincial Directorate of National Education and the Provincial Health Directorate. These buildings use electricity mainly in daytime and have large, often flat roofs; each 100 kWp would produce about 128 000 kWh a year.',
'**Strengthen earthquake and disaster resilience.** Combine PV with battery storage at disaster coordination centres, AFAD facilities, emergency assembly-area buildings and selected schools and health centres, so that lighting, communication and water pumps can keep running when the grid fails after an earthquake.',
'**Simplify and speed up approvals.** Work with the distribution companies BEDAŞ and AYEDAŞ and the district municipalities to create a one-stop procedure with clear deadlines for household and apartment-building rooftop applications, including structural and fire-safety checks.',
'**Inform citizens.** Support a public information campaign and an online rooftop-potential map for İstanbul, and encourage group purchasing for neighbourhoods and housing cooperatives to lower costs and ensure installation quality.',
'**Monitor and report.** Publish the yearly production of public rooftop systems, so that the savings and the reduction in fossil-fuel generation and air pollution can be followed openly.']
for i,r in enumerate(recs,1): P(f'{i}. {r}',indent=0.9,after=3)
P('Rooftop solar uses roof space that is already available, needs no new land, reduces peak summer demand on the grid and gives every district a local, clean energy source. I believe that a programme led by the Governorship would make İstanbul a model for other cities in Türkiye. I would be glad to share the full report and calculations.',before=3,after=8)
P('Respectfully yours,',align='left',after=22)
P('[Name Surname]',align='left',bold=True,after=0)
P('[Affiliation]',align='left',after=8)
P('Enclosure: Report “Rooftop Solar Power for İstanbul Homes” (November 2026). Data: European Commission JRC PVGIS 5.3; EPDK tariff tables of 4 April 2026.',align='left',size=9.5,italic=True,after=0)
d.core_properties.author=''
from config import OUT
d.save(f'{OUT}/letter_istanbul_governorship.docx'); print('ok')
