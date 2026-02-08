from django.contrib import admin
from .models import ChatRoom, Message

class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ("sender", "content", "timestamp", "is_read")
    can_delete = False

@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ("user1", "user2", "created_at")
    search_fields = ("user1__username", "user2__username")
    list_filter = ("created_at",)
    inlines = [MessageInline]

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("chat_room", "sender", "timestamp", "is_read")
    search_fields = ("sender__username", "content")
    list_filter = ("is_read", "timestamp")
