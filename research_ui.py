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
    else:st.info('Official SEC research corpus. Automatic answers require authenticated source cells; unsupported evidence abstains.')
except requests.RequestException:st.error('Research API unavailable.');st.stop()
workflow=st.selectbox('Research workflow',['research','automatic_real'],
    help='automatic_real is a bounded source-verified BM25 cell experiment; research preserves the original D3 path.')
question=st.text_area('Financial question',value=("What were P&G's net sales for the three months ended September 30, 2026?"
    if workflow=='automatic_real' else 'CIK 202 net sales 10-K FY2025'),max_chars=2000)
arm=st.selectbox('Retrieval arm',['B','D','F','R','T','A','AT'])
operation=st.selectbox('Operation',['EXTRACT','COMPARE','ABS_CHANGE','PERCENT_CHANGE','PERCENTAGE_POINTS'])
with st.expander('Explicit scope filters'):
    cik=st.text_input('CIK filter (optional)');form=st.selectbox('Form filter',['','10-K','10-Q','10-K/A','10-Q/A'])
if st.button('Research search',type='primary'):
    filters={k:v for k,v in {'cik':cik.strip(),'form_type':form}.items() if v}
    try:
        response=requests.post(url+'/research/v1/query',headers={'Authorization':'Bearer '+token},
            json={'question':question,'filters':filters,'arm':arm,'operation':operation,'workflow':workflow},timeout=35)
        if response.status_code!=200:st.error(f'Research request failed ({response.status_code}).');st.stop()
        data=response.json();st.write('Retrieval:',data['retrieval_status'],'—',data['effective_mode'])
        st.write('Answer:',data['answer']['status'])
        if data['answer']['status']=='SUPPORTED' and data.get('automatic_workflow_version'):
            values=data['answer'].get('result_values',[]);unit=data['answer'].get('result_unit','')
            st.success('Verified SEC source cells — '+', '.join(values)+' '+unit)
            st.write('Calculation:',data['answer'].get('formula',''))
            st.caption('D1 metadata scope remains '+data['column_refinement']['metadata_scope_status']+
                       '; the requested columns were verified against source bytes.')
        if data['answer']['reasons']:st.warning(', '.join(data['answer']['reasons']))
        with st.expander('Technical answer details'):
            st.json(data['answer'])
        for item in data['evidence']:
            with st.expander(f"{item['issuer']} | {item['form']} | {item['report_date']} | {item['row_label'] or 'Text evidence'}"):
                if item['extraction_status']=='PARTIAL_EXTRACTION':st.warning('Partial extraction — evidence may be incomplete.')
                st.text(item['content']);st.json(item['locator'])
                if item.get('verification_status'):st.caption('Verification: '+item['verification_status'])
                if item.get('financial_period'):st.write('Financial period:',item['financial_period'])
                for warning in item.get('warnings',[]):st.warning(warning)
                if item['source_url'].startswith('https://www.sec.gov/Archives/'):
                    st.link_button('Open official SEC source',item['source_url'])
                    if data.get('automatic_workflow_version'):
                        st.caption('The SEC link opens the verified filing, not a verified row anchor. '
                                   'Locate the row manually using the label, period, displayed value and structural locator above.')
                else:st.caption('Synthetic source locator; no real SEC document is claimed.')
        st.caption('Generation: '+str(data['generation']));st.caption('Manifest: '+str(data['manifest_hash']))
    except requests.RequestException:st.error('Research transport unavailable or timed out; no answer inferred.')
