# Product brief

## Problem

Singapore publishes useful mobility and environmental datasets, but operators
and analysts still need to combine inconsistent sources, detect stale data,
and turn records into decisions. A colourful chart without provenance or data
quality cannot be trusted during an operational event.

## Primary user

An operations analyst preparing a morning briefing on mobility conditions and
areas likely to experience disruption.

## Product promise

FluxSG answers three questions:

1. What is happening now?
2. Can the underlying data be trusted?
3. What is likely to happen next, and how uncertain is that estimate?

## Initial success measures

- Source freshness is visible for 100% of dashboard metrics.
- Invalid source payloads fail loudly instead of silently entering storage.
- A new developer can run the complete system from documented commands.
- Forecasts are evaluated against a naive baseline before release.
- API latency and pipeline reliability are measured and published.

## Non-goals

- Replacing official transport information or journey-planning applications.
- Making safety-critical decisions.
- Hiding model uncertainty behind a single score.

