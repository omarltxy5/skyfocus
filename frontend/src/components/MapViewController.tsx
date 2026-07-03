import { useEffect } from "react";
import { useMap } from "react-leaflet";

interface Props {
  center: [number, number] | null;
  zoom: number;
}

/** Fly the map to the user's nearest-airport view once geo is resolved. */
export default function MapViewController({ center, zoom }: Props) {
  const map = useMap();

  useEffect(() => {
    if (!center) return;
    map.flyTo(center, zoom, { duration: 1.4 });
  }, [map, center, zoom]);

  return null;
}
