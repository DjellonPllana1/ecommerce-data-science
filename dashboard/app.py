from pathlib import Path
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dashboard.api_client import APIError,get,post

ROOT=Path(__file__).resolve().parents[1]
st.set_page_config(page_title='E-Commerce Intelligence Platform',page_icon='🛒',layout='wide')
st.markdown("""<style>.block-container{padding-top:1.5rem}.kpi{border:1px solid #e5e7eb;border-radius:12px;padding:1rem;background:#fff}h1,h2,h3{color:#172554}</style>""",unsafe_allow_html=True)
st.title('E-Commerce Intelligence Platform')
st.caption('End-to-End Data Science on Real E-Commerce Data')
page=st.sidebar.radio('Navigate',['Executive Overview','Sales Analytics','Customer Intelligence','Delivery Risk','Sales Forecasting','Model Performance','About the Project'])

@st.cache_data(ttl=300)
def api_get(path,**params): return get(path,**params)
def frame(path,**params): return pd.DataFrame(api_get(path,**params))
def service_error(exc): st.error(str(exc)); st.info('Start FastAPI with: `uvicorn api.main:app --reload`')
def kpis(data):
    cols=st.columns(4); cols[0].metric('Revenue',f"R$ {data['total_revenue']:,.0f}"); cols[1].metric('Eligible orders',f"{data['total_eligible_orders']:,}"); cols[2].metric('Unique customers',f"{data['unique_customers']:,}"); cols[3].metric('Average order value',f"R$ {data['average_order_value']:,.2f}")
    cols=st.columns(3); cols[0].metric('Repeat customer rate',f"{data['repeat_customer_rate']:.2f}%"); cols[1].metric('Late-delivery rate',f"{data['late_delivery_rate']:.2f}%"); cols[2].metric('Avg. delivery duration',f"{data['average_delivery_duration_days']:.1f} days")

