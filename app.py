"""Gold dashboard: sample-data exploration with independent chart periods."""
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

DATA = Path(__file__).parent / 'data'
PAPER, INK, GOLD = '#fbfbf8', '#1c1c18', '#a3780a'
HUES = {'China':'#b3392e', 'China + HK':'#b3392e', 'Russia':'#2e5fa3',
        'India':'#c98a1b', 'Turkey':'#8e4a8b', 'Poland':'#337f79',
        'UK + US':'#5b6b7a', 'UAE + Gulf':'#a99b8d', 'other':'#aeb4b8',
        'Czechia':'#6c71a5', 'Hungary':'#797034', 'Iraq':'#477969',
        'Kazakhstan':'#487c9b', 'Philippines':'#ad6e87', 'Qatar':'#84614b',
        'Serbia':'#63734b', 'Singapore':'#9a6c42', 'Thailand':'#79677e',
        'Uzbekistan':'#5b8987'}
def hue(name):
    return HUES.get(name, '#737d86')

st.set_page_config(page_title='Gold dashboard', layout='wide')
st.markdown('''<style>
.stApp {background:#fbfbf8;color:#1c1c18}
.block-container {max-width:1280px;padding-top:4.5rem;padding-bottom:3rem}
h1,h2,h3 {font-family:Georgia,serif!important;color:#1c1c18}
.stTabs [data-baseweb="tab-list"] {gap:30px}
.stTabs [data-baseweb="tab-highlight"] {background:#a3780a}
div[data-testid="stMetric"] {padding:12px 16px;background:#fff;border:1px solid #e5e5dc;border-radius:6px}
</style>''', unsafe_allow_html=True)

@st.cache_data
def load(name, date='date'):
    return pd.read_csv(DATA / f'{name}.csv', parse_dates=[date]).sort_values(date)
try:
    price, etf, declared = load('price'), load('etf'), load('declared')
    gap, swiss = load('gap', 'quarter_end'), load('swiss')
except FileNotFoundError:
    st.error('Data files are missing. Keep the data folder beside app.py.')
    st.stop()

st.title('Gold dashboard')
st.caption('SAMPLE DATA · Prices, ETF holdings, purchases and exports')

def period(key, frame, date='date'):
    quarterly = date == 'quarter_end'
    frequency = 'Q' if quarterly else 'M'
    unit = 'quarter' if quarterly else 'month'
    row_periods = frame[date].dt.to_period(frequency)
    options = sorted(row_periods.unique())
    def label(value):
        return f'Q{value.quarter} {value.year}' if quarterly else value.strftime('%b %Y')
    labels = [label(value) for value in options]
    chosen_start, chosen_end = st.select_slider(
        'Quarter range' if quarterly else 'Month range',
        options=labels, value=(labels[0], labels[-1]),
        key=f'{key}_period_slider',
        help='Drag either handle or use the arrow keys to select complete periods.')
    start, end = options[labels.index(chosen_start)], options[labels.index(chosen_end)]
    if start > end:
        st.warning(f'Choose an end {unit} on or after the start {unit}.')
        return frame.iloc[0:0].copy()
    st.caption(f'{label(start)} – {label(end)} · {"Quarterly" if quarterly else "Monthly"} data')
    return frame.loc[row_periods.between(start, end)].copy()

def draw(fig, height=390, sankey=False):
    fig.update_layout(height=height, paper_bgcolor=PAPER, plot_bgcolor=PAPER,
        font=dict(family='Arial, sans-serif',color=INK,size=13),
        margin=dict(l=95,r=75,t=55,b=75), hovermode='x unified',
        legend=dict(orientation='h',y=1.12,x=0))
    fig.update_xaxes(showgrid=False,automargin=True,title_standoff=18)
    fig.update_yaxes(gridcolor='#e9e9e2',zeroline=True,zerolinecolor='#96968d',
                     automargin=True,title_standoff=22)
    if sankey:
        fig.update_layout(font=dict(color='#000000',size=15),
            margin=dict(l=140,r=240,t=35,b=35), hovermode='closest')
    st.plotly_chart(fig, use_container_width=True,
        theme=None, config={'displayModeBar':False})

def line(frame, y, name, color):
    return go.Scatter(x=frame.date,y=frame[y],name=name,mode='lines',
                      line=dict(color=color,width=2.5))

