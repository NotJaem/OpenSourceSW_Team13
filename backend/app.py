import json
import requests  # HTTP 요청을 보내기 위한 외부 라이브러리
from flask import Flask, request, jsonify  # Flask는 웹 서버 프레임워크이며 request는 요청, jsonify는 JSON 응답 반환용
from datetime import datetime, timedelta  # 시간 계산을 위한 모듈
from flask_cors import CORS  # 다른 도메인에서 접근할 수 있도록 CORS 허용

app = Flask(__name__)  # Flask 앱 인스턴스 생성
CORS(app)  # 프론트엔드와 연동 시 CORS 문제 방지

GOOGLE_API_KEY = 'your_API_Key'  # Google Maps API 호출 시 필요한 인증 키

# json 파일 열기
with open('schedule.json', 'r') as f:
    SCHEDULE = json.load(f)

ORIGIN = '37.3196,127.1284'       # 단국대 스타벅스 앞 큰길
DESTINATION = '37.3279,127.1245'  # 신세계백화점·다이소 사이 도로변
WAYPOINTS = []  # 필요 시 경유지 추가

@app.route('/predict-arrival', methods=['POST'])
def predict_arrival():
    try:
        user_input = request.get_json()
        arrival_str = user_input.get('arrival_time')
        arrival_time = datetime.strptime(arrival_str, '%H:%M')
        now = datetime.now()
        arrival_time = arrival_time.replace(year=now.year, month=now.month, day=now.day)

        # 전체 시간 리스트 정렬
        all_departures = sorted([
            datetime.strptime(t, '%H:%M').replace(year=now.year, month=now.month, day=now.day)
            for t in SCHEDULE
        ])

        # 도착 시간 기준으로 과거 2개 + 미래 1개 선택
        candidate_departures = [t for t in all_departures if t <= arrival_time]
        if not candidate_departures:
            return jsonify({'status': 'no_bus', 'message': '해당 시간 이전 출발 셔틀이 없습니다.'})

        past_two = candidate_departures[-2:] if len(candidate_departures) >= 2 else candidate_departures
        future_one = [t for t in all_departures if t > arrival_time][:1]
        selected_candidates = past_two + future_one

        results = []
        for dep in selected_candidates:
            try:
                travel_time_sec, route_steps = get_travel_duration_and_route(dep)
                predicted_arrival = dep + timedelta(seconds=travel_time_sec)

                elapsed = (datetime.now() - dep).total_seconds()
                progress = min(max(elapsed / travel_time_sec, 0), 1.0)
                segment_index = int(progress * (len(route_steps) - 1))
                segment_index = min(segment_index, len(route_steps) - 2)
                segment_progress = (progress * (len(route_steps) - 1)) % 1

                start_loc = route_steps[segment_index]['start_location']
                end_loc = route_steps[segment_index + 1]['start_location']
                lat = start_loc['lat'] + (end_loc['lat'] - start_loc['lat']) * segment_progress
                lng = start_loc['lng'] + (end_loc['lng'] - start_loc['lng']) * segment_progress

                remaining = (predicted_arrival - datetime.now()).total_seconds()

                results.append({
                    'departure_time': dep.strftime('%H:%M'),
                    'predicted_arrival': predicted_arrival.strftime('%H:%M'),
                    'eta_minutes': round(remaining / 60, 1),
                    'current_location': {'lat': lat, 'lng': lng},
                    'progress': round(progress * 100, 1),
                    'status': 'ok'
                })
            except Exception as e:
                results.append({
                    'departure_time': dep.strftime('%H:%M'),
                    'status': 'error',
                    'message': str(e)
                })

        return jsonify({'status': 'ok', 'candidates': results})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})


def get_travel_duration_and_route(departure_time):
    timestamp = int(departure_time.timestamp())
    now_ts = int(datetime.now().timestamp())

    if timestamp < now_ts:
        timestamp = now_ts

    url = 'https://maps.googleapis.com/maps/api/directions/json'
    params = {
        'origin': ORIGIN,
        'destination': DESTINATION,
        'mode': 'transit',
        'waypoints': '|'.join(WAYPOINTS),
        'departure_time': timestamp,
        'key': GOOGLE_API_KEY
    }

    response = requests.get(url, params=params)
    data = response.json()

    if data['status'] != 'OK':
        raise Exception('Google API 호출 실패: ' + data['status'] + " / " + data.get("error_message", ""))

    leg = data['routes'][0]['legs'][0]
    duration = leg.get('duration_in_traffic', leg['duration'])['value']
    steps = leg['steps']

    return duration, steps


if __name__ == '__main__':
    app.run(debug=True)
