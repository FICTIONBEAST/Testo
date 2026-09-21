# Oil thesis: long the front, short the peace

**Date:** 21 September 2026 (market data 12:48 UTC) · **Horizon:** to the 3 November US midterms, then a pre-written reversal · **Status:** live; refresh weekly with `python3 oil_thesis/analysis.py`

---

## 0. The call

**Direction: LONG oil, tactically, through the pre-election window. Flat by Friday 23 October. Flip to a short-the-curve position after 3 November, or earlier if the trigger board in §6 fires.**

In one paragraph: the physical market is the tightest it has been all year (Hormuz transits at 5–10 % of normal, Saudi Arabia's Hormuz-bypass pipeline shut since 10–11 September, US distillate stocks 13 % below the five-year average after touching 1996 lows, the US Strategic Petroleum Reserve at a 1983 low), while the political calendar explicitly defers resolution: the President has said three times since 9 September that the war ends "right after the midterms" and that oil will "come tumbling down" *then*, and Iran's parliament speaker said on 20 September that Hormuz stays shut until its seven conditions are met. Over the next five weeks the risk premium is therefore more likely to be rebuilt than removed, and a backwardated curve pays a long ~4 % per month simply to wait. The same calendar, however, makes a post-election de-escalation the base case, so the position carries a hard date, a defined loss, and a reversal that is written before entry, not after.

### Trade ticket

| Field | Value |
|---|---|
| Primary instrument | ICE Brent **Dec-26** futures (or CME Brent Last Day Financial `BZZ26`), expiry 30 Oct 2026 |
| Reference price | Dec-26 Brent **$96.92**; Nov-26 (prompt) $101.01; WTI Nov-26 $93.27 |
| Entry zone | $94–98 Dec-26, scaled over the UNGA week (22–26 Sep); no adds below $92 |
| Defined-risk version | Buy Dec-26 Brent $95 call / sell $120 call (≈ $9–10 debit at OVX 50); or futures + $82/$70 put spread |
| Retail / ETF version | BNO (Brent ETF) with a hard stop; USO if Brent access is unavailable (accept the $7.7 Brent–WTI basis) |
| Optional overlay | Long NY Harbor ULSD (`HO`) Dec-26 at ≤ 25 % of crude notional; see §5 for the US export-ban caveat |
| Risk budget | 1.5 % of capital. Stop / put strike at **$82** Dec-26 (−$15). Contracts = (1.5 % × capital) ÷ ($15 × 1,000 bbl) |
| Profit taking | ⅓ at $110, ⅓ at $120, remainder on a $10 trailing stop |
| Add rule | Add 50 % on a Dec-26 close above $105 **only if** no bearish trigger has fired |
| Hard time stop | Flatten by **23 Oct 2026** regardless of P&L (seven trading days before the election) |
| Reversal (Phase 2) | After 3 Nov, or on ≥ 3 bearish triggers: short Mar-27 / long Dec-27 Brent calendar spread (≈ $10.40 today; target $3, stop $16), or Mar-27 $85/$70 put spread |

---

## 1. Situation

### 1.1 Geopolitical

- **The war.** US–Israeli strikes on Iran began in late February 2026. The Strait of Hormuz has been effectively closed to commercial traffic for ~204 days. A two-week ceasefire in April and a 14-point memorandum on 17 June (60 days of toll-free passage, demining within 30 days) both collapsed; the US naval blockade of Iranian exports was reinstated on 14 July and Kharg Island loadings halted on 31 July.
- **This month's escalation ladder.** 5–9 Sep: the US sank eight Iranian tankers in two waves; Iran struck ten ships, two US vessels and a US base in Jordan; Iran declared a "restricted zone" from the US blockade line into the Gulf of Oman. 10–11 Sep: drones launched from Iraq hit Saudi Arabia's East–West pipeline (the 5 mb/d Hormuz bypass to Yanbu) in "at least eight places"; Riyadh shut it. 13 and 19 Sep: Houthi strikes on Yanbu; on 19 Sep the first ballistic missile aimed at Riyadh. 20 Sep: parliament speaker Ghalibaf: "there will be no opening" of Hormuz until Iran's conditions are met, delivered via Qatar as seven demands.
- **Diplomacy.** The GCC–Iran meeting in Salalah (14 Sep) was postponed indefinitely after Bahrain objected and Washington warned Gulf states against a deal without the US. Qatar is shuttling proposals; Araghchi is in Doha and then New York for UN General Assembly week; Trump meets Gulf leaders on 22 Sep and Xi on 24 Sep (Treasury is preparing secondary sanctions on Iran's "enablers", which principally means Chinese buyers). Prediction markets price Hormuz traffic returning to normal by 30 September at ~2 %.
- **The US political calendar.** Trump, 9/12/18 Sep: the war ends "immediately after the election… oil prices are going to be tumbling downward"; gasoline is $4.28 (AAA, 10 Sep) and diesel $5.78. He has also floated a "big decision" on a campaign to "annihilate" the regime and "staying to keep the oil, like Venezuela". Midterms: **3 November**.
- **Supply-side politics.** OPEC+ completed the unwind of its 2023 cuts with the September increment and is holding October flat, but quotas are academic: Saudi output fell to 6.24 mb/d in August (−1.9 mb/d m/m) and Iran to 2.09 mb/d. Russia is selling Urals at ~$60 under a US sanctions waiver. The IEA's 400 mb collective stock release (11 March) is spent; the US SPR sits at 308 mb, the lowest since 1983, and DOE's refill mandate is now a source of *demand*.

### 1.2 Economic

- **Stagflation is here, and the Fed is fighting the inflation half.** CPI 3.37 % (July) with energy +14.7 %; core 2.48 %; unemployment 4.1 %. The FOMC hiked 25 bp on 16 September to 3.75–4.00 % by a 12–0 vote, the first hike since 2023; 16 of 18 participants project another. The dollar index moved from 99.1 to 100.3 on the week. The 2-year sits ~4.4 %, the 10-year ~4.8 %.
- **Demand destruction is real and already in the forecasts.** IEA (September OMR): 2026 demand −2.5 mb/d (Q3 −3.4, Q4 −2.0), recovering +2.6 mb/d in 2027; losses concentrated in Asian middle distillates and petrochemical feedstock. China's crude imports fell 32 % in Q2 to 8.1 mb/d; Sinopec sees Chinese demand −8.9 % in 2026. OPEC still models +0.38 mb/d for 2026, a large and unresolved divergence.
- **Equities are not yet pricing recession.** S&P 500 ~7,590 on 10 Sep, 2.7 % below its 13 August high; oil volatility (OVX) 50, down from 63 on 14 Sep.
- **Consensus is far below spot.** EIA STEO (Sept): Brent ~$90 average for 2H26. Post-June bank calls (MS $75, GS 2027 $75, JPM Q3 $86) predate the July breakdown and the Saudi damage.

### 1.3 Physical balance

- **Supply:** world output 100.1 mb/d in August (−1.6 m/m); more than 10 mb/d of Gulf output shut in; 2026 supply 100.7 mb/d (−5.7 y/y) with full Middle East recovery deferred to 2027 (IEA). Saudi Arabia is exporting via escorted "dark" transits along the Omani coast (one recent day: ~6 mb, half the Gulf's outflow) and is expected to restart the East–West line at 40–60 % capacity within roughly two weeks; Yanbu held only 5–7 days of stock at the shutdown. US shale is not responding: rig count +43 y/y, EIA expects only +0.2 mb/d of US growth in 2026.
- **Stocks:** global inventories −400 mb year-to-date (EIA). US commercial crude 423.4 mb (+1 % vs five-year average) but distillate 13 % below and gasoline 6 % below; refinery utilisation 97.8 %, i.e. no slack. Distillate stocks touched 107.1 mb on 7 August, the lowest for the date since 1996.
- **Cracks and freight:** US diesel crack a record $106/bbl on 1 Sep and still ~$105 vs WTI today (normal: $15–25); VLCC Middle East–China earnings a record ~$800k/day; war-risk premiums 40× pre-crisis with six P&I clubs withdrawing cover; Dated Brent traded above $140 and Dubai to $170 at the April peak.
- **Q4 arithmetic:** demand recovers ~1.4 mb/d from Q3 to Q4 (IEA path) while supply is flat to lower until the Saudi bypass and Hormuz normalise. That is a ~1–1.5 mb/d deficit drawn from already-depleted stocks in the heating season.

### 1.4 What the market is pricing (pulled via Coupler.io → Yahoo Finance, `oil_thesis/data/`)

| Contract | Brent 11 Sep | Brent 21 Sep | Δ | WTI 11 Sep | WTI 21 Sep | Δ |
|---|---:|---:|---:|---:|---:|---:|
| Nov-26 (prompt) | 105.24 | **101.01** | −4.23 | 96.05 | **93.27** | −2.78 |
| Dec-26 | 100.20 | **96.92** | −3.28 | 91.49 | 89.76 | −1.73 |
| Mar-27 | 89.25 | 89.43 | +0.18 | 81.75 | 82.44 | +0.69 |
| Jun-27 | 83.04 | 84.17 | +1.13 | 76.17 | 78.07 | +1.90 |
| Dec-27 | 77.52 | 79.03 | +1.51 | 71.63 | 73.38 | +1.75 |

| Metric | 11 Sep | 21 Sep |
|---|---:|---:|
| Brent M1–M2 spread ($/bbl) | 5.04 | 4.09 |
| Brent prompt minus Dec-27 | 27.72 | 21.98 |
| Brent–WTI (Nov) | 9.19 | 7.74 |
| ULSD crack vs WTI ($/bbl) | 106.43 | 104.88 |
| RBOB crack vs WTI | 36.33 | 41.31 |
| 3-2-1 crack | 59.69 | 62.50 |
| OVX (30-day implied vol) | 58.1 | 50.4 |
| DXY | 99.09 | 100.27 |
| Roll: Dec-26 → prompt if unchanged | +5.0 % | +4.2 % |

Read: the week's four-day slide took ~$4 off the prompt and *added* ~$1.5 to Dec-27. The market is saying "less acute today, but the equilibrium after the crisis is higher than we thought" (SPR refill demand, shale discipline, damaged Gulf infrastructure). Backwardation is still steep: a Dec-26 long earns ~4 % per month of convergence if the prompt merely holds. 52-week context (weekly bars): low $58.72 (mid-Dec 2025), high $126.10 (w/o 27 Apr), pre-war close $72.48, June trough $70.14; the April peak to June trough was −44 % in nine weeks; realised weekly volatility since the war began annualises to ~70 %.

---

## 2. Why long, and why not short, now

1. **Supply loss still exceeds demand loss.** −5.7 mb/d of 2026 supply against −2.5 mb/d of demand, and the Q3→Q4 seasonal demand recovery arrives before any Gulf supply recovery. The IEA has cut its demand forecast five months running and *still* shows the balance tightening into Q4.
2. **The buffers that broke the March–June spike are gone.** In March the system absorbed the shock with 400 mb of coordinated stock releases and normal product inventories. Today the SPR is at 308 mb, Europe is guarding what is left, distillate is at multi-decade lows, and refineries run at 98 %. The next supply hit meets a market with no cushion, which is why the diesel crack is $105 and freight is at records. Convexity is to the upside.
3. **The political calendar defers the bearish catalyst.** The administration is telling voters not to expect relief before 3 November; Iran is telling its public the strait stays shut until seven conditions are met and that it is prepared for a "decisive war". A deal that takes both sides' stated positions at face value sits *after* the horizon of this trade. The pre-election tail is the "big decision" on a major strike, which is to the upside.
4. **Carry favours the long.** At $4.09 of prompt backwardation, a short pays ~4 % a month to wait for a catalyst the President has scheduled for November. A long is paid the same amount to be wrong on timing.
5. **The deferred curve already prices normalisation.** Dec-27 Brent at $79 sits below the EIA's $90 2H26 average and near the pre-June bank forecasts. A short in the back has little left to earn; a short in the front is a bet on a pre-election deal.
6. **Positioning is not yet crowded.** Managed-money Brent net length of ~265k lots (8 Sep) is elevated but below its May peak, and funds net-sold gasoline and diesel in the week to 15 September. There is room for the pain trade to be higher.

**Why not short now, despite the four-day slide:** the slide was headline-driven (Qatar-mediated messages, UNGA meetings, escorted Saudi transits, a pipeline restart "soon"). None of those changes the physical balance before November; the escorted transits are still a fraction of pre-war flows and remain under attack (a vessel was struck in the strait on 12 September). The June template (−44 % in nine weeks) needed a signed memorandum, an SPR with a third more oil in it and normal product stocks; a repeat from here is possible but would find a higher floor.

---

## 3. The short thesis, and when it becomes the trade

The case for being short is real and it is *the same facts with a different clock*:

- Demand destruction compounds: China −8.9 %, Asia distillate demand collapsing, the Fed hiking into an energy shock, the dollar above 100.
- The end of the war is being telegraphed by the one actor who can end the blockade, and markets discount known events early; the June collapse began five weeks before the memorandum was signed.
- Saudi barrels are leaking out under US escort; the East–West line restarts within weeks; Iran is selectively admitting "friendly" tonnage (India). Every increment of flow removes premium.
- A US product-export restriction, officially "not under consideration" but under rising pressure (Khanna's Gasoline Export Ban Act), would crush NY Harbor product cracks and push WTI down relative to Brent.
- Speculative length is elevated and headline-sensitive: the 11 September and 21 September sessions each gave back 4–6 % on talk alone.

**When it becomes the trade.** (a) After 3 November, as the base case, regardless of whether a deal has been announced; the market will front-run the President's own timetable. (b) Earlier, the moment three of the bearish triggers in §6 have fired. (c) Immediately, in the escalation scenario, *if* the escalation is a decisive US strike that the market reads as war-ending (the "annihilate" case): sell the spike, because that is the June pattern in fast-forward.

**Expression.** Prefer the curve to flat price: short Mar-27 / long Dec-27 Brent. A deal collapses backwardation (front falls, back barely moves, as in April–June when Dec-26 "barely moved"); escalation widens it. Entry ≈ $10.40, target $3, stop $16. For outright exposure use a Mar-27 $85/$70 put spread; do not short futures naked into an OVX-50 market with a $30 upside tail. **Targets after a deal:** $80–85 Brent within six to eight weeks, not $70: mine clearance is 40–50 days (Pentagon: up to six months), insurance is "quick up, slow down", the SPR must be refilled (~$20 bn programme), Saudi infrastructure is damaged, and northern-hemisphere winter demand for distillate peaks in Q1.

---

## 4. Scenarios and expected value (judgmental probabilities; instrument = Brent Dec-26 at $96.92; horizon 23 Oct)

| Scenario | P | Dec-26 on 23 Oct | P&L / bbl | What it looks like |
|---|---:|---:|---:|---|
| A. De-escalation path | 30 % | $82 | −14.9 | UNGA meeting or Qatar framework with a date; Hormuz transits > 25/day; escorted flows scale; Fed hawkish; equities −5 % |
| B. Grind | 45 % | $102 | +5.1 | No deal, no new losses; East–West restarts at half capacity; Hormuz 5–15 %; roll carries the long |
| C. Escalation | 25 % | $128 | +31.1 | Major US strike campaign; hits on Ras Tanura / Juaymah / Fujairah; Bab el-Mandeb closure; Kuwait or Iraq export halts |

Expected value: **+$5.6/bbl for the long** (−$5.6 for the short). The long's EV goes negative only if the probability of scenario A before 23 October exceeds **49 %**. Note the shape: the long's loss is bounded by structure ($15 by stop or put strike), its gain is not; the short's gain is bounded (~$15) and its loss is not. That asymmetry, not the point estimate, is the reason for the direction. Reproduce with `python3 oil_thesis/analysis.py`.

---

## 5. Trade construction

**Instrument choice.** Brent over WTI: the shortage is seaborne and Asian; WTI is landlocked in a market whose crude stocks are *above* the five-year average, hence the $7.7 basis. Crude over products for the core: the ULSD crack at $105 is the single most extreme number in the complex and is exposed to a US export restriction (NY Harbor ULSD would be *hit* by a ban that keeps product at home). If you want distillate, cap it at a quarter of the crude notional and treat it as the winter kicker.

**Structure by account type.**

| Account | Long expression | Loss cap | Notes |
|---|---|---|---|
| Futures | Long Brent Dec-26; stop $82 | $15/bbl (gap risk) | Roll into Jan-27 only if still long on 23 Oct (you should not be) |
| Futures + options | Long Dec-26 + buy $82 put / sell $70 put; optionally sell $130 call to fund | ~$15 + net premium | Keeps upside to $130; call sale is the cost of cheap protection |
| Options only | Dec-26 $95/$120 call spread | Premium (~$9–10) | Max gain ~$15 net; theta bleeds if B is slow |
| ETF / equity account | BNO shares, 25 % below full risk size; hard stop | Position size | Contango/backwardation roll is inside the ETF; backwardation helps |
| Equities (beta play) | XOP / XLE | Market risk | Beta to oil ~0.5–0.7 and to the S&P ~1; a Fed-driven equity selloff can lose money while oil rises. Not recommended as the primary expression |

**Sizing.** Risk 1.5 % of capital to the thesis. With a $15 stop and 1,000 bbl per contract, that is one Brent contract per $1.0 m of capital, or ~$35–40k of BNO per $1.0 m. At OVX 50 the one-day one-sigma move is ~3.2 %, so a $15 stop is ~4.5 daily sigmas; expect to be tested.

**Entry.** Scale a third per day over 22–24 September (UNGA and Trump–Xi headlines), the balance on a Dec-26 close back above $100. Do not chase above $105 unless the add rule is met.

**Calendar (all dates 2026).**

| Date | Event | Action |
|---|---|---|
| 22 Sep | Trump meets Gulf leaders; UNGA week opens; Araghchi in Doha | Begin scaling in |
| 24 Sep | Trump–Xi summit (secondary sanctions on Iranian oil buyers) | Expect two-way headlines; hold |
| 30 Sep | Nov-26 Brent expiry; Dec-26 becomes prompt | Convergence check: Dec-26 should gain on the roll |
| ~early Oct | East–West pipeline partial restart (consensus ~2 weeks from 15 Sep) | Bearish trigger 4 watch |
| mid-Oct | NOAA winter outlook; IEA/OPEC October reports; Q3 earnings | Distillate overlay decision |
| **23 Oct** | Seven trading days pre-election | **Flatten the long. No exceptions.** |
| 30 Oct | Dec-26 Brent expiry | Nothing should be open |
| **3 Nov** | Midterms | Phase 2 window opens |
| 4 Nov onward | "Immediately after the election" | Enter bear calendar spread / put spread on the first close that fails to make a new high |

---

## 6. Trigger board (measurable; the code in `oil_thesis/signals.py` scores these)

**Bearish triggers (cut the long at 2; flip to Phase 2 at 3):**

| # | Trigger | Threshold | Source |
|---|---|---|---|
| B1 | Direct US–Iran senior talks scheduled or a Trump–Pezeshkian/Araghchi meeting with a published framework | Any confirmed date | Qatar/Oman MFA, White House |
| B2 | Hormuz transits | 5-day average > 25 ships/day (vs ~8 now, ~85 normal) | IMF PortWatch, Windward, straits.live |
| B3 | Brent M1–M2 spread | < $1.50 (from $4.09) | ICE settlements / the Coupler.io curve pull |
| B4 | Saudi bypass restored | East–West > 4 mb/d **and** Yanbu loading normally **and** 14 days without a strike on Saudi energy assets | Aramco, Kpler, satellite flaring |
| B5 | Crowding | Managed-money Brent net long > 350k lots while price fails to make a new high | ICE COT (Fridays) |
| B6 | US product export restriction announced | Any | DOE / White House |
| B7 | Demand shock through markets | S&P 500 > 7 % below its 13 Aug high (7,799) **and** the Fed signalling further hikes | Market data |

**Bullish triggers (hold; add on two):**

| # | Trigger |
|---|---|
| U1 | US strike campaign against Iranian leadership or energy infrastructure ordered |
| U2 | Strike on Ras Tanura, Juaymah, Fujairah, Habshan, or Basra loading |
| U3 | Bab el-Mandeb effectively closed to Saudi/UAE tonnage (Houthi blockade enforced) |
| U4 | Iran attacks a US carrier or a GCC capital with mass-casualty effect |
| U5 | Hormuz 5-day transits fall below 5/day, or escorted Saudi transits halted |
| U6 | Distillate stocks fall week-on-week into October (counter-seasonal draw) |

**Invalidation of the whole framework:** a signed, dated reopening agreement with US participation before the election, or a decisive regime-change strike the market reads as war-ending. Either way: go flat immediately, then re-enter Phase 2 on the first failed rally.

---

## 7. What would make this wrong

- **The President moves the timetable forward.** He has an incentive to; the only stated constraint is Iran's seven conditions. If Qatar lands a framework during UNGA week, scenario A arrives inside the horizon and the long loses its $15 fast. This is why the entry is scaled and the loss defined.
- **Demand falls faster than supply.** A Fed hiking into 3.4 % headline inflation with energy at +14.7 % is the 2022 template, when oil fell from $120 to $80 in six months despite a war. The difference now is the size of the physical loss (10 mb/d Gulf shut-in vs a Russian rerouting) and the absence of an SPR to lean on; the similarity is that demand destruction is unforgiving in the products. Watch B7.
- **Escorted flows scale quietly.** If US-protected dark transits reach 20–30 ships a day and Iran declines to attack them, the premium erodes without a headline. B2 catches this.
- **The June memory is stronger than the physical facts.** Funds got burned in June; every rally now meets sellers at $105–110. That is why profit-taking is staged rather than left to a single target.
- **Weather.** A strong El Niño points to a milder northern-tier US winter, which blunts the distillate kicker; NOAA's mid-October outlook is the check.
- **Model risk.** Scenario probabilities are judgmental, from a single crisis year; there is no back-test that covers a closed Hormuz. The trade's risk control is structural (stop, put strike, time stop), not statistical.

---

## 8. Data provenance

| Item | Source / tool | Notes |
|---|---|---|
| Futures curve (Brent & WTI Nov-26…Dec-27), ULSD, RBOB, OVX, DXY | **Coupler.io → Yahoo Finance Price** source, dataflow `98da0d11-063d-4119-af02-d925bf18efba` | Snapshots 11 Sep and 21 Sep in `oil_thesis/data/`; the free plan caps 100 rows per source and one connection, so the source was re-pointed between a 5-day multi-ticker curve pull and a 1-year weekly Brent pull |
| Brent 52-week weekly bars | same dataflow, `BZ=F` 1wk/1y | `brent_weekly_1y_2026-09-14.csv` |
| WTI monthly spot, CPI, unemployment, Fed funds, Treasury curve, S&P 500 | **Wolfram Alpha** | Aug/Sep 2026 prints |
| IEA OMR Sept 2026, OPEC MOMR Sept 2026, EIA STEO Sept 2026, EIA WPSR (w/e 4 and 11 Sep) | Web search (agency pages are egress-blocked from this sandbox; figures via Argus, Reuters, Rigzone, BOE Report, IndexBox summaries) | Cross-checked where two sources reported the same figure |
| Hormuz transits, insurance, vessel counts | straits.live, IMF PortWatch, Windward, S&P Global, RFE/RL | Counts vary with AIS spoofing; use 5-day averages |
| Saudi output, Abqaiq, East–West pipeline, Yanbu | OPEC secondary sources via Azertac/Reuters, CNBC, Al Jazeera, OilPrice, Wikipedia timeline | |
| Positioning | Bloomberg/ICE COT via John Kemp, Saxo COT (w/e 15 Sep) | |
| Politics and diplomacy | CNBC, CNN, Al Jazeera, Al Arabiya, Axios, The Hill, Time, Semafor, Fox, Oman Observer, TASS | Quotes checked across at least two outlets |
| Prediction markets | Polymarket, Kalshi, Lines.com | Hormuz normal by 30 Sep ≈ 2 % yes; pipeline restart by 30 Sep ≈ 63 % |
| Bank forecasts | OilPrice, TheStreet, Invezz (post-June) | Stale; included for what consensus has *not* updated |

Not used: **FactSet AI-Ready Data** is installed on this account but its connection is incomplete; connect it for institutional curve, COT and physical-assessment data and it slots into §9 below.

---

## 9. Operationalising the thesis (engineering notes)

You asked for the things a software/database engineer would miss. Here is how this thesis becomes a monitored system rather than a document.

**Pipeline.** Coupler.io already speaks to Yahoo Finance without credentials (done: the dataflow above), and it can land data in PostgreSQL, Supabase, BigQuery or Snowflake as destinations. Schedule the two pulls (daily curve, weekly Brent) into a Postgres table; add three more sources that need no vendor: EIA API v2 (weekly stocks, refinery runs, SPR; free key), CFTC/ICE COT (weekly CSV), IMF PortWatch (daily chokepoint transits, public CSV). The free Coupler tier stopped this session at 100 rows per source and one connection; the paid tier or direct API calls remove that.

**Schema.** One narrow fact table `market_obs(ts, symbol, field, value, source)` with a `(symbol, field, ts)` index beats wide tables when tickers change weekly. Put the trigger thresholds in a `rules` table with `valid_from/valid_to` so the board in §6 is versioned data, not code; `signals.py` reads them.

**Scoring job.** `oil_thesis/signals.py` is pure Python with no dependencies; run it from a GitHub Actions cron (free) or a $5 VPS with `systemd` timers, write the verdict back to Postgres, and alert on state changes only (LONG→REDUCE etc.), never on every run. The tests in `test_signals.py` pin the thresholds so a threshold edit without a test edit fails CI.

**Dashboard.** Coupler.io's "live artifact" skill can render a Cowork page directly over the dataflow; otherwise a single static page rebuilt by `build_report.py` on each cron run and served from object storage (S3/R2 + Cloudflare) costs nothing and needs no server. Keep the report's source data inline so the page is self-contained when shared.

**Hosting and network.** Nothing here needs inbound ports: pulls are outbound HTTPS, the report is static. If you self-host Postgres, bind it to localhost or a Tailscale/WireGuard interface, never 0.0.0.0; use `pg_dump` nightly to object storage; the whole system fits in 1 vCPU / 1 GB. Secrets (EIA key, DB URL) in the runner's secret store, not the repo.

**Modelling, honestly.** A kNN or clustering "regime" classifier on (M1–M2 spread, OVX, DXY, ULSD crack, transits/day) is cheap to build and useful as a *label* for the dashboard (calm / stressed / crisis), but 2026 is one crisis with ~150 daily observations; do not size positions from it. Logistic regression on headline features for "deal within 30 days" has the same problem. The prediction-market probabilities (Polymarket/Kalshi have public APIs) are a better external prior than anything fitted to this sample; pull them into the same table and chart them against the M1–M2 spread.

---

*This is a research thesis with a defined risk framework, not personalised investment advice. Futures and options can lose more than the initial margin; the ETF expressions can lose their full value. All prices are as of the timestamps shown and will be stale by the time you read this; re-run the pull before acting.*
