from flask import Flask, request, jsonify, send_from_directory
import firebase_admin
from firebase_admin import credentials, auth, db
from flask_cors import CORS
import requests
import os

app = Flask(__name__, static_folder='templates', static_url_path='')
CORS(app)

cred = credentials.Certificate("C:/Users/rk364/Desktop/sumit/WEBSITE/TY playlist/YT-Player/firebase-adminsdk.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://yt-player-48e44-default-rtdb.firebaseio.com/'  # Replace with your actual URL
})

# Token verification helper
def verify_token(request):
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return None
    try:
        token = auth_header.split(" ")[1]
        decoded_token = auth.verify_id_token(token)
        return decoded_token['uid']
    except:
        return None

@app.route('/')
def index():
    return send_from_directory('templates', 'login.html')

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    token = data.get("token")
    if not token:
        return jsonify({"error": "Missing token"}), 400
    try:
        decoded = auth.verify_id_token(token)
        uid = decoded['uid']
        return jsonify({"message": "User registered", "uid": uid})
    except Exception as e:
        return jsonify({"error": str(e)}), 401

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    token = data.get("token")
    if not token:
        return jsonify({"error": "Missing token"}), 400
    try:
        decoded = auth.verify_id_token(token)
        uid = decoded['uid']
        return jsonify({"message": "Login successful", "uid": uid})
    except Exception as e:
        return jsonify({"error": str(e)}), 401

@app.route('/create_playlist', methods=['POST'])
def create_playlist():
    uid = verify_token(request)
    if not uid:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    name = data.get('name')
    if not name:
        return jsonify({"error": "Playlist name required"}), 400

    ref = db.reference(f'users/{uid}/playlists')
    new_playlist = ref.push({
        'name': name,
        'videos': []
    })
    return jsonify({"id": new_playlist.key, "name": name})

@app.route('/playlists', methods=['GET'])
def get_playlists():
    uid = verify_token(request)
    if not uid:
        return jsonify({"error": "Unauthorized"}), 401

    ref = db.reference(f'users/{uid}/playlists')
    data = ref.get()
    playlists = []
    if data:
        for key, val in data.items():
            videos = val.get('videos', [])
            # Convert to list if it's a dict (common Firebase behavior)
            if isinstance(videos, dict):
                videos = list(videos.values())
            playlists.append({
                'id': key,
                'name': val.get('name'),
                'videos': videos
            })
    return jsonify({"playlists": playlists})


@app.route('/playlists/<playlist_id>/add_video', methods=['POST'])
def add_video_to_playlist(playlist_id):
    print("📥 Add video called for playlist:", playlist_id)
    uid = verify_token(request)
    print("✔ UID:", uid)

    if not uid:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    video_url = data.get("video_url")

    if not video_url:
        return jsonify({"error": "Missing video URL"}), 400

    playlist_ref = db.reference(f'users/{uid}/playlists/{playlist_id}/videos')
    existing = playlist_ref.get() or []
    existing.append(video_url)
    playlist_ref.set(existing)

    return jsonify({"message": "Video added successfully"})


@app.route("/fetch_metadata", methods=["POST"])
def fetch_metadata():
    data = request.get_json()
    video_url = data.get("video_url")
    try:
        res = requests.get(f"https://www.youtube.com/oembed?url={video_url}&format=json")
        if res.status_code != 200:
            return jsonify({"error": "Invalid or inaccessible video"}), 400
        return res.json()
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/playlists/<playlist_id>/delete_video/<int:video_index>', methods=['DELETE'])
def delete_video_from_playlist(playlist_id, video_index):
    uid = verify_token(request)
    if not uid:
        return jsonify({"error": "Unauthorized"}), 401

    playlist_ref = db.reference(f'users/{uid}/playlists/{playlist_id}/videos')
    videos = playlist_ref.get() or []
    if not isinstance(videos, list):
        videos = list(videos.values())
    if video_index < 0 or video_index >= len(videos):
        return jsonify({"error": "Invalid video index"}), 400

    # Remove the video at the given index
    videos.pop(video_index)
    playlist_ref.set(videos)
    return jsonify({"message": "Video deleted successfully"})

@app.route('/playlists/<playlist_id>', methods=['DELETE'])
def delete_playlist(playlist_id):
    uid = verify_token(request)
    if not uid:
        return jsonify({"error": "Unauthorized"}), 401

    playlist_ref = db.reference(f'users/{uid}/playlists/{playlist_id}')
    if not playlist_ref.get():
        return jsonify({"error": "Playlist not found"}), 404

    playlist_ref.delete()
    return jsonify({"message": "Playlist deleted successfully"})



@app.route('/home')
def home():
    return send_from_directory('templates', 'home.html')

if __name__ == '__main__':
    app.run(debug=True)