first, second = st.tabs(['Gold Price & ETF Holdings','Gold Purchases & Exports'])
with first:
    st.subheader('Gold price over time')
    p = period('price',price)
    model = st.checkbox('Show yield-model comparison',value=False)
    if not p.empty:
        cols = st.columns(2)
        cols[0].metric('Gold price · last observation',f"${p.price_usd_oz.iloc[-1]:,.0f}/oz")
        cols[1].metric('Last observation',p.date.iloc[-1].strftime('%b %Y'))
        fig = go.Figure(line(p,'price_usd_oz','Gold price',GOLD))
        if model:
            fig.add_trace(go.Scatter(x=p.date,y=p.yield_implied_usd_oz,
                name='Yield-model estimate',mode='lines',
                line=dict(color=INK,width=1.7,dash='dash')))
        fig.update_yaxes(title='USD per ounce')
        draw(fig,430)
        if model:
            st.caption('Yield-model estimate: a comparison based on the earlier price–real-yield '
                       'relationship. A difference from this model does not establish its cause.')
    st.divider()
    st.subheader('ETF gold holdings over time')
    e = period('etf',etf)
    if not e.empty:
        st.metric('Gold held · last observation',f'{e.tonnes.iloc[-1]:,.1f} t')
        fig = go.Figure(line(e,'tonnes','ETF gold holdings','#5b6b7a'))
        fig.update_yaxes(title='Tonnes held')
        draw(fig)
    st.caption('The supplied ETF table contains dates and tonnes; it does not identify investors or their locations.')

