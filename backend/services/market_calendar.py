"""
Market Calendar Service - 股市交易日历
提供 A 股、美股的交易日历和节假日数据
"""
import os
from datetime import date, datetime
from typing import Dict, List, Optional, Any
from functools import lru_cache
import json

# 禁用代理
os.environ['NO_PROXY'] = '*'
os.environ['no_proxy'] = '*'


class MarketCalendarService:
    """市场日历服务"""
    
    # 缓存交易日数据
    _cn_trading_dates: Optional[set] = None
    _us_holidays: Dict[int, List[Dict]] = {}  # year -> holidays
    
    def __init__(self, finnhub_api_key: Optional[str] = None):
        self.finnhub_api_key = finnhub_api_key
    
    def get_cn_trading_dates(self) -> set:
        """获取 A 股历史交易日（使用 AKShare）"""
        if MarketCalendarService._cn_trading_dates is not None:
            return MarketCalendarService._cn_trading_dates
        
        try:
            import akshare as ak
            df = ak.tool_trade_date_hist_sina()
            # 转换为 date 集合
            trading_dates = set()
            for d in df['trade_date']:
                if isinstance(d, str):
                    trading_dates.add(datetime.strptime(d, '%Y-%m-%d').date())
                else:
                    trading_dates.add(d.date() if hasattr(d, 'date') else d)
            MarketCalendarService._cn_trading_dates = trading_dates
            return trading_dates
        except Exception as e:
            print(f"获取 A 股交易日历失败: {e}")
            return set()
    
    def get_us_holidays(self, year: int) -> List[Dict[str, Any]]:
        """获取美股节假日（使用 Finnhub）"""
        if year in MarketCalendarService._us_holidays:
            return MarketCalendarService._us_holidays[year]
        
        if not self.finnhub_api_key:
            return self._get_us_holidays_fallback(year)
        
        try:
            import finnhub
            client = finnhub.Client(api_key=self.finnhub_api_key)
            # Finnhub 返回指定交易所的节假日
            holidays = client.market_holiday(exchange='US')
            
            # 过滤指定年份
            year_holidays = []
            for h in holidays.get('data', []):
                holiday_date = datetime.strptime(h['atDate'], '%Y-%m-%d').date()
                if holiday_date.year == year:
                    year_holidays.append({
                        'date': h['atDate'],
                        'name': h.get('eventName', 'Holiday'),
                        'is_trading': h.get('tradingHour') is not None
                    })
            
            MarketCalendarService._us_holidays[year] = year_holidays
            return year_holidays
        except Exception as e:
            print(f"获取美股节假日失败: {e}")
            return self._get_us_holidays_fallback(year)
    
    def _get_us_holidays_fallback(self, year: int) -> List[Dict[str, Any]]:
        """美股节假日备用数据（常规节假日）"""
        # 美股固定节假日
        holidays = [
            {'month': 1, 'day': 1, 'name': "New Year's Day"},
            {'month': 1, 'day': 15, 'name': "Martin Luther King Jr. Day"},  # 1月第3个周一，这里简化
            {'month': 2, 'day': 17, 'name': "Presidents' Day"},  # 2月第3个周一
            {'month': 5, 'day': 26, 'name': "Memorial Day"},  # 5月最后一个周一
            {'month': 6, 'day': 19, 'name': "Juneteenth"},
            {'month': 7, 'day': 4, 'name': "Independence Day"},
            {'month': 9, 'day': 1, 'name': "Labor Day"},  # 9月第1个周一
            {'month': 11, 'day': 27, 'name': "Thanksgiving Day"},  # 11月第4个周四
            {'month': 12, 'day': 25, 'name': "Christmas Day"},
        ]
        
        result = []
        for h in holidays:
            try:
                d = date(year, h['month'], h['day'])
                result.append({
                    'date': d.isoformat(),
                    'name': h['name'],
                    'is_trading': False
                })
            except:
                pass
        return result
    
    def get_cn_holidays(self, year: int, month: int) -> List[Dict[str, Any]]:
        """获取 A 股指定月份的休市日（非交易日且非周末）"""
        trading_dates = self.get_cn_trading_dates()
        if not trading_dates:
            return []
        
        holidays = []
        # 遍历该月每一天
        first_day = date(year, month, 1)
        if month == 12:
            last_day = date(year + 1, 1, 1)
        else:
            last_day = date(year, month + 1, 1)
        
        current = first_day
        while current < last_day:
            weekday = current.weekday()
            is_weekend = weekday >= 5
            is_trading = current in trading_dates
            
            # 非周末且非交易日 = 节假日
            if not is_weekend and not is_trading:
                # 尝试识别节假日名称
                name = self._guess_cn_holiday_name(current)
                holidays.append({
                    'date': current.isoformat(),
                    'name': name,
                    'is_trading': False
                })
            
            current = date.fromordinal(current.toordinal() + 1)
        
        return holidays
    
    def _guess_cn_holiday_name(self, d: date) -> str:
        """根据日期猜测中国节假日名称"""
        # 简化的节假日识别
        month, day = d.month, d.day
        
        if month == 1 and day <= 3:
            return "元旦"
        elif month == 1 and 21 <= day <= 31:
            return "春节"
        elif month == 2 and day <= 10:
            return "春节"
        elif month == 4 and 3 <= day <= 5:
            return "清明节"
        elif month == 5 and 1 <= day <= 5:
            return "劳动节"
        elif month == 6 and 7 <= day <= 9:
            return "端午节"
        elif month == 9 and 15 <= day <= 17:
            return "中秋节"
        elif month == 10 and 1 <= day <= 7:
            return "国庆节"
        else:
            return "休市"
    
    def get_calendar(self, market: str, year: int, month: int) -> Dict[str, Any]:
        """
        获取指定市场、年月的日历数据
        
        Args:
            market: 'CN' (A股), 'US' (美股), 'HK' (港股)
            year: 年份
            month: 月份 (1-12)
        
        Returns:
            {
                'market': 'CN',
                'year': 2026,
                'month': 2,
                'holidays': [{'date': '2026-02-10', 'name': '春节', 'is_trading': False}],
                'trading_days': ['2026-02-03', '2026-02-04', ...],
                'non_trading_days': ['2026-02-01', '2026-02-07', ...]  # 周末
            }
        """
        holidays = []
        trading_days = []
        non_trading_days = []
        
        # 生成该月所有日期
        first_day = date(year, month, 1)
        if month == 12:
            next_month = date(year + 1, 1, 1)
        else:
            next_month = date(year, month + 1, 1)
        
        all_dates = []
        current = first_day
        while current < next_month:
            all_dates.append(current)
            current = date.fromordinal(current.toordinal() + 1)
        
        if market.upper() == 'CN':
            trading_dates = self.get_cn_trading_dates()
            holidays = self.get_cn_holidays(year, month)
            holiday_dates = {h['date'] for h in holidays}
            
            for d in all_dates:
                d_str = d.isoformat()
                if d in trading_dates:
                    trading_days.append(d_str)
                elif d_str not in holiday_dates:
                    non_trading_days.append(d_str)  # 周末
        
        elif market.upper() == 'US':
            us_holidays = self.get_us_holidays(year)
            holidays = [h for h in us_holidays if h['date'].startswith(f"{year}-{month:02d}")]
            holiday_dates = {h['date'] for h in holidays}
            
            for d in all_dates:
                d_str = d.isoformat()
                weekday = d.weekday()
                is_weekend = weekday >= 5
                
                if is_weekend:
                    non_trading_days.append(d_str)
                elif d_str in holiday_dates:
                    pass  # 已在 holidays 中
                else:
                    trading_days.append(d_str)
        
        else:
            # 默认按周末处理
            for d in all_dates:
                if d.weekday() >= 5:
                    non_trading_days.append(d.isoformat())
                else:
                    trading_days.append(d.isoformat())
        
        return {
            'market': market.upper(),
            'year': year,
            'month': month,
            'holidays': holidays,
            'trading_days': trading_days,
            'non_trading_days': non_trading_days
        }
