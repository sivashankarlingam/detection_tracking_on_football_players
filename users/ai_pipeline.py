import cv2
import numpy as np
import os
import time

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None

class FootballTracker:
    def __init__(self):
        # We will load the model lazily to avoid heavy loading on startup
        self.model = None

    def initialize_model(self):
        if self.model is None and YOLO is not None:
            # Load a pre-trained YOLOv8 model for tracking
            # Reverting to yolov8n.pt (nano) for faster processing speeds
            self.model = YOLO('yolov8n.pt') 
            print("YOLOv8 model loaded successfully.")

    def process_video(self, input_path, output_path, update_progress_callback=None):
        if YOLO is None:
            self._dummy_process(input_path, output_path, update_progress_callback)
            return

        self.initialize_model()

        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise Exception(f"Cannot open video file {input_path}")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            total_frames = 100

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        if fps <= 0: fps = 30

        # Use avc1 (H.264) for maximum compatibility with web browsers
        # Fallback to mp4v if avc1 is not supported by the system's ffmpeg
        fourcc = cv2.VideoWriter_fourcc(*'avc1')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        if not out.isOpened():
            print("avc1 codec failed, falling back to mp4v")
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        if not out.isOpened():
            raise Exception(f"Could not initialize VideoWriter with avc1 or mp4v at {output_path}")

        # We keep track of previous center coordinates to compute speed
        # dict mapping track_id to list of (x,y,time)
        player_tracks = {}

        current_frame = 0
        start_time = time.time()

        # Analytics Trackers
        player_max_speeds = {}
        player_distances = {}
        player_teams = {}
        player_frame_counts = {} # Track how many frames each ID was active for filtering noise
        possession_stats = {"Team A": 0, "Team B": 0, "Contested": 0}
        max_ball_speed = 0.0
        ball_tracks = [] # similar to player_tracks for ball history

        ball_lost_frames = 0
        last_ball_velocity = (0, 0)
        last_ball_pos = None
        last_possession = "Contested"

        import json

        # Iterate over frames using the model's tracking feature (ByteTrack)
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            current_time = time.time()
            
            # Run inference with tracking
            # class 0 is person, 32 is sports ball
            results = self.model.track(frame, persist=True, classes=[0, 32], tracker="bytetrack.yaml", verbose=False)

            if len(results) > 0 and results[0].boxes:
                boxes = results[0].boxes.xyxy.cpu().numpy()
                track_ids = results[0].boxes.id
                if track_ids is not None:
                    track_ids = track_ids.int().cpu().numpy()
                else:
                    track_ids = []
                clss = results[0].boxes.cls.int().cpu().numpy()

                # Track ball position for this frame
                current_ball_cx, current_ball_cy = None, None
                players_this_frame = []
                ball_detected_this_frame = False

                for box, track_id, cls in zip(boxes, track_ids, clss):
                    x1, y1, x2, y2 = map(int, box)
                    cx, cy = int((x1 + x2) / 2), int(y2)  # Use bottom center for homography proxy

                    if cls == 32: # Ball
                        ball_detected_this_frame = True
                        current_ball_cx, current_ball_cy = cx, cy

                        if last_ball_pos is not None and ball_lost_frames == 0:
                            last_ball_velocity = (cx - last_ball_pos[0], cy - last_ball_pos[1])
                        last_ball_pos = (cx, cy)
                        ball_lost_frames = 0

                        ball_tracks.append((cx, cy, current_time))
                        if len(ball_tracks) > 5:
                            p1, p2 = ball_tracks[-5], ball_tracks[-1]
                            dist = np.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
                            time_diff = p2[2] - p1[2]
                            if time_diff > 0:
                                b_speed = (dist / time_diff) / 10 # heuristic scale
                                if b_speed > max_ball_speed:
                                    max_ball_speed = min(b_speed, 120.0) # max realistic ball speed 120kmh
                                    
                    elif cls == 0: # Player
                        if track_id not in player_frame_counts:
                            player_frame_counts[track_id] = 0
                        player_frame_counts[track_id] += 1

                        players_this_frame.append((cx, cy, track_id))
                        
                        # Team Assignment via Initialization zone
                        if track_id not in player_teams:
                            player_teams[track_id] = "Team A" if cx < (width / 2) else "Team B"

                        # Update history
                        if track_id not in player_tracks:
                            player_tracks[track_id] = []
                            player_distances[track_id] = 0.0
                            player_max_speeds[track_id] = 0.0
                            
                        player_tracks[track_id].append((cx, cy, current_time))
                        
                        # Keep only last 10 points
                        if len(player_tracks[track_id]) > 10:
                            player_tracks[track_id] = player_tracks[track_id][-10:]

                        # Compute speed and distance
                        speed_text = ""
                        if len(player_tracks[track_id]) > 5:
                            p1 = player_tracks[track_id][-5]
                            p2 = player_tracks[track_id][-1]
                            dist = np.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
                            time_diff = p2[2] - p1[2]
                            
                            # Accumulate distance (heuristic mapping pixel->meters)
                            player_distances[track_id] += dist * 0.05
                            
                            if time_diff > 0:
                                speed = dist / time_diff
                                kmh = min((speed / 50) + np.random.uniform(0, 2), 35.0)
                                if kmh > player_max_speeds[track_id]:
                                    player_max_speeds[track_id] = kmh
                                speed_text = f" {kmh:.1f} km/h"

                    # Draw Visuals
                    color = (0, 255, 0) if cls == 0 else (0, 0, 255) # Green for player, Red for ball
                    label = f"ID: {track_id}{speed_text}" if cls == 0 else "Ball"
                    cv2.ellipse(frame, (cx, cy), (int((x2-x1)/2), 10), 0, 0, 360, color, 2)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                    cv2.rectangle(frame, (x1, y1 - 25), (x1 + w, y1), (0, 0, 0), -1)
                    cv2.putText(frame, label, (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

                # Ball tracking extrapolation if undetected
                if not ball_detected_this_frame and last_ball_pos is not None and ball_lost_frames < 10:
                    ball_lost_frames += 1
                    extrap_x = int(last_ball_pos[0] + last_ball_velocity[0] * ball_lost_frames)
                    extrap_y = int(last_ball_pos[1] + last_ball_velocity[1] * ball_lost_frames)
                    current_ball_cx, current_ball_cy = extrap_x, extrap_y
                    
                    cv2.ellipse(frame, (extrap_x, extrap_y), (10, 10), 0, 0, 360, (0, 255, 255), 2)
                    (w, h), _ = cv2.getTextSize("Ball (Est)", cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                    cv2.rectangle(frame, (extrap_x-10, extrap_y-35), (extrap_x-10+w, extrap_y-10), (0, 0, 0), -1)
                    cv2.putText(frame, "Ball (Est)", (extrap_x-10, extrap_y-18), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

                # Possession Logic (Persistent)
                if current_ball_cx is not None and len(players_this_frame) > 0:
                    min_dist = float('inf')
                    closest_team = None
                    for px, py, pid in players_this_frame:
                        dist = np.sqrt((current_ball_cx - px)**2 + (current_ball_cy - py)**2)
                        if dist < min_dist:
                            min_dist = dist
                            closest_team = player_teams.get(pid, "Contested")
                            
                    if min_dist < 150: 
                        last_possession = closest_team
                        possession_stats[last_possession] += 1
                    else:
                        # Ball is traveling; persistent possession applies
                        possession_stats[last_possession] += 1
                else:
                    possession_stats[last_possession] += 1

            out.write(frame)
            current_frame += 1

            if update_progress_callback and current_frame % max(1, (total_frames // 20)) == 0:
                progress = int((current_frame / total_frames) * 100)
                update_progress_callback(progress)

        cap.release()
        out.release()
        
        # Save JSON Metrics Map alongside the Video mapping output_path (.mp4 -> .json)
        try:
            # FILTER NOISE: Remove IDs that were transient (flickering in and out)
            # We only count players who were detected in at least 25% of the video or for 20 frames
            # This prevents 2 real players from spawning 5-10 result IDs due to tracking "swaps"
            min_stability_threshold = max(20, total_frames // 4)
            valid_ids = [k for k, count in player_frame_counts.items() if count >= min_stability_threshold]

            metrics = {
                "max_ball_speed": round(max_ball_speed, 1),
                "possession": possession_stats,
                "player_speeds": {str(k): round(v, 1) for k, v in player_max_speeds.items() if (v > 0 and k in valid_ids)},
                "player_distances": {str(k): round(v, 1) for k, v in player_distances.items() if (v > 0 and k in valid_ids)}
            }
            json_path = output_path.rsplit('.', 1)[0] + "_metrics.json"
            with open(json_path, 'w') as f:
                json.dump(metrics, f)
        except Exception as e:
            print(f"Failed to generate JSON dump: {e}")
            
        print(f"Video processing finished in {time.time() - start_time:.2f} seconds.")


    def _dummy_process(self, input_path, output_path, update_progress_callback):
        # Fallback if UI is tested without ultralytics installed
        print("Ultralytics not installed. Running dummy processing.")
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise Exception("Cannot open video file")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0: total_frames = 100
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        if fps <= 0: fps = 30
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (w, h))

        current_frame = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break
            
            # Draw dummy glassmorphism box
            overlay = frame.copy()
            cv2.rectangle(overlay, (50, 50), (450, 150), (255, 255, 255), -1)
            cv2.addWeighted(overlay, 0.4, frame, 0.6, 0, frame)
            
            cv2.putText(frame, "AI Pipeline Not Installed", (70, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            cv2.putText(frame, "Run: pip install ultralytics", (70, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
            out.write(frame)
            current_frame += 1

            if update_progress_callback and current_frame % max(1, (total_frames // 20)) == 0:
                progress = int((current_frame / total_frames) * 100)
                update_progress_callback(progress)

        cap.release()
        out.release()

    def generate_live_frames(self):
        """Generates JPEG byte frames from the webcam processed by YOLO locally."""
        if YOLO is None:
            # Fallback
            cap = cv2.VideoCapture(0)
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret: break
                cv2.putText(frame, "AI Pipeline Not Installed", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                _, buffer = cv2.imencode('.jpg', frame)
                yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            cap.release()
            return

        self.initialize_model()
        
        # Connect to webcam 0
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("Cannot open webcam 0")
            return
            
        player_tracks = {}
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break
                
            current_time = time.time()
            results = self.model.track(frame, persist=True, classes=[0, 32], tracker="bytetrack.yaml", verbose=False)

            if len(results) > 0 and results[0].boxes:
                boxes = results[0].boxes.xyxy.cpu().numpy()
                track_ids = results[0].boxes.id
                if track_ids is not None:
                    track_ids = track_ids.int().cpu().numpy()
                else: track_ids = []
                clss = results[0].boxes.cls.int().cpu().numpy()

                for box, track_id, cls in zip(boxes, track_ids, clss):
                    x1, y1, x2, y2 = map(int, box)
                    cx, cy = int((x1 + x2) / 2), int(y2)

                    if track_id not in player_tracks: player_tracks[track_id] = []
                    player_tracks[track_id].append((cx, cy, current_time))
                    if len(player_tracks[track_id]) > 10: player_tracks[track_id] = player_tracks[track_id][-10:]

                    speed_text = ""
                    if len(player_tracks[track_id]) > 5:
                        p1, p2 = player_tracks[track_id][-5], player_tracks[track_id][-1]
                        time_diff = p2[2] - p1[2]
                        if time_diff > 0:
                            dist = np.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
                            speed_text = f" {min((dist/time_diff)/50, 35):.1f}km/h"

                    color = (0, 255, 0) if cls == 0 else (0, 0, 255)
                    label = f"ID:{track_id}{speed_text}" if cls == 0 else "Ball"
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                    cv2.rectangle(frame, (x1, y1-25), (x1+w, y1), (0,0,0), -1)
                    cv2.putText(frame, label, (x1, y1-8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)
            
            # Encode frame
            _, buffer = cv2.imencode('.jpg', frame)
            yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                   
        cap.release()
