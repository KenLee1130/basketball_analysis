"""
A module for reading and writing video files.

This module provides utility functions to load video frames into memory and save
processed frames back to video files, with support for common video formats.
"""

import cv2
import os
import shutil
import subprocess

def read_video(video_path):
    """
    Read all frames from a video file into memory.

    Args:
        video_path (str): Path to the input video file.

    Returns:
        list: List of video frames as numpy arrays.
    """
    cap = cv2.VideoCapture(video_path)
    frames = []
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frames.append(frame)
    return frames

def save_video(ouput_video_frames,output_video_path):
    """
    Save a sequence of frames as a video file.

    Creates necessary directories if they don't exist and writes frames using
    a codec that matches the requested output file extension.

    Args:
        ouput_video_frames (list): List of frames to save.
        output_video_path (str): Path where the video should be saved.
    """
    if not ouput_video_frames:
        raise ValueError("No frames were provided to save_video.")

    output_video_path = os.path.abspath(output_video_path)
    output_dir = os.path.dirname(output_video_path)

    # If folder doesn't exist, create it
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    _, extension = os.path.splitext(output_video_path)
    extension = extension.lower()
    width = ouput_video_frames[0].shape[1]
    height = ouput_video_frames[0].shape[0]

    if extension == '.mp4':
        base_path, _ = os.path.splitext(output_video_path)
        temp_output_path = base_path + ".tmp.avi"
        codec = 'XVID'
        final_output_path = temp_output_path
    else:
        codec = 'XVID'
        final_output_path = output_video_path

    fourcc = cv2.VideoWriter_fourcc(*codec)
    out = cv2.VideoWriter(
        final_output_path,
        fourcc,
        24,
        (width, height),
    )

    if not out.isOpened():
        raise RuntimeError(
            f"Could not open video writer for '{final_output_path}' using codec '{codec}'."
        )

    for frame in ouput_video_frames:
        out.write(frame)
    out.release()

    if extension == '.mp4':
        ffmpeg_path = shutil.which("ffmpeg")
        if ffmpeg_path is None:
            if os.path.exists(temp_output_path):
                os.replace(temp_output_path, output_video_path)
            raise RuntimeError(
                "ffmpeg is required to produce H.264 MP4 output but was not found on PATH."
            )

        command = [
            ffmpeg_path,
            "-y",
            "-i", temp_output_path,
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-an",
            output_video_path,
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        if os.path.exists(temp_output_path):
            os.remove(temp_output_path)

        if result.returncode != 0:
            raise RuntimeError(
                "ffmpeg failed to convert the intermediate AVI to H.264 MP4:\n"
                f"{result.stderr}"
            )
