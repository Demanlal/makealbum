import os, subprocess, uuid
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.http import FileResponse, HttpResponse
from .models import Album, Photo


def generate_ultra_cinematic(request, album_id):

    album = get_object_or_404(Album, id=album_id)
    photos = list(Photo.objects.filter(album=album))

    if not photos:
        return HttpResponse("No photos found")

    # ================= USER INPUT (NEW) =================
    if request.method == "POST":
        selected_bg = request.POST.get("bgvideo")
        selected_music = request.POST.get("music")

        bg_file = request.FILES.get("bg_upload")
        music_file = request.FILES.get("music_upload")
    else:
        return HttpResponse("❌ Use POST method")

    # folders ensure
    bg_folder = os.path.join(settings.MEDIA_ROOT, "background")
    music_folder = os.path.join(settings.MEDIA_ROOT, "music")

    os.makedirs(bg_folder, exist_ok=True)
    os.makedirs(music_folder, exist_ok=True)

    # ================= BACKGROUND LOGIC =================
    bg = None

    if bg_file:
        filename = str(uuid.uuid4()) + "_" + bg_file.name
        bg_path = os.path.join(bg_folder, filename)

        with open(bg_path, "wb+") as f:
            for chunk in bg_file.chunks():
                f.write(chunk)

        bg = bg_path

    elif selected_bg:
        bg = os.path.join(bg_folder, selected_bg)

    else:
        return HttpResponse("❌ Please select or upload background")

    # ================= MUSIC LOGIC =================
    music = None

    if music_file:
        filename = str(uuid.uuid4()) + "_" + music_file.name
        music_path = os.path.join(music_folder, filename)

        with open(music_path, "wb+") as f:
            for chunk in music_file.chunks():
                f.write(chunk)

        music = music_path

    elif selected_music:
        music = os.path.join(music_folder, selected_music)

    # ================= FRAMES =================
    work_dir = os.path.join(settings.MEDIA_ROOT, "video_frames", str(album.id))
    os.makedirs(work_dir, exist_ok=True)

    frames = []

    for i, p in enumerate(photos):
        if not p.image or not os.path.exists(p.image.path):
            continue

        path = os.path.join(work_dir, f"img_{i:03}.jpg")

        with open(p.image.path, "rb") as src:
            with open(path, "wb") as dst:
                dst.write(src.read())

        frames.append(path)

    if not frames:
        return HttpResponse("❌ No valid images found")

    # ================= EXTRA ASSETS =================
    light = os.path.join(bg_folder, "light.mp4")
    grain = os.path.join(bg_folder, "grain.mp4")

    use_bg = bg and os.path.exists(bg)
    use_light = os.path.exists(light)
    use_grain = os.path.exists(grain)
    use_music = music and os.path.exists(music)

    output = os.path.join(settings.MEDIA_ROOT, f"ultra_album_{album.id}.mp4")

    # ================= INPUTS =================
    inputs = []

    for img in frames:
        inputs += ["-loop", "1", "-t", "4", "-i", img]

    if use_bg:
        inputs += ["-stream_loop", "-1", "-i", bg]

    if use_light:
        inputs += ["-stream_loop", "-1", "-i", light]

    if use_grain:
        inputs += ["-stream_loop", "-1", "-i", grain]

    if use_music:
        inputs += ["-i", music]

    filters = []

    # 👉 STEP 1: SMALL CARD (sheet size)
    #for i in range(len(frames)):
    # for i in range(0, len(frames), 2):
    #     filters.append(
    #         f"[{i}:v]"
    #         "scale=1400:-1,"
    #         "zoompan=z='min(zoom+0.0007,1.3)':d=125:s=700x500,"
    #         "fade=t=in:st=0:d=1,"
    #         "fade=t=out:st=3:d=1"
    #         f"[v{i}]"
    #     )
    for i in range(0, len(frames), 2):
        filters.append(f"[{i}:v]scale=640:720[left{i}]")
        filters.append(f"[{i + 1}:v]scale=640:720[right{i}]")
        filters.append(f"[left{i}][right{i}]hstack=inputs=2[slide{i}]")

    # 👉 STEP 2: TRANSITIONS
    # current = "[v0]"
    # offset = 3
    #
    # for i in range(1, len(frames)):
    #     filters.append(
    #         f"{current}[v{i}]"
    #         f"xfade=transition=fade:duration=1:offset={offset}"
    #         f"[v{i}out]"
    #     )
    #     current = f"[v{i}out]"
    #     offset += 3
    current = "[slide0]"
    offset = 3

    for i in range(2, len(frames), 2):
        filters.append(
            f"{current}[slide{i}]xfade=transition=fade:duration=1:offset={offset}[out{i}]"
        )
        current = f"[out{i}]"
        offset += 3

    slideshow = current
    index = len(frames)

    # 👉 STEP 3: BACKGROUND BLUR
    if use_bg:
        filters.append(f"[{index}:v]scale=1280:720,boxblur=20:1[bg]")
        index += 1
    else:
        filters.append(f"{slideshow}null[bg]")

    # 👉 STEP 4: SHADOW EFFECT
    filters.append(
        f"{slideshow}format=rgba,boxblur=8:1,scale=720:520[shadow]"
    )

    filters.append(
        f"[bg][shadow]overlay=(W-w)/2+15:(H-h)/2+15[tmpbg]"
    )

    # 👉 STEP 5: CENTER CARD
    filters.append(
        f"[tmpbg]{slideshow}overlay=(W-w)/2:(H-h)/2[base]"
    )

    current = "[base]"

    # 👉 STEP 6: LIGHT
    if use_light:
        filters.append(
            f"[{index}:v]scale=1280:720,format=rgba,colorchannelmixer=aa=0.25[light]"
        )
        filters.append(f"{current}[light]overlay=0:0[tmp1]")
        current = "[tmp1]"
        index += 1

    # 👉 STEP 7: GRAIN
    if use_grain:
        filters.append(
            f"[{index}:v]scale=1280:720,format=rgba,colorchannelmixer=aa=0.12[grain]"
        )
        filters.append(f"{current}[grain]overlay=0:0[v]")
    else:
        filters.append(f"{current}null[v]")

    # 👉 FINAL
    filter_complex = ";".join(filters)

    # ================= COMMAND =================
    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
    ]

    if use_music:
        audio_index = len([x for x in inputs if x == "-i"]) - 1
        cmd += ["-map", f"{audio_index}:a", "-c:a", "aac", "-shortest"]

    cmd.append(output)

    print(" ".join(cmd))

    subprocess.run(cmd)

    if not os.path.exists(output):
        return HttpResponse("❌ Video render failed")

    return FileResponse(
        open(output, "rb"),
        as_attachment=True,
        filename=f"album_{album.id}.mp4",
        content_type="video/mp4"
    )