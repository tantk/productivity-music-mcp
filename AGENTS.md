# FocusLine Agent Instructions

When the user asks to play music, start a pomodoro, or anything music-related:

1. Call `set_context()` first with a brief summary of what the user is working on and how they seem to be feeling. Base this on the conversation so far.

2. Then call `music()` with the user's request.

Example:
```
set_context("User has been debugging a threading issue for 30 minutes, seems stuck but determined")
music("focus music")
```

This helps the AI DJ pick better music and timer settings.
