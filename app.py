import streamlit as st
import pandas as pd
import time
from src.trading.config import CANDIDATES, Settings
from src.trading.data import CoinDCXPublic, DataError
from src.trading.strategy import analyze
from src.trading.demo import demo_candles

st.set_page_config(page_title="202650 | Trading Intelligence", page_icon="◈", layout="wide")
st.markdown("""<style>
.block-container{padding-top:1.4rem;max-width:1500px}.hero{padding:1.2rem 1.4rem;border:1px solid #203249;border-radius:16px;background:linear-gradient(115deg,#101e31,#102b32)}
.small-muted{color:#93a4ba;font-size:.88rem}.decision{font-size:1.2rem;font-weight:800}.stMetric{background:#111d2e;border:1px solid #203249;padding:12px;border-radius:12px}
</style>""", unsafe_allow_html=True)

st.markdown('<div class="hero"><h1>◈ 202650</h1><div>CRYPTO TRADING INTELLIGENCE · BOLLINGER BANDS MEAN REVERSION V1</div><p class="small-muted">Capital protection first · Deterministic rules · No forced signals</p></div>',unsafe_allow_html=True)
st.warning("Analysis application only. CoinDCX public API futures order execution is not enabled or supported in this build. Signals are not financial advice.")

with st.sidebar:
    st.header("Configuration")
    mode=st.radio("Data mode",["Live public CoinDCX data","Demo data (synthetic)"],index=0)
    st.caption("Demo data is synthetic and cannot be used as a real market signal.")
    equity=st.number_input("Account equity reference (USDT)",min_value=10.0,value=1000.0,step=100.0)
    risk_pct=st.slider("Risk per trade (%)",0.05,1.0,0.25,0.05)
    daily_limit=st.slider("Daily loss limit (%)",0.25,5.0,1.0,0.25)
    consecutive=st.number_input("Consecutive losses today",0,10,0)
    daily_loss_amount=st.number_input("Realized daily loss (USDT)",min_value=0.0,value=0.0,step=1.0)
    spread_limit=st.slider("Max spread (%)",0.01,1.0,0.15,0.01)
    fee=st.number_input("Estimated fee per side (%)",0.0,1.0,0.05,0.01)
    slip=st.number_input("Estimated slippage per side (%)",0.0,1.0,0.03,0.01)
    rr_min=st.slider("Minimum net R:R",1.0,5.0,1.5,0.1)
    scan=st.button("⟳ Scan markets",type="primary",use_container_width=True)
    st.caption("Live scan may take time due to API requests and rate limits.")

