import threading
from .models import VideoAnalysis
import time
import cv2
import os
import tempfile
from django.conf import settings
from django.core.files.base import ContentFile
from cloudinary.uploader import upload

# This function will run in the background
def process_video_task(analysis_id):
    try:
        # Avoid circular import by fetching model here, or just fetch directly
        from .models import VideoAnalysis
        analysis = VideoAnalysis.objects.get(id=analysis_id)
        analysis.status = 'Processing'
        analysis.save()

        # In Cloudinary Media Storage, path is the Cloudinary Cloud path or public_id.
        # But our local AI pipeline needs a local file path.
        # Since input may be stored in Cloudinary, we should download it temporarily if not local
        # For simplicity, assuming local server handling, however we will parse to temp paths.
        
        # Prepare output path in a system temp directory (ephemeral storage)
        output_filename = f"output_{analysis_id}.mp4"
        temp_dir = tempfile.gettempdir()
        output_temp_path = os.path.join(temp_dir, output_filename)
        
        # We also need a local input path. To be safe, Cloudinary models often provide a URL.
        # Since this script previously dealt with local files, we'll try to fetch local if possible
        # or use Cloudinary's URL.
        input_url = analysis.input_video.url
        
        from .ai_pipeline import FootballTracker
        tracker = FootballTracker()

        last_progress_update = 0

        def update_progress(p):
            nonlocal last_progress_update
            # Only update if progress increases by at least 5% or hits 99
            if p >= last_progress_update + 5 or p >= 99:
                for attempt in range(5):
                    try:
                        # Fetch instance inside to avoid stale object states
                        from .models import VideoAnalysis
                        v = VideoAnalysis.objects.get(id=analysis_id)
                        v.progress = min(p, 99)
                        v.save()
                        last_progress_update = p
                        break
                    except Exception as e:
                        if 'locked' in str(e).lower() or 'operationalerror' in str(type(e)).lower():
                            time.sleep(0.5)
                        else:
                            break

        # ── Download Cloudinary input video to a local temp file ─────────────
        # cv2.VideoCapture() cannot open HTTP/HTTPS URLs directly — it must
        # receive a local filesystem path. We download the Cloudinary video
        # from its storage URL to a temp file and pass that path to the AI pipeline.
        import urllib.request
        input_url = analysis.input_video.url
        # If running locally, analysis.input_video.url might be a local path,
        # but in production it's a Cloudinary URL. urllib handles both if they are valid URLs.
        input_ext = os.path.splitext(input_url.split('?')[0])[-1] or '.mp4'
        input_temp_path = os.path.join(temp_dir, f"input_{analysis_id}{input_ext}")

        print(f"DEBUG: Downloading input video from storage: {input_url}")
        urllib.request.urlretrieve(input_url, input_temp_path)
        print(f"DEBUG: Downloaded to temp path: {input_temp_path}")

        # Run the AI pipeline using the local temp file
        tracker.process_video(input_temp_path, output_temp_path, update_progress)

        # ── FFmpeg H.264 Re-encoding ─────────────
        # OpenCV in Docker often falls back to 'mp4v' because it lacks the 'avc1'
        # plugin. Since 'mp4v' cannot be played natively in web browsers, we use
        # the system's FFmpeg CLI to correctly re-encode the file to H.264.
        import subprocess
        h264_temp_path = output_temp_path.rsplit('.', 1)[0] + "_h264.mp4"
        try:
            print(f"DEBUG: Starting final FFmpeg re-encoding to H.264... {output_temp_path}")
            # -y overwrites, -vcodec libx264 enforces proper browser support
            subprocess.run([
                'ffmpeg', '-y', '-i', output_temp_path,
                '-vcodec', 'libx264', '-crf', '23', '-preset', 'fast',
                '-pix_fmt', 'yuv420p', h264_temp_path
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            
            # Replace the old mp4v file with the newly encoded H.264 file
            os.replace(h264_temp_path, output_temp_path)
            print("Successfully re-encoded to proper H.264.")
        except subprocess.CalledProcessError as e:
            print(f"FFmpeg re-encoding failed: {e.stderr.decode('utf-8', errors='ignore')}")
            # If it fails, it will safely fall back to uploading the original mp4v
            if os.path.exists(h264_temp_path):
                os.remove(h264_temp_path)

        # Update final state - Upload processed video to cloudinary
        analysis = VideoAnalysis.objects.get(id=analysis_id)
        
        # Uploading to Cloudinary
        upload_data = upload(
            output_temp_path,
            resource_type="video",
            folder="videos/output/"
        )
        
        # Cloudinary returns 'public_id' we need to store for MediaCloudinaryStorage.
        # usually `public_id` or string of the path. Django-Cloudinary-Storage handles FileField transparently
        analysis.output_video.name = upload_data['public_id']
        analysis.progress = 100
        analysis.status = 'Completed'
        analysis.save()
        
        # Clean up both temporary files to save space
        if os.path.exists(output_temp_path):
            os.remove(output_temp_path)
        if 'input_temp_path' in locals() and os.path.exists(input_temp_path):
            os.remove(input_temp_path)
            
        print(f"Video {analysis_id} processing completed.")

    except Exception as e:
        print(f"Error processing video {analysis_id}: {str(e)}")
        try:
            analysis = VideoAnalysis.objects.get(id=analysis_id)
            analysis.status = 'Failed'
            analysis.save()
        except:
            pass

def trigger_video_processing(analysis_id):
    thread = threading.Thread(target=process_video_task, args=(analysis_id,))
    thread.daemon = True
    thread.start()
