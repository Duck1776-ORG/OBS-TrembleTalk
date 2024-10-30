import obspython as obs
import pyaudio
import numpy as np
import time
import math
from threading import Thread, Event

# Global variables
source_name = "Media Source"
threshold = 85
silence_duration = 0.30
last_audio_time = 0
video_playing = False
volume_db = 0
shake_thread = None
stop_thread = None
is_shaking_enabled = False
original_pos = None
amplitude = 0
target_scenes = []

# PyAudio setup
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

p = pyaudio.PyAudio()
stream = None

def script_description():
    print("Made for you.")
    print("Credit to Duck1776 | Clay | R3DCLAY")
    return """
    CHRIST IS KING

    Python 3.11.9
    OBS Studio 30.2.3

    Talking into your mic at a normal voice will cause a video source to play.

    The louder you talk, the more the video shakes.

    Audio is captured through PyAudio from your computer. Anything that is an input device is registered for input.

    You must fill out the box below, on the main OBS view, in the Sources section, add your Media Source. Whatever you name that source needs to go into this box.
    """

def script_update(settings):
    global source_name, silence_duration, target_scenes
    source_name = obs.obs_data_get_string(settings, "video_source")
    silence_duration = obs.obs_data_get_double(settings, "silence_duration")
    target_scenes = [
        obs.obs_data_get_string(settings, f"target_scene_{i}") 
        for i in range(1, 5) 
        if obs.obs_data_get_string(settings, f"target_scene_{i}")
    ]

def script_properties():
    props = obs.obs_properties_create()
    obs.obs_properties_add_text(props, "video_source", "Media Source", obs.OBS_TEXT_DEFAULT)    
    obs.obs_properties_add_button(props, "toggle_button", "Toggle Shake Effect", toggle_button_clicked)
    for i in range(1, 5):
        obs.obs_properties_add_text(props, f"target_scene_{i}", f"Target Scene {i}", obs.OBS_TEXT_DEFAULT)
    return props

def script_load(settings):
    global stream
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)
    obs.timer_add(check_audio, 100)

def script_unload():
    global stream, shake_thread, stop_thread, is_shaking_enabled, original_pos
    if stream:
        stream.stop_stream()
        stream.close()
    p.terminate()
    if is_shaking_enabled and stop_thread:
        stop_thread.set()
        shake_thread.join()
    shake_thread = None
    stop_thread = None
    is_shaking_enabled = False
    original_pos = None

def check_audio():
    global last_audio_time, video_playing, amplitude, threshold
    if not is_current_scene_target():
        return
    try:
        data = np.frombuffer(stream.read(CHUNK), dtype=np.int16)
        volume_norm = np.linalg.norm(data) * 10
        volume_db = 20 * math.log10(volume_norm) if volume_norm > 0 else -100
        if volume_db > threshold:
            if not is_shaking_enabled:
                amplitude = 0
            else:
                if volume_db >= 110:
                    amplitude = (volume_db - 110) / (120 - 110) * 60
                elif volume_db >= 85:
                    amplitude = 0
                else:
                    amplitude = 0
            last_audio_time = time.time()
            if not video_playing:
                play_video()
        elif video_playing and (time.time() - last_audio_time) > silence_duration:
            stop_video()
    except Exception as e:
        print(f"Error reading audio: {e}")

def is_current_scene_target():
    current_scene = obs.obs_frontend_get_current_scene()
    current_scene_name = obs.obs_source_get_name(current_scene)
    obs.obs_source_release(current_scene)
    return current_scene_name in target_scenes

def play_video():
    global video_playing
    if not is_current_scene_target():
        return
    source = obs.obs_get_source_by_name(source_name)
    if source is not None:
        obs.obs_source_media_set_time(source, 0)
        obs.obs_source_media_play_pause(source, False)
        video_playing = True
        if is_shaking_enabled:
            play_shake()
    else:
        print(f"Error: Video source '{source_name}' not found")

def stop_video():
    global video_playing
    if not is_current_scene_target():
        return
    source = obs.obs_get_source_by_name(source_name)
    if source is not None:
        obs.obs_source_media_play_pause(source, True)
        obs.obs_source_media_set_time(source, 0)
        video_playing = False
        if is_shaking_enabled:
            stop_shake()
    else:
        print(f"Error: Video source '{source_name}' not found")

def shake_image():
    global stop_thread, original_pos
    if not is_current_scene_target():
        return
    source = obs.obs_get_source_by_name(source_name)
    if source is not None:
        try:
            current_scene = obs.obs_frontend_get_current_scene()
            scene = obs.obs_scene_from_source(current_scene)
            scene_item = obs.obs_scene_find_source(scene, source_name)
            if scene_item:
                if original_pos is None:
                    pos = obs.vec2()
                    obs.obs_sceneitem_get_pos(scene_item, pos)
                    original_pos = (pos.x, pos.y)
                start_time = time.time()
                while not stop_thread.is_set():
                    if not is_current_scene_target():
                        break
                    current_time = time.time() - start_time
                    offset_x = amplitude * math.sin(current_time * 30)
                    offset_y = amplitude * math.cos(current_time * 25)
                    pos = obs.vec2()
                    pos.x = original_pos[0] + offset_x
                    pos.y = original_pos[1] + offset_y
                    obs.obs_sceneitem_set_pos(scene_item, pos)
                    time.sleep(1/60)
                pos = obs.vec2()
                pos.x = original_pos[0]
                pos.y = original_pos[1]
                obs.obs_sceneitem_set_pos(scene_item, pos)
        finally:
            obs.obs_source_release(source)
            obs.obs_source_release(current_scene)
    else:
        print(f"Source '{source_name}' not found")

def play_shake():
    global shake_thread, stop_thread
    if not is_current_scene_target():
        return
    source = obs.obs_get_source_by_name(source_name)
    if source is not None:
        stop_thread = Event()
        shake_thread = Thread(target=shake_image)
        shake_thread.daemon = True
        shake_thread.start()
    else:
        print(f"error starting shake")

def stop_shake():
    global shake_thread, stop_thread
    if not is_current_scene_target():
        return
    source = obs.obs_get_source_by_name(source_name)
    if source is not None:
        stop_thread.set()
        shake_thread.join()
        stop_thread = None
        shake_thread = None
    else:
        print(f"error stopping shake")

def toggle_button_clicked(props, prop):
    global is_shaking_enabled
    is_shaking_enabled = not is_shaking_enabled
    print(f"Shake effect {'enabled' if is_shaking_enabled else 'disabled'}")
    return True