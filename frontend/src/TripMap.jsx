import {
  MapContainer,
  TileLayer,
  Marker,
  Polyline,
  Popup,
} from "react-leaflet";

import "leaflet/dist/leaflet.css";

import L from "leaflet";
//import { MapPin, Navigation } from "lucide-react";
import "./App.css";

delete L.Icon.Default.prototype._getIconUrl;

L.Icon.Default.mergeOptions({
  iconUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl:
    "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

function TripMap({
  pickupCoords,
  dropoffCoords,
  distanceKm,
  durationMin,
  geometry,
}) {

  const center = [
    (pickupCoords[0] + dropoffCoords[0]) / 2,
    (pickupCoords[1] + dropoffCoords[1]) / 2,
  ];

  return (

    <div className="trip-card">

      <MapContainer
        center={center}
        zoom={11}
        scrollWheelZoom={false}
        className="trip-map"
      >

        <TileLayer
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution="© OpenStreetMap"
        />

        <Marker position={pickupCoords}>
          <Popup>Pickup</Popup>
        </Marker>

        <Marker position={dropoffCoords}>
          <Popup>Destination</Popup>
        </Marker>

        <Polyline
          positions={geometry || [pickupCoords, dropoffCoords]}
          color="#007AFF"
          weight={6}
        />

      </MapContainer>

      <div className="trip-footer">

        <div className="trip-item">

          <div>

            <span>Distance</span>

            <strong>{distanceKm} km</strong>

          </div>

        </div>

        <div className="trip-item">

          <div>

            <span>Estimated</span>

            <strong>{durationMin} min</strong>

          </div>

        </div>

      </div>

    </div>

  );

}

export default TripMap;