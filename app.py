import streamlit as st
import pandas as pd
import os
import plotly.graph_objects as go
from trinity_logic import TrinityEngine

st.set_page_config(page_title="3Q Trinity Backtest", layout="wide")
st.sidebar.title("⚙️ 설정")
start_cash = st.sidebar.number_input("초기 투자금 ($)", value=10000, step=1000)

# 1. 파일 업로드 기능
uploaded_file = st.sidebar.file_uploader("새로운 DB.csv 업로드 (선택사항)", type=['csv'])

st.title("📊 3Q QLD 트리니티 웹 시스템")
st.markdown("---")

# 2. 데이터 로드 로직 (업로드 파일 우선 -> 없으면 깃허브 서버 파일 사용)
target_file = None

if uploaded_file is not None:
    target_file = uploaded_file
    st.sidebar.success("📂 업로드된 파일 사용 중")
elif os.path.exists("DB.csv"):
    target_file = "DB.csv"
    st.sidebar.info("💾 서버에 저장된 DB 사용 중")
else:
    st.warning("👈 좌측 사이드바에서 DB 파일을 업로드하거나, 깃허브에 DB.csv를 올려주세요.")

# 3. 엔진 구동
if target_file:
    engine = TrinityEngine(target_file)
    result = engine.run(initial_cash=start_cash)
    
    if result is not None and not result.empty:
        last = result.iloc[-1]
        ret = ((last['Total_Asset']/start_cash)-1)*100
        mdd = ((result['Total_Asset'].cummax() - result['Total_Asset']) / result['Total_Asset'].cummax()).max() * 100
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("최종 자산", f"${last['Total_Asset']:,.0f}")
        c2.metric("수익률", f"{ret:.2f}%")
        c3.metric("MDD", f"{mdd:.2f}%", delta_color="inverse")
        c4.metric("현재 기어", f"{last['Gear']}")
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=result.index, y=result['Total_Asset'], name='트리니티 전략', line=dict(color='red', width=2)))
        fig.add_trace(go.Scatter(x=result.index, y=result['Close']*(start_cash/result['Close'].iloc[0]), name='단순보유', line=dict(dash='dot', color='grey')))
        st.plotly_chart(fig, use_container_width=True)
        
        with st.expander("📄 상세 거래 내역"):
            st.dataframe(result.style.format("{:.2f}"))
    else:
        st.error("데이터를 읽을 수 없습니다. 파일 형식을 확인해주세요.")
