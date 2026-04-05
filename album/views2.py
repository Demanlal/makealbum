import io, zipfile,qrcode
import os

from django.conf import settings
from django.core.mail import send_mail
from django.http import HttpResponse, FileResponse
from sqlparse.filters import output

from .forms import AlbumRequestForm, RegisterForm, LoginForm
from .models import Photo, UserProfile, Album
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.urls import reverse
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.admin.views.decorators import staff_member_required


def album_list(request):
    albums = Album.objects.all().order_by('-created_at')
    return render(request, 'create_albums.html', {'albums': albums})



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


# @login_required
# def request_album(request):
#     if request.method == 'POST':
#         form = AlbumRequestForm(request.POST)
#         if form.is_valid():
#             album = form.save(commit=False)
#             album.created_by = request.user
#             album.status = 'PENDING'
#             album.save()
#             return redirect('album-request-success')
#     else:
#         form = AlbumRequestForm()
#
#     return render(request, 'request_album.html', {'form': form})

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
    return render(request, 'album_details2.html', {
        'album': album,
        'photos': photos
    })

@login_required
def upload_photo(request, album_id):

    try:
        album = Album.objects.get(id=album_id)
    except Album.DoesNotExist:
        messages.error(request, "Album not found.")
        return redirect('album-list')

    # 🔒 Owner check
    if album.created_by != request.user:
        messages.error(request, "You are not allowed to upload photos to this album.")
        return render(request, 'album_details2.html', {'album': album})

    # 🔒 Approval check
    if album.status != 'APPROVED':
        messages.warning(request, "Album is not approved yet.")
        return render(request, 'album_details2.html', {'album': album})

    if request.method == 'POST':
        image = request.FILES.get('image')
        if image:
            Photo.objects.create(
                album=album,
                image=image,
                uploaded_by=request.user
            )
            messages.success(request, "Photo uploaded successfully!")
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




# def register(request):
#     if request.method == 'POST':
#         form = RegisterForm(request.POST)
#         if form.is_valid():
#             user = form.save()
#             UserProfile.objects.create(user=user)  # role=PENDING
#             user = User.objects.create_user(...)
#             profile, created = UserProfile.objects.get_or_create(user=user)
#             return redirect('login')
#     else:
#         form = RegisterForm()
#
#     return render(request, 'register.html', {'form': form})

# def register(request):
#     if request.method == 'POST':
#         form = RegisterForm(request.POST)
#         if form.is_valid():
#             user = form.save()   # ✅ user sirf ek baar create
#
#             # ✅ profile safe way me create
#             UserProfile.objects.get_or_create(user=user)
#
#             return redirect('login')
#     else:
#         form = RegisterForm()
#
#     return render(request, 'register.html', {'form': form})


def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():

            # ✅ Create user (ONLY ONCE)
            user = form.save()

            # ✅ Create user profile safely
            UserProfile.objects.get_or_create(user=user)

            # ✅ Send welcome email (dynamic receiver)
            if user.email:   # safety check
                send_mail(
                    'Welcome to Our App',
                    'Your account has been created successfully.',
                    settings.EMAIL_HOST_USER,
                    [user.email],
                    fail_silently=False,
                )

            return redirect('login')
    else:
        form = RegisterForm()

    return render(request, 'register.html', {'form': form})



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
                return redirect('dashboard')

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

# from django.shortcuts import render, get_object_or_404
# from .models import Album
#
# def ai_slideshow(request, album_id):
#     album = get_object_or_404(
#         Album,
#         id=album_id,
#         status='APPROVED'
#     )
#
#     photos = album.photos.filter(is_active=True)
#
#     return render(request, "ai_slideshow.html", {
#         "album": album,
#         "photos": photos
#     })
from django.shortcuts import render, get_object_or_404
from .models import Album

def ai_slideshow(request, album_id):
    album = get_object_or_404(
        Album,
        id=album_id,
        status="APPROVED"
    )

    photos = album.photos.filter(is_active=True)

    return render(request, "ai_slideshow1.html", {
        "album": album,
        "photos": photos
    })


from django.shortcuts import render, get_object_or_404
from .models import Album

