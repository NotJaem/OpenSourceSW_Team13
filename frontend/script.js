// 진입 버튼으로 UI 전환
document.addEventListener('DOMContentLoaded', () => {
  const enterBtn = document.getElementById('enter-btn');
  if (enterBtn) {
    enterBtn.addEventListener('click', () => {
      document.getElementById('landing').style.display = 'none';
      document.getElementById('main-ui').style.display = 'block';
      setTimeout(() => map.invalidateSize(), 100); // 지도 재정렬
    });
  }
});

// 브라우저의 "뒤로 가기" 눌렀을 때 처리
document.addEventListener('DOMContentLoaded', () => {
  const enterBtn = document.getElementById('enter-btn');

  if (enterBtn) {
    enterBtn.addEventListener('click', () => {
      // 히스토리 스택에 상태 추가 (URL은 그대로지만 내부 상태 저장됨)
      history.pushState({ page: 'main' }, '', '');
      document.getElementById('landing').style.display = 'none';
      document.getElementById('main-ui').style.display = 'block';
      setTimeout(() => map.invalidateSize(), 100);
    });
  }

  // 브라우저의 "뒤로 가기" 눌렀을 때 처리
  window.addEventListener('popstate', (event) => {
    document.getElementById('main-ui').style.display = 'none';
    document.getElementById('landing').style.display = 'flex';
  });
});

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
      const ampm = document.getElementById('ampm').value;
      const hour = document.getElementById('hour').value;
      const minute = document.getElementById('minute').value;

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
    });
  }

  // 뒤로가기 대응
  window.addEventListener('popstate', () => {
    document.getElementById('main-ui').style.display = 'none';
    document.getElementById('time-setting').style.display = 'none';
    document.getElementById('landing').style.display = 'flex';
  });
});


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
    document.getElementById('arrival-time-box').innerText = latest.predicted_arrival;

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