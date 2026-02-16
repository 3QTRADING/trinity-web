import streamlit as st
import plotly.graph_objects as go
from trinity_logic import TrinityEngine

st.set_page_config(page_title="3Q Trinity Backtest", layout="wide")
st.sidebar.title("⚙️ 설정")
start_cash = st.sidebar.number_input("초기 투자금 ($)", value=10000, step=1000)
uploaded_file = st.sidebar.file_uploader("DB.csv 파일 업로드", type=['csv'])

st.title("📊 3Q QLD 트리니티 웹 시스템")
st.write("8분할 / 스킵 / 6일갱신 / 비대칭복리 / 기어(S,N,D) 적용 완료")

if uploaded_file:
    engine = TrinityEngine(uploaded_file)
    result = engine.run(initial_cash=start_cash)
    
    if result is not None and not result.empty:
        last = result.iloc[-1]
        ret = ((last['Total_Asset']/start_cash)-1)*100
        mdd = ((result['Total_Asset'].cummax() - result['Total_Asset']) / result['Total_Asset'].cummax()).max() * 100
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("최종 자산", f"${last['Total_Asset']:,.0f}")
        c2.metric("수익률", f"{ret:.2f}%")
        c3.metric("MDD", f"{mdd:.2f}%")
        c4.metric("현재 기어", f"{last['Gear']}")
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=result.index, y=result['Total_Asset'], name='내 자산', line=dict(color='red')))
        fig.add_trace(go.Scatter(x=result.index, y=result['Close']*(start_cash/result['Close'].iloc[0]), name='단순보유', line=dict(dash='dot', color='grey')))
        st.plotly_chart(fig, use_container_width=True)
        
        with st.expander("상세 내역 보기"):
            st.dataframe(result)