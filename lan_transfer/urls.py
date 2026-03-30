from django.urls import path

from .views import (
    TransferPageView,
    create_room,
    join_room,
    post_signal,
    poll_signals,
    room_info,
)

urlpatterns = [
    path('', TransferPageView.as_view(), name='lan-transfer-page'),
    path('api/create-room/', create_room, name='lan-transfer-create-room'),
    path('api/join-room/', join_room, name='lan-transfer-join-room'),
    path('api/signal/', post_signal, name='lan-transfer-post-signal'),
    path('api/poll/', poll_signals, name='lan-transfer-poll'),
    path('api/room-info/', room_info, name='lan-transfer-room-info'),
]
