from django.core.management import call_command

def run_poll_api():
    call_command('poll_api')
    print("poll_api task executed via cronjob")

def run_update_clinch():
    call_command('updateclinch', gameplayed=True)
    print("updateclinch task executed via cronjob")