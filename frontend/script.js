let routePolyline = null;
let marker = null;

document.addEventListener('DOMContentLoaded', () => {
  // 스크롤 시간 선택기 채우기
  populatePicker('hour-list', 1, 12);
  populatePicker('minute-list', 0, 59);

  const enterBtn = document.getElementById('enter-btn');
  const timeConfirmBtn = document.getElementById('time-confirm-btn');

  if (enterBtn) {
    enterBtn.addEventListener('click', () => {
      history.pushState({ page: 'time-setting' }, '', '');
      document.getElementById('landing').style.display = 'none';
      document.getElementById('time-setting').style.display = 'flex';
    });
  }

  if (timeConfirmBtn) {
    timeConfirmBtn.addEventListener('click', () => {
      const ampm = getCenteredValue(document.getElementById('ampm-list'));
      const hour = getCenteredValue(document.getElementById('hour-list'));
      const minute = getCenteredValue(document.getElementById('minute-list'));

      if (!ampm || !hour || !minute) {
        alert('도착 시각을 모두 선택해주세요!');
        return;
      }

      let h = parseInt(hour, 10);
      if (ampm === '오후' && h !== 12) h += 12;
      if (ampm === '오전' && h === 12) h = 0;

      const formatted = `${String(h).padStart(2, '0')}:${minute}`;
      document.getElementById('arrival-time').value = formatted;

      history.pushState({ page: 'main-ui' }, '', '');
      document.getElementById('time-setting').style.display = 'none';
      document.getElementById('main-ui').style.display = 'block';

      setTimeout(() => map.invalidateSize(), 100);
      predictArrival(formatted);
    });
  }

  // 뒤로가기 대응
  window.addEventListener('popstate', () => {
    document.getElementById('main-ui').style.display = 'none';
    document.getElementById('time-setting').style.display = 'none';
    document.getElementById('landing').style.display = 'flex';
  });
});

const retryBtn = document.getElementById('retry-btn');
if (retryBtn) {
  retryBtn.addEventListener('click', () => {
    history.pushState({ page: 'time-setting' }, '', '');
    document.getElementById('main-ui').style.display = 'none';
    document.getElementById('time-setting').style.display = 'flex';

    // 지도 초기화
    if (marker) {
      map.removeLayer(marker);
      marker = null;
    }
    if (routePolyline) {
      map.removeLayer(routePolyline);
      routePolyline = null;
    }

    // UI 초기화
    document.getElementById('arrival-time-box').innerText = '--:--';
    document.getElementById('progress-bar').style.width = '0%';
    document.getElementById('progress-percent').innerText = '0%';
    document.getElementById('progress-percent').style.left = 'calc(0% - 12px)';
    document.getElementById('bus-icon').style.left = 'calc(0% - 12px)';
    document.getElementById('eta-text').innerText = '';
  });
}

// leaflet 지도 초기화
const map = L.map('map').setView([37.322, 127.125], 14);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 19
}).addTo(map);

// 시간 선택기 리스트 생성
function populatePicker(id, start, end, pad = true) {
  const list = document.getElementById(id);
  const topSpacer = document.createElement('div');
  topSpacer.style.height = '40px';
  list.appendChild(topSpacer);

  for (let i = start; i <= end; i++) {
    const item = document.createElement('div');
    item.textContent = pad ? String(i).padStart(2, '0') : i;
    list.appendChild(item);
  }

  const bottomSpacer = document.createElement('div');
  bottomSpacer.style.height = '40px';
  list.appendChild(bottomSpacer);
}

// 현재 선택된 시간 요소 추출
function getCenteredValue(list) {
  const children = Array.from(list.children);
  const listTop = list.getBoundingClientRect().top + list.clientHeight / 2;

  return children.reduce((closest, child) => {
    const offset = Math.abs(child.getBoundingClientRect().top + child.clientHeight / 2 - listTop);
    return offset < closest.offset ? { value: child.textContent, offset } : closest;
  }, { value: null, offset: Infinity }).value;
}

// 서버에 도착 시각 보내고 셔틀 위치 예측 요청
function predictArrival(arrivalTime) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 10000);

  fetch('http://127.0.0.1:5001/predict-arrival', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ arrival_time: arrivalTime }),
    signal: controller.signal
  })
    .then(res => {
      clearTimeout(timeoutId);
      if (!res.ok) throw new Error(`서버 오류 ${res.status}`);
      return res.json();
    })
    .then(data => {
      if (data.status !== 'ok') throw new Error(data.message || '예측 실패');
      const latest = data.result;

      // 마커 이동
      const { lat, lng } = latest.current_location;
      if (marker) marker.setLatLng([lat, lng]);
      else marker = L.marker([lat, lng]).addTo(map);
      map.setView([lat, lng], 15);

      // 도착 시각 및 진행률 반영
      document.getElementById('arrival-time-box').innerText = latest.predicted_arrival;
      document.getElementById('progress-bar').style.width = `${latest.progress}%`;

      const p = latest.progress.toFixed(1);
      document.getElementById('progress-percent').innerText = `${p}%`;
      document.getElementById('progress-percent').style.left = `calc(${p}% - 12px)`;
      document.getElementById('bus-icon').style.left = `calc(${p}% - 12px)`;
      document.getElementById('eta-text').innerHTML = `약 <span class="eta-number">${latest.eta_minutes}</span>분 남았습니다.`;

      // 기존 경로 제거 후 새로 그리기
      if (routePolyline) {
        map.removeLayer(routePolyline);
      }
      if (Array.isArray(latest.route) && latest.route.length) {
        const latlngs = latest.route.map(p => [p.lat, p.lng]);
        routePolyline = L.polyline(latlngs, {
          color: '#FF4500',
          weight: 4,
          opacity: 0.8,
          lineJoin: 'round'
        }).addTo(map);
        map.fitBounds(routePolyline.getBounds(), { padding: [50, 50] });
      }
    })
    .catch(err => {
      if (err.name === 'AbortError') {
        alert('요청 시간이 초과되었습니다. 다시 시도해주세요.');
      } else {
        console.error(err);
        alert(err.message || '알 수 없는 오류 발생');
      }
    });
}