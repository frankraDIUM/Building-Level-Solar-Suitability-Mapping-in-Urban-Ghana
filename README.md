# 🌞 Building-Level Solar Suitability Mapping in Urban Ghana
**Accra Solar Rooftop Suitability & Investment Dashboard**

A geospatial AI pipeline and interactive decision-support tool for urban solar potential in Central Accra, Ghana.


---

Dashboard Preview

<p align="center">
  <img src="https://github.com/frankraDIUM/Building-Level-Solar-Suitability-Mapping-in-Urban-Ghana/blob/main/Solar.gif" />
</p>
---

Solar Potential Density
<p align="center">
  <img src="https://github.com/frankraDIUM/Building-Level-Solar-Suitability-Mapping-in-Urban-Ghana/blob/main/Solar1.gif" />
</p>
---

Spatial Clusters
<p align="center">
  <img src="https://github.com/frankraDIUM/Building-Level-Solar-Suitability-Mapping-in-Urban-Ghana/blob/main/Solar2.gif" />
</p>
---

Top Investment Opportunities
<p align="center">
  <img src="https://github.com/frankraDIUM/Building-Level-Solar-Suitability-Mapping-in-Urban-Ghana/blob/main/Solar3.gif" />
</p>

---

Summary

  This project developed a scalable, end-to-end geospatial AI pipeline to assess rooftop solar potential across Accra, Ghana. 
  
  The system integrates high-resolution building footprints, terrain-derived slope and aspect, NASA POWER solar irradiance data, 
  realistic economic modeling (including dynamic NPV and payback), shadow attenuation via building height proxies, 
  
  H3 hexagonal aggregation for scalability, and Getis-Ord Gi* hotspot analysis. 
  
  The result is an interactive Streamlit dashboard that supports multi-scale decision-making, from individual building investment to neighborhood-level policy planning.


Key outcomes:

  - Analyzed 632,195 buildings in the Greater Accra area.
  - Generated realistic solar potential estimates (mean ~12,408 kWh/year per building after shadow adjustment).
  - Produced dynamic ROI metrics with user-adjustable parameters (tariff, discount rate, self-consumption, cost per kW).
  - Identified spatial clusters of high solar investment potential using hotspot analysis.
  - Delivered a production-ready interactive dashboard with four distinct map views.


*1. Objectives*

Detect and characterize individual building rooftops using open building footprint datasets.
  - Assess technical solar suitability using slope, aspect, usable roof area, and shadow effects.
  - Estimate annual energy generation with performance losses and shadow attenuation.
  - Perform detailed economic analysis (payback period, NPV) with real-time sensitivity.
  - Aggregate results at hexagonal grid level for policy insights and performance.
  - Identify spatial investment hotspots and priority zones.
  - Provide an intuitive, interactive dashboard for stakeholders (households, SMEs, policymakers, investors).

*2. Methodology & Pipeline*

Phase 1–2: Data Acquisition & Building Footprints

  Combined Microsoft Global Building Footprints and Google Open Buildings datasets, 
  filtered to Accra bounding box, resulting in 632,195 valid building polygons.

Phase 3–4: Terrain & Solar Resource

  Copernicus DEM (30m) → derived slope and aspect at building centroids.
  NASA POWER API (2020–2025) → annual GHI of ~1,779 kWh/m²/year used as baseline.

Phase 5: Rooftop Geometry & Suitability Modeling

  - Accurate footprint area calculated in UTM Zone 30N.
  - Roof utilization factor based on slope (0.92 for ≤15°, decaying for steeper roofs).
  - Usable area = footprint × 0.82 (edge/obstacle buffer) × utilization factor.
  - Weighted suitability score (slope 45%, aspect 30%, area 25%) with nonlinear scaling.

Phase 6: Shadow Modeling & Energy Adjustment

  - Empirical height proxy: height_m = clip(sqrt(area) × 0.65, 3, 45).
  - Multi-angle shadow length (weighted 30°/45°/60° sun elevations).
  - Shadow factor = exp(-weighted_shadow / 120).
  - Adjusted solar generation: usable_area × GHI × efficiency (20.5%) × PR (0.76) × shadow_factor.

Phase 7: Economic & Financial Modeling

  - System size derived from usable area.
  - Realistic cost structure (fixed + variable per kW with bulk discount).
  - Dynamic NPV and payback with user-controlled tariff, discount rate, self-consumption, and 0.5% annual degradation.
Priority Score = 0.4×Solar Index + 0.4×Normalized NPV + 0.2×Normalized Hotspot Score (+ risk penalty for long payback).

Phase 8: Spatial Aggregation & Hotspot Analysis

  - H3 hexagonal grid (resolution 9) for aggregation (~3,135 hexes).
  - Metrics per hex: total solar, avg NPV, avg solar index, building count.
  - Getis-Ord Gi* hotspot detection on normalized solar-per-building to identify statistically significant clusters.

Phase 9: Interactive Dashboard

Built with Streamlit + Folium, featuring:

  - Four synchronized map views: All Buildings (point markers), Solar Potential Density (H3 hex choropleth), Spatial Clusters (Gi* hotspots), Top Investment Opportunities (top 10% priority buildings).
  - Real-time ROI simulator with sliders.
  - Dynamic metrics, priority scoring, and GIS export (GeoJSON).
  - Loading spinners and performance optimizations (caching, downcasting, sampling).

*3. Key Results*

  - Total potential generation: ~6,000+ GWh/year (shadow-adjusted) across Accra.
  - Economic viability: Average simple payback ~7 years; many buildings show strong positive NPV.
  - High-potential buildings: ~81.5% have positive NPV under baseline assumptions.
  - Spatial insights: 44 hexagons identified as statistically significant hotspots (90%+ confidence).
  - Investment prioritization: Priority Score combines technical suitability, financial return, and spatial clustering for ranked decision support.

*4. Technical Implementation Highlights*

  - Scalability: Handles 632k+ buildings efficiently through vectorization, H3 aggregation, and caching.
  - Realism: Incorporates terrain constraints, shadow effects, degradation, O&M costs, and user-driven sensitivity analysis.
  - Multi-scale: Building-level detail + hexagonal policy view + hotspot detection.
  - User-centric: Interactive sliders, multiple synchronized views, export functionality, and clear legends.
  - Open & Reproducible: Relies on open datasets (Microsoft/Google buildings, Copernicus DEM, NASA POWER) and open-source tools (GeoPandas, Folium, H3, esda).

*5. Limitations & Future Work*

  - Shadow model uses simplified height proxy and exponential decay (no full neighbor ray-tracing).
  - Slope/aspect derived from terrain DEM (not true roof pitch).
  - Assumes full self-consumption or fixed export rates.
  - Future enhancements could include: true DSM-based shading, net-metering scenarios, inflation-adjusted tariffs, and machine learning for suitability prediction.

*6. Conclusion*

  This project demonstrates a practical, scalable approach to urban solar potential assessment tailored to Ghanaian conditions (unreliable grid, high electricity costs, rapid urbanization). 
  The resulting dashboard serves as a powerful decision-support tool for households, businesses, utilities, and policymakers. 
  It bridges technical geospatial analysis with economic realism and spatial intelligence, providing actionable insights for accelerating solar adoption in Accra and similar African cities.
