from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp
import os
import re

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True, methods=["GET", "POST"], allow_headers=["Content-Type"])

DOWNLOAD_DIRECTORY = "downloads"
if not os.path.exists(DOWNLOAD_DIRECTORY):
    os.makedirs(DOWNLOAD_DIRECTORY)

def sanitize_filename(filename):
    # Replace problematic characters with underscores
    return re.sub(r'[<>:"/\\|?*\x00-\x1F]', '_', filename)

@app.route('/extract', methods=['POST'])
def extract():
    data = request.get_json()
    encoded_url = data['url']

    # Print the URL to the console
    print(f"Extracting video from URL: {encoded_url}")

    ydl_opts = {
        'quiet': True,
        'format': 'bestaudio/best',  # Use a format that allows extraction of both audio and video formats
        'noplaylist': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        },
        'retries': 5,
        'timeout': 60,
        'ignoreerrors': True,
        'nocheckcertificate': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(encoded_url, download=False)
            formats = info.get('formats', [])
            if not formats:
                return jsonify({'error': 'No formats found'}), 404

            format_list = []
            for f in formats:
                # Determine quality
                quality = f.get('format_note') or f.get('height') or 'Unknown'
                if isinstance(quality, int):
                    quality = f'{quality}p'

                # Check if the format is audio or video
                if 'audio' in f.get('acodec', '').lower() and 'video' not in f.get('vcodec', '').lower():
                    format_type = 'Audio'
                else:
                    format_type = 'Video'
                
                format_list.append({
                    'format_id': f.get('format_id'),
                    'quality': quality,
                    'type': format_type,
                    'ext': f.get('ext', 'mp4'),
                    'url': f.get('url')
                })

            # Print available formats to the terminal
            print("Available formats:")
            for f in format_list:
                print(f"ID: {f['format_id']}, Quality: {f['quality']}, Type: {f['type']}, Extension: {f['ext']}, URL: {f['url']}")

        return jsonify({
            'formats': format_list,
            'thumbnail_url': info.get('thumbnail', 'https://via.placeholder.com/150'),
            'title': info.get('title', 'Unknown Title')
        })

    except yt_dlp.DownloadError as e:
        return jsonify({'error': f"Download error: {str(e)}"}), 400
    except Exception as e:
        return jsonify({'error': f"An unexpected error occurred: {str(e)}"}), 500

@app.route('/select', methods=['POST'])
def select():
    data = request.get_json()
    encoded_url = data['url']
    format_id = data['format_id']

    # Print the URL and format_id to the console
    print(f"Downloading video from URL: {encoded_url} with format_id: {format_id}")

    ydl_opts = {
        'quiet': True,
        'outtmpl': os.path.join(DOWNLOAD_DIRECTORY, '%(title)s.%(ext)s'),
        'format': format_id,
        'noplaylist': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        },
        'retries': 5,
        'timeout': 60,
        'ignoreerrors': True,
        'nocheckcertificate': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(encoded_url)
            download_path = ydl.prepare_filename(info)
            sanitized_name = sanitize_filename(os.path.basename(download_path))
            sanitized_path = os.path.join(DOWNLOAD_DIRECTORY, sanitized_name)
            thumbnail_url = info.get('thumbnail', 'https://via.placeholder.com/150')
            size = info.get('filesize') or info.get('filesize_approx', 'Unknown')
            ext = info.get('ext', 'mp4')

        if os.path.exists(sanitized_path):
            return jsonify({
                'download_url': f'/download/{sanitized_name}',
                'thumbnail_url': thumbnail_url,
                'size': size,
                'name': sanitized_name,
                'ext': ext,
            })
        else:
            return jsonify({'error': 'Failed to download video'}), 400

    except yt_dlp.DownloadError as e:
        return jsonify({'error': f"Download error: {str(e)}"}), 400
    except Exception as e:
        return jsonify({'error': f"An unexpected error occurred: {str(e)}"}), 500

@app.route('/download/<filename>', methods=['GET'])
def download(filename):
    sanitized_filename = sanitize_filename(filename)
    file_path = os.path.join(DOWNLOAD_DIRECTORY, sanitized_filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return jsonify({'error': 'File not found'}), 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
