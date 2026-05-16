from typing import Dict, List, Tuple


MAX_HISTORY_MESSAGES = 24


class SessionStore:
    """In-memory conversation store keyed by session id and role id."""

    def __init__(self, max_messages: int = MAX_HISTORY_MESSAGES):
        self.max_messages = max_messages
        self._sessions: Dict[Tuple[str, str], List[dict]] = {}

    @property
    def sessions(self) -> Dict[Tuple[str, str], List[dict]]:
        return self._sessions

    def get(self, session_id: str, role_id: str) -> List[dict]:
        return self._sessions.setdefault((session_id, role_id), [])

    def append_turn(self, session_id: str, role_id: str, user_prompt: str, answer: str) -> None:
        history = self.get(session_id, role_id)
        history.extend(
            [
                {"role": "user", "content": user_prompt},
                {"role": "assistant", "content": answer},
            ]
        )
        self._sessions[(session_id, role_id)] = history[-self.max_messages :]

    def reset(self, session_id: str) -> None:
        for key in list(self._sessions):
            if key[0] == session_id:
                del self._sessions[key]

    def clear(self) -> None:
        self._sessions.clear()
