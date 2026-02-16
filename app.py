import streamlit as st
import pandas as pd
import os
import glob
import plotly.graph_objects as go
from trinity_logic import TrinityEngine

# 1. 페이지 설정
st.set_page_config(page_title="3Q Trinity Auto", layout="wide")
st.title("📊 3Q QLD 트리니티 자동 매매 시스템")
st.markdown("---")

# 2. 파일 자동 탐색 로직 (이름이 달라도 찾음)
target_file = None

# (1순위) DB.csv 찾기
if os.path.exists('DB.csv'):
    target_file = 'DB.csv'
# (2순위) 없으면 폴더 내 아무 csv나 찾기 (requirements.txt 제외)
else:
    csv_files = [f for f in glob.glob("*.csv") if "requirements" not in f]
    if csv_files:
        target_file = csv_files[0] # 첫 번째 발견된 파일 선택

# 3. 결과 실행
if target_file:
    try:
        # 사이드바 설정
        st.sidebar.header("⚙️ 기본 설정")
        start_cash = st.sidebar.number_input("초기 투자금 ($)", value=10000, step=1000)
        
        # 파일 찾았다고 알림
        st.success(f"✅ 데이터 파일 발견! ('{target_file}' 파일로 분석을 시작합니다)")

        # 엔진 가동
        engine = TrinityEngine(target_file)
        result = engine.run(initial_cash=start_cash)
        
        if result is not None and not result.empty:
            # 결과 계산
            last = result.iloc[-1]
            ret = ((last['Total_Asset'] / start_cash) - 1) * 100
            mdd = ((result['Total_Asset'].cummax() - result['Total_Asset']) / result['Total_Asset'].cummax()).max() * 100
            
            # 메트릭
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("최종 자산", f"${last['Total_Asset']:,.0f}")
            c2.metric("수익률", f"{ret:.2f}%")
            c3.metric("MDD", f"{mdd:.2f}%", delta_color="inverse")
            c4.metric("현재 기어", f"{last['Gear']}")
            
            # 차트
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=result.index, y=result['Total_Asset'], name='트리니티 전략', line=dict(color='red', width=2)))
            fig.add_trace(go.Scatter(x=result.index, y=result['Close'] * (start_cash / result['Close'].iloc[0]), name='단순보유', line=dict(dash='dot', color='grey')))
            st.plotly_chart(fig, use_container_width=True)
            
            with st.expander("상세 데이터 보기"):
                st.dataframe(result)
        else:
            st.error(f"'{target_file}' 파일을 읽었으나 내용이 비어있거나 형식이 다릅니다.")

    except Exception as e:
        st.error(f"실행 중 오류 발생: {e}")
else:
    # 파일을 진짜 못 찾았을 때
    st.error("🚨 깃허브에 엑셀(CSV) 파일이 하나도 없습니다!")
    st.info("해결책: 깃허브 저장소(GitHub)에 '트리니티...DB.csv' 파일을 업로드만 해주세요. (이름 상관없음)")
