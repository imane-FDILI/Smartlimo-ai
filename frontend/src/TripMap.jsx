// TripMap.jsx - carte du trajet style "Apple Plans"
import { MapContainer, TileLayer, Marker, Polyline, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";   // VITAL : sans ce CSS, les tuiles sont invisibles !
import L from "leaflet";

// Pastilles colorees facon Apple (vert = depart, rouge = arrivee)
const dotIcon = (color) =>
  L.divIcon({
    className: "",
    html: `<div style="width:16px;height:16px;background:${color};border:3px solid white;border-radius:50%;box-shadow:0 2px 6px rgba(0,0,0,0.35)"></div>`,
    iconSize: [16, 16],
    iconAnchor: [8, 8],
  });

function TripMap({ pickupCoords, dropoffCoords, distanceKm, durationMin, geometry }) {
  return (
    <div className="trip-map">
      <MapContainer
        bounds={[pickupCoords, dropoffCoords]}
        boundsOptions={{ padding: [30, 30] }}
        style={{ height: "220px", width: "100%" }}
        scrollWheelZoom={false}
      >
        {/* Tuiles CartoDB Voyager : le style pastel epure proche d'Apple Plans */}
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
          attribution='&copy; OpenStreetMap &copy; CARTO'
        />

        <Marker position={pickupCoords} icon={dotIcon("#34C759")}>
          <Popup>Pickup</Popup>
        </Marker>
        <Marker position={dropoffCoords} icon={dotIcon("#FF3B30")}>
          <Popup>Destination</Popup>
        </Marker>

        {/* Le trajet : dore SmartLimo, epais, bouts arrondis */}
        <Polyline
          positions={geometry && geometry.length > 1 ? geometry : [pickupCoords, dropoffCoords]}
          color="#c9a227"
          weight={5}
          opacity={0.9}
          lineCap="round"
          lineJoin="round"
        />
      </MapContainer>

      <div className="trip-info">
        <span>📍 {distanceKm} km</span>
        <span className="trip-sep">•</span>
        <span>🕐 ~{durationMin} min</span>
      </div>
    </div>
  );
}

export default TripMap;