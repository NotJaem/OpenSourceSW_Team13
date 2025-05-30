// 지도 초기화
const map = L.map('map').setView([37.322, 127.125], 14); //학교
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 19
}).addTo(map);

let marker = null;

document.getElementById('predict-btn').addEventListener('click', () => {
  const arrivalTime = document.getElementById('arrival-time').value;
  if (!arrivalTime) {
    alert('도착 시각을 입력하세요!');
    return;
  }

  fetch('http://127.0.0.1:5001/predict-arrival', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ arrival_time: arrivalTime })
  })
  .then(res => res.json())
  .then(data => {
    console.log(data);
    if (data.status !== 'ok') {
      alert(data.message || '예측 실패');
      return;
    }

    // 최신 결과
    const latest = data.result;
    if (latest.status !== 'ok') {
      alert(latest.message || '예측 실패');
      return;
    }

    // 지도에 마커
    const { lat, lng } = latest.current_location;
    if (marker) {
      marker.setLatLng([lat, lng]);
    } else {
      marker = L.marker([lat, lng]).addTo(map);
    }
    map.setView([lat, lng], 15);

    // 예상 도착 시각
    document.getElementById('arrival').innerText = latest.predicted_arrival;

    // 진행률
    document.getElementById('progress-bar').style.width = `${latest.progress}%`;

    // 남은 시간
    document.getElementById('eta-text').innerText = `약 ${latest.eta_minutes}분 남았습니다.`;
  })
  .catch(err => {
    console.error(err);
    alert('서버 요청 실패');
  });
});