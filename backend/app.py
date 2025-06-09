import json
import requests
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


NAVER_CLIENT_ID = 'API_Client_ID' 
NAVER_CLIENT_SECRET = 'API_Client_Secret'

# 도로명 주소 기반 지명
ORIGIN_NAME = "경기도 용인시 수지구 죽전로 152"
DESTINATION_NAME = "경기도 용인시 수지구 포은대로 536"
WAYPOINT_NAME_LIST = [
    "경기도 용인시 수지구 죽전동 1442",
    "경기도 용인시 기흥구 보정동 1353"
]


with open('schedule.json', 'r', encoding='utf-8') as f:
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
    res = requests.get(url, headers=headers, params=params, timeout=5)
    res.raise_for_status()
    data = res.json()
    if not data.get('addresses'):
        raise ValueError(f'지명 "{place_name}"에 대한 좌표를 찾을 수 없습니다.')
    addr = data['addresses'][0]
    return f"{addr['x']},{addr['y']}"


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
    res = requests.get(url, headers=headers, params=params, timeout=5)
    res.raise_for_status()
    data = res.json()
    if data.get('code') != 0:
        raise ValueError('NAVER API 호출 실패: ' + data.get('message', ''))

    route_data = data['route']['trafast'][0]
    duration = route_data['summary']['duration'] / 1000.0  # ms → sec

    raw_path = route_data.get('path', [])
    path_coords = []
    for p in raw_path:
        if isinstance(p, str):
            lng_str, lat_str = p.split(',')
        elif isinstance(p, (list, tuple)) and len(p) >= 2:
            lng_str, lat_str = str(p[0]), str(p[1])
        else:
            continue
        try:
            lng, lat = float(lng_str), float(lat_str)
            path_coords.append((lng, lat))
        except ValueError:
            continue

    route_data['path'] = path_coords
    return duration, route_data

# 좌표 초기화
try:
    ORIGIN = get_coordinates_from_name(ORIGIN_NAME)
    DESTINATION = get_coordinates_from_name(DESTINATION_NAME)
    DEFAULT_WAYPOINTS = [get_coordinates_from_name(n) for n in WAYPOINT_NAME_LIST]
except Exception as e:
    app.logger.error('지오코딩 실패: %s', e)
    raise


@app.route('/predict-arrival', methods=['POST'])
def predict_arrival():
    try:
        req = request.get_json() or {}
        arrival_str = req.get('arrival_time', '')
        if not arrival_str:
            return jsonify({'status': 'error', 'message': 'arrival_time 필수'}), 400

        try:
            arrival_time = datetime.strptime(arrival_str, '%H:%M').replace(
                year=datetime.now().year,
                month=datetime.now().month,
                day=datetime.now().day
            )
        except ValueError:
            return jsonify({'status': 'error', 'message': '올바른 HH:MM 형식이 아닙니다.'}), 400

        past = [t for t in SCHEDULE if t <= arrival_time]
        future = [t for t in SCHEDULE if t > arrival_time]
        candidates = past[-2:] + future[:1]

        if not candidates:
            return jsonify({'status': 'no_bus', 'message': '후보 셔틀이 없습니다.'})

        selected = None
        for dep in candidates:
            try:
                travel_sec, route_info = get_travel_duration_and_route(
                    ORIGIN, DESTINATION, DEFAULT_WAYPOINTS
                )
                pred_arrival = dep + timedelta(seconds=travel_sec)
                if pred_arrival > arrival_time:
                    selected = {'dep': dep, 'pred': pred_arrival,
                                'dur': travel_sec, 'route': route_info}
                    break
            except Exception as err:
                app.logger.error('API 오류 for dep=%s: %s', dep.strftime('%H:%M'), err)

        if not selected:
            return jsonify({'status': 'no_bus', 'message': '입력 시각 이후 도착 셔틀 없음'})

        dep = selected['dep']
        travel_time = selected['dur']
        pred = selected['pred']
        route_info = selected['route']

        elapsed = (arrival_time - dep).total_seconds()
        progress = max(0.0, min(elapsed / travel_time, 1.0))

        path = route_info.get('path', [])
        if len(path) < 2:
            return jsonify({'status': 'error', 'message': '경로 정보 부족'}), 500

        idx_f = progress * (len(path) - 1)
        lo = int(idx_f)
        hi = min(lo + 1, len(path) - 1)
        r = idx_f - lo
        lng = path[lo][0] + (path[hi][0] - path[lo][0]) * r
        lat = path[lo][1] + (path[hi][1] - path[lo][1]) * r

        remaining = (pred - arrival_time).total_seconds()
        frontend_route = [{'lng': p[0], 'lat': p[1]} for p in path]

        result = {
            'departure_time': dep.strftime('%H:%M'),
            'predicted_arrival': pred.strftime('%H:%M'),
            'eta_minutes': round(remaining / 60, 1),
            'current_location': {'lat': lat, 'lng': lng},
            'progress': round(progress * 100, 1),
            'route': frontend_route,
            'status': 'ok'
        }
        return jsonify({'status': 'ok', 'result': result})

    except Exception as e:
        app.logger.error('예외 발생: %s', e)
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False, port=5001)

