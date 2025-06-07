function getCenteredValue(list) {
  const children = Array.from(list.children);
  const listTop = list.getBoundingClientRect().top + list.clientHeight / 2;
  return children.reduce((closest, child) => {
    const offset = Math.abs(child.getBoundingClientRect().top + child.clientHeight / 2 - listTop);
    return offset < closest.offset ? { value: child.textContent, offset } : closest;
  }, { value: null, offset: Infinity }).value;
}

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

populatePicker('hour-list', 1, 12);
populatePicker('minute-list', 0, 59);

document.addEventListener('DOMContentLoaded', () => {
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

  window.addEventListener('popstate', () => {
    document.getElementById('main-ui').style.display = 'none';
    document.getElementById('time-setting').style.display = 'none';
    document.getElementById('landing').style.display = 'flex';
  });
});

const map = L.map('map').setView([37.322, 127.125], 14);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
  maxZoom: 19
}).addTo(map);

let marker = null;

function predictArrival(arrivalTime) {
  fetch('http://127.0.0.1:5001/predict-arrival', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ arrival_time: arrivalTime })
  })
    .then(res => res.json())
    .then(data => {
      if (data.status !== 'ok') {
        alert(data.message || '예측 실패');
        return;
      }

      const latest = data.result;
      if (latest.status !== 'ok') {
        alert(latest.message || '예측 실패');
        return;
      }

      const { lat, lng } = latest.current_location;
      if (marker) {
        marker.setLatLng([lat, lng]);
      } else {
        marker = L.marker([lat, lng]).addTo(map);
      }
      map.setView([lat, lng], 15);

      // 예측 시각 업데이트
      document.getElementById('arrival-time-box').innerText = latest.predicted_arrival;

      // 진행률 바 너비 설정
      document.getElementById('progress-bar').style.width = `${latest.progress}%`;

      // 🔧 추가: 진행 퍼센트 텍스트 & 아이콘 위치 조절
      const percent = latest.progress;
      const percentText = document.getElementById('progress-percent');
      percentText.innerText = `${percent.toFixed(1)}%`;
      percentText.style.left = `calc(${percent}% - 12px)`; // 텍스트 중앙 정렬 보정

      const busIcon = document.getElementById('bus-icon');
      busIcon.style.left = `calc(${percent}% - 12px)`; // 아이콘 위치 보정

      // ETA 텍스트 업데이트
      document.getElementById('eta-text').innerHTML =
        `약 <span class="eta-number">${latest.eta_minutes}</span>분 남았습니다.`;
    })
    .catch(err => {
      console.error(err);
      alert('서버 요청 실패');
    });
}