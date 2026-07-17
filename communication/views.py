from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages as django_messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q
from core.decorators import role_required
from core.utils import paginate_queryset
from .models import Announcement, Notification, Message
from .forms import AnnouncementForm, MessageComposeForm, MessageReplyForm


# ─── Announcements ────────────────────────────────────────────

@login_required
def announcement_list(request):
    """Public-facing: show published announcements visible to user's role."""
    now = timezone.now()
    qs = Announcement.objects.filter(is_published=True).filter(
        Q(expiry_date__isnull=True) | Q(expiry_date__gte=now)
    ).filter(
        Q(publish_date__isnull=True) | Q(publish_date__lte=now)
    ).order_by('-created_at')
    visible = [a for a in qs if a.is_visible_to(request.user)]
    announcements = paginate_queryset(visible, request, per_page=15)
    return render(request, 'communication/announcement_list.html', {'announcements': announcements})


@login_required
@role_required('SUPER_ADMIN', 'ICT_ADMIN', 'PRINCIPAL', 'VICE_PRINCIPAL')
def announcement_manage(request):
    """Staff view: manage all announcements."""
    qs = Announcement.objects.select_related('author').order_by('-created_at')
    announcements = paginate_queryset(qs, request, per_page=20)
    return render(request, 'communication/announcement_manage.html', {'announcements': announcements})


@login_required
@role_required('SUPER_ADMIN', 'ICT_ADMIN', 'PRINCIPAL', 'VICE_PRINCIPAL')
def announcement_create(request):
    if request.method == 'POST':
        form = AnnouncementForm(request.POST)
        if form.is_valid():
            ann = form.save(commit=False)
            ann.author = request.user
            if ann.is_published and not ann.publish_date:
                ann.publish_date = timezone.now()
            ann.save()
            django_messages.success(request, 'Announcement created.')
            return redirect('communication:manage')
    else:
        form = AnnouncementForm()
    return render(request, 'communication/announcement_form.html', {'form': form, 'title': 'New Announcement'})


@login_required
@role_required('SUPER_ADMIN', 'ICT_ADMIN', 'PRINCIPAL', 'VICE_PRINCIPAL')
def announcement_update(request, pk):
    ann = get_object_or_404(Announcement, pk=pk)
    if request.method == 'POST':
        form = AnnouncementForm(request.POST, instance=ann)
        if form.is_valid():
            form.save()
            django_messages.success(request, 'Announcement updated.')
            return redirect('communication:manage')
    else:
        form = AnnouncementForm(instance=ann)
    return render(request, 'communication/announcement_form.html', {'form': form, 'ann': ann, 'title': 'Edit Announcement'})


@login_required
@role_required('SUPER_ADMIN', 'ICT_ADMIN', 'PRINCIPAL', 'VICE_PRINCIPAL')
def announcement_delete(request, pk):
    ann = get_object_or_404(Announcement, pk=pk)
    if request.method == 'POST':
        ann.delete()
        django_messages.success(request, 'Announcement deleted.')
        return redirect('communication:manage')
    return render(request, 'communication/announcement_confirm_delete.html', {'ann': ann})


@login_required
@role_required('SUPER_ADMIN', 'ICT_ADMIN', 'PRINCIPAL', 'VICE_PRINCIPAL')
def announcement_publish(request, pk):
    ann = get_object_or_404(Announcement, pk=pk)
    ann.is_published = not ann.is_published
    if ann.is_published and not ann.publish_date:
        ann.publish_date = timezone.now()
    ann.save(update_fields=['is_published', 'publish_date'])
    state = 'published' if ann.is_published else 'unpublished'
    django_messages.success(request, f'Announcement {state}.')
    return redirect('communication:manage')


# ─── Notifications ─────────────────────────────────────────────

@login_required
def notification_list(request):
    notifs = Notification.objects.filter(user=request.user).order_by('-created_at')
    notifs_page = paginate_queryset(notifs, request, per_page=20)
    return render(request, 'communication/notification_list.html', {'notifications': notifs_page})


@login_required
def notification_mark_read(request, pk):
    notif = get_object_or_404(Notification, pk=pk, user=request.user)
    notif.is_read = True
    notif.save(update_fields=['is_read'])
    if notif.link:
        return redirect(notif.link)
    return redirect('communication:notifications')


@login_required
def notification_mark_all_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': 'ok'})
    return redirect('communication:notifications')


# ─── Messages ─────────────────────────────────────────────────

@login_required
def inbox(request):
    msgs = Message.objects.filter(
        recipient=request.user,
        is_archived_by_recipient=False
    ).select_related('sender').order_by('-created_at')
    msgs_page = paginate_queryset(msgs, request, per_page=20)
    unread_count = Message.objects.filter(recipient=request.user, is_read=False).count()
    return render(request, 'communication/inbox.html', {'messages_list': msgs_page, 'unread_count': unread_count})


@login_required
def sent_messages(request):
    msgs = Message.objects.filter(
        sender=request.user,
        is_archived_by_sender=False
    ).select_related('recipient').order_by('-created_at')
    msgs_page = paginate_queryset(msgs, request, per_page=20)
    return render(request, 'communication/sent.html', {'messages_list': msgs_page})


@login_required
def message_compose(request):
    if request.method == 'POST':
        form = MessageComposeForm(request.POST)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.sender = request.user
            msg.save()
            # Notify recipient
            Notification.send(
                user=msg.recipient,
                title='New Message',
                message=f'You have a new message from {request.user.get_full_name()}: "{msg.subject}"',
                notification_type='INFO',
                link=f'/communication/messages/{msg.pk}/'
            )
            django_messages.success(request, 'Message sent.')
            return redirect('communication:sent')
    else:
        recipient_id = request.GET.get('to')
        initial = {}
        if recipient_id:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            try:
                initial['recipient'] = User.objects.get(pk=recipient_id)
            except User.DoesNotExist:
                pass
        form = MessageComposeForm(initial=initial)
    return render(request, 'communication/message_compose.html', {'form': form})


@login_required
def message_detail(request, pk):
    msg = get_object_or_404(Message, pk=pk)
    if msg.recipient == request.user and not msg.is_read:
        msg.is_read = True
        msg.save(update_fields=['is_read'])
    # Security: only sender or recipient can view
    if request.user not in (msg.sender, msg.recipient):
        django_messages.error(request, 'Access denied.')
        return redirect('communication:inbox')
    reply_form = MessageReplyForm()
    replies = msg.replies.select_related('sender', 'recipient').order_by('created_at')
    return render(request, 'communication/message_detail.html', {
        'message': msg, 'reply_form': reply_form, 'replies': replies
    })


@login_required
def message_reply(request, pk):
    parent_msg = get_object_or_404(Message, pk=pk)
    if request.user not in (parent_msg.sender, parent_msg.recipient):
        django_messages.error(request, 'Access denied.')
        return redirect('communication:inbox')
    if request.method == 'POST':
        form = MessageReplyForm(request.POST)
        if form.is_valid():
            recipient = parent_msg.sender if request.user == parent_msg.recipient else parent_msg.recipient
            reply = Message.objects.create(
                sender=request.user,
                recipient=recipient,
                subject=f'Re: {parent_msg.subject}',
                body=form.cleaned_data['body'],
                parent=parent_msg
            )
            Notification.send(
                user=recipient,
                title='New Reply',
                message=f'{request.user.get_full_name()} replied to your message: "{parent_msg.subject}"',
                notification_type='INFO',
                link=f'/communication/messages/{reply.pk}/'
            )
            django_messages.success(request, 'Reply sent.')
    return redirect('communication:message-detail', pk=pk)
