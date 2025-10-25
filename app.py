
import streamlit as st, pandas as pd
from pathlib import Path
st.set_page_config(page_title="NFL Edge Dashboard", layout="wide")
st.title("🏈 NFL Edge Dashboard - Betting Intelligence")
ROOT = Path(__file__).resolve().parent
arts = ROOT / "artifacts"
csvs = sorted(arts.glob("week_*_projections.csv"))
if not csvs:
    st.error("No projections found. Run `python3 run_week.py` after setting ODDS_API_KEY.")
    st.stop()
latest = csvs[-1]
st.caption(f"Loaded: {latest.name}")
df = pd.read_csv(latest)
df["Abs Edge (pts)"] = df.get("Edge_pts", 0).abs()
df["Abs Total Edge (pts)"] = df.get("Edge_total_pts", 0).abs()

st.subheader("Filters (adjust to find betting opportunities)")
col1, col2, col3 = st.columns(3)
with col1:
    edge_min = st.slider("Minimum spread edge (points)", 0.0, 10.0, 0.0, 0.5)
with col2:
    cover_min = st.slider("Minimum Home cover %", 0.0, 100.0, 0.0, 5.0)
with col3:
    over_min = st.slider("Minimum Over %", 0.0, 100.0, 0.0, 5.0)

filt = df[(df["Abs Edge (pts)"] >= edge_min) & (df["Home cover %"] >= cover_min) & (df["Over %"] >= over_min)]
st.caption(f"Showing {len(filt)} of {len(df)} games")

# Check if betting columns exist
has_betting = "Best_bet" in df.columns

# Tabs for different views
if has_betting:
    tab1, tab2, tab3, tab4 = st.tabs(["📊 All Games", "💰 Best Bets", "📈 Detailed Stats", "🧠 Analytics Index"])
else:
    tab1, tab2, tab3 = st.tabs(["📊 All Games", "📈 Detailed Stats", "🧠 Analytics Index"])

with tab1:
    st.subheader("All Games - Spreadsheet View")
    if has_betting:
        # Calculate moneyline recommendation based on win probability
        display_df = filt.copy()
        
        # Add moneyline info
        def get_ml_rec(row):
            home_win_pct = row['Home win %'] / 100
            away_win_pct = 1 - home_win_pct
            
            # Estimate fair moneyline odds
            if home_win_pct > 0.6:
                return f"HOME ML {home_win_pct*100:.0f}%"
            elif away_win_pct > 0.6:
                return f"AWAY ML {away_win_pct*100:.0f}%"
            else:
                return "TOSS-UP"
        
        display_df['Moneyline'] = display_df.apply(get_ml_rec, axis=1)
        
        # Select and order columns
        display_cols = ["away", "home", "Exp score (away-home)", "Best_bet",
                       "Spread used (home-)", "Rec_spread", 
                       "Total used", "Rec_total",
                       "Moneyline",
                       "Home win %", "EV_spread", "EV_total",
                       "Stake_spread", "Stake_total"]
        
        # Format the dataframe
        st.dataframe(
            display_df[display_cols].style.format({
                "Home win %": "{:.1f}%",
                "EV_spread": "{:.1%}",
                "EV_total": "{:.1%}",
                "Spread used (home-)": "{:+.1f}",
                "Total used": "{:.1f}",
                "Stake_spread": "${:,.0f}",
                "Stake_total": "${:,.0f}"
            }),
            use_container_width=True,
            height=600
        )
    else:
        cols = ["away","home","Exp score (away-home)","Model spread home-","Spread used (home-)","Edge_pts",
                "Model total","Total used","Edge_total_pts","Home win %","Home cover %","Over %"]
        st.dataframe(filt[cols].sort_values("Abs Edge (pts)", ascending=False).reset_index(drop=True))

