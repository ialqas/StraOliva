"use client";

import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { SegmentWind } from "@/lib/api";
import { useLang } from "@/lib/i18n";

interface Props {
  segments: SegmentWind[];
  center?: [number, number];  // [lng, lat]; default: middle of the segments
}

export function WindMapInner({ segments, center }: Props) {
  const container = useRef<HTMLDivElement>(null);
  const { t } = useLang();
  const finishLabel = t("Ziel", "Finish");

  useEffect(() => {
    if (!container.current || segments.length === 0) return;

    const [centerLng, centerLat]: [number, number] = center ?? [
      segments.reduce((s, g) => s + (g.start_lng + g.end_lng) / 2, 0) / segments.length,
      segments.reduce((s, g) => s + (g.start_lat + g.end_lat) / 2, 0) / segments.length,
    ];

    const map = new maplibregl.Map({
      container: container.current,
      style: "https://tiles.openfreemap.org/styles/positron",
      center: [centerLng, centerLat],
      zoom: 12,
      attributionControl: false,
    });

    map.addControl(new maplibregl.AttributionControl({ compact: true }), "bottom-right");
    map.addControl(new maplibregl.NavigationControl({ showCompass: true }), "top-right");

    const markers: maplibregl.Marker[] = [];

    map.on("load", () => {
      // ── Segment lines (full polyline or fallback straight line) ──────────
      const geojson: GeoJSON.FeatureCollection = {
        type: "FeatureCollection",
        features: segments.map((seg) => ({
          type: "Feature",
          properties: { color: seg.color, name: seg.name, label: seg.label },
          geometry: {
            type: "LineString",
            coordinates:
              seg.coords.length >= 2
                ? seg.coords
                : [[seg.start_lng, seg.start_lat], [seg.end_lng, seg.end_lat]],
          },
        })),
      };

      map.addSource("segments", { type: "geojson", data: geojson });

      map.addLayer({
        id: "segments-glow",
        type: "line",
        source: "segments",
        paint: {
          "line-color": ["get", "color"],
          "line-width": 14,
          "line-opacity": 0.1,
          "line-blur": 6,
        },
        layout: { "line-join": "round", "line-cap": "round" },
      });

      map.addLayer({
        id: "segments-line",
        type: "line",
        source: "segments",
        paint: {
          "line-color": ["get", "color"],
          "line-width": 3.5,
          "line-opacity": 0.92,
        },
        layout: { "line-join": "round", "line-cap": "round" },
      });

      // ── Start / End markers ──────────────────────────────────────────────
      segments.forEach((seg) => {
        const startEl = document.createElement("div");
        startEl.style.cssText = `
          width:20px;height:20px;border-radius:50%;
          background:${seg.color};border:2px solid white;
          display:flex;align-items:center;justify-content:center;
          font-size:9px;font-weight:700;color:white;
          box-shadow:0 1px 4px rgba(0,0,0,0.3);cursor:pointer;
        `;
        startEl.textContent = "S";
        markers.push(
          new maplibregl.Marker({ element: startEl })
            .setLngLat([seg.start_lng, seg.start_lat])
            .setPopup(
              new maplibregl.Popup({ offset: 14, closeButton: false }).setHTML(
                `<div style="font-size:12px;line-height:1.6">
                  <strong>${seg.name}</strong><br/>
                  ${seg.label}<br/>
                  ${seg.distance_m ? (seg.distance_m / 1000).toFixed(2) + " km" : ""}
                  ${seg.avg_grade != null ? ` · ${seg.avg_grade > 0 ? "+" : ""}${seg.avg_grade.toFixed(1)}%` : ""}
                </div>`
              )
            )
            .addTo(map)
        );

        const endEl = document.createElement("div");
        endEl.style.cssText = `
          width:20px;height:20px;display:flex;
          align-items:center;justify-content:center;
          filter:drop-shadow(0 1px 2px rgba(0,0,0,0.3));cursor:default;
        `;
        endEl.title = `${seg.name} — ${finishLabel} (${Math.round(seg.bearing_deg)}°)`;
        endEl.innerHTML = `
          <svg viewBox="0 0 24 24" width="20" height="20"
               style="transform:rotate(${seg.bearing_deg}deg)" fill="${seg.color}">
            <polygon points="12,2 19,20 12,16 5,20"/>
          </svg>`;
        markers.push(
          new maplibregl.Marker({ element: endEl })
            .setLngLat([seg.end_lng, seg.end_lat])
            .addTo(map)
        );
      });
    });

    return () => {
      markers.forEach((m) => m.remove());
      map.remove();
    };
  }, [segments, center?.[0], center?.[1], finishLabel]);

  return (
    <div
      ref={container}
      style={{ width: "100%", height: "100%", borderRadius: "0.75rem", overflow: "hidden" }}
    />
  );
}