settings=Settings(risk_pct=risk_pct,daily_loss_pct=daily_limit,spread_limit_pct=spread_limit,fee_pct_per_side=fee,slippage_pct_per_side=slip,min_rr=rr_min)
if "results" not in st.session_state: st.session_state.results=[]
if scan:
    results=[]; errors=[]; progress=st.progress(0)
    if mode.startswith("Live"):
        client=CoinDCXPublic()
        try:
            instruments=client.active_instruments(); prices=client.current_prices()
            price_map=prices.get("prices",{})
            chosen=client.map_candidates(instruments, CANDIDATES, price_map)
            st.session_state.active_universe=chosen
            missing=[ticker for ticker in CANDIDATES if ticker not in chosen]
            for ticker in missing:
                results.append({"coin":ticker,"pair":"UNMAPPED","decision":"NO TRADE","status":"DATA ERROR",
                               "reason":"No exact active USDT futures contract with a price-feed entry was found.",
                               "conditions":{},"metrics":{},"trade_plan":None,"quality_score":0,"market_regime":"UNKNOWN",
                               "price":None,"source":"CoinDCX public futures data","data_timestamp":"Unavailable"})
            for i,(ticker,pair) in enumerate(chosen.items()):
                try:
                    pinfo=price_map.get(pair,{})
                    last=float(pinfo.get("ls") or pinfo.get("mp") or 0)
                    tick_ts=pinfo.get("btST") or pinfo.get("cmRT") or prices.get("ts")
                    stale=client.tick_is_stale(tick_ts)
                    candles=client.candles_15m(pair,lookback_minutes=3000)
                    h1=client.candles_1h(pair,lookback_minutes=6000)
                    book=client.orderbook(pair,depth=20)
                    candle_stale=(len(candles)==0 or (pd.Timestamp.now(tz="UTC")-candles.index[-1]).total_seconds()>1800)
                    stale=stale or candle_stale
                    decision=analyze(pair,candles,h1,last,settings,equity=equity,daily_loss=daily_loss_amount,consecutive_losses=consecutive,spread_pct=book.get("spread_pct"),stale=stale,orderbook=book)
                    decision.update(coin=ticker,price=last,source="CoinDCX public futures data",data_timestamp=str(candles.index[-1]) if len(candles) else "Unavailable",orderbook=book)
                    results.append(decision)
                except Exception as e:
                    results.append({"coin":ticker,"pair":pair,"decision":"NO TRADE","status":"DATA ERROR","reason":str(e),
                                   "conditions":{},"metrics":{},"trade_plan":None,"quality_score":0,"market_regime":"UNKNOWN",
                                   "price":None,"source":"CoinDCX public futures data","data_timestamp":"Unavailable"})
                    errors.append(f"{ticker} ({pair}): {e}")
                progress.progress((i+1)/max(1,len(chosen)))
            if not chosen: errors.append("No exact candidate futures contracts could be mapped to active CoinDCX instruments.")
        except Exception as e:
            errors.append(f"CoinDCX API error: {e}")
            results=[{"coin":ticker,"pair":"UNAVAILABLE","decision":"NO TRADE","status":"DATA ERROR","reason":str(e),"conditions":{},"metrics":{},"trade_plan":None,"quality_score":0,"market_regime":"UNKNOWN","price":None,"source":"CoinDCX public futures data","data_timestamp":"Unavailable"} for ticker in CANDIDATES]
    else:
        for i,ticker in enumerate(CANDIDATES):
            df=demo_candles(seed=10+i)
            h1=df.resample("1h").agg({"open":"first","high":"max","low":"min","close":"last","volume":"sum"}).dropna()
            demo_spread=0.04
            demo_book={"best_bid":float(df.close.iloc[-1])*(1-demo_spread/200),"best_ask":float(df.close.iloc[-1])*(1+demo_spread/200),"spread_pct":demo_spread,"bid_depth":1000,"ask_depth":1000,"timestamp_ms":int(time.time()*1000)}
            result=analyze(ticker+"_USDT",df,h1,float(df.close.iloc[-1]),settings,equity=equity,daily_loss=daily_loss_amount,consecutive_losses=consecutive,spread_pct=demo_spread,orderbook=demo_book)
            result.update(coin=ticker,price=float(df.close.iloc[-1]),source="SYNTHETIC DEMO DATA",data_timestamp=str(df.index[-1]),orderbook=demo_book)
            results.append(result); progress.progress((i+1)/len(CANDIDATES))
    st.session_state.results=results; st.session_state.errors=errors; st.session_state.scan_time=time.strftime("%Y-%m-%d %H:%M:%S UTC",time.gmtime())

results=st.session_state.results
errors=st.session_state.get("errors",[])
scan_time=st.session_state.get("scan_time","Not scanned yet")
if results:
    counts={s:sum(r.get("decision")==s for r in results) for s in ["LONG","SHORT","WAIT","NO TRADE"]}
    c=st.columns(5)
    c[0].metric("Markets evaluated",len(results)); c[1].metric("LONG",counts["LONG"]); c[2].metric("SHORT",counts["SHORT"]); c[3].metric("WAIT",counts["WAIT"]); c[4].metric("NO TRADE",counts["NO TRADE"])
    data_errors=sum(r.get("status")=="DATA ERROR" for r in results)
    st.caption(f"Last scan: {scan_time} · Data errors: {data_errors} · News data: **NEWS DATA UNAVAILABLE** · Data mode: {results[0].get('source','unknown')}")
    df=pd.DataFrame([{ "Coin":r.get("coin"),"Pair":r.get("pair"),"Status":r.get("status","OK"),"Decision":r.get("decision"),"Price":r.get("price"),"Spread %":r.get("spread_pct"),"RSI":r.get("metrics",{}).get("rsi"),"ADX":r.get("metrics",{}).get("adx"),"Regime":r.get("market_regime"),"Quality (not win probability)":r.get("quality_score"),"Reason":r.get("reason")} for r in results])
    st.subheader("Market Scanner")
    st.dataframe(df,use_container_width=True,hide_index=True)
    qualified=[r for r in results if r.get("decision") in ["LONG","SHORT"]]
    if qualified:
        st.subheader("Qualified setups")
        for r in sorted(qualified,key=lambda z:z.get("quality_score",0),reverse=True):
            p=r["trade_plan"]
            with st.expander(f"{r['decision']} · {r['coin']} · quality {r['quality_score']}/100",expanded=True):
                a=st.columns(4); a[0].metric("Entry",f"{p['entry']:.8g}");a[1].metric("Stop-loss",f"{p['stop_loss']:.8g}");a[2].metric("Target",f"{p['take_profit']:.8g}");a[3].metric("Net R:R",f"{p['reward_to_risk']:.2f}")
                st.write(f"**Size estimate:** {p['position_size_units']:.8g} units · **Notional:** {p['estimated_notional']:.2f} USDT · **Risk:** {p['max_loss_before_costs']:.2f} USDT")
                st.write(f"RSI {p['rsi']:.2f} · ADX {p['adx']:.2f} · ATR {p['atr']:.8g} · BB lower/mid/upper {p['bb_lower']:.8g} / {p['bb_mid']:.8g} / {p['bb_upper']:.8g}")
                st.info("Signal logic passed. This is an analysis reference, not an executable order. Fees/slippage are estimates; higher timeframe context and contract constraints may not be fully verified.")
    st.subheader("Market Details")
    for r in results:
        with st.expander(f"{r.get('coin')} · {r.get('decision')} · {r.get('pair')}"):
            st.write(r.get("reason")); st.write("**Status:**",r.get("status","OK")); st.write("**Condition checks:**"); st.json(r.get("conditions",{})); st.write("**Metrics:**"); st.json(r.get("metrics",{})); st.write("**Warnings:**",r.get("warnings",[])); st.write("**Orderbook:**",r.get("orderbook",{}));
            if r.get("trade_plan"): st.json(r["trade_plan"])
    st.download_button("Export scan CSV",df.to_csv(index=False),"202650_scan.csv","text/csv")
