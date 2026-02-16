import streamlit as st
import pandas as pd
import os
import plotly.graph_objects as go
from trinity_logic import TrinityEngine

# 1. 페이지 설정 (넓게 보기)
st.set_page_config(page_title="3Q Trinity Auto-System", layout="wide")

# 2. 제목 및 스타일
st.title("📊 3Q QLD 트리니티 자동 매매 시스템")
st.markdown("### 🚀 파일 업로드 없이 자동 실행됩니다.")
st.markdown("---")

# 3. 데이터 파일 지정 (깃허브에 올려둔 파일명과 똑같아야 함)
DB_FILENAME = 'DB.csv'

# 4. 자동 실행 로직
if os.path.exists(DB_FILENAME):
    try:
        # 사이드바 (설정만 가능, 파일 업로드 없음)
        st.sidebar.header("⚙️ 시드 설정")
        start_cash = st.sidebar.number_input("초기 투자금 ($)", value=10000, step=1000)
        
        # 엔진 가동 알림
        st.success(f"✅ 서버에서 '{DB_FILENAME}' 파일을 찾았습니다. 분석을 시작합니다...")

        # --- [핵심] 엔진 구동 ---
        engine = TrinityEngine(DB_FILENAME)
        result = engine.run(initial_cash=start_cash)
        
        if result is not None and not result.empty:
            # (1) 결과 요약 계산
            last = result.iloc[-1]
            total_return = ((last['Total_Asset'] / start_cash) - 1) * 100
            mdd = ((result['Total_Asset'].cummax() - result['Total_Asset']) / result['Total_Asset'].cummax()).max() * 100
            
            # (2) 상단 메트릭 표시
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("최종 자산 평가액", f"${last['Total_Asset']:,.0f}")
            col2.metric("총 수익률", f"{total_return:.2f}%", delta_color="normal")
            col3.metric("최대 낙폭 (MDD)", f"{mdd:.2f}%", delta_color="inverse")
            col4.metric("현재 기어 상태", f"{last['Gear']} 모드")
            
            # (3) 메인 차트 그리기
            st.subheader("📈 자산 증식 추이 (Equity Curve)")
            fig = go.Figure()
            # 트리니티 전략
            fig.add_trace(go.Scatter(
                x=result.index, y=result['Total_Asset'], 
                mode='lines', name='트리니티 전략', 
                line=dict(color='#FF4B4B', width=2)
            ))
            # 단순 보유 (비교군)
            benchmark_asset = result['Close'] * (start_cash / result['Close'].iloc[0])
            fig.add_trace(go.Scatter(
                x=result.index, y=benchmark_asset, 
                mode='lines', name='단순보유 (Buy & Hold)', 
                line=dict(color='gray', dash='dot')
            ))
            st.plotly_chart(fig, use_container_width=True)
            
            # (4) 상세 데이터
            with st.expander("🔎 일별 상세 거래 내역 확인하기"):
                st.dataframe(result.style.format("{:.2f}"))
                
        else:
            st.error("데이터 파일은 있지만, 내용 형식이 맞지 않습니다. DB.csv를 확인해주세요.")

    except Exception as e:
        st.error(f"시스템 실행 중 오류가 발생했습니다: {e}")

else:
    # 파일이 없을 때 화면에 띄울 경고창
    st.error("🚨 [오류] 실행할 데이터 파일이 없습니다!")
    st.warning(f"깃허브(GitHub) 저장소에 '{DB_FILENAME}' 파일을 업로드해주세요.")
    st.info("파일을 올리고 웹사이트를 '새로고침' 하시면 바로 실행됩니다.")
