import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import os
import glob

# -----------------------------------------------------------
# 1. 트리니티 핵심 엔진 (데이터 파싱 + 매매 로직)
# -----------------------------------------------------------
class TrinityLogic:
    def __init__(self, filepath):
        self.filepath = filepath
        self.df = self.load_data()
        
        # ⚙️ 기어별 매매 밴드 설정 (S, N, D)
        self.GEAR_RANGES = {
            'S': 0.03, # 3%
            'N': 0.05, # 5%
            'D': 0.10  # 10%
        }
        
    def load_data(self):
        """
        정부장님 DB.csv 형식(3번째 줄 헤더)에 맞춰 강제로 데이터를 뜯어옵니다.
        """
        try:
            # 1. 엑셀 구조상 3번째 줄(Index 2)에 헤더가 있음 -> header=2 옵션 필수
            raw = pd.read_csv(self.filepath, header=2)
            
            # 2. [주가 데이터] B열(Date), C열(Close) 추출
            # iloc[:, 1:3] -> 1번째(B), 2번째(C) 컬럼
            price_df = raw.iloc[:, 1:3].copy() 
            price_df.columns = ['Date', 'Close']
            price_df['Date'] = pd.to_datetime(price_df['Date'], errors='coerce')
            price_df['Close'] = pd.to_numeric(price_df['Close'], errors='coerce')
            price_df = price_df.dropna().set_index('Date')

            # 3. [기어 데이터] S열(Date), U열(Signal) 추출
            # S열은 18번째(index 18), U열은 20번째(index 20) -> 직접 지정
            gear_df = raw.iloc[:, [18, 20]].copy()
            gear_df.columns = ['Date', 'Gear']
            gear_df['Date'] = pd.to_datetime(gear_df['Date'], errors='coerce')
            gear_df['Gear'] = gear_df['Gear'].astype(str).str.strip().str.upper()
            gear_df = gear_df.dropna(subset=['Date']).set_index('Date')

            # 4. 병합 (주가 데이터 기준, 기어는 주단위이므로 빈 날짜 채우기)
            df = price_df.join(gear_df, how='left')
            df['Gear'] = df['Gear'].fillna(method='ffill') # 직전 기어 유지
            df['Gear'] = df['Gear'].fillna('N') # 없으면 N 기본값
            
            # S, N, D 외의 이상한 값은 N으로 처리
            df['Gear'] = df['Gear'].apply(lambda x: x if x in ['S', 'N', 'D'] else 'N')
            
            return df.sort_index()

        except Exception as e:
            st.error(f"데이터 읽기 실패: {e}")
            return pd.DataFrame()

    def run_backtest(self, start_cash=10000):
        if self.df.empty: return pd.DataFrame()

        # 초기 설정
        cash = start_cash
        virtual_seed = start_cash # 비대칭 복리 계산용 시드
        holdings = 0
        avg_price = 0
        
        # 6일 갱신 관련
        ref_price = self.df['Close'].iloc[0]
        days_count = 0
        
        logs = []

        # --- [일별 루프] ---
        for date, row in self.df.iterrows():
            close = row['Close']
            gear = row['Gear']
            
            # 1. 기준가 갱신 (6거래일 주기)
            if days_count >= 6:
                ref_price = close
                days_count = 0
            else:
                days_count += 1
            
            # 2. 유닛 계산 (8분할)
            unit_val = virtual_seed / 8
            
            action = "Hold"
            profit = 0
            
            # 3. 밴드 설정
            gap = self.GEAR_RANGES[gear] # 0.03, 0.05, 0.10
            buy_line = ref_price * (1 - gap)
            sell_line = ref_price * (1 + gap)
            
            # 4. 매매 판단 (하루 1유닛 스킵 로직)
            
            # [매수] 가격 < 하단 AND 풀매수(0.9 이상) 아님
            current_invested_ratio = (holdings * close) / virtual_seed if virtual_seed > 0 else 0
            
            if close <= buy_line and current_invested_ratio < 0.9:
                if cash >= unit_val:
                    # 매수 실행
                    cost = unit_val
                    buy_qty = cost / close
                    
                    # 평단 갱신
                    total_val = (holdings * avg_price) + cost
                    holdings += buy_qty
                    avg_price = total_val / holdings
                    cash -= cost
                    
                    action = "Buy"

            # [매도] 가격 > 상단 AND 보유량 있음
            elif close >= sell_line and holdings > 0:
                # 1유닛만 매도 (스킵)
                sell_qty = min(holdings, unit_val / close)
                revenue = sell_qty * close
                
                # 실현 손익
                realized_pnl = (close - avg_price) * sell_qty
                profit = realized_pnl
                
                cash += revenue
                holdings -= sell_qty
                if holdings < 0.0001: holdings = 0
                
                action = "Sell"
                
                # 5. [핵심] 비대칭 복리 (이익 90%, 손실 20% 반영)
                if realized_pnl > 0:
                    virtual_seed += realized_pnl * 0.9
                else:
                    virtual_seed += realized_pnl * 0.2

            # 로그 기록
            total_equity = cash + (holdings * close)
            logs.append({
                'Date': date,
                'Close': close,
                'Gear': gear,
                'Ref_Price': ref_price,
                'Action': action,
                'Profit': profit,
                'Total_Asset': total_equity,
                'Virtual_Seed': virtual_seed,
                'Holdings': holdings
            })
            
        return pd.DataFrame(logs).set_index('Date')

# -----------------------------------------------------------
# 2. 웹 화면 (UI)
# -----------------------------------------------------------
st.set_page_config(page_title="3Q Trinity System", layout="wide")
st.title("📊 3Q QLD 트리니티 자동 매매 (최종수정)")
st.markdown("---")

# 파일 자동 탐색
target_file = None
if os.path.exists('DB.csv'):
    target_file = 'DB.csv'
else:
    # DB.csv가 없으면 폴더 내 아무 csv나 잡음
    csvs = [f for f in glob.glob("*.csv") if "requirements" not in f]
    if csvs: target_file = csvs[0]

if target_file:
    st.sidebar.success(f"파일 연결됨: {target_file}")
    start_seed = st.sidebar.number_input("시작 투자금($)", 10000, step=1000)
    
    # 로직 실행
    engine = TrinityLogic(target_file)
    result = engine.run_backtest(start_seed)
    
    if not result.empty:
        # 결과표시
        last = result.iloc[-1]
        ret = ((last['Total_Asset']/start_seed)-1)*100
        mdd = ((result['Total_Asset'].cummax() - result['Total_Asset']) / result['Total_Asset'].cummax()).max() * 100
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("최종 자산", f"${last['Total_Asset']:,.0f}")
        c2.metric("수익률", f"{ret:.2f}%")
        c3.metric("MDD", f"{mdd:.2f}%", delta_color="inverse")
        c4.metric("현재 기어", last['Gear'])
        
        # 차트
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=result.index, y=result['Total_Asset'], name='트리니티', line=dict(color='red')))
        fig.add_trace(go.Scatter(x=result.index, y=result['Close']*(start_seed/result['Close'].iloc[0]), name='단순보유', line=dict(color='grey', dash='dot')))
        st.plotly_chart(fig, use_container_width=True)
        
        # 거래 로그
        with st.expander("상세 거래 내역 (로직 검증용)"):
            st.dataframe(result)
    else:
        st.error("데이터 로드 실패: 엑셀 파일 내부 형식을 확인해주세요.")
else:
    st.error("🚨 깃허브에 CSV 파일이 없습니다! 파일을 올려주세요.")
