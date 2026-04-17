from django.urls import path
from . import views

urlpatterns = [
    path('album/list', views.album_list, name='album-list'),
    path('album/create/', views.request_album, name='create-album'),
    path('album/<uuid:album_id>/', views.album_detail, name='album-detail'),
    path('album/<uuid:album_id>/edit/', views.edit_album, name='album-edit'),
    path('photo/<int:photo_id>/delete/', views.delete_photo, name='delete-photo'),
    path('album-approval/', views.approve_albums, name='approve-albums'),
    path(
        'album/<uuid:album_id>/',
        views.album_detail,
        name='album-detail'
    ),
    path("video/delete/<int:video_id>/", views.delete_video, name="delete-video"),
    path('users/approved/', views.approved_users, name='approved-users'),
    path('', views.user_login, name='login'),
    path('', views.user_logout, name='logout'),

    path('user-approval/', views.approve_users, name='user-approval'),
    path('photo/download/<int:photo_id>/', views.download_photo, name='download-photo'),
    path('album/<uuid:album_id>/download/', views.download_album, name='download-album'),
    path('photos/download-selected/', views.download_selected_photos, name='download-selected'),
    path('album/request/success/',views.album_request_success,name='album-request-success'),
    path('users/<int:pk>/', views.user_detail, name='user-detail'),
    path('users/<int:pk>/update/', views.user_update, name='user-update'),
    path('users/<int:pk>/toggle/', views.user_toggle, name='user-toggle'),
    path('users/<int:pk>/delete/', views.user_delete, name='user-delete'),

    path('slideshow/<uuid:album_id>/', views.animated_slideshow, name='slideshow'),

    path(
        "album/<uuid:album_id>/mobile/",
        views.album_view,
        name="flip_album"
    ),
    path(
        "album/<uuid:album_id>/desktop/",
        views.ai_view,
        name="ai_view"
    ),
    path("album/<uuid:album_id>/", views.album_view, name="album"),
    path("album/<uuid:album_id>/video/", views.generate_ultra_cinematic, name="album_video1"),

    path('upload-media/<uuid:album_id>/', views.upload_media, name='upload-media'),
    path('download-video/<int:id>/', views.download_video, name='download-video'),
    path('delete-video/<int:id>/', views.delete_video, name='delete-video'),
    path('download-selected-videos/', views.download_selected_videos, name='download-selected-videos'),

]



