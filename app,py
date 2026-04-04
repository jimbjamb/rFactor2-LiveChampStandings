import json
import time
from flask import Flask, render_template
from flask_socketio import SocketIO

from pyRfactor2SharedMemory.sharedMemoryAPI import SimInfoAPI

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

STANDINGS_FILE = "standings.json"

POINTS_SYSTEM = [25, 20, 16, 13, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1]

info = SimInfoAPI()

def get_data():
    try:
        if not info.isSharedMemoryAvailable():
            return []
        
        scoring = info.scoringInfo()

        with open(STANDINGS_FILE, 'r', encoding='utf-8') as f:
            db = json.load(f)

        m_scoring_info = getattr(scoring, 'mScoringInfo', scoring)
        
        is_race = getattr(m_scoring_info, 'mSession', 0) == 8

        players_name_bytes = getattr(m_scoring_info, 'mPlayerName', b'')
        players_name = players_name_bytes.decode('utf-8', errors='ignore').split('\0', 1)[0].strip()

        all_drivers = []
        num_vehicles = getattr(m_scoring_info, 'mNumVehicles', 0)
        vehicles = getattr(scoring, 'mVehicles', [])

        for i in range(num_vehicles):
            v = vehicles[i]

            name_bytes = getattr(v, 'mDriverName', b'')
            name = name_bytes.decode('utf-8', errors='ignore').split('\0', 1)[0].strip()

            if not name:
                continue

            team_bytes = getattr(v, 'mVehicleName', b'')
            team = team_bytes.decode('utf-8', errors='ignore').split('\0', 1)[0].strip()

            pos = getattr(v, 'mPlace', 0)

            base_points = db['standings'].get(name, 0)
            live_points = 0
            if is_race and 1 <= pos <= len(POINTS_SYSTEM):
                live_points = POINTS_SYSTEM[pos-1]

            total_points = base_points + live_points
            color = db['teams'].get(team, '#808080')

            all_drivers.append({
                "name": name,
                "points": total_points,
                "color": color,
                "is_player": (name == players_name)
            })

        all_drivers.sort(key=lambda x: x['points'], reverse=True)

        try:
            p_idx = next(i for i, d in enumerate(all_drivers) if d['is_player'])
        except StopIteration:
            p_idx = 0

        start = max(0, p_idx - 3)
        return all_drivers[start:start+7]
    
    except Exception as e:
        print(f"Read error in get_data: {e}")
        return []
    
def background_thread():
    while True:
        data = get_data()
        if data:
            socketio.emit('update_data', {'drivers': data})
        socketio.sleep(1)

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    print("Starting server on http://localhost:5000 ...")
    socketio.start_background_task(background_thread)
    socketio.run(app, port=5000, allow_unsafe_werkzeug=True)