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
        self.model = None

    def initialize_model(self):
        if self.model is None and YOLO is not None:
            self.model = YOLO('yolov8m.pt')
            print("YOLOv8m model loaded successfully.")

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

        width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps    = int(cap.get(cv2.CAP_PROP_FPS))
        if fps <= 0:
            fps = 30

        try:
            fourcc = cv2.VideoWriter_fourcc(*'avc1')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            if not out.isOpened():
                raise Exception("avc1 failed")
        except Exception as e:
            print(f"DEBUG: avc1 initialization failed: {e}. Falling back to mp4v.")
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            if not out.isOpened():
                print("CRITICAL: Even mp4v fallback failed! Using MJPG as last resort.")
                fourcc = cv2.VideoWriter_fourcc(*'MJPG')
                out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        # --- Homography Setup (Standard 105m x 68m pitch) ---
        # TODO: Replace the X, Y coordinates below with the EXACT pixel coordinates 
        # of the 4 corners of the Penalty Box from your specific video feed.
        src_pts = np.array([
            [0, 0],       # Bottom-Left Penalty Box Corner (Pixel X, Y)
            [0, 0],       # Bottom-Right Penalty Box Corner (Pixel X, Y)
            [0, 0],       # Top-Left Penalty Box Corner (Pixel X, Y)
            [0, 0]        # Top-Right Penalty Box Corner (Pixel X, Y)
        ], dtype=np.float32)

        # Mapping to the precise physical dimensions of a standard Penalty Box (40.3m x 16.5m)
        dst_pts = np.array([
            [0, 16.5],       # Bottom-Left
            [40.3, 16.5],    # Bottom-Right
            [0, 0],          # Top-Left
            [40.3, 0]        # Top-Right
        ], dtype=np.float32)

        H_matrix, _ = cv2.findHomography(src_pts, dst_pts)

        def transform_point(cx, cy):
            if H_matrix is None:
                # Fallback proportional mapping if Homography fails (e.g. coordinates are all zeros)
                # Maps directly to a standard 105mx68m pitch
                return (cx / float(width)) * 105.0, (cy / float(height)) * 68.0
                
            pt = np.array([[[cx, cy]]], dtype=np.float32)
            transformed = cv2.perspectiveTransform(pt, H_matrix)
            return transformed[0][0][0], transformed[0][0][1]

        # --- Tracker Data Structures ---
        player_tracks     = {}
        player_max_speeds = {}
        player_distances  = {}
        player_teams      = {}
        possession_stats  = {"Team A": 0, "Team B": 0, "Contested": 0}
        max_ball_speed    = 0.0
        ball_tracks       = []
        
        last_possession   = "Contested"

        # --- Kalman Filter Setup for Ball ---
        kf = cv2.KalmanFilter(4, 2)
        kf.measurementMatrix = np.array([[1, 0, 0, 0], [0, 1, 0, 0]], np.float32)
        kf.transitionMatrix = np.array([[1, 0, 1, 0], [0, 1, 0, 1], [0, 0, 1, 0], [0, 0, 0, 1]], np.float32)
        kf.processNoiseCov = np.eye(4, dtype=np.float32) * 0.03
        kf.measurementNoiseCov = np.eye(2, dtype=np.float32) * 1e-1
        kf.errorCovPost = np.eye(4, dtype=np.float32) * 1.0
        
        ball_kf_initialized = False
        ball_lost_frames = 0
        current_ball_cx, current_ball_cy = None, None

        import json
        current_frame = 0
        start_time = time.time()

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            current_time = time.time()
            
            # Run tracker
            results = self.model.track(
                frame, persist=True, classes=[0, 32],
                tracker="bytetrack.yaml", verbose=False
            )

            players_this_frame = []
            ball_detected_this_frame = False

            if len(results) > 0 and results[0].boxes:
                boxes     = results[0].boxes.xyxy.cpu().numpy()
                track_ids = results[0].boxes.id
                if track_ids is not None:
                    track_ids = track_ids.int().cpu().numpy()
                else:
                    track_ids = []
                clss = results[0].boxes.cls.int().cpu().numpy()

                for box, track_id, cls in zip(boxes, track_ids, clss):
                    x1, y1, x2, y2 = map(int, box)
                    cx = int((x1 + x2) / 2)
                    cy = int(y2)

                    if cls == 32:  # Ball
                        ball_detected_this_frame = True

                        if not ball_kf_initialized:
                            kf.statePost = np.array([[np.float32(cx)], [np.float32(cy)], [0], [0]], np.float32)
                            ball_kf_initialized = True
                        else:
                            kf.predict()
                            kf.correct(np.array([[np.float32(cx)], [np.float32(cy)]], np.float32))

                        current_ball_cx, current_ball_cy = cx, cy
                        ball_lost_frames = 0

                        # Calculate true metric speed using Homography
                        ball_mx, ball_my = transform_point(cx, cy)
                        ball_tracks.append((ball_mx, ball_my, current_time))
                        
                        if len(ball_tracks) > 5:
                            p1, p2 = ball_tracks[-5], ball_tracks[-1]
                            dist_m = np.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)
                            time_diff = p2[2] - p1[2]
                            if time_diff > 0:
                                b_speed_kmh = (dist_m / time_diff) * 3.6
                                if b_speed_kmh > max_ball_speed:
                                    max_ball_speed = min(b_speed_kmh, 150.0)

                    elif cls == 0:  # Player
                        players_this_frame.append((cx, cy, track_id))

                        if track_id not in player_teams:
                            # Simple heuristic for teams: right/left of screen on first sight
                            player_teams[track_id] = "Team A" if cx < (width / 2) else "Team B"

                        if track_id not in player_tracks:
                            player_tracks[track_id]     = []
                            player_distances[track_id]  = 0.0
                            player_max_speeds[track_id] = 0.0

                        pmx, pmy = transform_point(cx, cy)
                        player_tracks[track_id].append((pmx, pmy, current_time))
                        
                        if len(player_tracks[track_id]) > 10:
                            player_tracks[track_id] = player_tracks[track_id][-10:]

                        speed_text = ""
                        if len(player_tracks[track_id]) > 5:
                            p1 = player_tracks[track_id][-5]
                            p2 = player_tracks[track_id][-1]
                            
                            incr_p1 = player_tracks[track_id][-2]
                            incr_p2 = player_tracks[track_id][-1]
                            incr_dist = np.sqrt((incr_p2[0]-incr_p1[0])**2 + (incr_p2[1]-incr_p1[1])**2)
                            
                            # Increment total distance by real meters
                            player_distances[track_id] += incr_dist

                            dist_m = np.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)
                            time_diff = p2[2] - p1[2]
                            
                            if time_diff > 0:
                                speed_kmh = (dist_m / time_diff) * 3.6
                                kmh = min(speed_kmh, 38.0) # Human physical limit
                                if kmh > player_max_speeds[track_id]:
                                    player_max_speeds[track_id] = kmh
                                speed_text = f" {kmh:.1f} km/h"

                    # Draw visuals
                    color = (0, 255, 0) if cls == 0 else (0, 0, 255)
                    label = f"ID: {track_id}{speed_text}" if cls == 0 else "Ball"
                    cv2.ellipse(frame, (cx, cy), (int((x2-x1)/2), 10), 0, 0, 360, color, 2)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                    cv2.rectangle(frame, (x1, y1-25), (x1+w, y1), (0, 0, 0), -1)
                    cv2.putText(frame, label, (x1, y1-8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            # --- Ball Occlusion Handling (Kalman Filter Predict) ---
            if not ball_detected_this_frame and ball_kf_initialized and ball_lost_frames < 30:
                ball_lost_frames += 1
                pred = kf.predict()
                extrap_x, extrap_y = int(pred[0, 0]), int(pred[1, 0])
                current_ball_cx, current_ball_cy = extrap_x, extrap_y
                
                # Draw estimated ball
                cv2.ellipse(frame, (extrap_x, extrap_y), (10, 10), 0, 0, 360, (0, 255, 255), 2)
                cv2.putText(frame, "Ball (Est)", (extrap_x-10, extrap_y-18), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

            # --- Possession Logic ---
            if current_ball_cx is not None and len(players_this_frame) > 0:
                min_dist     = float('inf')
                closest_team = None
                for cx, cy, pid in players_this_frame:
                    d = np.sqrt((current_ball_cx-cx)**2 + (current_ball_cy-cy)**2)
                    if d < min_dist:
                        min_dist     = d
                        closest_team = player_teams.get(pid, "Contested")
                if min_dist < 150: # pixel threshold for control
                    last_possession = closest_team
                possession_stats[last_possession] += 1
            else:
                possession_stats[last_possession] += 1

            # --- 2D Tactical Radar Mini-Map ---
            radar_w, radar_h = 210, 136
            radar_x1, radar_y1 = width - radar_w - 20, height - radar_h - 20
            
            overlay = frame.copy()
            # Draw pitch
            cv2.rectangle(overlay, (radar_x1, radar_y1), (radar_x1 + radar_w, radar_y1 + radar_h), (0, 100, 0), -1)
            cv2.rectangle(overlay, (radar_x1, radar_y1), (radar_x1 + radar_w, radar_y1 + radar_h), (255, 255, 255), 2)
            cv2.line(overlay, (radar_x1 + radar_w//2, radar_y1), (radar_x1 + radar_w//2, radar_y1 + radar_h), (255, 255, 255), 2)
            cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

            def map_to_radar(X_m, Y_m):
                rx = int(radar_x1 + (X_m / 105.0) * radar_w)
                # Map Y such that 0 is top and 68 is bottom of radar
                ry = int(radar_y1 + (Y_m / 68.0) * radar_h)
                rx = max(radar_x1, min(rx, radar_x1 + radar_w))
                ry = max(radar_y1, min(ry, radar_y1 + radar_h))
                return rx, ry

            # Draw Players on radar
            for (cx, cy, p_id) in players_this_frame:
                pmx, pmy = transform_point(cx, cy)
                rx, ry = map_to_radar(pmx, pmy)
                color = (255, 50, 50) if player_teams.get(p_id, "Team A") == "Team B" else (50, 50, 255)
                cv2.circle(frame, (rx, ry), 4, color, -1)
                cv2.circle(frame, (rx, ry), 4, (255, 255, 255), 1)

            # Draw Ball on radar
            if current_ball_cx is not None:
                bmx, bmy = transform_point(current_ball_cx, current_ball_cy)
                rx, ry = map_to_radar(bmx, bmy)
                cv2.circle(frame, (rx, ry), 4, (0, 255, 255), -1)

            out.write(frame)
            current_frame += 1

            if current_frame % 50 == 0:
                print(f"Pipeline Progress: Frame {current_frame}/{total_frames} ({int(current_frame/total_frames*100)}%)")

            if update_progress_callback and current_frame % max(1, total_frames // 20) == 0:
                update_progress_callback(int((current_frame / total_frames) * 100))

        cap.release()
        out.release()

        # Save JSON metrics alongside the video
        try:
            metrics = {
                "max_ball_speed":   round(max_ball_speed, 1),
                "possession":       possession_stats,
                "player_speeds":    {str(k): round(v, 1) for k, v in player_max_speeds.items() if v > 0},
                "player_distances": {str(k): round(v, 1) for k, v in player_distances.items()  if v > 0},
            }
            json_path = output_path.rsplit('.', 1)[0] + "_metrics.json"
            with open(json_path, 'w') as f:
                json.dump(metrics, f)
        except Exception as e:
            print(f"Failed to generate JSON metrics: {e}")

        print(f"Video processing finished in {time.time() - start_time:.2f}s.")

    # ─────────────────────────────────────────────────────────────────────────
    def _dummy_process(self, input_path, output_path, update_progress_callback):
        """Fallback when ultralytics is not installed."""
        print("Ultralytics not installed. Running dummy processing.")
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise Exception("Cannot open video file")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 100
        fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
        w   = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h   = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        try:
            fourcc = cv2.VideoWriter_fourcc(*'avc1')
            out = cv2.VideoWriter(output_path, fourcc, fps, (w, h))
            if not out.isOpened():
                raise Exception("avc1 failed")
        except:
            print("Warning: avc1 initialization failed. mp4v may not play in web browsers. Please install openh264.")
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(output_path, fourcc, fps, (w, h))

        current_frame = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            overlay = frame.copy()
            cv2.rectangle(overlay, (50, 50), (450, 150), (255, 255, 255), -1)
            cv2.addWeighted(overlay, 0.4, frame, 0.6, 0, frame)
            cv2.putText(frame, "AI Pipeline Not Installed", (70, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            cv2.putText(frame, "Run: pip install ultralytics", (70, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
            out.write(frame)
            current_frame += 1
            if update_progress_callback and current_frame % max(1, total_frames // 20) == 0:
                update_progress_callback(int((current_frame / total_frames) * 100))

        cap.release()
        out.release()

    # ─────────────────────────────────────────────────────────────────────────
    def generate_live_frames(self):
        """MJPEG generator from server webcam (requires server-side camera hardware)."""
        if YOLO is None:
            cap = cv2.VideoCapture(0)
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                cv2.putText(frame, "AI Pipeline Not Installed", (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                _, buffer = cv2.imencode('.jpg', frame)
                yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n'
            cap.release()
            return

        self.initialize_model()
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("Cannot open webcam 0")
            return

        player_tracks = {}

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            current_time = time.time()
            results = self.model.track(
                frame, persist=True, classes=[0, 32],
                tracker="bytetrack.yaml", verbose=False
            )

            if len(results) > 0 and results[0].boxes:
                boxes     = results[0].boxes.xyxy.cpu().numpy()
                track_ids = results[0].boxes.id
                if track_ids is not None:
                    track_ids = track_ids.int().cpu().numpy()
                else:
                    track_ids = []
                clss = results[0].boxes.cls.int().cpu().numpy()

                for box, track_id, cls in zip(boxes, track_ids, clss):
                    x1, y1, x2, y2 = map(int, box)
                    cx, cy = int((x1+x2)/2), int(y2)

                    if track_id not in player_tracks:
                        player_tracks[track_id] = []
                    player_tracks[track_id].append((cx, cy, current_time))
                    if len(player_tracks[track_id]) > 10:
                        player_tracks[track_id] = player_tracks[track_id][-10:]

                    speed_text = ""
                    if len(player_tracks[track_id]) > 5:
                        p1, p2    = player_tracks[track_id][-5], player_tracks[track_id][-1]
                        time_diff = p2[2] - p1[2]
                        if time_diff > 0:
                            dist       = np.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)
                            speed_text = f" {min((dist/time_diff)/50, 35):.1f}km/h"

                    color = (0, 255, 0) if cls == 0 else (0, 0, 255)
                    label = f"ID:{track_id}{speed_text}" if cls == 0 else "Ball"
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                    cv2.rectangle(frame, (x1, y1-25), (x1+w, y1), (0, 0, 0), -1)
                    cv2.putText(frame, label, (x1, y1-8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            _, buffer = cv2.imencode('.jpg', frame)
            yield b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n'

        cap.release()
