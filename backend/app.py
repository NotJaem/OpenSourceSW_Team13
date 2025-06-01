import json
import requests
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

NAVER_CLIENT_ID = 'key'  # <-- NAVER API Client ID 입력
NAVER_CLIENT_SECRET = 'key'  # <-- NAVER API Client Secret 입력

# 도로명 주소 기반 지명
ORIGIN_NAME = "경기도 용인시 수지구 죽전로 152"
DESTINATION_NAME = "경기도 용인시 수지구 포은대로 536"
WAYPOINT_NAME_LIST = [
    "경기도 용인시 수지구 죽전동 1442",
    "경기도 용인시 기흥구 보정동 1353"
]

# JSON 시간 데이터를 datetime 리스트로 변환
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
        print('user_input:', user_input)  # 클라이언트가 전달한 전체 요청 데이터

        arrival_str = user_input.get('arrival_time')
        print('받은 arrival_time:', arrival_str)  # 입력된 도착 시각(문자열)

        arrival_time = datetime.strptime(arrival_str, '%H:%M').replace(
            year=datetime.now().year, month=datetime.now().month, day=datetime.now().day)
        print('파싱된 arrival_time:', arrival_time)  # datetime으로 변환된 도착 시각

        # 후보: 과거 2개 + 미래 1개
        candidate_departures = [t for t in SCHEDULE if t <= arrival_time]
        past_two = candidate_departures[-2:] if len(candidate_departures) >= 2 else candidate_departures
        future_one = [t for t in SCHEDULE if t > arrival_time][:1]
        selected_candidates = past_two + future_one
        print('선택된 후보 출발시각 목록:', [c.strftime('%H:%M') for c in selected_candidates])

        if not selected_candidates:
            print('후보 셔틀 없음')
            return jsonify({'status': 'no_bus', 'message': '후보 셔틀이 없습니다.'})

         # 후보들 중에서 arrival_time보다 큰 predicted_arrival의 첫번째를 찾음
        selected = None
        for dep in selected_candidates:
            try:
                travel_time_sec, route = get_travel_duration_and_route(
                    ORIGIN, DESTINATION, DEFAULT_WAYPOINTS)
                predicted_arrival = dep + timedelta(seconds=travel_time_sec)
                print(f'  - dep: {dep.strftime("%H:%M")}, 예상도착: {predicted_arrival.strftime("%H:%M")}, 이동시간(초): {travel_time_sec}')
                if predicted_arrival > arrival_time:
                    selected = {
                        'dep': dep,
                        'predicted_arrival': predicted_arrival,
                        'travel_time_sec': travel_time_sec,
                        'route': route
                    }
                    print(f'>> 선택된 후보: dep={dep.strftime("%H:%M")}, predicted_arrival={predicted_arrival.strftime("%H:%M")}')
                    break
            except Exception as e:
                print(f'  - dep: {dep.strftime("%H:%M")} API 오류: {e}')

        if not selected:
            print('조건에 맞는 셔틀 후보 없음')
            return jsonify({'status': 'no_bus', 'message': '입력 도착시각 이후 도착 가능한 셔틀이 없습니다.'})

        dep = selected['dep']
        travel_time_sec = selected['travel_time_sec']
        predicted_arrival = selected['predicted_arrival']
        route = selected['route']


        # 진행률 등 계산
        elapsed = (arrival_time - dep).total_seconds()
        print('경과시간(초):', elapsed)  # 셔틀 출발 이후 도착시각까지 흐른 시간
        progress = min(max(elapsed / travel_time_sec, 0), 1.0)
        print('진행률(progress, 0~1):', progress)  # 셔틀 진행률

        path = route.get('path')
        print('경로 path 길이:', len(path) if path else 'None')  # 경로 좌표 개수
        if not path or len(path) < 2:
            print('경로 정보 부족')
            raise Exception('경로 정보(path)가 부족합니다.')

        # 진행도 기반 현재 위치 계산
        index_float = progress * (len(path) - 1)
        lower_index = int(index_float)
        upper_index = min(lower_index + 1, len(path) - 1)
        ratio = index_float - lower_index

        x1, y1 = path[lower_index]
        x2, y2 = path[upper_index]
        lng = x1 + (x2 - x1) * ratio
        lat = y1 + (y2 - y1) * ratio

        remaining = (predicted_arrival - arrival_time).total_seconds()
        print('남은 시간(초):', remaining)  # arrival_time 기준, 셔틀 도착까지 남은 시간(초)

        result = {
            'departure_time': dep.strftime('%H:%M'),
            'predicted_arrival': predicted_arrival.strftime('%H:%M'),
            'eta_minutes': round(remaining / 60, 1),
            'current_location': {'lat': lat, 'lng': lng},
            'progress': round(progress * 100, 1),
            'status': 'ok'
        }
        print('최종 반환 result:', result)  # 실제로 프론트에 보낼 예측 결과

        return jsonify({'status': 'ok', 'result': result})
    except Exception as e:
        print('예외 발생:', str(e))
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
    duration = route['summary']['duration'] / 1000  # ms -> sec

    return duration, route


if __name__ == '__main__':
    app.run(debug=True, use_reloader=False, port=5001)