with second:
    view = st.radio('Choose a view',['Country activity','Reported vs estimated','Export destinations'],
                    horizontal=True,label_visibility='collapsed')
    if view == 'Country activity':
        st.subheader('Net purchases and sales by country')
        d = period('ranking',declared)
        if not d.empty:
            totals = d.groupby('country').net_purchases_t.sum().sort_values()
            fig = go.Figure(go.Bar(x=totals.values,y=totals.index,orientation='h',
                marker_color=[hue(c) for c in totals.index],
                text=[f'{v:+,.1f}' for v in totals.values],textposition='outside',cliponaxis=False,
                hovertemplate='%{y}: %{x:+,.1f} t<extra></extra>'))
            fig.update_xaxes(title='Net purchases / sales (tonnes)',zeroline=True)
            draw(fig,max(430,len(totals)*29))
        st.caption('Totals over the selected months. Positive = net buying; negative = net selling.')
        st.divider()
        st.subheader('Compare two countries')
        countries = sorted(declared.country.unique())
        left,right = st.columns(2)
        a = left.selectbox('Country 1',countries,index=countries.index('China') if 'China' in countries else 0)
        b = right.selectbox('Country 2',countries,index=countries.index('Russia') if 'Russia' in countries else min(1,len(countries)-1))
        comparison = period('comparison',declared)
        if a == b:
            st.info('Choose different countries to compare their activity.')
        subset = comparison[comparison.country.isin([a,b])]
        if not subset.empty:
            bound = max(abs(subset.net_purchases_t.min()),abs(subset.net_purchases_t.max()),1)*1.15
            for column,country in zip(st.columns(2),[a,b]):
                with column:
                    st.markdown(f'**{country}**')
                    c = subset[subset.country == country]
                    fig = go.Figure(go.Bar(x=c.date,y=c.net_purchases_t,
                        marker_color=hue(country),name=country,
                        hovertemplate='%{x|%b %Y}: %{y:+,.2f} t<extra></extra>'))
                    fig.update_yaxes(title='Tonnes per month',range=[-bound,bound])
                    if not comparison.empty:
                        fig.update_xaxes(range=[comparison.date.min()-pd.Timedelta(days=16),
                                                comparison.date.max()+pd.Timedelta(days=16)])
                    draw(fig,370)
    elif view == 'Reported vs estimated':
        st.subheader('Reported vs estimated purchases')
        q = period('gap',gap,'quarter_end')
        if not q.empty:
            reported,estimated = q.imf_reported_t.sum(),q.wgc_estimate_t.sum()
            for col,label,value in zip(st.columns(3),['Reported total','Estimated total','Difference'],
                                       [reported,estimated,estimated-reported]):
                col.metric(label,f'{value:,.0f} t')
            fig = go.Figure(go.Bar(x=q.quarter_end,y=q.imf_reported_t,
                name='IMF-reported',marker_color='#4d5861'))
            fig.add_trace(go.Scatter(x=q.quarter_end,y=q.wgc_estimate_t,
                name='WGC estimate',mode='lines+markers',line=dict(color='#4d5861',dash='dash',width=2)))
            fig.update_xaxes(tickmode='array',tickvals=q.quarter_end,
                             ticktext=[str(v.to_period('Q')) for v in q.quarter_end])
            fig.update_yaxes(title='Tonnes per quarter',rangemode='tozero')
            draw(fig,490)
        st.caption('Difference = estimated minus reported purchases. It does not independently '
                   'confirm undisclosed buying. Only the selected complete quarters are included.')
    else:
        st.subheader('Swiss gold exports by destination')
        s = period('exports',swiss)
        if not s.empty:
            totals = s.groupby('destination').tonnes.sum().sort_values(ascending=False)
            for col,label,value in zip(st.columns(3),['Total exports','Largest destination','Destination groups'],
                [f'{totals.sum():,.1f} t',totals.index[0],str(len(totals))]):
                col.metric(label,value)
            def pale(hex_color):
                return 'rgba('+','.join(str(int(hex_color[i:i+2],16)) for i in (1,3,5))+',0.35)'
            # Fix node centres so labels can sit outside the coloured ribbons.
            values = totals.values
            count = len(values)
            chart_height = 640
            plot_height = chart_height - 70
            node_padding = 34
            spacing = node_padding / plot_height
            thicknesses = values / values.sum() * (1-spacing*(count-1))
            centres = []
            cursor = 0.0
            for thickness in thicknesses:
                centres.append(float(cursor+thickness/2))
                cursor += thickness+spacing
            fig = go.Figure(go.Sankey(arrangement='fixed',
                node=dict(label=['']*(count+1),pad=node_padding,thickness=22,
                    x=[0.02]+[0.98]*count, y=[0.5]+centres,
                    customdata=['Switzerland']+list(totals.index),
                    hovertemplate='%{customdata}<extra></extra>',
                    line=dict(color='rgba(0,0,0,0)',width=0),
                    color=['#999fa3']+[hue(c) for c in totals.index]),
                link=dict(source=[0]*count,target=list(range(1,count+1)),
                    value=values,color=[pale(hue(c)) for c in totals.index],
                    hovertemplate='%{value:,.1f} tonnes<extra></extra>')))
            fig.add_annotation(x=0.02,y=0.5,xref='paper',yref='paper',
                text=f'<b>Switzerland</b><br>{totals.sum():,.1f} t',
                showarrow=False,xanchor='right',yanchor='middle',align='right',xshift=-22,
                font=dict(color='#000000',size=15))
            for (destination,value), centre in zip(totals.items(),centres):
                fig.add_annotation(x=0.98,y=1-centre,xref='paper',yref='paper',
                    text=f'<b>{destination}</b><br>{value:,.1f} t',
                    showarrow=False,xanchor='left',yanchor='middle',align='left',xshift=22,
                    font=dict(color='#000000',size=15))
            draw(fig,chart_height,sankey=True)
        st.caption('Ribbon width represents total exports in the selected months. '
                   'Exports show shipment destinations, not final ownership. This view aggregates time.')

with st.expander('Data and definitions'):
    st.write('All five supplied CSVs contain practice data. Each chart has its own period selection. Monthly rows are selected by calendar month; '
             'quarterly rows are selected by complete quarter. Daily filtering is not available. Missing observations are not converted to zero.')
    st.table(pd.DataFrame([
        ['price.csv','date, price_usd_oz, real_yield_pct, yield_implied_usd_oz'],
        ['etf.csv','date, tonnes'],['declared.csv','date, country, net_purchases_t'],
        ['gap.csv','quarter_end, imf_reported_t, wgc_estimate_t'],
        ['swiss.csv','date, destination, tonnes']],columns=['File','Fields']))
    st.caption('Country colours preserve identity. Solid price line = supplied price; dashed line = model/estimate. '
               'Source names in the practice files do not make the sample values real observations.')
