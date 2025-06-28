def run_poll_api():
    from GHLWebsiteApp.management.commands import poll_api
    poll_api.Command.handle()
    print("poll_api task executed via cronjob")