if has_betting:
    with tab2:
        st.subheader("🎯 Recommended Bets (Ranked by EV)")
        
        # Gather all bets
        all_bets = []
        for _, r in df.iterrows():
            if r["Best_bet"] != "NO PLAY":
                all_bets.append({
                    "Game": f"{r['away']} @ {r['home']}",
                    "Score": r["Exp score (away-home)"],
                    "Best_bet": r["Best_bet"],
                    "Rec_spread": r["Rec_spread"],
                    "Rec_total": r["Rec_total"],
                    "EV_Spread": r["EV_spread"],
                    "EV_Total": r["EV_total"],
                    "Stake_Spread": r["Stake_spread"],
                    "Stake_Total": r["Stake_total"],
                    "Max_EV": max(r["EV_spread"], r["EV_total"])
                })
        
        # Sort by max EV
        all_bets.sort(key=lambda x: x["Max_EV"], reverse=True)
        
        if all_bets:
            st.success(f"Found {len(all_bets)} games with betting opportunities")
            
            # Show total recommended stake
            total_stake = sum([b["Stake_Spread"] + b["Stake_Total"] for b in all_bets])
            st.metric("Total Recommended Stake", f"${total_stake:,.0f}")
            
            # Display each game's recommendations
            for i, bet in enumerate(all_bets, 1):
                with st.expander(f"**{i}. {bet['Game']}** - Max EV: {bet['Max_EV']*100:.1f}%", expanded=i<=3):
                    st.caption(f"Predicted Score: {bet['Score']}")
                    
                    col_a, col_b = st.columns(2)
                    
                    with col_a:
                        st.markdown("**📊 SPREAD:**")
                        if bet['Rec_spread'] != 'NO PLAY':
                            st.info(bet['Rec_spread'])
                            st.metric("EV", f"{bet['EV_Spread']*100:.1f}%")
                            st.caption(f"💰 Stake: ${bet['Stake_Spread']:,.0f}")
                        else:
                            st.caption("No spread play")
                    
                    with col_b:
                        st.markdown("**🎯 TOTAL:**")
                        if bet['Rec_total'] != 'NO PLAY':
                            st.info(bet['Rec_total'])
                            st.metric("EV", f"{bet['EV_Total']*100:.1f}%")
                            st.caption(f"💰 Stake: ${bet['Stake_Total']:,.0f}")
                        else:
                            st.caption("No total play")
                    
                    st.divider()
                    st.markdown(f"**🏆 BEST BET:** {bet['Best_bet']}")
        else:
            st.info("No plays meet the minimum EV threshold. Stay disciplined!")

detailed_tab = tab3 if has_betting else tab2
with detailed_tab:
    st.subheader("Detailed Statistics")
cols = ["away","home","Exp score (away-home)","Model spread home-","Spread used (home-)","Edge_pts",
        "Model total","Total used","Edge_total_pts","Home win %","Home cover %","Over %","Abs Edge (pts)"]
    st.dataframe(filt[cols].sort_values("Abs Edge (pts)", ascending=False).reset_index(drop=True),
                use_container_width=True)

