import pandas as pd
import numpy as np

class TrinityEngine:
    def __init__(self, db_file):
        self.db_file = db_file
        self.data = self._load_data()
        
        # 기어 설정 (S, N, D)
        self.GEAR_PARAMS = {
            'S': {'buy': -0.03, 'sell': 0.03},
            'N': {'buy': -0.05, 'sell': 0.05},
            'D': {'buy': -0.10, 'sell': 0.10}
        }
        self.SPLIT_COUNT = 8  # 8분할
        self.RESET_DAYS = 6   # 6일 갱신

    def _load_data(self):
        try:
            df = pd.read_csv(self.db_file)
            # 주가 데이터 (3행부터, B열=Date, C열=Close)
            price_df = df.iloc[3:, 1:3].copy()
            price_df.columns = ['Date', 'Close']
            price_df['Date'] = pd.to_datetime(price_df['Date'], errors='coerce')
            price_df['Close'] = pd.to_numeric(price_df['Close'], errors='coerce')
            price_df = price_df.dropna().set_index('Date')

            # 기어 데이터 (3행부터, S열=Date, U열=Signal)
            gear_df = df.iloc[3:, [18, 20]].copy()
            gear_df.columns = ['Date', 'Gear']
            gear_df['Date'] = pd.to_datetime(gear_df['Date'], errors='coerce')
            gear_df['Gear'] = gear_df['Gear'].astype(str).str.strip().str.upper()
            gear_df = gear_df.dropna(subset=['Date']).set_index('Date')

            merged = price_df.join(gear_df, how='left')
            merged['Gear'] = merged['Gear'].fillna(method='ffill')
            merged['Gear'] = merged['Gear'].apply(lambda x: x if x in ['S', 'N', 'D'] else 'N')
            
            return merged.sort_index()
        except:
            return pd.DataFrame()

    def run(self, initial_cash=10000):
        if self.data.empty: return None
        
        cash = initial_cash
        virtual_seed = initial_cash
        holdings = 0
        avg_price = 0
        ref_price = self.data['Close'].iloc[0]
        day_counter = 0 
        logs = []

        for date, row in self.data.iterrows():
            close = row['Close']
            gear = row['Gear']
            
            # 6일 갱신
            if day_counter >= self.RESET_DAYS:
                ref_price = close
                day_counter = 0
            else:
                day_counter += 1
            
            unit_money = virtual_seed / self.SPLIT_COUNT
            action, trade_amt, realized_pnl = "Hold", 0, 0
            
            params = self.GEAR_PARAMS[gear]
            buy_target = ref_price * (1 + params['buy'])
            sell_target = ref_price * (1 + params['sell'])
            
            # 매수 (스킵/8분할 적용)
            invested_ratio = (holdings * close) / virtual_seed if virtual_seed > 0 else 0
            if close <= buy_target and invested_ratio < 0.95:
                if cash >= unit_money:
                    qty = unit_money / close
                    cost = qty * close
                    total_val = (holdings * avg_price) + cost
                    holdings += qty
                    avg_price = total_val / holdings
                    cash -= cost
                    action, trade_amt = "Buy", cost

            # 매도
            elif close >= sell_target and holdings > 0 and action == "Hold":
                qty = min(unit_money / close, holdings)
                revenue = qty * close
                pnl = (close - avg_price) * qty
                cash += revenue
                holdings -= qty
                if holdings < 0.0001: holdings = 0
                action, trade_amt, realized_pnl = "Sell", revenue, pnl
                
                # 비대칭 복리
                if pnl > 0: virtual_seed += pnl * 0.90
                else: virtual_seed += pnl * 0.20

            logs.append({
                'Date': date, 'Close': close, 'Gear': gear, 'Ref_Price': ref_price,
                'Action': action, 'PnL': realized_pnl, 
                'Total_Asset': cash + (holdings * close),
                'Virtual_Seed': virtual_seed
            })
        return pd.DataFrame(logs).set_index('Date')