"""Streamlit command dashboard for ClearGlassInc Artemis Phase 1.

Run locally with:
    streamlit run artemis/environmental/dashboard.py
"""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from artemis.environmental.risk import EnvironmentalObservation, dashboard_snapshot


def main() -> None:
    """Render the Environmental Cyber-Risk command interface."""

    st.set_page_config(
        page_title="ClearGlass Artemis Ionospheric Threat Command",
        layout="wide",
        page_icon="🛰️",
    )
    now = datetime.now(timezone.utc)
    st.title("🛰️ IONOSPHERIC THREAT COMMAND v1.0")
    st.caption(f"ClearGlassInc Artemis | Burlington, Ontario | SECURE | {now:%Y-%m-%d %H:%M UTC}")

    log_nf2 = st.sidebar.slider("Simulated log N_F2", min_value=3.0, max_value=7.0, value=5.62, step=0.01)
    observation = EnvironmentalObservation(log_nf2=log_nf2, observed_at=now)
    snapshot = dashboard_snapshot(observation)
    band = snapshot["band"]

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("log N_F2 (Current)", f"{log_nf2:.2f}", delta="↑ 0.08 from last hour")
        fig = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=log_nf2,
                gauge={
                    "axis": {"range": [3, 7]},
                    "bar": {"color": "red" if band == "RED" else "orange" if band == "YELLOW" else "green"},
                    "steps": [
                        {"range": [3, 5.4], "color": "rgba(0, 180, 0, 0.18)"},
                        {"range": [5.4, 5.8], "color": "rgba(255, 165, 0, 0.22)"},
                        {"range": [5.8, 7], "color": "rgba(255, 0, 0, 0.18)"},
                    ],
                },
                title={"text": "Ionospheric Density"},
            )
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Alert Status")
        if band == "RED":
            st.error(snapshot["status"])
        elif band == "YELLOW":
            st.warning(snapshot["status"])
        else:
            st.success(snapshot["status"])

        st.subheader("Threat Vector Table")
        st.dataframe(pd.DataFrame([row.__dict__ for row in snapshot["threat_vectors"]]), use_container_width=True)

    with col3:
        st.subheader("Live Feeds (CSA / NOAA)")
        st.write(f"Solar Wind: {observation.solar_wind_kms:.0f} km/s | Kp Index: {observation.kp_index:.1f}")
        st.write("Last CSA Alert: No active warnings")
        st.caption("Public data feed — replace simulation with authenticated ingestion for production.")

    st.divider()
    st.caption(
        "Minimal viable command interface for GitHub Actions CI/CD, real API integration, "
        "client white-labeling, and human-approved AIP workflow upgrades."
    )
    if st.button("Refresh Threat Vector"):
        st.rerun()


if __name__ == "__main__":
    main()
