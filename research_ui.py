"""Separate local research UI; run explicitly, never replaces accepted UI."""
import os
from urllib.parse import urlparse
import requests
import streamlit as st

st.set_page_config(page_title='Financial Intelligence Research v1',layout='wide')
st.title('Financial Intelligence — Research v1')
st.caption('Opt-in research prototype. Source correspondence does not certify financial answers.')
url=os.getenv('TOPIC3_RESEARCH_API_URL','http://127.0.0.1:8767').rstrip('/')
parsed=urlparse(url)
if parsed.hostname not in {'127.0.0.1','localhost'} or parsed.scheme!='http' or parsed.username or parsed.password:
    st.error('Research UI requires an explicitly configured local API.');st.stop()
token=os.getenv('TOPIC3_RESEARCH_API_TOKEN','')
if not token:token=st.text_input('Research API token',type='password')
try:
    health=requests.get(url+'/research/v1/health',timeout=3).json()
    if health.get('source_type')=='SYNTHETIC_DEMO':st.warning('SYNTHETIC DEMO — all values are fabricated fixtures, not SEC observations.')
    else:st.info('Official SEC research corpus. Numerical answers abstain when D2 source context is unsupported.')
except requests.RequestException:st.error('Research API unavailable.');st.stop()
question=st.text_area('Financial question',value='CIK 202 net sales 10-K FY2025',max_chars=2000)
arm=st.selectbox('Retrieval arm',['B','D','F','R','T','A','AT'])
operation=st.selectbox('Operation',['EXTRACT','COMPARE','ABS_CHANGE','PERCENT_CHANGE','PERCENTAGE_POINTS'])
with st.expander('Explicit scope filters'):
    cik=st.text_input('CIK filter (optional)');form=st.selectbox('Form filter',['','10-K','10-Q','10-K/A','10-Q/A'])
if st.button('Research search',type='primary'):
    filters={k:v for k,v in {'cik':cik.strip(),'form_type':form}.items() if v}
    try:
        response=requests.post(url+'/research/v1/query',headers={'Authorization':'Bearer '+token},
            json={'question':question,'filters':filters,'arm':arm,'operation':operation},timeout=35)
        if response.status_code!=200:st.error(f'Research request failed ({response.status_code}).');st.stop()
        data=response.json();st.write('Retrieval:',data['retrieval_status'],'—',data['effective_mode'])
        st.write('Answer:',data['answer']['status']);st.json(data['answer'])
        if data['answer']['reasons']:st.warning(', '.join(data['answer']['reasons']))
        for item in data['evidence']:
            with st.expander(f"{item['issuer']} | {item['form']} | {item['report_date']} | {item['row_label'] or 'Text evidence'}"):
                if item['extraction_status']=='PARTIAL_EXTRACTION':st.warning('Partial extraction — evidence may be incomplete.')
                st.text(item['content']);st.json(item['locator'])
                if item['source_url'].startswith('https://www.sec.gov/Archives/'):
                    st.link_button('Open official SEC source',item['source_url'])
                else:st.caption('Synthetic source locator; no real SEC document is claimed.')
        st.caption('Generation: '+str(data['generation']));st.caption('Manifest: '+str(data['manifest_hash']))
    except requests.RequestException:st.error('Research transport unavailable or timed out; no answer inferred.')
