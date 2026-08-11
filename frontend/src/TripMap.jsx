// SmartLimo AI - TripMap.jsx - carte du trajet style "Apple Plans"
//
// Affiche une mini-carte Leaflet montrant le point de départ, la
// destination et le tracé du trajet, avec le style visuel épuré inspiré
// d'Apple Plans (tuiles pastel, pastilles colorées, ligne dorée épaisse).
// Reçoit toutes ses données en props depuis Chatbot.jsx (issues de
// l'appel à l'API GET /route/, voir geo_service.py côté backend).
import { MapContainer, TileLayer, Marker, Polyline, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";   // VITAL : sans ce CSS, les tuiles sont invisibles !
import L from "leaflet";
import { MapPin, Clock } from "lucide-react";

// Pastilles colorees facon Apple (vert = depart, rouge = arrivee)
// Construit une icône Leaflet personnalisée : un simple rond coloré avec
// une bordure blanche et une ombre, plutôt que le marqueur "épingle" par
// défaut de Leaflet (visuellement plus cohérent avec le reste de l'app).
const dotIcon = (color) =>
  L.divIcon({
    className: "",
    html: `<div style="width:16px;height:16px;background:${color};border:3px solid white;border-radius:50%;box-shadow:0 2px 6px rgba(0,0,0,0.35)"></div>`,
    iconSize: [16, 16],
    iconAnchor: [8, 8],   // centre l'icône exactement sur les coordonnées (8,8 = moitié de 16x16)
  });

// pickupCoords / dropoffCoords : tableaux [latitude, longitude].
// distanceKm / durationMin : valeurs déjà calculées côté backend (OSRM),
// affichées telles quelles sous la carte.
// geometry : liste de points [lat, lon] formant le tracé détaillé de
// l'itinéraire routier (peut être absente/vide si l'API n'a pas pu la
// fournir, d'où le repli sur une ligne droite pickup->dropoff plus bas).
function TripMap({ pickupCoords, dropoffCoords, distanceKm, durationMin, geometry }) {
  return (
    <div className="trip-map">
      <MapContainer
        // bounds calcule automatiquement le zoom/centrage pour que les
        // deux points (départ et arrivée) soient visibles ensemble.
        bounds={[pickupCoords, dropoffCoords]}
        boundsOptions={{ padding: [30, 30] }}
        style={{ height: "220px", width: "100%" }}
        scrollWheelZoom={false}   // évite que le défilement de la page ne zoome accidentellement la carte
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
        {/* Si geometry contient au moins 2 points, on trace l'itinéraire
            réel renvoyé par OSRM ; sinon (donnée absente), on trace une
            simple ligne droite entre les deux points comme repli visuel. */}
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
        <span className="trip-info-item">
          <MapPin size={14} /> {distanceKm} km
        </span>
        <span className="trip-sep">•</span>
        <span className="trip-info-item">
          <Clock size={14} /> ~{durationMin} min
        </span>
      </div>
    </div>
  );
}

export default TripMap;
