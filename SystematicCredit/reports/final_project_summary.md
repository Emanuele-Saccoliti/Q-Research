# Final Project Summary

This project implements a Bond-CDS basis trading and credit curve calibration toolkit in Python, with an Excel/VBA dashboard for trading-desk-style monitoring.

The Python engine calibrates CDS-implied curves from market CDS spreads, bootstraps piecewise-constant hazard rates, computes survival probabilities, estimates maturity-matched CDS spreads for corporate bonds, calculates bond-CDS basis, generates z-score relative-value signals, sizes positions by CS01, applies macro hedging in risk-off regimes, and evaluates performance through transaction-cost-aware backtesting.

The Excel dashboard is generated from the pipeline output tables and includes curve calibration, hazard/survival, basis, signals, positions, macro regimes, hedge overlay, P&L attribution, performance, stress testing, and configuration sheets.

Limitations are explicit: the default data is synthetic and intended for interview demonstration rather than production trading.
