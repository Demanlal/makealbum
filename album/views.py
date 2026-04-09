import io
import os
import subprocess
import uuid
import random
import zipfile
from io import BytesIO

import qrcode

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.core.mail import send_mail
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .forms import AlbumRequestForm, RegisterForm, LoginForm
from .models import Photo, UserProfile, Album, Video




def album_list(request):
    albums = Album.objects.all().order_by('-created_at')
    return render(request, 'create_albums2.html', {'albums': albums})



@staff_member_required
def approve_albums(request):
    albums = Album.objects.all().order_by('-created_at')

    if request.method == 'POST':
        album_id = request.POST.get('album_id')
        action = request.POST.get('action')

        album = get_object_or_404(Album, id=album_id)

        if action == 'approve':
            album.status = 'APPROVED'
            album.save()

        elif action == 'reject':
            album.status = 'REJECTED'
            album.save()

        elif action == 'delete':
            album.delete()

        return redirect('approve-albums')

    return render(request, 'album_approve.html', {'albums': albums})


def request_album(request):
    if request.method == 'POST':
        form = AlbumRequestForm(request.POST)
        if form.is_valid():
            album = form.save(commit=False)
            album.created_by = request.user
            album.status = 'PENDING'
            album.save()

            # 🔹 Build album URL
            album_url = request.build_absolute_uri(
                reverse('album-detail', args=[album.id])
            )

            # 🔹 Generate QR
            qr_img = qrcode.make(album_url)
            buffer = io.BytesIO()
            qr_img.save(buffer, format='PNG')
            buffer.seek(0)

            # 🔹 Save QR to model field
            album.qr_code.save(
                f'album_{album.id}_qr.png',
                ContentFile(buffer.read()),
                save=True
            )

            return redirect('album-request-success')
    else:
        form = AlbumRequestForm()

    return render(request, 'request_album.html', {'form': form})

@staff_member_required
def edit_album(request, album_id):
    album = get_object_or_404(Album, id=album_id)

    if request.method == 'POST':
        album.title = request.POST.get('title')
        album.save()
        return redirect('approve-albums')

    return render(request, 'edit_album.html', {'album': album})

#@login_required
def album_detail(request, album_id):
    album = get_object_or_404(Album, id=album_id)
    photos = album.photos.filter(is_active=True)
    #videos = album.videos.filter(is_active=True)
    return render(request, 'album_details2.html', {
        'album': album,
        'photos': photos,
        #'videos': videos
    })


@login_required
def upload_media(request, album_id):

    album = get_object_or_404(Album, id=album_id)

    # 🔒 Owner check
    if album.created_by != request.user:
        messages.error(request, "You are not allowed to upload media to this album.")
        return render(request, 'album_details2.html', {'album': album})

    # 🔒 Approval check
    if album.status != 'APPROVED':
        messages.warning(request, "Album is not approved yet.")
        return render(request, 'album_details2.html', {'album': album})

    if request.method == 'POST':
        image = request.FILES.get('image')
        video = request.FILES.get('video')

        # 📷 IMAGE VALIDATION
        if image:
            if not image.content_type.startswith('image'):
                messages.error(request, "Invalid image format!")
            else:
                Photo.objects.create(
                    album=album,
                    image=image,
                    uploaded_by=request.user
                )
                messages.success(request, "Photo uploaded successfully!")

        # 🎬 VIDEO VALIDATION
        if video:
            if not video.content_type.startswith('video'):
                messages.error(request, "Invalid video format!")
            else:
                Video.objects.create(
                    album=album,
                    video=video,
                    uploaded_by=request.user
                )
                messages.success(request, "Video uploaded successfully!")

        # ❗ Agar dono empty ho
        if not image and not video:
            messages.warning(request, "Please select a file to upload.")

        return redirect('album-detail', album.id)

    return render(request, 'album_details2.html', {'album': album})

def download_photo(request, photo_id):
    photo = get_object_or_404(Photo, id=photo_id)
    return FileResponse(photo.image.open(), as_attachment=True)

def download_album(request, album_id):
    album = get_object_or_404(Album, id=album_id)
    buffer = io.BytesIO()
    zip_file = zipfile.ZipFile(buffer, 'w')

    for photo in album.photos.all():
        zip_file.write(photo.image.path, photo.image.name.split('/')[-1])

    zip_file.close()
    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{album.title}.zip"'
    return response

