import threading
from .models import VideoAnalysis
import time
import cv2
import os
from django.conf import settings

# This function will run in the background
def process_video_task(analysis_id):
    try:
        # Avoid circular import by fetching model here, or just fetch directly
        from .models import VideoAnalysis
        analysis = VideoAnalysis.objects.get(id=analysis_id)
        analysis.status = 'Processing'
        analysis.save()

        # Input and output paths
        input_path = analysis.input_video.path
        
        # Prepare output path
        output_filename = f"output_{analysis_id}.mp4"
        output_path = os.path.join(settings.MEDIA_ROOT, 'videos', 'output', output_filename)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
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

        # Run the AI pipeline
        tracker.process_video(input_path, output_path, update_progress)

        # Update final state
        analysis = VideoAnalysis.objects.get(id=analysis_id)
        # We save the relative media path so it can be served via URL
        analysis.output_video = f"videos/output/{output_filename}"
        analysis.progress = 100
        analysis.status = 'Completed'
        analysis.save()
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
