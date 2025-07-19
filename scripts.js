let map;
let userMarker;

function initMap(lat = 28.6139, lng = 77.2090) {
    const center = { lat, lng };
    map = new google.maps.Map(document.getElementById("map"), {
        zoom: 13,
        center: center,
    });

    userMarker = new google.maps.Marker({
        position: center,
        map: map,
        title: "You are here",
    });
}

function searchByText() {
    const query = document.getElementById("locationInput").value;
    if (!query) return alert("Please enter a location.");

    fetch(`/search?q=${encodeURIComponent(query)}`)
        .then(res => res.json())
        .then(data => {
            renderMechanicCards(data);
        });
}

function searchByLocation() {
    if (!navigator.geolocation) {
        alert("Geolocation not supported.");
        return;
    }

    navigator.geolocation.getCurrentPosition(position => {
        const lat = position.coords.latitude;
        const lng = position.coords.longitude;

        initMap(lat, lng);

        fetch(`/api/mechanics?lat=${lat}&lng=${lng}`)
            .then(res => res.json())
            .then(data => {
                renderMechanicCards(data);
            });
    }, () => {
        alert("Unable to retrieve your location.");
    });
}

function renderMechanicCards(mechanics) {
    const container = document.getElementById("mechanicResults");
    container.innerHTML = "";

    if (!mechanics.length) {
        container.innerHTML = "<p class='text-center text-muted'>No mechanics found.</p>";
        return;
    }

    mechanics.forEach(mechanic => {
        const card = `
        <div class="col-md-4 mb-4">
            <div class="card shadow-sm">
                <div class="card-body">
                    <h5 class="card-title">${mechanic.name}</h5>
                    <p class="card-text">
                        <strong>Location:</strong> ${mechanic.location}<br>
                        <strong>Phone:</strong> ${mechanic.phone || 'N/A'}
                    </p>
                </div>
            </div>
        </div>`;
        container.innerHTML += card;
    });
}

// Initialize default map view
window.onload = function () {
    initMap();  // Defaults to Delhi if user location is not used
};
