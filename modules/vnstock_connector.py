"""Market data connector for XTSC demo.

Priority:
1) vnstock live data for VNINDEX (Vietnam providers such as VCI/TCBS/KBS)
2) yfinance fallback for ^VNINDEX
3) local sample data, so Streamlit app never crashes

Notes for Streamlit Cloud:
- Pin Python to 3.11 via runtime.txt. Some vnstock builds may not be stable on Python 3.14.
- Public market APIs can be rate-limited/blocked in cloud environments, so this connector is intentionally defensive.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Tuple, List
import pandas as pd


def _to_datetime_ns(series) -> pd.Series:
    """Convert any datetime-like series/index to timezone-naive datetime64[ns].

    This avoids Streamlit Cloud merge_asof errors such as:
    incompatible merge keys dtype('<M8[us]') and dtype('<M8[ns]').
    """
    s = pd.to_datetime(series, errors="coerce")
    try:
        if getattr(s.dt, "tz", None) is not None:
            s = s.dt.tz_convert(None)
    except Exception:
        try:
            s = s.dt.tz_localize(None)
        except Exception:
            pass
    return s.astype("datetime64[ns]")


def _standardize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """Return columns date, close from multiple market-data schemas."""
    if df is None or len(df) == 0:
        raise ValueError("DataFrame rỗng")
    df = df.copy()
    df.columns = [str(c).lower().strip() for c in df.columns]

    # Common date/time column names across vnstock/yfinance versions/providers
    for c in ["time", "date", "trading_date", "datetime", "timestamp"]:
        if c in df.columns:
            df["date"] = _to_datetime_ns(df[c])
            break
    if "date" not in df.columns:
        # yfinance may return DatetimeIndex
        if isinstance(df.index, pd.DatetimeIndex):
            df["date"] = _to_datetime_ns(df.index)
        else:
            df["date"] = pd.date_range(end=pd.Timestamp.today().normalize(), periods=len(df), freq="B")

    # Common close column names
    for c in ["close", "close_price", "match_price", "price", "adj close", "adj_close"]:
        if c in df.columns:
            df["close"] = pd.to_numeric(df[c], errors="coerce")
            break
    if "close" not in df.columns:
        raise ValueError("Không tìm thấy cột giá đóng cửa từ dữ liệu thị trường")

    out = df[["date", "close"]].dropna().sort_values("date")
    if out.empty:
        raise ValueError("Không còn dòng hợp lệ sau khi chuẩn hóa dữ liệu")
    return out


def _history_with_new_vnstock(symbol: str, start: str, end: str, source: str) -> pd.DataFrame:
    from vnstock import Vnstock  # type: ignore
    stock = Vnstock().stock(symbol=symbol, source=source)
    return stock.quote.history(start=start, end=end, interval="1D")


def _history_with_vnstock3(symbol: str, start: str, end: str, source: str) -> pd.DataFrame:
    # Some environments install vnstock3 separately.
    from vnstock3 import Vnstock  # type: ignore
    stock = Vnstock().stock(symbol=symbol, source=source)
    return stock.quote.history(start=start, end=end, interval="1D")


def _history_with_legacy_vnstock(symbol: str, start: str, end: str) -> pd.DataFrame:
    # Older vnstock API. Many newer versions no longer expose this function.
    from vnstock import stock_historical_data  # type: ignore
    return stock_historical_data(symbol=symbol, start_date=start, end_date=end)


def _history_with_yfinance(start: str, end: str) -> pd.DataFrame:
    import yfinance as yf  # type: ignore
    # Yahoo commonly uses ^VNINDEX for Ho Chi Minh Stock Index.
    candidates = ["^VNINDEX", "VNINDEX.VN"]
    errors: List[str] = []
    for ticker in candidates:
        try:
            df = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=False, threads=False)
            px = _standardize_ohlcv(df.reset_index())
            return px
        except Exception as e:  # pragma: no cover - cloud/API dependent
            errors.append(f"{ticker}/yfinance: {e}")
    raise RuntimeError("Không lấy được dữ liệu qua yfinance: " + " | ".join(errors))


def get_vnindex_history(months: int = 18, source: str = "VCI") -> Tuple[pd.DataFrame, str]:
    """Return VNINDEX history and data-source label.

    Output columns: date, vnindex, market_return_pct, market_volatility_pct.
    """
    end = date.today()
    start = end - timedelta(days=int(months * 31))
    start_s, end_s = start.isoformat(), end.isoformat()

    errors: List[str] = []
    symbols = ["VNINDEX", "VN-INDEX", "VN30"]
    sources = []
    # Prioritize user-selected source, then try alternatives.
    for s in [source, "TCBS", "VCI", "KBS"]:
        if s and s not in sources:
            sources.append(s)

    for provider in sources:
        for symbol in symbols:
            try:
                raw = _history_with_new_vnstock(symbol, start_s, end_s, provider)
                px = _standardize_ohlcv(raw)
                label_symbol = "VN30" if symbol == "VN30" else "VNINDEX"
                break
            except Exception as e:  # pragma: no cover - cloud/API dependent
                errors.append(f"vnstock:{symbol}/{provider}: {e}")
                px = None
        if px is not None:
            break
    else:
        # Try vnstock3 explicit package if present.
        for provider in sources:
            for symbol in symbols:
                try:
                    raw = _history_with_vnstock3(symbol, start_s, end_s, provider)
                    px = _standardize_ohlcv(raw)
                    label_symbol = "VN30" if symbol == "VN30" else "VNINDEX"
                    break
                except Exception as e:  # pragma: no cover
                    errors.append(f"vnstock3:{symbol}/{provider}: {e}")
                    px = None
            if px is not None:
                break
        else:
            try:
                raw = _history_with_legacy_vnstock("VNINDEX", start_s, end_s)
                px = _standardize_ohlcv(raw)
                label_symbol = "VNINDEX"
            except Exception as e:  # pragma: no cover
                errors.append(f"legacy vnstock: {e}")
                try:
                    px = _history_with_yfinance(start_s, end_s)
                    label_symbol = "VNINDEX"
                    out = px.rename(columns={"close": "vnindex"})
                    out["market_return_pct"] = out["vnindex"].pct_change().fillna(0) * 100
                    out["market_volatility_pct"] = out["market_return_pct"].rolling(20).std().fillna(0)
                    return out, "yfinance live (^VNINDEX)"
                except Exception as e2:  # pragma: no cover
                    errors.append(str(e2))
                    raise RuntimeError("Không lấy được dữ liệu VNINDEX từ vnstock/yfinance: " + " | ".join(errors))

    out = px.rename(columns={"close": "vnindex"})
    out["market_return_pct"] = out["vnindex"].pct_change().fillna(0) * 100
    out["market_volatility_pct"] = out["market_return_pct"].rolling(20).std().fillna(0)
    return out, f"vnstock live ({label_symbol}/{provider})"


def enrich_macro_with_vnstock(local_macro: pd.DataFrame, use_live: bool = True, source: str = "VCI") -> Tuple[pd.DataFrame, str, str]:
    """Merge local macro proxy data with live VNINDEX if available."""
    if not use_live:
        return local_macro.copy(), "Dữ liệu mẫu nội bộ", "Đang dùng dữ liệu mẫu từ thư mục data/."
    try:
        live, label = get_vnindex_history(months=18, source=source)
        macro = local_macro.copy()
        macro["date"] = _to_datetime_ns(macro["date"])
        live = live.copy()
        live["date"] = _to_datetime_ns(live["date"])
        macro = macro.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
        live = live.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
        merged = pd.merge_asof(
            macro,
            live,
            on="date",
            direction="nearest",
            tolerance=pd.Timedelta(days=10),
            suffixes=("_local", ""),
        )
        if "vnindex" not in merged.columns or merged["vnindex"].isna().all():
            raise RuntimeError("Dữ liệu live không khớp được với lịch tháng trong file mẫu")
        if "vnindex_local" in merged.columns:
            merged["vnindex"] = merged["vnindex"].fillna(merged["vnindex_local"])
            merged = merged.drop(columns=["vnindex_local"])
        if "market_volatility_pct" not in merged.columns:
            merged["market_volatility_pct"] = merged["vnindex"].pct_change().rolling(3).std().fillna(0) * 100
        return merged, label, "Đã kết nối dữ liệu thị trường live. Các chỉ tiêu vĩ mô khác vẫn dùng proxy nội bộ."
    except Exception as e:
        macro = local_macro.copy()
        return macro, "Dữ liệu mẫu nội bộ", f"Không lấy được dữ liệu live trên môi trường hiện tại, dùng fallback. Lý do: {e}"
