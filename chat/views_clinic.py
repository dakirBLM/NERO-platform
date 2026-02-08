
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from .models import ChatRoom, Message
from accounts.models import User
from patients.models import Patient
from django.db.models import Q
from django.http import JsonResponse

@login_required
def start_chat_with_patient_clinic(request):
    """Start a chat between the current clinic and a patient (from clinic side)."""
    patient_id = request.GET.get('patient_id')
    if not patient_id or not hasattr(request.user, 'clinic'):
        return redirect('chat_room_list_clinic')
    try:
        patient = Patient.objects.get(id=patient_id)
        other_user = patient.user
    except (Patient.DoesNotExist, User.DoesNotExist, AttributeError):
        return redirect('chat_room_list_clinic')
    if other_user == request.user:
        return redirect('chat_room_list_clinic')
    chat_room = ChatRoom.objects.filter(
        Q(user1=request.user, user2=other_user) | Q(user1=other_user, user2=request.user)
    ).first()
    if not chat_room:
        chat_room = ChatRoom.objects.create(user1=request.user, user2=other_user)
    return redirect(reverse('chat_room_view_clinic', args=[chat_room.id]))

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.urls import reverse
from .models import ChatRoom, Message
from accounts.models import User
from patients.models import Patient
from django.db.models import Q

@login_required
def chat_room_list_clinic(request):
    if not hasattr(request.user, 'clinic'):
        return redirect('login')
    chat_rooms = ChatRoom.objects.filter(Q(user1=request.user) | Q(user2=request.user))
    rooms = []
    for room in chat_rooms:
        other = room.user2 if room.user1 == request.user else room.user1
        # Only show rooms where the other user is a patient
        if hasattr(other, 'patient'):
            unread_count = room.messages.filter(is_read=False).exclude(sender=request.user).count()
            rooms.append({'room': room, 'other': other, 'unread_count': unread_count})
    context = {
        'rooms': rooms,
        'clinic': request.user.clinic,
    }
    return render(request, 'chat/chat_room_list_clinic.html', context)

@login_required
def chat_room_view_clinic(request, room_id):
    if not hasattr(request.user, 'clinic'):
        return redirect('login')
    chat_room = get_object_or_404(ChatRoom, id=room_id)
    other = chat_room.user2 if chat_room.user1 == request.user else chat_room.user1
    if not hasattr(other, 'patient'):
        return redirect('chat_room_list_clinic')
    chat_room.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)
    messages = chat_room.messages.order_by('timestamp')
    context = {'chat_room': chat_room, 'messages': messages, 'clinic': request.user.clinic, 'other': other}
    return render(request, 'chat/chat_room_clinic.html', context)


@login_required
def unread_count_clinic(request):
    """Return JSON with total unread messages for clinic user."""
    if not hasattr(request.user, 'clinic'):
        return JsonResponse({'unread': 0})
    chat_rooms = ChatRoom.objects.filter(Q(user1=request.user) | Q(user2=request.user))
    total_unread = Message.objects.filter(chat_room__in=chat_rooms, is_read=False).exclude(sender=request.user).count()
    return JsonResponse({'unread': total_unread})
