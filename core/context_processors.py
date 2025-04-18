from datetime import date

def streak_context(request):
    if request.user.is_authenticated:
        return {
            'streak': request.user.profile.streak
        }
    return {}