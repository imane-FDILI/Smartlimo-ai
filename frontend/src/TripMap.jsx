// TripMap.jsx - une mini-carte affichant le trajet pickup -> dropoff
import { MapContainer, TileLayer, Marker, Polyline, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";          // le style officiel de Leaflet (obligatoire !)
import L from "leaflet";

// Correctif connu : les icones par defaut de Leaflet ne chargent pas avec Vite
// -> on pointe manuellement vers les images hebergees sur un CDN
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

function TripMap({ pickupCoords, dropoffCoords, distanceKm, durationMin }) {
  // pickupCoords / dropoffCoords : [lat, lon] fournis par TON endpoint /route

  // le centre de la carte = le milieu des deux points
  const center = [
    (pickupCoords[0] + dropoffCoords[0]) / 2,
    (pickupCoords[1] + dropoffCoords[1]) / 2,
  ];

  return (
    <div className="trip-map">
      <MapContainer center={center} zoom={10} style={{ height: "200px", width: "100%", borderRadius: "12px" }}>
        {/* les tuiles OpenStreetMap (la carte de fond) */}
        <TileLayer
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; OpenStreetMap contributors'
        />
        {/* les deux epingles */}
        <Marker position={pickupCoords}><Popup>Pickup</Popup></Marker>
        <Marker position={dropoffCoords}><Popup>Destination</Popup></Marker>
        {/* la ligne droite entre les deux (le trace symbolique du trajet) */}
        <Polyline positions={[pickupCoords, dropoffCoords]} color="#c9a227" weight={3} />
      </MapContainer>
      <div className="trip-info">
        Distance: {distanceKm} km &nbsp;|&nbsp; Duration: ~{durationMin} min
      </div>
    </div>
  );
}

export default TripMap;