# Analytics Intensity Index Tab
aii_tab = tab4 if has_betting else tab3
with aii_tab:
    st.subheader("🧠 Analytics Intensity Index (AII)")
    st.caption("Independent model measuring team analytics adoption and efficiency")
    
    # Load AII data
    aii_csvs = sorted(arts.glob("aii_*.csv"))
    if not aii_csvs:
        st.warning("No AII data found. Run `python3 run_analytics.py` to generate.")
        st.info("The AII model measures:\n- 4th down decision quality\n- Motion/scheme creativity\n- Injury management\n- Analytics adoption tier")
    else:
        aii_latest = aii_csvs[-1]
        st.caption(f"Loaded: {aii_latest.name}")
        aii_df = pd.read_csv(aii_latest)
        
        # Create AII game-by-game spreadsheet - SAME FORMAT AS TAB 1
        st.markdown("### 📊 AII Model - Game by Game View")
        st.caption("Same format as game model, showing analytics-based team ratings")
        
        from nfl_edge.analytics_index import compare_with_game_model
        comparison = compare_with_game_model(aii_df, df)
        
        if not comparison.empty:
            # Build display matching Tab 1 format
            aii_game_view = []
            
            for _, game_row in df.iterrows():
                away = game_row['away']
                home = game_row['home']
                
                # Get AII scores
                away_aii = aii_df[aii_df['team'] == away]['aii_normalized'].values
                home_aii = aii_df[aii_df['team'] == home]['aii_normalized'].values
                away_tier = aii_df[aii_df['team'] == away]['analytics_tier'].values
                home_tier = aii_df[aii_df['team'] == home]['analytics_tier'].values
                
                if len(away_aii) > 0 and len(home_aii) > 0:
                    away_aii = away_aii[0]
                    home_aii = home_aii[0]
                    away_tier = away_tier[0] if len(away_tier) > 0 else 3
                    home_tier = home_tier[0] if len(home_tier) > 0 else 3
                    
                    aii_edge = away_aii - home_aii
                    
                    # Determine AII recommendation
                    if aii_edge > 0.2:
                        aii_rec = f"AII favors {away} (Analytics edge: +{aii_edge*100:.0f}%)"
                    elif aii_edge < -0.2:
                        aii_rec = f"AII favors {home} (Analytics edge: {aii_edge*100:.0f}%)"
                    else:
                        aii_rec = "AII sees toss-up"
                    
                    # Get game model prediction
                    game_bet = game_row.get('Best_bet', 'NO PLAY')
                    
                    # Check agreement
                    if aii_edge > 0.2 and away in game_bet:
                        agreement = "✅ AGREE"
                    elif aii_edge < -0.2 and home in game_bet:
                        agreement = "✅ AGREE"
                    elif abs(aii_edge) <= 0.2:
                        agreement = "➖ NEUTRAL"
                    else:
                        agreement = "⚠️ DISAGREE"
                    
                    aii_game_view.append({
                        'away': away,
                        'home': home,
                        'Away AII': away_aii,
                        'Home AII': home_aii,
                        'Away Tier': away_tier,
                        'Home Tier': home_tier,
                        'AII Edge': aii_edge,
                        'AII Recommendation': aii_rec,
                        'Game Model Bet': game_bet[:60] if len(game_bet) > 60 else game_bet,
                        'Agreement': agreement
                    })
            
            aii_display_df = pd.DataFrame(aii_game_view)
            
            st.dataframe(
                aii_display_df.style.format({
                    'Away AII': '{:.3f}',
                    'Home AII': '{:.3f}',
                    'AII Edge': '{:.3f}',
                }),
                use_container_width=True,
                height=600
            )
        
        # Key insights
        st.markdown("### 💡 Key Insights")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            top_team = aii_df.iloc[0]
            st.metric("Most Analytical", top_team['team'], f"AII: {top_team['aii_normalized']:.3f}")
        
        with col2:
            bottom_team = aii_df.iloc[-1]
            st.metric("Least Analytical", bottom_team['team'], f"AII: {bottom_team['aii_normalized']:.3f}")
        
        with col3:
            avg_aii = aii_df['aii_normalized'].mean()
            st.metric("League Average", f"{avg_aii:.3f}", "AII Score")
        
        # Explanation
        with st.expander("ℹ️ What is AII?"):
            st.markdown("""
            **Analytics Intensity Index (AII)** is a separate model that measures how analytically advanced each team is.
            
            **Components:**
            1. **4th Down Optimality** - How well teams make go-for-it decisions
            2. **Motion/Scheme Creativity** - Pre-snap motion usage and EPA impact
            3. **Injury Management** - Adjusted Games Lost and roster consistency
            4. **Analytics Tier** - Coaching staff and front office analytics adoption (1-5 scale)
            
            **Why it matters:**
            - High AII teams tend to outperform their talent level
            - When AII agrees with game model → higher confidence
            - When AII disagrees → look closer at the matchup
            
            **Research shows:** +1 standard deviation in AII = +0.54 wins per season on average
            """)
            
        st.markdown("---")
        st.caption("⚠️ AII is an independent model. Use it to validate or question game predictions, not replace them.")
