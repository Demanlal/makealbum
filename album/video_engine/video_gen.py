import os, subprocess
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.http import FileResponse, HttpResponse
from .models import Album, Photo


def generate_ultra_cinematic(request, album_id):

    album = get_object_or_404(Album, id=album_id)
    photos = list(Photo.objects.filter(album=album))

    if not photos:
        return HttpResponse("No photos found")

    work_dir = os.path.join(settings.MEDIA_ROOT, "video_frames", str(album.id))
    # os.makedirs(work_dir, exist_ok=True)
    os.makedirs(settings.MEDIA_ROOT, exist_ok=True)

    frames = []
    for i, p in enumerate(photos):
        path = os.path.join(work_dir, f"img_{i:03}.jpg")
        with open(p.image.path, "rb") as src, open(path, "wb") as dst:
            dst.write(src.read())
        frames.append(path)

    # 🎵 MUSIC (latest)
    music_dir = os.path.join(settings.MEDIA_ROOT, "music")
    music = None
    if os.path.isdir(music_dir):
        mp3s = sorted(
            [f for f in os.listdir(music_dir) if f.endswith(".mp3")],
            key=lambda x: os.path.getctime(os.path.join(music_dir, x)),
            reverse=True
        )
        if mp3s:
            music = os.path.join(music_dir, mp3s[0])

    # 🎬 assets
    bg = os.path.join(settings.MEDIA_ROOT, "background", "bg.mp4")
    light = os.path.join(settings.MEDIA_ROOT, "background", "light.mp4")
    grain = os.path.join(settings.MEDIA_ROOT, "background", "grain.mp4")

    use_bg = os.path.exists(bg)
    use_light = os.path.exists(light)
    use_grain = os.path.exists(grain)

    # output = os.path.join(settings.MEDIA_ROOT, f"ultra_album_{album.id}.mp4")
    output = os.path.join(
        settings.MEDIA_ROOT,
        f"ultra_album_{album.id}.mp4"
    )
    # ================= INPUTS =================
    inputs = []
    for img in frames:
        inputs += ["-loop", "1", "-t", "4", "-i", img]

    # inputs += ["-i", bg, "-i", light, "-i", grain]
    #inputs += ["-stream_loop", "-1", "-i", bg]
    inputs += ["-stream_loop", "-1", "-i", bg]

    if use_light:
        inputs += ["-stream_loop", "-1", "-i", light]

    if use_grain:
        inputs += ["-stream_loop", "-1", "-i", grain]

    if music:
        inputs += ["-i", music]
    # if music:
    #     audio_index = len(inputs) // 2  # current input number
    #     inputs += ["-i", music]

    # ================= FILTERS =================
    filters = []

    for i in range(len(frames)):
        filters.append(
            f"[{i}:v]"
            "scale=1400:-1,"
            "zoompan=z='min(zoom+0.0007,1.3)':d=125:s=1280x720,"
            "fade=t=in:st=0:d=1,"
            "fade=t=out:st=3:d=1"
            f"[v{i}]"
        )

    # current = "[v0]"
    # for i in range(1, len(frames)):
    #     filters.append(
    #         f"{current}[v{i}]"
    #         f"xfade=transition=fade:duration=1:offset=3"
    #         f"[v{i}out]"
    #     )
    #     current = f"[v{i}out]"
    current = "[v0]"
    offset = 3  # first transition

    for i in range(1, len(frames)):
        filters.append(
            f"{current}[v{i}]"
            f"xfade=transition=fade:duration=1:offset={offset}"
            f"[v{i}out]"
        )
        current = f"[v{i}out]"
        offset += 3  # next transition time

    slideshow = current
    #
    # bg_i = len(frames)
    # light_i = len(frames) + 1
    # grain_i = len(frames) + 2
    bg_i = len(frames)
    next_index = bg_i + 1

    if use_light:
        light_i = next_index
        next_index += 1

    if use_grain:
        grain_i = next_index

    # background resize
    filters.append(f"[{bg_i}:v]scale=1280:720[bg]")

    if use_light:
        filters.append(
            f"[{light_i}:v]scale=1280:720,format=rgba,colorchannelmixer=aa=0.25[light]"
        )

    if use_grain:
        filters.append(
            f"[{grain_i}:v]scale=1280:720,format=rgba,colorchannelmixer=aa=0.15[grain]"
        )

    # base overlay
    filters.append(f"[bg]{slideshow}overlay=(W-w)/2:(H-h)/2[base]")

    current = "[base]"

    if use_light:
        filters.append(f"{current}[light]overlay=0:0[tmp1]")
        current = "[tmp1]"

    if use_grain:
        filters.append(f"{current}[grain]overlay=0:0[v]")
    else:
        filters.append(f"{current}null[v]")

    # filters.append(f"[{bg_i}:v]scale=1280:720[bg]")
    # filters.append(f"[{light_i}:v]scale=1280:720,format=rgba,colorchannelmixer=aa=0.25[light]")
    # filters.append(f"[{grain_i}:v]scale=1280:720,format=rgba,colorchannelmixer=aa=0.15[grain]")
    #
    # # filters.append(f"[bg]{slideshow}overlay=(W-w)/2:(H-h)/2[base]")
    # # filters.append(f"[base][light]overlay=0:0[lighted]")
    # filters.append(f"[bg]{slideshow}overlay=(W-w)/2:(H-h)/2[base]")
    # filters.append(f"[base][light]overlay=0:0[lighted]")
    # filters.append(f"[lighted][grain]overlay=0:0[v]")

    # 🔥 FINAL VIDEO LABEL MUST BE [v]
    #filters.append(f"[lighted][grain]overlay=0:0[v]")
    # filters.append(f"[lighted][grain]overlay=0:0[v]")

    filter_complex = ";".join(filters)

    print("BG exists:", os.path.exists(bg))
    print("Light exists:", os.path.exists(light))
    print("Grain exists:", os.path.exists(grain))
    print("Music exists:", os.path.exists(music) if music else None)

    audio_index = None



    # ================= COMMAND =================
    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[v]"
    ]

    # if music:
    #     cmd += ["-map", f"{len(frames)+3}:a"]
    # cmd += ["-map", "[v]"]

    # if audio_index is not None:
    #     cmd += ["-map", f"{audio_index}:a"]
    # cmd += ["-map", "[v]"]
    #
    # if audio_index is not None:
    #     cmd += ["-map", f"{audio_index}:a"]
    # cmd += ["-map", "[v]"]

    if audio_index is not None:
        cmd += ["-map", f"{audio_index}:a"]

    # if music:
    #     audio_index = len(frames) + 1
    #     if use_light:
    #         audio_index += 1
    #     if use_grain:
    #         audio_index += 1
    #
    #     cmd += ["-map", f"{audio_index}:a"]

    # cmd += [
    #     "-c:v", "libx264",
    #     "-preset", "slow",
    #     "-crf", "18",
    #     "-pix_fmt", "yuv420p",
    #     "-c:a", "aac",
    #     "-shortest",
    #     output
    # ]
    audio_index = len(frames) + 1
    # cmd += [
    #     "-map", "[v]",
    #     "-map", f"{audio_index}:a",
    #     "-c:v", "libx264",
    #     "-preset", "slow",
    #     "-crf", "18",
    #     "-pix_fmt", "yuv420p",
    #     "-c:a", "aac",
    #     "-shortest",
    #     output
    # ]
    # music add (LAST INPUT)
    # inputs.extend(["-i", music])

    # =========================
    # DYNAMIC AUDIO INDEX
    # =========================
    total_inputs = len([x for x in inputs if x == "-i"])
    audio_index = total_inputs - 1

    map_audio = f"{audio_index}:a"
    # cmd += [
    #     "-map", "[v]",
    #     "-map", f"{audio_index}:a",
    #     "-c:v", "libx264",
    #     "-preset", "slow",
    #     "-crf", "18",
    #     "-pix_fmt", "yuv420p",
    #     "-c:a", "aac",
    #     "-shortest",
    #     output
    # ]
    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-map", map_audio,
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-shortest",
        output
    ]

    print(" ".join(cmd))  # debug
    # subprocess.run(cmd, check=True)
    # result = subprocess.run(cmd, capture_output=True, text=True)
    # print(result.stderr)
    # result = subprocess.run(cmd, capture_output=True, text=True)
    #
    # print("STDOUT:", result.stdout)
    # print("STDERR:", result.stderr)
    result = subprocess.run(cmd, capture_output=True, text=True)

    print("STDERR:", result.stderr)
    print("RETURN CODE:", result.returncode)

    if not os.path.exists(output):
        print("Video not ready yet")
        return HttpResponse("Video render failed — check ffmpeg error")

    # return FileResponse(open(output, "rb"), content_type="video/mp4")

    return FileResponse(
        open(output, "rb"),
        as_attachment=True,
        filename=f"album_{album.id}.mp4",
        content_type="video/mp4"
    )