def download_selected_photos(request):
    photo_ids = request.POST.getlist('photo_ids')
    buffer = io.BytesIO()
    zip_file = zipfile.ZipFile(buffer, 'w')


    for photo in Photo.objects.filter(id__in=photo_ids):
        zip_file.write(photo.image.path, photo.image.name.split('/')[-1])

    zip_file.close()
    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename="selected_photos.zip"'
    return response

def animated_slideshow(request, album_id):
    album = get_object_or_404(
        Album,
        id=album_id,
        status='APPROVED'
    )

    photos = album.photos.filter(is_active=True)

    return render(request, 'animation.html', {
        'album': album,
        'photos': photos
    })



@login_required
def album_request_success(request):
    return render(request, 'album_request_success.html')



@staff_member_required
def delete_photo(request, photo_id):
    photo = get_object_or_404(Photo, id=photo_id)
    album_id = photo.album.id
    photo.delete()
    return redirect('album-detail', album_id=album_id)

def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.get_or_create(user=user)
            return redirect('login')
    else:
        form = RegisterForm()

    return render(request, 'register.html', {'form': form})
# def register(request):
#     if request.method == 'POST':
#         form = RegisterForm(request.POST)
#         if form.is_valid():
#
#             # ✅ Create user (ONLY ONCE)
#             user = form.save()
#
#             # ✅ Create user profile safely
#             UserProfile.objects.get_or_create(user=user)
#
#             # ✅ Send welcome email (dynamic receiver)
#             if user.email:   # safety check
#                 send_mail(
#                     'Welcome to Our App',
#                     'Your account has been created successfully.',
#                     settings.EMAIL_HOST_USER,
#                     [user.email],
#                     fail_silently=False,
#                 )
#
#             return redirect('login')
#     else:
#         form = RegisterForm()
#
#     return render(request, 'register.html', {'form': form})



@staff_member_required
def approve_users(request):
    if request.method == 'POST':
        profile_id = request.POST.get('profile_id')
        role = request.POST.get('role')

        profile = UserProfile.objects.get(id=profile_id)
        profile.role = role
        profile.is_approved = True
        profile.save()

        # Staff / Admin flag
        if role in ['ADMIN', 'STAFF']:
            profile.user.is_staff = True
            profile.user.save()

    users = UserProfile.objects.filter(is_approved=False)
    return render(request, 'user_approval.html', {'users': users})




def user_login(request):
    form = LoginForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        user = authenticate(
            request,
            username=form.cleaned_data['username'],
            password=form.cleaned_data['password']
        )

        if user:
            profile = user.userprofile

            if not profile.is_approved:
                messages.error(request, "Your account is not approved yet.")
                return redirect('login')

            login(request, user)

            album = Album.objects.filter(status='APPROVED').first()

            if album:
                return redirect('album-list')
            else:
                messages.error(request, "No approved album found")
                return redirect('album-list')

        messages.error(request, "Invalid username or password")

    return render(request, 'login.html', {'form': form})



@staff_member_required
def approved_users(request):
    users = UserProfile.objects.filter(is_approved=True).exclude(role='PENDING')
    return render(request, 'approved_users.html', {'users': users})

@staff_member_required
def user_detail(request, pk):
    profile = get_object_or_404(UserProfile, pk=pk)
    return render(request, 'user_details.html', {'profile': profile})

@staff_member_required
def user_detail(request, pk):
    profile = get_object_or_404(UserProfile, pk=pk)
    return render(request, 'user_details.html', {'profile': profile})

@staff_member_required
def user_update(request, pk):
    profile = get_object_or_404(UserProfile, pk=pk)
    role = request.POST.get('role')
    if role:
        profile.role = role
        profile.save()
    return redirect('approved-users')


@staff_member_required
def user_toggle(request, pk):
    profile = get_object_or_404(UserProfile, pk=pk)
    profile.is_approved = not profile.is_approved
    profile.save()
    return redirect('approved-users')


@staff_member_required
def user_delete(request, pk):
    profile = get_object_or_404(UserProfile, pk=pk)
    profile.user.delete()   # deletes user + profile
    return redirect('approved-users')


def notify_user(request, user_id):
    user = UserProfile.objects.get(id=user_id)

    send_mail(
        'Account Approved',
        'Your account is approved.',
        settings.EMAIL_HOST_USER,
        [user.email],
    )


def flip_album(request, album_id):
    album = get_object_or_404(Album, id=album_id)
    photos = album.photos.filter(is_active=True)

    return render(request, "flip_album.html", {
        "album": album,
        "photos": photos
    })





