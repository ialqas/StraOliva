"use client";

import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

interface Props {
  lat: (number | null)[];
  lng: (number | null)[];
  height?: number;
}

export function ActivityMapInner({ lat, lng, height = 340 }: Props) {
  const container = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!container.current) return;

    // Build valid coordinate pairs [lng, lat] — GeoJSON order
    const coords: [number, number][] = [];
    for (let i = 0; i < lat.length; i++) {
      if (lat[i] != null && lng[i] != null) {
        coords.push([lng[i]!, lat[i]!]);
      }
    }
    if (coords.length < 2) return;

    // Compute bounding box
    let minLng = coords[0][0], maxLng = coords[0][0];
    let minLat = coords[0][1], maxLat = coords[0][1];
    for (const [lo, la] of coords) {
      if (lo < minLng) minLng = lo;
      if (lo > maxLng) maxLng = lo;
      if (la < minLat) minLat = la;
      if (la > maxLat) maxLat = la;
    }

    const map = new maplibregl.Map({
      container: container.current,
      style: "https://tiles.openfreemap.org/styles/bright",
      bounds: [[minLng, minLat], [maxLng, maxLat]],
      fitBoundsOptions: { padding: 48, maxZoom: 16 },
      attributionControl: false,
    });

    map.addControl(new maplibregl.AttributionControl({ compact: true }), "bottom-right");

    map.on("load", () => {
      map.addSource("route", {
        type: "geojson",
        data: { type: "Feature", properties: {}, geometry: { type: "LineString", coordinates: coords } },
      });

      // Glow / shadow
      map.addLayer({
        id: "route-glow",
        type: "line",
        source: "route",
        paint: { "line-color": "#FC4C02", "line-width": 8, "line-opacity": 0.15, "line-blur": 4 },
        layout: { "line-join": "round", "line-cap": "round" },
      });

      // Main line
      map.addLayer({
        id: "route-line",
        type: "line",
        source: "route",
        paint: { "line-color": "#FC4C02", "line-width": 3, "line-opacity": 0.95 },
        layout: { "line-join": "round", "line-cap": "round" },
      });

      // Start marker (green dot)
      new maplibregl.Marker({ color: "#16A34A", scale: 0.7 })
        .setLngLat(coords[0])
        .addTo(map);

      // End marker (red dot) — only if start ≠ end
      const last = coords[coords.length - 1];
      const dist = Math.hypot(last[0] - coords[0][0], last[1] - coords[0][1]);
      if (dist > 0.0005) {
        new maplibregl.Marker({ color: "#DC2626", scale: 0.7 })
          .setLngLat(last)
          .addTo(map);
      }
    });

    return () => map.remove();
  }, [lat, lng]);

  return (
    <div
      ref={container}
      style={{ width: "100%", height, borderRadius: "0.5rem", overflow: "hidden" }}
    />
  );
}
