"use client";

import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

interface Props {
  tracks: [number, number][][]; // [[lng, lat], ...]
  center: [number, number];
}

export function HeatmapMapInner({ tracks, center }: Props) {
  const container = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!container.current || tracks.length === 0) return;

    const map = new maplibregl.Map({
      container: container.current,
      // Positron: very clean, minimal labels — lets orange tracks stand out
      style: "https://tiles.openfreemap.org/styles/positron",
      center: [center[0], center[1]],
      zoom: 11,
      attributionControl: false,
    });

    map.addControl(new maplibregl.AttributionControl({ compact: true }), "bottom-right");
    map.addControl(new maplibregl.NavigationControl({ showCompass: false,  }), "top-right");

    map.on("load", () => {
      const geojson: GeoJSON.FeatureCollection = {
        type: "FeatureCollection",
        features: tracks.map((coords) => ({
          type: "Feature",
          properties: {},
          geometry: { type: "LineString", coordinates: coords },
        })),
      };

      map.addSource("tracks", { type: "geojson", data: geojson });

      // Wide glow layer for density effect
      map.addLayer({
        id: "tracks-glow",
        type: "line",
        source: "tracks",
        paint: {
          "line-color": "#FC4C02",
          "line-width": 4,
          "line-opacity": 0.05,
          "line-blur": 3,
        },
        layout: { "line-join": "round", "line-cap": "round" },
      });

      // Thin sharp lines — overlap creates the heatmap density effect
      map.addLayer({
        id: "tracks-line",
        type: "line",
        source: "tracks",
        paint: {
          "line-color": "#FC4C02",
          "line-width": 1.5,
          "line-opacity": 0.35,
        },
        layout: { "line-join": "round", "line-cap": "round" },
      });
    });

    return () => map.remove();
  }, [tracks, center]);

  return (
    <div
      ref={container}
      style={{ width: "100%", height: "100%", borderRadius: "0.75rem", overflow: "hidden" }}
    />
  );
}
