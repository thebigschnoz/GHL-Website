from django.core.management import call_command

def run_poll_api():
    call_command('poll_api')
    print("poll_api task executed via cronjob")