TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        # Login
        "tagline": "Your couple's activity jar",
        "tab.signin": "Sign in",
        "tab.register": "Register",
        "label.username": "Username",
        "label.password": "Password",
        "label.display_name": "Display name",
        "placeholder.display_name": "How your partner sees you",
        "btn.signin": "Sign in",
        "btn.register": "Create account",
        "placeholder.activity": "Add an activity...",
        # Errors
        "err.username_short": "Username must be at least 3 characters.",
        "err.password_short": "Password must be at least 6 characters.",
        "err.username_taken": "Username already taken.",
        "err.invalid_login": "Invalid username or password.",
        "err.invalid_code": "Invalid code. Check and try again!",
        "err.already_paired": "You're already in a pair!",
        # Pairing
        "pair.title": "Link up with your partner",
        "pair.subtitle": "Create a pair or join an existing one.",
        "pair.start": "Start a pair",
        "pair.start_desc": "Get a code to share with your partner.",
        "pair.generate": "Generate code",
        "pair.join": "Join a pair",
        "pair.join_desc": "Enter the code your partner shared.",
        "pair.join_btn": "Join",
        "pair.placeholder": "e.g. ABC123",
        "pair.share": "Share this code with your partner:",
        "pair.share_hint": "They'll enter it on their pairing screen.",
        "pair.continue": "Continue",
        "pair.waiting": "(waiting for partner)",
        # Header
        "btn.leave": "Leave",
        "btn.logout": "Logout",
        # Activities
        "btn.add": "Add",
        "btn.pick_random": "Pick a random activity!",
        "heading.todo": "To Do",
        "heading.done": "Done",
        "btn.reset_all": "Reset all",
        # Empty / done states
        "empty.title": "Your jar is empty!",
        "empty.subtitle": "Add some activities you'd like to do together.",
        "alldone.title": "You've done everything!",
        "alldone.subtitle": "Reset the list or add new activities.",
        "no_activities": "No activities left!",
        # Picker
        "picker.picking": "Picking...",
        "picker.shaking": "The jar is being shaken!",
        "picker.result": "You should do\u2026",
        "picker.result_sub": "Here's what came out of the jar!",
        "picker.mark_done": "Done! Mark it off",
        "picker.not_now": "Not now",
        # Confirm dialog
        "confirm.delete_activity": "Delete \"{name}\"?",
        "confirm.leave_pair": "Leave this pair?",
        "confirm.yes_delete": "Yes, delete",
        "confirm.yes": "Yes",
        "confirm.cancel": "Cancel",
        # Language
        "lang.en": "English",
        "lang.de": "Deutsch",
    },
    "de": {
        # Login
        "tagline": "Euer Aktivit\u00e4ten-Glas",
        "tab.signin": "Anmelden",
        "tab.register": "Registrieren",
        "label.username": "Benutzername",
        "label.password": "Passwort",
        "label.display_name": "Anzeigename",
        "placeholder.display_name": "So sieht dich dein Partner",
        "btn.signin": "Anmelden",
        "btn.register": "Konto erstellen",
        "placeholder.activity": "Aktivit\u00e4t hinzuf\u00fcgen...",
        # Errors
        "err.username_short": "Benutzername muss mindestens 3 Zeichen lang sein.",
        "err.password_short": "Passwort muss mindestens 6 Zeichen lang sein.",
        "err.username_taken": "Benutzername ist bereits vergeben.",
        "err.invalid_login": "Ung\u00fcltiger Benutzername oder Passwort.",
        "err.invalid_code": "Ung\u00fcltiger Code. Pr\u00fcfe ihn und versuch es nochmal!",
        "err.already_paired": "Du bist bereits in einem Paar!",
        # Pairing
        "pair.title": "Verbinde dich mit deinem Partner",
        "pair.subtitle": "Erstelle ein Paar oder tritt einem bei.",
        "pair.start": "Paar erstellen",
        "pair.start_desc": "Erhalte einen Code zum Teilen mit deinem Partner.",
        "pair.generate": "Code generieren",
        "pair.join": "Paar beitreten",
        "pair.join_desc": "Gib den Code deines Partners ein.",
        "pair.join_btn": "Beitreten",
        "pair.placeholder": "z.B. ABC123",
        "pair.share": "Teile diesen Code mit deinem Partner:",
        "pair.share_hint": "Er/sie gibt ihn auf der Pairing-Seite ein.",
        "pair.continue": "Weiter",
        "pair.waiting": "(wartet auf Partner)",
        # Header
        "btn.leave": "Verlassen",
        "btn.logout": "Abmelden",
        # Activities
        "btn.add": "Hinzuf\u00fcgen",
        "btn.pick_random": "Zuf\u00e4llige Aktivit\u00e4t w\u00e4hlen!",
        "heading.todo": "Offen",
        "heading.done": "Erledigt",
        "btn.reset_all": "Alle zur\u00fccksetzen",
        # Empty / done states
        "empty.title": "Euer Glas ist leer!",
        "empty.subtitle": "F\u00fcgt Aktivit\u00e4ten hinzu, die ihr zusammen machen wollt.",
        "alldone.title": "Ihr habt alles geschafft!",
        "alldone.subtitle": "Setzt die Liste zur\u00fcck oder f\u00fcgt neue Aktivit\u00e4ten hinzu.",
        "no_activities": "Keine Aktivit\u00e4ten \u00fcbrig!",
        # Picker
        "picker.picking": "Wird ausgew\u00e4hlt...",
        "picker.shaking": "Das Glas wird gesch\u00fcttelt!",
        "picker.result": "Ihr solltet\u2026",
        "picker.result_sub": "Das kam aus dem Glas!",
        "picker.mark_done": "Erledigt! Abhaken",
        "picker.not_now": "Jetzt nicht",
        # Confirm dialog
        "confirm.delete_activity": "\"{name}\" l\u00f6schen?",
        "confirm.leave_pair": "Paar verlassen?",
        "confirm.yes_delete": "Ja, l\u00f6schen",
        "confirm.yes": "Ja",
        "confirm.cancel": "Abbrechen",
        # Language
        "lang.en": "English",
        "lang.de": "Deutsch",
    },
}

SUPPORTED_LANGS = list(TRANSLATIONS.keys())
DEFAULT_LANG = "en"


def t(key: str, lang: str = DEFAULT_LANG, **kwargs: str) -> str:
    """Look up a translation key, falling back to English."""
    text = TRANSLATIONS.get(lang, {}).get(key) or TRANSLATIONS[DEFAULT_LANG].get(key, key)
    if kwargs:
        text = text.format(**kwargs)
    return text