def album_slideshow_view(request, album_id):
    # 📀 ALBUM
    album = get_object_or_404(Album, id=album_id)

    # 📸 PHOTOS (ORDERED)
    photos = Photo.objects.filter(album=album).order_by('id')

    # 🎵 OPTIONAL MUSIC (AUTO PICK)
    music_dir = os.path.join(settings.MEDIA_ROOT, "music")
    music_url = None

    if os.path.exists(music_dir):
        music_files = [f for f in os.listdir(music_dir) if f.endswith(".mp3")]
        if music_files:
            selected_music = random.choice(music_files)
            music_url = settings.MEDIA_URL + "music/" + selected_music

    return render(request, "slide2.html", {
        "album": album,
        "photos": photos,
        "music_url": music_url,
    })

def album_view(request, album_id):
    album = get_object_or_404(Album, id=album_id)
    photos = Photo.objects.filter(album=album)

    # 🎵 latest music
    music_dir = os.path.join(settings.MEDIA_ROOT, "music")
    selected_music = None

    if os.path.isdir(music_dir):
        mp3s = [
            (f, os.path.getctime(os.path.join(music_dir, f)))
            for f in os.listdir(music_dir)
            if f.lower().endswith(".mp3")
        ]
        if mp3s:
            mp3s.sort(key=lambda x: x[1], reverse=True)
            selected_music = mp3s[0][0]

    music_url = settings.MEDIA_URL + "music/" + selected_music if selected_music else None

    return render(request, "flip_album313.html", {
        "album": album,
        "photos": photos,
        "music_url": music_url,
        "now": timezone.now()
    })

def ai_view(request, album_id):
    album = get_object_or_404(Album, id=album_id)
    photos = Photo.objects.filter(album=album)

    # 🎵 latest music
    music_dir = os.path.join(settings.MEDIA_ROOT, "music")
    selected_music = None

    if os.path.isdir(music_dir):
        mp3s = [
            (f, os.path.getctime(os.path.join(music_dir, f)))
            for f in os.listdir(music_dir)
            if f.lower().endswith(".mp3")
        ]
        if mp3s:
            mp3s.sort(key=lambda x: x[1], reverse=True)
            selected_music = mp3s[0][0]

    music_url = settings.MEDIA_URL + "music/" + selected_music if selected_music else None

    return render(request, "ai_slideshow1.html", {
        "album": album,
        "photos": photos,
        "music_url": music_url,
        "now": timezone.now()
    })