def flip_album(request, album_id):
    album = get_object_or_404(Album, id=album_id)
    photos = album.photos.filter(is_active=True)

    return render(request, "flip_album.html", {
        "album": album,
        "photos": photos
    })






def album_view1(request, album_id):
    album = Album.objects.get(id=album_id)
    photos = Photo.objects.filter(album=album)

    # 🎵 MUSIC FOLDER PATH
    music_dir = os.path.join(settings.MEDIA_ROOT, "music")

    # 🎶 ALL MP3 FILES
    music_files = [
        f for f in os.listdir(music_dir)
        if f.endswith(".mp3")
    ]

    # 🧠 RANDOM PICK
    selected_music = random.choice(music_files) if music_files else None

    music_url = (
        settings.MEDIA_URL + "music/" + selected_music
        if selected_music else None
    )

    return render(request, "new_ky1.html", {
        "album": album,
        "photos": photos,
        "music_url": music_url
    })

import os
import random
from django.conf import settings
from django.shortcuts import render, get_object_or_404
from .models import Album, Photo


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


def flip_album1(request, album_id):
    album = get_object_or_404(Album, id=album_id)
    photos = album.photos.filter(is_active=True)

    return render(request, "s2/new_ky2.html", {
        "album": album,
        "photos": photos
    })

# def flip_album2(request, album_id):
#     album = get_object_or_404(Album, id=album_id)
#     photos = album.photos.filter(is_active=True)
#
#     return render(request, "ht.html", {
#         "album": album,
#         "photos": photos
#     })

def flip_album2(request, album_id):
    album = get_object_or_404(Album, id=album_id)
    photos = album.photos.filter(is_active=True)

    return render(request, "s2/flip_album2.html", {
        "album": album,
        "photos": photos
    })

def album_flipbook(request, album_id):
    album = get_object_or_404(Album, id=album_id)
    photos = Photo.objects.filter(album=album).order_by('id')

    context = {
        'album': album,
        'photos': photos,
    }

    return render(request, 's2/new2.html', context)





import os, subprocess
from django.conf import settings
from django.shortcuts import render, get_object_or_404
from django.http import FileResponse
from django.utils import timezone
from .models import Album, Photo

import os
import random
from django.conf import settings

# def album_view(request, album_id):
#     album = Album.objects.get(id=album_id)
#     photos = Photo.objects.filter(album=album)
#
#     # 🎵 MUSIC FOLDER PATH
#     music_dir = os.path.join(settings.MEDIA_ROOT, "music")
#
#     # 🎶 ALL MP3 FILES
#     music_files = [
#         f for f in os.listdir(music_dir)
#         if f.endswith(".mp3")
#     ]
#
#     # 🧠 RANDOM PICK
#     selected_music = random.choice(music_files) if music_files else None
#
#     music_url = (
#         settings.MEDIA_URL + "music/" + selected_music
#         if selected_music else None
#     )
#
#     return render(request, "flip_album4.html", {
#         "album": album,
#         "photos": photos,
#         "music_url": music_url
#     })

import os
from django.conf import settings

# def album_view(request, album_id):
#     album = Album.objects.get(id=album_id)
#     photos = Photo.objects.filter(album=album)
#
#     # 🎵 MUSIC FOLDER PATH
#     music_dir = os.path.join(settings.MEDIA_ROOT, "music")
#
#     selected_music = None
#
#     if os.path.exists(music_dir):
#         mp3_files = [
#             f for f in os.listdir(music_dir)
#             if f.lower().endswith(".mp3")
#         ]
#
#         if mp3_files:
#             # 🆕 NEWEST MP3 (last modified)
#             mp3_files.sort(
#                 key=lambda x: os.path.getmtime(os.path.join(music_dir, x)),
#                 reverse=True
#             )
#             selected_music = mp3_files[0]
#
#     music_url = (
#         settings.MEDIA_URL + "music/" + selected_music
#         if selected_music else None
#     )
#
#     return render(request, "flip_album5.html", {
#         "album": album,
#         "photos": photos,
#         "music_url": music_url
#     })

import os
from django.conf import settings