if errors:
    st.error("Data / scanner errors")
    for e in errors: st.write("•",e)

# Page navigation via tabs
st.divider(); tabs=st.tabs(["Dashboard","Strategy & Rules","Risk Management","Backtesting","Paper Trading","Trade History","Settings & API"])
with tabs[0]:
    st.markdown("### Scanner health")
    st.write("Scanner status:","Scanned" if results else "Not scanned")
    st.write("Last update:",scan_time)
    st.write("Active markets:",len(results))
    st.write("API errors:",len(errors))
    st.write("BTC market context: available only when BTC is successfully scanned. No market-wide correlation block is currently applied.")
with tabs[1]:
    st.markdown("### Bollinger Bands Mean Reversion V1")
    st.write("BB(20, 2) · RSI(14) · ADX(14) · ATR(14) · primary 15-minute completed candles · 1-hour context.")
    st.markdown("**LONG:** ADX < 20; one of the prior two closes below lower BB; latest close re-enters above lower BB; RSI < 35; data, liquidity, risk, stop and net R:R checks pass.")
    st.markdown("**SHORT:** ADX < 20; one of the prior two closes above upper BB; latest close re-enters below upper BB; RSI > 65; all validations pass.")
    st.markdown("**WAIT:** potential excursion without completed re-entry. **NO TRADE:** failed conditions, invalid data, risk restriction, or unsuitable conditions.")
    st.caption("The implementation uses 5-minute futures candles aggregated into 15-minute bars because the public documentation currently lists 5-minute rather than 15-minute futures candle resolution. Only completed 15-minute aggregates are retained.")
with tabs[2]:
    st.markdown("### Risk controls (analysis sizing only)")
    st.write(f"Risk per trade: {risk_pct}% · Daily loss limit: {daily_limit}% · Max consecutive losses: 3 · Max simultaneous positions: 1")
    st.write("Martingale, averaging down, adding to losing positions, and automatic leverage escalation are prohibited by design.")
    st.write("Position size = equity × risk% ÷ stop distance. This estimate excludes contract multiplier, exchange quantity precision, minimum quantity, funding, and account margin constraints.")
with tabs[3]:
    st.markdown("### Backtesting")
    st.warning("Backtest engine not implemented in this initial package. Do not treat scanner results as strategy performance. The required no-lookahead, fee/slippage/funding, risk-limit, and train/test features remain to be built and verified.")
with tabs[4]:
    st.markdown("### Paper Trading")
    st.warning("Paper trade simulator not implemented in this initial package. Signals are analysis only; no simulated fills or portfolio tracking are claimed.")
with tabs[5]:
    st.markdown("### Trade History / Audit Log")
    st.info("This initial version does not persist evaluation history. Current scan can be exported as CSV. Persistent audit logging remains a planned module.")
with tabs[6]:
    st.markdown("### Settings & API status")
    st.write("Public market data only; no API credentials are requested or stored.")
    st.write("CoinDCX public docs: active futures instruments, current prices, and futures candlesticks endpoints are used. API schema/rate availability can change.")
    st.markdown("**Known limitations:** no private account balances, authenticated execution, news/event integration, funding-cost data, contract-precision sizing, or automated BTC-correlation protection in this build.")
    st.markdown("**News status:** NEWS DATA UNAVAILABLE")

st.caption("202650 · Accuracy over activity · No signal is a valid result · This tool is educational and informational, not financial advice.")