####################################################
####################################################
####################################################
# import os, subprocess, uuid
# from django.conf import settings
# from django.shortcuts import get_object_or_404
# from django.http import FileResponse, HttpResponse
# from .models import Album, Photo
#
#
# def generate_ultra_cinematic(request, album_id):
#
#     album = get_object_or_404(Album, id=album_id)
#     photos = list(Photo.objects.filter(album=album))
#
#     if not photos:
#         return HttpResponse("No photos found")
#
#     # ================= USER INPUT (NEW) =================
#     if request.method == "POST":
#         selected_bg = request.POST.get("bgvideo")
#         selected_music = request.POST.get("music")
#
#         bg_file = request.FILES.get("bg_upload")
#         music_file = request.FILES.get("music_upload")
#     else:
#         return HttpResponse("❌ Use POST method")
#
#     # folders ensure
#     bg_folder = os.path.join(settings.MEDIA_ROOT, "background")
#     music_folder = os.path.join(settings.MEDIA_ROOT, "music")
#
#     os.makedirs(bg_folder, exist_ok=True)
#     os.makedirs(music_folder, exist_ok=True)
#
#     # ================= BACKGROUND LOGIC =================
#     bg = None
#
#     if bg_file:
#         filename = str(uuid.uuid4()) + "_" + bg_file.name
#         bg_path = os.path.join(bg_folder, filename)
#
#         with open(bg_path, "wb+") as f:
#             for chunk in bg_file.chunks():
#                 f.write(chunk)
#
#         bg = bg_path
#
#     elif selected_bg:
#         bg = os.path.join(bg_folder, selected_bg)
#
#     else:
#         return HttpResponse("❌ Please select or upload background")
#
#     # ================= MUSIC LOGIC =================
#     music = None
#
#     if music_file:
#         filename = str(uuid.uuid4()) + "_" + music_file.name
#         music_path = os.path.join(music_folder, filename)
#
#         with open(music_path, "wb+") as f:
#             for chunk in music_file.chunks():
#                 f.write(chunk)
#
#         music = music_path
#
#     elif selected_music:
#         music = os.path.join(music_folder, selected_music)
#
#     # ================= FRAMES =================
#     work_dir = os.path.join(settings.MEDIA_ROOT, "video_frames", str(album.id))
#     os.makedirs(work_dir, exist_ok=True)
#
#     frames = []
#
#     for i, p in enumerate(photos):
#         if not p.image or not os.path.exists(p.image.path):
#             continue
#
#         path = os.path.join(work_dir, f"img_{i:03}.jpg")
#
#         with open(p.image.path, "rb") as src:
#             with open(path, "wb") as dst:
#                 dst.write(src.read())
#
#         frames.append(path)
#
#     if not frames:
#         return HttpResponse("❌ No valid images found")
#
#     # ================= EXTRA ASSETS =================
#     light = os.path.join(bg_folder, "light.mp4")
#     grain = os.path.join(bg_folder, "grain.mp4")
#
#     use_bg = bg and os.path.exists(bg)
#     use_light = os.path.exists(light)
#     use_grain = os.path.exists(grain)
#     use_music = music and os.path.exists(music)
#
#     output = os.path.join(settings.MEDIA_ROOT, f"ultra_album_{album.id}.mp4")
#
#     # ================= INPUTS =================
#     inputs = []
#
#     for img in frames:
#         inputs += ["-loop", "1", "-t", "4", "-i", img]
#
#     if use_bg:
#         inputs += ["-stream_loop", "-1", "-i", bg]
#
#     if use_light:
#         inputs += ["-stream_loop", "-1", "-i", light]
#
#     if use_grain:
#         inputs += ["-stream_loop", "-1", "-i", grain]
#
#     if use_music:
#         inputs += ["-i", music]
#
#     # # ================= FILTERS =================
#     # filters = []
#     #
#     # for i in range(len(frames)):
#     #     filters.append(
#     #         f"[{i}:v]"
#     #         "scale=1400:-1,"
#     #         "zoompan=z='min(zoom+0.0007,1.3)':d=125:s=640x720,"  # 👈 50% width FIX
#     #         "fade=t=in:st=0:d=1,"
#     #         "fade=t=out:st=3:d=1"
#     #         f"[v{i}]"
#     #     )
#     #
#     # current = "[v0]"
#     # offset = 3
#     #
#     # for i in range(1, len(frames)):
#     #     filters.append(
#     #         f"{current}[v{i}]"
#     #         f"xfade=transition=fade:duration=1:offset={offset}"
#     #         f"[v{i}out]"
#     #     )
#     #     current = f"[v{i}out]"
#     #     offset += 3
#     #
#     # slideshow = current
#     # index = len(frames)
#     #
#     # if use_bg:
#     #     filters.append(f"[{index}:v]scale=1280:720[bg]")
#     #     filters.append(f"[bg]{slideshow}overlay=(W-w)/2:(H-h)/2[base]")
#     #     current = "[base]"
#     #     index += 1
#     # else:
#     #     current = slideshow
#     #
#     # if use_light:
#     #     filters.append(
#     #         f"[{index}:v]scale=1280:720,format=rgba,colorchannelmixer=aa=0.25[light]"
#     #     )
#     #     filters.append(f"{current}[light]overlay=0:0[tmp1]")
#     #     current = "[tmp1]"
#     #     index += 1
#     #
#     # if use_grain:
#     #     filters.append(
#     #         f"[{index}:v]scale=1280:720,format=rgba,colorchannelmixer=aa=0.15[grain]"
#     #     )
#     #     filters.append(f"{current}[grain]overlay=0:0[v]")
#     # else:
#     #     filters.append(f"{current}null[v]")
#     #
#     # filter_complex = ";".join(filters)
#     # ================= FILTERS (NEW CINEMATIC) =================
#     filters = []
#
#     # 👉 STEP 1: SMALL CARD (sheet size)
#     for i in range(len(frames)):
#         filters.append(
#             f"[{i}:v]"
#             "scale=1400:-1,"
#             "zoompan=z='min(zoom+0.0007,1.3)':d=125:s=700x500,"
#             "fade=t=in:st=0:d=1,"
#             "fade=t=out:st=3:d=1"
#             f"[v{i}]"
#         )
#
#     # 👉 STEP 2: TRANSITIONS
#     current = "[v0]"
#     offset = 3
#
#     for i in range(1, len(frames)):
#         filters.append(
#             f"{current}[v{i}]"
#             f"xfade=transition=fade:duration=1:offset={offset}"
#             f"[v{i}out]"
#         )
#         current = f"[v{i}out]"
#         offset += 3
#
#     slideshow = current
#     index = len(frames)
#
#     # 👉 STEP 3: BACKGROUND BLUR
#     if use_bg:
#         filters.append(f"[{index}:v]scale=1280:720,boxblur=20:1[bg]")
#         index += 1
#     else:
#         filters.append(f"{slideshow}null[bg]")
#
#     # 👉 STEP 4: SHADOW EFFECT
#     filters.append(
#         f"{slideshow}format=rgba,boxblur=8:1,scale=720:520[shadow]"
#     )
#
#     filters.append(
#         f"[bg][shadow]overlay=(W-w)/2+15:(H-h)/2+15[tmpbg]"
#     )
#
#     # 👉 STEP 5: CENTER CARD
#     filters.append(
#         f"[tmpbg]{slideshow}overlay=(W-w)/2:(H-h)/2[base]"
#     )
#
#     current = "[base]"
#
#     # 👉 STEP 6: LIGHT
#     if use_light:
#         filters.append(
#             f"[{index}:v]scale=1280:720,format=rgba,colorchannelmixer=aa=0.25[light]"
#         )
#         filters.append(f"{current}[light]overlay=0:0[tmp1]")
#         current = "[tmp1]"
#         index += 1
#
#     # 👉 STEP 7: GRAIN
#     if use_grain:
#         filters.append(
#             f"[{index}:v]scale=1280:720,format=rgba,colorchannelmixer=aa=0.12[grain]"
#         )
#         filters.append(f"{current}[grain]overlay=0:0[v]")
#     else:
#         filters.append(f"{current}null[v]")
#
#     # 👉 FINAL
#     filter_complex = ";".join(filters)
#
#     # ================= COMMAND =================
#     cmd = [
#         "ffmpeg", "-y",
#         *inputs,
#         "-filter_complex", filter_complex,
#         "-map", "[v]",
#         "-c:v", "libx264",
#         "-preset", "slow",
#         "-crf", "18",
#         "-pix_fmt", "yuv420p",
#     ]
#
#     if use_music:
#         audio_index = len([x for x in inputs if x == "-i"]) - 1
#         cmd += ["-map", f"{audio_index}:a", "-c:a", "aac", "-shortest"]
#
#     cmd.append(output)
#
#     print(" ".join(cmd))
#
#     subprocess.run(cmd)
#
#     if not os.path.exists(output):
#         return HttpResponse("❌ Video render failed")
#
#     return FileResponse(
#         open(output, "rb"),
#         as_attachment=True,
#         filename=f"album_{album.id}.mp4",
#         content_type="video/mp4"
#     )
###################################################
####################################################
###########################################################



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
        #filters.append(f"[{index}:v]scale=1280:720,boxblur=20:1[bg]")
        filters.append(f"[{index}:v]scale=1280:720[bg]")
        index += 1
    else:
        filters.append(f"{slideshow}null[bg]")

    # 👉 STEP 4: SHADOW EFFECT
    # filters.append(
    #     f"{slideshow}format=rgba,boxblur=8:1,scale=720:520[shadow]"
    # )
    filters.append(
        f"{slideshow}format=rgba,scale=720:520[shadow]"
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

def user_logout():
    pass



def download_video(request, album_id):
    video = get_object_or_404(Video, id=id)
    response = HttpResponse(video.video, content_type='video/mp4')
    response['Content-Disposition'] = f'attachment; filename="{video.video.name}"'
    return response



def download_selected_videos(request):
    ids = request.POST.getlist('video_ids')
    videos = Video.objects.filter(id__in=ids)

    zip_buffer = BytesIO()

    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        for video in videos:
            zip_file.write(video.video.path, video.video.name)

    zip_buffer.seek(0)

    response = HttpResponse(zip_buffer, content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename="videos.zip"'

    return response

def delete_video(request, id):
    video = get_object_or_404(Video, id=id)
    video.delete()
    return redirect('album-detail')  # apna URL name use karo

from django.http import HttpResponse
from django.contrib.auth import get_user_model
from album.models import UserProfile

def create_admin(request):
    User = get_user_model()

    username = 'demansahu'
    email = 'demansahu335@gmail.com'
    password = 'Deman@1234!5'

    user, created = User.objects.get_or_create(username=username, email=email)

    if created:
        user.set_password(password)
        user.is_staff = True
        user.is_superuser = True
        user.save()

        # ✅ Profile create + update
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = 'ADMIN'        # 🔥 role set
        profile.is_approved = True    # 🔥 approve
        profile.save()

        return HttpResponse("✅ Superuser + ADMIN profile created")

    else:
        # ✅ Agar already exist karta hai to bhi update kar do
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = 'ADMIN'
        profile.is_approved = True
        profile.save()

        return HttpResponse("⚠️ Superuser already exists (UPDATED to ADMIN)")