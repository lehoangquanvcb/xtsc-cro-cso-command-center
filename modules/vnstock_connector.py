"""VNStock connector for XTSC demo.

The connector tries to load live market data from vnstock/vnstock3-compatible APIs.
If the cloud environment blocks the public API or the package interface changes,
it returns the local sample dataset so the dashboard remains deployable.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Tuple
import pandas as pd


def _standardize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).lower() for c in df.columns]
    # Common date/time column names across vnstock versions/providers
    for c in ["time", "date", "trading_date", "datetime"]:
        if c in df.columns:
            df["date"] = pd.to_datetime(df[c])
            break
    if "date" not in df.columns:
        df["date"] = pd.date_range(end=pd.Timestamp.today().normalize(), periods=len(df), freq="B")
    # Common close column names
    for c in ["close", "close_price", "match_price", "price"]:
        if c in df.columns:
            df["close"] = pd.to_numeric(df[c], errors="coerce")
            break
    if "close" not in df.columns:
        raise ValueError("Không tìm thấy cột giá đóng cửa từ dữ liệu vnstock")
    return df[["date", "close"]].dropna().sort_values("date")


def _history_with_new_vnstock(symbol: str, start: str, end: str, source: str) -> pd.DataFrame:
    # Newer vnstock versions keep backward compatibility through Vnstock,
    # but official docs note that interfaces are evolving in 2026.
    from vnstock import Vnstock  # type: ignore
    stock = Vnstock().stock(symbol=symbol, source=source)
    return stock.quote.history(start=start, end=end, interval="1D")


def _history_with_legacy_vnstock(symbol: str, start: str, end: str) -> pd.DataFrame:
    # Very old vnstock API fallback.
    from vnstock import stock_historical_data  # type: ignore
    return stock_historical_data(symbol=symbol, start_date=start, end_date=end)


def get_vnindex_history(months: int = 18, source: str = "VCI") -> Tuple[pd.DataFrame, str]:
    """Return VNINDEX history and data-source label.

    Output columns: date, vnindex, market_return_pct, market_volatility_pct.
    """
    end = date.today()
    start = end - timedelta(days=int(months * 31))
    start_s, end_s = start.isoformat(), end.isoformat()

    errors = []
    for symbol in ["VNINDEX", "VN-INDEX"]:
        try:
            raw = _history_with_new_vnstock(symbol, start_s, end_s, source)
            px = _standardize_ohlcv(raw)
            break
        except Exception as e:  # pragma: no cover - cloud/API dependent
            errors.append(f"{symbol}/{source}: {e}")
            px = None
    else:
        try:
            raw = _history_with_legacy_vnstock("VNINDEX", start_s, end_s)
            px = _standardize_ohlcv(raw)
        except Exception as e:  # pragma: no cover
            errors.append(f"legacy: {e}")
            raise RuntimeError("Không lấy được dữ liệu VNINDEX từ vnstock: " + " | ".join(errors))

    out = px.rename(columns={"close": "vnindex"})
    out["market_return_pct"] = out["vnindex"].pct_change().fillna(0) * 100
    out["market_volatility_pct"] = out["market_return_pct"].rolling(20).std().fillna(0)
    return out, f"vnstock live ({source})"


def enrich_macro_with_vnstock(local_macro: pd.DataFrame, use_live: bool = True, source: str = "VCI") -> Tuple[pd.DataFrame, str, str]:
    """Merge local macro proxy data with live VNINDEX if available."""
    if not use_live:
        return local_macro.copy(), "Dữ liệu mẫu nội bộ", "Đang dùng dữ liệu mẫu từ thư mục data/"
    try:
        live, label = get_vnindex_history(months=18, source=source)
        macro = local_macro.copy()
        macro["date"] = pd.to_datetime(macro["date"])
        live["date"] = pd.to_datetime(live["date"])
        merged = pd.merge_asof(
            macro.sort_values("date"),
            live.sort_values("date"),
            on="date",
            direction="nearest",
            tolerance=pd.Timedelta(days=10),
            suffixes=("_local", ""),
        )
        # Prefer live VNINDEX, keep local fallback for macro fields not available from vnstock.
        if "vnindex" not in merged.columns or merged["vnindex"].isna().all():
            raise RuntimeError("Dữ liệu live không khớp được với lịch tháng trong file mẫu")
        if "vnindex_local" in merged.columns:
            merged["vnindex"] = merged["vnindex"].fillna(merged["vnindex_local"])
            merged = merged.drop(columns=["vnindex_local"])
        if "market_volatility_pct" not in merged.columns:
            merged["market_volatility_pct"] = merged["vnindex"].pct_change().rolling(3).std().fillna(0) * 100
        return merged, label, "Đã kết nối vnstock. Các chỉ tiêu vĩ mô khác vẫn dùng proxy nội bộ."
    except Exception as e:
        macro = local_macro.copy()
        return macro, "Dữ liệu mẫu nội bộ", f"Không lấy được vnstock trên môi trường hiện tại, dùng fallback. Lý do: {e}"
