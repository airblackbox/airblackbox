"""Session passport - provable, legitimate agent activity for platforms.

When an agent acts inside a logged-in session (a recruiter's LinkedIn,
a support console, any authenticated web app) there is no API to proxy -
the actions ARE the browser events. The passport records each action as a
chained, covenant-governed receipt and produces a session passport: a
signed, verifiable summary of exactly what the agent did.

    from air_blackbox.passport import BrowserSession

    with BrowserSession(covenant="recruiting.yaml", runs_dir="./runs") as s:
        for profile in candidates:
            if s.action("read_profile", target=profile.url).allowed:
                data = driver.read(profile.url)          # your driver
            d = s.action("send_message", target=profile.url)
            if d.needs_approval and human_approves(profile):
                s.approve(d)
                driver.message(profile.url, text)

    passport = s.passport()   # counts, covenant hash, chain status, verdict
    s.export_passport()       # signed .air-evidence bundle

The passport answers the platform's real question - not "was this
automated" but "was it accountable": bounded, human-approved where it
matters, no bulk harvesting, chain intact.
"""

from air_blackbox.passport.session import (
    ActionDecision,
    BrowserSession,
    SessionPassport,
)

__all__ = ["BrowserSession", "ActionDecision", "SessionPassport"]