try:
    if page=='Executive Overview':
        st.header('Executive Overview'); overview=api_get('/analytics/overview'); kpis(overview)
        monthly=frame('/analytics/monthly-sales'); monthly['month']=pd.to_datetime(monthly.month); c1,c2=st.columns(2); c1.plotly_chart(px.line(monthly,x='month',y='revenue',title='Monthly revenue'),width='stretch'); c2.plotly_chart(px.line(monthly,x='month',y='orders',title='Monthly orders'),width='stretch')
        customers=frame('/analytics/customer-summary'); forecast=pd.DataFrame(api_get('/forecast',horizon=7)['forecasts']); c1,c2=st.columns(2); c1.plotly_chart(px.pie(customers,names='customer_type',values='customers',title='Customer mix'),width='stretch'); c2.plotly_chart(px.line(forecast,x='date',y=['predicted_orders'],title='Seven-day order outlook'),width='stretch')
        st.info('The marketplace generated meaningful scale and growth, but retention remained low and late delivery was a material operational issue. Near-term forecasts support staffing and cash planning.')
    elif page=='Sales Analytics':
        st.header('Sales Analytics'); overview=api_get('/analytics/overview'); kpis(overview); monthly=frame('/analytics/monthly-sales'); monthly['month']=pd.to_datetime(monthly.month); st.plotly_chart(px.line(monthly,x='month',y=['revenue','orders'],title='Commercial trend (independent axes recommended for detailed analysis)'),width='stretch')
        categories=frame('/analytics/categories'); st.plotly_chart(px.bar(categories.head(15),x='item_revenue',y='category',orientation='h',title='Top categories by item GMV'),width='stretch'); delivery=frame('/analytics/delivery'); st.plotly_chart(px.line(delivery,x='month',y=['average_delivery_days','late_delivery_rate'],title='Delivery performance'),width='stretch'); st.caption('Payments are aggregated before order joins; category revenue uses item-price GMV.')
    elif page=='Customer Intelligence':
        st.header('Customer Intelligence'); profiles=pd.read_csv(ROOT/'reports/segmentation/cluster_profiles.csv'); rules=pd.read_csv(ROOT/'reports/segmentation/rule_segment_distribution.csv'); c1,c2=st.columns(2); c1.plotly_chart(px.bar(profiles,x='cluster_name',y='customer_percentage',title='KMeans customer share'),width='stretch'); c2.plotly_chart(px.bar(profiles,x='cluster_name',y='revenue_share',title='KMeans revenue share'),width='stretch'); st.dataframe(rules,width='stretch')
        st.subheader('Interactive RFM assignment'); a,b,c=st.columns(3); recency=a.number_input('Recency (days)',0.0,3000.0,120.0); frequency=b.number_input('Frequency (orders)',0.0,100.0,2.0); monetary=c.number_input('Monetary value (R$)',0.0,100000.0,250.0)
        if st.button('Predict customer segment',type='primary'): result=post('/predict/customer-segment',{'recency':recency,'frequency':frequency,'monetary':monetary}); st.success(f"Cluster {result['cluster_id']}: {result['cluster_name']}")
    elif page=='Delivery Risk':
        st.header('Delivery Risk'); st.warning('This is a probability for operational prioritization, not a guarantee.')
        with st.form('delivery'):
            c1,c2,c3=st.columns(3); values={'purchase_month':c1.number_input('Purchase month',1,12,6),'purchase_day_of_week':c2.number_input('Day of week (0=Mon)',0,6,2),'purchase_hour':c3.number_input('Purchase hour',0,23,14),'customer_zip_region':c1.number_input('ZIP prefix region',0,99999,1300),'item_value':c2.number_input('Item value',0.0,100000.0,150.0),'freight_value':c3.number_input('Freight value',0.0,10000.0,20.0),'item_count':c1.number_input('Item count',1,100,1),'unique_products':c2.number_input('Unique products',1,100,1),'seller_count':c3.number_input('Seller count',1,100,1),'total_product_weight_g':c1.number_input('Total weight (g)',0.0,1000000.0,1200.0),'average_product_length_cm':c2.number_input('Avg length (cm)',0.0,1000.0,30.0),'average_product_height_cm':c3.number_input('Avg height (cm)',0.0,1000.0,15.0),'average_product_width_cm':c1.number_input('Avg width (cm)',0.0,1000.0,20.0),'payment_value':c2.number_input('Payment value',0.0,100000.0,170.0),'payment_installments':c3.number_input('Installments',0,100,2),'estimated_delivery_window_days':c1.number_input('Estimated window (days)',0.1,365.0,20.0),'customer_state':c2.text_input('Customer state','SP'),'dominant_product_category':c3.text_input('Product category','bed_bath_table'),'dominant_seller_state':c1.text_input('Seller state','SP'),'same_customer_seller_state':c2.selectbox('Same customer/seller state',[1,0]),'payment_type':c3.selectbox('Payment type',['credit_card','boleto','voucher','debit_card'])}; submitted=st.form_submit_button('Estimate delivery risk',type='primary')
        if submitted:
            result=post('/predict/late-delivery',values); st.metric('Late-delivery probability',f"{result['late_delivery_probability']:.1%}"); st.subheader(result['interpretation']); st.write(f"Predicted class: {result['predicted_class']}")
    elif page=='Sales Forecasting':
        st.header('Sales Forecasting'); horizon=st.selectbox('Forecast horizon',[7,14,30]); result=api_get('/forecast',horizon=horizon); forecast=pd.DataFrame(result['forecasts']); forecast['date']=pd.to_datetime(forecast.date); c1,c2=st.columns(2); c1.metric('Forecast orders',f"{forecast.predicted_orders.sum():,.0f}"); c2.metric('Forecast revenue',f"R$ {forecast.predicted_revenue.sum():,.0f}")
        fig=go.Figure([go.Scatter(x=forecast.date,y=forecast.orders_upper_bound,line=dict(width=0),showlegend=False),go.Scatter(x=forecast.date,y=forecast.orders_lower_bound,fill='tonexty',line=dict(width=0),name='Planning interval'),go.Scatter(x=forecast.date,y=forecast.predicted_orders,name='Predicted orders')]); st.plotly_chart(fig,width='stretch'); st.caption(result['interval_type']+' Longer horizons had higher observed holdout error. Historical context is available in the persisted forecasting reports.')
    elif page=='Model Performance':
        st.header('Model Performance'); delivery=json.loads((ROOT/'models/late_delivery_metadata.json').read_text()); forecast=json.loads((ROOT/'models/forecasting/forecast_metadata.json').read_text()); cluster=json.loads((ROOT/'models/customer_segmentation/cluster_metadata.json').read_text()); st.subheader('Late-delivery classifier'); st.json(delivery['test_metrics']); c1,c2=st.columns(2); c1.image(str(ROOT/'reports/modeling/figures/confusion_matrix.png')); c2.image(str(ROOT/'reports/modeling/figures/precision_recall_curve.png')); st.subheader('Customer clustering'); st.metric('Selected k',cluster['selected_k']); st.metric('Silhouette score',f"{cluster['silhouette_score']:.3f}"); st.dataframe(pd.read_csv(ROOT/'reports/segmentation/k_selection_metrics.csv')); st.subheader('Forecasting'); st.write('Selected:',forecast['selected_models']); st.dataframe(pd.read_csv(ROOT/'reports/forecasting/model_comparison.csv'))
    else:
        st.header('About the Project'); st.markdown('''### Business problem\nTranslate marketplace transactions into reliable executive analytics, customer intelligence, delivery-risk prioritization, and operational forecasts.\n\n### Architecture'''); st.graphviz_chart('digraph { rankdir=LR; Data -> PostgreSQL -> "Analytics + ML" -> FastAPI -> Streamlit }'); st.markdown('''### End-to-end scope\nPostgreSQL preserves relational integrity and supports grain-safe SQL. Python performs EDA, classification, clustering, and time-series forecasting. FastAPI provides validated read-only analytics and cached model inference. Streamlit communicates results to business users.\n\n### Limitations\nThe dataset represents one historical marketplace period. Models omit promotions, traffic, holidays, macroeconomics, and current operational conditions. Predictions are associative and probabilistic, not causal guarantees.''')
except APIError as exc: service_error(exc)
except Exception as exc: st.error(f'Page could not be rendered: {exc}')
