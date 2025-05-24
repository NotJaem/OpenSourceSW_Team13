import json
import requests
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

NAVER_CLIENT_ID = 'API_Client_ID'  # <-- 여기에 본인의 NAVER API Client ID 입력
NAVER_CLIENT_SECRET = 'API_Client_Secret'  # <-- 여기에 본인의 NAVER API Client Secret 입력

# 지명 기반 기본 설정
ORIGIN_NAME = "경기 용인시 수지구 죽전로 152"
DESTINATION_NAME = "경기 용인시 수지구 포은대로 536"
WAYPOINT_NAME_LIST = ["경기 용인시 기흥구 죽전로 3 "]

# JSON 시간 데이터를 datetime 객체 리스트로 변환
with open('schedule.json', 'r') as f:
    raw_schedule = json.load(f)
    now = datetime.now()
    SCHEDULE = sorted([
        datetime.strptime(t, '%H:%M').replace(year=now.year, month=now.month, day=now.day)
        for t in raw_schedule
    ])

def get_coordinates_from_name(place_name):
    url = 'https://maps.apigw.ntruss.com/map-geocode/v2/geocode'
    headers = {
        'X-NCP-APIGW-API-KEY-ID': NAVER_CLIENT_ID,
        'X-NCP-APIGW-API-KEY': NAVER_CLIENT_SECRET
    }
    params = {'query': place_name}
    response = requests.get(url, headers=headers, params=params)
    data = response.json()
    if 'addresses' not in data or not data['addresses']:
        raise Exception(f'지명 "{place_name}"에 대한 좌표를 찾을 수 없습니다.')
    addr = data['addresses'][0]
    return f"{addr['x']},{addr['y']}"

try:
    ORIGIN = get_coordinates_from_name(ORIGIN_NAME)
    DESTINATION = get_coordinates_from_name(DESTINATION_NAME)
    DEFAULT_WAYPOINTS = [get_coordinates_from_name(name) for name in WAYPOINT_NAME_LIST]
except Exception as e:
    print("지오코딩 실패:", e)
    exit(1)

@app.route('/predict-arrival', methods=['POST'])
def predict_arrival():
    try:
        user_input = request.get_json()
        arrival_str = user_input.get('arrival_time')

        origin = ORIGIN
        destination = DESTINATION
        waypoints = DEFAULT_WAYPOINTS

        arrival_time = datetime.strptime(arrival_str, '%H:%M')
        now = datetime.now()
        arrival_time = arrival_time.replace(year=now.year, month=now.month, day=now.day)

        candidate_departures = [t for t in SCHEDULE if t <= arrival_time]
        if not candidate_departures:
            return jsonify({'status': 'no_bus', 'message': '해당 시간 이전 출발 셔틀이 없습니다.'})

        past_two = candidate_departures[-2:] if len(candidate_departures) >= 2 else candidate_departures
        future_one = [t for t in SCHEDULE if t > arrival_time][:1]
        selected_candidates = past_two + future_one

        results = []
        for dep in selected_candidates:
            try:
                travel_time_sec, route = get_travel_duration_and_route(origin, destination, waypoints)
                predicted_arrival = dep + timedelta(seconds=travel_time_sec)

                elapsed = (datetime.now() - dep).total_seconds()
                progress = min(max(elapsed / travel_time_sec, 0), 1.0)

                summary = route.get('summary')
                if not summary:
                    raise Exception('요약 정보가 없습니다.')

                start = summary.get('start')
                goal = summary.get('goal')
                if not start or not goal:
                    raise Exception('출발지 또는 도착지 정보가 없습니다.')

                start_loc = start.get('location')
                end_loc = goal.get('location')
                if not start_loc or not end_loc:
                    raise Exception('위치 정보가 없습니다.')

                lat = start_loc[1] + (end_loc[1] - start_loc[1]) * progress
                lng = start_loc[0] + (end_loc[0] - start_loc[0]) * progress

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

def get_travel_duration_and_route(origin, destination, waypoints):
    url = 'https://maps.apigw.ntruss.com/map-direction/v1/driving'
    headers = {
        'X-NCP-APIGW-API-KEY-ID': NAVER_CLIENT_ID,
        'X-NCP-APIGW-API-KEY': NAVER_CLIENT_SECRET
    }
    params = {
        'start': origin,
        'goal': destination,
        'waypoints': '|'.join(waypoints),
        'option': 'trafast'
    }

    response = requests.get(url, headers=headers, params=params)
    data = response.json()

    if data.get('code') != 0:
        raise Exception('NAVER API 호출 실패: ' + data.get('message', '') + ' / 응답 전문: ' + json.dumps(data))

    route = data['route']['trafast'][0]
    duration = route['summary']['duration'] / 1000  # ms to sec

    return duration, route

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False, port=5001)
