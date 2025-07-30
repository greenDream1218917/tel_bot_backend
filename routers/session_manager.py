# Shared session manager for Telegram sessions
active_sessions = {}

def get_active_sessions():
    return active_sessions

def add_session(session_name, session_data):
    active_sessions[session_name] = session_data

def get_session(session_name):
    return active_sessions.get(session_name)

def remove_session(session_name):
    if session_name in active_sessions:
        del active_sessions[session_name] 