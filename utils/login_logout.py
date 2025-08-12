from django.contrib.sessions.models import Session
from django.utils import timezone 





def get_all_logged_in_users():
    # Query all non-expired sessions
    # use timezone.now() instead of datetime.now() in latest versions of Django
    sessions = Session.objects.filter(expire_date__gte=timezone.now())
    uid_list = set()

    # Build a list of user ids from that query
    for session in sessions:
        data = session.get_decoded()
        uid_list.add(data.get('_auth_user_id', None))

    # Query all logged in users based on id list
    return list(uid_list)