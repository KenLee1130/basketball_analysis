# 🏀 Basketball Video Analysis

Analyze basketball footage with automated detection of players, ball, team assignment, and more. This repository integrates object tracking, zero-shot classification, and custom keypoint detection for a fully annotated basketball game experience.

Leveraging the convenience of Roboflow for dataset management and Ultralytics' YOLO models for both training and inference, this project provides a robust framework for basketball video analysis.

Training notebooks are included to help you customize and fine-tune models to suit your specific needs, ensuring a seamless and efficient workflow.

## 📁 Table of Contents

1.  [Features](#-features)
2.  [Prerequisites](#-prerequisites)
3.  [Demo Video](#-demo-video)
4.  [Installation](#-installation)
5.  [Training the Models](#-training-the-models)
6.  [Usage](#-usage)
7.  [Project Structure](#-project-structure)
8.  [Future Work](#-future-work)
9.  [Contributing](#-contributing)
10. [License](#-license)

---

## ✨ Features

- Player and ball detection/tracking using pretrained models.
- Court keypoint detection for visualizing important zones.
- Team assignment with jersey color classification.
- Ball possession detection, pass detection, and interception detection.
- Easy stubbing to skip repeated computation for fast iteration.
- Various “drawers” to overlay detected elements onto frames.

---

## 🎮 Demo Video

Below is the final annotated output video.

[![BasketBall Analysis Demo Video](https://img.youtube.com/vi/xWpP0LjEUng/0.jpg)](https://youtu.be/xWpP0LjEUng)

## 🔧 Prerequisites

- Python 3.9-3.11
- (Optional) Docker

---

## ⚙️ Installation

Setup your environment locally or via Docker.

### Python Environment

1. Create a virtual environment with Python 3.9-3.11 (conda is a convenient option on Ubuntu 24.04+).
2. Install PyTorch first for your platform and hardware.
3. Install the remaining runtime dependencies:

```bash
pip install -r requirements.txt
```

If you already have a working `torch` installation in your environment, `requirements.txt` will keep it and install the rest of the packages around it.

Example with conda:

```bash
conda create -n basketball python=3.11 -y
conda activate basketball
python -m pip install -U pip setuptools wheel
# Install a torch build that matches your platform/GPU first.
pip install -r requirements.txt
```

`requirements.txt` is the runtime/inference environment. Roboflow is intentionally excluded from this file because it pins a separate `opencv-python-headless` build that conflicts with the OpenCV package used by the main application.

### Docker

#### Build the Docker image:

```bash
docker build -t basketball-analysis .
```

#### Verify the image:

```bash
docker images
```

## 🎓 Training the Models

Harnessing the powerful tools offered by Roboflow and Ultralytics makes it straightforward to manage datasets, handle annotations, and train advanced object detection models. Roboflow provides an intuitive platform for dataset preprocessing and augmentation, while Ultralytics’ YOLO architectures (v5, v8, and beyond) deliver state-of-the-art detection performance.

This repository relies on trained models for detecting basketballs, players, and court keypoints. You have two options to get these models:

1. Download the Pretrained Weights

   - ball_detector_model.pt  
     (https://drive.google.com/file/d/1KejdrcEnto2AKjdgdo1U1syr5gODp6EL/view?usp=sharing)
   - court_keypoint_detector.pt  
     (https://drive.google.com/file/d/1nGoG-pUkSg4bWAUIeQ8aN6n7O1fOkXU0/view?usp=sharing)
   - player_detector.pt  
     (https://drive.google.com/file/d/1fVBLZtPy9Yu6Tf186oS4siotkioHBLHy/view?usp=sharing)

   Simply download these files and place them into the `models/` folder in your project. This allows you to run the pipelines without manually retraining.

2. Train Your Own Models  
   The training scripts are provided in the `training_notebooks/` folder. These Jupyter notebooks use Roboflow datasets and the Ultralytics YOLO frameworks to train various detection tasks:

   - `basketball_ball_training.ipynb`: Trains a basketball ball detector (using YOLOv5). Incorporates motion blur augmentations to improve ball detection accuracy on fast-moving game footage.
   - `basketball_court_keypoint_training.ipynb`: Uses YOLOv8 to detect keypoints on the court (e.g., lines, corners, key zones).
   - `basketball_player_detection_training.ipynb`: Trains a player detection model (using YOLO v11) to identify players in each frame.

   You can easily run these notebooks in Google Colab or another environment with GPU access. If you want a dedicated local notebook/training environment, install the training-specific dependency set in a separate environment:

```bash
pip install -r requirements-training.txt
```

   Keeping training dependencies separate avoids `opencv-python` vs. `opencv-python-headless` conflicts in the main runtime environment. After training, download the newly generated `.pt` files and place them in the `models/` folder.

## Once you have your models in place, you may proceed with the usage steps described above. If you want to retrain or fine-tune for your specific dataset, remember to adjust the paths in the notebooks and in `main.py` to point to the newly generated models.

## 🚀 Usage

You can run this repository’s core functionality (analysis pipeline) with Python or Docker.

### 1) Using Python Directly

Run the main entry point with your chosen video file:

```bash
python main.py path_to_input_video.mp4 --output_video output_videos/output_result.mp4
```

- By default, intermediate “stubs” (pickled detection results) are used if found, allowing you to skip repeated detection/tracking.
- Use the `--stub_path` flag to specify a custom stub folder, or disable stubs if you want to run everything fresh.

### 1.5) Download and Segment Full-Game Videos

If you want to prepare YouTube full-game footage before analysis, this repository now includes a small CLI under `full_game/`.

Install the two external tools first:

```bash
sudo apt install ffmpeg
python -m pip install -U "yt-dlp[default]"
```

If your system `yt-dlp` comes from Ubuntu packages, it may be too old for current YouTube extraction. The safest route is to install the latest official release in your user path:

```bash
mkdir -p ~/.local/bin
curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o ~/.local/bin/yt-dlp
chmod a+rx ~/.local/bin/yt-dlp
hash -r
yt-dlp --version
```

Recent YouTube support also benefits from a JavaScript runtime. `node` or `deno` works; if one is on your `PATH`, the `full_game` downloader will try to use it automatically with newer `yt-dlp` releases.

Download a single YouTube video at a target resolution:

```bash
python -m full_game download \
  --url "https://www.youtube.com/watch?v=YOUR_VIDEO_ID" \
  --resolution 720
```

- `--resolution best` keeps the highest quality available.
- Downloaded files default to `full_game/downloads/`.
- If a video needs authentication or age verification, add `--cookies-from-browser chrome` or another supported browser.

Cut a local clip by start and end time:

```bash
python -m full_game segment \
  --input full_game/downloads/your_video.mp4 \
  --start 00:10:00 \
  --end 00:12:30
```

- Time accepts `seconds`, `MM:SS`, or `HH:MM:SS`.
- Segments default to `full_game/segments/` and are encoded as H.264 MP4 for easier playback.
- Use `--output path/to/clip.mp4` if you want to control the filename directly.

Then feed the clip into the analysis pipeline:

```bash
python main.py full_game/segments/your_clip.mp4 --output_video output_videos/your_clip_result.mp4
```

### 2) Using Docker

#### Build the container if not built already:

```bash
docker build -t basketball-analysis .
```

#### Run the container, mounting your local input video folder:

```bash
docker run \
  -v $(pwd)/videos:/app/videos \
  -v $(pwd)/output_videos:/app/output_videos \
  basketball-analysis \
  python main.py videos/input_video.mp4 --output_video output_videos/output_result.mp4
```

---

## 🏰 Project Structure

- `main.py`  
  – Orchestrates the entire pipeline: reading video frames, running detection/tracking, team assignment, drawing results, and saving the output video.

- `trackers/`  
  – Houses `PlayerTracker` and `BallTracker`, which use detection models to generate bounding boxes and track objects across frames.

- `utils/`  
  – Contains helper functions like `bbox_utils.py` for geometric calculations, `stubs_utils.py` for reading and saving intermediate results, and `video_utils.py` for reading/saving videos.

- `drawers/`  
  – Contains classes that overlay bounding boxes, court lines, passes, etc., onto frames.

- `ball_aquisition/`  
  – Logic for identifying which player is in possession of the ball.

- `pass_and_interception_detector/`  
  – Identifies passing events and interceptions.

- `court_keypoint_detector/`  
  – Detects lines and keypoints on the court using the specified model.

- `team_assigner/`  
  – Uses zero-shot classification (Hugging Face or similar) to assign players to teams based on jersey color.

- `configs/`  
  – Holds default paths for models, stubs, and output video.

---

## 🔮 Future Work

As we continue to enhance the capabilities of this basketball video analysis tool, several areas for future development have been identified:

1. **Integrating a Pose Model for Advanced Rule Detection**  
   Incorporating a pose detection model could enable the identification of complex basketball rules such as double dribbling and traveling. By analyzing player movements and positions, the system could automatically flag these infractions, adding another layer of analysis to the video footage.

These enhancements will further refine the analysis capabilities and provide users with more comprehensive insights into basketball games.

## 🤝 Contributing

Contributions are welcome!

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Submit a pull request with a clear explanation of your changes.

---

## 🐜 License

This project is licensed under the MIT License.  
See `LICENSE` for details.

---

## 💬 Questions or Feedback?

Feel free to open an issue or reach out via email if you have questions about the project, suggestions for improvements, or just want to say hi!

Enjoy analyzing basketball footage with automatic detection and tracking!