# def album_view(request, album_id):
#     album = Album.objects.get(id=album_id)
#     photos = Photo.objects.filter(album=album)
#
#     music_dir = os.path.join(settings.MEDIA_ROOT, "music")
#     selected_music = None
#
#     if os.path.isdir(music_dir):
#         mp3_files = []
#
#         for f in os.listdir(music_dir):
#             if f.lower().endswith(".mp3"):
#                 full_path = os.path.join(music_dir, f)
#                 mp3_files.append((f, os.path.getctime(full_path)))
#
#         if mp3_files:
#             # 🆕 NEWEST CREATED FILE
#             mp3_files.sort(key=lambda x: x[1], reverse=True)
#             selected_music = mp3_files[0][0]
#
#     music_url = (
#         settings.MEDIA_URL + "music/" + selected_music
#         if selected_music else None
#     )
#
#     return render(request, "flip_album5.html", {
#         "album": album,
#         "photos": photos,
#         "music_url": music_url
#     })


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

    return render(request, "flip_album31.html", {
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

# import os, subprocess
# from django.conf import settings
# from django.shortcuts import get_object_or_404
# from django.http import FileResponse
# from .models import Album, Photo
#
#
# def generate_album_video(request, album_id):
#     album = get_object_or_404(Album, id=album_id)
#     photos = list(Photo.objects.filter(album=album))
#
#     work_dir = os.path.join(settings.MEDIA_ROOT, "video_frames", str(album.id))
#     os.makedirs(work_dir, exist_ok=True)
#
#     frames = []
#
#     for i, p in enumerate(photos):
#         path = os.path.join(work_dir, f"f_{i:03}.jpg")
#         with open(p.image.path, "rb") as src, open(path, "wb") as dst:
#             dst.write(src.read())
#         frames.append(path)
#
#     for i, p in enumerate(reversed(photos)):
#         path = os.path.join(work_dir, f"r_{i:03}.jpg")
#         with open(p.image.path, "rb") as src, open(path, "wb") as dst:
#             dst.write(src.read())
#         frames.append(path)
#
#     list_file = os.path.join(work_dir, "list.txt")
#     with open(list_file, "w") as f:
#         for img in frames:
#             f.write(f"file '{img}'\n")
#             f.write("duration 4\n")
#         f.write(f"file '{frames[-1]}'\n")
#
#     video_path = os.path.join(settings.MEDIA_ROOT, f"album_{album.id}.mp4")
#
#     # latest music
#     music = None
#     music_dir = os.path.join(settings.MEDIA_ROOT, "music")
#     if os.path.isdir(music_dir):
#         mp3s = sorted(
#             [f for f in os.listdir(music_dir) if f.endswith(".mp3")],
#             key=lambda x: os.path.getctime(os.path.join(music_dir, x)),
#             reverse=True
#         )
#         if mp3s:
#             music = os.path.join(music_dir, mp3s[0])
#
#     cmd = [
#         "ffmpeg","-y",
#         "-f","concat","-safe","0",
#         "-i",list_file,
#         "-i", music if music else "anullsrc",
#         "-vf","scale=1280:720,format=yuv420p",
#         "-c:v","libx264",
#         "-pix_fmt","yuv420p",
#         "-c:a","aac",
#         "-shortest",
#         video_path
#     ]
#
#     #subprocess.run(cmd)
#     result = subprocess.run(cmd, capture_output=True, text=True)
#     print("STDOUT:", result.stdout)
#     print("STDERR:", result.stderr)
#
#     # response = FileResponse(open(video_path,"rb"), content_type="video/mp4")
#     # response["Content-Disposition"] = f'attachment; filename="album_{album.id}.mp4"'
#     # return response
#     response = FileResponse(open(output, "rb"), content_type="video/mp4")
#     response["Content-Disposition"] = f'attachment; filename="album_{album.id}.mp4"'
#     return response



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

    if audio_index is not None:
        cmd += ["-map", f"{audio_index}:a"]
    audio_index = len(frames) + 1

    # =========================
    # DYNAMIC AUDIO INDEX
    # =========================
    total_inputs = len([x for x in inputs if x == "-i"])
    audio_index = total_inputs - 1

    map_audio = f"{audio_index}:a"
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

